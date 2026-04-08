from django.urls import reverse, reverse_lazy

from apps.core.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from .forms import (
    AnaliseFiltroForm,
    AnaliseForm,
)
from .models import Analise
from .services import AnaliseService
from .services_async import AnaliseExecucaoIAService
from .views_ai import AI_TASK_UI_CONFIGS
from config.tasks import ANALISES_AI_POLL_TRIGGER


class AnaliseListView(BaseListView):
    model = Analise
    service_class = AnaliseService
    template_name = "analises/analise_list.html"
    context_object_name = "analises"

    def get_queryset(self):
        return self.get_service().listar(self.get_filter_data())

    def get_filter_form(self):
        return AnaliseFiltroForm(self.request.GET or None)

    def get_filter_data(self):
        filter_form = self.get_filter_form()
        if filter_form.is_valid():
            return filter_form.cleaned_data
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtro_form"] = kwargs.get("filtro_form") or self.get_filter_form()
        context["filtros_atuais"] = self.get_filter_data()
        return context


class AnaliseDetailView(BaseDetailView):
    model = Analise
    service_class = AnaliseService
    template_name = "analises/analise_detail.html"
    context_object_name = "analise"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        execucoes_por_tipo = AnaliseExecucaoIAService().listar_ultimas_por_tipo(
            self.object
        )
        context["execucoes_ia_por_tipo"] = execucoes_por_tipo
        context["poll_trigger"] = ANALISES_AI_POLL_TRIGGER
        context["ai_cards"] = self._build_ai_cards(execucoes_por_tipo)
        context["ai_history_url"] = reverse("analises:ia_execucao_historico", args=[self.object.pk])
        context["ai_comparison_url"] = reverse(
            "analises:ia_execucao_comparacao",
            args=[self.object.pk],
        )
        return context

    def _build_ai_cards(self, execucoes_por_tipo):
        ordered_types = ("resumo", "parecer", "extracao", "comparacao", "checklist")
        return [
            self._build_ai_card(
                tipo=task_type,
                execucao=execucoes_por_tipo.get(task_type),
                **AI_TASK_UI_CONFIGS[task_type],
            )
            for task_type in ordered_types
        ]

    def _build_ai_card(
        self,
        *,
        tipo,
        panel_id,
        col_class,
        execucao,
        result_url_name,
        request_url_name,
        result_template_name,
        card_title,
        card_description,
        badge_label,
        badge_tone_class,
        empty_title,
        empty_description,
        processing_message,
        retry_button_label="Reprocessar",
    ):
        should_poll = bool(
            execucao and execucao.status in {"pendente", "em_processamento"}
        )
        return {
            "tipo": tipo,
            "panel_id": panel_id,
            "col_class": col_class,
            "execucao": execucao,
            "poll_trigger": ANALISES_AI_POLL_TRIGGER,
            "should_poll": should_poll,
            "show_legacy_result": bool(
                execucao is None and tipo == "parecer" and self.object.parecer
            ),
            "allow_reprocess": bool(
                execucao and execucao.status in {"concluido", "falhou"}
            ),
            "retry_button_label": retry_button_label,
            "resultado_url": reverse(result_url_name, args=[self.object.pk]),
            "request_url": reverse(request_url_name, args=[self.object.pk]),
            "reprocess_url": (
                reverse(
                    "analises:ia_execucao_reprocessar",
                    args=[self.object.pk, execucao.pk],
                )
                if execucao
                else ""
            ),
            "reprocess_target": f"#{panel_id}",
            "result_template_name": result_template_name,
            "card_title": card_title,
            "card_description": card_description,
            "badge_label": badge_label,
            "badge_tone_class": badge_tone_class,
            "empty_title": empty_title,
            "empty_description": empty_description,
            "processing_message": processing_message,
        }


class AnaliseCreateView(BaseCreateView):
    model = Analise
    form_class = AnaliseForm
    service_class = AnaliseService
    template_name = "analises/analise_form.html"
    success_url = reverse_lazy("analises:list")
    success_message = "Analise cadastrada com sucesso."


class AnaliseUpdateView(BaseUpdateView):
    model = Analise
    form_class = AnaliseForm
    service_class = AnaliseService
    template_name = "analises/analise_form.html"
    success_url = reverse_lazy("analises:list")
    success_message = "Analise atualizada com sucesso."


class AnaliseDeleteView(BaseDeleteView):
    model = Analise
    service_class = AnaliseService
    template_name = "analises/analise_confirm_delete.html"
    success_url = reverse_lazy("analises:list")
    success_message = "Analise removida com sucesso."


index = AnaliseListView.as_view()
