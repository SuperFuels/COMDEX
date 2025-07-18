# glyph_parser.py
# Part of GlyphOS symbolic runtime for AION

import re
import json
from typing import List, Dict, Optional, Union

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


class StructuredGlyph:
    def __init__(self, raw: str):
        self.raw = raw
        self.parsed = self._parse()

    def _parse(self) -> Dict:
        """
        Parse glyphs in the format:
        ⟦ Type | Target : Value → Action ⟧
        """
        pattern = r"⟦\s*(\w+)\s*\|\s*(\w+)\s*:\s*([\w\d\s\-]+)\s*→\s*([\S]+)\s*⟧"
        match = re.match(pattern, self.raw)
        if not match:
            return {
                "raw": self.raw,
                "error": "Invalid structured glyph"
            }

        return {
            "raw": self.raw,
            "type": match.group(1).strip(),
            "target": match.group(2).strip(),
            "value": match.group(3).strip(),
            "action": match.group(4).strip()
        }

    def to_dict(self) -> Dict:
        return self.parsed


class GlyphParser:
    def __init__(self, input_string: str):
        self.input = input_string.strip()
        self.parsed: List[Dict] = []

    def parse(self) -> List[Dict]:
        if self.input.startswith("⟦") and self.input.endswith("⟧"):
            # Structured glyph
            structured = StructuredGlyph(self.input)
            self.parsed = [structured.to_dict()]
        else:
            # Individual glyphs
            symbols = list(self.input)
            self.parsed = [Glyph(sym).to_dict() for sym in symbols if Glyph(sym).is_valid()]
        return self.parsed

    def dump_json(self) -> str:
        return json.dumps(self.parse(), indent=2)


# ✅ Top-level helper for other modules
def parse_glyph(bytecode: str) -> Dict:
    parsed = GlyphParser(bytecode).parse()
    return parsed[0] if parsed else {"symbol": bytecode, "error": "Invalid glyph"}


# 🔁 CLI test
if __name__ == "__main__":
    test_cases = [
        "🜁⚛✦🧭⌬⟁",
        "⟦ Write | Glyph : Self → ⬁ ⟧",
        "⟦ Mutate | Cube : Logic → Dual ⟧",
        "⟦ Invalid ⟧"
    ]
    for case in test_cases:
        print(f"Input: {case}")
        parser = GlyphParser(case)
        print(parser.dump_json())
        print("---")