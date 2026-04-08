import json

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView

from apps.core.mixins import AppLoginRequiredMixin, ServiceMixin
from config.tasks import ANALISES_AI_POLL_TRIGGER

from .forms import (
    ChecklistAIForm,
    ComparisonAIForm,
    DocumentoSummaryAIForm,
    ExtractionAIForm,
    TechnicalAnalysisAIForm,
)
from .models import Analise
from .services import AnaliseService
from .services_async import AnaliseAsyncService, AnaliseExecucaoIAService


AI_TASK_UI_CONFIGS = {
    "resumo": {
        "panel_id": "ai-summary-panel",
        "col_class": "col-12 col-xxl-6 ai-panel-shell",
        "request_url_name": "analises:ia_resumo",
        "result_url_name": "analises:ia_resumo_resultado",
        "result_template_name": "analises/partials/ai_result_resumo.html",
        "card_title": "Resumo do documento",
        "card_description": "Leitura executiva para decidir rapidamente se o documento merece aprofundamento.",
        "badge_label": "Resumo",
        "badge_tone_class": "status-pill-primary",
        "empty_title": "Nenhum resumo gerado ainda",
        "empty_description": "Clique em 'Gerar resumo do documento' para sintetizar fatos, inferencias e lacunas.",
        "processing_message": "O resumo foi solicitado. O card sera atualizado automaticamente em alguns instantes.",
        "retry_button_label": "Reprocessar",
    },
    "extracao": {
        "panel_id": "ai-extraction-panel",
        "col_class": "col-12 col-xxl-6 ai-panel-shell",
        "request_url_name": "analises:ia_extracao",
        "result_url_name": "analises:ia_extracao_resultado",
        "result_template_name": "analises/partials/ai_result_extracao.html",
        "card_title": "Dados extraidos",
        "card_description": "Campos estruturados para reaproveitamento futuro em automacoes e persistencia.",
        "badge_label": "Extracao",
        "badge_tone_class": "status-pill-info",
        "empty_title": "Nenhum dado extraido ainda",
        "empty_description": "Use a extracao para montar um inventario estruturado de prazos, garantias, vigencia e outros campos criticos.",
        "processing_message": "A extracao foi iniciada. Este card sera atualizado automaticamente quando houver resultado.",
        "retry_button_label": "Reprocessar",
    },
    "parecer": {
        "panel_id": "ai-parecer-panel",
        "col_class": "col-12 col-xxl-6 ai-panel-shell",
        "request_url_name": "analises:ia_parecer",
        "result_url_name": "analises:ia_parecer_resultado",
        "result_template_name": "analises/partials/ai_result_parecer.html",
        "card_title": "Parecer tecnico",
        "card_description": "Leitura orientada a decisao, com recomendacoes e status sugerido para a analise.",
        "badge_label": "Decisao",
        "badge_tone_class": "status-pill-success",
        "empty_title": "Nenhum parecer gerado ainda",
        "empty_description": "Execute o parecer tecnico para registrar riscos, proxima acao e classificacao sugerida.",
        "processing_message": "O parecer tecnico foi solicitado e este card sera atualizado automaticamente.",
        "retry_button_label": "Reprocessar",
    },
    "comparacao": {
        "panel_id": "ai-comparison-panel",
        "col_class": "col-12 col-xxl-6 ai-panel-shell",
        "request_url_name": "analises:ia_comparacao",
        "result_url_name": "analises:ia_comparacao_resultado",
        "result_template_name": "analises/partials/ai_result_comparacao.html",
        "card_title": "Comparacao com a licitacao",
        "card_description": "Confronta o texto enviado com o contexto da oportunidade para evidenciar aderencias e pontos de risco.",
        "badge_label": "Comparacao",
        "badge_tone_class": "status-pill-warning",
        "empty_title": "Nenhuma comparacao gerada ainda",
        "empty_description": "Use esta acao para verificar aderencia, divergencias contratuais e pontos nao comprovados no texto analisado.",
        "processing_message": "A comparacao foi iniciada. Este card sera atualizado automaticamente.",
        "retry_button_label": "Reprocessar",
    },
    "checklist": {
        "panel_id": "ai-checklist-panel",
        "col_class": "col-12 ai-panel-shell",
        "request_url_name": "analises:ia_checklist",
        "result_url_name": "analises:ia_checklist_resultado",
        "result_template_name": "analises/partials/ai_result_checklist.html",
        "card_title": "Checklist analitico",
        "card_description": "Lista acionavel para revisar frentes documental, tecnica, juridica e operacional.",
        "badge_label": "Checklist",
        "badge_tone_class": "status-pill-info",
        "empty_title": "Nenhum checklist gerado ainda",
        "empty_description": "Clique em 'Gerar checklist' para transformar a leitura do documento em uma lista acionavel de verificacao.",
        "processing_message": "O checklist foi solicitado e este card sera atualizado automaticamente.",
        "retry_button_label": "Reprocessar",
    },
}


