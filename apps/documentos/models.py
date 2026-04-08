from django.db import models

from apps.core.models import BaseModel
from apps.licitacoes.models import Licitacao

from .choices import StatusDocumentoChoices, TipoDocumentoChoices


class Documento(BaseModel):
    licitacao = models.ForeignKey(
        Licitacao,
        on_delete=models.CASCADE,
        related_name="documentos",
    )
    nome = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to="documentos/licitacoes/%Y/%m/")
    tipo = models.CharField(
        max_length=32,
        choices=TipoDocumentoChoices.choices,
        default=TipoDocumentoChoices.OUTROS,
    )
    status = models.CharField(
        max_length=32,
        choices=StatusDocumentoChoices.choices,
        default=StatusDocumentoChoices.PENDENTE,
    )
    data_upload = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ("-data_upload",)
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self):
        return f"{self.nome} - {self.licitacao.numero}"
