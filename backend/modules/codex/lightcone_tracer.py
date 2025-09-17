# 📄 backend/modules/codex/lightcone_tracer.py

"""
🌌 LightCone Tracer – Forward/Reverse Symbolic Execution
─────────────────────────────────────────────────────────
Traces CodexLang execution and symbolic mutation lineage
to enable LightCone-style temporal analysis across cells.
"""

from typing import List, Dict, Optional
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.symbolic.symbolic_trace_utils import trace_forward, trace_backward
from backend.modules.symbolic.symbolic_context_utils import build_context_from_cell
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.codex.qfc_websocket_bridge import broadcast_qfc_beams

codex_executor = CodexExecutor()

def execute_lightcone_forward(cells: List[GlyphCell], entry_id: str) -> List[Dict[str, any]]:
    """
    Execute forward from a starting GlyphCell through linked cells (e.g., data flow).
    """
    trace_results = []
    visited = set()

    def _walk_forward(cell: GlyphCell):
        if cell.id in visited:
            return
        visited.add(cell.id)

        ctx = build_context_from_cell(cell)
        result = codex_executor.run_glyphcell(cell, context=ctx)
        trace_results.append({"cell_id": cell.id, "result": result})

        for linked_id in cell.linked_cells or []:
            linked_cell = next((c for c in cells if c.id == linked_id), None)
            if linked_cell:
                _walk_forward(linked_cell)

    entry_cell = next((c for c in cells if c.id == entry_id), None)
    if entry_cell:
        _walk_forward(entry_cell)

    return trace_results


def execute_lightcone_reverse(cells: List[GlyphCell], target_id: str) -> List[Dict[str, any]]:
    """
    Walk backward through logic lineage (e.g., mutation parents).
    """
    trace_results = []
    visited = set()

    def _walk_back(cell: GlyphCell):
        if cell.id in visited:
            return
        visited.add(cell.id)

        ctx = build_context_from_cell(cell)
        result = codex_executor.run_glyphcell(cell, context=ctx)
        trace_results.append({"cell_id": cell.id, "result": result})

        parent_id = getattr(cell, "mutation_parent_id", None)
        if parent_id:
            parent_cell = next((c for c in cells if c.id == parent_id), None)
            if parent_cell:
                _walk_back(parent_cell)

    target_cell = next((c for c in cells if c.id == target_id), None)
    if target_cell:
        _walk_back(target_cell)

    return trace_results

def lightcone_to_qfc_nodes(trace_results: List[Dict]) -> List[Dict]:
    """
    Convert a LightCone trace into QFC holograph nodes for rendering in the HUD.
    Each trace step becomes a QFC node with metadata (cell_id, result, etc.)
    """
    qfc_nodes = []
    for step in trace_results:
        cell_id = step.get("cell_id")
        result = step.get("result", {})
        node = {
            "id": f"qfc_{cell_id}",
            "label": f"{cell_id}",
            "result": result.get("result"),
            "sqi_score": result.get("sqi_score"),
            "mutation": result.get("mutation_type", "symbolic"),
            "linked": result.get("linked_cells", []),
            "position": result.get("coord", [0, 0, 0, 0]),
        }
        qfc_nodes.append(node)
    return qfc_nodes

def broadcast_lightcone_to_qfc(trace_results: List[Dict], container_id: str):
    """
    Fire-and-forget broadcast to QFC HUD of all nodes in the LightCone trace.
    """
    nodes = lightcone_to_qfc_nodes(trace_results)
    broadcast_qfc_beams(container_id, nodes)