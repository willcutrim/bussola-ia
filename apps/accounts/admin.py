from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "nome_completo",
        "ativo",
        "is_staff",
        "is_superuser",
    )
    search_fields = ("username", "email", "nome_completo")
    list_filter = ("ativo", "is_staff", "is_superuser", "is_active")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Informacoes pessoais",
            {"fields": ("first_name", "last_name", "nome_completo", "email", "telefone")},
        ),
        (
            "Permissoes e status",
            {
                "fields": (
                    "ativo",
                    "deve_trocar_senha",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
        (
            "Informacoes adicionais",
            {
                "fields": (
                    "email",
                    "nome_completo",
                    "telefone",
                    "ativo",
                    "deve_trocar_senha",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
    )
