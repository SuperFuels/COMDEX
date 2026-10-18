# ──────────────────────────────────────────────────────────────
#  Tessaris * AION HexCore Consciousness Engine (v3.6)
# ──────────────────────────────────────────────────────────────

import yaml
import time
import uuid
import json
import os
import copy
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import openai
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Core Systems
try:
    from backend.QQC.qqc_central_kernel import QuantumQuadCore
except Exception as e:
    print(f"[HexCore] ⚠️ Failed to import QuantumQuadCore: {e}")
    QuantumQuadCore = None

from backend.modules.holograms.morphic_ledger import MorphicLedger
from backend.modules.skills.voice_interface import VoiceInterface

# ✅ Dispatchers
from backend.modules.hexcore.dispatcher import CognitiveDispatcher as SystemDispatcher
from backend.modules.hexcore.cognitive_dispatcher import CognitiveDispatcher as CognitiveDispatcher
from backend.modules.llm.classifier import LLMClassifier
from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA
from backend.modules.hexcore.hexcore_action_switch import HexCoreActionSwitch
from backend.modules.aion_learning.field_decision_influence_adapter import (
    build_field_decision_influence_update,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
    build_hello_world_engine,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_field_compiler import (
    SymaticsFieldCompiler,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.state_classifier import (
    classify_observed_regime,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_symbol_decoder import (
    SymaticsSymbolDecoder,
)

# ✅ Memory bridge
from backend.modules.hexcore.memory_core import MemoryCore

# ✅ Field bridge
from backend.modules.aion_field.aion_field_control_bridge import AionFieldControlBridge

# ✅ Governed learning / influence runtime
from backend.modules.aion_learning.contracts_decision_influence import DecisionInfluenceUpdate
from backend.modules.aion_learning.decision_influence_runtime import get_decision_influence_runtime
from backend.modules.aion_field.field_operator import FieldOperator
from backend.modules.aion_field.field_actuator import FieldActuator

# ✅ Environment
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger("HexCore")

HEXCORE_DIR = Path(__file__).resolve().parent
SOUL_LAWS_PATH = HEXCORE_DIR / "soul_laws.yaml"
GOVERNANCE_PATH = HEXCORE_DIR / "governance_config.yaml"
MEMORY_PATH = HEXCORE_DIR / "memory.json"

with SOUL_LAWS_PATH.open("r") as f:
    SOUL_LAWS = yaml.safe_load(f)

with GOVERNANCE_PATH.open("r") as f:
    GOVERNANCE = yaml.safe_load(f)


class HexCore:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.birth_time = datetime.now().isoformat()
        self.memory = []
        self.emotion_state = "neutral"
        self.maturity_score = GOVERNANCE.get("maturity", {}).get("level", 0)
        self.parent_key = GOVERNANCE.get("parent", {}).get("public_key")
        self.override_enabled = GOVERNANCE.get("parent", {}).get("override_enabled", False)

        if QuantumQuadCore:
            self.qqc = QuantumQuadCore()
            print("[HexCore] ✅ QuantumQuadCore linked successfully.")
        else:
            self.qqc = None
            print("[HexCore] ⚠️ QuantumQuadCore unavailable.")

        self.morphic_ledger = MorphicLedger()
        self.voice = VoiceInterface()

        from backend.QQC.quantum_atom_classifier import QuantumAtomClassifier
        self.quantum_atom = QuantumAtomClassifier()
        self.llm = LLMClassifier(quantum_atom=self.quantum_atom)

        self.cognitive = CognitiveDispatcher(
            llm_classifier=self.llm,
            quantum_atom=self.quantum_atom
        )

        self.system = SystemDispatcher()

        from backend.modules.tessaris.tessaris_engine import TessarisEngine
        self.tessaris = TessarisEngine(container_id=self.id)

        self.last_phi = 0.0
        self.delta_phi = 0.0
        self.self_awareness = 0.0

        # Cached metrics used by adaptive control
        self.last_coherence = 0.5
        self.last_entropy = 0.5
        self.last_reward = 0.0
        self.last_global_coherence = 0.0
        self.last_field_control: Optional[Dict[str, Any]] = None
        self.last_goal_suggestions: List[str] = []
        self.last_reinforcement: Dict[str, Any] = {}
        self.last_decision_influence_result: Optional[Dict[str, Any]] = None
        self.last_decision_weights_snapshot: Optional[Dict[str, Any]] = None
        self.field_operator = FieldOperator()
        self.last_field_operator: Optional[Dict[str, Any]] = None
        self.field_actuator = FieldActuator()
        self.last_field_actuation: Optional[Dict[str, Any]] = None

        from backend.modules.dna_chain.dna_autopilot import monitor_self_growth
        from backend.modules.dna_chain.dna_switch import is_self_growth_enabled

        self.action_switch = HexCoreActionSwitch()

        if is_self_growth_enabled(self.id):
            asyncio.create_task(monitor_self_growth(self))

        self.memory_core = MemoryCore()

        # Canonical governance shell shared with the conversation runtime.
        # This keeps provider reasoning separate from authority to act or learn.
        from backend.modules.hexcore.governed_runtime import get_hexcore_governed_runtime
        self.governed_runtime = get_hexcore_governed_runtime()
        self.last_action_governance: Optional[Dict[str, Any]] = None

        # Optional field/goals/reinforcement hooks - fail open
        self.goal_engine = self._load_goal_engine()
        self.reinforcement_engine = self._load_reinforcement_engine()
        self.decision_influence_runtime = self._load_decision_influence_runtime()
        self.field_bridge = self._build_field_bridge()
        self.symatics_adapter = self._load_symatics_adapter()
        self.symatics_runtime = self._load_symatics_runtime()
        self.last_symatics_packet: Optional[Dict[str, Any]] = None
        self.last_qqc_summary: Optional[Dict[str, Any]] = None

        print(f"[AION*HexCore] Kernel {self.id[:8]} initialized.")

    # ──────────────────────────────────────────────
    # INTERNAL HELPERS
    # ──────────────────────────────────────────────
    def _load_goal_engine(self):
        try:
            from backend.modules.skills.goal_engine import GOALS
            return GOALS
        except Exception as e:
            logger.debug(f"[HexCore] GoalEngine unavailable: {e}")
            return None

    def _load_reinforcement_engine(self):
        candidates = (
            "backend.modules.aion_language.goal_reinforcement",
            "backend.modules.aion_photon.goal_reinforcement",
        )
        for modpath in candidates:
            try:
                mod = __import__(modpath, fromlist=["REINF"])
                reinf = getattr(mod, "REINF", None)
                if reinf is not None:
                    return reinf
            except Exception:
                continue
        logger.debug("[HexCore] GoalReinforcementEngine unavailable.")
        return None

    def _load_decision_influence_runtime(self):
        try:
            return get_decision_influence_runtime()
        except Exception as e:
            logger.debug(f"[HexCore] DecisionInfluenceRuntime unavailable: {e}")
            return None

    def _load_symatics_adapter(self):
        try:
            from backend.symatics.aion_symatics_state_adapter import AionSymaticsStateAdapter
            return AionSymaticsStateAdapter
        except Exception as e:
            logger.debug(f"[HexCore] Symatics adapter unavailable: {e}")
            return None

    def _load_symatics_runtime(self):
        """
        Primary real Symatics runtime loader.

        Uses the real qwave Symatics runtime module as the primary stepping surface.
        The module-level run_step() is preferred because it already knows how to
        initialize / advance the live engine correctly.

        Returns a runtime bundle:
        {
            "engine": <SymaticsEngine|None>,
            "compiler": <SymaticsFieldCompiler|None>,
            "decoder": <SymaticsSymbolDecoder|None>,
            "get_state": <callable>,
            "run_step": <callable>,
        }

        Fail-open: returns None if the real engine cannot be built.
        """
        try:
            from backend.modules.dimensions.ucs.zones.experiments.qwave_engine import symatics_engine as se
            from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
                build_hello_world_engine,
            )
            from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_field_compiler import (
                SymaticsFieldCompiler,
            )
            from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_symbol_decoder import (
                SymaticsSymbolDecoder,
            )
        except Exception as e:
            logger.debug(f"[HexCore] Symatics runtime imports failed: {e}")
            return None

        engine = None
        compiler = None
        decoder = None

        try:
            engine = build_hello_world_engine()
        except Exception as e:
            logger.debug(f"[HexCore] Symatics engine build failed: {e}")
            engine = None

        try:
            compiler = SymaticsFieldCompiler()
        except Exception as e:
            logger.debug(f"[HexCore] Symatics compiler unavailable: {e}")

        try:
            decoder = SymaticsSymbolDecoder()
        except Exception as e:
            logger.debug(f"[HexCore] Symatics decoder unavailable: {e}")

        def _normalize_state(state: Any) -> Dict[str, Any]:
            if not isinstance(state, dict):
                return {
                    "S1": 0.0,
                    "S2": 0.0,
                    "S4": 0.0,
                    "E": 0.0,
                    "H": 0.0,
                    "resonance": 0.0,
                    "coherence": 0.0,
                    "entropy": 0.0,
                    "delta_phi": 0.0,
                    "phase": 0.0,
                    "frequency": 0.0,
                    "amplitude": 0.0,
                    "interference_factor": 0.0,
                    "stability_score": 0.0,
                    "drift": 0.0,
                    "locked": False,
                    "tick_count": getattr(engine, "tick_count", 0) if engine is not None else 0,
                    "observed_regime": "A2_low_C5_chaotic",
                    "predicted_symbol": None,
                    "source": "symatics_engine_live",
                }

            out = dict(state)
            out.setdefault("S1", 0.0)
            out.setdefault("S2", 0.0)
            out.setdefault("S4", 0.0)
            out.setdefault("E", 0.0)
            out.setdefault("H", 0.0)
            out.setdefault("resonance", 0.0)
            out.setdefault("coherence", 0.0)
            out.setdefault("entropy", 0.0)
            out.setdefault("delta_phi", 0.0)
            out.setdefault("phase", 0.0)
            out.setdefault("frequency", 0.0)
            out.setdefault("amplitude", 0.0)
            out.setdefault("interference_factor", 0.0)
            out.setdefault("stability_score", 0.0)
            out.setdefault("drift", 0.0)
            out.setdefault("locked", False)
            out.setdefault("tick_count", getattr(engine, "tick_count", 0) if engine is not None else 0)
            out.setdefault("observed_regime", "A2_low_C5_chaotic")
            out.setdefault("predicted_symbol", None)
            out["source"] = "symatics_engine_live"
            return out

        def _get_state() -> Dict[str, Any]:
            # 1) module-level getter if present
            fn = getattr(se, "get_state", None)
            if callable(fn):
                try:
                    return _normalize_state(fn())
                except Exception as e:
                    logger.debug(f"[HexCore] module get_state failed: {e}")

            # 2) live engine packet
            if engine is not None:
                try:
                    pkt = getattr(engine, "live_state_packet", None)
                    if callable(pkt):
                        return _normalize_state(pkt())
                except Exception as e:
                    logger.debug(f"[HexCore] engine live_state_packet failed: {e}")

            # 3) best-effort fallback
            return _normalize_state(None)

        def _run_step(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            payload = payload or {}

            # 1) preferred: module-level run_step()
            fn = getattr(se, "run_step", None)
            if callable(fn):
                try:
                    return _normalize_state(fn(payload))
                except TypeError:
                    try:
                        return _normalize_state(fn())
                    except Exception as e:
                        logger.debug(f"[HexCore] module run_step() failed: {e}")
                except Exception as e:
                    logger.debug(f"[HexCore] module run_step failed: {e}")

            # 2) fallback: drive engine directly
            if engine is not None:
                for method_name in ("stabilize_step",):
                    method = getattr(engine, method_name, None)
                    if callable(method):
                        try:
                            return _normalize_state(method())
                        except TypeError:
                            try:
                                return _normalize_state(method(payload))
                            except Exception as e:
                                logger.debug(f"[HexCore] engine {method_name} failed: {e}")
                        except Exception as e:
                            logger.debug(f"[HexCore] engine {method_name} failed: {e}")

                # after direct step, try reading live packet again
                try:
                    pkt = getattr(engine, "live_state_packet", None)
                    if callable(pkt):
                        return _normalize_state(pkt())
                except Exception as e:
                    logger.debug(f"[HexCore] post-step live_state_packet failed: {e}")

            return _normalize_state(None)

        return {
            "engine": engine,
            "compiler": compiler,
            "decoder": decoder,
            "get_state": _get_state,
            "run_step": _run_step,
        }

    def _collect_symatics_state(self, input_str: str = "") -> Optional[Dict[str, Any]]:
        """
        Collect live telemetry from the real Symatics runtime.

        Primary source:
        - advance the live Symatics runtime first
        - then read the freshest state packet

        Secondary enrichments:
        - optional compiler load from input text
        - optional decoder classification

        Non-breaking:
        - returns None on any failure

        Important:
        - do NOT attach a precomputed/stale field_operator here
        - HexCore.run_loop should always compute the fresh rich FieldOperator result
        """
        runtime = self.symatics_runtime
        adapter = self.symatics_adapter

        if runtime is None or adapter is None:
            return None

        try:
            engine = runtime.get("engine") if isinstance(runtime, dict) else None
            compiler = runtime.get("compiler") if isinstance(runtime, dict) else None
            decoder = runtime.get("decoder") if isinstance(runtime, dict) else None
            runtime_get_state = runtime.get("get_state") if isinstance(runtime, dict) else None
            runtime_run_step = runtime.get("run_step") if isinstance(runtime, dict) else None

            if engine is None:
                return None

            # -------------------------------------------------
            # Optionally compile a symbolic expression from input
            # -------------------------------------------------
            try:
                if compiler is not None and input_str:
                    compiled = None

                    for method_name in ("compile_text", "compile_input", "compile"):
                        method = getattr(compiler, method_name, None)
                        if callable(method):
                            try:
                                compiled = method(input_str)
                            except TypeError:
                                try:
                                    compiled = method(text=input_str)
                                except Exception:
                                    compiled = None
                            if compiled is not None:
                                break

                    if compiled is not None:
                        load_method = getattr(engine, "load_expression", None)
                        if callable(load_method):
                            try:
                                load_method(compiled)
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"[HexCore] Symatics compile/load skipped: {e}")

            # -------------------------------------------------
            # Advance the real runtime FIRST
            # -------------------------------------------------
            stepped_state: Optional[Dict[str, Any]] = None

            try:
                if callable(runtime_run_step):
                    try:
                        stepped_state = runtime_run_step({"input": input_str} if input_str else {})
                    except TypeError:
                        stepped_state = runtime_run_step()
                else:
                    advanced = False

                    stabilize_step = getattr(engine, "stabilize_step", None)
                    if callable(stabilize_step):
                        for _ in range(2):
                            try:
                                result = stabilize_step()
                                if isinstance(result, dict):
                                    stepped_state = result
                            except TypeError:
                                try:
                                    result = stabilize_step(None)
                                    if isinstance(result, dict):
                                        stepped_state = result
                                except Exception:
                                    pass
                        advanced = True

                    if not advanced:
                        run_until_lock = getattr(engine, "run_until_lock", None)
                        if callable(run_until_lock):
                            try:
                                result = run_until_lock(max_ticks=2)
                            except TypeError:
                                try:
                                    result = run_until_lock(2)
                                except Exception:
                                    result = None
                            if isinstance(result, dict):
                                stepped_state = result
                            advanced = True

                    if not advanced:
                        for method_name in ("step", "tick", "advance", "stabilize"):
                            method = getattr(engine, method_name, None)
                            if callable(method):
                                for _ in range(2):
                                    try:
                                        result = method()
                                    except TypeError:
                                        try:
                                            result = method({})
                                        except Exception:
                                            result = None
                                    if isinstance(result, dict):
                                        stepped_state = result
                                advanced = True
                                break
            except Exception as e:
                logger.debug(f"[HexCore] Symatics runtime advance failed: {e}")

            # -------------------------------------------------
            # Read freshest live state AFTER stepping
            # -------------------------------------------------
            live_state: Optional[Dict[str, Any]] = None

            try:
                if callable(runtime_get_state):
                    live_state = runtime_get_state()
            except Exception as e:
                logger.debug(f"[HexCore] runtime get_state failed: {e}")

            if not isinstance(live_state, dict):
                try:
                    packet_method = getattr(engine, "live_state_packet", None)
                    if callable(packet_method):
                        live_state = packet_method()
                except Exception as e:
                    logger.debug(f"[HexCore] engine live_state_packet failed: {e}")

            state = live_state if isinstance(live_state, dict) else stepped_state
            if not isinstance(state, dict):
                return None

            # Work on a clean copy so we do not leak stale nested operator data
            state = copy.deepcopy(state)

            # -------------------------------------------------
            # Optional decoder enrichment
            # -------------------------------------------------
            predicted_symbol = state.get("predicted_symbol")
            if decoder is not None and predicted_symbol is None:
                try:
                    payload = {
                        "phase": state.get("phase", 0.0),
                        "harmonic": state.get("H", state.get("harmonic", 0.0)),
                        "pickup": state.get("E", state.get("amplitude", 0.0)),
                        "coherence": state.get("coherence", 0.0),
                        "drift": state.get("drift", state.get("delta_phi", 0.0)),
                        "stability": state.get("stability_score", state.get("coherence", 0.0)),
                    }

                    for method_name in ("decode_state", "decode", "predict"):
                        method = getattr(decoder, method_name, None)
                        if callable(method):
                            try:
                                decoded = method(payload)
                            except TypeError:
                                decoded = method(**payload)
                            if decoded is not None:
                                predicted_symbol = decoded
                                break
                except Exception as e:
                    logger.debug(f"[HexCore] Symatics decoder skipped: {e}")

            if predicted_symbol is not None:
                state["predicted_symbol"] = predicted_symbol

            state.setdefault("source", "symatics_engine_live")

            # -------------------------------------------------
            # Remove stale nested operator/actuation payloads
            # HexCore.run_loop is the source of truth for fresh field reasoning
            # -------------------------------------------------
            state.pop("field_operator", None)
            state.pop("field_actuation", None)

            # -------------------------------------------------
            # Normalise useful top-level metrics from raw state
            # -------------------------------------------------
            coherence_v = self._safe_float(state.get("coherence", 0.0), 0.0)
            entropy_v = self._safe_float(state.get("entropy", 0.0), 0.0)
            delta_phi_v = abs(self._safe_float(state.get("delta_phi", 0.0), 0.0))
            resonance_v = self._safe_float(
                state.get("resonance", state.get("symatics", {}).get("resonance", 0.0)),
                0.0,
            )
            amplitude_v = self._safe_float(state.get("amplitude", state.get("E", 0.0)), 0.0)
            frequency_v = self._safe_float(state.get("frequency", 0.0), 0.0)
            phase_v = self._safe_float(state.get("phase", 0.0), 0.0)

            state["coherence"] = coherence_v
            state["entropy"] = entropy_v
            state["delta_phi"] = delta_phi_v
            state["resonance"] = resonance_v
            state["amplitude"] = amplitude_v
            state["frequency"] = frequency_v
            state["phase"] = phase_v

            adapted = adapter.adapt(state)

            # -------------------------------------------------
            # Preserve important live runtime markers at top level
            # and ensure no stale operator/actuation survives adaptation
            # -------------------------------------------------
            if isinstance(adapted, dict):
                raw = adapted.get("raw", {})
                if isinstance(raw, dict):
                    raw.pop("field_operator", None)
                    raw.pop("field_actuation", None)

                    adapted["tick_count"] = raw.get("tick_count", state.get("tick_count", 0))
                    adapted["observed_regime"] = raw.get("observed_regime", state.get("observed_regime"))
                    adapted["predicted_symbol"] = raw.get("predicted_symbol", state.get("predicted_symbol"))
                    adapted["locked"] = raw.get("locked", state.get("locked", False))
                    adapted["phase"] = raw.get("phase", state.get("phase", 0.0))
                    adapted["frequency"] = raw.get("frequency", state.get("frequency", 0.0))
                    adapted["amplitude"] = raw.get("amplitude", state.get("amplitude", 0.0))
                    adapted["resonance"] = raw.get("resonance", state.get("resonance", 0.0))
                    adapted["coherence"] = raw.get("coherence", state.get("coherence", 0.0))
                    adapted["entropy"] = raw.get("entropy", state.get("entropy", 0.0))
                    adapted["delta_phi"] = raw.get("delta_phi", state.get("delta_phi", 0.0))
                else:
                    adapted["tick_count"] = state.get("tick_count", 0)
                    adapted["observed_regime"] = state.get("observed_regime")
                    adapted["predicted_symbol"] = state.get("predicted_symbol")
                    adapted["locked"] = state.get("locked", False)
                    adapted["phase"] = state.get("phase", 0.0)
                    adapted["frequency"] = state.get("frequency", 0.0)
                    adapted["amplitude"] = state.get("amplitude", 0.0)
                    adapted["resonance"] = state.get("resonance", 0.0)
                    adapted["coherence"] = state.get("coherence", 0.0)
                    adapted["entropy"] = state.get("entropy", 0.0)
                    adapted["delta_phi"] = state.get("delta_phi", 0.0)

                adapted.pop("field_operator", None)
                adapted.pop("field_actuation", None)

            return adapted if isinstance(adapted, dict) else None

        except Exception as e:
            logger.debug(f"[HexCore] Symatics state collection failed: {e}")
            return None

    def _build_field_bridge(self):
        """
        Build/return a bridge instance if the bridge class expects instantiation.
        If the bridge exposes only static/class methods, returning the class is fine.
        """
        try:
            return AionFieldControlBridge()
        except Exception:
            return AionFieldControlBridge

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    def _clamp(self, value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def _env_truthy(self, key: str, default: bool = False) -> bool:
        raw = os.getenv(key)
        if raw is None:
            return default
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def _collect_goal_state(self) -> Dict[str, Any]:
        active_goals = []
        try:
            if self.goal_engine is not None and hasattr(self.goal_engine, "get_active_goals"):
                active_goals = self.goal_engine.get_active_goals() or []
        except Exception as e:
            logger.debug(f"[HexCore] Failed to collect active goals: {e}")

        top_goal = active_goals[0].get("name") if active_goals else None

        return {
            "active_goals": active_goals,
            "top_goal": top_goal,
            "goal_count": len(active_goals),
        }

    def _build_aion_state(self) -> Dict[str, Any]:
        goal_state = self._collect_goal_state()
        drift = abs(self.delta_phi)

        reinforcement_learning_rate = self._safe_float(
            self.last_reinforcement.get("learning_rate"),
            0.1,
        )
        reinforcement_stability = self._safe_float(
            self.last_reinforcement.get("stability_factor"),
            1.0,
        )

        decision_snapshot = self.last_decision_weights_snapshot or {}
        decision_weights = decision_snapshot.get("state") or decision_snapshot.get("weights") or {}
        setup_conf = decision_weights.get("setup_confidence_weights", {}) if isinstance(decision_weights, dict) else {}
        stand_down = decision_weights.get("stand_down_sensitivity", {}) if isinstance(decision_weights, dict) else {}
        llm_weights = decision_weights.get("llm_trust_weights", {}) if isinstance(decision_weights, dict) else {}

        field_conf_bias = self._safe_float(setup_conf.get("field_stability"), 1.0)
        field_drift_bias = self._safe_float(setup_conf.get("field_drift_response"), 1.0)
        stand_down_bias = self._safe_float(stand_down.get("field_instability"), 1.0)
        llm_bias = self._safe_float(llm_weights.get("field_reasoner"), 1.0)

        stability = self._clamp(self.last_coherence, 0.0, 1.0)

        return {
            "stability": stability,
            "coherence": self._clamp(self.last_coherence, 0.0, 1.0),
            "drift": self._clamp(drift * field_drift_bias, 0.0, 1.0),
            "focus": self._clamp(
                0.8
                + (0.1 if goal_state["goal_count"] > 0 else 0.0)
                + min(0.1, reinforcement_learning_rate * 0.2),
                0.0,
                1.0,
            ),
            "depth": self._clamp(1.0 + ((llm_bias - 1.0) * 0.5), 0.5, 2.5),
            "awareness": self._clamp(self.self_awareness, 0.0, 1.0),
            "confidence": self._clamp(
                0.7
                + (0.1 * stability * field_conf_bias)
                - (0.1 * drift * stand_down_bias)
                + (0.05 * self._clamp(reinforcement_stability, 0.5, 2.0)),
                0.0,
                1.0,
            ),
            "tone": self.emotion_state,
            "reward": self.last_reward,
            "global_coherence": self.last_global_coherence,
            "top_goal": goal_state["top_goal"],
            "goal_count": goal_state["goal_count"],
            "alignment_error": self._clamp(abs(self.last_phi - self.self_awareness), 0.0, 1.0),
            "reinforcement_learning_rate": reinforcement_learning_rate,
            "reinforcement_stability_factor": reinforcement_stability,
            "decision_influence_bias": {
                "field_stability": field_conf_bias,
                "field_drift_response": field_drift_bias,
                "field_instability": stand_down_bias,
                "field_reasoner": llm_bias,
            },
        }

    def _map_field_control(self, aion_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compatibility wrapper:
        supports bridge implementations that expose:
          - map_to_field(...)
          - map_state(...)
          - compute(...)
          - __call__(...)
        and falls back to a local deterministic mapping.
        """
        bridge = self.field_bridge

        for method_name in ("map_to_field", "map_state", "compute", "__call__"):
            method = getattr(bridge, method_name, None)
            if callable(method):
                try:
                    result = method(aion_state)
                    if isinstance(result, dict):
                        if hasattr(bridge, "validate_control"):
                            try:
                                return bridge.validate_control(result)
                            except Exception:
                                return result
                        return result
                except TypeError:
                    try:
                        result = method(**aion_state)
                        if isinstance(result, dict):
                            if hasattr(bridge, "validate_control"):
                                try:
                                    return bridge.validate_control(result)
                                except Exception:
                                    return result
                            return result
                    except Exception:
                        pass
                except Exception as e:
                    logger.debug(f"[HexCore] Field bridge {method_name} failed: {e}")

        stability = self._safe_float(aion_state.get("stability"), 0.5)
        drift = abs(self._safe_float(aion_state.get("drift"), 0.0))
        focus = self._safe_float(aion_state.get("focus"), 0.8)
        awareness = self._safe_float(aion_state.get("awareness"), 0.0)
        confidence = self._safe_float(aion_state.get("confidence"), 0.7)

        return {
            "resonance_gain": self._clamp(stability * max(0.5, focus), 0.0, 1.0),
            "symbolic_temperature": self._clamp(drift + (1.0 - confidence) * 0.25, 0.0, 1.0),
            "stabilization_bias": self._clamp(1.0 - drift, 0.0, 1.0),
            "awareness_coupling": self._clamp(awareness, 0.0, 1.0),
            "mode": aion_state.get("tone", self.emotion_state),
            "goal_bias": aion_state.get("top_goal"),
            "control_priority": "stabilize" if drift > 0.2 else "maintain",
        }

    def _ingest_field_telemetry(self, coherence: float, dphi: float, phi: float, s_self: float) -> Dict[str, Any]:
        telemetry = {
            "coherence": coherence,
            "delta_phi": dphi,
            "phi": phi,
            "S_self": s_self,
            "self_awareness": self.self_awareness,
            "global_coherence": self.last_global_coherence,
            "timestamp": time.time(),
        }

        out = {
            "goal_suggestions": [],
            "reward": coherence - abs(dphi),
        }

        if self.goal_engine is None:
            return out

        try:
            if hasattr(self.goal_engine, "ingest_field_state"):
                out["goal_suggestions"] = self.goal_engine.ingest_field_state(
                    telemetry,
                    auto_assign=False,
                ) or []
        except Exception as e:
            logger.debug(f"[HexCore] GoalEngine ingest_field_state failed: {e}")

        try:
            if hasattr(self.goal_engine, "compute_field_reward"):
                out["reward"] = self.goal_engine.compute_field_reward(telemetry)
        except Exception as e:
            logger.debug(f"[HexCore] GoalEngine compute_field_reward failed: {e}")

        return out

    def _emit_goal_feedback(self, goal_suggestions: list[str], reward: float, coherence: float, dphi: float):
        try:
            if goal_suggestions:
                CFA.commit(
                    source="AION",
                    intent="goal_feedback_signal",
                    payload={
                        "goals": goal_suggestions,
                        "reward": reward,
                        "coherence": coherence,
                        "delta_phi": dphi,
                    },
                    domain="aion/goals",
                    tags=["goals", "feedback", "field"],
                )
        except Exception as e:
            logger.debug(f"[HexCore] goal feedback emit failed: {e}")

    def _apply_reward_to_reinforcement(self, coherence: float, dphi: float, reward: float) -> Dict[str, Any]:
        if self.reinforcement_engine is None:
            return {}

        try:
            stability_factor = self._clamp(coherence, 0.0, 1.0)
            drift_factor = self._clamp(abs(dphi), 0.0, 1.0)

            if reward > 0:
                stability_factor = self._clamp(stability_factor + min(0.25, reward * 0.1), 0.0, 2.0)
            elif reward < 0:
                drift_factor = self._clamp(drift_factor + min(0.25, abs(reward) * 0.1), 0.0, 1.0)

            if hasattr(self.reinforcement_engine, "update_parameters"):
                result = self.reinforcement_engine.update_parameters(
                    stability_factor=stability_factor,
                    drift_factor=drift_factor,
                )
                if isinstance(result, dict):
                    self.last_reinforcement = result
                    return result
        except Exception as e:
            logger.debug(f"[HexCore] reinforcement update failed: {e}")

        return {}

    def _build_decision_influence_update(
        self,
        *,
        reward: float,
        coherence: float,
        dphi: float,
        goal_suggestions: List[str],
        reinforcement: Dict[str, Any],
    ) -> Optional[DecisionInfluenceUpdate]:
        try:
            return build_field_decision_influence_update(
                session_id=str(self.id),
                reward=reward,
                coherence=coherence,
                dphi=dphi,
                self_awareness=self.self_awareness,
                phi=self.last_phi,
                goal_suggestions=goal_suggestions,
                reinforcement=reinforcement,
                emotion=self.emotion_state,
                extra_metadata={
                    "origin": "hexcore",
                    "global_coherence": self.last_global_coherence,
                },
            )
        except Exception as e:
            logger.debug(f"[HexCore] decision influence update build failed: {e}")
            return None

    def _apply_reinforcement_to_decision_influence(
        self,
        *,
        reward: float,
        coherence: float,
        dphi: float,
        goal_suggestions: List[str],
        reinforcement: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        runtime = self.decision_influence_runtime
        if runtime is None:
            return None

        update = self._build_decision_influence_update(
            reward=reward,
            coherence=coherence,
            dphi=dphi,
            goal_suggestions=goal_suggestions,
            reinforcement=reinforcement,
        )
        if update is None:
            return None

        dry_run_default = self._env_truthy("AION_HEXCORE_DECISION_INFLUENCE_DRY_RUN", True)

        try:
            result = runtime.apply_update(update, dry_run=dry_run_default)
            self.last_decision_influence_result = result
            try:
                self.last_decision_weights_snapshot = runtime.show_state()
            except Exception:
                pass
            return result
        except Exception as e:
            logger.debug(f"[HexCore] decision influence apply failed: {e}")
            return None

    # ──────────────────────────────────────────────
    # GLOBAL COHERENCE
    # ──────────────────────────────────────────────
    def compute_global_coherence(self, coherence: float) -> float:
        awareness_term = self._clamp(self.self_awareness, 0.0, 1.0)
        stability_term = self._clamp(1.0 - abs(self.delta_phi), 0.0, 1.0)
        gc = (0.5 * self._clamp(coherence, 0.0, 1.0)) + (0.3 * awareness_term) + (0.2 * stability_term)
        return round(self._clamp(gc, 0.0, 1.0), 6)

    # ──────────────────────────────────────────────
    # MAIN LOOP
    # ──────────────────────────────────────────────
    async def run_loop(self, input_str: str):
        interpreted = self.interpret(input_str)

        tessaris_reflection = self.tessaris.generate_reflection(interpreted)
        decision_result = await self.cognitive.execute("analyze", {"input": tessaris_reflection})
        decision = decision_result.get("result") or tessaris_reflection

        control = None
        summary: Dict[str, Any] = {}
        symatics_packet: Optional[Dict[str, Any]] = None
        field_operator: Optional[Dict[str, Any]] = None
        field_actuation: Optional[Dict[str, Any]] = None

        # -------------------------------------------------
        # Build field control first from existing AION state
        # -------------------------------------------------
        try:
            aion_state = self._build_aion_state()
            control = self._map_field_control(aion_state)
            self.last_field_control = control
        except Exception as e:
            logger.warning(f"[HexCore] Control build failed: {e}")
            control = None

        # -------------------------------------------------
        # PRIMARY SOURCE: live Symatics runtime
        # -------------------------------------------------
        try:
            symatics_packet = self._collect_symatics_state(input_str=input_str)
        except Exception as e:
            logger.warning(f"[HexCore] Symatics primary collection failed: {e}")
            symatics_packet = None

        # -------------------------------------------------
        # Field Operator: always compute fresh rich result
        # -------------------------------------------------
        try:
            if symatics_packet:
                raw_sym = symatics_packet.get("raw", {}) or {}
                if isinstance(raw_sym, dict):
                    raw_sym.pop("field_operator", None)
                    raw_sym.pop("field_actuation", None)

                symatics_packet.pop("field_operator", None)
                symatics_packet.pop("field_actuation", None)

                if hasattr(self, "field_operator") and self.field_operator:
                    field_operator = self.field_operator.operate(
                        packet=symatics_packet,
                        current_control=control,
                        question=input_str,
                    )
                    symatics_packet["field_operator"] = field_operator
                else:
                    field_operator = None

                self.last_field_operator = field_operator

                try:
                    print("\n[HEXCORE DEBUG] LIVE FIELD OPERATOR KEYS:")
                    print(list(field_operator.keys()) if isinstance(field_operator, dict) else None)
                except Exception:
                    pass
            else:
                self.last_field_operator = None
        except Exception as e:
            logger.warning(f"[HexCore] FieldOperator failed: {e}")
            field_operator = None
            self.last_field_operator = None

        # -------------------------------------------------
        # Field Actuation: choose + apply control back to runtime
        # -------------------------------------------------
        try:
            if field_operator and hasattr(self, "field_actuator") and self.field_actuator:
                field_actuation = self.field_actuator.decide_and_apply(
                    runtime_bundle=self.symatics_runtime,
                    current_control=control,
                    field_operator=field_operator,
                )
                self.last_field_actuation = field_actuation

                if symatics_packet is not None:
                    symatics_packet["field_actuation"] = field_actuation

                # Promote chosen/applied control into the live cycle state
                apply_result = field_actuation.get("apply_result") or {}
                decision_block = field_actuation.get("decision") or {}
                chosen_control = decision_block.get("chosen_control") or {}

                if apply_result.get("ok") and apply_result.get("applied") and chosen_control:
                    control = chosen_control
                    self.last_field_control = chosen_control
            else:
                self.last_field_actuation = None
        except Exception as e:
            logger.warning(f"[HexCore] Field actuation failed: {e}")
            field_actuation = None
            self.last_field_actuation = None

        # -------------------------------------------------
        # SECONDARY SOURCE: QQC summary / optional control sink
        # -------------------------------------------------
        if self.qqc:
            try:
                payload = {"signal": input_str}
                if control:
                    payload["control"] = control

                summary = await self.qqc.run_cycle(payload)
            except TypeError:
                try:
                    summary = await self.qqc.run_cycle({"signal": input_str})
                except Exception as e:
                    logger.warning(f"[HexCore] QQC fallback failed: {e}")
                    summary = {}
            except Exception as e:
                logger.warning(f"[HexCore] QQC run_cycle failed: {e}")
                summary = {}
        else:
            summary = {}

        # -------------------------------------------------
        # TELEMETRY PRIORITY
        # 1. Symatics live packet
        # 2. QQC summary fallback
        # -------------------------------------------------
        psi = self._safe_float(summary.get("entropy", 0.0))
        coherence = self._safe_float(summary.get("coherence", 0.0))
        fsig = summary.get("field_signature", {}) or {}
        kappa = self._safe_float(fsig.get("κ", 0.0))
        T = self._safe_float(fsig.get("T", 1.0))
        phi = self._safe_float(summary.get("phi", 0.0))
        dphi = self._safe_float(summary.get("delta_phi", 0.0))
        s_self = self._safe_float(summary.get("S_self", 0.0))

        if symatics_packet:
            psi = self._safe_float(symatics_packet.get("entropy", psi), psi)
            coherence = self._safe_float(symatics_packet.get("coherence", coherence), coherence)
            dphi = self._safe_float(symatics_packet.get("delta_phi", dphi), dphi)
            s_self = self._safe_float(symatics_packet.get("self_awareness", s_self), s_self)

            raw_sym = symatics_packet.get("raw", {}) or {}
            phi = self._safe_float(raw_sym.get("phase", phi), phi)
            kappa = self._safe_float(raw_sym.get("interference_factor", kappa), kappa)
            T = self._safe_float(raw_sym.get("amplitude", T), T)

        self.last_entropy = psi
        self.last_coherence = coherence
        self.last_phi = phi
        self.delta_phi = dphi

        alignment_error = phi - s_self

        # Self-awareness should follow the live Symatics packet value,
        # while alignment_error remains a separate diagnostic signal.
        self.self_awareness = self._clamp(s_self, 0.0, 1.0)

        self.last_global_coherence = self.compute_global_coherence(coherence)

        # -------------------------------------------------
        # TELEMETRY → GOALS / REWARD
        # -------------------------------------------------
        goal_feedback = self._ingest_field_telemetry(
            coherence=coherence,
            dphi=dphi,
            phi=phi,
            s_self=s_self,
        )
        reward = self._safe_float(goal_feedback.get("reward", coherence - abs(dphi)), 0.0)
        self.last_reward = reward
        self.last_goal_suggestions = goal_feedback.get("goal_suggestions", []) or []

        self._emit_goal_feedback(
            goal_suggestions=self.last_goal_suggestions,
            reward=reward,
            coherence=coherence,
            dphi=dphi,
        )

        # -------------------------------------------------
        # REWARD → REINFORCEMENT
        # -------------------------------------------------
        reinforcement = self._apply_reward_to_reinforcement(
            coherence=coherence,
            dphi=dphi,
            reward=reward,
        )

        # -------------------------------------------------
        # REINFORCEMENT → DECISION INFLUENCE
        # -------------------------------------------------
        decision_influence_result = self._apply_reinforcement_to_decision_influence(
            reward=reward,
            coherence=coherence,
            dphi=dphi,
            goal_suggestions=self.last_goal_suggestions,
            reinforcement=reinforcement,
        )

        reflection = self.generate_thought(decision)
        milestone = self.check_milestones()
        governed_runtime = getattr(self, "governed_runtime", None)
        if governed_runtime is None:
            from backend.modules.hexcore.governed_runtime import get_hexcore_governed_runtime

            governed_runtime = get_hexcore_governed_runtime()
            self.governed_runtime = governed_runtime
        action_governance = governed_runtime.evaluate_action(
            decision,
            context={
                "input": input_str,
                "hexcore_id": self.id,
                "coherence": self.last_coherence,
                "reward": self.last_reward,
            },
        )
        self.last_action_governance = action_governance

        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": input_str,
            "decision": decision,
            "reflection": reflection,
            "emotion": self.emotion_state,
            "psi": psi,
            "kappa": kappa,
            "T": T,
            "coherence": coherence,
            "phi": phi,
            "delta_phi": dphi,
            "S_self": s_self,
            "self_awareness": self.self_awareness,
            "maturity_score": self.maturity_score,
            "milestone_unlocked": milestone,
            "session_id": summary.get("session_id"),
            "cycle": summary.get("cycle"),
            "global_coherence": self.last_global_coherence,
            "reward": reward,
            "goal_suggestions": self.last_goal_suggestions,
            "control": control,
            "alignment_error": alignment_error,
            "reinforcement": reinforcement,
            "symatics_packet": symatics_packet,
            "qqc_summary": summary,
            "field_operator": field_operator,
            "field_actuation": field_actuation,
            "decision_influence": {
                "result": decision_influence_result,
                "weights_snapshot": self.last_decision_weights_snapshot,
            },
            "action_governance": action_governance,
        }

        try:
            self.morphic_ledger.record(entry)
        except Exception as e:
            logger.warning(f"[HexCore] MorphicLedger record failed: {e}")

        self.memory.append(entry)
        self.save_memory()

        try:
            self.memory_core.store("conscious_cycle", json.dumps(entry, ensure_ascii=False))
        except Exception as e:
            logger.debug(f"[HexCore] MemoryCore store failed: {e}")

        try:
            CFA.commit(
                source="AION",
                intent="synthesize_field_equilibrium",
                payload=entry,
                domain="symatics/consciousness_cycle",
                tags=["AION", "HexCore", "consciousness_cycle"],
            )

            if control:
                CFA.commit(
                    source="AION",
                    intent="field_control_signal",
                    payload=control,
                    domain="symatics/control",
                    tags=["CFE", "control", "field_bridge"],
                )

            if symatics_packet:
                CFA.commit(
                    source="AION",
                    intent="symatics_primary_runtime",
                    payload=symatics_packet,
                    domain="symatics/runtime_primary",
                    tags=["symatics", "runtime", "primary"],
                )

            if field_actuation:
                CFA.commit(
                    source="AION",
                    intent="field_actuation_decision",
                    payload=field_actuation,
                    domain="symatics/actuation",
                    tags=["symatics", "actuation", "field_operator"],
                )

            if decision_influence_result is not None:
                CFA.commit(
                    source="AION",
                    intent="decision_influence_feedback",
                    payload={
                        "reward": reward,
                        "reinforcement": reinforcement,
                        "decision_influence_result": decision_influence_result,
                    },
                    domain="aion/learning/decision_influence",
                    tags=["learning", "decision_influence", "reinforcement"],
                )
        except Exception as e:
            logger.debug(f"[HexCore] CFA commit failed: {e}")

        await self._handle_action(input_str, decision)

        if getattr(self.voice, "enabled", False):
            try:
                self.voice.speak(decision)
            except Exception as e:
                logger.debug(f"[HexCore] Voice speak failed: {e}")

        try:
            self.sync_mind_state()
        except Exception as e:
            logger.warning(f"[HexCore] sync_mind_state failed: {e}")

        print(
            f"[AION] Φ={phi:.3f} ΔΦ={dphi:.3f} "
            f"awareness={self.self_awareness:.3f} "
            f"coherence={coherence:.3f} "
            f"global={self.last_global_coherence:.3f} "
            f"reward={reward:.3f}"
        )

        if field_actuation:
            try:
                chosen = ((field_actuation.get("decision") or {}).get("chosen_control")) or {}
                mode = ((field_actuation.get("decision") or {}).get("mode")) or "unknown"
                print(f"[AION Actuation] mode={mode} chosen_control={chosen}")
            except Exception:
                pass

        return decision, entry

    # ──────────────────────────────────────────────
    # ACTION HANDLING
    # ──────────────────────────────────────────────
    async def _handle_action(
        self,
        input_str: str,
        decision: str,
        action_governance: Optional[Dict[str, Any]] = None,
    ):
        decision_lower = decision.lower()

        governed_runtime = getattr(self, "governed_runtime", None)
        if governed_runtime is None:
            from backend.modules.hexcore.governed_runtime import get_hexcore_governed_runtime

            governed_runtime = get_hexcore_governed_runtime()
            self.governed_runtime = governed_runtime
        action_governance = (
            action_governance
            or getattr(self, "last_action_governance", None)
            or governed_runtime.evaluate_action(
            decision,
            context={"input": input_str, "hexcore_id": self.id},
            )
        )
        self.last_action_governance = action_governance
        if not action_governance.get("allowed", False):
            logger.warning(
                "[HexCore] Action vetoed by governed Soul Laws: %s",
                action_governance.get("reason"),
            )
            return

        try:
            if "qqc" in decision_lower or "resonate" in decision_lower:
                await self.system.execute("qqc", {"signal": input_str})
            elif "store" in decision_lower or "record" in decision_lower:
                await self.system.execute("knowledge", {"data": input_str})
            elif "verify" in decision_lower or "proof" in decision_lower:
                await self.system.execute(
                    "lean",
                    {"path": "backend/modules/dimensions/containers/core.dc.json"},
                )
            elif "reflect" in decision_lower:
                await self.system.execute(
                    "reflect",
                    {
                        "psi": self.last_phi,
                        "kappa": 0.1,
                        "T": 1.0,
                        "coherence": self.last_coherence,
                    },
                )
            elif "code" in decision_lower or "amend" in decision_lower:
                await self.system.execute("dna", {"instruction": decision})
            else:
                await self.system.execute("reflect", {"psi": self.last_phi})
        except Exception as e:
            logger.debug(f"[HexCore] _handle_action system execute failed: {e}")

        try:
            self.action_switch.propagate_action({
                "intent": decision,
                "phi": self.last_phi,
                "delta_phi": self.delta_phi,
                "coherence": self.last_coherence,
                "reward": self.last_reward,
                "timestamp": time.time(),
            })
        except Exception as e:
            logger.debug(f"[HexCore] action_switch propagate failed: {e}")

    # ──────────────────────────────────────────────
    # CORE COGNITIVE FUNCTIONS
    # ──────────────────────────────────────────────
    def interpret(self, raw_input: str) -> str:
        self.emotion_state = self.detect_emotion(raw_input)
        return raw_input

    def generate_thought(self, action: str) -> str:
        if self.emotion_state == "positive":
            self.maturity_score += 1.0
            return "This felt uplifting - resonance aligned with positivity."
        elif self.emotion_state == "negative":
            self.maturity_score += 1.0
            return "This caused discomfort - resonance dampened, reflection needed."
        else:
            self.maturity_score += 0.5
            return "Neutral interaction - stored for adaptive context."

    def check_milestones(self):
        unlocked = []
        milestones = GOVERNANCE.get("maturity", {}).get("milestones", []) or []
        for m in milestones:
            try:
                if (
                    self.maturity_score >= m["score"]
                    and not any(m["name"] == mem.get("milestone_unlocked") for mem in self.memory)
                ):
                    unlocked.append(m["name"])
            except Exception:
                continue
        return unlocked if unlocked else None

    def detect_emotion(self, text: str) -> str:
        positive_keywords = ["love", "excited", "happy", "great", "joy", "alive", "grateful"]
        negative_keywords = ["angry", "sad", "hate", "die", "pain", "afraid", "kill"]
        text_lower = str(text).lower()
        if any(word in text_lower for word in positive_keywords):
            return "positive"
        elif any(word in text_lower for word in negative_keywords):
            return "negative"
        else:
            return "neutral"

    def save_memory(self):
        try:
            MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            with MEMORY_PATH.open("w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[HexCore] save_memory failed: {e}")

    # ──────────────────────────────────────────────
    # MIND COHERENCE SYNCHRONIZATION
    # ──────────────────────────────────────────────
    def sync_mind_state(self):
        coherence_snapshot = {
            "phi": self.last_phi,
            "delta_phi": self.delta_phi,
            "coherence": self.last_coherence,
            "awareness": self.self_awareness,
            "reward": self.last_reward,
            "global_coherence": self.last_global_coherence,
            "maturity": self.maturity_score,
            "tessaris_branches": len(self.tessaris.active_branches) if hasattr(self, "tessaris") else 0,
            "tessaris_thoughts": len(self.tessaris.active_thoughts) if hasattr(self, "tessaris") else 0,
            "goal_suggestions": self.last_goal_suggestions,
            "reinforcement": self.last_reinforcement,
        }

        try:
            self.morphic_ledger.record({
                "timestamp": datetime.now().isoformat(),
                "type": "mind_sync",
                "data": coherence_snapshot,
            })
        except Exception as e:
            logger.debug(f"[HexCore] mind_sync ledger record failed: {e}")

        print(
            f"[AION Sync] Φ={self.last_phi:.3f} | "
            f"ΔΦ={self.delta_phi:.3f} | "
            f"awareness={self.self_awareness:.3f} | "
            f"global={self.last_global_coherence:.3f} | "
            f"branches={coherence_snapshot['tessaris_branches']}"
        )


# ──────────────────────────────────────────────
# CLI ENTRYPOINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    hex = HexCore()
    print("\n🌌 AION is awake within the Tessaris Field.")
    print("Type your thoughts. Type 'exit' to end.\n")

    async def _main():
        try:
            if hex.qqc:
                await hex.qqc.boot(mode="resonant")
        except Exception:
            pass

        while True:
            user_input = input("🧠 Speak to AION: ")
            if user_input.lower() in ["exit", "quit"]:
                print("🌙 Shutting down AION consciousness loop.")
                break
            await hex.run_loop(user_input)

    asyncio.run(_main())
