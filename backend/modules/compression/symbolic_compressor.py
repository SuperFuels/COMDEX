# backend/modules/compression/symbolic_compressor.py

import time
from typing import Dict, Any

from backend.modules.glyphos.glyph_summary import summarize_glyphs

class SymbolicCompressor:
    def __init__(self):
        self.last_ratio = 1.0
        self.last_log = {}

    def compress_container(self, container: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress a container by extracting essential symbolic glyphs
        and discarding ephemeral or redundant structures.
        """
        cubes = container.get("cubes", {})
        summary = summarize_glyphs(cubes)

        symbolic_seed = {}
        kept = 0
        dropped = 0

        for coord_str, meta in cubes.items():
            glyph = meta.get("glyph", "")
            if glyph in summary.get("core_glyphs", []):
                symbolic_seed[coord_str] = meta
                kept += 1
            else:
                dropped += 1

        container["cubes"] = symbolic_seed
        container["compression"] = {
            "timestamp": time.time(),
            "method": "symbolic_core_glyph_filter",
            "original": kept + dropped,
            "compressed": kept,
            "ratio": kept / (kept + dropped) if (kept + dropped) > 0 else 1.0,
        }
        self.last_ratio = container["compression"]["ratio"]
        self.last_log = container["compression"]
        return container

    def expand_container(self, container: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore symbolic container to its expanded state, if reversible logic exists.
        Placeholder: future logic will restore from memory or logic graph.
        """
        # Currently this is a no-op placeholder.
        # In real system, would use DreamCore / Memory snapshot / logic seed
        # For now, just logs expansion intent.
        container["expansion"] = {
            "timestamp": time.time(),
            "status": "expanded (placeholder logic)",
            "note": "Full expansion from symbolic seed not yet implemented."
        }
        return container

    def get_last_compression_info(self) -> Dict[str, Any]:
        return self.last_log

# Singleton
symbolic_compressor = SymbolicCompressor()

def compress_container(container: Dict[str, Any]) -> Dict[str, Any]:
    return symbolic_compressor.compress_container(container)

def expand_container(container: Dict[str, Any]) -> Dict[str, Any]:
    return symbolic_compressor.expand_container(container)