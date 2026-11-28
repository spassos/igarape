# TODO

Open work for Igarapé, in rough priority order. The [README roadmap](README.md#roadmap) has the
high-level milestones; this file has the details. Remove an item when its PR merges.

## Validate on real machines

- [ ] End-to-end run of the agentic SDLC (discovery → specify → plan → implement → review → ship) with
  Codex, GitHub Copilot and OpenCode, as was done for Claude Code. Note what each agent needs that
  the generated guidance does not give it.
- [ ] On macOS with Colima, in a freshly generated project: `make dev` and `make test` with no
  testcontainers variables exported (Docker context detection, `TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE`).
- [ ] On macOS, a project inside an iCloud-synced folder (`~/Documents`): confirm `make bootstrap`
  clears the hidden flag and imports work without `UV_NO_SYNC=1` or a manual `chflags`.

## Architecture governance

Make the decisions behind the checks explicit, persistent and independently governed, also for
existing repositories.

- [ ] Traceability: every import-linter contract, and any test or CI gate tied to a decision, cites
  the ADR it implements. A check fails when an Accepted ADR has no enforcement or a rule points to a
  Superseded ADR.
- [ ] Ownership: generate a `CODEOWNERS` entry for `docs/adr/` and the `[tool.importlinter]`
  configuration, so changing a constraint needs the architecture owners' approval. A revision is a
  new ADR that supersedes the old one.
- [ ] Brownfield adoption: record an existing repository's current architecture as ADRs, baseline
  today's violations (import-linter `ignore_imports`) and ratchet, so new code cannot add violations
  and the baseline only shrinks.

## Template and CLI

- [ ] `igarape update --postgres` (and `--redis`, `--broker`): switch a generated project's profile
  through `copier update`, with an `AGENTS.md` rule telling agents to use it instead of editing by
  hand. Document what happens when generated files were changed (merge conflicts).
- [ ] `make agents-check`: fail when one agent's files diverge from the shared sources.
- [ ] Event consumers: a dead-letter topic's maximum message size must be at least the source
  topic's, because the rejection header makes the message larger (found in the customers example).

## Supply chain and OpenSSF Scorecard

Current score: https://scorecard.dev/viewer/?uri=github.com/spassos/igarape

- [ ] Token-Permissions: move `contents: write` in `publish-pypi.yml` to the narrowest scope possible.
- [ ] Signed-Releases: sign or attest the release artifacts (wheel and sdist).
- [ ] Fuzzing: fuzz the CLI's input validation (for example `--mcp` parsing) if Atheris supports the
  Python versions in use.
- [ ] CII-Best-Practices: register for the OpenSSF Best Practices badge.
- [ ] Branch-Protection and Code-Review: protect `main`, require reviews and allow squash merging
  only. Squash merges also stop release-please from listing a PR twice in the CHANGELOG (once for the
  merge commit, once for its commits).
- [ ] Maintained improves on its own once the repository is 90 days old (around 2027-02-23).

## Evidence and positioning

- [ ] Pilot comparing agents with and without the generated guidance on the same tasks.
- [ ] Explain, with evidence, what Igarapé does that the alternatives do not.

## Landing page

- [ ] Phase 2: serve the site from `igarape.dev` once the domain is owned and verified
  (runbook in `site/README.md`).
