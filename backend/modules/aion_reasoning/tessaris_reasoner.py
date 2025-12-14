#!/usr/bin/env python3
# ============================================================
# ⚖️ TessarisReasoner - Phase 63 Reflex-Reasoner Fusion Core (A3 Complete)
# ============================================================
# Inner reasoning cortex for Tessaris Engine.
# Responsibilities:
#   * Load & apply RuleRecipes (R7) from RuleRecipeEngine
#   * Integrate ReflexArc feedback (SQI, ΔΦ, entropy drift)
#   * Perform ethical / logical / motivational balancing
#   * Detect contradictions + apply penalty weighting
#   * Integrate RuleBookTree meta-score for reasoning coherence
#   * Emit Θ decision events for StrategyPlanner
# ============================================================

import os
import json
import time
import logging
from statistics import fmean
from pathlib import Path
from typing import Dict, Any, List

from backend.modules.aion_cognition.reflex_memory import ReflexMemory
from backend.modules.aion_cognition.rule_recipe_engine import RuleRecipeEngine
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.soul.soul_laws import validate_ethics

log = logging.getLogger(__name__)

QUIET = os.getenv("AION_QUIET_MODE", "0") == "1"

# Throttle to stop hot loops from spamming RMC + disk
REASONER_RMC_PUSH_MIN_INTERVAL_S = float(os.getenv("AION_REASONER_RMC_PUSH_MIN_INTERVAL_S", "5"))
REASONER_TRACE_WRITE_MIN_INTERVAL_S = float(os.getenv("AION_REASONER_TRACE_WRITE_MIN_INTERVAL_S", "2"))


