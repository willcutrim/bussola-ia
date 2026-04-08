from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import BaseModel
from apps.documentos.models import Documento
from apps.licitacoes.models import Licitacao

from .choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)


class Analise(BaseModel):
    licitacao = models.ForeignKey(
        Licitacao,
        on_delete=models.CASCADE,
        related_name="analises",
    )
    documento = models.ForeignKey(
        Documento,
        on_delete=models.SET_NULL,
        related_name="analises",
        blank=True,
        null=True,
    )
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=StatusAnaliseChoices.choices,
        default=StatusAnaliseChoices.PENDENTE,
    )
    parecer = models.TextField(blank=True)
    prioridade = models.CharField(
        max_length=32,
        choices=PrioridadeAnaliseChoices.choices,
        default=PrioridadeAnaliseChoices.MEDIA,
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="analises_responsaveis",
        blank=True,
        null=True,
    )
    data_analise = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-data_analise",)
        verbose_name = "Analise"
        verbose_name_plural = "Analises"

    def __str__(self):
        return f"{self.titulo} - {self.licitacao.numero}"


class AnaliseExecucaoIA(BaseModel):
    analise = models.ForeignKey(
        Analise,
        on_delete=models.CASCADE,
        related_name="execucoes_ia",
    )
    tipo_tarefa = models.CharField(
        max_length=32,
        choices=TipoTarefaExecucaoIAChoices.choices,
    )
    status = models.CharField(
        max_length=32,
        choices=StatusExecucaoIAChoices.choices,
        default=StatusExecucaoIAChoices.PENDENTE,
    )
    versao = models.PositiveIntegerField(default=1)
    payload_entrada = models.JSONField(default=dict, blank=True)
    resultado_payload = models.JSONField(default=dict, blank=True)
    resultado_bruto = models.TextField(blank=True)
    mensagem_erro = models.TextField(blank=True)
    erro_detalhe_interno = models.TextField(blank=True)
    solicitada_em = models.DateTimeField(default=timezone.now)
    iniciada_em = models.DateTimeField(blank=True, null=True)
    concluida_em = models.DateTimeField(blank=True, null=True)
    identificador_task = models.CharField(max_length=255, blank=True)
    modelo_utilizado = models.CharField(max_length=128, blank=True)
    response_id = models.CharField(max_length=255, blank=True)
    tentativas = models.PositiveSmallIntegerField(default=0)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="execucoes_ia_criadas",
        blank=True,
        null=True,
    )
    reprocessamento_de = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="reprocessamentos",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-solicitada_em", "-versao", "-created_at")
        verbose_name = "Execucao de IA"
        verbose_name_plural = "Execucoes de IA"
        constraints = [
            models.UniqueConstraint(
                fields=("analise", "tipo_tarefa"),
                condition=Q(
                    deleted_at__isnull=True,
                    status__in=[
                        StatusExecucaoIAChoices.PENDENTE,
                        StatusExecucaoIAChoices.EM_PROCESSAMENTO,
                    ],
                ),
                name="uniq_execucao_ia_ativa_por_analise_e_tipo",
            ),
            models.UniqueConstraint(
                fields=("analise", "tipo_tarefa", "versao"),
                condition=Q(deleted_at__isnull=True),
                name="uniq_execucao_ia_versao_por_analise_e_tipo",
            ),
        ]
        indexes = [
            models.Index(fields=("analise", "tipo_tarefa", "versao")),
            models.Index(fields=("analise", "tipo_tarefa", "status")),
            models.Index(fields=("tipo_tarefa", "solicitada_em")),
            models.Index(fields=("identificador_task",)),
        ]

    def __str__(self):
        return (
            f"Analise {self.analise_id} - {self.get_tipo_tarefa_display()} "
            f"v{self.versao} - {self.get_status_display()}"
        )
