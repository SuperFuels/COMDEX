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
        self.operators = set(["→", "↔", "⟲", "⊕", "⧖"])  # Define recognized ops

    def parse_codexlang_string(self, code: str) -> List[Dict[str, Any]]:
        """
        Main parser entrypoint. Splits glyph string and builds instruction tree.
        Example CodexLang: "⚛ → ✦ ⟲ 🧠"
        """
        tokens = code.strip().split()
        return self.build_tree(tokens)

    def build_tree(self, tokens: List[str]) -> List[Dict[str, Any]]:
        """
        Converts flat token list into hierarchical instruction nodes.
        """
        tree = []
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token in self.operators:
                # Symbolic operator node
                node = {
                    "op": token,
                    "args": [],
                    "children": []
                }
                # Peek ahead for children
                if i + 1 < len(tokens):
                    next_token = tokens[i + 1]
                    if next_token not in self.operators:
                        node["children"].append({
                            "op": next_token,
                            "args": [],
                            "children": []
                        })
                        i += 1
                tree.append(node)

            else:
                # Basic glyph as atomic instruction
                tree.append({
                    "op": token,
                    "args": [],
                    "children": []
                })

            i += 1

        return tree