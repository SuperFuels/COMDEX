"""
📄 symbol_graph.py

🧠 Symbol Graph Engine for GlyphOS
Maintains a dynamic graph of symbolic relationships between glyphs, tags, and reflective insights.
Integrates with glyph interpretation (glyph_logic) and adaptive synthesis (glyph_synthesis_engine).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Design Features:
✅ Reflection Feedback: Inject reflection outputs as edges in the symbol graph.
✅ Tag-Driven Linking: Auto-link glyphs that share tags or appear in close temporal proximity.
✅ Entropy & Density Analysis: Compute graph density and trigger adaptive synthesis.
✅ Queryable Graph: Search connections between glyphs, tags, or reflective nodes.
✅ IGI Integration: Write insights back into Knowledge Graph (KnowledgeGraphWriter).
"""
import networkx as nx
from typing import Dict, List, Any, Optional
import datetime
import logging

from backend.modules.glyphos.glyph_synthesis_engine import GlyphSynthesisEngine

logger = logging.getLogger(__name__)

class SymbolGraph:
    def __init__(self):
        self.graph = nx.DiGraph()  # Directed symbol graph
        self.synth_engine = GlyphSynthesisEngine()

    def _get_kg_writer(self):
        from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
        return get_kg_writer()

    # ────────────────────────────────────────────────
    # 🏗️ Core Graph Operations
    # ────────────────────────────────────────────────
    def add_glyph_node(self, glyph: str, metadata: Dict[str, Any]):
        if glyph not in self.graph.nodes:
            self.graph.add_node(glyph, metadata=metadata, created_at=datetime.datetime.utcnow())
            logger.debug(f"[SymbolGraph] Added glyph node: {glyph}")

    def add_reflection_edge(self, source_glyph: str, reflection: str):
        reflection_node = f"reflection::{hash(reflection)}"
        if reflection_node not in self.graph.nodes:
            self.graph.add_node(reflection_node, type="reflection", content=reflection)
        self.graph.add_edge(source_glyph, reflection_node, relation="reflects")

        self._get_kg_writer().inject_self_reflection(
            message=reflection,
            trigger=source_glyph
        )
        logger.info(f"[SymbolGraph] Reflection linked: {source_glyph} -> {reflection_node}")

    def add_tag_links(self, glyph: str, tags: List[str]):
        for tag in tags:
            tag_node = f"tag::{tag}"
            if tag_node not in self.graph.nodes:
                self.graph.add_node(tag_node, type="tag")
            self.graph.add_edge(glyph, tag_node, relation="tagged")

            for other_glyph in self.graph.nodes:
                if other_glyph != glyph and self.graph.nodes[other_glyph].get("type") != "tag":
                    if self.graph.has_edge(other_glyph, tag_node):
                        self.graph.add_edge(glyph, other_glyph, relation="co-tagged")
                        logger.debug(f"[SymbolGraph] Co-tag link: {glyph} ↔ {other_glyph}")

    # ────────────────────────────────────────────────
    # 🧠 Adaptive Growth Logic
    # ────────────────────────────────────────────────
    def analyze_density_and_suggest(self):
        density = nx.density(self.graph)
        logger.info(f"[SymbolGraph] Graph density: {density:.4f}")
        if density > 0.3:
            suggestion = self.synth_engine.suggest_new_glyphs(self.graph)
            if suggestion:
                self._get_kg_writer().inject_prediction(
                    hypothesis=f"Propose synthesis of glyph {suggestion}",
                    based_on="Symbol Graph Density",
                    confidence=0.8,
                    plugin="SymbolGraph"
                )
                logger.info(f"[SymbolGraph] Suggested new glyph synthesis: {suggestion}")

    # ────────────────────────────────────────────────
    # 🔍 Querying & Export
    # ────────────────────────────────────────────────
    def query_connections(self, glyph: str) -> Dict[str, Any]:
        if glyph not in self.graph.nodes:
            return {"error": f"No glyph node found for {glyph}"}
        neighbors = list(self.graph.neighbors(glyph))
        return {
            "glyph": glyph,
            "connections": [
                {
                    "target": n,
                    "relation": self.graph.edges[glyph, n]["relation"]
                }
                for n in neighbors
            ]
        }

    def export_graph(self) -> Dict[str, Any]:
        return nx.readwrite.json_graph.node_link_data(self.graph)

    # ────────────────────────────────────────────────
    # 🔁 Reflection & Tag Feedback Hooks (A5b)
    # ────────────────────────────────────────────────
    def feed_reflection(self, glyph: str, reflection: str):
        self.add_glyph_node(glyph, metadata={"source": "reflection"})
        self.add_reflection_edge(glyph, reflection)

    def feed_tags(self, glyph: str, tags: List[str]):
        self.add_glyph_node(glyph, metadata={"source": "tag_feedback"})
        self.add_tag_links(glyph, tags)


# ────────────────────────────────────────────────
# Singleton Instance
# ────────────────────────────────────────────────
symbol_graph = SymbolGraph()