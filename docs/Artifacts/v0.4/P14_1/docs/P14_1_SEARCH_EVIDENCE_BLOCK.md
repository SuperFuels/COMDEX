# P14 Search v0.1 (GA/ES) — Evidence Block (v0.4)

## What is locked
Deterministic GA + ES search implementations with option-name compatibility and an auditable trace surface.

## Scope (v0.1)
- GA + ES only (toy objective smoke tests).
- Determinism under fixed seed.
- Emits: bestGenome, bestFitness.primary, traceBestScalar[].

## Repo entry points
- GA:  Glyph_Net_Browser/src/sim/search/ga.ts
- ES:  Glyph_Net_Browser/src/sim/search/es.ts
- RNG: Glyph_Net_Browser/src/sim/search/rng_lcg.ts
- Test: Glyph_Net_Browser/src/sim/tests/P14_search_ga_es_smoke.test.ts

## Reproduce (repo)
```bash
cd /workspaces/COMDEX || exit 1
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests/P14_search_ga_es_smoke.test.ts
```

## Locked run
- RUN_ID: P14_120260102T213934Z_P14_SEARCH_GAES_V01
- GIT_REV: 30b5ab16eb695f028a8ce6aa23000f6101418f63
- Log: docs/Artifacts/v0.4/P14_1/logs/P14_120260102T213934Z_P14_SEARCH_GAES_V01_vitest.txt

## Guardrail
Search + smoke tests validate determinism and result-shape only; no physics claims.
