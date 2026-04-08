from django.urls import path

from .views import (
    DocumentoCreateView,
    DocumentoDeleteView,
    DocumentoDetailView,
    DocumentoListView,
    DocumentoUpdateView,
)

app_name = "documentos"

urlpatterns = [
    path("", DocumentoListView.as_view(), name="index"),
    path("novo/", DocumentoCreateView.as_view(), name="create"),
    path("<int:pk>/", DocumentoDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", DocumentoUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", DocumentoDeleteView.as_view(), name="delete"),
]
