"""Validate delivery policy in the workflow files copied verbatim into every service."""

import os
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
    jobs = delivery["jobs"]
    context = {"github.ref": "refs/heads/main"}
    if cd:
        context["vars.ENABLE_CD"] = "true"
    if releases:
        context["vars.ENABLE_RELEASES"] = "true"
    assert "pull_request" in workflow("ci")["on"]
    assert "main" in delivery["on"]["push"]["branches"]
    assert not (TEMPLATE / ".github" / "workflows" / "release.yml").exists()
    assert jobs["ci"]["uses"] == "./.github/workflows/ci.yml" and "if" not in jobs["ci"]
    assert matches(jobs["build"]["if"], context) is cd
    # The release job always runs after CI (only its step is gated), so the build never waits on
    # a skipped job and a release commit is tagged before its image is built and deployed.
    release = jobs["release"]
    assert release["needs"] == "ci" and "if" not in release
    (step,) = release["steps"]
    assert step["uses"].startswith("googleapis/release-please-action@")
    assert matches(step["if"], context) is releases
    assert release["permissions"] == {"contents": "write", "issues": "write", "pull-requests": "write"}
    assert set(jobs["build"]["needs"]) == {"ci", "release"}
    assert jobs["staging"]["needs"] == "build"
    assert set(jobs["production"]["needs"]) == {"build", "staging"}
    for environment in ("staging", "production"):
        assert jobs[environment]["with"]["version"] == "${{ needs.build.outputs.version }}"


@pytest.mark.parametrize("release", ["", "1.4.0"])
def test_image_ships_the_release_version_or_the_sha(release: str, tmp_path: Path) -> None:
    build = workflow("cd")["jobs"]["build"]
    step = next(step for step in build["steps"] if step.get("id") == "name")
    assert step["env"]["RELEASE"] == "${{ needs.release.outputs.version }}"
    output = tmp_path / "output"
    sha = "0123abc"
    env = {
        "RELEASE": release,
        "RELEASES_ENABLED": "false",
        "GITHUB_SHA": sha,
        "GITHUB_REPOSITORY": "Acme/Orders",
        "GITHUB_OUTPUT": str(output),
    }
    subprocess.run(["bash", "-eu", "-c", step["run"]], check=True, env=env)
    repo = "ghcr.io/acme/orders"
    tags = [f"{repo}:{sha}", f"{repo}:main"] + ([f"{repo}:{release}"] if release else [])
    lines = "\n".join(["tags<<EOF", *tags, "EOF"])
    assert output.read_text() == f"repo={repo}\nversion={release or sha}\n{lines}\n"
    assert build["outputs"]["version"] == "${{ steps.name.outputs.version }}"
    pushed = next(step for step in build["steps"] if step.get("id") == "build")["with"]
    assert pushed["build-args"] == "APP_VERSION=${{ steps.name.outputs.version }}"
    assert pushed["tags"] == "${{ steps.name.outputs.tags }}"
    # The smoke test checks what was built, not the SHA, so a release proves its version is live.
    deploy = workflow("deploy")
    assert deploy["on"]["workflow_call"]["inputs"]["version"]["required"] == "true"
    verify = next(step for step in deploy["jobs"]["deploy"]["steps"] if step.get("id") == "verify")
    assert '--version "$VERSION"' in verify["run"]
    assert deploy["jobs"]["deploy"]["env"]["VERSION"] == "${{ inputs.version }}"


@pytest.mark.parametrize(
    "releases_enabled,tagged_ref,recovered",
    [
        ("true", "HEAD", True),
        ("true", "HEAD^", False),
        ("true", None, False),
        ("false", "HEAD", False),
    ],
)
def test_delivery_recovers_version_only_for_the_tagged_release_commit(
    releases_enabled: str, tagged_ref: str | None, recovered: bool, tmp_path: Path
) -> None:
    steps = workflow("cd")["jobs"]["build"]["steps"]
    assert steps[0]["with"]["fetch-tags"] == "${{ vars.ENABLE_RELEASES == 'true' }}"
    step = next(step for step in steps if step.get("id") == "name")
    assert step["env"]["RELEASES_ENABLED"] == "${{ vars.ENABLE_RELEASES }}"

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for message in ("previous release", "current commit"):
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--no-gpg-sign",
                "--allow-empty",
                "-qm",
                message,
            ],
            cwd=tmp_path,
            check=True,
        )
    version = "1.4.0"
    (tmp_path / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    if tagged_ref:
        subprocess.run(["git", "tag", "--no-sign", f"v{version}", tagged_ref], cwd=tmp_path, check=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    output = tmp_path / "output"
    env = {
        **os.environ,
        "RELEASE": "",
        "RELEASES_ENABLED": releases_enabled,
        "GITHUB_SHA": sha,
        "GITHUB_REPOSITORY": "Acme/Orders",
        "GITHUB_OUTPUT": str(output),
    }
    subprocess.run(["bash", "-eu", "-c", step["run"]], cwd=tmp_path, check=True, env=env)
    result = output.read_text().splitlines()
    assert f"version={version if recovered else sha}" in result
    assert ("ghcr.io/acme/orders:1.4.0" in result) is recovered


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
