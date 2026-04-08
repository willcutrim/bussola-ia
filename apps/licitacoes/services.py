from apps.core.services import BaseService

from .choices import SituacaoChoices
from .repositories import LicitacaoRepository


def _strip_or_blank(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _strip_or_none(value):
    if isinstance(value, str):
        stripped_value = value.strip()
        return stripped_value or None
    return value


class LicitacaoService(BaseService):
    repository_class = LicitacaoRepository

    def listar(self, filtros=None):
        return self.get_repository().listar_com_filtros(filtros=filtros)

    def obter(self, pk):
        return self.get_repository().obter_por_id(pk)

    def listar_ativas(self):
        return self.get_repository().listar_ativas()

    def listar_por_empresa(self, empresa):
        return self.get_repository().listar_por_empresa(empresa)

    def obter_por_numero(self, numero):
        normalized_numero = _strip_or_none(numero)
        if not normalized_numero:
            return None
        return self.get_repository().obter_por_numero(normalized_numero)

    def criar(self, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().create(**payload)

    def atualizar(self, instance, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().update(instance, **payload)

    def listar_em_andamento(self):
        return self.get_repository().listar_em_andamento()

    def listar_encerradas(self):
        return self.get_repository().listar_encerradas()

    def contar_por_situacao(self):
        return self.get_repository().contar_por_situacao()

    def total_ativas(self):
        return self.get_repository().total_ativas()

    def marcar_como_em_analise(self, instance):
        return self._update_situacao(instance, SituacaoChoices.EM_ANALISE)

    def marcar_como_em_andamento(self, instance):
        return self._update_situacao(instance, SituacaoChoices.EM_ANDAMENTO)

    def marcar_como_encerrada(self, instance):
        return self._update_situacao(instance, SituacaoChoices.ENCERRADA)

    def marcar_como_cancelada(self, instance):
        return self._update_situacao(instance, SituacaoChoices.CANCELADA)

    def _prepare_payload(self, cleaned_data):
        payload = dict(cleaned_data)
        payload["numero"] = _strip_or_blank(payload.get("numero"))
        payload["objeto"] = _strip_or_blank(payload.get("objeto"))
        payload["orgao"] = _strip_or_blank(payload.get("orgao"))
        payload["link_externo"] = _strip_or_blank(payload.get("link_externo", ""))
        payload["observacoes"] = _strip_or_blank(payload.get("observacoes", ""))
        return payload

    def _update_situacao(self, instance, situacao):
        return self.get_repository().update(instance, situacao=situacao)
