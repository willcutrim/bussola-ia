from django.views.generic import TemplateView

from apps.core.mixins import AppLoginRequiredMixin, ServiceMixin

from .services import DashboardIAService


class DashboardIAView(AppLoginRequiredMixin, ServiceMixin, TemplateView):
    template_name = "analises/dashboard_ai.html"
    service_class = DashboardIAService

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = self.get_service().obter_dashboard()
        context.update(
            {
                "page_title": "Operacao de IA",
                "page_subtitle": "Acompanhamento operacional das execucoes assincronas, falhas e produtividade do modulo de analises.",
                "dashboard_ai": dashboard,
                "dashboard_kpis": dashboard["kpis"],
            }
        )
        return context


dashboard_ia = DashboardIAView.as_view()
