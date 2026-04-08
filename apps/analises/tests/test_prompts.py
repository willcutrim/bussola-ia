from django.test import SimpleTestCase

from apps.analises.constants import AnaliseAITask
from apps.analises.prompts import (
    DOMAIN_SYSTEM_PROMPT,
    build_analysis_prompt,
    build_checklist_prompt,
    build_comparison_prompt,
    build_document_summary_prompt,
    build_extraction_prompt,
    build_priority_classification_prompt,
)


class AnalisePromptsTests(SimpleTestCase):
    def assert_prompt_contract(self, prompt, *, task, includes_json=True):
        self.assertEqual(prompt.task, task)
        self.assertEqual(prompt.system_prompt, DOMAIN_SYSTEM_PROMPT)
        self.assertNotEqual(prompt.user_prompt, "")
        self.assertIn("Nao invente fatos", prompt.system_prompt)
        self.assertIn("fato", prompt.system_prompt)
        self.assertIn("inferencia", prompt.system_prompt)
        self.assertIn("lacuna", prompt.system_prompt)
        self.assertIn("Formato de saida", prompt.user_prompt)
        if includes_json:
            self.assertIn("Responder em JSON", prompt.user_prompt)

    def test_build_document_summary_prompt_inclui_guardrails_e_contexto(self):
        prompt = build_document_summary_prompt(
            texto_documento="Conteudo do edital.",
            documento_contexto={"nome": "Edital"},
            licitacao_contexto={"numero": "PE-001/2026"},
        )

        self.assert_prompt_contract(
            prompt,
            task=AnaliseAITask.DOCUMENT_SUMMARY,
        )
        self.assertIn("resumo_executivo", prompt.user_prompt)
        self.assertIn("Contexto do documento", prompt.user_prompt)
        self.assertIn("PE-001/2026", prompt.user_prompt)

    def test_build_extraction_prompt_inclui_campos_alvo(self):
        prompt = build_extraction_prompt(
            texto_documento="Conteudo do edital.",
            campos_alvo=["prazo", "garantia"],
            documento_contexto={"nome": "Edital"},
        )

        self.assert_prompt_contract(
            prompt,
            task=AnaliseAITask.DOCUMENT_EXTRACTION,
        )
        self.assertIn("campos_extraidos", prompt.user_prompt)
        self.assertIn("prazo", prompt.user_prompt)
        self.assertIn("garantia", prompt.user_prompt)

    def test_build_analysis_prompt_inclui_instrucao_de_rastreabilidade(self):
        prompt = build_analysis_prompt(
            texto_documento="Conteudo tecnico.",
            documento_contexto={"nome": "Edital"},
            licitacao_contexto={"numero": "PE-001/2026"},
            analise_contexto={"status_atual": "pendente"},
        )

        self.assert_prompt_contract(
            prompt,
            task=AnaliseAITask.TECHNICAL_ANALYSIS,
        )
        self.assertIn("parecer_tecnico", prompt.user_prompt)
        self.assertIn("recomendacoes", prompt.user_prompt)
        self.assertIn("prioridade_sugerida", prompt.user_prompt)

    def test_build_comparison_prompt_inclui_aderencias_e_divergencias(self):
        prompt = build_comparison_prompt(
            texto_documento="Documento comparado.",
            licitacao_contexto={"numero": "PE-001/2026"},
            documento_contexto={"nome": "Edital"},
        )

        self.assert_prompt_contract(
            prompt,
            task=AnaliseAITask.DOCUMENT_COMPARISON,
        )
        self.assertIn("aderencias", prompt.user_prompt)
        self.assertIn("divergencias", prompt.user_prompt)
        self.assertIn("recomendacao", prompt.user_prompt)

    def test_build_checklist_prompt_permanece_util_sem_texto_documento(self):
        prompt = build_checklist_prompt(
            licitacao_contexto={"numero": "PE-001/2026"},
            comparison_contexto={"divergencias": ["Prazo ausente"]},
            documento_contexto={"nome": "Checklist base"},
        )

        self.assert_prompt_contract(
            prompt,
            task=AnaliseAITask.CHECKLIST_GENERATION,
        )
        self.assertIn("itens", prompt.user_prompt)
        self.assertIn("Prazo ausente", prompt.user_prompt)

    def test_build_priority_classification_prompt_inclui_saida_classificatoria(self):
        prompt = build_priority_classification_prompt(
            texto_documento="Documento com risco alto.",
            licitacao_contexto={"numero": "PE-001/2026"},
            documento_contexto={"nome": "Edital"},
            analise_contexto={"status_atual": "pendente"},
        )

        self.assert_prompt_contract(
            prompt,
            task=AnaliseAITask.PRIORITY_CLASSIFICATION,
        )
        self.assertIn("status_sugerido", prompt.user_prompt)
        self.assertIn("justificativa", prompt.user_prompt)
