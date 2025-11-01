"""
Tessaris RQC - Operator Registry
───────────────────────────────────────────────
Central registry for photonic runtime operators.
Unifies ⊕ (superpose), ⟲ (resonate), and ↔ (entangle)
for dynamic dispatch and telemetry coupling.
"""

from backend.RQC.src.photon_runtime.operations.superpose import superpose
from backend.RQC.src.photon_runtime.operations.resonate import resonate
from backend.RQC.src.photon_runtime.operations.entangle import entangle

OP_REGISTRY = {
    "superpose": superpose,
    "resonate": resonate,
    "entangle": entangle,
}

def list_operators():
    """Return available operator names."""
    return list(OP_REGISTRY.keys())

def get_operator(name: str):
    """Return operator function by name."""
    return OP_REGISTRY.get(name)

if __name__ == "__main__":
    print("Tessaris RQC Operator Registry")
    for op in list_operators():
        print(f"  ⟶ {op}")