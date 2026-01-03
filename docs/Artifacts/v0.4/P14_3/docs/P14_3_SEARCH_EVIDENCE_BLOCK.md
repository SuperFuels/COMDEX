# P14_3 — Search compat unification (LOCKED)

RUN_ID: `P14_320260102T221043Z_P14_SEARCH_COMPAT_V03`  
GIT_REV: `30b5ab16eb695f028a8ce6aa23000f6101418f63`  
Date (UTC): `2026-01-02T22:10:44Z`

## What is locked
- Deterministic RNG compat surface: `next()`, `nextInt(n)`, `int(lo,hi)`, `float01()`
- Search core emits BOTH:
  - New fields: `best`, `bestFitness`, `traceBestScalar`
  - Legacy fields: `best_candidate`, `best_fitness`, `best_score_trace`, `best_pass_trace`
- Evaluator wiring: P14→P12_SIM A2 proxy scorer (selectivity/crosstalk) + toy fallback
- GA/ES smoke tests remain deterministic under the same RNG

## Canonical repro
```bash
cd /workspaces/COMDEX || exit 1
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests
```

## Guardrail
Model-scoped determinism + plumbing only. No physics/biology claims.
