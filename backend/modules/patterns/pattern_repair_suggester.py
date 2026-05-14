# File: backend/modules/patterns/pattern_repair_suggester.py
# 🧠 Suggests repairs or enhancements to patterns when matches fail
# Uses symbolic glyph logic, wildcard inference, and structure comparison

import difflib
from typing import List, Dict, Any
from backend.modules.symbolic_spreadsheet.utils.glyph_utils import parse_logic_to_glyphs
from backend.modules.patterns.pattern_registry_loader import load_pattern_registry


# ─── Repair Suggestion Entry Point ──────────────────────────────────────────

def suggest_pattern_repairs(logic: str) -> List[Dict[str, Any]]:
    """
    Attempts to find the closest-matching pattern for failed glyphs.
    Suggests wildcard use, partial matches, or structure fixes.
    """
    try:
        input_glyphs = parse_logic_to_glyphs(logic)
    except Exception as e:
        print(f"[Error] Failed to parse logic: {e}")
        return []

    try:
        registry = load_pattern_registry()
    except Exception as e:
        print(f"[Error] Failed to load pattern registry: {e}")
        return []

    suggestions = []

    for pattern in registry:
        pattern_name = pattern.get("name", "unnamed")
        pattern_glyphs = pattern.get("glyphs", [])
        score, issues = compare_glyph_sequences(input_glyphs, pattern_glyphs)
        if 0 < score < 1.0:
            patch = _suggest_patch(input_glyphs, pattern_glyphs, issues)
            suggestions.append({
                "pattern": pattern_name,
                "similarity": round(score, 2),
                "issues": issues,
                "patch": patch
            })

    return sorted(suggestions, key=lambda s: -s["similarity"])


# ─── Glyph Sequence Comparator ───────────────────────────────────────

def compare_glyph_sequences(input_glyphs: List[Dict], pattern_glyphs: List[Dict]) -> tuple[float, List[str]]:
    """
    Compares two glyph sequences and returns a similarity score [0,1]
    and a list of mismatched elements or structural suggestions.
    """
    matcher = difflib.SequenceMatcher(None, _glyph_repr_list(pattern_glyphs), _glyph_repr_list(input_glyphs))
    ratio = matcher.ratio()
    differences = []

    for i, (pg, ig) in enumerate(zip(pattern_glyphs, input_glyphs)):
        if pg["type"] != ig["type"]:
            differences.append(f"Type mismatch at {i}: {pg['type']} != {ig['type']}")
        elif pg.get("value") and pg.get("value") != ig.get("value"):
            differences.append(f"Value mismatch at {i}: {pg['value']} != {ig['value']}")

    if len(pattern_glyphs) != len(input_glyphs):
        differences.append(f"Length mismatch: pattern={len(pattern_glyphs)} input={len(input_glyphs)}")

    return ratio, differences


# ─── Helper: Glyph Representation ────────────────────────────────────

def _glyph_repr_list(glyphs: List[Dict[str, str]]) -> List[str]:
    """Converts a glyph list into a string representation for difflib."""
    return [f"{g['type']}:{g.get('value', '*')}" for g in glyphs]


# ─── Patch Suggestion Helper ───────────────────────────────────

def _suggest_patch(input_glyphs: List[Dict], pattern_glyphs: List[Dict], issues: List[str]) -> Dict:
    """Propose a patch based on identified issues."""
    if "Length mismatch" in issues:
        return {"action": "pad", "glyphs": pattern_glyphs + [{"type": "pad", "value": "*"}]}
    if any("Type mismatch" in i for i in issues):
        return {"action": "type_fix", "glyphs": [{**g, "type": p["type"]} for g, p in zip(input_glyphs, pattern_glyphs)]}
    return {"action": "none"}


# ─── CLI Tester ─────────────────────────────────────

if __name__ == "__main__":
    test_inputs = [
        "a + b",
        "sin(x)",
        "x ⊕ y",
        "overwrite(memory)",
        "if x > 0: return x ** 2"
    ]

    for logic in test_inputs:
        print(f"\n🔍 Testing: {logic}")
        suggestions = suggest_pattern_repairs(logic)
        if suggestions:
            for s in suggestions:
                print(f"  ⚠️ Pattern: {s['pattern']}, Similarity: {s['similarity']}, Issues: {s['issues']}, Patch: {s['patch']}")
        else:
            print("  ✅ No issues detected / exact match")