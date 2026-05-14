import os
import json
from typing import List, Dict, Any, Optional, Union

from backend.modules.symbolnet.symbolnet_ingestor import SymbolNetIngestor
from backend.modules.runtime.container_runtime import safe_load_container_by_id
from backend.modules.codex.symbolic_registry import symbolic_registry
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph


class SymbolNetOverlayInjector:
    def __init__(self):
        self.ingestor = SymbolNetIngestor()

    def inject_overlay(
        self,
        container: Union[str, Dict[str, Any]],
        save_path: Optional[str] = None,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Inject SymbolNet overlay into a given .dc.json container.

        Args:
            container: str (container ID or file path) or loaded dict.
            save_path: Optional path to save the enriched container.
            sources: Optional list of enrichment sources.

        Returns:
            The modified container dictionary.
        """
        if isinstance(container, str):
            if container.endswith(".json") and os.path.exists(container):
                with open(container, "r", encoding="utf-8") as f:
                    container_data = json.load(f)
            else:
                container_data = safe_load_container_by_id(container)
        else:
            container_data = container

        glyphs = container_data.get("glyphs", [])

        enriched_overlay = {}

        for glyph in glyphs:
            label = glyph.get("label") or glyph.get("symbol") or glyph.get("text")
            if not label:
                continue

            if "type" not in glyph:
                print(f"⚠️ Skipping glyph without 'type': {label}")
                continue

            try:
                lg = LogicGlyph.from_dict(glyph)
                enriched = self.ingestor.ingest_glyph(lg, sources)
                enriched_overlay[label] = enriched
            except Exception as e:
                print(f"⚠️ Error enriching glyph {label}: {e}")

        # Inject overlay
        if "overlays" not in container_data:
            container_data["overlays"] = {}
        container_data["overlays"]["symbolnet"] = enriched_overlay

        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(container_data, f, indent=2, ensure_ascii=False)
            print(f"[SymbolNetOverlayInjector] ✅ Saved enriched container to: {save_path}")

        return container_data


# CLI support for quick testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inject SymbolNet overlay into .dc.json container")
    parser.add_argument("input", help="Container ID or path to .dc.json file")
    parser.add_argument("--out", help="Optional path to save the updated container")
    parser.add_argument("--sources", nargs="*", help="Optional list of enrichment sources (conceptnet, wikidata)")

    args = parser.parse_args()

    injector = SymbolNetOverlayInjector()
    updated = injector.inject_overlay(
        container=args.input,
        save_path=args.out,
        sources=args.sources
    )