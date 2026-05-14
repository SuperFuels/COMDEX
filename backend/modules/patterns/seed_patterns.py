# backend/modules/patterns/seed_patterns.py
from .pattern_registry import PatternRegistry, Pattern

def seed_builtin_patterns():
    registry = PatternRegistry()
    if not registry.find_by_glyphs([
        {"type": "variable"},
        {"type": "operator", "value": "⊕"},
        {"type": "variable"}
    ], strict=True):
        registry.register(Pattern(
            name="XOR Pattern",
            glyphs=[
                {"type": "variable"},
                {"type": "operator", "value": "⊕"},
                {"type": "variable"}
            ],
            pattern_type="logic",
            trigger_logic="a ⊕ b"
        ))
        registry.save()  # 🔄 Persist