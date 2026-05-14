# v40 — Correlation over two delta streams (no materialization)

This bridge proves the **delta update laws** used by the executable benchmark:
- Sx, Sy, Sxx, Syy, Sxy maintained under point updates
- no materialization (stream of deltas + template)
- core Lean only (no mathlib)

## Lean proof artifact
- `V40_CorrelationTwoStreamsNoMaterialization.lean` (copied from workspace canonical path)

### Key theorems (names in Lean file)
- `sumN_setAt_delta`  
  Changing one index shifts `sumN` by `(new - old)` iff `idx < n`.
- `Sx_update`, `Sy_update`
- `Sxx_update`, `Syy_update`
- `Sxy_update_x`, `Sxy_update_y`

## Executable receipt (benchmark output)
See:
- `v40_correlation_two_streams_no_materialization_out.txt`

It records:
- canon idempotence + stability
- `query_ok=True` (maintained components == recompute snapshot)
- `LEAN_OK=1`
- `SHA256 (v40)` lines for the Lean file + benchmark script

---

Lock ID: v40_correlation_two_streams_no_materialization  
Status: LOCKED  
Maintainer: Tessaris AI  
Author: Kevin Robinson.
