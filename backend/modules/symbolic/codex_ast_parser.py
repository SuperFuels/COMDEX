import re
from backend.modules.symbolic.codex_ast_types import CodexAST

def parse_codexlang_to_ast(expression: str) -> dict:
    """
    Converts a simple CodexLang expression to a pseudo-AST structure.
    Currently supports only the pattern: ∀x. P(x) → Q(x)
    """
    if "∀" in expression and "→" in expression:
        # Example: ∀x. P(x) → Q(x)
        match = re.match(r"∀(\w+)\.\s*(\w+)\((\w+)\)\s*→\s*(\w+)\((\w+)\)", expression)
        if match:
            var, pred1, arg1, pred2, arg2 = match.groups()
            return {
                "type": "ForAll",
                "var": var,
                "body": {
                    "type": "Implies",
                    "left": {"type": "Predicate", "name": pred1, "args": [arg1]},
                    "right": {"type": "Predicate", "name": pred2, "args": [arg2]}
                }
            }

    raise ValueError(f"Unsupported or invalid CodexLang: {expression}")

def parse_codex_ast_from_json(ast_json: dict) -> CodexAST:
    """
    Parses a Codex AST from a JSON object and returns a CodexAST instance.
    This is used by the Codex mutation API endpoint.
    """
    return CodexAST(**ast_json)