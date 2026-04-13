from rest_framework import serializers
from .models import Usuario, Servico, DisponibilidadeHorario, Agendamento


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ["email", "nome", "tipo", "password"]

    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)


class ServicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servico
        fields = "__all__"
        read_only_fields = ["prestador"]


class DisponibilidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisponibilidadeHorario
        fields = "__all__"
        read_only_fields = ["prestador"]

    def validate(self, data):
        if data["hora_inicio"] >= data["hora_fim"]:
            raise serializers.ValidationError("hora_inicio deve ser antes de hora_fim.")
        return data


class AgendamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agendamento
        fields = "__all__"
        read_only_fields = ["cliente", "data_hora_fim", "status", "criado_em"]