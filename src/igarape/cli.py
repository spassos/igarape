"""Igarapé CLI: generate a Python service ready for coding agents (`igarape new orders-api`)."""

import argparse
import importlib.metadata
import keyword
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from copier import run_copy
from copier.errors import CopierError

TEMPLATE = "https://github.com/spassos/igarape.git"
AGENTS = ("claude", "codex", "copilot", "opencode")
INITIAL_COMMIT = "chore: initial scaffold from igarape"
# How to open the project with each agent, for the final hint.
OPEN_WITH = {
    "claude": "run `claude`",
    "codex": "run `codex`",
    "copilot": "open it in VS Code with Copilot agent mode",
    "opencode": "run `opencode`",
}


def step[T](label: str, action: Callable[[], T]) -> T:
    """Run one generation step, reporting it on stderr so stdout keeps only the summary."""
    print(f"  {label} ...", end=" ", file=sys.stderr, flush=True)
    started = time.monotonic()
    try:
        result = action()
    except BaseException:
        print("failed", file=sys.stderr, flush=True)
        raise
    print(f"done ({time.monotonic() - started:.1f}s)", file=sys.stderr, flush=True)
    return result


def run_tool(command: list[str], cwd: Path, verbose: bool) -> None:
    """Run a helper tool quietly, showing its output only when it fails or with --verbose."""
    if verbose:
        subprocess.run(command, cwd=cwd, check=True)
        return
    result = subprocess.run(
        command,
        check=False,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    if result.returncode:
        print(f"\n{result.stdout.rstrip()}", file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)


def services(answers: dict[str, object]) -> list[str]:
    """Infrastructure the generated project starts in Docker."""
    chosen = ["PostgreSQL"] if answers["use_postgres"] else []
    chosen += ["Redis"] if answers["use_redis"] else []
    broker = {"kafka": "Kafka", "rabbit": "RabbitMQ"}.get(str(answers["event_broker"]))
    return chosen + ([broker] if broker else [])


def environment_notes(infra: list[str]) -> list[str]:
    """Explain how the generated project's tooling relates to the environment igarape runs in."""
    notes = []
    uv = shutil.which("uv")
    active = os.environ.get("VIRTUAL_ENV")
    if uv is None:
        notes.append(
            "uv is not on your PATH and the make targets need it: install it with "
            "`python -m pip install uv` or see https://docs.astral.sh/uv/."
        )
    elif active and Path(uv).absolute().is_relative_to(Path(active).absolute()):
        notes.append(
            f"uv comes from the active virtualenv ({active}): keep it active when you run make, "
            "or install uv for your user (`pipx install uv`)."
        )
    if active:
        notes.append(
            "The project has its own environment (.venv, created by `make dev`) and make targets use "
            "it even with this virtualenv active. Run tools with `uv run ...`, not bare python or pytest."
        )
    if infra and shutil.which("docker") is None:
        notes.append(
            f"Docker was not found. `make dev` starts {', '.join(infra)} with it; to use services "
            "you already run, set their URLs in .env and run `make dev DOCKER=0`."
        )
    return notes


def summary(path: Path, answers: dict[str, object], agents: list[str]) -> str:
    """Next steps for the generated project, shown on stdout."""
    infra = services(answers)
    try:
        where = os.path.relpath(path)
    except ValueError:
        where = str(path)
    if where.startswith(".."):
        where = str(path)
    if infra:
        dev = f"{', '.join(infra)} in Docker + API with reload at http://127.0.0.1:8000/docs"
    else:
        dev = "API with reload at http://127.0.0.1:8000/docs (in memory, no Docker)"
    lines = [
        f"Created {path}",
        "",
        "Next steps:",
        f"  cd {where}",
        f"  make dev         # {dev}",
        "  make token       # bearer token for the /v1 routes",
        "  make test-unit   # fast tests, no Docker",
        "  make help        # every command",
        "  (the first `make dev` installs dependencies into .venv and creates .env)",
        "",
        "Coding agent: "
        + "; ".join(OPEN_WITH[agent] for agent in agents)
        + " in that directory. Agents read AGENTS.md first.",
    ]
    lines += [f"Note: {note}" for note in environment_notes(infra)]
    return "\n".join(lines)


def initial_commit(project: Path) -> subprocess.CompletedProcess[str]:
    """Commit the generated files so the first agent change has a clean diff."""
    subprocess.run(["git", "add", "-A"], cwd=project, check=True)
    return subprocess.run(
        ["git", "commit", "-q", "-m", INITIAL_COMMIT],
        cwd=project,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )


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
    new.add_argument("--verbose", action="store_true", help="show the output of Copier and uv")
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
        profile = ", ".join(services(answers)) or "in memory"
        print(
            f"igarape: creating {path.name} ({profile}; agents: {', '.join(answers['agents'])})",
            file=sys.stderr,
        )
        with tempfile.TemporaryDirectory(dir=path.parent) as temp:
            project = Path(temp) / "project"
            with warnings.catch_warnings():
                # Copier warns about uncommitted changes in a local template checkout; --verbose shows it.
                if not args.verbose:
                    warnings.simplefilter("ignore")
                step(
                    f"Rendering the template from {source if args.template else 'GitHub'}",
                    lambda: run_copy(
                        source,
                        project,
                        vcs_ref=revision,
                        data=answers,
                        defaults=True,
                        unsafe=False,
                        quiet=not args.verbose,
                    ),
                )
            uv = [sys.executable, "-P", "-m", "uv", "lock"]
            step("Locking dependencies (uv lock)", lambda: run_tool(uv, project, args.verbose))
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
            commit = step("Initial Git commit", lambda: initial_commit(project))
            project.rename(path)
    except (CopierError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"igarape: {exc}", file=sys.stderr)
        return 1

    if commit.returncode:
        print(
            f"igarape: initial commit skipped (git exited with status {commit.returncode}).", file=sys.stderr
        )
        detail = commit.stdout.rstrip() or "Git did not report any details."
        print(detail, file=sys.stderr)
        print(
            "igarape: fix the Git error, then run "
            f'`git add -A && git commit -m "{INITIAL_COMMIT}"` in the generated directory.',
            file=sys.stderr,
        )

    print(summary(path, answers, sorted(set(args.agent or ["codex"]))))
    return 0
