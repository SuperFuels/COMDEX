# File: backend/modules/glyphos/microgrid_index.py

from __future__ import annotations

from typing import Dict, Tuple, Optional, List, Any, Iterable
import time
import logging

log = logging.getLogger("microgrid")


class MicrogridIndex:
    """
    Lightweight in-memory index for glyphs on a (x,y,z,layer) lattice.

    Notes:
    - This class is used in a "best-effort" way across UCS modules.
    - We provide a process-global singleton hook via MicrogridIndex._GLOBAL
      because other modules already reference that attribute.
    """

    _GLOBAL: Optional["MicrogridIndex"] = None  # used by other modules

    def __init__(self):
        # Maps (x, y, z, optional layer) -> glyph metadata dict
        self.glyph_map: Dict[Tuple[int, int, int, Optional[int]], Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Singleton helpers (non-breaking)
    # ------------------------------------------------------------------
    @classmethod
    def global_instance(cls) -> "MicrogridIndex":
        """Get/create a process-global instance used by HUD taps."""
        inst = getattr(cls, "_GLOBAL", None)
        if inst is None:
            inst = cls()
            cls._GLOBAL = inst
        return inst

    @classmethod
    def set_global(cls, inst: Optional["MicrogridIndex"]) -> None:
        """Explicitly set/clear the global instance."""
        cls._GLOBAL = inst

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def register_glyph(
        self,
        x: int,
        y: int,
        z: int,
        glyph: str,
        layer: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, int, int, Optional[int]]:
        """
        Register or overwrite a glyph cell entry.

        Stores fields:
          glyph, timestamp, activations, energy, plus any provided metadata.
        """
        coord = (int(x), int(y), int(z), int(layer) if layer is not None else None)

        meta: Dict[str, Any] = dict(metadata) if isinstance(metadata, dict) else {}
        energy = meta.get("energy", 1.0)
        try:
            energy = float(energy)
        except Exception:
            energy = 1.0

        # Normalize common metadata fields
        if "tags" in meta and not isinstance(meta["tags"], list):
            meta["tags"] = [str(meta["tags"])]

        meta.update(
            {
                "glyph": str(glyph),
                "timestamp": time.time(),
                "activations": int(meta.get("activations", 0) or 0),
                "energy": energy,
            }
        )

        self.glyph_map[coord] = meta
        log.debug("Registered glyph '%s' at %s", glyph, coord)
        return coord

    def get_glyph(
        self,
        x: int,
        y: int,
        z: int,
        layer: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        return self.glyph_map.get((int(x), int(y), int(z), int(layer) if layer is not None else None))

    def remove_glyph(
        self,
        x: int,
        y: int,
        z: int,
        layer: Optional[int] = None,
    ) -> bool:
        coord = (int(x), int(y), int(z), int(layer) if layer is not None else None)
        if coord in self.glyph_map:
            del self.glyph_map[coord]
            return True
        return False

    def activate_glyph(
        self,
        x: int,
        y: int,
        z: int,
        layer: Optional[int] = None,
        *,
        decay: float = 0.98,
    ) -> Optional[Dict[str, Any]]:
        """
        Increment activations and decay energy for a glyph cell.
        Returns the updated metadata (or None if not found).
        """
        coord = (int(x), int(y), int(z), int(layer) if layer is not None else None)
        glyph_data = self.glyph_map.get(coord)
        if not glyph_data:
            return None

        glyph_data["activations"] = int(glyph_data.get("activations", 0) or 0) + 1

        try:
            glyph_data["energy"] = float(glyph_data.get("energy", 1.0)) * float(decay)
        except Exception:
            glyph_data["energy"] = 1.0

        glyph_data["timestamp"] = time.time()
        log.debug("Activated glyph at %s -> %s", coord, glyph_data)
        return glyph_data

    def sweep_region(
        self,
        x_range: range,
        y_range: range,
        z_range: range,
        layer: Optional[int] = None,
    ) -> Dict[Tuple[int, int, int, Optional[int]], Dict[str, Any]]:
        results: Dict[Tuple[int, int, int, Optional[int]], Dict[str, Any]] = {}
        layer_n = int(layer) if layer is not None else None

        for x in x_range:
            for y in y_range:
                for z in z_range:
                    coord = (int(x), int(y), int(z), layer_n)
                    if coord in self.glyph_map:
                        results[coord] = self.glyph_map[coord]

        log.debug("Swept region and found %d active glyphs", len(results))
        return results

    # ------------------------------------------------------------------
    # Import/Export helpers
    # ------------------------------------------------------------------
    def export_index(self) -> Dict[str, Dict[str, Any]]:
        """Export internal glyph map as a string-keyed dict."""
        out: Dict[str, Dict[str, Any]] = {}
        for (x, y, z, layer), meta in self.glyph_map.items():
            key = f"{x},{y},{z},{layer if layer is not None else 'null'}"
            out[key] = dict(meta) if isinstance(meta, dict) else {"value": meta}
        return out

    def import_index(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Import string-keyed glyph map into internal structure."""
        self.glyph_map.clear()
        if not isinstance(data, dict):
            log.warning("import_index: expected dict, got %s", type(data).__name__)
            return

        for key, meta in data.items():
            if not isinstance(key, str):
                continue

            parts = key.split(",")
            if len(parts) < 3:
                log.warning("Skipping malformed glyph key: %r", key)
                continue

            try:
                x, y, z = map(int, parts[:3])
                layer = None
                if len(parts) >= 4:
                    p = parts[3].strip()
                    if p and p.lower() not in ("null", "none", "?"):
                        layer = int(p)

                coord = (x, y, z, layer)

                meta_dict = dict(meta) if isinstance(meta, dict) else {"value": meta}
                # Ensure the core fields exist
                meta_dict.setdefault("glyph", meta_dict.get("glyph", ""))
                meta_dict.setdefault("timestamp", time.time())
                meta_dict.setdefault("activations", int(meta_dict.get("activations", 0) or 0))
                try:
                    meta_dict["energy"] = float(meta_dict.get("energy", 1.0))
                except Exception:
                    meta_dict["energy"] = 1.0

                self.glyph_map[coord] = meta_dict
            except Exception as e:
                log.warning("Error importing glyph at key %r: %s", key, e)

        log.info("Imported %d glyphs into microgrid index", len(self.glyph_map))

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def query_by_type(
        self,
        glyph_type: str,
        layer_filter: Optional[int] = None,
    ) -> Dict[Tuple[int, int, int, Optional[int]], Dict[str, Any]]:
        """Return all glyphs of a given `meta['type']`, optionally filtered by layer."""
        lf = int(layer_filter) if layer_filter is not None else None
        out: Dict[Tuple[int, int, int, Optional[int]], Dict[str, Any]] = {}
        for coord, meta in self.glyph_map.items():
            if not isinstance(meta, dict):
                continue
            if meta.get("type") != glyph_type:
                continue
            if lf is not None and coord[3] != lf:
                continue
            out[coord] = meta
        return out

    def get_glyph_type_map(self) -> Dict[str, List[str]]:
        """Return a glyph-type mapping for frontend HUD overlays."""
        type_map: Dict[str, List[str]] = {}
        for (x, y, z, layer), meta in self.glyph_map.items():
            gtype = "unknown"
            if isinstance(meta, dict):
                gtype = str(meta.get("type", "unknown"))
            key = f"{x},{y},{z},{layer if layer is not None else 'null'}"
            type_map.setdefault(gtype, []).append(key)
        return type_map

    def simulate_decay(self, decay_rate: float = 0.99, threshold: float = 0.01) -> int:
        """Globally decays energy values for all glyphs. Returns count of changed glyphs."""
        try:
            decay_rate = float(decay_rate)
        except Exception:
            decay_rate = 0.99
        try:
            threshold = float(threshold)
        except Exception:
            threshold = 0.01

        decayed = 0
        for _coord, meta in self.glyph_map.items():
            if not isinstance(meta, dict):
                continue
            try:
                original = float(meta.get("energy", 1.0))
            except Exception:
                original = 1.0

            new_energy = original * decay_rate
            if new_energy < threshold:
                new_energy = 0.0

            if new_energy != original:
                meta["energy"] = new_energy
                decayed += 1

        log.debug("Simulated decay for %d glyphs at rate %s", decayed, decay_rate)
        return decayed


def cube_to_coord(cube: dict) -> str:
    """Convert a cube dictionary to a coordinate string."""
    if not isinstance(cube, dict):
        return "?,?,?,?"
    x = cube.get("x", "?")
    y = cube.get("y", "?")
    z = cube.get("z", "?")
    t = cube.get("t", "?")
    return f"{x},{y},{z},{t}"


__all__ = ["MicrogridIndex", "cube_to_coord"]