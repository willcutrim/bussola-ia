from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.documentos.choices import StatusDocumentoChoices
from apps.documentos.services import DocumentoService


class DocumentoServiceUnitTests(SimpleTestCase):
    def setUp(self):
        self.repository = Mock()
        self.service = DocumentoService(repository=self.repository)

    def test_listar_delega_para_repository(self):
        filtros = {"nome": "Edital"}

        self.service.listar(filtros=filtros)

        self.repository.listar_com_filtros.assert_called_once_with(filtros=filtros)

    def test_obter_delega_para_repository(self):
        self.service.obter(10)

        self.repository.obter_por_id.assert_called_once_with(10)

    def test_criar_normaliza_dados_e_delega_persistencia(self):
        cleaned_data = {
            "licitacao": object(),
            "nome": "  Edital Principal  ",
            "arquivo": object(),
            "tipo": "edital",
            "status": "pendente",
            "observacoes": "  Observacao importante  ",
        }

        self.service.criar(cleaned_data)

        self.repository.create.assert_called_once_with(
            licitacao=cleaned_data["licitacao"],
            nome="Edital Principal",
            arquivo=cleaned_data["arquivo"],
            tipo="edital",
            status="pendente",
            observacoes="Observacao importante",
        )

    def test_atualizar_normaliza_dados_e_delega_persistencia(self):
        instance = Mock()
        cleaned_data = {
            "licitacao": object(),
            "nome": "  Proposta Comercial  ",
            "arquivo": object(),
            "tipo": "proposta",
            "status": "enviado",
            "observacoes": "  ",
        }

        self.service.atualizar(instance, cleaned_data)

        self.repository.update.assert_called_once_with(
            instance,
            licitacao=cleaned_data["licitacao"],
            nome="Proposta Comercial",
            arquivo=cleaned_data["arquivo"],
            tipo="proposta",
            status="enviado",
            observacoes="",
        )

    def test_listagens_utilitarias_delegam_para_repository(self):
        licitacao = object()

        self.service.listar_por_licitacao(licitacao)
        self.service.listar_pendentes()
        self.service.listar_validados()

        self.repository.listar_por_licitacao.assert_called_once_with(licitacao)
        self.repository.listar_pendentes.assert_called_once_with()
        self.repository.listar_validados.assert_called_once_with()

    def test_metodos_de_status_atualizam_via_repository(self):
        instance = Mock()

        self.service.marcar_como_pendente(instance)
        self.service.marcar_como_enviado(instance)
        self.service.marcar_como_validado(instance)
        self.service.marcar_como_rejeitado(instance)

        self.repository.update.assert_any_call(
            instance, status=StatusDocumentoChoices.PENDENTE
        )
        self.repository.update.assert_any_call(
            instance, status=StatusDocumentoChoices.ENVIADO
        )
        self.repository.update.assert_any_call(
            instance, status=StatusDocumentoChoices.VALIDADO
        )
        self.repository.update.assert_any_call(
            instance, status=StatusDocumentoChoices.REJEITADO
        )
        self.assertEqual(self.repository.update.call_count, 4)
