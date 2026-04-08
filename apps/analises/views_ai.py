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

    def is_htmx_request(self):
        return self.request.headers.get("HX-Request") == "true"

    def get_result_url(self):
        return reverse(self.result_url_name, kwargs={"pk": self.object.pk})

    def get_request_url(self):
        return reverse(self.request_url_name, kwargs={"pk": self.object.pk})

    def get_result_context(
        self,
        *,
        execucao=None,
        error_messages=None,
    ):
        result = None
        if execucao is not None and execucao.resultado_payload:
            result = execucao.resultado_payload

        return {
            "analise": self.object,
            "execucao": execucao,
            "result": result,
            "error_messages": error_messages or [],
            "card_title": self.card_title,
            "card_description": self.card_description,
            "badge_label": self.badge_label,
            "badge_tone_class": self.badge_tone_class,
            "poll_trigger": ANALISES_AI_POLL_TRIGGER,
            "resultado_url": self.get_result_url(),
            "request_url": self.get_request_url(),
            "result_template_name": self.result_template_name,
            "empty_title": self.empty_title,
            "empty_description": self.empty_description,
            "processing_message": self.processing_message,
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
            "retry_button_label": self.retry_button_label,
        }

    def render_result_partial(self, *, execucao=None, error_messages=None, status=200):
        return render(
            self.request,
            "analises/partials/ai_result_container.html",
            self.get_result_context(
                execucao=execucao,
                error_messages=error_messages,
            ),
            status=status,
        )

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
