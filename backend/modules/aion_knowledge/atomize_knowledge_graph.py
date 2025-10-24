"""
Phase 45F — Atomize Knowledge Graph
────────────────────────────────────────────────────────────
Transforms the semantic WikiGraph (entities + links)
into a living atomic lattice composed of AtomContainers,
optionally bundled into a Hoberman Knowledge Sphere.

Input:
    data/semantic/wikigraph.json
Output:
    data/knowledge/atoms/wikigraph_atoms.qkg.json
    backend/modules/dimensions/containers/hoberman_knowledge_sphere.dc.json
"""

import json, time, logging
from pathlib import Path
from typing import Dict, Any, List

from backend.modules.dimensions.containers.atom_container import AtomContainer
from backend.modules.dimensions.containers.hoberman_container import HobermanContainer
from backend.modules.codex.codex_utils import generate_hash

logger = logging.getLogger(__name__)

WIKIGRAPH_PATH = Path("data/semantic/wikigraph.json")
ATOMIZED_PATH  = Path("data/knowledge/atoms/wikigraph_atoms.qkg.json")
HOBERMAN_PATH  = Path("backend/modules/dimensions/containers/hoberman_knowledge_sphere.dc.json")


class AtomizeKnowledgeGraph:
    """
    🧬 AtomizeKnowledgeGraph
    Converts WikiGraph nodes into AtomContainers and
    groups them into a Hoberman Knowledge Sphere.
    """

    def __init__(self):
        self.atoms: List[AtomContainer] = []
        self.hoberman: HobermanContainer = None
        self.summary: Dict[str, Any] = {}

    # ─────────────────────────────────────────
    def load_graph(self) -> Dict[str, Any]:
        """Load the semantic WikiGraph file."""
        if not WIKIGRAPH_PATH.exists():
            raise FileNotFoundError(f"WikiGraph not found: {WIKIGRAPH_PATH}")
        with open(WIKIGRAPH_PATH, "r") as f:
            data = json.load(f)
        graph = data.get("wikigraph", data)
        logger.info(f"[Atomize] Loaded WikiGraph ({len(graph.get('nodes', {}))} nodes).")
        return graph

    # ─────────────────────────────────────────
    def build_atoms(self, graph: Dict[str, Any]):
        """Create AtomContainers for each node in the WikiGraph."""
        for node_id, node_data in graph.get("nodes", {}).items():
            title = node_data.get("title", node_id)
            categories = node_data.get("categories", [])
            resonance = node_data.get("resonance", {})
            links = node_data.get("links", [])

            atom = AtomContainer(
                id=node_id,
                kind="knowledge_atom",
                title=title,
                caps=["semantic", "knowledge", "resonant"],
                tags=categories,
                nodes=links,
                meta={
                    "resonance": resonance,
                    "origin": "wikigraph",
                    "timestamp": time.time(),
                }
            )
            atom._register_address_and_link(hub_id="aion_knowledge_hub")
            self.atoms.append(atom)

        logger.info(f"[Atomize] Created {len(self.atoms)} AtomContainers.")

    # ─────────────────────────────────────────
    def build_hoberman_sphere(self):
        """Encapsulate all atoms in a Hoberman Knowledge Sphere."""
        self.hoberman = HobermanContainer(container_id="hoberman_knowledge_sphere")
        seed_glyphs = [a.id for a in self.atoms]  # symbolic identifiers for expansion
        self.hoberman.from_glyphs(seed_glyphs)
        logger.info("[Atomize] Hoberman Knowledge Sphere initialized with atom seeds.")

    # ─────────────────────────────────────────
    def export(self):
        """Export atomized graph and Hoberman sphere."""
        # Atom export
        ATOMIZED_PATH.parent.mkdir(parents=True, exist_ok=True)
        atom_pack = [a.export_pack() for a in self.atoms]
        with open(ATOMIZED_PATH, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "atom_count": len(atom_pack),
                "hash": generate_hash(atom_pack),
                "atoms": atom_pack
            }, f, indent=2)
        logger.info(f"[Atomize] Exported atom data → {ATOMIZED_PATH}")

        # Hoberman export
        HOBERMAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HOBERMAN_PATH, "w") as f:
            json.dump({
                "id": self.hoberman.container_id,
                "name": "Hoberman Knowledge Sphere",
                "type": "HobermanContainer",
                "meta": {
                    "seed_atoms": [a.id for a in self.atoms],
                    "count": len(self.atoms),
                    "geometry": "Knowledge Sphere",
                    "address": f"ucs://aion/knowledge/{self.hoberman.container_id}#container"
                }
            }, f, indent=2)
        logger.info(f"[Atomize] Exported Hoberman container → {HOBERMAN_PATH}")

    # ─────────────────────────────────────────
    def summarize(self):
        """Compute and log a brief resonance summary."""
        avg_links = sum(len(a.nodes) for a in self.atoms) / max(1, len(self.atoms))
        self.summary = {
            "atoms": len(self.atoms),
            "avg_links": round(avg_links, 2),
            "timestamp": time.time(),
        }
        logger.info(f"[Atomize] Summary → {self.summary}")
        return self.summary

    # ─────────────────────────────────────────
    def run_full_atomization(self):
        """Full end-to-end build pipeline."""
        graph = self.load_graph()
        self.build_atoms(graph)
        self.build_hoberman_sphere()
        self.export()
        return self.summarize()


# ─────────────────────────────────────────
# Global / Script Entry
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Running AION Knowledge Graph Atomization…")
    builder = AtomizeKnowledgeGraph()
    summary = builder.run_full_atomization()
    print("✅ Atomization Complete.")
    print(json.dumps(summary, indent=2))