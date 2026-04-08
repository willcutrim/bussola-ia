from django.db.models import Count

from apps.core.repositories import BaseRepository

from .choices import StatusDocumentoChoices
from .models import Documento


class DocumentoRepository(BaseRepository):
    model = Documento

    def get_queryset(self):
        return super().get_queryset().select_related("licitacao", "licitacao__empresa")

    def listar_com_filtros(self, filtros=None):
        filtros = filtros or {}
        queryset = self.get_queryset()

        licitacao = filtros.get("licitacao")
        if licitacao not in (None, ""):
            licitacao_id = getattr(licitacao, "pk", licitacao)
            queryset = queryset.filter(licitacao_id=licitacao_id)

        nome = filtros.get("nome")
        if nome:
            queryset = queryset.filter(nome__icontains=nome)

        tipo = filtros.get("tipo")
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        status = filtros.get("status")
        if status:
            queryset = queryset.filter(status=status)

        data_upload_inicial = filtros.get("data_upload_inicial")
        if data_upload_inicial:
            queryset = queryset.filter(data_upload__date__gte=data_upload_inicial)

        data_upload_final = filtros.get("data_upload_final")
        if data_upload_final:
            queryset = queryset.filter(data_upload__date__lte=data_upload_final)

        return queryset

    def obter_por_id(self, pk):
        return self.get_by_id(pk)

    def listar_por_licitacao(self, licitacao):
        licitacao_id = getattr(licitacao, "pk", licitacao)
        return self.get_queryset().filter(licitacao_id=licitacao_id)

    def listar_por_tipo(self, tipo):
        return self.get_queryset().filter(tipo=tipo)

    def listar_por_status(self, status):
        return self.get_queryset().filter(status=status)

    def listar_pendentes(self):
        return self.listar_por_status(StatusDocumentoChoices.PENDENTE)

    def listar_validados(self):
        return self.listar_por_status(StatusDocumentoChoices.VALIDADO)

    def contar_por_status(self):
        return (
            self.get_queryset()
            .values("status")
            .annotate(total=Count("id"))
            .order_by("status")
        )

    def total_por_licitacao(self, licitacao):
        return self.listar_por_licitacao(licitacao).count()
