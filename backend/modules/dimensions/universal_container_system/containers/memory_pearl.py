from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

# ✅ Hub connector (idempotent)
try:
    from backend.modules.dimensions.container_helpers import connect_container_to_hub
except Exception:  # pragma: no cover
    def connect_container_to_hub(*_a, **_k):  # safe no-op fallback
        pass

# ✅ Optional directory + wormhole link (safe fallbacks)
try:
    from backend.modules.aion.address_book import address_book
except Exception:  # pragma: no cover
    class _NullAB:
        def register_container(self, *_a, **_k): pass
    address_book = _NullAB()

try:
    from backend.modules.dna_chain.container_linker import link_wormhole
except Exception:  # pragma: no cover
    def link_wormhole(*_a, **_k): pass


class MemoryPearl(UCSBaseContainer):
    def __init__(self, runtime):
        super().__init__(name="Memory Pearl", geometry="memory_pearl", runtime=runtime)
        self.disable_feature("gravity")  # memory nodes are free-floating
        self.apply_time_dilation(1.0)

        # --- NEW: Register + connect to hub (idempotent, safe) ---
        try:
            doc = {
                "id": getattr(self, "id", None) or self.name,
                "name": self.name,
                "geometry": self.geometry,
                "type": "container",
                "meta": {"address": f"ucs://local/{getattr(self, 'id', None) or self.name}#container"},
            }
            # 1) Hub connect (no-op if already connected)
            connect_container_to_hub(doc)

            # 2) Optional: Address directory + default wormhole link
            try:
                address_book.register_container(doc)
            finally:
                link_wormhole(doc["id"], "ucs_hub")
        except Exception:
            # keep init resilient
            pass

    def chain_memory(self, pearls):
        print(f"🧿 Linking {len(pearls)} memory pearls in {self.name}")
        self.glyph_storage.extend(pearls)
        self.emit_sqi_event("memory_chain_linked")