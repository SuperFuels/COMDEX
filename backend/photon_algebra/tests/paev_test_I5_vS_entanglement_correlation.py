#!/usr/bin/env python3
"""
PAEV Test I5 - Entropy-Entanglement Coupling (v_S vs CHSH proxy)
Tessaris Photon Algebra Framework (Registry-aligned)

Reads E6Omega_vS_trace.json, computes correlation between v_S/v_c and S_CHSH,
and searches small positive lags for predictive coupling.

Artifacts:
  - backend/modules/knowledge/I5_entropy_entanglement_corr.json
  - PAEV_I5_vS_vs_CHSH_scatter.png
  - PAEV_I5_vS_vs_CHSH_lag.png
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

print("=== I5 - Entropy-Entanglement Coupling (v_S vs CHSH proxy) ===")

# =====================================================
# 🔹 Load Tessaris constants (auto-synced)
# =====================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)  # unified nonlinear coefficient

# =====================================================
# 📂 Source trace
# =====================================================
trace_path = Path("backend/modules/knowledge/E6Omega_vS_trace.json")
if not trace_path.exists():
    raise FileNotFoundError(
        "Missing E6Omega_vS_trace.json. Run E6-Ω v5 instrumented test first:\n"
        "  PYTHONPATH=. python backend/photon_algebra/tests/paev_test_E6Omega_v5_instrumented.py"
    )

data = json.loads(trace_path.read_text())
records = data.get("records", [])
if not records:
    raise RuntimeError("No records found in E6Omega_vS_trace.json")

vs = np.array([r["v_s_over_v_c"] for r in records], dtype=float)
Sx = np.array([r["S_CHSH"] for r in records], dtype=float)
t = np.array([r["t"] for r in records], dtype=float)

# =====================================================
# 🔍 Correlation functions
# =====================================================
def pearson(x, y):
    """Compute Pearson correlation coefficient safely."""
    x = np.asarray(x) - np.mean(x)
    y = np.asarray(y) - np.mean(y)
    denom = (np.std(x) * np.std(y) + 1e-12)
    return float(np.mean(x * y) / denom)

corr0 = pearson(vs, Sx)

# Small positive lag sweep: vs(t) -> Sx(t+lag)
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

# =====================================================
# 🧩 Results package
# =====================================================
results_json = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "constants": const,
    "source_trace": str(trace_path),
    "params": {
        "max_lag_steps": int(max_lag),
        "dt": float(np.median(np.diff(t))) if t.size > 1 else None,
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
# Scatter: v_S/v_c vs S_CHSH
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

# Correlation vs lag
plt.figure(figsize=(7, 4))
plt.plot(lags, corrs, "o-", lw=1.5)
plt.axhline(0.5, color="gray", linestyle="--", linewidth=1, label="significance threshold (r=0.5)")
plt.xlabel("Lag (steps)")
plt.ylabel("Pearson r")
plt.legend()
plt.title("I5 - Correlation vs lag (v_S -> S_CHSH)")
plt.grid(True, ls="--", alpha=0.4)
plt.tight_layout()
fig2 = "PAEV_I5_vS_vs_CHSH_lag.png"
plt.savefig(fig2, dpi=200)
print(f"✅ Figure saved -> {fig2}")

# =====================================================
# 🧾 Summary output
# =====================================================
print(json.dumps(results_json, indent=2))
print("All outputs generated successfully.")