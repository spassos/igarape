# 0003 — Autenticação JWT/OIDC e autorização por objeto

**Status:** Accepted

## Contexto
A API precisa de autenticação e autorização desde o primeiro endpoint (OWASP API Security
Top 10 2023: API1 BOLA, API2, API5). O provedor de identidade muda de time para time (Keycloak,
Auth0, Entra ID, Cognito, Google) e o serviço não deve depender de nenhum deles. Clientes são
outros serviços, SPAs e apps móveis.

## Decisão
- **Bearer JWT de qualquer provedor OIDC**, validado localmente com as chaves públicas do JWKS
  (`APP_AUTH_JWKS_URL`, `APP_AUTH_ISSUER`, `APP_AUTH_AUDIENCE`, `APP_AUTH_ALGORITHMS`, padrão
  `RS256`). O adapter `adapters/jwt_verifier.py` (PyJWT) mantém o JWKS em cache, aceita só os
  algoritmos configurados e exige `exp`, `iss`, `aud` e `sub`. Domínio e aplicação veem apenas
  `Principal(subject, scopes)` e o port `TokenVerifier`.
- **Negado por padrão:** rotas de negócio ficam sob `/v1` e declaram `require_scopes(...)`
  (`items:read`, `items:write`). Sem token ou token inválido → `401` com
  `WWW-Authenticate: Bearer`; sem o escopo → `403`. Só `/health/*` é pública.
- **Autorização por objeto no caso de uso:** o dono (`owner_id`) é o `sub` do token. Ler item de
  outro dono responde `404`, igual a um id inexistente, para não revelar existência.
- **Desenvolvimento:** `APP_AUTH_DEV_SECRET` (HS256) só vale em `local`/`test`; `make token`
  emite tokens locais. Em staging/produção a aplicação falha na inicialização se faltar JWKS,
  emissor ou audiência, ou se houver segredo de desenvolvimento.
- **Rate limiting no API gateway**, não na aplicação. A aplicação limita o corpo
  (`APP_MAX_BODY_BYTES`, `413`) e aplica timeouts.
- Erros em RFC 9457 (`application/problem+json`); `/docs` e `/openapi.json` só em `local`/`test`.

## Alternativas consideradas
| Opção | Prós | Contras |
|---|---|---|
| Cookies de sessão | Revogação imediata, simples para web | Estado no servidor, CSRF, ruim para serviço a serviço e mobile |
| API keys próprias | Simples | Sem identidade de usuário nem escopos padronizados; rotação e armazenamento por nossa conta |
| SDK do provedor | Integração rápida | Acoplamento a um fornecedor; troca de provedor vira reescrita |
| authlib / fastapi-users | Muitos fluxos prontos | Superfície maior que o necessário (servidor OAuth, gestão de usuários); só precisamos validar tokens |
| `403` para objeto de outro dono | Semântica mais literal | Confirma que o id existe (enumeração) |
| Rate limit na aplicação | Sem dependência de infraestrutura | Contadores por réplica, estado extra (Redis) e regra duplicada; o gateway já vê todo o tráfego |

## Consequências
- Trocar de provedor é configuração. Revogação depende da validade curta do access token.
- Todo endpoint novo precisa de escopo, regra de dono e teste de `401`/`403`/`404`
  (`tests/api/test_security.py`).
- Sem gateway com rate limit, a API fica exposta a abuso de volume (API4/API6): é requisito de
  implantação.
- Comandos internos (worker) carregam `owner_id` de um produtor confiável; o broker precisa de
  ACL que restrinja quem publica.
