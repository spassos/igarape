"""The generated Dockerfile pins its base images by digest for every supported Python version."""

import re
from pathlib import Path

import pytest
from copier import run_copy

ROOT = Path(__file__).parents[1]
PINNED_FROM = re.compile(r"^FROM (?P<image>\S+):(?P<tag>\S+)@sha256:[0-9a-f]{64} AS \w+$", re.MULTILINE)


@pytest.mark.parametrize("python_version", ["3.12", "3.13", "3.14"])
def test_base_images_are_pinned_by_digest(tmp_path: Path, python_version: str) -> None:
    project = tmp_path / "svc"
    run_copy(
        str(ROOT),
        project,
        data={"project_name": "Svc", "python_version": python_version},
        defaults=True,
        unsafe=False,
        vcs_ref="HEAD",
        quiet=True,
    )
    dockerfile = (project / "Dockerfile").read_text()
    froms = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]
    pinned = PINNED_FROM.findall(dockerfile)
    assert len(froms) == len(pinned) == 2, froms
    assert {image for image, _ in pinned} == {"ghcr.io/astral-sh/uv", "python"}
    assert all(python_version in tag for _, tag in pinned)
