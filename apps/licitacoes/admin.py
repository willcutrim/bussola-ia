from django.contrib import admin

from apps.core.admin import BaseModelAdmin

from .models import Licitacao


@admin.register(Licitacao)
class LicitacaoAdmin(BaseModelAdmin):
    list_display = (
        "numero",
        "orgao",
        "empresa",
        "modalidade",
        "situacao",
        "data_abertura",
        "ativa",
    )
    list_filter = ("modalidade", "situacao", "ativa", "deleted_at")
    search_fields = ("numero", "objeto", "orgao", "empresa__nome")
    list_select_related = ("empresa",)
    ordering = ("-data_abertura", "numero")
