# P12_SIM — Stage C SIM harness (A2 + A4 + A3.1) — LOCK EVIDENCE

RUN_ID: P12SIM20260102T200720Z_A2A4A31
GIT_REV: 30b5ab16eb695f028a8ce6aa23000f6101418f63

## Repro command
```bash
cd /workspaces/COMDEX || exit 1
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests
```

## Locked scope
- A2 Resonant Addressing (oscillator bank proxy)
- A4 k_link vs distance (Kuramoto 2-node proxy)
- A3.1 Chiral Handshake (chirality-gated coupling + phase drift metric)

## Guardrail
Proxy models only; engineering signatures; no physics claims.
