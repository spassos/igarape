# Contributing

Thanks for helping. This repository ships the `igarape` CLI and the Copier template it renders.
Read [`AGENTS.md`](AGENTS.md) and [`docs/architecture.md`](docs/architecture.md) before changing
the template.

## Development setup

Requirements: [uv](https://docs.astral.sh/uv/), Git, `make`, and Docker for the integration
scenarios.

```bash
git clone https://github.com/spassos/igarape.git && cd igarape
uv sync
uv run igarape new ../scratch-svc --template .   # render your local checkout
```

`--template .` renders the checkout at `HEAD`; Copier includes uncommitted changes and warns
about them (`DirtyLocalWarning`). Use `--ref` to render another revision.

## Test levels

| Command | What it does | Needs |
|---|---|---|
| `uv run ruff check . && uv run ruff format --check .` | Lint and format the CLI and tests | — |
| `uv run pytest` | Renders every scenario and checks the layout, agent adapters, CLI validation and delivery policy | — |
| `uv run pytest -m smoke` | Builds the wheel, generates the default service and calls its API over HTTP | — |
| `uv run pytest -m slow` | Runs `make bootstrap` and `make check` inside each generated scenario | Docker for `full-kafka`, `postgres-rabbit`, `redis-only` |
| `uv run pytest -m slow -k minimal` | One scenario only | — |

CI runs all of them (see [`template-ci.yml`](.github/workflows/template-ci.yml)), plus zizmor on
the generated workflows and an image build, smoke test and Trivy scan of generated services.

### Test policy

- **Every new feature and every bug fix comes with automated tests** in the same pull request.
  A bug fix starts with a test that reproduces the bug. Pull requests without tests for the
  behaviour they add or change are not merged.
- Template changes are covered at the level they affect: rendering/layout in
  `tests/test_template.py`, an agent adapter in `tests/test_agent_<agent>.py`, CLI input in
  `tests/test_cli.py` and the property-based `tests/test_cli_properties.py`, delivery policy in
  `tests/test_delivery.py`. Generated-service changes add tests inside `template/tests/` and must
  keep `make check` (coverage ≥ 90%) green in every scenario.
- CI must be green before merging; tests are never skipped, weakened or deleted to get green.

## Rules

- **Every scenario must pass its own gate.** A change to `template/` is done when
  `uv run pytest -m slow` is green for all scenarios. Jinja whitespace (`{%-`) is the usual cause
  of ruff format or isort failures in generated code.
- **New option ⇒ new scenario.** A new question in `copier.yml` needs a scenario in
  `SCENARIOS` in [`tests/test_template.py`](tests/test_template.py) and, if it changes generated
  code, an entry in the `generated-project` matrix of `template-ci.yml`.
- **Shared guidance lives once:** `AGENTS.md`, `.agents/skills/` and
  [`includes/roles.jinja`](includes/roles.jinja). Never copy role or skill text into one agent's
  files.
- **Keep generated projects lean:** prefer the standard library and already-chosen libraries
  (`template/docs/adr/0002-stack-and-architecture.md.jinja`).
- **Workflows** pin every action by full commit SHA with a `# vX.Y.Z` comment, start from
  `permissions: {}` and grant per job only what is needed, and check out with
  `persist-credentials: false`. Validate with:

  ```bash
  uvx zizmor --offline --min-severity medium template/.github/workflows .github/workflows
  docker run --rm -v "$PWD/.github/workflows:/w" -w /w rhysd/actionlint:latest -color=false *.yml
  ```

  Conditional workflow files only get a `.yml` name once rendered, so also scan a project
  generated with `--agent claude --agent codex --agent copilot --agent opencode`.
- **Base images are pinned by digest.** [`template/Dockerfile.jinja`](template/Dockerfile.jinja)
  has one literal `FROM image:tag@sha256:...` per Python version (Jinja picks one; keep each `FROM`
  free of Jinja so Scorecard can parse it). Generated projects keep them current with Dependabot.
  Refresh before a release with `uv run python scripts/refresh_image_digests.py` (`--check` only
  reports stale digests).
- **Language:** agent-facing files (AGENTS.md, skills, subagents) are English; generated human
  docs are Portuguese; this repository's own docs are English.

## Commits and pull requests

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages
and PR titles: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `build:`, `ci:`, `chore:`. Keep
one focused change per PR and fill in the [PR template](.github/pull_request_template.md).

## Adding a coding agent adapter

1. **Register it:** add the choice to `agents` in [`copier.yml`](copier.yml) and to `AGENTS` in
   [`src/igarape/cli.py`](src/igarape/cli.py).
2. **Instructions:** if the agent reads `AGENTS.md`, add nothing. Otherwise add the thinnest
   pointer its format supports (as `CLAUDE.md` does with `@AGENTS.md`).
3. **Skills:** reuse `.agents/skills/`. If the agent needs another location, use symlinks (as
   `.claude/skills/` does), not copies.
4. **Subagents:** add one file per role under a conditional directory such as
   `template/{% if '<agent>' in agents %}.<agent>{% endif %}/agents/`. Each file imports
   `includes/roles.jinja` and maps `role.access` (`read-only` or `write`) to the agent's
   permission model.
5. **MCP:** render the agent's MCP config only when `mcp_servers` is not empty.
6. **Docs:** mention the agent where `AGENTS.md.jinja`, `README.md.jinja` and
   `docs/ways-of-working.md` list agents, and update the agent table and badge in
   [`README.md`](README.md).
7. **Tests:** add `tests/test_agent_<agent>.py` (every role rendered, permissions follow access,
   nothing rendered when unselected) and add the agent to the `all-agents` scenario and the
   zizmor step in `template-ci.yml`.
