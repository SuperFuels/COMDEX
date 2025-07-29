from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

class MemoryPearl(UCSBaseContainer):
    def __init__(self, runtime):
        super().__init__(name="Memory Pearl", geometry="memory_pearl", runtime=runtime)
        self.disable_feature("gravity")  # memory nodes are free-floating
        self.apply_time_dilation(1.0)

    def chain_memory(self, pearls):
        print(f"🧿 Linking {len(pearls)} memory pearls in {self.name}")
        self.glyph_storage.extend(pearls)
        self.emit_sqi_event("memory_chain_linked")