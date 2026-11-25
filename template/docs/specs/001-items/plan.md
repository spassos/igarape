# Plano — 001 Itens

**Spec:** ./spec.md · **ADRs:** 0002 · **Status:** Done

| AC | Nível | Teste |
|---|---|---|
| AC-1 | unit, api, integration | `tests/unit/test_item_service.py`, `tests/api/test_items_api.py`, `tests/integration/test_app.py` |
| AC-2 | unit, api | `tests/unit/test_domain.py`, `tests/api/test_items_api.py` |
| AC-3 | unit, integration | `test_get_reads_through_cache`, `tests/integration/test_app.py` |
| AC-4 | unit, api | `test_get_unknown_item_raises`, `test_unknown_item_returns_404` |
| AC-5 | unit | `tests/unit/test_worker.py` (quando há broker) |
| AC-6 | api, integration | `tests/api/test_health.py`, `tests/integration/test_app.py` |

- [x] T1 — Domínio `Item` + evento `ItemCreated`
- [x] T2 — `ItemService` com ports e fakes
- [x] T3 — Adapters reais + container + migração
- [x] T4 — API HTTP + health checks
- [x] T5 — Worker de importação
