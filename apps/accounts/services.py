from apps.core.services import BaseService

from .repositories import UserRepository


def _strip_or_blank(value):
    if isinstance(value, str):
        return value.strip()
    return value


class UserService(BaseService):
    repository_class = UserRepository

    def listar(self, filtros=None):
        return self.get_repository().listar_com_filtros(filtros=filtros)

    def obter(self, pk):
        return self.get_repository().obter_por_id(pk)

    def obter_por_email(self, email):
        email = self._normalizar_email(email)
        if not email:
            return None
        return self.get_repository().obter_por_email(email)

    def obter_por_username(self, username):
        username = _strip_or_blank(username)
        if not username:
            return None
        return self.get_repository().obter_por_username(username)

    def listar_ativos(self):
        return self.get_repository().listar_ativos()

    def listar_staff(self):
        return self.get_repository().listar_staff()

    def listar_superusuarios(self):
        return self.get_repository().listar_superusuarios()

    def total_ativos(self):
        return self.get_repository().total_ativos()

    def total_staff(self):
        return self.get_repository().total_staff()

    def criar(self, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().create(**payload)

    def atualizar(self, instance, cleaned_data):
        payload = self._prepare_payload(cleaned_data, instance=instance)
        return self.get_repository().update(instance, **payload)

    def criar_usuario(self, cleaned_data, senha=None):
        payload = self._prepare_payload(cleaned_data)
        user_model = self.get_repository().get_model()
        user = user_model(**payload)
        if senha:
            user.set_password(senha)
        else:
            user.set_unusable_password()
        payload["password"] = user.password
        return self.get_repository().create(**payload)

    def ativar(self, instance):
        return self.get_repository().update(instance, ativo=True, is_active=True)

    def desativar(self, instance):
        return self.get_repository().update(instance, ativo=False, is_active=False)

    def marcar_para_troca_de_senha(self, instance):
        return self.get_repository().update(instance, deve_trocar_senha=True)

    def remover_marcacao_troca_de_senha(self, instance):
        return self.get_repository().update(instance, deve_trocar_senha=False)

    def _prepare_payload(self, cleaned_data, instance=None):
        payload = dict(cleaned_data)
        payload["username"] = _strip_or_blank(payload.get("username")) or getattr(
            instance, "username", None
        )
        payload["email"] = self._normalizar_email(payload.get("email")) or getattr(
            instance, "email", None
        )
        payload["nome_completo"] = _strip_or_blank(
            payload.get("nome_completo", "")
        )
        payload["telefone"] = _strip_or_blank(payload.get("telefone", ""))
        self._sincronizar_status_ativo(payload, instance=instance)
        return payload

    def _normalizar_email(self, email):
        email = _strip_or_blank(email)
        if not email:
            return None
        return email.lower()

    def _sincronizar_status_ativo(self, payload, instance=None):
        if "ativo" in payload:
            payload["is_active"] = payload["ativo"]
            return

        if instance is not None:
            payload["ativo"] = instance.ativo
            payload["is_active"] = instance.ativo
