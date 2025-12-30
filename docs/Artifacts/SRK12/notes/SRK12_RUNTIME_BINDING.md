# SRK-12 Runtime Binding Notes

## Canonical runtime anchor
- `backend/modules/photon/photon_algebra_runtime.py`

## Spec → runtime responsibilities
- Implement `fuse(φ)` as phase-parameterized interference:
  - constructive reinforcement and destructive cancellation (⊥)
- Implement governed selection:
  - Born weight from `|amp|^2` (Δ used as the weight concept)
  - policy modulation via `status_bonus`
  - renormalization after modulation
- Emit audit traces compatible with:
  - `docs/Artifacts/SRK12/ledger/SRK12_GOVERNED_SELECTION_TRACE_SCHEMA.json`

## Ledger dependency
SRK-12 must reference SRK-8 repaired ledger hashes for any operator semantics it consumes:
- `docs/Artifacts/SRK8/ledger/theorem_ledger_repaired.jsonl`
