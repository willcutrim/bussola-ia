from __future__ import annotations

import logging

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.tasks import task

from apps.analises.choices import TipoTarefaExecucaoIAChoices
from apps.analises.integrations import AIPermanentError, AITransientError
from apps.analises.services_ai import AnaliseAIService
from apps.analises.services_async import (
    AnaliseExecucaoIAService,
    ERRO_PROCESSAMENTO_IA,
    ERRO_TRANSITORIO_IA,
)
from config.tasks import ANALISES_AI_QUEUE_NAME


logger = logging.getLogger(__name__)


@task(queue_name=ANALISES_AI_QUEUE_NAME, takes_context=True)
def gerar_resumo_documento_task(context, execucao_id: int):
    return _executar_execucao_ia(
        context=context,
        execucao_id=execucao_id,
        tipo_tarefa=TipoTarefaExecucaoIAChoices.RESUMO,
        task_handler=gerar_resumo_documento_task,
    )


@task(queue_name=ANALISES_AI_QUEUE_NAME, takes_context=True)
def extrair_dados_documento_task(context, execucao_id: int):
    return _executar_execucao_ia(
        context=context,
        execucao_id=execucao_id,
        tipo_tarefa=TipoTarefaExecucaoIAChoices.EXTRACAO,
        task_handler=extrair_dados_documento_task,
    )


@task(queue_name=ANALISES_AI_QUEUE_NAME, takes_context=True)
def gerar_parecer_tecnico_task(context, execucao_id: int):
    return _executar_execucao_ia(
        context=context,
        execucao_id=execucao_id,
        tipo_tarefa=TipoTarefaExecucaoIAChoices.PARECER,
        task_handler=gerar_parecer_tecnico_task,
    )


@task(queue_name=ANALISES_AI_QUEUE_NAME, takes_context=True)
def comparar_documento_com_licitacao_task(context, execucao_id: int):
    return _executar_execucao_ia(
        context=context,
        execucao_id=execucao_id,
        tipo_tarefa=TipoTarefaExecucaoIAChoices.COMPARACAO,
        task_handler=comparar_documento_com_licitacao_task,
    )


@task(queue_name=ANALISES_AI_QUEUE_NAME, takes_context=True)
def gerar_checklist_task(context, execucao_id: int):
    return _executar_execucao_ia(
        context=context,
        execucao_id=execucao_id,
        tipo_tarefa=TipoTarefaExecucaoIAChoices.CHECKLIST,
        task_handler=gerar_checklist_task,
    )


def _executar_execucao_ia(*, context, execucao_id: int, tipo_tarefa: str, task_handler):
    execucao_service = AnaliseExecucaoIAService()
    ai_service = AnaliseAIService()
    execucao = execucao_service.obter(execucao_id)

    if execucao.tipo_tarefa != tipo_tarefa:
        raise ValueError(
            f"Execucao {execucao_id} nao corresponde ao tipo esperado {tipo_tarefa}."
        )

    execucao = execucao_service.marcar_em_processamento(execucao)
    log_context = {
        "execucao_id": execucao.pk,
        "analise_id": execucao.analise_id,
        "tipo_tarefa": execucao.tipo_tarefa,
        "tentativa": execucao.tentativas,
        "identificador_task": execucao.identificador_task,
        "task_result_id": context.task_result.id,
        "task_attempt": context.attempt,
    }
    logger.info("Execucao IA iniciada", extra=log_context)

    try:
        resultado = _processar_execucao(ai_service=ai_service, execucao=execucao)
    except AITransientError as exc:
        logger.warning("Falha transitoria em execucao IA", exc_info=True, extra=log_context)
        execucao_retry = execucao_service.reagendar_retry(
            execucao,
            task_handler=task_handler,
            erro_detalhe_interno=_build_internal_error_detail(exc),
        )
        if execucao_retry is not None:
            return {
                "execucao_id": execucao.pk,
                "status": execucao_retry.status,
                "retry_agendado": True,
            }
        execucao_service.marcar_falha(
            execucao,
            mensagem_erro=ERRO_TRANSITORIO_IA,
            erro_detalhe_interno=_build_internal_error_detail(exc),
        )
        raise
    except (
        AIPermanentError,
        ImproperlyConfigured,
        ValidationError,
        ValueError,
    ) as exc:
        logger.exception("Falha permanente em execucao IA", extra=log_context)
        execucao_service.marcar_falha(
            execucao,
            mensagem_erro=ERRO_PROCESSAMENTO_IA,
            erro_detalhe_interno=_build_internal_error_detail(exc),
        )
        raise
    except Exception as exc:
        logger.exception("Falha inesperada em execucao IA", extra=log_context)
        execucao_service.marcar_falha(
            execucao,
            mensagem_erro=ERRO_PROCESSAMENTO_IA,
            erro_detalhe_interno=_build_internal_error_detail(exc),
        )
        raise

    execucao_service.marcar_concluida(
        execucao,
        resultado_payload=resultado.payload,
        resultado_bruto=resultado.raw_text,
        modelo_utilizado=resultado.model,
        response_id=resultado.response_id,
    )
    logger.info(
        "Execucao IA concluida",
        extra={
            **log_context,
            "modelo": resultado.model,
            "response_id": resultado.response_id,
        },
    )
    return {
        "execucao_id": execucao.pk,
        "status": "concluido",
        "modelo": resultado.model,
    }


def _build_internal_error_detail(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return f"{exc.__class__.__name__}: {message}"
    return exc.__class__.__name__


def _processar_execucao(*, ai_service: AnaliseAIService, execucao):
    payload = execucao.payload_entrada or {}
    analise = execucao.analise

    if execucao.tipo_tarefa == TipoTarefaExecucaoIAChoices.RESUMO:
        return ai_service.gerar_resumo_documento(
            texto_documento=payload["texto_documento"],
            documento=analise.documento,
            licitacao=analise.licitacao,
        )

    if execucao.tipo_tarefa == TipoTarefaExecucaoIAChoices.EXTRACAO:
        return ai_service.extrair_dados_documento(
            texto_documento=payload["texto_documento"],
            documento=analise.documento,
            licitacao=analise.licitacao,
            campos_alvo=payload.get("campos_alvo"),
        )

    if execucao.tipo_tarefa == TipoTarefaExecucaoIAChoices.PARECER:
        return ai_service.gerar_parecer_tecnico(
            texto_documento=payload["texto_documento"],
            licitacao=analise.licitacao,
            documento=analise.documento,
            analise=analise,
            persistir=True,
        )

    if execucao.tipo_tarefa == TipoTarefaExecucaoIAChoices.COMPARACAO:
        return ai_service.comparar_documento_com_licitacao(
            texto_documento=payload["texto_documento"],
            licitacao=analise.licitacao,
            documento=analise.documento,
        )

    if execucao.tipo_tarefa == TipoTarefaExecucaoIAChoices.CHECKLIST:
        return ai_service.gerar_checklist(
            texto_documento=payload.get("texto_documento"),
            licitacao=analise.licitacao,
            documento=analise.documento,
            contexto_comparacao=payload.get("contexto_comparacao"),
        )

    raise ValueError(f"Tipo de tarefa de IA nao suportado: {execucao.tipo_tarefa}.")
