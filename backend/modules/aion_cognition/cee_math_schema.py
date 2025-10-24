# ================================================================
# 🧮 CEE — MathExercise Schema (Symbolic Ops)
# Phase 45G – Task g9
# ================================================================
"""
Defines the MathExercise data schema and generation logic for
the Cognitive Exercise Engine (CEE). Each exercise encodes
a symbolic reasoning or semantic grouping task grounded in
QuantPy / QTensorField resonance evaluation.

Supported exercise types:
    • equation_match  → find equivalent or simplified expression
    • symbol_fill     → complete a missing symbol or term
    • group_sort      → categorize symbols into conceptual groups

Output examples are resonance-tagged and ready for inclusion in
.mathfield.qdata.json or .lexfield.qdata.json datasets.
"""

import numpy as np
import time, random, json, logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any

from backend.quant.qtensor.qtensor_field import QTensorField

logger = logging.getLogger(__name__)

# ================================================================
# 🔢 QuantPy symbolic operation bindings (using QTensorField)
# ================================================================
def qadd(a, b):
    """QuantPy tensorized addition (⊕ superposition)."""
    if not isinstance(a, QTensorField):
        a = QTensorField(np.array([[a]]))
    if not isinstance(b, QTensorField):
        b = QTensorField(np.array([[b]]))
    return a.superpose(b)

def qmul(a, b):
    """QuantPy tensorized multiplication (↔ entanglement magnitude)."""
    if not isinstance(a, QTensorField):
        a = QTensorField(np.array([[a]]))
    if not isinstance(b, QTensorField):
        b = QTensorField(np.array([[b]]))
    ent_a, ent_b, rho = a.entangle(b)
    return ent_a, ent_b, rho


# ================================================================
# 🧩 Data Schema
# ================================================================
@dataclass
class MathExercise:
    type: str
    prompt: str
    options: List[str] = field(default_factory=list)
    answer: str = ""
    resonance: Dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, type: str, prompt: str, options=None, answer="", resonance=None, timestamp=None, meta=None, **kwargs):
        self.type = type
        self.prompt = prompt
        self.options = options or []
        self.answer = answer
        self.resonance = resonance or {}
        self.timestamp = timestamp or time.time()
        self.meta = meta or {}
        # ignore any extra kwargs (like 'mode', 'context', 'group', etc.)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def generate():
        """Factory method to generate one example MathExercise entry."""
        from random import choice
        exercises = [generate_equation_match(), generate_symbol_fill(), generate_group_sort()]
        ex = choice(exercises)
        if isinstance(ex, dict):
            return MathExercise(**ex)
        return ex

# ================================================================
# 🔢 Resonance Generator
# ================================================================
def _generate_resonance():
    """Return randomized but coherent resonance values."""
    ρ = round(random.uniform(0.6, 0.9), 3)
    I = round(random.uniform(0.8, 1.0), 3)
    SQI = round((ρ + I) / 2, 3)
    return {"ρ": ρ, "I": I, "SQI": SQI}


# ================================================================
# 🧮 Exercise Factories
# ================================================================
def generate_equation_match():
    """Produce a symbolic equivalence challenge."""
    expr_a = "(x + 1)**2"
    expr_b = "x**2 + 2*x + 1"
    distractors = ["x**2 + x + 1", "x**2 + 1", "(x + 2)**2"]
    options = random.sample(distractors + [expr_b], 4)

    return MathExercise(
        type="equation_match",
        prompt=f"Simplify or match: {expr_a}",
        options=options,
        answer=expr_b,
        resonance=_generate_resonance(),
        timestamp=time.time(),
        meta={"difficulty": "medium", "topic": "algebra"}
    )


def generate_symbol_fill():
    """Produce a symbolic fill-in challenge."""
    prompt = "E = m * ? ** 2"
    options = random.sample(["c", "v", "t", "h"], 4)
    answer = "c"

    return MathExercise(
        type="symbol_fill",
        prompt=prompt,
        options=options,
        answer=answer,
        resonance=_generate_resonance(),
        timestamp=time.time(),
        meta={"difficulty": "easy", "topic": "physics"}
    )


def generate_group_sort(groups=None):
    """Generate a semantic grouping task (for lexical/symbolic generalization)."""
    if groups is None:
        groups = ["Fruits", "Animals"]

    items = [
        ("apple", "Fruits"),
        ("banana", "Fruits"),
        ("pear", "Fruits"),
        ("dog", "Animals"),
        ("cat", "Animals"),
        ("bird", "Animals"),
    ]
    random.shuffle(items)

    mapping = {w: g for w, g in items}
    all_items = [w for w, _ in items]
    ρ = round(random.uniform(0.6, 0.9), 3)
    I = round(random.uniform(0.7, 0.95), 3)
    SQI = round((ρ + I) / 2, 3)

    return {
        "type": "group_sort",
        "groups": groups,
        "items": all_items,
        "mapping": mapping,
        "resonance": {"ρ": ρ, "I": I, "SQI": SQI},
        "timestamp": time.time(),
    }


# ================================================================
# 🚀 Test Harness
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ex = MathExercise.generate()
    print(json.dumps(ex.to_dict() if isinstance(ex, MathExercise) else ex, indent=2))