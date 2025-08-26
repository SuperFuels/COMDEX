from typing import List, Dict, Optional, Union, Any
from backend.modules.symbolnet.conceptnet_adapter import ConceptNetAdapter
from backend.modules.symbolnet.wikidata_adapter import WikidataAdapter
from backend.modules.symbolnet.symbolnet_bridge import SymbolNetBridge
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph


class SymbolNetIngestor:
    """
    Main orchestrator for ingesting symbolic glyphs into the SymbolNet system.
    """

    def __init__(self):
        self.adapters = {
            "conceptnet": ConceptNetAdapter(),
            "wikidata": WikidataAdapter()
        }
        self.kg_writer = KnowledgeGraphWriter()
        self.bridge = SymbolNetBridge()

    def ingest_glyph(self, glyph: Union[LogicGlyph, Dict, str], sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Ingests a glyph into SymbolNet, enriching it with semantic info from external sources.

        Args:
            glyph (LogicGlyph | dict | str): The symbolic glyph to enrich.
            sources (List[str]): Which adapters to use (default: all).

        Returns:
            Dict[str, Any]: Enriched metadata attached to the glyph.
        """
        results = {}
        sources_to_use = sources or list(self.adapters.keys())

        for source in sources_to_use:
            adapter = self.adapters.get(source)
            if adapter:
                enrichment = adapter.enrich(glyph)

                # 🔍 Clean system-level fields before merging
                if enrichment:
                    enrichment.pop("symbolnet_enriched", None)
                    enrichment.pop("symbolnet_sources", None)

                    results[source] = enrichment

                    # 🔐 Safe glyph ID extraction
                    glyph_id = getattr(glyph, "id", None) or getattr(glyph, "uid", None)
                    if not glyph_id and isinstance(glyph, dict):
                        glyph_id = glyph.get("id")

                    if glyph_id:
                        try:
                            self.kg_writer.attach_metadata(glyph_id, enrichment, source=source)
                            self.kg_writer.link_source(glyph_id, f"symbolnet:{source}")
                        except Exception as e:
                            print(f"[SymbolNetIngestor] ⚠️ Failed to attach metadata to {glyph_id}: {e}")

        # 🧠 Optional: Bridge into merged format
        merged = self.bridge.merge_data(results)

        if isinstance(glyph, LogicGlyph):
            # 🔒 Avoid recursive metadata pollution
            if not glyph.metadata.get("symbolnet_enriched"):
                glyph.metadata.update(merged)
            else:
                print(f"[SymbolNetIngestor] ⏭ Glyph already enriched — skipping metadata update.")

        return merged

    def batch_ingest(self, glyphs: List[Union[LogicGlyph, Dict, str]], sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Ingests multiple glyphs at once.

        Args:
            glyphs (List[LogicGlyph | dict | str]): List of symbolic glyphs.
            sources (Optional[List[str]]): Specific sources to use.

        Returns:
            List[Dict[str, Any]]: List of enriched metadata per glyph.
        """
        return [self.ingest_glyph(glyph, sources) for glyph in glyphs]