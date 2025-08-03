# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/sqi_reasoning_module.py

from typing import Dict, Any
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_controller_module import SQIController

class SQIReasoningEngine:
    """
    Symbolic Quantum Intelligence (SQI) Reasoning Engine:
    - Analyzes resonance & exhaust traces
    - Suggests drift, exhaust, harmonic corrections, and control preset sync
    - Stage-aware tuning logic with SQI hard stop & live feedback hooks
    """

    def __init__(
        self,
        target_resonance_drift: float = 0.5,
        target_exhaust_speed: float = 250.0,
        enabled: bool = True,
        controller: SQIController = None   # ✅ Optional SQI controller for preset sync
    ):
        self.target_resonance_drift = target_resonance_drift
        self.target_exhaust_speed = target_exhaust_speed
        self.enabled = enabled
        self.last_drift = None
        self.last_exhaust = None
        self.controller = controller  # ✅ Link to SQI Controller (for preset sync)
        self.analysis_history = []    # ✅ New: Keep last N analyses

    # -------------------------
    # 🧠 TRACE ANALYSIS
    # -------------------------
    def analyze_trace(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            print("🛑 [SQI] Disabled: Skipping analysis.")
            return {"drift": 0.0, "drift_trend": "—", "avg_exhaust": 0.0, "fields": trace.get("fields", {})}

        resonance = trace.get("resonance", [])
        fields = trace.get("fields", {})
        exhaust = trace.get("exhaust", [])
        stage = trace.get("stage", None)

        drift = (max(resonance) - min(resonance)) if resonance else 0.0
        avg_exhaust = sum(exhaust) / len(exhaust) if exhaust else 0.0
        drift_trend = None

        if self.last_drift is not None:
            drift_trend = "↑" if drift > self.last_drift else "↓" if drift < self.last_drift else "→"

        print(f"🧠 [SQI] Stage={stage or 'N/A'} | Drift={drift:.3f} ({drift_trend or '—'}) | Exhaust={avg_exhaust:.2f}")

        self.last_drift = drift
        self.last_exhaust = avg_exhaust

        # ✅ Save history for visualization/debug
        self.analysis_history.append({
            "drift": drift,
            "trend": drift_trend,
            "exhaust": avg_exhaust,
            "stage": stage
        })
        if len(self.analysis_history) > 20:
            self.analysis_history.pop(0)

        return {"drift": drift, "drift_trend": drift_trend, "avg_exhaust": avg_exhaust, "fields": fields, "stage": stage}

    # -------------------------
    # 🔧 ADJUSTMENT RECOMMENDER
    # -------------------------
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

        # ✅ Stage baseline frequency
        stage_baseline_freq = STAGE_CONFIGS.get(stage, {}).get("wave_frequency", fields.get("wave_frequency", 1.0))

        # -------------------------
        # ⚖️ DRIFT MANAGEMENT
        # -------------------------
        if drift > self.target_resonance_drift:
            if drift > (self.target_resonance_drift * 3):  
                # 🚨 HARD FAILSAFE: Auto harmonic resync + preset sync
                print(f"🚨 [SQI] Critical drift ({drift:.3f})! Forcing harmonic resync & preset injection.")
                if self.controller:
                    self.controller.apply_preset("95%")  # Example failsafe preset
                    self.controller.engine._resync_harmonics()

            elif drift > (self.target_resonance_drift * 2):  # Heavy drift
                factor = 0.97 if drift_trend == "↑" else 0.99
                new_freq = max(stage_baseline_freq * 0.8, fields["wave_frequency"] * factor)
                adjustments["wave_frequency"] = new_freq
                adjustments["magnetism"] = fields["magnetism"] * factor
                print(f"⚠️ SQI: Heavy drift detected (Stage={stage}) → Freq={new_freq:.3f}, Magnetism scaled.")
            elif drift_trend == "↑":  # Minor drift rise
                print(f"⚠️ SQI: Minor drift rising (Stage={stage}) → Holding (dead zone).")
            else:
                # Drift falling but still above target: gentle correction
                factor = 0.995
                adjustments["wave_frequency"] = fields["wave_frequency"] * factor

        elif drift < (self.target_resonance_drift * 0.5) and drift_trend == "↓":
            # Over-correction recovery: gently boost frequency back up
            boost = 1.003
            adjustments["wave_frequency"] = fields["wave_frequency"] * boost
            print(f"✅ SQI: Drift stable and falling, gentle boost applied (Freq x{boost:.3f}).")

        # -------------------------
        # 🌬 EXHAUST BALANCING (Gravity linked)
        # -------------------------
        if avg_exhaust < self.target_exhaust_speed * 0.9:
            adjustments["gravity"] = fields["gravity"] * 1.02  # Boost thrust
        elif avg_exhaust > self.target_exhaust_speed * 1.2:
            adjustments["gravity"] = fields["gravity"] * 0.97  # Reduce excess thrust

        # -------------------------
        # 🎶 HARMONIC FEEDBACK
        # -------------------------
        dynamic_drift_threshold = drift * 1.2 if drift > 0 else self.target_resonance_drift
        set_harmonic_gain(1.0 if drift < self.target_resonance_drift else 0.9)
        set_decay_rate(0.999 if drift_trend == "↓" else 0.995)
        set_damping_factor(0.98 if drift > self.target_resonance_drift else 1.0)
        set_resonance_threshold(dynamic_drift_threshold)

        print(f"🎶 [SQI] Harmonics tuned: Gain={1.0 if drift < self.target_resonance_drift else 0.9}, Decay adjusted.")

        # -------------------------
        # 🔗 CONTROL PRESET SYNC (NEW)
        # -------------------------
        if self.controller and drift <= self.target_resonance_drift:
            preset_name = f"{min(int(drift / self.target_resonance_drift * 100), 100)}%"
            print(f"📡 [SQI] Syncing control preset: {preset_name}")
            self.controller.apply_preset(preset_name)

        # -------------------------
        # 🔮 FINAL OUTPUT
        # -------------------------
        print(f"🔮 [SQI] Recommended Adjustments: {adjustments if adjustments else 'None'}")
        return adjustments