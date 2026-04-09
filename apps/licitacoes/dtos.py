from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ArquivoPNCPDTO:
    titulo: str
    url: str
    tipo: str | None = None


@dataclass(frozen=True)
class ContratacaoPNCPDTO:
    numero_controle_pncp: str | None
    numero_compra: str
    ano_compra: int | None
    sequencial_compra: str | None
    processo: str | None
    orgao_nome: str
    orgao_cnpj: str | None
    modalidade_nome: str | None
    situacao_nome: str | None
    objeto_compra: str
    data_publicacao: date | None
    data_abertura_proposta: date | None
    valor_total_estimado: Decimal | None
    link_sistema_origem: str | None
    arquivos: list[ArquivoPNCPDTO] = field(default_factory=list)
