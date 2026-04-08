from datetime import timedelta

from django.db.models import Avg, Count, DurationField, Exists, ExpressionWrapper, F, Max, OuterRef
from django.utils import timezone

from apps.core.repositories import BaseRepository

from .choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)
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

    def listar_criticas_sem_parecer_concluido(self, *, limite=10):
        parecer_concluido = AnaliseExecucaoIA.objects.filter(
            analise_id=OuterRef("pk"),
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            status=StatusExecucaoIAChoices.CONCLUIDO,
        )
        return (
            self.get_queryset()
            .filter(prioridade=PrioridadeAnaliseChoices.CRITICA)
            .annotate(possui_parecer_concluido=Exists(parecer_concluido))
            .filter(possui_parecer_concluido=False)
            .order_by("-data_analise", "-created_at")[:limite]
        )


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

    def obter_por_id_e_analise(self, *, analise, execucao_id):
        analise_id = getattr(analise, "pk", analise)
        return self.get_queryset().get(pk=execucao_id, analise_id=analise_id)

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

    def listar_historico(self, analise):
        return self.listar_por_analise(analise).order_by(
            "-solicitada_em",
            "-versao",
            "-created_at",
        )

    def listar_concluidas_por_analise(self, analise):
        return self.listar_por_analise(analise).filter(
            status=StatusExecucaoIAChoices.CONCLUIDO
        )

    def listar_falhas_por_analise(self, analise):
        return self.listar_por_analise(analise).filter(
            status=StatusExecucaoIAChoices.FALHOU
        )

    def listar_por_analise_e_tipo(self, analise, tipo_tarefa):
        return self.listar_por_analise(analise).filter(tipo_tarefa=tipo_tarefa)

    def obter_ultima_por_tipo(self, analise, tipo_tarefa):
        return (
            self.listar_por_analise_e_tipo(analise, tipo_tarefa)
            .order_by("-versao", "-solicitada_em", "-created_at")
            .first()
        )

    def obter_execucao_anterior(self, execucao):
        return (
            self.listar_por_analise_e_tipo(execucao.analise_id, execucao.tipo_tarefa)
            .filter(versao__lt=execucao.versao)
            .order_by("-versao", "-solicitada_em", "-created_at")
            .first()
        )

    def obter_proxima_versao(self, *, analise, tipo_tarefa):
        analise_id = getattr(analise, "pk", analise)
        agregado = (
            self.get_queryset()
            .select_for_update()
            .filter(analise_id=analise_id, tipo_tarefa=tipo_tarefa)
            .aggregate(max_versao=Max("versao"))
        )
        return int(agregado["max_versao"] or 0) + 1

    def listar_ultimas_por_tipo(self, analise):
        execucoes = self.listar_por_analise(analise).order_by(
            "tipo_tarefa",
            "-versao",
            "-solicitada_em",
            "-created_at",
        )
        ultimas_execucoes: dict[str, AnaliseExecucaoIA] = {}
        for execucao in execucoes:
            ultimas_execucoes.setdefault(execucao.tipo_tarefa, execucao)
        return ultimas_execucoes

    def total_execucoes(self):
        return self.get_queryset().count()

    def total_analises_com_uso_ia(self):
        return self.get_queryset().values("analise_id").distinct().count()

    def total_reprocessamentos(self):
        return self.get_queryset().filter(reprocessamento_de__isnull=False).count()

    def total_por_status(self):
        return (
            self.get_queryset()
            .values("status")
            .annotate(total=Count("id"))
            .order_by("status")
        )

    def total_por_tipo_tarefa(self):
        return (
            self.get_queryset()
            .values("tipo_tarefa")
            .annotate(total=Count("id"))
            .order_by("tipo_tarefa")
        )

    def listar_execucoes_recentes(self, limite=10):
        return self.get_queryset().order_by(
            "-solicitada_em",
            "-created_at",
        )[:limite]

    def listar_falhas_recentes(self, limite=10):
        return (
            self.get_queryset()
            .filter(status=StatusExecucaoIAChoices.FALHOU)
            .order_by("-concluida_em", "-solicitada_em", "-created_at")[:limite]
        )

    def tempo_medio_processamento(self):
        agregado = (
            self.get_queryset()
            .filter(
                status=StatusExecucaoIAChoices.CONCLUIDO,
                iniciada_em__isnull=False,
                concluida_em__isnull=False,
            )
            .annotate(
                duracao_processamento=ExpressionWrapper(
                    F("concluida_em") - F("iniciada_em"),
                    output_field=DurationField(),
                )
            )
            .aggregate(media=Avg("duracao_processamento"))
        )
        return agregado["media"]

    def listar_processando_ha_tempo(
        self,
        *,
        limite=10,
        limite_horas=2,
        referencia=None,
    ):
        referencia = referencia or timezone.now()
        limiar = referencia - timedelta(hours=limite_horas)
        return (
            self.get_queryset()
            .filter(
                status=StatusExecucaoIAChoices.EM_PROCESSAMENTO,
                iniciada_em__isnull=False,
                iniciada_em__lte=limiar,
            )
            .order_by("iniciada_em", "solicitada_em")[:limite]
        )

    def listar_analises_com_multiplas_falhas_recentes(
        self,
        *,
        limite=10,
        janela_dias=7,
        minimo_falhas=2,
        referencia=None,
    ):
        referencia = referencia or timezone.now()
        inicio_janela = referencia - timedelta(days=janela_dias)
        return (
            self.get_queryset()
            .filter(
                status=StatusExecucaoIAChoices.FALHOU,
                solicitada_em__gte=inicio_janela,
            )
            .values(
                "analise_id",
                "analise__titulo",
                "analise__licitacao__numero",
            )
            .annotate(
                total_falhas=Count("id"),
                ultima_falha=Max("concluida_em"),
            )
            .filter(total_falhas__gte=minimo_falhas)
            .order_by("-total_falhas", "-ultima_falha", "analise__titulo")[:limite]
        )
