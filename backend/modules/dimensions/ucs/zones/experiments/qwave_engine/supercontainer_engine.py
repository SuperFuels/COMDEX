import math
import time
import random
import json
import os
from typing import Dict, Any, List
from copy import deepcopy
import matplotlib.pyplot as plt
from datetime import datetime

from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.field_bridge import FieldBridge
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.tesseract_injector import TesseractInjector, CompressionChamber
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.qwave_tuning import QWaveTuning

# -------------------------
# ✅ Safe Tuning Serializer
# -------------------------
def safe_qwave_tuning():
    """Return only serializable attributes from QWaveTuning."""
    serializable = {}
    for k, v in vars(QWaveTuning).items():
        if not k.startswith("__") and isinstance(v, (int, float, bool, str, list, dict)):
            serializable[k] = v
    return serializable

# -------------------------
# 🧠 SQI REASONING ENGINE (UPDATED WITH TOGGLE + STAGE AWARENESS)
# -------------------------
class SQIReasoningEngine:
    def __init__(self, target_resonance_drift: float = 0.5, target_exhaust_speed: float = 250.0, enabled: bool = True):
        self.target_resonance_drift = target_resonance_drift
        self.target_exhaust_speed = target_exhaust_speed
        self.enabled = enabled  # 🔑 Master toggle for SQI
        self.last_drift = None
        self.last_exhaust = None

    def analyze_trace(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            print("🛑 [SQI] Disabled: Skipping analysis.")
            return {"drift": 0.0, "drift_trend": "-", "avg_exhaust": 0.0, "fields": trace.get("fields", {})}

        resonance = trace.get("resonance", [])
        fields = trace.get("fields", {})
        exhaust = trace.get("exhaust", [])
        stage = trace.get("stage", None)  # ✅ Stage-aware hook

        drift = (max(resonance) - min(resonance)) if resonance else 0.0
        avg_exhaust = sum(exhaust) / len(exhaust) if exhaust else 0.0
        drift_trend = None

        if self.last_drift is not None:
            drift_trend = "↑" if drift > self.last_drift else "↓" if drift < self.last_drift else "->"

        print(f"🧠 [SQI] Stage={stage or 'N/A'} | Drift={drift:.3f} ({drift_trend or '-'}) | Exhaust={avg_exhaust:.2f}")

        self.last_drift = drift
        self.last_exhaust = avg_exhaust
        return {"drift": drift, "drift_trend": drift_trend, "avg_exhaust": avg_exhaust, "fields": fields, "stage": stage}

    def recommend_adjustments(self, analysis: Dict[str, Any]) -> Dict[str, float]:
        if not self.enabled:
            print("🛑 [SQI] Disabled: No adjustments applied.")
            return {}

        drift, drift_trend, avg_exhaust, fields = (
            analysis["drift"],
            analysis["drift_trend"],
            analysis["avg_exhaust"],
            analysis["fields"]
        )
        stage = analysis.get("stage")

        adjustments = {}
        stage_baseline_freq = QWaveTuning.STAGE_CONFIGS.get(stage, {}).get("wave_frequency", fields.get("wave_frequency", 1.0))

        # ✅ Resonance Drift Control (dead zone + per-stage clamp)
        if drift > self.target_resonance_drift:
            if drift > (self.target_resonance_drift * 2):  # Major drift
                factor = 0.97 if drift_trend == "↑" else 0.99
                new_freq = max(stage_baseline_freq * 0.8, fields["wave_frequency"] * factor)
                adjustments["wave_frequency"] = new_freq
                adjustments["magnetism"] = fields["magnetism"] * factor
                print(f"⚠️ SQI: Heavy drift detected (Stage={stage}) -> Freq={new_freq:.3f}")
            elif drift_trend == "↑":
                print(f"⚠️ SQI: Minor drift rising (Stage={stage}) -> Holding (dead zone).")

        # ✅ Exhaust Balancing
        if avg_exhaust < self.target_exhaust_speed:
            adjustments["gravity"] = fields["gravity"] * 1.02
        elif avg_exhaust > self.target_exhaust_speed * 1.2:
            adjustments["gravity"] = fields["gravity"] * 0.97

        print(f"🔮 [SQI] Recommended Adjustments: {adjustments if adjustments else 'None'}")
        return adjustments

# -------------------------
# ✅ DCContainerIO (.dc export/import)
# -------------------------
class DCContainerIO:
    @staticmethod
    def export(dc_data: Dict[str, Any], path: str, stage: str = None, sqi_enabled: bool = False):
        """Export .dc container for entangled glyph replay + GHXVisualizer."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Ensure timestamp
        if "timestamp" not in dc_data:
            dc_data["timestamp"] = datetime.utcnow().isoformat()

        # Inject metadata (engine + SQI state + stage context)
        dc_data["metadata"] = {
            "engine": "QWave",
            "stage": stage or "unknown",
            "sqi_enabled": sqi_enabled,
            "entangled_glyphs": len(dc_data.get("glyphs", [])),
            "timestamp": dc_data["timestamp"]
        }

        with open(path, "w") as f:
            json.dump(dc_data, f, indent=2)
        print(f"📦 Exported .dc container -> {path} | Stage={stage or 'N/A'} | SQI={sqi_enabled}")

    @staticmethod
    def import_dc(path: str) -> Dict[str, Any]:
        """Load .dc container back into engine or replay visualizer."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌ DC file not found: {path}")
        with open(path, "r") as f:
            data = json.load(f)

        # ✅ Auto-inject defaults if missing
        data.setdefault("glyphs", [])
        data.setdefault("metadata", {
            "engine": "QWave",
            "stage": "unknown",
            "sqi_enabled": False,
            "entangled_glyphs": len(data.get("glyphs", [])),
            "timestamp": datetime.utcnow().isoformat()
        })

        print(f"📥 Imported .dc container from {path} | Stage={data['metadata'].get('stage')} | SQI={data['metadata'].get('sqi_enabled')}")
        return data

