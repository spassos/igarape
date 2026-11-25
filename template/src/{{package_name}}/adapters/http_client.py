"""Outbound HTTP: one configured client plus retry policy for transient failures.

Build gateways for third-party APIs on top of ``create_http_client`` and
decorate calls with ``retry_transient`` (see the ``integrate`` skill). Any URL that
comes from a caller or from stored data must pass ``ensure_public_https_url`` first (SSRF).
"""

import ipaddress
import socket
from urllib.parse import urlsplit

import httpx
import stamina

RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class UnsafeURLError(ValueError):
    """Raised when an outbound URL could reach something other than the public internet."""


def create_http_client(base_url: str, timeout_seconds: float = 5.0) -> httpx.AsyncClient:
    """Return an AsyncClient with explicit timeouts (never use library defaults)."""
    return httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(timeout_seconds))


def is_transient(exc: BaseException) -> bool:
    """Retry on network errors and on retryable HTTP status codes."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS
    return isinstance(exc, httpx.TransportError)


retry_transient = stamina.retry(on=is_transient, attempts=3, timeout=30.0)


def ensure_public_https_url(url: str) -> str:
    """Return ``url`` if it is https and every address its host resolves to is public.

    Every resolved address (IPv4 and IPv6, IPv4-mapped IPv6 unwrapped) must be global:
    private and unique-local (fc00::/7), loopback, link-local (169.254.0.0/16 cloud
    metadata, fe80::/10), reserved, multicast and unspecified addresses are rejected.

    Keep redirects off (httpx's default ``follow_redirects=False``) or re-validate each
    ``Location``, otherwise a public URL can bounce the request inside the network.
    DNS rebinding: the host is resolved again when the request is sent, so a hostile DNS
    server can answer differently in between. Where that matters, connect to the address
    checked here (sending the original ``Host``/SNI) or use an egress proxy with an allowlist.
    Resolution is blocking: call it through ``asyncio.to_thread`` from async code.
    """
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise UnsafeURLError("Only absolute https URLs are allowed")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as exc:
        raise UnsafeURLError(f"Cannot resolve host {parts.hostname!r}") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if _is_internal(address):
            raise UnsafeURLError(f"Host {parts.hostname!r} resolves to a non-public address")
    return url


def _is_internal(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
        or not address.is_global
    )
