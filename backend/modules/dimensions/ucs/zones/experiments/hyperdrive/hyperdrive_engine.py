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
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.warp_checks import check_warp_pi
from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

# ECU and Auto-Tuner
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.ecu_runtime_module import ecu_runtime_loop
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_auto_tuner_module import HyperdriveAutoTuner
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import resync_harmonics, inject_harmonics

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

# Added predictive and collapse trace imports
from backend.modules.collapse.collapse_trace_exporter import export_collapse_trace
from backend.modules.glyphos.glyph_trace_logger import glyph_trace
from backend.modules.consciousness.prediction_engine import PredictionEngine
# Awareness + Drift Damping
from backend.modules.consciousness.awareness_engine import AwarenessEngine
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.drift_damping import apply_drift_damping

# -------------------------
# 🔥 HYPERDRIVE ENGINE CLASS
# -------------------------
class HyperdriveEngine:
    SAVE_PATH = "data/qwave_engine_state.json"
    LOG_DIR = "data/qwave_logs"

    def __init__(self, name: str, args, runtime,
                 container: SymbolicExpansionContainer, safe_mode: bool = False,
                 stage_lock: int = 6, virtual_absorber: bool = True, sqi_enabled: bool = True):
        self.name = name
        self.args = args
        self.runtime = runtime
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
        self.sqi_controller = SQIController(self)

        # ✅ Initialize Hyperdrive Constants FIRST
        HyperdriveTuningConstants.load_runtime()

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
        self.event_log: List[Dict[str, Any]] = []

        # ⚛ Dynamics
        self.damping_factor = HyperdriveTuningConstants.DAMPING_FACTOR
        self.decay_rate = HyperdriveTuningConstants.DECAY_RATE

        # 🏆 Best-state tracking
        self.best_score: float = None
        self.best_fields: Dict[str, float] = {}
        self.best_particles: List[Dict[str, Any]] = []
        self.best_state_module = BestStateModule(self)

        # 🔌 Subsystems
        self.injectors = [TesseractInjector(i, phase_offset=i * 3) for i in range(4)]
        self.chambers = [CompressionChamber(i, compression_factor=1.3) for i in range(4)]
        self.field_bridge = FieldBridge(safe_mode=safe_mode)
        self.sqi_engine = SQIReasoningEngine(engine=self)

        # 🧠 Awareness Engine (IGI Integration)
        if not hasattr(self, "awareness"):
            self.awareness = AwarenessEngine(container=getattr(self, "container", None))

        # 🔗 Twin Engine Support (Dual-warp runtime)
        self.twin_engine = None
        self.injector_controller = self.injectors[0] if self.injectors else None
        self.last_dc_trace = None
        self.particle_density: float = 1.0   # Default density baseline
        self.particles: list = []            # Ensure particle list exists

        self.collapse_enabled = HyperdriveTuningConstants.ENABLE_COLLAPSE
        self.stage_stability_window = 50
        self.stability_threshold = HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD / 2
        self.gain = HyperdriveTuningConstants.HARMONIC_GAIN

        # 🛡 Safe Mode Config
        self._configure_safe_mode()

        # Tick orchestration logic (async-compatible)
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tick_orchestrator import (
            run_tick_orchestration,
            _single_tick,
        )

        # Bind orchestrated tick methods
        self._single_tick = _single_tick.__get__(self)
        self.tick = lambda: asyncio.run(run_tick_orchestration(self))

        # Ensure log directory exists
        os.makedirs(self.LOG_DIR, exist_ok=True)

        # ✅ State Init (AFTER stages exist)
        self.tuning_constants = HyperdriveTuningConstants.restore()
        self.name = name
        self.args = args
        self.runtime = runtime

        # ✅ Initialize Engine Chambers
        self.engine_containers = []
        self.CHAMBER_COUNT = 4

        for i in range(self.CHAMBER_COUNT):
            sec_id = f"SEC-chamber-{i}"
            hob_id = f"HOB-chamber-{i}"

            # 🧩 Create Symbolic Expansion Container
            sec = UCSBaseContainer(
                name=sec_id,
                geometry="Symbolic Expansion Sphere",
                runtime=self.runtime,
                container_type="SEC",
                features={
                    "time_dilation": 1.0,
                    "micro_grid": True
                }
            )

            # 🌀 Create Hoberman Sphere Container
            hob = UCSBaseContainer(
                name=hob_id,
                geometry="Hoberman Sphere",
                runtime=self.runtime,
                container_type="HOB",
                features={
                    "time_dilation": 1.0,
                    "micro_grid": True
                }
            )

            self.engine_containers.extend([sec, hob])

    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import resync_harmonics

    def ignite(self):
        """
        Initialize plasma ignition and ensure particle baseline.
        - Ensures particles exist.
        - Centralized harmonic resync via module.
        """
        if not self.particles:
            self.spawn_particles(count=250, velocity=0.5)

        # 🎼 Centralized harmonic resync
        resync_harmonics(self)

        print("🔥 Hyperdrive ignition sequence complete.")

        # ✅ Pre-Ignition Warp PI Validation
        pi_check = check_warp_pi(self, window=300, label="ignite_warp_pi_snapshot")
        if not pi_check:
            print("⚠ Warp PI threshold not met. Continuing warm-up sequence...")  

    def spawn_particles(self, count=250, velocity=0.5):
        for _ in range(count):
            self.particles.append({
                "vx": 0.0, "vy": 0.0, "vz": velocity,
                "x": 0.0, "y": 0.0, "z": 0.0,
                "mass": 1.0, "charge": 1.0, "density": 1.0
            })
        print(f"💠 Seeded engine with {count} baseline plasma particles.")


        # 📦 Export collapse trace
        self.last_dc_trace = export_collapse_trace(self.get_state())
        self.log_event("📦 Collapse trace exported for replay/debugging.")

        # 🛰️ Log GHX/Codex replay snapshot
        glyph_trace.add_glyph_replay(
            glyphs=[{"id": f"tick_{self.tick_count}", "glyph": "⧖"}],  # placeholder glyph for SQI lock
            container_id=self.container.id,
            tick_start=max(0, self.tick_count - 50),
            tick_end=self.tick_count,
            entangled_links=[],
        )

        # 🎼 Sync harmonic constants
        HyperdriveTuningConstants.load_runtime()
        self.damping_factor = HyperdriveTuningConstants.DAMPING_FACTOR
        self.decay_rate = HyperdriveTuningConstants.DECAY_RATE
        print(f"🎼 Harmonic constants synced: Gain={HyperdriveTuningConstants.HARMONIC_GAIN:.4f} | Decay={self.decay_rate:.4f} | Damping={self.damping_factor:.4f}")
        
        # 🛡 Restore idle baseline fields if drift detected on boot
        if any(abs(self.fields[k] - v) > 0.2 for k, v in HyperdriveTuningConstants.BEST_IDLE_FIELDS.items()):
            print("🛡 Restoring idle baseline fields from HyperdriveTuningConstants.BEST_IDLE_FIELDS")
            self.fields.update(deepcopy(HyperdriveTuningConstants.BEST_IDLE_FIELDS))

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
    # ✅ SQI LOCK HANDLER
    # -------------------------
    def handle_sqi_lock(self, drift: float):
        if not self.sqi_locked:
            self.sqi_locked = True
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import resync_harmonics
            resync_harmonics(self)
            self.log_event(f"🔒 SQI Lock achieved | Drift={drift:.4f} | Resonance={self.resonance_phase:.4f}")
            if hasattr(self, "save_idle_state"):
                self.save_idle_state(self)
                print(f"💾 SQI idle state saved at drift={drift:.4f}")
            # 🔗 Sync preset at lock
            self.sqi_controller.apply_preset("100%")
            # 📦 Export DC trace at SQI lock
            self.last_dc_trace = export_collapse_trace(self)
            self.log_event("📦 Collapse trace exported for replay/debugging.")
            # 🛡 Save safe constants snapshot on SQI lock
            HyperdriveTuningConstants.save_runtime()
            self.log_event("💾 HyperdriveTuningConstants snapshot persisted at SQI lock.")

    import asyncio

    # -------------------------
    # 🔮 PREDICTIVE GLYPH INJECTION (Delegated)
    # -------------------------
    def inject_from_prediction(self, prediction: Dict[str, Any]):
        """
        Delegates predictive glyph injection to tick_module.
        """
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tick_module import inject_from_prediction
        inject_from_prediction(self, prediction)

    def log_event(self, message: str):
        """
        🪵 Log Engine Event (if logger exists)
        Allows optional runtime event logging for diagnostics.
        """
        try:
            print(f"[LOG][{self.name}] {message}")  # fallback
            if hasattr(self, "logger"):
                self.logger.info(message)
        except Exception as e:
            print(f"[WARN] log_event failed: {e}")

