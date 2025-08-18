# backend/modules/codex/codex_ast_encoder.py

from typing import List, Dict, Any, Union
import re

from backend.modules.codex.codexlang_types import CodexAST
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph


def parse_codexlang_to_ast(expression: str) -> dict:
    """
    Converts a simple CodexLang expression to a pseudo-AST structure.
    Currently supports patterns like: ∀x. P(x) → Q(x)
    """
    if "∀" in expression and "→" in expression:
        # Match ∀x. P(x) → Q(x)
        match = re.match(r"∀(\w+)\.\s*(\w+)\((\w+)\)\s*→\s*(\w+)\((\w+)\)", expression)
        if match:
            var, pred1, arg1, pred2, arg2 = match.groups()
            return {
                "type": "ForAll",
                "var": var,
                "body": {
                    "type": "Implies",
                    "left": {"type": "predicate", "operator": pred1, "operands": [arg1]},
                    "right": {"type": "predicate", "operator": pred2, "operands": [arg2]}
                }
            }

    raise ValueError(f"Unsupported or invalid CodexLang: {expression}")


def encode_codex_ast_to_glyphs(ast: Union[CodexAST, Dict[str, Any]]) -> List[LogicGlyph]:
    """
    Convert a CodexAST tree or logic-aware AST dict into a list of LogicGlyphs for symbolic processing.
    Supports both raw CodexAST and richer parsed structures from codexlang_parser.py.
    """
    glyphs: List[LogicGlyph] = []

    def traverse(node: Union[CodexAST, Dict[str, Any]]) -> LogicGlyph:
        if isinstance(node, CodexAST):
            op = node.root
            operands = node.args
            encoded_operands = []
            for arg in operands:
                if isinstance(arg, CodexAST) or isinstance(arg, dict):
                    subglyph = traverse(arg)
                    glyphs.append(subglyph)
                    encoded_operands.append(subglyph.get("id", subglyph))
                else:
                    encoded_operands.append(arg)

            glyph = LogicGlyph(
                type="symbolic",
                operator=op,
                operands=encoded_operands,
                metadata=node.meta
            )
            return glyph.encode()

        elif isinstance(node, dict):
            node_type = node.get("type")
            operator = node.get("operator")
            operands = node.get("operands", [])
            metadata = node.get("metadata", {})

            # Special handling for quantifiers and logic structures
            if node_type == "ForAll":
                glyph = LogicGlyph(
                    type="logic",
                    operator="∀",
                    operands=[node["var"], traverse(node["body"]).get("id")],
                    metadata=metadata
                )
                return glyph.encode()

            elif node_type == "Exists":
                glyph = LogicGlyph(
                    type="logic",
                    operator="∃",
                    operands=[node["var"], traverse(node["body"]).get("id")],
                    metadata=metadata
                )
                return glyph.encode()

            elif node_type == "Implies":
                glyph = LogicGlyph(
                    type="logic",
                    operator="→",
                    operands=[traverse(node["left"]).get("id"), traverse(node["right"]).get("id")],
                    metadata=metadata
                )
                return glyph.encode()

            elif node_type == "Equiv":
                glyph = LogicGlyph(
                    type="logic",
                    operator="↔",
                    operands=[traverse(node["left"]).get("id"), traverse(node["right"]).get("id")],
                    metadata=metadata
                )
                return glyph.encode()

            elif node_type == "Not":
                glyph = LogicGlyph(
                    type="logic",
                    operator="¬",
                    operands=[traverse(node["expr"]).get("id")],
                    metadata=metadata
                )
                return glyph.encode()

            elif node_type == "And":
                ops = [traverse(child).get("id") for child in node["args"]]
                glyph = LogicGlyph(
                    type="logic",
                    operator="∧",
                    operands=ops,
                    metadata=metadata
                )
                return glyph.encode()

            elif node_type == "Or":
                ops = [traverse(child).get("id") for child in node["args"]]
                glyph = LogicGlyph(
                    type="logic",
                    operator="∨",
                    operands=ops,
                    metadata=metadata
                )
                return glyph.encode()

            elif node_type == "predicate":
                glyph = LogicGlyph(
                    type="logic",
                    operator=operator,
                    operands=operands,
                    metadata=metadata
                )
                return glyph.encode()

            # Generic fallback for any other logic/math/operator types
            encoded_operands = []
            for operand in operands:
                if isinstance(operand, (dict, CodexAST)):
                    subglyph = traverse(operand)
                    glyphs.append(subglyph)
                    encoded_operands.append(subglyph.get("id", subglyph))
                else:
                    encoded_operands.append(operand)

            glyph = LogicGlyph(
                type=_map_type(node_type),
                operator=operator,
                operands=encoded_operands,
                metadata=metadata
            )
            return glyph.encode()

        else:
            raise TypeError(f"Unsupported AST node type: {type(node)}")

    root_glyph = traverse(ast)
    glyphs.append(root_glyph)
    return glyphs


def _map_type(ast_type: str) -> str:
    """Map AST node type to glyph category."""
    if ast_type in {"Implies", "Equiv", "Not", "And", "Or", "ForAll", "Exists"}:
        return "logic"
    elif ast_type in {"Addition", "Subtraction", "Multiplication", "Division", "Equality"}:
        return "math"
    elif ast_type == "VectorOp":
        return "vector"
    return "symbolic"  # fallback


# Example glyph:
# {
#     "type": "logic",
#     "operator": "∀",
#     "operands": ["x", "<id-of-body>"],
#     "id": "...",
#     "metadata": {}
# }