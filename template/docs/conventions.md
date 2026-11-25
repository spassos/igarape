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

## Observabilidade
- `structlog` com eventos `snake_case` e contexto chave/valor; `request_id` propagado
  (`X-Request-ID`). JSON fora do ambiente local.
- `/health/live` (processo + versão) e `/health/ready` (dependências) obrigatórios.

## Testes (pirâmide)
| Nível | Pasta | Dependências | Quando |
|---|---|---|---|
| Unit | `tests/unit` | nenhuma (fakes em memória) | regra de negócio e casos de uso |
| API | `tests/api` | TestClient + fakes | contrato HTTP, validação, mapeamento de erros |
| Integração | `tests/integration` | testcontainers / respx | cada adapter real + fluxo ponta a ponta |

AAA, um comportamento por teste, nome descreve o comportamento, sem `sleep`, sem internet.

## Git
- Trunk-based: branches curtas `feat/NNN-slug`, `fix/...`; squash merge.
- Conventional Commits no título do PR (gera versão e CHANGELOG).
- Um PR por mudança focada. Vincule o pedido e o teste de regressão para correções locais, ou a spec para mudanças planejadas.
