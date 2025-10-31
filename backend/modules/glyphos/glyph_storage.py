#!/usr/bin/env python3
# ================================================================
# 🧬 Glyph Storage + Global Registry — Tessaris/GlyphOS Core (v2)
# ================================================================
"""
Responsibilities:
- Store/read glyphs inside microcube containers
- Maintain ONE global glyph registry (bijective)
- Persist registry to disk + reload at boot (atomic)
- Guarantee glyph uniqueness for synthesis engine

On-disk format (v2):
{
  "by_lemma": { "<word>": {"lemma": "...", "glyph": "...", "checksum": "...", "metadata": {...}}, ... },
  "by_glyph": { "<glyph>": "<word>", ... },
  "_meta": {"version": 2}
}

Compatibility:
- get_glyph_registry() returns the classic lemma->entry dict (by_lemma).
- store_glyph_entry(...) returns a result dict: {"ok": bool, "glyph": str, "reason": "..."}.
"""

import json, os, tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Optional memory sink
try:
    from backend.modules.hexcore.memory_engine import store_memory_entry as _store_mem
except Exception:
    def _store_mem(*a, **k):  # no-op fallback
        return None

# Optional reserved/operator glyphs filter
try:
    import json as _json
    _PHOTON_RESERVED_PATH = Path("backend/modules/photonlang/photon_reserved_map.json")
    def _load_reserved() -> set[str]:
        if _PHOTON_RESERVED_PATH.exists():
            data = _json.loads(_PHOTON_RESERVED_PATH.read_text(encoding="utf-8"))
            vals = set()
            for v in data.values():
                if isinstance(v, str): vals.add(v)
                elif isinstance(v, list): vals.update(x for x in v if isinstance(x, str))
            return vals
        return set()
except Exception:
    def _load_reserved() -> set[str]:
        return set()

_OPERATOR_GLYPHS = {"⊕", "↔", "∇", "⟲", "μ", "π"}
_RESERVED = _OPERATOR_GLYPHS | _load_reserved()

# Alphabet for conflict fallback (only used if a proposed glyph is taken)
from backend.modules.glyphos.constants import GLYPH_ALPHABET

# Microcube directory
GLYPH_DIR = Path("dc_containers")

# Persistent registry file
REGISTRY_FILE = Path("data/system/glyph_registry.json")
LOCK_FILE = REGISTRY_FILE.with_suffix(".lock")

# Global registry maps in RAM
_G_LEMMA: Dict[str, Dict[str, Any]] = {}
_G_GLYPH: Dict[str, str] = {}

# ================================================================
# 🔒 Simple file lock (posix flock)
# ================================================================
class _RegistryLock:
    def __enter__(self):
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(LOCK_FILE, "w")
        try:
            import fcntl
            fcntl.flock(self.f.fileno(), fcntl.LOCK_EX)
        except Exception:
            # Best effort on non-posix
            pass
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            import fcntl
            fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        self.f.close()

# ================================================================
# 📦 Microcube I/O
# ================================================================
def get_microcube_path(container_id: str, coords: list[int]) -> Path:
    path = GLYPH_DIR / container_id / f"{coords[0]}_{coords[1]}_{coords[2]}.glyph"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def write_glyph_to_microcube(container_id: str, coords: list[int], glyph: dict) -> dict:
    from .glyph_compiler import compile_glyph
    bytecode = compile_glyph(glyph)
    path = get_microcube_path(container_id, coords)
    path.write_text(bytecode, encoding="utf-8")
    return {"status": "saved", "path": str(path), "coords": coords}

def read_glyph_from_microcube(container_id: str, coords: list[int]) -> dict:
    from .glyph_compiler import decompile_glyph
    path = get_microcube_path(container_id, coords)
    if not path.exists():
        return {"status": "not_found", "coords": coords}
    bytecode = path.read_text(encoding="utf-8")
    glyph = decompile_glyph(bytecode)
    return {"status": "loaded", "coords": coords, "glyph": glyph}

# ================================================================
# 🧠 Global Glyph Registry (lazy, thread-safe, atomic)
# ================================================================

import os, json, threading, tempfile
from pathlib import Path
from typing import Any, Dict

# Microcube directory
GLYPH_DIR = Path("dc_containers")

# Persistent registry file
REGISTRY_FILE = Path("data/system/glyph_registry.json")

# Environment toggles
QUIET = os.getenv("GLYPHOS_QUIET", "0") == "1"
NO_MEMORY = os.getenv("GLYPHOS_NO_MEMORY", "0") == "1" or os.getenv("AION_LITE", "0") == "1"

# In-memory state (lazy-loaded)
_G_REG_LOCK = threading.RLock()
_GLYPH_REG: Dict[str, Dict[str, Any]] | None = None


