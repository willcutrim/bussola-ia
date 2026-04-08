from django.db import models


class ModalidadeChoices(models.TextChoices):
    PREGAO = "pregao", "Pregao"
    CONCORRENCIA = "concorrencia", "Concorrencia"
    DISPENSA = "dispensa", "Dispensa"
    INEXIGIBILIDADE = "inexigibilidade", "Inexigibilidade"
    TOMADA_DE_PRECOS = "tomada_de_precos", "Tomada de precos"
    OUTROS = "outros", "Outros"


class SituacaoChoices(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    EM_ANALISE = "em_analise", "Em analise"
    EM_ANDAMENTO = "em_andamento", "Em andamento"
    ENCERRADA = "encerrada", "Encerrada"
    CANCELADA = "cancelada", "Cancelada"
