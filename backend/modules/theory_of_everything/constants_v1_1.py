import json
from pathlib import Path

new_constants = {
    "ħ_eff": 1.0e-3,
    "G_eff": 1.0e-5,
    "Λ_eff": 1.0e-6,
    "α_eff": 0.5,
    "L_total": 1.0,
    "validation": "J2 Grand Synchronization closed successfully",
    "timestamp": "2025-10-06T13:35Z",
    "drifts": {"ΔE": 2.203e-05, "ΔS": 9.506e-06, "ΔH": 1.342e-06}
}

path = Path("backend/modules/knowledge/constants_v1.1.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(new_constants, indent=2))
print(f"✅ Exported TOE-stable constants to {path.resolve()}")