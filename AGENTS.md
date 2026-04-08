# AGENTS.md

## Contexto do projeto

Este repositório segue o padrão Bússola para projetos Django profissionais.
A stack principal é:

- Python
- Django
- PostgreSQL
- HTMX
- Bootstrap 5

A arquitetura padrão é:

- views -> services -> repositories

## Regras obrigatórias

- Sempre preferir Class-Based Views (CBVs).
- Não colocar regra de negócio diretamente nas views.
- Toda lógica de negócio deve ir para services.
- Acesso a dados e queries mais elaboradas devem ir para repositories.
- Evitar soluções improvisadas fora do padrão do projeto.
- Antes de criar novos arquivos base, verificar se já existe um base ou mixin equivalente.
- Reaproveitar componentes e partials existentes sempre que possível.
- Não introduzir frameworks frontend adicionais sem necessidade explícita.
- Não trocar a arquitetura atual por outra.
- Não criar novos campos/modelos sem necessidade clara e sem justificar no código.
- Priorizar clareza, consistência e reuso.

## Convenções de views

- Preferir CBVs para listagem, criação, edição, exclusão e detalhe.
- Views devem coordenar fluxo HTTP, permissões, formulários e respostas.
- Views não devem concentrar regra de negócio.
- Sempre que possível, usar mixins e bases reutilizáveis.
- Para autenticação pública, manter o fluxo simples:
  - `AccountLoginView` para login
  - `AccountSignupView` para criação de conta
  - `AccountLogoutView` para logout
- Quando o cadastro público existir, preferir login automático após criação bem-sucedida em vez de obrigar o usuário a autenticar de novo.

## Convenções de services

- Services devem concentrar casos de uso.
- Services devem receber dados já validados quando fizer sentido.
- Services devem retornar resultados claros e previsíveis.
- Services não devem renderizar templates nem conhecer detalhes de interface.
- No padrão atual dos apps, preferir nomes explícitos em português como `listar`, `obter`, `criar` e `atualizar`.
- Quando houver regra simples de orquestração entre registros relacionados, ela deve ficar no service com `transaction.atomic` quando fizer sentido.
- Em integrações externas, como IA, o service deve orquestrar builders, client e persistência sem conhecer SDK diretamente.
- Quando houver camada de IA, separar responsabilidades em arquivos previsíveis como `constants.py`, `schemas_ai.py`, `builders.py`, `prompts.py`, `integrations/openai_client.py`, `services_ai.py` e `views_ai.py` quando houver interface HTTP dedicada.

## Convenções de repositories

- Repositories devem encapsular consultas, filtros, select_related, prefetch_related e otimizações.
- Quando a tarefa envolver listagens ou dashboards, revisar possibilidade de otimização de queries.
- Evitar repetição de filtros complexos em múltiplas views ou services.
- Em apps CRUD, preferir métodos previsíveis como `listar_com_filtros`, `obter_por_id`, `obter_por_<campo>` e `listar_ativas` quando houver ganho real.
- Aplicar `select_related` apenas em relacionamentos com uso recorrente e ganho claro na listagem.

## Convenções de forms

- Forms validam entrada e normalizações leves.
- Normalizações simples de texto, documentos e siglas podem ficar no form ou no service, desde que não virem regra de negócio complexa.
- Não mover para forms regras que alterem múltiplos registros; isso pertence ao service.
- No frontend atual, máscaras e microinterações simples devem ser declaradas por atributos no campo e executadas pelo JS compartilhado:
  - `data-mask="cnpj"`
  - `data-mask="cpf"`
  - `data-mask="phone"`
  - `data-password-toggle="true"` em inputs de senha
- Para documentos como CNPJ/CPF e telefone, preservar o padrão:
  - máscara no frontend
  - normalização/limpeza leve no form ou service
  - validação de negócio só quando houver necessidade clara

## Convenções de testes

- Preferir `TestCase` com migrations reais do app.
- Evitar `schema_editor` manual em testes de app quando o app já possui migration.
- Cobrir repositories, services e integração mínima das views sem depender de templates quando a interface ainda não existir.
- Em integrações com IA ou serviços externos, nunca chamar serviço real nos testes; mockar apenas a borda externa.
- Em camadas de IA, preferir separar a suíte em:
  - `test_builders.py`
  - `test_prompts.py`
  - `test_openai_client_unit.py`
  - `test_ai_services_unit.py`
  - `test_ai_services_integration.py`
  - `test_ai_views_integration.py`
