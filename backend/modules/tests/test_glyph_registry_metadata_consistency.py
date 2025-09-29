# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_glyph_registry_metadata_consistency.py
"""
Cross-check glyph metadata vs registry handlers.

Ensures:
- Every glyph:* entry in INSTRUCTION_METADATA has a live handler in registry.
- No metadata drift (described ops without implementations).
"""

import pytest
from backend.codexcore_virtual import instruction_registry as IR


def test_all_glyph_metadata_have_handlers():
    glyph_keys = [k for k in IR.INSTRUCTION_METADATA.keys() if k.startswith("glyph:")]

    assert glyph_keys, "No glyph:* entries found in INSTRUCTION_METADATA"

    for key in glyph_keys:
        assert key in IR.registry.registry, f"Metadata entry {key} missing in registry"


def test_registry_glyphs_are_documented():
    # All registered glyph:* handlers should be documented in INSTRUCTION_METADATA
    registry_keys = [k for k in IR.registry.registry.keys() if k.startswith("glyph:")]

    for key in registry_keys:
        assert key in IR.INSTRUCTION_METADATA, f"Registry glyph {key} undocumented in metadata"