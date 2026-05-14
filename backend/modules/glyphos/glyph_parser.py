# glyph_parser.py
# Part of GlyphOS symbolic runtime for AION

from __future__ import annotations

import re
import json
import logging
from typing import List, Dict, Optional, Any

# NEW: Canonical instruction metadata bridge (metadata only; not authoritative)
from backend.codexcore_virtual.instruction_metadata_bridge import get_instruction_metadata

# Canonical ops map (fast-path)
from backend.modules.codex.canonical_ops import CANONICAL_OPS

logger = logging.getLogger(__name__)

# ─── 🔠 Symbol Table ────────────────────────────────────────────────────────────
# GlyphOS-only symbols (don't exist in CodexCore)
glyph_index = {
    "🜁": {"name": "memory_seed", "type": "instruction", "tags": ["init", "load"]},
    "⚛": {"name": "ethic_filter", "type": "modifier", "tags": ["soul_law"]},
    "✦": {"name": "dream_trigger", "type": "event", "tags": ["reflection"]},
    "🧭": {"name": "navigation_pulse", "type": "action", "tags": ["teleport", "wormhole"]},
    "⌬": {"name": "compression_lens", "type": "modifier", "tags": ["reduce", "optimize"]},
    "⟁": {"name": "dimension_lock", "type": "barrier", "tags": ["test", "gate"]},
}

# These sets are only used if some caller wants explicit mode routing later.
_PHOTON_OPS = {"⊕", "⊗", "↔", "⊖", "¬", "★", "∅", "≈", "⊂"}
_SYMATICS_OPS = {"⊕", "⊗", "↔", "⊖", "⟲", "μ", "π", "⋈", "↺"}


def resolve_opcode(symbol: str, mode: Optional[str] = None) -> str:
    """
    Resolve a raw symbol into a canonical opcode with the correct precedence:

      1) already-canonical (contains ':')
      2) explicit mode override (photon:/symatics:) for known operators
      3) collision_resolver (authoritative if present)
      4) CANONICAL_OPS table
      5) symbolic_instruction_set legacy aliases
      6) instruction_metadata_bridge domain (LAST resort)
      7) unknown:<symbol>

    This avoids metadata forcing "logic:" onto symbols that are actually handled
    elsewhere (photon/symatics/quantum collisions).
    """
    if not symbol:
        return "unknown:∅"

    if ":" in symbol:
        return symbol

    if mode == "photon" and symbol in _PHOTON_OPS:
        return f"photon:{symbol}"
    if mode == "symatics" and symbol in _SYMATICS_OPS:
        return f"symatics:{symbol}"

    # Prefer collision resolver (knows global priority rules)
    try:
        from backend.modules.codex.collision_resolver import resolve_op

        try:
            r = resolve_op(symbol, mode=mode)  # newer signatures
        except TypeError:
            r = resolve_op(symbol)             # older signatures

        if isinstance(r, str) and r:
            return r
    except Exception:
        pass

    # Canonical ops table
    r = CANONICAL_OPS.get(symbol)
    if isinstance(r, str) and r:
        return r

    # Legacy shim (hard aliases)
    try:
        from backend.codexcore_virtual import symbolic_instruction_set as sis

        return sis.get_opcode(symbol)
    except Exception:
        pass

    # Metadata LAST (only when nothing else can resolve it)
    meta = get_instruction_metadata(symbol)
    if meta:
        return f"{meta.get('domain', 'unknown')}:{symbol}"

    return f"unknown:{symbol}"


# ─── Helper: Domain Resolver ────────────────────────────────────────────────────

def resolve_symbol(symbol: str) -> Dict[str, Any]:
    """
    Resolve a glyph/operator into a domain-tagged entry.

    IMPORTANT: opcode resolution does NOT trust metadata first.
    Metadata is informational; canonicalization is handled by resolve_opcode().
    """
    # GlyphOS-only glyphs take priority (they're not in canonical tables)
    if symbol in glyph_index:
        meta = glyph_index[symbol]
        return {
            "symbol": symbol,
            "opcode": f"glyph:{symbol}",
            "name": meta.get("name", "unknown"),
            "type": meta.get("type", "unknown"),
            "tags": meta.get("tags", []),
            "valid": True,
        }

    meta = get_instruction_metadata(symbol) or {}
    opcode = resolve_opcode(symbol)

    return {
        "symbol": symbol,
        "opcode": opcode,
        "name": meta.get("name", "unknown"),
        "type": meta.get("type", "operator"),
        "tags": meta.get("tags", []),
        "valid": not opcode.startswith("unknown:"),
    }


# ─── 🧩 Glyph Object ────────────────────────────────────────────────────────────

