# BG01 — Frame Dragging Analogue (Evidence Block)

**Pillar:** BRIDGE  
**Anchor:** BG01 — Frame Dragging Analogue (Gemini “Coupling Dual”)  
**Generated:** `2025-12-25T23:26:11Z`  
**Pinned commit:** `1da797bed (dirty)`

## Scope / Guardrails

This evidence block is **simulation-first** and **model-only**.

We claim **operator coupling** inside a shared information-flux (J-field) model:
- We *program curl* (magnetism-side operator proxy) via bounded phase swirl injection.
- We measure the induced shift in a **curvature proxy** (gravity-side proxy derived from lattice amplitude structure).
- We report a signed, reproducible coupling coefficient under deterministic configuration + seed.

**Non-claims:** no claims about real-world gravity, frame dragging in spacetime, or unification laws of nature.

## What the anchor asserts (pytest)

- `coupling_coeff > 0` (signed coupling, by convention)
- `tessaris` beats `open_loop` and `random_jitter` on `coupling_score`
- boundedness guardrail: `max_norm` remains under configured safety threshold

## Pinned Runs

| Controller | Run hash | coupling_coeff | coupling_score | max_norm |
|---|---:|---:|---:|---:|
| `tessaris_bg01_curl_drive` | `c6371a3` | `0.223286` | `0.149784` | `8.832` |
| `open_loop` | `9dc5cd9` | `0.154724` | `-0.095276` | `8.832` |
| `random_jitter_kappa` | `de7f372` | `0.218126` | `-0.161568` | `8.832` |

## Pinned Artifact Paths

- `BRIDGE/artifacts/programmable_bridge/BG01/c6371a3/`
- `BRIDGE/artifacts/programmable_bridge/BG01/9dc5cd9/`
- `BRIDGE/artifacts/programmable_bridge/BG01/de7f372/`

Expected files per run folder:
- `run.json`
- `metrics.csv`
- `meta.json`
- `config.json`

## Repro Command

```bash
cd /workspaces/COMDEX || exit 1
env PYTHONPATH=$PWD/BRIDGE/src python -m pytest \
  BRIDGE/tests/test_bg01_frame_dragging_analogue.py -vv
```

## Reviewer checklist

1. Run the repro command (should PASS deterministically).
2. Open each pinned run folder and inspect:
   - `run.json` for summary metrics
   - `metrics.csv` for time series (curl RMS, curvature proxy, kappa schedule)
3. Confirm the pinned run hashes match this evidence block and `BRIDGE/AUDIT_REGISTRY.md`.
