from django.contrib import admin

from apps.core.admin import BaseModelAdmin

from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(BaseModelAdmin):
    list_display = ("nome", "licitacao", "tipo", "status", "data_upload")
    search_fields = ("nome", "licitacao__numero")
    list_filter = ("tipo", "status")
    list_select_related = ("licitacao",)
