from __future__ import annotations

from datetime import timedelta

from django.tasks import DEFAULT_TASK_BACKEND_ALIAS
from django.utils import timezone


TASK_BACKEND_ALIAS = DEFAULT_TASK_BACKEND_ALIAS
TASK_BACKEND_DEFAULT_PATH = "django.tasks.backends.immediate.ImmediateBackend"

ANALISES_AI_QUEUE_NAME = "analises-ai"
ANALISES_AI_MAX_TENTATIVAS = 3
ANALISES_AI_RETRY_DELAYS_SECONDS = (30, 120)
ANALISES_AI_POLL_TRIGGER = "every 3s"


def calcular_proximo_retry(tentativa_atual: int):
    if tentativa_atual <= 0:
        return None

    retry_index = tentativa_atual - 1
    if retry_index >= len(ANALISES_AI_RETRY_DELAYS_SECONDS):
        return None

    return timezone.now() + timedelta(
        seconds=ANALISES_AI_RETRY_DELAYS_SECONDS[retry_index]
    )