class Glyph:
    def __init__(self, symbol: str):
        self.entry = resolve_symbol(symbol)

    def to_dict(self) -> Dict[str, Any]:
        return self.entry


# ─── ⟦ Structured Glyph Parser ⟧ ────────────────────────────────────────────────

class StructuredGlyph:
    def __init__(self, raw: str):
        self.raw = raw
        self.parsed = self._parse()

    def _parse(self) -> Dict[str, Any]:
        """
        Parse glyphs in the canonical structure:
            ⟦ Type | Target : Value -> Action ⟧

        - Adds SoulLaw compliance metadata
        - Guards against malformed CodexLang
        - Always returns a well-formed dict (never raises)
        """
        from backend.modules.glyphos.codexlang_translator import parse_action_expr, translate_node

        pattern = r"⟦\s*(\w+)\s*\|\s*(\w+)\s*:\s*([^\->]+?)\s*->\s*(.+?)\s*⟧"
        match = re.match(pattern, self.raw)

        if not match:
            logger.warning(f"[GlyphParser] ⚠️ Invalid structured glyph: {self.raw}")
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

        # Parse and canonicalize action expression
        try:
            parsed_action = parse_action_expr(raw_action)
            parsed_action = translate_node(parsed_action)
        except Exception as e:
            logger.warning(f"[GlyphParser] ⚠️ Action parse failed: {e} | raw={raw_action}")
            parsed_action = {"op": f"unknown:{raw_action}", "args": []}

        result: Dict[str, Any] = {
            "raw": self.raw,
            "type": match.group(1).strip(),
            "target": match.group(2).strip(),
            "value": match.group(3).strip(),
            "action_raw": raw_action,
            "action": parsed_action,
            "soul_law_compliance": "pass",  # default unless logic fails
        }

        # Resolve internal symbols (value/action)
        def _resolve_field(val: Any) -> List[Dict[str, Any]]:
            if isinstance(val, str):
                symbols = [s for s in re.split(r"[\s,]+", val.strip()) if s]
                return [resolve_symbol(sym) for sym in symbols]
            if isinstance(val, dict):
                op = val.get("op") or val.get("opcode") or ""
                # If op is canonical like "logic:⊕", "resolve_symbol" expects raw glyph,
                # so strip domain if present.
                raw = op.split(":")[-1] if isinstance(op, str) else ""
                return [resolve_symbol(raw)] if raw else []
            return []

        for field in ("value", "action"):
            try:
                result[f"{field}_resolved"] = _resolve_field(result[field])
            except Exception as e:
                logger.warning(f"[GlyphParser] Failed to resolve field '{field}': {e}")
                result[f"{field}_resolved"] = []

        # Logic evaluation hook (optional)
        if result.get("type", "").lower() == "logic":
            try:
                from backend.modules.logic.logic_parser import parse_logic_expression
                logic_tree = parse_logic_expression(raw_action)
                result["tree"] = logic_tree.evaluate()
            except Exception as e:
                result["tree"] = f"Parse error: {e}"
                result["soul_law_compliance"] = "violated"

        return result

    def to_dict(self) -> Dict[str, Any]:
        return self.parsed


# ─── 🔍 Unified Parser ──────────────────────────────────────────────────────────

class GlyphParser:
    def __init__(self, input_string: str):
        self.input = input_string.strip()
        self.parsed: List[Dict[str, Any]] = []

    def parse(self) -> List[Dict[str, Any]]:
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

def parse_glyph(symbol: str) -> dict:
    """
    Parse a single glyph into a canonical instruction dict.
    """
    canonical = resolve_opcode(symbol)
    if canonical.startswith("unknown:"):
        return {"op": canonical}
    return {"op": canonical}


# ─── ✅ NEW: Parse Glyph String (LEGACY HOBERMAN HOOK) ──────────────────────────

def parse_glyph_string(glyph_str: str) -> List[Dict[str, Any]]:
    """
    Parses a raw glyph string into tokenized glyph objects.
    E.g. "🜁⚛✦" -> [{"symbol": "🜁", ...}, {"symbol": "⚛", ...}, {"symbol": "✦", ...}]
    """
    return [Glyph(sym).to_dict() for sym in glyph_str if sym.strip()]


# ─── ✅ Parse CodexLang string for instruction trees ────────────────────────────

def parse_codexlang_string(input_str: str) -> Dict[str, Any]:
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
        "⟦ Write | Glyph : Self -> ⬁ ⟧",
        "⟦ Logic | X : A ∧ B -> ¬C ⟧",  # should show tree
        "⟦ Mutate | Cube : Logic -> Dual ⟧",
        "⟦ Invalid ⟧",
        "💀✪🌌",  # invalid glyphs
    ]
    for case in test_cases:
        print(f"\nInput: {case}")
        parser = GlyphParser(case)
        print(parser.dump_json())