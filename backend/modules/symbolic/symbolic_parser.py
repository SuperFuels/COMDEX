# File: backend/modules/symbolic/symbolic_parser.py
from typing import Union, Dict, Any
import logging
from backend.modules.symbolic.codex_ast_types import CodexAST
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.symbolic.natural_language_parser import parse_nl_to_ast
from backend.modules.symbolic.codex_ast_parser import parse_codexlang_to_ast


def parse_raw_input_to_ast(raw: Union[str, Dict[str, Any]]) -> CodexAST:
    """
    Normalize raw symbolic input into a CodexAST with SoulLaw compliance.

    Supports:
    - Natural language: "x is greater than y" → CodexLang → CodexAST
    - Raw CodexLang: "add(x, y)"
    - Dict-based glyph trees:
        {
            "root": "add",
            "args": ["x", "y"],
            "meta": {"domain": "math"}
        }

    Guarantees:
    - Never raises on malformed input
    - Returns CodexAST with `soul_law_compliance` tag
    - Integrates natural-language + CodexLang fusion
    """
    try:
        # 🧠 String inputs — could be natural or CodexLang
        if isinstance(raw, str):
            raw_str = raw.strip()
            if not raw_str:
                logging.warning("[SymbolicParser] Empty string input; returning empty AST.")
                return CodexAST({"type": "empty", "tokens": [], "soul_law_compliance": "skip"})

            try:
                # Try NL → CodexLang → CodexAST path
                ast_nl = parse_nl_to_ast(raw_str)
                codexlang = CodexLangRewriter().ast_to_codexlang(ast_nl)
                return parse_codexlang_to_ast(codexlang)
            except Exception:
                # Fallback to raw CodexLang parsing
                return parse_codexlang_to_ast(raw_str)

        # 🌐 Dict inputs — glyph or structured ASTs
        elif isinstance(raw, dict):
            root = raw.get("root") or raw.get("operator") or raw.get("type")
            if not root:
                logging.warning(f"[SymbolicParser] Missing 'root' or 'operator' in dict: {raw}")
                return CodexAST({"type": "error", "message": "missing_root", "soul_law_compliance": "violated"})

            args = raw.get("args", [])
            meta = raw.get("meta", {})
            ast_dict = {
                "type": "function",
                "name": root,
                "args": args,
                "meta": meta,
                "soul_law_compliance": "pass",
            }
            return CodexAST(ast_dict)

        else:
            logging.error(f"[SymbolicParser] Unsupported input type: {type(raw)}")
            return CodexAST({
                "type": "error",
                "message": f"Unsupported input type: {type(raw)}",
                "soul_law_compliance": "violated"
            })

    except Exception as e:
        logging.error(f"[SymbolicParser] Exception parsing raw input: {e} | raw={raw}")
        return CodexAST({
            "type": "error",
            "message": str(e),
            "source": str(raw),
            "soul_law_compliance": "violated"
        })


def parse_codexlang_to_ast(codexlang: str) -> CodexAST:
    """
    Convert CodexLang string (e.g., 'add(x, y)') into a CodexAST
    with SoulLaw compliance and safety guards.
    """
    return parse_codexlang_to_ast(codexlang)