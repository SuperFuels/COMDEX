# -*- coding: utf-8 -*-
# File: backend/symatics/core/srk4_resonance.py
"""
SRK-4 - Resonant Field Coupling Kernel (v1.1-stable)
─────────────────────────────────────────────────────────────
Tessaris Core v1.1 - Λ↔ψ↔⟲R Coupling Layer

Extends SRK-3 with ⟲-based resonance coupling between ψ and Λ,
enabling phase-locked feedback and resonance-coherence alignment.
"""
import numpy as np
from backend.symatics.entropy_field import EntropyFieldState


class SRKExtension:
    """SRK-4 module providing Λ↔ψ↔⟲R coupling and resonance diagnostics."""

    name = "SRK-4 Resonant Coupling"
    version = "1.1-stable"

    # ──────────────────────────────────────────────
    def integrate(self, kernel):
        # Ensure SRK-3 entropy field exists
        if not hasattr(kernel, "entropy_field"):
            kernel.entropy_field = EntropyFieldState()

        # Shared buffers + parameters
        self.resonance_window = []
        self.beta_R = 0.1  # base resonance gain
        self.last_resonance_feedback = {}

        # Bind to kernel
        kernel.resonance_field = self
        if not hasattr(kernel, "extensions"):
            kernel.extensions = []
        if self not in kernel.extensions:
            kernel.extensions.append(self)

        print(f"[SRK-4] Loaded {self.name} (v{self.version})")

    # ──────────────────────────────────────────────
    def _synthesize_psi_values(self, photonic_field) -> np.ndarray:
        """
        Generate ψ-sample vector when photonic field lacks explicit ψ values.
        Uses amplitude/phase to synthesize coherent samples for alignment.
        """
        amp = getattr(photonic_field, "amplitude", 1.0 + 0j)
        phi = float(getattr(photonic_field, "phase", 0.0))
        return np.array([
            amp * np.exp(1j * (phi - 0.5 * phi)),
            amp * np.exp(1j * phi),
            amp * np.exp(1j * (phi + 0.75 * phi)),
        ], dtype=complex)

    # ──────────────────────────────────────────────
    def feedback(self, kernel, feedback: dict = None):
        """
        Compute resonant feedback from ψ and Λ fields:
            R = phase alignment metric = ⟲(ψ, Λ)
        Updates λ damping with β_R-scaled coherence amplification.
        """
        try:
            psi_vals = getattr(kernel.photonic_field, "psi_values", None)
            if psi_vals is None:
                psi_vals = self._synthesize_psi_values(kernel.photonic_field)

            phase = np.angle(psi_vals)
            R = float(np.mean(np.cos(phase)))  # coherence phase alignment
            gamma_S = float(getattr(kernel.entropy_field, "gamma_S", 0.0))

            # Resonance-modulated λ update (bounded)
            kernel.lambda_t *= (1.0 - gamma_S + self.beta_R * R)
            kernel.lambda_t = max(0.0, min(kernel.lambda_t, 0.2))

            # Record resonance state
            pkt = {"R": R, "gamma_S": gamma_S, "lambda_t": kernel.lambda_t}
            self.resonance_window.append(pkt)
            self.resonance_window = self.resonance_window[-100:]
            self.last_resonance_feedback = dict(pkt, passed=True)

            # Optional shared feedback dict
            if feedback is not None:
                feedback.update({
                    "R": R,
                    "resonance_feedback": self.last_resonance_feedback,
                })

            # ──────────────────────────────────────────────
            # Codex trace emission (telemetry)
            # ──────────────────────────────────────────────
            if hasattr(kernel, "trace") and kernel.trace:
                try:
                    event_data = {
                        "R": R,
                        "lambda_t": kernel.lambda_t,
                        "gamma_S": gamma_S,
                        "passed": True,
                    }

                    # Fallback chain for compatibility
                    if hasattr(kernel.trace, "log_event"):
                        kernel.trace.log_event("resonance_feedback", event_data)
                    elif hasattr(kernel.trace, "emit"):
                        kernel.trace.emit("resonance_feedback", event_data)
                    elif hasattr(kernel.trace, "record"):
                        # Corrected signature for CodexTrace.record()
                        if hasattr(kernel.trace, "record"):
                            kernel.trace.record("resonance_feedback", {}, event_data)
                    else:
                        print("[SRK-4] No compatible trace method found.")

                except Exception as trace_err:
                    print(f"[SRK-4] Trace logging failed: {trace_err}")

        except Exception as e:
            print(f"[SRK-4] Resonance feedback skipped: {e}")
            self.last_resonance_feedback = {"error": str(e), "passed": False}

    # ──────────────────────────────────────────────
    def diagnostics(self, kernel) -> dict:
        """Return resonance coupling diagnostics."""
        try:
            return {
                "resonance_feedback": self.last_resonance_feedback,
                "resonance_trend": self.resonance_window[-5:],
                "samples": len(self.resonance_window),
                "last_R": round(self.last_resonance_feedback.get("R", 0.0), 6),
                "lambda_t": round(getattr(kernel, "lambda_t", 0.0), 6),
                "gamma_S": round(getattr(kernel.entropy_field, "gamma_S", 0.0), 6),
                "beta_R": self.beta_R,
            }
        except Exception as e:
            return {"error": str(e)}


# ──────────────────────────────────────────────
# [Manifest Tag] SRK-4.x family finalized - ready for SRK-5 Coherent Field Layer
# ──────────────────────────────────────────────