# -------------------------
# 🔥 SUPERCONTAINER ENGINE (ENHANCED)
# -------------------------
class SupercontainerEngine:
    SAVE_PATH = "data/qwave_engine_state.json"
    LOG_DIR = "data/qwave_logs"

    def __init__(self, container: SymbolicExpansionContainer, safe_mode: bool = False,
                 stage_lock: int = 6, virtual_absorber: bool = True, sqi_enabled: bool = False):
        self.container = container
        self.safe_mode = safe_mode
        self.stage_lock = stage_lock
        self.virtual_absorber = virtual_absorber
        self.tick_limit = 1000 if safe_mode else 20000
        self.tick_count = 0

        # 🔧 SQI State
        self.sqi_enabled = sqi_enabled
        self.pending_sqi_ticks = None
        self.last_sqi_adjustments: Dict[str, float] = {}

        # 🔑 Stage Management
        self.stages = list(QWaveTuning.STAGE_CONFIGS.keys())
        self.current_stage = self.stages.index("wave_focus")

        # ⚙ Core Fields
        self.fields = {"gravity": 1.0, "magnetism": 1.0, "wave_frequency": 1.0, "field_pressure": 1.0}
        self.particles: List[Dict[str, float]] = []
        self.last_update = time.time()
        self.nested_containers: List[Dict[str, Any]] = []

        # 📊 Logs
        self.resonance_log: List[float] = []
        self.resonance_filtered: List[float] = []
        self.graph_log: List[Dict[str, Any]] = []
        self.resonance_phase = 0.0
        self.exhaust_log: List[Dict[str, Any]] = []

        # ⚛ Dynamics
        self.damping_factor = QWaveTuning.DAMPING_FACTOR
        self.decay_rate = QWaveTuning.DECAY_RATE

        # 🏆 Best-state tracking
        self.best_score: float = None
        self.best_fields: Dict[str, float] = {}
        self.best_particles: List[Dict[str, Any]] = []

        # 🔌 Subsystems
        self.injectors = [TesseractInjector(i, phase_offset=i * 3) for i in range(4)]
        self.chambers = [CompressionChamber(i, compression_factor=1.3) for i in range(4)]
        self.field_bridge = FieldBridge(safe_mode=safe_mode)
        self.collapse_enabled = QWaveTuning.ENABLE_COLLAPSE
        self.sqi_engine = SQIReasoningEngine()
        self.last_dc_trace = None

        # 🎯 Stability thresholds
        self.stage_stability_window = 50
        self.stability_threshold = QWaveTuning.RESONANCE_DRIFT_THRESHOLD / 2

        # 🛡 Safe Mode Config
        if self.safe_mode:
            print("🛡️ Engine initialized in SAFE MODE.")
            self.fields = {k: min(v, 1.0) for k, v in self.fields.items()}
            self.max_particles = 300
            self.tick_delay = 0.03
            self.safe_mode_avatar = {"level": get_soul_law_validator().MIN_AVATAR_LEVEL}
        else:
            self.max_particles = 800
            self.tick_delay = 0.005
            self.safe_mode_avatar = {"level": get_soul_law_validator().MIN_AVATAR_LEVEL}

        os.makedirs(self.LOG_DIR, exist_ok=True)

        # 🔁 Load Best State or Saved Engine
        self._load_best_state()
        if os.path.exists(self.SAVE_PATH) and not self.safe_mode:
            print("♻️ Loading saved QWave engine state...")
            self.set_state(self._load_saved_state())
        else:
            self._configure_stage()
            self.safe_mode_avatar = {"level": 10}
            self.container.expand(avatar_state=self.safe_mode_avatar)

    def _load_best_state(self):
        """Load best-known engine state if available, else use defaults."""
        best_state_path = "data/qwave_best_state.json"
        if os.path.exists(best_state_path):
            try:
                with open(best_state_path, "r") as f:
                    state = json.load(f)
                self.fields.update(state.get("fields", {}))
                self.best_score = state.get("score", None)
                self.best_fields = state.get("fields", {}).copy()
                self.best_particles = state.get("particles", [])
                print(f"🔁 Loaded best state: score={self.best_score} ({len(self.best_particles)} particles)")
            except Exception as e:
                print(f"⚠ Failed to load best state: {e}")
        else:
            print("⚠ No best state file found. Using baseline fields.")

