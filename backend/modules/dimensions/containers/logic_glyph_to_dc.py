# backend/modules/symbolic_engine/symbolic_kernels/logic_glyph_to_dc.py

from typing import List, Dict, Any
from .logic_glyphs import LogicGlyph

def serialize_logic_glyph(glyph: LogicGlyph) -> Dict[str, Any]:
    return {
        "type": glyph.__class__.__name__,
        "symbol": glyph.symbol,
        "operands": [
            serialize_logic_glyph(op) if isinstance(op, LogicGlyph) else op
            for op in glyph.operands
        ],
        "metadata": glyph.metadata
    }

def inject_logic_glyph_trace(container_trace: Dict[str, Any], glyph_tree: LogicGlyph, label: str = "logic"):
    """
    Injects serialized logic glyph trace into .dc container format.
    """
    logic_trace = serialize_logic_glyph(glyph_tree)

    if "trace" not in container_trace:
        container_trace["trace"] = {}

    container_trace["trace"][label] = logic_trace