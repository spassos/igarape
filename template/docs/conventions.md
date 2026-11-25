# Convenções de engenharia

Regra geral: **não reinventar a roda** — use a biblioteca padrão e as libs já escolhidas
(ADR 0002) antes de escrever infraestrutura própria.

## Código
- Python moderno (PEP 8/257/484/604), formatado e lintado pelo Ruff; `mypy --strict`.
- Funções pequenas (complexidade ciclomática ≤ 8), um nível de abstração por função, nomes do
  domínio. Sem comentários que repetem o código; docstrings explicam o *porquê* e o contrato.
- Imports absolutos; nada de `import *`; nada de estado global mutável (exceto configuração de log).
- Dataclasses `frozen` no domínio; pydantic apenas nas bordas (HTTP, mensagens, settings).
- Datas sempre com timezone (UTC); IDs `UUID`; dinheiro em `Decimal`.

## Arquitetura (hexagonal)
- `domain` ← `application` ← `adapters`/`entrypoints`; composição só em `container.py`.
- Toda dependência externa entra por um *port* (`Protocol`) com fake em memória.
- Erros de negócio herdam de `DomainError`; tradução para HTTP/mensagem nas bordas.

## Async e I/O
- Tudo assíncrono; nunca bloquear o event loop (sem `requests`, `time.sleep`).
- Timeout explícito em toda chamada de rede; retry (stamina) só em operações idempotentes.
- Consumidores de eventos idempotentes; eventos com mudanças apenas aditivas.

## Configuração e segredos
- 12-factor: `Settings` com prefixo `APP_`; segredos como `SecretStr`, nunca logados.
- `.env` só local (ignorado pelo git); produção injeta variáveis pela plataforma.

## Segurança (OWASP API Top 10)
Negado por padrão: toda rota de negócio fica sob `/v1` e declara `require_scopes(...)`; só
`/health/*` é pública. Decisões em [ADR 0003](adr/0003-autenticacao-jwt-oidc.md).

| Risco (2023) | Controle no template | Ao criar ou alterar um endpoint |
|---|---|---|
| API1 BOLA | `owner_id` = `sub` do token; item de outro dono → `404` | Filtrar todo acesso por dono (ou regra da spec); teste com dois sujeitos |
| API2 Autenticação | JWT/OIDC via JWKS (`adapters/jwt_verifier.py`): algoritmos permitidos, `exp`/`iss`/`aud`/`sub` obrigatórios | Nunca validar token fora do `TokenVerifier`; `401` + `WWW-Authenticate: Bearer` |
| API3 Propriedades | Schemas pydantic de entrada e saída separados | Não aceitar `id`, `owner_id` ou campos internos no corpo; responder só campos do schema |
| API4 Recursos | Limite de corpo (`APP_MAX_BODY_BYTES` → `413`), timeouts; rate limit no gateway | Listagens paginadas com `limit` máximo; limites de tamanho em todo campo |
| API5 Função | Escopos `<recurso>:read`/`<recurso>:write` | Escopo mínimo por rota; `403` quando faltar |
| API6 Fluxos sensíveis | Rate limit no gateway | Registrar na spec os fluxos que pedem limite próprio (cadastro, compra) |
| API7 SSRF | `ensure_public_https_url()` em `adapters/http_client.py` | Validar toda URL de saída vinda de usuário ou de terceiros |
| API8 Configuração | Erros RFC 9457 (`application/problem+json`), headers de segurança, `no-store` em `/v1`, HSTS em produção; `/docs` só em `local`/`test` | Sem stack trace ou texto de exceção na resposta; nada de CORS aberto |
| API9 Inventário | Versão no caminho (`/v1`), OpenAPI testado por Schemathesis | Mudança incompatível = nova versão; contrato na spec |
| API10 Consumo de APIs | httpx com timeout, `retry_transient` | Validar respostas de terceiros com modelos pydantic; nunca repassar payload do fornecedor |

Também: entrada validada na borda (pydantic com tamanho, formato e valores permitidos);
segredos só via `Settings`/`SecretStr`; nunca logar tokens, `Authorization` ou PII.
`APP_AUTH_DEV_SECRET` só vale em `local`/`test`; em staging/produção a aplicação não sobe sem
JWKS, emissor e audiência.

## Observabilidade
- `structlog` com eventos `snake_case` e contexto chave/valor; `request_id` propagado
  (`X-Request-ID`). JSON fora do ambiente local.
- `/health/live` (processo + versão) e `/health/ready` (dependências) obrigatórios.

## Testes (pirâmide)
| Nível | Onde | Dependências | Quando |
|---|---|---|---|
| Unit | `tests/unit` | nenhuma (fakes em memória) | regra de negócio e casos de uso |
| Propriedades | `tests/unit/test_domain_properties.py` | Hypothesis | invariantes do domínio para qualquer entrada válida |
| API | `tests/api` | TestClient + fakes | contrato HTTP, validação, mapeamento de erros |
| Segurança | `tests/api/test_security.py` | TestClient + `make_auth_headers` | `401`/`403`, BOLA (`404`), headers, `413` por critério |
| Contrato | `tests/api/test_openapi_contract.py` | Schemathesis | toda operação do OpenAPI: respostas conformes, nunca `500` |
| Integração | `tests/integration` | testcontainers / respx | cada adapter real + fluxo ponta a ponta |
| Migrações | `tests/integration/test_migrations.py` | testcontainers (só com Postgres) | upgrade → downgrade → upgrade; modelos = migrações |
| DAST | CD (staging) | OWASP ZAP baseline | scan passivo da versão implantada |

Contrato e propriedades usam Hypothesis derandomizado (`derandomize=True`, sem banco de exemplos,
sem deadline): a mesma entrada em toda execução. Lacunas conhecidas do OpenAPI ficam explícitas em
`UNDOCUMENTED_STATUS_CODES` (hoje vazia) e um teste falha quando a rota passa a documentá-las.

Unit, propriedades, API, segurança e contrato rodam em `make test-unit`. Decisões em
[ADR 0004](adr/0004-estrategia-de-testes.md).

AAA, um comportamento por teste, nome descreve o comportamento, sem `sleep`, sem internet.

## Git
- Trunk-based: branches curtas `feat/NNN-slug`, `fix/...`; squash merge.
- Conventional Commits no título do PR (gera versão e CHANGELOG).
- Um PR por mudança focada. Vincule o pedido e o teste de regressão para correções locais, ou a spec para mudanças planejadas.
