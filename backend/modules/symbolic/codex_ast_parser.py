import re
from backend.modules.symbolic.codex_ast_types import CodexAST

def parse_codexlang_to_ast(expression: str) -> CodexAST:
    """
    Converts a simple CodexLang expression to a real CodexAST structure.
    Supports: ∀x. P(x) → Q(x)
    """
    if "∀" in expression and "→" in expression:
        match = re.match(r"∀(\w+)\.\s*(\w+)\((\w+)\)\s*→\s*(\w+)\((\w+)\)", expression)
        if match:
            var, pred1, arg1, pred2, arg2 = match.groups()

            left = CodexAST(type="Predicate", value=pred1, children=[
                CodexAST(type="Variable", value=arg1)
            ])

            right = CodexAST(type="Predicate", value=pred2, children=[
                CodexAST(type="Variable", value=arg2)
            ])

            implies = CodexAST(type="Implies", children=[left, right])
            root = CodexAST(type="ForAll", value=var, children=[implies])

            return root

    raise ValueError(f"Unsupported or invalid CodexLang: {expression}")
    
def parse_codex_ast_from_json(ast_json: dict) -> CodexAST:
    """
    Parses a Codex AST from a JSON object and returns a CodexAST instance.
    This is used by the Codex mutation API endpoint.
    """
    return CodexAST(**ast_json)