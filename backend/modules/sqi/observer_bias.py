# File: backend/modules/sqi/observer_bias.py

from ..hexcore.memory_engine import MemoryEngine
from ..codex.codex_metrics import log_metric
from ..aion.ethics_engine import evaluate_ethics_score

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