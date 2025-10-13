# -*- coding: utf-8 -*-
# File: backend/symatics/core/srk_kernel.py
"""
Symatics Reasoning Kernel (SRK-1)
─────────────────────────────────────────────
Tessaris Core v0.9 — ψ₁↔ψ₂ Entanglement Manifold

Extends v0.8 with:
  • Coupled ψ-state entanglement propagation (ψ₁↔ψ₂)
  • Shared ΔE feedback and reciprocal phase offsets
  • Decoherence damping λ(t) for quantum decay control
  • Cross-correlation ρ(ψ₁, ψ₂) telemetry in diagnostics
  • Backward-compatible single ψ(t) propagation
"""

import cmath
import math
from datetime import datetime, timezone
from statistics import mean
from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
from backend.symatics import symatics_rulebook as SR
from backend.core.registry_bridge import registry_bridge
from backend.modules.codex.codex_trace import CodexTrace

try:
    from backend.symatics.sym_tactics import SymTactics
except ImportError:
    SymTactics = None


class SymaticsReasoningKernel:
    """SRK-1 (v0.9) — tensor-aware quantum kernel with entanglement manifold."""

    def __init__(self, auto_stabilize=True, decoherence_lambda=0.03):
        self.registry = registry_bridge
        self.trace = CodexTrace() if hasattr(CodexTrace, "__call__") else None
        self.dispatch = evaluate_symatics_expr
        self.auto_stabilize = auto_stabilize
        self.decoherence_lambda = decoherence_lambda

        # Feedback + quantum memory
        self.law_signatures = []
        self.last_energy_balance = {}
        self.field_feedback = {"field_intensity": 0.0, "psi_density": 0.0, "deltaE_stability": 1.0}
        self.feedback_history = []
        self.equilibrium_trend = []

        # Quantum state variables
        self.psi_amplitude = 1 + 0j
        self.psi_history = []

        # Entanglement register
        self.entangled_pairs = {}

    # ─────────────────────────────────────────────────────────────
    # Core operators
    # ─────────────────────────────────────────────────────────────
    def superpose(self, a, b):  return self._evaluate("⊕", a, b)
    def measure(self, a):       return self._evaluate("μ", a)
    def resonate(self, a, b):   return self._evaluate("⟲", a, b)
    def entangle(self, a, b):   return self._evaluate("↔", a, b, entangle=True)
    def project(self, a):       return self._evaluate("π", a)

    # ─────────────────────────────────────────────────────────────
    # Evaluation pipeline + feedback + ψ(t)
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
        signature = self._derive_law_signature(op)
        self.law_signatures.append({"t": ts, "signature": signature})
        self.law_signatures = self.law_signatures[-25:]

        # 3️⃣ Energy telemetry
        energy_balance = None
        if SymTactics and hasattr(SymTactics, "energy_mass_equivalence"):
            try:
                energy_balance = SymTactics.energy_mass_equivalence(args)
                self.last_energy_balance = energy_balance
            except Exception as e:
                energy_balance = {"error": str(e)}

        # 4️⃣ Tensor feedback
        feedback = self._compute_tensor_feedback(op, args, energy_balance)
        self.field_feedback = feedback

        # 5️⃣ Quantum propagation
        if entangle:
            psi_state = self._propagate_entangled_state(feedback)
        else:
            psi_state = self._propagate_quantum_state(feedback)

        # 6️⃣ Adaptive feedback loop
        if self.auto_stabilize:
            self._update_feedback_weights(feedback, psi_state)

        # 7️⃣ Trace logging
        if self.trace and hasattr(self.trace, "log_event"):
            payload = {
                "timestamp": ts,
                "operator": op,
                "law_signature": signature,
                "energy_balance": energy_balance,
                "field_feedback": feedback,
                "psi_amplitude": psi_state,
                "equilibrium_trend": self.equilibrium_trend[-5:],
                "entangled_pairs": len(self.entangled_pairs),
                "result": result,
            }
            try:
                self.trace.log_event(op, args, payload)
            except Exception as e:
                print(f"[SRK] Trace logging failed: {e}")

        return {
            "operator": op,
            "args": list(args),
            "result": result.get("result") if isinstance(result, dict) else result,
            "status": result.get("status", "ok") if isinstance(result, dict) else "ok",
            "law_signature": signature,
            "energy_balance": energy_balance,
            "field_feedback": feedback,
            "psi_amplitude": psi_state,
            "equilibrium_trend": self.equilibrium_trend[-5:],
            "entangled_pairs": len(self.entangled_pairs),
        }

    # ─────────────────────────────────────────────────────────────
    # Tensor feedback calculus
    # ─────────────────────────────────────────────────────────────
    def _compute_tensor_feedback(self, op, args, energy_balance):
        try:
            base = sum(float(x) for x in args if isinstance(x, (int, float))) or 1.0
        except Exception:
            base = 1.0
        f_int = abs(math.sin(base)) ** 0.5
        psi = abs(math.cos(base)) ** 0.5
        dE = 1.0
        if isinstance(energy_balance, dict) and "ΔE" in energy_balance:
            try:
                dE = abs(1.0 / (1.0 + abs(float(energy_balance["ΔE"]))))
            except Exception:
                pass
        return {
            "field_intensity": round(f_int, 6),
            "psi_density": round(psi, 6),
            "deltaE_stability": round(dE, 6),
        }

    # ─────────────────────────────────────────────────────────────
    # Quantum propagation (ψ evolution)
    # ─────────────────────────────────────────────────────────────
    def _propagate_quantum_state(self, feedback, γ=0.05):
        deltaE = 1 - feedback.get("deltaE_stability", 1.0)
        φ = math.pi * deltaE
        decay = math.exp(-γ)

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
        φ_base = math.pi * (1 - feedback.get("deltaE_stability", 1.0))
        λ = self.decoherence_lambda

        # Two coupled amplitudes with mirrored phase offsets
        ψ1 = self.psi_amplitude * cmath.exp(1j * φ_base) * math.exp(-λ)
        ψ2 = self.psi_amplitude * cmath.exp(-1j * φ_base) * math.exp(-λ)

        n1, n2 = abs(ψ1), abs(ψ2)
        if n1 > 0: ψ1 /= n1
        if n2 > 0: ψ2 /= n2

        tag = f"ψpair_{len(self.entangled_pairs)+1}"
        self.entangled_pairs[tag] = (ψ1, ψ2)

        # Cross-correlation ρ(ψ₁, ψ₂)
        ρ = ψ1.real * ψ2.real + ψ1.imag * ψ2.imag
        ρ = max(-1.0, min(1.0, ρ))

        # Update aggregate ψ state (average coherence)
        self.psi_amplitude = (ψ1 + ψ2) / 2
        self.psi_history.append(self.psi_amplitude)
        self.psi_history = self.psi_history[-50:]

        return {
            "ψ1": complex(round(ψ1.real, 6), round(ψ1.imag, 6)),
            "ψ2": complex(round(ψ2.real, 6), round(ψ2.imag, 6)),
            "ρ": round(ρ, 6),
        }

    # ─────────────────────────────────────────────────────────────
    # Adaptive feedback control
    # ─────────────────────────────────────────────────────────────
    def _update_feedback_weights(self, feedback, ψt=None):
        deltaE = feedback.get("deltaE_stability", 1.0)
        psi = feedback.get("psi_density", 0.0)
        intensity = feedback.get("field_intensity", 0.0)

        equilibrium = round((psi + intensity + deltaE) / 3.0, 6)
        self.feedback_history.append(equilibrium)
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
            "π": "π→∇⊗ψ"
        }.get(op, op)

    # ─────────────────────────────────────────────────────────────
    # Diagnostics
    # ─────────────────────────────────────────────────────────────
    def diagnostics(self):
        trace_count = 0
        if self.trace and hasattr(self.trace, "count"):
            try:
                trace_count = self.trace.count() or 0
            except Exception:
                pass

        reg = getattr(self.registry, "instruction_registry", None)
        handlers = list(getattr(reg, "registry", {}).keys()) if reg and hasattr(reg, "registry") else []
        law_keys = list(getattr(SR, "LAW_REGISTRY", {}).keys()) if hasattr(SR, "LAW_REGISTRY") else []

        return {
            "operators": handlers,
            "laws": law_keys,
            "trace_count": trace_count,
            "law_signatures": self.law_signatures[-5:],
            "energy_balance": self.last_energy_balance,
            "field_feedback": self.field_feedback,
            "psi_amplitude": complex(round(self.psi_amplitude.real, 6), round(self.psi_amplitude.imag, 6)),
            "equilibrium_trend": self.equilibrium_trend[-5:],
            "entangled_pairs": len(self.entangled_pairs),
        }