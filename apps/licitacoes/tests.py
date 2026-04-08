from datetime import date

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.empresas.models import Empresa

from .choices import ModalidadeChoices, SituacaoChoices
from .models import Licitacao
from .repositories import LicitacaoRepository
from .services import LicitacaoService
from .views import LicitacaoListView


class LicitacoesBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="licitacoes-tester",
            email="licitacoes@example.com",
            password="testpass123",
        )
        cls.empresa_alpha = Empresa.objects.create(
            nome="Alpha Consultoria",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        cls.empresa_beta = Empresa.objects.create(
            nome="Beta Solucoes",
            cnpj="98.765.432/0001-10",
            ativa=True,
        )

        cls.licitacao_alpha = Licitacao.objects.create(
            empresa=cls.empresa_alpha,
            numero="PE-001/2026",
            objeto="Contratacao de servicos de tecnologia",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 4, 20),
            valor_estimado="150000.00",
            link_externo="https://alpha.test/licitacao",
            observacoes="Licitacao inicial",
            ativa=True,
        )
        cls.licitacao_beta = Licitacao.objects.create(
            empresa=cls.empresa_beta,
            numero="CC-002/2026",
            objeto="Obra de infraestrutura",
            orgao="Governo do Estado",
            modalidade=ModalidadeChoices.CONCORRENCIA,
            situacao=SituacaoChoices.EM_ANDAMENTO,
            data_abertura=date(2026, 5, 10),
            valor_estimado="950000.00",
            link_externo="https://beta.test/licitacao",
            observacoes="Em disputa",
            ativa=True,
        )
        cls.licitacao_gamma = Licitacao.objects.create(
            numero="DP-003/2025",
            objeto="Aquisicao emergencial",
            orgao="Camara Municipal",
            modalidade=ModalidadeChoices.DISPENSA,
            situacao=SituacaoChoices.ENCERRADA,
            data_abertura=date(2025, 12, 15),
            valor_estimado="50000.00",
            observacoes="Finalizada",
            ativa=False,
        )


class LicitacaoRepositoryTests(LicitacoesBaseTestCase):
    def setUp(self):
        self.repository = LicitacaoRepository()

    def test_listar_com_filtros_aplica_parametros_relevantes(self):
        licitacoes = list(
            self.repository.listar_com_filtros(
                {
                    "empresa": self.empresa_alpha.pk,
                    "numero": "001",
                    "orgao": "fortaleza",
                    "modalidade": ModalidadeChoices.PREGAO,
                    "situacao": SituacaoChoices.EM_ANALISE,
                    "ativa": "true",
                    "data_abertura_inicial": date(2026, 4, 1),
                    "data_abertura_final": date(2026, 4, 30),
                }
            )
        )

        self.assertEqual(licitacoes, [self.licitacao_alpha])

    def test_listar_com_filtros_aceita_instancia_de_empresa(self):
        licitacoes = list(
            self.repository.listar_com_filtros({"empresa": self.empresa_beta})
        )

        self.assertEqual(licitacoes, [self.licitacao_beta])

    def test_queryset_base_usa_select_related_de_empresa(self):
        with self.assertNumQueries(1):
            licitacoes = list(self.repository.list())
            empresa_nome = licitacoes[0].empresa.nome

        self.assertEqual(empresa_nome, "Beta Solucoes")

    def test_metodos_utilitarios(self):
        self.assertEqual(self.repository.obter_por_id(self.licitacao_alpha.pk), self.licitacao_alpha)
        self.assertEqual(self.repository.obter_por_numero("CC-002/2026"), self.licitacao_beta)
        self.assertEqual(
            list(self.repository.listar_ativas().values_list("numero", flat=True)),
            ["CC-002/2026", "PE-001/2026"],
        )
        self.assertEqual(
            list(self.repository.listar_por_empresa(self.empresa_alpha).values_list("numero", flat=True)),
            ["PE-001/2026"],
        )
        self.assertEqual(
            list(self.repository.listar_em_andamento().values_list("numero", flat=True)),
            ["CC-002/2026"],
        )
        self.assertEqual(
            list(self.repository.listar_encerradas().values_list("numero", flat=True)),
            ["DP-003/2025"],
        )
        self.assertEqual(self.repository.total_ativas(), 2)
        self.assertEqual(
            list(self.repository.contar_por_situacao()),
            [
                {"situacao": "em_analise", "total": 1},
                {"situacao": "em_andamento", "total": 1},
                {"situacao": "encerrada", "total": 1},
            ],
        )


