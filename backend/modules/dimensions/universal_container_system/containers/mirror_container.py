from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

class MirrorContainer(UCSBaseContainer):
    def __init__(self, runtime):
        super().__init__(name="Mirror Container", geometry="mirror_container", runtime=runtime)
        self.enable_feature("micro_grid")
        self.apply_time_dilation(1.0)

    def reflect_state(self):
        print(f"🪞 {self.name} reflecting current state: {self.state}")
        return {"name": self.name, "geometry": self.geometry, "features": self.features}