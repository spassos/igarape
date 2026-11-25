---
name: plan
description: Technical design and task breakdown for an approved spec — writes docs/specs/NNN-slug/plan.md and ADRs in docs/adr/ for hard-to-reverse decisions. Use for "plan", "design", "arquitetura", "ADR", "quebrar em tarefas" after a spec is approved.
---

# Plan → plan.md (+ ADRs)

1. Read the approved `spec.md`, `AGENTS.md`, `docs/conventions.md`, existing `docs/adr/` and the
   code it touches. Spawn the `architect` subagent for an independent design when the change adds
   an integration, a data migration or a public contract.
2. Write `docs/specs/NNN-<slug>/plan.md` from `assets/plan-template.md`:
   - Design per layer (domain / application+ports / adapters / entrypoints / container wiring).
   - Contracts and migrations (expand/contract for breaking changes).
   - Failure modes: timeouts, retries (idempotent only), duplicates, ordering, partial failure.
   - Test strategy: map every AC to test level and file.
   - Tasks: small (≤ ~2h), each leaves `make check` green, ordered so main stays releasable.
3. Decision that is costly to reverse (new datastore, broker, library, pattern, public contract)?
   Write `docs/adr/NNNN-<slug>.md` from `assets/adr-template.md` (status Proposed).
4. Ask the human to approve the plan (and ADRs → Accepted). Next: `$implement` task by task.
