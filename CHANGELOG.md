# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Security fixes are listed under **Security** with
their advisory or CVE identifier.

## [0.2.0](https://github.com/spassos/igarape/compare/v0.1.0...v0.2.0) (2026-11-25)


### Added

* commit the scaffold and let Claude Code commit with git ([98c9638](https://github.com/spassos/igarape/commit/98c96382ea995fc8faec709c5d195b1766cda3e0))
* **site:** add the landing page on GitHub Pages ([9238b35](https://github.com/spassos/igarape/commit/9238b35ba521cd94412d2f3667f0eb09e08cca78))


### Fixed

* **template:** keep local variables out of exception logs ([9dc0525](https://github.com/spassos/igarape/commit/9dc0525637ed02fa3875a97afdc711ea96396dbc))
* **template:** render the reference spec for the chosen integrations ([4cec4ec](https://github.com/spassos/igarape/commit/4cec4ece0f760685f5076b5576e3ae93b90d2a80))


### Changed

* **readme:** add a "Why Igarapé" section ([2c9cb04](https://github.com/spassos/igarape/commit/2c9cb04a6bc8a90a213b1684999b4cc46ef723a8))
* **readme:** merge "What you get" into "Why Igarapé" ([52c4bf4](https://github.com/spassos/igarape/commit/52c4bf4ad06aaa1c55383eee1ec1d6e1f7dd2470))

## [Unreleased]

### Added

- Landing page at https://spassos.github.io/igarape/, in `site/` and deployed by `pages.yml`
  (GitHub Pages). It is static HTML and CSS with no scripts or third-party resources, and a test
  (`uv run pytest site/tests`, run on pull requests that touch the site or `README.md`) checks that
  every sentence comes literally from the README and that the agents, Python versions, skills and
  quick start match the repository. The site is not part of the CLI package or generated projects.

### Added

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

- Generated Claude Code settings allow `git` (the `implement` skill commits each task) and ask
  before `git push`. The generated README explains that project permissions apply only after the
  folder's trust dialog is accepted, and how to pass them to headless runs.
- Releases need no manual tagging. This repository runs release-please in `publish-pypi.yml`: the
  release PR bumps `pyproject.toml`, `uv.lock` and the manifest from Conventional Commits and adds
  the `CHANGELOG.md` entry; merging it tags `vX.Y.Z`, publishes the GitHub release and publishes
  that version to PyPI in the same run.
- Generated services run release-please (`ENABLE_RELEASES=true`) as a `release` job of `cd.yml`,
  after CI and before the image build (`release.yml` is removed). Merging the release PR tags the
  commit and, with CD, deploys it as that version: the image gets a `:X.Y.Z` tag, `APP_VERSION` and
  `/health/live` report `X.Y.Z` and the smoke test checks it. Other merges still ship the SHA.

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
