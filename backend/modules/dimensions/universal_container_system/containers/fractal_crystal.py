from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.dimensions.universal_container_system.portal_manager import PortalManager
from backend.modules.dimensions.universal_container_system.address_book import AddressBook

class FractalCrystal(UCSBaseContainer):
    def __init__(self, runtime, features=None, address_id=None):
        super().__init__(name="Fractal Crystal", geometry="fractal_crystal", runtime=runtime, features=features)

        # Enable original features
        self.enable_feature("micro_grid")
        self.apply_time_dilation(0.8)  # slower deep zoom cycles

        # 📒 Address Book Registration
        self.address_id = address_id or f"fractal-{self.id}"
        AddressBook.register(self.address_id, self)

        # 🌀 Portal/Wormhole Support
        self.portal_manager = PortalManager()
        self.connected_containers = set()

    def connect_to_container(self, target_container):
        """Create a wormhole link to another container for data routing."""
        if target_container and hasattr(target_container, "id"):
            self.connected_containers.add(target_container.id)
            self.portal_manager.create_portal(self.id, target_container.id)
            print(f"🌀 [Fractal Crystal] Wormhole established -> {target_container.name}")

    def pull_from_wormhole(self):
        """Pull data or glyph streams from linked containers."""
        for target_id in list(self.connected_containers):
            data = self.portal_manager.pull_data(target_id)
            if data:
                print(f"📥 [Fractal Crystal] Pulled {len(data)} glyphs from {target_id}")
                self.absorb_glyphs(data)

    def infinite_zoom(self, depth=3):
        """Original infinite zoom logic with SQI event emission."""
        print(f"🧊 Infinite fractal zoom in {self.name}, depth: {depth}")
        for i in range(depth):
            self.emit_sqi_event(f"zoom_level_{i}")

    def execute_logic(self):
        """Core execution logic integrating wormhole data and infinite zoom."""
        self.visualize_state("zooming")

        # 🔄 Optional wormhole ingestion before zoom
        self.pull_from_wormhole()

        # 🧊 Perform infinite zoom
        self.infinite_zoom(depth=3)

        # 🚪 Optional portal cleanup
        self.portal_manager.close_inactive_portals()