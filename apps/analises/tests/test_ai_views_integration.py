from datetime import date
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.tasks import default_task_backend
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.analises.choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)
from apps.analises.models import Analise, AnaliseExecucaoIA
from config.tasks import ANALISES_AI_QUEUE_NAME
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


DUMMY_TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.dummy.DummyBackend",
        "QUEUES": ["default", ANALISES_AI_QUEUE_NAME],
    }
}
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="bussula-analises-tests-")


@override_settings(TASKS=DUMMY_TASKS, MEDIA_ROOT=TEST_MEDIA_ROOT)
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
        if hasattr(default_task_backend, "clear"):
            default_task_backend.clear()

    def test_detail_renderiza_workspace_de_ia(self):
        response = self.client.get(reverse("analises:detail", args=[self.analise.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Central de analise assistida")
        self.assertContains(response, "Gerar resumo do documento")
        self.assertContains(response, 'id="ai-summary-panel"', html=False)
        self.assertContains(response, "Sem execucao")

    def test_rotas_de_ia_exigem_autenticacao(self):
        self.client.logout()

        response = self.client.post(
            reverse("analises:ia_resumo", args=[self.analise.pk]),
            {"texto_documento": "Conteudo"},
        )

        self.assertEqual(response.status_code, 302)

    def test_ia_resumo_solicita_execucao_assincrona_e_retorna_202_json(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("analises:ia_resumo", args=[self.analise.pk]),
                {"texto_documento": "Conteudo do edital."},
            )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["task_type"], TipoTarefaExecucaoIAChoices.RESUMO)
        self.assertIn("/analises/", payload["detail_url"])
        self.assertIn("/resultado/", payload["resultado_url"])

        execucao = AnaliseExecucaoIA.objects.get(pk=payload["execucao_id"])
        self.assertEqual(execucao.analise, self.analise)
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.PENDENTE)
        self.assertEqual(
            execucao.payload_entrada["texto_documento"],
            "Conteudo do edital.",
        )
        self.assertTrue(execucao.identificador_task)

    def test_ia_resumo_htmx_retorna_card_em_fila(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("analises:ia_resumo", args=[self.analise.pk]),
                {"texto_documento": "Conteudo do edital."},
                HTTP_HX_REQUEST="true",
            )

        self.assertEqual(response.status_code, 202)
        self.assertContains(response, "Resumo do documento", status_code=202)
        self.assertContains(response, "Pendente", status_code=202)
        self.assertContains(response, "Processando analise...", status_code=202)
        self.assertContains(
            response,
            reverse("analises:ia_resumo_resultado", args=[self.analise.pk]),
            status_code=202,
        )
        self.assertContains(response, 'hx-trigger="every 3s"', status_code=202)

    def test_ia_resumo_reaproveita_execucao_ativa(self):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.client.post(
                reverse("analises:ia_resumo", args=[self.analise.pk]),
                {"texto_documento": "Conteudo do edital."},
            )

        with self.captureOnCommitCallbacks(execute=True):
            second = self.client.post(
                reverse("analises:ia_resumo", args=[self.analise.pk]),
                {"texto_documento": "Conteudo do edital."},
            )

        self.assertEqual(AnaliseExecucaoIA.objects.count(), 1)
        self.assertEqual(first.json()["execucao_id"], second.json()["execucao_id"])
        self.assertFalse(second.json()["created"])

    def test_resultado_view_renderiza_resultado_concluido(self):
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            payload_entrada={"texto_documento": "Base"},
            resultado_payload={
                "resumo_executivo": "Resumo consolidado",
                "fatos": ["Fato 1"],
                "inferencias": [],
                "lacunas": [],
            },
            modelo_utilizado="gpt-5.4-mini",
            tentativas=1,
        )

        response = self.client.get(
            reverse("analises:ia_resumo_resultado", args=[self.analise.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumo consolidado")
        self.assertContains(response, "Concluido")
        self.assertContains(response, "Reprocessar")
        self.assertNotContains(response, 'hx-trigger="every 3s"')

    def test_resultado_view_renderiza_estado_de_falha(self):
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.COMPARACAO,
            status=StatusExecucaoIAChoices.FALHOU,
            payload_entrada={"texto_documento": "Base"},
            resultado_payload={},
            mensagem_erro="Falha controlada.",
            tentativas=2,
        )

        response = self.client.get(
            reverse("analises:ia_comparacao_resultado", args=[self.analise.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Falhou")
        self.assertContains(response, "Falha controlada.")
        self.assertContains(response, "Reprocessar")

    def test_ia_extracao_retorna_400_quando_texto_nao_e_informado(self):
        response = self.client.post(
            reverse("analises:ia_extracao", args=[self.analise.pk]),
            {},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
