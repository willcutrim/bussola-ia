from django.urls import reverse_lazy

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
