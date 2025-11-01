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

import json, time, logging
from statistics import fmean
from pathlib import Path
from typing import Dict, Any, List

from backend.modules.aion_cognition.reflex_memory import ReflexMemory
from backend.modules.aion_cognition.rule_recipe_engine import RuleRecipeEngine
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.soul.soul_laws import validate_ethics

log = logging.getLogger(__name__)


class TessarisReasoner:
    def __init__(self):
        self.recipes = RuleRecipeEngine()
        self.reflex = ReflexMemory()
        self.rmc = ResonantMemoryCache()
        self.heartbeat = ResonanceHeartbeat(namespace="reasoner", base_interval=1.8)
        self.log_path = Path("data/reasoning/tessaris_reasoner_trace.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("⚖️ TessarisReasoner initialized (Phase 63 Reflex-Reasoner Fusion + A3 Enhancements)")

    # ------------------------------------------------------------
    # 🔍 Context Assembly
    # ------------------------------------------------------------
    def assemble_context(self, intent: Dict[str, Any], motivation: Dict[str, Any]) -> Dict[str, Any]:
        """Combine intent + motivation + last reflex state into a unified reasoning context."""
        reflex_state = self.reflex.get_last_state() or {}
        context = {
            "intent_goal": intent.get("goal", "undefined"),
            "intent_why": intent.get("why"),
            "motivation": motivation,
            "reflex_feedback": reflex_state,
            "timestamp": time.time(),
        }
        return context

    # ------------------------------------------------------------
    # 🧩 Rule Evaluation Core
    # ------------------------------------------------------------
    def evaluate_rules(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply loaded RuleRecipes to the given reasoning context."""
        rules = self.recipes.load_active_rules()
        applied = []
        for rule in rules:
            try:
                result = self.recipes.apply_rule(rule, context)
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
        sqi = float(reflex.get("sqi", 0.6))
        delta_phi = float(reflex.get("delta_phi", 0.0))
        entropy = float(reflex.get("entropy", 0.5))

        # ─────────────────────────────────────────────────────────
        # 📊 Phase A3 Additions: Ethical + Contradiction Weighting
        # ─────────────────────────────────────────────────────────
        ethics_list = [float(r.get("ethics", 1.0)) for r in applied if isinstance(r.get("ethics", 1.0), (int, float))]
        logic_list = [float(r.get("logic", 1.0)) for r in applied if isinstance(r.get("logic", 1.0), (int, float))]

        ethics_score = fmean(ethics_list) if ethics_list else 1.0
        logic_score = fmean(logic_list) if logic_list else 1.0
        motivation_values = [float(v) for v in motivation.values() if isinstance(v, (int, float))]
        motivation_factor = fmean(motivation_values) if motivation_values else 0.5

        # Detect contradictions among rule outputs
        contradictions = [r for r in applied if r.get("conflict", False)]
        contradiction_ratio = len(contradictions) / len(applied) if applied else 0.0
        contradiction_penalty = contradiction_ratio * 0.3

        # Integrate RuleBookTree scoring
        try:
            from backend.modules.aion_cognition.rulebook_tree import RuleBookTree
            rbt = RuleBookTree()
            rbt_score = float(rbt.evaluate_context(ctx))
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
        decision = {
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
                if "value" in val:
                    decision[key] = float(val["value"])
                else:
                    try:
                        decision[key] = float(list(val.values())[0])
                    except Exception:
                        decision[key] = 0.5

        # Update ResonantMemoryCache + emit feedback
        try:
            self.rmc.push_sample(rho=coherence, entropy=entropy, sqi=sqi, delta=delta_phi, source="reasoner")
            self.rmc.save()
        except Exception as e:
            log.warning(f"[Reasoner] ⚠️ RMC feedback error: {e}")

        # Θ pulse + decision event
        pulse = self.heartbeat.tick()
        pulse.update({
            "Φ_coherence": coherence,
            "Φ_entropy": entropy,
            "sqi": sqi,
            "resonance_delta": delta_phi,
        })
        self.heartbeat.event(
            "reasoning_decision",
            goal=intent.get("goal"),
            confidence=adjusted_score,
            ethics=ethics_score,
            logic=logic_score,
            contradictions=contradiction_ratio,
        )

        # Log trace
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
            sqi = reflex_data.get("sqi", 0.6)
            delta = reflex_data.get("delta_phi", 0.0)
            entropy = reflex_data.get("entropy", 0.5)
            self.rmc.push_sample(sqi=sqi, delta=delta, entropy=entropy, source="reflex_feedback")
            self.rmc.save()
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
            motivation = context.get("motivation", {})
            intent = context.get("intent", {})
            reflex = context.get("reflex", {})
            timestamp = context.get("timestamp")

            sqi = reflex.get("sqi", 0.6)
            entropy = reflex.get("entropy", 0.5)
            delta = reflex.get("delta_phi", 0.0)

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