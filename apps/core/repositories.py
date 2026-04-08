from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.models import Count, Sum

from apps.empresas.models import Empresa
from apps.licitacoes.models import Licitacao


class BaseRepository:
    model = None

    def __init__(self, queryset=None):
        self.queryset = queryset

    def get_model(self):
        if self.model is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define model."
            )
        return self.model

    def get_queryset(self):
        if self.queryset is not None:
            return self.queryset.all()
        return self.get_model()._default_manager.all()

    def list(self):
        return self.get_queryset()

    def filter(self, **kwargs):
        return self.get_queryset().filter(**kwargs)

    def exists(self, **kwargs):
        return self.filter(**kwargs).exists()

    def get_by_id(self, pk):
        return self.get_queryset().get(pk=pk)

    def create(self, **kwargs):
        return self.get_queryset().create(**kwargs)

    def update(self, instance, **kwargs):
        for field, value in kwargs.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class DashboardRepository:
    def _table_exists(self, model):
        return model._meta.db_table in connection.introspection.table_names()

    def _safe_count(self, model, **filters):
        if not self._table_exists(model):
            return 0
        return model.objects.filter(**filters).count()

    def contar_empresas(self):
        return self._safe_count(Empresa)

    def contar_empresas_ativas(self):
        return self._safe_count(Empresa, ativa=True)

    def contar_licitacoes(self):
        return self._safe_count(Licitacao)

    def contar_licitacoes_ativas(self):
        return self._safe_count(Licitacao, ativa=True)

    def contar_usuarios(self):
        user_model = get_user_model()
        return self._safe_count(user_model)

    def somar_valor_estimado(self):
        if not self._table_exists(Licitacao):
            return 0

        total = Licitacao.objects.filter(valor_estimado__isnull=False).aggregate(
            total=Sum("valor_estimado")
        )["total"]
        return total or 0

    def listar_licitacoes_recentes(self, limit=6):
        if not self._table_exists(Licitacao):
            return []
        return list(
            Licitacao.objects.select_related("empresa")
            .order_by("-created_at")[:limit]
        )

    def listar_empresas_recentes(self, limit=5):
        if not self._table_exists(Empresa):
            return []
        return list(Empresa.objects.order_by("-created_at")[:limit])

    def distribuir_licitacoes_por_situacao(self):
        if not self._table_exists(Licitacao):
            return []

        return list(
            Licitacao.objects.values("situacao")
            .annotate(total=Count("id"))
            .order_by("-total", "situacao")
        )
