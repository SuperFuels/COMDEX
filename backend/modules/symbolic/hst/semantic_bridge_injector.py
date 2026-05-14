import logging
from typing import List, Optional, Dict, Tuple
import numpy as np

from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicTreeNode, SymbolicMeaningTree
from backend.modules.symbolic.symbolnet.symbolnet_loader import get_semantic_vector, cosine_similarity

logger = logging.getLogger(__name__)


class SemanticBridgeInjector:
    def __init__(self, similarity_threshold: float = 0.75):
        self.similarity_threshold = similarity_threshold

    def inject_semantic_bridges(self, tree: SymbolicMeaningTree) -> List[Tuple[str, str, float]]:
        """
        Injects cross-node semantic bridges based on vector similarity using SymbolNet / ConceptNet.
        """
        bridges = []
        vectors = {}

        # Step 1: Precompute vectors
        for node_id, node in tree.node_index.items():
            vec = get_semantic_vector(node.label)
            if vec is not None:
                vectors[node_id] = vec

        # Step 2: Pairwise similarity
        ids = list(vectors.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                id1, id2 = ids[i], ids[j]
                sim = cosine_similarity(vectors[id1], vectors[id2])
                if sim >= self.similarity_threshold:
                    node1 = tree.node_index[id1]
                    node2 = tree.node_index[id2]

                    # Inject mutual bridge metadata
                    node1.metadata.setdefault("semantic_bridges", []).append({
                        "target": id2,
                        "score": sim
                    })
                    node2.metadata.setdefault("semantic_bridges", []).append({
                        "target": id1,
                        "score": sim
                    })

                    bridges.append((id1, id2, sim))
                    logger.info(f"[🌐] Semantic bridge: {id1} ↔ {id2} | sim={sim:.2f}")

        return bridges