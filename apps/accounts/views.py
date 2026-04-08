from django.conf import settings
from django.contrib.auth import login as auth_login
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView
from django.urls import reverse_lazy

from apps.core.mixins import FlashMessageMixin, ServiceMixin
from apps.core.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from .forms import AccountLoginForm, SignupForm, UserCreateForm, UserFiltroForm, UserForm
from .models import User
from .services import UserService


class AccountLoginView(LoginView):
    authentication_form = AccountLoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", "Entrar")
        context.setdefault(
            "page_subtitle",
            "Acesse o painel para gerenciar empresas, licitacoes, documentos e analises.",
        )
        return context


class AccountLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


class AccountSignupView(FlashMessageMixin, ServiceMixin, CreateView):
    model = User
    form_class = SignupForm
    service_class = UserService
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("home")
    success_message = "Conta criada com sucesso. Seu acesso ja esta liberado."
    error_message = "Nao foi possivel criar a conta."

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cleaned_data = {
            key: value
            for key, value in form.cleaned_data.items()
            if key not in {"password1", "password2"}
        }

        try:
            self.object = self.get_service().criar_usuario(
                cleaned_data,
                senha=form.cleaned_data.get("password1"),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)

        backend = settings.AUTHENTICATION_BACKENDS[0]
        auth_login(self.request, self.object, backend=backend)
        self.add_success_message()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        self.add_error_message()
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", "Criar conta")
        context.setdefault(
            "page_subtitle",
            "Cadastre seu acesso para entrar no painel e continuar a operacao.",
        )
        return context


class UserListView(BaseListView):
    model = User
    service_class = UserService
    template_name = "accounts/user_list.html"
    context_object_name = "usuarios"

    def get_queryset(self):
        return self.get_service().listar(self.get_filter_data())

    def get_filter_form(self):
        return UserFiltroForm(self.request.GET or None)

    def get_filter_data(self):
        filter_form = self.get_filter_form()
        if filter_form.is_valid():
            return filter_form.cleaned_data
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuarios_qs = self.get_service().listar()
        context["filtro_form"] = kwargs.get("filtro_form") or self.get_filter_form()
        context["filtros_atuais"] = self.get_filter_data()
        context["accounts_kpis"] = [
            {
                "title": "Usuarios",
                "value": usuarios_qs.count(),
                "helper": "contas mapeadas no painel",
                "tone": "primary",
                "icon": "users",
            },
            {
                "title": "Ativos",
                "value": self.get_service().total_ativos(),
                "helper": "acessos liberados no momento",
                "tone": "success",
                "icon": "shield",
            },
            {
                "title": "Equipe interna",
                "value": self.get_service().total_staff(),
                "helper": "usuarios com permissao administrativa",
                "tone": "info",
                "icon": "briefcase",
            },
            {
                "title": "Troca de senha",
                "value": usuarios_qs.filter(deve_trocar_senha=True).count(),
                "helper": "contas com revisao pendente",
                "tone": "warning",
                "icon": "key",
            },
        ]
        return context


class UserDetailView(BaseDetailView):
    model = User
    service_class = UserService
    template_name = "accounts/user_detail.html"
    context_object_name = "usuario"


class UserCreateView(BaseCreateView):
    model = User
    form_class = UserCreateForm
    service_class = UserService
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:list")
    success_message = "Usuario cadastrado com sucesso."

    def perform_create(self, form):
        cleaned_data = {
            key: value
            for key, value in form.cleaned_data.items()
            if key not in {"password1", "password2"}
        }
        return self.get_service().criar_usuario(
            cleaned_data,
            senha=form.cleaned_data.get("password1"),
        )


class UserUpdateView(BaseUpdateView):
    model = User
    form_class = UserForm
    service_class = UserService
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:list")
    success_message = "Usuario atualizado com sucesso."


class UserDeleteView(BaseDeleteView):
    model = User
    service_class = UserService
    template_name = "accounts/user_confirm_delete.html"
    success_url = reverse_lazy("accounts:list")
    success_message = "Usuario removido com sucesso."


index = UserListView.as_view()
