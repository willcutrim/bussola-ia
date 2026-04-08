# Camada de IA do app `analises`

## Objetivo

Padronizar a implementacao da camada de IA do modulo `analises` no padrao Bússola.

## Mapa de arquivos

- `constants.py`: tarefas, escolha de modelo e configuracao central por caso de uso
- `schemas_ai.py`: contratos estruturados da saida
- `builders.py`: builders de contexto e montagem de payload
- `prompts.py`: `SYSTEM` prompt do dominio e builders de prompt por tarefa
- `integrations/openai_client.py`: borda externa da OpenAI
- `services_ai.py`: orquestracao, validacao de payload e persistencia
- `views_ai.py`: camada HTTP fina, com resposta JSON ou partial HTMX

## Tarefas atuais

- resumo de documento
- extracao estruturada
- parecer tecnico
- comparacao documento x licitacao
- checklist analitico

## Regras de arquitetura

- `views_ai.py` nao monta prompt e nao chama SDK externo diretamente
- `services_ai.py` orquestra `builders -> prompts -> client -> validacao -> persistencia`
- `prompts.py` define o contrato do dominio e proibe invencao de dados
- `schemas_ai.py` valida o payload antes de qualquer persistencia
- selecao de modelo fica centralizada em `constants.py`

## Padrao de UI atual

Na tela de detalhe da analise:

- existe um formulario-base para `texto_documento` e campos auxiliares
- cada acao usa `hx-post`
- cada resposta atualiza um card independente
- erros previsiveis retornam partial de erro renderizavel

Partials atuais:

- `partials/ai_actions.html`
- `partials/ai_result_resumo.html`
- `partials/ai_result_extracao.html`
- `partials/ai_result_parecer.html`
- `partials/ai_result_comparacao.html`
- `partials/ai_result_checklist.html`
- `partials/ai_result_error.html`

## Persistencia atual

- o parecer tecnico atualiza a `Analise`
- resumo, extracao, comparacao e checklist ainda nao possuem persistencia dedicada no dominio e hoje sao exibidos na interface

## Testes

A suite da camada de IA foi separada em:

- `test_builders.py`
- `test_prompts.py`
- `test_openai_client_unit.py`
- `test_ai_services_unit.py`
- `test_ai_services_integration.py`
- `test_ai_views_integration.py`

Regra fixa: testes nunca chamam a OpenAI real; apenas a borda externa e mockada.
