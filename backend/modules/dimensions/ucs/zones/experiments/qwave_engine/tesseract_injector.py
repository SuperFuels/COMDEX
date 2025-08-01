"""-------------------------
🧩 Tesseract Injector Module
----------------------------
• Defines TesseractInjector for multi-stage compression.
• Supports phased multi-cylinder injectors for QWave engine.
• Adds safe fallback for null particle handling.
• Auto-fills missing particle fields (x, y, z, mass) to prevent physics errors.
• Integrates CompressionChamber for staged intake → compression → release.
• Used by QWave Control Panel for SQI resonance tuning and density amplification.
"""

from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer

class TesseractInjector:
    def __init__(self, injector_id, phase_offset, compression_stages=2, base_compression=1.2):
        """
        Initialize a Tesseract Injector for multi-stage particle compression.
        :param injector_id: Unique injector identifier.
        :param phase_offset: Timing offset for phased firing.
        :param compression_stages: Number of compression multipliers applied.
        :param base_compression: Initial density multiplier.
        """
        self.id = injector_id
        self.phase_offset = phase_offset
        self.stages = [base_compression * (1 + i * 0.1) for i in range(compression_stages)]

    def tick(self, engine, tick_count):
        """
        Tick handler: Fires injector if tick aligns with phase offset.
        """
        if (tick_count + self.phase_offset) % 10 == 0:
            self.multi_compress_and_fire(engine)

    def multi_compress_and_fire(self, engine):
        """
        Injects a proton, applies staged compression multipliers,
        and appends the result safely into engine particle flow.
        Ensures fallback particle creation if inject_proton() returns None.
        Auto-fills required fields to prevent gravity force errors.
        """
        particle = engine.inject_proton() or {"density": 1.0}  # ✅ Safe fallback
        if not isinstance(particle, dict):
            particle = {"density": 1.0}

        # ✅ Auto-fill required particle attributes for physics stability
        particle.setdefault("density", 1.0)
        particle.setdefault("mass", 1.0)
        particle.setdefault("x", 0.0)
        particle.setdefault("y", 0.0)
        particle.setdefault("z", 0.0)

        # Apply compression stages
        for stage in self.stages:
            particle["density"] *= stage

        engine.particles.append(particle)
        print(f"🔥 [Tesseract Injector {self.id}] Fired particle | Density={particle['density']:.3f}")


class CompressionChamber:
    def __init__(self, chamber_id, compression_factor=1.2):
        """
        Compression chamber that intakes particles, applies a single-stage compression,
        and outputs compressed particles back to the engine.
        """
        self.id = chamber_id
        self.container = SymbolicExpansionContainer(container_id=f"chamber-{chamber_id}")
        self.compression_factor = compression_factor
        self.load = []

    def intake(self, particle):
        """
        Intake particle into the chamber for staged compression.
        """
        if particle:  # ✅ Ignore None safely
            self.load.append(particle)

    def compress_and_release(self):
        """
        Compress and release one particle from the chamber.
        Returns None if no particles are available.
        """
        if not self.load:
            return None
        particle = self.load.pop(0)

        # ✅ Ensure particle dict validity and density field
        if not isinstance(particle, dict):
            particle = {"density": 1.0, "mass": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}
        particle.setdefault("density", 1.0)
        particle.setdefault("mass", 1.0)
        particle.setdefault("x", 0.0)
        particle.setdefault("y", 0.0)
        particle.setdefault("z", 0.0)

        # Apply compression
        particle["density"] *= self.compression_factor
        return particle