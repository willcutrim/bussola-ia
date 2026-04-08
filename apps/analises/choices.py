from django.db import models


class StatusAnaliseChoices(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    EM_ANDAMENTO = "em_andamento", "Em andamento"
    CONCLUIDA = "concluida", "Concluida"
    REJEITADA = "rejeitada", "Rejeitada"


class PrioridadeAnaliseChoices(models.TextChoices):
    BAIXA = "baixa", "Baixa"
    MEDIA = "media", "Media"
    ALTA = "alta", "Alta"
    CRITICA = "critica", "Critica"
