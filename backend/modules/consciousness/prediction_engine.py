"""
📄 prediction_engine.py

🔮 Prediction Engine for AION and Symbolic Agents  
Generates symbolic futures, goal-driven forecasts, and timeline branches.
"""

import uuid
import random
import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

from backend.modules.dna_chain.switchboard import DNA_SWITCH
def get_glyph_trace():
    from backend.modules.glyphos.glyph_trace_logger import glyph_trace
    return glyph_trace
from backend.modules.soul.soul_laws import get_soul_laws
from backend.modules.consciousness.symbolic_gradient_engine import SymbolicGradientEngine
from backend.modules.knowledge_graph.glyph_feedback_tracer import GlyphFeedbackTracer
from backend.modules.knowledge_graph.brain_map_streamer import BrainMapStreamer
from backend.modules.glyphos.symbolic_entangler import get_entangled_for
from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore
from backend.modules.consciousness.gradient_entanglement_adapter import GradientEntanglementAdapter
from backend.modules.knowledge_graph.entanglement_fusion import EntanglementFusion
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.codex.codex_metrics import calculate_glyph_cost as estimate_glyph_cost

try:
    from backend.modules.tessaris.tessaris_engine import TessarisEngine
    from backend.modules.dream_core import DreamCore
except ImportError:
    MemoryEngine, TessarisEngine, DreamCore = None, None, None

DNA_SWITCH.register(__file__)

# ✅ Lazy import wrapper
def get_estimate_codex_cost():
    from backend.modules.codex.codex_executor import estimate_codex_cost
    return estimate_codex_cost


class PredictionEngine:
    def __init__(self, container_id: str = "global", memory_engine=None, tessaris_engine=None, dream_core=None):
        self.container_id = container_id
        self.memory_engine = memory_engine or (MemoryEngine() if MemoryEngine else None)
        self.tessaris_engine = tessaris_engine or (TessarisEngine() if TessarisEngine else None)
        self.dream_core = dream_core or (DreamCore() if DreamCore else None)

        self.gradient_engine = SymbolicGradientEngine()
        self.feedback_tracer = GlyphFeedbackTracer(container_id=self.container_id)
        self.entanglement_adapter = GradientEntanglementAdapter()
        self.entanglement_fusion = EntanglementFusion()
        self.brain_streamer = BrainMapStreamer()
        self.quantum_core = GlyphQuantumCore(container_id=self.container_id)
        self.history = []


def run_prediction_on_container(container: dict) -> dict:
    """
    Run prediction logic on a symbolic container.
    Picks optimal paths for atoms, electrons, etc.
    Returns a dictionary of predicted glyph outcomes.
    """
    predictions = {}
    glyphs = container.get("glyphs", [])

    for glyph in glyphs:
        gid = glyph.get("id")
        gtype = glyph.get("type")
        meta = glyph.get("meta", {})
        outcomes = meta.get("predictive_outcomes", [])

        print(f"🔍 Glyph: {gid}, Type: {gtype}, Outcomes: {len(outcomes)}")

        if gtype in ("electron", "atom"):
            if not outcomes:
                logger.warning(f"[Prediction] No candidates found for {gtype} glyph {gid}")
                continue

            best = select_best_prediction(outcomes, context=glyph)
            if best:
                predictions[gid] = {
                    "label": best.get("label", "unknown"),
                    "logic_score": best.get("logic_score", 0),
                    "all_candidates": outcomes,
                    "source_metadata": meta,
                }
                print(f"✅ Best for {gid}: {best.get('label')} [score: {best.get('logic_score', 0)}]")
                logger.info(f"[Prediction] {gid} ({gtype}) → {best.get('label')} [score: {best.get('logic_score', 0)}]")
                CodexTrace.log_prediction(gid, gtype, best)
            else:
                print(f"⚠️ No valid prediction selected for {gid}")
                logger.warning(f"[Prediction] No valid prediction selected for {gid} ({gtype})")

    if container.get("id"):
        print(f"🧠 Writing {len(predictions)} predictions to KG for container: {container['id']}")
        KnowledgeGraphWriter.store_predictions(container["id"], predictions)

    return predictions


