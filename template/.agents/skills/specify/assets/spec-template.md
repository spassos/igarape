# NNN — <título da fatia>

**Status:** Draft | Approved (<data>) · **PRD:** ../../product/<slug>.md · **Plan:** ./plan.md

## Contexto
<1 parágrafo: por que esta fatia, para quem.>

## Critérios de aceite
- **AC-1** — Dado <estado>, quando <ação>, então <resultado observável>.
- **AC-2** — Dado ..., quando <entrada inválida>, então `422` com `detail` explicando o campo.
- **AC-3** — Dado <dependência indisponível>, quando ..., então <comportamento degradado/erro> e log `<evento>`.

## Contratos
### HTTP
`POST /resource` → `201`
```json
{"request": "exemplo"}
```
Erros: `404` não encontrado · `409` conflito · `422` validação · `503` dependência fora.

### Eventos
| Direção | Tópico/fila | Chave | Payload (exemplo) | Versionamento |
|---|---|---|---|---|
| publica | `resource.created` | `id` | `{"id": "...", "occurred_at": "..."}` | campos só aditivos |

### Dados
<Tabelas/colunas novas, índices, migração (expand → migrate → contract se houver quebra).>

## Requisitos não funcionais
- Performance: p95 < <x> ms em <y> rps.
- Segurança: <authn/authz, PII/LGPD, validações>.
- Observabilidade: logs `<evento>` com `<campos>`; readiness inclui `<dependência>`.

## Fora de escopo
- ...
