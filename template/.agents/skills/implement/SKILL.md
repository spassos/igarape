---
name: implement
description: Implement a clearly requested local fix or an approved plan with tests, hexagonal layering, and make check. Use for "implement", "implementar", "codar", "fix", or when executing tasks from docs/specs/NNN-*/plan.md.
---

# Implement

For a clearly requested local fix, take the expected behavior from the request and start with a
regression test. For changes to a public contract, a migration, or an architectural decision,
wait for an approved spec and plan, then work through the unchecked tasks in order.

For the fix or each planned task:

1. **Red** — write a test that reproduces the problem or proves the acceptance criterion. Run
   `make test-unit` for unit and API tests, or the relevant integration test, and check that it
   fails for the expected reason. Use the `test_engineer` subagent when independent test design helps.
2. **Green** — make the smallest change in the appropriate layer. Business rules go in
   `domain/`, orchestration in `application/`, I/O in `adapters/`, and transport contracts in
   `entrypoints/`. Add new integrations with `$integrate`. Select adapters in `container.py`.
3. **Refactor** — remove duplication and keep names and functions clear.
4. **Verify** — run `make check` and fix any failures caused by the change. Keep the quality
   rules and coverage threshold in place.
5. **Hand off** — report the regression test or acceptance criteria covered, the checks run, and
   any blockers. For planned work, update task status in `plan.md` and the affected documentation,
   and commit the completed task with its spec and task identifiers. Use `$review` for review.

New or changed HTTP endpoint checklist (details: `docs/conventions.md#segurança-owasp-api-top-10`):

- Route under `/v1` that declares the `require_scopes("<resource>:<action>")` dependency with
  the least scope; never add a public route without an approved spec saying so.
- Owned objects: pass `principal.subject` to the use case, filter by owner there and raise the
  not-found domain error for another owner's object (`404`, never `403`).
- Request schema accepts only client-settable fields (never `id`, `owner_id`, timestamps); string
  and list fields have size limits; list endpoints take `limit` with a maximum.
- Errors are domain errors mapped to `application/problem+json`; nothing secret or internal in
  `detail`; never log tokens or the `Authorization` header.
- Tests: happy path plus `401`, `403` and another-owner `404` in `tests/api/test_security.py`
  using the `make_auth_headers` fixture; the Schemathesis contract test must stay green.
