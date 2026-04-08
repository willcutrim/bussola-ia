---
name: django-htmx-list
description: Use esta skill quando a tarefa envolver páginas de listagem com filtros, paginação, atualização parcial via HTMX e tabelas reutilizáveis em Django Templates. Não usar para telas sem interação parcial.
---

# Objetivo

Criar listagens consistentes, leves e reaproveitáveis.

# Estrutura preferida

- template da página
- partial de filtros
- partial de tabela
- empty state reutilizável, quando aplicável

# Quando usar

- listagens administrativas
- filtros por status, data, profissional, categoria
- paginação parcial
- atualização dinâmica com HTMX

# Regras

- Separar página completa da partial atualizável.
- Não duplicar HTML de tabela em múltiplos lugares.
- Reutilizar empty_state.html sempre que couber.
- Não tratar table_base.html como obrigação universal se o projeto ainda não fechou esse contrato.
- Manter filtros simples e sem acoplamento excessivo.

# Workflow

1. Identificar dados, filtros e ações da listagem.
2. Definir o que renderiza na página completa.
3. Definir o que vai para partial HTMX.
4. Garantir consistência visual com outras listagens.
5. Revisar query e paginação.
6. Validar estados vazios.

# Entrega esperada

Tela de listagem com boa reutilização, partials claras e sem excesso de acoplamento.