class LicitacaoServiceTests(LicitacoesBaseTestCase):
    def setUp(self):
        self.service = LicitacaoService()

    def test_criar_normaliza_campos_textuais(self):
        licitacao = self.service.criar(
            {
                "empresa": self.empresa_alpha,
                "numero": "  PE-100/2026  ",
                "objeto": "  Novo objeto  ",
                "orgao": "  Tribunal Regional  ",
                "modalidade": ModalidadeChoices.PREGAO,
                "situacao": SituacaoChoices.RASCUNHO,
                "data_abertura": date(2026, 6, 1),
                "valor_estimado": "300000.00",
                "link_externo": "  https://nova.test/licitacao  ",
                "observacoes": "  Observacao importante  ",
                "ativa": True,
            }
        )

        self.assertEqual(licitacao.numero, "PE-100/2026")
        self.assertEqual(licitacao.objeto, "Novo objeto")
        self.assertEqual(licitacao.orgao, "Tribunal Regional")
        self.assertEqual(licitacao.link_externo, "https://nova.test/licitacao")
        self.assertEqual(licitacao.observacoes, "Observacao importante")

    def test_obter_por_numero_retorna_none_quando_vazio(self):
        self.assertIsNone(self.service.obter_por_numero("   "))

    def test_metodos_de_situacao_atualizam_registro(self):
        self.service.marcar_como_em_andamento(self.licitacao_alpha)
        self.licitacao_alpha.refresh_from_db()
        self.assertEqual(self.licitacao_alpha.situacao, SituacaoChoices.EM_ANDAMENTO)

        self.service.marcar_como_encerrada(self.licitacao_alpha)
        self.licitacao_alpha.refresh_from_db()
        self.assertEqual(self.licitacao_alpha.situacao, SituacaoChoices.ENCERRADA)

        self.service.marcar_como_cancelada(self.licitacao_beta)
        self.licitacao_beta.refresh_from_db()
        self.assertEqual(self.licitacao_beta.situacao, SituacaoChoices.CANCELADA)


class LicitacaoListViewTests(LicitacoesBaseTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_filter_data_usa_form_valido(self):
        request = self.factory.get(
            reverse("licitacoes:index"),
            {
                "empresa": str(self.empresa_alpha.pk),
                "numero": "PE",
                "orgao": "fortaleza",
                "modalidade": ModalidadeChoices.PREGAO,
                "situacao": SituacaoChoices.EM_ANALISE,
                "ativa": "true",
                "data_abertura_inicial": "2026-04-01",
                "data_abertura_final": "2026-04-30",
            },
        )
        request.user = self.user

        view = LicitacaoListView()
        view.setup(request)

        filter_data = view.get_filter_data()

        self.assertEqual(filter_data["empresa"], self.empresa_alpha)
        self.assertEqual(filter_data["numero"], "PE")
        self.assertEqual(filter_data["orgao"], "fortaleza")
        self.assertEqual(filter_data["modalidade"], ModalidadeChoices.PREGAO)
        self.assertEqual(filter_data["situacao"], SituacaoChoices.EM_ANALISE)
        self.assertEqual(filter_data["ativa"], "true")
        self.assertEqual(filter_data["data_abertura_inicial"], date(2026, 4, 1))
        self.assertEqual(filter_data["data_abertura_final"], date(2026, 4, 30))

    def test_get_queryset_usa_service_com_filtros(self):
        request = self.factory.get(
            reverse("licitacoes:index"),
            {"situacao": SituacaoChoices.EM_ANDAMENTO, "ativa": "true"},
        )
        request.user = self.user

        view = LicitacaoListView()
        view.setup(request)

        numeros = list(view.get_queryset().values_list("numero", flat=True))

        self.assertEqual(numeros, ["CC-002/2026"])


class LicitacoesViewIntegrationTests(LicitacoesBaseTestCase):
    def setUp(self):
        self.client.force_login(self.user)

    def test_create_view_cria_licitacao_e_redireciona(self):
        response = self.client.post(
            reverse("licitacoes:create"),
            {
                "empresa": self.empresa_alpha.pk,
                "numero": " PE-200/2026 ",
                "objeto": " Novo edital ",
                "orgao": " Novo orgao ",
                "modalidade": ModalidadeChoices.PREGAO,
                "situacao": SituacaoChoices.RASCUNHO,
                "data_abertura": "2026-07-10",
                "valor_estimado": "123000.00",
                "link_externo": " https://novo.test/licitacao ",
                "observacoes": " observacao ",
                "ativa": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("licitacoes:index"),
            fetch_redirect_response=False,
        )
        self.assertTrue(Licitacao.objects.filter(numero="PE-200/2026").exists())

    def test_update_view_atualiza_licitacao_e_redireciona(self):
        response = self.client.post(
            reverse("licitacoes:update", args=[self.licitacao_alpha.pk]),
            {
                "empresa": self.empresa_alpha.pk,
                "numero": "PE-001/2026-ATUAL",
                "objeto": self.licitacao_alpha.objeto,
                "orgao": self.licitacao_alpha.orgao,
                "modalidade": self.licitacao_alpha.modalidade,
                "situacao": self.licitacao_alpha.situacao,
                "data_abertura": self.licitacao_alpha.data_abertura.strftime("%Y-%m-%d"),
                "valor_estimado": self.licitacao_alpha.valor_estimado,
                "link_externo": self.licitacao_alpha.link_externo,
                "observacoes": self.licitacao_alpha.observacoes,
                "ativa": "on",
            },
        )

        self.licitacao_alpha.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("licitacoes:index"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.licitacao_alpha.numero, "PE-001/2026-ATUAL")

    def test_delete_view_realiza_soft_delete_e_redireciona(self):
        response = self.client.post(reverse("licitacoes:delete", args=[self.licitacao_beta.pk]))

        self.licitacao_beta.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("licitacoes:index"),
            fetch_redirect_response=False,
        )
        self.assertIsNotNone(self.licitacao_beta.deleted_at)
