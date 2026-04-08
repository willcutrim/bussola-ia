from django.utils import timezone

from apps.core.services import BaseService

from .choices import StatusAnaliseChoices
from .repositories import AnaliseRepository


def _strip_or_blank(value):
    if isinstance(value, str):
        return value.strip()
    return value


class AnaliseService(BaseService):
    repository_class = AnaliseRepository

    def listar(self, filtros=None):
        return self.get_repository().listar_com_filtros(filtros=filtros)

    def obter(self, pk):
        return self.get_repository().obter_por_id(pk)

    def listar_por_licitacao(self, licitacao):
        return self.get_repository().listar_por_licitacao(licitacao)

    def listar_por_documento(self, documento):
        return self.get_repository().listar_por_documento(documento)

    def listar_por_responsavel(self, responsavel):
        return self.get_repository().listar_por_responsavel(responsavel)

    def listar_pendentes(self):
        return self.get_repository().listar_pendentes()

    def listar_em_andamento(self):
        return self.get_repository().listar_em_andamento()

    def listar_concluidas(self):
        return self.get_repository().listar_concluidas()

    def contar_por_status(self):
        return self.get_repository().contar_por_status()

    def contar_por_prioridade(self):
        return self.get_repository().contar_por_prioridade()

    def total_por_licitacao(self, licitacao):
        return self.get_repository().total_por_licitacao(licitacao)

    def criar(self, cleaned_data):
        payload = self._prepare_payload(cleaned_data)
        return self.get_repository().create(**payload)

    def atualizar(self, instance, cleaned_data):
        payload = self._prepare_payload(cleaned_data, instance=instance)
        return self.get_repository().update(instance, **payload)

    def marcar_como_pendente(self, instance):
        return self._update_status(instance, StatusAnaliseChoices.PENDENTE)

    def marcar_como_em_andamento(self, instance):
        return self._update_status(instance, StatusAnaliseChoices.EM_ANDAMENTO)

    def marcar_como_concluida(self, instance):
        return self._update_status(instance, StatusAnaliseChoices.CONCLUIDA)

    def marcar_como_rejeitada(self, instance):
        return self._update_status(instance, StatusAnaliseChoices.REJEITADA)

    def _prepare_payload(self, cleaned_data, instance=None):
        payload = dict(cleaned_data)
        payload["titulo"] = _strip_or_blank(payload.get("titulo"))
        payload["descricao"] = _strip_or_blank(payload.get("descricao", ""))
        payload["parecer"] = _strip_or_blank(payload.get("parecer", ""))
        self._ajustar_conclusao_por_status(payload, instance=instance)
        return payload

    def _ajustar_conclusao_por_status(self, payload, instance=None):
        status = payload.get("status")
        if status == StatusAnaliseChoices.CONCLUIDA:
            payload["concluida_em"] = payload.get("concluida_em") or getattr(
                instance, "concluida_em", None
            ) or timezone.now()
            return

        if "status" in payload:
            payload["concluida_em"] = None

    def _update_status(self, instance, status):
        concluida_em = instance.concluida_em
        if status == StatusAnaliseChoices.CONCLUIDA:
            concluida_em = concluida_em or timezone.now()
        else:
            concluida_em = None

        return self.get_repository().update(
            instance,
            status=status,
            concluida_em=concluida_em,
        )
