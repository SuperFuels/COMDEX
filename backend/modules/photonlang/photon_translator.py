# 📁 backend/modules/photonlang/photon_translator.py
"""
Photon Translator Core
────────────────────────────────────────────
Maps textual Photon/Python code into glyph-plane representations
using the canonical reserved manifest.

Provides:
  • translate_line(line:str) → glyph-string
  • compile_file(path:str)   → compiled structure
"""

import json, re
from pathlib import Path
from typing import Dict, Any, List

# Manifest path
MANIFEST_PATH = Path(__file__).resolve().parent / "photon_reserved_map.json"

# ─── Load Reserved Manifest ───────────────────────────────────────────────
try:
    RESERVED = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
except Exception as e:
    RESERVED = {"ops": {}, "keywords": {}, "glyphs": [], "domains": []}
    print(f"[PhotonTranslator] ⚠️ Failed to load manifest: {e}")

# Flattened operator list for fast lookup
ALL_OPS = {op for domain_ops in RESERVED.get("ops", {}).values() for op in domain_ops}
ALL_KW = {kw for domain_kws in RESERVED.get("keywords", {}).values() for kw in domain_kws}

# ─── Core Translator ──────────────────────────────────────────────────────
class PhotonTranslator:
    def __init__(self):
        self.reserved_ops = ALL_OPS
        self.reserved_kw = ALL_KW
        self.glyph_map = self._build_glyph_map()

    def _build_glyph_map(self) -> Dict[str, str]:
        """Static demo glyph-map (extendable via wiki lexicon later)."""
        base = {
            "container_id": "💡",
            "wave": "🌊",
            "resonance": "🌀",
            "memory": "🧠",
            "photon": "⚛",
            "quantum": "✦",
            "field": "🜁",
            "nav": "🧭",
        }
        return base

    # ─── Translate one line ───────────────────────────────────────────────
    def translate_line(self, line: str) -> str:
        """Convert reserved text & glyphs inline → symbolic representation."""
        if not line.strip():
            return ""

        out = line
        # Replace keywords → [kw]
        for kw in sorted(self.reserved_kw, key=len, reverse=True):
            out = re.sub(rf"\b{kw}\b", f"[{kw}]", out)

        # Replace glyph map entries
        for word, glyph in self.glyph_map.items():
            out = re.sub(rf"\b{word}\b", glyph, out)

        # Highlight operators
        for op in self.reserved_ops:
            out = out.replace(op, f" {op} ")

        return out.strip()

    # ─── Compile full Photon file ─────────────────────────────────────────
    def compile_file(self, path: str) -> Dict[str, Any]:
        """Compile Photon source file into a symbolic capsule (AST placeholder)."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)
        lines = p.read_text(encoding="utf-8").splitlines()
        translated = [self.translate_line(l) for l in lines]
        return {
            "source": str(p),
            "translated": "\n".join(translated),
            "glyph_count": sum(l.count("💡") + l.count("🌊") + l.count("🧠") for l in translated),
            "domains": RESERVED.get("domains", []),
        }

# ─── Exported Helper (for backend.api.photon_api) ───────────────────────────────
def translate_photon_line(line: str) -> str:
    """
    Global helper alias for PhotonTranslator().translate_line(line)
    Used by backend.api.photon_api to keep imports simple.
    """
    translator = PhotonTranslator()
    return translator.translate_line(line)

# ─── CLI Test Harness ─────────────────────────────────────────────────────
if __name__ == "__main__":
    pt = PhotonTranslator()
    sample = 'import quantum\ncontainer_id = wave ⊕ resonance'
    print("Original:", sample)
    print("Translated:", pt.translate_line(sample))