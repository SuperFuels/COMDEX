# File: backend/modules/symbolic/hst/meaning_resonance_layer.py

import logging
import numpy as np
from typing import List, Dict, Any

from backend.modules.symbolic.symbol_tree_generator import SymbolicTreeNode
from backend.modules.symbolnet.symbolnet_loader import get_semantic_vector
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.sqi.sqi_scorer import score_symbolic_node_resonance
from backend.modules.codex.code_metrics import CodexMetrics

logger = logging.getLogger(__name__)

class MeaningResonanceEngine:
    def __init__(self, goal_vector: np.ndarray = None):
        self.kg_writer = KnowledgeGraphWriter()
        self.goal_vector = goal_vector
        self.codex_metrics = CodexMetrics()

    def compute_node_resonance(self, node: SymbolicTreeNode) -> Dict[str, Any]:
        label = node.label or node.metadata.get("label") or ""
        vector = get_semantic_vector(label)

        if vector is None:
            logger.debug(f"[🟡] No semantic vector found for label: {label}")
            return {"resonanceScore": 0.0, "resonantLabels": []}

        resonance_score = 0.0
        resonant_labels = []

        # 🔁 Compare against siblings or known symbolic nodes
        for peer in node.get_peers():
            peer_label = peer.label or peer.metadata.get("label")
            peer_vec = get_semantic_vector(peer_label)
            if peer_vec is not None:
                similarity = float(np.dot(vector, peer_vec) / (np.linalg.norm(vector) * np.linalg.norm(peer_vec)))
                if similarity > 0.6:
                    resonant_labels.append(peer_label)
                    resonance_score += similarity

        # 🎯 Boost score if aligned with Codex goal vector
        goal_alignment_score = 0.0
        if self.goal_vector is not None:
            norm_vec = vector / (np.linalg.norm(vector) + 1e-8)
            goal_alignment_score = float(np.dot(norm_vec, self.goal_vector))
            resonance_score += goal_alignment_score

        # 🧠 Optionally apply SQI scoring layer
        sqi_score = score_symbolic_node_resonance(node, vector)
        resonance_score += sqi_score

        # 🔁 Update node metadata
        node.metadata["resonanceScore"] = resonance_score
        node.metadata["resonantLabels"] = resonant_labels
        node.metadata["goalMatch"] = goal_alignment_score
        node.metadata["sqiResonance"] = sqi_score

        # 📊 Codex metrics feedback
        self.codex_metrics.record_resonance_event(node.label, resonance_score)

        return node.metadata

    def inject_resonance_into_tree(self, tree_root: SymbolicTreeNode):
        nodes = tree_root.flatten()
        logger.info(f"[🌌] Injecting meaning resonance into {len(nodes)} nodes...")
        for node in nodes:
            self.compute_node_resonance(node)

        # 🧠 Optionally export enriched nodes to KG
        try:
            self.kg_writer.write_symbolic_tree(tree_root)
            logger.info("[📤] Resonance-enriched symbolic tree exported to Knowledge Graph.")
        except Exception as e:
            logger.warning(f"[⚠️] Failed to export symbolic tree: {e}")