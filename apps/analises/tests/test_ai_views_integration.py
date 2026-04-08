from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.analises.choices import PrioridadeAnaliseChoices, StatusAnaliseChoices
from apps.analises.models import Analise
from apps.analises.views_ai import (
    AnaliseCompararDocumentoView,
    AnaliseExtrairDadosDocumentoView,
    AnaliseGerarChecklistView,
    AnaliseGerarParecerView,
    AnaliseGerarResumoDocumentoView,
)
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


class AnaliseAIViewsIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="analista-ia",
            email="analista-ia@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="Bussola Labs",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-010/2026",
            objeto="Contratacao de plataforma analitica",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 5, 5),
            ativa=True,
        )
        cls.documento = Documento.objects.create(
            licitacao=cls.licitacao,
            nome="Edital principal",
            arquivo=SimpleUploadedFile("edital-principal.pdf", b"pdf"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise inicial",
            descricao="Primeira rodada",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=cls.user,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_detail_renderiza_workspace_de_ia(self):
        response = self.client.get(reverse("analises:detail", args=[self.analise.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Central de analise assistida")
        self.assertContains(response, "Gerar resumo do documento")
        self.assertContains(response, 'id="ai-summary-panel"', html=False)

    def test_rotas_de_ia_exigem_autenticacao(self):
        self.client.logout()

        response = self.client.post(
            reverse("analises:ia_resumo", args=[self.analise.pk]),
            {"texto_documento": "Conteudo"},
        )

        self.assertEqual(response.status_code, 302)

    @patch.object(AnaliseGerarResumoDocumentoView, "ai_service_class")
    def test_ia_resumo_delega_para_service_com_contexto_da_analise(self, service_class):
        service_class.return_value.gerar_resumo_documento.return_value = {
            "resumo_executivo": "Resumo sintetico",
        }

        response = self.client.post(
            reverse("analises:ia_resumo", args=[self.analise.pk]),
            {"texto_documento": "Conteudo do edital."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["task"], "resumo_documento")
        self.assertIn("/analises/", response.json()["analise"]["detail_url"])
        service_class.return_value.gerar_resumo_documento.assert_called_once_with(
            texto_documento="Conteudo do edital.",
            documento=self.documento,
            licitacao=self.licitacao,
        )

    @patch.object(AnaliseGerarResumoDocumentoView, "ai_service_class")
    def test_ia_resumo_htmx_retorna_fragmento_html(self, service_class):
        service_class.return_value.gerar_resumo_documento.return_value = {
            "resumo_executivo": "Resumo sintetico via HTMX",
            "fatos": ["Prazo localizado."],
            "inferencias": [],
            "lacunas": [],
        }

        response = self.client.post(
            reverse("analises:ia_resumo", args=[self.analise.pk]),
            {"texto_documento": "Conteudo do edital."},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumo do documento")
        self.assertContains(response, "Resumo sintetico via HTMX")

    @patch.object(AnaliseExtrairDadosDocumentoView, "ai_service_class")
    def test_ia_extracao_delega_para_service(self, service_class):
        service_class.return_value.extrair_dados_documento.return_value = {
            "campos_extraidos": {},
        }

        response = self.client.post(
            reverse("analises:ia_extracao", args=[self.analise.pk]),
            {
                "texto_documento": "Conteudo do edital.",
                "campos_alvo": "prazo,garantia",
            },
        )

        self.assertEqual(response.status_code, 200)
        service_class.return_value.extrair_dados_documento.assert_called_once_with(
            texto_documento="Conteudo do edital.",
            documento=self.documento,
            licitacao=self.licitacao,
            campos_alvo=["prazo", "garantia"],
        )

    @patch.object(AnaliseGerarParecerView, "ai_service_class")
    def test_ia_parecer_persiste_resultado_no_service(self, service_class):
        service_class.return_value.gerar_parecer_tecnico.return_value = {
            "parecer_tecnico": "Parecer gerado",
            "status_sugerido": "em_andamento",
            "prioridade_sugerida": "alta",
        }

        response = self.client.post(
            reverse("analises:ia_parecer", args=[self.analise.pk]),
            {"texto_documento": "Conteudo tecnico do documento."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["persistido"])
        service_class.return_value.gerar_parecer_tecnico.assert_called_once_with(
            texto_documento="Conteudo tecnico do documento.",
            licitacao=self.licitacao,
            documento=self.documento,
            analise=self.analise,
            persistir=True,
        )

    @patch.object(AnaliseCompararDocumentoView, "ai_service_class")
    def test_ia_comparacao_delega_para_service(self, service_class):
        service_class.return_value.comparar_documento_com_licitacao.return_value = {
            "aderencias": [],
            "divergencias": [],
        }

        response = self.client.post(
            reverse("analises:ia_comparacao", args=[self.analise.pk]),
            {"texto_documento": "Conteudo comparavel."},
        )

        self.assertEqual(response.status_code, 200)
        service_class.return_value.comparar_documento_com_licitacao.assert_called_once_with(
            texto_documento="Conteudo comparavel.",
            licitacao=self.licitacao,
            documento=self.documento,
        )

    @patch.object(AnaliseGerarChecklistView, "ai_service_class")
    def test_ia_checklist_delega_para_service(self, service_class):
        service_class.return_value.gerar_checklist.return_value = {
            "resumo": "Checklist gerado",
            "itens": [],
        }

        response = self.client.post(
            reverse("analises:ia_checklist", args=[self.analise.pk]),
            {
                "texto_documento": "Conteudo base.",
                "comparison_contexto": '{"divergencias": ["Prazo ausente"]}',
            },
        )

        self.assertEqual(response.status_code, 200)
        service_class.return_value.gerar_checklist.assert_called_once_with(
            texto_documento="Conteudo base.",
            licitacao=self.licitacao,
            documento=self.documento,
            contexto_comparacao={"divergencias": ["Prazo ausente"]},
        )

    def test_ia_extracao_retorna_400_quando_texto_nao_e_informado(self):
        response = self.client.post(
            reverse("analises:ia_extracao", args=[self.analise.pk]),
            {},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    @patch.object(AnaliseGerarResumoDocumentoView, "ai_service_class")
    def test_ia_resumo_retorna_400_quando_service_falha_com_erro_previsivel(self, service_class):
        service_class.return_value.gerar_resumo_documento.side_effect = ValueError(
            "Falha controlada"
        )

        response = self.client.post(
            reverse("analises:ia_resumo", args=[self.analise.pk]),
            {"texto_documento": "Conteudo do edital."},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Falha controlada")
