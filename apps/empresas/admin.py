from django.contrib import admin

from apps.core.admin import BaseModelAdmin

from .models import ContatoEmpresa, Empresa, EnderecoEmpresa


@admin.register(Empresa)
class EmpresaAdmin(BaseModelAdmin):
    list_display = ("nome", "cnpj", "email", "telefone", "ativa", "updated_at")
    list_filter = ("ativa", "deleted_at")
    search_fields = ("nome", "nome_fantasia", "razao_social", "cnpj", "email")
    ordering = ("nome",)


@admin.register(EnderecoEmpresa)
class EnderecoEmpresaAdmin(BaseModelAdmin):
    list_display = ("empresa", "cidade", "estado", "cep", "updated_at")
    list_filter = ("estado", "deleted_at")
    search_fields = ("empresa__nome", "cidade", "estado", "cep")


@admin.register(ContatoEmpresa)
class ContatoEmpresaAdmin(BaseModelAdmin):
    list_display = ("nome", "empresa", "cargo", "email", "principal", "ativo")
    list_filter = ("principal", "ativo", "deleted_at")
    search_fields = ("nome", "empresa__nome", "cargo", "email", "telefone")
    ordering = ("nome",)
