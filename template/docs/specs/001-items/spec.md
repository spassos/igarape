# 001 — Itens (exemplo de referência)

**Status:** Shipped · **Plan:** ./plan.md

## Contexto
Fatia mínima que exercita todas as integrações do template: API, banco, cache, eventos de saída e
de entrada. Substitua pelo seu domínio.

## Critérios de aceite
- **AC-1** — Dado um nome válido, quando `POST /items`, então `201` com `id`, `name`, `created_at`,
  o item é persistido e o evento `items.created` é publicado.
- **AC-2** — Dado nome vazio ou > 120 caracteres, quando `POST /items`, então `422`.
- **AC-3** — Dado um item existente, quando `GET /items/{id}`, então `200`; leituras seguintes
  são servidas do cache por `APP_CACHE_TTL_SECONDS`.
- **AC-4** — Dado um id inexistente, quando `GET /items/{id}`, então `404`.
- **AC-5** — Dado uma mensagem `{"name": "..."}` em `items.import`, quando consumida pelo worker,
  então o item é criado como no AC-1; mensagens inválidas são rejeitadas.
- **AC-6** — `/health/live` retorna a versão implantada; `/health/ready` retorna `503` se alguma
  dependência falhar.

## Contratos
### HTTP
`POST /items` `{"name": "book"}` → `201`
`{"id": "3f0c...", "name": "book", "created_at": "2026-01-01T12:00:00Z"}`

### Eventos
| Direção | Tópico | Payload |
|---|---|---|
| publica | `items.created` | `{"item_id": "3f0c...", "name": "book", "occurred_at": "2026-01-01T12:00:00Z"}` |
| consome | `items.import` | `{"name": "book"}` |

### Dados
Tabela `items(id uuid pk, name varchar(120), created_at timestamptz)` — migração `0001`.
