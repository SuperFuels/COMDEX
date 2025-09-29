# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_glyph_metadata.py
"""
Test: Glyph Operator Metadata
─────────────────────────────────────────────
Ensures that glyph:* operators are properly
documented in INSTRUCTION_METADATA so frontend
tools (GHX visualizer, docs generator) can
describe them automatically.
"""

import pytest
from backend.codexcore_virtual.instruction_registry import INSTRUCTION_METADATA


@pytest.mark.parametrize("glyph_key", [
    "glyph:teleport",
    "glyph:write_cube",
    "glyph:run_mutation",
    "glyph:rewrite",
    "glyph:log",
])
def test_glyph_metadata_presence(glyph_key):
    """Verify glyph operator is registered in metadata."""
    assert glyph_key in INSTRUCTION_METADATA, f"{glyph_key} missing in INSTRUCTION_METADATA"

    meta = INSTRUCTION_METADATA[glyph_key]
    assert "type" in meta and meta["type"] == "glyph_op"
    assert "impl" in meta and isinstance(meta["impl"], str)
    assert "desc" in meta and isinstance(meta["desc"], str)
    assert len(meta["desc"]) > 0, f"{glyph_key} description is empty"