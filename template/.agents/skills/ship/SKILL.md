---
name: ship
description: Deliver a reviewed change through the repository's enabled workflows — branch, Conventional Commit PR, CI gates, merge, release-please, CD to staging and production with post-deploy verification and rollback. Use for "ship", "deploy", "release", "abrir PR", "subir para produção", "entregar".
---

# Ship a reviewed change

1. Use `fix/<slug>` for a local fix or `feat/NNN-<slug>` for a planned feature. Run `make check` locally.
2. Open a PR with `.github/pull_request_template.md` filled in; title in Conventional Commits
   (`feat(items): ...`) — it becomes the squash commit and drives the version bump.
3. CI must be green: quality (ruff, mypy, import-linter), tests + coverage, security (pip-audit,
   gitleaks, zizmor), image build + Trivy, PR title. Optional agent review comment
   (`codex-review.yml` or `claude-review.yml`), when enabled. Address findings; never re-run hoping for a different result.
4. Human approval → squash merge to `main`.
5. Watch the main CI run. With CD disabled, a merged change with green CI completes delivery.
6. When the repository variable `ENABLE_CD` is `true`, follow the image publication, staging and
   production jobs. Check each deployment's smoke test for the expected commit and readiness
   before reporting it live. Report any skipped, pending or failed deployment accurately.
7. When `ENABLE_RELEASES` is `true`, release-please maintains the release PR and changelog.
   Check product metrics when defined and record the actual delivery status for planned work.
