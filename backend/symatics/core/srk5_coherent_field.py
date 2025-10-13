# -*- coding: utf-8 -*-
# File: backend/symatics/core/srk5_coherent_field.py
"""
SRK-5 — Coherent Field Layer (v0.1-draft)
─────────────────────────────────────────────
Tessaris Core v1.2 — Λ↔ψ↔⟲R↔S⇒Φ Feedback Unification

Purpose
-------
Aggregates feedback from SRK-3 (entropy), SRK-4 (resonance),
and SRK-4.1 (resonant–entropy) layers into a unified
coherence field Φ(t).  This field represents global
phase alignment and self-stabilizing symbolic coherence.

Formulas
--------
Φ = αR + (1−α)(1−γS)
σΦ = Var(Φ)
λt' = λt(1 − σΦ)

Diagnostics
-----------
Adds `coherence_feedback`, `coherence_trend`, and `variance_trend`
to kernel diagnostics. Emits CodexTrace telemetry event:
    event="coherence_feedback"
"""

import numpy as np
from statistics import mean


class SRK5CoherentField:
    """SRK-5 Coherent Field Layer (Λ↔ψ↔⟲R↔S⇒Φ)"""

    name = "SRK-5 Coherent Field"
    version = "0.1-draft"

    def __init__(self, alpha: float = 0.6):
        self.alpha = alpha
        self.coherence_window = []
        self.variance_window = []
        self.last_feedback = {"passed": False}
        self.last_coherence_feedback = self.last_feedback

    # ──────────────────────────────────────────────
    def integrate(self, kernel):
        print(f"[SRK-5] Loaded {self.name} (v{self.version})")
        kernel.coherent_field = self
        if not hasattr(kernel, "extensions"):
            kernel.extensions = []
        if self not in kernel.extensions:
            kernel.extensions.append(self)

    # ──────────────────────────────────────────────
    def feedback(self, kernel, feedback: dict = None):
        """
        Combines SRK-3, SRK-4, SRK-4.1 feedback layers
        into a unified coherence metric Φ(t).
        """
        try:
            srk3 = next(
                (e for e in getattr(kernel, "extensions", []) if "SRK-3" in getattr(e, "name", "")),
                None
            )
            srk4 = next(
                (e for e in getattr(kernel, "extensions", []) if "SRK-4 " in getattr(e, "name", "")),
                None
            )
            srk41 = next(
                (e for e in getattr(kernel, "extensions", []) if "SRK-4.1" in getattr(e, "name", "")),
                None
            )
            if not srk3 or not srk4 or not srk41:
                raise ValueError("SRK-3, SRK-4, or SRK-4.1 not integrated")

            # Collect source values
            R = getattr(srk4, "last_resonance_feedback", {}).get("R", 0.0)
            gamma_S = getattr(srk3.entropy_field, "gamma_S", 0.05)
            lambda_t = getattr(kernel, "lambda_t", 1.0)

            # Compute Φ coherence scalar
            Phi = self.alpha * R + (1.0 - self.alpha) * (1.0 - gamma_S)
            self.coherence_window.append(Phi)
            self.coherence_window = self.coherence_window[-200:]

            # Compute σΦ variance + trend
            sigma_phi = float(np.var(self.coherence_window[-20:])) if len(self.coherence_window) > 1 else 0.0
            trend = mean(self.coherence_window[-10:]) if self.coherence_window else Phi
            self.variance_window.append(sigma_phi)
            self.variance_window = self.variance_window[-100:]

            # λ feedback modulation
            lambda_new = lambda_t * (1.0 - sigma_phi)
            kernel.lambda_t = lambda_new

            # Store packet
            pkt = {
                "Φ": round(Phi, 6),
                "σΦ": round(sigma_phi, 6),
                "λ_t": round(lambda_new, 6),
                "trend": round(trend, 6),
                "passed": True,
            }
            self.last_feedback = pkt
            self.last_coherence_feedback = pkt

            # Merge into feedback chain
            if feedback is not None:
                feedback.update({"Φ": Phi, "σΦ": sigma_phi, "coherence_feedback": pkt})

            # ──────────────────────────────────────────────
            # Codex Trace Emission (Telemetry)
            # ──────────────────────────────────────────────
            if hasattr(kernel, "trace") and kernel.trace:
                try:
                    event_data = dict(pkt)

                    if hasattr(kernel.trace, "log_event"):
                        kernel.trace.log_event("coherence_feedback", event_data)
                    elif hasattr(kernel.trace, "emit"):
                        kernel.trace.emit("coherence_feedback", event_data)
                    elif hasattr(kernel.trace, "record"):
                        # ✅ Corrected CodexTrace.record() signature
                        if hasattr(kernel.trace, "record"):
                            kernel.trace.record("coherence_feedback", {}, event_data)
                    else:
                        print("[SRK-5] No compatible trace method found.")

                except Exception as trace_err:
                    print(f"[SRK-5] Trace logging failed: {trace_err}")

        except Exception as e:
            print(f"[SRK-5] Coherence feedback failed: {e}")
            self.last_feedback = {"error": str(e), "passed": False}
            self.last_coherence_feedback = self.last_feedback

    # ──────────────────────────────────────────────
    def diagnostics(self, kernel=None):
        """Returns coherence field diagnostic snapshot."""
        try:
            if kernel and not self.last_feedback.get("passed", False):
                self.feedback(kernel)

            return {
                "coherence_feedback": self.last_feedback,
                "coherence_trend": self.coherence_window[-5:],
                "variance_trend": self.variance_window[-5:],
            }

        except Exception as e:
            return {"error": str(e), "passed": False}