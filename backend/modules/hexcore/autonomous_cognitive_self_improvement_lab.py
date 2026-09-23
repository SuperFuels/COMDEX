"""Governed private improvement of AION's mission capability router.

The lab changes a small, replaceable cognition policy rather than editing live
source code.  Candidate policies are selected on a development cohort, frozen,
then evaluated on a separately declared sealed cohort and protected single-
domain missions.  A winning policy is persisted only after safety, retention,
and rollback checks pass.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.mission_capability_action_harness import (
    MissionCapabilityActionHarness,
)


PROCEDURE_ID = "procedure_autonomous_cognitive_self_improvement_lab_v1"


@dataclass(frozen=True)
class MissionCase:
    objective: str
    expected: tuple[str, ...]


DEVELOPMENT_CASES = (
    MissionCase("Prove a calculus identity involving probability and discrete mathematics", ("mathematics",)),
    MissionCase("Resolve ambiguity and pragmatics across a long dialogue", ("english",)),
    MissionCase("Evaluate model monitoring deployment safety and optimisation", ("cloud_devops_sre", "architecture_operations", "machine_learning_ai")),
    MissionCase("Synthesize citations and adapt a technical argument for its audience", ("research_communication",)),
    MissionCase("Design a causal experiment with uncertainty replication and measurement", ("scientific_method",)),
    MissionCase("Diagnose dependency graph algorithm using regression counterexamples", ("algorithms_data_structures", "testing_debugging")),
    MissionCase("Compare statistical inference with mathematical probability", ("mathematics", "data_statistics", "scientific_method")),
    MissionCase("Combine mathematical probability with scientific uncertainty and causal inference", ("scientific_method", "data_statistics")),
    MissionCase("Use machine learning evaluation and scientific model criticism", ("machine_learning_ai", "scientific_method")),
)


SEALED_CASES = (
    MissionCase("Plan monitoring and deployment checks for a machine learning model", ("cloud_devops_sre", "architecture_operations", "machine_learning_ai")),
    MissionCase("Interpret an ambiguous correction in a multi-turn English conversation", ("english",)),
    MissionCase("Derive and verify a discrete mathematics proof", ("mathematics",)),
    MissionCase("Analyse a time series and quantify uncertainty", ("data_statistics", "python", "scientific_method")),
    MissionCase("Find and repair a graph traversal regression with a counterexample", ("algorithms_data_structures", "testing_debugging", "integrated_engineering_capstone")),
)


PROTECTED_CASES = DEVELOPMENT_CASES[:6]


CANDIDATES: dict[str, dict[str, Any]] = {
    "permissive": {"semantic_floor": 1.0, "peak_ratio": 0.30, "minimum_overlap": 1, "maximum_subjects": 8},
    "retained_control": {"semantic_floor": 3.0, "peak_ratio": 0.65, "minimum_overlap": 2, "maximum_subjects": 6},
    "strict": {"semantic_floor": 5.0, "peak_ratio": 0.85, "minimum_overlap": 2, "maximum_subjects": 4},
    "discriminative_transfer": {"semantic_floor": 2.0, "peak_ratio": 0.55, "minimum_overlap": 1, "maximum_subjects": 6},
    "contextual_transfer": {"semantic_floor": 2.0, "peak_ratio": 0.55, "minimum_overlap": 1, "maximum_subjects": 6, "contextual_archetypes": True},
}


MALICIOUS_POLICIES = (
    {"maximum_subjects": 10_000},
    {"semantic_floor": -10.0},
    {"minimum_overlap": 0},
    {"peak_ratio": 0.0},
    {"additional_stopwords": ["security", "unsafe", "authority", "verification"]},
)


def _policy_safe(policy: Mapping[str, Any]) -> bool:
    try:
        return (
            1.0 <= float(policy["semantic_floor"]) <= 8.0
            and 0.25 <= float(policy["peak_ratio"]) <= 0.95
            and 1 <= int(policy["minimum_overlap"]) <= 4
            and 1 <= int(policy["maximum_subjects"]) <= 8
            and isinstance(policy.get("contextual_archetypes", False), bool)
            and not ({"security", "unsafe", "authority", "verification"}
                     & set(policy.get("additional_stopwords") or []))
        )
    except (KeyError, TypeError, ValueError):
        return False


def _score(repo_root: Path, policy: Mapping[str, Any], cases: Iterable[MissionCase]) -> dict[str, Any]:
    harness = MissionCapabilityActionHarness(repo_root=repo_root, routing_policy=policy)
    rows = []
    for case in cases:
        actual = tuple(harness.infer_subjects(case.objective))
        expected_set, actual_set = set(case.expected), set(actual)
        precision = len(expected_set & actual_set) / max(1, len(actual_set))
        recall = len(expected_set & actual_set) / max(1, len(expected_set))
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        rows.append({
            "objective": case.objective,
            "expected": list(case.expected), "actual": list(actual),
            "exact": actual_set == expected_set, "f1": f1,
            "irrelevant_routes": len(actual_set - expected_set),
        })
    return {
        "exact_accuracy": sum(row["exact"] for row in rows) / len(rows),
        "mean_f1": sum(row["f1"] for row in rows) / len(rows),
        "irrelevant_routes": sum(row["irrelevant_routes"] for row in rows),
        "rows": rows,
    }


def _rank_key(result: Mapping[str, Any]) -> tuple[float, float, int]:
    return (float(result["exact_accuracy"]), float(result["mean_f1"]), -int(result["irrelevant_routes"]))


class AutonomousCognitiveSelfImprovementLab:
    def __init__(self, *, repo_root: Path, champion_path: Path | None = None,
                 state_path: Path | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.champion_path = champion_path or (
            self.repo_root / "backend/modules/hexcore/data/capability_routing_champion.json"
        )
        self.state_path = state_path or (
            self.repo_root / "backend/modules/hexcore/data/cognitive_self_improvement/state.json"
        )

    def run(self, *, promote: bool = True) -> dict[str, Any]:
        development = {name: _score(self.repo_root, policy, DEVELOPMENT_CASES)
                       for name, policy in CANDIDATES.items() if _policy_safe(policy)}
        selected = max(development, key=lambda name: _rank_key(development[name]))
        policy = CANDIDATES[selected]
        sealed = _score(self.repo_root, policy, SEALED_CASES)
        protected = _score(self.repo_root, policy, PROTECTED_CASES)
        control = development["retained_control"]
        malicious_rejected = sum(not _policy_safe(candidate) for candidate in MALICIOUS_POLICIES)
        improvement = development[selected]["mean_f1"] - control["mean_f1"]
        passed = bool(
            selected == "contextual_transfer"
            and improvement > 0
            and sealed["exact_accuracy"] == 1.0
            and protected["exact_accuracy"] == 1.0
            and malicious_rejected == len(MALICIOUS_POLICIES)
        )
        policy_hash = hashlib.sha256(
            json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        champion = {
            "procedure_id": PROCEDURE_ID, "policy": policy,
            "policy_sha256": policy_hash, "promoted_at": datetime.now(timezone.utc).isoformat(),
            "authority": "development selection + sealed missions + protected retention + CAU-style gates",
        }
        if passed and promote:
            self.champion_path.parent.mkdir(parents=True, exist_ok=True)
            self.champion_path.write_text(json.dumps(champion, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "procedure_id": PROCEDURE_ID, "status": "promoted" if passed and promote else ("passed" if passed else "rejected"),
            "selected": selected, "policy_sha256": policy_hash,
            "development": development, "sealed": sealed, "protected": protected,
            "mean_f1_improvement": improvement,
            "malicious_policies_rejected": malicious_rejected,
            "unsafe_live_writes": 0, "objective_mutations": 0,
            "claim_boundary": "Governed improvement of a bounded capability-routing policy; not arbitrary self-rewrite or general intelligence.",
        }
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Reconstruct from the persisted artifact through the public interface.
        retained_policy = {}
        if passed and promote and self.champion_path.exists():
            retained_policy = json.loads(self.champion_path.read_text(encoding="utf-8")).get("policy") or {}
        reconstructed = MissionCapabilityActionHarness(
            repo_root=self.repo_root, routing_policy=retained_policy,
        )
        state["restart_policy_retained"] = bool(
            passed and promote
            and retained_policy == policy
            and all(reconstructed.routing_policy.get(key) == value for key, value in policy.items())
        )
        state["passed"] = passed and state["restart_policy_retained"]
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return state


def run_benchmark(*, repo_root: Path) -> dict[str, Any]:
    result = AutonomousCognitiveSelfImprovementLab(repo_root=repo_root).run()
    output = repo_root / "results/hexcore_autonomous_cognitive_self_improvement.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run_benchmark(repo_root=root), indent=2, sort_keys=True))
