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
        return context

    def _build_ai_cards(self, execucoes_por_tipo):
        return [
            self._build_ai_card(
                tipo="resumo",
                panel_id="ai-summary-panel",
                col_class="col-12 col-xxl-6 ai-panel-shell",
                execucao=execucoes_por_tipo.get("resumo"),
                result_url_name="analises:ia_resumo_resultado",
                request_url_name="analises:ia_resumo",
                result_template_name="analises/partials/ai_result_resumo.html",
                card_title="Resumo do documento",
                card_description="Leitura executiva para decidir rapidamente se o documento merece aprofundamento.",
                badge_label="Resumo",
                badge_tone_class="status-pill-primary",
                empty_title="Nenhum resumo gerado ainda",
                empty_description="Clique em 'Gerar resumo do documento' para sintetizar fatos, inferencias e lacunas.",
                processing_message="O resumo foi solicitado. O card sera atualizado automaticamente em alguns instantes.",
            ),
            self._build_ai_card(
                tipo="parecer",
                panel_id="ai-parecer-panel",
                col_class="col-12 col-xxl-6 ai-panel-shell",
                execucao=execucoes_por_tipo.get("parecer"),
                result_url_name="analises:ia_parecer_resultado",
                request_url_name="analises:ia_parecer",
                result_template_name="analises/partials/ai_result_parecer.html",
                card_title="Parecer tecnico",
                card_description="Leitura orientada a decisao, com recomendacoes e status sugerido para a analise.",
                badge_label="Decisao",
                badge_tone_class="status-pill-success",
                empty_title="Nenhum parecer gerado ainda",
                empty_description="Execute o parecer tecnico para registrar riscos, proxima acao e classificacao sugerida.",
                processing_message="O parecer tecnico foi solicitado e este card sera atualizado automaticamente.",
            ),
            self._build_ai_card(
                tipo="extracao",
                panel_id="ai-extraction-panel",
                col_class="col-12 col-xxl-6 ai-panel-shell",
                execucao=execucoes_por_tipo.get("extracao"),
                result_url_name="analises:ia_extracao_resultado",
                request_url_name="analises:ia_extracao",
                result_template_name="analises/partials/ai_result_extracao.html",
                card_title="Dados extraidos",
                card_description="Campos estruturados para reaproveitamento futuro em automacoes e persistencia.",
                badge_label="Extracao",
                badge_tone_class="status-pill-info",
                empty_title="Nenhum dado extraido ainda",
                empty_description="Use a extracao para montar um inventario estruturado de prazos, garantias, vigencia e outros campos criticos.",
                processing_message="A extracao foi iniciada. Este card sera atualizado automaticamente quando houver resultado.",
            ),
            self._build_ai_card(
                tipo="comparacao",
                panel_id="ai-comparison-panel",
                col_class="col-12 col-xxl-6 ai-panel-shell",
                execucao=execucoes_por_tipo.get("comparacao"),
                result_url_name="analises:ia_comparacao_resultado",
                request_url_name="analises:ia_comparacao",
                result_template_name="analises/partials/ai_result_comparacao.html",
                card_title="Comparacao com a licitacao",
                card_description="Confronta o texto enviado com o contexto da oportunidade para evidenciar aderencias e pontos de risco.",
                badge_label="Comparacao",
                badge_tone_class="status-pill-warning",
                empty_title="Nenhuma comparacao gerada ainda",
                empty_description="Use esta acao para verificar aderencia, divergencias contratuais e pontos nao comprovados no texto analisado.",
                processing_message="A comparacao foi iniciada. Este card sera atualizado automaticamente.",
            ),
            self._build_ai_card(
                tipo="checklist",
                panel_id="ai-checklist-panel",
                col_class="col-12 ai-panel-shell",
                execucao=execucoes_por_tipo.get("checklist"),
                result_url_name="analises:ia_checklist_resultado",
                request_url_name="analises:ia_checklist",
                result_template_name="analises/partials/ai_result_checklist.html",
                card_title="Checklist analitico",
                card_description="Lista acionavel para revisar frentes documental, tecnica, juridica e operacional.",
                badge_label="Checklist",
                badge_tone_class="status-pill-info",
                empty_title="Nenhum checklist gerado ainda",
                empty_description="Clique em 'Gerar checklist' para transformar a leitura do documento em uma lista acionavel de verificacao.",
                processing_message="O checklist foi solicitado e este card sera atualizado automaticamente.",
            ),
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
            "retry_button_label": "Reprocessar",
            "resultado_url": reverse(result_url_name, args=[self.object.pk]),
            "request_url": reverse(request_url_name, args=[self.object.pk]),
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
