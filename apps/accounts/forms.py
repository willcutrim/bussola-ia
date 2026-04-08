from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from apps.core.forms import BootstrapFormMixin

from .models import User


BOOLEAN_FILTER_CHOICES = (
    ("", "---------"),
    ("true", "Sim"),
    ("false", "Nao"),
)


def _normalize_spaces(value):
    if not value:
        return ""
    return " ".join(value.split())


def _normalize_email(value):
    if not value:
        return ""
    return value.strip().lower()


class AccountLoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "placeholder": "Seu usuario"}
        )
        self.fields["password"].widget.attrs.update(
            {
                "autocomplete": "current-password",
                "placeholder": "Sua senha",
                "data-password-toggle": "true",
            }
        )


class UserForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "nome_completo",
            "telefone",
            "ativo",
            "deve_trocar_senha",
            "is_staff",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["telefone"].widget.attrs.update(
            {"data-mask": "phone", "inputmode": "numeric", "autocomplete": "tel"}
        )

    def clean_username(self):
        username = self.cleaned_data.get("username", "")
        return _normalize_spaces(username)

    def clean_email(self):
        email = self.cleaned_data.get("email", "")
        return _normalize_email(email)

    def clean_nome_completo(self):
        nome_completo = self.cleaned_data.get("nome_completo", "")
        return _normalize_spaces(nome_completo)

    def clean_telefone(self):
        telefone = self.cleaned_data.get("telefone", "")
        if not telefone:
            return ""
        return telefone.strip()


class UserCreateForm(UserForm):
    password1 = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"data-password-toggle": "true"},
        ),
    )
    password2 = forms.CharField(
        label="Confirmacao de senha",
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"data-password-toggle": "true"},
        ),
    )

    class Meta(UserForm.Meta):
        fields = UserForm.Meta.fields

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 != password2:
            raise ValidationError("As senhas informadas precisam ser iguais.")

        return cleaned_data


class SignupForm(BootstrapFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"data-password-toggle": "true"},
        ),
    )
    password2 = forms.CharField(
        label="Confirmacao de senha",
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"data-password-toggle": "true"},
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email", "nome_completo", "telefone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["email"].label = "E-mail"
        self.fields["nome_completo"].label = "Nome completo"
        self.fields["telefone"].label = "Telefone"
        self.fields["username"].widget.attrs["placeholder"] = "Escolha um usuario"
        self.fields["email"].widget.attrs["placeholder"] = "voce@empresa.com"
        self.fields["nome_completo"].widget.attrs["placeholder"] = "Seu nome completo"
        self.fields["telefone"].widget.attrs.update(
            {
                "placeholder": "(00) 00000-0000",
                "data-mask": "phone",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }
        )
        self.fields["password1"].widget.attrs["placeholder"] = "Defina uma senha"
        self.fields["password2"].widget.attrs["placeholder"] = "Confirme a senha"

    def clean_username(self):
        username = self.cleaned_data.get("username", "")
        return _normalize_spaces(username)

    def clean_email(self):
        email = self.cleaned_data.get("email", "")
        return _normalize_email(email)

    def clean_nome_completo(self):
        nome_completo = self.cleaned_data.get("nome_completo", "")
        return _normalize_spaces(nome_completo)

    def clean_telefone(self):
        telefone = self.cleaned_data.get("telefone", "")
        if not telefone:
            return ""
        return telefone.strip()

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 != password2:
            raise ValidationError("As senhas informadas precisam ser iguais.")

        return cleaned_data


class UserFiltroForm(BootstrapFormMixin, forms.Form):
    username = forms.CharField(required=False)
    email = forms.CharField(required=False)
    nome_completo = forms.CharField(required=False)
    ativo = forms.ChoiceField(required=False, choices=BOOLEAN_FILTER_CHOICES)
    is_staff = forms.ChoiceField(required=False, choices=BOOLEAN_FILTER_CHOICES)
    is_superuser = forms.ChoiceField(required=False, choices=BOOLEAN_FILTER_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["username"].widget.attrs["placeholder"] = "Buscar por username"
        self.fields["email"].label = "E-mail"
        self.fields["email"].widget.attrs["placeholder"] = "Buscar por e-mail"
        self.fields["nome_completo"].label = "Nome completo"
        self.fields["nome_completo"].widget.attrs["placeholder"] = "Buscar por nome"
        self.fields["ativo"].label = "Status"
        self.fields["is_staff"].label = "Equipe interna"
        self.fields["is_superuser"].label = "Superusuario"
