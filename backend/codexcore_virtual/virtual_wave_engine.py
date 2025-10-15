"""
Tessaris • QQC v0.5 — Symatics Lightwave Engine
VirtualWaveEngine — unified symbolic/photonic execution core
with Symatics amplitude/phase/frequency modulation hooks.
"""

import time
import math
import random
import logging
from backend.codexcore_virtual.virtual_cpu_beam_core import VirtualCPUBeamCore
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.core.entangled_wave import EntangledWave

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Symbolic → Photonic modulation map
# ──────────────────────────────────────────────
OPCODE_PHOTONICS = {
    "⊕": {"phase_shift": 0.25 * math.pi, "amp_mod": 1.0, "freq_mul": 1.0},   # superposition
    "↔": {"phase_shift": 0.5 * math.pi,  "amp_mod": 0.95, "freq_mul": 0.9},   # entanglement
    "μ": {"phase_shift": 0.0,            "amp_mod": 0.85, "freq_mul": 0.7},   # measurement
    "⟲": {"phase_shift": 1.0 * math.pi,  "amp_mod": 1.1,  "freq_mul": 1.2},   # resonance
    "π": {"phase_shift": 0.75 * math.pi, "amp_mod": 0.9,  "freq_mul": 1.0},   # projection
}


class VirtualWaveEngine:
    def __init__(self, container_id="default.qqc"):
        self.container_id = container_id
        self.cpu = VirtualCPUBeamCore()
        self.entangled_wave = EntangledWave()
        self.last_tick_time = None
        self.running = False
        self.tick_counter = 0

    # ──────────────────────────────────────────────
    # Load symbolic program
    # ──────────────────────────────────────────────
    def load_wave_program(self, instructions):
        self.cpu.load_program(instructions)
        print(f"[VirtualWaveEngine] Loaded symbolic program with {len(instructions)} ops.")

    # ──────────────────────────────────────────────
    # Symatics modulation — adjust amp/phase/freq
    # ──────────────────────────────────────────────
    def _apply_symatics_modulation(self, wave: WaveState, opcode: str):
        """Applies symbolic→photonic modulation based on Symatics operator."""
        if opcode not in OPCODE_PHOTONICS:
            return

        mod = OPCODE_PHOTONICS[opcode]
        old_phase = wave.phase

        # Apply modulations
        wave.phase = (wave.phase + mod["phase_shift"] + random.uniform(-0.05, 0.05)) % (2 * math.pi)
        wave.amplitude *= mod["amp_mod"]
        wave.frequency *= mod["freq_mul"]

        # Gradual coherence decay simulation
        wave.coherence = max(0.7, min(1.0, wave.coherence - random.uniform(0.0, 0.02)))

        # Metadata update
        wave.metadata.update({
            "last_opcode": opcode,
            "phase_shift": round(mod["phase_shift"], 3),
            "amp_mod": mod["amp_mod"],
            "freq_mul": mod["freq_mul"],
            "tick": self.tick_counter
        })

        logger.info(
            f"[SymaticsHook] {opcode} modulated → "
            f"phase {old_phase:.3f}→{wave.phase:.3f}, "
            f"amp={wave.amplitude:.2f}, freq={wave.frequency:.2f}, "
            f"coh={wave.coherence:.3f}"
        )

    # ──────────────────────────────────────────────
    # Main runtime loop
    # ──────────────────────────────────────────────
    def run(self):
        """Main execution loop for symbolic–photonic integration."""
        self.running = True
        print(f"[QQC] Starting Symatics Lightwave Engine for {self.container_id}")

        while self.running and getattr(self.cpu, "running", True):
            tick_start = time.time()

            # Step CPU (symbolic layer)
            self.cpu.tick()
            opcode = getattr(self.cpu, "current_opcode", "⊕")  # fallback
            self.tick_counter += 1

            # Apply Symatics modulation + evolve waves
            for wave in self.entangled_wave.waves:
                self._apply_symatics_modulation(wave, opcode)
                wave.evolve()

            # Emit BeamEvent
            evt = BeamEvent(
                event_type="tick",
                source=self.container_id,
                target="symatics_lightwave",
                drift=sum(getattr(w, "drift", 0.0) for w in self.entangled_wave.waves),
                qscore=sum(getattr(w, "coherence", 1.0) for w in self.entangled_wave.waves)
                / max(len(self.entangled_wave.waves), 1),
                metadata={"tick": self.tick_counter, "opcode": opcode}
            )
            beam_event_bus.publish(evt)

            # Collapse event (SQI gating)
            if self.tick_counter % 5 == 0 and self.entangled_wave.waves:
                result = self.entangled_wave.collapse_all()
                print(f"[QQC] Collapse metrics → {result.get('collapse_metrics', {})}")

            # Tick timing
            self.last_tick_time = time.time() - tick_start
            time.sleep(0.05)  # simulate photonic latency

    # ──────────────────────────────────────────────
    # Wave management
    # ──────────────────────────────────────────────
    def attach_wave(self, wave: WaveState):
        self.entangled_wave.add_wave(wave)
        print(f"[VirtualWaveEngine] Attached WaveState {wave.id} to engine.")

    def stop(self):
        self.running = False
        print("[QQC] Stopped VirtualWaveEngine.")