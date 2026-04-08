from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.utils.text import capfirst
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.mixins import (
    AppLoginRequiredMixin,
    FlashMessageMixin,
    RepositoryMixin,
    ServiceMixin,
)


class BaseListView(AppLoginRequiredMixin, ServiceMixin, RepositoryMixin, ListView):
    paginate_by = 20

    def get_queryset(self):
        if self.queryset is not None:
            return self.queryset.all()
        if self.service_class is not None:
            return self.get_service().list()
        if self.repository_class is not None:
            return self.get_repository().list()
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meta = self.model._meta
        context.setdefault("page_title", capfirst(meta.verbose_name_plural))
        context.setdefault("page_subtitle", f"Visao geral do modulo de {meta.verbose_name_plural}.")
        context.setdefault("status", "")
        return context


class BaseDetailView(AppLoginRequiredMixin, ServiceMixin, RepositoryMixin, DetailView):
    def get_queryset(self):
        if self.queryset is not None:
            return self.queryset.all()
        if self.service_class is not None:
            return self.get_service().list()
        if self.repository_class is not None:
            return self.get_repository().list()
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meta = self.model._meta
        context.setdefault("page_title", str(self.object))
        context.setdefault("page_subtitle", capfirst(meta.verbose_name))
        context.setdefault("status", "")
        return context


class BaseCreateView(
    AppLoginRequiredMixin, FlashMessageMixin, ServiceMixin, CreateView
):
    success_message = "Registro criado com sucesso."
    error_message = "Nao foi possivel criar o registro."

    def form_valid(self, form):
        try:
            self.object = self.perform_create(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)

        self.add_success_message()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        self.add_error_message()
        return super().form_invalid(form)

    def perform_create(self, form):
        if self.service_class is not None:
            service = self.get_service()
            if hasattr(service, "criar"):
                return service.criar(form.cleaned_data)
            return service.create(**form.cleaned_data)
        return form.save()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        verbose_name = capfirst(self.model._meta.verbose_name)
        context.setdefault("page_title", f"Nova {verbose_name}")
        context.setdefault("page_subtitle", "Preencha os dados principais antes de salvar.")
        context.setdefault("status", "")
        return context


class BaseUpdateView(
    AppLoginRequiredMixin, FlashMessageMixin, ServiceMixin, UpdateView
):
    success_message = "Registro atualizado com sucesso."
    error_message = "Nao foi possivel atualizar o registro."

    def form_valid(self, form):
        self.object = self.get_object()
        try:
            self.object = self.perform_update(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)

        self.add_success_message()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        self.add_error_message()
        return super().form_invalid(form)

    def perform_update(self, form):
        if self.service_class is not None:
            service = self.get_service()
            if hasattr(service, "atualizar"):
                return service.atualizar(self.object, form.cleaned_data)
            return service.update(self.object, **form.cleaned_data)
        return form.save()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        verbose_name = capfirst(self.model._meta.verbose_name)
        context.setdefault("page_title", f"Editar {verbose_name}")
        context.setdefault("page_subtitle", "Revise os dados e confirme as alteracoes.")
        context.setdefault("status", "")
        return context


class BaseDeleteView(
    AppLoginRequiredMixin, FlashMessageMixin, ServiceMixin, DeleteView
):
    success_message = "Registro removido com sucesso."
    error_message = "Nao foi possivel remover o registro."

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.perform_delete(self.object)
        except ValidationError:
            self.add_error_message()
            return HttpResponseRedirect(self.get_success_url())

        self.add_success_message()
        return HttpResponseRedirect(self.get_success_url())

    def perform_delete(self, instance):
        if self.service_class is not None:
            return self.get_service().delete(instance)
        return instance.delete()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        verbose_name = capfirst(self.model._meta.verbose_name)
        context.setdefault("page_title", f"Excluir {verbose_name}")
        context.setdefault("page_subtitle", "Esta acao remove o registro da visao principal do sistema.")
        context.setdefault("status", "")
        return context
