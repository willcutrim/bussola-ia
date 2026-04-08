---
name: django-template-partials
description: Use esta skill quando a tarefa exigir organizar templates Django em blocos reutilizáveis como listagem, filtros, formulários, modais, detalhes e fragmentos compartilhados. Não usar para lógica backend pura.
---

# Objetivo

Padronizar a organização de templates do projeto.

# Padrões desejados

- page template principal
- _table.html
- _filters.html
- _form.html
- fragmentos reutilizáveis
- empty_state.html quando aplicável
- shared partials em `apps/core/templates/includes/`
- templates do app em `apps/<app>/templates/<app>/`

# Regras

- Não colocar lógica complexa em template.
- Evitar duplicação estrutural.
- Manter nomes previsíveis.
- Preservar consistência visual.
- Quando um padrão se repetir, marcar como candidato a base futura, sem forçar abstrações prematuras.
- Reusar preferencialmente:
  - `includes/form_field.html`
  - `includes/messages.html`
  - `includes/page_header.html`
  - `includes/status_badge.html`
- Em telas HTMX de detalhe/ações:
  - manter um template principal enxuto
  - criar partial por bloco de resultado
  - manter partial de erro quando houver processamento parcial
  - usar `includes/empty_state.html` para estado inicial
- Para autenticação, aceitar páginas standalone quando isso reduzir ruído visual e melhorar a entrada no sistema.
- Não assumir que `status_badge.html` sempre receberá `status`; ele também pode receber `tone` e `label`.

# Workflow

1. Identificar blocos repetidos.
2. Separar fragmentos reutilizáveis.
3. Preservar clareza do template principal.
4. Reusar partials existentes.
5. Se houver campos de senha, reutilizar o toggle de visualização já suportado pelo partial.
6. Se houver documento/telefone, preferir máscaras via `data-mask` e JS compartilhado.
7. Avaliar se a abstração é madura o suficiente ou ainda deve ser local ao app.
8. Em interfaces HTMX, definir claramente qual partial cada ação atualiza.

# Entrega esperada

Templates mais limpos, previsíveis e preparados para evolução.
