# Camada de IA do app `analises`

## Objetivo

Padronizar a implementacao da camada de IA do modulo `analises` no padrao Bússola.

## Mapa de arquivos

- `constants.py`: tarefas, escolha de modelo e configuracao central por caso de uso
- `schemas_ai.py`: contratos estruturados da saida
- `builders.py`: builders de contexto e montagem de payload
- `prompts.py`: `SYSTEM` prompt do dominio e builders de prompt por tarefa
- `integrations/openai_client.py`: borda externa da OpenAI
- `services_ai.py`: processamento real da IA, validacao de payload e persistencia do parecer
- `services_async.py`: solicitacao assincrona, ciclo de vida e rastreabilidade das execucoes
- `tasks.py`: tasks finas do Django Tasks para orquestrar execucao, status e retries
- `views_ai.py`: camada HTTP fina para solicitar execucao e consultar cards atualizados
- `models.py`: `Analise` e `AnaliseExecucaoIA`

## Tarefas atuais

- resumo de documento
- extracao estruturada
- parecer tecnico
- comparacao documento x licitacao
- checklist analitico

## Regras de arquitetura

- `views_ai.py` nao monta prompt, nao chama SDK externo e nao processa IA na request
- `services_ai.py` orquestra `builders -> prompts -> client -> validacao -> persistencia`
- `services_async.py` centraliza `solicitacao -> on_commit -> enqueue -> rastreio`
- `tasks.py` atualiza status e delega o processamento real para `services_ai.py`
- `prompts.py` define o contrato do dominio e proibe invencao de dados
- `schemas_ai.py` valida o payload antes de qualquer persistencia
- selecao de modelo fica centralizada em `constants.py`
- o dominio do app nao conhece Celery; a aplicacao usa `django.tasks` como abstracao principal

## Padrao de UI atual

Na tela de detalhe da analise:

- existe um formulario-base para `texto_documento` e campos auxiliares
- cada acao usa `hx-post`
- cada resposta inicia uma execucao assincrona e atualiza um card independente
- cards em `pendente` ou `em_processamento` fazem polling HTMX para a rota de resultado
- erros previsiveis de validacao retornam partial de erro renderizavel
- falhas de processamento ficam persistidas em `AnaliseExecucaoIA`

Partials atuais:

- `partials/ai_actions.html`
- `partials/ai_result_resumo.html`
- `partials/ai_result_extracao.html`
- `partials/ai_result_parecer.html`
- `partials/ai_result_comparacao.html`
- `partials/ai_result_checklist.html`
- `partials/ai_result_error.html`

## Persistencia atual

- `AnaliseExecucaoIA` guarda historico, payload de entrada, resultado, erro, tentativas, modelo e identificador da task
- o parecer tecnico continua atualizando a `Analise`
- resumo, extracao, comparacao e checklist ficam persistidos no historico de execucao
- a UI sempre usa a ultima execucao por tipo para montar cada card

## Testes

A suite da camada de IA foi separada em:

- `test_builders.py`
- `test_prompts.py`
- `test_openai_client_unit.py`
- `test_ai_services_unit.py`
- `test_ai_services_integration.py`
- `test_ai_views_integration.py`
- `test_async_services_unit.py`
- `test_tasks_unit.py`
- `test_tasks_integration.py`

Regra fixa: testes nunca chamam a OpenAI real; apenas a borda externa e mockada.
