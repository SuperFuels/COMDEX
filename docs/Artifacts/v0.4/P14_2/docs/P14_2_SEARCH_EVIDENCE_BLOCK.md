# P14_2 — P12_SIM Evaluator Wiring (v0.4)

RUN_ID: `P14_220260102T220043Z_P14_P12SIM_EVAL_V02`

## What is locked
- P14 search scaffold remains deterministic (seeded LCG + stable JSON).
- Adds evaluator wiring to P12-style A2 proxy metrics (selectivity S, crosstalk X) via `p12_sim.ts`.
- Includes toy objective fallback to keep search plumbing testable independent of SIM.

## Canonical repro
```bash
cd /workspaces/COMDEX || exit 1
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests/P14_search_p12sim_smoke.test.ts
```

## Repo artifacts
- `Glyph_Net_Browser/src/sim/search/search.ts`
- `Glyph_Net_Browser/src/sim/search/rng_lcg.ts`
- `Glyph_Net_Browser/src/sim/search/evaluators/p12_sim.ts`
- `Glyph_Net_Browser/src/sim/tests/P14_search_p12sim_smoke.test.ts`

## Guardrail
Model-scoped evaluator wiring only; no physics/biology claims.
