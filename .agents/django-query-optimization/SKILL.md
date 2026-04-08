---
name: django-query-optimization
description: Use esta skill quando a tarefa envolver melhoria de desempenho em consultas Django ORM, especialmente em listagens, dashboards, detalhes com relacionamentos, select_related, prefetch_related e prevenção de N+1. Não usar para mudanças apenas visuais.
---

# Objetivo

Melhorar desempenho e previsibilidade de consultas.

# Sinais de uso

- listagem lenta
- dashboard lento
- muitos relacionamentos
- repetição de queries
- uso inadequado de count, first, exists ou loops com ORM

# Regras

- Verificar N+1 antes de propor qualquer refatoração grande.
- Preferir select_related em relações simples de chave estrangeira.
- Preferir prefetch_related em relações reversas e many-to-many.
- Evitar avaliações repetidas do queryset.
- Usar exists() quando só precisar verificar existência.
- Usar values/values_list apenas quando fizer sentido real.

# Workflow

1. Identificar queryset principal.
2. Mapear relações acessadas na view, template ou service.
3. Revisar N+1 e avaliações repetidas.
4. Sugerir otimização mínima necessária.
5. Evitar micro-otimização sem ganho claro.
6. Explicar o motivo da mudança.

# Resultado esperado

Consulta mais eficiente sem sacrificar legibilidade.