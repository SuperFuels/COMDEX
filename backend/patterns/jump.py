from backend.modules.patterns.pattern_registry import PatternRegistry

registry = PatternRegistry()

def warp_to_pattern(name: str):
    p = registry.get(name)
    if not p: return None
    return {
        "name": p.name,
        "glyphs": [g for g in p.glyphs],
        "metadata": p.metadata
    }