import ast
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from igarape import cli

ROOT = Path(__file__).resolve().parents[1]


def test_cli_records_options_in_generated_project(tmp_path: Path) -> None:
    project = tmp_path / "catalog"
    subprocess.run(
        [
            "igarape",
            "new",
            str(project),
            "--template",
            str(ROOT),
            "--name",
            'Catalog "API"',
            "--description",
            'Team """A""" service',
            "--postgres",
            "--broker",
            "rabbit",
            "--mcp",
            "docs=https://docs.example.com/mcp",
            "--mcp",
            "tracker=https://tracker.example.com/mcp",
        ],
        check=True,
    )
    metadata = tomllib.loads((project / "pyproject.toml").read_text())
    assert metadata["project"]["description"] == 'Team """A""" service'
    ast.parse((project / "src/catalog/__init__.py").read_text())
    ast.parse((project / "src/catalog/entrypoints/http/app.py").read_text())
    assert (project / "migrations").is_dir()
    assert (project / "src/catalog/entrypoints/worker.py").is_file()
    config = tomllib.loads((project / ".codex/config.toml").read_text())
    assert config["mcp_servers"] == {
        "docs": {"url": "https://docs.example.com/mcp"},
        "tracker": {"url": "https://tracker.example.com/mcp"},
    }


@pytest.mark.parametrize("case", ["existing", "invalid-mcp", "duplicate-mcp"])
def test_cli_rejects_invalid_request_without_modifying_destination(tmp_path: Path, case: str) -> None:
    project = tmp_path / "orders"
    flags = []
    if case == "existing":
        project.mkdir()
        (project / "keep.txt").write_text("keep")
    elif case == "invalid-mcp":
        flags = ["--mcp", "docs=https://user:password@example.com"]
    else:
        flags = ["--mcp", "docs=https://example.com", "--mcp", "docs=https://example.org"]
    result = subprocess.run(["igarape", "new", str(project), *flags], capture_output=True, check=False)
    assert result.returncode != 0
    if case == "existing":
        assert list(project.iterdir()) == [project / "keep.txt"]
        assert (project / "keep.txt").read_text() == "keep"
    else:
        assert not project.exists()


def test_cli_reports_version_and_records_selected_agents(tmp_path: Path) -> None:
    version = subprocess.run(["igarape", "--version"], capture_output=True, text=True, check=True)
    assert version.stdout.startswith("igarape ")
    project = tmp_path / "billing"
    subprocess.run(["igarape", "new", str(project), "--template", str(ROOT), "--agent", "codex"], check=True)
    answers = (project / ".copier-answers.yml").read_text()
    assert "agents:\n- codex" in answers
    assert (project / ".codex/agents/reviewer.toml").is_file()


def test_cli_rejects_unknown_agent(tmp_path: Path) -> None:
    project = tmp_path / "orders"
    result = subprocess.run(
        ["igarape", "new", str(project), "--agent", "unknown"], capture_output=True, check=False
    )
    assert result.returncode != 0 and b"--agent" in result.stderr
    assert not project.exists()


def git_env(tmp_path: Path, config: str) -> dict[str, str]:
    global_config = tmp_path / "gitconfig"
    global_config.write_text(config)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return {**env, "GIT_CONFIG_GLOBAL": str(global_config), "GIT_CONFIG_NOSYSTEM": "1"}


def test_cli_commits_the_scaffold_when_git_has_an_identity(tmp_path: Path) -> None:
    project = tmp_path / "orders"
    env = git_env(tmp_path, "[user]\n\tname = Dev\n\temail = dev@example.invalid\n")

    subprocess.run(["igarape", "new", str(project), "--template", str(ROOT)], check=True, env=env)

    log = subprocess.run(
        ["git", "log", "--format=%s"], cwd=project, env=env, capture_output=True, text=True, check=True
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=project, env=env, capture_output=True, text=True, check=True
    )
    assert log.stdout.splitlines() == ["chore: initial scaffold from igarape"]
    assert status.stdout == ""


@pytest.mark.parametrize(
    ("config", "diagnostics"),
    [
        ("[user]\n\tuseConfigOnly = true\n", ("user.name", "user.email")),
        (
            (
                "[user]\n\tname = Dev\n\temail = dev@example.invalid\n"
                "[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = igarape-test-signer-does-not-exist\n"
            ),
            ("igarape-test-signer-does-not-exist", "failed to sign"),
        ),
    ],
    ids=["missing-identity", "signing-failure"],
)
def test_cli_still_succeeds_and_explains_when_git_cannot_commit(
    tmp_path: Path, config: str, diagnostics: tuple[str, ...]
) -> None:
    project = tmp_path / "orders"
    env = {**git_env(tmp_path, config), "LC_ALL": "C"}

    result = subprocess.run(
        ["igarape", "new", str(project), "--template", str(ROOT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "initial commit skipped" in result.stderr
    assert all(diagnostic in result.stderr for diagnostic in diagnostics)
    assert 'git commit -m "chore: initial scaffold from igarape"' in result.stderr
    assert (project / ".git").is_dir()
    assert (project / "pyproject.toml").is_file()


@pytest.mark.parametrize(
    ("flags", "dev_line"),
    [
        ([], "API with reload at http://127.0.0.1:8000/docs (in memory, no Docker)"),
        (["--postgres", "--redis"], "PostgreSQL, Redis in Docker + API with reload"),
    ],
    ids=["in-memory", "postgres-redis"],
)
def test_cli_reports_steps_and_next_steps_for_the_profile(
    tmp_path: Path, flags: list[str], dev_line: str
) -> None:
    project = tmp_path / "orders"
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    result = subprocess.run(
        ["igarape", "new", str(project), "--template", str(ROOT), "--agent", "claude", *flags],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    # Progress goes to stderr, one line per step and without tool noise; stdout is the summary.
    steps = [line.strip() for line in result.stderr.splitlines() if line.startswith("  ")]
    assert [line.split(" ...")[0] for line in steps] == [
        f"Rendering the template from {ROOT}",
        "Locking dependencies (uv lock)",
        "Initial Git commit",
    ]
    assert all(re.search(r" \.\.\. done \(\d+\.\ds\)$", line) for line in steps)
    assert "Resolved" not in result.stderr and "Warning" not in result.stderr
    assert "  cd orders\n" in result.stdout
    assert f"make dev         # {dev_line}" in result.stdout
    assert "make token" in result.stdout and "run `claude`" in result.stdout
    assert "virtualenv" not in result.stdout


def test_cli_explains_an_active_virtualenv(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin/uv").symlink_to(shutil.which("uv") or "/usr/bin/false")
    env = {**os.environ, "VIRTUAL_ENV": str(venv), "PATH": f"{venv / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    result = subprocess.run(
        ["igarape", "new", str(tmp_path / "orders"), "--template", str(ROOT)],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert f"uv comes from the active virtualenv ({venv})" in result.stdout
    assert "make targets use it even with this virtualenv active" in result.stdout


def test_cli_points_to_uv_when_it_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    notes = cli.environment_notes(["PostgreSQL"])
    assert notes[0].startswith("uv is not on your PATH")
    assert "make dev DOCKER=0" in notes[1]
