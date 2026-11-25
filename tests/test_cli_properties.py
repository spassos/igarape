"""Property-based tests (Hypothesis) for the CLI's external input: `--mcp NAME=URL`.

Accepted values end up in generated TOML/JSON config files, so the parser must only accept
credential-free HTTPS endpoints and nothing it accepts may break out of the rendered config.
"""

import argparse
import json
import tomllib
from urllib.parse import urlsplit

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from igarape.cli import mcp_server

FUZZ = settings(max_examples=300, derandomize=True, database=None, deadline=None)

names = st.from_regex(r"[A-Za-z0-9_-]{1,40}", fullmatch=True)
labels = st.from_regex(r"[a-z][a-z0-9-]{0,20}[a-z0-9]", fullmatch=True)
hosts = st.lists(labels, min_size=2, max_size=4).map(".".join)
paths = st.from_regex(r"(/[A-Za-z0-9._~-]{1,12}){0,4}", fullmatch=True)
ports = st.one_of(st.just(""), st.integers(1, 65535).map(lambda port: f":{port}"))
https_urls = st.builds(lambda host, port, path: f"https://{host}{port}{path}", hosts, ports, paths)


@FUZZ
@given(name=names, url=https_urls)
def test_accepts_credential_free_https_endpoints_unchanged(name: str, url: str) -> None:
    assert mcp_server(f"{name}={url}") == (name, url)


@FUZZ
@given(name=names, url=https_urls)
def test_accepted_values_cannot_escape_the_rendered_config(name: str, url: str) -> None:
    parsed_name, parsed_url = mcp_server(f"{name}={url}")
    # Same escaping as the templates (`to_json`) for .codex/config.toml and the JSON configs.
    toml = f"[mcp_servers.{json.dumps(parsed_name)}]\nurl = {json.dumps(parsed_url)}\n"
    assert tomllib.loads(toml) == {"mcp_servers": {parsed_name: {"url": parsed_url}}}
    as_json = json.dumps({"mcpServers": {parsed_name: {"type": "http", "url": parsed_url}}})
    assert json.loads(as_json)["mcpServers"][parsed_name]["url"] == parsed_url


@FUZZ
@given(name=names, scheme=st.sampled_from(["http", "ftp", "file", "javascript", "HTTPS ", ""]), host=hosts)
def test_rejects_non_https_schemes(name: str, scheme: str, host: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        mcp_server(f"{name}={scheme}://{host}/mcp")


@FUZZ
@given(name=names, url=https_urls, extra=st.sampled_from(["user@", "user:secret@"]))
def test_rejects_credentials_in_the_url(name: str, url: str, extra: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        mcp_server(f"{name}={url.replace('https://', 'https://' + extra, 1)}")


@FUZZ
@given(name=names, url=https_urls, suffix=st.sampled_from(["?token=x", "#frag", "?", "#"]))
def test_rejects_query_and_fragment(name: str, url: str, suffix: str) -> None:
    candidate = url + ("/" if not urlsplit(url).path else "") + suffix
    with pytest.raises(argparse.ArgumentTypeError):
        mcp_server(f"{name}={candidate}")


@FUZZ
@given(
    name=st.text(min_size=1, max_size=20).filter(
        lambda n: not all(c.isascii() and (c.isalnum() or c in "-_") for c in n) and "=" not in n
    ),
    url=https_urls,
)
def test_rejects_names_outside_the_safe_alphabet(name: str, url: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        mcp_server(f"{name}={url}")


@FUZZ
@given(name=names, url=https_urls, junk=st.sampled_from([" ", "\t", "\n", "\x00", "\x1b", "\u200b"]))
def test_rejects_whitespace_and_control_characters(name: str, url: str, junk: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        mcp_server(f"{name}={url}{junk}")
