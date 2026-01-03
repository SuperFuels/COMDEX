# P14_4 Search Evidence Block — P12_SIM Harness Evaluator (A2)

RUN_ID: `P14_420260102T223404Z_P14_P12SIM_HARNESS_EVAL_V04`
GIT_REV: `30b5ab16eb695f028a8ce6aa23000f6101418f63`

## What is locked
- Harness-backed evaluator that calls the same SIM components as `A2_resonant_addressing.test.ts`:
  mulberry32 RNG, runSim harness, oscillator model (bank/step/energy), metrics (selectivity/crosstalk), and lexicon applyProgramAtTime.
- Search core compatibility preserved (RNG + search result shapes).
- Deterministic improvement over random baseline under fixed seed (smoke).

## Repro
```bash
cd /workspaces/COMDEX || exit 1
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests/P14_search_p12sim_harness_smoke.test.ts
```

## Guardrail
Model-scoped harness/proxy metrics only. No biology/physics claims.
