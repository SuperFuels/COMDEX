# holographic_tree_generator.py
# 🌀 Z11: Render SymbolicMeaningTree inside GHX/QFC holographic environments

from typing import Dict, List, Any
from backend.modules.symbolic.hst.symbolic_meaning_tree import SymbolicMeaningTree, SymbolicTreeNode
from backend.modules.sqi.qglyph_utils import generate_qglyph_for_node
import uuid


def build_holographic_tree(symbolic_tree: SymbolicMeaningTree, agent_id: str = None) -> Dict[str, Any]:
    """
    Converts a SymbolicMeaningTree into a GHX/QFC-compatible holographic rendering structure.
    Includes 3D entangled nodes, morphic overlays, replay paths, and multi-agent fusion metadata.
    """
    def node_to_ghx_format(node: SymbolicTreeNode, depth: int = 0) -> Dict[str, Any]:
        qglyph = generate_qglyph_for_node(node)
        return {
            "id": node.node_id,
            "label": node.symbol.label,
            "type": node.symbol.type,
            "depth": depth,
            "position": compute_3d_position(node, depth),
            "morphic_overlay": build_morphic_overlay(node),
            "glyph_id": node.symbol.glyph_id,
            "entangled_ids": node.entangled_ids,
            "agent_id": agent_id,
            "qglyph": qglyph,
            "children": [node_to_ghx_format(child, depth + 1) for child in node.children]
        }

    return {
        "tree_id": symbolic_tree.tree_id,
        "root": node_to_ghx_format(symbolic_tree.root),
        "timestamp": symbolic_tree.created_at,
        "metadata": symbolic_tree.metadata,
        "fusion_enabled": True,
        "supports_replay": True
    }


def compute_3d_position(node: SymbolicTreeNode, depth: int) -> Dict[str, float]:
    """Simple radial layout based on node depth and entanglement."""
    import math
    angle = hash(node.node_id) % 360
    radius = 1.5 * (depth + 1)
    return {
        "x": radius * math.cos(math.radians(angle)),
        "y": depth * 2.0,
        "z": radius * math.sin(math.radians(angle))
    }


def build_morphic_overlay(node: SymbolicTreeNode) -> Dict[str, Any]:
    """Generates morphic visual metadata overlays for a symbolic node."""
    return {
        "goal_match": node.scores.get("goal_match_score", 0.0),
        "entropy": node.scores.get("entropy", 0.0),
        "mutation_path": node.mutation_path,
        "node_type": node.symbol.type,
        "is_prediction": node.metadata.get("is_prediction", False)
    }


# Optional CLI or GHX hook

def generate_and_export_holographic_tree(symbolic_tree: SymbolicMeaningTree, output_path: str) -> str:
    """
    Generates a holographic tree JSON export and saves it to disk.
    """
    import json
    tree_data = build_holographic_tree(symbolic_tree)
    with open(output_path, 'w') as f:
        json.dump(tree_data, f, indent=2)
    return output_path


# 🔁 GHX/QFC engines can call `build_holographic_tree(...)` directly for live rendering injection.