# NNN — <título da fatia>

**Status:** Draft | Approved (<data>) · **PRD:** ../../product/<slug>.md · **Plan:** ./plan.md

## Contexto
<1 parágrafo: por que esta fatia, para quem.>

## Critérios de aceite
- **AC-1** — Dado <estado>, quando <ação>, então <resultado observável>.
- **AC-2** — Dado ..., quando <entrada inválida>, então `422` (`application/problem+json`) com `detail` explicando o campo.
- **AC-3** — Dado <dependência indisponível>, quando ..., então <comportamento degradado/erro> e log `<evento>`.
- **AC-4** — Dado nenhum token ou token inválido, então `401`; sem o escopo `<recurso>:<ação>`, então `403`.
- **AC-5** — Dado um recurso de outro sujeito, quando <ação>, então `404` (igual a inexistente).

## Contratos
### HTTP
`POST /v1/resource` (escopo `resource:write`) → `201`
```json
{"request": "exemplo"}
```
Erros (`application/problem+json`): `401` · `403` · `404` não encontrado ou de outro dono · `409` conflito · `413` · `422` validação · `503` dependência fora.

### Eventos
| Direção | Tópico/fila | Chave | Payload (exemplo) | Versionamento |
|---|---|---|---|---|
| publica | `resource.created` | `id` | `{"id": "...", "occurred_at": "..."}` | campos só aditivos |

### Dados
<Tabelas/colunas novas, índices, migração (expand → migrate → contract se houver quebra).>

## Requisitos não funcionais
- Performance: p95 < <x> ms em <y> rps.
- Observabilidade: logs `<evento>` com `<campos>`; readiness inclui `<dependência>`.

## Segurança
| Item | Decisão |
|---|---|
| Autenticação | <Bearer JWT (padrão) · rota pública justificada> |
| Autorização por recurso | <escopo por rota; regra de dono: quem lê/altera cada objeto; resposta para não dono = `404`> |
| Exposição de dados | <campos retornados; PII/LGPD; campos que nunca vêm do cliente (`id`, `owner_id`)> |
| Limites | <tamanho de campos/corpo, `limit` máximo de listagens, rate limit no gateway e fluxos sensíveis> |
| Saída para terceiros | <URLs validadas com `ensure_public_https_url`, respostas validadas, timeouts> |

## Fora de escopo
- ...
