from django import forms

from apps.core.forms import BootstrapFormMixin
from apps.licitacoes.models import Licitacao

from .choices import StatusDocumentoChoices, TipoDocumentoChoices
from .models import Documento


class DocumentoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Documento
        fields = (
            "licitacao",
            "nome",
            "arquivo",
            "tipo",
            "status",
            "observacoes",
        )
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_nome(self):
        nome = self.cleaned_data.get("nome", "")
        return " ".join(nome.split())

    def clean_observacoes(self):
        observacoes = self.cleaned_data.get("observacoes", "")
        if not observacoes:
            return ""
        return observacoes.strip()


class DocumentoFiltroForm(BootstrapFormMixin, forms.Form):
    licitacao = forms.ModelChoiceField(
        queryset=Licitacao.objects.select_related("empresa"),
        required=False,
        empty_label="---------",
    )
    nome = forms.CharField(required=False)
    tipo = forms.ChoiceField(
        required=False,
        choices=(("", "---------"), *TipoDocumentoChoices.choices),
    )
    status = forms.ChoiceField(
        required=False,
        choices=(("", "---------"), *StatusDocumentoChoices.choices),
    )
    data_upload_inicial = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    data_upload_final = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
