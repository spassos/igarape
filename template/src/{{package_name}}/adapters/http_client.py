"""Outbound HTTP: one configured client plus retry policy for transient failures.

Build gateways for third-party APIs on top of ``create_http_client`` and
decorate calls with ``retry_transient`` (see the ``integrate`` skill).
"""

import httpx
import stamina

RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


def create_http_client(base_url: str, timeout_seconds: float = 5.0) -> httpx.AsyncClient:
    """Return an AsyncClient with explicit timeouts (never use library defaults)."""
    return httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(timeout_seconds))


def is_transient(exc: BaseException) -> bool:
    """Retry on network errors and on retryable HTTP status codes."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS
    return isinstance(exc, httpx.TransportError)


retry_transient = stamina.retry(on=is_transient, attempts=3, timeout=30.0)
