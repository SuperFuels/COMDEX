# glyph_parser.py
# Part of GlyphOS symbolic runtime for AION

import re
import json
from typing import List, Dict, Optional

# NEW: For Logic tree evaluation
from backend.modules.glyphos.codexlang_translator import parse_logic_expression

# NEW: Canonical instruction metadata bridge
from backend.codexcore_virtual.instruction_metadata_bridge import get_instruction_metadata

# ─── 🔠 Symbol Table ────────────────────────────────────────────────────────────
# GlyphOS-only symbols (don’t exist in CodexCore)
glyph_index = {
    "🜁": {"name": "memory_seed", "type": "instruction", "tags": ["init", "load"]},
    "⚛": {"name": "ethic_filter", "type": "modifier", "tags": ["soul_law"]},
    "✦": {"name": "dream_trigger", "type": "event", "tags": ["reflection"]},
    "🧭": {"name": "navigation_pulse", "type": "action", "tags": ["teleport", "wormhole"]},
    "⌬": {"name": "compression_lens", "type": "modifier", "tags": ["reduce", "optimize"]},
    "⟁": {"name": "dimension_lock", "type": "barrier", "tags": ["test", "gate"]}
}

# ─── Helper: Domain Resolver ────────────────────────────────────────────────────

def resolve_symbol(symbol: str) -> Dict:
    """
    Resolve a glyph/operator into a domain-tagged entry.
    """
    meta = get_instruction_metadata(symbol)
    if meta:  # Symbol is in canonical instruction set
        domain = meta.get("domain", "unknown")
        return {
            "symbol": symbol,
            "opcode": f"{domain}:{symbol}",
            "name": meta.get("name", "unknown"),
            "type": meta.get("type", "operator"),
            "tags": meta.get("tags", []),
            "valid": True,
        }
    # Fallback: GlyphOS-only glyphs
    return {
        "symbol": symbol,
        "opcode": "glyph:" + symbol,
        "name": glyph_index.get(symbol, {}).get("name", "unknown"),
        "type": glyph_index.get(symbol, {}).get("type", "unknown"),
        "tags": glyph_index.get(symbol, {}).get("tags", []),
        "valid": bool(glyph_index.get(symbol)),
    }

# ─── 🧩 Glyph Object ────────────────────────────────────────────────────────────

class Glyph:
    def __init__(self, symbol: str):
        self.entry = resolve_symbol(symbol)

    def to_dict(self) -> Dict:
        return self.entry

# ─── ⟦ Structured Glyph Parser ⟧ ────────────────────────────────────────────────

class StructuredGlyph:
    def __init__(self, raw: str):
        self.raw = raw
        self.parsed = self._parse()

    def _parse(self) -> Dict:
        """
        Parse glyphs in the canonical structure:
            ⟦ Type | Target : Value → Action ⟧

        - Adds SoulLaw compliance metadata
        - Guards against malformed CodexLang
        - Always returns a well-formed dict (never raises)
        """
        import logging
        from backend.modules.glyphos.codexlang_translator import parse_action_expr, translate_node
        from backend.modules.glyphos.symbol_resolver import resolve_symbol
        from backend.modules.logic.logic_parser import parse_logic_expression

        pattern = r"⟦\s*(\w+)\s*\|\s*(\w+)\s*:\s*([^\→]+?)\s*→\s*(.+?)\s*⟧"
        match = re.match(pattern, self.raw)

        # ─────────────────────────────────────────────
        # Invalid glyph structure → return compliant stub
        # ─────────────────────────────────────────────
        if not match:
            logging.warning(f"[GlyphParser] ⚠️ Invalid structured glyph: {self.raw}")
            return {
                "raw": self.raw,
                "error": "Invalid structured glyph",
                "soul_law_compliance": "violated",
                "type": "unknown",
                "target": None,
                "value": None,
                "action_raw": None,
                "action": {"op": "invalid", "args": []},
                "value_resolved": [],
                "action_resolved": [],
            }

        raw_action = match.group(4).strip()

        # ─────────────────────────────────────────────
        # Parse and canonicalize action expression
        # ─────────────────────────────────────────────
        try:
            parsed_action = parse_action_expr(raw_action)
            parsed_action = translate_node(parsed_action)
        except Exception as e:
            logging.warning(f"[GlyphParser] ⚠️ Action parse failed: {e} | raw={raw_action}")
            parsed_action = {"op": f"unknown:{raw_action}", "args": []}

        result = {
            "raw": self.raw,
            "type": match.group(1).strip(),
            "target": match.group(2).strip(),
            "value": match.group(3).strip(),
            "action_raw": raw_action,
            "action": parsed_action,
            "soul_law_compliance": "pass",  # default unless logic fails
        }

        # ─────────────────────────────────────────────
        # Resolve internal symbols (value/action)
        # ─────────────────────────────────────────────
        def _resolve_field(val):
            if isinstance(val, str):
                # Split simple strings into token symbols
                symbols = [s for s in re.split(r"[\s,]+", val.strip()) if s]
                return [resolve_symbol(sym) for sym in symbols]
            elif isinstance(val, dict):
                return [resolve_symbol(val.get("op", ""))]
            return []

        for field in ("value", "action"):
            try:
                result[f"{field}_resolved"] = _resolve_field(result[field])
            except Exception as e:
                logging.warning(f"[GlyphParser] Failed to resolve field '{field}': {e}")
                result[f"{field}_resolved"] = []

        # ─────────────────────────────────────────────
        # Logic evaluation hook (optional)
        # ─────────────────────────────────────────────
        if result["type"].lower() == "logic":
            try:
                logic_tree = parse_logic_expression(raw_action)
                result["tree"] = logic_tree.evaluate()
            except Exception as e:
                result["tree"] = f"Parse error: {e}"
                result["soul_law_compliance"] = "violated"

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
        return json.dumps(self.parse(), indent=2, ensure_ascii=False)

# ─── ✅ Helper: Single-Glyph Parse ──────────────────────────────────────────────

from backend.modules.codex.canonical_ops import CANONICAL_OPS

def parse_glyph(symbol: str) -> dict:
    """
    Parse a single glyph into a canonical instruction dict.
    """
    canonical = CANONICAL_OPS.get(symbol)
    if not canonical:
        return {"op": f"unknown:{symbol}"}
    return {"op": canonical}

# ─── ✅ NEW: Parse Glyph String (LEGACY HOBERMAN HOOK) ──────────────────────────

def parse_glyph_string(glyph_str: str) -> List[Dict]:
    """
    Parses a raw glyph string into tokenized glyph objects.
    E.g. "🜁⚛✦" → [{"symbol": "🜁", ...}, {"symbol": "⚛", ...}, {"symbol": "✦", ...}]
    """
    return [Glyph(sym).to_dict() for sym in glyph_str if sym.strip()]

# ─── ✅ Parse CodexLang string for instruction trees ────────────────────────────

def parse_codexlang_string(input_str: str) -> Dict:
    try:
        parser = GlyphParser(input_str)
        result = parser.parse()
        return result[0] if result else {"error": "Failed to parse CodexLang string"}
    except Exception as e:
        return {"error": f"CodexLang parse failed: {e}"}

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