def get_ai_task_ui_config(task_type: str) -> dict:
    try:
        return AI_TASK_UI_CONFIGS[task_type]
    except KeyError as exc:
        raise ImproperlyConfigured(
            f"Configuracao de UI nao cadastrada para a tarefa de IA '{task_type}'."
        ) from exc


class AnaliseAIViewMixin(AppLoginRequiredMixin, ServiceMixin, SingleObjectMixin):
    model = Analise
    service_class = AnaliseService
    execucao_service_class = AnaliseExecucaoIAService
    task_type = ""
    result_url_name = ""
    request_url_name = ""
    card_title = ""
    card_description = ""
    badge_label = ""
    badge_tone_class = "status-pill-primary"
    result_template_name = ""
    empty_title = ""
    empty_description = ""
    processing_message = ""
    retry_button_label = "Reprocessar"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_service().listar()

    def get_object(self, queryset=None):
        if getattr(self, "object", None) is not None:
            return self.object
        queryset = queryset or self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs["pk"])

    def get_execucao_service(self):
        return self.execucao_service_class()

    def get_task_ui_config(self):
        return get_ai_task_ui_config(self.task_type)

    def is_htmx_request(self):
        return self.request.headers.get("HX-Request") == "true"

    def get_result_url(self):
        url_name = self.result_url_name or self.get_task_ui_config()["result_url_name"]
        return reverse(url_name, kwargs={"pk": self.object.pk})

    def get_request_url(self):
        url_name = self.request_url_name or self.get_task_ui_config()["request_url_name"]
        return reverse(url_name, kwargs={"pk": self.object.pk})

    def get_reprocess_url(self, execucao):
        return reverse(
            "analises:ia_execucao_reprocessar",
            kwargs={"pk": self.object.pk, "execucao_pk": execucao.pk},
        )

    def get_result_context(
        self,
        *,
        execucao=None,
        error_messages=None,
    ):
        ui_config = self.get_task_ui_config()
        result = None
        if execucao is not None and execucao.resultado_payload:
            result = execucao.resultado_payload

        return {
            "analise": self.object,
            "execucao": execucao,
            "result": result,
            "error_messages": error_messages or [],
            "card_title": self.card_title or ui_config["card_title"],
            "card_description": self.card_description or ui_config["card_description"],
            "badge_label": self.badge_label or ui_config["badge_label"],
            "badge_tone_class": self.badge_tone_class or ui_config["badge_tone_class"],
            "poll_trigger": ANALISES_AI_POLL_TRIGGER,
            "resultado_url": self.get_result_url(),
            "request_url": self.get_request_url(),
            "result_template_name": self.result_template_name or ui_config["result_template_name"],
            "empty_title": self.empty_title or ui_config["empty_title"],
            "empty_description": self.empty_description or ui_config["empty_description"],
            "processing_message": self.processing_message or ui_config["processing_message"],
            "should_poll": bool(
                execucao
                and execucao.status in {"pendente", "em_processamento"}
            ),
            "show_legacy_result": bool(
                execucao is None
                and self.task_type == "parecer"
                and self.object.parecer
            ),
            "allow_reprocess": bool(
                execucao
                and execucao.status in {"concluido", "falhou"}
            ),
            "retry_button_label": self.retry_button_label or ui_config["retry_button_label"],
            "reprocess_url": self.get_reprocess_url(execucao) if execucao else "",
            "reprocess_target": f"#{ui_config['panel_id']}",
        }

    def render_result_partial(self, *, execucao=None, error_messages=None, status=200):
        response = render(
            self.request,
            "analises/partials/ai_result_container.html",
            self.get_result_context(
                execucao=execucao,
                error_messages=error_messages,
            ),
            status=status,
        )
        if execucao is not None and (
            self.request.method == "POST"
            or execucao.status in {"concluido", "falhou"}
        ):
            response["HX-Trigger"] = json.dumps({"aiHistoryRefresh": True})
        return response

    def _collect_form_errors(self, form):
        error_messages: list[str] = []
        for errors in form.errors.get_json_data().values():
            for error in errors:
                message = error.get("message")
                if message:
                    error_messages.append(str(message))
        error_messages.extend(str(error) for error in form.non_field_errors())
        return error_messages or ["Nao foi possivel processar a solicitacao de IA."]


