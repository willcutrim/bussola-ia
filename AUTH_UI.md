# Auth/UI Notes

## Fluxo atual de autenticação

- `accounts.User` é o user model ativo do projeto.
- Login continua por `username`.
- `email` é único, mas não é o identificador principal do login.
- Rotas públicas consolidadas:
  - `accounts:login`
  - `accounts:signup`
  - `accounts:logout`
- O cadastro público autentica o usuário imediatamente e redireciona para `home`.
- Logout deve sair por `POST`.

## Frontend compartilhado de auth

- Telas de login/cadastro podem ser standalone, sem `base.html`.
- Microinterações ficam no JS compartilhado `static/js/app.js`.
- Toggle de senha:
  - usar `PasswordInput`
  - marcar o input com `data-password-toggle="true"`
  - renderizar pelo partial `includes/form_field.html` quando possível
- Máscaras visuais:
  - `data-mask="cnpj"`
  - `data-mask="cpf"`
  - `data-mask="phone"`

## Templates

- Compartilhados: `apps/core/templates/includes/`
- Por app: `apps/<app>/templates/<app>/`
- Partials estáveis para reaproveitar:
  - `includes/form_field.html`
  - `includes/messages.html`
  - `includes/page_header.html`
  - `includes/status_badge.html`

## Pontos de atenção

- `status_badge.html` pode receber `status` ou `tone`/`label`.
- Nem todos os apps usam o mesmo nome para a rota principal:
  - `accounts` e `analises`: `list`
  - `empresas`, `licitacoes`, `documentos`: `index`
