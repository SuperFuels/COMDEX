"""
Container Expander: Initializes and grows .dc containers
Uses DimensionKernel to seed runtime cube space and prepare for Avatar spawn
"""

from .dimension_kernel import DimensionKernel

class ContainerExpander:
    def __init__(self, container_id):
        self.kernel = DimensionKernel(container_id)

    def seed_initial_space(self, size=3):
        """
        Seeds a 3x3x3 base space in (x,y,z) with t=0.
        """
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    self.kernel.register_cube(x, y, z, 0)
        return f"Seeded initial {size}x{size}x{size} runtime space."

    def grow_space(self, direction="z", layers=1):
        return self.kernel.expand(axis=direction, amount=layers)

    def inject_glyph(self, x, y, z, t, glyph):
        self.kernel.add_glyph(x, y, z, t, glyph)

    def status(self):
        return self.kernel.dump_snapshot()
