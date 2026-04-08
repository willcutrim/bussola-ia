from __future__ import annotations

import logging
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.services import BaseService
from config.tasks import (
    ANALISES_AI_MAX_TENTATIVAS,
    calcular_proximo_retry,
)

from .choices import StatusExecucaoIAChoices, TipoTarefaExecucaoIAChoices
from .models import Analise, AnaliseExecucaoIA
from .repositories import AnaliseExecucaoIARepository


logger = logging.getLogger(__name__)

ERRO_PROCESSAMENTO_IA = (
    "Nao foi possivel concluir o processamento de IA. Tente novamente."
)
ERRO_TRANSITORIO_IA = (
    "O processamento de IA encontrou uma indisponibilidade temporaria."
)


class AnaliseExecucaoIAService(BaseService):
    repository_class = AnaliseExecucaoIARepository

    def obter(self, pk: int) -> AnaliseExecucaoIA:
        return self.get_repository().obter_por_id(pk)

    def listar_por_analise(self, analise: Analise):
        return self.get_repository().listar_por_analise(analise)

    def listar_ultimas_por_tipo(self, analise: Analise):
        return self.get_repository().listar_ultimas_por_tipo(analise)

    def obter_ultima_por_tipo(
        self, analise: Analise, tipo_tarefa: str
    ) -> AnaliseExecucaoIA | None:
        return self.listar_ultimas_por_tipo(analise).get(tipo_tarefa)

    def obter_ativa_por_analise_e_tipo(
        self, analise: Analise, tipo_tarefa: str
    ) -> AnaliseExecucaoIA | None:
        return self.get_repository().obter_ativa_por_analise_e_tipo(analise, tipo_tarefa)

    def criar_solicitacao(
        self,
        *,
        analise: Analise,
        tipo_tarefa: str,
        payload_entrada: dict[str, Any],
    ) -> AnaliseExecucaoIA:
        return self.get_repository().create(
            analise=analise,
            tipo_tarefa=tipo_tarefa,
            status=StatusExecucaoIAChoices.PENDENTE,
            payload_entrada=payload_entrada,
            resultado_payload={},
            mensagem_erro="",
            solicitada_em=timezone.now(),
            iniciada_em=None,
            concluida_em=None,
            identificador_task="",
            modelo_utilizado="",
            response_id="",
            tentativas=0,
        )

    def atualizar_identificador_task(
        self,
        execucao: AnaliseExecucaoIA,
        *,
        identificador_task: str,
    ) -> AnaliseExecucaoIA:
        return self.get_repository().update(
            execucao,
            identificador_task=identificador_task,
        )

    def marcar_em_processamento(
        self,
        execucao: AnaliseExecucaoIA,
    ) -> AnaliseExecucaoIA:
        return self.get_repository().update(
            execucao,
            status=StatusExecucaoIAChoices.EM_PROCESSAMENTO,
            iniciada_em=execucao.iniciada_em or timezone.now(),
            concluida_em=None,
            mensagem_erro="",
            tentativas=execucao.tentativas + 1,
        )

    def marcar_concluida(
        self,
        execucao: AnaliseExecucaoIA,
        *,
        resultado_payload: dict[str, Any],
        modelo_utilizado: str,
        response_id: str | None,
    ) -> AnaliseExecucaoIA:
        return self.get_repository().update(
            execucao,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            resultado_payload=resultado_payload,
            modelo_utilizado=modelo_utilizado,
            response_id=response_id or "",
            mensagem_erro="",
            concluida_em=timezone.now(),
        )

    def marcar_falha(
        self,
        execucao: AnaliseExecucaoIA,
        *,
        mensagem_erro: str,
    ) -> AnaliseExecucaoIA:
        return self.get_repository().update(
            execucao,
            status=StatusExecucaoIAChoices.FALHOU,
            mensagem_erro=mensagem_erro,
            concluida_em=timezone.now(),
        )

    def reagendar_retry(
        self,
        execucao: AnaliseExecucaoIA,
        *,
        task_handler,
    ) -> AnaliseExecucaoIA | None:
        backend = task_handler.get_backend()
        if not backend.supports_defer:
            return None

        run_after = calcular_proximo_retry(execucao.tentativas)
        if run_after is None or execucao.tentativas >= ANALISES_AI_MAX_TENTATIVAS:
            return None

        execucao = self.get_repository().update(
            execucao,
            status=StatusExecucaoIAChoices.PENDENTE,
            mensagem_erro="",
            concluida_em=None,
        )
        task_result = task_handler.using(run_after=run_after).enqueue(
            execucao_id=execucao.pk
        )
        logger.info(
            "Execucao IA reagendada",
            extra={
                "execucao_id": execucao.pk,
                "analise_id": execucao.analise_id,
                "tipo_tarefa": execucao.tipo_tarefa,
                "tentativa": execucao.tentativas,
                "identificador_task": task_result.id,
                "run_after": run_after.isoformat(),
            },
        )
        return self.atualizar_identificador_task(
            execucao,
            identificador_task=task_result.id,
        )


