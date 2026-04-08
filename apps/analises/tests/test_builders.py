from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.analises.builders import (
    PromptPayload,
    build_analise_contexto,
    build_documento_contexto,
    build_licitacao_contexto,
    build_prompt_payload,
    render_context_section,
    render_text_section,
    serialize_for_prompt,
)


class AnaliseBuildersTests(SimpleTestCase):
    def test_build_prompt_payload_descarta_sessoes_vazias_e_monta_texto_previsivel(self):
        payload = build_prompt_payload(
            task="document_summary",
            system_prompt="  system  ",
            sections=[
                ("Tarefa", "  Resumir documento  "),
                ("Vazio", "   "),
                ("Contexto", None),
            ],
            metadata={"kind": "summary"},
        )

        self.assertIsInstance(payload, PromptPayload)
        self.assertEqual(payload.system_prompt, "system")
        self.assertIn("## Tarefa", payload.user_prompt)
        self.assertIn("Resumir documento", payload.user_prompt)
        self.assertNotIn("## Vazio", payload.user_prompt)
        self.assertNotEqual(payload.user_prompt, "")

    def test_build_documento_contexto_retorna_payload_esperado(self):
        documento = SimpleNamespace(
            pk=7,
            nome="Edital principal",
            tipo="edital",
            status="pendente",
            observacoes="Documento base",
            licitacao_id=13,
        )

        contexto = build_documento_contexto(documento)

        self.assertEqual(
            contexto,
            {
                "id": 7,
                "nome": "Edital principal",
                "tipo": "edital",
                "status": "pendente",
                "observacoes": "Documento base",
                "licitacao_id": 13,
            },
        )

    def test_build_licitacao_contexto_serializa_campos_complexos(self):
        class EmpresaStub:
            def __str__(self):
                return "Empresa Alpha"

        empresa = EmpresaStub()
        licitacao = SimpleNamespace(
            pk=3,
            numero="PE-001/2026",
            objeto="Contratacao de software",
            orgao="Prefeitura",
            modalidade="pregao",
            situacao="em_analise",
            data_abertura=date(2026, 4, 20),
            valor_estimado=Decimal("125000.90"),
            empresa_id=1,
            empresa=empresa,
            observacoes="Urgente",
        )

        contexto = build_licitacao_contexto(licitacao)

        self.assertEqual(contexto["numero"], "PE-001/2026")
        self.assertEqual(contexto["data_abertura"], "2026-04-20")
        self.assertEqual(contexto["valor_estimado"], "125000.90")
        self.assertEqual(contexto["empresa"], "Empresa Alpha")

    def test_build_analise_contexto_retorna_estado_atual(self):
        analise = SimpleNamespace(
            pk=9,
            titulo="Analise juridica",
            descricao="Primeira rodada",
            status="pendente",
            prioridade="alta",
            parecer="Necessita revisao",
            responsavel_id=12,
        )

        contexto = build_analise_contexto(analise)

        self.assertEqual(contexto["status_atual"], "pendente")
        self.assertEqual(contexto["prioridade_atual"], "alta")
        self.assertEqual(contexto["parecer_atual"], "Necessita revisao")

    def test_render_helpers_retornam_estrutura_estavel(self):
        titulo, payload = render_context_section("Contexto", {"numero": "PE-001/2026"})
        texto_titulo, texto = render_text_section("Texto", "  Conteudo relevante  ")

        self.assertEqual(titulo, "Contexto")
        self.assertIn('"numero": "PE-001/2026"', payload)
        self.assertEqual(texto_titulo, "Texto")
        self.assertEqual(texto, "Conteudo relevante")

    def test_serialize_for_prompt_retorna_string_json_ou_texto_limpo(self):
        self.assertEqual(serialize_for_prompt("  alpha  "), "alpha")
        self.assertIn('"campo": "valor"', serialize_for_prompt({"campo": "valor"}))
