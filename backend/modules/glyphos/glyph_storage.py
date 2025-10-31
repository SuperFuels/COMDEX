#!/usr/bin/env python3
# ================================================================
# 🧬 Glyph Storage + Global Registry — Tessaris/GlyphOS Core
# ================================================================
"""
Responsibilities:
- Store/read glyphs inside microcube containers
- Maintain ONE global glyph registry
- Persist registry to disk + reload at boot
- Guarantee glyph uniqueness for synthesis engine
"""

import json
from pathlib import Path
from .glyph_compiler import compile_glyph, decompile_glyph

# Microcube directory
GLYPH_DIR = Path("dc_containers")

# Persistent registry file
REGISTRY_FILE = Path("data/system/glyph_registry.json")

# Global registry map in RAM
G_GLYPH_REGISTRY = {}

# ================================================================
# 📦 Microcube I/O
# ================================================================
def get_microcube_path(container_id: str, coords: list[int]) -> Path:
    path = GLYPH_DIR / container_id / f"{coords[0]}_{coords[1]}_{coords[2]}.glyph"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_glyph_to_microcube(container_id: str, coords: list[int], glyph: dict) -> dict:
    bytecode = compile_glyph(glyph)
    path = get_microcube_path(container_id, coords)
    path.write_text(bytecode, encoding="utf-8")

    return {"status": "saved", "path": str(path), "coords": coords}


def read_glyph_from_microcube(container_id: str, coords: list[int]) -> dict:
    path = get_microcube_path(container_id, coords)
    if not path.exists():
        return {"status": "not_found", "coords": coords}

    bytecode = path.read_text(encoding="utf-8")
    glyph = decompile_glyph(bytecode)
    return {"status": "loaded", "coords": coords, "glyph": glyph}

# ================================================================
# 🧠 Global Glyph Registry
# ================================================================
def load_registry():
    """Load registry from disk (boot-time)"""
    global G_GLYPH_REGISTRY
    if REGISTRY_FILE.exists():
        try:
            G_GLYPH_REGISTRY = json.loads(REGISTRY_FILE.read_text())
            print(f"[GlyphOS] Loaded {len(G_GLYPH_REGISTRY)} glyphs from registry")
        except Exception as e:
            print(f"[⚠️ GlyphOS] Failed to load registry: {e}")


def save_registry():
    """Persist registry to disk"""
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(G_GLYPH_REGISTRY, indent=2))


def get_glyph_registry() -> dict:
    return G_GLYPH_REGISTRY


def store_glyph_entry(lemma: str, glyph: str, checksum: str = None, metadata: dict | None = None):
    """
    Register a glyph globally (RAM + persistent file + memory engine)
    NEW: metadata may include semantic fields: {rho, I, SQI}
    """
    from backend.modules.hexcore.memory_engine import store_memory_entry

    entry = {"lemma": lemma, "glyph": glyph, "checksum": checksum}

    # ✅ Attach semantic layer if present
    if metadata:
        entry["metadata"] = metadata

    # Update memory map
    G_GLYPH_REGISTRY[lemma] = entry
    save_registry()

    # Also save to memory engine
    try:
        store_memory_entry("glyph_registry", entry)
    except Exception:
        pass

    print(f"[GlyphOS] Registered glyph: {lemma} → {glyph}")
    if metadata:
        print(f"   └─ semantics: {metadata}")

    return True

# ================================================================
# 📂 Export / Debug
# ================================================================
def export_registry(path="glyph_registry_export.json"):
    Path(path).write_text(json.dumps(G_GLYPH_REGISTRY, indent=2), encoding="utf-8")
    print(f"[GlyphOS] Exported registry to {path}")

# ================================================================
# 🗄️ Container Scan
# ================================================================
def scan_container_for_glyphs(container_id: str) -> list[dict]:
    container_path = GLYPH_DIR / container_id
    if not container_path.exists():
        return []

    glyphs = []
    for file in container_path.glob("*.glyph"):
        try:
            coords = list(map(int, file.stem.split("_")))
            bytecode = file.read_text(encoding="utf-8")
            glyphs.append({
                "coords": coords,
                "glyph": decompile_glyph(bytecode),
                "bytecode": bytecode
            })
        except Exception as e:
            print(f"[⚠️] Failed to read glyph from {file}: {e}")
    return glyphs

# Auto-load at import
load_registry()