# -------------------------
# 🔥 TICK
# -------------------------

    def tick(self):
        dt = time.time() - self.last_update
        if dt < self.tick_delay:
            return
        self.last_update = time.time()
        self.tick_count += 1

        # 🧬 Auto-reseed particles
        if len(self.particles) < 200:
            print(f"⚠ Low particle count ({len(self.particles)}). Injecting 50 baseline protons.")
            for _ in range(50):
                self.inject_proton()

        # 🔒 Tick limit safeguard
        if self.tick_limit and self.tick_count >= self.tick_limit:
            print("🛑 Tick limit reached. Auto-collapsing engine.")
            self.collapse()
            return

        # ⚠ Instability detection
        if self._check_instability():
            return

        # 🎯 Resonance progression
        feedback_voltage = self.field_bridge.get_feedback_voltage() or 0.0
        self.resonance_phase = (
            self.resonance_phase +
            (self.fields["wave_frequency"] - feedback_voltage * self.damping_factor) * dt
        ) * self.decay_rate
        self.resonance_log.append(self.resonance_phase)
        self.resonance_filtered.append(
            sum(self.resonance_log[-10:]) / min(len(self.resonance_log), 10)
        )

        # 📊 Debug drift
        drift = max(self.resonance_filtered[-20:], default=0) - min(self.resonance_filtered[-20:], default=0)
        print(f"📊 Tick={self.tick_count} | Resonance={self.resonance_phase:.4f} | Drift={drift:.4f} | Particles={len(self.particles)}")

        # 🔬 Particle physics update
        MAX_VELOCITY = 1e3  # ✅ Clamp to prevent overflow
        DAMPENING = 0.95    # ✅ Exponential dampening factor

        for p in self.particles:
            if not isinstance(p, dict):
                continue
            p.setdefault("charge", 1.0)
            p.setdefault("density", 1.0)
            p.setdefault("vx", 0.0); p.setdefault("vy", 0.0); p.setdefault("vz", 0.0)
            p.setdefault("x", 0.0); p.setdefault("y", 0.0); p.setdefault("z", 0.0)
            p.setdefault("mass", 1.0)

            # ⚡ Force updates
            gx, gy, gz = self._gravity_force(p)
            mx, my, mz = self._magnetic_force(p)
            wx, wy, wz = self._wave_push(p)

            p["vx"] += (gx + mx + wx) * dt
            p["vy"] += (gy + my + wy) * dt
            p["vz"] += (gz + mz + wz) * dt

            # ✅ Apply dampening to control runaway acceleration
            p["vx"] *= DAMPENING
            p["vy"] *= DAMPENING
            p["vz"] *= DAMPENING

            # ✅ Clamp velocities to avoid overflow
            p["vx"] = max(min(p["vx"], MAX_VELOCITY), -MAX_VELOCITY)
            p["vy"] = max(min(p["vy"], MAX_VELOCITY), -MAX_VELOCITY)
            p["vz"] = max(min(p["vz"], MAX_VELOCITY), -MAX_VELOCITY)

            # ✅ Safe speed calculation
            try:
                speed = math.sqrt(p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2)
            except OverflowError:
                speed = MAX_VELOCITY  # fallback if still unstable

            p["velocity_delta"] = speed - p.get("last_speed", 0)
            p["last_speed"] = speed

            # 🛰 Position update
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["z"] += p["vz"] * dt

        # 🫀 Pulse detection
        if len(self.resonance_filtered) >= 30 and self.tick_count > 200:
            drift = max(self.resonance_filtered[-30:]) - min(self.resonance_filtered[-30:])
            if drift <= self.stability_threshold:
                if not self.sqi_enabled:
                    print(f"🫀 Pulse detected (delayed): drift={drift:.3f}, enabling SQI...")
                    self.sqi_enabled = True
                    self.pending_sqi_ticks = 20
                else:
                    print(f"🫀 Pulse stable: SQI already active (drift={drift:.3f})")

                # ✅ Detect SQI lock (drift stabilized)
                if drift <= 0.05 and not getattr(self, "sqi_locked", False):
                    print(f"🔒 SQI LOCKED: Resonance={self.resonance_phase:.4f} | Drift={drift:.4f}")
                    self.sqi_locked = True

                    # 💾 Auto-save SQI idle state
                    if hasattr(self, "save_idle_state"):
                        self.save_idle_state(self)
                        print(f"💾 SQI idle state saved at drift={drift:.4f}")

        # 🔧 Inline SQI correction
        if self.sqi_enabled and self.pending_sqi_ticks is not None:
            self.pending_sqi_ticks -= 1
            if self.pending_sqi_ticks <= 0:
                trace = {
                    "resonance": self.resonance_filtered[-30:],
                    "fields": self.fields.copy(),
                    "exhaust": [e.get("impact_speed", 0) for e in self.exhaust_log[-20:]],
                    "stage": self.stages[self.current_stage],
                }
                analysis = self.sqi_engine.analyze_trace(trace)
                adjustments = self.sqi_engine.recommend_adjustments(analysis)
                if adjustments:
                    self.fields.update(adjustments)
                    print(f"🔧 [SQI-inline] Micro-adjust applied: {adjustments}")
                self.pending_sqi_ticks = 50

        # 🔄 Stage advancement
        if self._check_stage_stability():
            prev_stage = self.stages[self.current_stage]

            # ✅ Prevent advancing if already at final stage
            if self.current_stage == len(self.stages) - 1:
                print("🔒 SQI micro-tune: Already at final stage, skipping stage advance.")
            else:
                self.advance_stage()

            new_stage = self.stages[self.current_stage]

            if new_stage == prev_stage:
                print(f"⚠ Stage advance skipped: Already at final stage.")
                print(f"⏳ Skipping snapshot export: Stage unchanged ({new_stage})")
            else:
                print(f"🚀 Stage advanced: {prev_stage} ➝ {new_stage}")
                self._resync_harmonics()

                # 📦 Auto-export .dc snapshot (only if stage actually changed)
                self.last_dc_trace = f"data/qwave_logs/{new_stage}_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dc.json"
                DCContainerIO.export(
                    {
                        "fields": deepcopy(self.fields),
                        "glyphs": [],
                        "timestamp": datetime.utcnow().isoformat(),
                        "stage": new_stage,
                        "particles": len(self.particles),
                        "score": self.best_score if self.best_score else 0.0,
                        "sqi_enabled": self.sqi_enabled
                    },
                    self.last_dc_trace,
                    stage=new_stage,
                    sqi_enabled=self.sqi_enabled
                )
                print(f"📦 Exported .dc container -> {self.last_dc_trace} | Stage={new_stage} | SQI={self.sqi_enabled}")

                if self.sqi_enabled:
                    print("🎯 SQI: Running micro-tune after stage advance.")
                    self.pending_sqi_ticks = 5

    def _gravity_force(self, particle):
        g = self.fields.get("gravity", 1.0)
        mass = particle.get("mass", 1.0)
        return (0.0, -g * mass, 0.0)

    def _magnetic_force(self, particle):
        m = self.fields.get("magnetism", 1.0)
        charge = particle.get("charge", 1.0)
        vx, vy, vz = particle.get("vx", 0.0), particle.get("vy", 0.0), particle.get("vz", 0.0)
        return m * charge * (-vy), m * charge * (vx), 0.0

    def _wave_push(self, particle):
        wf = self.fields.get("wave_frequency", 1.0)
        density = particle.get("density", 1.0)
        return (0.0, wf * density * 0.05, 0.0)

    def inject_proton(self, charge: float = 1.0, density: float = 1.0):
        particle = {"x": 0.0, "y": 0.0, "z": 0.0, "vx": 0.0, "vy": 0.0, "vz": 0.0,
                    "charge": charge, "density": density, "mass": 1.0,
                    "last_speed": 0.0, "velocity_delta": 0.0}
        self.particles.append(particle)
        return particle

    def _configure_stage(self):
        stage = self.stages[self.current_stage]
        if stage not in QWaveTuning.STAGE_CONFIGS:
            print(f"⚠ Stage '{stage}' not in QWaveTuning.STAGE_CONFIGS. Using defaults.")
            return
        self.fields.update(QWaveTuning.STAGE_CONFIGS[stage])
        print(f"⚙ Stage configured: {stage} -> {self.fields}")

    def advance_stage(self):
        """Advance to the next stage if not locked or at max."""
        if self.current_stage < len(self.stages) - 1:
            self.current_stage += 1
            print(f"🚀 Advanced to stage: {self.stages[self.current_stage]}")
            self._configure_stage()
            self._resync_harmonics()
        else:
            print("⚠ Stage advance skipped: Already at final stage.")

    def _resync_harmonics(self):
        harmonic_scale = QWaveTuning.harmonic_for_stage(self.stages[self.current_stage])
        print(f"🎶 Harmonic resync for stage '{self.stages[self.current_stage]}': {harmonic_scale}")
        self.fields["wave_frequency"] = QWaveTuning.STAGE_CONFIGS[self.stages[self.current_stage]]["wave_frequency"] * harmonic_scale

    def toggle_sqi(self, enable: bool):
        self.sqi_enabled = enable
        self.pending_sqi_ticks = None
        print(f"🔧 SQI {'ENABLED' if enable else 'DISABLED'} at runtime.")
        if enable:
            self._resync_harmonics()

    # -----------------------------------------
    # 🔀 Stage Transition
    # -----------------------------------------
    def transition_stage(self, new_stage: str):
        if new_stage not in self.stages:
            raise ValueError(f"❌ Invalid stage: {new_stage}")
        self.current_stage = self.stages.index(new_stage)
        self._configure_stage()
        self._resync_harmonics()

        # Optional: Auto-export .dc snapshot per stage
        from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.dc_container_io import DCContainerIO
        self.last_dc_trace = f"data/qwave_logs/{new_stage}_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dc.json"
        DCContainerIO.export({
            "fields": deepcopy(self.fields),
            "glyphs": [],
            "timestamp": datetime.utcnow().isoformat()
        }, self.last_dc_trace, stage=new_stage, sqi_enabled=self.sqi_enabled)
        print(f"📦 Auto-exported .dc snapshot for stage '{new_stage}' -> {self.last_dc_trace}")

