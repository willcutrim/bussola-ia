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
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="bussula-analises-history-int-")


@override_settings(TASKS=DUMMY_TASKS, MEDIA_ROOT=TEST_MEDIA_ROOT)
class AnaliseExecutionHistoryIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="analista-history-int",
            email="analista-history-int@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="History Integration",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-404/2026",
            objeto="Historico e auditoria na interface",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 6, 15),
            ativa=True,
        )
        cls.documento = Documento.objects.create(
            licitacao=cls.licitacao,
            nome="Edital Historico Integration",
            arquivo=SimpleUploadedFile("historico-integration.pdf", b"pdf"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise para historico integrado",
            descricao="Historico integrado",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=cls.user,
        )

    def setUp(self):
        self.client.force_login(self.user)
        if hasattr(default_task_backend, "clear"):
            default_task_backend.clear()

    def test_historico_renderiza_execucoes_ordenadas_com_metadados(self):
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Base 1"},
            resultado_payload={"resumo_executivo": "Resumo v1"},
            modelo_utilizado="gpt-5.4-mini",
            criado_por=self.user,
        )
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.FALHOU,
            versao=2,
            payload_entrada={"texto_documento": "Base 2"},
            mensagem_erro="Falha controlada",
            modelo_utilizado="gpt-5.4",
            criado_por=self.user,
        )

        response = self.client.get(
            reverse("analises:ia_execucao_historico", args=[self.analise.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historico de execucoes de IA")
        self.assertContains(response, "Versao v2")
        self.assertContains(response, "Versao v1")
        self.assertContains(response, "Falha controlada")
        self.assertLess(
            response.content.decode().index("Versao v2"),
            response.content.decode().index("Versao v1"),
        )

    def test_comparacao_renderiza_diferencas_entre_execucoes(self):
        base = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
            resultado_payload={"parecer_tecnico": "Parecer A", "riscos": ["Risco 1"]},
            modelo_utilizado="gpt-5.4",
        )
        comparada = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=2,
            payload_entrada={"texto_documento": "Base"},
            resultado_payload={
                "parecer_tecnico": "Parecer B",
                "riscos": ["Risco 1", "Risco 2"],
                "proximos_passos": ["Revisar garantias"],
            },
            modelo_utilizado="gpt-5.4-mini",
        )

        response = self.client.get(
            reverse("analises:ia_execucao_comparacao", args=[self.analise.pk]),
            {"base": base.pk, "target": comparada.pk},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mudancas de metadados")
        self.assertContains(response, "Modelo")
        self.assertContains(response, "parecer_tecnico")
        self.assertContains(response, "proximos_passos")

    def test_detalhe_da_execucao_renderiza_resultado_especifico(self):
        execucao = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
            resultado_payload={
                "resumo_executivo": "Resumo especifico",
                "fatos": ["Fato 1"],
                "inferencias": [],
                "lacunas": [],
            },
            modelo_utilizado="gpt-5.4-mini",
        )

        response = self.client.get(
            reverse(
                "analises:ia_execucao_detalhe",
                args=[self.analise.pk, execucao.pk],
            ),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumo especifico")
        self.assertContains(response, "Versao: v1")
        self.assertContains(response, "Reprocessar")

    def test_reprocessamento_via_rota_cria_nova_execucao_rastreavel(self):
        origem = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.COMPARACAO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Documento base"},
            resultado_payload={"conclusao": "Versao inicial"},
            criado_por=self.user,
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse(
                    "analises:ia_execucao_reprocessar",
                    args=[self.analise.pk, origem.pk],
                ),
                HTTP_HX_REQUEST="true",
            )

        self.assertEqual(response.status_code, 202)
        self.assertContains(response, "Pendente", status_code=202)
        self.assertEqual(AnaliseExecucaoIA.objects.count(), 2)

        nova_execucao = AnaliseExecucaoIA.objects.exclude(pk=origem.pk).get()
        self.assertEqual(nova_execucao.versao, 2)
        self.assertEqual(nova_execucao.reprocessamento_de, origem)
        self.assertEqual(nova_execucao.criado_por, self.user)
        self.assertEqual(nova_execucao.status, StatusExecucaoIAChoices.PENDENTE)
        self.assertTrue(nova_execucao.identificador_task)
        self.assertIn("aiHistoryRefresh", response.headers.get("HX-Trigger", ""))
