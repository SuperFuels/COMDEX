# File: backend/modules/symbolic/codex_ast_parser.py

import re
import logging
from backend.modules.symbolic.codex_ast_types import CodexAST
from backend.modules.codex.codexlang_parser import tokenize_codexlang, parse_expression


def parse_codexlang_to_ast(expression: str) -> CodexAST:
    """
    Converts a CodexLang expression string into a CodexAST structure with SoulLaw compliance.

    ✅ Supports:
       - Quantifiers: ∀, ∃
       - Connectives: ¬, →, ↔, ∧, ∨, ⊕, ↑, ↓, =
       - Predicates/functions: P(x), likes(John, y)
       - Zero-arity symbols like Human, ψ₀, A, B

    ⚙️ Enhancements:
       - Gracefully handles malformed or incomplete expressions
       - Adds soul_law_compliance metadata to AST
       - Never raises exceptions upstream
    """
    if not expression or not isinstance(expression, str):
        logging.warning("[CodexLang] Empty or invalid expression; returning empty AST.")
        return CodexAST({"type": "empty", "tokens": [], "soul_law_compliance": "skip"})

    try:
        tokens = tokenize_codexlang(expression)
        if not tokens:
            logging.warning(f"[CodexLang] Tokenization returned empty list for: {expression}")
            return CodexAST({"type": "empty", "source": expression, "soul_law_compliance": "skip"})

        parsed_tree = parse_expression(tokens)
        if not parsed_tree or not isinstance(parsed_tree, dict):
            logging.warning(f"[CodexLang] Invalid parse tree for: {expression}")
            return CodexAST({"type": "error", "source": expression, "soul_law_compliance": "fail"})

        # ✅ Determine SoulLaw compliance state
        if parsed_tree.get("type") in ("error", "empty"):
            soul_state = "violated" if parsed_tree["type"] == "error" else "skip"
        else:
            soul_state = "pass"

        parsed_tree["soul_law_compliance"] = soul_state
        parsed_tree["source_expr"] = expression

        return CodexAST(parsed_tree)

    except Exception as e:
        logging.error(f"[CodexLang] Exception during parse_codexlang_to_ast: {e} | expr={expression}")
        return CodexAST({
            "type": "error",
            "message": str(e),
            "source": expression,
            "soul_law_compliance": "violated"
        })


def parse_codex_ast_from_json(ast_json: dict) -> CodexAST:
    """
    Reconstructs a CodexAST from its JSON/dict form.
    Ensures soul_law_compliance field persists through reconstruction.
    """
    if not isinstance(ast_json, dict):
        logging.warning("[CodexAST] Expected dict input; received invalid structure.")
        return CodexAST({"type": "error", "soul_law_compliance": "violated"})

    ast_json.setdefault("soul_law_compliance", "unknown")
    return CodexAST(**ast_json)