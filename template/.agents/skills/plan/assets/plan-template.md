# Plano — NNN <título>

**Spec:** ./spec.md · **ADRs:** <links> · **Status:** Draft | Approved (<data>)

## Desenho
| Camada | Mudança |
|---|---|
| domain | <entidades, invariantes, eventos> |
| application | <casos de uso, ports novos/alterados> |
| adapters | <implementações: postgres/redis/broker/http/memory> |
| entrypoints | <rotas, consumers, schemas> |
| container | <wiring, health checks> |

## Contratos e migrações
<OpenAPI/eventos/tabelas. Compatibilidade e estratégia expand → contract.>

## Ameaças e abusos
| Ameaça (OWASP API 2023) | Controle | Teste |
|---|---|---|
| <ex.: API1 ler objeto de outro dono> | <filtro por dono → `404`> | <`tests/api/test_security.py::...`> |

## Modos de falha
| Falha | Comportamento | Teste |
|---|---|---|

## Estratégia de testes
| AC | Nível (unit/property/api/contract/integration) | Arquivo de teste |
|---|---|---|

## Tarefas
- [ ] T1 — <descrição> (AC-1)
- [ ] T2 — ...

## Riscos / rollout
<feature flag, migração em etapas, plano de rollback.>