# -------------------------
# ⚠ Instability Check (SQI-Aware)
# -------------------------
    def _check_instability(self) -> bool:
        """
        Detects instability spikes in resonance or particle motion.
        Returns True if instability is detected and tick should halt.
        """
        # ✅ Drift-based instability
        if len(self.resonance_filtered) >= 10:
            drift = max(self.resonance_filtered[-10:]) - min(self.resonance_filtered[-10:])
            if drift > QWaveTuning.RESONANCE_DRIFT_THRESHOLD:
                print(f"⚠ Instability detected: Drift={drift:.3f} exceeds threshold ({QWaveTuning.RESONANCE_DRIFT_THRESHOLD}).")
                return True

        # ✅ Particle velocity overspeed check
        for p in self.particles[-50:]:  # Only sample recent subset for performance
            speed = math.sqrt(p.get("vx", 0) ** 2 + p.get("vy", 0) ** 2 + p.get("vz", 0) ** 2)
            if speed > QWaveTuning.SPEED_THRESHOLD:
                print(f"⚠ Instability detected: Particle overspeed (speed={speed:.2f}) > {QWaveTuning.SPEED_THRESHOLD}")
                return True

        return False


# -------------------------
# 🔁 BEST STATE LOAD (Corrected + SQI-aware)
# -------------------------
    def _load_best_state(self):
        best_path = os.path.join(self.LOG_DIR, "qwave_best_state.json")
        if not os.path.exists(best_path):
            print("i️ No prior best state found. Starting fresh.")
            return

        try:
            with open(best_path) as f:
                best_state = json.load(f)

            # ✅ Validate structure
            if not all(k in best_state for k in ["fields", "particles", "score"]):
                print("⚠️ Corrupt best-state file detected. Skipping load.")
                return

            # ✅ Load fields & particles
            self.fields.update(best_state["fields"])
            self.particles = deepcopy(best_state["particles"])
            self.best_score = float(best_state["score"])

            # ✅ Recompute particle speed properties
            for p in self.particles:
                speed = math.sqrt(p.get("vx", 0) ** 2 + p.get("vy", 0) ** 2 + p.get("vz", 0) ** 2)
                p["last_speed"] = speed
                p["velocity_delta"] = 0.0

            # ✅ Sync stage config + harmonics
            self._configure_stage()
            self._resync_harmonics()

            # ✅ Reset drift metrics to prevent SQI overshoot
            self.resonance_filtered.clear()
            self.exhaust_log.clear()
            self.sqi_engine.last_drift = None
            self.sqi_engine.last_exhaust = None

            # ✅ Log initial snapshot
            self._log_graph_snapshot()

            print(f"🔁 Loaded best state: score={self.best_score:.4f} ({len(self.particles)} particles)")
            print(f"i️ SQI fine-tuning will {'run after initial stabilization ticks' if self.sqi_enabled else 'remain OFF until manually enabled'}.")

            # ✅ Delay SQI feedback only if SQI is enabled
            self.pending_sqi_ticks = 500 if self.sqi_enabled else None

        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ Failed to load best state: {e}. Starting fresh.")


    def _log_graph_snapshot(self):
        """Log current engine state for resonance graph tracking."""
        snapshot = {
            "tick": self.tick_count,
            "stage": self.stages[self.current_stage],
            "resonance": self.resonance_phase,
            "fields": self.fields.copy(),
            "particles": len(self.particles),
            "pulse": getattr(self, "pulse_detected", False)
        }
        self.graph_log.append(snapshot)
        print(f"📊 Graph snapshot logged: tick={snapshot['tick']} | stage={snapshot['stage']} | resonance={snapshot['resonance']:.4f}")


    def _compute_score(self):
        drift_penalty = abs(self.resonance_filtered[-1] if self.resonance_filtered else 0)
        exhaust_penalty = sum(e["impact_speed"] for e in self.exhaust_log[-5:]) / (len(self.exhaust_log[-5:]) or 1)
        return -(drift_penalty * 1.5 + exhaust_penalty * 1.0)


    def _export_best_state(self):
        """Export the best state snapshot to .dc.json without dc_container_io dependency."""
        from copy import deepcopy
        import json, os
        from datetime import datetime

        safe_score = float(self.best_score) if self.best_score is not None else 0.0
        stage = self.stages[self.current_stage]

        # Define export path
        self.last_dc_trace = f"data/qwave_logs/{stage}_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dc.json"
        os.makedirs(os.path.dirname(self.last_dc_trace), exist_ok=True)

        # Build export payload
        payload = {
            "fields": deepcopy(self.fields),
            "glyphs": [],
            "timestamp": datetime.utcnow().isoformat(),
            "stage": stage,
            "particles": len(self.particles),
            "score": safe_score,
            "sqi_enabled": self.sqi_enabled
        }

        # Write export file
        with open(self.last_dc_trace, "w") as f:
            json.dump(payload, f, indent=2)

        print(f"📦 Best state exported -> {self.last_dc_trace} | Score={safe_score:.4f}")

