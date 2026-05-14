# ============================================================
# Tessaris Symatics Reasoning Kernel
# SRK-7 - Harmonic-Resonance Synchronization Kernel (v0.1-alpha)
# ============================================================

import numpy as np

class SRK7HarmonicResonance:
    """
    SRK-7 synchronizes harmonic feedback (SRK-6) and resonance coupling (SRK-4/4.1),
    generating the Symatic Synchrony Scalar Ξ(t) for global phase coherence.
    """

    def __init__(self):
        self.name = "SRK-7 Harmonic-Resonance Synchronization"
        self.version = "v0.1-alpha"
        self.alpha_Xi = 0.04
        self.beta_Xi = 0.01
        self.threshold_Xi = 0.1
        self.last_feedback = None
        self.sync_trend = []
        self.phase_error_trend = []

    # --------------------------------------------------------
    # Integration Hook
    # --------------------------------------------------------
    def integrate(self, kernel):
        kernel.harmonic_resonance = self
        if not hasattr(kernel, "diagnostics_registry"):
            kernel.diagnostics_registry = {}
        kernel.diagnostics_registry["harmonic_resonance_feedback"] = self.get_last_feedback
        print(f"[SRK-7] Loaded {self.name} ({self.version})")

    # --------------------------------------------------------
    # Synchronization Feedback
    # --------------------------------------------------------
    def feedback(self, kernel):
        """Compute harmonic-resonance synchronization feedback."""
        try:
            if not hasattr(kernel, "harmonic_coupling") or not hasattr(kernel, "resonance_field"):
                raise AttributeError("Kernel missing SRK-4/6 integration")

            H_pkt = getattr(kernel.harmonic_coupling, "last_feedback", None)
            R_pkt = getattr(kernel.resonance_field, "resonance_feedback", None)
            if not H_pkt or not R_pkt:
                raise ValueError("Missing harmonic or resonance state")

            H = H_pkt.get("H", 0.0)
            R = R_pkt.get("R", 0.0)
            phase_error = abs(H - R)

            Xi = (H * R) / (1 + phase_error)
            Xi_prime = Xi * (1 - phase_error) + self.alpha_Xi * (H - R) ** 2

            passed = abs(Xi_prime - Xi) < self.threshold_Xi

            feedback_pkt = {
                "H": float(H),
                "R": float(R),
                "Ξ": float(Xi),
                "Ξ′": float(Xi_prime),
                "αΞ": self.alpha_Xi,
                "βΞ": self.beta_Xi,
                "phase_error": float(phase_error),
                "passed": passed,
            }

            self.last_feedback = feedback_pkt
            self.sync_trend.append(Xi)
            self.phase_error_trend.append(phase_error)

            # --- Safe CodexTrace Telemetry ---
            def _to_native(val):
                if isinstance(val, (np.generic,)):
                    return val.item()
                if isinstance(val, (np.ndarray, list, tuple)):
                    return [_to_native(v) for v in val]
                if isinstance(val, complex):
                    return {"real": val.real, "imag": val.imag}
                return val

            safe_pkt = {k: _to_native(v) for k, v in feedback_pkt.items()}

            if hasattr(kernel, "trace") and kernel.trace:
                try:
                    if hasattr(kernel.trace, "log_event"):
                        kernel.trace.log_event("harmonic_resonance_feedback", safe_pkt)
                    elif hasattr(kernel.trace, "emit"):
                        kernel.trace.emit("harmonic_resonance_feedback", safe_pkt)
                    elif hasattr(kernel.trace, "record"):
                        kernel.trace.record("harmonic_resonance_feedback", safe_pkt, result="ok")
                    else:
                        print("[SRK-7] No compatible trace method found.")
                except Exception as trace_err:
                    print(f"[SRK-7] Trace logging failed: {trace_err}")

            return safe_pkt

        except Exception as e:
            print(f"[SRK-7] Synchronization feedback failed: {e}")
            self.last_feedback = {"error": str(e), "passed": False}
            return self.last_feedback

    # --------------------------------------------------------
    # Diagnostics Accessors
    # --------------------------------------------------------
    def get_last_feedback(self):
        return self.last_feedback or {"status": "no_feedback"}

    def diagnostics(self, kernel=None):
        return {
            "harmonic_resonance_feedback": self.last_feedback or {},
            "sync_trend": self.sync_trend[-5:],
            "phase_error_trend": self.phase_error_trend[-5:]
        }


# ============================================================
# Factory for SRK Core Integration
# ============================================================
def SRKExtension():
    return SRK7HarmonicResonance()