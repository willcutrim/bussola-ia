from django.urls import reverse_lazy

from apps.core.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from .forms import DocumentoFiltroForm, DocumentoForm
from .models import Documento
from .services import DocumentoService


class DocumentoListView(BaseListView):
    model = Documento
    service_class = DocumentoService
    template_name = "documentos/documento_list.html"
    context_object_name = "documentos"

    def get_queryset(self):
        return self.get_service().listar(self.get_filter_data())

    def get_filter_form(self):
        return DocumentoFiltroForm(self.request.GET or None)

    def get_filter_data(self):
        filter_form = self.get_filter_form()
        if filter_form.is_valid():
            return filter_form.cleaned_data
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtro_form"] = kwargs.get("filtro_form") or self.get_filter_form()
        return context


class DocumentoDetailView(BaseDetailView):
    model = Documento
    service_class = DocumentoService
    template_name = "documentos/documento_detail.html"
    context_object_name = "documento"


class DocumentoCreateView(BaseCreateView):
    model = Documento
    form_class = DocumentoForm
    service_class = DocumentoService
    template_name = "documentos/documento_form.html"
    success_url = reverse_lazy("documentos:index")
    success_message = "Documento cadastrado com sucesso."


class DocumentoUpdateView(BaseUpdateView):
    model = Documento
    form_class = DocumentoForm
    service_class = DocumentoService
    template_name = "documentos/documento_form.html"
    success_url = reverse_lazy("documentos:index")
    success_message = "Documento atualizado com sucesso."


class DocumentoDeleteView(BaseDeleteView):
    model = Documento
    service_class = DocumentoService
    template_name = "documentos/documento_confirm_delete.html"
    success_url = reverse_lazy("documentos:index")
    success_message = "Documento removido com sucesso."


index = DocumentoListView.as_view()
