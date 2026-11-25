---
name: discovery
description: Product discovery — turn an idea, problem or request into an approved PRD in docs/product/. Use when someone describes a new product, feature idea, problem or opportunity ("discovery", "PRD", "nova funcionalidade", "ideia", "problema") and no PRD exists yet.
---

# Discovery → PRD

Goal: agree on **the problem, for whom, and how we will know it worked** before any solution.

1. Read `docs/product/` to avoid duplicates and reuse context.
2. Interview the human — ask at most 5 questions per round, only what you cannot infer:
   - Who has the problem? What do they do today (workaround) and what does it cost?
   - What outcome changes if we solve it? Which metric moves, from what baseline to what target?
   - What is explicitly out of scope? Constraints (compliance, deadlines, integrations, volumes, SLAs)?
   - Which systems/data/events are involved (sources and outputs)?
3. Write `docs/product/<kebab-slug>.md` from `assets/prd-template.md`. Keep it to ~1 page.
   Mark unknowns as `> ❓ Open question:` instead of inventing answers.
4. List risks (value, usability, feasibility, viability) and the cheapest way to de-risk each.
5. Ask the human to approve. Record `Status: Approved` + date. Only then suggest `$specify`
   (one spec per independently shippable slice — propose the slices).

Do not design the solution or write code in this phase.
