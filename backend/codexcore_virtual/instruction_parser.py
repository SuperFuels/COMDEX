# ===============================
# 📁 backend/codexcore_virtual/instruction_parser.py
# ===============================

import re
import logging
from typing import List, Dict, Any

from backend.codexcore_virtual.instruction_metadata_bridge import get_instruction_metadata
from backend.modules.codex.virtual.instruction_parser import parse_codexlang  # ✅ Unified parser import

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def resolve_opcode(symbol: str, mode: str = None) -> str:
    """
    Resolve a raw symbol into a domain-tagged opcode.
    Photon/Symatics mode bypasses metadata to avoid 'logic:' stubs.
    """
    # Explicit override for photon/symatics
    if mode in {"photon", "symatics"}:
        resolved = f"{mode}:{symbol}"
        logger.debug(f"[resolve_opcode] mode={mode}, symbol={symbol} -> {resolved}")
        return resolved

    # Metadata-driven resolution
    meta = get_instruction_metadata(symbol) or {}
    domain = meta.get("domain", "logic")
    resolved = f"{domain}:{symbol}"
    logger.debug(f"[resolve_opcode] mode={mode}, symbol={symbol}, meta={meta} -> {resolved}")
    return resolved


def tokenize_with_parens(segment: str) -> List[str]:
    """
    Tokenize a segment into top-level tokens while respecting parentheses depth.
    """
    tokens, buf, depth = [], "", 0
    for ch in segment:
        if ch == "(":
            depth += 1
            buf += ch
        elif ch == ")":
            depth -= 1
            buf += ch
        elif ch.isspace() and depth == 0:
            if buf:
                tokens.append(buf)
                buf = ""
        else:
            buf += ch
    if buf:
        tokens.append(buf)
    return tokens


def parse_codex_instructions(codex_str: str, mode: str = None) -> List[Dict[str, Any]]:
    """
    Parses a CodexLang glyph string into a list of symbolic CPU instructions.
    Handles chained ops, sequences (=>), and nested parentheses properly.
    SoulLaw-aligned, metadata-safe.
    """
    if not codex_str or not codex_str.strip():
        return []

    # Normalize operators for compatibility
    codex_str = codex_str.replace("->", "→").replace("<->", "↔")

    instructions: List[Dict[str, Any]] = []

    # Split at top-level => sequence operator
    segments = re.split(r"\s*=>\s*", codex_str)

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        logger.debug(f"[parser] Processing segment='{segment}' mode={mode}")

        # ── Parenthesized expression at top level ─────────────────
        if segment.startswith("(") and segment.endswith(")"):
            inner_instrs = parse_codex_instructions(segment[1:-1], mode=mode)
            if len(inner_instrs) == 1:
                instructions.append(inner_instrs[0])
            else:
                instructions.extend(inner_instrs)
            continue

        # ── Function-style ops (⟲(expr)) ─────────────────────────
        match = re.match(r"(\S+)\((.*)\)", segment)
        if match:
            op = match.group(1)
            inner = match.group(2).strip()
            resolved = resolve_opcode(op, mode)
            logger.debug(f"[parser] Function-style op={op} resolved={resolved}")

            if any(sym in inner for sym in ["→", "⊕", "⊗", "↔", "⊖", "⟲"]):
                inner_instrs = parse_codex_instructions(inner, mode=mode)
                instructions.append({
                    "opcode": resolved,
                    "args": inner_instrs,
                    "meta": {"mode": mode or "logic", "pattern": "function"}
                })
            else:
                instructions.append({
                    "opcode": resolved,
                    "args": [inner],
                    "meta": {"mode": mode or "logic", "pattern": "function"}
                })
            continue

        # ── Binary ops (⊕, →, ⊗, ↔, ⊖) ──────────────────────────
        tokens = tokenize_with_parens(segment)
        i = 0
        handled = False
        while i < len(tokens):
            tok = tokens[i]
            if tok in {"→", "⊕", "⊗", "↔", "⊖"}:
                if i > 0 and i + 1 < len(tokens):
                    left, right = tokens[i - 1], tokens[i + 1]

                    if isinstance(left, str) and left.startswith("(") and left.endswith(")"):
                        left = parse_codex_instructions(left[1:-1], mode=mode)
                        if len(left) == 1:
                            left = left[0]
                    if isinstance(right, str) and right.startswith("(") and right.endswith(")"):
                        right = parse_codex_instructions(right[1:-1], mode=mode)
                        if len(right) == 1:
                            right = right[0]

                    resolved = resolve_opcode(tok, mode)
                    logger.debug(f"[parser] Binary op={tok} resolved={resolved}")
                    instructions.append({
                        "opcode": resolved,
                        "args": [left, right],
                        "meta": {"mode": mode or "logic", "pattern": "binary"}
                    })
                    handled = True
            i += 1

        # ── Literal fallback ─────────────────────────────────────
        if not handled:
            resolved = resolve_opcode(segment, mode)
            logger.debug(f"[parser] Literal fallback segment={segment} resolved={resolved}")
            instructions.append({
                "opcode": resolved,
                "args": [],
                "meta": {"mode": mode or "logic", "pattern": "literal"}
            })

    # 🧠 Optional SoulLaw validation hook
    try:
        from backend.modules.glyphvault.soul_law_validator import soul_law_validator
        if not soul_law_validator.validate_container({"instructions": instructions}):
            logger.warning("[SoulLaw] Validation failed: instruction sequence may violate SoulLaw")
    except Exception:
        pass  # Silent fail for environments without validator

    return instructions


# 🧪 CLI Debug Harness
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    samples = [
        "A ⊕ B",
        "X → Y",
        "⟲(Reflect)",
        "A ⊕ B → C",
        "A ⊕ B → C => ⟲(Loop)",
        "⟲(A ⊕ B)",
        "(A ⊕ B) → C",
        "⟲((A ⊕ B) → C)",
        "A ⊖ ∅",           # ✅ test subtraction
        "NoteThisLiteral",
    ]

    for s in samples:
        print(f"\nInput: {s}")
        print("Photon:", parse_codex_instructions(s, mode="photon"))
        print("Symatics:", parse_codex_instructions(s, mode="symatics"))
        print("Raw:", parse_codex_instructions(s))