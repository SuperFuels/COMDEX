#!/usr/bin/env python3
from backend.modules.patterns.symbolic_pattern_engine import _pattern_engine

_pattern_engine.register_new_pattern(
    glyphs=[{"text":"A"}],
    name="TestPattern",
    pattern_type="test",
    trigger_logic="",
    source_container="manual"
)