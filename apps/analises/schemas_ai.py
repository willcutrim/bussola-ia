from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .choices import PrioridadeAnaliseChoices, StatusAnaliseChoices


PrioridadeLiteral = Literal[
    PrioridadeAnaliseChoices.BAIXA,
    PrioridadeAnaliseChoices.MEDIA,
    PrioridadeAnaliseChoices.ALTA,
    PrioridadeAnaliseChoices.CRITICA,
]

StatusLiteral = Literal[
    StatusAnaliseChoices.PENDENTE,
    StatusAnaliseChoices.EM_ANDAMENTO,
    StatusAnaliseChoices.CONCLUIDA,
    StatusAnaliseChoices.REJEITADA,
]

ConfiancaLiteral = Literal["alta", "media", "baixa"]
ClassificacaoLiteral = Literal["fato", "inferencia", "lacuna"]
ChecklistCategoriaLiteral = Literal["documental", "tecnica", "juridica", "operacional"]
ChecklistStatusLiteral = Literal["atendido", "pendente", "nao_identificado"]


class AnaliseAIBaseSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class CampoExtraido(AnaliseAIBaseSchema):
    valor: Any = None
    fonte: str | None = None
    confianca: ConfiancaLiteral
    classificacao: ClassificacaoLiteral = "fato"


class ChecklistItem(AnaliseAIBaseSchema):
    titulo: str
    categoria: ChecklistCategoriaLiteral
    status: ChecklistStatusLiteral
    justificativa: str


class DocumentSummaryResponse(AnaliseAIBaseSchema):
    resumo_executivo: str
    fatos: list[str] = Field(default_factory=list)
    inferencias: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)


class DocumentExtractionResponse(AnaliseAIBaseSchema):
    campos_extraidos: dict[str, CampoExtraido] = Field(default_factory=dict)
    fatos: list[str] = Field(default_factory=list)
    inferencias: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)


class TechnicalAnalysisResponse(AnaliseAIBaseSchema):
    parecer_tecnico: str
    fatos: list[str] = Field(default_factory=list)
    inferencias: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    recomendacoes: list[str] = Field(default_factory=list)
    prioridade_sugerida: PrioridadeLiteral
    status_sugerido: StatusLiteral


class ComparisonResponse(AnaliseAIBaseSchema):
    aderencias: list[str] = Field(default_factory=list)
    divergencias: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    fatos: list[str] = Field(default_factory=list)
    inferencias: list[str] = Field(default_factory=list)
    recomendacao: str


class ChecklistResponse(AnaliseAIBaseSchema):
    resumo: str
    fatos: list[str] = Field(default_factory=list)
    inferencias: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    itens: list[ChecklistItem] = Field(default_factory=list)


class PriorityClassificationResponse(AnaliseAIBaseSchema):
    prioridade_sugerida: PrioridadeLiteral
    status_sugerido: StatusLiteral
    justificativa: str
    fatos: list[str] = Field(default_factory=list)
    inferencias: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)


__all__ = [
    "CampoExtraido",
    "ChecklistItem",
    "ChecklistResponse",
    "ComparisonResponse",
    "DocumentExtractionResponse",
    "DocumentSummaryResponse",
    "PriorityClassificationResponse",
    "TechnicalAnalysisResponse",
]
