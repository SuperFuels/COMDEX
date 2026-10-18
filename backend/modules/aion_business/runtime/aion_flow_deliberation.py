from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


CandidateRoute = Callable[[Mapping[str, Any]], Mapping[str, Any]]
CriticRoute = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class DeliberationBudget:
    maximum_iterations: int = 3
    maximum_tokens: int = 20_000
    maximum_seconds: float = 120.0
    maximum_cost: float = 0.0
    maximum_energy_wh: float = 5.0
    maximum_candidates: int = 5

    def __post_init__(self) -> None:
        if not 1 <= self.maximum_iterations <= 8 or not 1 <= self.maximum_candidates <= 8:
            raise ValueError("deliberation_iteration_or_candidate_limit_invalid")
        if self.maximum_tokens <= 0 or self.maximum_seconds <= 0 or self.maximum_cost < 0 or self.maximum_energy_wh < 0:
            raise ValueError("deliberation_budget_invalid")


class AionFlowDeliberationEngine:
    """Bounded, evidence-first candidate generation, criticism and reconciliation."""

    def deliberate(
        self,
        *,
        task: Mapping[str, Any],
        evidence_pack: Mapping[str, Any],
        candidate_routes: Iterable[Mapping[str, Any]],
        critic_routes: Iterable[Mapping[str, Any]] = (),
        budget: DeliberationBudget,
        success: Callable[[Mapping[str, Any]], bool] | None = None,
        high_consequence: bool = False,
    ) -> Dict[str, Any]:
        started = time.monotonic()
        routes = list(candidate_routes)[: budget.maximum_candidates]
        if not routes:
            raise ValueError("deliberation_candidate_required")
        identities = [(str(item.get("provider") or ""), str(item.get("model") or ""), str(item.get("harness") or "")) for item in routes]
        independence = len(set(identities)) == len(identities)
        candidates = self._parallel_candidates(routes, {"task": dict(task), "evidence_pack": dict(evidence_pack)})
        totals = self._usage(candidates)
        budget_error = self._budget_error(totals, budget, time.monotonic() - started)
        if budget_error:
            return self._blocked(candidates, [], totals, budget_error, independence)

        criticism = []
        for route in list(critic_routes)[:8]:
            for candidate in candidates:
                if self._same_route(route, candidate):
                    continue
                output = self._safe_call(route.get("call"), {"candidate": candidate, "evidence_pack": dict(evidence_pack), "task": dict(task)})
                criticism.append({
                    "critic_id": str(route.get("route_id") or "critic"),
                    "candidate_id": candidate["candidate_id"],
                    "provider": str(route.get("provider") or ""),
                    "findings": list(output.get("findings") or []),
                    "assumptions": list(output.get("assumptions") or []),
                    "red_team": list(output.get("red_team") or []),
                    "usage": dict(output.get("usage") or {}),
                })
        criticism_usage = self._usage(criticism)
        totals = {key: totals[key] + criticism_usage[key] for key in totals}
        budget_error = self._budget_error(totals, budget, time.monotonic() - started)
        if budget_error:
            return self._blocked(candidates, criticism, totals, budget_error, independence)

        eligible = [item for item in candidates if item["valid"] and item["evidence_status"] == "verified"]
        repeated = len({item["output_hash"] for item in candidates}) < len(candidates)
        oscillation = any(item.get("history") and len(item["history"]) >= 3 and item["history"][-1] == item["history"][-3] != item["history"][-2] for item in candidates)
        ranked = sorted(eligible, key=self._score, reverse=True)
        winner = ranked[0] if ranked else None
        success_met = bool(winner and (success(winner) if success else self._score(winner) >= 0.7))
        close_disagreement = len(ranked) > 1 and abs(self._score(ranked[0]) - self._score(ranked[1])) < 0.05 and ranked[0]["output_hash"] != ranked[1]["output_hash"]
        human_required = bool(high_consequence or not success_met or close_disagreement or oscillation)
        dissent = [
            {"candidate_id": item["candidate_id"], "output_hash": item["output_hash"], "score": round(self._score(item), 4), "summary": item.get("summary", "")}
            for item in ranked[1:]
        ]
        status = "awaiting_human_arbitration" if human_required else "resolved"
        result = {
            "schema_version": "aion.flow.deliberation_result.v1",
            "status": status,
            "winner": winner if not human_required else None,
            "proposed_winner": winner,
            "candidates": candidates,
            "criticism": criticism,
            "dissent": dissent,
            "uncertainty": {
                "close_disagreement": close_disagreement,
                "repeated_outputs": repeated,
                "oscillation": oscillation,
                "independent_routes": independence,
                "unresolved": human_required,
            },
            "arbitration_order": ["deterministic_validation", "evidence_status", "measured_score", "human_if_unresolved"],
            "budget_usage": totals | {"seconds": round(time.monotonic() - started, 4), "iterations": 1},
            "model_vote_grants_authority": False,
            "created_at": utc_now_iso(),
        }
        result["deliberation_hash"] = canonical_hash(result)
        return result

    def refine(
        self,
        *,
        initial: Mapping[str, Any],
        improve: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        evidence_pack: Mapping[str, Any],
        budget: DeliberationBudget,
        success: Callable[[Mapping[str, Any]], bool],
    ) -> Dict[str, Any]:
        began = time.monotonic()
        current = dict(initial)
        history, usage = [], {"tokens": 0, "cost": 0.0, "energy_wh": 0.0}
        stop_reason = "maximum_iterations"
        for iteration in range(1, budget.maximum_iterations + 1):
            current_hash = canonical_hash(current)
            if current_hash in history:
                stop_reason = "repeated_output" if history and history[-1] == current_hash else "oscillation"
                break
            history.append(current_hash)
            if success(current):
                stop_reason = "success_criteria_met"
                break
            output = self._safe_call(improve, {"candidate": current, "evidence_pack": dict(evidence_pack), "iteration": iteration})
            route_usage = dict(output.pop("usage", {}) or {})
            usage["tokens"] += int(route_usage.get("tokens", 0) or 0)
            usage["cost"] += float(route_usage.get("cost", 0) or 0)
            usage["energy_wh"] += float(route_usage.get("energy_wh", 0) or 0)
            error = self._budget_error(usage, budget, time.monotonic() - began)
            if error:
                stop_reason = error
                break
            current = dict(output)
        return {
            "status": "resolved" if stop_reason == "success_criteria_met" else "unresolved",
            "candidate": current,
            "iterations": len(history),
            "history_hashes": history,
            "stop_reason": stop_reason,
            "budget_usage": usage | {"seconds": round(time.monotonic() - began, 4)},
            "downstream_execution_allowed": stop_reason == "success_criteria_met",
        }

    @classmethod
    def _parallel_candidates(cls, routes: list[Mapping[str, Any]], payload: Mapping[str, Any]) -> list[Dict[str, Any]]:
        candidates = []
        with ThreadPoolExecutor(max_workers=min(8, len(routes)), thread_name_prefix="aion-deliberation") as pool:
            pending = {pool.submit(cls._safe_call, route.get("call"), payload): route for route in routes}
            for future in as_completed(pending):
                route = pending[future]
                output = dict(future.result())
                candidate = {
                    "candidate_id": str(route.get("route_id") or f"candidate-{len(candidates) + 1}"),
                    "provider": str(route.get("provider") or ""),
                    "model": str(route.get("model") or ""),
                    "harness": str(route.get("harness") or ""),
                    "valid": bool(output.get("valid", False)),
                    "evidence_status": str(output.get("evidence_status") or "unresolved"),
                    "quality": max(0.0, min(float(output.get("quality", 0)), 1.0)),
                    "correctness": max(0.0, min(float(output.get("correctness", 0)), 1.0)),
                    "evidence_coverage": max(0.0, min(float(output.get("evidence_coverage", 0)), 1.0)),
                    "summary": str(output.get("summary") or "")[:1000],
                    "output": output.get("output"),
                    "usage": dict(output.get("usage") or {}),
                    "history": list(output.get("history") or []),
                }
                candidate["output_hash"] = canonical_hash(candidate.get("output"))
                candidates.append(candidate)
        return sorted(candidates, key=lambda item: item["candidate_id"])

    @staticmethod
    def _safe_call(call: Any, payload: Mapping[str, Any]) -> Dict[str, Any]:
        if not callable(call):
            return {"valid": False, "evidence_status": "unresolved", "error": "route_not_callable"}
        try:
            value = call(payload)
            return dict(value) if isinstance(value, Mapping) else {"valid": False, "error": "route_output_invalid"}
        except Exception as exc:
            return {"valid": False, "evidence_status": "unresolved", "error": type(exc).__name__}

    @staticmethod
    def _same_route(critic: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
        return bool(critic.get("provider") and critic.get("provider") == candidate.get("provider") and critic.get("model") == candidate.get("model"))

    @staticmethod
    def _score(candidate: Mapping[str, Any]) -> float:
        return (float(candidate.get("quality", 0)) + float(candidate.get("correctness", 0)) * 2 + float(candidate.get("evidence_coverage", 0)) * 2) / 5

    @staticmethod
    def _usage(items: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        result = {"tokens": 0, "cost": 0.0, "energy_wh": 0.0}
        for item in items:
            usage = item.get("usage") or {}
            result["tokens"] += int(usage.get("tokens", 0) or 0)
            result["cost"] += float(usage.get("cost", 0) or 0)
            result["energy_wh"] += float(usage.get("energy_wh", 0) or 0)
        return result

    @staticmethod
    def _budget_error(usage: Mapping[str, Any], budget: DeliberationBudget, seconds: float) -> str:
        if int(usage.get("tokens", 0)) > budget.maximum_tokens:
            return "token_budget_exceeded"
        if float(usage.get("cost", 0)) > budget.maximum_cost:
            return "cost_budget_exceeded"
        if float(usage.get("energy_wh", 0)) > budget.maximum_energy_wh:
            return "energy_budget_exceeded"
        if seconds > budget.maximum_seconds:
            return "time_budget_exceeded"
        return ""

    @staticmethod
    def _blocked(candidates: list[Mapping[str, Any]], criticism: list[Mapping[str, Any]], usage: Mapping[str, Any], reason: str, independence: bool) -> Dict[str, Any]:
        return {
            "schema_version": "aion.flow.deliberation_result.v1", "status": "budget_blocked", "reason": reason,
            "winner": None, "candidates": candidates, "criticism": criticism, "dissent": [],
            "uncertainty": {"unresolved": True, "independent_routes": independence}, "budget_usage": dict(usage),
            "model_vote_grants_authority": False, "downstream_execution_allowed": False,
        }
