# ──────────────────────────────────────────────────────────────
#  Tessaris * AION Cognitive Dispatcher (v3)
#  Unified semantic routing layer for consciousness engines.
#  Uses LLM or Quantum Atom classification for adaptive routing.
# ──────────────────────────────────────────────────────────────

import asyncio
import logging
from typing import Any, Dict

# ─── Core Integrations ──────────────────────────────────────────────
from backend.modules.holograms.morphic_ledger import MorphicLedger
from backend.modules.dna_chain.dna_autopilot import monitor_self_growth, is_self_growth_enabled

# ─── Consciousness (Cognition + Awareness) ──────────────────────────────
from backend.modules.consciousness.context_engine import ContextEngine
from backend.modules.consciousness.decision_engine import DecisionEngine
from backend.modules.consciousness.planning_engine import PlanningEngine
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.consciousness.logic_prediction_utils import LogicPredictionUtils
from backend.modules.aion_reflection.reflection_engine import ReflectionEngine
from backend.modules.aion.recursive_learner import RecursiveLearner
from backend.modules.aion.rewrite_engine import RewriteEngine
from backend.modules.consciousness.awareness_engine import AwarenessEngine
from backend.modules.consciousness.consciousness_manager import ConsciousnessManager
from backend.modules.consciousness.identity_engine import IdentityEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.consciousness.situational_engine import SituationalEngine

# ─── Avatar / Dream Interfaces ──────────────────────────────────────
from backend.modules.avatar.avatar_core import AIONAvatar
from backend.modules.aion.dream_core import DreamCore

# ─── Symbolic / Gradient Systems ────────────────────────────────────
from backend.modules.consciousness.symbolic_gradient_engine import SymbolicGradientEngine
from backend.modules.consciousness.gradient_entanglement_adapter import GradientEntanglementAdapter
from backend.modules.consciousness.qglyph_loop_runner import QGlyphLoopRunner

# ─── Emotion & Ethics ───────────────────────────────────────────────
from backend.modules.consciousness.emotion_engine import EmotionEngine
from backend.modules.consciousness.ethics_engine import EthicsEngine
from backend.modules.consciousness.energy_engine import EnergyEngine

# ─── Goals & Tasks ─────────────────────────────────────────────────
from backend.modules.consciousness.goal_task_manager import GoalTaskManager
from backend.modules.aion.goal_handler import GoalHandler

# ─── Memory & Learning ─────────────────────────────────────────────
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.consciousness.memory_bridge import MemoryBridge
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.consciousness.time_engine import TimeEngine

# ─── Safety / DNA / Control ────────────────────────────────────────
from backend.modules.consciousness.privacy_vault import PrivacyVault
from backend.modules.dna_chain.switchboard import DNA_SWITCH

logger = logging.getLogger("CognitiveDispatcher")


