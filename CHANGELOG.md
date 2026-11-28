# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Security fixes are listed under **Security** with
their advisory or CVE identifier.

## [0.3.1](https://github.com/spassos/igarape/compare/v0.3.0...v0.3.1) (2026-11-28)


### Changed

* track open work in TODO.md and add architecture governance to the roadmap ([24d9aef](https://github.com/spassos/igarape/commit/24d9aef27ddb22250e4a3c428b2cdc352c1a905c))

## [0.3.0](https://github.com/spassos/igarape/compare/v0.2.2...v0.3.0) (2026-11-26)


### Added

* generate guidance only for the selected coding agents ([b8feef0](https://github.com/spassos/igarape/commit/b8feef0e4d5af28ee8409a6c4db5bcd925e40c3e))
* one-command local dev and agent-specific generated guidance ([5103cb8](https://github.com/spassos/igarape/commit/5103cb808bdd0b1b3f7f6c902ed5d7f45f1d9179))
* one-command local development and clearer `igarape new` output ([d108459](https://github.com/spassos/igarape/commit/d108459da1de94c33e17836a205bbdd931b3374c))


### Fixed

* **cli:** report a skipped initial commit as skipped ([7756148](https://github.com/spassos/igarape/commit/7756148088f753df282cb4261b91a54607cd68b5))
* **template:** keep the developer's .env out of generated tests ([771ccad](https://github.com/spassos/igarape/commit/771ccadc3a03e6a8a569644f4cc0ade9633c3955))
* **template:** work with Colima and macOS iCloud folders out of the box ([6ead63a](https://github.com/spassos/igarape/commit/6ead63a492da96824867183a296d78d39cc4b5f1))

## [0.2.2](https://github.com/spassos/igarape/compare/v0.2.1...v0.2.2) (2026-11-25)


### Changed

* **site:** redesign the Igarapé landing page ([e1e0c7a](https://github.com/spassos/igarape/commit/e1e0c7aa2672673638fe03cb391d5594194b410e))
* **site:** redesign the Igarapé landing page ([4687b71](https://github.com/spassos/igarape/commit/4687b71d112f9cd2cb3486e10a528ac26c5d4539))

## [0.2.1](https://github.com/spassos/igarape/compare/v0.2.0...v0.2.1) (2026-11-25)


### Fixed

* make PyPI installs self-contained and harden generated workflows ([c49ed9c](https://github.com/spassos/igarape/commit/c49ed9cb506671beefb798a6d76e0c5cecbd61f0))
* make PyPI installs self-contained and harden generated workflows ([b5de0a8](https://github.com/spassos/igarape/commit/b5de0a855a6b9bb7dc0f6c081d84aefab3e02f52))

## [0.2.0](https://github.com/spassos/igarape/compare/v0.1.0...v0.2.0) - 2026-11-25

### Added

- Landing page at https://spassos.github.io/igarape/, in `site/` and deployed by `pages.yml`
  (GitHub Pages). It is static HTML and CSS with no scripts or third-party resources, and a test
  (`uv run pytest site/tests`, run on pull requests that touch the site or `README.md`) checks that
  every sentence comes literally from the README and that the agents, Python versions, skills and
  quick start match the repository. The site is not part of the CLI package or generated projects.
- `igarape new` commits the generated scaffold (`chore: initial scaffold from igarape`), so the
  first agent change starts from a clean tree. Without a Git user identity it still succeeds and
  prints how to commit.

### Security

- Generated services no longer write local variables into exception logs. `dict_tracebacks`
  rendered every frame's locals, so an unhandled error could log bearer tokens, token subjects
  (often e-mail addresses) or other personal data. Tracebacks now keep the frames without locals,
  and a generated test fails if a local value reaches the log. Affects projects generated with
  0.1.0; no advisory has been published.

### Changed

- Releases need no manual tagging. This repository runs release-please in `publish-pypi.yml`: the
  release PR bumps `pyproject.toml`, `uv.lock` and the manifest from Conventional Commits and adds
  the `CHANGELOG.md` entry; merging it tags `vX.Y.Z`, publishes the GitHub release and publishes
  that version to PyPI in the same run.
- Generated services run release-please (`ENABLE_RELEASES=true`) as a `release` job of `cd.yml`,
  after CI and before the image build (`release.yml` is removed). Merging the release PR tags the
  commit and, with CD, deploys it as that version: the image gets a `:X.Y.Z` tag, `APP_VERSION` and
  `/health/live` report `X.Y.Z` and the smoke test checks it. Other merges still ship the SHA.
- Generated Claude Code settings allow `git` (the `implement` skill commits each task) and ask
  before `git push`. The generated README explains that project permissions apply only after the
  folder's trust dialog is accepted, and how to pass them to headless runs.
- README: a "Why Igarapé" section, with the former "What you get" merged into it.

### Fixed

- Generated release PRs only updated `CHANGELOG.md` (release type `simple`): the version in
  `pyproject.toml` never moved. They now use the `python` release type and also bump the project's
  entry in `uv.lock`, so the release commit still passes `uv sync --locked` and `uv lock --check`.
- The reference spec and plan (`docs/specs/001-items/`) describe only the integrations chosen at
  generation. An in-memory project no longer documents a PostgreSQL table, migrations, Redis or
  the `items.import` worker, which led coding agents to write acceptance criteria the service
  cannot meet. The worker criterion is now the last one (AC-11, with a broker), so AC-1 to AC-10
  keep the same ids in every scenario.

## [0.1.0] - 2026-11-25

First release of the `igarape` CLI and template.

### Added

- `igarape new <dir>` CLI (Copier underneath; `copier update` for upgrades) with `--agent`
  (repeatable: `claude`, `codex`, `copilot`, `opencode`), `--postgres`, `--redis`,
  `--broker kafka|rabbit`, `--mcp NAME=URL`, `--python`, `--template` and `--ref`.
- Agent-neutral guidance written once: `AGENTS.md`, seven SDLC skills and four subagent roles
  rendered for Codex, Claude Code, GitHub Copilot and OpenCode.
- Generated FastAPI service with hexagonal layers enforced by import-linter, in-memory by
  default, with opt-in PostgreSQL, Redis and Kafka/RabbitMQ.
- Security by default in generated services (OWASP API Security Top 10 2023): generic
  JWT/OIDC authentication (JWKS, scopes, deny by default), object-level authorization,
  `/v1` routes, RFC 9457 problem details, security headers, request-body limit, `/docs` off in
  production and an SSRF guard for outbound HTTP.
- `make check` gate in generated services: Ruff, mypy `--strict`, import-linter, pip-audit and
  pytest with branch coverage ≥ 90%, including Schemathesis contract tests, Hypothesis property
  tests and an Alembic migration round-trip.
- Generated CI/CD with pinned actions, gitleaks, zizmor, Trivy, provenance attestation, opt-in
  CD with smoke test and rollback, an OWASP ZAP baseline against staging and release-please.
- Repository controls: Template CI over six scenarios with real PostgreSQL, Redis, Kafka and
  RabbitMQ, image build and scan of generated services, CodeQL, OpenSSF Scorecard and Dependabot.

### Security

- Base images of the generated `Dockerfile` pinned by digest; Debian security updates applied at
  build time and pip removed from the runtime image (fixable HIGH CVEs failed the image scan).
- The CLI rejects `--mcp` URLs with an empty `?` or `#`, which slipped past the
  no-query/fragment rule (found by property-based testing).

[Unreleased]: https://github.com/spassos/igarape/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/spassos/igarape/releases/tag/v0.1.0
