# glyph_parser.py
# Part of GlyphOS symbolic runtime for AION

import re
import json
from typing import List, Dict, Optional

# NEW: For Logic tree evaluation
from backend.modules.glyphos.codexlang_translator import parse_logic_expression

# ─── 🔠 Symbol Table ────────────────────────────────────────────────────────────

glyph_index = {
    "🜁": {"name": "memory_seed", "type": "instruction", "tags": ["init", "load"]},
    "⚛": {"name": "ethic_filter", "type": "modifier", "tags": ["soul_law"]},
    "✦": {"name": "dream_trigger", "type": "event", "tags": ["reflection"]},
    "🧭": {"name": "navigation_pulse", "type": "action", "tags": ["teleport", "wormhole"]},
    "⌬": {"name": "compression_lens", "type": "modifier", "tags": ["reduce", "optimize"]},
    "⟁": {"name": "dimension_lock", "type": "barrier", "tags": ["test", "gate"]}
}

# ─── 🧩 Glyph Object ────────────────────────────────────────────────────────────

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
            "tags": self.definition.get("tags", []),
            "valid": self.is_valid()
        }

# ─── ⟦ Structured Glyph Parser ⟧ ────────────────────────────────────────────────

class StructuredGlyph:
    def __init__(self, raw: str):
        self.raw = raw
        self.parsed = self._parse()

    def _parse(self) -> Dict:
        """
        Parse glyphs in the format:
        ⟦ Type | Target : Value → Action ⟧
        Allows symbols and operators in Value/Action.
        """
        pattern = r"⟦\s*(\w+)\s*\|\s*(\w+)\s*:\s*([^\→]+?)\s*→\s*(.+?)\s*⟧"
        match = re.match(pattern, self.raw)
        if not match:
            return {
                "raw": self.raw,
                "error": "Invalid structured glyph"
            }

        result = {
            "raw": self.raw,
            "type": match.group(1).strip(),
            "target": match.group(2).strip(),
            "value": match.group(3).strip(),
            "action": match.group(4).strip()
        }

        # ✅ NEW: Logic tree evaluation hook
        if result["type"].lower() == "logic":
            try:
                logic_tree = parse_logic_expression(result["action"])
                result["tree"] = logic_tree.evaluate()
            except Exception as e:
                result["tree"] = f"Parse error: {e}"

        return result

    def to_dict(self) -> Dict:
        return self.parsed

# ─── 🔍 Unified Parser ──────────────────────────────────────────────────────────

class GlyphParser:
    def __init__(self, input_string: str):
        self.input = input_string.strip()
        self.parsed: List[Dict] = []

    def parse(self) -> List[Dict]:
        if self.input.startswith("⟦") and self.input.endswith("⟧"):
            structured = StructuredGlyph(self.input)
            self.parsed = [structured.to_dict()]
        else:
            symbols = list(self.input)
            self.parsed = [Glyph(sym).to_dict() for sym in symbols]
        return self.parsed

    def dump_json(self) -> str:
        return json.dumps(self.parse(), indent=2)

# ─── ✅ Helper: Single-Glyph Parse ──────────────────────────────────────────────

def parse_glyph(bytecode: str) -> Dict:
    parsed = GlyphParser(bytecode).parse()
    return parsed[0] if parsed else {"symbol": bytecode, "error": "Invalid glyph"}

# ─── ✅ NEW: Parse Glyph String (LEGACY HOBERMAN HOOK) ──────────────────────────

def parse_glyph_string(glyph_str: str) -> List[Dict]:
    """
    Parses a raw glyph string into tokenized glyph objects.
    E.g. "🜁⚛✦" → [{"symbol": "🜁", ...}, {"symbol": "⚛", ...}, {"symbol": "✦", ...}]
    """
    return [Glyph(sym).to_dict() for sym in glyph_str if sym.strip()]

# ─── ✅ Parse CodexLang string for instruction trees ────────────────────────────

def parse_codexlang_string(input_str: str) -> Dict:
    """
    Accepts CodexLang string like:
      ⟦ Compute | Target : A ↔ B → Result ⟧
    Returns structured instruction tree for symbolic execution.
    """
    parser = GlyphParser(input_str)
    result = parser.parse()
    return result[0] if result else {"error": "Failed to parse CodexLang string"}

# ─── 🧪 CLI Test Harness ────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        "🜁⚛✦🧭⌬⟁",
        "⟦ Write | Glyph : Self → ⬁ ⟧",
        "⟦ Logic | X : A ∧ B → ¬C ⟧",  # should show tree
        "⟦ Mutate | Cube : Logic → Dual ⟧",
        "⟦ Invalid ⟧",
        "💀✪🌌",  # invalid glyphs
    ]
    for case in test_cases:
        print(f"\nInput: {case}")
        parser = GlyphParser(case)
        print(parser.dump_json())