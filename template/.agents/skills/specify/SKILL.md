---
name: specify
description: Write a testable feature spec (acceptance criteria, API/event contracts, non-functional requirements) in docs/specs/NNN-slug/spec.md from an approved PRD or a clear request. Use for "spec", "especificação", "critérios de aceite", "user story", or when a public contract, migration or architectural decision needs an approved spec.
---

# Specify → spec.md

1. Find the source: an approved PRD in `docs/product/` or an explicit request. If the request is
   vague, ask — do not guess behavior.
2. Pick the next number: `ls docs/specs` → `NNN` (3 digits). Create `docs/specs/NNN-<slug>/spec.md`
   from `assets/spec-template.md`. One spec = one independently shippable slice (≤ ~3 days of work).
3. Acceptance criteria are the contract with tests: ids `AC-1..n`, Given/When/Then, observable
   behavior only (HTTP status/body, persisted state, emitted event, log/metric). Cover the happy
   path, validation errors, not-found/conflict, dependency failure (timeout, broker down) and
   idempotency where relevant.
4. Contracts: for HTTP give method, path, request/response examples and error codes; for events
   give topic/queue, key, JSON payload example and versioning rule; for data give tables/columns
   and migration impact. Breaking changes need a migration path.
5. Non-functional: latency/throughput targets, security (authn/authz, PII), observability (logs,
   events), feature flags/rollout.
6. Ask the human to approve. Set `Status: Approved`. Next: `$plan`.
