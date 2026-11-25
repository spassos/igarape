<p align="center">
  <img src="docs/assets/logo.svg" alt="igarapé — o caminho da ideia até a produção" width="560">
</p>

# Igarapé

**Igarapé** is a CLI that generates Python service repositories ready for coding agents, with one
process, one set of skills and one set of quality gates — from product discovery to a version
verified in production.

```bash
uvx --from 'git+https://github.com/spassos/igarape.git@main' igarape new orders-api
cd orders-api && make bootstrap && make run
```

> **Status:** early development. Codex is supported today; Claude Code, GitHub Copilot and
> OpenCode are next (see [Roadmap](#roadmap)).

## Why the name

*Igarapé* comes from Tupi: *igara* (canoe) + *pé* (path) — "the canoe's path", the narrow
waterways that cross the Amazon forest. The process is the igarapé; every coding agent (Codex,
Claude Code, Copilot, OpenCode) is an *igara* travelling the same path to production.

## What you get

- **Agentic SDLC:** six phases — Discovery → Specify → Plan → Implement → Review → Ship — each with
  a versioned artifact (PRD, spec, plan, ADRs) and a human gate. A well-scoped local fix can start
  directly at `implement`, with a regression test.
- **Agent layer:** `AGENTS.md`, one skill per phase in `.agents/skills/`, and four subagent roles
  (`architect`, `test_engineer`, `reviewer`, `security_auditor`) defined once and rendered for each
  selected agent.
- **Python service:** FastAPI with hexagonal architecture enforced by import-linter. In memory by
  default; PostgreSQL (SQLAlchemy + Alembic), Redis and Kafka/RabbitMQ (FastStream) are opt-in.
- **One gate:** `make check` runs Ruff (PEP 8/257, Bandit rules), mypy `--strict`, import-linter,
  pip-audit and pytest with a coverage threshold — the same command for people, agents and CI.
- **Delivery:** GitHub Actions with pinned actions, gitleaks, zizmor and Trivy. Opt-in CD deploys
  to staging and production and only calls a release done when a smoke test sees the commit SHA
  live.

## Usage

```bash
igarape new inventory --postgres --redis --broker rabbit
igarape new ai-service --mcp docs=https://example.com/mcp
igarape --help
```

| Option | Default | Effect |
|---|---|---|
| `--agent` (repeatable) | `codex` | Coding agents to configure |
| `--name` / `--description` / `--author` | derived | Project metadata |
| `--python` | `3.13` | 3.12, 3.13 or 3.14 |
| `--postgres`, `--redis` | off | Optional integrations, tested against real containers |
| `--broker` | `none` | `kafka` or `rabbit` (publisher + consumer worker) |
| `--mcp NAME=URL` (repeatable) | none | Project MCP server (HTTPS, no credentials) |
| `--template` / `--ref` | upstream `main` | Use a local checkout or a specific revision |

Install it for repeated use with `uv tool install git+https://github.com/spassos/igarape.git`.
Generated projects record their template revision in `.copier-answers.yml`, so `uvx copier update`
brings later template improvements.

## Agent support

| Agent | Instructions | Skills | Subagents | MCP | Status |
|---|---|---|---|---|---|
| Codex | `AGENTS.md` | `.agents/skills` | `.codex/agents/*.toml` | `.codex/config.toml` | ✅ |
| Claude Code | `CLAUDE.md` → `@AGENTS.md` | `.claude/skills` (symlinks) | `.claude/agents/*.md` | `.mcp.json` | Planned |
| GitHub Copilot | `AGENTS.md` | `.agents/skills` | `.github/agents/*.agent.md` | `.vscode/mcp.json` | Planned |
| OpenCode | `AGENTS.md` | `.agents/skills` | `.opencode/agents/*.md` | `opencode.json` | Planned |

## Roadmap

1. **Portable core** — CLI, `--agent`, agent-neutral roles, Codex adapter. *(in progress)*
2. **Claude Code and OpenCode** — adapters, `make agents-check` drift check, Claude review workflow.
3. **GitHub Copilot** — custom agents, `copilot-setup-steps.yml`, MCP for VS Code.
4. **Evidence** — Docker image build in CI, pilot comparing agents with and without guidance.

## Developing

```bash
uv sync
uv run pytest            # render every scenario and check the layout
uv run pytest -m smoke   # build the wheel, generate a service and call its API
uv run pytest -m slow    # make check inside each generated project (Docker for integrations)
```

Read [`AGENTS.md`](AGENTS.md) before changing the template. Publishing to PyPI:
[`docs/pypi.md`](docs/pypi.md).

## License

[MIT](LICENSE)
