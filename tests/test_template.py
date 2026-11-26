"""Check the rendered layout, a live default API, and the generated projects' gates."""

import ast
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import tomllib
from contextlib import suppress
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest
from copier import run_copy

ROOT = Path(__file__).parents[1]

SCENARIOS = {
    "with-mcp": {
        "use_postgres": False,
        "use_redis": False,
        "event_broker": "none",
        "mcp_servers": {"openai-docs": "https://developers.openai.com/mcp"},
    },
    "full-kafka": {"use_postgres": True, "use_redis": True, "event_broker": "kafka"},
    "minimal": {"use_postgres": False, "use_redis": False, "event_broker": "none"},
    "postgres-rabbit": {"use_postgres": True, "use_redis": False, "event_broker": "rabbit"},
    "redis-only": {"use_postgres": False, "use_redis": True, "event_broker": "none"},
    "all-agents": {
        "use_postgres": False,
        "use_redis": False,
        "event_broker": "none",
        "agents": ["claude", "codex", "copilot", "opencode"],
        "mcp_servers": {"docs": "https://docs.example.com/mcp"},
    },
}


def render(destination: Path, answers: dict[str, object]) -> Path:
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


def project_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}


def sh(cwd: Path, *command: str) -> None:
    subprocess.run(command, cwd=cwd, check=True, env=project_env())


