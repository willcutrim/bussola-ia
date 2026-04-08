from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView

from apps.core.mixins import AppLoginRequiredMixin, ServiceMixin

from .forms import (
    ChecklistAIForm,
    ComparisonAIForm,
    DocumentoSummaryAIForm,
    ExtractionAIForm,
    TechnicalAnalysisAIForm,
)
from .models import Analise
from .services import AnaliseService
from .services_ai import AnaliseAIService


class AnaliseAIBaseView(AppLoginRequiredMixin, ServiceMixin, SingleObjectMixin, FormView):
    http_method_names = ["post"]
    model = Analise
    service_class = AnaliseService
    ai_service_class = AnaliseAIService
    task_name = ""
    persistir_resultado = False
    result_template_name = ""
    result_title = ""

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

    def get_ai_service(self):
        return self.ai_service_class()

    def is_htmx_request(self):
        return self.request.headers.get("HX-Request") == "true"

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
            return self.render_partial(
                error_messages=self._collect_form_errors(form),
                status=200,
            )

        return JsonResponse(
            {
                "ok": False,
                "task": self.task_name,
                "analise_id": self.object.pk,
                "errors": form.errors.get_json_data(),
                "non_field_errors": list(form.non_field_errors()),
            },
            status=400,
        )

    def form_valid(self, form):
        try:
            data = self.execute_ai_task(form.cleaned_data)
        except (ValidationError, ValueError) as exc:
            if self.is_htmx_request():
                return self.render_partial(error_messages=[str(exc)], status=200)
            return JsonResponse(
                {
                    "ok": False,
                    "task": self.task_name,
                    "analise_id": self.object.pk,
                    "error": str(exc),
                },
                status=400,
            )
        except ImproperlyConfigured as exc:
            if self.is_htmx_request():
                return self.render_partial(error_messages=[str(exc)], status=200)
            return JsonResponse(
                {
                    "ok": False,
                    "task": self.task_name,
                    "analise_id": self.object.pk,
                    "error": str(exc),
                },
                status=503,
            )

        if self.is_htmx_request():
            return self.render_partial(result=data)

        return JsonResponse(
            {
                "ok": True,
                "task": self.task_name,
                "analise": {
                    "id": self.object.pk,
                    "detail_url": reverse(
                        "analises:detail",
                        kwargs={"pk": self.object.pk},
                    ),
                },
                "persistido": self.persistir_resultado,
                "data": data,
            }
        )

    def execute_ai_task(self, cleaned_data):
        raise NotImplementedError

    def render_partial(self, *, result=None, error_messages=None, status=200):
        context = {
            "analise": self.object,
            "result": result,
            "error_messages": error_messages or [],
            "result_title": self.result_title,
        }
        template_name = (
            "analises/partials/ai_result_error.html"
            if error_messages
            else self.result_template_name
        )
        return render(self.request, template_name, context, status=status)

    def _collect_form_errors(self, form):
        error_messages: list[str] = []
        for errors in form.errors.get_json_data().values():
            for error in errors:
                message = error.get("message")
                if message:
                    error_messages.append(str(message))
        error_messages.extend(str(error) for error in form.non_field_errors())
        return error_messages or ["Nao foi possivel processar a solicitacao de IA."]


class AnaliseGerarResumoDocumentoView(AnaliseAIBaseView):
    form_class = DocumentoSummaryAIForm
    task_name = "resumo_documento"
    result_template_name = "analises/partials/ai_result_resumo.html"
    result_title = "Resumo do documento"

    def execute_ai_task(self, cleaned_data):
        return self.get_ai_service().gerar_resumo_documento(
            texto_documento=cleaned_data["texto_documento"],
            documento=self.object.documento,
            licitacao=self.object.licitacao,
        )


class AnaliseExtrairDadosDocumentoView(AnaliseAIBaseView):
    form_class = ExtractionAIForm
    task_name = "extracao_documento"
    result_template_name = "analises/partials/ai_result_extracao.html"
    result_title = "Dados extraidos"

    def execute_ai_task(self, cleaned_data):
        return self.get_ai_service().extrair_dados_documento(
            texto_documento=cleaned_data["texto_documento"],
            documento=self.object.documento,
            licitacao=self.object.licitacao,
            campos_alvo=cleaned_data.get("campos_alvo"),
        )


class AnaliseGerarParecerView(AnaliseAIBaseView):
    form_class = TechnicalAnalysisAIForm
    task_name = "parecer_tecnico"
    persistir_resultado = True
    result_template_name = "analises/partials/ai_result_parecer.html"
    result_title = "Parecer tecnico"

    def execute_ai_task(self, cleaned_data):
        return self.get_ai_service().gerar_parecer_tecnico(
            texto_documento=cleaned_data["texto_documento"],
            licitacao=self.object.licitacao,
            documento=self.object.documento,
            analise=self.object,
            persistir=self.persistir_resultado,
        )


class AnaliseCompararDocumentoView(AnaliseAIBaseView):
    form_class = ComparisonAIForm
    task_name = "comparacao_documento"
    result_template_name = "analises/partials/ai_result_comparacao.html"
    result_title = "Comparacao com a licitacao"

    def execute_ai_task(self, cleaned_data):
        return self.get_ai_service().comparar_documento_com_licitacao(
            texto_documento=cleaned_data["texto_documento"],
            licitacao=self.object.licitacao,
            documento=self.object.documento,
        )


class AnaliseGerarChecklistView(AnaliseAIBaseView):
    form_class = ChecklistAIForm
    task_name = "checklist_analitico"
    result_template_name = "analises/partials/ai_result_checklist.html"
    result_title = "Checklist analitico"

    def execute_ai_task(self, cleaned_data):
        return self.get_ai_service().gerar_checklist(
            texto_documento=cleaned_data.get("texto_documento"),
            licitacao=self.object.licitacao,
            documento=self.object.documento,
            contexto_comparacao=cleaned_data.get("comparison_contexto"),
        )
