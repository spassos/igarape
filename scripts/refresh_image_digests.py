"""Print the current digests of the generated Dockerfile's base images, per Python version.

The generated `Dockerfile` pins `FROM <image>:<tag>@sha256:<digest>` (OpenSSF Scorecard
"Pinned-Dependencies"); generated projects keep them fresh with Dependabot. Run this before a
release to refresh the template's starting point, then paste the output into
`includes/image_digests.jinja`:

    uv run python scripts/refresh_image_digests.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

PYTHON_VERSIONS = ("3.12", "3.13", "3.14")
ACCEPT = "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json"


def _get(url: str, headers: dict[str, str] | None = None, method: str = "GET") -> urllib.request.Request:
    return urllib.request.Request(url, headers=headers or {}, method=method)


def _token(url: str) -> str:
    with urllib.request.urlopen(_get(url), timeout=20) as response:
        return str(json.load(response)["token"])


def digest(registry: str, repository: str, tag: str, token_url: str) -> str:
    """Return the multi-arch index digest of ``repository:tag`` (retries on rate limits)."""
    token = _token(token_url)
    request = _get(
        f"https://{registry}/v2/{repository}/manifests/{tag}",
        {"Authorization": f"Bearer {token}", "Accept": ACCEPT},
        method="HEAD",
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return str(response.headers["Docker-Content-Digest"])
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("unreachable")


def main() -> int:
    """Print the Jinja mapping for includes/image_digests.jinja."""
    lines = ["{%- set image_digests = {"]
    for version in PYTHON_VERSIONS:
        uv = digest(
            "ghcr.io",
            "astral-sh/uv",
            f"python{version}-trixie-slim",
            "https://ghcr.io/token?scope=repository:astral-sh/uv:pull",
        )
        python = digest(
            "registry-1.docker.io",
            "library/python",
            f"{version}-slim-trixie",
            "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull",
        )
        lines.append(f'  "{version}": {{"uv": "{uv}", "python": "{python}"}},')
    lines.append("} %}")
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
