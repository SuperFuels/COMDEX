#!/usr/bin/env python3
# ============================================================
# ⚖️ TessarisReasoner — Phase 63 Reflex–Reasoner Fusion Core
# ============================================================
# Inner reasoning cortex for Tessaris Engine.
# Responsibilities:
#   • Load & apply RuleRecipes (R7) from RuleRecipeEngine
#   • Integrate ReflexArc feedback (SQI, ΔΦ, entropy drift)
#   • Perform ethical / logical / motivational balancing
#   • Emit decisions + confidence for StrategyPlanner
#   • Feed reasoning deltas back to Reflection & Heartbeat
# ============================================================

import json, time, random, logging
from statistics import fmean
from pathlib import Path
from typing import Dict, Any, List, Optional

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
        log.info("⚖️ TessarisReasoner initialized (Phase 63 Reflex–Reasoner Fusion)")

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
        Main reasoning routine — harmonizes reflex data, motivation, and ethics.
        Returns a decision dict ready for StrategyPlanner or ActionSwitch.
        """
        ctx = self.assemble_context(intent, motivation)
        applied = self.evaluate_rules(ctx)

        # Extract reflex + resonance metrics
        reflex = ctx["reflex_feedback"]
        sqi = reflex.get("sqi", 0.6)
        delta_phi = reflex.get("delta_phi", 0.0)
        entropy = reflex.get("entropy", 0.5)

        # Weighted reasoning coherence
        ethics_score = fmean([r.get("ethics", 1.0) for r in applied]) if applied else 1.0
        logic_score = fmean([r.get("logic", 1.0) for r in applied]) if applied else 1.0
        motivation_factor = fmean(list(motivation.values())) if motivation else 0.5

        coherence = round((ethics_score + logic_score + motivation_factor + sqi) / 4.0, 3)
        drift_penalty = abs(delta_phi) * 0.2
        adjusted_score = round(max(0.0, min(1.0, coherence - drift_penalty)), 3)

        # Ethical validation using SoulLaws
        decision_allowed = validate_ethics(intent.get("goal", ""))

        decision = {
            "goal": intent.get("goal"),
            "why": intent.get("why"),
            "allowed": bool(decision_allowed),
            "confidence": adjusted_score,
            "ethics_score": ethics_score,
            "logic_score": logic_score,
            "motivation_factor": motivation_factor,
            "reflex_sqi": sqi,
            "ΔΦ": delta_phi,
            "entropy": entropy,
            "timestamp": time.time(),
        }

        # Update ResonantMemoryCache
        self.rmc.push_sample(rho=coherence, entropy=entropy, sqi=sqi, delta=delta_phi, source="reasoner")
        self.rmc.save()

        # Emit Θ pulse feedback
        pulse = self.heartbeat.tick()
        pulse.update({
            "Φ_coherence": coherence,
            "Φ_entropy": entropy,
            "sqi": sqi,
            "resonance_delta": delta_phi,
        })

        # Log trace
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision) + "\n")

        log.info(f"[Reasoner] goal={intent.get('goal')} allowed={decision_allowed} conf={adjusted_score:.3f}")
        return decision

    # ------------------------------------------------------------
    def feedback_from_reflex(self, reflex_data: Dict[str, Any]):
        """
        Accepts live Reflex feedback (e.g. from ReflexExecutor) and updates caches.
        """
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
            reflection = context.get("reflection", {})
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

            # log / store decision if desired
            if hasattr(self, "logger"):
                self.logger.info(f"[TessarisReasoner] Integrated context → score={reasoning_score:.3f}, mood={mood}")

            return decision

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"[TessarisReasoner] Integration failed: {e}")
            return {"error": str(e), "reasoning_score": 0.0}