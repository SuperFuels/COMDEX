# ===============================
# 📁 modules/codex/virtual/instruction_parser.py
# ===============================
"""
CodexLang Instruction Parser

Parses symbolic glyph strings into executable nested instruction trees.
Handles operators, grouping, and implicit structure.
Now patched to:
  * Use canonical operator metadata bridge.
  * Enforce Symatics operator precedence.
  * Support nested parentheses (⟲(A ⊕ B), ⟲((A ⊕ B) -> C)).
"""

import re
from typing import Any, Dict, List
from backend.codexcore_virtual.instruction_metadata_bridge import get_instruction_metadata


class InstructionParser:
    def __init__(self):
        # Recognized symbolic operators
        self.operators = ["->", "↔", "⟲", "⊕", "⧖", "⊖"]

        # Operator precedence (low -> high)
        self.precedence = {
            "->": 1,
            "⧖": 1,
            "↔": 2,
            "⟲": 2,
            "⊕": 3,
            "⊖": 3,   # same level as ⊕ (binary algebraic ops)
        }

    # ─── Opcode Resolver ───────────────────────────────────────────
    def resolve_opcode(self, symbol: str, mode: str = None) -> str:
        """
        Resolve a raw symbol into a domain-tagged opcode
        using the canonical metadata bridge.
        Optionally prefix with execution mode (photon:/symatics:).
        """
        meta = get_instruction_metadata(symbol) or {}
        domain = meta.get("domain", "logic")  # fallback domain

        base = f"{domain}:{symbol}"
        if mode in {"photon", "symatics"}:
            return f"{mode}:{symbol}"   # keep mode prefix clean
        return base

    # ─── Public Entrypoint ───────────────────────────────────────────
    def parse_codexlang_string(self, code: str, mode: str = None) -> Dict[str, Any]:
        """Main parser entrypoint."""
        tokens = self.tokenize(code.strip())
        if not tokens:
            return {"op": None, "args": []}

        tree = self.build_tree(tokens, mode=mode)

        if isinstance(tree, list):
            if len(tree) == 1:
                return tree[0]
            return {"op": "program", "children": tree}
        return tree

    # ─── Tokenizer ──────────────────────────────────────────────────
    def tokenize(self, code: str) -> List[str]:
        """
        Tokenize string while respecting parentheses.
        Example: "⟲(A ⊕ B)" -> ["⟲", "(", "A", "⊕", "B", ")"]
        """
        tokens: List[str] = []
        buf = ""
        for ch in code:
            if ch in {"(", ")"} or ch.isspace():
                if buf:
                    tokens.append(buf)
                    buf = ""
                if ch.strip():
                    tokens.append(ch)
            else:
                buf += ch
        if buf:
            tokens.append(buf)
        return tokens

    # ─── Tree Builder ───────────────────────────────────────────────
    def build_tree(self, tokens: List[str], mode: str = None) -> Any:
        """Convert tokens into AST using precedence + parentheses."""

        if not tokens:
            return None

        # Handle wrapping parentheses
        if tokens[0] == "(" and tokens[-1] == ")":
            return self.build_tree(tokens[1:-1], mode=mode)

        # Handle function-style ops like ⟲( ... )
        if len(tokens) >= 3 and tokens[1] == "(" and tokens[-1] == ")":
            op = tokens[0]
            inner = self.build_tree(tokens[2:-1], mode=mode)
            return {"op": self.resolve_opcode(op, mode=mode), "args": [inner]}

        # Operator precedence
        for prec in sorted(set(self.precedence.values())):
            depth = 0
            for i, token in enumerate(tokens):
                if token == "(":
                    depth += 1
                elif token == ")":
                    depth -= 1
                elif depth == 0 and token in self.operators and self.precedence[token] == prec:
                    left = self.build_tree(tokens[:i], mode=mode)
                    right = self.build_tree(tokens[i + 1 :], mode=mode)
                    return {
                        "op": self.resolve_opcode(token, mode=mode),
                        "args": [x for x in [left, right] if x],
                    }

        # Base case -> literal(s)
        if len(tokens) == 1:
            return {"op": "lit", "value": tokens[0]}
        return [{"op": "lit", "value": tok} for tok in tokens if tok not in {"(", ")"}]


# ✅ Public wrapper
_parser = InstructionParser()


def parse_codexlang(code: str, mode: str = None) -> Dict[str, Any]:
    return _parser.parse_codexlang_string(code, mode=mode)


# 🧪 CLI Debug Harness
if __name__ == "__main__":
    samples = [
        "⚛ -> ✦ ⟲ 🧠",
        "A ⊕ B -> C",
        "X ↔ Y",
        "⟲(A ⊕ B)",
        "⟲((A ⊕ B) -> C)",
        "A ⊖ ∅",
    ]
    for s in samples:
        print(f"\nInput: {s}")
        print(parse_codexlang(s, mode="photon"))