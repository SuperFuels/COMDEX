# P9 Evidence Block — True Multiplexing (2-channel DSSS + post-demix)

- RUN_ID: `P920260101T190301Z_P9_MUX2`
- Git revision: `eec82c5c13e5f3425f913e8c7f3a091c1799ddfc`
- Test: `backend/photon_algebra/tests/paev_test_P9_true_multiplexing.py`

## Produced artifacts
- JSON: `docs/Artifacts/v0.4/P9/runs/P920260101T190301Z_P9_MUX2/P9_true_multiplexing.json`
- PNG:  `docs/Artifacts/v0.4/P9/runs/P920260101T190301Z_P9_MUX2/PAEV_P9_Multiplex_MainRho_vs_Distance.png`
- PNG:  `docs/Artifacts/v0.4/P9/runs/P920260101T190301Z_P9_MUX2/PAEV_P9_Multiplex_CrosstalkAbsRho_vs_Distance.png`
- Log:  `docs/Artifacts/v0.4/P9/logs/P920260101T190301Z_P9_MUX2.log`

## Expected status
- checks.overall_pass = true
- checks.orthogonality_ok = true

## Notes
- This run uses a linear controller + block-rate 2×2 post-demix to undo channel mixing.
