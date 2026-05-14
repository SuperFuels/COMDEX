# backend/modules/dimensions/container_helpers.py
import os

try:
    from backend.modules.aion.address_book import address_book
except Exception:
    class _ABStub:
        def register_container(self, *a, **k): pass
        def get_all(self): return []
    address_book = _ABStub()

try:
    from backend.modules.dna_chain.container_linker import link_wormhole
except Exception:
    def link_wormhole(*a, **k): return False


def _find_hub_id_fallback(default_id: str = "tesseract_hub") -> str:
    # 1) ENV override
    env_id = os.getenv("MULTIVERSE_HQ_ID")
    if env_id:
        return env_id

    # 2) Address book lookup by meta.role/kind/geometry
    try:
        for c in address_book.get_all():
            meta = c.get("meta") or {}
            if meta.get("role") == "hub" or meta.get("kind") == "tesseract" or c.get("geometry") == "Tesseract":
                return c.get("id") or c.get("name")
    except Exception:
        pass

    # 3) Default
    return default_id


def connect_container_to_hub(container_doc: dict, hub_id: str | None = None) -> None:
    """
    Idempotently:
      - registers container in address book
      - links container to hub via wormhole
    """
    if not container_doc:
        return
    cid = container_doc.get("id") or container_doc.get("name")
    if not cid:
        return

    # Register
    try:
        address_book.register_container(container_doc)
    except Exception:
        pass

    # Link
    hub = hub_id or _find_hub_id_fallback()
    try:
        link_wormhole(cid, hub)
    except Exception:
        pass