# ──────────────────────────────────────────────
#  Tessaris * Fabric Ontology Engine (Stage 14)
#  Knowledge Graph Propagation & Resonance Coupling
#  Enables ψ-κ-T-Φ field deltas to update ontology nodes
#  and propagate meaning through connected graph edges.
# ──────────────────────────────────────────────

import os
import json
import uuid
import math
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.modules.holograms.morphic_ledger import morphic_ledger

# Optional: Graph storage backend (can evolve to Neo4j / RDF later)
FABRIC_PATH = "data/fabric/fabric_ontology.jsonl"
os.makedirs(os.path.dirname(FABRIC_PATH), exist_ok=True)

logger = logging.getLogger(__name__)


class FabricOntology:
    """
    The Fabric Ontology represents the semantic substrate of Tessaris -
    a knowledge graph where every node embodies a concept, glyph, or symbol
    that can resonate, update, or collapse according to ψ-κ-T-Φ deltas.
    """

    def __init__(self, fabric_path: str = FABRIC_PATH):
        self.fabric_path = fabric_path
        self.graph: Dict[str, Dict[str, Any]] = {}
        self._load_existing_graph()

    # ──────────────────────────────────────────────
    #  Graph IO
    # ──────────────────────────────────────────────
    def _load_existing_graph(self):
        if os.path.exists(self.fabric_path):
            try:
                with open(self.fabric_path, "r", encoding="utf-8") as f:
                    for line in f:
                        node = json.loads(line)
                        self.graph[node["id"]] = node
                logger.info(f"[FabricOntology] Loaded {len(self.graph)} ontology nodes.")
            except Exception as e:
                logger.warning(f"[FabricOntology] Failed to load ontology: {e}")

    def _persist_node(self, node: Dict[str, Any]):
        try:
            with open(self.fabric_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(node) + "\n")
        except Exception as e:
            logger.warning(f"[FabricOntology] Failed to persist node: {e}")

    # ──────────────────────────────────────────────
    #  Core Node Operations
    # ──────────────────────────────────────────────
    def upsert_node(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> str:
        nid = attributes.get("id") if attributes and "id" in attributes else f"fabric_{uuid.uuid4().hex[:8]}"
        node = self.graph.get(nid, {
            "id": nid,
            "name": name,
            "created": datetime.utcnow().isoformat(),
            "links": [],
            "state": {"ψ": 0.0, "κ": 0.0, "T": 0.0, "Φ": 0.0, "μ": 0.0},
        })
        if attributes:
            node.update(attributes)
        self.graph[nid] = node
        self._persist_node(node)
        return nid

    def link_nodes(self, source_id: str, target_id: str, relation: str = "resonates_with", weight: float = 1.0):
        if source_id not in self.graph or target_id not in self.graph:
            return
        link = {"target": target_id, "relation": relation, "weight": weight}
        self.graph[source_id]["links"].append(link)

    # ──────────────────────────────────────────────
    #  Resonance Propagation Engine
    # ──────────────────────────────────────────────
    def propagate_resonance(self, psi_delta: float, kappa_delta: float, coherence: float):
        """
        Propagate ψ-κ-T deltas through the graph.
        Each node receives an influence proportional to:
            ΔΦ = (ψΔ + κΔ) * link_weight * coherence
        """
        try:
            if not self.graph:
                logger.warning("[FabricOntology] Empty graph; nothing to propagate.")
                return

            delta_log = []
            for nid, node in self.graph.items():
                Φ_prev = node["state"].get("Φ", 0.0)
                resonance_sum = 0.0
                for link in node.get("links", []):
                    resonance_sum += link.get("weight", 1.0) * (psi_delta + kappa_delta)
                ΔΦ = resonance_sum * coherence
                node["state"]["Φ"] = Φ_prev + ΔΦ
                node["state"]["ψ"] += psi_delta
                node["state"]["κ"] += kappa_delta
                node["state"]["T"] = (node["state"]["ψ"] + node["state"]["κ"]) / 2
                node["state"]["μ"] = math.tanh(node["state"]["Φ"])
                delta_log.append({
                    "node_id": nid,
                    "ΔΦ": round(ΔΦ, 6),
                    "Φ_new": round(node["state"]["Φ"], 6),
                })

            # Write propagation result to Morphic Ledger
            morphic_ledger.append({
                "timestamp": datetime.utcnow().isoformat(),
                "psi_delta": psi_delta,
                "kappa_delta": kappa_delta,
                "coherence": coherence,
                "propagation_events": delta_log,
                "origin": "FabricOntology",
            }, observer="system_fabric")

            logger.info(f"[FabricOntology] Propagated Δψ={psi_delta:.4f}, Δκ={kappa_delta:.4f} to {len(self.graph)} nodes.")
        except Exception as e:
            logger.error(f"[FabricOntology] Propagation error: {e}")

    # ──────────────────────────────────────────────
    #  Semantic Gravity Synchronization
    # ──────────────────────────────────────────────
    def sync_semantic_gravity(self, gravity_map: Dict[str, float]):
        """
        Integrate semantic gravity wells (from SymbolicHSXBridge)
        into ontology resonance states.
        """
        try:
            for nid, gravity in gravity_map.items():
                if nid in self.graph:
                    self.graph[nid]["state"]["μ"] = (
                        self.graph[nid]["state"].get("μ", 0.0) * 0.8 + gravity * 0.2
                    )
            logger.debug(f"[FabricOntology] Synced {len(gravity_map)} semantic gravity entries.")
        except Exception as e:
            logger.warning(f"[FabricOntology] Failed to sync semantic gravity: {e}")

    # ──────────────────────────────────────────────
    #  Export Utilities
    # ──────────────────────────────────────────────
    def export_graph(self) -> Dict[str, Any]:
        return {"nodes": list(self.graph.values()), "edges": [
            {"source": nid, **link} for nid, n in self.graph.items() for link in n.get("links", [])
        ]}