"""Refresh the digests that pin the generated Dockerfile's base images, per Python version.

`template/Dockerfile.jinja` has one literal `FROM <image>:<tag>@sha256:<digest>` per supported
Python version (so OpenSSF Scorecard sees them pinned); generated projects keep them current with
Dependabot. Run before a release:

    uv run python scripts/refresh_image_digests.py          # rewrite the template in place
    uv run python scripts/refresh_image_digests.py --check  # exit 1 if a digest is stale
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DOCKERFILE = Path(__file__).parents[1] / "template" / "Dockerfile.jinja"
PYTHON_VERSIONS = ("3.12", "3.13", "3.14")
ACCEPT = "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json"
IMAGES = {
    # FROM prefix (per Python version) -> (registry, repository, tag, token URL)
    "ghcr.io/astral-sh/uv:python{v}-trixie-slim": (
        "ghcr.io",
        "astral-sh/uv",
        "python{v}-trixie-slim",
        "https://ghcr.io/token?scope=repository:astral-sh/uv:pull",
    ),
    "python:{v}-slim-trixie": (
        "registry-1.docker.io",
        "library/python",
        "{v}-slim-trixie",
        "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull",
    ),
}


def _token(url: str) -> str:
    with urllib.request.urlopen(url, timeout=20) as response:  # fixed https hosts
        return str(json.load(response)["token"])


def digest(registry: str, repository: str, tag: str, token_url: str) -> str:
    """Return the hex of the multi-arch index digest of ``repository:tag`` (retries on 429)."""
    request = urllib.request.Request(
        f"https://{registry}/v2/{repository}/manifests/{tag}",
        headers={"Authorization": f"Bearer {_token(token_url)}", "Accept": ACCEPT},
        method="HEAD",
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return str(response.headers["Docker-Content-Digest"]).removeprefix("sha256:")
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("unreachable")


def main() -> int:
    """Rewrite (or, with --check, verify) the pinned digests in the template Dockerfile."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true", help="only report stale digests")
    args = parser.parse_args()
    text = DOCKERFILE.read_text()
    stale = []
    for prefix_fmt, (registry, repository, tag_fmt, token_url) in IMAGES.items():
        for version in PYTHON_VERSIONS:
            prefix = prefix_fmt.format(v=version)
            current = digest(registry, repository, tag_fmt.format(v=version), token_url)
            pattern = re.compile(rf"(FROM {re.escape(prefix)}@sha256:)([0-9a-f]{{64}})")
            match = pattern.search(text)
            if match is None:
                sys.stderr.write(f"missing FROM {prefix}@sha256:... in {DOCKERFILE}\n")
                return 1
            if match[2] != current:
                stale.append(prefix)
                text = pattern.sub(rf"\g<1>{current}", text)
    if stale and not args.check:
        DOCKERFILE.write_text(text)
    sys.stdout.write(
        "".join(f"{'stale' if args.check else 'updated'}: {p}\n" for p in stale) or "up to date\n"
    )
    return 1 if stale and args.check else 0


if __name__ == "__main__":
    sys.exit(main())
