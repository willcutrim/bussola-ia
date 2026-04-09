from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from apps.documentos.choices import TipoDocumentoChoices
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.constants import PNCP_DOCUMENTO_URL_PREFIX, PNCP_OBSERVACAO_PREFIX
from apps.licitacoes.dtos import ArquivoPNCPDTO, ContratacaoPNCPDTO


def mapear_contratacao_pncp_payload(payload: dict) -> ContratacaoPNCPDTO:
    arquivos = [
        mapear_arquivo_pncp_payload(item)
        for item in payload.get("arquivos") or []
        if isinstance(item, dict)
    ]

    return ContratacaoPNCPDTO(
        numero_controle_pncp=_as_optional_str(payload.get("numeroControlePNCP")),
        numero_compra=_as_optional_str(payload.get("numeroCompra")) or "SEM-NUMERO",
        ano_compra=_as_int(payload.get("anoCompra")),
        sequencial_compra=_as_optional_str(payload.get("sequencialCompra")),
        processo=_as_optional_str(payload.get("processo")),
        orgao_nome=_extract_orgao_nome(payload),
        orgao_cnpj=_extract_orgao_cnpj(payload),
        modalidade_nome=_as_optional_str(payload.get("modalidadeNome")),
        situacao_nome=_as_optional_str(payload.get("situacaoCompraNome")),
        objeto_compra=_as_optional_str(payload.get("objetoCompra")) or "Objeto nao informado",
        data_publicacao=_as_date(payload.get("dataPublicacaoPncp")),
        data_abertura_proposta=_as_date(payload.get("dataAberturaProposta")),
        valor_total_estimado=_as_decimal(payload.get("valorTotalEstimado")),
        link_sistema_origem=_as_optional_str(payload.get("linkSistemaOrigem")),
        arquivos=arquivos,
    )


def mapear_arquivo_pncp_payload(payload: dict) -> ArquivoPNCPDTO:
    titulo = _as_optional_str(payload.get("titulo")) or "Arquivo PNCP"
    return ArquivoPNCPDTO(
        titulo=titulo,
        url=_as_optional_str(payload.get("url")) or "",
        tipo=_as_optional_str(payload.get("tipoDocumentoNome")),
    )


def mapear_modalidade_pncp(modalidade_nome: str | None) -> str:
    normalized = _normalize_text(modalidade_nome)
    mapping = {
        "pregao": ModalidadeChoices.PREGAO,
        "concorrencia": ModalidadeChoices.CONCORRENCIA,
        "dispensa": ModalidadeChoices.DISPENSA,
        "inexigibilidade": ModalidadeChoices.INEXIGIBILIDADE,
        "tomada de precos": ModalidadeChoices.TOMADA_DE_PRECOS,
    }
    return mapping.get(normalized, ModalidadeChoices.OUTROS)


def mapear_situacao_pncp(situacao_nome: str | None) -> str:
    normalized = _normalize_text(situacao_nome)
    mapping = {
        "recebendo proposta": SituacaoChoices.EM_ANDAMENTO,
        "divulgada no pncp": SituacaoChoices.EM_ANALISE,
        "homologada": SituacaoChoices.ENCERRADA,
        "encerrada": SituacaoChoices.ENCERRADA,
        "revogada": SituacaoChoices.CANCELADA,
        "anulada": SituacaoChoices.CANCELADA,
        "cancelada": SituacaoChoices.CANCELADA,
    }
    return mapping.get(normalized, SituacaoChoices.EM_ANALISE)


def mapear_tipo_documento_pncp(tipo: str | None, titulo: str) -> str:
    normalized = _normalize_text(tipo or titulo)
    if "edital" in normalized:
        return TipoDocumentoChoices.EDITAL
    if "proposta" in normalized:
        return TipoDocumentoChoices.PROPOSTA
    if "habilit" in normalized:
        return TipoDocumentoChoices.HABILITACAO
    if "contrato" in normalized:
        return TipoDocumentoChoices.CONTRATO
    return TipoDocumentoChoices.OUTROS


def montar_observacao_importacao(dto: ContratacaoPNCPDTO, chave_idempotencia: str) -> str:
    partes = [
        PNCP_OBSERVACAO_PREFIX,
        f"chave={chave_idempotencia}",
    ]
    if dto.numero_controle_pncp:
        partes.append(f"numero_controle={dto.numero_controle_pncp}")
    if dto.processo:
        partes.append(f"processo={dto.processo}")
    return " | ".join(partes)


def montar_observacao_documento(url: str) -> str:
    return f"{PNCP_DOCUMENTO_URL_PREFIX}: {url}" if url else PNCP_DOCUMENTO_URL_PREFIX


def _extract_orgao_nome(payload: dict) -> str:
    orgao = payload.get("orgaoEntidade")
    if isinstance(orgao, dict):
        nome = _as_optional_str(orgao.get("razaoSocial"))
        if nome:
            return nome
    return _as_optional_str(payload.get("orgaoNome")) or "Orgao nao informado"


def _extract_orgao_cnpj(payload: dict) -> str | None:
    orgao = payload.get("orgaoEntidade")
    if isinstance(orgao, dict):
        return _as_optional_str(orgao.get("cnpj"))
    return _as_optional_str(payload.get("orgaoCnpj"))


def _as_optional_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _as_date(value) -> date | None:
    text = _as_optional_str(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()
