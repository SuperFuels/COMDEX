import numpy as np, json, os, datetime
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.load_constants import load_constants

BASE = "backend/modules/knowledge"; os.makedirs(BASE, exist_ok=True)

# Neutral field with injected noise; test causal balance residual
x = np.linspace(-20, 20, 4096)
clean = np.cos(0.3*x)
noise = 0.05*np.random.default_rng(1).normal(size=x.size)
field = clean + noise
S = np.cumsum(field)/x.size
J = -np.gradient(S, x)
balance_residual = float(np.mean(np.abs(np.gradient(J, x) + np.gradient(S, x))))

immune = balance_residual < 1e-3

constants = load_constants()
print("\n=== Λ5 — Noise Immunity (Tessaris) ===")
print(f"Constants → ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, α={constants['α']}, β={constants['β']}, χ={constants['χ']}")
print(f"Balance residual = {balance_residual:.3e} → {'Immune' if immune else 'Sensitive'}")

plt.figure(figsize=(8,3.5))
plt.plot(x, field, label="field (noisy)")
plt.plot(x, J, label="J_info")
plt.title("Λ5 — Noise Immunity")
plt.xlabel("x"); plt.ylabel("amplitude"); plt.grid(alpha=0.3); plt.legend()
plot_path = os.path.join(BASE, "PAEV_Λ5_noise_immunity.png")
plt.savefig(plot_path, dpi=200); plt.close()

summary = {
  "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
  "constants": constants,
  "metrics": {
    "balance_residual": balance_residual,
    "immune": bool(immune),
    "threshold": 1e-3
  },
  "notes": [
    f"Residual ∥∇·J + ∂S/∂x∥ = {balance_residual:.3e}.",
    "Λ neutral medium suppresses noise-driven causal imbalance."
  ],
  "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}
out = os.path.join(BASE, "Λ5_noise_immunity_summary.json")
with open(out, "w", encoding="utf-8") as f: json.dump(summary, f, indent=2)
print(f"✅ Summary saved → {out}")
print(f"✅ Plot saved → {plot_path}")
print("------------------------------------------------------------")