class AnaliseAsyncService:
    def __init__(
        self,
        *,
        execucao_service: AnaliseExecucaoIAService | None = None,
    ) -> None:
        self.execucao_service = execucao_service or AnaliseExecucaoIAService()

    def solicitar_resumo_documento(
        self,
        *,
        analise: Analise,
        texto_documento: str,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            payload_entrada={"texto_documento": self._require_text(texto_documento)},
        )

    def solicitar_extracao_documento(
        self,
        *,
        analise: Analise,
        texto_documento: str,
        campos_alvo: list[str] | tuple[str, ...] | None = None,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.EXTRACAO,
            payload_entrada={
                "texto_documento": self._require_text(texto_documento),
                "campos_alvo": [str(item) for item in (campos_alvo or []) if str(item)],
            },
        )

    def solicitar_parecer_tecnico(
        self,
        *,
        analise: Analise,
        texto_documento: str,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            payload_entrada={"texto_documento": self._require_text(texto_documento)},
        )

    def solicitar_comparacao_documento(
        self,
        *,
        analise: Analise,
        texto_documento: str,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.COMPARACAO,
            payload_entrada={"texto_documento": self._require_text(texto_documento)},
        )

    def solicitar_checklist(
        self,
        *,
        analise: Analise,
        texto_documento: str | None = None,
        contexto_comparacao: dict[str, Any] | None = None,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        texto_limpo = ""
        if isinstance(texto_documento, str):
            texto_limpo = texto_documento.strip()

        payload_entrada = {
            "texto_documento": texto_limpo,
            "contexto_comparacao": contexto_comparacao or {},
        }
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.CHECKLIST,
            payload_entrada=payload_entrada,
        )

    def _solicitar_execucao(
        self,
        *,
        analise: Analise,
        tipo_tarefa: str,
        payload_entrada: dict[str, Any],
    ) -> tuple[AnaliseExecucaoIA, bool]:
        with transaction.atomic():
            execucao_ativa = self.execucao_service.obter_ativa_por_analise_e_tipo(
                analise,
                tipo_tarefa,
            )
            if execucao_ativa is not None:
                return execucao_ativa, False

            try:
                execucao = self.execucao_service.criar_solicitacao(
                    analise=analise,
                    tipo_tarefa=tipo_tarefa,
                    payload_entrada=payload_entrada,
                )
            except IntegrityError:
                execucao_existente = self.execucao_service.obter_ativa_por_analise_e_tipo(
                    analise,
                    tipo_tarefa,
                )
                if execucao_existente is None:
                    raise
                return execucao_existente, False

            task_handler = self._get_task_handler(tipo_tarefa)
            transaction.on_commit(
                lambda execucao_id=execucao.pk, task_handler=task_handler: self._enfileirar_execucao(
                    execucao_id=execucao_id,
                    task_handler=task_handler,
                )
            )

        execucao.refresh_from_db()
        return execucao, True

    def _enfileirar_execucao(self, *, execucao_id: int, task_handler) -> None:
        execucao = self.execucao_service.obter(execucao_id)
        try:
            task_result = task_handler.enqueue(execucao_id=execucao_id)
        except Exception:
            logger.exception(
                "Falha ao enfileirar execucao de IA",
                extra={
                    "execucao_id": execucao.pk,
                    "analise_id": execucao.analise_id,
                    "tipo_tarefa": execucao.tipo_tarefa,
                },
            )
            self.execucao_service.marcar_falha(
                execucao,
                mensagem_erro=ERRO_PROCESSAMENTO_IA,
            )
            return

        self.execucao_service.atualizar_identificador_task(
            execucao,
            identificador_task=task_result.id,
        )
        logger.info(
            "Execucao IA enfileirada",
            extra={
                "execucao_id": execucao.pk,
                "analise_id": execucao.analise_id,
                "tipo_tarefa": execucao.tipo_tarefa,
                "identificador_task": task_result.id,
                "backend": task_result.backend,
            },
        )

    def _get_task_handler(self, tipo_tarefa: str):
        from . import tasks

        task_map = {
            TipoTarefaExecucaoIAChoices.RESUMO: tasks.gerar_resumo_documento_task,
            TipoTarefaExecucaoIAChoices.EXTRACAO: tasks.extrair_dados_documento_task,
            TipoTarefaExecucaoIAChoices.PARECER: tasks.gerar_parecer_tecnico_task,
            TipoTarefaExecucaoIAChoices.COMPARACAO: tasks.comparar_documento_com_licitacao_task,
            TipoTarefaExecucaoIAChoices.CHECKLIST: tasks.gerar_checklist_task,
        }
        try:
            return task_map[tipo_tarefa]
        except KeyError as exc:
            raise ValueError(f"Tipo de tarefa de IA nao suportado: {tipo_tarefa}.") from exc

    def _require_text(self, texto_documento: str) -> str:
        if not isinstance(texto_documento, str) or not texto_documento.strip():
            raise ValueError(
                "O texto do documento e obrigatorio para executar esta solicitacao."
            )
        return texto_documento.strip()


__all__ = [
    "AnaliseAsyncService",
    "AnaliseExecucaoIAService",
    "ERRO_PROCESSAMENTO_IA",
    "ERRO_TRANSITORIO_IA",
]