class AnaliseAIBaseView(AnaliseAIViewMixin, FormView):
    http_method_names = ["post"]
    async_service_class = AnaliseAsyncService

    def get_async_service(self):
        return self.async_service_class()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["data"] = self.get_bound_form_data()
        return kwargs

    def get_bound_form_data(self):
        data = self.request.POST.copy()
        analise = self.object
        data["analise"] = str(analise.pk)
        data["licitacao"] = str(analise.licitacao_id)

        if analise.documento_id:
            data["documento"] = str(analise.documento_id)
        else:
            data.pop("documento", None)

        return data

    def form_invalid(self, form):
        if self.is_htmx_request():
            return self.render_result_partial(
                error_messages=self._collect_form_errors(form),
                status=200,
            )

        return JsonResponse(
            {
                "ok": False,
                "task_type": self.task_type,
                "analise_id": self.object.pk,
                "errors": form.errors.get_json_data(),
                "non_field_errors": list(form.non_field_errors()),
            },
            status=400,
        )

    def form_valid(self, form):
        try:
            execucao, created = self.solicitar_execucao(form.cleaned_data)
        except (ValidationError, ValueError) as exc:
            if self.is_htmx_request():
                return self.render_result_partial(error_messages=[str(exc)], status=200)
            return JsonResponse(
                {
                    "ok": False,
                    "task_type": self.task_type,
                    "analise_id": self.object.pk,
                    "error": str(exc),
                },
                status=400,
            )
        except ImproperlyConfigured as exc:
            if self.is_htmx_request():
                return self.render_result_partial(error_messages=[str(exc)], status=200)
            return JsonResponse(
                {
                    "ok": False,
                    "task_type": self.task_type,
                    "analise_id": self.object.pk,
                    "error": str(exc),
                },
                status=503,
            )

        execucao.refresh_from_db()
        if self.is_htmx_request():
            return self.render_result_partial(execucao=execucao, status=202)

        return JsonResponse(
            {
                "ok": True,
                "task_type": self.task_type,
                "status": execucao.status,
                "execucao_id": execucao.pk,
                "versao": execucao.versao,
                "detail_url": reverse(
                    "analises:detail",
                    kwargs={"pk": self.object.pk},
                ),
                "resultado_url": self.get_result_url(),
                "created": created,
            },
            status=202,
        )

    def solicitar_execucao(self, cleaned_data):
        raise NotImplementedError


class AnaliseAIResultBaseView(AnaliseAIViewMixin, TemplateView):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        execucao = self.get_execucao_service().obter_ultima_por_tipo(
            self.object,
            self.task_type,
        )
        return self.render_result_partial(execucao=execucao)


