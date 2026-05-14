# File: backend/modules/dimensions/containers/tesseract_hub.py
from typing import Optional, Dict, Any

# Safe fallbacks so this module never hard-crashes at import time
try:
    from backend.modules.aion.address_book import address_book
except Exception:  # pragma: no cover
    class _AddressBookStub:
        def register_container(self, *a, **k): pass
    address_book = _AddressBookStub()

def _try_link_wormhole(src: str, dst: str) -> None:
    try:
        from backend.modules.dna_chain.container_linker import link_wormhole
    except Exception:  # pragma: no cover
        return
    try:
        link_wormhole(src, dst)
    except Exception:
        pass

def _try_save_in_ucs(cid: str, container: Dict[str, Any]) -> None:
    # lazy import to avoid circulars
    try:
        from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
        ucs_runtime.save_container(cid, container)
    except Exception:
        pass

def _seed_kernel_space(cid: str, size: int) -> None:
    """
    Best-effort: create a small logical grid footprint so UIs don't see an empty hub.
    Non-fatal if DimensionKernel isn't available.
    """
    try:
        from backend.modules.dimensions.dimension_kernel import DimensionKernel
    except Exception:
        return

    try:
        k = DimensionKernel(cid)
        # seed a size*size*size grid at t=0
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    k.register_cube(x, y, z, 0)
        # let UCS save a minimal snapshot if possible
        snap = {
            "id": cid,
            "name": cid,
            "geometry": "Tesseract",
            "symbol": "🧭",
            "glyph_categories": [],
            "nodes": [],
            "links": [],
            "entangled": [],
            "cubes_seeded": True,
            "grid_size": size,
        }
        _try_save_in_ucs(cid, snap)
    except Exception:
        # never fail boot just because of seeding
        pass

def ensure_tesseract_hub(hub_id: str = "tesseract_hq",
                         name: str = "Tesseract HQ",
                         size: int = 8,
                         address_alias: str = "ucs_hub") -> str:
    """
    Idempotently ensures a central Tesseract hub container exists, is registered
    in the address book, saved to UCS, and linked in the wormhole graph.

    Returns the hub_id.
    """
    # minimal, UCS-friendly container document
    container = {
        "id": hub_id,
        "name": name,
        "geometry": "Tesseract",
        "symbol": "🧭",
        "type": "hub",
        "meta": {
            "title": name,
            "address": f"ucs://local/{hub_id}#container",
            "tags": ["hub", "core", "tesseract"],
        },
        "glyph_categories": [],
        "nodes": [],
        "links": [],
        "entangled": [],
    }

    # 1) Address registration (idempotent)
    try:
        address_book.register_container(container)
    except Exception:
        pass

    # 2) Save in UCS (idempotent)
    _try_save_in_ucs(hub_id, container)

    # 3) Seed a logical grid so it isn't "empty" (best-effort, non-fatal)
    _seed_kernel_space(hub_id, size)

    # 4) Wormhole links (best-effort):
    #    - keep backward compat by alias-linking the legacy name to new hub
    #    - and vice-versa so lookups in either direction succeed
    if address_alias and address_alias != hub_id:
        _try_link_wormhole(address_alias, hub_id)
        _try_link_wormhole(hub_id, address_alias)

    return hub_id