"""Every GitHub Action is pinned to one full commit SHA across the generated workflows.

Dependabot updates `template/.github/workflows/*.yml`, but not workflows whose file name is
conditional Jinja (`{% if ... %}name.yml{% endif %}`). This guard fails when a bump leaves one of
them behind, so generated projects never mix two versions of the same action.
"""

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parents[1]
USES = re.compile(r"uses:\s*(?P<action>[\w.-]+/[\w./-]+)@(?P<ref>\S+)(?:\s*#\s*(?P<version>\S+))?")


def _pins(directory: Path) -> dict[str, set[tuple[str, str | None]]]:
    pins: dict[str, set[tuple[str, str | None]]] = defaultdict(set)
    for workflow in directory.iterdir():
        for match in USES.finditer(workflow.read_text()):
            pins[match["action"]].add((match["ref"], match["version"]))
    return pins


def test_template_workflows_pin_each_action_to_one_sha() -> None:
    pins = _pins(ROOT / "template" / ".github" / "workflows")
    assert pins, "no actions found"
    for action, refs in pins.items():
        assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref, _ in refs), (action, refs)
        assert len({ref for ref, _ in refs}) == 1, f"{action} is pinned to several SHAs: {sorted(refs)}"
