# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/hyperdrive_auto_tuner_module.py

import os
import json
from copy import deepcopy
from datetime import datetime

# ✅ Updated import to use HyperdriveTuningConstants (no old hyperdrive_constants)
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_feedback_module import run_sqi_feedback


class HyperdriveAutoTuner:
    """
    🔧 Hyperdrive Auto-Tuner (Unified)
    ----------------------------------
    • ECU-aligned SQI resonance tuner w/ staged warm-up & safety guards.
    • SQI feedback, drift-based corrections, and runtime persistence.
    • Exports resonance traces + stabilized engine .dc snapshots.
    """

    def __init__(self, engine):
        self.engine = engine
        self.sqi_cooldown = 0
        self.logger = TelemetryLogger(log_dir="data/qwave_logs")

    def tune(self, iterations: int = 50, warmup_ticks: int = 50):
        """Run warm-up, then iterative SQI tuning with ECU-aligned drift checks."""
        print(f"🔥 Preheating engine for {warmup_ticks} baseline ticks...")
        for _ in range(warmup_ticks):
            self._tick_engine()

        # 🧠 SQI Feedback Warmup Sequence
        self._sqi_feedback_warmup()

        for i in range(iterations):
            print(f"\n🔄 Auto-Tune Iteration {i+1}/{iterations}")
            self.engine.run_simulation(duration=8)
            self._tick_engine(ecu_sync=True)

            drift = self._get_current_drift()
            stability = self._evaluate_stability()
            thermal = getattr(self.engine, "thermal_load", 0.0)
            power = getattr(self.engine, "power_draw", 0.0)

            print(f"📈 Drift={drift:.4f} | Stability={stability:.4f} | Thermal={thermal:.1f}°C | Power={power:.0f}W")

            # 🔥 Safety guards using HyperdriveTuningConstants
            if thermal > HyperdriveTuningConstants.THERMAL_MAX * 0.95 or power > HyperdriveTuningConstants.POWER_MAX * 0.95:
                print(f"🔥 Safety Hold: Thermal/Power near limit. SQI paused.")
                self.sqi_cooldown += 2
                continue

            # ✅ Auto-reactivate SQI if drift spike
            if not getattr(self.engine, "sqi_enabled", False) and drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD * 1.2:
                print("🔄 Auto-reactivating SQI: Drift spike detected.")
                self.engine.sqi_enabled = True

            # ✅ SQI trigger
            if drift > (HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD * 0.8) and self.sqi_cooldown == 0:
                if self.engine.sqi_enabled:
                    print(f"⚠ SQI triggered: Drift={drift:.3f}")
                    run_sqi_feedback(self.engine)
                    self._apply_sqi_persistence()
                    self.sqi_cooldown = 3
                    self.engine.pending_sqi_ticks = 10
                else:
                    print(f"🛑 SQI disabled: Drift={drift:.3f}, skipping correction.")
            else:
                print(f"✅ SQI skipped (Cooldown={self.sqi_cooldown})")

            # ✅ Stability check & pulse detection
            if self._check_pulse_and_stability(stability):
                break

            # ✅ Cooldown decrement
            if self.sqi_cooldown > 0:
                self.sqi_cooldown = max(0, self.sqi_cooldown - (2 if drift < (HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD * 0.6) else 1))

            # Log telemetry
            self.logger.log({
                "iteration": i + 1,
                "drift": drift,
                "thermal": thermal,
                "power": power,
                "stability": stability,
                "sqi_enabled": getattr(self.engine, "sqi_enabled", False),
                "cooldown": self.sqi_cooldown,
                "timestamp": datetime.utcnow().isoformat()
            })

    # ============================================================
    # 🧠 SQI Feedback Warmup (NEW)
    # ============================================================
    def _sqi_feedback_warmup(self):
        """🧠 Pre-tuning SQI feedback pulse sequence to break initial stagnation."""
        print("🧠 SQI Feedback Warmup Sequence (6 cycles)")
        for i in range(6):
            print(f"🌀 Warmup Cycle {i + 1}/6")
            if hasattr(self.engine, "_run_sqi_feedback"):
                self.engine._run_sqi_feedback()
            if hasattr(self.engine, "_inject_noise"):
                self.engine._inject_noise()
            if hasattr(self.engine, "_sync_and_damp"):
                self.engine._sync_and_damp()
            self.engine.tick()
            if hasattr(self.engine, "_break_stagnation"):
                self.engine._break_stagnation()

            self.logger.log({
                "phase": "warmup",
                "cycle": i + 1,
                "tick": getattr(self.engine, "tick_count", 0),
                "timestamp": datetime.utcnow().isoformat()
            })

            try:
                import time
                time.sleep(0.3)
            except Exception:
                pass

    # ============================================================
    # 🔑 INTERNAL HELPERS
    # ============================================================
    def _tick_engine(self, ecu_sync=False):
        """Tick engine and optionally sync with ECU tick rate."""
        if hasattr(self.engine, "tick"):
            self.engine.tick()
            if ecu_sync:
                for _ in range(int(getattr(self.engine, "tick_rate", 10000) * 0.001)):
                    self.engine.tick()
        elif hasattr(self.engine, "run_simulation"):
            self.engine.run_simulation(duration=1)

    def _apply_sqi_persistence(self):
        """Apply SQI adjustments to runtime constants and persist."""
        adjustments = getattr(self.engine, "last_sqi_adjustments", {})
        if adjustments:
            print(f"💾 Persisting SQI adjustments: {adjustments}")
            HyperdriveTuningConstants.apply_sqi_adjustments(adjustments)

    def _check_pulse_and_stability(self, stability: float) -> bool:
        """Pulse detection & final export."""
        if stability >= 0.95 and getattr(self.engine, "tick_count", 0) > 200:
            print(f"🫀 Pulse detected: Engine stabilized (Score={stability:.3f})")
            self._generate_report()
            self._export_final_snapshot()
            return True
        if stability >= 0.9:
            print(f"🫀 Pulse detected: Engine resonance stable (Score={stability:.3f})")
        if stability >= 0.95:
            print("✅ Stability target reached. Auto-tuning complete.")
            self._generate_report()
            self._export_final_snapshot()
            return True
        return False

    def _evaluate_stability(self) -> float:
        """ECU-aligned drift window stability score."""
        if not self.engine.resonance_filtered:
            return 0.0
        window = self.engine.resonance_filtered[-30:]
        drift = max(window) - min(window)
        score = max(0.0, 1.0 - min(drift / 10.0, 1.0))
        if getattr(self.engine, "last_sqi_adjustments", None):
            score = min(1.0, score + 0.05)
        return score

    def _get_current_drift(self) -> float:
        """ECU-aligned drift calculation."""
        if not self.engine.resonance_filtered:
            return 0.0
        window = self.engine.resonance_filtered[-30:]
        return max(window) - min(window)

    # ============================================================
    # ⚡ NEW: DYNAMIC ADJUST
    # ============================================================
    @staticmethod
    def dynamic_adjust(engine, coherence: float):
        """
        ⚡ Dynamic harmonic auto-adjustment based on real-time coherence.
        Called by simulate_virtual_exhaust() every tick.
        """
        print(f"🎚 [AutoTuner] Dynamic adjust triggered: coherence={coherence:.3f}")

        # If coherence is low, boost harmonic gain slightly
        if coherence < 0.7:
            old_gain = engine.fields.get("wave_frequency", 1.0)
            new_gain = old_gain * 1.05
            engine.fields["wave_frequency"] = new_gain
            print(f"⚠ Low coherence ({coherence:.3f}) → boosted wave freq from {old_gain:.3f} to {new_gain:.3f}")
            engine._resync_harmonics()

        # If coherence is high, stabilize damping slightly
        elif coherence > 0.9:
            old_damping = engine.damping_factor
            engine.damping_factor *= 0.98
            print(f"✅ High coherence ({coherence:.3f}) → reduced damping from {old_damping:.4f} to {engine.damping_factor:.4f}")

        # Log adjustment event
        engine.log_event(f"AutoTuner adjusted engine for coherence={coherence:.3f}")

    # ============================================================
    # 📦 EXPORTS
    # ============================================================
    def _generate_report(self):
        """Print tuning summary & save trace."""
        print("\n📊 === Hyperdrive Auto-Tune Report ===")
        print(f"🔧 Final Fields: {json.dumps(self.engine.fields, indent=2)}")
        print(f"🎯 Best Score: {getattr(self.engine, 'best_score', 'N/A')}")
        print(f"📡 Particles: {len(self.engine.particles)}")
        print(f"🎶 Final Stage: {self.engine.stages[self.engine.current_stage]}")
        print(f"⚛ SQI Enabled: {self.engine.sqi_enabled}")
        drift = max(self.engine.resonance_filtered[-50:]) - min(self.engine.resonance_filtered[-50:]) if self.engine.resonance_filtered else 0.0
        print(f"📈 Final Drift: {drift:.6f}")

        trace_dir = "data/hyperdrive_logs"
        os.makedirs(trace_dir, exist_ok=True)
        trace_path = os.path.join(trace_dir, f"resonance_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(trace_path, "w") as f:
            json.dump(self.engine.resonance_filtered[-200:], f, indent=2)
        print(f"📑 Resonance trace saved → {trace_path}")

    def _export_final_snapshot(self):
        """Save stabilized engine state to .dc.json snapshot."""
        snapshot_dir = "data/hyperdrive_logs"
        os.makedirs(snapshot_dir, exist_ok=True)
        report_path = os.path.join(snapshot_dir, f"final_tuning_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dc.json")
        snapshot = {
            "fields": deepcopy(self.engine.fields),
            "timestamp": datetime.utcnow().isoformat(),
            "stage": self.engine.stages[self.engine.current_stage],
            "particles": len(self.engine.particles),
            "score": getattr(self.engine, "best_score", 0.0),
            "sqi_enabled": self.engine.sqi_enabled,
            "resonance": self.engine.resonance_filtered[-50:] if self.engine.resonance_filtered else []
        }
        with open(report_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        print(f"📦 Final tuning snapshot exported → {report_path}")