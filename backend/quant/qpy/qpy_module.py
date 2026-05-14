import json, numpy as np
from datetime import datetime, timezone
from backend.quant.common.base_quant_module import BaseQuantModule

class QArray(np.ndarray):
    """
    Resonant symbolic array.
    Holds photon-level metadata: Φ_phase, ε_tolerance, κ_curvature, SQI_score.
    """

    def __new__(cls, input_array, Φ=0.0, ε=0.0, κ=0.0, SQI=1.0):
        obj = np.asarray(input_array).view(cls)
        obj.Φ = Φ
        obj.ε = ε
        obj.κ = κ
        obj.SQI = SQI
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self.Φ = getattr(obj, "Φ", 0.0)
        self.ε = getattr(obj, "ε", 0.0)
        self.κ = getattr(obj, "κ", 0.0)
        self.SQI = getattr(obj, "SQI", 1.0)

    # ──────────────────────────────────────────────
    def resonance_summary(self):
        return {"Φ": self.Φ, "ε": self.ε, "κ": self.κ, "SQI": self.SQI}

# ──────────────────────────────────────────────
# Core QPy module
# ──────────────────────────────────────────────

class QPyModule(BaseQuantModule):
    module_name = "QPy"
    version = "0.2"

    def __init__(self):
        super().__init__()
        self.log("QPy (QuantPy) initialized")

    # ──────────────────────────────────────────────
    # Symbolic operators
    # ──────────────────────────────────────────────

    def op_superpose(self, A: QArray, B: QArray):
        """⊕ Superposition operator"""
        res = (A + B) / 2
        Φ = (A.Φ + B.Φ) / 2
        ε = (A.ε + B.ε) / 2
        κ = np.std(res) * 0.01
        return QArray(res, Φ=Φ, ε=ε, κ=κ, SQI=(A.SQI + B.SQI) / 2)

    def op_measure(self, A: QArray):
        """μ Measurement operator"""
        val = float(np.mean(A))
        ε = np.abs(np.std(A))
        return {"μ_value": val, "ε": ε, "timestamp": datetime.now(timezone.utc).isoformat()}

    def op_resonate(self, A: QArray, gain=0.9):
        """⟲ Resonance feedback"""
        res = A * gain
        Φ = A.Φ + (1 - gain) * 0.05
        κ = np.var(res) * 0.001
        return QArray(res, Φ=Φ, ε=A.ε, κ=κ, SQI=A.SQI * gain)

    def op_entangle(self, A: QArray, B: QArray):
        """↔ Entanglement operator"""
        combined = np.tensordot(A, B, axes=0)
        Φ = (A.Φ + B.Φ) / 2
        ε = np.abs(A.ε - B.ε)
        κ = np.corrcoef(A.flatten(), B.flatten())[0, 1]
        return QArray(combined, Φ=Φ, ε=ε, κ=κ, SQI=(A.SQI + B.SQI) / 2)

    # ──────────────────────────────────────────────
    # Export & telemetry
    # ──────────────────────────────────────────────

    def export_state(self, A: QArray, path="backend/logs/qpy_state.json"):
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "Φ": A.Φ,
            "ε": A.ε,
            "κ": A.κ,
            "SQI": A.SQI,
            "shape": A.shape,
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        self.log("QPy state exported", state)
        return state

    # ──────────────────────────────────────────────
    # Run self-test
    # ──────────────────────────────────────────────

    def run_test(self):
        A = QArray(np.random.rand(4, 4), Φ=0.01, ε=0.001)
        B = QArray(np.random.rand(4, 4), Φ=0.02, ε=0.002)

        C = self.op_superpose(A, B)
        R = self.op_resonate(C)
        M = self.op_measure(R)
        E = self.op_entangle(A, B)
        self.export_state(E)

        report = {
            "ΔΦ": E.Φ - C.Φ,
            "Δε": E.ε - C.ε,
            "κ": E.κ,
            "μ": M["μ_value"],
            "status": "ok",
        }

        self.log("QPy test completed", report)
        return report