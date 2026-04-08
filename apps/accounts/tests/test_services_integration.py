from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.services import UserService


class UserServiceIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user_alpha = user_model.objects.create_user(
            username="alpha.user",
            email="alpha@example.com",
            password="testpass123",
            nome_completo="Alpha User",
            telefone="85999999999",
            ativo=True,
            is_staff=False,
        )
        cls.user_beta = user_model.objects.create_user(
            username="beta.admin",
            email="beta@example.com",
            password="testpass123",
            nome_completo="Beta Admin",
            telefone="85988888888",
            ativo=False,
            is_staff=True,
            is_superuser=True,
        )

    def setUp(self):
        self.service = UserService()

    def test_criar_usuario_persiste_corretamente(self):
        user = self.service.criar(
            {
                "username": "  gamma.user  ",
                "email": "  Gamma@Example.Com ",
                "nome_completo": "  Gamma User  ",
                "telefone": " 85977777777 ",
                "ativo": True,
                "deve_trocar_senha": False,
                "is_staff": False,
            }
        )

        self.assertEqual(user.username, "gamma.user")
        self.assertEqual(user.email, "gamma@example.com")
        self.assertEqual(user.nome_completo, "Gamma User")
        self.assertEqual(user.telefone, "85977777777")
        self.assertTrue(user.ativo)
        self.assertTrue(user.is_active)

    def test_atualizar_usuario_persiste_corretamente(self):
        user = self.service.atualizar(
            self.user_alpha,
            {
                "username": "  alpha.user.updated  ",
                "email": "  alpha.updated@example.com ",
                "nome_completo": "  Alpha Updated  ",
                "telefone": " 85966666666 ",
                "ativo": False,
                "deve_trocar_senha": True,
                "is_staff": True,
            },
        )

        self.user_alpha.refresh_from_db()
        self.assertEqual(user.username, "alpha.user.updated")
        self.assertEqual(self.user_alpha.email, "alpha.updated@example.com")
        self.assertEqual(self.user_alpha.nome_completo, "Alpha Updated")
        self.assertEqual(self.user_alpha.telefone, "85966666666")
        self.assertFalse(self.user_alpha.ativo)
        self.assertFalse(self.user_alpha.is_active)
        self.assertTrue(self.user_alpha.deve_trocar_senha)
        self.assertTrue(self.user_alpha.is_staff)

    def test_listar_com_filtros_retorna_resultados_esperados(self):
        users = list(
            self.service.listar(
                {
                    "username": "beta",
                    "email": "beta@",
                    "nome_completo": "admin",
                    "ativo": "false",
                    "is_staff": "true",
                    "is_superuser": "true",
                }
            )
        )

        self.assertEqual(users, [self.user_beta])

    def test_obter_por_email_funciona_corretamente(self):
        user = self.service.obter_por_email("  ALPHA@EXAMPLE.COM ")

        self.assertEqual(user, self.user_alpha)

    def test_obter_por_username_funciona_corretamente(self):
        user = self.service.obter_por_username("  beta.admin ")

        self.assertEqual(user, self.user_beta)

    def test_ativar_e_desativar_persistem_corretamente(self):
        self.service.desativar(self.user_alpha)
        self.user_alpha.refresh_from_db()
        self.assertFalse(self.user_alpha.ativo)
        self.assertFalse(self.user_alpha.is_active)

        self.service.ativar(self.user_alpha)
        self.user_alpha.refresh_from_db()
        self.assertTrue(self.user_alpha.ativo)
        self.assertTrue(self.user_alpha.is_active)

    def test_criar_usuario_com_senha_gera_hash_corretamente(self):
        user = self.service.criar_usuario(
            {
                "username": "secure.user",
                "email": "secure@example.com",
                "nome_completo": "Secure User",
                "telefone": "",
                "ativo": True,
            },
            senha="SenhaSegura123",
        )

        self.assertNotEqual(user.password, "SenhaSegura123")
        self.assertTrue(user.check_password("SenhaSegura123"))
        self.assertTrue(user.ativo)
        self.assertTrue(user.is_active)
