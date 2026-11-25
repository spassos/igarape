## O quê e por quê
<!-- Uma ou duas frases. -->

<!-- Correção local: referencie o pedido e o teste de regressão. Mudança planejada: vincule a spec, o plano e a ADR (se houver). -->

## Critérios de aceite
| Comportamento esperado | Teste |
|---|---|
| <!-- Critério da spec ou comportamento corrigido --> | `tests/...::test_...` |

## Checklist (Definition of Done)
- [ ] `make check` verde localmente
- [ ] Teste de regressão ou testes para os critérios de aceite
- [ ] Alterações de contrato, se houver, documentadas na spec e compatíveis (ou versionadas)
- [ ] Migrações, se houver, reversíveis ou com expand/contract
- [ ] Sem segredos/PII em código, logs ou fixtures
- [ ] Docs/ADRs atualizados
- [ ] `$review` executado sem bloqueios

## Riscos e rollout
<!-- Feature flag? Ordem de deploy? Plano de rollback? -->
