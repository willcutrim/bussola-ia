from django.urls import path

from .views import (
    AnaliseCreateView,
    AnaliseDeleteView,
    AnaliseDetailView,
    AnaliseListView,
    AnaliseUpdateView,
)
from .views_dashboard import DashboardIAView
from .views_ai import (
    AnaliseCompararDocumentoView,
    AnaliseComparacaoResultadoView,
    AnaliseExecucaoIAComparacaoView,
    AnaliseExecucaoIADetailView,
    AnaliseExecucaoIAHistoryView,
    AnaliseExecucaoIAReprocessarView,
    AnaliseChecklistResultadoView,
    AnaliseExtrairDadosDocumentoView,
    AnaliseExtracaoResultadoView,
    AnaliseGerarChecklistView,
    AnaliseGerarParecerView,
    AnaliseGerarResumoDocumentoView,
    AnaliseParecerResultadoView,
    AnaliseResumoResultadoView,
)

app_name = "analises"

urlpatterns = [
    path("", AnaliseListView.as_view(), name="list"),
    path("dashboard/ia/", DashboardIAView.as_view(), name="dashboard_ia"),
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
        "<int:pk>/ia/resumo/resultado/",
        AnaliseResumoResultadoView.as_view(),
        name="ia_resumo_resultado",
    ),
    path(
        "<int:pk>/ia/extracao/",
        AnaliseExtrairDadosDocumentoView.as_view(),
        name="ia_extracao",
    ),
    path(
        "<int:pk>/ia/extracao/resultado/",
        AnaliseExtracaoResultadoView.as_view(),
        name="ia_extracao_resultado",
    ),
    path(
        "<int:pk>/ia/parecer/",
        AnaliseGerarParecerView.as_view(),
        name="ia_parecer",
    ),
    path(
        "<int:pk>/ia/parecer/resultado/",
        AnaliseParecerResultadoView.as_view(),
        name="ia_parecer_resultado",
    ),
    path(
        "<int:pk>/ia/comparacao/",
        AnaliseCompararDocumentoView.as_view(),
        name="ia_comparacao",
    ),
    path(
        "<int:pk>/ia/comparacao/resultado/",
        AnaliseComparacaoResultadoView.as_view(),
        name="ia_comparacao_resultado",
    ),
    path(
        "<int:pk>/ia/checklist/",
        AnaliseGerarChecklistView.as_view(),
        name="ia_checklist",
    ),
    path(
        "<int:pk>/ia/checklist/resultado/",
        AnaliseChecklistResultadoView.as_view(),
        name="ia_checklist_resultado",
    ),
    path(
        "<int:pk>/ia/historico/",
        AnaliseExecucaoIAHistoryView.as_view(),
        name="ia_execucao_historico",
    ),
    path(
        "<int:pk>/ia/execucoes/comparacao/",
        AnaliseExecucaoIAComparacaoView.as_view(),
        name="ia_execucao_comparacao",
    ),
    path(
        "<int:pk>/ia/execucoes/<int:execucao_pk>/",
        AnaliseExecucaoIADetailView.as_view(),
        name="ia_execucao_detalhe",
    ),
    path(
        "<int:pk>/ia/execucoes/<int:execucao_pk>/reprocessar/",
        AnaliseExecucaoIAReprocessarView.as_view(),
        name="ia_execucao_reprocessar",
    ),
]
