# backend/modules/photonlang/fidelity/libcst_mode.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Set

# --- Optional project pipeline imports (safe fallbacks if absent) ---
try:
    from backend.modules.photonlang.adapters.python_tokens import (
        expand_text_py,
        normalize_roundtrip,
    )
    from backend.modules.photonlang.translator import expand_symatics_ops
    from backend.modules.photonlang.ir import TransformOptions, TransformResult
    _HAVE_PIPELINE = True
except Exception:  # minimal fallbacks for optional-path use
    from typing import Optional

    @dataclass
    class TransformResult:  # type: ignore[no-redef]
        text: str

    class TransformOptions:  # type: ignore
        pass

    def expand_text_py(src: str) -> str:  # type: ignore
        return src

    def expand_symatics_ops(src: str) -> str:  # type: ignore
        return src

    def normalize_roundtrip(src: str) -> str:  # type: ignore
        return src

    _HAVE_PIPELINE = False

# --- LibCST is optional; fall back to normalize_roundtrip if missing ---
try:
    import libcst as cst
    _HAVE_LIBCST = True
except Exception:
    _HAVE_LIBCST = False
    cst = None  # type: ignore

# --- Registry-sourced glyph set (safe default if registry missing) ---
try:
    from backend.modules.photonlang.registry import glyphs as _registry_glyphs

    def _glyph_set() -> Set[str]:
        return set(_registry_glyphs())
except Exception:
    def _glyph_set() -> Set[str]:
        # Minimal default: extend as needed
        return {"⊕", "μ", "↔", "⟲", "π"}

GLYPH_CALLS: Set[str] = _glyph_set()


@dataclass
class Result:  # kept for compatibility with earlier optional-path usage
    text: str


class _GlyphCallRewriter(cst.CSTTransformer):  # type: ignore[name-defined]
    """
    CST pass that rewrites bare glyph call names to __OPS__['⋯'] lookups.
    If expand_symatics_ops already handled this textually, this pass is a no-op.
    """
    def leave_Call(self, original_node: "cst.Call", updated_node: "cst.Call") -> "cst.Call":
        func = updated_node.func
        if isinstance(func, cst.Name) and func.value in GLYPH_CALLS:
            new_func = cst.parse_expression(f"__OPS__['{func.value}']")
            return updated_node.with_changes(func=new_func)
        return updated_node


def expand_with_libcst(
    src: str,
    *,
    options: "TransformOptions | None" = None,
) -> TransformResult:
    """
    Fidelity path (safe for glyph input):
      1) expand_text_py        : glyphs → legal Python tokens           [lexical]
      2) expand_symatics_ops   : glyph calls → __OPS__['⋯'](...)        [textual]
      3) LibCST parse/emit     : stabilize whitespace/trivia            [syntactic]
         (+ CST rewrite pass to catch any remaining bare glyph calls)

    Falls back to normalize_roundtrip on any CST issues or if LibCST unavailable.
    """
    # 1–2: make the code parseable first (preserves existing test behavior)
    py = expand_text_py(src)
    py = expand_symatics_ops(py)

    if not _HAVE_LIBCST:
        return TransformResult(text=normalize_roundtrip(py))

    try:
        mod = cst.parse_module(py)  # type: ignore[attr-defined]
        # Run rewriter in case any bare glyph calls survived step (2)
        mod2 = mod.visit(_GlyphCallRewriter())
        rendered = mod2.code
        return TransformResult(text=rendered)
    except Exception:
        # Deterministic fallback
        return TransformResult(text=normalize_roundtrip(py))