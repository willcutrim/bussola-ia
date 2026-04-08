from django.urls import path

from . import views

app_name = "empresas"

urlpatterns = [
    path("", views.EmpresaListView.as_view(), name="index"),
    path("nova/", views.EmpresaCreateView.as_view(), name="create"),
    path("<int:pk>/", views.EmpresaDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.EmpresaUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", views.EmpresaDeleteView.as_view(), name="delete"),
    path(
        "enderecos/novo/",
        views.EnderecoEmpresaCreateView.as_view(),
        name="endereco_create",
    ),
    path(
        "enderecos/<int:pk>/editar/",
        views.EnderecoEmpresaUpdateView.as_view(),
        name="endereco_update",
    ),
    path("contatos/", views.ContatoEmpresaListView.as_view(), name="contato_list"),
    path(
        "contatos/novo/",
        views.ContatoEmpresaCreateView.as_view(),
        name="contato_create",
    ),
    path(
        "contatos/<int:pk>/editar/",
        views.ContatoEmpresaUpdateView.as_view(),
        name="contato_update",
    ),
]