# -----------------------------
# ✅ NEW: Stage Stability Checker
# -----------------------------
    def _check_stage_stability(self) -> bool:
        """
        Determines if resonance drift has stabilized enough to advance stages.
        """
        if len(self.resonance_filtered) < self.stage_stability_window:
            return False

        drift_window = self.resonance_filtered[-self.stage_stability_window:]
        drift = max(drift_window) - min(drift_window)
        if drift <= self.stability_threshold:
            print(f"✅ Stage stability confirmed: Drift={drift:.4f} <= Threshold={self.stability_threshold}")
            return True
        return False

    # -----------------------------
    # 🏆 Best-State Tracking update 
    # -----------------------------
        current_score = self._compute_score()
        if self.best_score is None or current_score > self.best_score:
            self.best_score = current_score
            self.best_fields = self.fields.copy()
            self.best_particles = [p.copy() for p in self.particles]
            print(f"💾 [BEST] New best score {self.best_score:.4f}")
            self._export_best_state()

        # 📡 Virtual Exhaust (Stage-Specific)
        if self.virtual_absorber and self.current_stage == self.stages.index("controlled_exhaust"):
            self._simulate_virtual_exhaust()

        # 📊 Log graph snapshot every tick
        self._log_graph_snapshot()


def _check_stage_stability(self):
    if len(self.resonance_filtered) < self.stage_stability_window:
        return False
    window = self.resonance_filtered[-self.stage_stability_window:]
    drift = max(window) - min(window)

    # Log pulse signature
    if drift <= (self.stability_threshold * 0.5):  
        print(f"🫀 Pulse detected: drift={drift:.4f} (stable signature)")
        if not self.sqi_enabled:
            print("🔓 Auto-enabling SQI: Pulse stability confirmed.")
            self.sqi_enabled = True
            self.pending_sqi_ticks = 10  # Light SQI kickstart

    if drift <= self.stability_threshold:
        print(f"✅ Resonance stable (drift={drift:.3f}) -> Advancing stage.")
        self._log_graph_snapshot()
        return True
    return False


