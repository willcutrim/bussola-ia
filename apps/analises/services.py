from datetime import timedelta

from django.utils import timezone

from apps.core.services import BaseService

from .choices import (
    PrioridadeAnaliseChoices,
    StatusAnaliseChoices,
    StatusExecucaoIAChoices,
    TipoTarefaExecucaoIAChoices,
)
from .repositories import AnaliseExecucaoIARepository, AnaliseRepository


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


class DashboardIAService:
    def __init__(
        self,
        *,
        execucao_repository=None,
        analise_repository=None,
    ):
        self.execucao_repository = execucao_repository or AnaliseExecucaoIARepository()
        self.analise_repository = analise_repository or AnaliseRepository()

    def obter_dashboard(self):
        total_execucoes = self.execucao_repository.total_execucoes()
        total_analises_com_uso_ia = self.execucao_repository.total_analises_com_uso_ia()
        total_reprocessamentos = self.execucao_repository.total_reprocessamentos()
        totais_status = self._normalizar_distribuicao(
            agregados=self.execucao_repository.total_por_status(),
            campo="status",
            choices=StatusExecucaoIAChoices,
            tone_map={
                StatusExecucaoIAChoices.PENDENTE: "warning",
                StatusExecucaoIAChoices.EM_PROCESSAMENTO: "info",
                StatusExecucaoIAChoices.CONCLUIDO: "success",
                StatusExecucaoIAChoices.FALHOU: "danger",
            },
        )
        totais_tarefas = self._normalizar_distribuicao(
            agregados=self.execucao_repository.total_por_tipo_tarefa(),
            campo="tipo_tarefa",
            choices=TipoTarefaExecucaoIAChoices,
            tone_map={
                TipoTarefaExecucaoIAChoices.RESUMO: "primary",
                TipoTarefaExecucaoIAChoices.EXTRACAO: "info",
                TipoTarefaExecucaoIAChoices.PARECER: "success",
                TipoTarefaExecucaoIAChoices.COMPARACAO: "warning",
                TipoTarefaExecucaoIAChoices.CHECKLIST: "info",
            },
        )
        total_concluidas = self._obter_total_distribuicao(
            totais_status, StatusExecucaoIAChoices.CONCLUIDO
        )
        total_falhas = self._obter_total_distribuicao(
            totais_status, StatusExecucaoIAChoices.FALHOU
        )
        total_em_processamento = self._obter_total_distribuicao(
            totais_status,
            StatusExecucaoIAChoices.EM_PROCESSAMENTO,
        )
        total_pendentes = self._obter_total_distribuicao(
            totais_status,
            StatusExecucaoIAChoices.PENDENTE,
        )
        tempo_medio = self.execucao_repository.tempo_medio_processamento()
        execucoes_recentes = list(self.execucao_repository.listar_execucoes_recentes())
        falhas_recentes = list(self.execucao_repository.listar_falhas_recentes())
        itens_atencao = self._montar_itens_atencao()

        return {
            "resumo": {
                "total_execucoes": total_execucoes,
                "total_analises_com_uso_ia": total_analises_com_uso_ia,
                "total_reprocessamentos": total_reprocessamentos,
                "total_concluidas": total_concluidas,
                "total_falhas": total_falhas,
                "total_em_processamento": total_em_processamento,
                "total_pendentes": total_pendentes,
                "tempo_medio_processamento": tempo_medio,
                "tempo_medio_processamento_label": self._formatar_duracao(tempo_medio),
            },
            "kpis": [
                {
                    "title": "Execucoes de IA",
                    "value": total_execucoes,
                    "helper": f"{total_analises_com_uso_ia} analises com uso registrado",
                    "tone": "primary",
                    "icon": "chart",
                },
                {
                    "title": "Concluidas",
                    "value": total_concluidas,
                    "helper": f"{self._percentual(total_concluidas, total_execucoes)}% do volume total",
                    "tone": "success",
                    "icon": "shield",
                },
                {
                    "title": "Falhas",
                    "value": total_falhas,
                    "helper": f"{self._percentual(total_falhas, total_execucoes)}% precisam de revisao",
                    "tone": "warning" if total_falhas else "info",
                    "icon": "pulse",
                },
                {
                    "title": "Em processamento",
                    "value": total_em_processamento,
                    "helper": f"{total_pendentes} pendentes na fila e media de {self._formatar_duracao_curta(tempo_medio)}",
                    "tone": "info",
                    "icon": "search",
                },
            ],
            "status_distribution": totais_status,
            "task_distribution": totais_tarefas,
            "execucoes_recentes": execucoes_recentes,
            "falhas_recentes": falhas_recentes,
            "itens_atencao": itens_atencao,
        }

    def _montar_itens_atencao(self):
        itens = []
        for execucao in self.execucao_repository.listar_processando_ha_tempo():
            itens.append(
                {
                    "tipo": "processamento_longo",
                    "tone": "warning",
                    "title": "Execucao em processamento ha mais tempo que o esperado",
                    "description": (
                        f"{execucao.get_tipo_tarefa_display()} da analise '{execucao.analise.titulo}' "
                        f"segue em processamento desde {timezone.localtime(execucao.iniciada_em).strftime('%d/%m/%Y %H:%M')}."
                    ),
                    "analise": execucao.analise,
                    "execucao": execucao,
                }
            )

        for item in self.execucao_repository.listar_analises_com_multiplas_falhas_recentes():
            itens.append(
                {
                    "tipo": "falhas_recentes",
                    "tone": "danger",
                    "title": "Analise com falhas recorrentes na ultima janela operacional",
                    "description": (
                        f"{item['analise__titulo']} ({item['analise__licitacao__numero']}) acumulou "
                        f"{item['total_falhas']} falhas recentes de IA."
                    ),
                    "analise_id": item["analise_id"],
                }
            )

        for analise in self.analise_repository.listar_criticas_sem_parecer_concluido():
            itens.append(
                {
                    "tipo": "critica_sem_parecer",
                    "tone": "warning",
                    "title": "Analise critica sem parecer concluido",
                    "description": (
                        f"A analise '{analise.titulo}' segue marcada como {PrioridadeAnaliseChoices.CRITICA.label} "
                        "sem uma execucao concluida de parecer tecnico."
                    ),
                    "analise": analise,
                }
            )

        return itens[:10]

    def _normalizar_distribuicao(self, *, agregados, campo, choices, tone_map):
        totais = {item[campo]: item["total"] for item in agregados}
        total_geral = sum(totais.values()) or 1
        distribuicao = []
        for value, label in choices.choices:
            total = totais.get(value, 0)
            distribuicao.append(
                {
                    "value": value,
                    "label": label,
                    "total": total,
                    "percentual": round((total / total_geral) * 100) if total else 0,
                    "tone": tone_map.get(value, "primary"),
                }
            )
        return distribuicao

    def _obter_total_distribuicao(self, distribuicao, value):
        for item in distribuicao:
            if item["value"] == value:
                return item["total"]
        return 0

    def _percentual(self, total, base):
        if not base:
            return 0
        return round((total / base) * 100)

    def _formatar_duracao(self, duracao):
        if duracao is None:
            return "Sem amostra suficiente"

        total_segundos = int(duracao.total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos, _ = divmod(resto, 60)
        if horas:
            return f"{horas}h {minutos}min"
        return f"{max(minutos, 1)} min"

    def _formatar_duracao_curta(self, duracao):
        if duracao is None:
            return "sem media"
        total_segundos = int(duracao.total_seconds())
        if total_segundos < 60:
            return "1 min"
        if duracao >= timedelta(hours=1):
            horas, resto = divmod(total_segundos, 3600)
            minutos, _ = divmod(resto, 60)
            return f"{horas}h {minutos}min"
        minutos = total_segundos // 60
        return f"{max(minutos, 1)} min"
