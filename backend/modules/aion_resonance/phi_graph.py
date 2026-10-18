from __future__ import annotations

import datetime
import json
from pathlib import Path

from backend.modules.aion_learning.vault_store import AionLearningVaultStore

GRAPH_PATH = Path("data/phi_graph.json")


class PhiGraph:
    """Business-learned resonance relationship graph."""

    ENTITY_ID = "phi_relationship_graph"

    def __init__(self, *, vault_store=None, graph_path=None):
        self.graph_path = Path(graph_path or GRAPH_PATH)
        self.vault_store = vault_store or AionLearningVaultStore(
            auto_configure=graph_path is None
        )
        self.nodes = {}
        self.edges = {}
        self._load()

    def _load(self):
        if self.vault_store.enabled:
            data = self.vault_store.get_state(self.ENTITY_ID, {"nodes": {}, "edges": {}})
        elif self.graph_path.is_file():
            try:
                data = json.loads(self.graph_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        else:
            data = {}
        self.nodes = dict(data.get("nodes", {})) if isinstance(data, dict) else {}
        self.edges = dict(data.get("edges", {})) if isinstance(data, dict) else {}

    def _save(self):
        payload = self.snapshot()
        if self.vault_store.enabled:
            self.vault_store.put_state(self.ENTITY_ID, payload)
            return
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def snapshot(self):
        return {"nodes": dict(self.nodes), "edges": dict(self.edges)}

    def add_node(self, term, phi_vector):
        node = self.nodes.get(term, {})
        node.update(phi_vector)
        node["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.nodes[term] = node
        self._save()

    def update_truth(self, term, delta):
        node = self.nodes.setdefault(term, {"truth_weight": 0.5})
        node["truth_weight"] = max(0.0, min(1.0, node["truth_weight"] + delta))
        node["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.nodes[term] = node
        self._save()

    def add_entanglement(self, a, b, relation, similarity):
        key = f"{a}↔{b}"
        edge = self.edges.get(key, {"strength": 0.5, "history": []})
        edge["strength"] = max(0.0, min(1.0, edge["strength"] + (similarity - 0.5) * 0.3))
        edge["relation"] = relation
        edge["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        edge["history"].append({"similarity": similarity, "relation": relation})
        self.edges[key] = edge
        self._save()

    def entangled_with(self, term):
        return {key: value for key, value in self.edges.items() if term in key.split("↔")}

    def find_related(self, tone="harmonic", min_strength=0.5):
        return {
            term: node for term, node in self.nodes.items()
            if node.get("Φ_coherence", 0) > min_strength and node.get("tone") == tone
        }


GRAPH = PhiGraph()


def update_phi_graph(term_a, term_b, relation, similarity, phi_a, phi_b):
    GRAPH.add_node(term_a, phi_a)
    GRAPH.add_node(term_b, phi_b)
    GRAPH.add_entanglement(term_a, term_b, relation, similarity)
    delta_truth = (phi_a["Φ_coherence"] - phi_a["Φ_entropy"]) * 0.1
    GRAPH.update_truth(term_a, delta_truth)
    GRAPH.update_truth(term_b, -delta_truth / 2)