class AnaliseExecucaoIAHistoryView(AnaliseAIViewMixin, TemplateView):
    http_method_names = ["get"]
    template_name = "analises/partials/ai_execution_history.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        execucao_service = self.get_execucao_service()
        historico_por_tipo = execucao_service.listar_historico_por_tipo(self.object)
        grupos = []
        for task_type, ui_config in AI_TASK_UI_CONFIGS.items():
            registros = historico_por_tipo.get(task_type, [])
            grupos.append(
                {
                    "task_type": task_type,
                    "title": ui_config["card_title"],
                    "badge_label": ui_config["badge_label"],
                    "badge_tone_class": ui_config["badge_tone_class"],
                    "panel_id": ui_config["panel_id"],
                    "entries": [
                        {
                            "execucao": registro["execucao"],
                            "anterior": registro["anterior"],
                            "reprocess_url": reverse(
                                "analises:ia_execucao_reprocessar",
                                kwargs={
                                    "pk": self.object.pk,
                                    "execucao_pk": registro["execucao"].pk,
                                },
                            ),
                            "compare_url": (
                                reverse(
                                    "analises:ia_execucao_comparacao",
                                    kwargs={"pk": self.object.pk},
                                )
                                + f"?base={registro['anterior'].pk}&target={registro['execucao'].pk}"
                                if registro["anterior"] is not None
                                else ""
                            ),
                            "detail_url": reverse(
                                "analises:ia_execucao_detalhe",
                                kwargs={
                                    "pk": self.object.pk,
                                    "execucao_pk": registro["execucao"].pk,
                                },
                            ),
                        }
                        for registro in registros
                    ],
                }
            )
        return render(
            request,
            self.template_name,
            {
                "analise": self.object,
                "history_groups": grupos,
            },
        )


class AnaliseExecucaoIADetailView(AnaliseAIViewMixin, TemplateView):
    http_method_names = ["get"]
    execution_result_url_name = "analises:ia_execucao_detalhe"

    def get_execucao(self):
        return self.get_execucao_service().obter_por_id_e_analise(
            analise=self.object,
            execucao_id=self.kwargs["execucao_pk"],
        )

    def get_result_url(self):
        execucao = self.get_execucao()
        return reverse(
            self.execution_result_url_name,
            kwargs={"pk": self.object.pk, "execucao_pk": execucao.pk},
        )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        execucao = self.get_execucao()
        self.task_type = execucao.tipo_tarefa
        return self.render_result_partial(execucao=execucao)


class AnaliseExecucaoIAComparacaoView(AnaliseAIViewMixin, TemplateView):
    http_method_names = ["get"]
    template_name = "analises/partials/ai_execution_comparison.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        base_id = request.GET.get("base")
        target_id = request.GET.get("target")
        if not base_id or not target_id:
            return render(
                request,
                self.template_name,
                {
                    "analise": self.object,
                    "comparison_error": "Selecione duas execucoes compativeis para comparar.",
                },
                status=400,
            )

        execucao_service = self.get_execucao_service()
        execucao_base = execucao_service.obter_por_id_e_analise(
            analise=self.object,
            execucao_id=base_id,
        )
        execucao_comparada = execucao_service.obter_por_id_e_analise(
            analise=self.object,
            execucao_id=target_id,
        )
        try:
            comparison = execucao_service.preparar_comparacao(
                execucao_base=execucao_base,
                execucao_comparada=execucao_comparada,
            )
        except ValueError as exc:
            return render(
                request,
                self.template_name,
                {
                    "analise": self.object,
                    "comparison_error": str(exc),
                },
                status=400,
            )

        return render(
            request,
            self.template_name,
            {
                "analise": self.object,
                "comparison": comparison,
            },
        )


class AnaliseExecucaoIAReprocessarView(AnaliseAIViewMixin, TemplateView):
    http_method_names = ["post"]
    async_service_class = AnaliseAsyncService

    def get_async_service(self):
        return self.async_service_class()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        execucao = self.get_execucao_service().obter_por_id_e_analise(
            analise=self.object,
            execucao_id=self.kwargs["execucao_pk"],
        )
        self.task_type = execucao.tipo_tarefa
        nova_execucao, _created = self.get_async_service().reprocessar_execucao(
            execucao=execucao,
            criado_por=request.user,
        )
        response = self.render_result_partial(execucao=nova_execucao, status=202)
        response["HX-Trigger"] = json.dumps({"aiHistoryRefresh": True})
        return response


class AnaliseGerarResumoDocumentoView(AnaliseAIBaseView):
    form_class = DocumentoSummaryAIForm
    task_type = "resumo"
    request_url_name = "analises:ia_resumo"
    result_template_name = "analises/partials/ai_result_resumo.html"
    result_url_name = "analises:ia_resumo_resultado"
    card_title = "Resumo do documento"
    card_description = "Leitura executiva para decidir rapidamente se o documento merece aprofundamento."
    badge_label = "Resumo"
    badge_tone_class = "status-pill-primary"
    empty_title = "Nenhum resumo gerado ainda"
    empty_description = "Clique em 'Gerar resumo do documento' para sintetizar fatos, inferencias e lacunas."
    processing_message = "O resumo foi solicitado. O card sera atualizado automaticamente em alguns instantes."

    def solicitar_execucao(self, cleaned_data):
        return self.get_async_service().solicitar_resumo_documento(
            analise=self.object,
            texto_documento=cleaned_data["texto_documento"],
            criado_por=self.request.user,
        )


