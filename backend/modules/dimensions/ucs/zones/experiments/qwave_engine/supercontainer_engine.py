# File: backend/modules/dimensions/ucs/zones/experiments/qwave_engine/supercontainer_engine.py

import math
import time
import json
import os
from typing import Dict, Any, List
import matplotlib.pyplot as plt
from datetime import datetime

from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.field_bridge import FieldBridge

class SupercontainerEngine:
    SAVE_PATH = "data/qwave_engine_state.json"
    LOG_DIR = "data/qwave_logs"

    def __init__(self, container: SymbolicExpansionContainer, safe_mode: bool = False, stage_lock: int = 6, virtual_absorber: bool = True):
        self.container = container
        self.safe_mode = safe_mode
        self.stage_lock = stage_lock
        self.virtual_absorber = virtual_absorber
        self.tick_limit = 500 if safe_mode else None
        self.tick_count = 0

        # ✅ Wave generation stages
        self.current_stage = 0
        self.stages = [
            "proton_injection",        # Particle seed
            "plasma_excitation",       # Energy & spin
            "wave_focus",              # Constriction/field shaping
            "black_hole_compression",  # Compression funnel
            "torus_field_loop",        # Field resonance loop
            "controlled_exhaust"       # Wave emission + exhaust
        ]

        self.fields = {"gravity": 1.0, "magnetism": 1.0, "wave_frequency": 1.0, "field_pressure": 1.0}
        self.particles: List[Dict[str, float]] = []
        self.last_update = time.time()
        self.nested_containers: List[Dict[str, Any]] = []

        # ✅ Logging
        self.resonance_log: List[float] = []
        self.exhaust_log: List[Dict[str, Any]] = []

        # ✅ Physical Field Bridge
        self.field_bridge = FieldBridge(safe_mode=safe_mode)

        if self.safe_mode:
            print("🛡️ Engine initialized in SAFE MODE.")
            self.fields = {k: min(v, 1.0) for k, v in self.fields.items()}
            self.max_particles = 10
            self.tick_delay = 1.0
        else:
            self.max_particles = 500
            self.tick_delay = 0.01

        os.makedirs(self.LOG_DIR, exist_ok=True)

        if os.path.exists(self.SAVE_PATH) and not self.safe_mode:
            print("♻️ Loading saved QWave engine state...")
            self.set_state(self._load_saved_state())
        else:
            self._configure_stage()
            self.container.expand()

    # ---------------------------------------------------------
    # 🔄 Runtime Tick Loop
    # ---------------------------------------------------------
    def tick(self):
        dt = time.time() - self.last_update
        if dt < self.tick_delay:
            return
        self.last_update = time.time()
        self.tick_count += 1

        if self.tick_limit and self.tick_count > self.tick_limit:
            print("🛑 Tick limit reached. Collapsing engine.")
            self.collapse()
            return

        # ✅ Log resonance phase for wave measurement
        phase = math.sin(time.time() * self.fields["wave_frequency"])
        self.resonance_log.append(phase)

        # 🔬 Particle physics
        for p in self.particles:
            gx, gy, gz = self._gravity_force(p)
            mx, my, mz = self._magnetic_force(p)
            wx, wy, wz = self._wave_push(p)

            p["vx"] += (gx + mx + wx) * dt
            p["vy"] += (gy + my + wy) * dt
            p["vz"] += (gz + mz + wz) * dt

            speed = math.sqrt(p["vx"]**2 + p["vy"]**2 + p["vz"]**2)
            p["velocity_delta"] = speed - p.get("last_speed", 0)
            p["last_speed"] = speed

            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["z"] += p["vz"] * dt

            if self.safe_mode and speed > 10:
                print("🚨 Velocity spike detected! Emergency collapse.")
                self.collapse()
                return

        # ✅ Particle injection
        if self.stages[self.current_stage] == "proton_injection" and len(self.particles) < self.max_particles:
            self.inject_proton()

        # ✅ Exhaust logging and physical bridge output
        if self.virtual_absorber and self.current_stage == self.stages.index("controlled_exhaust"):
            self._simulate_virtual_exhaust()

    # ---------------------------------------------------------
    # ⚛ Virtual Exhaust Absorber (with FieldBridge integration)
    # ---------------------------------------------------------
    def _simulate_virtual_exhaust(self):
        impacts = []
        for p in self.particles:
            speed = math.sqrt(p["vx"]**2 + p["vy"]**2 + p["vz"]**2)
            energy = 0.5 * p["mass"] * speed**2
            impacts.append({"speed": round(speed, 3), "energy": round(energy, 3)})
            self.exhaust_log.append({"tick": self.tick_count, "impact_speed": speed, "energy": energy})

            # 🔥 Emit real exhaust wave to coils (auto-calibrated per tick)
            phase = self.resonance_log[-1] if self.resonance_log else 0
            self.field_bridge.emit_exhaust_wave(phase, energy)

            # Optional ADC feedback-based auto-calibration
            adjustment = self.field_bridge.auto_calibrate(target_voltage=1.0)
            if adjustment:
                print(f"🔧 Coil auto-tuned by {adjustment:+.2f} based on feedback.")

            # Reset particle for reuse
            p.update({"x": 0.0, "y": 0.0, "z": 0.0, "vx": 0.0, "vy": 0.0, "vz": 0.0})

        if impacts:
            print(f"📡 Virtual Exhaust Impact: {impacts[-1]}")

    # ---------------------------------------------------------
    # ⚛ Particle Physics
    # ---------------------------------------------------------
    def inject_proton(self):
        self.particles.append({"x": 0.0, "y": 0.0, "z": 0.0, "vx": 0.0, "vy": 0.0, "vz": 0.0, "mass": 1.0, "charge": 1.0})

    def _gravity_force(self, p): return tuple(-self.fields["gravity"] * p["mass"] * self._sign(v) for v in (p["x"], p["y"], p["z"]))
    def _magnetic_force(self, p): 
        swirl = self.fields["magnetism"] * p["charge"]
        return (-swirl * p["vy"], swirl * p["vx"], 0)
    def _wave_push(self, p): return (self.fields["wave_frequency"] * 0.5, 0, 0)
    def _sign(self, v): return -1 if v > 0 else 1

    # ---------------------------------------------------------
    # 🔒 Stage Control
    # ---------------------------------------------------------
    def advance_stage(self):
        if self.stage_lock and self.current_stage >= self.stage_lock - 1:
            print(f"🔒 Stage lock active: cannot advance beyond {self.stages[self.stage_lock-1]}")
            return
        self.current_stage = (self.current_stage + 1) % len(self.stages)
        print(f"🔄 Engine advanced to stage: {self.stages[self.current_stage]}")
        self._configure_stage()
        if not self.safe_mode:
            self.save_state()

    def _configure_stage(self):
        stage = self.stages[self.current_stage]
        if stage == "proton_injection":
            self.fields.update({"gravity": 0.8, "magnetism": 0.5, "wave_frequency": 0.5})
        elif stage == "plasma_excitation":
            self.fields.update({"gravity": 1.0, "magnetism": 1.2, "wave_frequency": 1.0})
        elif stage == "wave_focus":
            self.fields.update({"gravity": 1.2, "magnetism": 1.5, "wave_frequency": 1.5})
        elif stage == "black_hole_compression":
            self.fields.update({"gravity": 1.8, "magnetism": 2.0, "wave_frequency": 2.0})
        elif stage == "torus_field_loop":
            self.fields.update({"gravity": 1.5, "magnetism": 1.8, "wave_frequency": 2.2})
        elif stage == "controlled_exhaust":
            self.fields.update({"gravity": 1.0, "magnetism": 1.0, "wave_frequency": 1.0})
        print(f"⚙ Stage configured: {stage} → {self.fields}")

    # ---------------------------------------------------------
    # 📈 Export Logs & Graphs
    # ---------------------------------------------------------
    def export_logs(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.LOG_DIR, f"qwave_log_{timestamp}.json")
        data = {"resonance_log": self.resonance_log, "exhaust_log": self.exhaust_log, "particles": self.particles}
        with open(log_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"📄 Logs saved: {log_file}")

        vel_deltas = [p.get("velocity_delta", 0) for p in self.particles]
        exhaust_speeds = [e["impact_speed"] for e in self.exhaust_log]

        plt.figure(figsize=(14, 4))
        plt.subplot(1, 3, 1)
        plt.plot(vel_deltas, color="cyan"); plt.title("Velocity Δ")
        plt.subplot(1, 3, 2)
        plt.plot(self.resonance_log, color="yellow"); plt.title("Resonance Phase")
        plt.subplot(1, 3, 3)
        plt.plot(exhaust_speeds if exhaust_speeds else [0], color="red"); plt.title("Exhaust Impact Speed")
        graph_file = os.path.join(self.LOG_DIR, f"qwave_graphs_{timestamp}.png")
        plt.tight_layout(); plt.savefig(graph_file); plt.close()
        print(f"📊 Graphs saved: {graph_file}")

    # ---------------------------------------------------------
    # 📡 State Management
    # ---------------------------------------------------------
    def get_state(self) -> Dict[str, Any]:
        return {
            "stage": self.stages[self.current_stage],
            "fields": self.fields,
            "particle_count": len(self.particles),
            "nested_containers": self.nested_containers,
            "particles": [{k: round(v, 3) if isinstance(v, float) else v for k, v in p.items()} for p in self.particles],
        }

    def set_state(self, state: Dict[str, Any]):
        self.fields = state.get("fields", self.fields)
        stage_name = state.get("stage", self.stages[0])
        if stage_name in self.stages:
            self.current_stage = self.stages.index(stage_name)
        self.nested_containers = state.get("nested_containers", [])
        self.particles = state.get("particles", [])
        self.container.nested = self.nested_containers
        self.container.expand()
        print(f"✅ Engine state restored: {stage_name} ({len(self.particles)} particles)")

    def save_state(self):
        if self.safe_mode:
            return print("🛡️ Safe Mode: Skipping save.")
        os.makedirs(os.path.dirname(self.SAVE_PATH), exist_ok=True)
        with open(self.SAVE_PATH, "w") as f:
            json.dump(self.get_state(), f, indent=2)
        print(f"💾 Engine state saved to {self.SAVE_PATH}")

    def _load_saved_state(self) -> Dict[str, Any]:
        with open(self.SAVE_PATH, "r") as f:
            return json.load(f)

    # ---------------------------------------------------------
    # 🛑 Emergency Collapse
    # ---------------------------------------------------------
    def collapse(self):
        print("⚠️ Emergency Collapse Triggered!")
        self.particles.clear()
        self.fields = {k: 1.0 for k in self.fields}
        self.current_stage = 0
        self._configure_stage()