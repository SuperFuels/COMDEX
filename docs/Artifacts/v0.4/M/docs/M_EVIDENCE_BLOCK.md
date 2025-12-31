# M Evidence Block — Emergent Curvature and Geodesic Proxies (M1–M6)

## Claim (model-only)
Under the Tessaris Unified Constants & Verification Protocol, the M-series demonstrates (simulation/lattice-model only):

- **M1:** emergent metric-like coefficients and a stable curvature proxy (non-overflow regime).
- **M2:** curvature–energy correspondence fit (**diagnostic**; fit error exceeds the module’s internal “tight” threshold in the pinned run; retained as a trend/relationship check, not as a strict proof step).
- **M3b/M3d:** dynamic curvature feedback and geodesic-like bounded motion in a stabilized regime (**noted tuning sensitivity**: damping/gain affect noise/underdamping; pinned run preserves this behavior).
- **M4b:** coupled curvature wells with observable energy exchange (normal-mode coupling signature).
- **M5:** bound-state redshift analogue (**small-magnitude shift in pinned run**; treated as an analogue signal under the proxy definition, not a physical redshift claim).
- **M6:** redshift-analogue invariance across boosts \(v/c_{\mathrm{eff}}\in\{0.0,0.1,0.2,0.3,0.4\}\) (invariance diagnostic passes in the pinned run).

No physical-world claims are made.

## Notes on “tuning” vs “broken”
- Some modules report **warnings / “needs tuning” language** in their own stdout (e.g., M2 fit error, M3 damping/gain comments, M5 magnitude language).  
- These are treated as **diagnostic notes**, not failures, unless they:
  1) invalidate the defined metric,  
  2) break determinism / reproducibility,  
  3) violate stated bounds or closures, or  
  4) contradict the equation being tested.
- The pinned run is accepted for v0.4 because the artifacts reproduce and the core invariance/bounding checks (notably M1 stability, M4 coupling signature, M6 invariance) remain intact.

## Pinned Run
- RUN_ID: 20251230T213353Z_M
- Git revision: 5a271385a6156344e43dee93cd8779876d38a797

## Lock-used artifacts (must exist in run folder)
- M1:  M1_metric_emergence_summary.json,              PAEV_M1_metric_emergence.png
- M2:  M2_curvature_energy_summary.json,              PAEV_M2_curvature_energy.png
- M3b: M3b_stable_curvature_feedback_summary.json,    PAEV_M3b_stable_curvature_feedback.png
- M3d: M3d_geodesic_oscillation_summary.json,         PAEV_M3d_geodesic_oscillation.png
- M4b: M4b_coupled_curvature_wells_summary.json,      PAEV_M4b_coupled_curvature_wells.png
- M5:  M5_bound_state_redshift_summary.json,          PAEV_M5_bound_state_redshift.png
- M6:  M6_invariance_redshift_summary.json,           PAEV_M6_invariance_redshift.png

## Verification
sha256sum -c docs/Artifacts/v0.4/M/checksums/20251230T213353Z_M.sha256

Lock ID: M_LOCK_v0.4_20251230T213353Z_M
Status: LOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson