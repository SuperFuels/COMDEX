# File: backend/modules/symbolic_spreadsheet/sympy/sympy_sheet_executor.py
# 🧠 Task C1-C4: SymPy Sheet Executor - Executes symbolic logic, detects contradictions, prepares mutations, and triggers SQI/emotion hooks

from sympy import symbols, simplify, sympify, Eq, solve, S
from sympy.core.sympify import SympifyError
from typing import Dict, Any, List
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

_symbol_cache = {}

def execute_sympy_logic(cell: GlyphCell) -> Dict[str, Any]:
    """
    Evaluate a GlyphCell's symbolic logic using SymPy.
    Returns a dictionary with result, validation, mutation triggers, and diagnostics.
    """
    raw_logic = cell.get("logic", "")
    result = {
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

        if isinstance(expr, Eq):
            sol = solve(expr)
            result["prediction"] = str(sol) if sol else "No solution"
            if simplified == False:
                result["contradiction"] = True
                result["validated"] = False
                result["mutation_suggestion"] = "Consider revising logic for consistency"
            else:
                result["validated"] = True
        else:
            result["result"] = str(simplified)
            result["validated"] = True

        result["sqi_trigger"] = 0.1 if result["validated"] else -0.1
        result["emotion_trigger"] = "curious" if result["prediction"] else None

    except SympifyError as e:
        result["error"] = f"SympifyError: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"

    return result

def apply_sympy_to_cells(cells: List[GlyphCell]) -> List[GlyphCell]:
    """
    Iterate over all cells and attach SymPy results and mutation/SQI/emotion triggers.
    """
    enriched = []
    for cell in cells:
        sympy_out = execute_sympy_logic(cell)
        cell.update({
            "result": sympy_out["result"],
            "validated": sympy_out["validated"],
            "prediction": sympy_out["prediction"],
            "sympy_result": sympy_out["sympy_result"],
            "simplified": sympy_out["simplified"],
            "sympy_error": sympy_out["error"],
            "contradiction": sympy_out["contradiction"],
            "mutation_suggestion": sympy_out["mutation_suggestion"],
            "sqi_trigger": sympy_out["sqi_trigger"],
            "emotion_trigger": sympy_out["emotion_trigger"],
        })
        enriched.append(cell)
    return enriched