# -------------------------
# 🔥 SINGLE TICK (Async)
# -------------------------
async def _single_tick(self):
    """
    Executes a single tick with:
    - Pre-tick instability check
    - Drift damping + Awareness feedback
    - Core tick logic execution
    - Optional twin-engine sync
    """
    # 🛑 Pre-tick Instability Check
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.instability_check_module import check_instability
    if check_instability(self):
        self.log_event("⚠️ Instability detected: Tick skipped for stabilization.")
        return

    # 🌊 Drift Damping + Awareness Feedback
    drift = apply_drift_damping(self)
    if hasattr(self, "awareness"):
        try:
            self.awareness.update_confidence(max(0.0, 1.0 - drift))
            self.awareness.record_confidence(
                glyph="🎶",
                coord=f"stage:{self.stages[self.current_stage]}",
                container_id=getattr(self.container, "id", "N/A"),
                tick=self.tick_count,
                trigger_type="sqi_drift_feedback"
            )
            if drift > self.sqi_engine.target_resonance_drift:
                self.awareness.log_blindspot(
                    glyph="⚠",
                    coord=f"stage:{self.stages[self.current_stage]}",
                    container_id=getattr(self.container, "id", "N/A"),
                    tick=self.tick_count,
                    context="high_drift_blindspot"
                )
        except Exception as e:
            self.log_event(f"⚠️ AwarenessEngine drift logging failed: {e}")

    # ✅ Core Tick Logic
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tick_module import tick
    tick(self)

    # 🔗 Twin Engine Auto-Tick (if linked)
    if self.twin_engine:
        await self.twin_engine._single_tick()

