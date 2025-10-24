# ================================================================
# 🧠 Phase 45G — Atomize Knowledge Graph (Lexical + Resonant)
# ================================================================
"""
Transforms the entire lexical–semantic layer into a living,
resonant atomic lattice within AION.brain.KGC.

Inputs:
    data/lexicons/lexicore.lex.json
    data/lexicons/language_resonance_matrix.json
    data/lexicons/etymology_lineage.ety.json
    data/semantic/wikigraph.json
    data/qtensor/langfield_resonance_adapted.qdata.json

Outputs:
    data/knowledge/atoms/wikigraph_atoms.qkg.json
    backend/modules/dimensions/containers/hoberman_knowledge_sphere.dc.json
    (plus injection into AION.brain.KGC)
"""

import json, time, logging
from pathlib import Path
from typing import Dict, Any, List

from backend.modules.dimensions.containers.atom_container import AtomContainer
from backend.modules.dimensions.containers.hoberman_container import HobermanContainer
from backend.modules.aion_knowledge import knowledge_graph_core as KGC
from backend.modules.codex.codex_utils import generate_hash

logger = logging.getLogger(__name__)

# Input sources
LEX_PATH   = Path("data/lexicons/lexicore.lex.json")
LRM_PATH   = Path("data/lexicons/language_resonance_matrix.json")
ETY_PATH   = Path("data/lexicons/etymology_lineage.ety.json")
WIKI_PATH  = Path("data/semantic/wikigraph.json")
QDATA_PATH = Path("data/qtensor/langfield_resonance_adapted.qdata.json")

# Outputs
ATOMIZED_PATH = Path("data/knowledge/atoms/wikigraph_atoms.qkg.json")
HOBERMAN_PATH = Path("backend/modules/dimensions/containers/hoberman_knowledge_sphere.dc.json")


