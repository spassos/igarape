# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Security fixes are listed under **Security** with
their advisory or CVE identifier.

## [Unreleased]

### Fixed

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
