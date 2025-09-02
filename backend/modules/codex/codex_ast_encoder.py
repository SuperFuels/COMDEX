from typing import List, Dict, Any, Union
import re

from backend.modules.codex.codexlang_types import CodexAST
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import EncodedLogicGlyph as LogicGlyph


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

    def safe_id(glyph: Union[LogicGlyph, Dict]) -> str:
        return glyph.get("id") if isinstance(glyph, dict) else getattr(glyph, "id", str(glyph))

    def normalize_symbol(symbol: Union[str, Dict[str, Any], None]) -> str:
        if isinstance(symbol, str):
            return symbol
        elif isinstance(symbol, dict):
            return symbol.get("name") or symbol.get("value") or "unknown"
        return "unknown"

    def traverse(node: Union[CodexAST, Dict[str, Any]]) -> LogicGlyph:
        if isinstance(node, CodexAST):
            op = normalize_symbol(node.root)
            operands = node.args
            encoded_operands = []
            for arg in operands:
                if isinstance(arg, (CodexAST, dict)):
                    subglyph = traverse(arg)
                    glyphs.append(subglyph)
                    encoded_operands.append(safe_id(subglyph))
                else:
                    encoded_operands.append(arg)

            glyph = LogicGlyph.create(
                symbol=op,
                operands=encoded_operands,
                metadata=node.meta
            )
            return glyph

        elif isinstance(node, dict):
            node_type = node.get("type")
            operator = normalize_symbol(node.get("operator"))
            operands = node.get("operands", [])
            metadata = node.get("metadata", {})

            if node_type == "ForAll":
                glyph = LogicGlyph.create(
                    symbol="∀",
                    operands=[node["var"], safe_id(traverse(node["body"]))],
                    metadata=metadata
                )
                return glyph

            elif node_type == "Exists":
                glyph = LogicGlyph.create(
                    symbol="∃",
                    operands=[node["var"], safe_id(traverse(node["body"]))],
                    metadata=metadata
                )
                return glyph

            elif node_type == "Implies":
                glyph = LogicGlyph.create(
                    symbol="→",
                    operands=[
                        safe_id(traverse(node["left"])),
                        safe_id(traverse(node["right"]))
                    ],
                    metadata=metadata
                )
                return glyph

            elif node_type == "Equiv":
                glyph = LogicGlyph.create(
                    symbol="↔",
                    operands=[
                        safe_id(traverse(node["left"])),
                        safe_id(traverse(node["right"]))
                    ],
                    metadata=metadata
                )
                return glyph

            elif node_type == "Not":
                glyph = LogicGlyph.create(
                    symbol="¬",
                    operands=[safe_id(traverse(node["expr"]))],
                    metadata=metadata
                )
                return glyph

            elif node_type == "And":
                ops = [safe_id(traverse(child)) for child in node["args"]]
                glyph = LogicGlyph.create(
                    symbol="∧",
                    operands=ops,
                    metadata=metadata
                )
                return glyph

            elif node_type == "Or":
                ops = [safe_id(traverse(child)) for child in node["args"]]
                glyph = LogicGlyph.create(
                    symbol="∨",
                    operands=ops,
                    metadata=metadata
                )
                return glyph

            elif node_type == "predicate":
                glyph = LogicGlyph.create(
                    symbol=normalize_symbol(operator),
                    operands=operands,
                    metadata=metadata
                )
                return glyph

            # Fallback for unknown or custom node types
            encoded_operands = []
            for operand in operands:
                if isinstance(operand, (dict, CodexAST)):
                    subglyph = traverse(operand)
                    glyphs.append(subglyph)
                    encoded_operands.append(safe_id(subglyph))
                else:
                    encoded_operands.append(operand)

            glyph = LogicGlyph.create(
                symbol=normalize_symbol(operator),
                operands=encoded_operands,
                metadata=metadata
            )
            return glyph

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

import ast as py_ast
from backend.modules.symbolic.codex_ast_types import CodexAST, make_unknown


def parse_python_file_to_codex_ast(code: str) -> CodexAST:
    try:
        # This parses valid Python source code to an AST
        parsed_ast = py_ast.parse(code)
        # 🧠 TODO: Convert to structured CodexAST tree here.
        # For now, we stub with `make_unknown` to simulate AST wrapping
        return make_unknown()
    except Exception as e:
        print(f"Error parsing Python code: {e}")
        return make_unknown()

# Example glyph:
# {
#     "type": "logic",
#     "operator": "∀",
#     "operands": ["x", "<id-of-body>"],
#     "id": "...",
#     "metadata": {}
# }