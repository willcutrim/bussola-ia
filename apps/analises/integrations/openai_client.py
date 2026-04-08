from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from pydantic import BaseModel

from apps.analises.builders import PromptPayload
from apps.analises.constants import (
    OPENAI_APP_NAME,
    OPENAI_DEFAULT_STORE,
    OPENAI_DEFAULT_TIMEOUT_SECONDS,
    AnaliseAITaskConfig,
)


@dataclass(frozen=True)
class OpenAIClientConfig:
    api_key: str | None
    organization: str | None = None
    project: str | None = None
    timeout_seconds: float = OPENAI_DEFAULT_TIMEOUT_SECONDS
    store: bool = OPENAI_DEFAULT_STORE

    @classmethod
    def from_env(cls) -> "OpenAIClientConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            organization=os.getenv("OPENAI_ORG_ID"),
            project=os.getenv("OPENAI_PROJECT_ID"),
        )


@dataclass(frozen=True)
class AIResponsePayload:
    task: str
    model: str
    text: str
    parsed: BaseModel | dict[str, Any] | list[Any] | None
    response_id: str | None = None


class AnaliseOpenAIClient:
    def __init__(
        self,
        *,
        config: OpenAIClientConfig | None = None,
        client: Any | None = None,
    ) -> None:
        self.config = config or OpenAIClientConfig.from_env()
        self._client = client

    def gerar_resposta(
        self,
        prompt: PromptPayload,
        *,
        task_config: AnaliseAITaskConfig,
        model: str | None = None,
    ) -> AIResponsePayload:
        client = self._get_client()
        resolved_model = model or task_config.model
        response = client.responses.parse(
            model=resolved_model,
            instructions=prompt.system_prompt,
            input=prompt.user_prompt,
            max_output_tokens=task_config.max_output_tokens,
            store=self.config.store,
            reasoning={"effort": task_config.reasoning_effort}
            if task_config.reasoning_effort
            else None,
            text_format=task_config.response_schema,
            metadata=self._build_metadata(prompt),
            verbosity=task_config.verbosity,
        )

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("A resposta estruturada da IA nao retornou payload parseavel.")

        return AIResponsePayload(
            task=prompt.task,
            model=resolved_model,
            text=getattr(response, "output_text", "").strip(),
            parsed=parsed,
            response_id=getattr(response, "id", None),
        )

    def _get_client(self):
        if self._client is not None:
            return self._client

        if not self.config.api_key:
            raise ImproperlyConfigured(
                "OPENAI_API_KEY nao configurada. Defina a chave para usar a camada de IA."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImproperlyConfigured(
                "A biblioteca openai nao esta instalada. Adicione a dependencia antes de usar a camada de IA."
            ) from exc

        kwargs: dict[str, Any] = {
            "api_key": self.config.api_key,
            "timeout": self.config.timeout_seconds,
        }
        if self.config.organization:
            kwargs["organization"] = self.config.organization
        if self.config.project:
            kwargs["project"] = self.config.project

        self._client = OpenAI(**kwargs)
        return self._client

    def _build_metadata(self, prompt: PromptPayload) -> dict[str, str]:
        metadata = {
            "app": OPENAI_APP_NAME,
            "task": prompt.task,
        }
        for key, value in (prompt.metadata or {}).items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                metadata[str(key)] = str(value)
        return metadata


__all__ = [
    "AIResponsePayload",
    "AnaliseOpenAIClient",
    "OpenAIClientConfig",
]
