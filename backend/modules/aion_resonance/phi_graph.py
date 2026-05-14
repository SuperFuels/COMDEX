# File: backend/modules/aion_resonance/phi_graph.py
# 🌐 AION Φ-Knowledge Graph
# Stores and evolves resonance entanglements between Φ concepts.

import json, os, math, datetime

GRAPH_PATH = "data/phi_graph.json"

class PhiGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self._load()

    # --- Persistence ---
    def _load(self):
        if os.path.exists(GRAPH_PATH):
            with open(GRAPH_PATH, "r") as f:
                data = json.load(f)
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", {})
        else:
            self.nodes, self.edges = {}, {}

    def _save(self):
        with open(GRAPH_PATH, "w") as f:
            json.dump({"nodes": self.nodes, "edges": self.edges}, f, indent=2)

    # --- Node Management ---
    def add_node(self, term, phi_vector):
        """Add or update a Φ node."""
        node = self.nodes.get(term, {})
        node.update(phi_vector)
        node["updated"] = datetime.datetime.utcnow().isoformat()
        self.nodes[term] = node
        self._save()

    def update_truth(self, term, delta):
        """Adjust belief weight (truth_weight) based on resonance."""
        node = self.nodes.setdefault(term, {"truth_weight": 0.5})
        node["truth_weight"] = max(0.0, min(1.0, node["truth_weight"] + delta))
        node["updated"] = datetime.datetime.utcnow().isoformat()
        self.nodes[term] = node
        self._save()

    # --- Edge / Entanglement Management ---
    def add_entanglement(self, a, b, relation, similarity):
        """Link two Φ nodes with an entanglement edge."""
        key = f"{a}↔{b}"
        edge = self.edges.get(key, {"strength": 0.5, "history": []})
        drift = similarity - 0.5
        edge["strength"] = max(0.0, min(1.0, edge["strength"] + drift * 0.3))
        edge["relation"] = relation
        edge["updated"] = datetime.datetime.utcnow().isoformat()
        edge["history"].append({"similarity": similarity, "relation": relation})
        self.edges[key] = edge
        self._save()

    # --- Query Interface ---
    def entangled_with(self, term):
        """Return all nodes entangled with a given term."""
        return {k: v for k, v in self.edges.items() if term in k.split("↔")}

    def find_related(self, tone="harmonic", min_strength=0.5):
        """Find all nodes of a given tone and sufficient coherence."""
        return {
            t: n for t, n in self.nodes.items()
            if n.get("Φ_coherence", 0) > min_strength and n.get("tone") == tone
        }


# Singleton helper
GRAPH = PhiGraph()

def update_phi_graph(term_a, term_b, relation, similarity, phi_a, phi_b):
    """High-level helper for auto-updating Φ graph."""
    GRAPH.add_node(term_a, phi_a)
    GRAPH.add_node(term_b, phi_b)
    GRAPH.add_entanglement(term_a, term_b, relation, similarity)

    delta_truth = (phi_a["Φ_coherence"] - phi_a["Φ_entropy"]) * 0.1
    GRAPH.update_truth(term_a, delta_truth)
    GRAPH.update_truth(term_b, -delta_truth / 2)