class TessarisReasoner:
    def __init__(self):
        self.recipes = RuleRecipeEngine()
        self.reflex = ReflexMemory()
        self.rmc = ResonantMemoryCache()
        self.heartbeat = ResonanceHeartbeat(namespace="reasoner", base_interval=1.8)
        self.log_path = Path("data/reasoning/tessaris_reasoner_trace.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self._last_rmc_push: Dict[str, float] = {}
        self._last_trace_write_ts: float = 0.0

        log.info("⚖️ TessarisReasoner initialized (Phase 63 Reflex-Reasoner Fusion + A3 Enhancements)")

    # ------------------------------------------------------------
    # 🔧 Internal throttles
    # ------------------------------------------------------------
    def _throttled_rmc_push(
        self,
        *,
        rho: float,
        entropy: float,
        sqi: float,
        delta: float,
        source: str,
        min_interval_s: float = REASONER_RMC_PUSH_MIN_INTERVAL_S,
    ) -> bool:
        now = time.time()
        last = self._last_rmc_push.get(source, 0.0)
        if (now - last) < min_interval_s:
            return False
        self._last_rmc_push[source] = now
        self.rmc.push_sample(rho=rho, entropy=entropy, sqi=sqi, delta=delta, source=source)
        # RMC.save() is already rate-limited in your updated RMC file, so this is safe.
        self.rmc.save()
        return True

    def _safe_float(self, v: Any, default: float) -> float:
        try:
            if isinstance(v, dict):
                if "value" in v:
                    return float(v["value"])
                # try first numeric-ish value
                for vv in v.values():
                    if isinstance(vv, (int, float, str)):
                        return float(vv)
                return default
            return float(v)
        except Exception:
            return default

    # ------------------------------------------------------------
    # 🔍 Context Assembly
    # ------------------------------------------------------------
    def assemble_context(self, intent: Dict[str, Any], motivation: Dict[str, Any]) -> Dict[str, Any]:
        """Combine intent + motivation + last reflex state into a unified reasoning context."""
        reflex_state = self.reflex.get_last_state() or {}
        return {
            "intent_goal": intent.get("goal", "undefined"),
            "intent_why": intent.get("why"),
            "motivation": motivation,
            "reflex_feedback": reflex_state,
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------
    # 🧩 Rule Evaluation Core
    # ------------------------------------------------------------
    def evaluate_rules(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply loaded RuleRecipes to the given reasoning context."""
        rules = self.recipes.load_active_rules()
        applied: List[Dict[str, Any]] = []
        for rule in rules:
            try:
                result = self.recipes.apply_rule(rule, context)
                if isinstance(result, dict):
                    applied.append(result)
            except Exception as e:
                log.warning(f"[Reasoner] rule error: {e}")
        return applied

    # ------------------------------------------------------------
    # 🧠 Core Reasoning Cycle
    # ------------------------------------------------------------
    def reason(self, intent: Dict[str, Any], motivation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main reasoning routine - harmonizes reflex data, motivation, ethics, and logic.
        Returns a decision dict ready for StrategyPlanner or ActionSwitch.
        """
        ctx = self.assemble_context(intent, motivation)
        applied = self.evaluate_rules(ctx)

        # Extract reflex + resonance metrics safely
        reflex = ctx.get("reflex_feedback", {}) or {}
        sqi = self._safe_float(reflex.get("sqi", 0.6), 0.6)
        delta_phi = self._safe_float(reflex.get("delta_phi", 0.0), 0.0)
        entropy = self._safe_float(reflex.get("entropy", 0.5), 0.5)

        # ─────────────────────────────────────────────────────────
        # 📊 Phase A3 Additions: Ethical + Contradiction Weighting
        # ─────────────────────────────────────────────────────────
        ethics_list = [
            self._safe_float(r.get("ethics", 1.0), 1.0)
            for r in applied
            if isinstance(r, dict)
        ]
        logic_list = [
            self._safe_float(r.get("logic", 1.0), 1.0)
            for r in applied
            if isinstance(r, dict)
        ]

        ethics_score = fmean(ethics_list) if ethics_list else 1.0
        logic_score = fmean(logic_list) if logic_list else 1.0

        motivation_values: List[float] = []
        if isinstance(motivation, dict):
            for v in motivation.values():
                if isinstance(v, (int, float)):
                    motivation_values.append(float(v))
        motivation_factor = fmean(motivation_values) if motivation_values else 0.5

        # Detect contradictions among rule outputs
        contradictions = [r for r in applied if isinstance(r, dict) and r.get("conflict", False)]
        contradiction_ratio = (len(contradictions) / len(applied)) if applied else 0.0
        contradiction_penalty = contradiction_ratio * 0.3

        # Integrate RuleBookTree scoring
        try:
            from backend.modules.aion_cognition.rulebook_tree import RuleBookTree

            rbt = RuleBookTree()
            rbt_score = self._safe_float(rbt.evaluate_context(ctx), 0.8)
        except Exception:
            rbt_score = 0.8  # fallback

        # Compute unified coherence
        coherence = round((ethics_score + logic_score + motivation_factor + sqi + rbt_score) / 5.0, 3)
        drift_penalty = abs(delta_phi) * 0.2
        adjusted_score = round(max(0.0, min(1.0, coherence - drift_penalty - contradiction_penalty)), 3)

        # Ethical validation (via SoulLaws)
        decision_allowed = validate_ethics(intent.get("goal", ""))

        # ─────────────────────────────────────────────────────────
        # 🧩 Build decision dictionary
        # ─────────────────────────────────────────────────────────
        decision: Dict[str, Any] = {
            "goal": intent.get("goal"),
            "why": intent.get("why"),
            "allowed": bool(decision_allowed),
            "confidence": adjusted_score,
            "ethics_score": ethics_score,
            "logic_score": logic_score,
            "motivation_factor": motivation_factor,
            "rbt_score": rbt_score,
            "reflex_sqi": sqi,
            "ΔΦ": delta_phi,
            "entropy": entropy,
            "contradiction_ratio": round(contradiction_ratio, 3),
            "timestamp": time.time(),
        }

        # Normalize nested dict fields (fixes "must be real number, not dict")
        for key, val in list(decision.items()):
            if isinstance(val, dict):
                decision[key] = self._safe_float(val, 0.5)

        # Update ResonantMemoryCache + emit feedback (THROTTLED)
        try:
            self._throttled_rmc_push(
                rho=coherence,
                entropy=entropy,
                sqi=sqi,
                delta=delta_phi,
                source="reasoner",
            )
        except Exception as e:
            log.warning(f"[Reasoner] ⚠️ RMC feedback error: {e}")

        # Θ pulse + decision event
        pulse = self.heartbeat.tick()
        try:
            pulse.update(
                {
                    "Φ_coherence": coherence,
                    "Φ_entropy": entropy,
                    "sqi": sqi,
                    "resonance_delta": delta_phi,
                }
            )
        except Exception:
            pass

        self.heartbeat.event(
            "reasoning_decision",
            goal=intent.get("goal"),
            confidence=adjusted_score,
            ethics=ethics_score,
            logic=logic_score,
            contradictions=contradiction_ratio,
        )

        # Log trace (rate-limited)
        now = time.time()
        if (now - self._last_trace_write_ts) >= REASONER_TRACE_WRITE_MIN_INTERVAL_S:
            self._last_trace_write_ts = now
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(decision) + "\n")
            except Exception as e:
                log.warning(f"[Reasoner] ⚠️ Failed to log reasoning trace: {e}")

        log.info(
            f"[Reasoner] goal={intent.get('goal')} "
            f"allowed={decision_allowed} conf={adjusted_score:.3f} "
            f"ΔΦ={delta_phi:.3f} contradictions={contradiction_ratio:.2f}"
        )

        return decision

    # ------------------------------------------------------------
    def feedback_from_reflex(self, reflex_data: Dict[str, Any]):
        """Integrate live Reflex feedback (e.g., from ReflexExecutor)."""
        try:
            sqi = self._safe_float(reflex_data.get("sqi", 0.6), 0.6)
            delta = self._safe_float(reflex_data.get("delta_phi", 0.0), 0.0)
            entropy = self._safe_float(reflex_data.get("entropy", 0.5), 0.5)

            # rho is not provided here; use sqi as a reasonable proxy
            self._throttled_rmc_push(
                rho=sqi,
                entropy=entropy,
                sqi=sqi,
                delta=delta,
                source="reflex_feedback",
            )

            log.debug(f"[Reasoner] Reflex feedback integrated SQI={sqi:.3f} ΔΦ={delta:.3f}")
        except Exception as e:
            log.warning(f"[Reasoner] feedback_from_reflex error: {e}")

    # ------------------------------------------------------------
    def integrate(self, context: dict) -> dict:
        """
        Unified integration entrypoint for ReasonerBridge.
        Combines motivation, intent, reflex, and reflection context,
        performs weighted reasoning, and emits a Θ decision state.
        """
        try:
            motivation = context.get("motivation", {}) or {}
            intent = context.get("intent", {}) or {}
            reflex = context.get("reflex", {}) or {}
            timestamp = context.get("timestamp", time.time())

            sqi = self._safe_float(reflex.get("sqi", 0.6), 0.6)
            entropy = self._safe_float(reflex.get("entropy", 0.5), 0.5)
            delta = self._safe_float(reflex.get("delta_phi", 0.0), 0.0)

            reasoning_score = round((sqi + (1 - entropy) - delta) / 2, 3)
            mood = "stable"
            if reasoning_score >= 0.75:
                mood = "positive"
            elif reasoning_score < 0.5:
                mood = "critical"

            decision = {
                "timestamp": timestamp,
                "reasoning_score": reasoning_score,
                "mood": mood,
                "context_keys": list(context.keys()),
            }

            self.heartbeat.event("reasoning_integration", score=reasoning_score, mood=mood)
            return decision

        except Exception as e:
            log.warning(f"[TessarisReasoner] Integration failed: {e}")
            return {"error": str(e), "reasoning_score": 0.0}