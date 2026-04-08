from django.core.exceptions import ImproperlyConfigured

from .repositories import DashboardRepository


class BaseService:
    repository_class = None

    def __init__(self, repository=None):
        self.repository = repository

    def get_repository_class(self):
        if self.repository_class is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define repository_class."
            )
        return self.repository_class

    def get_repository(self):
        if self.repository is not None:
            return self.repository

        repository_class = self.get_repository_class()
        self.repository = repository_class()
        return self.repository

    def list(self):
        return self.get_repository().list()

    def get_by_id(self, pk):
        return self.get_repository().get_by_id(pk)

    def create(self, **kwargs):
        return self.get_repository().create(**kwargs)

    def update(self, instance, **kwargs):
        return self.get_repository().update(instance, **kwargs)

    def delete(self, instance):
        instance.delete()
        return instance


class DashboardService:
    repository_class = DashboardRepository

    def __init__(self, repository=None):
        self.repository = repository

    def get_repository(self):
        if self.repository is None:
            self.repository = self.repository_class()
        return self.repository

    def obter_resumo(self):
        repository = self.get_repository()
        licitacoes_por_situacao = repository.distribuir_licitacoes_por_situacao()
        total_licitacoes = repository.contar_licitacoes()
        total_em_analise = sum(
            item["total"]
            for item in licitacoes_por_situacao
            if item["situacao"] == "em_analise"
        )

        return {
            "total_empresas": repository.contar_empresas(),
            "total_empresas_ativas": repository.contar_empresas_ativas(),
            "total_licitacoes": total_licitacoes,
            "total_licitacoes_ativas": repository.contar_licitacoes_ativas(),
            "total_usuarios": repository.contar_usuarios(),
            "valor_estimado_total": repository.somar_valor_estimado(),
            "total_em_analise": total_em_analise,
            "licitacoes_recentes": repository.listar_licitacoes_recentes(),
            "empresas_recentes": repository.listar_empresas_recentes(),
            "licitacoes_por_situacao": licitacoes_por_situacao,
        }