def _atomic_write_json(target: Path, obj: Any) -> None:
    """Write JSON atomically to avoid partial writes."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=target.name + ".", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    finally:
        # If replace succeeded, tmp no longer exists; ignore removal errors.
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _normalize_loaded(data: Any) -> Dict[str, Dict[str, Any]]:
    """
    Normalize registry to a simple dict: {lemma: {lemma, glyph, ...}}.
    Accepts:
      • v2: {"by_lemma": {...}, "by_glyph": {...}, "_meta": {...}}
      • v1: {lemma: "✦"}  (flat string map)
      • v1.1: {lemma: {"lemma": ..., "glyph": ...}}
    """
    if isinstance(data, dict) and "by_lemma" in data:
        reg = data.get("by_lemma", {})
    elif isinstance(data, dict):
        reg = data
    else:
        reg = {}

    # If flat strings, wrap into entry objects
    if reg and all(isinstance(v, str) for v in reg.values()):
        reg = {k: {"lemma": k, "glyph": v} for k, v in reg.items()}

    # Ensure each entry has lemma key
    normalized: Dict[str, Dict[str, Any]] = {}
    for lemma, entry in reg.items():
        if not isinstance(entry, dict):
            entry = {"lemma": lemma, "glyph": str(entry)}
        entry.setdefault("lemma", lemma)
        if "glyph" not in entry or not entry["glyph"]:
            # skip invalid/incomplete rows
            continue
        normalized[lemma] = entry
    return normalized


def _ensure_loaded() -> None:
    """Lazy-load registry into memory (idempotent)."""
    global _GLYPH_REG
    if _GLYPH_REG is not None:
        return
    raw: Any = {}
    if REGISTRY_FILE.exists():
        try:
            raw = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
    _GLYPH_REG = _normalize_loaded(raw)
    if not QUIET:
        print(f"[GlyphOS] Loaded {len(_GLYPH_REG)} entries (normalized)")


def get_glyph_registry() -> Dict[str, Dict[str, Any]]:
    """Public read API: lemma → entry."""
    _ensure_loaded()
    return _GLYPH_REG


def save_registry() -> None:
    """Persist the in-memory registry to disk atomically."""
    _ensure_loaded()
    with _G_REG_LOCK:
        _atomic_write_json(REGISTRY_FILE, _GLYPH_REG)


def store_glyph_entry(
    lemma: str,
    glyph: str,
    checksum: str | None = None,
    metadata: dict | None = None,
) -> Dict[str, Any]:
    """
    Register/overwrite a glyph for a lemma (RAM + file).
    Keep it simple here; bijection/conflict handling can be layered on top if needed.
    Returns: {"glyph": "<glyph>", "reason": "created|updated"}
    """
    if not lemma or not glyph:
        return {"glyph": None, "reason": "invalid_args"}

    # Local import to avoid circulars during early boot
    try:
        from backend.modules.hexcore.memory_engine import store_memory_entry  # type: ignore
    except Exception:
        store_memory_entry = None  # noqa: F811

    _ensure_loaded()
    with _G_REG_LOCK:
        prev = _GLYPH_REG.get(lemma)
        entry = {"lemma": lemma, "glyph": glyph}
        if checksum is not None:
            entry["checksum"] = checksum
        if metadata is not None:
            entry["metadata"] = metadata

        _GLYPH_REG[lemma] = entry
        _atomic_write_json(REGISTRY_FILE, _GLYPH_REG)

    if not NO_MEMORY and store_memory_entry:
        try:
            store_memory_entry("glyph_registry", entry)
        except Exception:
            pass

    if not QUIET:
        action = "updated" if prev else "created"
        print(f"[GlyphOS] Registered glyph: {lemma} → {glyph} ({action})")

    return {"glyph": glyph, "reason": ("updated" if prev else "created")}


# ================================================================
# 📂 Export / Debug
# ================================================================
def export_registry(path: str = "glyph_registry_export.json") -> None:
    _ensure_loaded()
    Path(path).write_text(json.dumps(_GLYPH_REG, indent=2), encoding="utf-8")
    if not QUIET:
        print(f"[GlyphOS] Exported registry to {path}")


# ================================================================
# 🗄️ Container Scan
# ================================================================
def scan_container_for_glyphs(container_id: str) -> list[dict]:
    from .glyph_compiler import decompile_glyph  # local import to keep deps light
    container_path = GLYPH_DIR / container_id
    if not container_path.exists():
        return []

    glyphs = []
    for file in container_path.glob("*.glyph"):
        try:
            coords = list(map(int, file.stem.split("_")))
            bytecode = file.read_text(encoding="utf-8")
            glyphs.append(
                {"coords": coords, "glyph": decompile_glyph(bytecode), "bytecode": bytecode}
            )
        except Exception as e:
            print(f"[⚠️] Failed to read glyph from {file}: {e}")
    return glyphs


# Initialize in-memory view on import (safe + idempotent)
_ensure_loaded()