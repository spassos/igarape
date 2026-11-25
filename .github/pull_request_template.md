## What and why
<!-- One or two sentences. Link the issue if there is one. -->

## Checklist
- [ ] Title follows Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`, …)
- [ ] `uv run ruff check . && uv run pytest` green
- [ ] Template change: `uv run pytest -m slow` green for every scenario
- [ ] New `copier.yml` option: new scenario in `tests/test_template.py`
- [ ] Agent guidance changed only in the shared sources (`AGENTS.md`, `.agents/skills/`, `includes/roles.jinja`)
- [ ] Workflow change: actions pinned by SHA, least-privilege permissions, zizmor and actionlint clean
- [ ] Docs updated (README, `docs/architecture.md`, generated docs)
