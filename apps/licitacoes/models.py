from django.db import models

from apps.core.models import BaseModel
from apps.empresas.models import Empresa

from .choices import ModalidadeChoices, SituacaoChoices


class Licitacao(BaseModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,
        related_name="licitacoes",
        blank=True,
        null=True,
    )
    numero = models.CharField(max_length=120)
    objeto = models.TextField()
    orgao = models.CharField(max_length=255)
    modalidade = models.CharField(
        max_length=32,
        choices=ModalidadeChoices.choices,
        default=ModalidadeChoices.OUTROS,
    )
    situacao = models.CharField(
        max_length=32,
        choices=SituacaoChoices.choices,
        default=SituacaoChoices.RASCUNHO,
    )
    data_abertura = models.DateField(blank=True, null=True)
    valor_estimado = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
    )
    link_externo = models.URLField(blank=True)
    observacoes = models.TextField(blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ("-data_abertura", "numero")
        verbose_name = "Licitacao"
        verbose_name_plural = "Licitacoes"

    def __str__(self):
        return f"{self.numero} - {self.orgao}"
