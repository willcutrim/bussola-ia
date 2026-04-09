from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction

from apps.documentos.choices import StatusDocumentoChoices
from apps.documentos.models import Documento
from apps.empresas.models import Empresa
from apps.licitacoes.dtos import ArquivoPNCPDTO, ContratacaoPNCPDTO
from apps.licitacoes.integrations import PNCPClient
from apps.licitacoes.mappers import (
    mapear_arquivo_pncp_payload,
    mapear_contratacao_pncp_payload,
    mapear_modalidade_pncp,
    mapear_situacao_pncp,
    mapear_tipo_documento_pncp,
    montar_observacao_documento,
    montar_observacao_importacao,
)
from apps.licitacoes.models import Licitacao

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportacaoPNCPResultado:
    total_payloads: int
    licitacoes_criadas: int
    licitacoes_atualizadas: int
    documentos_criados: int


class ImportacaoPNCPService:
    def __init__(self, *, client: PNCPClient | None = None) -> None:
        self.client = client or PNCPClient()

    @transaction.atomic
    def importar_contratacoes_por_periodo(
        self,
        *,
        data_inicial: str,
        data_final: str,
        pagina: int = 1,
        tamanho_pagina: int = 50,
    ) -> ImportacaoPNCPResultado:
        payloads = self.client.buscar_contratacoes_por_periodo(
            data_inicial=data_inicial,
            data_final=data_final,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
        )

        criadas = 0
        atualizadas = 0
        documentos_criados = 0

        for payload in payloads:
            licitacao, was_created, dto = self.importar_licitacao_do_payload(payload)
            if was_created:
                criadas += 1
            else:
                atualizadas += 1

            documentos_criados += self.importar_documentos_da_licitacao(
                licitacao=licitacao,
                arquivos=dto.arquivos,
            )

        logger.info(
            "Importacao PNCP concluida: %s payloads, %s criadas, %s atualizadas, %s documentos.",
            len(payloads),
            criadas,
            atualizadas,
            documentos_criados,
        )

        return ImportacaoPNCPResultado(
            total_payloads=len(payloads),
            licitacoes_criadas=criadas,
            licitacoes_atualizadas=atualizadas,
            documentos_criados=documentos_criados,
        )

    @transaction.atomic
    def importar_licitacao_do_payload(
        self,
        payload: dict,
    ) -> tuple[Licitacao, bool, ContratacaoPNCPDTO]:
        dto = mapear_contratacao_pncp_payload(payload)
        chave_idempotencia = self._build_chave_idempotencia(dto)

        empresa = self._obter_ou_criar_empresa(dto)
        licitacao = self._obter_licitacao_existente(dto, chave_idempotencia)

        dados = {
            "empresa": empresa,
            "numero": self._build_numero_licitacao(dto),
            "objeto": dto.objeto_compra,
            "orgao": dto.orgao_nome,
            "modalidade": mapear_modalidade_pncp(dto.modalidade_nome),
            "situacao": mapear_situacao_pncp(dto.situacao_nome),
            "data_abertura": dto.data_abertura_proposta or dto.data_publicacao,
            "valor_estimado": dto.valor_total_estimado,
            "link_externo": dto.link_sistema_origem or "",
            "observacoes": montar_observacao_importacao(dto, chave_idempotencia),
            "ativa": True,
        }

        if licitacao is None:
            licitacao = Licitacao.objects.create(**dados)
            return licitacao, True, dto

        for field, value in dados.items():
            setattr(licitacao, field, value)
        licitacao.save()
        return licitacao, False, dto

    @transaction.atomic
    def importar_documentos_da_licitacao(
        self,
        *,
        licitacao: Licitacao,
        arquivos: list[ArquivoPNCPDTO],
    ) -> int:
        criados = 0
        for arquivo in arquivos:
            if not arquivo.url:
                continue
            observacao = montar_observacao_documento(arquivo.url)
            documento = Documento.objects.filter(
                licitacao=licitacao,
                observacoes=observacao,
            ).first()
            if documento:
                continue

            nome_arquivo = self._build_nome_arquivo(arquivo)
            Documento.objects.create(
                licitacao=licitacao,
                nome=arquivo.titulo,
                arquivo=ContentFile(
                    b"",
                    name=nome_arquivo,
                ),
                tipo=mapear_tipo_documento_pncp(arquivo.tipo, arquivo.titulo),
                status=StatusDocumentoChoices.ENVIADO,
                observacoes=observacao,
            )
            criados += 1

        return criados

    @transaction.atomic
    def sincronizar_arquivos_da_compra(self, *, licitacao: Licitacao) -> int:
        numero_controle = self._extract_numero_controle_from_observacao(licitacao.observacoes)
        if not numero_controle:
            return 0

        payloads = self.client.buscar_arquivos_da_compra(numero_controle)
        arquivos = [mapear_arquivo_pncp_payload(payload) for payload in payloads]
        return self.importar_documentos_da_licitacao(licitacao=licitacao, arquivos=arquivos)

    def _obter_ou_criar_empresa(self, dto: ContratacaoPNCPDTO) -> Empresa | None:
        if not dto.orgao_cnpj:
            return None

        defaults = {
            "nome": dto.orgao_nome,
            "razao_social": dto.orgao_nome,
            "ativa": True,
        }
        empresa, _ = Empresa.objects.get_or_create(cnpj=dto.orgao_cnpj, defaults=defaults)
        return empresa

    def _obter_licitacao_existente(
        self,
        dto: ContratacaoPNCPDTO,
        chave_idempotencia: str,
    ) -> Licitacao | None:
        if dto.link_sistema_origem:
            por_link = Licitacao.objects.filter(link_externo=dto.link_sistema_origem).first()
            if por_link:
                return por_link

        marcador_chave = f"chave={chave_idempotencia}"
        por_chave = Licitacao.objects.filter(observacoes__icontains=marcador_chave).first()
        if por_chave:
            return por_chave

        return Licitacao.objects.filter(
            numero=self._build_numero_licitacao(dto),
            orgao=dto.orgao_nome,
        ).first()

    def _build_chave_idempotencia(self, dto: ContratacaoPNCPDTO) -> str:
        if dto.numero_controle_pncp:
            return dto.numero_controle_pncp

        partes = [
            dto.orgao_cnpj or dto.orgao_nome,
            str(dto.ano_compra or ""),
            dto.sequencial_compra or "",
            dto.numero_compra,
        ]
        return "|".join(parte.strip() for parte in partes if parte is not None)

    def _build_numero_licitacao(self, dto: ContratacaoPNCPDTO) -> str:
        ano = dto.ano_compra or "sem-ano"
        sequencial = dto.sequencial_compra or dto.numero_compra
        return f"{dto.numero_compra}/{ano}-{sequencial}"[:120]

    def _extract_numero_controle_from_observacao(self, observacoes: str) -> str | None:
        if not observacoes:
            return None
        for fragmento in observacoes.split("|"):
            trecho = fragmento.strip()
            if trecho.startswith("numero_controle="):
                return trecho.split("=", 1)[1].strip() or None
        return None

    def _build_nome_arquivo(self, arquivo: ArquivoPNCPDTO) -> str:
        suffix = Path(arquivo.url).suffix or ".txt"
        stem = "_".join(arquivo.titulo.lower().split())[:80] or "arquivo_pncp"
        return f"pncp/{stem}{suffix}"
