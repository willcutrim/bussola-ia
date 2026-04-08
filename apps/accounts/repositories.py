from apps.core.repositories import BaseRepository

from .models import User


class UserRepository(BaseRepository):
    model = User

    def get_queryset(self):
        return super().get_queryset()

    def listar_com_filtros(self, filtros=None):
        filtros = filtros or {}
        queryset = self.get_queryset()

        username = filtros.get("username")
        if username:
            queryset = queryset.filter(username__icontains=username)

        email = filtros.get("email")
        if email:
            queryset = queryset.filter(email__icontains=email)

        nome_completo = filtros.get("nome_completo")
        if nome_completo:
            queryset = queryset.filter(nome_completo__icontains=nome_completo)

        ativo = self._normalize_boolean_filter(filtros.get("ativo"))
        if ativo is not None:
            queryset = queryset.filter(ativo=ativo)

        is_staff = self._normalize_boolean_filter(filtros.get("is_staff"))
        if is_staff is not None:
            queryset = queryset.filter(is_staff=is_staff)

        is_superuser = self._normalize_boolean_filter(filtros.get("is_superuser"))
        if is_superuser is not None:
            queryset = queryset.filter(is_superuser=is_superuser)

        return queryset

    def obter_por_id(self, pk):
        return self.get_by_id(pk)

    def obter_por_email(self, email):
        return self.get_queryset().filter(email=email).first()

    def obter_por_username(self, username):
        return self.get_queryset().filter(username=username).first()

    def listar_ativos(self):
        return self.get_queryset().filter(ativo=True)

    def listar_staff(self):
        return self.get_queryset().filter(is_staff=True)

    def listar_superusuarios(self):
        return self.get_queryset().filter(is_superuser=True)

    def total_ativos(self):
        return self.listar_ativos().count()

    def total_staff(self):
        return self.listar_staff().count()

    def _normalize_boolean_filter(self, value):
        if value in (None, ""):
            return None

        if isinstance(value, bool):
            return value

        normalized_value = str(value).strip().lower()
        if normalized_value == "true":
            return True
        if normalized_value == "false":
            return False
        return None
