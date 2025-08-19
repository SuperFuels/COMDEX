import re

def parse_codexlang_to_ast(expression: str) -> dict:
    """
    Converts a simple CodexLang expression to a pseudo-AST structure.
    For now, supports only ∀x. P(x) → Q(x)
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