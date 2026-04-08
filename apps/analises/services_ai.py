from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from pydantic import BaseModel

from apps.analises.builders import (
    build_analise_contexto,
    build_documento_contexto,
    build_licitacao_contexto,
)
from apps.analises.constants import get_task_config
from apps.analises.integrations import AnaliseOpenAIClient
from apps.analises.models import Analise
from apps.analises.prompts import (
    build_analysis_prompt,
    build_checklist_prompt,
    build_comparison_prompt,
    build_document_summary_prompt,
    build_extraction_prompt,
    build_priority_classification_prompt,
)
from apps.analises.services import AnaliseService
from apps.documentos.models import Documento
from apps.licitacoes.models import Licitacao


class AnaliseAIService:
    def __init__(
        self,
        *,
        client: AnaliseOpenAIClient | None = None,
        analise_service: AnaliseService | None = None,
    ) -> None:
        self.client = client or AnaliseOpenAIClient()
        self.analise_service = analise_service or AnaliseService()

    def gerar_resumo_documento(
        self,
        *,
        texto_documento: str,
        documento: Documento | None = None,
        licitacao: Licitacao | None = None,
    ) -> dict[str, Any]:
        prompt = build_document_summary_prompt(
            texto_documento=self._require_text(texto_documento),
            documento_contexto=build_documento_contexto(documento),
            licitacao_contexto=build_licitacao_contexto(
                licitacao or getattr(documento, "licitacao", None)
            ),
        )
        return self._run_task(prompt)

    def extrair_dados_documento(
        self,
        *,
        texto_documento: str,
        documento: Documento | None = None,
        licitacao: Licitacao | None = None,
        campos_alvo: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        prompt = build_extraction_prompt(
            texto_documento=self._require_text(texto_documento),
            campos_alvo=campos_alvo,
            documento_contexto=build_documento_contexto(documento),
            licitacao_contexto=build_licitacao_contexto(
                licitacao or getattr(documento, "licitacao", None)
            ),
        )
        return self._run_task(prompt)

    def gerar_parecer_tecnico(
        self,
        *,
        texto_documento: str,
        licitacao: Licitacao,
        documento: Documento | None = None,
        analise: Analise | None = None,
        persistir: bool = False,
    ) -> dict[str, Any]:
        prompt = build_analysis_prompt(
            texto_documento=self._require_text(texto_documento),
            documento_contexto=build_documento_contexto(documento),
            licitacao_contexto=build_licitacao_contexto(licitacao),
            analise_contexto=build_analise_contexto(analise),
        )
        resultado = self._run_task(prompt)
        if persistir and analise is not None:
            self._persistir_resultado_analitico(analise, resultado)
        return resultado

    def comparar_documento_com_licitacao(
        self,
        *,
        texto_documento: str,
        licitacao: Licitacao,
        documento: Documento | None = None,
    ) -> dict[str, Any]:
        prompt = build_comparison_prompt(
            texto_documento=self._require_text(texto_documento),
            documento_contexto=build_documento_contexto(documento),
            licitacao_contexto=build_licitacao_contexto(licitacao),
        )
        return self._run_task(prompt)

    def gerar_checklist(
        self,
        *,
        texto_documento: str | None = None,
        licitacao: Licitacao | None = None,
        documento: Documento | None = None,
        contexto_comparacao: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prompt = build_checklist_prompt(
            texto_documento=texto_documento.strip()
            if isinstance(texto_documento, str)
            else None,
            documento_contexto=build_documento_contexto(documento),
            licitacao_contexto=build_licitacao_contexto(
                licitacao or getattr(documento, "licitacao", None)
            ),
            comparison_contexto=contexto_comparacao,
        )
        return self._run_task(prompt)

    def classificar_prioridade_status(
        self,
        *,
        texto_documento: str,
        licitacao: Licitacao | None = None,
        documento: Documento | None = None,
        analise: Analise | None = None,
        persistir: bool = False,
    ) -> dict[str, Any]:
        prompt = build_priority_classification_prompt(
            texto_documento=self._require_text(texto_documento),
            licitacao_contexto=build_licitacao_contexto(
                licitacao or getattr(documento, "licitacao", None)
            ),
            documento_contexto=build_documento_contexto(documento),
            analise_contexto=build_analise_contexto(analise),
        )
        resultado = self._run_task(prompt)
        if persistir and analise is not None:
            self._persistir_classificacao(analise, resultado)
        return resultado

    def _run_task(self, prompt) -> dict[str, Any]:
        task_config = get_task_config(prompt.task)
        response = self.client.gerar_resposta(prompt, task_config=task_config)
        return self._normalize_payload(response.parsed, task_config.response_schema)

    def _normalize_payload(
        self,
        payload: BaseModel | dict[str, Any] | list[Any] | None,
        schema: type[BaseModel],
    ) -> dict[str, Any]:
        if payload is None:
            raise ValidationError("A resposta da IA veio vazia.")

        if isinstance(payload, BaseModel):
            validated = payload
        else:
            try:
                validated = schema.model_validate(payload)
            except Exception as exc:
                raise ValidationError(
                    "A resposta da IA nao respeitou o contrato estruturado esperado."
                ) from exc

        return validated.model_dump(mode="json")

    def _persistir_resultado_analitico(
        self,
        analise: Analise,
        payload: dict[str, Any],
    ) -> Analise:
        return self.analise_service.atualizar(
            analise,
            self._build_update_payload(
                analise,
                parecer=payload["parecer_tecnico"],
                status=payload["status_sugerido"],
                prioridade=payload["prioridade_sugerida"],
            ),
        )

    def _persistir_classificacao(
        self,
        analise: Analise,
        payload: dict[str, Any],
    ) -> Analise:
        return self.analise_service.atualizar(
            analise,
            self._build_update_payload(
                analise,
                parecer=analise.parecer,
                status=payload["status_sugerido"],
                prioridade=payload["prioridade_sugerida"],
            ),
        )

    def _build_update_payload(
        self,
        analise: Analise,
        *,
        parecer: str,
        status: str,
        prioridade: str,
    ) -> dict[str, Any]:
        return {
            "titulo": analise.titulo,
            "descricao": analise.descricao,
            "documento": analise.documento,
            "licitacao": analise.licitacao,
            "responsavel": analise.responsavel,
            "parecer": parecer,
            "status": status,
            "prioridade": prioridade,
        }

    def _require_text(self, texto_documento: str) -> str:
        if not isinstance(texto_documento, str) or not texto_documento.strip():
            raise ValidationError(
                "O texto do documento e obrigatorio para executar a tarefa de IA."
            )
        return texto_documento.strip()


__all__ = ["AnaliseAIService"]
