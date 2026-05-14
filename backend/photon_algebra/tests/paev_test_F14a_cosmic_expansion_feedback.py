"""
F14a - Cosmic Expansion from Λ_eff (Tessaris mapping)
-----------------------------------------------------
Goal:
  Map the Tessaris vacuum-energy proxy Λ_eff to a toy FRW scale factor a(t)
  and verify late-time acceleration (ä > 0).

Strategy:
  * Try to read Λ_final from F13b_dynamic_vacuum_feedback.json; fallback to constants Λ.
  * Integrate:   H(t) = sqrt(max( (Λ_eff/3) + 8πG/3 * ρ_m(a), 0 ))
    with ρ_m(a) = ρ0 / a^3 (dust-like), ρ0 small; ȧ = H a.
  * Report acceleration sign on the tail window; save plots + JSON.

Outputs:
  * PAEV_F14a_ScaleFactor.png
  * PAEV_F14a_Hubble.png
  * backend/modules/knowledge/F14a_cosmic_expansion_feedback.json
"""
import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path
# constants
CANDIDATES = [
    Path("backend/modules/knowledge/constants_v1.2.json"),
    Path("backend/modules/knowledge/constants_v1.1.json"),
    Path("backend/modules/knowledge/constants_v1.0.json"),
]
for p in CANDIDATES:
    if p.exists():
        constants = json.loads(p.read_text()); break
else:
    constants = {}
ħ  = float(constants.get("ħ", 1e-3))
G  = float(constants.get("G", 1e-5))
Λ0 = float(constants.get("Λ", 1e-6))

# prefer Λ from F13b
Λ_eff = Λ0
f13b_path = Path("backend/modules/knowledge/F13b_dynamic_vacuum_feedback.json")
if f13b_path.exists():
    try:
        Λ_eff = float(json.loads(f13b_path.read_text())["metrics"]["Λ_final"])
    except Exception:
        pass

# toy FRW integration
T, dt = 4000, 0.004
t = np.arange(T)*dt
a  = np.zeros_like(t); a[0] = 1.0
H  = np.zeros_like(t)
ρ0 = 0.02  # small dust energy in Tessaris units

for k in range(1, T):
    ρm = ρ0/(a[k-1]**3)
    H[k-1] = np.sqrt(max((Λ_eff/3.0) + (8*np.pi*G/3.0)*ρm, 0.0))
    a[k] = a[k-1] + dt*H[k-1]*a[k-1]
H[-1] = H[-2]

# acceleration proxy (finite diff)
a_ddot = np.gradient(np.gradient(a, dt), dt)
tail = max(100, T//10)
acc_mean = float(np.mean(a_ddot[-tail:]))
acc_pos  = acc_mean > 0

classification = "✅ Accelerating expansion from Λ_eff" if acc_pos else "❌ No acceleration (tune Λ_eff/ρ0)"

print("=== F14a - Cosmic Expansion from Λ_eff ===")
print(f"Λ_eff={Λ_eff:.6f}, G={G:.1e}, ρ0={ρ0:.3f}")
print(f"a(T)={a[-1]:.3f},  ⟨ä⟩_tail={acc_mean:.3e}")
print(f"-> {classification}")

# plots
out = Path(".")
plt.figure(figsize=(10,4))
plt.plot(t, a, lw=1.8)
plt.title("F14a - Scale Factor a(t)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.tight_layout(); plt.savefig(out/"PAEV_F14a_ScaleFactor.png", dpi=160)

plt.figure(figsize=(10,4))
plt.plot(t, H, lw=1.6)
plt.title("F14a - Hubble Proxy H(t)")
plt.xlabel("time"); plt.ylabel("H(t)")
plt.tight_layout(); plt.savefig(out/"PAEV_F14a_Hubble.png", dpi=160)

print("✅ Plots saved:\n  - PAEV_F14a_ScaleFactor.png\n  - PAEV_F14a_Hubble.png")

# knowledge card
summary = {
    "Λ_eff": Λ_eff, "G": G, "ħ": ħ,
    "timing": {"steps": T, "dt": dt},
    "metrics": {"a_final": float(a[-1]), "acc_tail_mean": acc_mean},
    "classification": classification,
    "files": {"scale_plot": "PAEV_F14a_ScaleFactor.png", "hubble_plot": "PAEV_F14a_Hubble.png"},
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge/F14a_cosmic_expansion_feedback.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved -> backend/modules/knowledge/F14a_cosmic_expansion_feedback.json")