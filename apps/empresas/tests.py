from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .models import ContatoEmpresa, Empresa, EnderecoEmpresa
from .repositories import (
    ContatoEmpresaRepository,
    EmpresaRepository,
    EnderecoEmpresaRepository,
)
from .services import ContatoEmpresaService, EmpresaService, EnderecoEmpresaService
from .views import ContatoEmpresaListView, EmpresaListView


class EmpresasBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="tester",
            email="tester@example.com",
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
            ativa=False,
        )
        cls.empresa_gamma = Empresa.objects.create(
            nome="Gamma Participacoes",
            ativa=True,
        )

        cls.endereco_alpha = EnderecoEmpresa.objects.create(
            empresa=cls.empresa_alpha,
            logradouro="Rua A",
            cidade="Fortaleza",
            estado="CE",
            cep="60000-000",
        )
        cls.endereco_beta = EnderecoEmpresa.objects.create(
            empresa=cls.empresa_beta,
            logradouro="Rua B",
            cidade="Recife",
            estado="PE",
            cep="50000-000",
        )

        cls.contato_alpha_principal = ContatoEmpresa.objects.create(
            empresa=cls.empresa_alpha,
            nome="Ana Silva",
            principal=True,
            ativo=True,
        )
        cls.contato_alpha_secundario = ContatoEmpresa.objects.create(
            empresa=cls.empresa_alpha,
            nome="Bruno Costa",
            principal=False,
            ativo=True,
        )
        cls.contato_beta_inativo = ContatoEmpresa.objects.create(
            empresa=cls.empresa_beta,
            nome="Carla Lima",
            principal=True,
            ativo=False,
        )


class EmpresaRepositoryTests(EmpresasBaseTestCase):
    def setUp(self):
        self.repository = EmpresaRepository()

    def test_listar_com_filtros_aplica_nome_ativa_e_cnpj(self):
        nomes = list(
            self.repository.listar_com_filtros(
                {"nome": "alpha", "ativa": True, "cnpj": "345"}
            ).values_list("nome", flat=True)
        )

        self.assertEqual(nomes, ["Alpha Consultoria"])

    def test_listar_com_filtros_ignora_ativa_vazio(self):
        nomes = list(
            self.repository.listar_com_filtros(
                {"nome": "a", "ativa": "", "cnpj": ""}
            ).values_list("nome", flat=True)
        )

        self.assertEqual(
            nomes,
            ["Alpha Consultoria", "Beta Solucoes", "Gamma Participacoes"],
        )

    def test_retorna_queryset_ordenado_com_select_related_de_endereco(self):
        with self.assertNumQueries(1):
            empresas = list(self.repository.list())
            cidade_primeira = empresas[0].endereco.cidade

        self.assertEqual(
            [empresa.nome for empresa in empresas],
            ["Alpha Consultoria", "Beta Solucoes", "Gamma Participacoes"],
        )
        self.assertEqual(cidade_primeira, "Fortaleza")

    def test_fornece_consultas_utilitarias(self):
        empresa = self.repository.obter_por_id(self.empresa_alpha.pk)
        empresa_por_cnpj = self.repository.obter_por_cnpj("98.765.432/0001-10")
        ativas = list(self.repository.listar_ativas().values_list("nome", flat=True))

        self.assertEqual(empresa, self.empresa_alpha)
        self.assertEqual(empresa_por_cnpj, self.empresa_beta)
        self.assertEqual(ativas, ["Alpha Consultoria", "Gamma Participacoes"])


class EnderecoEmpresaRepositoryTests(EmpresasBaseTestCase):
    def setUp(self):
        self.repository = EnderecoEmpresaRepository()

    def test_lista_e_obtem_endereco_por_empresa(self):
        enderecos = list(self.repository.listar_por_empresa(self.empresa_alpha))
        endereco = self.repository.obter_por_empresa(self.empresa_beta)

        self.assertEqual(enderecos, [self.endereco_alpha])
        self.assertEqual(endereco, self.endereco_beta)


