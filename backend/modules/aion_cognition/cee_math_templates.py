# ================================================================
# 🧮 CEE Math Templates - QMath / QTensor Integration
# ================================================================
"""
Upgraded symbolic math template generator using QuantPy / QTensorField
for resonance-based symbolic computation.

Each generated exercise now evaluates real tensor fields rather than
placeholders, linking symbolic correctness with resonance statistics.
"""

import json, time, random, logging
from pathlib import Path
from dataclasses import asdict

from backend.modules.aion_cognition.cee_math_schema import MathExercise
from backend.quant.qtensor.qtensor_field import QTensorField, random_field

logger = logging.getLogger(__name__)
OUT_PATH = Path("data/learning/mathfield_v1.qdata.json")

# ----------------------------------------------------------------------
def tensor_resonance(a_shape=(4, 4), b_shape=(4, 4)):
    """Return averaged (ρ, I, SQI) resonance metrics from two random QTensorFields."""
    ψa = random_field(a_shape)
    ψb = random_field(b_shape)
    interaction = ψa.interact(ψb)
    ρ = interaction["correlation"]
    I = ψa.measure()["intensity_mean"]
    SQI = round((ρ + I) / 2, 3)
    return round(ρ, 3), round(I, 3), SQI

# ----------------------------------------------------------------------
def generate_equation_match() -> MathExercise:
    """Symbolic algebra item using QTensor resonance."""
    prompts = [
        ("(x + 2)**2", "x**2 + 4*x + 4"),
        ("(a + b)**2", "a**2 + 2*a*b + b**2"),
        ("(x + 1)*(x - 1)", "x**2 - 1"),
        ("(p + q)**3", "p**3 + 3*p**2*q + 3*p*q**2 + q**3"),
    ]
    prompt, answer = random.choice(prompts)
    options = [a for _, a in prompts]

    ρ, I, SQI = tensor_resonance()

    return MathExercise(
        type="equation_match",
        prompt=f"Simplify or match: {prompt}",
        options=options,
        answer=answer,
        resonance={"ρ": ρ, "I": I, "SQI": SQI},
        timestamp=time.time(),
        meta={"difficulty": "medium", "topic": "algebra"}
    )

# ----------------------------------------------------------------------
def generate_symbol_fill() -> MathExercise:
    """Physics formula completion using tensor-based resonance."""
    prompt = "F = m * a"
    options = ["F", "m", "a"]
    answer = "a"

    ρ, I, SQI = tensor_resonance((2, 2), (2, 2))

    return MathExercise(
        type="symbol_fill",
        prompt=prompt,
        options=options,
        answer=answer,
        resonance={"ρ": ρ, "I": I, "SQI": SQI},
        timestamp=time.time(),
        meta={"difficulty": "easy", "topic": "physics"}
    )

# ----------------------------------------------------------------------
def generate_batch(n: int = 8):
    """Produce a mixed symbolic batch."""
    items = []
    for _ in range(n):
        func = random.choice([generate_equation_match, generate_symbol_fill])
        items.append(func())
    return items

# ----------------------------------------------------------------------
def export_mathfield():
    """Generate and export the resonance map dataset."""
    exercises = generate_batch(10)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump([asdict(e) for e in exercises], open(OUT_PATH, "w"), indent=2)

    ρ_mean = round(sum(e.resonance["ρ"] for e in exercises) / len(exercises), 3)
    I_mean = round(sum(e.resonance["I"] for e in exercises) / len(exercises), 3)
    SQI_mean = round(sum(e.resonance["SQI"] for e in exercises) / len(exercises), 3)

    summary = {"ρ̄": ρ_mean, "Ī": I_mean, "SQĪ": SQI_mean}
    logger.info(f"[CEE-MathTemplates] Exported -> {OUT_PATH}")
    print(json.dumps(summary, indent=2))
    return summary

# ----------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    export_mathfield()