from django.urls import path

from .views import (
    AnaliseCreateView,
    AnaliseDeleteView,
    AnaliseDetailView,
    AnaliseListView,
    AnaliseUpdateView,
)
from .views_ai import (
    AnaliseCompararDocumentoView,
    AnaliseExtrairDadosDocumentoView,
    AnaliseGerarChecklistView,
    AnaliseGerarParecerView,
    AnaliseGerarResumoDocumentoView,
)

app_name = "analises"

urlpatterns = [
    path("", AnaliseListView.as_view(), name="list"),
    path("novo/", AnaliseCreateView.as_view(), name="create"),
    path("<int:pk>/", AnaliseDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", AnaliseUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", AnaliseDeleteView.as_view(), name="delete"),
    path(
        "<int:pk>/ia/resumo/",
        AnaliseGerarResumoDocumentoView.as_view(),
        name="ia_resumo",
    ),
    path(
        "<int:pk>/ia/extracao/",
        AnaliseExtrairDadosDocumentoView.as_view(),
        name="ia_extracao",
    ),
    path(
        "<int:pk>/ia/parecer/",
        AnaliseGerarParecerView.as_view(),
        name="ia_parecer",
    ),
    path(
        "<int:pk>/ia/comparacao/",
        AnaliseCompararDocumentoView.as_view(),
        name="ia_comparacao",
    ),
    path(
        "<int:pk>/ia/checklist/",
        AnaliseGerarChecklistView.as_view(),
        name="ia_checklist",
    ),
]
