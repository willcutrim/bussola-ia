from datetime import date
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.tasks import TaskResultStatus
from django.test import TestCase, override_settings

from apps.analises.choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)
from apps.analises.constants import AnaliseAITask, get_task_config
from apps.analises.integrations import AIResponsePayload, AITransientError
from apps.analises.models import Analise, AnaliseExecucaoIA
from apps.analises.schemas_ai import (
    DocumentSummaryResponse,
    TechnicalAnalysisResponse,
)
from apps.analises.tasks import gerar_parecer_tecnico_task, gerar_resumo_documento_task
from config.tasks import ANALISES_AI_QUEUE_NAME
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


IMMEDIATE_TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
        "QUEUES": ["default", ANALISES_AI_QUEUE_NAME],
    }
}
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="bussula-analises-tests-")


@override_settings(TASKS=IMMEDIATE_TASKS, MEDIA_ROOT=TEST_MEDIA_ROOT)
class AnaliseTasksIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="analista-task-int",
            email="analista-task-int@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="Task Integration",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-202/2026",
            objeto="Contratacao de servicos de IA",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 4, 22),
            ativa=True,
        )
        cls.documento = Documento.objects.create(
            licitacao=cls.licitacao,
            nome="Edital Integration",
            arquivo=SimpleUploadedFile("edital-integration.pdf", b"integration"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise de integracao",
            descricao="Primeira leitura",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=cls.user,
        )

    def criar_execucao(self, *, tipo_tarefa, payload_entrada):
        return AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=tipo_tarefa,
            status=StatusExecucaoIAChoices.PENDENTE,
            payload_entrada=payload_entrada,
            resultado_payload={},
        )

    def test_task_resumo_persiste_historico_sem_alterar_analise(self):
        execucao = self.criar_execucao(
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            payload_entrada={"texto_documento": "Conteudo resumivel."},
        )

        with patch(
            "apps.analises.integrations.openai_client.AnaliseOpenAIClient.gerar_resposta",
            return_value=AIResponsePayload(
                task=AnaliseAITask.DOCUMENT_SUMMARY,
                model=get_task_config(AnaliseAITask.DOCUMENT_SUMMARY).model,
                text="Resumo estruturado",
                parsed=DocumentSummaryResponse(
                    resumo_executivo="Resumo estruturado",
                    fatos=["Prazo identificado."],
                    inferencias=[],
                    lacunas=[],
                ),
                response_id="resp-summary-1",
            ),
        ):
            task_result = gerar_resumo_documento_task.enqueue(execucao_id=execucao.pk)

        execucao.refresh_from_db()
        self.analise.refresh_from_db()
        self.assertEqual(task_result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.CONCLUIDO)
        self.assertEqual(execucao.response_id, "resp-summary-1")
        self.assertEqual(execucao.resultado_payload["resumo_executivo"], "Resumo estruturado")
        self.assertEqual(self.analise.parecer, "")
        self.assertEqual(self.analise.status, StatusAnaliseChoices.PENDENTE)

    def test_task_parecer_persiste_resultado_e_atualiza_analise(self):
        execucao = self.criar_execucao(
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            payload_entrada={"texto_documento": "Conteudo tecnico do edital."},
        )

        with patch(
            "apps.analises.integrations.openai_client.AnaliseOpenAIClient.gerar_resposta",
            return_value=AIResponsePayload(
                task=AnaliseAITask.TECHNICAL_ANALYSIS,
                model=get_task_config(AnaliseAITask.TECHNICAL_ANALYSIS).model,
                text="Parecer",
                parsed=TechnicalAnalysisResponse(
                    parecer_tecnico="Documento aderente com ressalvas.",
                    fatos=["Prazo identificado."],
                    inferencias=["Pode exigir revisao juridica."],
                    lacunas=["Nao ha matriz de riscos."],
                    recomendacoes=["Validar clausulas de garantia."],
                    prioridade_sugerida="alta",
                    status_sugerido="em_andamento",
                ),
                response_id="resp-analysis-1",
            ),
        ):
            task_result = gerar_parecer_tecnico_task.enqueue(execucao_id=execucao.pk)

        execucao.refresh_from_db()
        self.analise.refresh_from_db()
        self.assertEqual(task_result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.CONCLUIDO)
        self.assertEqual(execucao.modelo_utilizado, get_task_config(AnaliseAITask.TECHNICAL_ANALYSIS).model)
        self.assertEqual(self.analise.parecer, "Documento aderente com ressalvas.")
        self.assertEqual(self.analise.status, StatusAnaliseChoices.EM_ANDAMENTO)
        self.assertEqual(self.analise.prioridade, PrioridadeAnaliseChoices.ALTA)

    def test_task_transitoria_sem_defer_marca_execucao_como_falhou(self):
        execucao = self.criar_execucao(
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            payload_entrada={"texto_documento": "Conteudo resumivel."},
        )

        with patch(
            "apps.analises.integrations.openai_client.AnaliseOpenAIClient.gerar_resposta",
            side_effect=AITransientError("Rate limit"),
        ):
            task_result = gerar_resumo_documento_task.enqueue(execucao_id=execucao.pk)

        execucao.refresh_from_db()
        self.assertEqual(task_result.status, TaskResultStatus.FAILED)
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.FALHOU)
        self.assertTrue(execucao.mensagem_erro)
