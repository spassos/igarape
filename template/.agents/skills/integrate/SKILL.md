---
name: integrate
description: Add or change an integration with an external source or output — database table/migration, cache, message broker topic (publish or consume), or third-party HTTP API — following ports & adapters with fakes and integration tests. Use for "integração", "nova tabela", "migração", "consumir evento", "publicar evento", "chamar API", "cache".
---

# Integrate an external system

Every integration follows the same five steps (do not skip any):

1. **Port** — add/extend a `Protocol` in `application/ports.py`, typed with domain objects only.
2. **Fake** — in-memory implementation in `adapters/memory.py` used by unit tests and local runs.
3. **Adapter** — real implementation in `adapters/<system>.py` with explicit timeouts, typed
   errors and a `ping()` for readiness. Libraries already chosen (do not add alternatives):
   SQLAlchemy Core + Alembic (SQL), redis-py asyncio (cache), FastStream (Kafka/RabbitMQ),
   httpx + stamina (HTTP). New library? Write an ADR (`$plan`).
4. **Wiring** — construct it in `container.py` from `Settings` (new `APP_*` setting, `SecretStr`
   for credentials, update `.env.example` and `compose.yaml`), register cleanup in the exit stack
   and its health check.
5. **Tests** — unit tests through the fake; integration test against the real thing with
   testcontainers in `tests/integration/` (`@pytest.mark.integration`); contract examples from
   the spec as fixtures.

Recipes for each kind: `references/recipes.md`.