def select_best_prediction(outcomes: list, context: dict) -> dict:
    """
    Evaluate list of outcome dicts and choose the most optimal one.
    Applies SQI-inspired logic score, entropy penalty, cost penalty,
    and goal alignment reward.
    """
    scored = []

    for outcome in outcomes:
        glyph = outcome.get("glyph", {})
        logic = outcome.get("logic_score", 0) or 0
        entropy = outcome.get("entropy_delta", 0) or 0
        goal_alignment = outcome.get("goal_score", 0) or 0
        cost = estimate_glyph_cost(glyph) if glyph else 0

        score = (
            (logic * 2.0) -
            (entropy * 1.5) -
            (cost * 0.8) +
            (goal_alignment * 2.5)
        )

        scored.append((score, outcome))

    if not scored:
        logger.warning("[Prediction] No outcomes could be scored. Choosing randomly.")
        return random.choice(outcomes)

    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, best_outcome = scored[0]

    logger.debug(f"[Prediction] Best score: {best_score} for outcome: {best_outcome.get('label', 'N/A')}")
    return best_outcome

    async def forecast_hyperdrive(self, hyperdrive_engine) -> Dict:
        """
        Forecasts symbolic hyperdrive drift, resonance costs, and timeline stability.
        Integrates SQI coherence, drift costs, Codex predictions, entangled KG biasing,
        and optionally injects corrective stabilization glyphs if drift exceeds threshold.
        """
        try:
            # 🧠 Pull core state info
            coherence = getattr(hyperdrive_engine, "coherence", 0.0)
            drift = 1.0 - coherence
            sqi_engine = getattr(hyperdrive_engine, "sqi_engine", None)
            container_id = getattr(hyperdrive_engine, "container_id", "global")

            # 🔍 Estimate drift cost if SQIReasoningEngine supports it
            drift_cost = 1.0
            if sqi_engine and hasattr(sqi_engine, "estimate_drift_cost"):
                drift_cost = sqi_engine.estimate_drift_cost(drift=drift)

            # ✅ Fallback resonance estimate if missing
            resonance_estimate = None
            if sqi_engine and hasattr(sqi_engine, "get_last_prediction"):
                try:
                    last_pred = sqi_engine.get_last_prediction()
                    resonance_estimate = last_pred.get("resonance_estimate") if last_pred else None
                except Exception:
                    resonance_estimate = None
            if resonance_estimate is None:
                # Seed from engine resonance buffer or wave frequency
                if hasattr(hyperdrive_engine, "resonance_filtered") and hyperdrive_engine.resonance_filtered:
                    resonance_estimate = sum(hyperdrive_engine.resonance_filtered[-3:]) / min(3, len(hyperdrive_engine.resonance_filtered))
                else:
                    resonance_estimate = getattr(hyperdrive_engine, "wave_frequency", 1.0)
                print(f"⚠️ Fallback SQI prediction used: resonance_estimate={resonance_estimate:.4f}")

            # 🎯 Predict symbolic correction paths
            current_glyph = getattr(hyperdrive_engine, "current_glyph", "⧖ hyperdrive:tick")
            predictions = await self.generate_future_paths(
                current_glyph=current_glyph,
                container_path=container_id,
                goal="Stabilize Hyperdrive",
                coord="hyperdrive-core",
                emotion="neutral",
                num_paths=2,
                agent_id="hyperdrive"
            )

            # 🔗 Entangled KG Bias: Adjust based on drift
            bias_score = max(0.0, min(1.0, 1.0 - drift))
            await self.entanglement_fusion.propagate_gradient(
                glyph_id=current_glyph,
                gradient_vector={"hyperdrive_bias": bias_score, "drift_cost": drift_cost, "resonance_estimate": resonance_estimate},
                source_agent="hyperdrive"
            )

            # 🛠 Automatic corrective glyph injection if drift is critical
            if drift > 0.6:
                corrective_glyph = f"{current_glyph} ⧖ SQI↺[stabilize]"
                print(f"⚠️ High drift detected ({drift:.2f}) → Injecting corrective glyph: {corrective_glyph}")
                try:
                    from backend.modules.codex.codex_executor import trigger_glyph
                    await trigger_glyph(
                        glyph=corrective_glyph,
                        container_id=container_id,
                        metadata={"origin": "forecast_hyperdrive", "action": "auto_stabilize"}
                    )
                except Exception as e:
                    print(f"⚠️ Corrective glyph injection failed: {e}")

            # 📊 Return structured forecast
            return {
                "coherence": coherence,
                "drift": drift,
                "drift_cost": drift_cost,
                "resonance_estimate": resonance_estimate,  # ✅ Added fallback resonance field
                "predictions": predictions,
                "recommendation": "Boost SQI tuning" if drift > 0.5 else "Stable",
                "auto_injected": drift > 0.6,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            print(f"⚠️ Hyperdrive forecast failed: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    async def generate_future_paths(
        self,
        current_glyph: str,
        container_path: Optional[str] = None,
        goal: Optional[str] = None,
        coord: Optional[str] = None,
        emotion: Optional[str] = None,
        num_paths: int = 3,
        agent_id: str = "local"
    ) -> List[Dict]:
        """Generates symbolic futures with KG rebiasing, collapse feedback, and live streaming."""
        predictions = []
        goal_vector = self._embed_goal(goal)
        entangled_glyphs = get_entangled_for(current_glyph)
        qbit = self.quantum_core.generate_qbit(current_glyph, coord or "unknown")

        estimate_codex_cost = get_estimate_codex_cost()

        for i in range(num_paths):
            future_glyph = self._predict_with_quantum(current_glyph, goal_vector, entangled_glyphs, qbit)
            confidence = self._estimate_confidence(current_glyph, future_glyph, emotion, goal_vector)

            prediction = {
                "id": str(uuid.uuid4()),
                "tick": datetime.now(timezone.utc).isoformat(),
                "input_glyph": current_glyph,
                "predicted_glyph": future_glyph,
                "confidence": confidence,
                "goal": goal,
                "emotion_context": emotion,
                "container_path": container_path,
                "coord": coord,
                "qbit_id": qbit["qbit_id"],
                "qbit_state": qbit["state"],
                "entangled_ancestry": entangled_glyphs,
                "soul_law_violation": self._check_soul_laws(future_glyph),
                "codex_cost_estimate": estimate_codex_cost(future_glyph),
                "is_dream_pattern": self._matches_dream_trace(future_glyph),
                "multiverse_label": "⚛ superposed" if qbit["state"] == "superposed" else ("↔ entangled" if entangled_glyphs else "⧖ linear"),
                "reasoning": f"Path {i+1}: '{future_glyph}' derived via {qbit['state']} (↔ {len(entangled_glyphs)} ancestry links)"
            }

            # 🔴 Weak Prediction Feedback
            if prediction["confidence"] < 0.4:
                self.feedback_tracer.trace_feedback_path(prediction["id"], prediction, "Low confidence forecast")
                await self.gradient_engine._inject_gradient_feedback(prediction, "Low-confidence symbolic prediction")
                self.entanglement_adapter.propagate_gradient_feedback(prediction["id"], "Low-confidence bias")

                # 🌐 Multi-agent gradient sync
                await self.entanglement_fusion.propagate_gradient(
                    glyph_id=prediction["id"],
                    gradient_vector={"low_confidence": prediction["confidence"]},
                    source_agent=agent_id
                )

            # 🌌 Stream live node update
            await self.brain_streamer.stream_node_update(prediction["id"], status="neutral")

            predictions.append(prediction)

        # 🔻 Collapse feedback & recursive optimization
        collapsed = self.quantum_core.collapse_qbit(qbit)
        await self._inject_collapse_feedback(collapsed, current_glyph, goal, container_path, coord, agent_id=agent_id)

        # Store predictions in KG
        try:
            add_prediction_path({
                "input": current_glyph,
                "goal": goal,
                "paths": predictions,
                "qbit_state": collapsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "container_path": container_path,
                "coord": coord,
            })
        except Exception as e:
            print(f"⚠️ Prediction KG injection failed: {e}")

        self.history.extend(predictions)
        return predictions

    async def _inject_collapse_feedback(self, collapsed_qbit: dict, current_glyph: str, goal: str, container_path: str, coord: str, agent_id: str = "local"):
        """Handles collapse bias, streams ripples, triggers recursive re-predictions, and multi-agent sync."""
        try:
            if self.dream_core:
                self.dream_core.reflect_qglyph_collapse(collapsed_qbit)

            await self.gradient_engine.handle_qglyph_collapse(collapsed_qbit, agent_id=agent_id)
            self.entanglement_adapter.propagate_from_collapse(collapsed_qbit)

            qglyph_id = collapsed_qbit.get("selected", {}).get("qbit_id", "unknown")
            await self.entanglement_fusion.fuse_entangled_nodes(
                glyph_id=qglyph_id,
                confidence_delta=+0.05,
                source_agent=agent_id
            )

            await self.brain_streamer.stream_collapse_ripple(collapsed_qbit)

            bias_score = collapsed_qbit.get("observer_bias", {}).get("decision", 0)
            if abs(bias_score) > 0.6:
                print("🔁 Strong collapse bias detected → triggering recursive re-prediction...")
                await self.generate_future_paths(current_glyph, container_path, goal, coord, agent_id=agent_id)

        except Exception as e:
            print(f"⚠️ Collapse feedback failed: {e}")

    # Remaining utility methods unchanged...
    def _predict_with_quantum(self, glyph, goal_vector, entangled, qbit):
        if qbit["state"] == "superposed":
            return f"{glyph} ⚛ ⧖ [superposed fork]"
        elif entangled:
            return f"{glyph} ↔ {random.choice(entangled)}"
        else:
            suffix = random.choice(["→", "⮕", "⋯", "⊕"])
            goal_hint = f"⟦{random.choice(['align','expand','mirror'])}⟧" if goal_vector else "?"
            return f"{glyph} {suffix} {goal_hint}"

    def _embed_goal(self, goal: Optional[str]) -> Optional[List[float]]:
        if not goal or not self.tessaris_engine:
            return None
        try:
            return self.tessaris_engine.embed_text(goal)
        except Exception:
            return None

    def _estimate_confidence(self, input_glyph: str, prediction: str, emotion: Optional[str], goal_vector: Optional[List[float]]) -> float:
        base = 0.5
        if emotion == "positive": base += 0.2
        elif emotion == "negative": base -= 0.2

        if goal_vector and self.tessaris_engine:
            try:
                pred_vector = self.tessaris_engine.embed_text(prediction)
                base += self._cosine_similarity(goal_vector, pred_vector) * 0.3
            except:
                pass

        if self.memory_engine:
            memories = self.memory_engine.search_similar_glyphs(input_glyph, top_k=3)
            if any(m["glyph"] in prediction for m in memories):
                base += 0.1

        return round(min(max(base, 0.0), 1.0), 2)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a ** 2 for a in vec1))
        norm2 = math.sqrt(sum(b ** 2 for b in vec2))
        return dot / (norm1 * norm2 + 1e-8)

    def _check_soul_laws(self, glyph_text: str) -> Optional[Dict]:
        for law in get_soul_laws():
            for trigger in law.get("triggers", []):
                if trigger.lower() in glyph_text.lower():
                    return {"law_id": law["id"], "title": law["title"]}
        return None

    def _matches_dream_trace(self, glyph_text: str) -> bool:
        if not self.dream_core:
            return False
        try:
            past_dreams = self.dream_core.get_recent_dreams(limit=5)
            return any(glyph_text in d.get("summary", "") for d in past_dreams)
        except:
            return False

    def summarize_prediction_trace(self) -> List[str]:
        return [f"{p['input_glyph']} → {p['predicted_glyph']} ({p['confidence']})" for p in self.history]

    def reset_history(self):
        self.history.clear()
