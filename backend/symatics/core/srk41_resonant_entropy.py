# -*- coding: utf-8 -*-
# File: backend/symatics/core/srk41_resonant_entropy.py
"""
SRK-4.1 Resonant-Entropy Coupling
─────────────────────────────────────────────
Tessaris Core v1.1 — Λ↔ψ↔⟲R↔S Feedback Loop

Extends SRK-4 Resonant Coupling (v1.1) with direct modulation:
    γS' = γS * (1 − R)
    λt' = λt * (1 − 0.5 R)

Purpose
-------
Allows high-resonance states to dynamically reduce entropy damping,
achieving self-stabilizing coherent modes (“resonant intelligence”).

Diagnostics
-----------
Adds `resonant_entropy_feedback` and `stability_trend` to kernel diagnostics.
Now also emits Codex trace telemetry: `resonant_entropy_feedback`.
"""

from statistics import mean


class SRK41ResonantEntropy:
    """SRK-4.1 Resonant-Entropy Coupling (Λ↔ψ↔⟲R↔S)"""

    name = "SRK-4.1 Resonant-Entropy Coupling"
    version = "1.1"

    def __init__(self):
        self.history = []
        self.stability_trend = []
        self.last_feedback = {"passed": False}
        self.last_resonant_entropy_feedback = self.last_feedback

    # ──────────────────────────────────────────────
    # Integration hook
    # ──────────────────────────────────────────────
    def integrate(self, kernel):
        print(f"[SRK-4.1] Loaded {self.name} (v{self.version})")
        kernel.resonant_entropy = self
        if not hasattr(kernel, "extensions"):
            kernel.extensions = []
        if self not in kernel.extensions:
            kernel.extensions.append(self)

    # ──────────────────────────────────────────────
    # Coupled Λ↔ψ↔⟲R↔S feedback
    # ──────────────────────────────────────────────
    def feedback(self, kernel, feedback: dict = None):
        try:
            srk3 = next(
                (e for e in getattr(kernel, "extensions", [])
                 if "SRK-3" in getattr(e, "name", "")),
                None
            )
            srk4 = next(
                (e for e in getattr(kernel, "extensions", [])
                 if getattr(e, "name", "").startswith("SRK-4 ")
                 and "4.1" not in getattr(e, "name", "")),
                None
            )
            if not srk3 or not srk4:
                raise ValueError("SRK-3 or SRK-4 not integrated")

            # Extract resonance & entropy coupling parameters
            R = getattr(srk4, "last_resonance_feedback", {}).get("R", 0.0)
            gamma_S = getattr(srk3.entropy_field, "gamma_S", 0.05)
            lambda_t = getattr(kernel, "lambda_t", 1.0)

            # Coupled modulation
            gamma_S_new = gamma_S * (1.0 - R)
            lambda_new = lambda_t * (1.0 - 0.5 * R)

            # Apply back into kernel + entropy field
            srk3.entropy_field.gamma_S = gamma_S_new
            kernel.lambda_t = lambda_new

            # Stability metric (avg λ + γ damping)
            stability = round((lambda_new + gamma_S_new) / 2.0, 6)
            self.history.append({
                "R": R,
                "gamma_S": gamma_S_new,
                "lambda_t": lambda_new,
                "stability": stability,
            })
            self.history = self.history[-100:]

            # Mean stability trend (rolling)
            trend = mean([h["stability"] for h in self.history[-10:]]) if self.history else 1.0
            self.stability_trend.append(trend)
            self.stability_trend = self.stability_trend[-50:]

            # Persistent feedback packet
            self.last_feedback = {
                "R": round(R, 6),
                "gamma_S": round(gamma_S_new, 6),
                "lambda_t": round(lambda_new, 6),
                "stability": round(stability, 6),
                "trend": round(trend, 6),
                "passed": True,
            }
            self.last_resonant_entropy_feedback = self.last_feedback

            # ──────────────────────────────────────────────
            # Codex trace event for symbolic telemetry
            # ──────────────────────────────────────────────
            if hasattr(kernel, "trace") and kernel.trace:
                try:
                    event_data = {
                        "R": self.last_feedback.get("R"),
                        "gamma_S": self.last_feedback.get("gamma_S"),
                        "lambda_t": self.last_feedback.get("lambda_t"),
                        "stability": self.last_feedback.get("stability"),
                        "trend": self.last_feedback.get("trend"),
                        "passed": self.last_feedback.get("passed"),
                    }

                    if hasattr(kernel.trace, "log_event"):
                        kernel.trace.log_event("resonant_entropy_feedback", event_data)
                    elif hasattr(kernel.trace, "emit"):
                        kernel.trace.emit("resonant_entropy_feedback", event_data)
                    elif hasattr(kernel.trace, "record"):
                        # ✅ Corrected CodexTrace.record() signature
                        if hasattr(kernel.trace, "record"):
                            kernel.trace.record("resonant_entropy_feedback", {}, event_data)
                    else:
                        print("[SRK-4.1] No compatible trace method found.")

                except Exception as trace_err:
                    print(f"[SRK-4.1] Trace logging failed: {trace_err}")

        except Exception as e:
            self.last_feedback = {"error": str(e), "passed": False}
            self.last_resonant_entropy_feedback = self.last_feedback
            print(f"[SRK-4.1] Resonant-Entropy feedback skipped: {e}")

    # ──────────────────────────────────────────────
    # Diagnostics (auto-refresh)
    # ──────────────────────────────────────────────
    def diagnostics(self, kernel=None):
        """
        Returns the latest resonant-entropy feedback snapshot.
        If no feedback has been run yet, triggers one refresh
        using the provided kernel context.
        """
        try:
            # Auto-refresh coupling if needed
            if kernel is not None and (not self.last_feedback.get("passed", False)):
                self.feedback(kernel)

            diag = {
                "resonant_entropy_feedback": self.last_feedback,
                "stability_trend": self.stability_trend[-5:],
            }

            # Include latest resonance snapshot for introspection
            if self.history:
                recent = self.history[-1]
                diag.update({
                    "R": round(recent.get("R", 0.0), 6),
                    "gamma_S": round(recent.get("gamma_S", 0.0), 6),
                    "lambda_t": round(recent.get("lambda_t", 0.0), 6),
                    "stability": round(recent.get("stability", 0.0), 6),
                })

            return diag

        except Exception as e:
            return {"error": str(e), "passed": False}