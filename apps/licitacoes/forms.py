from django import forms

from apps.core.forms import BootstrapFormMixin
from apps.empresas.models import Empresa

from .choices import ModalidadeChoices, SituacaoChoices
from .models import Licitacao


ATIVA_CHOICES = (
    ("", "---------"),
    ("true", "Ativas"),
    ("false", "Inativas"),
)


class LicitacaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Licitacao
        fields = (
            "empresa",
            "numero",
            "objeto",
            "orgao",
            "modalidade",
            "situacao",
            "data_abertura",
            "valor_estimado",
            "link_externo",
            "observacoes",
            "ativa",
        )
        widgets = {
            "data_abertura": forms.DateInput(attrs={"type": "date"}),
            "valor_estimado": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "observacoes": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_numero(self):
        numero = self.cleaned_data.get("numero", "")
        return " ".join(numero.split())

    def clean_orgao(self):
        orgao = self.cleaned_data.get("orgao", "")
        return " ".join(orgao.split())

    def clean_link_externo(self):
        link_externo = self.cleaned_data.get("link_externo")
        if not link_externo:
            return ""
        return link_externo.strip()


class LicitacaoFiltroForm(BootstrapFormMixin, forms.Form):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        required=False,
        empty_label="---------",
    )
    numero = forms.CharField(required=False)
    orgao = forms.CharField(required=False)
    modalidade = forms.ChoiceField(
        required=False,
        choices=(("", "---------"), *ModalidadeChoices.choices),
    )
    situacao = forms.ChoiceField(
        required=False,
        choices=(("", "---------"), *SituacaoChoices.choices),
    )
    ativa = forms.ChoiceField(required=False, choices=ATIVA_CHOICES)
    data_abertura_inicial = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    data_abertura_final = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
