from datetime import date
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.analises.choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
)
from apps.analises.models import Analise, AnaliseExecucaoIA
from apps.analises.services_async import AnaliseAsyncService
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="bussula-analises-tests-")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AnaliseAsyncServiceUnitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="analista-async",
            email="analista-async@example.com",
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
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise juridica inicial",
            descricao="Primeira leitura",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=cls.user,
        )

    def test_solicitar_resumo_registra_execucao_e_enfileira_no_on_commit(self):
        service = AnaliseAsyncService()
        task_handler = Mock()
        task_handler.enqueue.return_value = SimpleNamespace(
            id="task-123",
            backend="default",
        )

        with patch.object(service, "_get_task_handler", return_value=task_handler):
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                execucao, created = service.solicitar_resumo_documento(
                    analise=self.analise,
                    texto_documento="  Conteudo resumivel.  ",
                )

        self.assertTrue(created)
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.PENDENTE)
        self.assertEqual(execucao.payload_entrada["texto_documento"], "Conteudo resumivel.")
        self.assertEqual(len(callbacks), 1)
        task_handler.enqueue.assert_not_called()

        callbacks[0]()

        execucao.refresh_from_db()
        self.assertEqual(execucao.identificador_task, "task-123")
        task_handler.enqueue.assert_called_once_with(execucao_id=execucao.pk)

    def test_solicitar_reutiliza_execucao_ativa_equivalente(self):
        service = AnaliseAsyncService()
        task_handler = Mock()
        task_handler.enqueue.return_value = SimpleNamespace(
            id="task-123",
            backend="default",
        )

        with patch.object(service, "_get_task_handler", return_value=task_handler):
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                primeira_execucao, created = service.solicitar_parecer_tecnico(
                    analise=self.analise,
                    texto_documento="Conteudo tecnico",
                )

            self.assertTrue(created)
            self.assertEqual(len(callbacks), 1)
            callbacks[0]()

            with self.captureOnCommitCallbacks(execute=False) as callbacks_reuso:
                segunda_execucao, created = service.solicitar_parecer_tecnico(
                    analise=self.analise,
                    texto_documento="Conteudo tecnico",
                )

        self.assertFalse(created)
        self.assertEqual(primeira_execucao.pk, segunda_execucao.pk)
        self.assertEqual(AnaliseExecucaoIA.objects.count(), 1)
        self.assertEqual(len(callbacks_reuso), 0)

    def test_solicitar_extracao_normaliza_campos_alvo_sem_executar_ia_diretamente(self):
        service = AnaliseAsyncService()
        task_handler = Mock()
        task_handler.enqueue.return_value = SimpleNamespace(
            id="task-999",
            backend="default",
        )

        with patch.object(service, "_get_task_handler", return_value=task_handler), patch(
            "apps.analises.services_ai.AnaliseAIService.gerar_resumo_documento"
        ) as ai_method:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                execucao, created = service.solicitar_extracao_documento(
                    analise=self.analise,
                    texto_documento="Texto base",
                    campos_alvo=["prazo", "garantia"],
                )

        self.assertTrue(created)
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.PENDENTE)
        self.assertEqual(execucao.payload_entrada["campos_alvo"], ["prazo", "garantia"])
        ai_method.assert_not_called()
        self.assertEqual(len(callbacks), 1)