class AnaliseResumoResultadoView(AnaliseAIResultBaseView):
    task_type = "resumo"
    request_url_name = "analises:ia_resumo"
    result_template_name = "analises/partials/ai_result_resumo.html"
    result_url_name = "analises:ia_resumo_resultado"
    card_title = "Resumo do documento"
    card_description = "Leitura executiva para decidir rapidamente se o documento merece aprofundamento."
    badge_label = "Resumo"
    badge_tone_class = "status-pill-primary"
    empty_title = "Nenhum resumo gerado ainda"
    empty_description = "Clique em 'Gerar resumo do documento' para sintetizar fatos, inferencias e lacunas."
    processing_message = "O resumo foi solicitado. O card sera atualizado automaticamente em alguns instantes."


class AnaliseExtrairDadosDocumentoView(AnaliseAIBaseView):
    form_class = ExtractionAIForm
    task_type = "extracao"
    request_url_name = "analises:ia_extracao"
    result_template_name = "analises/partials/ai_result_extracao.html"
    result_url_name = "analises:ia_extracao_resultado"
    card_title = "Dados extraidos"
    card_description = "Campos estruturados para reaproveitamento futuro em automacoes e persistencia."
    badge_label = "Extracao"
    badge_tone_class = "status-pill-info"
    empty_title = "Nenhum dado extraido ainda"
    empty_description = "Use a extracao para montar um inventario estruturado de prazos, garantias, vigencia e outros campos criticos."
    processing_message = "A extracao foi iniciada. Este card sera atualizado automaticamente quando houver resultado."

    def solicitar_execucao(self, cleaned_data):
        return self.get_async_service().solicitar_extracao_documento(
            analise=self.object,
            texto_documento=cleaned_data["texto_documento"],
            campos_alvo=cleaned_data.get("campos_alvo"),
            criado_por=self.request.user,
        )


class AnaliseExtracaoResultadoView(AnaliseAIResultBaseView):
    task_type = "extracao"
    request_url_name = "analises:ia_extracao"
    result_template_name = "analises/partials/ai_result_extracao.html"
    result_url_name = "analises:ia_extracao_resultado"
    card_title = "Dados extraidos"
    card_description = "Campos estruturados para reaproveitamento futuro em automacoes e persistencia."
    badge_label = "Extracao"
    badge_tone_class = "status-pill-info"
    empty_title = "Nenhum dado extraido ainda"
    empty_description = "Use a extracao para montar um inventario estruturado de prazos, garantias, vigencia e outros campos criticos."
    processing_message = "A extracao foi iniciada. Este card sera atualizado automaticamente quando houver resultado."


class AnaliseGerarParecerView(AnaliseAIBaseView):
    form_class = TechnicalAnalysisAIForm
    task_type = "parecer"
    request_url_name = "analises:ia_parecer"
    result_template_name = "analises/partials/ai_result_parecer.html"
    result_url_name = "analises:ia_parecer_resultado"
    card_title = "Parecer tecnico"
    card_description = "Leitura orientada a decisao, com recomendacoes e status sugerido para a analise."
    badge_label = "Decisao"
    badge_tone_class = "status-pill-success"
    empty_title = "Nenhum parecer gerado ainda"
    empty_description = "Execute o parecer tecnico para registrar riscos, proxima acao e classificacao sugerida."
    processing_message = "O parecer tecnico foi solicitado e este card sera atualizado automaticamente."

    def solicitar_execucao(self, cleaned_data):
        return self.get_async_service().solicitar_parecer_tecnico(
            analise=self.object,
            texto_documento=cleaned_data["texto_documento"],
            criado_por=self.request.user,
        )


