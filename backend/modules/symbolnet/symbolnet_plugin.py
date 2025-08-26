from typing import Optional, Dict, List, Union
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph
from backend.modules.symbolnet.symbolnet_ingestor import SymbolNetIngestor

class SymbolNetPlugin:
    """
    Plugin to enrich LogicGlyphs using SymbolNet during ingestion.
    """

    def __init__(self, enabled_sources: Optional[List[str]] = None, auto_link: bool = True):
        self.ingestor = SymbolNetIngestor()
        self.enabled_sources = enabled_sources
        self.auto_link = auto_link

    def apply(self, glyph: Union[LogicGlyph, Dict, str]) -> Optional[Dict]:
        """
        Applies SymbolNet enrichment to a glyph.

        Args:
            glyph (LogicGlyph | dict | str): A parsed symbolic glyph or raw string.

        Returns:
            Optional[Dict]: Enrichment metadata if applied.
        """
        if not glyph:
            return None

        try:
            enriched = self.ingestor.ingest_glyph(glyph, sources=self.enabled_sources)

            if self.auto_link and isinstance(glyph, LogicGlyph):
                glyph.metadata["symbolnet_enriched"] = True
                glyph.metadata["symbolnet_sources"] = list(enriched.keys())

            return enriched
        except Exception as e:
            label = getattr(glyph, "label", None) or getattr(glyph, "symbol", None) or str(glyph)
            print(f"[SymbolNetPlugin] ⚠️ Failed to enrich glyph {label}: {e}")
            return None