from types import SimpleNamespace
from unittest.mock import Mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from apps.analises.builders import PromptPayload
from apps.analises.constants import AnaliseAITask, get_task_config
from apps.analises.integrations import (
    AIPermanentError,
    AnaliseOpenAIClient,
    OpenAIClientConfig,
)
from apps.analises.schemas_ai import DocumentSummaryResponse


class AnaliseOpenAIClientUnitTests(SimpleTestCase):
    def test_gerar_resposta_monta_payload_com_modelo_da_tarefa(self):
        sdk_client = Mock()
        sdk_client.responses.parse.return_value = SimpleNamespace(
            id="resp_123",
            output_text="  Resumo ok  ",
            output_parsed=DocumentSummaryResponse(
                resumo_executivo="Resumo ok",
                fatos=["Fato 1"],
                inferencias=[],
                lacunas=[],
            ),
        )
        client = AnaliseOpenAIClient(
            config=OpenAIClientConfig(api_key="test-key"),
            client=sdk_client,
        )
        prompt = PromptPayload(
            task=AnaliseAITask.DOCUMENT_SUMMARY,
            system_prompt="SYSTEM",
            user_prompt="USER",
            metadata={
                "analise_id": 15,
                "source": "ui",
                "ignored": {"nested": True},
            },
        )
        task_config = get_task_config(AnaliseAITask.DOCUMENT_SUMMARY)

        response = client.gerar_resposta(prompt, task_config=task_config)

        self.assertEqual(response.task, AnaliseAITask.DOCUMENT_SUMMARY)
        self.assertEqual(response.model, task_config.model)
        self.assertEqual(response.text, "Resumo ok")
        sdk_client.responses.parse.assert_called_once_with(
            model=task_config.model,
            instructions="SYSTEM",
            input="USER",
            max_output_tokens=task_config.max_output_tokens,
            store=False,
            reasoning={"effort": task_config.reasoning_effort},
            text_format=task_config.response_schema,
            metadata={
                "app": "analises",
                "task": AnaliseAITask.DOCUMENT_SUMMARY,
                "analise_id": "15",
                "source": "ui",
            },
            verbosity=task_config.verbosity,
        )

    def test_gerar_resposta_aceita_override_de_modelo(self):
        sdk_client = Mock()
        sdk_client.responses.parse.return_value = SimpleNamespace(
            id="resp_custom",
            output_text="",
            output_parsed=DocumentSummaryResponse(
                resumo_executivo="Resumo",
                fatos=[],
                inferencias=[],
                lacunas=[],
            ),
        )
        client = AnaliseOpenAIClient(
            config=OpenAIClientConfig(api_key="test-key"),
            client=sdk_client,
        )
        prompt = PromptPayload(
            task=AnaliseAITask.DOCUMENT_SUMMARY,
            system_prompt="SYSTEM",
            user_prompt="USER",
        )

        response = client.gerar_resposta(
            prompt,
            task_config=get_task_config(AnaliseAITask.DOCUMENT_SUMMARY),
            model="gpt-5.4-custom",
        )

        self.assertEqual(response.model, "gpt-5.4-custom")
        self.assertEqual(
            sdk_client.responses.parse.call_args.kwargs["model"],
            "gpt-5.4-custom",
        )

    def test_gerar_resposta_rejeita_payload_nao_parseavel(self):
        sdk_client = Mock()
        sdk_client.responses.parse.return_value = SimpleNamespace(
            id="resp_erro",
            output_text="",
            output_parsed=None,
        )
        client = AnaliseOpenAIClient(
            config=OpenAIClientConfig(api_key="test-key"),
            client=sdk_client,
        )
        prompt = PromptPayload(
            task=AnaliseAITask.DOCUMENT_SUMMARY,
            system_prompt="SYSTEM",
            user_prompt="USER",
        )

        with self.assertRaisesMessage(
            AIPermanentError,
            "A resposta estruturada da IA nao retornou payload parseavel.",
        ):
            client.gerar_resposta(
                prompt,
                task_config=get_task_config(AnaliseAITask.DOCUMENT_SUMMARY),
            )

    def test_get_client_exige_chave_quando_nao_ha_cliente_injetado(self):
        client = AnaliseOpenAIClient(
            config=OpenAIClientConfig(api_key=None),
            client=None,
        )

        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "OPENAI_API_KEY nao configurada.",
        ):
            client._get_client()
