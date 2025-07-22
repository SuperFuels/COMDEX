# backend/modules/sqi/qglyph_generator.py

import uuid
from typing import List, Dict, Any

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