@pytest.fixture(params=sorted(SCENARIOS))
def project(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    answers = {} if request.param == "minimal" else SCENARIOS[request.param]
    return render(tmp_path / request.param, answers)


def test_renders_expected_layout(project: Path) -> None:
    answers = SCENARIOS[project.name]
    package = project / "src" / "acme_orders"

    assert (package / "adapters" / "postgres.py").exists() is answers["use_postgres"]
    assert (project / "migrations").exists() is answers["use_postgres"]
    assert (package / "adapters" / "redis_cache.py").exists() is answers["use_redis"]
    assert (package / "entrypoints" / "worker.py").exists() is (answers["event_broker"] != "none")
    for path in [
        "AGENTS.md",
        "docs/conventions.md",
        "docs/specs/001-items/spec.md",
        "docs/specs/001-items/plan.md",
    ]:
        assert (project / path).is_file(), path
    tomllib.loads((project / "pyproject.toml").read_text())
    skills = {p.parent.name for p in (project / ".agents/skills").glob("*/SKILL.md")}
    assert {"discovery", "specify", "plan", "implement", "integrate", "review", "ship"} <= skills
    agents = {p.stem for p in (project / ".codex/agents").glob("*.toml")}
    assert {"architect", "reviewer", "test_engineer", "security_auditor"} <= agents
    config = tomllib.loads((project / ".codex/config.toml").read_text())
    assert config.get("mcp_servers", {}) == {
        name: {"url": url} for name, url in answers.get("mcp_servers", {}).items()
    }
    for agent in (project / ".codex/agents").glob("*.toml"):
        assert {"name", "description", "developer_instructions"} <= tomllib.loads(agent.read_text()).keys()
    agents = answers.get("agents", ["codex"])
    assert (
        "agents:\n" + "".join(f"- {agent}\n" for agent in agents)
        in (project / ".copier-answers.yml").read_text()
    )
    assert (project / ".github/workflows/codex-review.yml").is_file()
    sandbox = {
        name: tomllib.loads((project / f".codex/agents/{name}.toml").read_text())["sandbox_mode"]
        for name in ("architect", "reviewer", "security_auditor", "test_engineer")
    }
    assert sandbox == {
        "architect": "read-only",
        "reviewer": "read-only",
        "security_auditor": "read-only",
        "test_engineer": "workspace-write",
    }
    leftovers = [p for p in project.rglob("*") if "{{" in p.name or p.suffix == ".jinja"]
    assert not leftovers


def test_reference_spec_describes_only_chosen_integrations(project: Path) -> None:
    answers = SCENARIOS[project.name]
    spec_dir = project / "docs/specs/001-items"
    spec = (spec_dir / "spec.md").read_text()
    plan = (spec_dir / "plan.md").read_text()
    broker = answers["event_broker"] != "none"

    assert ("items.import" in spec) is broker
    assert ("**AC-11**" in spec) is broker
    assert ("Tabela `items(" in spec) is answers["use_postgres"]
    assert ("migrations/versions/" in spec) is answers["use_postgres"]
    assert ("não há banco" in spec) is not answers["use_postgres"]
    assert ("Cache de leitura: Redis" in spec) is answers["use_redis"]
    criteria = re.findall(r"\*\*(AC-\d+)\*\*", spec)
    assert criteria == [f"AC-{n}" for n in range(1, len(criteria) + 1)]
    assert re.findall(r"^\| (AC-\d+) \|", plan, re.MULTILINE) == criteria
    for test_file in re.findall(r"`(tests/[\w/]+\.py)`", plan):
        assert (project / test_file).is_file(), test_file


def test_release_please_versions_pyproject_lockfile_and_changelog(project: Path) -> None:
    name = tomllib.loads((project / "pyproject.toml").read_text())["project"]["name"]
    version = tomllib.loads((project / "pyproject.toml").read_text())["project"]["version"]
    (config,) = json.loads((project / "release-please-config.json").read_text())["packages"].values()
    assert json.loads((project / ".release-please-manifest.json").read_text()) == {".": version}
    # The python strategy bumps pyproject.toml; uv.lock records the project version too, and a stale
    # one fails `uv sync --locked` in the image build of the release commit.
    assert config["release-type"] == "python" and config["package-name"] == name
    assert config["changelog-path"] == "CHANGELOG.md" and config["include-component-in-tag"] is False
    assert config["extra-files"] == [
        {"type": "toml", "path": "uv.lock", "jsonpath": f"$.package[?(@.name.value=='{name}')].version"}
    ]


def make_dry_run(project: Path, *args: str) -> str:
    result = subprocess.run(
        # A fixed COMPOSE keeps the dry run independent of the Docker tools on this machine.
        ["make", "-n", "COMPOSE=docker compose", *args],
        cwd=project,
        env=project_env(),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_make_dev_starts_only_the_chosen_infrastructure(project: Path) -> None:
    answers = SCENARIOS[project.name]
    infra = [
        name
        for name, chosen in (
            ("postgres", answers["use_postgres"]),
            ("redis", answers["use_redis"]),
            ("broker", answers["event_broker"] != "none"),
        )
        if chosen
    ]
    makefile = (project / "Makefile").read_text()
    # A virtualenv the user activated to install igarape must not leak into the project's tools.
    assert "\nunexport VIRTUAL_ENV\n" in makefile
    dev = make_dry_run(project, "dev")
    assert "uv sync --all-groups" in dev and "uvicorn --factory" in dev
    # The app image is never built for daily development; only the chosen services start.
    assert "--build" not in dev and "docker build" not in dev
    if infra:
        assert f"docker compose up -d --wait {' '.join(infra)}" in dev
        assert ("alembic upgrade head" in dev) is answers["use_postgres"]
        no_docker = make_dry_run(project, "dev", "DOCKER=0")
        assert "docker" not in no_docker.replace("DOCKER=0", "")
        assert "uvicorn --factory" in no_docker
    else:
        assert "docker" not in dev and "infra:" not in makefile


def fake_tools(directory: Path, **scripts: str) -> dict[str, str]:
    """PATH holding only fake executables (plus nothing else), so real Docker never interferes."""
    directory.mkdir()
    for name, body in scripts.items():
        tool = directory / name.replace("_", "-")
        tool.write_text(f"#!/bin/sh\n{body}\n")
        tool.chmod(0o755)
    return {**project_env(), "PATH": str(directory)}


@pytest.mark.parametrize(
    ("tools", "expected"),
    [
        # Colima from Homebrew without the Compose plugin: `docker compose` is not a command.
        ({"docker": '[ "$1" = compose ] && exit 125; exit 0'}, "brew install docker-compose"),
        ({"docker": '[ "$1" = info ] && exit 1; exit 0'}, "colima start"),
        ({}, "Docker is not installed"),
    ],
    ids=["no-compose-plugin", "daemon-stopped", "no-docker"],
)
def test_make_infra_explains_what_docker_is_missing(
    tmp_path: Path, tools: dict[str, str], expected: str
) -> None:
    project = render(tmp_path / "svc", SCENARIOS["postgres-rabbit"])
    make = shutil.which("make")
    assert make is not None
    result = subprocess.run(
        [make, "infra"],
        check=False,
        cwd=project,
        env=fake_tools(tmp_path / "bin", **tools),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert expected in result.stderr
    assert "DOCKER=0" in result.stderr


def test_make_infra_falls_back_to_standalone_docker_compose(tmp_path: Path) -> None:
    project = render(tmp_path / "svc", SCENARIOS["postgres-rabbit"])
    make = shutil.which("make")
    assert make is not None
    env = fake_tools(
        tmp_path / "bin",
        docker='[ "$1" = compose ] && exit 125; exit 0',
        docker_compose='echo "standalone $*"',
    )
    result = subprocess.run([make, "infra"], cwd=project, env=env, capture_output=True, text=True, check=True)
    assert "standalone up -d --wait postgres broker" in result.stdout


def test_project_imports_from_src_without_its_pth_file(project: Path) -> None:
    # macOS hides .venv files in iCloud-synced folders and Python 3.13+ skips hidden .pth files.
    makefile = (project / "Makefile").read_text()
    assert "\nexport PYTHONPATH := $(CURDIR)/src$(if $(PYTHONPATH),:$(PYTHONPATH))\n" in makefile
    assert "chflags -R nohidden .venv" in makefile
    pytest_options = tomllib.loads((project / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert pytest_options["pythonpath"] == ["src"]


def docker_context_helper(project: Path) -> str:
    conftest = (project / "tests/integration/conftest.py").read_text()
    module = ast.parse(conftest)
    (function,) = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "use_active_docker_context"
    ]
    return "import os, shutil, subprocess\n" + (ast.get_source_segment(conftest, function) or "")


@pytest.mark.parametrize(
    ("context_host", "environment", "expected"),
    [
        (
            "unix:///Users/dev/.colima/default/docker.sock",
            {},
            {
                "DOCKER_HOST": "unix:///Users/dev/.colima/default/docker.sock",
                "TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE": "/var/run/docker.sock",
            },
        ),
        (
            "unix:///Users/dev/.docker/run/docker.sock",
            {},
            {"DOCKER_HOST": "unix:///Users/dev/.docker/run/docker.sock"},
        ),
        ("unix:///var/run/docker.sock", {}, {}),
        (
            "unix:///ignored.sock",
            {"DOCKER_HOST": "unix:///Users/dev/.colima/work/docker.sock"},
            {
                "DOCKER_HOST": "unix:///Users/dev/.colima/work/docker.sock",
                "TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE": "/var/run/docker.sock",
            },
        ),
    ],
    ids=["colima", "docker-desktop", "default-socket", "explicit-docker-host"],
)
def test_integration_tests_follow_the_active_docker_context(
    tmp_path: Path, context_host: str, environment: dict[str, str], expected: dict[str, str]
) -> None:
    project = render(tmp_path / "svc", SCENARIOS["postgres-rabbit"])
    keys = ("DOCKER_HOST", "TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE")
    env = {
        k: v
        for k, v in fake_tools(tmp_path / "bin", docker=f'echo "{context_host}"').items()
        if k not in keys
    }
    script = docker_context_helper(project) + (
        f"\nuse_active_docker_context()\nprint({{k: os.environ[k] for k in {keys!r} if k in os.environ}})\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        env=env | environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert ast.literal_eval(result.stdout) == expected


@pytest.mark.slow
def test_generated_project_passes_its_own_gates(project: Path) -> None:
    if project.name not in {"minimal", "with-mcp", "all-agents"} and shutil.which("docker") is None:
        pytest.skip("Docker is required for integration tests")
    sh(project, "make", "bootstrap")
    sh(project, "make", "check")


def request_json(
    url: str, payload: dict[str, str] | None = None, token: str | None = None
) -> tuple[int, dict[str, object]]:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
    )
    with urlopen(request, timeout=2) as response:
        return response.status, json.load(response)


def wait_for_api(server: subprocess.Popen[bytes], log: Path) -> str:
    deadline = time.monotonic() + 30
    while server.poll() is None and time.monotonic() < deadline:
        address = re.search(r"Uvicorn running on (http://127\.0\.0\.1:\d+)", log.read_text())
        if address:
            url = address[1]
            try:
                status, ready = request_json(f"{url}/health/ready")
            except (URLError, TimeoutError):
                pass
            else:
                if status == 200 and ready["status"] == "ok":
                    return url
        time.sleep(0.1)
    pytest.fail(f"The generated API did not become ready:\n{log.read_text()}")


@pytest.mark.smoke
def test_default_scaffold_runs_without_docker(tmp_path: Path) -> None:
    project = tmp_path / "acme-orders"
    dist = tmp_path / "dist"
    sh(ROOT, "uv", "build", "--wheel", "--out-dir", str(dist))
    (wheel,) = dist.glob("*.whl")
    installation = tmp_path / "installation"
    sh(tmp_path, "uv", "venv", "--seed", str(installation))
    scripts = installation / "bin"
    sh(tmp_path, str(scripts / "python"), "-m", "pip", "install", str(wheel))

    # Git is a system prerequisite. uv must come from the wheel's dependencies.
    git = shutil.which("git")
    assert git is not None
    system_tools = tmp_path / "system-tools"
    system_tools.mkdir()
    (system_tools / "git").symlink_to(git)
    subprocess.run(
        [str(scripts / "igarape"), "new", project.name, "--template", str(ROOT)],
        cwd=tmp_path,
        check=True,
        env={**project_env(), "PATH": os.pathsep.join((str(system_tools), os.defpath))},
    )
    assert (project / ".git").is_dir()
    assert (project / "uv.lock").is_file()

    # Follow the README with the pip virtualenv still active, as a developer would.
    env = {key: value for key, value in project_env().items() if not key.startswith("APP_")}
    env.update(UVICORN_HOST="127.0.0.1", UVICORN_PORT="0", VIRTUAL_ENV=str(installation))
    bootstrap = subprocess.run(
        ["make", "bootstrap"], cwd=project, env=env, check=True, capture_output=True, text=True
    )
    assert "does not match the project environment" not in bootstrap.stdout + bootstrap.stderr
    assert re.search(r"^APP_AUTH_DEV_SECRET=[0-9a-f]{64}$", (project / ".env").read_text(), re.MULTILINE)
    token = subprocess.run(
        ["make", "-s", "token", "sub=alice"],
        cwd=project,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    log = tmp_path / "api.log"
    with log.open("w") as output:
        server = subprocess.Popen(
            ["make", "dev"],
            cwd=project,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            url = wait_for_api(server, log)
            created_status, item = request_json(f"{url}/v1/items", {"name": "book"}, token)
            assert created_status == 201
            assert item["name"] == "book"
            assert request_json(f"{url}/v1/items/{item['id']}", token=token) == (200, item)
            with pytest.raises(HTTPError) as anonymous:
                request_json(f"{url}/v1/items/{item['id']}")
            assert anonymous.value.code == 401
        except Exception:
            print(log.read_text())
            raise
        finally:
            with suppress(ProcessLookupError):
                os.killpg(server.pid, signal.SIGTERM)
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait()


AGENT_WORDS = {
    "claude": r"claude",
    "codex": r"codex",
    "copilot": r"copilot",
    "opencode": r"opencode",
}
SKILL_SYNTAX = {
    "codex": "`$implement`",
    "claude": "`/implement`",
    "copilot": "`implement`",
    "opencode": "`implement`",
}


@pytest.mark.parametrize("agent", sorted(AGENT_WORDS))
def test_single_agent_project_mentions_no_other_agent(tmp_path: Path, agent: str) -> None:
    project = render(tmp_path / agent, {"agents": [agent], "use_postgres": True, "event_broker": "kafka"})
    others = re.compile("|".join(word for name, word in AGENT_WORDS.items() if name != agent), re.IGNORECASE)
    leaks = [
        f"{path.relative_to(project)}: {match[0]}"
        for path in project.rglob("*")
        if path.is_file() and not path.is_symlink()
        for match in [others.search(f"{path.relative_to(project)}\n{path.read_text(errors='ignore')}")]
        if match
    ]
    assert leaks == []
    # Skills are referenced with the selected agent's own syntax.
    for doc in ("AGENTS.md", "docs/ways-of-working.md", ".agents/skills/review/SKILL.md"):
        text = (project / doc).read_text()
        assert "{{" not in text and "{%" not in text
    assert SKILL_SYNTAX[agent] in (project / "AGENTS.md").read_text()
    if agent != "codex":
        assert "$implement" not in (project / "AGENTS.md").read_text()
    review = (project / ".agents/skills/review/SKILL.md").read_text()
    assert review.startswith("---\nname: review\n") and "\n---\n\n# Review" in review
