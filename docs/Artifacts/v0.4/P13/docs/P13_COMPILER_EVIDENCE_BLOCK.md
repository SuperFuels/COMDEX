# P13 Compiler v0 — Evidence Block (v0.4)

## What is locked
A minimal, auditable compiler that maps **Intent → Program** (Lexicon Program object), plus a smoke test.

## Scope (v0)
- Supports only **A2** + **A3.1** intents.
- Output bundle includes: **Program (tokens[])**, thresholds, and metadata.
- Determinism: bundle is deterministic for the same intent **except** `meta.created_utc`.

## Repo entry points
- Compiler: `Glyph_Net_Browser/src/sim/compiler/compile.ts`
- Types:    `Glyph_Net_Browser/src/sim/compiler/types.ts`
- Smoke:    `Glyph_Net_Browser/src/sim/tests/P13_compiler_smoke.test.ts`
- Program runtime: `Glyph_Net_Browser/src/sim/lexicon.ts`

## Reproduce (repo)
```bash
cd /workspaces/COMDEX || exit 1
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests/P13_compiler_smoke.test.ts
```

## Locked run
- RUN_ID: P1320260102T202855Z_P13_COMPILER_V0
- GIT_REV: 30b5ab16eb695f028a8ce6aa23000f6101418f63
- Log: docs/Artifacts/v0.4/P13/logs/P1320260102T202855Z_P13_COMPILER_V0_vitest.txt

## Guardrail
Compiler + smoke test validates program-shape + minimal executability only. Model-scoped; no physics claims.
