# codex_core/virtual/instruction_tree_parser.py

"""
Instruction Tree Parser

Converts CodexLang strings or glyph arrays into structured symbolic instruction trees
using the symbolic opcode set defined in symbolic_instruction_set.py.
"""

from typing import List, Dict, Union
from codex_core.virtual.symbolic_instruction_set import SYMBOLIC_OPCODES
from backend.modules.glyphos.codexlang_translator import parse_codexlang_string


class InstructionTreeParser:
    def __init__(self):
        self.opcodes = SYMBOLIC_OPCODES

    def parse_from_codexlang(self, codex_str: str) -> List[Dict]:
        """
        Parses a full CodexLang string into symbolic instruction trees.
        """
        parsed = parse_codexlang_string(codex_str)
        return self._convert_nodes(parsed.get("tree", []))

    def parse_from_array(self, glyph_array: List[Dict[str, Union[str, List]]]) -> List[Dict]:
        """
        Takes a pre-parsed glyph array (e.g., from runtime) and attaches symbolic opcodes.
        """
        return self._convert_nodes(glyph_array)

    def _convert_nodes(self, nodes: List[Dict]) -> List[Dict]:
        out = []
        for node in nodes:
            symbol = node.get("symbol", "")
            action = node.get("action", "")
            opcode = self._resolve_opcode(symbol, action)

            children = self._convert_nodes(node.get("children", [])) if node.get("children") else []

            out.append({
                "opcode": opcode,
                "symbol": symbol,
                "action": action,
                "value": node.get("value"),
                "children": children,
                "coord": node.get("coord"),
            })
        return out

    def _resolve_opcode(self, symbol: str, action: str) -> str:
        """
        Resolve symbolic opcode using symbol and/or action match.
        """
        if symbol in self.opcodes:
            return self.opcodes[symbol]
        elif action in self.opcodes:
            return self.opcodes[action]
        return "NOP"  # Default fallback


# Example use
if __name__ == "__main__":
    parser = InstructionTreeParser()
    example = "Memory:Emotion = Joy => Store"
    result = parser.parse_from_codexlang(example)
    from pprint import pprint
    pprint(result)