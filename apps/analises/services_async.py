from __future__ import annotations

import json
import logging
from typing import Any

from django.contrib.auth import get_user_model
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
user_model = get_user_model()

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

    def listar_historico(self, analise: Analise):
        return self.get_repository().listar_historico(analise)

    def listar_historico_por_tipo(self, analise: Analise) -> dict[str, list[dict[str, Any]]]:
        historico = self.listar_historico(analise)
        grouped: dict[str, list[dict[str, Any]]] = {}

        for execucao in historico:
            anterior = self.get_repository().obter_execucao_anterior(execucao)
            grouped.setdefault(execucao.tipo_tarefa, []).append(
                {
                    "execucao": execucao,
                    "anterior": anterior,
                }
            )
        return grouped

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

    def obter_por_id_e_analise(
        self,
        *,
        analise: Analise,
        execucao_id: int,
    ) -> AnaliseExecucaoIA:
        return self.get_repository().obter_por_id_e_analise(
            analise=analise,
            execucao_id=execucao_id,
        )

    def obter_execucao_anterior(
        self,
        execucao: AnaliseExecucaoIA,
    ) -> AnaliseExecucaoIA | None:
        return self.get_repository().obter_execucao_anterior(execucao)

    def criar_solicitacao(
        self,
        *,
        analise: Analise,
        tipo_tarefa: str,
        payload_entrada: dict[str, Any],
        criado_por: user_model | None = None,
        reprocessamento_de: AnaliseExecucaoIA | None = None,
    ) -> AnaliseExecucaoIA:
        last_error: IntegrityError | None = None
        for _ in range(2):
            versao = self.get_repository().obter_proxima_versao(
                analise=analise,
                tipo_tarefa=tipo_tarefa,
            )
            try:
                return self.get_repository().create(
                    analise=analise,
                    tipo_tarefa=tipo_tarefa,
                    status=StatusExecucaoIAChoices.PENDENTE,
                    versao=versao,
                    payload_entrada=payload_entrada,
                    resultado_payload={},
                    resultado_bruto="",
                    mensagem_erro="",
                    erro_detalhe_interno="",
                    solicitada_em=timezone.now(),
                    iniciada_em=None,
                    concluida_em=None,
                    identificador_task="",
                    modelo_utilizado="",
                    response_id="",
                    tentativas=0,
                    criado_por=criado_por,
                    reprocessamento_de=reprocessamento_de,
                )
            except IntegrityError as exc:
                last_error = exc
                logger.warning(
                    "Conflito ao criar versao de execucao IA; tentando novamente",
                    extra={
                        "analise_id": analise.pk,
                        "tipo_tarefa": tipo_tarefa,
                    },
                )
        if last_error is not None:
            raise last_error
        raise IntegrityError("Nao foi possivel criar a execucao de IA.")

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
            erro_detalhe_interno="",
            tentativas=execucao.tentativas + 1,
        )

    def marcar_concluida(
        self,
        execucao: AnaliseExecucaoIA,
        *,
        resultado_payload: dict[str, Any],
        resultado_bruto: str,
        modelo_utilizado: str,
        response_id: str | None,
    ) -> AnaliseExecucaoIA:
        return self.get_repository().update(
            execucao,
            status=StatusExecucaoIAChoices.CONCLUIDO,
            resultado_payload=resultado_payload,
            resultado_bruto=resultado_bruto,
            modelo_utilizado=modelo_utilizado,
            response_id=response_id or "",
            mensagem_erro="",
            erro_detalhe_interno="",
            concluida_em=timezone.now(),
        )

    def marcar_falha(
        self,
        execucao: AnaliseExecucaoIA,
        *,
        mensagem_erro: str,
        erro_detalhe_interno: str = "",
    ) -> AnaliseExecucaoIA:
        return self.get_repository().update(
            execucao,
            status=StatusExecucaoIAChoices.FALHOU,
            mensagem_erro=mensagem_erro,
            erro_detalhe_interno=erro_detalhe_interno,
            concluida_em=timezone.now(),
        )

    def reagendar_retry(
        self,
        execucao: AnaliseExecucaoIA,
        *,
        task_handler,
        erro_detalhe_interno: str = "",
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
            erro_detalhe_interno=erro_detalhe_interno,
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

    def preparar_comparacao(
        self,
        *,
        execucao_base: AnaliseExecucaoIA,
        execucao_comparada: AnaliseExecucaoIA,
    ) -> dict[str, Any]:
        if execucao_base.analise_id != execucao_comparada.analise_id:
            raise ValueError("As execucoes precisam pertencer a mesma analise.")
        if execucao_base.tipo_tarefa != execucao_comparada.tipo_tarefa:
            raise ValueError("As execucoes precisam ser do mesmo tipo de tarefa.")

        payload_base = self._flatten_payload(execucao_base.resultado_payload or {})
        payload_comparado = self._flatten_payload(execucao_comparada.resultado_payload or {})
        campos = sorted(set(payload_base) | set(payload_comparado))

        campos_alterados: list[dict[str, str]] = []
        campos_adicionados: list[dict[str, str]] = []
        campos_removidos: list[dict[str, str]] = []

        for campo in campos:
            valor_base = payload_base.get(campo)
            valor_comparado = payload_comparado.get(campo)
            if valor_base == valor_comparado:
                continue
            if valor_base is None:
                campos_adicionados.append(
                    {"campo": campo, "depois": valor_comparado or "-"}
                )
                continue
            if valor_comparado is None:
                campos_removidos.append(
                    {"campo": campo, "antes": valor_base or "-"}
                )
                continue
            campos_alterados.append(
                {
                    "campo": campo,
                    "antes": valor_base or "-",
                    "depois": valor_comparado or "-",
                }
            )

        mudancas_metadados = []
        for label, before, after in (
            ("Status", execucao_base.get_status_display(), execucao_comparada.get_status_display()),
            ("Modelo", execucao_base.modelo_utilizado or "-", execucao_comparada.modelo_utilizado or "-"),
            ("Tentativas", str(execucao_base.tentativas), str(execucao_comparada.tentativas)),
            ("Task ID", execucao_base.identificador_task or "-", execucao_comparada.identificador_task or "-"),
        ):
            if before != after:
                mudancas_metadados.append(
                    {"label": label, "antes": before, "depois": after}
                )

        return {
            "tipo_tarefa": execucao_base.tipo_tarefa,
            "execucao_base": execucao_base,
            "execucao_comparada": execucao_comparada,
            "mudancas_metadados": mudancas_metadados,
            "campos_alterados": campos_alterados,
            "campos_adicionados": campos_adicionados,
            "campos_removidos": campos_removidos,
            "houve_mudanca_resultado": bool(
                campos_alterados or campos_adicionados or campos_removidos
            ),
        }

    def _flatten_payload(
        self,
        payload: dict[str, Any],
        *,
        prefix: str = "",
    ) -> dict[str, str]:
        flattened: dict[str, str] = {}
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flattened.update(self._flatten_payload(value, prefix=path))
                continue
            flattened[path] = self._format_value(value)
        return flattened

    def _format_value(self, value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=True, sort_keys=True)
        return str(value)


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
        criado_por: user_model | None = None,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
            payload_entrada={"texto_documento": self._require_text(texto_documento)},
            criado_por=criado_por,
        )

    def solicitar_extracao_documento(
        self,
        *,
        analise: Analise,
        texto_documento: str,
        campos_alvo: list[str] | tuple[str, ...] | None = None,
        criado_por: user_model | None = None,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.EXTRACAO,
            payload_entrada={
                "texto_documento": self._require_text(texto_documento),
                "campos_alvo": [str(item) for item in (campos_alvo or []) if str(item)],
            },
            criado_por=criado_por,
        )

    def solicitar_parecer_tecnico(
        self,
        *,
        analise: Analise,
        texto_documento: str,
        criado_por: user_model | None = None,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
            payload_entrada={"texto_documento": self._require_text(texto_documento)},
            criado_por=criado_por,
        )

    def solicitar_comparacao_documento(
        self,
        *,
        analise: Analise,
        texto_documento: str,
        criado_por: user_model | None = None,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=analise,
            tipo_tarefa=TipoTarefaExecucaoIAChoices.COMPARACAO,
            payload_entrada={"texto_documento": self._require_text(texto_documento)},
            criado_por=criado_por,
        )

    def solicitar_checklist(
        self,
        *,
        analise: Analise,
        texto_documento: str | None = None,
        contexto_comparacao: dict[str, Any] | None = None,
        criado_por: user_model | None = None,
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
            criado_por=criado_por,
        )

    def reprocessar_execucao(
        self,
        *,
        execucao: AnaliseExecucaoIA,
        criado_por: user_model | None = None,
    ) -> tuple[AnaliseExecucaoIA, bool]:
        return self._solicitar_execucao(
            analise=execucao.analise,
            tipo_tarefa=execucao.tipo_tarefa,
            payload_entrada=execucao.payload_entrada,
            criado_por=criado_por,
            reprocessamento_de=execucao,
        )

    def _solicitar_execucao(
        self,
        *,
        analise: Analise,
        tipo_tarefa: str,
        payload_entrada: dict[str, Any],
        criado_por: user_model | None = None,
        reprocessamento_de: AnaliseExecucaoIA | None = None,
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
                    criado_por=criado_por,
                    reprocessamento_de=reprocessamento_de,
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
                erro_detalhe_interno="Falha ao enfileirar execucao de IA.",
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
