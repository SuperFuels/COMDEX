# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/sqi_controller_module.py

import os, json, time, random
from datetime import datetime
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_engine_sync import sync_twin_engines as sync_engines
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.drift_damping import apply_drift_damping
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.warp_checks import check_pi_threshold
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger


PROFILE_FILE = "data/qwave_resonance_profile.json"
CONTROL_PRESETS = "backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/config/control_presets.json"

class SQIController:
    """
    🚀 Advanced SQI Controller:
    - Automates drift stabilization, resonance climb, and warp readiness.
    - Controls engine fields, harmonics, injectors, and particle tuning.
    - Interfaces with tick module for lock stabilization & harmonic resync.
    """

    def __init__(self, engine, engine_b=None):
        self.engine = engine
        self.engine_b = engine_b
        self.resonance_profile = self._load_profile()
        self.presets = self._load_presets()
        self.max_resonance = 100_000.0  # HARD STOP enforced

    # =========================
    # 🎯 TARGET + FIELD CONTROL
    # =========================
    def set_target(self, target_resonance: float):
        """Set target resonance drift percentage and enforce SQI hard stop."""
        if target_resonance > self.max_resonance:
            target_resonance = self.max_resonance
        self.engine.sqi_engine.target_resonance_drift = target_resonance * 0.00001
        self.engine.log_event(f"🎯 SQI target resonance set: {target_resonance:.2f}")

    def adjust_fields(self, gravity=None, magnetism=None, wave_frequency=None, field_pressure=None):
        """Fine-tune engine fields dynamically (SQI-controlled)."""
        if gravity is not None: self.engine.fields["gravity"] = gravity
        if magnetism is not None: self.engine.fields["magnetism"] = magnetism
        if wave_frequency is not None: self.engine.fields["wave_frequency"] = wave_frequency
        if field_pressure is not None: self.engine.fields["field_pressure"] = field_pressure
        self.engine.log_event(f"⚙ Fields updated: {self.engine.fields}")

    def adjust_harmonics(self, gain=None, decay=None, damping=None, drift_threshold=None):
        """Adjust harmonic and stability parameters via runtime setters."""
        if gain is not None: set_harmonic_gain(gain)
        if decay is not None: set_decay_rate(decay)
        if damping is not None: set_damping_factor(damping)
        if drift_threshold is not None: set_resonance_threshold(drift_threshold)
        self.engine.log_event(f"🎶 Harmonics/stability tuned: Gain={gain} Decay={decay} Damp={damping} Drift={drift_threshold}")

    # =========================
    # 🛡️ LOCK & STABILIZE (NEW)
    # =========================
    def lock_and_stabilize(self, drift: float):
        """
        Called during SQI lock-in from tick:
        - Resync harmonics
        - Apply closest control preset
        - Log resonance & lock profile
        """
        self.engage_feedback()

        # Harmonic resync
        if hasattr(self.engine, "_resync_harmonics"):
            self.engine._resync_harmonics()
            self.engine.log_event("🎼 Harmonic resync triggered on SQI lock.")

        # Apply nearest preset based on drift %
        drift_pct = int(drift * 100)
        nearest_preset = f"{min(max(drift_pct, 50), 100)}%"
        if nearest_preset in self.presets:
            self.apply_preset(nearest_preset)
            self.engine.log_event(f"🎛 Preset '{nearest_preset}' applied on SQI lock.")

        # Save resonance profile
        self._lock_resonance(drift_pct)
        self.engine.log_event(f"✅ SQI lock stabilized: Drift={drift:.4f}, Resonance={self.engine.resonance_phase:.4f}")

    # =========================
    # 🔄 AUTO OPTIMIZATION LOOP
    # =========================
    def auto_optimize(self, stages=None):
        """Optimize resonance across staged targets with preset enforcement."""
        stages = stages or [85, 90, 95, 99, 100]
        for stage in stages:
            self.apply_preset(f"{stage}%")
            self.set_target(stage)
            for _ in range(6):
                self.engine._run_sqi_feedback()
                self._inject_noise()
                self._sync_and_damp()
                self.engine.tick()
                TelemetryLogger().log({
                    "tick": self.engine.tick_count,
                    "resonance": self.engine.resonance_phase,
                    "fields": self.engine.fields,
                    "particles": len(self.engine.particles),
                    "timestamp": datetime.utcnow().isoformat()
                })
                time.sleep(0.3)
            self._lock_resonance(stage)
            if stage >= 100:
                self.engine.log_event("🛑 SQI cap reached at 100k resonance.")
                break

    # =========================
    # 🚀 WARP RAMP SEQUENCE
    # =========================
    def auto_warp_ramp(self):
        """SQI-driven smooth climb to warp-ready resonance."""
        self.engine.auto_sequence = True
        self.engine.log_event("🚀 SQI warp ramp initiated.")
        self.engage_feedback()

        for stage in [85, 90, 95, 99, 100]:
            if not self.engine.auto_sequence:
                break
            self.apply_preset(f"{stage}%")
            self.set_target(stage)
            for _ in range(8):
                self.engine._run_sqi_feedback()
                self._inject_noise()
                self._sync_and_damp()
                self.engine.tick()
                TelemetryLogger().log({
                    "tick": self.engine.tick_count,
                    "resonance": self.engine.resonance_phase,
                    "fields": self.engine.fields,
                    "particles": len(self.engine.particles),
                    "timestamp": datetime.utcnow().isoformat()
                })
                time.sleep(0.25)
            self._lock_resonance(stage)
            if stage >= 100:
                self.engine.log_event("✅ Warp-ready resonance achieved (100k).")
                break

    # =========================
    # 📡 DRIFT & STABILITY MGMT
    # =========================
    def _sync_and_damp(self):
        """Dual-engine sync and SQI drift stabilization."""
        if self.engine_b:
            sync_engines(self.engine, self.engine_b)
        drift = max(self.engine.resonance_filtered[-20:], default=0) - min(self.engine.resonance_filtered[-20:], default=0)
        # ✅ FIX: Use HyperdriveTuningConstants
        if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
            apply_drift_damping(drift, self.engine.fields)
            self.engine.log_event(f"🛠 Drift damped: Δ={drift:.4f}")

    def engage_feedback(self):
        self.engine.sqi_enabled = True
        self.engine.log_event("🧠 SQI feedback engaged.")

    # =========================
    # 💾 PROFILE + PRESETS
    # =========================
    def _load_presets(self):
        if os.path.exists(CONTROL_PRESETS):
            with open(CONTROL_PRESETS, "r") as f:
                return json.load(f)
        return {}

    def apply_preset(self, preset_name):
        """Apply harmonic + field preset by name."""
        if preset_name not in self.presets:
            return
        preset = self.presets[preset_name]

        # ✅ Unpack nested fields properly
        fields = preset.get("fields", {})
        self.adjust_fields(
            gravity=fields.get("gravity"),
            magnetism=fields.get("magnetism"),
            wave_frequency=fields.get("wave_frequency"),
            field_pressure=fields.get("field_pressure")
        )

        # ✅ Apply harmonics if defined
        if "harmonic_gain" in preset:
            self.adjust_harmonics(gain=preset["harmonic_gain"])

        self.engine.log_event(f"📂 Preset '{preset_name}' applied: {preset}")

    def _load_profile(self):
        if os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, "r") as f:
                return json.load(f)
        return {str(t): {"resonance": t, "pulse": None, "drift": None, "noise": []} for t in [50, 85, 90, 95, 99, 100]}

    def _lock_resonance(self, target):
        profile_key = str(target)
        if profile_key not in self.resonance_profile:
            self.resonance_profile[profile_key] = {"resonance": None, "pulse": None, "drift": None, "noise": []}

        profile = self.resonance_profile[profile_key]
        profile["resonance"] = round(self.engine.resonance_filtered[-1], 4) if self.engine.resonance_filtered else target
        profile["pulse"] = getattr(self.engine, "pulse_width", 0.02)
        profile["drift"] = random.uniform(0.0001, 0.001)
        profile["noise"].append(getattr(self.engine, "noise_level", 0.005))
        if len(profile["noise"]) > 5:
            profile["noise"] = profile["noise"][-5:]
        os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
        with open(PROFILE_FILE, "w") as f:
            json.dump(self.resonance_profile, f, indent=4)
        self.engine.log_event(f"✅ Resonance locked: {target}%")

    # =========================
    # 🎛 NOISE INJECTION
    # =========================
    def _inject_noise(self):
        if hasattr(self.engine, "fields"):
            noise = random.uniform(-0.002, 0.002)
            self.engine.fields["wave_frequency"] += noise
            self.engine.log_event(f"🌐 Noise injected: Δwave={noise:+.5f}")