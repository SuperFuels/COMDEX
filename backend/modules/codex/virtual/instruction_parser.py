# ===============================
# 📁 instruction_parser.py
# ===============================
"""
CodexLang Instruction Parser

Parses symbolic glyph strings into executable nested instruction trees.
Handles operators, grouping, and implicit structure.
"""

from typing import Any, Dict, List


class InstructionParser:
    def __init__(self):
        # Recognized symbolic operators
        self.operators = set(["→", "↔", "⟲", "⊕", "⧖"])

    def parse_codexlang_string(self, code: str) -> Dict[str, Any]:
        """
        Main parser entrypoint. Splits glyph string and builds instruction tree.
        Always returns a dict AST.
        Example CodexLang: "⚛ → ✦ ⟲ 🧠"
        """
        tokens = code.strip().split()
        if not tokens:
            return {"op": None, "args": []}

        tree = self.build_tree(tokens)

        # ✅ Normalize: wrap lists into a root dict
        if isinstance(tree, list):
            if len(tree) == 1:
                return tree[0]
            return {"op": "program", "children": tree}
        return tree

    def build_tree(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Converts a flat token list into a hierarchical instruction tree.
        The first recognized operator becomes the root "op".
        """
        for i, token in enumerate(tokens):
            if token in self.operators:
                # Split at operator into left/right subtrees
                left = self.build_tree(tokens[:i]) if i > 0 else None
                right = self.build_tree(tokens[i + 1:]) if i + 1 < len(tokens) else None
                return {
                    "op": token,
                    "args": [x for x in [left, right] if x],
                }

        # No operator → treat as literal glyph(s)
        if len(tokens) == 1:
            return {"op": "lit", "value": tokens[0]}
        return [{"op": "lit", "value": tok} for tok in tokens]


# ✅ Public wrapper
_parser = InstructionParser()

def parse_codexlang(code: str) -> Dict[str, Any]:
    return _parser.parse_codexlang_string(code)