# glyph_parser.py
# Part of GlyphOS symbolic runtime for AION

import re
import json
from typing import List, Dict, Optional

# Sample glyph structure for bootloading reference
glyph_index = {
    "🜁": {"name": "memory_seed", "type": "instruction", "tags": ["init", "load"]},
    "⚛": {"name": "ethic_filter", "type": "modifier", "tags": ["soul_law"]},
    "✦": {"name": "dream_trigger", "type": "event", "tags": ["reflection"]},
    "🧭": {"name": "navigation_pulse", "type": "action", "tags": ["teleport", "wormhole"]},
    "⌬": {"name": "compression_lens", "type": "modifier", "tags": ["reduce", "optimize"]},
    "⟁": {"name": "dimension_lock", "type": "barrier", "tags": ["test", "gate"]}
}

class Glyph:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.definition = glyph_index.get(symbol, {})

    def is_valid(self) -> bool:
        return bool(self.definition)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "name": self.definition.get("name", "unknown"),
            "type": self.definition.get("type", "unknown"),
            "tags": self.definition.get("tags", [])
        }

class GlyphParser:
    def __init__(self, input_string: str):
        self.input = input_string
        self.parsed: List[Glyph] = []

    def parse(self) -> List[Dict]:
        symbols = list(self.input.strip())
        self.parsed = [Glyph(sym) for sym in symbols if Glyph(sym).is_valid()]
        return [g.to_dict() for g in self.parsed]

    def dump_json(self) -> str:
        return json.dumps(self.parse(), indent=2)

# ✅ Add this top-level helper for other modules to import
def parse_glyph(bytecode: str) -> Dict:
    parsed = GlyphParser(bytecode).parse()
    return parsed[0] if parsed else {"symbol": bytecode, "error": "Invalid glyph"}

# 🔁 CLI test
if __name__ == "__main__":
    test_string = "🜁⚛✦🧭⌬⟁"
    parser = GlyphParser(test_string)
    print(parser.dump_json())