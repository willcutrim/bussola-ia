from datetime import date, timedelta
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.analises.choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)
from apps.analises.models import Analise, AnaliseExecucaoIA
from apps.analises.services import DashboardIAService
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="bussula-analises-dashboard-unit-")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class DashboardIAServiceUnitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="analista-dashboard-unit",
            email="analista-dashboard-unit@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="Dashboard IA Unit",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-505/2026",
            objeto="Dashboard operacional da IA",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 6, 20),
            ativa=True,
        )
        cls.documento = Documento.objects.create(
            licitacao=cls.licitacao,
            nome="Edital Dashboard Unit",
            arquivo=SimpleUploadedFile("dashboard-unit.pdf", b"pdf"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise dashboard unit",
            descricao="Contexto unitario",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=cls.user,
        )
        cls.analise_critica = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise critica sem parecer",
            descricao="Contexto critico",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.CRITICA,
            responsavel=cls.user,
        )

    def test_obter_dashboard_calcula_kpis_distribuicoes_e_atencao(self):
        agora = timezone.now()
        execucao_concluida = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Base resumo"},
            resultado_payload={"resumo_executivo": "Resumo"},
            modelo_utilizado="gpt-5.4-mini",
            criado_por=self.user,
            solicitada_em=agora - timedelta(hours=4),
            iniciada_em=agora - timedelta(hours=4),
            concluida_em=agora - timedelta(hours=3, minutes=45),
        )
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            status=StatusExecucaoIAChoices.FALHOU,
            versao=1,
            payload_entrada={"texto_documento": "Base parecer"},
            mensagem_erro="Falha 1",
            criado_por=self.user,
            solicitada_em=agora - timedelta(hours=3),
            concluida_em=agora - timedelta(hours=3),
        )
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            status=StatusExecucaoIAChoices.FALHOU,
            versao=2,
            payload_entrada={"texto_documento": "Base parecer 2"},
            mensagem_erro="Falha 2",
            criado_por=self.user,
            solicitada_em=agora - timedelta(hours=2),
            concluida_em=agora - timedelta(hours=2),
        )
        execucao_processando = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.COMPARACAO,
            status=StatusExecucaoIAChoices.EM_PROCESSAMENTO,
            versao=1,
            payload_entrada={"texto_documento": "Base comparacao"},
            criado_por=self.user,
            solicitada_em=agora - timedelta(hours=5),
            iniciada_em=agora - timedelta(hours=3),
        )
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.EXTRACAO,
            status=StatusExecucaoIAChoices.PENDENTE,
            versao=1,
            payload_entrada={"texto_documento": "Base extracao"},
            criado_por=self.user,
            solicitada_em=agora - timedelta(minutes=30),
            reprocessamento_de=execucao_concluida,
        )

        dashboard = DashboardIAService().obter_dashboard()

        self.assertEqual(dashboard["resumo"]["total_execucoes"], 5)
        self.assertEqual(dashboard["resumo"]["total_concluidas"], 1)
        self.assertEqual(dashboard["resumo"]["total_falhas"], 2)
        self.assertEqual(dashboard["resumo"]["total_em_processamento"], 1)
        self.assertEqual(dashboard["resumo"]["total_pendentes"], 1)
        self.assertEqual(dashboard["resumo"]["total_reprocessamentos"], 1)
        self.assertEqual(dashboard["resumo"]["total_analises_com_uso_ia"], 1)
        self.assertIsNotNone(dashboard["resumo"]["tempo_medio_processamento"])

        status_totals = {
            item["value"]: item["total"] for item in dashboard["status_distribution"]
        }
        self.assertEqual(status_totals[StatusExecucaoIAChoices.CONCLUIDO], 1)
        self.assertEqual(status_totals[StatusExecucaoIAChoices.FALHOU], 2)

        tipo_totals = {
            item["value"]: item["total"] for item in dashboard["task_distribution"]
        }
        self.assertEqual(tipo_totals[TipoTarefaExecucaoIAChoices.PARECER], 2)
        self.assertEqual(tipo_totals[TipoTarefaExecucaoIAChoices.RESUMO], 1)

        self.assertEqual(
            dashboard["execucoes_recentes"][0].tipo_tarefa,
            TipoTarefaExecucaoIAChoices.EXTRACAO,
        )
        self.assertEqual(len(dashboard["falhas_recentes"]), 2)
        tipos_atencao = {item["tipo"] for item in dashboard["itens_atencao"]}
        self.assertIn("processamento_longo", tipos_atencao)
        self.assertIn("falhas_recentes", tipos_atencao)
        self.assertIn("critica_sem_parecer", tipos_atencao)
