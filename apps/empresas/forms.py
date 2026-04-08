from django import forms
from django.core.exceptions import ValidationError

from apps.core.forms import BootstrapFormMixin

from .models import ContatoEmpresa, Empresa, EnderecoEmpresa


class EmpresaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Empresa
        fields = (
            "nome",
            "nome_fantasia",
            "razao_social",
            "cnpj",
            "email",
            "telefone",
            "site",
            "ativa",
            "observacoes",
        )
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cnpj"].widget.attrs.update(
            {"data-mask": "cnpj", "inputmode": "numeric", "placeholder": "00.000.000/0000-00"}
        )
        self.fields["telefone"].widget.attrs.update(
            {"data-mask": "phone", "inputmode": "numeric", "autocomplete": "tel"}
        )

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if not cnpj:
            return None

        cnpj_digits = "".join(char for char in cnpj if char.isdigit())
        if len(cnpj_digits) != 14:
            raise ValidationError("Informe um CNPJ com 14 digitos.")

        return cnpj_digits


class EnderecoEmpresaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = EnderecoEmpresa
        fields = (
            "empresa",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "cep",
        )

    def clean_estado(self):
        estado = self.cleaned_data.get("estado", "")
        return estado.strip().upper()

    def clean_cep(self):
        cep = self.cleaned_data.get("cep")
        if not cep:
            return ""
        return "".join(char for char in cep if char.isdigit())


class ContatoEmpresaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ContatoEmpresa
        fields = (
            "empresa",
            "nome",
            "cargo",
            "email",
            "telefone",
            "principal",
            "ativo",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["telefone"].widget.attrs.update(
            {"data-mask": "phone", "inputmode": "numeric", "autocomplete": "tel"}
        )
