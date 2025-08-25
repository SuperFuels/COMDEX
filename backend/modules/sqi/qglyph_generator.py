# backend/modules/sqi/qglyph_generator.py

import uuid
from typing import List, Dict, Any

from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph
from backend.modules.knowledge_graph.kg_writer_singleton import KnowledgeGraphWriter
from backend.modules.codex.codex_lang_rewriter import CodexLangRewriter

class QGlyphGenerator:
    def __init__(self):
        self.generated = []

    def generate_superposed_glyph(self, base_symbol: str, states: List[str] = ["0", "1"]) -> Dict[str, Any]:
        """
        Generate a Q-Glyph in symbolic superposition: base ↔ states.
        Example: A ↔ ["0", "1"] → {"↔": ["A:0", "A:1"]}
        """
        qglyph_id = str(uuid.uuid4())
        superposed = { "↔": [f"{base_symbol}:{s}" for s in states] }

        qglyph = {
            "id": qglyph_id,
            "type": "qglyph",
            "base": base_symbol,
            "superposed": superposed,
            "states": states,
        }

        self.generated.append(qglyph)
        return qglyph

    def generate_multi_qglyph_set(self, base_symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Generate a batch of Q-Glyphs in superposed form.
        """
        return [self.generate_superposed_glyph(sym) for sym in base_symbols]

    def get_generated_log(self) -> List[Dict[str, Any]]:
        return self.generated

# -------------------------
# ✅ ADDITION: String → QGlyph Parser
# -------------------------

def generate_qglyph_from_string(raw_string: str, metadata: dict = None) -> LogicGlyph:
    """
    Converts a raw symbolic string into a Q-Glyph compatible LogicGlyph,
    with metadata injected and KG registration.

    Args:
        raw_string (str): Symbolic logic string.
        metadata (dict): Optional container, trace, entanglement info.

    Returns:
        LogicGlyph: QGlyph-compatible logic glyph.
    """
    glyph = CodexLangRewriter.parse_string_to_glyph(raw_string)

    # Mark as QGlyph and inject metadata
    if metadata:
        glyph.metadata.update(metadata)

    glyph.metadata["qglyph"] = True
    glyph.metadata["source"] = "QGlyphGen"
    glyph.metadata["entangled"] = metadata.get("entangled", False) if metadata else False

    # Inject into Knowledge Graph
    KnowledgeGraphWriter.inject_glyph(glyph)

    return glyph