class AnaliseParecerResultadoView(AnaliseAIResultBaseView):
    task_type = "parecer"
    request_url_name = "analises:ia_parecer"
    result_template_name = "analises/partials/ai_result_parecer.html"
    result_url_name = "analises:ia_parecer_resultado"
    card_title = "Parecer tecnico"
    card_description = "Leitura orientada a decisao, com recomendacoes e status sugerido para a analise."
    badge_label = "Decisao"
    badge_tone_class = "status-pill-success"
    empty_title = "Nenhum parecer gerado ainda"
    empty_description = "Execute o parecer tecnico para registrar riscos, proxima acao e classificacao sugerida."
    processing_message = "O parecer tecnico foi solicitado e este card sera atualizado automaticamente."


class AnaliseCompararDocumentoView(AnaliseAIBaseView):
    form_class = ComparisonAIForm
    task_type = "comparacao"
    request_url_name = "analises:ia_comparacao"
    result_template_name = "analises/partials/ai_result_comparacao.html"
    result_url_name = "analises:ia_comparacao_resultado"
    card_title = "Comparacao com a licitacao"
    card_description = "Confronta o texto enviado com o contexto da oportunidade para evidenciar aderencias e pontos de risco."
    badge_label = "Comparacao"
    badge_tone_class = "status-pill-warning"
    empty_title = "Nenhuma comparacao gerada ainda"
    empty_description = "Use esta acao para verificar aderencia, divergencias contratuais e pontos nao comprovados no texto analisado."
    processing_message = "A comparacao foi iniciada. Este card sera atualizado automaticamente."

    def solicitar_execucao(self, cleaned_data):
        return self.get_async_service().solicitar_comparacao_documento(
            analise=self.object,
            texto_documento=cleaned_data["texto_documento"],
            criado_por=self.request.user,
        )


class AnaliseComparacaoResultadoView(AnaliseAIResultBaseView):
    task_type = "comparacao"
    request_url_name = "analises:ia_comparacao"
    result_template_name = "analises/partials/ai_result_comparacao.html"
    result_url_name = "analises:ia_comparacao_resultado"
    card_title = "Comparacao com a licitacao"
    card_description = "Confronta o texto enviado com o contexto da oportunidade para evidenciar aderencias e pontos de risco."
    badge_label = "Comparacao"
    badge_tone_class = "status-pill-warning"
    empty_title = "Nenhuma comparacao gerada ainda"
    empty_description = "Use esta acao para verificar aderencia, divergencias contratuais e pontos nao comprovados no texto analisado."
    processing_message = "A comparacao foi iniciada. Este card sera atualizado automaticamente."


class AnaliseGerarChecklistView(AnaliseAIBaseView):
    form_class = ChecklistAIForm
    task_type = "checklist"
    request_url_name = "analises:ia_checklist"
    result_template_name = "analises/partials/ai_result_checklist.html"
    result_url_name = "analises:ia_checklist_resultado"
    card_title = "Checklist analitico"
    card_description = "Lista acionavel para revisar frentes documental, tecnica, juridica e operacional."
    badge_label = "Checklist"
    badge_tone_class = "status-pill-info"
    empty_title = "Nenhum checklist gerado ainda"
    empty_description = "Clique em 'Gerar checklist' para transformar a leitura do documento em uma lista acionavel de verificacao."
    processing_message = "O checklist foi solicitado e este card sera atualizado automaticamente."

    def solicitar_execucao(self, cleaned_data):
        return self.get_async_service().solicitar_checklist(
            analise=self.object,
            texto_documento=cleaned_data.get("texto_documento"),
            contexto_comparacao=cleaned_data.get("comparison_contexto"),
            criado_por=self.request.user,
        )


class AnaliseChecklistResultadoView(AnaliseAIResultBaseView):
    task_type = "checklist"
    request_url_name = "analises:ia_checklist"
    result_template_name = "analises/partials/ai_result_checklist.html"
    result_url_name = "analises:ia_checklist_resultado"
    card_title = "Checklist analitico"
    card_description = "Lista acionavel para revisar frentes documental, tecnica, juridica e operacional."
    badge_label = "Checklist"
    badge_tone_class = "status-pill-info"
    empty_title = "Nenhum checklist gerado ainda"
    empty_description = "Clique em 'Gerar checklist' para transformar a leitura do documento em uma lista acionavel de verificacao."
    processing_message = "O checklist foi solicitado e este card sera atualizado automaticamente."
