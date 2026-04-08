from datetime import date, timedelta
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.analises.choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)
from apps.analises.models import Analise, AnaliseExecucaoIA
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="bussula-analises-dashboard-int-")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class DashboardIAViewIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="analista-dashboard-int",
            email="analista-dashboard-int@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="Dashboard IA Integration",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-606/2026",
            objeto="View do dashboard operacional da IA",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 6, 28),
            ativa=True,
        )
        cls.documento = Documento.objects.create(
            licitacao=cls.licitacao,
            nome="Edital Dashboard Integration",
            arquivo=SimpleUploadedFile("dashboard-int.pdf", b"pdf"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
        )
        cls.analise = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise dashboard integration",
            descricao="Contexto",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=cls.user,
        )
        cls.analise_critica = Analise.objects.create(
            licitacao=cls.licitacao,
            documento=cls.documento,
            titulo="Analise critica dashboard",
            descricao="Critica",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.CRITICA,
            responsavel=cls.user,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_dashboard_ia_renderiza_cards_listas_e_alertas(self):
        agora = timezone.now()
        execucao_falha = AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            status=StatusExecucaoIAChoices.FALHOU,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
            mensagem_erro="Erro de schema controlado",
            solicitada_em=agora - timedelta(hours=2),
            concluida_em=agora - timedelta(hours=2),
        )
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
            resultado_payload={"resumo_executivo": "Resumo pronto"},
            modelo_utilizado="gpt-5.4-mini",
            solicitada_em=agora - timedelta(hours=4),
            iniciada_em=agora - timedelta(hours=4),
            concluida_em=agora - timedelta(hours=3, minutes=40),
        )
        AnaliseExecucaoIA.objects.create(
            analise=self.analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.COMPARACAO,
            status=StatusExecucaoIAChoices.EM_PROCESSAMENTO,
            versao=1,
            payload_entrada={"texto_documento": "Base"},
            solicitada_em=agora - timedelta(hours=5),
            iniciada_em=agora - timedelta(hours=3),
        )

        response = self.client.get(reverse("analises:dashboard_ia"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operacao de IA")
        self.assertContains(response, "Execucoes de IA")
        self.assertContains(response, "Distribuicao por status")
        self.assertContains(response, "Distribuicao por tarefa")
        self.assertContains(response, "Ultimas execucoes")
        self.assertContains(response, "Falhas recentes")
        self.assertContains(response, "Itens que exigem acao")
        self.assertContains(response, self.analise.titulo)
        self.assertContains(response, execucao_falha.mensagem_erro)
        self.assertContains(
            response,
            reverse("analises:detail", args=[self.analise.pk]),
        )
        self.assertContains(
            response,
            reverse("analises:ia_execucao_detalhe", args=[self.analise.pk, execucao_falha.pk]),
        )

    def test_dashboard_ia_exige_autenticacao(self):
        self.client.logout()

        response = self.client.get(reverse("analises:dashboard_ia"))

        self.assertEqual(response.status_code, 302)