class AtomizeKnowledgeGraph:
    def __init__(self):
        self.atoms: List[AtomContainer] = []
        self.hoberman: HobermanContainer = None
        self.summary: Dict[str, Any] = {}
        self.sources = {}

    # ------------------------------------------------------------
    def _safe_load(self, path: Path):
        if not path.exists():
            logger.warning(f"[Atomize] Missing source: {path}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception as e:
                logger.error(f"[Atomize] Failed to load {path}: {e}")
                return {}

    # ------------------------------------------------------------
    def load_all_sources(self):
        self.sources = {
            "lex":  self._safe_load(LEX_PATH),
            "lrm":  self._safe_load(LRM_PATH),
            "ety":  self._safe_load(ETY_PATH),
            "wiki": self._safe_load(WIKI_PATH),
            "qdat": self._safe_load(QDATA_PATH),
        }
        logger.info("[Atomize] Loaded all lexical–semantic sources.")

    # ------------------------------------------------------------
    def _extract_resonance(self, wid: str) -> Dict[str, Any]:
        """Gather Φ–ψ–η–Λ resonance data for a word id."""
        qfield = self.sources.get("qdat", {}).get("tensor_field", {})
        ety_ln = self.sources.get("ety", {}).get("lineage", [])
        lrm_mx = self.sources.get("lrm", {}).get("matrix", {})

        Φ = ψ = η = Λ = q_val = phase = 1.0

        # from QTensor
        if wid in qfield:
            d = qfield[wid]
            Φ, ψ, η, Λ = d.get("Φ", 1.0), d.get("ψ", 1.0), d.get("η", 1.0), d.get("Λ", 1.0)
            q_val, phase = d.get("q_val", 1.0), d.get("phase", 0.0)

        # etym depth override
        for e in ety_ln:
            if isinstance(e, dict) and e.get("word", "").lower() == wid:
                η = e.get("depth", η)

        # lexical correlation fallback
        if wid in lrm_mx and wid in lrm_mx[wid]:
            ψ = lrm_mx[wid][wid]

        return {"Φ": Φ, "ψ": ψ, "η": η, "Λ": Λ, "q_val": q_val, "phase": phase}

    # ------------------------------------------------------------
    def build_atoms(self, graph: Dict[str, Any] = None):
        """Create AtomContainers for both lexical and semantic entries."""
        graph = graph or {}
        # load lexicon entries (list)
        lex_path = Path("data/lexicons/lexicore.lex.json")
        lex_entries = []
        if lex_path.exists():
            try:
                lex_entries = json.load(open(lex_path))
            except Exception as e:
                logger.warning(f"[Atomize] Failed to load LexiCore: {e}")

        # --- 1️⃣ WikiGraph Nodes ---
        for node_id, node_data in graph.get("nodes", {}).items():
            title = node_data.get("title", node_id)
            atom = AtomContainer(
                id=node_id,
                kind="knowledge_atom",
                title=title,
                caps=["semantic", "knowledge", "resonant"],
                tags=node_data.get("categories", []),
                nodes=node_data.get("links", []),
                meta={
                    "resonance": node_data.get("resonance", {}),
                    "origin": "wikigraph",
                    "timestamp": time.time(),
                },
            )
            atom._register_address_and_link(hub_id="aion_knowledge_hub")
            self.atoms.append(atom)

        # --- 2️⃣ LexiCore Lemmas ---
        for entry in lex_entries:
            wid = (
                entry.get("id")
                or entry.get("word")
                or entry.get("lemma")
                or entry.get("term")
                or ""
            ).lower()
            if not wid:
                continue

            atom = AtomContainer(
                id=wid,
                kind="lexical_atom",
                title=entry.get("lemma", wid),
                caps=["lexical", "semantic", "resonant"],
                tags=[entry.get("pos", "term")],
                nodes=[],
                meta={
                    "definition": entry.get("definition", ""),
                    "phonetic": entry.get("phonetic", ""),
                    "etymology": entry.get("etymology", ""),
                    "embedding_dim": len(entry.get("embedding", [])),
                    "origin": "lexicore",
                    "timestamp": time.time(),
                },
            )
            atom._register_address_and_link(hub_id="aion_knowledge_hub")
            self.atoms.append(atom)

        logger.info(f"[Atomize] Created {len(self.atoms)} AtomContainers with resonance data.")

    # ------------------------------------------------------------
    def inject_into_KGC(self):
        """Push atoms and edges into the live AION.brain.KGC runtime."""
        if not hasattr(KGC, "add_triplet"):
            logger.warning("[Atomize] KGC interface not found — skipping live injection.")
            return

        for atom in self.atoms:
            rid = atom.id
            res = atom.meta.get("resonance", {})
            KGC.add_triplet(rid, "resonance_amplitude", str(res.get("q_val", 1.0)))
            KGC.add_triplet(rid, "phase", str(res.get("phase", 0.0)))
            for link in atom.nodes:
                KGC.add_triplet(rid, "linked_to", link)

        logger.info(f"[Atomize] Injected {len(self.atoms)} atoms into AION.brain.KGC.")

    # ------------------------------------------------------------
    def build_hoberman_sphere(self):
        """Encapsulate all atoms in a Hoberman Knowledge Sphere."""
        self.hoberman = HobermanContainer(container_id="hoberman_knowledge_sphere")
        self.hoberman.from_glyphs([a.id for a in self.atoms])
        logger.info("[Atomize] Hoberman Knowledge Sphere initialized.")

    # ------------------------------------------------------------
    def export(self):
        """Export atomized graph and Hoberman sphere."""
        ATOMIZED_PATH.parent.mkdir(parents=True, exist_ok=True)
        atom_pack = [a.export_pack() for a in self.atoms]
        with open(ATOMIZED_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "atom_count": len(atom_pack),
                "hash": generate_hash(atom_pack),
                "atoms": atom_pack
            }, f, indent=2)
        logger.info(f"[Atomize] Exported atom data → {ATOMIZED_PATH}")

        HOBERMAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HOBERMAN_PATH, "w", encoding="utf-8") as f:
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

    # ------------------------------------------------------------
    def summarize(self):
        avg_links = sum(len(a.nodes) for a in self.atoms) / max(1, len(self.atoms))
        self.summary = {
            "atoms": len(self.atoms),
            "avg_links": round(avg_links, 2),
            "timestamp": time.time(),
        }
        logger.info(f"[Atomize] Summary → {self.summary}")
        return self.summary

    # ------------------------------------------------------------
    def run_full_atomization(self):
        self.load_all_sources()
        self.build_atoms()
        self.inject_into_KGC()
        self.build_hoberman_sphere()
        self.export()
        return self.summarize()


# ------------------------------------------------------------
# Script Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print("🧠 Running AION Full Knowledge Graph Atomization…")
    builder = AtomizeKnowledgeGraph()
    summary = builder.run_full_atomization()
    print("✅ Full Atomization Complete.")
    print(json.dumps(summary, indent=2))