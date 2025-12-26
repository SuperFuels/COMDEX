# BRIDGE — AUDIT REGISTRY

This registry lists **shipped** BRIDGE anchors and the **pinned** artifact run hashes.

## Shipped Anchors

### BG01 — Frame Dragging Analogue (Magneto–Gravity Dual)

**Claim (audit-safe, model-only):** programming **curl** in a shared information-flux field induces a predictable, signed shift in a **curvature proxy** (a cross-operator coupling).  
**We do not claim unification in nature**—only operator coupling in this controlled model.

**Pinned runs (BG01):**
- **tessaris_bg01_curl_drive:** `c6371a3`
- **open_loop:** `9dc5cd9`
- **random_jitter_kappa:** `de7f372`

**Pinned artifact paths:**
- `BRIDGE/artifacts/programmable_bridge/BG01/c6371a3/`
- `BRIDGE/artifacts/programmable_bridge/BG01/9dc5cd9/`
- `BRIDGE/artifacts/programmable_bridge/BG01/de7f372/`

**Repro command:**
```bash
cd /workspaces/COMDEX || exit 1
env PYTHONPATH=$PWD/BRIDGE/src python -m pytest \
  BRIDGE/tests/test_bg01_frame_dragging_analogue.py -vv
```

**Pinned commit:** `1da797bed (dirty)`
