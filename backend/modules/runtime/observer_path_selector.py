# File: backend/modules/runtime/observer_path_selector.py

from ..glyphos.qglyph import resolve_qglyph_superposition
from ..codex/observer_bias import compute_observer_bias
from ..hexcore.memory_engine import store_memory

import logging

logger = logging.getLogger(__name__)


def select_path_from_superposition(qglyph_pair: dict, context: dict = None) -> dict:
    """
    Determines which path of a QGlyph (↔) to collapse into based on observer bias and context.
    Returns the resolved glyph and metadata about the decision.
    """
    try:
        left = qglyph_pair.get("left")
        right = qglyph_pair.get("right")
        glyph_id = qglyph_pair.get("id", "unknown")

        bias = compute_observer_bias(context)

        # Score each path
        left_score = bias.evaluate_path(left)
        right_score = bias.evaluate_path(right)

        chosen = left if left_score >= right_score else right

        logger.info(f"[Collapse] QGlyph {glyph_id} → {chosen} (L:{left_score} R:{right_score})")

        decision_memory = {
            "glyph_id": glyph_id,
            "choice": chosen,
            "scores": {
                "left": left_score,
                "right": right_score
            },
            "context": context or {}
        }

        store_memory({"type": "qglyph_collapse", "data": decision_memory})

        return {
            "collapsed": chosen,
            "trace": decision_memory
        }

    except Exception as e:
        logger.exception("[Collapse] Failed to select QGlyph path")
        return {"error": str(e)}