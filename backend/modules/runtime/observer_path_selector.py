"""
observer_path_selector.py
=========================
Resolves QGlyph superpositions (↔) into a single collapsed path
based on observer bias and symbolic wave-context.

Integrates:
  • observer bias scoring (compute_observer_bias)
  • probabilistic symbolic collapse (resolve_qglyph_superposition)
  • memory trace logging (store_memory)
"""

import logging
from backend.modules.glyphos.qglyph import resolve_qglyph_superposition
from backend.modules.sqi.observer_bias import compute_observer_bias
from backend.modules.hexcore.memory_engine import store_memory

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

        # 1️⃣ Compute observer bias (0–1 scalar, where >0.5 favors left)
        bias = compute_observer_bias(context)
        bias_value = getattr(bias, "value", 0.5) if hasattr(bias, "value") else float(bias or 0.5)

        # 2️⃣ Optional score-based bias refinement
        if hasattr(bias, "evaluate_path"):
            left_score = bias.evaluate_path(left)
            right_score = bias.evaluate_path(right)
            # convert to [0,1] weight for collapse bias
            total = (left_score + right_score) or 1.0
            bias_value = left_score / total
        else:
            left_score, right_score = bias_value, 1.0 - bias_value

        # 3️⃣ Collapse via symbolic QGlyph resolver
        collapsed = resolve_qglyph_superposition(left, right, bias=bias_value)

        logger.info(
            f"[Collapse] QGlyph {glyph_id} → {collapsed} "
            f"(L:{left_score:.3f} R:{right_score:.3f} Bias:{bias_value:.3f})"
        )

        # 4️⃣ Memory trace for reconstruction and analysis
        decision_memory = {
            "glyph_id": glyph_id,
            "choice": collapsed,
            "scores": {
                "left": left_score,
                "right": right_score,
                "bias": bias_value,
            },
            "context": context or {},
        }
        store_memory({"type": "qglyph_collapse", "data": decision_memory})

        return {
            "collapsed": collapsed,
            "trace": decision_memory,
        }

    except Exception as e:
        logger.exception("[Collapse] Failed to select QGlyph path")
        return {"error": str(e)}