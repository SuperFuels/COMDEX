# ================================================================
# 💠 Phase 45G.6 - QMath Core Symbolic Generator (∇ψ Enhanced)
# ================================================================
"""
Symbolic mathematics core for AION Dual-Mode CEE.
Generates Symatics-style symbolic equations using ⊕, ↔, ⟲, ∇, μ, π
operators and computes resonance coherence (ρ), intensity (I),
and gradient-collapse metrics (∇ψ coherence).

Used by:
    backend/modules/aion_cognition/cognitive_exercise_engine_dual.py
"""

import math, random, time, logging
from dataclasses import dataclass, field

# Gradient and field imports
try:
    from backend.quant.qtensor.qtensor_field import random_field
    from backend.quant.qgradient import collapse_gradient
except Exception as e:
    random_field = None
    collapse_gradient = None

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Symbolic primitives (from Symatics Algebra spec)
# ------------------------------------------------------------
OPERATORS = ["⊕", "↔", "⟲", "∇", "μ", "π"]
SYMBOLS = ["ψ", "Φ", "η", "Λ", "Ω", "χ", "σ", "γ"]

# ------------------------------------------------------------
# Equation container
# ------------------------------------------------------------
@dataclass
class QEquation:
    expr: str
    coherence: float
    intensity: float
    phase: float
    grad_coherence: float = 0.0
    timestamp: float = field(default_factory=lambda: time.time())

    def as_dict(self):
        return {
            "expr": self.expr,
            "ρ": self.coherence,
            "I": self.intensity,
            "φ": self.phase,
            "ρ∇ψ": self.grad_coherence,
            "timestamp": self.timestamp,
        }

# ------------------------------------------------------------
# QMath Core
# ------------------------------------------------------------
class QMath:
    @staticmethod
    def random_equation(depth: int = 2) -> QEquation:
        """Generate a random symbolic equation using Symatics operators."""
        parts = []
        for _ in range(depth):
            a, b = random.choice(SYMBOLS), random.choice(SYMBOLS)
            op = random.choice(OPERATORS)
            parts.append(f"{a} {op} {b}")
        expr = " -> ".join(parts)

        # Compute pseudo resonance metrics
        phase = round(random.uniform(-math.pi, math.pi), 3)
        coherence = round(1 - abs(math.sin(phase)) * 0.5, 3)
        intensity = round(random.uniform(0.8, 1.2) * coherence, 3)

        # Optional ∇ψ gradient coherence (if backend is available)
        grad_coherence = 0.0
        if random_field and collapse_gradient:
            try:
                field = random_field((4, 4))
                grad_data = collapse_gradient(field)
                grad_coherence = round(grad_data["ρ"], 3)
                logger.info(
                    f"[QMath:∇ψ] Gradient coherence ρ∇ψ={grad_coherence}, φ={grad_data['φ']:.3f}"
                )
            except Exception as e:
                logger.warning(f"[QMath] ∇ψ computation skipped: {e}")

        logger.info(
            f"[QMath] Generated {expr} | ρ={coherence}, I={intensity}, φ={phase}, ρ∇ψ={grad_coherence}"
        )
        return QEquation(expr, coherence, intensity, phase, grad_coherence)

    # --------------------------------------------------------
    @staticmethod
    def evaluate_resonance(eq: QEquation) -> float:
        """Compute symbolic SQI proxy = mean(ρ, I, normalized phase, ρ∇ψ)."""
        norm_phase = 1 - abs(eq.phase) / math.pi  # normalize 0-1
        components = [eq.coherence, eq.intensity, norm_phase]
        if eq.grad_coherence > 0:
            components.append(eq.grad_coherence)
        sqi = round(sum(components) / len(components), 3)
        return sqi

    # --------------------------------------------------------
    @staticmethod
    def batch_generate(count: int = 5, depth: int = 2):
        """Generate multiple equations for symbolic sessions."""
        return [QMath.random_equation(depth=depth) for _ in range(count)]


# ------------------------------------------------------------
# Self-Test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    equations = QMath.batch_generate(3, 2)
    for eq in equations:
        sqi = QMath.evaluate_resonance(eq)
        print(eq.as_dict())
        print(f"SQI = {sqi}")