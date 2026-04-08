---
name: django-service-repository
description: Use esta skill quando a tarefa exigir organizar ou implementar regra de negócio em services e acesso a dados em repositories dentro do padrão views -> services -> repositories. Não usar para mudanças puramente visuais.
---

# Objetivo

Garantir separação de responsabilidades.

# Princípios

- Views coordenam HTTP.
- Services executam casos de uso.
- Repositories encapsulam queries e acesso a dados.
- Templates só exibem dados.

# Quando usar

- criação de fluxo de negócio
- refatoração de lógica que está na view
- extração de query complexa
- padronização arquitetural

# Workflow

1. Localizar regra de negócio espalhada.
2. Decidir o que pertence à view, ao service e ao repository.
3. Extrair lógica da view para service.
4. Extrair consultas complexas para repository.
5. Manter interface simples entre camadas.
6. Revisar nomes e responsabilidade de cada método.

# Regras

- Não deixar validação de negócio espalhada em múltiplas views.
- Não fazer repository conhecer detalhes de template.
- Não fazer service montar resposta HTML.
- Não criar service inútil que só repassa chamada sem ganho real.
- No padrão atual do projeto, preferir métodos de service em português como `listar`, `obter`, `criar` e `atualizar`.
- Regras que alteram mais de um registro relacionado devem ficar no service, idealmente com `transaction.atomic` quando houver risco de inconsistência.
- Repositories do projeto tendem a usar métodos previsíveis como `listar_com_filtros`, `obter_por_id` e `obter_por_<campo>`.
- Em autenticação/contas, preferir:
  - normalização de `email` em minúsculo
  - sincronização leve de flags como `ativo` e `is_active`
  - tratamento seguro de senha em método dedicado como `criar_usuario(..., senha=...)`
- Máscara visual de CNPJ/telefone não pertence ao service; o service só deve receber e normalizar o valor limpo quando necessário.
- Em fluxos de IA:
  - prompts e builders não pertencem à view
  - o service orquestra `builders -> prompts -> client -> validação -> persistência`
  - a integração externa deve ficar encapsulada em `integrations/`
  - schemas estruturados devem validar payload antes de qualquer persistência

# Resultado esperado

Código mais previsível, reutilizável e fácil de manter.
