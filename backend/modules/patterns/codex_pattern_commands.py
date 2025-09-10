from typing import List, Dict, Any
from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine
from backend.modules.patterns.pattern_registry import Pattern, registry
from backend.codexcore_virtual.instruction_registry import register_codex_command
from backend.modules.codex.codex_context_tools import CodexContext
from backend.modules.patterns.pattern_prediction_hooks import PatternPredictionHooks

engine = SymbolicPatternEngine()


@register_codex_command("detect_pattern")
def detect_pattern_cmd(args: Dict[str, Any], ctx: CodexContext):
    """
    Detects matching patterns in the current context.
    Usage: detect_pattern sequence=["↔", "⊕", "⧖"]
    """
    glyphs = args.get("sequence", [])
    matches = engine.detect_patterns(glyphs)
    return {"matches": [m.to_dict() for m in matches]}


@register_codex_command("mutate_pattern")
def mutate_pattern_cmd(args: Dict[str, Any], ctx: CodexContext):
    """
    Applies mutation to a pattern by ID or inline.
    Usage: mutate_pattern pattern_id="pattern-1234"
    """
    pattern_id = args.get("pattern_id")
    pattern = pattern_registry.get(pattern_id)
    if not pattern:
        return {"error": "Pattern not found."}
    mutated = engine.mutate_pattern(pattern.to_dict())
    return {"mutated": mutated}


@register_codex_command("predict_next")
def predict_next_cmd(args: Dict[str, Any], ctx: CodexContext):
    """
    Predicts next glyphs given a glyph prefix.
    Usage: predict_next sequence=["⊕", "↔"]
    """
    hooks = PatternPredictionHooks()
    sequence = args.get("sequence", [])
    predictions = hooks.suggest_next_glyphs(sequence)
    return {"predictions": predictions}


# --------------------------------------------------------
# Utility: Detect patterns in a container
# --------------------------------------------------------

from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine

engine = SymbolicPatternEngine()

def detect_pattern_in_container(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detects symbolic patterns inside a .dc container by scanning its glyph sequence.
    Supports both flat glyph lists and symbolic trees.
    """
    # ✅ Try flat glyphs first
    glyphs = container.get("glyphs") or container.get("content", {}).get("glyphs")

    # ✅ Fallback: extract from symbolic_tree if flat glyphs are missing
    if not glyphs:
        symbolic_tree = container.get("symbolic_tree", {})
        glyphs = _extract_all_glyphs_from_tree(symbolic_tree)

    if not glyphs or not isinstance(glyphs, list):
        return []

    matched_patterns: List[Pattern] = engine.detect_patterns(glyphs)
    return matched_patterns


def _extract_all_glyphs_from_tree(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Recursively extract glyphs from a symbolic_tree["nodes"] list.
    """
    nodes = tree.get("nodes", [])
    glyphs = []

    for node in nodes:
        glyph = node.get("glyph")
        if glyph:
            glyphs.append(glyph)
            # Recurse if nested glyphs (e.g. type=expression)
            if isinstance(glyph, dict) and "glyphs" in glyph:
                glyphs.extend(_extract_nested_glyphs(glyph["glyphs"]))

    return glyphs


def _extract_nested_glyphs(glyph_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Helper to recursively extract all nested glyphs from an expression.
    """
    extracted = []
    for glyph in glyph_list:
        extracted.append(glyph)
        if isinstance(glyph, dict) and "glyphs" in glyph:
            extracted.extend(_extract_nested_glyphs(glyph["glyphs"]))
    return extracted

# --------------------------------------------------------
# Utility: Mutate pattern inside container
# --------------------------------------------------------

from backend.modules.patterns.creative_pattern_mutation import CreativePatternMutation

def mutate_pattern_in_container(container: Dict[str, Any]) -> Dict[str, Any]:
    print("🧬 Starting mutation for container:", container.get("id"))

    mutator = CreativePatternMutation()
    mutations = mutator.propose_mutations_for_container(container, strategy="divergent")

    if not mutations:
        print("❌ No pattern matched.")
        return {"error": "No pattern matched."}

    # Apply first mutation to container
    mutated_pattern = mutations[0]
    container.setdefault("patterns", []).append(mutated_pattern)
    container["glyphs"] = mutated_pattern["glyphs"]

    print("✅ Mutation applied:", mutated_pattern)
    return {
        "mutated": True,
        "pattern": mutated_pattern,
        "strategy": mutated_pattern.get("mutation_strategy", "unknown")
    }

# --------------------------------------------------------
# Utility: Predict next glyphs from container
# --------------------------------------------------------

def predict_next_from_pattern(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Predicts the next likely glyphs from the first expression in the symbolic tree.
    """
    hooks = PatternPredictionHooks()
    nodes = container.get("symbolic_tree", {}).get("nodes", [])

    for node in nodes:
        glyphs = node.get("glyph", {}).get("glyphs")
        if glyphs and isinstance(glyphs, list):
            return hooks.suggest_next_glyphs(glyphs)

    return []