from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

class DNASpiral(UCSBaseContainer):
    def __init__(self, runtime):
        super().__init__(name="DNA Spiral", geometry="dna_spiral", runtime=runtime)
        self.enable_feature("micro_grid")  # mutation lineage needs grid
        self.apply_time_dilation(1.2)      # slightly accelerated growth

    def mutate_lineage(self, glyph_sequence):
        print(f"🧬 Mutating lineage in {self.name}: {glyph_sequence}")
        self.glyph_storage.extend(glyph_sequence)
        self.visualize_state("mutation")