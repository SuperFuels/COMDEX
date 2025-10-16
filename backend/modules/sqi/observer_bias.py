# File: backend/modules/sqi/observer_bias.py

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.codex.codex_metrics import log_metric
from backend.modules.consciousness.ethics_engine import evaluate_ethics_score

def filter_qglyph_collapse_options(options: list, memory: MemoryEngine, context: dict) -> dict:
    """
    Given a list of QGlyph collapse options, choose the most ethical path.
    Each option is a dict like: {"path": "A", "glyph": "⟦ logic ⟧", ...}

    Returns:
        {
            "selected": dict,   # best option
            "ranked": list      # full sorted list with ethics scores
        }
    """
    ranked = []
    for option in options:
        glyph = option.get("glyph", "")
        score = evaluate_ethics_score(glyph, context=context)
        option["ethics_score"] = score
        ranked.append(option)

    ranked.sort(key=lambda o: o["ethics_score"], reverse=True)
    selected = ranked[0] if ranked else {}

    log_metric("observer_collapse_decision", {
        "context": context,
        "selected_path": selected.get("path"),
        "ethics_score": selected.get("ethics_score"),
        "alternatives": [r.get("path") for r in ranked[1:]]
    })

    memory.store("collapse_decision", {
        "input_options": options,
        "selected": selected,
        "timestamp": context.get("timestamp")
    })

    return {
        "selected": selected,
        "ranked": ranked
    }

# ─────────────────────────────────────────────────────────────
# 🧭 Observer Bias Computation — Integration Hook
# ─────────────────────────────────────────────────────────────
import random

class _ObserverBias:
    """
    Represents an observer bias profile.
    Provides scalar bias value ∈ [0,1] and optional path evaluation.
    """

    def __init__(self, value: float):
        self.value = max(0.0, min(1.0, value))

    def evaluate_path(self, glyph: str) -> float:
        """
        Optional path scoring based on ethical context and glyph semantics.
        """
        try:
            from backend.modules.consciousness.ethics_engine import evaluate_ethics_score
            ethics_score = evaluate_ethics_score(glyph)
            # Weight ethics with base bias (averaged for smoother decision)
            return (ethics_score + self.value) / 2.0
        except Exception:
            # fallback uniform random bias
            return self.value


def compute_observer_bias(context: dict = None) -> _ObserverBias:
    """
    Computes the observer bias profile for the current collapse context.
    Bias represents how much the observer 'leans' left vs right in a QGlyph superposition.

    Returns:
        _ObserverBias: object with .value and .evaluate_path()
    """
    context = context or {}
    try:
        # Pull bias seed from context (e.g. memory entropy, observer ID hash)
        seed_source = str(context.get("observer_id", "")) + str(context.get("timestamp", ""))
        random.seed(seed_source)
        base_bias = random.random()  # uniform fallback

        # Optional context-based weighting
        if "entropy" in context:
            base_bias *= max(0.1, min(1.0, 1.0 - context["entropy"]))

        return _ObserverBias(base_bias)
    except Exception:
        return _ObserverBias(0.5)