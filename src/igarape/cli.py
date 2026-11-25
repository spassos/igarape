"""Igarapé CLI: generate a Python service ready for coding agents (`igarape new orders-api`)."""

import argparse
import importlib.metadata
import keyword
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from copier import run_copy
from copier.errors import CopierError

TEMPLATE = "https://github.com/spassos/igarape.git"
AGENTS = ("claude", "codex", "copilot", "opencode")


def mcp_server(value: str) -> tuple[str, str]:
    name, _, url = value.partition("=")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise argparse.ArgumentTypeError(
            "use NAME=HTTPS_URL with a server name containing letters, digits, - or _"
        )
    try:
        endpoint = urlsplit(url)
        valid = endpoint.scheme == "https" and endpoint.hostname and endpoint.username is None
        # Only endpoints suitable for committing to project configuration are supported.
        valid = (
            valid
            # An empty "?" or "#" parses as no query/fragment, so check the raw text.
            and "?" not in url
            and "#" not in url
            and not any(c.isspace() or not c.isprintable() for c in url)
        )
        _ = endpoint.port
    except ValueError:
        valid = False
    if not valid:
        raise argparse.ArgumentTypeError("use an HTTPS endpoint URL without credentials, query or fragment")
    return name, url


def build_parser() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    parser = argparse.ArgumentParser(prog="igarape", description=__doc__)
    parser.add_argument(
        "--version", action="version", version=f"igarape {importlib.metadata.version('igarape')}"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    new = commands.add_parser("new", help="generate a new service repository", description=__doc__)
    new.add_argument("destination", type=Path, help="new directory, e.g. orders-api")
    new.add_argument(
        "--agent",
        action="append",
        choices=AGENTS,
        metavar="AGENT",
        help=f"coding agent to configure (repeatable; choices: {', '.join(AGENTS)}; default: codex)",
    )
    new.add_argument("--name", help="project display name (default: directory name)")
    new.add_argument("--description", help="one-line service description")
    new.add_argument("--author", help="owning person or team")
    new.add_argument("--python", choices=["3.12", "3.13", "3.14"], help="service Python version")
    new.add_argument("--postgres", action="store_true", help="include PostgreSQL and migrations")
    new.add_argument("--redis", action="store_true", help="include Redis")
    new.add_argument("--broker", choices=["none", "kafka", "rabbit"], default="none")
    new.add_argument(
        "--mcp",
        action="append",
        type=mcp_server,
        default=[],
        metavar="NAME=HTTPS_URL",
        help="register a project MCP server (repeatable)",
    )
    new.add_argument("--template", type=Path, help="use a local template checkout")
    new.add_argument(
        "--ref", help="template Git revision (default: main upstream, HEAD for a local checkout)"
    )
    return parser, new


def main() -> int:
    root, parser = build_parser()
    args = root.parse_args()
    path = args.destination.expanduser().absolute()
    slug = path.name.lower().replace("_", "-").replace(" ", "-")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", slug) or keyword.iskeyword(slug.replace("-", "_")):
        parser.error("choose a directory name that can be used as a Python package, e.g. orders-api")
    servers = dict(args.mcp)
    if len(servers) != len(args.mcp):
        parser.error("each MCP server must have a unique name")
    answers = {
        "project_name": args.name if args.name is not None else path.name,
        "project_slug": slug,
        "use_postgres": args.postgres,
        "use_redis": args.redis,
        "event_broker": args.broker,
        "mcp_servers": servers,
        "agents": sorted(set(args.agent or ["codex"])),
    }
    for key, value in (
        ("description", args.description),
        ("author_name", args.author),
        ("python_version", args.python),
    ):
        if value is not None:
            answers[key] = value

    source = str(args.template.expanduser().resolve()) if args.template else TEMPLATE
    revision = args.ref or ("HEAD" if args.template else "main")
    try:
        if path.exists() or path.is_symlink():
            parser.error("destination already exists; choose a new directory")
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=path.parent) as temp:
            project = Path(temp) / "project"
            run_copy(source, project, vcs_ref=revision, data=answers, defaults=True, unsafe=False, quiet=True)
            subprocess.run(["uv", "lock"], cwd=project, check=True)
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
            project.rename(path)
    except (CopierError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"igarape: {exc}", file=sys.stderr)
        return 1

    print(f"Created {path}. Open it with your coding agent; README.md has the startup and test commands.")
    return 0
