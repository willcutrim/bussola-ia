from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from apps.licitacoes.constants import (
    PNCP_BASE_URL,
    PNCP_CONTRATACAO_ARQUIVOS_PATH,
    PNCP_CONTRATACAO_DETALHE_PATH,
    PNCP_CONTRATACOES_PATH,
    PNCP_DEFAULT_PAGE_SIZE,
    PNCP_MAX_PAGE_SIZE,
    PNCP_TIMEOUT_SECONDS,
)


class PNCPIntegrationError(Exception):
    """Erro generico da integracao PNCP."""


class PNCPEndpointError(PNCPIntegrationError):
    """Erro previsivel no consumo de endpoint PNCP."""


class PNCPTimedOutError(PNCPIntegrationError):
    """Timeout no consumo do PNCP."""


class PNCPUnexpectedResponseError(PNCPIntegrationError):
    """Resposta invalida ou fora do contrato esperado."""


@dataclass(frozen=True)
class PNCPClientConfig:
    base_url: str = PNCP_BASE_URL
    timeout_seconds: float = PNCP_TIMEOUT_SECONDS


class PNCPClient:
    def __init__(
        self,
        *,
        config: PNCPClientConfig | None = None,
        http_get=None,
    ) -> None:
        self.config = config or PNCPClientConfig()
        self._http_get = http_get or urlopen

    def buscar_contratacoes_por_periodo(
        self,
        *,
        data_inicial: str,
        data_final: str,
        pagina: int = 1,
        tamanho_pagina: int = PNCP_DEFAULT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        filtros = {
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "pagina": pagina,
            "tamanhoPagina": min(max(1, tamanho_pagina), PNCP_MAX_PAGE_SIZE),
        }
        return self.buscar_contratacoes_com_filtros(**filtros)

    def buscar_contratacoes_com_filtros(self, **filtros) -> list[dict[str, Any]]:
        response = self._request(PNCP_CONTRATACOES_PATH, params=filtros)
        if isinstance(response, list):
            return [item for item in response if isinstance(item, dict)]
        if isinstance(response, dict):
            itens = response.get("data") or response.get("items") or response.get("content")
            if isinstance(itens, list):
                return [item for item in itens if isinstance(item, dict)]
        raise PNCPUnexpectedResponseError(
            "O endpoint de contratacoes nao retornou uma lista valida."
        )

    def buscar_detalhe_compra(self, numero_controle_pncp: str) -> dict[str, Any]:
        endpoint = PNCP_CONTRATACAO_DETALHE_PATH.format(
            numero_controle_pncp=numero_controle_pncp
        )
        response = self._request(endpoint)
        if not isinstance(response, dict):
            raise PNCPUnexpectedResponseError(
                "O endpoint de detalhe da compra retornou payload invalido."
            )
        return response

    def buscar_arquivos_da_compra(self, numero_controle_pncp: str) -> list[dict[str, Any]]:
        endpoint = PNCP_CONTRATACAO_ARQUIVOS_PATH.format(
            numero_controle_pncp=numero_controle_pncp
        )
        response = self._request(endpoint)
        if not isinstance(response, list):
            raise PNCPUnexpectedResponseError(
                "O endpoint de arquivos da compra nao retornou uma lista valida."
            )
        return [item for item in response if isinstance(item, dict)]

    def _request(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        url = f"{self.config.base_url.rstrip('/')}{path}"
        if params:
            sanitized = {
                key: value
                for key, value in params.items()
                if value is not None and value != ""
            }
            if sanitized:
                url = f"{url}?{urlencode(sanitized)}"

        request = Request(url=url, method="GET")
        request.add_header("Accept", "application/json")

        try:
            with self._http_get(
                request,
                timeout=self.config.timeout_seconds,
            ) as response:
                raw_body = response.read()
        except TimeoutError as exc:
            raise PNCPTimedOutError("A requisicao ao PNCP excedeu o timeout configurado.") from exc
        except HTTPError as exc:
            raise PNCPEndpointError(
                f"PNCP respondeu com erro HTTP {exc.code}."
            ) from exc
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError):
                raise PNCPTimedOutError(
                    "A requisicao ao PNCP excedeu o timeout configurado."
                ) from exc
            raise PNCPEndpointError("Falha de conexao ao consumir o PNCP.") from exc

        try:
            return json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PNCPUnexpectedResponseError(
                "A resposta do PNCP nao esta em JSON valido."
            ) from exc
