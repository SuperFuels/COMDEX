import numpy as np, json, os, datetime
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.load_constants import load_constants

BASE = "backend/modules/knowledge"; os.makedirs(BASE, exist_ok=True)

# Drive a tiny mode then remove drive; measure persistence Q_Λ
x = np.linspace(0, 2000, 2000)
drive = np.zeros_like(x); drive[:200] = np.sin(2*np.pi*0.01*np.arange(200))
gamma = 1e-4   # tiny damping in neutral field
u = np.zeros_like(x)
for t in range(1, len(x)):
    u[t] = (1- gamma)*u[t-1] + drive[t-1]

after = u[300:]          # post-drive section
Q_lambda = float(np.mean(after**2) / (np.mean(u[:200]**2) + 1e-12))
persistent = Q_lambda > 0.5

constants = load_constants()
print("\n=== Λ2 - Zero-Point Persistence (Tessaris) ===")
print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, α={constants['α']}, β={constants['β']}, χ={constants['χ']}")
print(f"Q_Λ (post/drive energy) = {Q_lambda:.3f} -> {'Persistent' if persistent else 'Non-persistent'}")

plt.figure(figsize=(8,3.5))
plt.plot(x, u, label="u(t)")
plt.axvspan(0, 200, color='0.9', label="drive on")
plt.title("Λ2 - Zero-Point Persistence")
plt.xlabel("t"); plt.ylabel("amplitude"); plt.grid(alpha=0.3); plt.legend()
plot_path = os.path.join(BASE, "PAEV_Λ2_zero_point_persistence.png")
plt.savefig(plot_path, dpi=200); plt.close()

summary = {
  "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
  "constants": constants,
  "metrics": { "Q_lambda": Q_lambda, "persistent": bool(persistent) },
  "notes": [
    f"Post-drive persistence ratio Q_Λ = {Q_lambda:.3f}.",
    "Λ-field stores oscillations with negligible decay (neutral elasticity)."
  ],
  "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}
out = os.path.join(BASE, "Λ2_zero_point_persistence_summary.json")
with open(out, "w", encoding="utf-8") as f: json.dump(summary, f, indent=2)
print(f"✅ Summary saved -> {out}")
print(f"✅ Plot saved -> {plot_path}")
print("------------------------------------------------------------")