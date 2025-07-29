from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

class FractalCrystal(UCSBaseContainer):
    def __init__(self, runtime):
        super().__init__(name="Fractal Crystal", geometry="fractal_crystal", runtime=runtime)
        self.enable_feature("micro_grid")
        self.apply_time_dilation(0.8)  # slower deep zoom cycles

    def infinite_zoom(self, depth=3):
        print(f"🧊 Infinite fractal zoom in {self.name}, depth: {depth}")
        for i in range(depth):
            self.emit_sqi_event(f"zoom_level_{i}")