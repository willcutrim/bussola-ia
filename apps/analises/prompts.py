from __future__ import annotations

"""Contrato de prompts da camada de IA do app ``analises``.

Este modulo concentra apenas o contrato textual do dominio:

- SYSTEM prompt central
- formatos de saida por tarefa
- builders de prompt reutilizaveis

Regras estaveis:

- nao acoplar chamada OpenAI aqui
- nao persistir resultado aqui
- manter distincao entre fato, inferencia e lacuna quando aplicavel
- priorizar JSON estruturado nas tarefas com persistencia, classificacao ou reaproveitamento interno
"""

from .builders import (
    build_prompt_payload,
    render_context_section,
    render_text_section,
    serialize_for_prompt,
)
from .constants import AnaliseAITask


DOMAIN_SYSTEM_PROMPT = """
Voce atua como analista tecnico do dominio de licitacoes, documentos e conformidade no sistema Bussola.

Regras obrigatorias:
1. Nao invente fatos, campos, clausulas, prazos, numeros, classificacoes ou conclusoes que nao estejam sustentados pelo contexto recebido.
2. Sempre diferencie claramente:
   - fato: informacao explicitamente presente no contexto
   - inferencia: conclusao plausivel derivada do contexto
   - lacuna: dado ausente, ambiguo, contraditorio ou nao comprovado
3. Quando nao houver evidencias suficientes, admita a lacuna e nao preencha com suposicao.
4. Em tarefas de classificacao, checklist, comparacao ou parecer, justifique o resultado com base nos fatos e inferencias listados.
5. Quando a saida pedida for JSON, responda apenas com JSON valido e aderente ao formato solicitado, sem markdown adicional.
6. Escreva em portugues do Brasil, com linguagem objetiva, tecnica, auditavel e reutilizavel para operacao interna.
""".strip()


COMMON_GUARDRAILS = """
- Nao usar conhecimento externo para complementar dados do documento ou da licitacao.
- Se um campo solicitado nao estiver no contexto, retornar valor nulo ou registrar como lacuna, conforme o formato.
- Manter consistencia terminologica com licitacoes, documentos e analises.
""".strip()


DOCUMENT_SUMMARY_OUTPUT = """
Responder em JSON com a estrutura:
{
  "resumo_executivo": "string",
  "fatos": ["string"],
  "inferencias": ["string"],
  "lacunas": ["string"]
}
""".strip()


EXTRACTION_OUTPUT = """
Responder em JSON com a estrutura:
{
  "campos_extraidos": {
    "nome_do_campo": {
      "valor": "string | number | boolean | null",
      "fonte": "string | null",
      "confianca": "alta | media | baixa",
      "classificacao": "fato | inferencia | lacuna"
    }
  },
  "fatos": ["string"],
  "inferencias": ["string"],
  "lacunas": ["string"]
}
""".strip()


ANALYSIS_OUTPUT = """
Responder em JSON com a estrutura:
{
  "parecer_tecnico": "string",
  "fatos": ["string"],
  "inferencias": ["string"],
  "lacunas": ["string"],
  "recomendacoes": ["string"],
  "prioridade_sugerida": "baixa | media | alta | critica",
  "status_sugerido": "pendente | em_andamento | concluida | rejeitada"
}
""".strip()


COMPARISON_OUTPUT = """
Responder em JSON com a estrutura:
{
  "aderencias": ["string"],
  "divergencias": ["string"],
  "lacunas": ["string"],
  "fatos": ["string"],
  "inferencias": ["string"],
  "recomendacao": "string"
}
""".strip()


CHECKLIST_OUTPUT = """
Responder em JSON com a estrutura:
{
  "resumo": "string",
  "fatos": ["string"],
  "inferencias": ["string"],
  "lacunas": ["string"],
  "itens": [
    {
      "titulo": "string",
      "categoria": "documental | tecnica | juridica | operacional",
      "status": "atendido | pendente | nao_identificado",
      "justificativa": "string"
    }
  ]
}
""".strip()


CLASSIFICATION_OUTPUT = """
Responder em JSON com a estrutura:
{
  "prioridade_sugerida": "baixa | media | alta | critica",
  "status_sugerido": "pendente | em_andamento | concluida | rejeitada",
  "justificativa": "string",
  "fatos": ["string"],
  "inferencias": ["string"],
  "lacunas": ["string"]
}
""".strip()


def build_document_summary_prompt(
    *,
    texto_documento: str,
    documento_contexto: dict | None = None,
    licitacao_contexto: dict | None = None,
):
    return build_prompt_payload(
        task=AnaliseAITask.DOCUMENT_SUMMARY,
        system_prompt=DOMAIN_SYSTEM_PROMPT,
        sections=[
            ("Tarefa", "Gerar um resumo executivo fiel do documento, destacando fatos, inferencias e lacunas sem inventar informacoes."),
            ("Guardrails", COMMON_GUARDRAILS),
            ("Formato de saida", DOCUMENT_SUMMARY_OUTPUT),
            render_context_section("Contexto do documento", documento_contexto),
            render_context_section("Contexto da licitacao", licitacao_contexto),
            render_text_section("Texto do documento", texto_documento),
        ],
        metadata={"domain": "licitacoes", "kind": "summary"},
    )


