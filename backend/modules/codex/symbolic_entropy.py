# File: backend/modules/codex/symbolic_entropy.py

"""
symbolic_entropy.py

Calculates symbolic entropy, diversity, and complexity metrics
for symbolic beams and their logic trees.
"""

import math
from typing import Any, Dict, Tuple, List

def compute_entropy_metrics(beam: Any) -> float:
    """
    Compute symbolic entropy of the beam based on its symbolic logic tree.
    Entropy reflects the degree of symbolic diversity or disorder.
    """
    tree = getattr(beam, "logic_tree", None)
    if not tree:
        return 0.0

    symbol_counts = {}
    collect_symbols(tree, symbol_counts)
    total = sum(symbol_counts.values())

    if total == 0:
        return 0.0

    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in symbol_counts.values() if count > 0
    )

    return round(entropy, 4)


def compute_entropy_report(beam: Any) -> Dict[str, Any]:
    """
    Returns a detailed symbolic entropy report including:
    - Entropy score
    - Symbol diversity index
    - Operator richness
    - Tree depth
    - Total unique symbols
    """
    tree = getattr(beam, "logic_tree", None)
    if not tree:
        return {
            "entropy": 0.0,
            "depth": 0,
            "symbol_diversity": 0,
            "operator_richness": 0,
            "total_symbols": 0
        }

    symbol_counts = {}
    operator_counts = {}
    collect_symbols(tree, symbol_counts, operator_counts)

    total_symbols = sum(symbol_counts.values())
    entropy = compute_entropy_metrics(beam)
    depth = compute_tree_depth(tree)
    diversity = len(symbol_counts)
    operator_richness = len(operator_counts)

    return {
        "entropy": round(entropy, 4),
        "depth": depth,
        "symbol_diversity": diversity,
        "operator_richness": operator_richness,
        "total_symbols": total_symbols
    }


def collect_symbols(
    node: Dict[str, Any],
    symbol_counter: Dict[str, int],
    operator_counter: Dict[str, int] = None
) -> None:
    """
    Recursively collect and count symbolic labels and operators.
    """
    label = node.get("label")
    if label:
        symbol_counter[label] = symbol_counter.get(label, 0) + 1

    op = node.get("op")
    if op:
        symbol_counter[op] = symbol_counter.get(op, 0) + 1
        if operator_counter is not None:
            operator_counter[op] = operator_counter.get(op, 0) + 1

    for child in node.get("children", []):
        if isinstance(child, dict):
            collect_symbols(child, symbol_counter, operator_counter)


def compute_tree_depth(node: Dict[str, Any], depth: int = 0) -> int:
    """
    Recursively computes the maximum depth of the symbolic tree.
    """
    if not node.get("children"):
        return depth

    return max(
        compute_tree_depth(child, depth + 1)
        for child in node.get("children", [])
        if isinstance(child, dict)
    )


def compare_beam_entropy(beam_a: Any, beam_b: Any) -> Dict[str, float]:
    """
    Compare entropy between two beams.
    Returns a delta and direction.
    """
    entropy_a = compute_entropy_metrics(beam_a)
    entropy_b = compute_entropy_metrics(beam_b)
    delta = round(entropy_b - entropy_a, 4)

    return {
        "beam_a_entropy": entropy_a,
        "beam_b_entropy": entropy_b,
        "delta": delta,
        "direction": "increased" if delta > 0 else "decreased" if delta < 0 else "same"
    }