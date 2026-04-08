from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import json

from apps.core.forms import BootstrapFormMixin
from apps.documentos.models import Documento
from apps.licitacoes.models import Licitacao

from .choices import PrioridadeAnaliseChoices, StatusAnaliseChoices
from .models import Analise


class AnaliseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Analise
        fields = (
            "licitacao",
            "documento",
            "titulo",
            "descricao",
            "status",
            "parecer",
            "prioridade",
            "responsavel",
        )
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 5}),
            "parecer": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["licitacao"].queryset = Licitacao.objects.select_related("empresa")
        self.fields["documento"].queryset = Documento.objects.select_related(
            "licitacao",
            "licitacao__empresa",
        )
        self.fields["responsavel"].queryset = get_user_model().objects.all()

    def clean_titulo(self):
        titulo = self.cleaned_data.get("titulo", "")
        return " ".join(titulo.split())

    def clean_descricao(self):
        descricao = self.cleaned_data.get("descricao", "")
        if not descricao:
            return ""
        return descricao.strip()

    def clean_parecer(self):
        parecer = self.cleaned_data.get("parecer", "")
        if not parecer:
            return ""
        return parecer.strip()

    def clean_documento(self):
        documento = self.cleaned_data.get("documento")
        licitacao = self.cleaned_data.get("licitacao")

        if documento and licitacao and documento.licitacao_id != licitacao.pk:
            raise ValidationError(
                "O documento selecionado precisa pertencer a licitacao informada."
            )

        return documento


class AnaliseFiltroForm(BootstrapFormMixin, forms.Form):
    licitacao = forms.ModelChoiceField(
        queryset=Licitacao.objects.select_related("empresa"),
        required=False,
        empty_label="---------",
    )
    documento = forms.ModelChoiceField(
        queryset=Documento.objects.select_related("licitacao", "licitacao__empresa"),
        required=False,
        empty_label="---------",
    )
    titulo = forms.CharField(required=False)
    status = forms.ChoiceField(
        required=False,
        choices=(("", "---------"), *StatusAnaliseChoices.choices),
    )
    prioridade = forms.ChoiceField(
        required=False,
        choices=(("", "---------"), *PrioridadeAnaliseChoices.choices),
    )
    responsavel = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        empty_label="---------",
    )
    data_analise_inicial = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    data_analise_final = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )


class AnaliseAIBaseForm(forms.Form):
    analise = forms.ModelChoiceField(queryset=Analise.objects.select_related("licitacao", "documento"), required=False)
    licitacao = forms.ModelChoiceField(queryset=Licitacao.objects.select_related("empresa"), required=False)
    documento = forms.ModelChoiceField(
        queryset=Documento.objects.select_related("licitacao", "licitacao__empresa"),
        required=False,
    )
    texto_documento = forms.CharField(required=False, widget=forms.Textarea)
    persistir = forms.BooleanField(required=False)

    require_text = False
    require_licitacao = False

    def clean(self):
        cleaned_data = super().clean()
        analise = cleaned_data.get("analise")
        licitacao = cleaned_data.get("licitacao")
        documento = cleaned_data.get("documento")
        texto_documento = cleaned_data.get("texto_documento", "")

        if analise and not licitacao:
            cleaned_data["licitacao"] = analise.licitacao
            licitacao = analise.licitacao

        if analise and not documento and analise.documento_id:
            cleaned_data["documento"] = analise.documento
            documento = analise.documento

        if documento and not licitacao:
            cleaned_data["licitacao"] = documento.licitacao
            licitacao = documento.licitacao

        if documento and licitacao and documento.licitacao_id != licitacao.pk:
            raise ValidationError(
                "O documento informado precisa pertencer a licitacao selecionada."
            )

        if analise and licitacao and analise.licitacao_id != licitacao.pk:
            raise ValidationError(
                "A analise informada precisa pertencer a licitacao selecionada."
            )

        if analise and documento and analise.documento_id and analise.documento_id != documento.pk:
            raise ValidationError(
                "A analise informada precisa estar vinculada ao documento selecionado."
            )

        if self.require_licitacao and not licitacao:
            raise ValidationError("A licitacao e obrigatoria para esta operacao.")

        if self.require_text and not texto_documento.strip():
            raise ValidationError("O texto do documento e obrigatorio para esta operacao.")

        return cleaned_data


class DocumentoSummaryAIForm(AnaliseAIBaseForm):
    require_text = True


class ExtractionAIForm(AnaliseAIBaseForm):
    require_text = True
    campos_alvo = forms.CharField(required=False)

    def clean_campos_alvo(self):
        value = self.cleaned_data.get("campos_alvo", "")
        if not value:
            return []

        value = value.strip()
        if not value:
            return []

        if value.startswith("["):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValidationError("campos_alvo precisa ser JSON valido ou lista separada por virgulas.") from exc
            if not isinstance(parsed, list):
                raise ValidationError("campos_alvo em JSON precisa ser uma lista.")
            return [str(item).strip() for item in parsed if str(item).strip()]

        return [item.strip() for item in value.split(",") if item.strip()]


class TechnicalAnalysisAIForm(AnaliseAIBaseForm):
    require_text = True
    require_licitacao = True


class ComparisonAIForm(AnaliseAIBaseForm):
    require_text = True
    require_licitacao = True


class ChecklistAIForm(AnaliseAIBaseForm):
    comparison_contexto = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        texto_documento = cleaned_data.get("texto_documento", "").strip()
        licitacao = cleaned_data.get("licitacao")
        documento = cleaned_data.get("documento")
        comparison_contexto = cleaned_data.get("comparison_contexto")

        if not texto_documento and not licitacao and not documento and not comparison_contexto:
            raise ValidationError(
                "Informe pelo menos texto_documento, licitacao, documento ou comparison_contexto."
            )

        return cleaned_data

    def clean_comparison_contexto(self):
        value = self.cleaned_data.get("comparison_contexto", "")
        if not value:
            return None
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValidationError("comparison_contexto precisa ser JSON valido.") from exc
        if not isinstance(parsed, dict):
            raise ValidationError("comparison_contexto precisa ser um objeto JSON.")
        return parsed


class PriorityClassificationAIForm(AnaliseAIBaseForm):
    require_text = True
