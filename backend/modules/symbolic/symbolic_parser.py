# File: backend/modules/symbolic/symbolic_parser.py

from typing import Union, Dict, Any
from backend.modules.symbolic.codex_ast_types import CodexAST
from backend.modules.codex.codexlang_parser import parse_codexlang
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.symbolic.natural_language_parser import parse_nl_to_ast


def parse_raw_input_to_ast(raw: Union[str, Dict[str, Any]]) -> CodexAST:
    """
    Normalize raw symbolic input into a CodexAST.

    Supports:
    - Natural language (e.g., "x is greater than y") → CodexLang → CodexAST
    - Raw CodexLang strings: "add(x, y)"
    - Dict-based glyph trees:
      {
          "root": "add",
          "args": ["x", "y"],
          "meta": {"domain": "math"}
      }
    """
    if isinstance(raw, str):
        try:
            ast = parse_nl_to_ast(raw)
            codexlang = CodexLangRewriter().ast_to_codexlang(ast)
            return parse_codexlang(codexlang)
        except Exception:
            return parse_codexlang(raw)

    elif isinstance(raw, dict):
        if "root" not in raw:
            raise ValueError("Dict input must include a 'root' field.")
        args = raw.get("args", [])
        meta = raw.get("meta", {})
        return CodexAST(raw["root"], args, meta)

    else:
        raise TypeError(f"Unsupported input type: {type(raw)}")


def parse_codexlang_to_ast(codexlang: str) -> CodexAST:
    """
    Convert CodexLang string (e.g., 'add(x, y)') into CodexAST.
    """
    return parse_codexlang(codexlang)