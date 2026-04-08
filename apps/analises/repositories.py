from django.db.models import Count

from apps.core.repositories import BaseRepository

from .choices import StatusAnaliseChoices, StatusExecucaoIAChoices
from .models import Analise, AnaliseExecucaoIA


class AnaliseRepository(BaseRepository):
    model = Analise

    def get_queryset(self):
        return super().get_queryset().select_related(
            "licitacao",
            "licitacao__empresa",
            "documento",
            "responsavel",
        )

    def listar_com_filtros(self, filtros=None):
        filtros = filtros or {}
        queryset = self.get_queryset()

        licitacao = filtros.get("licitacao")
        if licitacao not in (None, ""):
            licitacao_id = getattr(licitacao, "pk", licitacao)
            queryset = queryset.filter(licitacao_id=licitacao_id)

        documento = filtros.get("documento")
        if documento not in (None, ""):
            documento_id = getattr(documento, "pk", documento)
            queryset = queryset.filter(documento_id=documento_id)

        titulo = filtros.get("titulo")
        if titulo:
            queryset = queryset.filter(titulo__icontains=titulo)

        status = filtros.get("status")
        if status:
            queryset = queryset.filter(status=status)

        prioridade = filtros.get("prioridade")
        if prioridade:
            queryset = queryset.filter(prioridade=prioridade)

        responsavel = filtros.get("responsavel")
        if responsavel not in (None, ""):
            responsavel_id = getattr(responsavel, "pk", responsavel)
            queryset = queryset.filter(responsavel_id=responsavel_id)

        data_analise_inicial = filtros.get("data_analise_inicial")
        if data_analise_inicial:
            queryset = queryset.filter(data_analise__date__gte=data_analise_inicial)

        data_analise_final = filtros.get("data_analise_final")
        if data_analise_final:
            queryset = queryset.filter(data_analise__date__lte=data_analise_final)

        return queryset

    def obter_por_id(self, pk):
        return self.get_by_id(pk)

    def listar_por_licitacao(self, licitacao):
        licitacao_id = getattr(licitacao, "pk", licitacao)
        return self.get_queryset().filter(licitacao_id=licitacao_id)

    def listar_por_documento(self, documento):
        documento_id = getattr(documento, "pk", documento)
        return self.get_queryset().filter(documento_id=documento_id)

    def listar_por_responsavel(self, responsavel):
        responsavel_id = getattr(responsavel, "pk", responsavel)
        return self.get_queryset().filter(responsavel_id=responsavel_id)

    def listar_por_prioridade(self, prioridade):
        return self.get_queryset().filter(prioridade=prioridade)

    def listar_pendentes(self):
        return self.get_queryset().filter(status=StatusAnaliseChoices.PENDENTE)

    def listar_em_andamento(self):
        return self.get_queryset().filter(status=StatusAnaliseChoices.EM_ANDAMENTO)

    def listar_concluidas(self):
        return self.get_queryset().filter(status=StatusAnaliseChoices.CONCLUIDA)

    def contar_por_status(self):
        return (
            self.get_queryset()
            .values("status")
            .annotate(total=Count("id"))
            .order_by("status")
        )

    def contar_por_prioridade(self):
        return (
            self.get_queryset()
            .values("prioridade")
            .annotate(total=Count("id"))
            .order_by("prioridade")
        )

    def total_por_licitacao(self, licitacao):
        return self.listar_por_licitacao(licitacao).count()


class AnaliseExecucaoIARepository(BaseRepository):
    model = AnaliseExecucaoIA

    def get_queryset(self):
        return super().get_queryset().select_related(
            "analise",
            "analise__licitacao",
            "analise__documento",
            "analise__responsavel",
        )

    def obter_por_id(self, pk):
        return self.get_by_id(pk)

    def obter_ativa_por_analise_e_tipo(self, analise, tipo_tarefa):
        analise_id = getattr(analise, "pk", analise)
        return (
            self.get_queryset()
            .filter(
                analise_id=analise_id,
                tipo_tarefa=tipo_tarefa,
                status__in=(
                    StatusExecucaoIAChoices.PENDENTE,
                    StatusExecucaoIAChoices.EM_PROCESSAMENTO,
                ),
            )
            .first()
        )

    def listar_por_analise(self, analise):
        analise_id = getattr(analise, "pk", analise)
        return self.get_queryset().filter(analise_id=analise_id)

    def listar_ultimas_por_tipo(self, analise):
        execucoes = self.listar_por_analise(analise).order_by(
            "tipo_tarefa",
            "-solicitada_em",
            "-created_at",
        )
        ultimas_execucoes: dict[str, AnaliseExecucaoIA] = {}
        for execucao in execucoes:
            ultimas_execucoes.setdefault(execucao.tipo_tarefa, execucao)
        return ultimas_execucoes
