"""The CLI's own release flow: release-please versions, tags and publishes in one workflow run."""

import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_pypi_description_uses_hosted_static_images() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    readme = pyproject["project"]["readme"]
    assert f"/{readme}" in pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    description = (ROOT / readme).read_text()
    assert "```mermaid" not in description
    images = re.findall(r"!\[[^\n]*?\]\(([^)]+)\)", description)
    base = "https://raw.githubusercontent.com/spassos/igarape/main/"
    assert set(images) == {
        f"{base}docs/assets/logo.svg",
        f"{base}docs/assets/scaffolding.png",
        f"{base}docs/assets/agentic-sdlc.png",
    }
    assert all((ROOT / image.removeprefix(base)).is_file() for image in images)


def test_release_versions_pyproject_lockfile_and_changelog() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    (locked,) = [package for package in lock["package"] if package["name"] == "igarape"]
    assert json.loads((ROOT / ".release-please-manifest.json").read_text()) == {".": version}
    assert locked["version"] == version
    (config,) = json.loads((ROOT / "release-please-config.json").read_text())["packages"].values()
    assert config["release-type"] == "python" and config["package-name"] == "igarape"
    assert config["changelog-path"] == "CHANGELOG.md" and config["include-component-in-tag"] is False
    assert config["extra-files"] == [
        {"type": "toml", "path": "uv.lock", "jsonpath": "$.package[?(@.name.value=='igarape')].version"}
    ]
    # Keep a Changelog section names; release-please appends each release to CHANGELOG.md.
    visible = {section["section"] for section in config["changelog-sections"] if not section.get("hidden")}
    assert visible <= {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}
    assert f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text()


def test_release_publishes_to_pypi_in_the_same_run() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/publish-pypi.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["on"]["push"]["branches"] == ["main"] and "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"] == {}
    jobs = workflow["jobs"]
    release, build, publish = jobs["release"], jobs["build"], jobs["publish"]
    (step,) = release["steps"]
    assert step["uses"].startswith("googleapis/release-please-action@")
    assert release["permissions"] == {"contents": "write", "issues": "write", "pull-requests": "write"}
    assert release["outputs"]["created"] == "${{ steps.release-please.outputs.release_created }}"
    # A release made with GITHUB_TOKEN triggers no other workflow, so build and publish follow it here.
    assert build["needs"] == "release" and build["permissions"] == {"contents": "read"}
    assert "needs.release.outputs.created == 'true'" in build["if"]
    assert "github.event_name == 'workflow_dispatch'" in build["if"]
    assert publish["needs"] == "build" and publish["permissions"] == {"id-token": "write"}
    assert publish["environment"]["name"] == "pypi"
    assert "needs.build.result == 'success'" in publish["if"]
