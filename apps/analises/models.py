from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.documentos.models import Documento
from apps.licitacoes.models import Licitacao

from .choices import PrioridadeAnaliseChoices, StatusAnaliseChoices


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
