"""Landing page (site/): fidelity to README.md and the repository, and a safe, accessible page.

Run with `uv run pytest site/tests` (the CLI suite in tests/ does not collect it). The Pages
workflow runs it on every pull request that touches the site, README.md or the facts it checks.
"""

import html
import re
import struct
import subprocess
import tomllib
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[2]
SITE = ROOT / "site"
PUBLIC = SITE / "public"
README = ROOT / "README.md"
SITE_URL = (SITE / "SITE_URL").read_text().strip()
PLACEHOLDER = "%SITE_URL%"
CSP = "default-src 'none'; img-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'"
# External links the page may point to (prefix followed by "/", "?", "#" or the end).
ALLOWED_EXTERNAL = (
    "https://github.com/spassos/igarape",
    "https://pypi.org/project/igarape",
    "https://scorecard.dev/viewer/?uri=github.com/spassos/igarape",
)
NUMBER_WORDS = {4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    def __init__(self, tag: str, attrs: dict[str, str | None], parent: "Node | None") -> None:
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children: list[Node | str] = []

    def text(self) -> str:
        return "".join(child if isinstance(child, str) else child.text() for child in self.children)

    def iter(self) -> Iterator["Node"]:
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.iter()

    def ancestors(self) -> Iterator["Node"]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent


class TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, None)
        self.current = self.root
        self.comments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, dict(attrs), self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.current.children.append(Node(tag, dict(attrs), self.current))

    def handle_endtag(self, tag: str) -> None:
        node = self.current
        while node is not self.root and node.tag != tag:
            node = node.parent  # type: ignore[assignment]
        assert node is not self.root, f"unexpected </{tag}>"
        self.current = node.parent  # type: ignore[assignment]

    def handle_data(self, data: str) -> None:
        self.current.children.append(data)

    def handle_comment(self, data: str) -> None:
        self.comments.append(data)


def parse(path: Path) -> Node:
    builder = TreeBuilder()
    builder.feed(path.read_text())
    builder.close()
    assert builder.current is builder.root, f"{path.name}: unclosed <{builder.current.tag}>"
    return builder.root


def squash(text: str) -> str:
    return " ".join(text.split())


def normalize_markdown(text: str) -> str:
    """README as plain text: no HTML tags, comments, link targets, emphasis, code ticks or quotes."""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    text = text.replace("**", "")
    text = re.sub(r"(?<![\w*])\*([^*`\n]+)\*(?![\w*])", r"\1", text)
    text = text.replace("`", "")
    return squash(html.unescape(text))


def readme_section(title: str) -> str:
    match = re.search(
        rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", README.read_text(), flags=re.MULTILINE | re.DOTALL
    )
    assert match, f"README has no '## {title}' section"
    return match[1]


def table_first_column(markdown: str) -> list[str]:
    rows = [line for line in markdown.splitlines() if line.startswith("|")]
    return [normalize_markdown(row.split("|")[1]) for row in rows[2:]]


def by_attr(tree: Node, attr: str) -> list[Node]:
    return [node for node in tree.iter() if attr in node.attrs]


def meta(tree: Node, key: str) -> str | None:
    for node in tree.iter():
        if node.tag == "meta" and key in (node.attrs.get("name"), node.attrs.get("property")):
            return node.attrs.get("content")
    return None


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site") / "_site"
    subprocess.run(["bash", str(SITE / "scripts" / "build.sh"), str(out)], check=True, capture_output=True)
    return out


@pytest.fixture(scope="module")
def page() -> Node:
    return parse(PUBLIC / "index.html")


@pytest.fixture(scope="module")
def copier() -> dict:
    return yaml.safe_load((ROOT / "copier.yml").read_text())


# Fidelity: what the page says comes from README.md and the repository.


def test_every_claim_is_literal_readme_text(page: Node) -> None:
    readme = normalize_markdown(README.read_text())
    claims = by_attr(page, "data-claim")
    assert len(claims) > 40
    missing = [squash(node.text()) for node in claims if squash(node.text()) not in readme]
    assert not missing, f"claims not found literally in README.md: {missing}"


def test_main_text_is_made_of_claims(page: Node) -> None:
    main = next(node for node in page.iter() if node.tag == "main")
    for node in main.iter():
        if node.tag not in {"p", "li"} or any(a.tag == "nav" for a in node.ancestors()):
            continue
        has_claim = any("data-claim" in n.attrs for n in node.iter())
        assert has_claim, f"<{node.tag}> without data-claim in <main>: {squash(node.text())!r}"


def test_description_is_a_readme_claim(page: Node) -> None:
    readme = normalize_markdown(README.read_text())
    for key in ("description", "og:description", "twitter:description"):
        assert meta(page, key) in readme, key


def test_agents_match_copier_choices(page: Node, copier: dict) -> None:
    listed = sorted(squash(node.text()) for node in by_attr(page, "data-agent"))
    assert listed == sorted(copier["agents"]["choices"])


def test_python_versions_match_copier_choices(page: Node, copier: dict) -> None:
    (node,) = by_attr(page, "data-python")
    assert re.findall(r"\d+\.\d+", node.text()) == copier["python_version"]["choices"]


def test_skills_match_the_template(page: Node) -> None:
    skills = sorted(p.name for p in (ROOT / "template" / ".agents" / "skills").iterdir() if p.is_dir())
    listed = [node.text() for node in by_attr(page, "data-skill")]
    assert sorted(listed) == skills
    (holder,) = {
        next(a for a in node.ancestors() if "data-claim" in a.attrs) for node in by_attr(page, "data-skill")
    }
    assert f"{NUMBER_WORDS[len(skills)]} skills" in holder.text()