def _simulate_virtual_exhaust(self):
    impacts = []
    for p in self.particles:
        speed = math.sqrt(p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2)
        energy = 0.5 * p["mass"] * speed ** 2
        impacts.append({"speed": round(speed, 3), "energy": round(energy, 3)})
        self.exhaust_log.append({"tick": self.tick_count, "impact_speed": speed, "energy": energy})

        # 🔧 Adaptive coil tuning
        adjustment = self.field_bridge.auto_calibrate(target_voltage=1.0)
        if adjustment:
            drift = abs(self.resonance_filtered[-1] - self.resonance_filtered[-5]) if len(self.resonance_filtered) > 5 else 0
            if drift > 0.8:
                adjustment *= 0.5
            print(f"🔧 Coil auto-tuned by {adjustment:+.2f}")

        # 🧠 SQI Damp Feedback (energy threshold trigger)
        if energy > 5.0:
            self.fields["gravity"] = max(self.fields["gravity"] - 0.02, 0.1)
            self.fields["magnetism"] = max(self.fields["magnetism"] - 0.01, 0.1)
            print(f"🫀 SQI Damp: High exhaust energy ({energy:.3f}) -> Gravity/Magnetism reduced")

        # 🚀 Inline SQI micro-tune if energy oscillations persist
        if self.sqi_enabled and len(self.exhaust_log) > 10:
            last_exhaust = [e["impact_speed"] for e in self.exhaust_log[-10:]]
            drift = max(last_exhaust) - min(last_exhaust)
            if drift > 50:  # oscillation detected
                self.fields["wave_frequency"] *= 0.98
                print(f"🔧 [SQI-inline] Oscillation damp: wave_frequency -> {self.fields['wave_frequency']:.3f}")

        # Emit exhaust wave
        phase = self.resonance_filtered[-1] if self.resonance_filtered else 0
        self.field_bridge.emit_exhaust_wave(phase, energy)

        # Proton recycle
        p.update({"x": 0.0, "y": 0.0, "z": 0.0, "vx": 0.0, "vy": 0.0, "vz": 0.0})

    if impacts:
        last_impact = impacts[-1]
        print(f"📡 Virtual Exhaust Impact: {last_impact}")
        energies = [imp["energy"] for imp in impacts[-5:]]
        if len(energies) >= 5 and max(energies) - min(energies) < 0.2:
            print("🫀 Pulse signature confirmed in exhaust oscillation")

    self._log_graph_snapshot()

