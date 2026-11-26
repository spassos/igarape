# AGENTS.md — igarape

This repository ships the **igarape CLI** (`igarape new <dir>`). It uses Copier to generate Python
services with an agentic SDLC that works across coding agents: Codex, Claude Code, GitHub Copilot
and OpenCode (`--agent`, repeatable).

- `src/igarape/cli.py` — CLI entry point.
- `copier.yml` — questions. `template/` — everything rendered into new projects (`*.jinja` files
  are rendered; conditional files/dirs use `{% if ... %}name{% endif %}`).
- `includes/roles.jinja` — the single, agent-neutral definition of the subagent roles
  (`architect`, `test_engineer`, `reviewer`, `security_auditor`). Agent-specific files import it;
  never copy role text into an agent's files.
- `includes/opencode_agent.jinja` — macro that renders a role as an OpenCode V2 agent file.
- `includes/agents.jinja` — `skill(name)` macro: shared docs reference skills in the selected agent's
  syntax (`$name` with Codex, `/name` with Claude Code only, plain name otherwise).
- `.agents/skills/new-service/` — skill that scaffolds a new service (`$new-service`).
- `tests/` — `uv run pytest` renders every scenario and checks the layout; `-m smoke` runs the CLI
  wheel and exercises the default API over HTTP; `-m slow` runs `make check` in each generated
  project (Docker for integration scenarios).

## Rules when changing the template
- Shared guidance lives once: `AGENTS.md`, `.agents/skills/` and `includes/roles.jinja`. An agent
  adapter only adds what that agent's format requires, and only when the agent is selected. A
  project generated for one agent never mentions the others (tested per agent).
- Generated code must pass its own gates for **every** scenario: `uv run pytest -m slow`.
  Watch Jinja whitespace (`{%-`): ruff format/isort failures usually come from it.
- Keep generated projects lean: prefer standard library and already-chosen libraries
  (template/docs/adr/0002). New option in `copier.yml` ⇒ new scenario in `tests/test_template.py`.
- Workflows pin actions by commit SHA and use least privilege; validate with
  `uvx zizmor --offline template/.github/workflows .github/workflows` and actionlint. CodeQL uses
  advanced setup (`.github/workflows/codeql.yml`): keep the repository's CodeQL default setup off.
- Generated base images are pinned by literal digests in `template/Dockerfile.jinja`, one `FROM`
  per Python version with no Jinja inside the `FROM` line (Scorecard parses the template); refresh
  with `scripts/refresh_image_digests.py`.
- Agent-facing files (AGENTS.md, skills, subagents) are English; generated human docs are Portuguese.
- Repository docs (`README.md`, `docs/architecture.md`, `CONTRIBUTING.md`, `SECURITY.md`) are English.
  Keep the README "Why you can trust it" table in sync with `.github/workflows/template-ci.yml`, and
  never claim a feature in the README that the template and its tests do not deliver.
