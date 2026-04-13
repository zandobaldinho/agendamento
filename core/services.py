from datetime import timedelta
from django.utils import timezone
from .models import Agendamento, DisponibilidadeHorario


def calcular_hora_fim(data_hora_inicio, duracao_minutos):
    return data_hora_inicio + timedelta(minutes=duracao_minutos)


def validar_dentro_disponibilidade(prestador, data_hora_inicio, data_hora_fim):
    dia_semana = data_hora_inicio.weekday()
    hora_inicio = data_hora_inicio.time()
    hora_fim = data_hora_fim.time()

    disponivel = DisponibilidadeHorario.objects.filter(
        prestador=prestador,
        dia_semana=dia_semana,
        hora_inicio__lte=hora_inicio,
        hora_fim__gte=hora_fim,
    ).exists()

    if not disponivel:
        raise ValueError("Horário fora da disponibilidade do prestador.")


def validar_sem_conflito(prestador, data_hora_inicio, data_hora_fim):
    conflito = Agendamento.objects.filter(
        servico__prestador=prestador,
        status__in=["pendente", "confirmado"],
        data_hora_inicio__lt=data_hora_fim,
        data_hora_fim__gt=data_hora_inicio,
    ).exists()

    if conflito:
        raise ValueError("Conflito de horário com outro agendamento.")