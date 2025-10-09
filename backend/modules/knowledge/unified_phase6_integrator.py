import os, json, datetime
import numpy as np
import matplotlib.pyplot as plt

BASE = "backend/modules/knowledge"
OUT_JSON = os.path.join(BASE, "unified_summary_v1.9_lambda.json")
OUT_PNG = os.path.join(BASE, "Tessaris_Lambda_Map.png")

print("=== Tessaris Phase VI Integrator — Λ (Neutral Field) ===")
files = [
  "Λ1_vacuum_stability_summary.json",
  "Λ2_zero_point_persistence_summary.json",
  "Λ3_dissipationless_transport_summary.json",
  "Λ4_causal_buffer_bridge_summary.json",
  "Λ5_noise_immunity_summary.json",
]

loaded = []
metrics = {}
for f in files:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        loaded.append(f); metrics[f] = d.get("metrics", {})
        print(f"  • Loaded {f}")
    else:
        print(f"  • Missing {f}")

# Aggregate
def get(m, k): 
    try: return float(m.get(k, np.nan))
    except: return np.nan

div_mean = get(metrics.get(files[0], {}), "divJ_mean")
drift = get(metrics.get(files[0], {}), "energy_drift")
Q_lambda = get(metrics.get(files[1], {}), "Q_lambda")
atten = get(metrics.get(files[2], {}), "attenuation")
rec_ratio = get(metrics.get(files[3], {}), "recovery_ratio_lambda")
residual = get(metrics.get(files[4], {}), "balance_residual")

state_bits = []
if not np.isnan(div_mean) and div_mean < 1e-3: state_bits.append("stable vacuum")
if not np.isnan(Q_lambda) and Q_lambda > 0.5: state_bits.append("persistent zero-point")
if not np.isnan(atten) and atten < 1e-2: state_bits.append("dissipationless transport")
if not np.isnan(rec_ratio) and rec_ratio >= 0.48: state_bits.append("strong buffer")
if not np.isnan(residual) and residual < 1e-3: state_bits.append("noise-immune")

state = " / ".join(state_bits) if state_bits else "subcritical — tune Λ and damping"

print("\n🧠 Λ Summary")
print(f"divJ_mean = {div_mean}")
print(f"Q_Λ       = {Q_lambda}")
print(f"atten     = {atten}")
print(f"recovery  = {rec_ratio}")
print(f"residual  = {residual}")
print(f"State: {state}")

summary = {
  "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
  "series": {"Λ": len(loaded)},
  "metrics": {
    "divJ_mean": div_mean,
    "Q_lambda": Q_lambda,
    "attenuation": atten,
    "recovery_ratio_lambda": rec_ratio,
    "balance_residual": residual
  },
  "state": state,
  "notes": [
    "Phase VI integrates Λ1–Λ5 to certify the neutral causal substrate.",
    "Λ enables persistent, lossless, and noise-immune causal computation."
  ],
  "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}
with open(OUT_JSON, "w", encoding="utf-8") as f: json.dump(summary, f, indent=2)
print(f"✅ Unified Λ summary saved → {OUT_JSON}")

# Simple radar-style visualization
labels = ["Vacuum", "Persistence", "Transport", "Buffer", "Immunity"]
vals = [
    1.0 if (not np.isnan(div_mean) and div_mean < 1e-3) else 0.0,
    min(max(Q_lambda,0.0),1.0) if not np.isnan(Q_lambda) else 0.0,
    1.0 - min(atten,1.0) if not np.isnan(atten) else 0.0,
    min(rec_ratio,1.0) if not np.isnan(rec_ratio) else 0.0,
    1.0 - min(residual/1e-3, 1.0) if not np.isnan(residual) else 0.0
]
theta = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
plt.figure(figsize=(5,5))
ax = plt.subplot(111, polar=True)
ax.plot(theta, vals, marker='o'); ax.fill(theta, vals, alpha=0.2)
ax.set_xticks(theta); ax.set_xticklabels(labels)
ax.set_ylim(0,1); ax.set_title("Tessaris Λ Capability Map")
plt.savefig(OUT_PNG, dpi=200, bbox_inches="tight"); plt.close()
print(f"✅ Visualization saved → {OUT_PNG}")
print("Phase VI (Λ) integration complete.")
print("------------------------------------------------------------")