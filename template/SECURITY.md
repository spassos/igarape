# Segurança

## Reportar vulnerabilidades
Não abra issue pública. Use *Security → Report a vulnerability* do GitHub (private advisory).

## Controles automatizados
- Dependências: `make audit` (pip-audit no lockfile completo) em todo PR; Dependabot semanal.
- Código: regras Bandit via Ruff (`S`), mypy strict, validação de entrada com pydantic.
- Segredos: gitleaks (pre-commit e CI); configuração apenas por variáveis `APP_*` (`SecretStr`).
- Supply chain de CI: actions fixadas por SHA, permissões mínimas, auditoria com zizmor.
- Imagem: base slim, usuário não-root, scan Trivy, attestation de proveniência no GHCR.
