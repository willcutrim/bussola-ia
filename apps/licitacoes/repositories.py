from django.db.models import Count

from apps.core.repositories import BaseRepository

from .choices import SituacaoChoices
from .models import Licitacao


class LicitacaoRepository(BaseRepository):
    model = Licitacao

    def get_queryset(self):
        return super().get_queryset().select_related("empresa")

    def listar_com_filtros(self, filtros=None):
        filtros = filtros or {}
        queryset = self.get_queryset()

        empresa = filtros.get("empresa")
        if empresa not in (None, ""):
            empresa_id = getattr(empresa, "pk", empresa)
            queryset = queryset.filter(empresa_id=empresa_id)

        numero = filtros.get("numero")
        if numero:
            queryset = queryset.filter(numero__icontains=numero)

        orgao = filtros.get("orgao")
        if orgao:
            queryset = queryset.filter(orgao__icontains=orgao)

        modalidade = filtros.get("modalidade")
        if modalidade:
            queryset = queryset.filter(modalidade=modalidade)

        situacao = filtros.get("situacao")
        if situacao:
            queryset = queryset.filter(situacao=situacao)

        ativa = self._normalize_boolean_filter(filtros.get("ativa"))
        if ativa is not None:
            queryset = queryset.filter(ativa=ativa)

        data_abertura_inicial = filtros.get("data_abertura_inicial")
        if data_abertura_inicial:
            queryset = queryset.filter(data_abertura__gte=data_abertura_inicial)

        data_abertura_final = filtros.get("data_abertura_final")
        if data_abertura_final:
            queryset = queryset.filter(data_abertura__lte=data_abertura_final)

        return queryset

    def obter_por_id(self, pk):
        return self.get_by_id(pk)

    def listar_ativas(self):
        return self.get_queryset().filter(ativa=True)

    def listar_por_empresa(self, empresa):
        empresa_id = getattr(empresa, "pk", empresa)
        return self.get_queryset().filter(empresa_id=empresa_id)

    def obter_por_numero(self, numero):
        return self.get_queryset().filter(numero=numero).first()

    def listar_em_andamento(self):
        return self.get_queryset().filter(situacao=SituacaoChoices.EM_ANDAMENTO)

    def listar_encerradas(self):
        return self.get_queryset().filter(situacao=SituacaoChoices.ENCERRADA)

    def contar_por_situacao(self):
        return (
            self.get_queryset()
            .values("situacao")
            .annotate(total=Count("id"))
            .order_by("situacao")
        )

    def total_ativas(self):
        return self.listar_ativas().count()

    def _normalize_boolean_filter(self, value):
        if value in (None, ""):
            return None

        if isinstance(value, bool):
            return value

        normalized_value = str(value).strip().lower()
        if normalized_value == "true":
            return True
        if normalized_value == "false":
            return False
        return None