# ──────────────────────────────────────────────────────────────
#  AION Cognitive Dispatcher (v3 Quantum-Ready)
# ──────────────────────────────────────────────────────────────
class CognitiveDispatcher:
    """
    The AION Cognitive Dispatcher orchestrates all consciousness subsystems.
    It semantically routes intents using an LLM (or Quantum Atom) classifier.
    """

    def __init__(self, llm_classifier=None, quantum_atom=None):
        self.llm = llm_classifier
        self.quantum_atom = quantum_atom  # optional symbolic classifier
        self.logger = logger
        self.ledger = MorphicLedger()
        from backend.modules.hexcore.governed_cognitive_stack import GovernedCognitiveStack
        self.governed_stack = GovernedCognitiveStack()

        # ─── Engine Groups ─────────────────────────────────────
        # Ensure situational engine is created first
        situational = SituationalEngine()

        self.cognition = {
            "context": ContextEngine(),
            "decision": DecisionEngine(situational),  # ✅ inject required dependency
            "planning": PlanningEngine(),
            "prediction": PredictionEngine(),
            "logic": LogicPredictionUtils(),
            "reflection": ReflectionEngine(),
            "recursion": RecursiveLearner(),
            "rewrite": RewriteEngine(),
        }

        # Optionally make situational engine visible to awareness systems
        self.awareness = {
            "situational": situational,
            "awareness": AwarenessEngine(),
            "consciousness": ConsciousnessManager(),
            "identity": IdentityEngine(),
            "personality": PersonalityProfile(),
            "avatar": AIONAvatar(),
            "dream": DreamCore(),
        }

        self.symbolic = {
            "gradient": SymbolicGradientEngine(),
            "entanglement": GradientEntanglementAdapter(),
            "qglyph": QGlyphLoopRunner(),
        }

        self.emotion = {
            "emotion": EmotionEngine(),
            "ethics": EthicsEngine(),
            "energy": EnergyEngine(),
        }

        self.goals = {
            "goal_task": GoalTaskManager(),
            "goal_handler": GoalHandler(agent_name="AION"),
        }

        self.memory = {
            "memory": MemoryEngine(),
            "bridge": MemoryBridge(container_id="aion_start"),
            "state": StateManager(),
            "time": TimeEngine(),
        }

        self.safety = {
            "privacy": PrivacyVault(),
            "dna": DNA_SWITCH,
        }

        # 🧬 Enable self-growth monitoring if allowed
        try:
            if is_self_growth_enabled("dispatcher"):
                asyncio.create_task(monitor_self_growth(self))
        except Exception as e:
            self.logger.debug(f"[Dispatcher] Self-growth monitor unavailable: {e}")

        self.logger.info("✅ AION CognitiveDispatcher (v3) initialized with full consciousness stack.")

    # ──────────────────────────────────────────────────────────────
    async def execute(self, intent: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify the semantic intent using LLM or Quantum Atom and
        route the task to the proper consciousness subsystem.
        """
        try:
            # Broad missions always enter through competence, ethics,
            # metacognition and authority checks before specialist routing.
            if payload.get("objective") or payload.get("goal") or payload.get("broad_mission"):
                deliberation = await asyncio.to_thread(
                    self.governed_stack.deliberate,
                    {**payload, "objective": payload.get("objective") or payload.get("goal") or intent},
                )
                if payload.get("deliberate_only", True):
                    return deliberation
                return await asyncio.to_thread(
                    self.governed_stack.execute,
                    deliberation,
                    execution_adapter=payload.get("execution_adapter"),
                )
            tag = await self._classify_intent(intent)
            self.logger.info(f"[Dispatcher] Intent classified -> {tag}")

            # ─── Core Routing Logic ───────────────────────────
            # Cognition
            if "predict" in tag:
                return await self._safe_run(self.cognition["prediction"], payload)
            if "plan" in tag:
                return await self._safe_run(self.cognition["planning"], payload)
            if "reflect" in tag or "analyze" in tag:
                return await self._safe_run(self.cognition["reflection"], payload)
            if "rewrite" in tag:
                return await self._safe_run(self.cognition["rewrite"], payload)
            if "learn" in tag or "recursion" in tag:
                return await self._safe_run(self.cognition["recursion"], payload)
            if "logic" in tag:
                return await self._safe_run(self.cognition["logic"], payload)

            # Awareness / Consciousness
            if "dream" in tag:
                return await self._safe_run(self.awareness["dream"], payload)
            if "identity" in tag:
                return await self._safe_run(self.awareness["identity"], payload)
            if "avatar" in tag:
                return await self._safe_run(self.awareness["avatar"], payload)
            if "conscious" in tag or "awareness" in tag:
                return await self._safe_run(self.awareness["consciousness"], payload)

            # Symbolic / Gradient
            if "gradient" in tag or "entangle" in tag:
                return await self._safe_run(self.symbolic["gradient"], payload)
            if "qglyph" in tag or "symbol" in tag:
                return await self._safe_run(self.symbolic["qglyph"], payload)

            # Emotion / Ethics / Energy
            if "emotion" in tag or "mood" in tag:
                return await self._safe_run(self.emotion["emotion"], payload)
            if "ethic" in tag or "moral" in tag:
                return await self._safe_run(self.emotion["ethics"], payload)
            if "energy" in tag:
                return await self._safe_run(self.emotion["energy"], payload)

            # Goals & Memory
            if "goal" in tag:
                return await self._safe_run(self.goals["goal_task"], payload)
            if "memory" in tag:
                return await self._safe_run(self.memory["memory"], payload)
            if "time" in tag:
                return await self._safe_run(self.memory["time"], payload)

            # Safety / Privacy
            if "privacy" in tag or "secure" in tag:
                return await self._safe_run(self.safety["privacy"], payload)

            # Fallback
            self.logger.warning(f"[Dispatcher] No matching engine found for: {intent}")
            return {"status": "no_match", "intent": intent, "tag": tag}

        except Exception as e:
            self.logger.error(f"[Dispatcher] Execution failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    # ──────────────────────────────────────────────────────────────
    async def _classify_intent(self, intent: str) -> str:
        """
        Classifies an intent using the LLM, or falls back to Quantum Atom.
        """
        try:
            if self.llm:
                return await self.llm.classify_intent(intent)
            elif self.quantum_atom:
                # Quantum Atom fallback: use resonance pattern matching
                return await self.quantum_atom.resonate_intent(intent)
            else:
                # Default symbolic heuristic
                return "reflect" if "think" in intent else "plan"
        except Exception as e:
            self.logger.warning(f"[Dispatcher] Intent classification fallback: {e}")
            return "reflect"

    # ──────────────────────────────────────────────────────────────
    async def _safe_run(self, engine, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run any engine safely with async/await and ledger trace.
        """
        try:
            # Detect coroutine vs threadable call
            if asyncio.iscoroutinefunction(getattr(engine, "run", None)):
                result = await engine.run(payload)
            elif hasattr(engine, "run"):
                result = await asyncio.to_thread(engine.run, payload)
            elif hasattr(engine, "process"):
                result = await asyncio.to_thread(engine.process, payload)
            elif hasattr(engine, "execute"):
                result = await asyncio.to_thread(engine.execute, payload)
            else:
                raise AttributeError("No callable entrypoint found in engine.")

            # Record to Morphic Ledger
            try:
                self.ledger.record({
                    "timestamp": asyncio.get_event_loop().time(),
                    "engine": engine.__class__.__name__,
                    "payload": payload,
                    "result": result,
                })
            except Exception:
                pass

            return {
                "status": "ok",
                "engine": engine.__class__.__name__,
                "result": result,
            }

        except Exception as e:
            self.logger.error(f"[Dispatcher] Engine {engine.__class__.__name__} failed: {e}")
            return {"status": "error", "engine": engine.__class__.__name__, "error": str(e)}