def test_phases_match_the_readme(page: Node) -> None:
    match = re.search(r"Six phases \(([^)]*)\)", README.read_text())
    assert match, "README no longer lists the six phases"
    assert [squash(node.text()) for node in by_attr(page, "data-phase")] == match[1].split(" → ")


def test_trust_checks_match_the_readme_table(page: Node) -> None:
    expected = table_first_column(readme_section("Why you can trust it"))
    assert [squash(node.text()) for node in by_attr(page, "data-check")] == expected


def test_quick_start_is_identical_to_the_readme(page: Node) -> None:
    match = re.search(r"```bash\n(.*?)```", readme_section("Quick start"), flags=re.DOTALL)
    assert match, "README quick start has no bash block"
    (node,) = by_attr(page, "data-quickstart")
    assert node.text() == match[1].rstrip("\n")


# Safety: no scripts, no third-party requests, nothing the CSP would have to allow.


@pytest.mark.parametrize("name", ["index.html", "404.html"])
def test_page_is_static_and_self_contained(built: Path, name: str) -> None:
    tree = parse(built / name)
    tags = {node.tag for node in tree.iter()}
    assert not tags & {"script", "iframe", "object", "embed", "form", "base", "style"}
    for node in tree.iter():
        assert "style" not in node.attrs, f"inline style on <{node.tag}>"
        assert not any(attr.startswith("on") for attr in node.attrs), f"event handler on <{node.tag}>"
        for attr in ("href", "src", "srcset", "action", "poster"):
            value = node.attrs.get(attr)
            if value is None:
                continue
            assert not value.startswith(("http:", "//", "javascript:", "data:")), value
            if value.startswith(SITE_URL):
                value = value[len(SITE_URL) :] or "index.html"
            elif value.startswith("https://"):
                assert node.tag == "a", f"external {attr} on <{node.tag}>: {value}"
                assert any(re.match(rf"{re.escape(p)}(?:[/?#]|$)", value) for p in ALLOWED_EXTERNAL), value
                assert "noopener" in (node.attrs.get("rel") or ""), value
                continue
            target = value.split("#")[0].split("?")[0]
            if target:
                assert (built / target).is_file(), f"{name}: missing local file {value}"
            if value.startswith("#"):
                assert any(n.attrs.get("id") == value[1:] for n in tree.iter()), f"{name}: no anchor {value}"


@pytest.mark.parametrize("name", ["index.html", "404.html"])
def test_page_has_strict_csp_and_referrer_policy(name: str) -> None:
    tree = parse(PUBLIC / name)
    csp = [
        n for n in tree.iter() if n.tag == "meta" and n.attrs.get("http-equiv") == "Content-Security-Policy"
    ]
    assert [n.attrs["content"] for n in csp] == [CSP]
    assert meta(tree, "referrer") == "strict-origin-when-cross-origin"


@pytest.mark.parametrize("name", ["index.html", "404.html"])
def test_page_is_accessible(name: str) -> None:
    tree = parse(PUBLIC / name)
    html_tag = next(node for node in tree.iter() if node.tag == "html")
    assert html_tag.attrs.get("lang") == "en"
    assert len([node for node in tree.iter() if node.tag == "h1"]) == 1
    assert all("alt" in node.attrs for node in tree.iter() if node.tag == "img")
    assert len([node for node in tree.iter() if node.tag == "main"]) == 1
    assert any(node.tag == "title" and node.text().strip() for node in tree.iter())


def test_index_has_skip_link_and_landmarks(page: Node) -> None:
    tags = [node.tag for node in page.iter()]
    assert {"header", "nav", "main", "footer"} <= set(tags)
    first_link = next(node for node in page.iter() if node.tag == "a")
    assert first_link.attrs.get("href") == "#main"


# Metadata and the site URL.


def test_site_url_lives_in_one_place() -> None:
    assert re.fullmatch(r"https://[a-z0-9.-]+/([a-z0-9-]+/)?", SITE_URL), SITE_URL
    for path in PUBLIC.rglob("*"):
        if path.suffix in {".html", ".css"}:
            text = path.read_text()
            assert "github.io" not in text and "igarape.dev" not in text, f"{path.name}: use {PLACEHOLDER}"


def test_index_has_social_metadata(built: Path) -> None:
    tree = parse(built / "index.html")
    canonical = [
        n.attrs.get("href") for n in tree.iter() if n.tag == "link" and n.attrs.get("rel") == "canonical"
    ]
    assert canonical == [SITE_URL]
    assert meta(tree, "og:url") == SITE_URL
    assert meta(tree, "og:image") == meta(tree, "twitter:image") == f"{SITE_URL}og.png"
    assert (meta(tree, "og:image:width"), meta(tree, "og:image:height")) == ("1200", "630")
    assert meta(tree, "twitter:card") == "summary_large_image"
    for key in (
        "og:type",
        "og:title",
        "og:description",
        "og:image:alt",
        "twitter:title",
        "twitter:image:alt",
    ):
        assert meta(tree, key), key
    assert PLACEHOLDER not in (built / "index.html").read_text() + (built / "404.html").read_text()


def test_og_image_is_1200_by_630_png() -> None:
    header = (PUBLIC / "og.png").read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24]) == (1200, 630)


def test_page_weight_is_small(built: Path) -> None:
    assert (built / "index.html").stat().st_size + (built / "style.css").stat().st_size < 50_000


# The site stays out of the CLI package and of generated projects.


def test_site_is_not_packaged_or_rendered(copier: dict) -> None:
    build = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["hatch"]["build"]["targets"]
    assert not any("site" in entry for entry in build["sdist"]["include"] + build["wheel"]["packages"])
    assert copier["_subdirectory"] == "template"
