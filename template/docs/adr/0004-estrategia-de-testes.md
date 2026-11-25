# 0004 — Estratégia de testes: contrato, propriedades, migrações e DAST

**Status:** Accepted

## Contexto
Testes por exemplo (unit, API, integração) provam os critérios de aceite, mas deixam escapar
entradas que ninguém pensou, divergência entre OpenAPI e comportamento, migrações que não
correspondem aos modelos e falhas de configuração visíveis só na aplicação implantada. Agentes
geram código rápido, então essas verificações precisam ser automáticas.

## Decisão
| Nível | Ferramenta | Onde roda | O que garante |
|---|---|---|---|
| Contrato/fuzz | Schemathesis a partir do OpenAPI (`tests/api/test_openapi_contract.py`) | `make test-unit` | Respostas conformes ao schema, sem `500`, para entradas geradas |
| Propriedades | Hypothesis (`tests/unit/test_domain_properties.py`) | `make test-unit` | Invariantes do domínio para qualquer entrada válida |
| Migrações | Alembic + testcontainers (`tests/integration/test_migrations.py`) | `make test`, só com Postgres | upgrade → downgrade → upgrade e modelos iguais às migrações |
| DAST | OWASP ZAP baseline (passivo) | CD, contra staging | Headers, cookies, exposição de informação na versão implantada |

Os níveis existentes continuam: unit, API (incluindo `tests/api/test_security.py`) e integração.

## Alternativas consideradas
| Opção | Prós | Contras |
|---|---|---|
| Só testes por exemplo | Simples | Não encontram casos-limite nem divergência de contrato |
| Pact (contrato dirigido pelo consumidor) | Valida consumidores reais | Exige broker e consumidores conhecidos; o OpenAPI já é a fonte |
| ZAP full scan (ativo) | Encontra mais | Lento, intrusivo e instável para todo deploy; rodar sob demanda |
| Schemathesis/ZAP só manual | Sem custo no pipeline | Regressões passam despercebidas |

## Consequências
- Mudar o OpenAPI sem mudar o comportamento (ou o contrário) quebra `make test-unit`.
- Hypothesis e Schemathesis aumentam o tempo dos testes; limite exemplos e use seeds
  deterministas no CI.
- Alertas do ZAP em staging são tratados (corrigidos ou justificados) antes de promover para produção.
- O ZAP baseline é passivo: não substitui `tests/api/test_security.py` nem revisão de autorização.
