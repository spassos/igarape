"""OpenCode adapter: subagents in .opencode/agents/*.md and MCP servers in opencode.json."""

import json
import tomllib
from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml
from copier import run_copy

ROOT = Path(__file__).parents[1]
ROLES = {
    "architect": "read-only",
    "reviewer": "read-only",
    "security_auditor": "read-only",
    "test_engineer": "write",
}
MCP = {"docs": "https://docs.example.com/mcp", 'team "tools"': "https://tools.example.com/mcp?a=1&b=2"}


def render(destination: Path, **answers: object) -> Path:
    run_copy(
        str(ROOT),
        destination,
        data={"project_name": "Acme Orders", **answers},
        defaults=True,
        unsafe=False,
        vcs_ref="HEAD",
        quiet=True,
    )
    return destination


def agent_file(project: Path, name: str) -> tuple[dict[str, object], str]:
    _, header, body = (project / f".opencode/agents/{name}.md").read_text().split("---\n", 2)
    return yaml.safe_load(header), body.strip()


def effect(rules: list[dict[str, str]], action: str, resource: str) -> str:
    """Evaluate OpenCode V2 rules on top of its allow-all base policy: the last match wins."""
    result = "allow"
    for rule in rules:
        pattern = rule["resource"]
        matches = fnmatchcase(resource, pattern) or (pattern.endswith(" *") and resource == pattern[:-2])
        if fnmatchcase(action, rule["action"]) and matches:
            result = rule["effect"]
    return result


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("opencode") / "acme", agents=["opencode"], mcp_servers=MCP)


def test_renders_one_v2_subagent_per_role(project: Path) -> None:
    assert {p.stem for p in (project / ".opencode/agents").glob("*.md")} == set(ROLES)
    for name in ROLES:
        meta, body = agent_file(project, name)
        assert set(meta) == {"description", "mode", "permissions"}, name
        assert meta["mode"] == "subagent"
        assert isinstance(meta["description"], str) and meta["description"]
        assert body.startswith("You are"), name
        assert all(set(rule) == {"action", "resource", "effect"} for rule in meta["permissions"])


@pytest.mark.parametrize("name", sorted(ROLES))
def test_permissions_follow_role_access(project: Path, name: str) -> None:
    rules = agent_file(project, name)[0]["permissions"]
    read_only = ROLES[name] == "read-only"

    assert effect(rules, "edit", "src/acme_orders/domain/models.py") == ("deny" if read_only else "allow")
    assert effect(rules, "subagent", "general") == "deny"
    assert effect(rules, "read", "src/acme_orders/container.py") == "allow"
    for command in ("git diff", "git diff main...HEAD", "git log -5 --stat", "git status"):
        assert effect(rules, "shell", command) == "allow", command
    for command in ("rm -rf src", "make fmt", "git diff --output=src/acme_orders/app.py"):
        assert effect(rules, "shell", command) == ("deny" if read_only else "allow"), command


def test_mcp_servers_in_opencode_json(project: Path) -> None:
    config = json.loads((project / "opencode.json").read_text())
    assert config == {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {"servers": {name: {"type": "remote", "url": url} for name, url in MCP.items()}},
    }


def test_only_selected_agent_is_configured(project: Path) -> None:
    assert not (project / ".codex").exists()
    assert not (project / ".github/workflows/codex-review.yml").exists()
    assert "agents:\n- opencode" in (project / ".copier-answers.yml").read_text()
    leftovers = [p for p in project.rglob("*") if "{{" in p.name or "{%" in p.name or p.suffix == ".jinja"]
    assert not leftovers


def test_no_opencode_json_without_mcp_servers(tmp_path: Path) -> None:
    project = render(tmp_path / "acme", agents=["opencode"])
    assert (project / ".opencode/agents/reviewer.md").is_file()
    assert not (project / "opencode.json").exists()


def test_opencode_and_codex_share_role_definitions(tmp_path: Path) -> None:
    project = render(tmp_path / "acme", agents=["opencode", "codex"], mcp_servers=MCP)
    assert (project / "opencode.json").is_file()
    assert (project / ".codex/config.toml").is_file()
    for name in ROLES:
        codex = tomllib.loads((project / f".codex/agents/{name}.toml").read_text())
        meta, body = agent_file(project, name)
        assert meta["description"] == codex["description"]
        assert body == codex["developer_instructions"].strip()
