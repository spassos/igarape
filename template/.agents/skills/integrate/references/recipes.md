# Integration recipes

## SQL table (PostgreSQL)
1. Add the `Table` to `adapters/postgres.py` (SQLAlchemy Core) and a repository class.
2. `make migration m="create <table>"` → review the generated file in `migrations/versions/`
   (autogenerate misses renames/data moves). Breaking change? expand (add nullable/new) →
   backfill → switch reads → contract (drop) in separate releases.
3. Bound parameters only (SQLAlchemy expressions); never f-strings into SQL.
4. Integration test with the `database_url` fixture (migrations already applied).

## Cache (Redis)
- Cache-aside in the use case: `get` → miss → load → `set(ttl)`. Keys `<aggregate>:<id>`;
  version the key prefix when the serialized shape changes. Invalidate on writes.
- Cache is an optimization: a cache failure must not fail reads unless the spec says so.

## Publish an event
- Domain event dataclass with `topic` and `payload()` (JSON-friendly, additive-only changes).
- Publish through `EventPublisher` after the state change succeeds. Need atomicity between DB and
  broker? Use the transactional outbox (write to an `outbox` table in the same transaction, relay
  publishes) and record it in an ADR.
- Document topic, key and payload in the spec; consumers must be idempotent.

## Consume an event
- Add a pydantic command/event model in `entrypoints/worker.py` and a subscriber in
  `register_handlers` that only parses and delegates to a use case. Messages carry identity
  (`owner_id`) only from trusted internal producers; restrict who may publish with broker ACLs.
- Handlers must be idempotent (dedupe by event id or natural key) and safe to retry.
- Unit test with FastStream's `TestKafkaBroker`/`TestRabbitBroker`; integration test with a
  real broker container.

## Third-party HTTP API
```python
class PaymentStatusResponse(BaseModel):  # the provider's contract, validated at our edge
    status: Literal["pending", "paid", "failed"]


class PaymentsGateway:  # adapters/payments.py, implements a port
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @retry_transient  # only for idempotent calls (GET/PUT or with idempotency keys)
    async def get_status(self, payment_id: str) -> PaymentStatus:
        response = await self._client.get(f"/payments/{quote(payment_id, safe='')}")
        response.raise_for_status()
        body = PaymentStatusResponse.model_validate_json(response.content)
        return PaymentStatus(body.status)
```
- Client from `create_http_client(settings.payments_url, timeout_seconds=...)`, created and
  closed in `container.py`. Every call has a timeout; never use library defaults.
- Base URLs come from `Settings`. Any URL that comes from a user, a message or a provider
  response (webhooks, callbacks, file links) goes through `ensure_public_https_url()` from
  `adapters/http_client.py` before the request (SSRF, OWASP API7). Do not follow redirects to
  unvalidated hosts.
- Treat provider responses as untrusted input (OWASP API10): parse them with a pydantic model,
  reject unexpected shapes as a domain error, cap sizes you store.
- Map provider errors to domain errors; never leak provider payloads to our API.
- Tests with `respx` (unit) — no real internet calls in CI. Cover a malformed provider response
  and a rejected private/`http://` URL.