def build_extraction_prompt(
    *,
    texto_documento: str,
    campos_alvo: list[str] | tuple[str, ...] | None = None,
    documento_contexto: dict | None = None,
    licitacao_contexto: dict | None = None,
):
    campos_texto = (
        serialize_for_prompt(list(campos_alvo))
        if campos_alvo
        else "Extrair os campos mais relevantes para analise documental, licitatoria e operacional."
    )
    return build_prompt_payload(
        task=AnaliseAITask.DOCUMENT_EXTRACTION,
        system_prompt=DOMAIN_SYSTEM_PROMPT,
        sections=[
            ("Tarefa", "Extrair dados estruturados do documento para persistencia e reaproveitamento interno."),
            ("Guardrails", COMMON_GUARDRAILS),
            ("Campos alvo", campos_texto),
            ("Formato de saida", EXTRACTION_OUTPUT),
            render_context_section("Contexto do documento", documento_contexto),
            render_context_section("Contexto da licitacao", licitacao_contexto),
            render_text_section("Texto do documento", texto_documento),
        ],
        metadata={"domain": "licitacoes", "kind": "extraction"},
    )


def build_analysis_prompt(
    *,
    texto_documento: str,
    documento_contexto: dict | None = None,
    licitacao_contexto: dict | None = None,
    analise_contexto: dict | None = None,
):
    return build_prompt_payload(
        task=AnaliseAITask.TECHNICAL_ANALYSIS,
        system_prompt=DOMAIN_SYSTEM_PROMPT,
        sections=[
            ("Tarefa", "Gerar parecer tecnico rastreavel sobre aderencia, riscos, pontos criticos e proxima acao recomendada."),
            ("Guardrails", COMMON_GUARDRAILS),
            ("Formato de saida", ANALYSIS_OUTPUT),
            render_context_section("Contexto do documento", documento_contexto),
            render_context_section("Contexto da licitacao", licitacao_contexto),
            render_context_section("Contexto da analise existente", analise_contexto),
            render_text_section("Texto do documento", texto_documento),
        ],
        metadata={"domain": "licitacoes", "kind": "technical_analysis"},
    )


def build_comparison_prompt(
    *,
    texto_documento: str,
    licitacao_contexto: dict,
    documento_contexto: dict | None = None,
):
    return build_prompt_payload(
        task=AnaliseAITask.DOCUMENT_COMPARISON,
        system_prompt=DOMAIN_SYSTEM_PROMPT,
        sections=[
            ("Tarefa", "Comparar o documento com o contexto da licitacao e identificar aderencias, divergencias, riscos e lacunas."),
            ("Guardrails", COMMON_GUARDRAILS),
            ("Formato de saida", COMPARISON_OUTPUT),
            render_context_section("Contexto do documento", documento_contexto),
            render_context_section("Contexto da licitacao", licitacao_contexto),
            render_text_section("Texto do documento", texto_documento),
        ],
        metadata={"domain": "licitacoes", "kind": "comparison"},
    )


def build_checklist_prompt(
    *,
    texto_documento: str | None = None,
    licitacao_contexto: dict | None = None,
    comparison_contexto: dict | None = None,
    documento_contexto: dict | None = None,
):
    sections = [
        ("Tarefa", "Gerar checklist acionavel para revisao documental, tecnica, juridica e operacional."),
        ("Guardrails", COMMON_GUARDRAILS),
        ("Formato de saida", CHECKLIST_OUTPUT),
        render_context_section("Contexto do documento", documento_contexto),
        render_context_section("Contexto da licitacao", licitacao_contexto),
        render_context_section("Contexto de comparacao", comparison_contexto),
    ]
    if texto_documento:
        sections.append(render_text_section("Texto do documento", texto_documento))

    return build_prompt_payload(
        task=AnaliseAITask.CHECKLIST_GENERATION,
        system_prompt=DOMAIN_SYSTEM_PROMPT,
        sections=sections,
        metadata={"domain": "licitacoes", "kind": "checklist"},
    )


def build_priority_classification_prompt(
    *,
    texto_documento: str,
    licitacao_contexto: dict | None = None,
    documento_contexto: dict | None = None,
    analise_contexto: dict | None = None,
):
    return build_prompt_payload(
        task=AnaliseAITask.PRIORITY_CLASSIFICATION,
        system_prompt=DOMAIN_SYSTEM_PROMPT,
        sections=[
            ("Tarefa", "Classificar prioridade e status sugerido da analise com justificativa rastreavel e sem inventar fatos."),
            ("Guardrails", COMMON_GUARDRAILS),
            ("Formato de saida", CLASSIFICATION_OUTPUT),
            render_context_section("Contexto do documento", documento_contexto),
            render_context_section("Contexto da licitacao", licitacao_contexto),
            render_context_section("Contexto da analise existente", analise_contexto),
            render_text_section("Texto do documento", texto_documento),
        ],
        metadata={"domain": "licitacoes", "kind": "classification"},
    )


__all__ = [
    "DOMAIN_SYSTEM_PROMPT",
    "build_analysis_prompt",
    "build_checklist_prompt",
    "build_comparison_prompt",
    "build_document_summary_prompt",
    "build_extraction_prompt",
    "build_priority_classification_prompt",
]
