---
name: django-cbv-crud
description: Use esta skill quando a tarefa envolver criar ou ajustar CRUDs em Django usando Class-Based Views, formulários, templates e estrutura compatível com o padrão Bússola. Não usar para scripts soltos, APIs puras sem templates, ou soluções fora de CBV.
---

# Objetivo

Implementar CRUDs consistentes com o padrão do projeto, priorizando:

- Class-Based Views
- services
- repositories
- templates reutilizáveis
- partials quando necessário

# Quando usar

Use esta skill quando a tarefa envolver:

- listagem
- criação
- edição
- exclusão
- detalhe
- filtros simples em telas Django com templates

# Quando não usar

Não use esta skill quando:

- a tarefa for exclusivamente de API DRF
- for um script administrativo
- a mudança estiver concentrada só em query performance
- a tarefa for apenas CSS/JS isolado

# Workflow obrigatório

1. Identificar model, formulário, view, service e repository relacionados.
2. Confirmar se já existe base view, mixin ou padrão semelhante.
3. Implementar a view em CBV.
4. Mover regra de negócio para service.
5. Centralizar query relevante em repository.
6. Criar ou ajustar template sem quebrar o padrão visual.
7. Reutilizar partials e estruturas existentes.
8. Revisar nomes e duplicações.
9. Resumir a solução de forma objetiva.

# Regras de implementação

- Não colocar regra de negócio na view.
- Não duplicar filtro complexo em múltiplos lugares.
- Não inventar uma nova estrutura de CRUD se já houver padrão no projeto.
- Se existir base genérica compatível, preferir extensão em vez de recriar tudo.
- Sempre respeitar o padrão visual do projeto.
- No padrão atual, `BaseCreateView` e `BaseUpdateView` já suportam services com `criar/atualizar`, então não criar mixins locais só para adaptar isso.
- Em telas ainda sem fluxo final definido, `success_url` pode apontar temporariamente para a listagem do app.
- Ao testar CRUD antes dos templates existirem, validar redirect e efeito no banco sem depender de renderização final.
- Antes de usar `{% url %}` em templates e redirects, confirmar se o app usa `index` ou `list` como nome da rota principal.
- Se o CRUD incluir campos de documento/telefone, preferir máscaras via `data-mask` no form em vez de JS inline local.
- Para campos de senha, reutilizar o toggle já suportado por `includes/form_field.html` com `PasswordInput`.
- Em fluxos de conta pública, criação pode autenticar o usuário imediatamente quando isso simplificar a experiência e não conflitar com regra de negócio.

# Saída esperada

Ao final, entregar:

- arquivos alterados
- breve justificativa arquitetural
- observações de reuso e impacto
