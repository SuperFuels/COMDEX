import math
from typing import Any, Dict, Union

def compute_innovation_score(idea: Dict[str, Any], mutated: bool = False) -> float:
    """
    Compute an overall innovation score for a symbolic idea.

    Args:
        idea (Dict): Dictionary containing symbolic idea metadata.
        mutated (bool): Whether this idea is a mutated fork.

    Returns:
        float: Final innovation score (0.0–1.0)
    """
    # Extract values with fallback defaults
    novelty = idea.get("novelty", 0.5)
    coherence = idea.get("coherence", 0.5)
    entropy = idea.get("entropy", 0.5)
    impact = idea.get("impact", 0.5)
    alignment = idea.get("alignment", 0.5)

    # Fix: Now pass the idea to measure_novelty instead of mutated
    if isinstance(mutated, dict):  # symbolic structure
        novelty_score = measure_novelty(mutated)
    else:  # fallback: use idea's own novelty score
        novelty_score = idea.get("novelty", 0.5)

    # Basic weighted score
    score = (
        0.25 * novelty_score +
        0.20 * coherence +
        0.15 * impact +
        0.15 * (1 - entropy) +  # low entropy preferred
        0.25 * alignment
    )

    # Bonuses
    if mutated:
        score *= 1.05  # small boost for mutated branches
    if alignment > 0.9:
        score += 0.05  # boost for strong alignment
    return min(score, 1.0)


def measure_symbolic_drift(a: Dict[str, Any], b: Dict[str, Any], depth: int = 0) -> float:
    """
    Compute symbolic drift between two trees. Based on label, operator, and value differences.
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        return 0.0

    drift = 0.0

    # Label difference
    if a.get("label") != b.get("label"):
        drift += 1.0

    # Operator difference
    if a.get("op") != b.get("op"):
        drift += 0.7

    # Value difference (numerical)
    if isinstance(a.get("value"), (int, float)) and isinstance(b.get("value"), (int, float)):
        delta = abs(a["value"] - b["value"])
        drift += min(delta / 10.0, 1.0)

    # Children recursive drift
    a_children = a.get("children", [])
    b_children = b.get("children", [])
    min_len = min(len(a_children), len(b_children))

    for i in range(min_len):
        drift += measure_symbolic_drift(a_children[i], b_children[i], depth + 1)

    # Drift for extra unmatched children
    drift += abs(len(a_children) - len(b_children)) * 0.5

    # Apply normalization
    return math.tanh(drift / (1.0 + depth))


def measure_novelty(tree: Dict[str, Any]) -> float:
    """
    Measure novelty based on structural and label uniqueness.
    Encourages creative structure and labeled variety.
    """
    labels = set()
    ops = set()
    value_range = [float("inf"), float("-inf")]

    def traverse(node: Dict[str, Any]):
        labels.add(node.get("label", ""))
        ops.add(node.get("op", "NONE"))
        v = node.get("value")
        if isinstance(v, (int, float)):
            value_range[0] = min(value_range[0], v)
            value_range[1] = max(value_range[1], v)
        for child in node.get("children", []):
            if isinstance(child, dict):
                traverse(child)

    traverse(tree)

    label_score = min(len(labels) / 10.0, 1.0)
    op_score = min(len(ops) / 5.0, 1.0)
    val_span = value_range[1] - value_range[0] if value_range[1] > value_range[0] else 0
    value_score = min(val_span / 10.0, 1.0)

    return 0.4 * label_score + 0.3 * op_score + 0.3 * value_score


def detect_contradictions(tree: Dict[str, Any]) -> float:
    """
    Penalize contradictions marked in the logic tree.
    Returns a value in [0.0, 1.0].
    """
    contradiction_count = 0
    total = 0

    def walk(node: Dict[str, Any]):
        nonlocal contradiction_count, total
        total += 1
        if node.get("contradiction") is True:
            contradiction_count += 1
        for child in node.get("children", []):
            if isinstance(child, dict):
                walk(child)

    walk(tree)

    if total == 0:
        return 0.0

    return min(contradiction_count / total, 1.0)

def get_innovation_score(idea: Dict[str, Any], mutated: Union[bool, Dict[str, Any]] = False) -> float:
    """
    Wrapper for backward compatibility with systems calling `get_innovation_score`.
    """
    return compute_innovation_score(idea, mutated=mutated)