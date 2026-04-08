from datetime import date
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings

from apps.analises.choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)
from apps.analises.models import Analise, AnaliseExecucaoIA
from apps.analises.services_async import AnaliseAsyncService, AnaliseExecucaoIAService
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="bussula-analises-history-unit-")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AnaliseExecutionHistoryUnitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="analista-history-unit",
            email="analista-history-unit@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="History Unit",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-303/2026",
            objeto="Contratacao de historico de execucoes",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 6, 5),
            ativa=True,
        )
        cls.documento = Documento.objects.create(
            licitacao=cls.licitacao,
            nome="Edital Historico Unit",
            arquivo=SimpleUploadedFile("historico-unit.pdf", b"pdf"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise para historico unitario",
            descricao="Historico",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=cls.user,
        )

    def setUp(self):
        self.execucao_service = AnaliseExecucaoIAService()
        self.async_service = AnaliseAsyncService(execucao_service=self.execucao_service)

    def test_criar_solicitacao_define_versao_incremental_por_analise_e_tipo(self):
        with transaction.atomic():
            primeira = self.execucao_service.criar_solicitacao(
                analise=self.analise,
                tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
                payload_entrada={"texto_documento": "Base 1"},
                criado_por=self.user,
            )
            self.execucao_service.marcar_falha(
                primeira,
                mensagem_erro="Falha 1",
                erro_detalhe_interno="Falha tecnica 1",
            )
            segunda = self.execucao_service.criar_solicitacao(
                analise=self.analise,
                tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
                payload_entrada={"texto_documento": "Base 2"},
                criado_por=self.user,
            )
            parecer = self.execucao_service.criar_solicitacao(
                analise=self.analise,
                tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
                payload_entrada={"texto_documento": "Base parecer"},
                criado_por=self.user,
            )

        self.assertEqual(primeira.versao, 1)
        self.assertEqual(segunda.versao, 2)
        self.assertEqual(parecer.versao, 1)
        self.assertEqual(segunda.criado_por, self.user)

    def test_marcar_concluida_persiste_resultado_bruto_e_limpa_erros(self):
        execucao = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.EM_PROCESSAMENTO,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
            mensagem_erro="Erro antigo",
            erro_detalhe_interno="Stack antigo",
        )

        self.execucao_service.marcar_concluida(
            execucao,
            resultado_payload={"resumo_executivo": "Resumo auditavel"},
            resultado_bruto="Resumo bruto auditavel",
            modelo_utilizado="gpt-5.4-mini",
            response_id="resp-audit-1",
        )

        execucao.refresh_from_db()
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.CONCLUIDO)
        self.assertEqual(execucao.resultado_bruto, "Resumo bruto auditavel")
        self.assertEqual(execucao.modelo_utilizado, "gpt-5.4-mini")
        self.assertEqual(execucao.mensagem_erro, "")
        self.assertEqual(execucao.erro_detalhe_interno, "")

    def test_marcar_falha_registra_erro_resumido_e_detalhe_interno(self):
        execucao = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            status=StatusExecucaoIAChoices.EM_PROCESSAMENTO,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
        )

        self.execucao_service.marcar_falha(
            execucao,
            mensagem_erro="Nao foi possivel concluir o processamento de IA. Tente novamente.",
            erro_detalhe_interno="ValidationError: schema invalido",
        )

        execucao.refresh_from_db()
        self.assertEqual(execucao.status, StatusExecucaoIAChoices.FALHOU)
        self.assertIn("Tente novamente", execucao.mensagem_erro)
        self.assertEqual(
            execucao.erro_detalhe_interno,
            "ValidationError: schema invalido",
        )

    def test_reprocessar_execucao_cria_nova_versao_e_vinculo_de_origem(self):
        origem = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.EXTRACAO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Base original", "campos_alvo": ["prazo"]},
            resultado_payload={"campos": []},
            criado_por=self.user,
        )
        task_handler = Mock()
        task_handler.enqueue.return_value = SimpleNamespace(
            id="task-history-2",
            backend="default",
        )

        with patch.object(self.async_service, "_get_task_handler", return_value=task_handler):
            with self.captureOnCommitCallbacks(execute=True):
                nova_execucao, created = self.async_service.reprocessar_execucao(
                    execucao=origem,
                    criado_por=self.user,
                )

        self.assertTrue(created)
        self.assertNotEqual(nova_execucao.pk, origem.pk)
        self.assertEqual(nova_execucao.versao, 2)
        self.assertEqual(nova_execucao.reprocessamento_de, origem)
        self.assertEqual(nova_execucao.criado_por, self.user)
        nova_execucao.refresh_from_db()
        self.assertEqual(nova_execucao.status, StatusExecucaoIAChoices.PENDENTE)
        self.assertEqual(nova_execucao.identificador_task, "task-history-2")

    def test_preparar_comparacao_identifica_mudancas_de_modelo_e_payload(self):
        base = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
            resultado_payload={"resumo_executivo": "Resumo A", "fatos": ["Fato 1"]},
            modelo_utilizado="gpt-5.4-mini",
        )
        comparada = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=2,
            payload_entrada={"texto_documento": "Base"},
            resultado_payload={
                "resumo_executivo": "Resumo B",
                "fatos": ["Fato 1", "Fato 2"],
                "lacunas": ["Sem anexo"],
            },
            modelo_utilizado="gpt-5.4",
        )

        comparison = self.execucao_service.preparar_comparacao(
            execucao_base=base,
            execucao_comparada=comparada,
        )

        self.assertTrue(comparison["houve_mudanca_resultado"])
        self.assertTrue(
            any(item["label"] == "Modelo" for item in comparison["mudancas_metadados"])
        )
        self.assertTrue(
            any(item["campo"] == "resumo_executivo" for item in comparison["campos_alterados"])
        )
        self.assertTrue(
            any(item["campo"] == "lacunas" for item in comparison["campos_adicionados"])
        )

    def test_obter_ultima_por_tipo_considera_versao_mais_recente(self):
        antiga = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.CHECKLIST,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
        )
        atual = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.CHECKLIST,
            status=StatusExecucaoIAChoices.PENDENTE,
            versao=2,
            payload_entrada={"texto_documento": "Base"},
        )

        ultima = self.execucao_service.obter_ultima_por_tipo(
            self.analise,
            TipoTarefaExecucaoIAChoices.CHECKLIST,
        )

        self.assertEqual(ultima.pk, atual.pk)
        self.assertNotEqual(ultima.pk, antiga.pk)
