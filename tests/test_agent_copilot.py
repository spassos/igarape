"""Check the GitHub Copilot adapter: custom agents, cloud-agent setup steps and MCP config."""

import json
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
MCP = {"docs": "https://example.com/mcp", "openai-docs": "https://developers.openai.com/mcp"}


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


def frontmatter(path: Path) -> tuple[dict[str, object], str]:
    _, header, body = path.read_text().split("---\n", 2)
    return yaml.safe_load(header), body


@pytest.fixture(scope="module")
def copilot(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("copilot") / "acme-orders", agents=["copilot"])


@pytest.fixture(scope="module")
def copilot_mcp(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return render(tmp_path_factory.mktemp("copilot-mcp") / "acme-orders", agents=["copilot"], mcp_servers=MCP)


def test_custom_agents_render_every_role(copilot: Path) -> None:
    agents = {p.name.removesuffix(".agent.md"): p for p in (copilot / ".github/agents").glob("*.agent.md")}
    assert agents.keys() == ROLES.keys()
    for name, path in agents.items():
        meta, body = frontmatter(path)
        assert meta["name"] == name
        assert isinstance(meta["description"], str) and meta["description"]
        tools = meta["tools"]
        assert {"read", "search", "execute"} <= set(tools)
        assert ("edit" in tools) is (ROLES[name] == "write")
        assert "AGENTS.md" in body and not body.startswith("\n\n")


def test_setup_steps_prepare_the_definition_of_done(copilot: Path) -> None:
    workflow = yaml.load(
        (copilot / ".github/workflows/copilot-setup-steps.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert workflow["permissions"] == {}
    assert set(workflow["on"]) == {"workflow_dispatch", "push", "pull_request"}
    assert list(workflow["jobs"]) == ["copilot-setup-steps"]
    job = workflow["jobs"]["copilot-setup-steps"]
    assert job["permissions"] == {"contents": "read"}
    checkout = job["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["persist-credentials"] == "false"
    assert any(step.get("run") == "uv sync --locked --all-groups" for step in job["steps"])


def test_only_selected_agents_are_rendered(copilot: Path, tmp_path: Path) -> None:
    assert (copilot / ".github/copilot-instructions.md").is_file()
    assert not (copilot / ".codex").exists()
    assert not (copilot / ".github/workflows/codex-review.yml").exists()
    assert not (copilot / ".vscode").exists() and not (copilot / ".github/mcp.json").exists()

    both = render(tmp_path / "both", agents=["copilot", "codex"])
    assert (both / ".codex/config.toml").is_file()
    assert (both / ".github/workflows/codex-review.yml").is_file()
    assert len(list((both / ".github/agents").glob("*.agent.md"))) == len(ROLES)
    assert (both / ".github/workflows/copilot-setup-steps.yml").is_file()

    codex = render(tmp_path / "codex", agents=["codex"])
    assert not (codex / ".github/agents").exists()
    assert not (codex / ".github/copilot-instructions.md").exists()
    assert not (codex / ".github/workflows/copilot-setup-steps.yml").exists()


def test_mcp_servers_reach_vscode_cli_and_agents(copilot_mcp: Path) -> None:
    expected = {name: {"type": "http", "url": url} for name, url in MCP.items()}
    assert json.loads((copilot_mcp / ".vscode/mcp.json").read_text()) == {"servers": expected}
    assert json.loads((copilot_mcp / ".github/mcp.json").read_text()) == {"mcpServers": expected}
    meta, _ = frontmatter(copilot_mcp / ".github/agents/reviewer.agent.md")
    assert {f"{name}/*" for name in MCP} <= set(meta["tools"])
