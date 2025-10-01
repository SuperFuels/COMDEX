# 📁 backend/codexcore_virtual/instruction_parser.py

import re
from typing import List, Dict, Any
from backend.codexcore_virtual.instruction_metadata_bridge import get_instruction_metadata
from backend.modules.codex.virtual.instruction_parser import parse_codexlang


def resolve_opcode(symbol: str, mode: str = None) -> str:
    """
    Resolve a raw symbol into a domain-tagged opcode.
    Photon/Symatics mode bypasses metadata to avoid 'logic:' stubs.
    """

    # Direct bypass for symbolic algebras
    if mode in {"photon", "symatics"}:
        return f"{mode}:{symbol}"

    # Default metadata path
    meta = get_instruction_metadata(symbol)
    if not meta:
        return f"logic:{symbol}"
    return f"{meta.get('domain', 'logic')}:{symbol}"


def tokenize_with_parens(segment: str) -> List[str]:
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
    """
    instructions: List[Dict[str, Any]] = []

    # Split at top-level => sequence operator
    segments = re.split(r"\s*=>\s*", codex_str)

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

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

            # recurse if inner contains operators
            if any(sym in inner for sym in ["→", "⊕", "⊗", "↔", "⟲"]):
                inner_instrs = parse_codex_instructions(inner, mode=mode)
                instructions.append({"opcode": resolved, "args": inner_instrs})
            else:
                instructions.append({"opcode": resolved, "args": [inner]})
            continue

        # ── Binary ops (⊕, →, ⊗, ↔) ──────────────────────────────
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
                    instructions.append({"opcode": resolved, "args": [left, right]})
                    handled = True
            i += 1

        # ── Literal fallback ─────────────────────────────────────
        if not handled:
            instructions.append({"opcode": "logic:print", "args": [segment]})

    return instructions


# 🧪 CLI Debug Harness
if __name__ == "__main__":
    samples = [
        "A ⊕ B",
        "X → Y",
        "⟲(Reflect)",
        "A ⊕ B → C",
        "A ⊕ B → C => ⟲(Loop)",
        "⟲(A ⊕ B)",
        "(A ⊕ B) → C",
        "⟲((A ⊕ B) → C)",
        "NoteThisLiteral",
    ]
    for s in samples:
        print(f"\nInput: {s}")
        print("Photon:", parse_codex_instructions(s, mode="photon"))
        print("Symatics:", parse_codex_instructions(s, mode="symatics"))
        print("Raw:", parse_codex_instructions(s))
