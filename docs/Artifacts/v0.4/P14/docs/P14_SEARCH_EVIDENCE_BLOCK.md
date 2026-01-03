# P14 Search v0 — Evidence Block (v0.4)

## What is locked
A deterministic search skeleton (random baseline + hillclimb) with an evaluator-injected interface
and a smoke test.

## Scope (v0)
- Search engines: **randomSearch**, **hillclimb**.
- Deterministic RNG: simple LCG seeded by `seed`.
- Evaluator is injected (no SIM coupling claimed here).
- Audit bundle support: stable JSON via key-sorted stringify.
- Smoke test uses a toy objective to prove determinism + basic improvement.

## Repo entry points
- Search: `Glyph_Net_Browser/src/sim/search/search.ts`
- Types:  `Glyph_Net_Browser/src/sim/search/types.ts`
- Bundle: `Glyph_Net_Browser/src/sim/search/bundle.ts`
- Stable JSON: `Glyph_Net_Browser/src/sim/search/stable_json.ts`
- RNG: `Glyph_Net_Browser/src/sim/search/rng_lcg.ts`
- Smoke: `Glyph_Net_Browser/src/sim/tests/P14_search_smoke.test.ts`

## Reproduce (repo)
```bash
cd /workspaces/COMDEX || exit 1
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests/P14_search_smoke.test.ts
```

## Locked run
- RUN_ID: P1420260102T211120Z_P14_SEARCH_V0
- GIT_REV: 30b5ab16eb695f028a8ce6aa23000f6101418f63
- Log: docs/Artifacts/v0.4/P14/logs/P1420260102T211120Z_P14_SEARCH_V0_vitest.txt

## Guardrail
This is an algorithmic search scaffold + determinism proof. Model-scoped; no physics claims.
