from django.urls import reverse, reverse_lazy

from apps.core.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from .forms import ContatoEmpresaForm, EmpresaForm, EnderecoEmpresaForm
from .models import ContatoEmpresa, Empresa, EnderecoEmpresa
from .services import ContatoEmpresaService, EmpresaService, EnderecoEmpresaService


def _parse_boolean_query_param(value):
    if value in (None, ""):
        return None

    normalized_value = str(value).strip().lower()
    truthy_values = {"1", "true", "t", "yes", "y", "sim", "on"}
    falsy_values = {"0", "false", "f", "no", "n", "nao", "não", "off"}

    if normalized_value in truthy_values:
        return True
    if normalized_value in falsy_values:
        return False
    return None


class EmpresaListView(BaseListView):
    model = Empresa
    service_class = EmpresaService
    template_name = "empresas/empresa_list.html"
    context_object_name = "empresas"

    def get_queryset(self):
        return self.get_service().listar(self.get_service_filters())

    def get_service_filters(self):
        return {
            "nome": self.request.GET.get("nome", "").strip(),
            "ativa": _parse_boolean_query_param(self.request.GET.get("ativa")),
            "cnpj": self.request.GET.get("cnpj", "").strip(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_listado = context["paginator"].count if context.get("paginator") else 0
        total_ativas = self.get_service().listar_ativas().count()

        context["filtros"] = {
            "nome": self.request.GET.get("nome", "").strip(),
            "ativa": self.request.GET.get("ativa", "").strip(),
            "cnpj": self.request.GET.get("cnpj", "").strip(),
        }
        context.update(
            {
                "page_title": "Empresas",
                "page_subtitle": "Cadastro mestre das empresas, contatos e dados comerciais.",
                "page_primary_action_url": reverse("empresas:create"),
                "page_primary_action_label": "Nova empresa",
                "empresa_kpis": [
                    {
                        "title": "Empresas",
                        "value": total_listado,
                        "helper": "Cadastros disponiveis na listagem",
                        "tone": "info",
                        "icon": "building",
                    },
                    {
                        "title": "Ativas",
                        "value": total_ativas,
                        "helper": "Empresas habilitadas para operacao",
                        "tone": "success",
                        "icon": "pulse",
                    },
                    {
                        "title": "Com CNPJ",
                        "value": self.get_service().total_com_cnpj(),
                        "helper": "Cadastros com identificacao preenchida",
                        "tone": "primary",
                        "icon": "search",
                    },
                ],
            }
        )
        return context


class EmpresaDetailView(BaseDetailView):
    model = Empresa
    service_class = EmpresaService
    template_name = "empresas/empresa_detail.html"
    context_object_name = "empresa"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_primary_action_url"] = reverse("empresas:update", args=[self.object.pk])
        context["page_primary_action_label"] = "Editar empresa"
        return context


class EmpresaCreateView(BaseCreateView):
    model = Empresa
    form_class = EmpresaForm
    service_class = EmpresaService
    template_name = "empresas/empresa_form.html"
    success_url = reverse_lazy("empresas:index")
    success_message = "Empresa cadastrada com sucesso."


class EmpresaUpdateView(BaseUpdateView):
    model = Empresa
    form_class = EmpresaForm
    service_class = EmpresaService
    template_name = "empresas/empresa_form.html"
    success_url = reverse_lazy("empresas:index")
    success_message = "Empresa atualizada com sucesso."


class EmpresaDeleteView(BaseDeleteView):
    model = Empresa
    service_class = EmpresaService
    template_name = "empresas/empresa_confirm_delete.html"
    success_url = reverse_lazy("empresas:index")
    success_message = "Empresa removida com sucesso."


class EnderecoEmpresaCreateView(BaseCreateView):
    model = EnderecoEmpresa
    form_class = EnderecoEmpresaForm
    service_class = EnderecoEmpresaService
    template_name = "empresas/enderecoempresa_form.html"
    success_url = reverse_lazy("empresas:index")
    success_message = "Endereco cadastrado com sucesso."


class EnderecoEmpresaUpdateView(BaseUpdateView):
    model = EnderecoEmpresa
    form_class = EnderecoEmpresaForm
    service_class = EnderecoEmpresaService
    template_name = "empresas/enderecoempresa_form.html"
    success_url = reverse_lazy("empresas:index")
    success_message = "Endereco atualizado com sucesso."


class ContatoEmpresaListView(BaseListView):
    model = ContatoEmpresa
    service_class = ContatoEmpresaService
    template_name = "empresas/contatoempresa_list.html"
    context_object_name = "contatos"

    def get_queryset(self):
        queryset = self.get_service().list()
        empresa_id = self.request.GET.get("empresa", "").strip()

        if empresa_id:
            queryset = queryset.filter(empresa_id=empresa_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtros"] = {
            "empresa": self.request.GET.get("empresa", "").strip(),
        }
        context.update(
            {
                "page_title": "Contatos",
                "page_subtitle": "Responsaveis comerciais e operacionais vinculados as empresas.",
                "page_primary_action_url": reverse("empresas:contato_create"),
                "page_primary_action_label": "Novo contato",
            }
        )
        return context


class ContatoEmpresaCreateView(BaseCreateView):
    model = ContatoEmpresa
    form_class = ContatoEmpresaForm
    service_class = ContatoEmpresaService
    template_name = "empresas/contatoempresa_form.html"
    success_url = reverse_lazy("empresas:index")
    success_message = "Contato cadastrado com sucesso."


class ContatoEmpresaUpdateView(BaseUpdateView):
    model = ContatoEmpresa
    form_class = ContatoEmpresaForm
    service_class = ContatoEmpresaService
    template_name = "empresas/contatoempresa_form.html"
    success_url = reverse_lazy("empresas:index")
    success_message = "Contato atualizado com sucesso."


index = EmpresaListView.as_view()
