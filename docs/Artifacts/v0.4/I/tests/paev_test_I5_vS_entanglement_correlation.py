#!/usr/bin/env python3
"""
PAEV Test I5 - Entropy-Entanglement Coupling (v_S vs CHSH proxy)
Tessaris Photon Algebra Framework (Registry-aligned)

Supports two trace schemas:
  (A) row-records: {"records":[{"t":..,"v_s_over_v_c":..,"S_CHSH":..}, ...]}
  (B) columnar:    {"time":[...], "v_S_over_v_c":[...], "S_CHSH":[...], ...}

Computes Pearson correlation between v_S/v_c and S_CHSH and searches small positive lags.

Artifacts:
  - backend/modules/knowledge/I5_entropy_entanglement_corr.json
  - PAEV_I5_vS_vs_CHSH_scatter.png
  - PAEV_I5_vS_vs_CHSH_lag.png
"""

import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import matplotlib.pyplot as plt

print("=== I5 - Entropy-Entanglement Coupling (v_S vs CHSH proxy) ===")

# =====================================================
# 🔹 Load Tessaris constants (auto-synced)
# =====================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

# (kept for audit parity / registry alignment)
ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)

# =====================================================
# 📂 Source trace loader (schema-tolerant)
# =====================================================
TRACE_CANDIDATES = [
    Path("backend/modules/knowledge/E6Omega_vS_trace.json"),
    Path("backend/modules/knowledge/E6Omega_vS_trace_v5c.json"),
]

ROW_LIST_KEYS = ("records", "trace", "samples", "data", "rows")

def _first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None

def _as_float_array(x, name):
    if x is None:
        raise RuntimeError(f"Missing required series: {name}")
    if not isinstance(x, list) or len(x) == 0:
        raise RuntimeError(f"Series '{name}' is missing or empty")
    return np.asarray(x, dtype=float)

def load_trace_any_schema():
    p = _first_existing(TRACE_CANDIDATES)
    if p is None:
        raise FileNotFoundError(
            "Missing trace file. Expected one of:\n"
            "  backend/modules/knowledge/E6Omega_vS_trace.json\n"
            "  backend/modules/knowledge/E6Omega_vS_trace_v5c.json\n"
        )

    d = json.loads(p.read_text())

    # ---- Schema A: row records ----
    for k in ROW_LIST_KEYS:
        recs = d.get(k)
        if isinstance(recs, list) and len(recs) > 0 and isinstance(recs[0], dict):
            def gf(r, *names):
                for n in names:
                    if n in r:
                        return r[n]
                return None

            vs = np.array([gf(r, "v_s_over_v_c", "v_S_over_v_c", "vs_over_vc", "vS_over_vc") for r in recs], dtype=float)
            sx = np.array([gf(r, "S_CHSH", "s_chsh", "chsh") for r in recs], dtype=float)
            tt = np.array([gf(r, "t", "time", "ts") for r in recs], dtype=float)

            if np.any(np.isnan(vs)) or np.any(np.isnan(sx)):
                raise RuntimeError("Row-record schema found but missing v_s_over_v_c / S_CHSH in some records.")

            return p, d, tt, vs, sx, f"row:{k}"

    # ---- Schema B: columnar arrays ----
    time_key_candidates = ("time", "t", "ts")
    vs_key_candidates = ("v_S_over_v_c", "v_s_over_v_c", "vs_over_vc", "vS_over_vc")
    sx_key_candidates = ("S_CHSH", "s_chsh", "chsh")

    def pick_series(keys):
        for k in keys:
            if k in d:
                return k, d[k]
        return None, None

    t_key, t_list = pick_series(time_key_candidates)
    vs_key, vs_list = pick_series(vs_key_candidates)
    sx_key, sx_list = pick_series(sx_key_candidates)

    vs = _as_float_array(vs_list, "v_S_over_v_c")
    sx = _as_float_array(sx_list, "S_CHSH")

    n = min(len(vs), len(sx))
    vs = vs[:n]
    sx = sx[:n]

    if t_list is None:
        tt = np.arange(n, dtype=float)
        t_key = "(synth)"
    else:
        tt = _as_float_array(t_list, "time")[:n]

    return p, d, tt, vs, sx, f"col:{t_key},{vs_key},{sx_key}"

trace_path, trace_data, t, vs, Sx, schema_tag = load_trace_any_schema()

# =====================================================
# 🔍 Correlation functions
# =====================================================
def pearson(x, y):
    x = np.asarray(x) - np.mean(x)
    y = np.asarray(y) - np.mean(y)
    denom = (np.std(x) * np.std(y) + 1e-12)
    return float(np.mean(x * y) / denom)

corr0 = pearson(vs, Sx)

max_lag = 10  # steps
lags = np.arange(0, max_lag + 1)
corrs = []
for L in lags:
    if L == 0:
        corrs.append(corr0)
    else:
        corrs.append(pearson(vs[:-L], Sx[L:]))

best_idx = int(np.argmax(corrs))
best_lag = int(lags[best_idx])
best_corr = float(corrs[best_idx])

# =====================================================
# 🧭 Classification logic
# =====================================================
if best_corr > 0.5:
    classification = "✅ Coupled bursts-entanglement (model)"
    note = f"v_S bursts precede entanglement rise by {best_lag} step(s)."
else:
    classification = "⚠ Inconclusive coupling (model)"
    note = "Correlation <= 0.5 for all tested lags."

dt_est = float(np.median(np.diff(t))) if t.size > 1 else None

# =====================================================
# 🧩 Results package
# =====================================================
results_json = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "constants": const,
    "source_trace": str(trace_path),
    "source_schema": schema_tag,
    "params": {
        "max_lag_steps": int(max_lag),
        "dt": dt_est,
        "n": int(len(vs)),
    },
    "stats": {
        "pearson_zero_lag": corr0,
        "best_lag_steps": best_lag,
        "best_corr": best_corr,
    },
    "classification": classification,
    "discovery_notes": [
        note,
        "All results pertain to Tessaris algebra; no spacetime signaling is implied.",
    ],
}

out_path = Path("backend/modules/knowledge/I5_entropy_entanglement_corr.json")
out_path.write_text(json.dumps(results_json, indent=2))
print(f"✅ Correlation JSON -> {out_path}")

# =====================================================
# 📉 Figures
# =====================================================
plt.figure(figsize=(7, 5))
plt.scatter(vs, Sx, s=8, alpha=0.35, label="samples")
plt.xlabel("v_S / v_c")
plt.ylabel("S_CHSH (proxy)")
plt.title(f"I5 - v_S vs CHSH (r0={corr0:.2f}, lag={best_lag}, r*={best_corr:.2f})")
plt.grid(True, ls="--", alpha=0.4)
plt.tight_layout()
fig1 = "PAEV_I5_vS_vs_CHSH_scatter.png"
plt.savefig(fig1, dpi=200)
print(f"✅ Figure saved -> {fig1}")

plt.figure(figsize=(7, 4))
plt.plot(lags, corrs, "o-", lw=1.5)
plt.axhline(0.5, color="gray", linestyle="--", linewidth=1, label="threshold (r=0.5)")
plt.xlabel("Lag (steps)")
plt.ylabel("Pearson r")
plt.legend()
plt.title("I5 - Correlation vs lag (v_S -> S_CHSH)")
plt.grid(True, ls="--", alpha=0.4)
plt.tight_layout()
fig2 = "PAEV_I5_vS_vs_CHSH_lag.png"
plt.savefig(fig2, dpi=200)
print(f"✅ Figure saved -> {fig2}")

print(json.dumps(results_json, indent=2))
print("All outputs generated successfully.")
