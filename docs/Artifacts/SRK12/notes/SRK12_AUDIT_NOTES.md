# SRK-12 EVV / Audit Notes (v1.1)

## Non-negotiables (Truth Chain)
- MUST use `\mu` for measurement/collapse/selection.
- MUST reserve `\nabla` for geometric gradient/divergence only.
- MUST use `\Delta` for Born weight / intensity (not collapse).

## Lock condition (artifact integrity)
Required:
- SRK-8 repaired ledger:
  - `docs/Artifacts/SRK8/ledger/theorem_ledger_repaired.jsonl`
- Runtime anchor:
  - `backend/modules/photon/photon_algebra_runtime.py`
- Validation anchor (evidence track):
  - `docs/rfc/Photon Algebra Experimental Validation/Photon Algebra Experimental Validation Suite (PAEV-10)/Born rule/`

Optional but recommended:
- Scene:
  - `docs/Artifacts/SRK12/qfc/SRK12_GOVERNED_SELECTION.scene.json`

## Deterministic replay requirement
Every governed selection MUST be replayable from:
- WaveCapsule snapshot (amps/phases),
- policy trace (status_bonus + tags),
- renormalization step,
- final choice.
