# -*- coding: utf-8 -*-
"""
SRK-3 - Field Entropy Kernel (v1.3 Stable)
─────────────────────────────────────────────
Extends SRK-1/2 with entropy-based damping,
coherence-entropy diagnostics, and CodexTrace integration.
"""

from backend.symatics.entropy_field import EntropyFieldState


class SRKExtension:
    """SRK-3 module providing Λ↔ψ↔S coupling and diagnostics."""

    name = "SRK-3 Entropy Field"
    version = "1.3"

    # ──────────────────────────────────────────────
    # Called once at kernel startup
    # ──────────────────────────────────────────────
    def integrate(self, kernel):
        # attach the entropy field
        self.entropy_field = EntropyFieldState()
        self.last_entropy_feedback = {}
        self.entropy_trend = []

        # bind to kernel
        kernel.entropy_field = self.entropy_field
        kernel.coherence_window = []

        # ensure this extension is registered
        if not hasattr(kernel, "extensions"):
            kernel.extensions = []
        if self not in kernel.extensions:
            kernel.extensions.append(self)

        print(f"[SRK-3] Loaded {self.name} (v{self.version})")

    # ──────────────────────────────────────────────
    # Called each evaluation cycle
    # ──────────────────────────────────────────────
    def feedback(self, kernel, feedback: dict = None):
        """
        Executes entropy feedback update for the current photonic field snapshot.
        Tracks entropy trend (S, γS, ∇S) and applies λ(t) damping accordingly.
        """
        try:
            # update entropy state and apply damping
            self.entropy_field.update(kernel.photonic_field, feedback)
            kernel.lambda_t *= (1.0 - self.entropy_field.gamma_S)

            # maintain coherence window (λ vs ψ density vs entropy)
            kernel.coherence_window.append({
                "psi_density": getattr(kernel.photonic_field, "psi_density", 0.0),
                "lambda_t": kernel.lambda_t,
                "S": self.entropy_field.S,
            })
            kernel.coherence_window = kernel.coherence_window[-100:]

            # store feedback record for diagnostics
            self.last_entropy_feedback = {
                "S": self.entropy_field.S,
                "gamma_S": self.entropy_field.gamma_S,
                "passed": True,
            }

            # record entropy trend (last 50 samples)
            self.entropy_trend.append({
                "S": self.entropy_field.S,
                "gamma_S": self.entropy_field.gamma_S,
                "gradS": (
                    self.entropy_field.history[-1]["gradS"]
                    if self.entropy_field.history else 0.0
                ),
            })
            self.entropy_trend = self.entropy_trend[-50:]

        except Exception as e:
            print(f"[SRK-3] Entropy feedback skipped: {e}")
            self.last_entropy_feedback = {"error": str(e), "passed": False}

    # ──────────────────────────────────────────────
    # Contributes to diagnostics()
    # ──────────────────────────────────────────────
    def diagnostics(self, kernel) -> dict:
        """
        Returns entropy-related diagnostics, including current entropy S,
        damping γS, number of coherence samples, recent entropy trend, and
        last feedback packet (CodexTrace-compatible).
        """
        try:
            return {
                "S": round(getattr(self.entropy_field, "S", 0.0), 6),
                "gamma_S": round(getattr(self.entropy_field, "gamma_S", 0.0), 6),
                "samples": len(getattr(kernel, "coherence_window", [])),
                "entropy_trend": self.entropy_trend[-5:],
                "entropy_feedback": self.last_entropy_feedback,
            }
        except Exception as e:
            return {"error": str(e)}