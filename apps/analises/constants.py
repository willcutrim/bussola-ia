from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .choices import TipoTarefaExecucaoIAChoices
from .schemas_ai import (
    ChecklistResponse,
    ComparisonResponse,
    DocumentExtractionResponse,
    DocumentSummaryResponse,
    PriorityClassificationResponse,
    TechnicalAnalysisResponse,
)


ReasoningEffort = Literal["low", "medium", "high"]
ResponseVerbosity = Literal["low", "medium", "high"]


class AnaliseAITask:
    DOCUMENT_SUMMARY = "document_summary"
    DOCUMENT_EXTRACTION = "document_extraction"
    TECHNICAL_ANALYSIS = "technical_analysis"
    DOCUMENT_COMPARISON = "document_comparison"
    CHECKLIST_GENERATION = "checklist_generation"
    PRIORITY_CLASSIFICATION = "priority_classification"


MODEL_GPT_5_4 = "gpt-5.4"
MODEL_GPT_5_4_MINI = "gpt-5.4-mini"

OPENAI_APP_NAME = "analises"
OPENAI_DEFAULT_TIMEOUT_SECONDS = 60.0
OPENAI_DEFAULT_STORE = False


@dataclass(frozen=True)
class AnaliseAITaskConfig:
    task: str
    model: str
    response_schema: type
    reasoning_effort: ReasoningEffort | None = None
    max_output_tokens: int = 1800
    verbosity: ResponseVerbosity | None = "medium"


TASK_CONFIGS = {
    AnaliseAITask.DOCUMENT_SUMMARY: AnaliseAITaskConfig(
        task=AnaliseAITask.DOCUMENT_SUMMARY,
        model=MODEL_GPT_5_4_MINI,
        response_schema=DocumentSummaryResponse,
        reasoning_effort="medium",
        max_output_tokens=1200,
        verbosity="medium",
    ),
    AnaliseAITask.DOCUMENT_EXTRACTION: AnaliseAITaskConfig(
        task=AnaliseAITask.DOCUMENT_EXTRACTION,
        model=MODEL_GPT_5_4_MINI,
        response_schema=DocumentExtractionResponse,
        reasoning_effort="medium",
        max_output_tokens=1800,
        verbosity="low",
    ),
    AnaliseAITask.TECHNICAL_ANALYSIS: AnaliseAITaskConfig(
        task=AnaliseAITask.TECHNICAL_ANALYSIS,
        model=MODEL_GPT_5_4,
        response_schema=TechnicalAnalysisResponse,
        reasoning_effort="high",
        max_output_tokens=2200,
        verbosity="high",
    ),
    AnaliseAITask.DOCUMENT_COMPARISON: AnaliseAITaskConfig(
        task=AnaliseAITask.DOCUMENT_COMPARISON,
        model=MODEL_GPT_5_4,
        response_schema=ComparisonResponse,
        reasoning_effort="high",
        max_output_tokens=2200,
        verbosity="high",
    ),
    AnaliseAITask.CHECKLIST_GENERATION: AnaliseAITaskConfig(
        task=AnaliseAITask.CHECKLIST_GENERATION,
        model=MODEL_GPT_5_4,
        response_schema=ChecklistResponse,
        reasoning_effort="high",
        max_output_tokens=2200,
        verbosity="medium",
    ),
    AnaliseAITask.PRIORITY_CLASSIFICATION: AnaliseAITaskConfig(
        task=AnaliseAITask.PRIORITY_CLASSIFICATION,
        model=MODEL_GPT_5_4,
        response_schema=PriorityClassificationResponse,
        reasoning_effort="high",
        max_output_tokens=1400,
        verbosity="medium",
    ),
}

TIPO_TAREFA_PARA_ANALISE_AI_TASK = {
    TipoTarefaExecucaoIAChoices.RESUMO: AnaliseAITask.DOCUMENT_SUMMARY,
    TipoTarefaExecucaoIAChoices.EXTRACAO: AnaliseAITask.DOCUMENT_EXTRACTION,
    TipoTarefaExecucaoIAChoices.PARECER: AnaliseAITask.TECHNICAL_ANALYSIS,
    TipoTarefaExecucaoIAChoices.COMPARACAO: AnaliseAITask.DOCUMENT_COMPARISON,
    TipoTarefaExecucaoIAChoices.CHECKLIST: AnaliseAITask.CHECKLIST_GENERATION,
}


def get_task_config(task: str) -> AnaliseAITaskConfig:
    try:
        return TASK_CONFIGS[task]
    except KeyError as exc:
        raise ValueError(f"Tarefa de IA nao suportada: {task}.") from exc


__all__ = [
    "AnaliseAITask",
    "AnaliseAITaskConfig",
    "MODEL_GPT_5_4",
    "MODEL_GPT_5_4_MINI",
    "OPENAI_APP_NAME",
    "OPENAI_DEFAULT_STORE",
    "OPENAI_DEFAULT_TIMEOUT_SECONDS",
    "TASK_CONFIGS",
    "TIPO_TAREFA_PARA_ANALISE_AI_TASK",
    "get_task_config",
]
