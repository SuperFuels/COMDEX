from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.dimensions.universal_container_system.portal_manager import PortalManager
from backend.modules.dimensions.universal_container_system.address_book import AddressBook

# ✅ Hub connector (idempotent + safe fallback)
try:
    from backend.modules.dimensions.container_helpers import connect_container_to_hub
except Exception:  # pragma: no cover
    def connect_container_to_hub(*_a, **_k):  # no-op fallback
        pass


class BlackHoleContainer(UCSBaseContainer):
    def __init__(self, runtime, features=None, address_id=None):
        super().__init__("Black Hole Compression Core", "black_hole", runtime, features)
        
        # 📒 Address Book Registration
        # use a stable id; fall back cleanly if UCSBaseContainer didn't set .id
        self.address_id = address_id or f"blackhole-{(getattr(self, 'id', None) or self.name)}"
        AddressBook.register(self.address_id, self)

        # 🌀 Portal/Wormhole Support
        self.portal_manager = PortalManager()
        self.connected_containers = set()

        # --- NEW: register this container with the hub (idempotent, safe) ---
        try:
            doc = {
                "id": getattr(self, "id", None) or self.address_id or self.name,
                "name": self.name,
                "geometry": self.geometry,
                "type": "container",
                "meta": {"address": f"ucs://local/{getattr(self, 'id', None) or self.address_id or self.name}#container"},
            }
            connect_container_to_hub(doc)
        except Exception:
            # keep init resilient
            pass

    def connect_to_container(self, target_container):
        """Create a wormhole link to another container for data routing."""
        if target_container and hasattr(target_container, "id"):
            self.connected_containers.add(target_container.id)
            self.portal_manager.create_portal(self.id, target_container.id)
            print(f"🌀 [Black Hole] Wormhole established → {target_container.name}")

    def pull_from_wormhole(self):
        """Pull data or glyph streams from linked containers."""
        for target_id in list(self.connected_containers):
            data = self.portal_manager.pull_data(target_id)
            if data:
                print(f"📥 [Black Hole] Pulled {len(data)} glyphs from {target_id}")
                self.absorb_glyphs(data)

    def execute_logic(self):
        """Core execution logic for compression and wormhole integration."""
        self.visualize_state("compressing")
        print(f"🪐 [Black Hole] Compressing symbolic glyph density: {self.name}")

        # 🔄 Optional wormhole ingestion before compression
        self.pull_from_wormhole()

        # 🌀 Compression sink
        self.emit_sqi_event("entropy_sink")

        # 🚪 Optional portal closure
        self.portal_manager.close_inactive_portals()