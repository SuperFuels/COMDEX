import datetime
import logging
from typing import Dict, Any
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_controller_module import SQIController
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update
from backend.modules.visualization.glyph_to_qfc import to_qfc_payload

logger = logging.getLogger(__name__)
SQI_EVENT_LOG = []

# ✅ SQI Drift Logger Function (used for GHX + HUD overlays)
def log_sqi_drift(container_id: str, beam_id: str, glow: float, frequency: float):
    print(f"[SQI] Drift beam {beam_id} in {container_id} -> glow={glow:.2f}, pulse={frequency:.2f}Hz")

# Optional: Provide a dummy broadcast function if GHX not connected
def broadcast_ghx_event(event: Dict):
    pass  # Or leave unimplemented if not in scope

class SQIReasoningEngine:
    """
    Symbolic Quantum Intelligence (SQI) Reasoning Engine:
    - Analyzes resonance & exhaust traces
    - Suggests drift, exhaust, harmonic corrections, and control preset sync
    - Stage-aware tuning logic with SQI hard stop & live feedback hooks
    """

    def __init__(
        self,
        engine=None,
        target_resonance_drift: float = 0.5,
        target_exhaust_speed: float = 250.0,
        enabled: bool = True,
        controller: SQIController = None
    ):
        self.engine = engine
        self.target_resonance_drift = target_resonance_drift
        self.target_exhaust_speed = target_exhaust_speed
        self.enabled = enabled
        self.last_drift = None
        self.last_exhaust = None
        self.controller = controller
        self.analysis_history = []

    # -------------------------
    # 🧠 TRACE ANALYSIS
    # -------------------------
    def analyze_trace(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            print("🛑 [SQI] Disabled: Skipping analysis.")
            return {
                "drift": 0.0,
                "drift_trend": "-",
                "avg_exhaust": 0.0,
                "fields": trace.get("fields", {}),
            }

        resonance = trace.get("resonance", [])
        fields = trace.get("fields", {})
        exhaust = trace.get("exhaust", [])
        stage = trace.get("stage", None)

        drift = (max(resonance) - min(resonance)) if resonance else 0.0
        avg_exhaust = sum(exhaust) / len(exhaust) if exhaust else 0.0

        drift_trend = None
        if self.last_drift is not None:
            drift_trend = "↑" if drift > self.last_drift else "↓" if drift < self.last_drift else "->"

        print(f"🧠 [SQI] Stage={stage or 'N/A'} | Drift={drift:.3f} ({drift_trend or '-'}) | Exhaust={avg_exhaust:.2f}")

        self.last_drift = drift
        self.last_exhaust = avg_exhaust

        self.analysis_history.append({
            "drift": drift,
            "trend": drift_trend,
            "exhaust": avg_exhaust,
            "stage": stage
        })
        if len(self.analysis_history) > 20:
            self.analysis_history.pop(0)

        # ---------------------------------------
        # 🌟 INNOVATION SCORING + HUD Streaming
        # ---------------------------------------
        try:
            from backend.modules.creative.innovation_scorer import InnovationScorer
            scorer = InnovationScorer()
            symbolic_tree = trace.get("symbolnet", {})  # Use symbolnet as proxy
            innovation_score = scorer.compute_innovation_score(symbolic_tree)
            print(f"🌟 [SQI] Innovation Score: {innovation_score:.3f}")

            # Embed in return payload
            enriched["innovation_score"] = innovation_score

            # Broadcast to GHX / HUD
            broadcast_ghx_event({
                "type": "sqi_metric",
                "metric": "innovation_score",
                "value": innovation_score,
                "beam_id": beam_id,
                "container_id": container_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"⚠️ [SQI] Innovation scoring failed: {e}")

        # ---------------------------------------
        # 📡 Optional Metadata: container/beam
        # ---------------------------------------
        container_id = trace.get("container_id", "N/A")
        beam_id = trace.get("beam_id", "unknown")

        # ---------------------------------------
        # 🪩 Log Drift -> Glow = drift, Pulse = exhaust
        # ---------------------------------------
        try:
            log_sqi_drift(container_id=container_id, beam_id=beam_id, glow=drift, frequency=avg_exhaust)
        except Exception as e:
            print(f"[SQI] Failed to log drift: {e}")

        # Return initial analysis (symbolic overlay follows later)
        enriched = {
            "drift": drift,
            "drift_trend": drift_trend,
            "avg_exhaust": avg_exhaust,
            "fields": fields,
            "stage": stage,
            "semantic_score": avg_match,
            "semantic_distance": avg_dist,
            "symbolnet": semantic_scores
        }
        # ---------------------------------------
        # 🧠 SymbolNet Semantic Overlay Analysis
        # ---------------------------------------
        from backend.modules.symbolic.hst.hst_semantic_scoring import concept_match, semantic_distance

        symbolnet = trace.get("symbolnet", {})
        semantic_scores = []

        for glyph_id, meta in symbolnet.items():
            label = meta.get("label")
            if not label:
                continue

            distance = semantic_distance(label, "goal")      # You may make this dynamic
            match_score = concept_match(label, "goal")

            semantic_scores.append({
                "glyph": glyph_id,
                "label": label,
                "distance": distance,
                "match_score": match_score
            })

        avg_match = (
            sum(s["match_score"] for s in semantic_scores) / len(semantic_scores)
            if semantic_scores else 0.0
        )
        avg_dist = (
            sum(s["distance"] for s in semantic_scores) / len(semantic_scores)
            if semantic_scores else 1.0
        )

        print(f"🧠 [SQI] SymbolNet: avg_match={avg_match:.3f}, avg_distance={avg_dist:.3f}")

        # ✅ LIVE QFC BROADCAST (new node for drift/exhaust/symbolnet)
        try:
            node_payload = {
                "glyph": "Σ",
                "op": "collapse",
                "metadata": {
                    "drift": drift,
                    "exhaust": avg_exhaust,
                    "semantic_score": avg_match,
                    "stage": stage,
                    "trace_id": trace.get("trace_id"),
                }
            }

            context = {
                "container_id": trace.get("container_id", "unknown"),
                "source_node": trace.get("beam_id", "origin")
            }

            qfc_payload = to_qfc_payload(node_payload, context)
            import asyncio
            asyncio.create_task(broadcast_qfc_update(context["container_id"], qfc_payload))
        except Exception as qfc_err:
            print(f"[⚠️ SQI->QFC] Failed to broadcast collapse: {qfc_err}")

        # Final enriched analysis object
        return {
            "drift": drift,
            "drift_trend": drift_trend,
            "avg_exhaust": avg_exhaust,
            "fields": fields,
            "stage": stage,
            "semantic_score": avg_match,
            "semantic_distance": avg_dist,
            "symbolnet": semantic_scores
        }

    # -------------------------
    # 🎯 SYMBOLIC NODE SCORING
    # -------------------------
    def score_node(self, node: Any) -> float:
        """
        Scores a SymbolicMeaningTree node based on semantic match to goal.
        Supports both dict and SymbolGlyph node formats.
        """
        if not self.enabled:
            return 0.0

        from backend.modules.symbolic.hst.hst_semantic_scoring import concept_match, semantic_distance

        # Extract label safely from dict or SymbolGlyph
        if isinstance(node, dict):
            label = node.get("label") or node.get("glyph") or ""
        else:
            label = getattr(node, "label", "") or getattr(node, "glyph", "")

        if not isinstance(label, str) or not label.strip():
            return 0.0

        try:
            match = concept_match(label, "goal")  # You can later parameterize "goal"
            dist = semantic_distance(label, "goal")

            score = match * (1.0 - dist)
            print(f"[SQI] Scored node: label='{label}', match={match:.3f}, dist={dist:.3f}, score={score:.3f}")
            return score
        except Exception as e:
            print(f"[SQI] Error scoring node '{label}': {e}")
            return 0.0
    # -------------------------
    # 🔧 ADJUSTMENT RECOMMENDER (FIXED)
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

        # ✅ Stage baseline frequency fix
        stage_baseline_freq = HyperdriveTuningConstants.STAGE_CONFIGS.get(
            stage, {}
        ).get("wave_frequency", fields.get("wave_frequency", 1.0))

        # -------------------------
        # ⚖️ DRIFT MANAGEMENT
        # -------------------------
        if drift > self.target_resonance_drift:
            if drift > (self.target_resonance_drift * 3):
                print(f"🚨 [SQI] Critical drift ({drift:.3f})! Forcing harmonic resync & preset injection.")
                if self.controller:
                    self.controller.apply_preset("95%")
                    if hasattr(self.controller, "engine"):
                        self.controller.engine._resync_harmonics()
            elif drift > (self.target_resonance_drift * 2):
                factor = 0.97 if drift_trend == "↑" else 0.99
                new_freq = max(stage_baseline_freq * 0.8, fields["wave_frequency"] * factor)
                adjustments["wave_frequency"] = new_freq
                adjustments["magnetism"] = fields["magnetism"] * factor
                print(f"⚠️ SQI: Heavy drift detected (Stage={stage}) -> Freq={new_freq:.3f}, Magnetism scaled.")
            elif drift_trend == "↑":
                print(f"⚠️ SQI: Minor drift rising (Stage={stage}) -> Holding (dead zone).")
            else:
                factor = 0.995
                adjustments["wave_frequency"] = fields["wave_frequency"] * factor

        elif drift < (self.target_resonance_drift * 0.5) and drift_trend == "↓":
            boost = 1.003
            adjustments["wave_frequency"] = fields["wave_frequency"] * boost
            print(f"✅ SQI: Drift stable and falling, gentle boost applied (Freq x{boost:.3f}).")

        # -------------------------
        # 🌬 EXHAUST BALANCING
        # -------------------------
        if avg_exhaust < self.target_exhaust_speed * 0.9:
            adjustments["gravity"] = fields["gravity"] * 1.02
        elif avg_exhaust > self.target_exhaust_speed * 1.2:
            adjustments["gravity"] = fields["gravity"] * 0.97

        # -------------------------
        # 🎶 HARMONIC FEEDBACK (REPLACED MISSING FUNCTIONS)
        # -------------------------
        dynamic_drift_threshold = drift * 1.2 if drift > 0 else self.target_resonance_drift
        HyperdriveTuningConstants.HARMONIC_GAIN = 1.0 if drift < self.target_resonance_drift else 0.9
        HyperdriveTuningConstants.DECAY_RATE = 0.999 if drift_trend == "↓" else 0.995
        HyperdriveTuningConstants.DAMPING_FACTOR = 0.98 if drift > self.target_resonance_drift else 1.0
        HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD = dynamic_drift_threshold

        print(f"🎶 [SQI] Harmonics tuned: Gain={HyperdriveTuningConstants.HARMONIC_GAIN:.3f}, "
              f"Decay={HyperdriveTuningConstants.DECAY_RATE:.3f}, "
              f"Damping={HyperdriveTuningConstants.DAMPING_FACTOR:.3f}, "
              f"Drift Threshold={dynamic_drift_threshold:.3f}")

        # -------------------------
        # 🔗 CONTROL PRESET SYNC
        # -------------------------
        if self.controller and drift <= self.target_resonance_drift:
            preset_name = f"{min(int(drift / self.target_resonance_drift * 100), 100)}%"
            print(f"📡 [SQI] Syncing control preset: {preset_name}")
            self.controller.apply_preset(preset_name)

        print(f"🔮 [SQI] Recommended Adjustments: {adjustments if adjustments else 'None'}")
        return adjustments

    # -------------------------
    # 💰 DRIFT COST ESTIMATION
    # -------------------------
    def estimate_drift_cost(self, drift: float, base_cost: float = 1.0) -> float:
        if not isinstance(drift, (int, float)):
            raise ValueError(f"[SQI] Drift must be numeric, got: {type(drift)}")
        drift = max(0.0, min(1.0, drift))
        weight = getattr(self, "drift_weight", 1.0)
        cost = drift * weight * base_cost
        print(f"[SQI] Drift Cost -> Drift={drift:.3f} | Weight={weight:.2f} | Cost={cost:.3f}")
        return cost

def log_sqi_event(event: Dict):
    """
    Log an event into the SQI reasoning engine.

    This is used to track symbolic logic events that contribute to reasoning,
    QKD integrity, collapse triggers, and replay.

    The event dict should include fields like:
    - type
    - timestamp
    - status
    - sender_id / receiver_id
    - collapse_hash
    - fingerprint
    - detail (optional)
    """
    # ✅ Add system timestamp if missing
    if "logged_at" not in event:
        event["logged_at"] = datetime.datetime.now(datetime.UTC).isoformat()

    # ✅ Append to internal log
    SQI_EVENT_LOG.append(event)

    # ✅ Print to log (optional, or make togglable)
    logger.info(f"[SQI_EVENT] {event['type']} - {event.get('status', 'ok')}")

    # ✅ Broadcast to GHX replay if available
    if broadcast_ghx_event:
        broadcast_ghx_event(event)

    # ✅ Future: Add hooks for CodexMetrics, DreamOS, etc.

    return event