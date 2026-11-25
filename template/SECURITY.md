# Segurança

## Reportar vulnerabilidades
Não abra issue pública. Use *Security → Report a vulnerability* do GitHub (private advisory) com
passos para reproduzir, versão afetada e impacto. Confirmamos o recebimento em até 3 dias úteis,
combinamos o prazo de correção conforme a severidade e publicamos o advisory após a correção.
Só a versão implantada mais recente recebe correções.

## Controles da API (OWASP API Security Top 10 2023)
Detalhes em [`docs/conventions.md`](docs/conventions.md#segurança-owasp-api-top-10) e
[ADR 0003](docs/adr/0003-autenticacao-jwt-oidc.md).

| Risco | Controle |
|---|---|
| API1 BOLA | Dono do objeto = `sub` do token; objeto de outro dono → `404` |
| API2 Autenticação | JWT/OIDC validado via JWKS: algoritmos permitidos, `exp`/`iss`/`aud`/`sub` obrigatórios; falha na inicialização sem configuração em staging/produção |
| API3 Propriedades | Schemas de entrada sem campos internos (`id`, `owner_id`) |
| API4 Recursos | Limite de corpo (`413`), timeouts; rate limiting no API gateway |
| API5 Função | Negado por padrão: `require_scopes` em toda rota `/v1`; só `/health` é pública |
| API7 SSRF | `ensure_public_https_url()` para URLs de saída |
| API8 Configuração | Erros `application/problem+json`, headers de segurança, `no-store`, HSTS em produção, `/docs` só em `local`/`test` |
| API9 Inventário | Rotas versionadas (`/v1`), contrato OpenAPI testado com Schemathesis |
| API10 Consumo | Respostas de terceiros validadas com pydantic, timeouts |

## Controles automatizados
- Dependências: `make audit` (pip-audit no lockfile completo) em todo PR; Dependabot semanal.
- Código: regras Bandit via Ruff (`S`), mypy strict, validação de entrada com pydantic.
- Testes: `tests/api/test_security.py` (`401`/`403`/BOLA), contrato Schemathesis, OWASP ZAP
  baseline contra staging no CD.
- Segredos: gitleaks (pre-commit e CI); configuração apenas por variáveis `APP_*` (`SecretStr`).
- Supply chain de CI: actions fixadas por SHA, permissões mínimas, auditoria com zizmor.
- Imagem: base slim, usuário não-root, scan Trivy, attestation de proveniência no GHCR.
