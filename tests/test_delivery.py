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


def test_dast_scans_staging_only_after_a_verified_release(tmp_path: Path) -> None:
    jobs = workflow("deploy")["jobs"]
    dast = jobs["dast"]
    assert dast["needs"] == "deploy"
    assert matches(dast["if"], {"inputs.environment": "staging"})
    assert not matches(dast["if"], {"inputs.environment": "production"})
    # A separate job: least privilege and no deploy secrets in reach of the scanner.
    assert dast["permissions"] == {"contents": "read"} and "env" not in dast and "secrets" not in str(dast)
    (scan,) = [step for step in dast["steps"] if step.get("uses", "").startswith("zaproxy/action-baseline@")]
    assert re.fullmatch(r"zaproxy/action-baseline@[0-9a-f]{40}", scan["uses"])
    options = scan["with"]
    assert options["target"] == "${{ needs.deploy.outputs.url }}/health/live"
    assert re.fullmatch(r"ghcr\.io/zaproxy/zaproxy:[\d.]+@sha256:[0-9a-f]{64}", options["docker_name"])
    assert options["fail_action"] == "true" and options["allow_issue_writing"] == "false"
    assert options["cmd_options"].split() == ["-I"]  # warnings are reported, FAIL rules break the job

    assert jobs["deploy"]["outputs"]["url"] == "${{ steps.settings.outputs.url }}"
    settings = next(step for step in jobs["deploy"]["steps"] if step.get("id") == "settings")
    output = tmp_path / "output"
    env = {"APP_URL": "https://staging.example.test/", "GITHUB_OUTPUT": str(output)}
    subprocess.run(["bash", "-eu", "-c", settings["run"]], check=True, env=env)
    assert output.read_text() == "url=https://staging.example.test\n"


def test_zap_rules_fail_only_on_listed_rules() -> None:
    rules_file = TEMPLATE / ".zap" / "rules.tsv"
    rows = [line.split("\t") for line in rules_file.read_text().splitlines() if not line.startswith("#")]
    assert all(len(row) == 3 and row[0].isdigit() and row[2].startswith("(") for row in rows)
    ids = [row[0] for row in rows]
    actions = {row[1] for row in rows}
    assert len(ids) == len(set(ids))
    assert actions == {"FAIL", "WARN", "INFO", "IGNORE"}  # the action only passes `-c` with an IGNORE rule
    fail = {row[0] for row in rows if row[1] == "FAIL"}
    assert {"10062", "10097", "10115", "20020", "90022"} <= fail
