from django.urls import path
from . import views

urlpatterns = [
   
    path("auth/registro/", views.RegistroView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),

    path("servicos/", views.ServicoListCreateView.as_view()),
    path("servicos/<int:pk>/", views.ServicoDetailView.as_view()),

    path("disponibilidade/", views.DisponibilidadeView.as_view()),

    path("agendamentos/", views.AgendamentoClienteView.as_view()),
    path("agendamentos/<int:pk>/cancelar/", views.CancelarAgendamentoClienteView.as_view()),

    path("prestador/agendamentos/", views.AgendamentoPrestadorView.as_view()),
    path("prestador/agendamentos/<int:pk>/", views.GerenciarAgendamentoPrestadorView.as_view()),

    path("prestadores/", views.ListarPrestadoresView.as_view()),
]