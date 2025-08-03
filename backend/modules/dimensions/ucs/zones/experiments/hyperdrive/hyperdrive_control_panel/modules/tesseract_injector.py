"""
🧩 Hyperdrive Tesseract Injector Module
--------------------------------------
• Defines TesseractInjector for multi-stage compression.
• Supports phased multi-cylinder injectors for Hyperdrive engine.
• Adds safe fallback for null particle handling.
• Auto-fills missing particle fields (x, y, z, mass) to prevent physics errors.
• Integrates CompressionChamber for staged intake → compression → release.
• ✅ Extended: SQI runtime scaling hooks for particle density, decay, and pulse strength.
• ✅ New: Harmonic coherence checks, SQI drift-adaptive density damp, injector-to-chamber auto-link, and telemetry logging.
"""

import os
from datetime import datetime
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer

# ✅ Safe fallback: Define inject_proton locally if module not found
try:
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_particle_module import inject_proton
except ModuleNotFoundError:
    def inject_proton(engine):
        """
        Fallback inject_proton if hyperdrive_particle_module is unavailable.
        Generates a default particle dict and appends to engine.
        """
        particle = {
            "density": 1.0,
            "mass": 1.0,
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "vz": 0.0
        }
        if hasattr(engine, "particles"):
            engine.particles.append(particle)
        return particle

# ✅ Proton injection cycle (fix for ecu_runtime_module import)
def proton_inject_cycle(engine):
    """
    Standalone proton injection cycle to satisfy ecu_runtime_module import.
    Calls inject_proton() and safely appends to engine.particles.
    """
    particle = inject_proton(engine)
    if particle and isinstance(particle, dict):
        engine.particles.append(particle)
        engine.log_event(f"🔬 Proton Inject Cycle: density={particle.get('density', 1.0):.3f}")
    return particle


class TesseractInjector:
    def __init__(self, injector_id, phase_offset, compression_stages=2, base_compression=1.2,
                 particle_density=1.0, particle_decay=0.98, pulse_strength=1.0):
        """
        Initialize a Tesseract Injector for multi-stage particle compression.
        """
        self.id = injector_id
        self.phase_offset = phase_offset
        self.stages = [base_compression * (1 + i * 0.1) for i in range(compression_stages)]
        self.particle_density = particle_density
        self.particle_decay = particle_decay
        self.pulse_strength = pulse_strength
        self.current_frequency = None  # ✅ Track synced frequency

    def tick(self, engine, tick_count):
        """Tick handler: Fires injector if tick aligns with phase offset."""
        if (tick_count + self.phase_offset) % 10 == 0:
            self.multi_compress_and_fire(engine)
        self._apply_decay(engine)

    def multi_compress_and_fire(self, engine):
        """
        Injects a proton, applies staged compression multipliers,
        performs harmonic/SQI checks, and appends result into engine flow.
        """
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonics_module import measure_harmonic_coherence
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger

        particle = inject_proton(engine) or {"density": self.particle_density}
        if not isinstance(particle, dict):
            particle = {"density": self.particle_density}

        # Auto-fill required particle attributes
        particle.setdefault("density", self.particle_density)
        particle.setdefault("mass", 1.0)
        particle.setdefault("x", 0.0)
        particle.setdefault("y", 0.0)
        particle.setdefault("z", 0.0)
        particle.setdefault("vx", 0.0)
        particle.setdefault("vy", 0.0)
        particle.setdefault("vz", 0.0)

        # Apply staged compression
        for stage in self.stages:
            particle["density"] *= stage

        # 🧠 SQI Drift-Adaptive Compression
        drift = max(engine.resonance_filtered[-20:], default=0) - min(engine.resonance_filtered[-20:], default=0)
        if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
            particle["density"] *= 0.95
            print(f"⚠ [Injector {self.id}] Drift high ({drift:.3f}) → Density damp applied.")

        # 🎼 Harmonic Coherence Check & Resync
        coherence = measure_harmonic_coherence(engine)
        if coherence < 0.6:
            print(f"🎼 [Injector {self.id}] Low coherence ({coherence:.3f}) → Auto harmonic resync")
            self.sync_to_frequency(engine.fields.get("wave_frequency", 1.0))

        # Apply pulse strength (velocity impulse)
        particle["vx"] += self.pulse_strength * 0.01
        particle["vy"] += self.pulse_strength * 0.01
        particle["vz"] += self.pulse_strength * 0.005

        # Append particle to engine
        engine.particles.append(particle)
        print(f"🔥 [Tesseract Injector {self.id}] Fired | Density={particle['density']:.3f} | Pulse={self.pulse_strength:.2f}")

        # 🔄 Auto-Link: Injector → Chamber intake
        if hasattr(engine, "chambers") and engine.chambers:
            target_chamber = engine.chambers[self.id % len(engine.chambers)]
            target_chamber.intake(particle)

        # 💾 Telemetry Logging
        TelemetryLogger(log_dir="data/qwave_logs").log({
            "timestamp": datetime.utcnow().isoformat(),
            "tick": engine.tick_count,
            "injector_id": self.id,
            "density": particle["density"],
            "pulse_strength": self.pulse_strength,
            "coherence": coherence,
            "drift": drift
        })

    def _apply_decay(self, engine):
        """Apply density decay to simulate dissipation."""
        for p in engine.particles:
            if isinstance(p, dict) and "density" in p:
                p["density"] *= self.particle_decay

    def sync_to_frequency(self, frequency: float):
        """Sync injector harmonic phase to given frequency."""
        self.current_frequency = frequency
        print(f"🔄 Injector {self.id} synced to frequency {frequency}")

    # 🔧 SQI Runtime Scaling Hooks
    def set_particle_density(self, density: float):
        self.particle_density = max(0.5, min(2.0, density))

    def set_particle_decay(self, decay: float):
        self.particle_decay = max(0.90, min(1.0, decay))

    def set_pulse_strength(self, strength: float):
        self.pulse_strength = max(0.5, min(2.0, strength))


class CompressionChamber:
    def __init__(self, chamber_id, compression_factor=1.2):
        self.id = chamber_id
        self.container = SymbolicExpansionContainer(container_id=f"chamber-{chamber_id}")
        self.compression_factor = compression_factor
        self.load = []
        self.current_frequency = None

    def intake(self, particle):
        if particle:
            self.load.append(particle)

    def compress_and_release(self):
        if not self.load:
            return None
        particle = self.load.pop(0)
        if not isinstance(particle, dict):
            particle = {"density": 1.0, "mass": 1.0, "x": 0.0, "y": 0.0, "z": 0.0, "vx": 0.0, "vy": 0.0, "vz": 0.0}

        particle.setdefault("density", 1.0)
        particle.setdefault("mass", 1.0)
        particle["density"] *= self.compression_factor
        print(f"🎯 [CompressionChamber {self.id}] Released particle | Density={particle['density']:.3f}")
        return particle

    def adjust_harmonic(self, frequency: float):
        self.current_frequency = frequency
        print(f"🎵 CompressionChamber {self.id} adjusted to harmonic frequency {frequency}")