def _initialize_state(self):
    """Initialize runtime state and default config flags."""
    self.state = {}
    self.state["tick_count"] = 0
    self.state["drift_accumulator"] = 0.0
    self.state["instability_flags"] = []
    self.state["last_collapse_tick"] = 0

    # Optional: preload harmonic profile state
    self.state["current_profile"] = getattr(self, "default_profile", "warp")
    self.state["phase_sync_enabled"] = getattr(self, "use_new_phase_sync", False)

    print("🧠 Runtime state initialized.")

# -------------------------
# 🧪 BATCH SIMULATION RUNNER (Unified)
# -------------------------
async def run_simulation(self, tick_limit: int = 1000, export_trace: bool = False, collapse_interval: int = 100):
    """
    Unified simulation runner:
    - Executes async ticks with drift damping, SQI feedback, and safety guards.
    - Auto-enforces safe tuning every 20 ticks.
    - Periodically exports collapse traces for Codex/GHX replay.
    - Supports twin-engine linked hyperdrive runs.
    """
    self.tick_limit = tick_limit
    self.log_event(f"🧠 Starting simulation loop for {tick_limit} ticks...")

    for _ in range(tick_limit):
        # 🔥 Primary Engine Tick
        await self._single_tick()

        # 🔗 Twin Engine Sync Tick (if linked)
        if self.twin_engine:
            await self.twin_engine._single_tick()

        # 🛡 Enforce safe tuning every 20 ticks
        if self.tick_count % 20 == 0:
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.safe_tuning_module import validate_constant_ranges
            if not validate_constant_ranges(self.fields):
                from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
                self.fields.update(HyperdriveTuningConstants.BEST_IDLE_FIELDS)
                self.log_event("🛡 Auto-corrected fields during simulation.")

        # 🎞 Export collapse trace snapshots
        if self.tick_count % collapse_interval == 0:
            from backend.modules.collapse.collapse_trace_exporter import export_collapse_trace
            export_collapse_trace(self.get_state())
            self.log_event(f"🎞 Collapse trace snapshot saved at tick {self.tick_count}")

    # 📦 Final snapshot + GHX replay export
    from backend.modules.collapse.collapse_trace_exporter import export_collapse_trace
    export_collapse_trace(self.get_state())

    from backend.modules.glyphnet.glyph_trace_logger import glyph_trace
    glyph_trace.add_glyph_replay(
        glyphs=[{"id": f"sim_{self.tick_count}", "glyph": "↯"}],
        container_id=self.container.id,
        tick_start=max(0, self.tick_count - tick_limit),
        tick_end=self.tick_count,
    )

    self.log_event(f"✅ Simulation complete at tick {self.tick_count}.")

    # -------------------------
    # 🛠 VIRTUAL EXHAUST → PARTICLE LINK (Delegated)
    # -------------------------
    def _simulate_virtual_exhaust(self):
        """
        Delegates virtual exhaust simulation to the dedicated module.
        Retains logging and particle impact handling through the centralized function.
        """
        from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.virtual_exhaust_module import simulate_virtual_exhaust
        
        # ✅ Call unified exhaust simulation (handles particle kick, PI metric, and SQI tuning internally)
        simulate_virtual_exhaust(self)

    # -------------------------
    # ✅ SYNC WRAPPER
    # -------------------------
    def tick(self):
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.create_task(self._single_tick())  
        else:
            return loop.run_until_complete(self._single_tick())
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
        """Initialize engine state from saved or best state, else start fresh."""
        self._load_best_state()
        if os.path.exists(self.SAVE_PATH) and not self.safe_mode:
            print("♻️ Loading saved engine state...")
            self.set_state(self._load_saved_state())
        else:
            print("⚙ No saved state; initializing stage...")

            # 🔑 Stage transition
            transition_stage(self, self.stages[self.current_stage])
            self.log_event(f"🔁 Stage initialized: {self.stages[self.current_stage]}")

            # 🎵 Apply stage harmonic boost
            stage_gain = HyperdriveTuningConstants.harmonic_for_stage(self.stages[self.current_stage])
            self.fields["wave_frequency"] *= stage_gain
            self.log_event(f"🎵 Stage harmonic boost applied: x{stage_gain:.3f}")

            # 🎼 Resync harmonics
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import resync_harmonics
            resync_harmonics(self)

            # 🛰️ Log symbolic trace for GHX/Codex replay
            glyph_trace.log_trace(
                glyph="🎵",
                result=f"Stage {self.stages[self.current_stage]} harmonic boost: x{stage_gain:.3f}",
                context="hyperdrive_stage"
            )

            # ✅ Restore BEST_IDLE_FIELDS baseline
            self.fields.update(HyperdriveTuningConstants.BEST_IDLE_FIELDS)
            print("♻️ Restored BEST_IDLE_FIELDS baseline fields.")

            # 🔒 Validate SoulLaw avatar context
            avatar_state = self.safe_mode_avatar if self.safe_mode else {
                "id": "hyperdrive_runtime",
                "role": "engine_operator",
                "level": get_soul_law_validator().MIN_AVATAR_LEVEL
            }
            if not get_soul_law_validator().validate_avatar_with_context(
                avatar_state=avatar_state,
                context="hyperdrive_symbolic_expansion"
            ):
                raise PermissionError("Avatar failed SoulLaw validation for Symbolic Expansion.")

            # 🌌 Expand container with morality enforcement
            self.container.expand(avatar_state=avatar_state, recursive_unlock=True, enforce_morality=True)

            # 🛡 Validate field safety after expansion
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.safe_tuning_module import validate_constant_ranges
            if not validate_constant_ranges(self.fields):
                print("⚠ Safe-tuning auto-correct triggered: resetting invalid field values.")
                self.fields.update(HyperdriveTuningConstants.BEST_IDLE_FIELDS)
                self.log_event("🛡 Safe field correction applied after expansion.")

    # -------------------------
    # 🔗 Twin Engine Sync Helper
    # -------------------------
    def get_sync_state(self):
        """Return minimal sync snapshot for twin-engine alignment."""
        return {
            "resonance_phase": self.resonance_phase,
            "fields": self.fields.copy(),
            "sqi_enabled": self.sqi_enabled
        }

            
    def _load_best_state(self):
        """Load best known engine state from persistent storage."""
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