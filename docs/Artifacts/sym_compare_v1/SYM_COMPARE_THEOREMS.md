# Symatics — Separation Theorems (sym_compare_v1)

Status: LOCKED & VERIFIED
Date: 2026-01-12
Maintainer: Tessaris AI
Author: Kevin Robinson

This note binds the formal (Lean) no-go theorems to the locked numerical witnesses emitted by deterministic runners.

## Artifact root and lock surface

- Root: docs/Artifacts/sym_compare_v1/
- Lock surface: docs/Artifacts/sym_compare_v1/SYM_COMPARE_LOCK_SURFACE.json
- Thresholds: docs/Artifacts/sym_compare_v1/SYM_COMPARE_ACCEPTANCE_THRESHOLDS.yaml (seed=0)

## Lean theorems (abstract no-go)

Lean workspace:
- backend/modules/lean/workspace/

File:
- backend/modules/lean/workspace/SymaticsBridge/SymCompare/NoGo.lean

Theorem names:
- SymCompare.image_phi_invariant
- SymCompare.N1_no_effectalg_representation
- SymCompare.N2_no_semiring_extension

Witness/SHA binding:
- backend/modules/lean/workspace/SymaticsBridge/SymCompare/Witnesses.lean

Build command:
- cd backend/modules/lean/workspace && lake build SymaticsBridge.SymCompare.NoGo SymaticsBridge.SymCompare.Witnesses

## Locked witnesses (JSON)

N1 (effect-algebra / OML separation):
- docs/Artifacts/sym_compare_v1/EFFECTALG_COUNTEREXAMPLE.json
- SHA256 must match EFFECTALG_METRICS.json.digests.counterexample_sha256 and SYM_COMPARE_LOCK_SURFACE.json

N2 (semiring distributivity separation):
- docs/Artifacts/sym_compare_v1/SEMIRING_COUNTEREXAMPLE.json
- SHA256 must match SEMIRING_METRICS.json.digests.counterexample_sha256 and SYM_COMPARE_LOCK_SURFACE.json
