# Igarapé landing page

The public landing page of the project, published with GitHub Pages at
**https://spassos.github.io/igarape/**. It is one hand-written HTML page with CSS: no build tool,
no JavaScript, no external requests. The site is separate from the CLI: nothing in `site/` is
packaged in the `igarape` wheel or sdist, rendered by Copier, or tested by the CLI test suite.

| Path | Role |
|---|---|
| `SITE_URL` | The site's public URL, in one place. `%SITE_URL%` in the pages is replaced with it at build time. |
| `public/` | Published pages, stylesheet, social image and local hero and font assets. |
| `scripts/build.sh` | Assembles `_site/`: `public/`, the icons from `docs/assets/` (copied, not duplicated) and the URL. |
| `scripts/og-image.html`, `scripts/make-og-image.cjs` | Source and renderer of the Open Graph card `public/og.png`. |
| `tests/test_site.py` | Fidelity and safety test (below). |
| [`../.github/workflows/pages.yml`](../.github/workflows/pages.yml) | Checks, builds and deploys the site. GitHub requires workflows in `.github/workflows/`. |

## Content rules

- **English only.** Keep product claims aligned with the root `README.md` and mark them with
  `data-claim`. The test strips Markdown from the README and fails when a claim is missing.
- Lists that come from the repository are checked against it: agents (`data-agent`) and Python
  versions (`data-python`) against `copier.yml`, skills (`data-skill`) against
  `template/.agents/skills/`, phases (`data-phase`) and CI checks (`data-check`) against the README,
  and the `uv` and `pip` quick-start commands must match the README.
- No `<script>`, inline styles, event handlers or third-party resources. Each page carries the CSP
  `default-src 'none'; img-src 'self'; font-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'`
  (Pages cannot set HTTP headers; `frame-ancestors` does not work in a meta tag, an accepted gap).
  Badges use text links. External links point to this repository, its PyPI project and its
  Scorecard page and use `rel="noopener"`.
- The stylesheet defines the forest and paper palettes. Main text, links and code use combinations
  that meet WCAG AA contrast. Retain visible keyboard focus and respect reduced-motion preferences.
- The river artwork is a generated illustration of an Amazon waterway. The two local WebP sizes
  keep the mobile download below 100 KB. The heading font is a local Bricolage Grotesque subset
  with its Open Font License in `public/assets/`.

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

`public/og.png` (1200×630) is committed. Regenerate it after changing `scripts/og-image.html`,
the hero image or the icon. The maintainer tool needs Node.js and
Playwright with Chromium.

```bash
npm install --global playwright && npx playwright install chromium   # once
NODE_PATH="$(npm root -g)" node site/scripts/make-og-image.cjs        # writes site/public/og.png
```

Look at the result before committing; the test checks its size, not its looks.
