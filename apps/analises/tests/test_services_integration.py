from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.analises.choices import PrioridadeAnaliseChoices, StatusAnaliseChoices
from apps.analises.models import Analise
from apps.analises.services import AnaliseService
from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


class AnaliseServiceIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.responsavel_alpha = user_model.objects.create_user(
            username="analista-alpha",
            email="alpha@example.com",
            password="testpass123",
        )
        cls.responsavel_beta = user_model.objects.create_user(
            username="analista-beta",
            email="beta@example.com",
            password="testpass123",
        )
        cls.empresa = Empresa.objects.create(
            nome="Alpha Consultoria",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.licitacao_alpha = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="PE-001/2026",
            objeto="Contratacao de servicos de tecnologia",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 4, 20),
            ativa=True,
        )
        cls.licitacao_beta = Licitacao.objects.create(
            empresa=cls.empresa,
            numero="CC-002/2026",
            objeto="Obra de infraestrutura",
            orgao="Governo do Estado",
            modalidade=ModalidadeChoices.CONCORRENCIA,
            situacao=SituacaoChoices.EM_ANDAMENTO,
            data_abertura=date(2026, 5, 10),
            ativa=True,
        )
        cls.documento_alpha = Documento.objects.create(
            licitacao=cls.licitacao_alpha,
            nome="Edital Alpha",
            arquivo=SimpleUploadedFile("edital-alpha.pdf", b"alpha"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
            observacoes="Documento base",
        )
        cls.documento_beta = Documento.objects.create(
            licitacao=cls.licitacao_beta,
            nome="Contrato Beta",
            arquivo=SimpleUploadedFile("contrato-beta.pdf", b"beta"),
            tipo=TipoDocumentoChoices.CONTRATO,
            status=StatusDocumentoChoices.VALIDADO,
            observacoes="Documento final",
        )

    def setUp(self):
        self.service = AnaliseService()
        self.analise_alpha = Analise.objects.create(
            licitacao=self.licitacao_alpha,
            documento=self.documento_alpha,
            titulo="Analise juridica inicial",
            descricao="Primeira leitura",
            status=StatusAnaliseChoices.PENDENTE,
            parecer="",
            prioridade=PrioridadeAnaliseChoices.ALTA,
            responsavel=self.responsavel_alpha,
        )
        self.analise_beta = Analise.objects.create(
            licitacao=self.licitacao_beta,
            documento=self.documento_beta,
            titulo="Analise comercial concluida",
            descricao="Revisao financeira",
            status=StatusAnaliseChoices.CONCLUIDA,
            parecer="Viavel",
            prioridade=PrioridadeAnaliseChoices.MEDIA,
            responsavel=self.responsavel_beta,
        )

    def test_criar_analise_persiste_corretamente(self):
        analise = self.service.criar(
            {
                "licitacao": self.licitacao_alpha,
                "documento": self.documento_alpha,
                "titulo": "  Analise tecnica final  ",
                "descricao": "  Revisao detalhada  ",
                "status": StatusAnaliseChoices.CONCLUIDA,
                "parecer": "  Aprovada  ",
                "prioridade": PrioridadeAnaliseChoices.CRITICA,
                "responsavel": self.responsavel_alpha,
                "concluida_em": None,
            }
        )

        self.assertEqual(analise.titulo, "Analise tecnica final")
        self.assertEqual(analise.descricao, "Revisao detalhada")
        self.assertEqual(analise.parecer, "Aprovada")
        self.assertEqual(analise.status, StatusAnaliseChoices.CONCLUIDA)
        self.assertIsNotNone(analise.concluida_em)
        self.assertTrue(Analise.objects.filter(titulo="Analise tecnica final").exists())

    def test_atualizar_analise_limpa_conclusao_quando_reaberta(self):
        analise = self.service.atualizar(
            self.analise_beta,
            {
                "licitacao": self.licitacao_beta,
                "documento": self.documento_beta,
                "titulo": "  Analise comercial reaberta  ",
                "descricao": "  Ajustes solicitados  ",
                "status": StatusAnaliseChoices.EM_ANDAMENTO,
                "parecer": "  Necessita revisao  ",
                "prioridade": PrioridadeAnaliseChoices.ALTA,
                "responsavel": self.responsavel_beta,
                "concluida_em": self.analise_beta.concluida_em,
            },
        )

        self.analise_beta.refresh_from_db()
        self.assertEqual(analise.titulo, "Analise comercial reaberta")
        self.assertEqual(self.analise_beta.status, StatusAnaliseChoices.EM_ANDAMENTO)
        self.assertEqual(self.analise_beta.parecer, "Necessita revisao")
        self.assertIsNone(self.analise_beta.concluida_em)

    def test_listar_com_filtros_retorna_resultados_esperados(self):
        analises = list(
            self.service.listar(
                {
                    "licitacao": self.licitacao_alpha,
                    "documento": self.documento_alpha,
                    "titulo": "juridica",
                    "status": StatusAnaliseChoices.PENDENTE,
                    "prioridade": PrioridadeAnaliseChoices.ALTA,
                    "responsavel": self.responsavel_alpha,
                }
            )
        )

        self.assertEqual(analises, [self.analise_alpha])

    def test_listar_por_licitacao_funciona_corretamente(self):
        analises = list(self.service.listar_por_licitacao(self.licitacao_beta))

        self.assertEqual(analises, [self.analise_beta])

    def test_listar_por_documento_funciona_corretamente(self):
        analises = list(self.service.listar_por_documento(self.documento_alpha))

        self.assertEqual(analises, [self.analise_alpha])

    def test_listar_por_responsavel_funciona_corretamente(self):
        analises = list(self.service.listar_por_responsavel(self.responsavel_alpha))

        self.assertEqual(analises, [self.analise_alpha])

    def test_listagens_por_status_funcionam_corretamente(self):
        pendentes = list(self.service.listar_pendentes())
        concluidas = list(self.service.listar_concluidas())

        self.assertEqual(pendentes, [self.analise_alpha])
        self.assertEqual(concluidas, [self.analise_beta])

    def test_marcar_status_atualiza_e_persiste_conclusao(self):
        self.service.marcar_como_em_andamento(self.analise_alpha)
        self.analise_alpha.refresh_from_db()
        self.assertEqual(self.analise_alpha.status, StatusAnaliseChoices.EM_ANDAMENTO)
        self.assertIsNone(self.analise_alpha.concluida_em)

        self.service.marcar_como_concluida(self.analise_alpha)
        self.analise_alpha.refresh_from_db()
        self.assertEqual(self.analise_alpha.status, StatusAnaliseChoices.CONCLUIDA)
        self.assertIsNotNone(self.analise_alpha.concluida_em)

        self.service.marcar_como_rejeitada(self.analise_alpha)
        self.analise_alpha.refresh_from_db()
        self.assertEqual(self.analise_alpha.status, StatusAnaliseChoices.REJEITADA)
        self.assertIsNone(self.analise_alpha.concluida_em)
