from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password, nome, tipo):
        if not email:
            raise ValueError("E-mail obrigatório")
        email = self.normalize_email(email)
        user = self.model(email=email, nome=nome, tipo=tipo)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Usuario(AbstractBaseUser):
    TIPO_CHOICES = [("prestador", "Prestador"), ("cliente", "Cliente")]

    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=150)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    criado_em = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome", "tipo"]

    objects = UsuarioManager()

    def __str__(self):
        return f"{self.nome} ({self.tipo})"


class Servico(models.Model):
    prestador = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="servicos",
        limit_choices_to={"tipo": "prestador"},
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    duracao_minutos = models.PositiveIntegerField()
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class DisponibilidadeHorario(models.Model):
    DIAS = [
        (0, "Segunda"), (1, "Terça"), (2, "Quarta"),
        (3, "Quinta"), (4, "Sexta"), (5, "Sábado"), (6, "Domingo"),
    ]
    prestador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="disponibilidades",
    )
    dia_semana = models.IntegerField(choices=DIAS)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    def __str__(self):
        return f"{self.prestador} - dia {self.dia_semana}"


class Agendamento(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("confirmado", "Confirmado"),
        ("cancelado", "Cancelado"),
    ]
    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="agendamentos_cliente",
        limit_choices_to={"tipo": "cliente"},
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        related_name="agendamentos",
    )
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pendente")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cliente} - {self.servico} - {self.status}"