# backend/modules/theory_of_everything/toe_symbolic_export.py
"""
Symbolic TOE Functional Export
Builds a readable L_total from v1.1 constants.
"""

from pathlib import Path
import json

def export_symbolic_lagrangian():
    const_path = Path("backend/modules/knowledge/constants_v1.1.json")
    if not const_path.exists():
        raise FileNotFoundError("Run export_constants_v1_1.py first.")
    constants = json.loads(const_path.read_text())

    ħ = constants["ħ_eff"]
    G = constants["G_eff"]
    Λ = constants["Λ_eff"]
    α = constants["α_eff"]

    expression = f"""
    L_total = {ħ:.3e} * (|∇ψ|2)
             + {G:.3e} * (R)
             - {Λ:.3e} * (g)
             + {α:.3f} * (|ψ|2 κ)
    """
    out_path = Path("backend/modules/theory_of_everything/L_total_symbolic.txt")
    out_path.write_text(expression.strip())
    print(f"✅ Exported symbolic L_total to {out_path.resolve()}")

if __name__ == "__main__":
    export_symbolic_lagrangian()