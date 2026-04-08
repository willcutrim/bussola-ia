from decimal import Decimal

from django.views.generic import TemplateView

from apps.core.mixins import AppLoginRequiredMixin, ServiceMixin
from apps.core.services import DashboardService


class HomeDashboardView(AppLoginRequiredMixin, ServiceMixin, TemplateView):
    template_name = "dashboard/home.html"
    service_class = DashboardService

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resumo = self.get_service().obter_resumo()
        total_licitacoes = resumo["total_licitacoes"] or 1
        valor_estimado_total = resumo["valor_estimado_total"]

        context.update(
            {
                "page_title": "Painel executivo",
                "page_subtitle": "Acompanhamento rapido da operacao comercial e das oportunidades em curso.",
                "dashboard": resumo,
                "dashboard_kpis": [
                    {
                        "title": "Licitacoes",
                        "value": resumo["total_licitacoes"],
                        "helper": f"{resumo['total_licitacoes_ativas']} ativas no pipeline",
                        "tone": "primary",
                        "icon": "briefcase",
                    },
                    {
                        "title": "Empresas",
                        "value": resumo["total_empresas"],
                        "helper": f"{resumo['total_empresas_ativas']} com operacao ativa",
                        "tone": "info",
                        "icon": "building",
                    },
                    {
                        "title": "Em analise",
                        "value": resumo["total_em_analise"],
                        "helper": "Demandas aguardando decisao",
                        "tone": "warning",
                        "icon": "pulse",
                    },
                    {
                        "title": "Valor estimado",
                        "value": f"R$ {valor_estimado_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        if isinstance(valor_estimado_total, Decimal)
                        else "R$ 0,00",
                        "helper": "Volume financeiro mapeado",
                        "tone": "success",
                        "icon": "chart",
                    },
                ],
                "dashboard_completion": round(
                    (resumo["total_licitacoes_ativas"] / total_licitacoes) * 100
                ),
            }
        )
        return context


home = HomeDashboardView.as_view()
