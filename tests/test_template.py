"""Check the rendered layout, a live default API, and the generated projects' gates."""

import json
import os
import re
import secrets
import shutil
import signal
import subprocess
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
    sh(
        tmp_path,
        "uvx",
        "--isolated",
        "--from",
        str(wheel),
        "igarape",
        "new",
        project.name,
        "--template",
        str(ROOT),
    )
    assert (project / ".git").is_dir()
    assert (project / "uv.lock").is_file()

    env = {key: value for key, value in project_env().items() if not key.startswith("APP_")}
    env.update(UVICORN_HOST="127.0.0.1", UVICORN_PORT="0", APP_AUTH_DEV_SECRET=secrets.token_hex(32))
    token = subprocess.run(
        ["uv", "run", "--frozen", "python", "scripts/dev_token.py", "--sub", "alice"],
        cwd=project,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    log = tmp_path / "api.log"
    with log.open("w") as output:
        server = subprocess.Popen(
            ["make", "run"],
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
