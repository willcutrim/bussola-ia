from django.urls import path

from . import views

app_name = "licitacoes"

urlpatterns = [
    path("", views.LicitacaoListView.as_view(), name="index"),
    path("nova/", views.LicitacaoCreateView.as_view(), name="create"),
    path("<int:pk>/", views.LicitacaoDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.LicitacaoUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", views.LicitacaoDeleteView.as_view(), name="delete"),
]
