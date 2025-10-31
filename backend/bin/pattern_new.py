#!/usr/bin/env python3
from backend.modules.patterns.symbolic_pattern_engine import _pattern_engine
import sys

glyph = sys.argv[1] if len(sys.argv) > 1 else "A"
name = sys.argv[2] if len(sys.argv) > 2 else f"Auto_{glyph}"

_pattern_engine.register_new_pattern(
    glyphs=[{"text": glyph}],
    name=name,
    pattern_type="manual",
    trigger_logic="",
    source_container="cli"
)
print(f"✅ Created pattern {name} for glyph {glyph}")