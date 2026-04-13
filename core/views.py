from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from django.contrib.auth import authenticate
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from .models import Usuario, Servico, DisponibilidadeHorario, Agendamento
from .serializers import (
    RegistroSerializer, ServicoSerializer,
    DisponibilidadeSerializer, AgendamentoSerializer
)
from .services import calcular_hora_fim, validar_dentro_disponibilidade, validar_sem_conflito


class IsPrestador(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo == "prestador"


class IsCliente(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo == "cliente"


class RegistroView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key})
        return Response({"erro": "Credenciais inválidas."}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ServicoListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsPrestador()]

    def get(self, request):
        if request.user.tipo == "prestador":
            servicos = Servico.objects.filter(prestador=request.user)
        else:
            prestador_id = request.query_params.get("prestador_id")
            if not prestador_id:
                return Response({"erro": "Informe prestador_id."}, status=400)
            servicos = Servico.objects.filter(prestador_id=prestador_id, ativo=True)
        return Response(ServicoSerializer(servicos, many=True).data)

    def post(self, request):
        serializer = ServicoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(prestador=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServicoDetailView(APIView):
    permission_classes = [IsPrestador]

    def get_object(self, pk, user):
        try:
            return Servico.objects.get(pk=pk, prestador=user)
        except Servico.DoesNotExist:
            return None

    def get(self, request, pk):
        servico = self.get_object(pk, request.user)
        if not servico:
            return Response({"erro": "Serviço não encontrado."}, status=404)
        return Response(ServicoSerializer(servico).data)

    def patch(self, request, pk):
        servico = self.get_object(pk, request.user)
        if not servico:
            return Response({"erro": "Serviço não encontrado."}, status=404)
        serializer = ServicoSerializer(servico, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        servico = self.get_object(pk, request.user)
        if not servico:
            return Response({"erro": "Serviço não encontrado."}, status=404)

        tem_agendamento_futuro = Agendamento.objects.filter(
            servico=servico,
            status="confirmado",
            data_hora_inicio__gt=timezone.now()
        ).exists()

        if tem_agendamento_futuro:
            return Response(
                {"erro": "Serviço possui agendamentos futuros confirmados. Desative-o em vez de deletar."},
                status=status.HTTP_409_CONFLICT
            )

        servico.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DisponibilidadeView(APIView):
    permission_classes = [IsPrestador]

    def get(self, request):
        disponibilidades = DisponibilidadeHorario.objects.filter(prestador=request.user)
        return Response(DisponibilidadeSerializer(disponibilidades, many=True).data)

    def post(self, request):
        serializer = DisponibilidadeSerializer(data=request.data)
        if serializer.is_valid():
            dia = serializer.validated_data["dia_semana"]
            hora_inicio = serializer.validated_data["hora_inicio"]
            hora_fim = serializer.validated_data["hora_fim"]

            sobreposicao = DisponibilidadeHorario.objects.filter(
                prestador=request.user,
                dia_semana=dia,
                hora_inicio__lt=hora_fim,
                hora_fim__gt=hora_inicio,
            ).exists()

            if sobreposicao:
                return Response(
                    {"erro": "Já existe uma janela de disponibilidade sobreposta nesse dia."},
                    status=status.HTTP_409_CONFLICT
                )

            serializer.save(prestador=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)


class AgendamentoClienteView(APIView):
    permission_classes = [IsCliente]

    def get(self, request):
        agendamentos = Agendamento.objects.filter(cliente=request.user)
        return Response(AgendamentoSerializer(agendamentos, many=True).data)

    def post(self, request):
        servico_id = request.data.get("servico")
        data_hora_inicio = request.data.get("data_hora_inicio")

        try:
            servico = Servico.objects.get(id=servico_id, ativo=True)
        except Servico.DoesNotExist:
            return Response({"erro": "Serviço não encontrado."}, status=404)

        inicio = parse_datetime(data_hora_inicio)
        if not inicio:
            return Response({"erro": "Data/hora inválida. Use o formato: YYYY-MM-DDTHH:MM:SS"}, status=400)

        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio)

        fim = calcular_hora_fim(inicio, servico.duracao_minutos)
        prestador = servico.prestador

        try:
            validar_dentro_disponibilidade(prestador, inicio, fim)
            validar_sem_conflito(prestador, inicio, fim)
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_409_CONFLICT)

        agendamento = Agendamento.objects.create(
            cliente=request.user,
            servico=servico,
            data_hora_inicio=inicio,
            data_hora_fim=fim,
        )
        return Response(AgendamentoSerializer(agendamento).data, status=201)


class CancelarAgendamentoClienteView(APIView):
    permission_classes = [IsCliente]

    def patch(self, request, pk):
        try:
            agendamento = Agendamento.objects.get(pk=pk, cliente=request.user)
        except Agendamento.DoesNotExist:
            return Response({"erro": "Agendamento não encontrado."}, status=404)

        if agendamento.status != "pendente":
            return Response({"erro": "Só é possível cancelar agendamentos pendentes."}, status=400)

        agendamento.status = "cancelado"
        agendamento.save()
        return Response(AgendamentoSerializer(agendamento).data)


class AgendamentoPrestadorView(APIView):
    permission_classes = [IsPrestador]

    def get(self, request):
        agendamentos = Agendamento.objects.filter(servico__prestador=request.user)

        status_filtro = request.query_params.get("status")
        data_filtro = request.query_params.get("data")

        if status_filtro:
            agendamentos = agendamentos.filter(status=status_filtro)
        if data_filtro:
            agendamentos = agendamentos.filter(data_hora_inicio__date=data_filtro)

        return Response(AgendamentoSerializer(agendamentos, many=True).data)


class GerenciarAgendamentoPrestadorView(APIView):
    permission_classes = [IsPrestador]

    def patch(self, request, pk):
        try:
            agendamento = Agendamento.objects.get(pk=pk, servico__prestador=request.user)
        except Agendamento.DoesNotExist:
            return Response({"erro": "Agendamento não encontrado."}, status=404)

        if agendamento.status == "cancelado":
            return Response({"erro": "Não é possível alterar um agendamento cancelado."}, status=400)

        novo_status = request.data.get("status")
        if novo_status not in ["confirmado", "cancelado"]:
            return Response({"erro": "Status inválido. Use 'confirmado' ou 'cancelado'."}, status=400)

        agendamento.status = novo_status
        agendamento.save()
        return Response(AgendamentoSerializer(agendamento).data)


class ListarPrestadoresView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        prestadores = Usuario.objects.filter(tipo="prestador")
        data = [{"id": p.id, "nome": p.nome, "email": p.email} for p in prestadores]
        return Response(data)