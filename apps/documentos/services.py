from apps.core.services import BaseService

from .choices import StatusDocumentoChoices
from .repositories import DocumentoRepository


def _strip_or_blank(value):
    if isinstance(value, str):
        return value.strip()
    return value


class DocumentoService(BaseService):
    repository_class = DocumentoRepository

    def listar(self, filtros=None):
        return self.get_repository().listar_com_filtros(filtros=filtros)

    def obter(self, pk):
        return self.get_repository().obter_por_id(pk)

    def listar_por_licitacao(self, licitacao):
        return self.get_repository().listar_por_licitacao(licitacao)

    def listar_pendentes(self):
        return self.get_repository().listar_pendentes()

    def listar_validados(self):
        return self.get_repository().listar_validados()

    def contar_por_status(self):
        return self.get_repository().contar_por_status()

    def total_por_licitacao(self, licitacao):
        return self.get_repository().total_por_licitacao(licitacao)

    def criar(self, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().create(**payload)

    def atualizar(self, instance, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().update(instance, **payload)

    def marcar_como_pendente(self, instance):
        return self._update_status(instance, StatusDocumentoChoices.PENDENTE)

    def marcar_como_enviado(self, instance):
        return self._update_status(instance, StatusDocumentoChoices.ENVIADO)

    def marcar_como_validado(self, instance):
        return self._update_status(instance, StatusDocumentoChoices.VALIDADO)

    def marcar_como_rejeitado(self, instance):
        return self._update_status(instance, StatusDocumentoChoices.REJEITADO)

    def _prepare_payload(self, cleaned_data):
        payload = dict(cleaned_data)
        payload["nome"] = _strip_or_blank(payload.get("nome"))
        payload["observacoes"] = _strip_or_blank(payload.get("observacoes", ""))
        return payload

    def _update_status(self, instance, status):
        return self.get_repository().update(instance, status=status)
