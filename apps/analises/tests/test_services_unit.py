from datetime import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from apps.analises.choices import StatusAnaliseChoices
from apps.analises.services import AnaliseService


class AnaliseServiceUnitTests(SimpleTestCase):
    def setUp(self):
        self.repository = Mock()
        self.service = AnaliseService(repository=self.repository)

    def test_listar_delega_para_repository(self):
        filtros = {"titulo": "juridica"}

        self.service.listar(filtros=filtros)

        self.repository.listar_com_filtros.assert_called_once_with(filtros=filtros)

    def test_obter_delega_para_repository(self):
        self.service.obter(12)

        self.repository.obter_por_id.assert_called_once_with(12)

    @patch("apps.analises.services.timezone.now")
    def test_criar_normaliza_dados_e_preenche_concluida_em_quando_concluida(
        self, mocked_now
    ):
        concluded_at = timezone.make_aware(datetime(2026, 4, 6, 10, 0, 0))
        mocked_now.return_value = concluded_at
        cleaned_data = {
            "licitacao": object(),
            "documento": object(),
            "titulo": "  Analise documental final  ",
            "descricao": "  Revisao do edital  ",
            "status": StatusAnaliseChoices.CONCLUIDA,
            "parecer": "  Apto para envio  ",
            "prioridade": "alta",
            "responsavel": object(),
            "concluida_em": None,
        }

        self.service.criar(cleaned_data)

        self.repository.create.assert_called_once_with(
            licitacao=cleaned_data["licitacao"],
            documento=cleaned_data["documento"],
            titulo="Analise documental final",
            descricao="Revisao do edital",
            status=StatusAnaliseChoices.CONCLUIDA,
            parecer="Apto para envio",
            prioridade="alta",
            responsavel=cleaned_data["responsavel"],
            concluida_em=concluded_at,
        )

    def test_atualizar_limpa_concluida_em_quando_status_deixa_de_ser_concluida(self):
        instance = Mock()
        cleaned_data = {
            "licitacao": object(),
            "documento": None,
            "titulo": "  Analise reaberta  ",
            "descricao": "  Ajuste pendente  ",
            "status": StatusAnaliseChoices.EM_ANDAMENTO,
            "parecer": "  ",
            "prioridade": "media",
            "responsavel": object(),
            "concluida_em": timezone.now(),
        }

        self.service.atualizar(instance, cleaned_data)

        self.repository.update.assert_called_once_with(
            instance,
            licitacao=cleaned_data["licitacao"],
            documento=None,
            titulo="Analise reaberta",
            descricao="Ajuste pendente",
            status=StatusAnaliseChoices.EM_ANDAMENTO,
            parecer="",
            prioridade="media",
            responsavel=cleaned_data["responsavel"],
            concluida_em=None,
        )

    def test_listagens_utilitarias_delegam_para_repository(self):
        licitacao = object()
        documento = object()
        responsavel = object()

        self.service.listar_por_licitacao(licitacao)
        self.service.listar_por_documento(documento)
        self.service.listar_por_responsavel(responsavel)
        self.service.listar_pendentes()
        self.service.listar_em_andamento()
        self.service.listar_concluidas()

        self.repository.listar_por_licitacao.assert_called_once_with(licitacao)
        self.repository.listar_por_documento.assert_called_once_with(documento)
        self.repository.listar_por_responsavel.assert_called_once_with(responsavel)
        self.repository.listar_pendentes.assert_called_once_with()
        self.repository.listar_em_andamento.assert_called_once_with()
        self.repository.listar_concluidas.assert_called_once_with()

    @patch("apps.analises.services.timezone.now")
    def test_metodos_de_status_atualizam_conclusao_corretamente(self, mocked_now):
        concluded_at = timezone.make_aware(datetime(2026, 4, 6, 11, 30, 0))
        mocked_now.return_value = concluded_at
        instance = Mock(concluida_em=None)

        self.service.marcar_como_pendente(instance)
        self.service.marcar_como_em_andamento(instance)
        self.service.marcar_como_concluida(instance)
        self.service.marcar_como_rejeitada(instance)

        self.repository.update.assert_any_call(
            instance,
            status=StatusAnaliseChoices.PENDENTE,
            concluida_em=None,
        )
        self.repository.update.assert_any_call(
            instance,
            status=StatusAnaliseChoices.EM_ANDAMENTO,
            concluida_em=None,
        )
        self.repository.update.assert_any_call(
            instance,
            status=StatusAnaliseChoices.CONCLUIDA,
            concluida_em=concluded_at,
        )
        self.repository.update.assert_any_call(
            instance,
            status=StatusAnaliseChoices.REJEITADA,
            concluida_em=None,
        )
        self.assertEqual(self.repository.update.call_count, 4)