- Em testes HTMX, validar tanto o contrato HTTP normal quanto a resposta parcial quando `HX-Request=true`.

## Convenções de templates

- Usar Django Templates.
- Quando houver atualização parcial, preferir HTMX.
- Templates compartilhados do projeto ficam em `apps/core/templates/`.
- Templates de cada app devem ficar em `apps/<app>/templates/<app>/`.
- Em páginas de listagem, preferir separação entre:
  - page template
  - partial de tabela
  - partial de filtros
  - partial de formulário, quando aplicável
- Reutilizar empty_state.html quando fizer sentido.
- Não assumir que table_base.html é contrato universal se a tarefa não exigir isso.
- Partials compartilhadas estáveis já confirmadas:
  - `includes/form_field.html`
  - `includes/messages.html`
  - `includes/page_header.html`
  - `includes/status_badge.html`
  - `includes/sidebar.html`
  - `includes/topbar.html`
- Em telas com ações de processamento via HTMX, preferir:
  - formulário-base simples no template principal
  - botões com `hx-post`
  - `hx-target` apontando para um card/partial específico
  - `hx-indicator` com feedback de carregamento
  - fallback previsível fora de HTMX
- Em respostas HTMX com erro previsível de validação, preferir retornar partial de erro renderizada em vez de depender apenas de status HTTP não renderizado no frontend.
- Em telas de autenticação, é aceitável usar layout standalone sem `base.html` quando isso simplificar a experiência de entrada.
- Logout deve sair por `POST` no template; não depender de link `GET` para esse fluxo.

## Layouts esperados

Ao criar novas interfaces, considerar como padrão:

- base de listagem
- base de formulário
- base de modal
- base de detalhe

Sempre manter consistência visual com o restante do projeto.

## Convenções de IA no app `analises`

- O contrato do domínio de IA deve manter:
  - `SYSTEM` prompt central
  - builders separados por tarefa
  - saída estruturada e validada por schema
  - distinção explícita entre fato, inferência e lacuna quando aplicável
- Seleção de modelo por tarefa deve ficar centralizada em `constants.py`, nunca espalhada em view ou template.
- `views_ai.py` deve ficar fina:
  - obtém a entidade do domínio
  - delega para `services_ai.py`
  - retorna JSON previsível fora de HTMX
  - retorna partial HTML em requests HTMX quando a interface exigir atualização parcial
- A UI de IA deve ser orientada a partials por resultado, evitando um template monolítico.

## Convenções de URLs

- Há dois nomes de listagem consolidados no projeto hoje:
  - `index` em `empresas`, `licitacoes` e `documentos`
  - `list` em `accounts` e `analises`
- Antes de referenciar `{% url %}` em templates compartilhados ou sidebars, conferir o nome real da rota do app e não assumir uniformidade artificial.

## Banco de dados e ORM

- Otimizar queries com select_related e prefetch_related quando necessário.
- Evitar N+1 queries.
- Usar exists() quando só precisar verificar existência.
- Evitar count() desnecessário em loops.
- Avaliar transaction.atomic em fluxos críticos.

## Qualidade de entrega

Antes de finalizar uma tarefa:

- revisar impacto arquitetural
- revisar duplicação
- revisar queries
- revisar nomes de métodos, classes e arquivos
- verificar se a solução segue o padrão Bússola
- explicar brevemente o que foi feito e por quê
- se a implementação revelou um padrão estável do projeto, atualizar instruções locais curtas quando isso reduzir atrito futuro
- quando a tarefa envolver telas, validar o fluxo real com login e navegação nas rotas principais, não só `manage.py check`

## O que não fazer

- Não mover regra de negócio para template.
- Não resolver tudo dentro da view.
- Não criar estrutura paralela à arquitetura existente.
- Não adicionar dependência nova sem necessidade real.
- Não alterar o estilo visual do projeto sem manter consistência com o padrão atual.

## Definição de pronto

Uma tarefa só está pronta quando:

- segue CBV
- respeita views -> services -> repositories
- usa partials quando necessário
- mantém consistência visual
- evita duplicação
- considera impacto em query e manutenção futura
