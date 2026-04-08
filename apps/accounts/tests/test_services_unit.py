from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.accounts.services import UserService


class UserServiceUnitTests(SimpleTestCase):
    def setUp(self):
        self.repository = Mock()
        self.repository.get_model.return_value = Mock()
        self.service = UserService(repository=self.repository)

    def test_listar_delega_para_repository(self):
        filtros = {"email": "alpha@"}

        self.service.listar(filtros=filtros)

        self.repository.listar_com_filtros.assert_called_once_with(filtros=filtros)

    def test_obter_delega_para_repository(self):
        self.service.obter(7)

        self.repository.obter_por_id.assert_called_once_with(7)

    def test_obter_por_email_normaliza_e_delega(self):
        self.service.obter_por_email("  Alpha@Example.Com ")

        self.repository.obter_por_email.assert_called_once_with("alpha@example.com")

    def test_obter_por_username_normaliza_e_delega(self):
        self.service.obter_por_username("  alpha.user  ")

        self.repository.obter_por_username.assert_called_once_with("alpha.user")

    def test_criar_normaliza_dados_e_delega_persistencia(self):
        cleaned_data = {
            "username": "  alpha.user  ",
            "email": "  Alpha@Example.Com ",
            "nome_completo": "  Alpha User  ",
            "telefone": " 85999999999 ",
            "ativo": True,
            "deve_trocar_senha": False,
            "is_staff": True,
        }

        self.service.criar(cleaned_data)

        self.repository.create.assert_called_once_with(
            username="alpha.user",
            email="alpha@example.com",
            nome_completo="Alpha User",
            telefone="85999999999",
            ativo=True,
            deve_trocar_senha=False,
            is_staff=True,
            is_active=True,
        )

    def test_atualizar_normaliza_dados_e_sincroniza_status(self):
        instance = Mock(ativo=False, email="old@example.com", username="old-user")
        cleaned_data = {
            "username": "  beta.user  ",
            "email": "  Beta@Example.Com ",
            "nome_completo": "  Beta User  ",
            "telefone": "  ",
            "ativo": False,
            "deve_trocar_senha": True,
            "is_superuser": False,
        }

        self.service.atualizar(instance, cleaned_data)

        self.repository.update.assert_called_once_with(
            instance,
            username="beta.user",
            email="beta@example.com",
            nome_completo="Beta User",
            telefone="",
            ativo=False,
            deve_trocar_senha=True,
            is_superuser=False,
            is_active=False,
        )

    def test_listagens_utilitarias_delegam_para_repository(self):
        self.service.listar_ativos()
        self.service.listar_staff()
        self.service.listar_superusuarios()

        self.repository.listar_ativos.assert_called_once_with()
        self.repository.listar_staff.assert_called_once_with()
        self.repository.listar_superusuarios.assert_called_once_with()

    def test_ativar_e_desativar_atualizam_flags_corretamente(self):
        instance = Mock()

        self.service.ativar(instance)
        self.service.desativar(instance)

        self.repository.update.assert_any_call(instance, ativo=True, is_active=True)
        self.repository.update.assert_any_call(instance, ativo=False, is_active=False)

    def test_marcacao_para_troca_de_senha_atualiza_flag(self):
        instance = Mock()

        self.service.marcar_para_troca_de_senha(instance)
        self.service.remover_marcacao_troca_de_senha(instance)

        self.repository.update.assert_any_call(instance, deve_trocar_senha=True)
        self.repository.update.assert_any_call(instance, deve_trocar_senha=False)

    def test_criar_usuario_com_senha_usa_set_password(self):
        hashed_user = Mock(password="hashed-password")
        user_model = Mock(return_value=hashed_user)
        self.repository.get_model.return_value = user_model

        self.service.criar_usuario(
            {
                "username": "  secure.user ",
                "email": "  secure@example.com ",
                "nome_completo": " Secure User ",
                "telefone": "",
                "ativo": True,
            },
            senha="SenhaSegura123",
        )

        hashed_user.set_password.assert_called_once_with("SenhaSegura123")
        self.repository.create.assert_called_once_with(
            username="secure.user",
            email="secure@example.com",
            nome_completo="Secure User",
            telefone="",
            ativo=True,
            is_active=True,
            password="hashed-password",
        )