# -------------------------
# 🧠 SQI FEEDBACK (Toggle Enabled + Adaptive Reactivation)
# -------------------------
    def _run_sqi_feedback(self):
        # 🔴 SQI toggle check
        if not getattr(self, "sqi_enabled", True):
            print("🛑 SQI is currently disabled (set self.sqi_enabled=True to re-enable).")
            return

        # ✅ Require resonance history
        if not self.resonance_filtered or len(self.resonance_filtered) < 5:
            print("⚠️ SQI skipped: Insufficient resonance data.")
            return

        print("🧠 Running SQI symbolic fine-tuning...")
        trace = {
            "resonance": self.resonance_filtered[-50:],  
            "fields": self.fields.copy(),
            "exhaust": [e.get("impact_speed", 0) for e in self.exhaust_log[-20:]]
        }

        reasoning = self.sqi_engine.analyze_trace(trace)
        adjustments = self.sqi_engine.recommend_adjustments(reasoning)

        if not adjustments:
            print("✅ SQI skipped: No corrective adjustments needed.")
            return

        # ✅ Clamp gravity/magnetism
        adjustments["gravity"] = min(adjustments.get("gravity", self.fields["gravity"]), 5.0)
        adjustments["magnetism"] = min(adjustments.get("magnetism", self.fields["magnetism"]), 5.0)

        # ✅ Smooth adjustments
        for k, v in adjustments.items():
            adjustments[k] = (self.fields[k] * 0.7) + (v * 0.3)

        print(f"🔮 SQI Adjustments Applied (clamped): {adjustments}")
        self.fields.update(adjustments)
        self.last_sqi_adjustments = adjustments

        # ✅ Drift analysis for auto-pause/reactivation
        drift_window = self.resonance_filtered[-10:]
        drift = (max(drift_window) - min(drift_window)) if drift_window else 0.0

        if drift < self.stability_threshold * 0.6:
            self._low_drift_ticks = getattr(self, "_low_drift_ticks", 0) + 1
            if self._low_drift_ticks >= 5:  # Require persistent low-drift
                print("🛑 SQI auto-paused: Drift locked-in.")
                self.sqi_enabled = False
                self._low_drift_ticks = 0
        else:
            # ✅ Auto-reactivate if drift rises again significantly
            if not self.sqi_enabled and drift > self.stability_threshold:
                print("🔄 SQI auto-reactivated: Drift exceeded threshold.")
                self.sqi_enabled = True

    def get_state(self) -> Dict[str, Any]:
        return {
            "stage": self.stages[self.current_stage],
            "fields": self.fields,
            "particle_count": len(self.particles),
            "nested_containers": self.nested_containers,
            "particles": [{k: round(v, 3) if isinstance(v, float) else v for k, v in p.items()} for p in self.particles],
            "sqi_enabled": self.sqi_enabled,  # ✅ SQI state persistence
            "last_sqi_adjustments": getattr(self, "last_sqi_adjustments", {})
        }

    def set_state(self, state: Dict[str, Any]):
        self.fields = state.get("fields", self.fields)
        stage_name = state.get("stage", self.stages[0])
        if stage_name in self.stages:
            self.current_stage = self.stages.index(stage_name)
        self.nested_containers = state.get("nested_containers", [])
        self.particles = state.get("particles", [])
        self.sqi_enabled = state.get("sqi_enabled", False)  # ✅ Restore SQI toggle
        self.last_sqi_adjustments = state.get("last_sqi_adjustments", {})
        self.container.nested = self.nested_containers
        self.container.expand(avatar_state=self.safe_mode_avatar if self.safe_mode else None)
        self.resonance_log.clear()
        self.resonance_filtered.clear()
        self.pending_sqi_ticks = 20  # ✅ Grace period before re-enabling SQI
        print(f"✅ Engine state restored: {stage_name} ({len(self.particles)} particles)")

    # -------------------------
    # 🏆 BEST-STATE UTILITIES
    # -------------------------
    def _compute_score(self):
        drift_window = self.resonance_filtered[-10:]
        drift_penalty = (max(drift_window) - min(drift_window)) if drift_window else 0.0
        exhaust_penalty = sum(e.get("impact_speed", 0) for e in self.exhaust_log[-5:]) / max(len(self.exhaust_log[-5:]), 1)

        # ✅ SQI bonus: reward effective corrections
        sqi_bonus = 0.0
        if getattr(self, "last_sqi_adjustments", {}):
            prev_drift = getattr(self, "_prev_drift_for_score", drift_penalty)
            if drift_penalty < prev_drift:
                sqi_bonus = 0.3  # Drift improved since last SQI adjustment
            self._prev_drift_for_score = drift_penalty

        drift_penalty = min(drift_penalty, 5.0)
        exhaust_penalty = min(exhaust_penalty, 10.0)

        score = -(drift_penalty * 1.5 + exhaust_penalty) + sqi_bonus
        print(f"🏆 [Score] Drift={drift_penalty:.3f}, Exhaust={exhaust_penalty:.2f}, SQI Bonus={sqi_bonus:.2f} -> Score={score:.4f}")
        return score

    def _export_best_state(self):
        os.makedirs(self.LOG_DIR, exist_ok=True)
        best_path = os.path.join(self.LOG_DIR, "qwave_best_state.json")
        data = {
            "fields": self.best_fields,
            "particles": deepcopy(self.best_particles),
            "score": self.best_score,
            "sqi_enabled": self.sqi_enabled,  # ✅ Store SQI toggle
            "last_sqi_adjustments": getattr(self, "last_sqi_adjustments", {}),
            "timestamp": datetime.now().isoformat()
        }
        with open(best_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Best state exported: {best_path}")

# -------------------------
# 🔥 QWave Auto-Tuner (SQI Toggle-Aware)
# -------------------------
class QWaveAutoTuner:
    def __init__(self, engine: SupercontainerEngine):
        self.engine = engine
        self.sqi_cooldown = 0  # ✅ SQI cooldown syncs with engine state if available

    def tune(self, iterations=50):
        for i in range(iterations):
            print(f"\n🔄 Auto-Tune Iteration {i+1}/{iterations}")
            self.engine.run_simulation(duration=8)

            drift = self._get_current_drift()
            print(f"📈 Drift Check: {drift:.3f}")

            # ✅ Auto-reactivate SQI if drift spikes past critical threshold
            if not getattr(self.engine, "sqi_enabled", False) and drift > 1.2:
                print("🔄 Auto-reactivating SQI: Drift spike detected.")
                self.engine.sqi_enabled = True

            # ✅ Conditional SQI trigger
            if drift > 0.8 and self.sqi_cooldown == 0:
                if self.engine.sqi_enabled:
                    print(f"⚠ SQI triggered: Drift={drift:.3f}")
                    self.engine._run_sqi_feedback()
                    self.sqi_cooldown = 3  # SQI enforced cooldown
                    self.engine.pending_sqi_ticks = 10  # Sync engine-side SQI gating
                else:
                    print(f"🛑 SQI disabled: Drift={drift:.3f}, skipping correction.")
            else:
                print(f"✅ SQI skipped (Drift={drift:.3f}, Cooldown={self.sqi_cooldown})")

            # ✅ Stability evaluation
            stability = self._evaluate_stability()
            print(f"📊 Stability Score: {stability:.3f}")

            if stability >= 0.9:
                print(f"🫀 Pulse detected: Resonance stable (Score={stability:.3f})")

            # ✅ Early exit if tuned
            if stability >= 0.95:
                print("✅ Stability target reached. Auto-tuning complete.")
                break

            # ✅ Decrement SQI cooldown with adaptive shortening if drift is falling fast
            if self.sqi_cooldown > 0:
                if drift < 0.6:  
                    self.sqi_cooldown = max(0, self.sqi_cooldown - 2)  # Cut cooldown faster if stable
                else:
                    self.sqi_cooldown -= 1

    def _evaluate_stability(self) -> float:
        if not self.engine.resonance_filtered:
            return 0.0
        window = self.engine.resonance_filtered[-20:]
        drift = max(window) - min(window)
        stability_score = max(0.0, 1.0 - min(drift / 10.0, 1.0))

        # ✅ Bonus for recent SQI corrections
        if getattr(self.engine, "last_sqi_adjustments", None):
            stability_score = min(1.0, stability_score + 0.05)
        return stability_score

    def _get_current_drift(self) -> float:
        if not self.engine.resonance_filtered:
            return 0.0
        window = self.engine.resonance_filtered[-10:]
        return max(window) - min(window)