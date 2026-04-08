from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured


class AppLoginRequiredMixin(LoginRequiredMixin):
    redirect_field_name = "next"


class FlashMessageMixin:
    success_message = ""
    error_message = ""

    def get_success_message(self):
        return self.success_message

    def get_error_message(self):
        return self.error_message

    def add_success_message(self, message=None):
        resolved_message = message or self.get_success_message()
        if resolved_message:
            messages.success(self.request, resolved_message)

    def add_error_message(self, message=None):
        resolved_message = message or self.get_error_message()
        if resolved_message:
            messages.error(self.request, resolved_message)


class RepositoryMixin:
    repository_class = None
    repository = None

    def get_repository_class(self):
        if self.repository_class is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define repository_class."
            )
        return self.repository_class

    def get_repository(self):
        if self.repository is not None:
            return self.repository

        repository_class = self.get_repository_class()
        self.repository = repository_class()
        return self.repository


class ServiceMixin:
    service_class = None
    service = None

    def get_service_class(self):
        if self.service_class is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define service_class."
            )
        return self.service_class

    def get_service(self):
        if self.service is not None:
            return self.service

        service_class = self.get_service_class()
        service_kwargs = {}

        if getattr(self, "repository_class", None) is not None and hasattr(
            self, "get_repository"
        ):
            service_kwargs["repository"] = self.get_repository()

        self.service = service_class(**service_kwargs)
        return self.service
