"""
Phase 45F — WikiGraph Builder (Atomized-Ready Revision)
────────────────────────────────────────────────────────
Builds an entity–concept lattice from Wikipedia or local data dumps.
Each node represents a resonance-bearing concept that will later
be atomized into the AION Knowledge Graph Container.

Output:
    data/semantic/wikigraph.json
"""

import json, time, logging
from pathlib import Path
from backend.modules.aion_language.meaning_field_engine import MFG

logger = logging.getLogger(__name__)
GRAPH_PATH = Path("data/semantic/wikigraph.json")

class WikiGraphBuilder:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.last_build = None

    # ─────────────────────────────────────────
    def add_entity(self, title: str, categories=None, links=None):
        """Register a Wikipedia entity node."""
        node_id = title.replace(" ", "_").lower()
        self.nodes[node_id] = {
            "title": title,
            "categories": categories or [],
            "links": links or [],
            "resonance": {
                "Φ_semantic": None,
                "ψ_phonetic": None,
                "η_etymic": None
            }
        }

    # ─────────────────────────────────────────
    def add_edge(self, src: str, dst: str, edge_type="concept_link"):
        """Create directional edge between entities."""
        self.edges.append({
            "source": src.replace(" ", "_").lower(),
            "target": dst.replace(" ", "_").lower(),
            "type": edge_type,
            "weight": 1.0,
            "resonance": {"Φ_link": None}
        })

    # ─────────────────────────────────────────
    def build_from_dump(self, dump_data):
        """
        Build WikiGraph from parsed Wikipedia JSON or API results.
        Expects dump_data = [{title, links[], categories[]} ...]
        """
        logger.info("[WikiGraph] Building concept lattice …")
        for entry in dump_data:
            self.add_entity(
                entry.get("title"),
                entry.get("categories"),
                entry.get("links")
            )
            for link in entry.get("links", []):
                self.add_edge(entry["title"], link)
        self.last_build = time.time()
        logger.info(f"[WikiGraph] Built {len(self.nodes)} nodes, {len(self.edges)} edges.")

    # ─────────────────────────────────────────
    def export(self):
        """Export WikiGraph lattice to disk (Atomized-ready JSON)."""
        GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        out = {
            "timestamp": self.last_build,
            "wikigraph": {
                "nodes": self.nodes,
                "edges": self.edges
            },
            "meta": {
                "schema": "wikigraph.v1",
                "source": "Wikipedia",
                "ready_for_atomization": True
            }
        }
        with open(GRAPH_PATH, "w") as f:
            json.dump(out, f, indent=2)
        logger.info(f"[WikiGraph] Exported graph → {GRAPH_PATH}")

    # ─────────────────────────────────────────
    def integrate_with_MFG(self):
        """Link concepts into MeaningFieldEngine clusters."""
        if not self.nodes:
            logger.warning("[WikiGraph] No nodes to integrate.")
            return
        for node_id, data in self.nodes.items():
            MFG.add_concept(node_id, categories=data["categories"])
        logger.info(f"[WikiGraph] Integrated {len(self.nodes)} nodes into MFG.")

    # ─────────────────────────────────────────
    def to_atom_blueprint(self):
        """Convert to AtomContainer-ready data structure."""
        blueprint = []
        for node_id, node in self.nodes.items():
            atom = {
                "id": node_id,
                "title": node["title"],
                "caps": ["knowledge-node", "semantic"],
                "tags": node["categories"],
                "meta": {
                    "resonance": node["resonance"],
                    "links": node["links"]
                }
            }
            blueprint.append(atom)
        return blueprint

    # ─────────────────────────────────────────
    def emit_to_atoms(self, atom_factory):
        """Optional hook — feed blueprint to AtomContainer builder."""
        blueprint = self.to_atom_blueprint()
        for atom in blueprint:
            atom_factory.create(atom)
        logger.info(f"[WikiGraph] Emitted {len(blueprint)} atoms to knowledge container.")

# Global Instance
try:
    WIKI
except NameError:
    WIKI = WikiGraphBuilder()
    print("🌐 WikiGraphBuilder global instance initialized as WIKI")