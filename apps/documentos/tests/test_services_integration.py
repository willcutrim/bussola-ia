from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TransactionTestCase

from apps.documentos.choices import StatusDocumentoChoices, TipoDocumentoChoices
from apps.documentos.models import Documento
from apps.documentos.services import DocumentoService
from apps.empresas.models import Empresa
from apps.licitacoes.choices import ModalidadeChoices, SituacaoChoices
from apps.licitacoes.models import Licitacao


class DocumentoServiceIntegrationTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Documento)

    @classmethod
    def tearDownClass(cls):
        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(Documento)
        finally:
            super().tearDownClass()

    def setUp(self):
        self.service = DocumentoService()
        self.empresa_alpha = Empresa.objects.create(
            nome="Alpha Consultoria",
            cnpj="12.345.678/0001-90",
            ativa=True,
        )
        self.licitacao_alpha = Licitacao.objects.create(
            empresa=self.empresa_alpha,
            numero="PE-001/2026",
            objeto="Contratacao de servicos de tecnologia",
            orgao="Prefeitura de Fortaleza",
            modalidade=ModalidadeChoices.PREGAO,
            situacao=SituacaoChoices.EM_ANALISE,
            data_abertura=date(2026, 4, 20),
            ativa=True,
        )
        self.licitacao_beta = Licitacao.objects.create(
            empresa=self.empresa_alpha,
            numero="CC-002/2026",
            objeto="Obra de infraestrutura",
            orgao="Governo do Estado",
            modalidade=ModalidadeChoices.CONCORRENCIA,
            situacao=SituacaoChoices.EM_ANDAMENTO,
            data_abertura=date(2026, 5, 10),
            ativa=True,
        )

        self.documento_alpha = Documento.objects.create(
            licitacao=self.licitacao_alpha,
            nome="Edital Alpha",
            arquivo=SimpleUploadedFile("edital-alpha.pdf", b"alpha"),
            tipo=TipoDocumentoChoices.EDITAL,
            status=StatusDocumentoChoices.PENDENTE,
            observacoes="Primeiro documento",
        )
        self.documento_beta = Documento.objects.create(
            licitacao=self.licitacao_beta,
            nome="Contrato Beta",
            arquivo=SimpleUploadedFile("contrato-beta.pdf", b"beta"),
            tipo=TipoDocumentoChoices.CONTRATO,
            status=StatusDocumentoChoices.VALIDADO,
            observacoes="Documento final",
        )

    def test_criar_documento_persiste_corretamente(self):
        documento = self.service.criar(
            {
                "licitacao": self.licitacao_alpha,
                "nome": "  Proposta Alpha  ",
                "arquivo": SimpleUploadedFile("proposta-alpha.pdf", b"proposta"),
                "tipo": TipoDocumentoChoices.PROPOSTA,
                "status": StatusDocumentoChoices.ENVIADO,
                "observacoes": "  Nova proposta  ",
            }
        )

        self.assertEqual(documento.nome, "Proposta Alpha")
        self.assertEqual(documento.observacoes, "Nova proposta")
        self.assertTrue(Documento.objects.filter(nome="Proposta Alpha").exists())

    def test_atualizar_documento_persiste_corretamente(self):
        documento = self.service.atualizar(
            self.documento_alpha,
            {
                "licitacao": self.licitacao_alpha,
                "nome": "  Edital Alpha Atualizado  ",
                "arquivo": self.documento_alpha.arquivo,
                "tipo": TipoDocumentoChoices.EDITAL,
                "status": StatusDocumentoChoices.ENVIADO,
                "observacoes": "  Ajustado  ",
            },
        )

        self.documento_alpha.refresh_from_db()
        self.assertEqual(documento.nome, "Edital Alpha Atualizado")
        self.assertEqual(self.documento_alpha.status, StatusDocumentoChoices.ENVIADO)
        self.assertEqual(self.documento_alpha.observacoes, "Ajustado")

    def test_listar_com_filtros_retorna_resultados_esperados(self):
        documentos = list(
            self.service.listar(
                {
                    "licitacao": self.licitacao_alpha,
                    "nome": "edital",
                    "tipo": TipoDocumentoChoices.EDITAL,
                    "status": StatusDocumentoChoices.PENDENTE,
                }
            )
        )

        self.assertEqual(documentos, [self.documento_alpha])

    def test_listar_por_licitacao_funciona_corretamente(self):
        documentos = list(self.service.listar_por_licitacao(self.licitacao_beta))

        self.assertEqual(documentos, [self.documento_beta])

    def test_listagens_por_status_funcionam_corretamente(self):
        pendentes = list(self.service.listar_pendentes())
        validados = list(self.service.listar_validados())

        self.assertEqual(pendentes, [self.documento_alpha])
        self.assertEqual(validados, [self.documento_beta])

    def test_metodos_de_mudanca_de_status_persistem_no_banco(self):
        self.service.marcar_como_enviado(self.documento_alpha)
        self.documento_alpha.refresh_from_db()
        self.assertEqual(self.documento_alpha.status, StatusDocumentoChoices.ENVIADO)

        self.service.marcar_como_validado(self.documento_alpha)
        self.documento_alpha.refresh_from_db()
        self.assertEqual(self.documento_alpha.status, StatusDocumentoChoices.VALIDADO)

        self.service.marcar_como_rejeitado(self.documento_alpha)
        self.documento_alpha.refresh_from_db()
        self.assertEqual(self.documento_alpha.status, StatusDocumentoChoices.REJEITADO)
