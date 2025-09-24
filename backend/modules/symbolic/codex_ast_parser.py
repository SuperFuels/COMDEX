# File: backend/modules/lean/codexlang_to_ast.py

import re
from backend.modules.symbolic.codex_ast_types import CodexAST
from backend.modules.codex.codexlang_parser import tokenize_codexlang, parse_expression


def parse_codexlang_to_ast(expression: str) -> CodexAST:
    """
    Converts a CodexLang expression string into a CodexAST structure.

    ✅ Supports all logical constructs:
       - Quantifiers: ∀, ∃
       - Connectives: ¬, →, ↔, ∧, ∨, ⊕, ↑, ↓
       - Predicates / functions: P(x), likes(John, y)
       - Zero-arity symbols like Human, A, B

    Example:
        ∀x. P(x) → Q(x)
        (A ⊕ B) → (B ⊕ A)
        (A ↑ B) → ¬(A ∧ B)

    Returns:
        CodexAST: structured representation of the logic expression
    """
    tokens = tokenize_codexlang(expression)
    if not tokens:
        raise ValueError(f"Empty or invalid CodexLang: {expression}")

    tree = parse_expression(tokens)
    return CodexAST(tree)


def parse_codex_ast_from_json(ast_json: dict) -> CodexAST:
    """
    Reconstructs a CodexAST from its JSON/dict form.
    This is used by Codex mutation and transport APIs.
    """
    return CodexAST(**ast_json)