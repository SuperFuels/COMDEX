# ===============================
# 📁 backend/modules/codex/codex_scroll_builder.py
# ===============================

import logging
from typing import List, Dict, Any

from backend.modules.codex.codex_metrics import score_glyph_tree  # Optional import for scoring
from backend.modules.glyphos.glyph_parser import parse_codexlang_string
from backend.modules.symbolic.codex_ast_types import CodexAST
def _get_parser():
    from backend.modules.codex.codexlang_parser import parse_codexlang
    return parse_codexlang
from backend.photon.photon_codex_adapter import codex_to_photon_ast

logger = logging.getLogger(__name__)


def build_codex_scroll(glyph_tree: List[Dict], include_coords: bool = False, indent: int = 0) -> str:
    """
    Converts structured glyph tree into CodexLang scroll format.
    Recursively traverses tree and renders symbolic logic.
    """
    lines = []

    for glyph in glyph_tree:
        symbol = glyph.get("symbol", "???")
        value = glyph.get("value", "undefined")
        action = glyph.get("action", "")
        children = glyph.get("children", [])
        coord = glyph.get("coord")

        # Build base line
        line = "    " * indent + f"{symbol}: {value}"
        if action:
            line += f" => {action}"
        if include_coords and coord:
            line += f"    # coord: {coord}"

        lines.append(line)

        # Recurse
        if children:
            child_lines = build_codex_scroll(children, include_coords=include_coords, indent=indent + 1)
            lines.append(child_lines)

    return "\n".join(lines)


def build_scroll_from_glyph(glyph_tree: List[Dict[str, Any]]) -> str:
    """
    ✅ Entry point used by memory_engine and runtime systems.
    Wraps build_codex_scroll and hides internal config flags.
    """
    return build_codex_scroll(glyph_tree, include_coords=True)


def build_scroll_as_photon_ast(code: str) -> Dict[str, Any]:
    """
    Build a scroll and immediately convert to Photon AST.
    Useful for bridging CodexLang ↔ Photon execution.
    """
    try:
        codex_ast = _get_parser()(code)

        # ✅ unwrap CodexAST to dict if needed
        if hasattr(codex_ast, "to_dict"):
            codex_ast = codex_ast.to_dict()
        elif hasattr(codex_ast, "__dict__"):
            codex_ast = dict(codex_ast.__dict__)

        photon_ast = codex_to_photon_ast(codex_ast)
        return photon_ast
    except Exception as e:
        logger.error(f"[ScrollBuilder] Failed to build Photon AST: {e}", exc_info=True)
        return {"op": "error", "detail": str(e)}

def parse_codexlang(code: str) -> CodexAST:
    """
    Parse a CodexLang string like 'greater_than(x, y)' into CodexAST.
    If input has no parentheses, treat as constant symbol.
    """
    try:
        if "(" not in code:
            return CodexAST({"root": code.strip(), "args": []})
        if ")" not in code:
            raise ValueError("CodexLang must contain matching parentheses")

        fn = code.split("(", 1)[0].strip()
        args = code.split("(", 1)[1].rsplit(")", 1)[0].split(",")
        args = [a.strip() for a in args if a.strip()]
        return CodexAST({"root": fn, "args": args})

    except Exception as e:
        raise ValueError(f"Invalid input for CodexLang parsing: {code}") from e

# Example test runner
if __name__ == "__main__":
    test_string = "Memory:Emotion = Joy => Store -> Memory:Emotion = Peace => Remember"
    parsed = _get_parser_string(test_string)
    tree = parsed.get("tree", [])

    scroll = build_scroll_from_glyph(tree)
    print("--- Codex Scroll ---")
    print(scroll)

    # 🔬 Test Photon AST build
    try:
        photon_ast = build_scroll_as_photon_ast("greater_than(x, y)")
        print("--- Photon AST ---")
        print(photon_ast)
    except Exception as e:
        print("Photon AST build failed:", e)