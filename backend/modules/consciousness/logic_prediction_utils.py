# backend/modules/consciousness/logic_prediction_utils.py
from typing import Dict, Any, Optional


class LogicPredictionUtils:
    """
    LogicPredictionUtils - wrapper around symbolic logic analysis tools.
    Provides contradiction detection for logical ASTs (used by CognitiveDispatcher).
    """

    def __init__(self):
        pass

    def detect_contradictions(self, node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Detects contradictions in logic ASTs, such as: P(x) ∧ ¬P(x)
        Returns a contradiction report if found, else None.
        """

        def ast_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
            if a.get("type") != b.get("type"):
                return False

            if a.get("type") in {"symbol", "variable"}:
                return a.get("value") == b.get("value")

            if a.get("type") == "call":
                return (
                    a.get("name") == b.get("name") and
                    all(ast_equal(x, y) for x, y in zip(a.get("args", []), b.get("args", [])))
                )

            if a.get("type") == "not":
                return ast_equal(a.get("value"), b.get("value"))

            if a.get("type") in {"and", "or", "implies", "iff"}:
                return (
                    ast_equal(a.get("left"), b.get("left")) and
                    ast_equal(a.get("right"), b.get("right"))
                )

            return False

        if node.get("type") == "and":
            left = node.get("left")
            right = node.get("right")

            # Contradiction pattern: P(x) ∧ ¬P(x)
            if right and right.get("type") == "not":
                if ast_equal(left, right.get("value")):
                    return {
                        "expression": node,
                        "reason": "⚛ Contradiction: P(x) ∧ ¬P(x) detected",
                        "score": 0.95
                    }

            # Symmetric pattern: ¬P(x) ∧ P(x)
            if left and left.get("type") == "not":
                if ast_equal(right, left.get("value")):
                    return {
                        "expression": node,
                        "reason": "⚛ Contradiction: ¬P(x) ∧ P(x) detected",
                        "score": 0.95
                    }

        return None