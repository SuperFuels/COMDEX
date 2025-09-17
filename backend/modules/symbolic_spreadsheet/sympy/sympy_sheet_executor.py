# 📄 backend/modules/symbolic_spreadsheet/sympy/sympy_sheet_executor.py
# 🧠 Task C1-C4: SymPy Sheet Executor - Executes symbolic logic, detects contradictions, prepares mutations, and triggers SQI/emotion hooks

from sympy import symbols, simplify, sympify, Eq, solve, S
from sympy.core.sympify import SympifyError
from typing import Dict, Any, List
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
import logging

logger = logging.getLogger(__name__)

_symbol_cache: Dict[str, Any] = {}

def execute_sympy_logic(cell: GlyphCell) -> Dict[str, Any]:
    """
    Evaluate a GlyphCell's symbolic logic using SymPy.
    Returns a dictionary with result, validation, mutation triggers, and diagnostics.
    """
    raw_logic = getattr(cell, "logic", "")
    result: Dict[str, Any] = {
        "result": None,
        "validated": False,
        "contradiction": False,
        "sympy_result": None,
        "simplified": None,
        "prediction": None,
        "mutation_suggestion": None,
        "sqi_trigger": 0.0,
        "emotion_trigger": None,
        "error": None,
    }

    try:
        if raw_logic not in _symbol_cache:
            _symbol_cache[raw_logic] = sympify(raw_logic)
        expr = _symbol_cache[raw_logic]
        result["sympy_result"] = expr

        simplified = simplify(expr)
        result["simplified"] = str(simplified)

        # Detect contradictions
        contradiction = False
        if isinstance(expr, Eq):
            sol = solve(expr)
            result["prediction"] = str(sol) if sol else "No solution"
            if not sol:
                contradiction = True
                result["mutation_suggestion"] = "Consider revising logic for consistency"
            result["validated"] = not contradiction
        else:
            result["result"] = str(simplified)
            result["validated"] = True

        result["contradiction"] = contradiction

        # SQI / Emotion triggers
        result["sqi_trigger"] = 0.1 if result["validated"] else -0.1
        result["emotion_trigger"] = "curious" if result["prediction"] else None

    except SympifyError as e:
        result["error"] = f"SympifyError: {str(e)}"
        logger.warning(f"[SymPy] SympifyError in cell {getattr(cell, 'id', 'unknown')}: {e}")
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        logger.warning(f"[SymPy] Unexpected error in cell {getattr(cell, 'id', 'unknown')}: {e}")

    return result


def apply_sympy_to_cells(cells: List[GlyphCell]) -> List[GlyphCell]:
    """
    Iterate over all cells and attach SymPy results and mutation/SQI/emotion triggers.
    """
    enriched: List[GlyphCell] = []
    for cell in cells:
        sympy_out = execute_sympy_logic(cell)

        # Update cell attributes safely
        cell.result = sympy_out.get("result")
        cell.validated = sympy_out.get("validated")
        cell.prediction = sympy_out.get("prediction")
        cell.sympy_result = sympy_out.get("sympy_result")
        cell.simplified = sympy_out.get("simplified")
        cell.sympy_error = sympy_out.get("error")
        cell.contradiction = sympy_out.get("contradiction")
        cell.mutation_suggestion = sympy_out.get("mutation_suggestion")
        cell.sqi_trigger = sympy_out.get("sqi_trigger")
        cell.emotion_trigger = sympy_out.get("emotion_trigger")

        # Optional: update SQI immediately
        try:
            cell.sqi_score = score_sqi(cell)
        except Exception as e:
            logger.warning(f"[SQI] Failed to score SQI for cell {cell.id}: {e}")

        enriched.append(cell)

    return enriched