"""
SQI Module:
Inline tick-driven SQI micro-corrections using SQIReasoningEngine.
- Runs alongside tick orchestrator physics/harmonics updates.
- Handles resonance drift corrections every tick.
- Delegates lock/preset control to SQIController if available.
"""

from datetime import datetime
from typing import Optional
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import SQIReasoningEngine
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_controller_module import SQIController


class SQIModule:
    def __init__(self, engine, controller: Optional[SQIController] = None):
        self.engine = engine
        self.sqi_engine = SQIReasoningEngine(engine=engine, controller=controller)
        self.controller = controller
        self.last_tick_adjustments = {}

    def feedback(self):
        """Perform inline SQI drift analysis + micro-adjustments."""
        if not getattr(self.engine, "sqi_enabled", True):
            print("🛑 [SQI Module] SQI disabled, skipping feedback.")
            return

        # Require resonance history for drift analysis
        if not self.engine.resonance_filtered or len(self.engine.resonance_filtered) < 5:
            print("⚠️ [SQI Module] Insufficient resonance data.")
            return

        # Build trace for SQI reasoning
        trace = {
            "resonance": self.engine.resonance_filtered[-50:],
            "fields": self.engine.fields.copy(),
            "exhaust": [e.get("impact_speed", 0) for e in self.engine.exhaust_log[-20:]],
            "stage": getattr(self.engine, "current_stage", None),
        }

        # Run SQI analysis + adjustments
        analysis = self.sqi_engine.analyze_trace(trace)
        adjustments = self.sqi_engine.recommend_adjustments(analysis)

        if not adjustments:
            print("✅ [SQI Module] No micro-adjustments needed.")
            return

        # Apply micro-adjustments to engine fields
        for k, v in adjustments.items():
            if k in self.engine.fields:
                self.engine.fields[k] = (self.engine.fields[k] * 0.7) + (v * 0.3)

        self.last_tick_adjustments = adjustments
        print(f"🔮 [SQI Module] Applied adjustments: {adjustments}")

        # Optionally trigger lock stabilization
        drift = analysis.get("drift", 0.0)
        if drift < self.sqi_engine.target_resonance_drift and self.controller:
            print(f"🔒 [SQI Module] Drift lock detected ({drift:.4f}). Triggering controller lock.")
            self.controller.lock_and_stabilize(drift)