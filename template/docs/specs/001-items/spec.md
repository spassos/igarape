# 001 — Itens (exemplo de referência)

**Status:** Shipped · **Plan:** ./plan.md

## Contexto
Fatia mínima que exercita todas as integrações do template: API autenticada, banco, cache,
eventos de saída e de entrada. Cada item pertence ao sujeito (`sub`) do token que o criou.
Substitua pelo seu domínio.

## Critérios de aceite
- **AC-1** — Dado um token com `items:write` e um nome válido, quando `POST /v1/items`, então
  `201` com `id`, `name`, `created_at`; o item é persistido com `owner_id` = `sub` do token e o
  evento `items.created` é publicado.
- **AC-2** — Dado nome vazio ou > 120 caracteres, quando `POST /v1/items`, então `422`.
- **AC-3** — Dado um item do próprio sujeito e um token com `items:read`, quando
  `GET /v1/items/{id}`, então `200`; leituras seguintes são servidas do cache por
  `APP_CACHE_TTL_SECONDS`.
- **AC-4** — Dado um id inexistente, quando `GET /v1/items/{id}`, então `404`.
- **AC-5** — Dado uma mensagem `{"name": "...", "owner_id": "..."}` em `items.import`, quando
  consumida pelo worker, então o item é criado para esse dono como no AC-1; mensagens inválidas
  são rejeitadas.
- **AC-6** — `/health/live` retorna a versão implantada; `/health/ready` retorna `503` se alguma
  dependência falhar. Ambos são públicos.
- **AC-7** — Dado nenhum token, token expirado, assinatura inválida, emissor ou audiência
  errados, quando qualquer rota `/v1`, então `401` com `WWW-Authenticate: Bearer`.
- **AC-8** — Dado um token válido sem o escopo da rota (`items:read` para ler, `items:write` para
  criar), então `403`.
- **AC-9** — Dado um item de outro sujeito, quando `GET /v1/items/{id}`, então `404`, idêntico ao
  AC-4 (sem revelar que o item existe).
- **AC-10** — Toda resposta de erro usa `application/problem+json` (RFC 9457) sem stack trace;
  corpo maior que `APP_MAX_BODY_BYTES` → `413`.
- **AC-11** — Toda operação do OpenAPI responde em conformidade com o schema publicado e nunca
  com `500` para entradas geradas a partir dele.

## Contratos
### HTTP
`Authorization: Bearer <JWT>` obrigatório em `/v1`.

`POST /v1/items` (`items:write`) `{"name": "book"}` → `201`
`{"id": "3f0c...", "name": "book", "created_at": "2026-01-01T12:00:00Z"}`

`GET /v1/items/{id}` (`items:read`) → `200` com o mesmo corpo.

Erros (`application/problem+json`):
`{"type": "about:blank", "title": "Not Found", "status": 404, "detail": "..."}`
`401` sem token ou token inválido · `403` sem escopo · `404` inexistente ou de outro dono ·
`413` corpo grande · `422` validação.

### Eventos
| Direção | Tópico | Payload |
|---|---|---|
| publica | `items.created` | `{"item_id": "3f0c...", "name": "book", "owner_id": "alice", "occurred_at": "2026-01-01T12:00:00Z"}` |
| consome | `items.import` | `{"name": "book", "owner_id": "alice"}` |

`items.import` vem de produtor interno confiável; o broker restringe quem publica.

### Dados
Tabela `items(id uuid pk, name varchar(120), owner_id, created_at timestamptz)`; migrações em
`migrations/versions/`.

## Requisitos não funcionais
- Segurança: JWT/OIDC via JWKS ([ADR 0003](../../adr/0003-autenticacao-jwt-oidc.md)); `owner_id`
  vem só do token (HTTP) ou do produtor interno (worker), nunca do corpo HTTP; rate limit no API
  gateway.
- Observabilidade: logs sem token nem cabeçalho `Authorization`.
