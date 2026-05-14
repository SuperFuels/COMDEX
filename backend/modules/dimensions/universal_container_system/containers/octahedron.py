from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

# ✅ Hub connector (safe fallback if unavailable)
try:
    from backend.modules.dimensions.container_helpers import connect_container_to_hub
except Exception:  # pragma: no cover
    def connect_container_to_hub(*_a, **_k):  # no-op fallback
        pass

# ✅ Optional address directory + wormhole link (safe fallbacks)
try:
    from backend.modules.aion.address_book import address_book
except Exception:  # pragma: no cover
    class _NullAddressBook:
        def register_container(self, *_a, **_k): pass
    address_book = _NullAddressBook()

try:
    from backend.modules.dna_chain.container_linker import link_wormhole
except Exception:  # pragma: no cover
    def link_wormhole(*_a, **_k): pass


class OctahedronContainer(UCSBaseContainer):
    def __init__(self, runtime, features=None):
        super().__init__("Octahedron Duality Bridge", "octahedron", runtime, features)

        # --- NEW: Register + connect to hub + link directory ---
        try:
            doc = {
                "id": getattr(self, "id", None) or self.name,
                "name": self.name,
                "geometry": self.geometry,
                "type": "container",
                "meta": {"address": f"ucs://local/{getattr(self, 'id', None) or self.name}#container"},
            }
            # 1) Connect to hub (safe idempotent)
            connect_container_to_hub(doc)

            # 2) Register in address directory
            try:
                address_book.register_container(doc)
            finally:
                # 3) Link to wormhole network
                link_wormhole(doc["id"], "ucs_hub")
        except Exception:
            # silent fail to keep init resilient
            pass

    def execute_logic(self):
        self.visualize_state("active")
        print(f"🟣 [Octahedron] Resolving duality/paradox for: {self.name}")
        self.emit_sqi_event("duality_merge")