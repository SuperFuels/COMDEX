# File: backend/modules/codex/symbolic_metadata.py

"""
symbolic_metadata.py

Attaches semantic, cognitive, and symbolic metadata to beams and logic trees.
Used during symbolic collapse, SQI reasoning, and post-mutation augmentation.
"""

import uuid
import random
import time
import logging
from typing import Dict, Any

from backend.modules.codex.symbolic_entropy import compute_entropy_metrics

logger = logging.getLogger(__name__)


def attach_symbolic_metadata(beam_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a beam dictionary with inferred symbolic metadata.
    Adds semantic tags, encoding hints, trust scores, and emotion weights.

    Args:
        beam_dict: The collapsed or mutated beam in dictionary form.

    Returns:
        Augmented beam dictionary with a `symbolic_metadata` field.
    """
    logic_tree = beam_dict.get("logic_tree", {})
    beam_id = beam_dict.get("id", str(uuid.uuid4()))

    tags = infer_tags(logic_tree)
    trust_score = estimate_trust(logic_tree)
    emotion_state = infer_emotion(logic_tree)
    entropy = compute_entropy_metrics(beam_like(beam_dict))

    metadata = {
        "beam_id": beam_id,
        "symbol_tags": tags,
        "entropy": entropy,
        "trust_score": trust_score,
        "emotion_state": emotion_state,
        "encoding": "symbolic_quantum_v1",
        "timestamp": time.time(),
    }

    beam_dict["symbolic_metadata"] = metadata
    logger.info(f"[SymbolicMetadata] Metadata attached to beam {beam_id}")
    return beam_dict


def infer_tags(logic_tree: Dict[str, Any]) -> list:
    """
    Heuristic tag inference based on tree structure and symbols.
    """
    tags = set()
    if not logic_tree:
        return ["empty"]

    label = logic_tree.get("label", "")
    op = logic_tree.get("op", "")

    if "love" in label.lower():
        tags.add("❤️ love")
    if "truth" in label.lower():
        tags.add("🧭 truth")
    if "error" in label.lower():
        tags.add("⚠️ error")
    if op in ("AND", "OR", "¬"):
        tags.add("🧠 logic")
    if op in ("→", "←", "↔"):
        tags.add("🔁 implication")
    if "contradiction" in logic_tree:
        tags.add("❗ contradiction")

    # Add depth tag
    depth = compute_tree_depth(logic_tree)
    if depth > 5:
        tags.add("🌌 deep_structure")

    return list(tags)


def estimate_trust(tree: Dict[str, Any]) -> float:
    """
    Simulate a basic symbolic trust score (0.0–1.0).
    Placeholder for deeper contextual inference.
    """
    base = 0.5
    if "truth" in str(tree).lower():
        base += 0.2
    if "error" in str(tree).lower():
        base -= 0.2
    return round(min(max(base + random.uniform(-0.1, 0.1), 0.0), 1.0), 4)


def infer_emotion(tree: Dict[str, Any]) -> str:
    """
    Simple label-based emotion inference for symbolic logic trees.
    """
    label = tree.get("label", "").lower()
    if "fear" in label or "error" in label:
        return "😨 fear"
    if "love" in label or "hope" in label:
        return "💖 love"
    if "death" in label or "null" in label:
        return "💀 void"
    return "🤖 neutral"


def compute_tree_depth(node: Dict[str, Any], current: int = 0) -> int:
    """
    Recursively compute the depth of the logic tree.
    """
    children = node.get("children", [])
    if not children:
        return current
    return max(compute_tree_depth(child, current + 1) for child in children if isinstance(child, dict))


# Wrapper so entropy can still be computed on raw beam dict
class beam_like:
    def __init__(self, beam_dict: Dict[str, Any]):
        self.logic_tree = beam_dict.get("logic_tree")