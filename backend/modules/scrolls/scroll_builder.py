# -*- coding: utf-8 -*-
# Compatibility shim that re-exports the codex scroll builder.
from __future__ import annotations

try:
    # Your real implementation lives here:
    from backend.modules.codex.codex_scroll_builder import (
        build_scroll_from_glyph as _build_scroll_from_glyph,
    )
except Exception:
    # Safe fallback so tests can still run without the full scroll stack.
    def _build_scroll_from_glyph(*args, **kwargs):
        return None

def build_scroll_from_glyph(*args, **kwargs):
    """Back-compat wrapper."""
    return _build_scroll_from_glyph(*args, **kwargs)

__all__ = ["build_scroll_from_glyph"]