from django.db import transaction

from apps.core.services import BaseService

from .repositories import (
    ContatoEmpresaRepository,
    EmpresaRepository,
    EnderecoEmpresaRepository,
)


def _strip_or_blank(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _strip_or_none(value):
    if isinstance(value, str):
        stripped_value = value.strip()
        return stripped_value or None
    return value


class EmpresaService(BaseService):
    repository_class = EmpresaRepository

    def listar(self, filtros=None):
        return self.get_repository().listar_com_filtros(filtros=filtros)

    def obter(self, pk):
        return self.get_repository().obter_por_id(pk)

    def obter_por_cnpj(self, cnpj):
        normalized_cnpj = _strip_or_none(cnpj)
        if not normalized_cnpj:
            return None
        return self.get_repository().obter_por_cnpj(normalized_cnpj)

    def listar_ativas(self):
        return self.get_repository().listar_ativas()

    def total_com_cnpj(self):
        return self.get_repository().total_com_cnpj()

    def criar(self, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().create(**payload)

    def atualizar(self, instance, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().update(instance, **payload)

    def _prepare_payload(self, cleaned_data):
        payload = dict(cleaned_data)
        payload["nome"] = _strip_or_blank(payload.get("nome"))
        payload["nome_fantasia"] = _strip_or_blank(payload.get("nome_fantasia", ""))
        payload["razao_social"] = _strip_or_blank(payload.get("razao_social", ""))
        payload["cnpj"] = _strip_or_none(payload.get("cnpj"))
        payload["email"] = _strip_or_blank(payload.get("email", ""))
        payload["telefone"] = _strip_or_blank(payload.get("telefone", ""))
        payload["site"] = _strip_or_blank(payload.get("site", ""))
        payload["observacoes"] = _strip_or_blank(payload.get("observacoes", ""))
        return payload


class EnderecoEmpresaService(BaseService):
    repository_class = EnderecoEmpresaRepository

    def obter_por_empresa(self, empresa):
        return self.get_repository().obter_por_empresa(empresa)

    def criar(self, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().create(**payload)

    def atualizar(self, instance, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().update(instance, **payload)

    def _prepare_payload(self, cleaned_data):
        payload = dict(cleaned_data)
        payload["logradouro"] = _strip_or_blank(payload.get("logradouro"))
        payload["numero"] = _strip_or_blank(payload.get("numero", ""))
        payload["complemento"] = _strip_or_blank(payload.get("complemento", ""))
        payload["bairro"] = _strip_or_blank(payload.get("bairro", ""))
        payload["cidade"] = _strip_or_blank(payload.get("cidade"))
        payload["estado"] = _strip_or_blank(payload.get("estado"))
        payload["cep"] = _strip_or_blank(payload.get("cep", ""))
        return payload


class ContatoEmpresaService(BaseService):
    repository_class = ContatoEmpresaRepository

    def listar_por_empresa(self, empresa):
        return self.get_repository().listar_por_empresa(empresa)

    def listar_ativos_por_empresa(self, empresa):
        return self.get_repository().listar_ativos_por_empresa(empresa)

    def obter_principal_por_empresa(self, empresa):
        return self.get_repository().obter_principal_por_empresa(empresa)

    @transaction.atomic
    def criar(self, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        self._desmarcar_outros_principais(
            empresa=payload.get("empresa"),
            principal=payload.get("principal", False),
        )
        contato = self.get_repository().create(**payload)
        return contato

    @transaction.atomic
    def atualizar(self, instance, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        self._desmarcar_outros_principais(
            empresa=payload.get("empresa", instance.empresa),
            principal=payload.get("principal", False),
            exclude_pk=instance.pk,
        )
        contato = self.get_repository().update(instance, **payload)
        return contato

    def _prepare_payload(self, cleaned_data):
        payload = dict(cleaned_data)
        payload["nome"] = _strip_or_blank(payload.get("nome"))
        payload["cargo"] = _strip_or_blank(payload.get("cargo", ""))
        payload["email"] = _strip_or_blank(payload.get("email", ""))
        payload["telefone"] = _strip_or_blank(payload.get("telefone", ""))
        return payload

    def _desmarcar_outros_principais(self, empresa, principal, exclude_pk=None):
        if not principal or empresa is None:
            return

        queryset = self.get_repository().filter(empresa=empresa, principal=True)
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        queryset.update(principal=False)
