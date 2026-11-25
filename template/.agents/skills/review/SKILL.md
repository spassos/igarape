---
name: review
description: Review the current change against the request or approved spec, conventions, security and Definition of Done, then fix blocking findings. Use for "review", "revisão", "code review", "security review", or before opening/merging a PR.
---

# Review

1. Run `make check` and investigate failures before handing off.
2. Review a local fix against the request and regression test. For planned work, inspect the
   approved spec and plan. Ask the `reviewer` for independent correctness review or the
   `security_auditor` for independent security review when the change warrants it.
3. Checklist (the reviewers use it too):
   - [ ] The regression test fails without the fix, or each acceptance criterion has a test that fails without the change.
   - [ ] Layering respected (`make arch`); domain/application framework-free; wiring only in `container.py`.
   - [ ] Inputs validated at the edge; domain errors mapped to correct status codes; no stack traces leaked.
   - [ ] Every network call has a timeout; retries only on idempotent operations; consumers idempotent.
   - [ ] No secrets/PII in code, logs, fixtures; settings via `Settings`/`SecretStr`.
   - [ ] Migrations reversible or expand/contract; API/event contracts backward compatible or versioned.
   - [ ] Logs are structured with meaningful event names; readiness covers new dependencies.
   - [ ] Clean code: small functions, clear names, no dead/commented code, no needless abstraction.
   - [ ] Docs updated (spec contracts, ADRs, README/AGENTS.md if commands changed).
4. Fix every **Blocking** finding (re-run `make check`); answer suggestions explicitly (fix or why not).
5. Next: `$ship`.
