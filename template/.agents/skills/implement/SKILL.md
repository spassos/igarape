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
