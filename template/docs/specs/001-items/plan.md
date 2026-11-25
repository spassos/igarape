# Plano — 001 Itens

**Spec:** ./spec.md · **ADRs:** 0002, 0003, 0004 · **Status:** Done

| AC | Nível | Teste |
|---|---|---|
| AC-1 | unit, api, integration | `tests/unit/test_item_service.py`, `tests/api/test_items_api.py`, `tests/integration/test_app.py` |
| AC-2 | unit, property, api | `tests/unit/test_domain.py`, `tests/unit/test_domain_properties.py`, `tests/api/test_items_api.py` |
| AC-3 | unit, integration | `test_get_reads_through_cache`, `tests/integration/test_app.py` |
| AC-4 | unit, api | `test_get_unknown_item_raises`, `test_unknown_item_returns_404` |
| AC-5 | unit | `tests/unit/test_worker.py` (quando há broker) |
| AC-6 | api, integration | `tests/api/test_health.py`, `tests/integration/test_app.py` |
| AC-7 | unit, api | `tests/unit/test_jwt_verifier.py`, `tests/api/test_security.py` |
| AC-8 | api | `tests/api/test_security.py` |
| AC-9 | unit, api | `tests/unit/test_item_service.py`, `tests/api/test_security.py` |
| AC-10 | api | `tests/api/test_security.py` |
| AC-11 | contract | `tests/api/test_openapi_contract.py` |
| Migrações | integration | `tests/integration/test_migrations.py` (quando há Postgres) |

## Ameaças e abusos
| Ameaça (OWASP API 2023) | Controle | Teste |
|---|---|---|
| Ler item alheio por id (API1) | filtro por `owner_id` no caso de uso → `404` | AC-9 |
| Token forjado, `alg` trocado, expirado (API2) | `TokenVerifier` com allowlist de algoritmos e claims obrigatórias | AC-7 |
| Definir `owner_id` pelo corpo (API3) | schema de entrada só com `name` | AC-1 |
| Corpo enorme, volume (API4) | `APP_MAX_BODY_BYTES`; rate limit no gateway | AC-10 |
| Exposição de docs e erros (API8) | `/docs` só local/test; problem+json | AC-10, AC-11 |

- [x] T1 — Domínio `Item` + evento `ItemCreated`
- [x] T2 — `ItemService` com ports e fakes
- [x] T3 — Adapters reais + container + migração
- [x] T4 — API HTTP + health checks
- [x] T5 — Worker de importação
- [x] T6 — Autenticação JWT/OIDC, escopos e dono do item
- [x] T7 — Erros problem+json, headers de segurança, limite de corpo
- [x] T8 — Testes de contrato, propriedades e migrações