class ContatoEmpresaRepositoryTests(EmpresasBaseTestCase):
    def setUp(self):
        self.repository = ContatoEmpresaRepository()

    def test_lista_ativos_e_obtem_principal_por_empresa(self):
        contatos_alpha = list(self.repository.listar_por_empresa(self.empresa_alpha))
        contatos_ativos_alpha = list(
            self.repository.listar_ativos_por_empresa(self.empresa_alpha)
        )
        principal_alpha = self.repository.obter_principal_por_empresa(self.empresa_alpha)
        principal_beta = self.repository.obter_principal_por_empresa(self.empresa_beta)

        self.assertEqual(
            [contato.nome for contato in contatos_alpha],
            ["Ana Silva", "Bruno Costa"],
        )
        self.assertEqual(
            [contato.nome for contato in contatos_ativos_alpha],
            ["Ana Silva", "Bruno Costa"],
        )
        self.assertEqual(principal_alpha, self.contato_alpha_principal)
        self.assertIsNone(principal_beta)


class EmpresaServiceTests(EmpresasBaseTestCase):
    def setUp(self):
        self.service = EmpresaService()

    def test_criar_normaliza_campos_simples(self):
        empresa = self.service.criar(
            {
                "nome": "  Nova Empresa  ",
                "nome_fantasia": "  Nova  ",
                "razao_social": "  Nova Razao  ",
                "cnpj": "  11.222.333/0001-44  ",
                "email": "  nova@empresa.com  ",
                "telefone": "  85999999999  ",
                "site": "  https://empresa.test  ",
                "ativa": True,
                "observacoes": "  Observacao  ",
            }
        )

        self.assertEqual(empresa.nome, "Nova Empresa")
        self.assertEqual(empresa.nome_fantasia, "Nova")
        self.assertEqual(empresa.razao_social, "Nova Razao")
        self.assertEqual(empresa.cnpj, "11.222.333/0001-44")
        self.assertEqual(empresa.email, "nova@empresa.com")
        self.assertEqual(empresa.telefone, "85999999999")
        self.assertEqual(empresa.site, "https://empresa.test")
        self.assertEqual(empresa.observacoes, "Observacao")

    def test_obter_por_cnpj_retorna_none_quando_vazio(self):
        self.assertIsNone(self.service.obter_por_cnpj("   "))


class EnderecoEmpresaServiceTests(EmpresasBaseTestCase):
    def setUp(self):
        self.service = EnderecoEmpresaService()

    def test_atualizar_normaliza_estado(self):
        endereco = self.service.atualizar(
            self.endereco_alpha,
            {
                "empresa": self.empresa_alpha,
                "logradouro": "  Rua Nova  ",
                "numero": " 123 ",
                "complemento": "  Sala 1 ",
                "bairro": "  Centro ",
                "cidade": "  Fortaleza ",
                "estado": " ce ",
                "cep": " 60000-111 ",
            },
        )

        self.assertEqual(endereco.logradouro, "Rua Nova")
        self.assertEqual(endereco.estado, "ce")
        self.assertEqual(endereco.cep, "60000-111")


class ContatoEmpresaServiceTests(EmpresasBaseTestCase):
    def setUp(self):
        self.service = ContatoEmpresaService()

    def test_atualizar_contato_principal_desmarca_outros(self):
        contato = self.service.atualizar(
            self.contato_alpha_secundario,
            {
                "empresa": self.empresa_alpha,
                "nome": "Bruno Costa",
                "cargo": "",
                "email": "",
                "telefone": "",
                "principal": True,
                "ativo": True,
            },
        )

        self.contato_alpha_principal.refresh_from_db()
        self.assertTrue(contato.principal)
        self.assertFalse(self.contato_alpha_principal.principal)


