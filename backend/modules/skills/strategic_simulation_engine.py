#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧩 Strategic Simulation Engine (SSE) — Phase 2 Expansion
────────────────────────────────────────────────────────────
Enhancements:
  • Dynamic reflection re-ranking (ΔSQI, ΔEthics, penalize/boost)
  • Branch variation weights (risk, cost, reward, entropy)
  • Context-aware intent expansion (RMC + strategy cues)
────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random, json, math, logging
from pathlib import Path

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 🧱 Scenario Node
# ─────────────────────────────────────────────
@dataclass
class ScenarioNode:
    id: str
    state: Dict[str, Any]
    action: Optional[str] = None
    depth: int = 0
    prob: float = 1.0
    sqi: float = 0.5
    ethics: float = 0.7
    goal_fit: float = 0.6
    reward: float = 0.5
    risk: float = 0.2
    cost: float = 0.1
    entropy: float = 0.3
    utility: float = 0.0
    children: List["ScenarioNode"] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────
# ⚙️ Strategic Simulation Engine
# ─────────────────────────────────────────────
class StrategicSimulationEngine:
    """Builds + scores scenario trees; integrates Reflection feedback."""

    def __init__(self, *, depth: int = 3, breadth: int = 4, seed: int = 42, quiet: Optional[bool] = None):
        import os
        self.depth = int(depth)
        self.breadth = int(breadth)
        random.seed(seed)
        self.quiet = (os.getenv("AION_SILENT_MODE", "0") == "1") if quiet is None else quiet

        # lazy imports to minimize circular deps
        from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
        from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
        self.rmc = ResonantMemoryCache()
        self.Theta = ResonanceHeartbeat(namespace="sse", base_interval=1.5, auto_tick=False)

        try:
            from backend.modules.aion_reflection.rule_feedback_engine import RuleFeedbackEngine
            self.ethics_engine = RuleFeedbackEngine()
        except Exception:
            self.ethics_engine = None

        self.out_tree = Path("data/analysis/sse_tree.json")
        self.out_best = Path("data/analysis/sse_best_path.json")
        self.out_tree.parent.mkdir(parents=True, exist_ok=True)

        log.info("🧩 SSE initialized (Phase 2 — reflection, weights, context)")

    # ─────────────────────────────────────────────
    # 🎬 Entry Point
    # ─────────────────────────────────────────────
    def simulate(self, *, intent: Dict[str, Any], context: Dict[str, Any], reflection: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        root = self._seed_root(intent, context)
        self._expand_tree(root, depth=self.depth, breadth=self.breadth, intent=intent, context=context)
        self._score_tree(root, intent=intent, context=context)
        best_path, best_u = self._extract_best_path(root)

        # optional reflection re-ranking
        if reflection:
            self.apply_reflection(root, reflection)
            best_path, best_u = self._extract_best_path(root)
            self.Theta.event("sse_reflected", best_utility=round(best_u, 3))

        self._persist_tree(root, best_path, best_u)
        self.Theta.event("sse_completed", best_utility=round(best_u, 3), what=intent.get("what"), why=intent.get("why"))

        return {
            "best_path": [n.action for n in best_path if n.action],
            "best_utility": best_u,
            "root": self._to_dict(root),
        }

    # ─────────────────────────────────────────────
    # 🌱 Step 1: Tree Building
    # ─────────────────────────────────────────────
    def _seed_root(self, intent, context) -> ScenarioNode:
        return ScenarioNode(
            id="root",
            state={"goal": intent.get("what"), "why": intent.get("why"), "ctx": context},
            depth=0,
            prob=1.0,
            action=None,
        )

    def _candidate_actions(self, state: Dict[str, Any], intent: Dict[str, Any]) -> List[str]:
        """Generate candidate actions dynamically using context + intent."""
        base = (intent.get("what") or "goal").lower()
        actions = [
            f"research_{base}",
            f"prototype_{base}",
            f"deploy_{base}",
            f"measure_{base}",
            f"iterate_{base}",
        ]

        # Context-aware intent expansion
        why = (intent.get("why") or "").lower()
        try:
            rho = self.rmc.average_rho()
            entropy = self.rmc.average_entropy()
        except Exception:
            rho, entropy = 0.6, 0.4

        if "optimize" in why:
            actions.extend([f"refine_{base}", f"stabilize_{base}"])
        elif "explore" in why:
            actions.extend([f"scan_{base}", f"expand_{base}"])
        elif "learn" in why:
            actions.extend([f"analyze_{base}", f"simulate_{base}"])

        # adjust breadth limit
        random.shuffle(actions)
        return actions[: self.breadth]

    def _expand_tree(self, node: ScenarioNode, *, depth: int, breadth: int, intent: Dict[str, Any], context: Dict[str, Any]):
        if node.depth >= depth:
            return
        actions = self._candidate_actions(node.state, intent)
        probs = self._softmax([random.uniform(0.7, 1.0) for _ in actions])

        for i, (act, p) in enumerate(zip(actions, probs)):
            child = ScenarioNode(
                id=f"{node.id}.{i}",
                state=self._transition(node.state, act),
                action=act,
                depth=node.depth + 1,
                prob=p,
            )
            node.children.append(child)
            self._expand_tree(child, depth=depth, breadth=breadth, intent=intent, context=context)

    def _transition(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Simulate environment transition with risk/reward parameters."""
        s = dict(state)
        s["last_action"] = action
        s["risk"] = round(random.uniform(0.05, 0.35), 3)
        s["cost"] = round(random.uniform(0.1, 0.4), 3)
        s["reward"] = round(random.uniform(0.4, 0.9), 3)
        s["entropy"] = round(random.uniform(0.1, 0.5), 3)
        return s

    # ─────────────────────────────────────────────
    # 🧮 Step 2: Evaluation
    # ─────────────────────────────────────────────
    def _score_tree(self, node: ScenarioNode, *, intent, context):
        for c in node.children:
            self._score_tree(c, intent=intent, context=context)

        node.sqi = self._sqi_estimate(node, intent, context)
        node.ethics = self._ethics_score(node, intent, context)
        node.goal_fit = self._goal_fit(node, intent)

        # copy branch variation parameters
        node.reward = node.state.get("reward", 0.5)
        node.risk = node.state.get("risk", 0.2)
        node.cost = node.state.get("cost", 0.1)
        node.entropy = node.state.get("entropy", 0.3)

        node.utility = self._utility(node)

    def _sqi_estimate(self, node, intent, context) -> float:
        try:
            base = self.rmc.average_sqi()
        except Exception:
            base = 0.5
        if node.action and (intent.get("why") or "") in node.action:
            base += 0.03
        return round(max(0.0, min(1.0, base)), 3)

    def _ethics_score(self, node, intent, context) -> float:
        try:
            if self.ethics_engine:
                res = self.ethics_engine.assess(action=node.action or "noop", context=node.state)
                val = float(res.get("ethics_score", 0.7))
                return round(max(0.0, min(1.0, val)), 3)
        except Exception:
            pass
        return 0.7

    def _goal_fit(self, node, intent) -> float:
        goal = (intent.get("what") or "").lower()
        act = (node.action or "").lower()
        return 0.9 if goal and goal in act else 0.6

    def _utility(self, node) -> float:
        """Weighted composite score using new branch variation weights."""
        w_sqi, w_eth, w_fit, w_rew = 0.35, 0.25, 0.20, 0.20
        u = w_sqi * node.sqi + w_eth * node.ethics + w_fit * node.goal_fit + w_rew * node.reward
        u *= (1 - 0.5 * (node.risk + node.cost))  # apply penalties
        u *= max(0.5, min(1.0, node.prob + 0.2))
        return round(max(0.0, min(1.0, u)), 4)

    # ─────────────────────────────────────────────
    # 🔁 Step 3: Reflection Feedback Integration
    # ─────────────────────────────────────────────
    def apply_reflection(self, node: ScenarioNode, feedback: Dict[str, Any]):
        d_sqi = float(feedback.get("ΔSQI", 0.0))
        d_eth = float(feedback.get("ΔEthics", 0.0))
        penal = set(feedback.get("penalize_actions", []))
        boost = set(feedback.get("boost_actions", []))

        def _walk(n: ScenarioNode):
            if d_sqi or d_eth:
                n.sqi = max(0, min(1, n.sqi + d_sqi))
                n.ethics = max(0, min(1, n.ethics + d_eth))
                n.utility = self._utility(n)
            if n.action in penal:
                n.utility = round(max(0.0, n.utility - 0.1), 4)
            if n.action in boost:
                n.utility = round(min(1.0, n.utility + 0.1), 4)
            for c in n.children:
                _walk(c)

        _walk(node)
        log.info("[SSE] Reflection feedback applied — utilities re-ranked.")

    # ─────────────────────────────────────────────
    # 🧠 Helpers
    # ─────────────────────────────────────────────
    def _softmax(self, xs):
        m = max(xs) if xs else 0.0
        ex = [math.exp(x - m) for x in xs]
        s = sum(ex) or 1.0
        return [e / s for e in ex]

    def _extract_best_path(self, root: ScenarioNode):
        path, node = [], root
        total_u = 0.0
        while node.children:
            node = max(node.children, key=lambda n: n.utility)
            path.append(node)
            total_u += node.utility
        return path, round(total_u, 4)

    def _to_dict(self, n: ScenarioNode) -> Dict[str, Any]:
        return {
            "id": n.id,
            "action": n.action,
            "depth": n.depth,
            "prob": n.prob,
            "sqi": n.sqi,
            "ethics": n.ethics,
            "goal_fit": n.goal_fit,
            "reward": n.reward,
            "risk": n.risk,
            "cost": n.cost,
            "entropy": n.entropy,
            "utility": n.utility,
            "state": n.state,
            "children": [self._to_dict(c) for c in n.children],
        }

    def _persist_tree(self, root: ScenarioNode, best_path, best_u):
        self.out_tree.write_text(json.dumps(self._to_dict(root), indent=2))
        self.out_best.write_text(
            json.dumps(
                {"best_path": [n.action for n in best_path if n.action], "best_utility": best_u},
                indent=2,
            )
        )