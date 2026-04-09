from __future__ import annotations

import shutil
import tempfile

from django.test import TestCase, override_settings

from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.models import Licitacao
from apps.licitacoes.services_importacao import ImportacaoPNCPService


class _FakePNCPClient:
    def __init__(self, *, contratacoes=None, arquivos_por_controle=None):
        self._contratacoes = contratacoes or []
        self._arquivos_por_controle = arquivos_por_controle or {}

    def buscar_contratacoes_por_periodo(self, **kwargs):
        return self._contratacoes

    def buscar_arquivos_da_compra(self, numero_controle_pncp):
        return self._arquivos_por_controle.get(numero_controle_pncp, [])


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class ImportacaoPNCPIntegrationTests(TestCase):
    def setUp(self):
        self.tmp_media = tempfile.mkdtemp(prefix="test-media-")
        self.override_media = override_settings(MEDIA_ROOT=self.tmp_media)
        self.override_media.enable()

    def tearDown(self):
        self.override_media.disable()
        shutil.rmtree(self.tmp_media, ignore_errors=True)

    def _payload_base(self):
        return {
            "numeroControlePNCP": "PNCP-CTRL-001",
            "numeroCompra": "45",
            "anoCompra": 2026,
            "sequencialCompra": "0001",
            "processo": "PROC-2026-11",
            "objetoCompra": "Contratacao de plataforma de dados",
            "modalidadeNome": "Pregao",
            "situacaoCompraNome": "Recebendo proposta",
            "dataPublicacaoPncp": "2026-03-10T14:00:00",
            "dataAberturaProposta": "2026-03-20T10:30:00",
            "valorTotalEstimado": "123456.78",
            "linkSistemaOrigem": "https://compras.exemplo.gov/45",
            "orgaoEntidade": {
                "razaoSocial": "Prefeitura Municipal de Exemplo",
                "cnpj": "11.222.333/0001-44",
            },
            "arquivos": [
                {
                    "titulo": "Edital completo",
                    "url": "https://pncp.gov/arquivos/edital-45.pdf",
                    "tipoDocumentoNome": "Edital",
                }
            ],
        }

    def test_importar_contratacoes_cria_licitacao_empresa_e_documentos(self):
        payload = self._payload_base()
        client = _FakePNCPClient(contratacoes=[payload])

        service = ImportacaoPNCPService(client=client)
        resultado = service.importar_contratacoes_por_periodo(
            data_inicial="2026-03-01",
            data_final="2026-03-31",
        )

        self.assertEqual(resultado.total_payloads, 1)
        self.assertEqual(resultado.licitacoes_criadas, 1)
        self.assertEqual(resultado.licitacoes_atualizadas, 0)
        self.assertEqual(resultado.documentos_criados, 1)

        empresa = Empresa.objects.get(cnpj="11.222.333/0001-44")
        licitacao = Licitacao.objects.get(numero="45/2026-0001")
        documento = Documento.objects.get(licitacao=licitacao)

        self.assertEqual(licitacao.empresa, empresa)
        self.assertEqual(licitacao.objeto, "Contratacao de plataforma de dados")
        self.assertEqual(licitacao.link_externo, "https://compras.exemplo.gov/45")
        self.assertIn("numero_controle=PNCP-CTRL-001", licitacao.observacoes)
        self.assertEqual(documento.nome, "Edital completo")
        self.assertIn("PNCP_ARQUIVO_URL", documento.observacoes)

    def test_importacao_e_idempotente_para_licitacao_e_documento(self):
        payload = self._payload_base()
        client = _FakePNCPClient(contratacoes=[payload])
        service = ImportacaoPNCPService(client=client)

        primeiro = service.importar_contratacoes_por_periodo(
            data_inicial="2026-03-01",
            data_final="2026-03-31",
        )
        segundo = service.importar_contratacoes_por_periodo(
            data_inicial="2026-03-01",
            data_final="2026-03-31",
        )

        self.assertEqual(primeiro.licitacoes_criadas, 1)
        self.assertEqual(segundo.licitacoes_criadas, 0)
        self.assertEqual(segundo.licitacoes_atualizadas, 1)
        self.assertEqual(Licitacao.objects.count(), 1)
        self.assertEqual(Documento.objects.count(), 1)

    def test_sincronizar_arquivos_da_compra_adiciona_novos_arquivos(self):
        payload = self._payload_base()
        client = _FakePNCPClient(contratacoes=[payload])
        service = ImportacaoPNCPService(client=client)

        licitacao, _, _ = service.importar_licitacao_do_payload(payload)

        client._arquivos_por_controle["PNCP-CTRL-001"] = [
            {
                "titulo": "Ata de sessao",
                "url": "https://pncp.gov/arquivos/ata-45.pdf",
                "tipoDocumentoNome": "Ata",
            },
            {
                "titulo": "Ata de sessao",
                "url": "https://pncp.gov/arquivos/ata-45.pdf",
                "tipoDocumentoNome": "Ata",
            },
        ]

        criados = service.sincronizar_arquivos_da_compra(licitacao=licitacao)

        self.assertEqual(criados, 1)
        self.assertEqual(Documento.objects.filter(licitacao=licitacao).count(), 1)
