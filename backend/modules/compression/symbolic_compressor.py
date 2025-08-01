# backend/modules/compression/symbolic_compressor.py

import time
import hashlib
from typing import Dict, Any, Union, List

from backend.modules.glyphos.glyph_summary import summarize_glyphs

LogicNode = Union[Dict[str, Any], List[Any], str]


class SymbolicCompressor:
    def __init__(self):
        self.last_ratio = 1.0
        self.last_log = {}

    # ---------------------------------------------------------
    # 🧩 Container Compression
    # ---------------------------------------------------------
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
        """
        container["expansion"] = {
            "timestamp": time.time(),
            "status": "expanded (placeholder logic)",
            "note": "Full expansion from symbolic seed not yet implemented."
        }
        return container

    def get_last_compression_info(self) -> Dict[str, Any]:
        return self.last_log

    # ---------------------------------------------------------
    # 🧠 Logic Tree Compression (used for Hoberman / SEC inflation)
    # ---------------------------------------------------------
    def compress_logic_tree(self, logic_tree: LogicNode) -> Dict[str, Any]:
        """
        Compress a symbolic logic tree by normalizing and hashing.
        """
        normalized = self._normalize(logic_tree)
        content_hash = self._hash_logic(normalized)
        return {
            "hash": content_hash,
            "compressed": normalized,
            "size": self._count_nodes(normalized),
        }

    def decompress_logic_tree(self, compressed: Dict[str, Any]) -> LogicNode:
        """
        Decompress a previously compressed symbolic logic tree.
        """
        return compressed.get("compressed")

    # ---------------------------------------------------------
    # 🔧 Utility: Normalization, Hashing, Node Counting
    # ---------------------------------------------------------
    def _normalize(self, node: LogicNode) -> LogicNode:
        if isinstance(node, dict):
            return {k: self._normalize(v) for k, v in node.items() if v not in (None, [], {}, "")}
        elif isinstance(node, list):
            flattened = [self._normalize(n) for n in node]
            return [f for f in flattened if f not in (None, [], {}, "")]
        else:
            return node

    def _hash_logic(self, node: LogicNode) -> str:
        serialized = str(node).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def _count_nodes(self, node: LogicNode) -> int:
        if isinstance(node, dict):
            return 1 + sum(self._count_nodes(v) for v in node.values())
        elif isinstance(node, list):
            return sum(self._count_nodes(n) for n in node)
        else:
            return 1


# Singleton
symbolic_compressor = SymbolicCompressor()

def compress_container(container: Dict[str, Any]) -> Dict[str, Any]:
    return symbolic_compressor.compress_container(container)

def expand_container(container: Dict[str, Any]) -> Dict[str, Any]:
    return symbolic_compressor.expand_container(container)

def compress_logic_tree(logic_tree: LogicNode) -> Dict[str, Any]:
    return symbolic_compressor.compress_logic_tree(logic_tree)

def decompress_logic_tree(compressed: Dict[str, Any]) -> LogicNode:
    return symbolic_compressor.decompress_logic_tree(compressed)