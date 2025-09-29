# ===============================
# 📁 backend/codexcore_virtual/instruction_parser.py
# ===============================
"""
CodexCore Virtual Instruction Parser

Parses CodexLang glyph strings into a flat list of instructions.
Each instruction is a dict: {"opcode": str, "args": list}.
Op symbols are resolved into domain-tagged form via metadata bridge.
Now patched to handle chained/multi-op expressions and nested parentheses.
"""

import re
from typing import List, Dict, Any
from backend.codexcore_virtual.instruction_metadata_bridge import get_instruction_metadata


# ─── Opcode Resolver ────────────────────────────────────────────────────────────

def resolve_opcode(symbol: str) -> str:
    """
    Resolve a raw symbol into a domain-tagged opcode
    using the canonical metadata bridge.
    Example: "⊗" → "physics:⊗"
    """
    meta = get_instruction_metadata(symbol)
    domain = meta.get("domain", "unknown")
    return f"{domain}:{symbol}"


# ─── Tokenizer ─────────────────────────────────────────────────────────────────

def tokenize_with_parens(segment: str) -> List[str]:
    """
    Split a string into tokens but keep parentheses groups intact.
    Example: "⟲((A ⊕ B) → C)" → ["⟲", "((A ⊕ B) → C)"]
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


# ─── Parser ────────────────────────────────────────────────────────────────────

def parse_codex_instructions(codex_str: str) -> List[Dict[str, Any]]:
    """
    Parses a CodexLang glyph string into a list of symbolic CPU instructions.
    Emits domain-tagged opcodes (e.g., physics:⊗ instead of just ⊗).
    Handles chained operations (A ⊕ B → C), sequences (=>), and nested parentheses.
    """
    instructions: List[Dict[str, Any]] = []

    # Split at top-level => sequence operator
    segments = re.split(r"\s*=>\s*", codex_str)

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        # Handle ⟲(Action) style or ⟲((expr))
        match = re.match(r"(\S+)\((.*)\)", segment)
        if match:
            op = match.group(1)
            inner = match.group(2).strip()
            resolved = resolve_opcode(op)

            # If the inside looks like an expression, recurse
            if any(sym in inner for sym in ["→", "⊕", "↔", "⟲"]):
                inner_instrs = parse_codex_instructions(inner)
                instructions.append({"opcode": resolved, "args": inner_instrs})
            else:
                instructions.append({"opcode": resolved, "args": [inner]})
            continue

        # Handle binary ops
        tokens = tokenize_with_parens(segment)
        i = 0
        while i < len(tokens):
            tok = tokens[i]

            if tok in {"→", "⊕"}:
                if i > 0 and i + 1 < len(tokens):
                    left, right = tokens[i - 1], tokens[i + 1]

                    # Recurse if left/right are parenthesized groups
                    if left.startswith("(") and left.endswith(")"):
                        left = parse_codex_instructions(left[1:-1])
                    if right.startswith("(") and right.endswith(")"):
                        right = parse_codex_instructions(right[1:-1])

                    resolved = resolve_opcode(tok)
                    instructions.append({"opcode": resolved, "args": [left, right]})
            i += 1

        # Fallback if no known operators found
        if not any(op["opcode"].endswith(("→", "⊕", "⟲", "↔")) for op in instructions):
            instructions.append({"opcode": "logic:print", "args": [segment]})

    return instructions


# ─── 🧪 CLI Debug Harness ──────────────────────────────────────────────────────

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
        print(parse_codex_instructions(s))