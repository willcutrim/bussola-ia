from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase

from apps.licitacoes.integrations.pncp_client import (
    PNCPEndpointError,
    PNCPClient,
    PNCPClientConfig,
    PNCPTimedOutError,
    PNCPUnexpectedResponseError,
)


class _FakeHTTPResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class PNCPClientUnitTests(SimpleTestCase):
    def test_busca_por_periodo_monta_filtros_e_retorna_lista(self):
        captured = {}

        def fake_http_get(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            payload = json.dumps([{"numeroControlePNCP": "X1"}]).encode("utf-8")
            return _FakeHTTPResponse(payload)

        client = PNCPClient(
            config=PNCPClientConfig(base_url="https://pncp.teste", timeout_seconds=12),
            http_get=fake_http_get,
        )

        response = client.buscar_contratacoes_por_periodo(
            data_inicial="2026-01-01",
            data_final="2026-01-31",
            pagina=2,
            tamanho_pagina=20,
        )

        self.assertEqual(response, [{"numeroControlePNCP": "X1"}])
        self.assertIn("dataInicial=2026-01-01", captured["url"])
        self.assertIn("dataFinal=2026-01-31", captured["url"])
        self.assertIn("pagina=2", captured["url"])
        self.assertIn("tamanhoPagina=20", captured["url"])
        self.assertEqual(captured["timeout"], 12)

    def test_busca_com_filtros_aceita_payload_com_content(self):
        def fake_http_get(request, timeout):
            payload = json.dumps({"content": [{"numeroControlePNCP": "X2"}]}).encode(
                "utf-8"
            )
            return _FakeHTTPResponse(payload)

        client = PNCPClient(http_get=fake_http_get)

        response = client.buscar_contratacoes_com_filtros(modalidade="Pregao")

        self.assertEqual(response, [{"numeroControlePNCP": "X2"}])

    def test_buscar_arquivos_valida_contrato_de_lista(self):
        def fake_http_get(request, timeout):
            payload = json.dumps({"data": []}).encode("utf-8")
            return _FakeHTTPResponse(payload)

        client = PNCPClient(http_get=fake_http_get)

        with self.assertRaises(PNCPUnexpectedResponseError):
            client.buscar_arquivos_da_compra("ctrl-1")

    def test_timeout_gera_excecao_especifica(self):
        def fake_http_get(request, timeout):
            raise TimeoutError("tempo excedido")

        client = PNCPClient(http_get=fake_http_get)

        with self.assertRaises(PNCPTimedOutError):
            client.buscar_detalhe_compra("ctrl-2")

    def test_http_error_gera_endpoint_error(self):
        def fake_http_get(request, timeout):
            raise HTTPError(
                url=request.full_url,
                code=503,
                msg="Service Unavailable",
                hdrs=None,
                fp=BytesIO(b""),
            )

        client = PNCPClient(http_get=fake_http_get)

        with self.assertRaises(PNCPEndpointError):
            client.buscar_detalhe_compra("ctrl-3")

    def test_urLError_de_timeout_gera_timeout_error(self):
        def fake_http_get(request, timeout):
            raise URLError(TimeoutError("tempo excedido"))

        client = PNCPClient(http_get=fake_http_get)

        with self.assertRaises(PNCPTimedOutError):
            client.buscar_contratacoes_com_filtros()

    def test_json_invalido_gera_erro_de_resposta(self):
        def fake_http_get(request, timeout):
            return _FakeHTTPResponse(b"nao-json")

        client = PNCPClient(http_get=fake_http_get)

        with self.assertRaises(PNCPUnexpectedResponseError):
            client.buscar_contratacoes_com_filtros()
