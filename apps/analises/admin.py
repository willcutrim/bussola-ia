from django.contrib import admin

from apps.core.admin import BaseModelAdmin

from .models import Analise, AnaliseExecucaoIA


@admin.register(Analise)
class AnaliseAdmin(BaseModelAdmin):
    list_display = (
        "titulo",
        "licitacao",
        "documento",
        "status",
        "prioridade",
        "responsavel",
        "data_analise",
    )
    search_fields = (
        "titulo",
        "licitacao__numero",
        "documento__nome",
        "responsavel__username",
        "responsavel__email",
    )
    list_filter = ("status", "prioridade", "data_analise")
    list_select_related = ("licitacao", "documento", "responsavel")
    ordering = ("-data_analise",)


@admin.register(AnaliseExecucaoIA)
class AnaliseExecucaoIAAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "analise",
        "tipo_tarefa",
        "status",
        "tentativas",
        "modelo_utilizado",
        "solicitada_em",
        "concluida_em",
    )
    search_fields = (
        "analise__titulo",
        "analise__licitacao__numero",
        "identificador_task",
        "response_id",
    )
    list_filter = ("tipo_tarefa", "status", "solicitada_em")
    list_select_related = ("analise", "analise__licitacao")
    ordering = ("-solicitada_em",)
    readonly_fields = BaseModelAdmin.readonly_base_fields + (
        "solicitada_em",
        "iniciada_em",
        "concluida_em",
    )
