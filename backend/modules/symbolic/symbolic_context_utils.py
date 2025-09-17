# 📄 backend/modules/symbolic/symbolic_context_utils.py

"""
🧠 Symbolic Context Utils
───────────────────────────────
Build CodexLang execution context from a GlyphCell.
Used by LightCone, CodexExecutor, SQI scoring, and pattern agents.
"""

from typing import Dict, Any
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

def build_context_from_cell(cell: GlyphCell) -> Dict[str, Any]:
    """
    Generate execution context from GlyphCell for CodexLang or beam tracing.

    Returns:
        A dictionary of execution context.
    """
    return {
        "cell_id": cell.id,
        "emotion": cell.emotion,
        "coord": cell.position,
        "linked": cell.linked_cells,
        "nested": cell.nested_logic,
        "container_id": getattr(cell, "container_id", "unknown_container"),
        "mutation_parent_id": getattr(cell, "mutation_parent_id", None),
        "mutation_type": getattr(cell, "mutation_type", None),
        "sqi": getattr(cell, "sqi_score", 0.0),
        "trace": cell.trace,
        "validated": cell.validated,
        "result": cell.result,
        "prediction": cell.prediction,
    }