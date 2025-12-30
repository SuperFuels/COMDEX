# VOL IV Audit Notes — Coherence as Information (v0.1)

## Truth Chain compliance (non-negotiable)
- MUST use `\mu` for measurement/collapse/selection.
- MUST reserve `\nabla` for geometric gradient/divergence only.
- MUST use `\Delta` for Born weight / intensity (not collapse).

## Metric definitions (lock-critical)
Define:
- `C_phi := |⟨exp(i Δφ)⟩| ∈ [0,1]`
- `D_phi := 1 - C_phi`
- `I := 1 - D_phi = C_phi`

These definitions avoid undefined behavior from `log(⟨cos(Δφ)⟩)` when the cosine average is ≤ 0.

## Acceptance thresholds
See:
- `docs/Artifacts/VolIV/build/VOLIV_ACCEPTANCE_THRESHOLDS.yaml`

Lock requires:
- `I_final >= 0.95` (equivalently `C_phi_final >= 0.95`)
- `D_phi_final <= 0.05`
- achieved within the lock window.

## Repro hooks
- Scene: `docs/Artifacts/VolIV/qfc/VOL4_COHERENCE_PHASE_LOCK.scene.json`
- Proof mirror: `docs/Artifacts/VolIV/proofs/VolIV_Coherence_As_Information_v0_1.tex`
- Evidence log: `docs/Artifacts/VolIV/ledger/VOLIV_LINT_PROOF.log`

## What “LOCKED & VERIFIED” means for Vol IV
Vol IV is LOCKED & VERIFIED only when:
1) the scene passes thresholds, and
2) the evidence log records the metric values + pass/fail, and
3) artifact paths remain stable (or Truth Chain is updated if they change).
