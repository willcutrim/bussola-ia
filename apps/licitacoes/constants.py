from __future__ import annotations

PNCP_BASE_URL = "https://pncp.gov.br/api"
PNCP_TIMEOUT_SECONDS = 20.0
PNCP_DEFAULT_PAGE_SIZE = 50
PNCP_MAX_PAGE_SIZE = 500

PNCP_CONTRATACOES_PATH = "/consulta/v1/contratacoes/publicacao"
PNCP_CONTRATACAO_DETALHE_PATH = "/consulta/v1/contratacoes/{numero_controle_pncp}"
PNCP_CONTRATACAO_ARQUIVOS_PATH = (
    "/consulta/v1/contratacoes/{numero_controle_pncp}/arquivos"
)

PNCP_OBSERVACAO_PREFIX = "PNCP_IMPORTACAO"
PNCP_DOCUMENTO_URL_PREFIX = "PNCP_ARQUIVO_URL"
