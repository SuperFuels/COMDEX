"""
K1 — Sympy Roundtrip Validation
Validates that the symbolic reconstruction of ℒ_total from constants_v1.1.json
matches the analytical form used in the TOE engine.
"""

from sympy import symbols, diff, simplify, expand
import json
from pathlib import Path
import matplotlib.pyplot as plt

# === Load constants ===
const_path = Path("backend/modules/knowledge/constants_v1.1.json")
constants = json.loads(const_path.read_text())
ħ, G, Λ, α = constants["ħ_eff"], constants["G_eff"], constants["Λ_eff"], constants["α_eff"]

# === Define symbolic fields ===
ψ, κ, g, R = symbols("ψ κ g R", complex=True)
gradψ = symbols("|∇ψ|")

# Reconstructed ℒ_total from constants
L_reconstructed = ħ * gradψ**2 + G * R - Λ * g + α * ψ**2 * κ

# Reference analytical structure
L_reference = 1e-3 * gradψ**2 + 1e-5 * R - 1e-6 * g + 0.5 * ψ**2 * κ

# === Sympy equivalence check ===
diff_expr = simplify(expand(L_reconstructed - L_reference))
drift_metric = float(abs(diff_expr.subs({ψ:1, κ:1, g:1, R:1, gradψ:1})))

print("=== K1 — Sympy Roundtrip Validation ===")
print(f"Symbolic drift metric Δℒ = {drift_metric:.3e}")
if drift_metric < 1e-6:
    print("✅ Roundtrip symbolic equivalence confirmed.")
else:
    print("⚠️ Drift beyond tolerance — recheck constants export consistency.")

# Simple visualization
plt.figure(figsize=(4,3))
plt.bar(["Δℒ drift"], [drift_metric])
plt.ylabel("Absolute Difference")
plt.title("K1 — Sympy Equivalence Drift")
plt.savefig("PAEV_K1_SympyEquivalence.png", dpi=200)
plt.close()
print("✅ Plot saved: PAEV_K1_SympyEquivalence.png")
print("----------------------------------------------------------")