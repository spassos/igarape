"""Validate delivery policy in the workflow files copied verbatim into every service."""

import re
import runpy
import subprocess
from pathlib import Path

import pytest
import yaml

TEMPLATE = Path(__file__).resolve().parents[1] / "template"


def workflow(name: str) -> dict:
    path = TEMPLATE / ".github" / "workflows" / f"{name}.yml"
    return yaml.load(path.read_text(), Loader=yaml.BaseLoader)


def matches(condition: str, context: dict[str, str]) -> bool:
    """Evaluate the equality checks used by the two publication jobs."""
    for clause in condition.split(" && "):
        comparison = re.fullmatch(r"([\w.]+) == '([^']+)'", clause)
        assert comparison, clause
        if context.get(comparison[1], "") != comparison[2]:
            return False
    return True


@pytest.mark.parametrize("cd,releases", [(False, False), (True, False), (False, True), (True, True)])
def test_main_delivery_policy(cd: bool, releases: bool) -> None:
    delivery = workflow("cd")
    release = workflow("release")
    jobs = delivery["jobs"]
    context = {"github.ref": "refs/heads/main"}
    if cd:
        context["vars.ENABLE_CD"] = "true"
    if releases:
        context["vars.ENABLE_RELEASES"] = "true"
    assert "pull_request" in workflow("ci")["on"]
    assert "main" in delivery["on"]["push"]["branches"]
    assert "main" in release["on"]["push"]["branches"]
    assert jobs["ci"]["uses"] == "./.github/workflows/ci.yml" and "if" not in jobs["ci"]
    assert matches(jobs["build"]["if"], context) is cd
    assert matches(release["jobs"]["release-please"]["if"], context) is releases
    assert jobs["build"]["needs"] == "ci"
    assert jobs["staging"]["needs"] == "build"
    assert set(jobs["production"]["needs"]) == {"build", "staging"}


def test_deploy_requires_destination_before_rollout() -> None:
    job = workflow("deploy")["jobs"]["deploy"]
    assert "if" not in job
    steps = job["steps"]
    validate = next(step for step in steps if step.get("name") == "Check deployment settings")
    assert steps.index(validate) < next(i for i, step in enumerate(steps) if step.get("id") == "rollout")
    result = subprocess.run(["bash", "-eu", "-c", validate["run"]], check=False, env={}, capture_output=True)
    assert result.returncode != 0 and b"APP_URL" in result.stderr
    assert (
        steps[-1]["if"]
        == "failure() && (steps.rollout.outcome == 'failure' || steps.verify.outcome == 'failure')"
    )


@pytest.mark.parametrize(
    "live_status,version,ready_status,health,expected",
    [
        (200, "abc", 200, "ok", True),
        (500, "abc", 200, "ok", False),
        (200, "old", 200, "ok", False),
        (200, "abc", 503, "ok", False),
        (200, "abc", 200, "error", False),
    ],
)
def test_deploy_smoke(live_status, version, ready_status, health, expected, monkeypatch) -> None:
    verify = runpy.run_path(str(TEMPLATE / "scripts" / "smoke.py"))["verify"]
    fixtures = {"live": (live_status, {"version": version}), "ready": (ready_status, {"status": health})}
    monkeypatch.setitem(verify.__globals__, "fetch", lambda url: fixtures[url.rsplit("/", 1)[1]])
    assert verify("http://example.test", "abc", attempts=1, delay=0) is expected