# === SQI A2–A5: PredictionEngine for atoms/electrons with SoulLaw ===

try:
    from backend.modules.soullaw.soul_law_validator import get_soul_laws
except ImportError:
    get_soul_laws = lambda: []

class PredictionEngine:
    def __init__(self):
        self.soul_laws = get_soul_laws()

    def run_prediction_on_container(self, container: Dict[str, Any]) -> Dict[str, Any]:
        container_type = container.get("type", "")
        if container_type == "atom":
            return self._predict_atom(container)
        else:
            logger.warning(f"PredictionEngine: Unsupported container type: {container_type}")
            return {}

    def _predict_atom(self, container: Dict[str, Any]) -> Dict[str, Any]:
        electrons = container.get("electrons", [])
        predictions = []

        for idx, electron in enumerate(electrons):
            label = electron.get("meta", {}).get("label", f"e⁻ {idx+1}")
            glyphs = electron.get("glyphs", [])

            if not self._passes_soul_law(glyphs):
                logger.warning(f"⚠️ SoulLaw violation in electron: {label}")
                continue

            best = max(glyphs, key=lambda g: g.get("confidence", 0), default=None)
            if best:
                predictions.append({
                    "electron": label,
                    "selected": best.get("value"),
                    "confidence": best.get("confidence"),
                    "linkContainerId": electron.get("meta", {}).get("linkContainerId")
                })

        return {
            "container_id": container.get("id"),
            "type": "atom",
            "prediction_count": len(predictions),
            "predictions": predictions
        }

    def _passes_soul_law(self, glyphs: List[Dict[str, Any]]) -> bool:
        for glyph in glyphs:
            for law in self.soul_laws:
                if not law.validate(glyph):
                    return False
        return True

# Optional external function (if needed elsewhere)
prediction_engine = PredictionEngine()

def run_prediction_on_container(container: Dict[str, Any]) -> Dict[str, Any]:
    return prediction_engine.run_prediction_on_container(container)
    
__all__ = ["run_prediction_on_container", "select_best_prediction"]