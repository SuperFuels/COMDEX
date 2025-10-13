# ============================================================
# Tessaris Symatics Reasoning Kernel
# SRK-6 — Harmonic Coupling Kernel (v0.1-pre)
# ============================================================

import numpy as np


class SRK6HarmonicCoupling:
    """
    SRK-6 couples temporal coherence (Φ) with frequency-domain harmonics (Ψ),
    creating a bidirectional feedback bridge between time and frequency spaces.

    Φ(t) ↔ Ψ(f)
    """

    def __init__(self):
        self.name = "SRK-6 Harmonic Coupling"
        self.version = "v0.1-pre"
        self.last_feedback = None
        self.harmonic_trend = []
        self.spectral_variance_trend = []
        self.alpha_H = 0.05     # harmonic gain coefficient
        self.beta_H = 0.02      # harmonic damping coefficient
        self.threshold_H = 0.2  # acceptable deviation from H=1

    # --------------------------------------------------------
    # Integration hook for SRK core
    # --------------------------------------------------------
    def integrate(self, kernel):
        kernel.harmonic_coupling = self
        if not hasattr(kernel, "diagnostics_registry"):
            kernel.diagnostics_registry = {}
        kernel.diagnostics_registry["harmonic_feedback"] = self.get_last_feedback
        print(f"[SRK-6] Loaded {self.name} ({self.version})")

    # --------------------------------------------------------
    # Harmonic Analysis (Fourier-domain)
    # --------------------------------------------------------
    def analyze_harmonics(self, phi_series, dt=1.0):
        """Compute harmonic spectrum Ψ(f) and metrics."""
        if len(phi_series) < 2:
            return None

        psi = np.fft.fft(phi_series - np.mean(phi_series))
        freq = np.fft.fftfreq(len(phi_series), d=dt)

        power_spectrum = np.abs(psi) ** 2
        spectral_density = np.sum(power_spectrum)
        time_density = np.sum(np.array(phi_series) ** 2)
        H = spectral_density / (time_density + 1e-12)

        sigma_H = np.var(power_spectrum / np.max(power_spectrum))
        return H, sigma_H, freq, power_spectrum

    # --------------------------------------------------------
    # Harmonic Feedback
    # --------------------------------------------------------
    def feedback(self, kernel):
        """Perform harmonic coupling feedback and emit Codex telemetry."""
        try:
            if not hasattr(kernel, "coherent_field"):
                raise AttributeError("Kernel missing coherent_field (SRK-5)")

            phi_series = kernel.coherent_field.get("trend", [])
            if not phi_series:
                raise ValueError("Empty Φ series")

            # --- Harmonic computation ---
            result = self.analyze_harmonics(phi_series)
            if result is None:
                raise ValueError("Harmonic analysis failed")
            H, sigma_H, freq, P = result

            alpha_H, beta_H = self.alpha_H, self.beta_H
            phi_correction = (1 + alpha_H * H - beta_H * sigma_H)
            phi_avg = np.mean(phi_series)
            phi_prime = phi_avg * phi_correction

            feedback_pkt = {
                "H": float(H),
                "σ_H": float(sigma_H),
                "Φ′": float(phi_prime),
                "α_H": alpha_H,
                "β_H": beta_H,
                "passed": abs(H - 1) < self.threshold_H,
            }

            self.last_feedback = feedback_pkt
            self.harmonic_trend.append(H)
            self.spectral_variance_trend.append(sigma_H)

            # ---------------------------------------------
            # Codex Trace Telemetry (Safe + Compatible)
            # ---------------------------------------------
            def _to_native(val):
                """Convert NumPy, complex, and exotic types to native Python types."""
                if isinstance(val, (np.generic,)):
                    return val.item()
                if isinstance(val, (np.ndarray, list, tuple)):
                    return [_to_native(v) for v in val]
                if isinstance(val, complex):
                    return {"real": val.real, "imag": val.imag}
                return val

            # Normalize feedback for safety
            safe_pkt = {k: _to_native(v) for k, v in feedback_pkt.items()}

            if hasattr(kernel, "trace") and kernel.trace:
                try:
                    if hasattr(kernel.trace, "log_event"):
                        kernel.trace.log_event("harmonic_feedback", safe_pkt)
                    elif hasattr(kernel.trace, "emit"):
                        kernel.trace.emit("harmonic_feedback", safe_pkt)
                    elif hasattr(kernel.trace, "record"):
                        # CodexTrace.record expects (glyph, context, result)
                        kernel.trace.record("harmonic_feedback", safe_pkt, result="ok")
                    else:
                        print("[SRK-6] No compatible trace method found.")
                except Exception as trace_err:
                    print(f"[SRK-6] Trace logging failed: {trace_err}")

            # Ensure JSON-safe before returning
            return {k: _to_native(v) for k, v in safe_pkt.items()}

        except Exception as e:
            print(f"[SRK-6] Harmonic feedback failed: {e}")
            self.last_feedback = {"error": str(e), "passed": False}
            return self.last_feedback

    # --------------------------------------------------------
    # Diagnostics Accessor
    # --------------------------------------------------------
    def get_last_feedback(self):
        return self.last_feedback or {"status": "no_feedback"}

    # --------------------------------------------------------
    # Diagnostics Report
    # --------------------------------------------------------
    def diagnostics(self, kernel=None):
        """Expose latest harmonic feedback and trends for SRK diagnostics."""
        return {
            "harmonic_feedback": self.last_feedback or {},
            "harmonic_trend": self.harmonic_trend[-5:],
            "spectral_variance_trend": self.spectral_variance_trend[-5:]
        }


# ============================================================
# Factory for SRK Core Integration
# ============================================================

def SRKExtension():
    return SRK6HarmonicCoupling()