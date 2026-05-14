import random
import logging
from typing import List, Dict, Any, Optional
from backend.modules.codex.metric_utils import estimate_glyph_cost

logger = logging.getLogger(__name__)

def select_best_prediction(outcomes: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Evaluate list of outcome dicts and choose the most optimal one.
    Applies SQI-inspired logic score, entropy penalty, cost penalty,
    and goal alignment reward.
    """
    scored = []

    for outcome in outcomes:
        glyph = outcome.get("glyph", {})
        logic = outcome.get("logic_score", 0) or 0
        entropy = outcome.get("entropy_delta", 0) or 0
        goal_alignment = outcome.get("goal_score", 0) or 0
        cost = estimate_glyph_cost(glyph) if glyph else 0

        score = (
            (logic * 2.0) -
            (entropy * 1.5) -
            (cost * 0.8) +
            (goal_alignment * 2.5)
        )

        scored.append((score, outcome))

    if not scored:
        logger.warning("[Prediction] No outcomes could be scored. Choosing randomly.")
        return random.choice(outcomes)

    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, best_outcome = scored[0]

    logger.debug(f"[Prediction] Best score: {best_score} for outcome: {best_outcome.get('label', 'N/A')}")
    return best_outcome