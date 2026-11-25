"""Post-deploy verification: the expected version is live and ready.

Used by CD after each deploy (``make smoke url=... version=...``). Exits non-zero
so the pipeline fails (and rollback kicks in) when production is not healthy.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

HTTP_OK = 200


def fetch(url: str) -> tuple[int, dict[str, Any]]:
    """GET a JSON endpoint, returning status and body (even on HTTP errors)."""
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Unsupported URL: {url}")
    try:
        with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 - scheme checked
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def verify(base_url: str, version: str, attempts: int, delay: float) -> bool:
    """Poll until /health/live reports ``version`` and /health/ready is 200."""
    base_url = base_url.rstrip("/")
    for attempt in range(1, attempts + 1):
        try:
            live_status, live = fetch(f"{base_url}/health/live")
            ready_status, ready = fetch(f"{base_url}/health/ready")
        except (OSError, ValueError) as error:
            sys.stderr.write(f"[{attempt}/{attempts}] unreachable: {error}\n")
        else:
            if (
                live_status == HTTP_OK
                and live.get("version") == version
                and ready_status == HTTP_OK
                and ready.get("status") == "ok"
            ):
                sys.stdout.write(f"OK: version {version} is live and ready\n")
                return True
            sys.stderr.write(
                f"[{attempt}/{attempts}] live={live.get('version')} ready={ready_status} "
                f"checks={ready.get('checks')}\n"
            )
        time.sleep(delay)
    return False


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--delay", type=float, default=10.0)
    args = parser.parse_args()
    return 0 if verify(args.url, args.version, args.attempts, args.delay) else 1


if __name__ == "__main__":
    sys.exit(main())
