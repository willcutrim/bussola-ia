from datetime import date
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.tasks import TaskResultStatus
from django.test import TestCase, override_settings

from apps.analises.choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)
from apps.analises.integrations import AITransientError
from apps.analises.models import Analise, AnaliseExecucaoIA
from apps.analises.services_ai import AnaliseAIExecutionResult
from apps.analises.tasks import (
    _executar_execucao_ia,
    gerar_resumo_documento_task,
)
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
class AnaliseTasksUnitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="analista-task",
            email="analista-task@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="Task Labs",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-101/2026",
            objeto="Contratacao de servicos de automacao",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 4, 20),
            ativa=True,
        )
        cls.documento = Documento.objects.create(
            licitacao=cls.licitacao,
            nome="Edital Task",
            arquivo=SimpleUploadedFile("edital-task.pdf", b"task"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise de task",
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

    def test_task_resumo_atualiza_status_para_concluido(self):
        execucao = self.criar_execucao(
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            payload_entrada={"texto_documento": "Conteudo resumivel"},
        )

        with patch(
            "apps.analises.tasks.AnaliseAIService.gerar_resumo_documento",
            return_value=AnaliseAIExecutionResult(
                payload={
                    "resumo_executivo": "Resumo pronto",
                    "fatos": ["Fato 1"],
                    "inferencias": [],
                    "lacunas": [],
                },
                model="gpt-5.4-mini",
                response_id="resp-1",
            ),
        ):
            task_result = gerar_resumo_documento_task.enqueue(execucao_id=execucao.pk)

        execucao.refresh_from_db()
        self.assertEqual(task_result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.CONCLUIDO)
        self.assertEqual(execucao.tentativas, 1)
        self.assertEqual(execucao.resultado_payload["resumo_executivo"], "Resumo pronto")
        self.assertEqual(execucao.modelo_utilizado, "gpt-5.4-mini")

    def test_task_resumo_marca_falha_quando_service_levanta_erro_previsivel(self):
        execucao = self.criar_execucao(
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            payload_entrada={"texto_documento": "Conteudo resumivel"},
        )

        with patch(
            "apps.analises.tasks.AnaliseAIService.gerar_resumo_documento",
            side_effect=ValidationError("Falha controlada"),
        ):
            task_result = gerar_resumo_documento_task.enqueue(execucao_id=execucao.pk)

        execucao.refresh_from_db()
        self.assertEqual(task_result.status, TaskResultStatus.FAILED)
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.FALHOU)
        self.assertEqual(execucao.tentativas, 1)
        self.assertTrue(execucao.mensagem_erro)

    def test_execucao_transitoria_reagenda_retry_quando_backend_suporta_defer(self):
        execucao = self.criar_execucao(
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            payload_entrada={"texto_documento": "Conteudo resumivel"},
        )
        fake_context = SimpleNamespace(
            task_result=SimpleNamespace(id="task-atual"),
            attempt=1,
        )
        fake_task_handler = Mock()
        fake_task_handler.get_backend.return_value = SimpleNamespace(
            supports_defer=True
        )
        fake_task_handler.using.return_value.enqueue.return_value = SimpleNamespace(
            id="task-retry",
            backend="default",
        )
        fake_ai_service = Mock()
        fake_ai_service.gerar_resumo_documento.side_effect = AITransientError(
            "Indisponibilidade temporaria"
        )

        with patch("apps.analises.tasks.AnaliseAIService", return_value=fake_ai_service):
            result = _executar_execucao_ia(
                context=fake_context,
                execucao_id=execucao.pk,
                tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
                task_handler=fake_task_handler,
            )

        execucao.refresh_from_db()
        self.assertTrue(result["retry_agendado"])
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.PENDENTE)
        self.assertEqual(execucao.identificador_task, "task-retry")
        self.assertEqual(execucao.tentativas, 1)
