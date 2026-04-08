from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel


class Empresa(BaseModel):
    nome = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True)
    razao_social = models.CharField(max_length=255, blank=True)
    cnpj = models.CharField(max_length=18, blank=True, null=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    site = models.URLField(blank=True)
    ativa = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ("nome",)
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        constraints = [
            models.UniqueConstraint(
                fields=("cnpj",),
                condition=Q(cnpj__isnull=False)
                & ~Q(cnpj="")
                & Q(deleted_at__isnull=True),
                name="uniq_empresa_cnpj_ativo_quando_preenchido",
            ),
        ]

    def __str__(self):
        return self.nome


class EnderecoEmpresa(BaseModel):
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name="endereco",
    )
    logradouro = models.CharField(max_length=255)
    numero = models.CharField(max_length=20, blank=True)
    complemento = models.CharField(max_length=255, blank=True)
    bairro = models.CharField(max_length=120, blank=True)
    cidade = models.CharField(max_length=120)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=12, blank=True)

    class Meta:
        verbose_name = "Endereço da empresa"
        verbose_name_plural = "Endereços das empresas"

    def __str__(self):
        cidade_estado = f"{self.cidade}/{self.estado}"
        return f"{self.empresa.nome} - {cidade_estado}"


class ContatoEmpresa(BaseModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="contatos",
    )
    nome = models.CharField(max_length=255)
    cargo = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    principal = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("nome",)
        verbose_name = "Contato da empresa"
        verbose_name_plural = "Contatos das empresas"
        constraints = [
            models.UniqueConstraint(
                fields=("empresa",),
                condition=Q(principal=True) & Q(deleted_at__isnull=True),
                name="uniq_contato_principal_ativo_por_empresa",
            ),
        ]

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"
