# 0001 — Registrar decisões de arquitetura

**Status:** Accepted

## Contexto
Decisões difíceis de reverter precisam de contexto preservado para pessoas e agentes.

## Decisão
Usamos ADRs curtos (template em `.agents/skills/plan/assets/adr-template.md`), numerados,
imutáveis após aceitos (substituídos por um novo ADR quando mudam). A skill `$plan` cria ADRs.

## Consequências
Agentes leem `docs/adr/` antes de propor desenho; revisões citam ADRs em vez de reabrir debates.
