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


class StatusExecucaoIAChoices(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    EM_PROCESSAMENTO = "em_processamento", "Em processamento"
    CONCLUIDO = "concluido", "Concluido"
    FALHOU = "falhou", "Falhou"


class TipoTarefaExecucaoIAChoices(models.TextChoices):
    RESUMO = "resumo", "Resumo"
    EXTRACAO = "extracao", "Extracao"
    PARECER = "parecer", "Parecer"
    COMPARACAO = "comparacao", "Comparacao"
    CHECKLIST = "checklist", "Checklist"
