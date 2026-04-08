from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Analise
    from apps.documentos.models import Documento
    from apps.licitacoes.models import Licitacao


@dataclass(frozen=True)
class PromptPayload:
    task: str
    system_prompt: str
    user_prompt: str
    expects_json: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


def build_prompt_payload(
    *,
    task: str,
    system_prompt: str,
    sections: list[tuple[str, str | None]],
    expects_json: bool = True,
    metadata: dict[str, Any] | None = None,
) -> PromptPayload:
    rendered_sections: list[str] = []
    for title, content in sections:
        cleaned_content = _clean_text(content)
        if not cleaned_content:
            continue
        rendered_sections.append(f"## {title}\n{cleaned_content}")

    return PromptPayload(
        task=task,
        system_prompt=system_prompt.strip(),
        user_prompt="\n\n".join(rendered_sections).strip(),
        expects_json=expects_json,
        metadata=metadata or {},
    )


def build_documento_contexto(documento: Documento | None) -> dict[str, Any] | None:
    if documento is None:
        return None

    return {
        "id": documento.pk,
        "nome": documento.nome,
        "tipo": documento.tipo,
        "status": documento.status,
        "observacoes": documento.observacoes,
        "licitacao_id": documento.licitacao_id,
    }


def build_licitacao_contexto(licitacao: Licitacao | None) -> dict[str, Any] | None:
    if licitacao is None:
        return None

    return {
        "id": licitacao.pk,
        "numero": licitacao.numero,
        "objeto": licitacao.objeto,
        "orgao": licitacao.orgao,
        "modalidade": licitacao.modalidade,
        "situacao": licitacao.situacao,
        "data_abertura": licitacao.data_abertura.isoformat() if licitacao.data_abertura else None,
        "valor_estimado": _serialize_scalar(licitacao.valor_estimado),
        "empresa": str(licitacao.empresa) if licitacao.empresa_id else None,
        "observacoes": licitacao.observacoes,
    }


def build_analise_contexto(analise: Analise | None) -> dict[str, Any] | None:
    if analise is None:
        return None

    return {
        "id": analise.pk,
        "titulo": analise.titulo,
        "descricao": analise.descricao,
        "status_atual": analise.status,
        "prioridade_atual": analise.prioridade,
        "parecer_atual": analise.parecer,
        "responsavel_id": analise.responsavel_id,
    }


def render_context_section(title: str, payload: dict[str, Any] | None) -> tuple[str, str | None]:
    if not payload:
        return title, None
    return title, serialize_for_prompt(payload)


def render_text_section(title: str, value: str | None) -> tuple[str, str | None]:
    return title, _clean_text(value)


def serialize_for_prompt(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, indent=2, default=_serialize_scalar)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _serialize_scalar(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


__all__ = [
    "PromptPayload",
    "build_analise_contexto",
    "build_documento_contexto",
    "build_licitacao_contexto",
    "build_prompt_payload",
    "render_context_section",
    "render_text_section",
    "serialize_for_prompt",
]
