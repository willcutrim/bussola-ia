from django.db import models


class TipoDocumentoChoices(models.TextChoices):
    EDITAL = "edital", "Edital"
    PROPOSTA = "proposta", "Proposta"
    HABILITACAO = "habilitacao", "Habilitacao"
    CONTRATO = "contrato", "Contrato"
    OUTROS = "outros", "Outros"


class StatusDocumentoChoices(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    ENVIADO = "enviado", "Enviado"
    VALIDADO = "validado", "Validado"
    REJEITADO = "rejeitado", "Rejeitado"
