from django.contrib import admin
from django.urls import include, path

from apps.core.views import home

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("empresas/", include("apps.empresas.urls")),
    path("licitacoes/", include("apps.licitacoes.urls")),
    path("analises/", include("apps.analises.urls")),
    path("documentos/", include("apps.documentos.urls")),
]
