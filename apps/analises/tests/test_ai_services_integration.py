from datetime import date
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.analises.choices import PrioridadeAnaliseChoices, StatusAnaliseChoices
from apps.analises.constants import AnaliseAITask, get_task_config
from apps.analises.integrations import AIResponsePayload
from apps.analises.models import Analise
from apps.analises.schemas_ai import (
    ChecklistItem,
    ChecklistResponse,
    ComparisonResponse,
    DocumentExtractionResponse,
    DocumentSummaryResponse,
    TechnicalAnalysisResponse,
)
from apps.analises.services_ai import AnaliseAIService
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


class AnaliseAIServiceIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.responsavel = user_model.objects.create_user(
            username="analista-ia",
            email="analista-ia@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="Alpha Consultoria",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-001/2026",
            objeto="Contratacao de servicos de tecnologia",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 4, 20),
            ativa=True,
        )
        cls.documento = Documento.objects.create(
            licitacao=cls.licitacao,
            nome="Edital Alpha",
            arquivo=SimpleUploadedFile("edital-alpha.pdf", b"alpha"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
            observacoes="Documento base",
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise juridica inicial",
            descricao="Primeira leitura",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=cls.responsavel,
        )
        cls.analise_sem_documento = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=None,
            titulo="Analise sem documento",
            descricao="Aguardando upload",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.BAIXA,
            responsavel=cls.responsavel,
        )

    def setUp(self):
        self.client = Mock()
        self.service = AnaliseAIService(client=self.client)

    def test_gerar_resumo_documento_retorna_payload_estruturado_sem_persistencia(self):
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.DOCUMENT_SUMMARY,
            model=get_task_config(AnaliseAITask.DOCUMENT_SUMMARY).model,
            text="",
            parsed=DocumentSummaryResponse(
                resumo_executivo="Resumo sintetico",
                fatos=["Prazo de entrega informado."],
                inferencias=[],
                lacunas=[],
            ),
            response_id="resp_summary",
        )

        payload = self.service.gerar_resumo_documento(
            texto_documento="Conteudo resumivel.",
            documento=None,
            licitacao=None,
        )

        self.analise.refresh_from_db()
        self.assertEqual(payload["resumo_executivo"], "Resumo sintetico")
        self.assertEqual(self.analise.parecer, "")
        self.assertEqual(self.analise.status, StatusAnaliseChoices.PENDENTE)

    def test_extrair_dados_documento_retorna_dados_estruturados(self):
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.DOCUMENT_EXTRACTION,
            model=get_task_config(AnaliseAITask.DOCUMENT_EXTRACTION).model,
            text="",
            parsed=DocumentExtractionResponse(
                campos_extraidos={},
                fatos=["Objeto contratual localizado."],
                inferencias=[],
                lacunas=[],
            ),
            response_id="resp_extract",
        )

        payload = self.service.extrair_dados_documento(
            texto_documento="Objeto: contratacao de software.",
            documento=self.documento,
            licitacao=self.licitacao,
            campos_alvo=["objeto"],
        )

        self.assertEqual(payload["fatos"], ["Objeto contratual localizado."])

    def test_gerar_parecer_tecnico_persiste_resultado_no_banco(self):
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.TECHNICAL_ANALYSIS,
            model=get_task_config(AnaliseAITask.TECHNICAL_ANALYSIS).model,
            text="",
            parsed=TechnicalAnalysisResponse(
                parecer_tecnico="Documento aderente com ressalvas.",
                fatos=["Prazo identificado."],
                inferencias=["Pode exigir revisao juridica."],
                lacunas=["Nao ha matriz de riscos."],
                recomendacoes=["Validar clausulas de garantia."],
                prioridade_sugerida="alta",
                status_sugerido="em_andamento",
            ),
            response_id="resp_analysis",
        )

        payload = self.service.gerar_parecer_tecnico(
            texto_documento="Conteudo relevante do edital.",
            licitacao=self.licitacao,
            documento=self.documento,
            analise=self.analise,
            persistir=True,
        )

        self.analise.refresh_from_db()
        self.assertEqual(payload["parecer_tecnico"], "Documento aderente com ressalvas.")
        self.assertEqual(self.analise.parecer, "Documento aderente com ressalvas.")
        self.assertEqual(self.analise.status, StatusAnaliseChoices.EM_ANDAMENTO)
        self.assertEqual(self.analise.prioridade, PrioridadeAnaliseChoices.ALTA)

    def test_comparar_documento_com_licitacao_retorna_payload_sem_efeitos_colaterais(self):
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.DOCUMENT_COMPARISON,
            model=get_task_config(AnaliseAITask.DOCUMENT_COMPARISON).model,
            text="",
            parsed=ComparisonResponse(
                aderencias=["Atende objeto contratado."],
                divergencias=["Garantia nao identificada."],
                lacunas=["Cronograma ausente."],
                fatos=["Objeto localizado."],
                inferencias=["Risco operacional moderado."],
                recomendacao="Solicitar complemento documental.",
            ),
            response_id="resp_comparison",
        )

        payload = self.service.comparar_documento_com_licitacao(
            texto_documento="Conteudo comparavel.",
            licitacao=self.licitacao,
            documento=None,
        )

        self.analise.refresh_from_db()
        self.assertEqual(payload["divergencias"], ["Garantia nao identificada."])
        self.assertEqual(self.analise.parecer, "")

    def test_gerar_checklist_aceita_contexto_sem_documento_ou_licitacao(self):
        self.client.gerar_resposta.return_value = AIResponsePayload(
            task=AnaliseAITask.CHECKLIST_GENERATION,
            model=get_task_config(AnaliseAITask.CHECKLIST_GENERATION).model,
            text="",
            parsed=ChecklistResponse(
                resumo="Checklist de revisao",
                fatos=["Existe divergencia de prazo."],
                inferencias=[],
                lacunas=[],
                itens=[
                    ChecklistItem(
                        titulo="Validar prazo de entrega",
                        categoria="operacional",
                        status="pendente",
                        justificativa="Prazo nao comprovado.",
                    )
                ],
            ),
            response_id="resp_checklist",
        )

        payload = self.service.gerar_checklist(
            contexto_comparacao={"divergencias": ["Prazo nao comprovado."]},
        )

        self.analise_sem_documento.refresh_from_db()
        self.assertEqual(payload["resumo"], "Checklist de revisao")
        self.assertEqual(payload["itens"][0]["titulo"], "Validar prazo de entrega")
        self.assertEqual(self.analise_sem_documento.parecer, "")
