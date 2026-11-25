# AGENTS.md — igarape

This repository ships the **igarape CLI** (`igarape new <dir>`). It uses Copier to generate Python
services with an agentic SDLC that works across coding agents. Supported today: Codex. Planned:
Claude Code, GitHub Copilot, OpenCode (see the roadmap in README.md).

- `src/igarape/cli.py` — CLI entry point.
- `copier.yml` — questions. `template/` — everything rendered into new projects (`*.jinja` files
  are rendered; conditional files/dirs use `{% if ... %}name{% endif %}`).
- `includes/roles.jinja` — the single, agent-neutral definition of the subagent roles
  (`architect`, `test_engineer`, `reviewer`, `security_auditor`). Agent-specific files import it;
  never copy role text into an agent's files.
- `.agents/skills/new-service/` — skill that scaffolds a new service (`$new-service`).
- `tests/` — `uv run pytest` renders every scenario and checks the layout; `-m smoke` runs the CLI
  wheel and exercises the default API over HTTP; `-m slow` runs `make check` in each generated
  project (Docker for integration scenarios).

## Rules when changing the template
- Shared guidance lives once: `AGENTS.md`, `.agents/skills/` and `includes/roles.jinja`. An agent
  adapter only adds what that agent's format requires, and only when the agent is selected.
- Generated code must pass its own gates for **every** scenario: `uv run pytest -m slow`.
  Watch Jinja whitespace (`{%-`): ruff format/isort failures usually come from it.
- Keep generated projects lean: prefer standard library and already-chosen libraries
  (template/docs/adr/0002). New option in `copier.yml` ⇒ new scenario in `tests/test_template.py`.
- Workflows pin actions by commit SHA and use least privilege; validate with
  `uvx zizmor --offline template/.github/workflows .github/workflows` and actionlint.
- Agent-facing files (AGENTS.md, skills, subagents) are English; generated human docs are Portuguese.
