# ===============================
# 📁 modules/codex/virtual/instruction_parser.py
# ===============================
"""
CodexLang Instruction Parser

Parses symbolic glyph strings into executable nested instruction trees.
Handles operators, grouping, and implicit structure.
Now patched to:
  • Use canonical operator metadata bridge.
  • Enforce Symatics operator precedence.
  • Support nested parentheses (⟲(A ⊕ B), ⟲((A ⊕ B) → C)).
"""

import re
from typing import Any, Dict, List
from backend.codexcore_virtual.instruction_metadata_bridge import get_instruction_metadata


class InstructionParser:
    def __init__(self):
        # Recognized symbolic operators
        self.operators = ["→", "↔", "⟲", "⊕", "⧖"]

        # Operator precedence (low → high), following Symatics gospel
        self.precedence = {
            "→": 1,   # forward / project
            "⧖": 1,   # delay
            "↔": 2,   # entangle
            "⟲": 2,   # reflect/mutate
            "⊕": 3,   # combine / superpose
        }

    def resolve_opcode(self, symbol: str) -> str:
        """Resolve a raw symbol into a domain-tagged opcode."""
        meta = get_instruction_metadata(symbol)
        domain = meta.get("domain", "unknown")
        return f"{domain}:{symbol}"

    # ─── Public Entrypoint ───────────────────────────────────────────

    def parse_codexlang_string(self, code: str) -> Dict[str, Any]:
        """Main parser entrypoint."""
        tokens = self.tokenize(code.strip())
        if not tokens:
            return {"op": None, "args": []}

        tree = self.build_tree(tokens)

        if isinstance(tree, list):
            if len(tree) == 1:
                return tree[0]
            return {"op": "program", "children": tree}
        return tree

    # ─── Tokenizer ──────────────────────────────────────────────────

    def tokenize(self, code: str) -> List[str]:
        """
        Tokenize string while respecting parentheses.
        Example: "⟲(A ⊕ B)" → ["⟲", "(", "A", "⊕", "B", ")"]
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

    def build_tree(self, tokens: List[str]) -> Any:
        """Convert tokens into AST using precedence + parentheses."""

        if not tokens:
            return None

        # Handle wrapping parentheses
        if tokens[0] == "(" and tokens[-1] == ")":
            return self.build_tree(tokens[1:-1])

        # Handle function-style ops like ⟲( ... )
        if len(tokens) >= 3 and tokens[1] == "(" and tokens[-1] == ")":
            op = tokens[0]
            inner = self.build_tree(tokens[2:-1])
            return {"op": self.resolve_opcode(op), "args": [inner]}

        # Operator precedence
        for prec in sorted(set(self.precedence.values())):
            depth = 0
            for i, token in enumerate(tokens):
                if token == "(":
                    depth += 1
                elif token == ")":
                    depth -= 1
                elif depth == 0 and token in self.operators and self.precedence[token] == prec:
                    left = self.build_tree(tokens[:i])
                    right = self.build_tree(tokens[i + 1 :])
                    return {
                        "op": self.resolve_opcode(token),
                        "args": [x for x in [left, right] if x],
                    }

        # Base case → literal(s)
        if len(tokens) == 1:
            return {"op": "lit", "value": tokens[0]}
        return [{"op": "lit", "value": tok} for tok in tokens if tok not in {"(", ")"}]


# ✅ Public wrapper
_parser = InstructionParser()


def parse_codexlang(code: str) -> Dict[str, Any]:
    return _parser.parse_codexlang_string(code)


# 🧪 CLI Debug Harness
if __name__ == "__main__":
    samples = [
        "⚛ → ✦ ⟲ 🧠",
        "A ⊕ B → C",
        "X ↔ Y",
        "⟲(A ⊕ B)",
        "⟲((A ⊕ B) → C)",
    ]
    for s in samples:
        print(f"\nInput: {s}")
        print(parse_codexlang(s))