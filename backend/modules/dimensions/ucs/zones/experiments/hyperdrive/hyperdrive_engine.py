import os
import json
import math
import time
import random
from datetime import datetime
from typing import Dict, Any, List
from copy import deepcopy
import matplotlib.pyplot as plt

# -------------------------
# 🧩 Core Dependencies
# -------------------------
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_field_bridge import FieldBridge
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tesseract_injector import TesseractInjector, CompressionChamber
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants

# Modularized Subsystems
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import SQIReasoningEngine
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.dc_container_io_module import DCContainerIO
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.safe_tuning_module import safe_qwave_tuning

# ECU and Auto-Tuner
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.ecu_runtime_module import ecu_runtime_loop
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_auto_tuner_module import HyperdriveAutoTuner

# Stage and Stability
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.stage_transition_module import transition_stage
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.instability_check_module import check_instability
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.stage_stability_module import check_stage_stability

# Virtual Exhaust
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.virtual_exhaust_module import simulate_virtual_exhaust

# SQI Feedback and State
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_feedback_module import run_sqi_feedback
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.state_manager_module import get_state, set_state
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.best_state_module import BestStateModule

# SQI Controller (for preset sync)
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_controller_module import SQIController


# -------------------------
# 🔥 HYPERDRIVE ENGINE CLASS
# -------------------------
class HyperdriveEngine:
    SAVE_PATH = "data/qwave_engine_state.json"
    LOG_DIR = "data/qwave_logs"

    def __init__(self, container: SymbolicExpansionContainer, safe_mode: bool = False,
                 stage_lock: int = 6, virtual_absorber: bool = True, sqi_enabled: bool = True):  # ✅ Default ON
        self.container = container
        self.safe_mode = safe_mode
        self.stage_lock = stage_lock
        self.virtual_absorber = virtual_absorber
        self.tick_limit = 1000 if safe_mode else 20000
        self.tick_count = 0

        # 🔧 SQI State
        self.sqi_enabled = sqi_enabled
        self.sqi_locked = sqi_enabled
        self.pending_sqi_ticks = None
        self.last_sqi_adjustments: Dict[str, float] = {}
        self.sqi_controller = SQIController(self)  # ✅ Controller for preset sync

        # 🔑 Stage Management
        self.stages = list(HyperdriveTuningConstants.STAGE_CONFIGS.keys())
        self.current_stage = self.stages.index("G1") if "G1" in self.stages else 0

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

        # 📝 Event Log
        self.event_log: List[Dict[str, Any]] = []

        # ⚛ Dynamics
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
        self.damping_factor = HyperdriveTuningConstants.DAMPING_FACTOR
        self.decay_rate = HyperdriveTuningConstants.DECAY_RATE
        self.decay_rate = DECAY_RATE

        # 🏆 Best-state tracking
        self.best_score: float = None
        self.best_fields: Dict[str, float] = {}
        self.best_particles: List[Dict[str, Any]] = []
        self.best_state_module = BestStateModule(self)

        # 🔌 Subsystems
        self.injectors = [TesseractInjector(i, phase_offset=i * 3) for i in range(4)]
        self.chambers = [CompressionChamber(i, compression_factor=1.3) for i in range(4)]
        self.field_bridge = FieldBridge(safe_mode=safe_mode)
        self.sqi_engine = SQIReasoningEngine()
        self.last_dc_trace = None

        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
        self.collapse_enabled = HyperdriveTuningConstants.ENABLE_COLLAPSE

        # 🎯 Stability thresholds
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
        self.stage_stability_window = 50
        self.stability_threshold = HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD / 2

        # 🛡 Safe Mode Config
        self._configure_safe_mode()

        # ✅ Tick override
        self.tick = self._single_tick

        os.makedirs(self.LOG_DIR, exist_ok=True)
        self._initialize_state()

        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants

        # ✅ Restore harmonic constants directly into engine context
        HyperdriveTuningConstants.load_runtime()
        self.damping_factor = HyperdriveTuningConstants.DAMPING_FACTOR
        self.decay_rate = HyperdriveTuningConstants.DECAY_RATE
        print(f"🎼 Harmonic constants synced: Gain={HyperdriveTuningConstants.HARMONIC_GAIN:.4f} | Decay={self.decay_rate:.4f} | Damping={self.damping_factor:.4f}")

    # -------------------------
    # 🛡 SAFE MODE CONFIG
    # -------------------------
    def _configure_safe_mode(self):
        if self.safe_mode:
            print("🛡️ Engine initialized in SAFE MODE.")
            self.fields = {k: min(v, 1.0) for k, v in self.fields.items()}
            self.max_particles = 300
            self.tick_delay = 0.03
        else:
            self.max_particles = 800
            self.tick_delay = 0.005
        self.safe_mode_avatar = {"level": get_soul_law_validator().MIN_AVATAR_LEVEL}

    # -------------------------
    # 🎼 HARMONIC RESYNC
    # -------------------------
    def _resync_harmonics(self):
        print("🎼 Resynchronizing harmonic resonance...")
        base_frequency = self.fields.get("wave_frequency", 1.0)
        self.resonance_phase = 0.0
        for i, injector in enumerate(self.injectors):
            injector.phase_offset = i * (360 / max(len(self.injectors), 1))
            injector.sync_to_frequency(base_frequency)
        for chamber in self.chambers:
            chamber.adjust_harmonic(base_frequency)
        print(f"✅ Harmonic resync complete: Base Frequency={base_frequency}")

    # -------------------------
    # 🎼 HARMONIC INJECTION
    # -------------------------
    def _inject_harmonics(self, harmonics: List[float]):
        if not harmonics:
            return
        print(f"🎵 Injecting harmonics: {harmonics}")
        base_freq = self.fields.get("wave_frequency", 1.0)
        for i, injector in enumerate(self.injectors):
            harmonic = harmonics[i % len(harmonics)]
            injector.sync_to_frequency(base_freq * harmonic)
        for chamber in self.chambers:
            chamber.adjust_harmonic(base_freq)
        self.resonance_phase += sum(harmonics) * 0.001
        self.resonance_log.append(self.resonance_phase)
        if len(self.resonance_log) > 200:
            self.resonance_log.pop(0)

    # -------------------------
    # ✅ SQI LOCK HANDLER
    # -------------------------
    def handle_sqi_lock(self, drift: float):
        if not self.sqi_locked:
            self.sqi_locked = True
            self._resync_harmonics()
            self.log_event(f"🔒 SQI Lock achieved | Drift={drift:.4f} | Resonance={self.resonance_phase:.4f}")
            if hasattr(self, "save_idle_state"):
                self.save_idle_state(self)
                print(f"💾 SQI idle state saved at drift={drift:.4f}")
            # 🔗 Sync preset at lock
            self.sqi_controller.apply_preset("100%")

    # -------------------------
    # 🔥 SINGLE TICK
    # -------------------------
    def _single_tick(self):
        self.tick_count += 1
        self._simulate_virtual_exhaust()
        self._run_sqi_feedback()
        self._log_graph_snapshot()

        # 🎶 Harmonic coherence measurement
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence
        coherence = measure_harmonic_coherence(self)
        self.log_event(f"Harmonic Coherence: {coherence:.3f}")

        # Auto-adjust harmonic gain if coherence is low
        if coherence < 0.8:
            # Adjust harmonic gain dynamically using HyperdriveTuningConstants
            boost = HyperdriveTuningConstants.HARMONIC_GAIN * 1.02
            HyperdriveTuningConstants.HARMONIC_GAIN = boost
            self.log_event(f"⚠ Harmonic coherence low ({coherence:.3f}) → Boosting gain to {boost:.4f}")

        # 🎵 Periodic harmonic injection during SQI runtime
        if self.sqi_enabled and self.tick_count % 100 == 0:  # every 100 ticks
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
            self._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)

        if self.sqi_enabled:
            drift = max(self.resonance_filtered[-20:], default=0) - min(self.resonance_filtered[-20:], default=0)
            if drift <= self.stability_threshold:
                self.handle_sqi_lock(drift)

        if self.tick_count >= self.tick_limit:
            print(f"⚠ Tick limit reached: {self.tick_limit}")
            return

    # -------------------------
    # 📝 EVENT LOGGER
    # -------------------------
    def log_event(self, message: str, level: str = "INFO"):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        }
        self.event_log.append(entry)
        log_path = os.path.join(self.LOG_DIR, "engine_events.log")
        with open(log_path, "a") as f:
            f.write(f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}\n")
        print(f"[{entry['level']}] {entry['message']}")

    # -------------------------
    # 📈 GRAPH SNAPSHOT LOGGER
    # -------------------------
    def _log_graph_snapshot(self):
        snapshot = {
            "tick": self.tick_count,
            "resonance": self.resonance_phase,
            "fields": self.fields.copy(),
            "particles": len(self.particles),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.graph_log.append(snapshot)
        if len(self.graph_log) > 5000:
            self.graph_log.pop(0)

    # -------------------------
    # 🔁 ENGINE INIT STATE
    # -------------------------
    def _initialize_state(self):
        self._load_best_state()
        if os.path.exists(self.SAVE_PATH) and not self.safe_mode:
            print("♻️ Loading saved engine state...")
            self.set_state(self._load_saved_state())
        else:
            print("⚙ No saved state; initializing stage...")
            transition_stage(self, self.stages[self.current_stage])
            # 🎼 Auto-resync harmonics after stage initialization
            self._resync_harmonics()
            self.container.expand(avatar_state=self.safe_mode_avatar)

    def _load_best_state(self):
        best_state_path = "data/qwave_best_state.json"
        if os.path.exists(best_state_path):
            try:
                with open(best_state_path, "r") as f:
                    state = json.load(f)
                self.fields.update(state.get("fields", {}))
                self.best_score = state.get("score", None)
                self.best_fields = state.get("fields", {}).copy()
                self.best_particles = state.get("particles", [])
                print(f"🔁 Loaded best state: score={self.best_score}")
            except Exception as e:
                print(f"⚠ Failed to load best state: {e}")
        else:
            print("⚠ No best state file found. Using baseline fields.")

    # ✅ Best State Accessors
    def compute_score(self):
        return self.best_state_module._compute_score()

    def export_best_state(self):
        return self.best_state_module._export_best_state()

    # -------------------------
    # 🔗 MODULE BINDINGS
    # -------------------------
    transition_stage = transition_stage
    _check_instability = check_instability
    _check_stage_stability = check_stage_stability
    _simulate_virtual_exhaust = simulate_virtual_exhaust
    _run_sqi_feedback = run_sqi_feedback
    get_state = get_state
    set_state = set_state