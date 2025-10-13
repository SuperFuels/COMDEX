# -*- coding: utf-8 -*-
# File: backend/symatics/core/srk_kernel.py
"""
Symatics Reasoning Kernel (SRK-1)
─────────────────────────────────────────────
Tessaris Core v1.0 — Λ-Field Decoherence Interface

Extends v0.9 with:
  • Dynamic λ(t) decoherence tracking and ρ(t) entanglement correlation
  • Field export to Symatics Rulebook for telemetry use
  • Adaptive λ update based on ΔE stability feedback
  • Expanded diagnostics block "decoherence_field"
  • Full backward compatibility with v0.9
"""

import cmath
import math
from datetime import datetime, timezone
from statistics import mean

from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
from backend.symatics import symatics_rulebook as SR
from backend.core.registry_bridge import registry_bridge
from backend.modules.codex.codex_trace import CodexTrace
from backend.symatics.photonic_field import PhotonFieldState  # ← uses your photonic_field.py
from importlib import import_module

try:
    from backend.symatics.sym_tactics import SymTactics
except ImportError:
    SymTactics = None


class SymaticsReasoningKernel:
    """SRK-1 (v1.0) — tensor-aware quantum kernel with Λ-Field decoherence loop."""

    def __init__(self, auto_stabilize: bool = True, decoherence_lambda: float = 0.03, alpha: float = 0.02):
        self.registry = registry_bridge
        # CodexTrace may be a class or factory; handle both safely
        try:
            self.trace = CodexTrace()
        except Exception:
            self.trace = None

        self.dispatch = evaluate_symatics_expr
        self.auto_stabilize = auto_stabilize

        # λ(t) parameters
        self.lambda_t = float(decoherence_lambda)
        self.alpha = float(alpha)  # learning rate for λ update

        # Feedback + quantum memory
        self.law_signatures = []
        self.last_energy_balance = {}
        self.field_feedback = {"field_intensity": 0.0, "psi_density": 0.0, "deltaE_stability": 1.0}
        self.photonic_field = PhotonFieldState(frequency=0.0, amplitude=1 + 0j, phase=0.0)
        self.feedback_history, self.equilibrium_trend = [], []

        # Quantum state
        self.psi_amplitude = 1 + 0j
        self.psi_history = []
        self.diagnostics_registry = {}

        # ──────────────────────────────────────────────
        # Load SRK extensions (SRK-3 → SRK-5)
        # ──────────────────────────────────────────────
        self.entangled_pairs = {}
        self.last_rho = 1.0
        self.extensions = []

        for mod in [
            "srk_entropy",                # SRK-3
            "srk4_resonance",             # SRK-4
            "srk41_resonant_entropy",     # SRK-4.1
            "srk5_coherent_field",        # SRK-5
            "srk6_harmonic_coupling"      # SRK-6 ← new harmonic coupling layer
        ]:
            try:
                module = import_module(f"backend.symatics.core.{mod}")

                # --- Class resolution chain ---
                if hasattr(module, "SRKExtension"):
                    ext = module.SRKExtension()
                elif hasattr(module, "SRK41ResonantEntropy"):
                    ext = module.SRK41ResonantEntropy()
                elif hasattr(module, "SRK5CoherentField"):
                    ext = module.SRK5CoherentField()
                elif hasattr(module, "SRK6HarmonicCoupling"):
                    ext = module.SRK6HarmonicCoupling()
                else:
                    raise AttributeError(f"No compatible extension class found in {mod}")

                # --- Integrate into kernel ---
                ext.integrate(self)
                self.extensions.append(ext)
                print(f"[SRK] Extension {ext.name} ({ext.version}) integrated.")

            except Exception as e:
                print(f"[SRK] Skipped extension {mod}: {e}")

    # ──────────────────────────────────────────────
    # Extension management (SRK-3, SRK-4, …)
    # ──────────────────────────────────────────────
    def load_extension(self, extension_cls):
        """
        Safely loads and integrates an SRK extension (e.g. SRK-3, SRK-4).
        The extension class must define an `integrate(kernel)` method.
        """
        try:
            ext = extension_cls()
            ext.integrate(self)
            if not hasattr(self, "extensions"):
                self.extensions = []
            if ext not in self.extensions:
                self.extensions.append(ext)
            print(f"[SRK] Extension {ext.name} (v{ext.version}) integrated.")
        except Exception as e:
            print(f"[SRK] Failed to load extension {extension_cls.__name__}: {e}")

    # ─────────────────────────────────────────────────────────────
    # Core operators with automatic SRK-3 entropy feedback (v0.4.6)
    # ─────────────────────────────────────────────────────────────
    def superpose(self, a, b):
        result = self._evaluate("⊕", a, b)
        self._entropy_feedback_update()
        return result

    def measure(self, a):
        result = self._evaluate("μ", a)
        self._entropy_feedback_update()
        return result

    def resonate(self, a, b):
        result = self._evaluate("⟲", a, b)
        self._entropy_feedback_update()
        return result

    def entangle(self, a, b):
        result = self._evaluate("↔", a, b, entangle=True)
        self._entropy_feedback_update()
        return result

    def project(self, a):
        result = self._evaluate("π", a)
        self._entropy_feedback_update()
        return result

    # ─────────────────────────────────────────────────────────────
    # Internal SRK-3 entropy feedback trigger
    # ─────────────────────────────────────────────────────────────
    def _entropy_feedback_update(self):
        """
        Universal SRK-3 feedback hook — invoked after each operator evaluation.
        Updates entropy field state and logs SRK-3 law telemetry if available.
        """
        try:
            srk3_ext = next(
                (ext for ext in getattr(self, "extensions", []) if getattr(ext, "name", "") == "SRK-3"),
                None
            )
            if srk3_ext and hasattr(srk3_ext, "entropy_field"):
                srk3_ext.entropy_field.update(self.photonic_field)

        except Exception as e:
            try:
                from backend.modules.codex.codex_trace import record_event
                record_event("entropy_update_error", error=str(e))
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────
    # Evaluation pipeline + ψ(t) + Λ-feedback
    # ─────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────
    # Evaluation pipeline — ψ(t), Λ(t), and ν(t) coupling
    # ─────────────────────────────────────────────────────────────
    def _evaluate(self, op, *args, entangle=False):
        result = self.dispatch({"op": op, "args": list(args)})
        ts = datetime.now(timezone.utc).isoformat()

        # 1️⃣ Law check
        try:
            SR.check_all_laws(op, *args)
        except Exception as e:
            print(f"[SRK] Law check failed for {op}: {e}")

        # 2️⃣ Law signature
        sig = self._derive_law_signature(op)
        self.law_signatures.append({"t": ts, "signature": sig})
        self.law_signatures = self.law_signatures[-25:]

        # 3️⃣ Energy telemetry
        energy_balance = None
        if SymTactics and hasattr(SymTactics, "energy_mass_equivalence"):
            try:
                energy_balance = SymTactics.energy_mass_equivalence(args)
                self.last_energy_balance = energy_balance
            except Exception as e:
                energy_balance = {"error": str(e)}

        # 4️⃣ Tensor feedback (ψ–Λ–ν coupling tensor)
        feedback = self._compute_tensor_feedback(op, args, energy_balance)
        self.field_feedback = feedback

        # 5️⃣ Quantum propagation ψ(t)
        psi_state = (
            self._propagate_entangled_state(feedback)
            if entangle else
            self._propagate_quantum_state(feedback)
        )

        # 6️⃣ Λ(t) update + export to Rulebook
        self._update_lambda(feedback)
        self._export_decoherence_field(psi_state)

        # 6.5️⃣ ν↔ψ coupling: stabilize ΔE by nudging ν and φ
        try:
            dnu = 0.05 * (1.0 - feedback.get("deltaE_stability", 1.0))
            dphi = 0.10 * (
                feedback.get("psi_density", 0.0)
                - feedback.get("field_intensity", 0.0)
            )
            self.photonic_field.step(dnu=dnu, dphi=dphi, damping=self.lambda_t)
        except Exception:
            pass

        for ext in getattr(self, "extensions", []):
            if hasattr(ext, "feedback"):
                ext.feedback(self, feedback)

        # 7️⃣ Adaptive feedback loop
        if self.auto_stabilize:
            self._update_feedback_weights(feedback, psi_state)

        # 8️⃣ Trace logging
        if self.trace and hasattr(self.trace, "log_event"):
            payload = {
                "timestamp": ts,
                "operator": op,
                "law_signature": sig,
                "energy_balance": energy_balance,
                "field_feedback": feedback,
                "psi_amplitude": psi_state,
                "lambda_t": self.lambda_t,
                "equilibrium_trend": self.equilibrium_trend[-5:],
                "entangled_pairs": len(self.entangled_pairs),
                "photon_state": getattr(self.photonic_field, "coherence_map", lambda: {})(),
                "result": result,
            }
            try:
                self.trace.log_event(op, args, payload)
            except Exception as e:
                print(f"[SRK] Trace logging failed: {e}")

        # 9️⃣ Return execution summary
        return {
            "operator": op,
            "args": list(args),
            "result": result.get("result") if isinstance(result, dict) else result,
            "status": result.get("status", "ok") if isinstance(result, dict) else "ok",
            "law_signature": sig,
            "energy_balance": energy_balance,
            "field_feedback": feedback,
            "psi_amplitude": psi_state,
            "lambda_t": round(self.lambda_t, 6),
            "equilibrium_trend": self.equilibrium_trend[-5:],
            "entangled_pairs": len(self.entangled_pairs),
            "photon": getattr(self.photonic_field, "coherence_map", lambda: {})(),
        }

    # ─────────────────────────────────────────────────────────────
    # Tensor feedback
    # ─────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────
    # Tensor feedback — ψ(t), Λ(t), ν(t) coupling
    # ─────────────────────────────────────────────────────────────
    def _compute_tensor_feedback(self, op, args, energy_balance):
        try:
            base = sum(float(x) for x in args if isinstance(x, (int, float))) or 1.0
        except Exception:
            base = 1.0

        # Primary ψ/Λ field components
        f_int = abs(math.sin(base)) ** 0.5         # field intensity proxy
        psi = abs(math.cos(base)) ** 0.5           # ψ density proxy
        dE = 1.0
        if isinstance(energy_balance, dict) and "ΔE" in energy_balance:
            try:
                dE = abs(1.0 / (1.0 + abs(float(energy_balance["ΔE"]))))
            except Exception:
                pass

        # Photonic field coupling — ν(x,t) ↔ ψ(t)
        try:
            from backend.symatics.photonic_field import (
                propagate_photon_field,
                compute_spectral_gradient,
            )

            # update ν and φ to reflect current ψ–Λ interaction
            self.photonic_field.frequency = base
            target_phase = math.atan2(psi, max(1e-9, f_int))
            self.photonic_field.amplitude = complex(psi, f_int)

            # gentle phase-lock toward ψ-derived phase
            self.photonic_field.phase_lock(target_phase, k=0.15)

            # propagate photonic state slightly forward in time
            self.photonic_field = propagate_photon_field(self.photonic_field, delta_t=1e-3)

            # compute spectral gradient feedback tensor
            grad = compute_spectral_gradient(psi, 1.0 - dE)
            spectral_gradient = grad["spectral_gradient"]
            feedback_coeff = grad["feedback_coeff"]

        except Exception as e:
            spectral_gradient = 0.0
            feedback_coeff = 1.0

        # Composite feedback field — merges ψ, Λ, ν dynamics
        return {
            "field_intensity": round(f_int, 6),
            "psi_density": round(psi, 6),
            "deltaE_stability": round(dE, 6),
            "spectral_gradient": round(spectral_gradient, 6),
            "feedback_coeff": round(feedback_coeff, 6),
        }

    # ─────────────────────────────────────────────────────────────
    # Quantum propagation ψ(t)
    # ─────────────────────────────────────────────────────────────
    def _propagate_quantum_state(self, feedback, γ=0.05):
        δE = 1 - feedback.get("deltaE_stability", 1.0)
        φ = math.pi * δE
        decay = math.exp(-γ - self.lambda_t)

        ψ_next = self.psi_amplitude * cmath.exp(1j * φ) * decay
        norm = abs(ψ_next)
        if norm > 0:
            ψ_next /= norm

        self.psi_amplitude = ψ_next
        self.psi_history.append(ψ_next)
        self.psi_history = self.psi_history[-50:]
        return complex(round(ψ_next.real, 6), round(ψ_next.imag, 6))

    # ─────────────────────────────────────────────────────────────
    # Entangled ψ₁↔ψ₂ propagation
    # ─────────────────────────────────────────────────────────────
    def _propagate_entangled_state(self, feedback):
        φ = math.pi * (1 - feedback.get("deltaE_stability", 1.0))
        λ = self.lambda_t

        ψ1 = self.psi_amplitude * cmath.exp(1j * φ) * math.exp(-λ)
        ψ2 = self.psi_amplitude * cmath.exp(-1j * φ) * math.exp(-λ)

        if abs(ψ1):
            ψ1 /= abs(ψ1)
        if abs(ψ2):
            ψ2 /= abs(ψ2)

        tag = f"ψpair_{len(self.entangled_pairs) + 1}"
        self.entangled_pairs[tag] = (ψ1, ψ2)

        ρ = max(-1.0, min(1.0, ψ1.real * ψ2.real + ψ1.imag * ψ2.imag))
        self.last_rho = ρ

        self.psi_amplitude = (ψ1 + ψ2) / 2
        self.psi_history.append(self.psi_amplitude)
        self.psi_history = self.psi_history[-50:]

        return {
            "ψ1": complex(round(ψ1.real, 6), round(ψ1.imag, 6)),
            "ψ2": complex(round(ψ2.real, 6), round(ψ2.imag, 6)),
            "ρ": round(ρ, 6),
        }

    # ─────────────────────────────────────────────────────────────
    # λ(t) update & export
    # ─────────────────────────────────────────────────────────────
    def _update_lambda(self, feedback):
        δE = 1 - feedback.get("deltaE_stability", 1.0)
        self.lambda_t += self.alpha * δE
        self.lambda_t = max(0.0, min(self.lambda_t, 0.2))

    def _export_decoherence_field(self, psi_state):
        try:
            if hasattr(SR, "LAW_REGISTRY"):
                quantum = SR.LAW_REGISTRY.setdefault("quantum", {})
                quantum["fields"] = {
                    "λ": round(self.lambda_t, 6),
                    "ρ": round(self.last_rho, 6),
                    "ψ": str(psi_state),
                }
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────
    # Adaptive feedback
    # ─────────────────────────────────────────────────────────────
    def _update_feedback_weights(self, feedback, ψt=None):
        δE = feedback.get("deltaE_stability", 1.0)
        psi = feedback.get("psi_density", 0.0)
        intensity = feedback.get("field_intensity", 0.0)

        eq = round((psi + intensity + δE) / 3.0, 6)
        self.feedback_history.append(eq)
        self.feedback_history = self.feedback_history[-50:]

        trend = mean(self.feedback_history[-5:]) if self.feedback_history else 1.0
        self.equilibrium_trend.append(round(trend, 6))
        self.equilibrium_trend = self.equilibrium_trend[-25:]

        try:
            if hasattr(self.registry, "update_weight"):
                self.registry.update_weight("symatics", trend)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────
    # Law signatures
    # ─────────────────────────────────────────────────────────────
    def _derive_law_signature(self, op):
        return {
            "⊕": "⊕→⟲→μ",
            "⟲": "⟲→μ→π",
            "μ": "μ→π",
            "↔": "↔→μ→πμ",
            "π": "π→∇⊗ψ",
        }.get(op, op)

    def diagnostics(self):
        """
        Collects current symbolic, photonic, and entropy-level diagnostics
        from the SymaticsReasoningKernel and all attached SRK extensions.

        Now includes:
          • SRK-3 Entropy Feedback (v0.4.6+)
          • SRK-4 Resonant Coupling (Λ↔ψ↔⟲R)
          • SRK-4.1 Resonant-Entropy Coupling (Λ↔ψ↔⟲R↔S)
        """

        trace_count = 0
        if self.trace and hasattr(self.trace, "count"):
            try:
                trace_count = self.trace.count() or 0
            except Exception:
                trace_count = 0

        reg = getattr(self.registry, "instruction_registry", None)
        handlers = list(getattr(reg, "registry", {}).keys()) if reg and hasattr(reg, "registry") else []
        laws = list(getattr(SR, "LAW_REGISTRY", {}).keys()) if hasattr(SR, "LAW_REGISTRY") else []

        # ──────────────────────────────────────────────
        # Collect diagnostics from SRK extensions
        # ──────────────────────────────────────────────
        ext_diag = {}
        srk3_ext = srk4_ext = srk41_ext = None

        for ext in getattr(self, "extensions", []):
            try:
                ext_diag[ext.name] = ext.diagnostics(self)
                n = getattr(ext, "name", "")
                if "SRK-3" in n:
                    srk3_ext = ext
                elif "SRK-4 Resonant" in n and "4.1" not in n:
                    srk4_ext = ext
                elif "SRK-4.1" in n or "Resonant-Entropy" in n:
                    srk41_ext = ext
            except Exception as e:
                ext_diag[getattr(ext, "name", "unknown")] = {"error": str(e)}

        # ──────────────────────────────────────────────
        # Base kernel diagnostics
        # ──────────────────────────────────────────────
        diag = {
            "operators": handlers,
            "laws": laws,
            "trace_count": trace_count,
            "law_signatures": self.law_signatures[-5:],
            "energy_balance": self.last_energy_balance,
            "field_feedback": self.field_feedback,
            "psi_amplitude": complex(
                round(self.psi_amplitude.real, 6),
                round(self.psi_amplitude.imag, 6)
            ),
            "lambda_t": round(self.lambda_t, 6),
            "equilibrium_trend": self.equilibrium_trend[-5:],
            "entangled_pairs": len(self.entangled_pairs),
            "photon": self.photonic_field.coherence_map(),
            "spectral_density": round(self.photonic_field.spectral_density(), 6),
            "decoherence_field": {
                "λ": round(self.lambda_t, 6),
                "ρ": round(self.last_rho, 6),
                "trend": self.equilibrium_trend[-5:],
            },
        }

        # ──────────────────────────────────────────────
        # Merge extension diagnostics
        # ──────────────────────────────────────────────
        diag.update(ext_diag)

        # ──────────────────────────────────────────────
        # SRK-3 Entropy Feedback (v0.4.6+)
        # ──────────────────────────────────────────────
        if srk3_ext and hasattr(srk3_ext, "last_entropy_feedback"):
            diag["entropy_feedback"] = srk3_ext.last_entropy_feedback
            try:
                ef = getattr(srk3_ext, "entropy_field", None)
                if ef and getattr(ef, "history", None):
                    recent = ef.history[-5:]
                    diag["entropy_trend"] = [
                        {
                            "S": h[0] if isinstance(h, tuple) else h.get("S", 0.0),
                            "gamma_S": h[1] if isinstance(h, tuple) else h.get("gamma_S", 0.0),
                            "gradS": h[2] if isinstance(h, tuple) else h.get("gradS", 0.0),
                        }
                        for h in recent
                    ]
            except Exception:
                pass

        # ──────────────────────────────────────────────
        # SRK-4 Resonant Feedback
        # ──────────────────────────────────────────────
        if srk4_ext:
            if hasattr(srk4_ext, "last_resonance_feedback"):
                diag["resonance_feedback"] = srk4_ext.last_resonance_feedback
            if hasattr(srk4_ext, "resonance_window"):
                diag["resonance_trend"] = srk4_ext.resonance_window[-5:]

        # ──────────────────────────────────────────────
        # SRK-4.1 Resonant-Entropy Feedback
        # ──────────────────────────────────────────────
        if srk41_ext:
            try:
                rdiag = srk41_ext.diagnostics(self)
                if isinstance(rdiag, dict):
                    diag["resonant_entropy_feedback"] = rdiag.get("resonant_entropy_feedback", {})
                    diag["resonant_entropy_trend"] = rdiag.get("stability_trend", [])
                    diag["resonant_entropy_state"] = {
                        "R": rdiag.get("R"),
                        "gamma_S": rdiag.get("gamma_S"),
                        "lambda_t": rdiag.get("lambda_t"),
                        "stability": rdiag.get("stability"),
                    }
            except Exception as e:
                diag["resonant_entropy_feedback"] = {"error": str(e)}

        return diag