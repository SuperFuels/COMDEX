"""
Tessaris • UltraQC v0.4-SLE
VirtualWaveEngine — unified symbolic/photonic execution core.
"""

import time
from backend.codexcore_virtual.virtual_cpu_beam_core import VirtualCPUBeamCore
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.core.entangled_wave import EntangledWave


class VirtualWaveEngine:
    def __init__(self, container_id="default.ultraqc"):
        self.container_id = container_id
        self.cpu = VirtualCPUBeamCore()
        self.entangled_wave = EntangledWave()
        self.last_tick_time = None
        self.running = False

    def load_wave_program(self, instructions):
        self.cpu.load_program(instructions)
        print(f"[VirtualWaveEngine] Loaded symbolic program with {len(instructions)} ops.")

    def run(self):
        self.running = True
        print(f"[UltraQC] Starting unified wave engine for {self.container_id}")

        while self.running and getattr(self.cpu, "running", True):
            tick_start = time.time()
            self.cpu.tick()

            # 🔁 Evolve entangled wave state
            for wave in self.entangled_wave.waves:
                wave.evolve()

            # 🧠 Emit symbolic-photonic event per tick
            evt = BeamEvent(
                event_type="tick",
                source=self.container_id,
                target="symatics_lightwave",
                drift=sum(getattr(w, "drift", 0.0) for w in self.entangled_wave.waves),
                qscore=sum(getattr(w, "qscore", 1.0) for w in self.entangled_wave.waves) / max(len(self.entangled_wave.waves), 1),
                metadata={"tick": self.cpu.ticks}
            )
            beam_event_bus.publish(evt)

            self.last_tick_time = time.time() - tick_start

            # ✅ SQI gating / collapse every N ticks
            if self.cpu.ticks % 5 == 0 and self.entangled_wave.waves:
                result = self.entangled_wave.collapse_all()
                print(f"[UltraQC] Collapse result → {result.get('collapse_metrics', {})}")

            time.sleep(0.05)  # simulate photonic delay

    def attach_wave(self, wave: WaveState):
        self.entangled_wave.add_wave(wave)
        print(f"[VirtualWaveEngine] Attached WaveState {wave.id} to engine.")

    def stop(self):
        self.running = False
        print("[UltraQC] Stopped VirtualWaveEngine.")