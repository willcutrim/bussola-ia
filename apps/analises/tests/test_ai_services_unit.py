from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.analises.builders import PromptPayload
from apps.analises.constants import AnaliseAITask, get_task_config
from apps.analises.integrations import AIResponsePayload
from apps.analises.schemas_ai import (
    ChecklistResponse,
    ComparisonResponse,
    DocumentExtractionResponse,
    DocumentSummaryResponse,
    TechnicalAnalysisResponse,
)
from apps.analises.services_ai import AnaliseAIService


class AnaliseAIServiceUnitTests(SimpleTestCase):
    def setUp(self):
        self.client = Mock()
        self.analise_service = Mock()
        self.service = AnaliseAIService(
            client=self.client,
            analise_service=self.analise_service,
        )
        self.licitacao = SimpleNamespace(
            pk=1,
            numero="PE-001/2026",
            objeto="Contratacao de software",
            orgao="Prefeitura",
            modalidade="pregao",
            situacao="em_analise",
            data_abertura=None,
            valor_estimado=None,
            empresa_id=None,
            empresa=None,
            observacoes="",
        )
        self.documento = SimpleNamespace(
            pk=2,
            nome="Edital principal",
            tipo="edital",
            status="pendente",
            observacoes="",
            licitacao_id=1,
            licitacao=self.licitacao,
        )
        self.analise = SimpleNamespace(
            pk=9,
            titulo="Analise inicial",
            descricao="",
            documento=self.documento,
            licitacao=self.licitacao,
            responsavel=None,
            responsavel_id=None,
            parecer="",
            status="pendente",
            prioridade="media",
        )

    def _make_prompt(self, task):
        return PromptPayload(
            task=task,
            system_prompt="SYSTEM",
            user_prompt="USER",
        )

    def test_gerar_resumo_documento_delega_para_builder_e_client(self):
        prompt = self._make_prompt(AnaliseAITask.DOCUMENT_SUMMARY)
        parsed = DocumentSummaryResponse(
            resumo_executivo="Resumo ok",
            fatos=["Fato"],
            inferencias=[],
            lacunas=[],
        )
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.DOCUMENT_SUMMARY,
            model=get_task_config(AnaliseAITask.DOCUMENT_SUMMARY).model,
            text="",
            parsed=parsed,
            response_id="resp_summary",
        )

        with patch("apps.analises.services_ai.build_documento_contexto", return_value={"id": 2}) as documento_contexto, patch(
            "apps.analises.services_ai.build_licitacao_contexto",
            return_value={"id": 1},
        ) as licitacao_contexto, patch(
            "apps.analises.services_ai.build_document_summary_prompt",
            return_value=prompt,
        ) as builder:
            response = self.service.gerar_resumo_documento(
                texto_documento="  Conteudo do edital.  ",
                documento=self.documento,
                licitacao=self.licitacao,
            )

        documento_contexto.assert_called_once_with(self.documento)
        licitacao_contexto.assert_called_once_with(self.licitacao)
        builder.assert_called_once_with(
            texto_documento="Conteudo do edital.",
            documento_contexto={"id": 2},
            licitacao_contexto={"id": 1},
        )
        self.client.gerar_resposta.assert_called_once_with(
            prompt,
            task_config=get_task_config(AnaliseAITask.DOCUMENT_SUMMARY),
        )
        self.assertEqual(response["resumo_executivo"], "Resumo ok")

    def test_extrair_dados_documento_delega_para_builder_e_client(self):
        prompt = self._make_prompt(AnaliseAITask.DOCUMENT_EXTRACTION)
        parsed = DocumentExtractionResponse(
            campos_extraidos={},
            fatos=["Prazo encontrado"],
            inferencias=[],
            lacunas=[],
        )
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.DOCUMENT_EXTRACTION,
            model=get_task_config(AnaliseAITask.DOCUMENT_EXTRACTION).model,
            text="",
            parsed=parsed,
            response_id="resp_extract",
        )

        with patch("apps.analises.services_ai.build_documento_contexto", return_value={"id": 2}), patch(
            "apps.analises.services_ai.build_licitacao_contexto",
            return_value={"id": 1},
        ), patch(
            "apps.analises.services_ai.build_extraction_prompt",
            return_value=prompt,
        ) as builder:
            response = self.service.extrair_dados_documento(
                texto_documento="Conteudo",
                documento=self.documento,
                licitacao=self.licitacao,
                campos_alvo=["prazo"],
            )

        builder.assert_called_once_with(
            texto_documento="Conteudo",
            campos_alvo=["prazo"],
            documento_contexto={"id": 2},
            licitacao_contexto={"id": 1},
        )
        self.client.gerar_resposta.assert_called_once_with(
            prompt,
            task_config=get_task_config(AnaliseAITask.DOCUMENT_EXTRACTION),
        )
        self.assertEqual(response["fatos"], ["Prazo encontrado"])

    def test_gerar_parecer_tecnico_persiste_resultado_validado(self):
        prompt = self._make_prompt(AnaliseAITask.TECHNICAL_ANALYSIS)
        parsed = TechnicalAnalysisResponse(
            parecer_tecnico="Documento aderente com ressalvas.",
            fatos=["Prazo identificado."],
            inferencias=["Pode exigir revisao juridica."],
            lacunas=["Nao ha matriz de riscos."],
            recomendacoes=["Validar clausulas de garantia."],
            prioridade_sugerida="alta",
            status_sugerido="em_andamento",
        )
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.TECHNICAL_ANALYSIS,
            model=get_task_config(AnaliseAITask.TECHNICAL_ANALYSIS).model,
            text="",
            parsed=parsed,
            response_id="resp_123",
        )

        with patch("apps.analises.services_ai.build_documento_contexto", return_value={"id": 2}), patch(
            "apps.analises.services_ai.build_licitacao_contexto",
            return_value={"id": 1},
        ), patch(
            "apps.analises.services_ai.build_analise_contexto",
            return_value={"id": 9},
        ), patch(
            "apps.analises.services_ai.build_analysis_prompt",
            return_value=prompt,
        ) as builder:
            response = self.service.gerar_parecer_tecnico(
                texto_documento="Conteudo relevante do edital.",
                licitacao=self.licitacao,
                documento=self.documento,
                analise=self.analise,
                persistir=True,
            )

        builder.assert_called_once_with(
            texto_documento="Conteudo relevante do edital.",
            documento_contexto={"id": 2},
            licitacao_contexto={"id": 1},
            analise_contexto={"id": 9},
        )
        self.client.gerar_resposta.assert_called_once_with(
            prompt,
            task_config=get_task_config(AnaliseAITask.TECHNICAL_ANALYSIS),
        )
        self.assertEqual(response["status_sugerido"], "em_andamento")
        self.analise_service.atualizar.assert_called_once_with(
            self.analise,
            {
                "titulo": self.analise.titulo,
                "descricao": self.analise.descricao,
                "documento": self.analise.documento,
                "licitacao": self.analise.licitacao,
                "responsavel": self.analise.responsavel,
                "parecer": "Documento aderente com ressalvas.",
                "status": "em_andamento",
                "prioridade": "alta",
            },
        )

    def test_comparar_documento_com_licitacao_delega_para_builder_e_client(self):
        prompt = self._make_prompt(AnaliseAITask.DOCUMENT_COMPARISON)
        parsed = ComparisonResponse(
            aderencias=["Atende prazo"],
            divergencias=["Nao ha garantia"],
            lacunas=[],
            fatos=["Prazo encontrado"],
            inferencias=["Risco contratual"],
            recomendacao="Ajustar clausula",
        )
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.DOCUMENT_COMPARISON,
            model=get_task_config(AnaliseAITask.DOCUMENT_COMPARISON).model,
            text="",
            parsed=parsed,
            response_id="resp_comparison",
        )

        with patch("apps.analises.services_ai.build_documento_contexto", return_value={"id": 2}), patch(
            "apps.analises.services_ai.build_licitacao_contexto",
            return_value={"id": 1},
        ), patch(
            "apps.analises.services_ai.build_comparison_prompt",
            return_value=prompt,
        ) as builder:
            response = self.service.comparar_documento_com_licitacao(
                texto_documento="Conteudo",
                licitacao=self.licitacao,
                documento=self.documento,
            )

        builder.assert_called_once_with(
            texto_documento="Conteudo",
            documento_contexto={"id": 2},
            licitacao_contexto={"id": 1},
        )
        self.client.gerar_resposta.assert_called_once_with(
            prompt,
            task_config=get_task_config(AnaliseAITask.DOCUMENT_COMPARISON),
        )
        self.assertEqual(response["divergencias"], ["Nao ha garantia"])

    def test_gerar_checklist_delega_para_builder_e_client(self):
        prompt = self._make_prompt(AnaliseAITask.CHECKLIST_GENERATION)
        parsed = ChecklistResponse(
            resumo="Checklist gerado",
            fatos=["Documento possui objeto"],
            inferencias=[],
            lacunas=[],
            itens=[],
        )
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.CHECKLIST_GENERATION,
            model=get_task_config(AnaliseAITask.CHECKLIST_GENERATION).model,
            text="",
            parsed=parsed,
            response_id="resp_checklist",
        )

        with patch("apps.analises.services_ai.build_documento_contexto", return_value={"id": 2}), patch(
            "apps.analises.services_ai.build_licitacao_contexto",
            return_value={"id": 1},
        ), patch(
            "apps.analises.services_ai.build_checklist_prompt",
            return_value=prompt,
        ) as builder:
            response = self.service.gerar_checklist(
                texto_documento="  Conteudo  ",
                licitacao=self.licitacao,
                documento=self.documento,
                contexto_comparacao={"divergencias": ["Garantia ausente"]},
            )

        builder.assert_called_once_with(
            texto_documento="Conteudo",
            documento_contexto={"id": 2},
            licitacao_contexto={"id": 1},
            comparison_contexto={"divergencias": ["Garantia ausente"]},
        )
        self.client.gerar_resposta.assert_called_once_with(
            prompt,
            task_config=get_task_config(AnaliseAITask.CHECKLIST_GENERATION),
        )
        self.assertEqual(response["resumo"], "Checklist gerado")

    def test_rejeita_payload_invalido_sem_vazar_estrutura_incorreta(self):
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.DOCUMENT_SUMMARY,
            model=get_task_config(AnaliseAITask.DOCUMENT_SUMMARY).model,
            text="",
            parsed=["payload-invalido"],
            response_id="resp_invalid",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "A resposta da IA nao respeitou o contrato estruturado esperado.",
        ):
            self.service.gerar_resumo_documento(texto_documento="Documento de teste.")

    def test_rejeita_texto_vazio_para_tarefas_que_exigem_documento(self):
        with self.assertRaisesMessage(
            ValidationError,
            "O texto do documento e obrigatorio para executar a tarefa de IA.",
        ):
            self.service.gerar_resumo_documento(texto_documento="   ")
