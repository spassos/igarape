"""Check the Claude Code adapter: CLAUDE.md, bridged skills, subagents, settings and MCP."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml
from copier import run_copy

ROOT = Path(__file__).parents[1]
SKILLS = {"discovery", "specify", "plan", "implement", "integrate", "review", "ship"}
ROLES = {"architect": True, "reviewer": True, "security-auditor": True, "test-engineer": False}
MCP = {"openai-docs": "https://developers.openai.com/mcp", "docs": "https://example.com/mcp"}


def render(destination: Path, **answers: object) -> Path:
    run_copy(
        str(ROOT),
        destination,
        data={"project_name": "Acme Orders", "agents": ["claude"], **answers},
        defaults=True,
        unsafe=False,
        vcs_ref="HEAD",
        quiet=True,
    )
    return destination


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("claude") / "acme-orders", mcp_servers=MCP)


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    _, header, body = path.read_text().split("---\n", 2)
    return yaml.safe_load(header), body


def test_claude_md_imports_agents_md(project: Path) -> None:
    claude_md = (project / "CLAUDE.md").read_text()
    assert claude_md.startswith("@AGENTS.md\n")
    assert "## Claude Code" in claude_md


def test_skills_are_symlinks_to_the_shared_skills(project: Path) -> None:
    skills = project / ".claude/skills"
    assert {p.name for p in skills.iterdir()} == SKILLS
    for name in SKILLS:
        link = skills / name
        assert link.is_symlink()
        assert link.readlink() == Path("../../.agents/skills") / name
        assert (link / "SKILL.md").resolve() == (project / ".agents/skills" / name / "SKILL.md").resolve()
        assert (link / "SKILL.md").is_file()


def test_subagents_render_the_shared_roles(project: Path) -> None:
    agents = project / ".claude/agents"
    assert {p.stem for p in agents.glob("*.md")} == set(ROLES)
    for name, read_only in ROLES.items():
        meta, body = frontmatter(agents / f"{name}.md")
        assert meta["name"] == name
        assert meta["description"]
        assert ("disallowedTools" in meta) is read_only
        if read_only:
            assert meta["disallowedTools"] == "Edit, Write, NotebookEdit"
        assert body.startswith("You are ")
    leftovers = [p for p in project.rglob("*") if "{{" in p.name or "{%" in p.name or p.suffix == ".jinja"]
    assert not leftovers


def test_settings_allow_safe_targets_and_deny_secrets(project: Path) -> None:
    permissions = json.loads((project / ".claude/settings.json").read_text())["permissions"]
    assert "Bash(make check)" in permissions["allow"]
    assert {rule for rule in permissions["allow"] if rule.startswith("Bash(git")} == {
        "Bash(git status)",
        "Bash(git status --short)",
        "Bash(git diff)",
        "Bash(git diff --cached)",
        "Bash(git diff --stat)",
        "Bash(git log --oneline)",
        "Bash(git add -- *)",
        "Bash(git commit -m *)",
    }
    assert permissions["ask"] == ["Bash(git push *)"]
    assert "Read(./.env)" in permissions["deny"]


def test_mcp_json_lists_http_servers(project: Path) -> None:
    config = json.loads((project / ".mcp.json").read_text())
    assert config == {"mcpServers": {name: {"type": "http", "url": url} for name, url in MCP.items()}}


def test_only_selected_agents_are_rendered(project: Path) -> None:
    assert not (project / ".codex").exists()
    assert not (project / ".github/workflows/codex-review.yml").exists()
    assert (project / ".github/workflows/claude-review.yml").is_file()
    assert "agents:\n- claude" in (project / ".copier-answers.yml").read_text()


def test_without_mcp_servers_no_mcp_json(tmp_path: Path) -> None:
    project = render(tmp_path / "plain")
    assert not (project / ".mcp.json").exists()
    assert (project / ".claude/settings.json").is_file()


def test_claude_and_codex_together(tmp_path: Path) -> None:
    project = render(tmp_path / "both", agents=["claude", "codex"])
    assert (project / "CLAUDE.md").is_file()
    assert (project / ".claude/skills/review/SKILL.md").is_file()
    assert (project / ".codex/agents/reviewer.toml").is_file()
    assert (project / ".github/workflows/claude-review.yml").is_file()
    assert (project / ".github/workflows/codex-review.yml").is_file()


def test_codex_only_has_no_claude_files(tmp_path: Path) -> None:
    project = render(tmp_path / "codex", agents=["codex"])
    assert not (project / "CLAUDE.md").exists()
    assert not (project / ".claude").exists()
    assert not (project / ".github/workflows/claude-review.yml").exists()


@pytest.mark.slow
def test_generated_claude_project_passes_its_own_gates(tmp_path: Path) -> None:
    project = render(tmp_path / "gates", mcp_servers=MCP)
    env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    for target in ("bootstrap", "check"):
        subprocess.run(["make", target], cwd=project, check=True, env=env)
