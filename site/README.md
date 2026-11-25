# Igarapé landing page

The public landing page of the project, published with GitHub Pages at
**https://spassos.github.io/igarape/**. It is one hand-written HTML page with CSS: no build tool,
no JavaScript, no external requests. The site is separate from the CLI: nothing in `site/` is
packaged in the `igarape` wheel or sdist, rendered by Copier, or tested by the CLI test suite.

| Path | Role |
|---|---|
| `SITE_URL` | The site's public URL, in one place. `%SITE_URL%` in the pages is replaced with it at build time. |
| `public/` | Published files: `index.html`, `404.html`, `style.css`, `og.png`. |
| `scripts/build.sh` | Assembles `_site/`: `public/`, the icons from `docs/assets/` (copied, not duplicated) and the URL. |
| `scripts/og-image.html`, `scripts/make-og-image.cjs` | Source and renderer of the Open Graph card `public/og.png`. |
| `tests/test_site.py` | Fidelity and safety test (below). |
| [`../.github/workflows/pages.yml`](../.github/workflows/pages.yml) | Checks, builds and deploys the site. GitHub requires workflows in `.github/workflows/`. |

## Content rules

- **English only.** Every sentence in `<main>` is copied literally from the root `README.md` and
  marked `data-claim`. The test strips Markdown from the README and fails if a claim is not found
  in it, so a README change that drops a claim breaks the check, and the page cannot say more than
  the README (which in turn may only claim what the template and its tests deliver).
- Lists that come from the repository are checked against it: agents (`data-agent`) and Python
  versions (`data-python`) against `copier.yml`, skills (`data-skill`) against
  `template/.agents/skills/`, phases (`data-phase`) and CI checks (`data-check`) against the README,
  and the quick-start block (`data-quickstart`) must be identical to the README's.
- No `<script>`, inline styles, event handlers or third-party resources. Each page carries the CSP
  `default-src 'none'; img-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'`
  (Pages cannot set HTTP headers; `frame-ancestors` does not work in a meta tag, an accepted gap).
  Badges use text links. External links point to this repository, its PyPI project and its
  Scorecard page and use `rel="noopener"`.
- Colours: only these pairs (WCAG 2.x AA).

  | Text / background | Ratio | Use |
  |---|---|---|
  | white or foam `#B8F0E8` / forest `#0B3D2E` | 12.2 / 9.7 | Any text |
  | forest / white or paper `#F7FAF8` | 12.2 / 11.6 | Body text |
  | leaf `#1F6F50` / white | 6.1 | Links, text; white on leaf for buttons |
  | canoe `#F4A259` / forest (and forest / canoe) | 5.9 | Accents, primary button, focus ring on dark |
  | river `#2EC4B6` / forest (and forest / river) | 5.6 | Links and chips on dark |
  | bank `#1E8C7E` / white | 4.1 | Large text and borders only |
  | river or canoe / white, bank or leaf / forest | ≤ 3 | Decoration only, never text |

## Preview locally

```bash
site/scripts/build.sh                     # writes _site/ (git-ignored)
python -m http.server 8000 -d _site       # http://127.0.0.1:8000/
uv run pytest site/tests                  # the same check CI runs
```

`404.html` uses absolute links to the published site, because Pages serves it for any missing path.

## Deployment

[`pages.yml`](../.github/workflows/pages.yml) runs when a pull request or a push to `main` touches
`site/`, `README.md`, `copier.yml`, `template/.agents/skills/`, `docs/assets/`, the Python lock
files or the workflow itself, and on manual runs.

- `check` (every run): `uv run pytest site/tests`.
- `build` and `deploy` (only on `main`): `site/scripts/build.sh`, then
  `actions/upload-pages-artifact` and `actions/deploy-pages` into the `github-pages` environment.
  Only `deploy` gets `pages: write` and `id-token: write`; everything else is read-only.

Because the workflow is filtered by path, do not make its `check` a required status check (pull
requests that do not touch those paths would wait for it forever); a failing `check` is visible on
the pull request.

### One-time repository settings (maintainer)

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. **Settings → Environments → `github-pages`** (created by the first deploy, or create it first)
   → Deployment branches and tags: **Selected branches**, only `main`.
3. After the first deploy: repository **About → Website** = `https://spassos.github.io/igarape/`.

## Phase 2: custom domain `igarape.dev`

Only the apex domain is planned; `www` only redirects. Do the steps in order: a domain that points
at Pages before it is verified can be taken over by another account.

1. Buy `igarape.dev`, then **verify it first**: Profile **Settings → Pages → Add a domain**, create
   the TXT record `_github-pages-challenge-spassos.igarape.dev` it shows, check it with
   `dig _github-pages-challenge-spassos.igarape.dev TXT +short` and confirm in GitHub.
2. DNS at the apex: `A` 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 and
   `AAAA` 2606:50c0:8000::153, 2606:50c0:8001::153, 2606:50c0:8002::153, 2606:50c0:8003::153.
   Add `CNAME www → spassos.github.io` (no repository name, no wildcard records).
3. Repository **Settings → Pages → Custom domain**: `igarape.dev` (with GitHub Actions as the
   source a `CNAME` file is ignored; do not add one). Wait for the certificate, then tick
   **Enforce HTTPS**. `.dev` is HSTS-preloaded, so the site only opens once the certificate exists.
4. Change `site/SITE_URL` to `https://igarape.dev/` (the one-line switch: canonical, `og:url`,
   `og:image` and the 404 links follow), update the header comment of `pages.yml`, the URL at the top
   of this file and the repository Website field. The old `github.io/igarape/` address redirects.
5. Never disable Pages or remove the custom domain while the DNS records still point at GitHub.

## Regenerate the Open Graph image

`public/og.png` (1200×630) is committed. Regenerate it after changing `scripts/og-image.html` or the
icon. This is a one-off maintainer tool, not a repository dependency: it needs Node.js and
Playwright with Chromium.

```bash
npm install --global playwright && npx playwright install chromium   # once
NODE_PATH="$(npm root -g)" node site/scripts/make-og-image.cjs        # writes site/public/og.png
```

Look at the result before committing; the test checks its size, not its looks.
