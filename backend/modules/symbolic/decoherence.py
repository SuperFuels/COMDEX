# File: backend/modules/symbolic/decoherence.py

from backend.modules.symbolic.symbol_tree_generator import SymbolicMeaningTree
from typing import Optional
import numpy as np

def calc_decoherence(tree: SymbolicMeaningTree) -> float:
    """
    Compute a symbolic decoherence score from a symbolic tree.
    
    Returns:
        float between 0.0 (fully coherent) and 1.0 (fully decoherent)
    """
    if not tree or not tree.node_index:
        return 1.0  # Fully decoherent if empty or malformed

    total_nodes = len(tree.node_index)
    if total_nodes == 0:
        return 1.0

    contradiction_count = 0
    entanglement_breaks = 0
    missing_goal_scores = 0
    entropies = []

    for node_id, node in tree.node_index.items():
        # 1. Contradictions
        if getattr(node, "status", "") == "contradiction":
            contradiction_count += 1

        # 2. Entanglement breaks
        if node.entangled_with:
            for partner_id in node.entangled_with:
                if partner_id not in tree.node_index:
                    entanglement_breaks += 1

        # 3. Missing goals
        if getattr(node, "goal_score", None) is None:
            missing_goal_scores += 1

        # 4. Entropy (from prediction or logic trace)
        if node.prediction and "entropy" in node.prediction:
            entropies.append(float(node.prediction["entropy"]))
        elif node.logic_trace and isinstance(node.logic_trace, list):
            last = node.logic_trace[-1]
            if "entropy" in last:
                entropies.append(float(last["entropy"]))

    # Normalize entropy to [0, 1], fallback to 1.0 if none found
    avg_entropy = np.mean(entropies) if entropies else 1.0
    entropy_score = max(0.0, min(avg_entropy, 1.0))

    # Weighted components
    contradiction_score = contradiction_count / total_nodes
    entangle_score = entanglement_breaks / total_nodes
    missing_score = missing_goal_scores / total_nodes

    # Final decoherence (weighted sum)
    decoherence = (
        0.4 * contradiction_score +
        0.3 * entangle_score +
        0.2 * missing_score +
        0.1 * entropy_score
    )

    return round(min(decoherence, 1.0), 4)