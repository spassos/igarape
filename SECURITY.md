# Security policy

## Supported versions

igarape is pre-1.0. Security fixes land on `main` only; once releases are published on PyPI, only
the latest release is supported. Generated projects receive template fixes through
`uvx copier update`.

| Version | Supported |
|---|---|
| `main` | Yes |
| `0.x` releases | Latest only |

## Reporting a vulnerability

Do not open a public issue. Report it privately through GitHub Security Advisories:
**Security → Report a vulnerability** on this repository
(<https://github.com/spassos/igarape/security/advisories/new>).

Include the affected revision (commit SHA or version), the CLI options or template files involved,
steps to reproduce and the impact you expect. The fix is coordinated in the private advisory and
disclosed together with the patched revision.

## Scope

| In scope | Out of scope |
|---|---|
| The `igarape` CLI (`src/igarape/`), e.g. input validation of `--mcp` URLs or destination handling | Vulnerabilities in a service after its team changed the generated code |
| The template (`template/`, `includes/`, `copier.yml`): insecure defaults in generated code, Dockerfile, workflows or agent permissions | Third-party dependencies and actions themselves (report upstream; we will update the pin) |
| This repository's workflows and release process | Deployment platforms and infrastructure that generated services run on |

A vulnerability in generated code is in scope when a freshly generated project reproduces it. For
a project generated earlier, check whether `copier update` already fixes it. Each generated
service ships its own `SECURITY.md` for issues in that service.

## Supply-chain controls of this repository

- Every GitHub Action is pinned by full commit SHA; workflows start from `permissions: {}` and
  check out without persisted credentials.
- zizmor scans this repository's workflows and the workflows of a project generated with every
  agent on each pull request and push to `main`.
- Generated images are built and scanned with Trivy in CI (fixable HIGH/CRITICAL fail the build).
- `uv.lock` pins the dependency tree; CI installs with `uv sync --locked`.
- Dependabot proposes weekly, grouped updates for GitHub Actions and Python dependencies.
- OpenSSF Scorecard analyses the repository weekly and on every push to `main`.
- The landing page (`site/`) runs no scripts and loads no third-party resources (strict CSP); only
  the deploy job of `pages.yml`, from `main`, can write to GitHub Pages.
- PyPI publishing runs only from `main`, when release-please creates a release (or by manual
  dispatch), uses trusted publishing (OIDC, no stored token) and publishes the exact artifacts that
  first generated and tested a service.
