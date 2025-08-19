# File: backend/modules/validation/symbolic_container_validator.py

from typing import Dict, Any, List
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.codex.codexlang_parser import parse_codexlang_to_ast
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph


def validate_ast_tree(ast: Dict[str, Any]) -> bool:
    """Check whether the AST has a valid node structure."""
    if not isinstance(ast, dict):
        return False
    if "type" not in ast:
        return False
    if "operator" in ast and not isinstance(ast["operator"], str):
        return False
    if "operands" in ast and not isinstance(ast["operands"], list):
        return False
    return True


def is_codexlang_synced(ast: Dict[str, Any], codex_lang: str) -> bool:
    """
    Render the AST back to CodexLang and compare to the original.
    This ensures the AST was derived from the given surface string.
    """
    try:
        rendered = CodexLangRewriter().ast_to_codexlang(ast)
        return rendered.strip() == codex_lang.strip()
    except Exception:
        return False


def glyphs_match_ast(ast: Dict[str, Any], glyphs: List[Dict[str, Any]]) -> bool:
    """
    Re-encode the AST and compare structure to stored glyphs.
    Currently shallow comparison by count.
    """
    try:
        expected = encode_codex_ast_to_glyphs(ast)
        return len(expected) == len(glyphs)
    except Exception:
        return False


def validate_symbolic_fields(container: Dict[str, Any]) -> bool:
    """
    Validate that all symbolic fields in the container are coherent:
    - symbolic_ast is structurally valid
    - codex_lang matches rendered AST
    - glyphs correspond to AST structure
    """
    ast = container.get("symbolic_ast", {})
    codex_lang = container.get("codex_lang", "")
    glyphs = container.get("glyphs", [])

    return (
        validate_ast_tree(ast) and
        is_codexlang_synced(ast, codex_lang) and
        glyphs_match_ast(ast, glyphs)
    )


def explain_validation_failure(container: Dict[str, Any]) -> str:
    """
    Debug-friendly explanation of what failed in validation.
    """
    ast = container.get("symbolic_ast", {})
    codex_lang = container.get("codex_lang", "")
    glyphs = container.get("glyphs", [])

    if not validate_ast_tree(ast):
        return "❌ symbolic_ast is missing or malformed (expected dict with type/operator/operands)."

    if not is_codexlang_synced(ast, codex_lang):
        return "❌ codex_lang does not match rendered CodexLang from AST."

    if not glyphs_match_ast(ast, glyphs):
        return "❌ glyphs do not match regenerated structure from AST."

    return "✅ All symbolic fields are valid."