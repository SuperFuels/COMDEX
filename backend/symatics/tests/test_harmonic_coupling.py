# ============================================================
# Tessaris Symatics Reasoning Kernel — SRK-6 Test Suite
# ============================================================
# Purpose:
# Validate SRK-6 Harmonic Coupling feedback, diagnostics,
# and CodexTrace integration using synthetic Φ(t) coherence data.
# ============================================================

import math
import json
import numpy as np

from backend.symatics.core.srk_kernel import SymaticsReasoningKernel as SymaticsKernel
from backend.symatics.core.srk6_harmonic_coupling import SRKExtension


class DummyKernel:
    """Lightweight kernel mock to simulate SRK core."""
    def __init__(self):
        self.trace = CodexTrace()
        self.coherent_field = {
            "trend": [0.4 + 0.05 * math.sin(2 * math.pi * i / 10) for i in range(50)]
        }
        self.diagnostics_registry = {}
        self.extensions = []


import numpy as np
import json

def to_native(obj):
    """Recursively convert NumPy and non-serializable types to Python-native."""
    if isinstance(obj, (np.generic,)):
        return obj.item()
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]
    return obj

def run_harmonic_feedback_test():
    print("\n=== Running SRK-6 Harmonic Coupling Test ===")

    from backend.symatics.core.srk_kernel import SymaticsReasoningKernel as SymaticsKernel
    from backend.symatics.core.srk6_harmonic_coupling import SRKExtension

    kernel = SymaticsKernel()
    srk6 = SRKExtension()
    srk6.integrate(kernel)

    # Mock coherent_field
    kernel.coherent_field = {"trend": np.linspace(0.3, 0.4, 20).tolist()}

    result = srk6.feedback(kernel)
    print("\n[Feedback Packet]")
    print(json.dumps(to_native(result), indent=2))

    diag = kernel.diagnostics()
    print("\n[Diagnostics Snapshot]")

    def safe_json(obj):
        """Convert NumPy and complex types into JSON-serializable primitives."""
        if isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        if isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return str(obj)

    print(json.dumps(to_native(diag), indent=2, default=safe_json))

    print("\n✅ SRK-6 harmonic feedback test passed.")

if __name__ == "__main__":
    run_harmonic_feedback_test()