class EmpresaListViewTests(EmpresasBaseTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_service_filters_converte_querystring(self):
        request = self.factory.get(
            reverse("empresas:index"),
            {"nome": " Alpha ", "ativa": "sim", "cnpj": " 345 "},
        )
        request.user = self.user

        view = EmpresaListView()
        view.setup(request)

        self.assertEqual(
            view.get_service_filters(),
            {"nome": "Alpha", "ativa": True, "cnpj": "345"},
        )

    def test_get_queryset_usa_service_com_filtros(self):
        request = self.factory.get(reverse("empresas:index"), {"ativa": "false"})
        request.user = self.user

        view = EmpresaListView()
        view.setup(request)

        nomes = list(view.get_queryset().values_list("nome", flat=True))

        self.assertEqual(nomes, ["Beta Solucoes"])


class ContatoEmpresaListViewTests(EmpresasBaseTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_queryset_permite_filtrar_por_empresa(self):
        request = self.factory.get(
            reverse("empresas:contato_list"),
            {"empresa": str(self.empresa_alpha.pk)},
        )
        request.user = self.user

        view = ContatoEmpresaListView()
        view.setup(request)

        nomes = list(view.get_queryset().values_list("nome", flat=True))

        self.assertEqual(nomes, ["Ana Silva", "Bruno Costa"])


class EmpresasViewIntegrationTests(EmpresasBaseTestCase):
    def setUp(self):
        self.client.force_login(self.user)

    def test_create_view_cria_empresa_e_redireciona(self):
        response = self.client.post(
            reverse("empresas:create"),
            {
                "nome": "Empresa Delta",
                "nome_fantasia": "Delta",
                "razao_social": "Delta SA",
                "cnpj": "11222333000155",
                "email": "delta@example.com",
                "telefone": "85988887777",
                "site": "https://delta.test",
                "ativa": "on",
                "observacoes": "Nova empresa",
            },
        )

        self.assertRedirects(
            response,
            reverse("empresas:index"),
            fetch_redirect_response=False,
        )
        self.assertTrue(Empresa.objects.filter(nome="Empresa Delta").exists())

    def test_update_view_atualiza_empresa_e_redireciona(self):
        response = self.client.post(
            reverse("empresas:update", args=[self.empresa_alpha.pk]),
            {
                "nome": "Alpha Consultoria Atualizada",
                "nome_fantasia": self.empresa_alpha.nome_fantasia,
                "razao_social": self.empresa_alpha.razao_social,
                "cnpj": self.empresa_alpha.cnpj,
                "email": self.empresa_alpha.email,
                "telefone": self.empresa_alpha.telefone,
                "site": self.empresa_alpha.site,
                "ativa": "on",
                "observacoes": self.empresa_alpha.observacoes,
            },
        )

        self.empresa_alpha.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("empresas:index"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.empresa_alpha.nome, "Alpha Consultoria Atualizada")

    def test_delete_view_realiza_soft_delete_e_redireciona(self):
        response = self.client.post(reverse("empresas:delete", args=[self.empresa_beta.pk]))

        self.empresa_beta.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("empresas:index"),
            fetch_redirect_response=False,
        )
        self.assertIsNotNone(self.empresa_beta.deleted_at)

    def test_contato_create_view_aplica_regra_de_principal(self):
        response = self.client.post(
            reverse("empresas:contato_create"),
            {
                "empresa": self.empresa_alpha.pk,
                "nome": "Novo Principal",
                "cargo": "Comercial",
                "email": "novo@alpha.com",
                "telefone": "85911112222",
                "principal": "on",
                "ativo": "on",
            },
        )

        self.contato_alpha_principal.refresh_from_db()
        novo_principal = ContatoEmpresa.objects.get(nome="Novo Principal")

        self.assertRedirects(
            response,
            reverse("empresas:index"),
            fetch_redirect_response=False,
        )
        self.assertTrue(novo_principal.principal)
        self.assertFalse(self.contato_alpha_principal.principal)
