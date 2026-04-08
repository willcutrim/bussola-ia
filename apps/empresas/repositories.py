from apps.core.repositories import BaseRepository

from .models import ContatoEmpresa, Empresa, EnderecoEmpresa


class EmpresaRepository(BaseRepository):
    model = Empresa

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("endereco")
            .prefetch_related("contatos")
            .order_by("nome")
        )

    def listar_com_filtros(self, filtros=None):
        filtros = filtros or {}
        queryset = self.get_queryset()

        nome = filtros.get("nome")
        if nome:
            queryset = queryset.filter(nome__icontains=nome)

        ativa = filtros.get("ativa")
        if ativa not in (None, ""):
            queryset = queryset.filter(ativa=ativa)

        cnpj = filtros.get("cnpj")
        if cnpj:
            queryset = queryset.filter(cnpj__icontains=cnpj)

        return queryset

    def obter_por_id(self, pk):
        return self.get_by_id(pk)

    def obter_por_cnpj(self, cnpj):
        return self.get_queryset().filter(cnpj=cnpj).first()

    def listar_ativas(self):
        return self.get_queryset().filter(ativa=True)

    def total_com_cnpj(self):
        return self.get_queryset().exclude(cnpj__isnull=True).exclude(cnpj="").count()


class EnderecoEmpresaRepository(BaseRepository):
    model = EnderecoEmpresa

    def get_queryset(self):
        return super().get_queryset().select_related("empresa").order_by("empresa__nome")

    def listar_por_empresa(self, empresa):
        return self.get_queryset().filter(empresa=empresa)

    def obter_por_empresa(self, empresa):
        return self.get_queryset().filter(empresa=empresa).first()


class ContatoEmpresaRepository(BaseRepository):
    model = ContatoEmpresa

    def get_queryset(self):
        return super().get_queryset().select_related("empresa").order_by("nome")

    def listar_por_empresa(self, empresa):
        return self.get_queryset().filter(empresa=empresa)

    def listar_ativos_por_empresa(self, empresa):
        return self.listar_por_empresa(empresa).filter(ativo=True)

    def obter_principal_por_empresa(self, empresa):
        return self.listar_ativos_por_empresa(empresa).filter(principal=True).first()
