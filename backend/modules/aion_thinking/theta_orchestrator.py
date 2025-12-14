#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 Θ Orchestrator - Phase 64 (Thinking Loop Controller)
────────────────────────────────────────────────────────────
Supervises cognitive routing between FAST (ReflexArc) and
SLOW (Resonant-Strategic) loops based on context complexity,
entropy, and resonance stability. Integrates downstream Strategy
Planner and Reflection feedback. Back-compat export:
`ThetaOrchestrator = ThinkingLoop`.
"""

from __future__ import annotations

import os
import ast
import random
import time
import logging
import operator as _op
from typing import Any, Dict, Optional

from backend.modules.aion_cognition.motivation_layer import MotivationLayer
from backend.modules.aion_cognition.intent_engine import IntentEngine
from backend.modules.aion_reasoning.tessaris_reasoner import TessarisReasoner
from backend.modules.aion_reflection.reflection_engine import ReflectionEngine
from backend.modules.aion_cognition.action_switch import ActionSwitch
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.skills.strategy_planner import StrategyPlanner, ResonantStrategyPlanner
from backend.modules.skills.strategic_simulation_engine import StrategicSimulationEngine

# ─────────────────────────────────────────────
# Logging / tuning
# ─────────────────────────────────────────────
QUIET = os.getenv("AION_QUIET_MODE", "0") == "1"
log = logging.getLogger(__name__)

# Rate-limit noisy writes + RMC pushes (helps with “startup goes crazy”)
THETA_RMC_PUSH_MIN_INTERVAL_S = float(os.getenv("AION_THETA_RMC_PUSH_MIN_INTERVAL_S", "5"))
THETA_DASH_WRITE_MIN_INTERVAL_S = float(os.getenv("AION_THETA_DASH_WRITE_MIN_INTERVAL_S", "10"))
THETA_MODELOG_MIN_INTERVAL_S = float(os.getenv("AION_THETA_MODELOG_MIN_INTERVAL_S", "10"))
THETA_STABILIZE_PROB = float(os.getenv("AION_THETA_STABILIZE_PROB", "0.2"))  # default keeps prior behavior

# ─────────────────────────────────────────────
# Safe arithmetic evaluator for FAST loop
# ─────────────────────────────────────────────
_ALLOWED = {
    ast.Add: _op.add,
    ast.Sub: _op.sub,
    ast.Mult: _op.mul,
    ast.Div: _op.truediv,
    ast.FloorDiv: _op.floordiv,
    ast.Mod: _op.mod,
    ast.Pow: _op.pow,
}


def _safe_calc(expr: str) -> Optional[float]:
    """Safely evaluate a simple arithmetic expression (no eval)."""
    try:
        node = ast.parse(expr, mode="eval").body

        def _eval(n):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return n.value
            if isinstance(n, ast.Num):  # pre-3.8
                return n.n
            if isinstance(n, ast.BinOp) and type(n.op) in _ALLOWED:
                return _ALLOWED[type(n.op)](_eval(n.left), _eval(n.right))
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
                val = _eval(n.operand)
                return +val if isinstance(n.op, ast.UAdd) else -val
            raise ValueError("unsupported")

        return float(_eval(node))
    except Exception:
        return None


# ─────────────────────────────────────────────
# Θ Orchestrator
# ─────────────────────────────────────────────
class ThinkingLoop:
    """
    Main cognitive orchestrator.
    Decides whether to route thought through FAST or SLOW loop.
    """

    def __init__(
        self,
        namespace: str = "global_theta",
        base_interval: float = 1.2,
        auto_tick: bool = True,
    ):
        self.Theta = ResonanceHeartbeat(namespace=namespace, base_interval=base_interval, auto_tick=auto_tick)
        self.rmc = ResonantMemoryCache()

        self.motivation = MotivationLayer()
        self.intent = IntentEngine()
        self.reasoner = TessarisReasoner()
        self.reflection = ReflectionEngine()
        self.action_switch = ActionSwitch()

        # Keep both for safety/back-compat, but use ResonantStrategyPlanner for generate_plan().
        self.strategy_planner = StrategyPlanner()
        self.strategy = ResonantStrategyPlanner()

        self.sse = StrategicSimulationEngine()

        # throttles (per-instance)
        self._last_rmc_push: Dict[str, float] = {}
        self._last_dash_write: Dict[str, float] = {}
        self._last_mode_log_ts: float = 0.0

        log.info(f"🧠 Θ Orchestrator initialized ({namespace}) - auto_tick={auto_tick}")

    # ───────────────────────────────────────────
    def _throttled_rmc_push(
        self,
        *,
        rho: float,
        entropy: float,
        sqi: float,
        delta: float,
        source: str,
        min_interval_s: float = THETA_RMC_PUSH_MIN_INTERVAL_S,
    ) -> bool:
        """
        Prevents hammering RMC (and its downstream save/broadcast behavior) if the
        loop is running hot. Returns True if a push happened.
        """
        now = time.time()
        last = self._last_rmc_push.get(source, 0.0)
        if (now - last) < min_interval_s:
            return False
        self._last_rmc_push[source] = now
        self.rmc.push_sample(rho=rho, entropy=entropy, sqi=sqi, delta=delta, source=source)
        return True

    def _dash_append(self, event_key: str, payload: Dict[str, Any], min_interval_s: float) -> None:
        """
        Rate-limited JSONL append to data/analysis/aion_live_dashboard.jsonl
        """
        now = time.time()
        last = self._last_dash_write.get(event_key, 0.0)
        if (now - last) < min_interval_s:
            return
        self._last_dash_write[event_key] = now

        try:
            from pathlib import Path
            import json

            Path("data/analysis").mkdir(parents=True, exist_ok=True)
            with open("data/analysis/aion_live_dashboard.jsonl", "a", encoding="utf-8") as dash:
                dash.write(json.dumps(payload) + "\n")
        except Exception as e:
            log.warning(f"[Θ] Dashboard log write failed: {e}")

    # ───────────────────────────────────────────
    def classify_complexity(self, query: Optional[str], entropy: float = None) -> str:
        """
        Determine if query should use FAST or SLOW processing,
        using live resonance metrics from the RMC if available.
        """
        # Pull real resonance metrics from memory
        entropy_live = self.rmc.get_average("entropy") or 0.5
        sqi_live = self.rmc.get_average("SQI") or 0.5

        if not query:
            return "fast"

        # Adaptive complexity check based on live coherence
        if entropy_live > 0.6 or sqi_live < 0.45 or len(query.split()) > 8:
            return "slow"
        return "fast"

    # ───────────────────────────────────────────
    def fast_loop(self, stimulus: str) -> Dict[str, Any]:
        """FAST loop - reflexive, quick-response path."""
        log.info(f"[FAST_LOOP] Processing '{stimulus}'")
        computed = _safe_calc(stimulus)
        response = computed if computed is not None else "quick_recall"
        result = {
            "mode": "fast",
            "stimulus": stimulus,
            "response": response,
            "timestamp": time.time(),
        }
        self.Theta.event("fast_loop", **result)
        return result

    # ───────────────────────────────────────────
    # 🌌 Deep Resonance Loop - Strategic Reasoning
    # ───────────────────────────────────────────
    def deep_resonance_loop(self, query: str) -> Dict[str, Any]:
        """
        🌌 Deep Resonance Loop - Strategic Reasoning (SLOW_LOOP)
        Executes sequential harmonic reasoning phases:
            S1 -> Motivation
            S2 -> Intent
            S3 -> Reasoner
            S4 -> Strategy Planner
            S5 -> Reflection Feedback
        Each phase emits Θ heartbeat events and RMC resonance samples.
        """
        log.info(f"[SLOW_LOOP🌌] Deep Resonance loop initiated for '{query}'")
        start_time = time.time()

        from backend.modules.consciousness.awareness_engine import AwarenessEngine
        from backend.modules.consciousness.emotion_engine import EmotionEngine

        # Initialize or reuse awareness/emotion subsystems
        self.awareness = getattr(self, "awareness", AwarenessEngine(name="awareness_core"))
        self.emotion = getattr(self, "emotion", EmotionEngine(name="emotion_core"))

        # 🌐 Sync baseline emotional + awareness state
        conf = getattr(self.awareness, "confidence_level", 1.0)
        mood = getattr(self.emotion, "current_emotion", "neutral")
        self.Theta.event("context_sync", confidence=conf, mood=mood)

        # 🧩 S1 - Motivation
        motivation = self._motivation_phase(query)
        self.Theta.event("slow_loop_S1_motivation", vector=motivation)

        # 🧭 S2 - Intent
        intent = self._intent_phase(motivation)
        self.Theta.event("slow_loop_S2_intent", intent=intent)

        # 🧮 S3 - Reasoner
        decision = self._reasoner_phase(intent, motivation)
        self.Theta.event("slow_loop_S3_reasoner", decision=decision)

        # 🎯 S4 - Strategy Planner
        strategy = self._strategy_phase(decision)
        self.Theta.event("slow_loop_S4_strategy", strategy=strategy)

        # 🧩 S6 - Strategic Simulation Engine (SSE)
        intent_ctx = {
            "motivation": motivation,
            "strategy": strategy,
            "decision": decision,
        }
        try:
            sse_result = self.sse.simulate(intent=intent, context=intent_ctx)
        except Exception as e:
            log.warning(f"[SLOW_LOOP] SSE simulation error: {e}")
            sse_result = {"best_path": [], "best_utility": 0.0}

        # 🔁 S5 - Reflection Feedback
        reflection = self._reflection_phase(decision, strategy)
        self.Theta.event("slow_loop_S5_reflection", reflection=reflection)

        # 🔂 Apply Reflection feedback into SSE (R6)
        try:
            if isinstance(reflection, dict):
                root = self.sse._seed_root(intent, intent_ctx)
                self.sse.apply_reflection(root, reflection)
        except Exception as e:
            log.warning(f"[SLOW_LOOP] SSE reflection integration failed: {e}")

        # Consolidate metrics and (throttled) RMC push
        rho = float(decision.get("confidence", 0.6))
        entropy = float(decision.get("entropy", 0.5))
        sqi = float(decision.get("reflex_sqi", decision.get("SQI", 0.6)) or 0.6)
        delta = float(decision.get("ΔΦ", 0.05))

        self._throttled_rmc_push(
            rho=rho,
            entropy=entropy,
            sqi=sqi,
            delta=delta,
            source="deep_resonance_loop",
        )

        # 🌿 Light semantic drift correction (kept, but controlled via env probability)
        try:
            if THETA_STABILIZE_PROB > 0 and random.random() < THETA_STABILIZE_PROB:
                self.rmc.stabilize(decay_rate=0.0008)
        except Exception:
            pass

        duration = round(time.time() - start_time, 3)

        # 🧭 Dashboard telemetry logging (rate-limited)
        self._dash_append(
            "deep_resonance_loop_complete",
            {
                "timestamp": time.time(),
                "event": "deep_resonance_loop_complete",
                "query": query,
                "duration": duration,
                "confidence": rho,
                "entropy": entropy,
                "SQI": sqi,
                "ΔΦ": delta,
                "strategy": strategy,
            },
            min_interval_s=THETA_DASH_WRITE_MIN_INTERVAL_S,
        )

        payload = {
            "mode": "slow",
            "query": query,
            "motivation": motivation,
            "intent": intent,
            "decision": decision,
            "strategy": strategy,
            "sse": sse_result,
            "reflection": reflection,
            "duration": duration,
            "timestamp": time.time(),
        }

        log.info(f"[SLOW_LOOP🌌] Completed Deep Resonance loop in {duration}s")
        return payload

    # ───────────────────────────────────────────
    # 🧩 Sub-Phases
    # ───────────────────────────────────────────
    def _motivation_phase(self, query: str) -> Dict[str, Any]:
        """S1 - Motivation: derive internal drive state from context."""
        try:
            vec = self.motivation.output_vector(context=query)
        except Exception:
            vec = self.motivation.output_vector()
        return {"motivation_vector": vec, "source": "MotivationLayer"}

    def _intent_phase(self, motivation: Dict[str, Any]) -> Dict[str, Any]:
        """S2 - Intent: convert motivation into actionable symbolic intent."""
        try:
            intent = self.intent.generate_intent(motivation=motivation)
        except Exception:
            intent = {"intent": "general_reflection"}
        return intent

    def _reasoner_phase(self, intent: Dict[str, Any], motivation: Dict[str, Any]) -> Dict[str, Any]:
        """S3 - Reasoner: perform symbolic reasoning on intent + motivation."""
        try:
            decision = self.reasoner.reason(intent, motivation)

            # 🧩 Normalize any non-standard or nested structure
            if isinstance(decision, dict):
                if "decision" in decision and isinstance(decision["decision"], dict):
                    decision = decision["decision"]

                decision = {
                    "confidence": float(decision.get("confidence", 0.5)),
                    "entropy": float(decision.get("entropy", 0.5)),
                    "ΔΦ": float(decision.get("ΔΦ", 0.1)),
                    "goal": decision.get("goal", "undefined"),
                    # preserve SQI-like signals if present
                    "reflex_sqi": float(decision.get("reflex_sqi", decision.get("SQI", 0.6)) or 0.6),
                }

            elif isinstance(decision, (int, float)):
                decision = {"confidence": float(decision), "entropy": 0.5, "ΔΦ": 0.1, "goal": "undefined", "reflex_sqi": 0.6}
            else:
                decision = {"confidence": 0.5, "entropy": 0.5, "ΔΦ": 0.1, "goal": "undefined", "reflex_sqi": 0.6}

        except Exception as e:
            log.warning(f"[SLOW_LOOP] Reasoner error: {e}")
            decision = {"confidence": 0.5, "entropy": 0.5, "ΔΦ": 0.1, "goal": "undefined", "reflex_sqi": 0.6}

        return decision

    def _strategy_phase(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """S4 - Strategy Planner: derive multi-step resonant plan from decision output."""
        try:
            if isinstance(decision, dict):
                goal_str = decision.get("goal") or f"decision_conf_{decision.get('confidence', 0.5):.2f}"
            else:
                goal_str = str(decision)

            strategy = self.strategy.generate_plan(goal_str)

            if not isinstance(strategy, dict):
                strategy = {
                    "plan": [str(strategy)],
                    "resonance_score": 0.5,
                    "predicted_confidence": 0.5,
                }

        except Exception as e:
            log.warning(f"[SLOW_LOOP] Strategy planner error: {e}")
            goal_str = "undefined"
            strategy = {
                "plan": ["reflect", "stabilize", "store"],
                "resonance_score": 0.5,
                "predicted_confidence": 0.5,
            }

        # RMC coupling (safe) — no extra force writes; RMC.save() is rate-limited now anyway.
        try:
            self.rmc.update_resonance_link(
                f"strategy_{goal_str}",
                "plan",
                float(strategy.get("resonance_score", 0.5)),
            )
            self.rmc.save()
        except Exception as e:
            log.warning(f"[RMC] Strategy link error: {e}")

        return strategy

    def _reflection_phase(self, decision: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """S5 - Reflection Feedback: consolidate reasoning and feed back to RMC."""
        try:
            if hasattr(self.reflection, "run_feedback"):
                reflection = self.reflection.run_feedback(decision, strategy)
            elif hasattr(self.reflection, "reflect"):
                reflection = self.reflection.reflect(decision)
            else:
                reflection = {"insight": "undefined", "ΔΦ": 0.05}
        except Exception as e:
            log.warning(f"[SLOW_LOOP] Reflection feedback error: {e}")
            reflection = {"insight": "stabilized", "ΔΦ": 0.05}

        # Feed Θ coherence + (throttled) RMC reinforcement
        try:
            rho = float(decision.get("confidence", 0.6))
            sqi = float(decision.get("reflex_sqi", decision.get("SQI", 0.6)) or 0.6)
            delta = float(reflection.get("ΔΦ", 0.05))
            entropy = float(decision.get("entropy", 0.5))

            self._throttled_rmc_push(
                rho=rho,
                entropy=entropy,
                sqi=sqi,
                delta=delta,
                source="reflection_phase",
            )
        except Exception as e:
            log.warning(f"[RMC] Reflection push error: {e}")

        return reflection

    # Compatibility alias
    def slow_loop(self, query: str) -> Dict[str, Any]:
        """Legacy alias - routes to deep_resonance_loop()"""
        return self.deep_resonance_loop(query)

    # ───────────────────────────────────────────
    def think(self, input_signal: str) -> Dict[str, Any]:
        """Master entrypoint - chooses FAST or SLOW loop."""
        entropy = random.uniform(0.3, 0.8)
        mode = self.classify_complexity(input_signal, entropy)

        self.Theta.event("thinking_loop_start", input=input_signal, entropy=entropy, mode=mode)
        result = self.fast_loop(input_signal) if mode == "fast" else self.slow_loop(input_signal)
        self.Theta.event("thinking_loop_end", mode=mode, result=result)

        # Log mode transition to dashboard feed (rate-limited)
        now = time.time()
        if (now - self._last_mode_log_ts) >= THETA_MODELOG_MIN_INTERVAL_S:
            self._last_mode_log_ts = now
            self._dash_append(
                "thinking_mode_switch",
                {
                    "timestamp": now,
                    "event": "thinking_mode_switch",
                    "mode": mode,
                    "input": input_signal,
                    "entropy": entropy,
                    "namespace": self.Theta.namespace,
                },
                min_interval_s=0.0,  # already rate-limited by _last_mode_log_ts
            )

        return result

    # ------------------------------------------------------------
    # 🧘 Compatibility layer for CLI (think slow / think fast)
    # ------------------------------------------------------------
    def run_loop(self, mode: str = "slow", topic: str = "general"):
        """
        Backward-compatible wrapper for CLI commands.
        Executes the main reflective or reflexive thinking loop.
        """
        try:
            mode = (mode or "slow").lower()
            if mode == "fast":
                if hasattr(self, "reflex_loop"):
                    return self.reflex_loop(topic=topic)
                return self.fast_loop(topic)
            if mode == "slow":
                return self.deep_resonance_loop(topic)
            log.warning(f"[Θ] Unknown run_loop mode '{mode}', defaulting to FAST.")
            return self.fast_loop(topic)
        except Exception as e:
            log.warning(f"[Θ] run_loop error ({mode}): {e}")
            return {"mode": mode, "topic": topic, "error": str(e)}

    # ------------------------------------------------------------
    # 🧘 Default reflection / reflex loops for AION CLI
    # ------------------------------------------------------------
    def reflex_loop(self, topic: str = "general"):
        """FAST/reflex loop shim for CLI 'think fast' - routes to fast_loop()."""
        try:
            log.info(f"[Θ] Reflex loop engaged - topic: {topic}")
            start = time.time()

            # Start with the normal fast loop
            result = self.fast_loop(topic)

            # Optional math-like interpretation, but SAFE (no eval)
            if isinstance(topic, str):
                expr = topic.replace("x", "*").replace("X", "*").strip()
                computed = _safe_calc(expr)
                if computed is not None:
                    if not QUIET:
                        print(f"[💡 Reflex Reasoning] {topic} = {computed}")
                    result = {"topic": topic, "result": computed, "mode": "fast_math"}

            duration = round(time.time() - start, 3)

            if not QUIET:
                print(f"[Θ] Reflex loop engaged - topic: {topic}")
                print(f"[Θ] Reflex computation 1/2 - response vector aligned.")
                print(f"[Θ] Reflex computation 2/2 - response vector aligned.")
                print(f"[Θ] Reflex reasoning complete -> topic '{topic}' integrated. (duration={duration}s)\n")

            return result
        except Exception as e:
            log.warning(f"[Θ] Reflex loop error: {e}")
            return {
                "mode": "fast",
                "stimulus": topic,
                "response": "quick_recall",
                "error": str(e),
            }

    # ------------------------------------------------------------
    # 🌌 True reflection cycle - activates full SLOW_LOOP
    # ------------------------------------------------------------
    def reflect_cycle(self, topic: str = "general"):
        """
        Execute a full deep resonance reasoning cycle.
        Invoked by AION Cognitive Bridge (CLI 'reflect' command).
        Routes through: Motivation -> Intent -> Reasoner -> Strategy -> Reflection.
        """
        log.info(f"[Θ] Reflection cycle started for topic: '{topic}'")
        try:
            result = self.deep_resonance_loop(topic)
            if not QUIET:
                print(
                    f"[Θ] Reflection cycle complete - topic '{topic}' integrated "
                    f"(duration={round(result.get('duration', 0), 3)}s)\n"
                )
            return result
        except Exception as e:
            log.warning(f"[Θ] Reflection cycle failed: {e}")
            if not QUIET:
                print("⚠️ Reflection failed - falling back to reflex loop.")
            return self.reflex_loop(topic=topic)

    # ─────────────────────────────────────────────
    # Legacy alias - support older commands
    # ─────────────────────────────────────────────
    def reflect_loop(self, topic=None):
        """
        Legacy compatibility for older AION commands.
        Maps reflect_loop -> reflex_loop so 'reflect' command still works.
        """
        return self.reflex_loop(topic=topic)


# ─────────────────────────────────────────────
# Backwards-compat export
# ─────────────────────────────────────────────
__all__ = ["ThinkingLoop", "ThetaOrchestrator"]
ThetaOrchestrator = ThinkingLoop


# ─────────────────────────────────────────────
# Demo Mode
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    loop = ThinkingLoop(auto_tick=False)
    print("🧠 Θ Orchestrator - Cognitive Routing Demo\n")

    while True:
        try:
            query = input("🗣 Input signal (or 'exit'): ")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Exiting.")
            break
        if query.lower().strip() == "exit":
            break
        output = loop.think(query)
        print("->", output)
        print()