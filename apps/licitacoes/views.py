from django.urls import reverse, reverse_lazy

from apps.core.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from .forms import LicitacaoFiltroForm, LicitacaoForm
from .models import Licitacao
from .services import LicitacaoService


class LicitacaoListView(BaseListView):
    model = Licitacao
    service_class = LicitacaoService
    template_name = "licitacoes/licitacao_list.html"
    context_object_name = "licitacoes"

    def get_queryset(self):
        return self.get_service().listar(self.get_filter_data())

    def get_filter_form(self):
        return LicitacaoFiltroForm(self.request.GET or None)

    def get_filter_data(self):
        filter_form = self.get_filter_form()
        if filter_form.is_valid():
            return filter_form.cleaned_data
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        situacao_resumo = list(self.get_service().contar_por_situacao())
        total_listado = context["paginator"].count if context.get("paginator") else 0
        total_ativas = self.get_service().total_ativas()

        context["filtro_form"] = kwargs.get("filtro_form") or self.get_filter_form()
        context.update(
            {
                "page_title": "Licitacoes",
                "page_subtitle": "Pipeline administrativo e acompanhamento dos editais priorizados.",
                "page_primary_action_url": reverse("licitacoes:create"),
                "page_primary_action_label": "Nova licitacao",
                "licitacao_kpis": [
                    {
                        "title": "Total listado",
                        "value": total_listado,
                        "helper": "Registros considerando o filtro atual",
                        "tone": "primary",
                        "icon": "briefcase",
                    },
                    {
                        "title": "Ativas",
                        "value": total_ativas,
                        "helper": "Em monitoramento ativo",
                        "tone": "success",
                        "icon": "pulse",
                    },
                    {
                        "title": "Em analise",
                        "value": next(
                            (
                                item["total"]
                                for item in situacao_resumo
                                if item["situacao"] == "em_analise"
                            ),
                            0,
                        ),
                        "helper": "Pedem decisao comercial",
                        "tone": "warning",
                        "icon": "search",
                    },
                ],
                "situacao_resumo": situacao_resumo,
            }
        )
        return context


class LicitacaoDetailView(BaseDetailView):
    model = Licitacao
    service_class = LicitacaoService
    template_name = "licitacoes/licitacao_detail.html"
    context_object_name = "licitacao"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_primary_action_url"] = reverse("licitacoes:update", args=[self.object.pk])
        context["page_primary_action_label"] = "Editar licitacao"
        return context


class LicitacaoCreateView(BaseCreateView):
    model = Licitacao
    form_class = LicitacaoForm
    service_class = LicitacaoService
    template_name = "licitacoes/licitacao_form.html"
    success_url = reverse_lazy("licitacoes:index")
    success_message = "Licitacao cadastrada com sucesso."


class LicitacaoUpdateView(BaseUpdateView):
    model = Licitacao
    form_class = LicitacaoForm
    service_class = LicitacaoService
    template_name = "licitacoes/licitacao_form.html"
    success_url = reverse_lazy("licitacoes:index")
    success_message = "Licitacao atualizada com sucesso."


class LicitacaoDeleteView(BaseDeleteView):
    model = Licitacao
    service_class = LicitacaoService
    template_name = "licitacoes/licitacao_confirm_delete.html"
    success_url = reverse_lazy("licitacoes:index")
    success_message = "Licitacao removida com sucesso."


index = LicitacaoListView.as_view()
