# pattern_kg_bridge.py
import datetime
from typing import List, Dict, Any, Optional
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine
from backend.modules.patterns.pattern_sqi_scorer import compute_pattern_sqi_score


class PatternKGBridge:
    """
    Bridges symbolic patterns into the Knowledge Graph.
    Supports injection, mutation lineage, and SQI metadata encoding.
    """

    def __init__(self):
        self.kg = get_kg_writer()
        self.registry = PatternRegistry()
        self.engine = SymbolicPatternEngine()

    def inject_pattern_as_kg_node(self, pattern: Dict[str, Any], container_id: Optional[str] = None) -> str:
        """
        Injects a symbolic pattern as a KG node with attached metadata.
        """
        pattern_id = pattern.get("pattern_id") or f"pattern_{datetime.datetime.utcnow().isoformat()}"
        label = pattern.get("label", pattern_id)
        glyphs = pattern.get("glyphs", [])
        metadata = {
            "pattern_id": pattern_id,
            "glyphs": glyphs,
            "strategy": pattern.get("mutation_strategy"),
            "sqi_score": pattern.get("sqi_score"),
            "tags": pattern.get("tags", []),
            "origin": pattern.get("parent_pattern_id"),
            "container": container_id,
        }

        # Add as KG node
        return self.kg.add_node(node_id=pattern_id, label=label, meta=metadata)

    def inject_mutation_relation(self, parent_id: str, child_id: str) -> None:
        """
        Adds a directional edge between parent and mutated pattern.
        """
        self.kg.add_edge(src=parent_id, dst=child_id, relation="mutated_into")

    def inject_batch_patterns(self, patterns: List[Dict[str, Any]], container_id: Optional[str] = None) -> List[str]:
        """
        Injects multiple patterns into the KG.
        Returns list of injected node IDs.
        """
        inserted_ids = []
        for pattern in patterns:
            node_id = self.inject_pattern_as_kg_node(pattern, container_id=container_id)
            inserted_ids.append(node_id)

            # If parent ID exists, add mutation edge
            parent_id = pattern.get("parent_pattern_id")
            if parent_id:
                self.inject_mutation_relation(parent_id, node_id)

        return inserted_ids

    def auto_inject_from_container(self, container: Dict[str, Any], strategy: str = "divergent") -> List[str]:
        """
        Detects symbolic patterns in a container, mutates them, and injects into the KG.
        """
        patterns = self.engine.detect_patterns(container)
        mutated = self.engine.mutate_patterns(patterns, strategy=strategy)

        for p in mutated:
            if "sqi_score" not in p:
                p["sqi_score"] = compute_pattern_sqi_score(p)

        return self.inject_batch_patterns(mutated, container_id=container.get("id"))

    def inject_custom_relation(self, from_id: str, to_id: str, relation: str = "relates_to", extra_meta: Optional[Dict[str, Any]] = None):
        """
        Manually inject a relationship between two symbolic pattern nodes.
        """
        return self.kg.add_edge(
            src=from_id,
            dst=to_id,
            relation=relation
        )

    def inject_pattern_prediction(self, pattern: Dict[str, Any], prediction: str, confidence: float = 0.8, plugin: str = "PatternAI") -> str:
        """
        Injects a prediction glyph tied to a symbolic pattern.
        """
        return self.kg.inject_prediction(
            hypothesis=prediction,
            based_on=pattern.get("pattern_id"),
            confidence=confidence,
            plugin=plugin
        )