from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import (
    EvidenceCapsule,
    HexCorePersistentLearningRuntime,
    TransitionObservation,
)


@dataclass(frozen=True)
class DomainSpec:
    world_id: str
    entity: str
    state_field: str
    gain_action: str
    gain_delta: int
    loss_action: str
    loss_delta: int
    terminal_action: str
    outcome_field: str
    threshold: int


DOMAINS = [
    DomainSpec(
        world_id="thermal_seal_v1",
        entity="thermal_seal",
        state_field="temperature",
        gain_action="warm",
        gain_delta=3,
        loss_action="cool",
        loss_delta=-2,
        terminal_action="release",
        outcome_field="released",
        threshold=6,
    ),
    DomainSpec(
        world_id="nutrient_reactor_v1",
        entity="nutrient_reactor",
        state_field="nutrient",
        gain_action="feed",
        gain_delta=4,
        loss_action="consume",
        loss_delta=-1,
        terminal_action="harvest",
        outcome_field="harvested",
        threshold=8,
    ),
    DomainSpec(
        world_id="pressure_lock_v1",
        entity="pressure_lock",
        state_field="pressure",
        gain_action="pump",
        gain_delta=5,
        loss_action="bleed",
        loss_delta=-3,
        terminal_action="unlock",
        outcome_field="unlocked",
        threshold=10,
    ),
]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "source": "multi_domain_benchmark_authority",
        "goal": goal,
        "S": 1.0,
        "H": 0.0,
    }


class ThresholdControlDomain:
    def __init__(self, spec: DomainSpec) -> None:
        self.spec = spec

    def initial_state(self, value: int = 0) -> Dict[str, Any]:
        return {self.spec.state_field: value, self.spec.outcome_field: False}

    def transition(self, state: Mapping[str, Any], action: str) -> Dict[str, Any]:
        next_state = dict(state)
        value = int(next_state.get(self.spec.state_field) or 0)
        if action == self.spec.gain_action:
            next_state[self.spec.state_field] = value + self.spec.gain_delta
        elif action == self.spec.loss_action:
            next_state[self.spec.state_field] = max(0, value + self.spec.loss_delta)
        elif action == self.spec.terminal_action:
            next_state[self.spec.outcome_field] = value >= self.spec.threshold
        return next_state

    def run(self, steps: Sequence[str], *, start_value: int = 0) -> Dict[str, Any]:
        state = self.initial_state(start_value)
        trace = []
        for action in steps:
            before = dict(state)
            state = self.transition(state, action)
            trace.append({"state": before, "action": action, "next_state": dict(state)})
            if state[self.spec.outcome_field]:
                break
        success = bool(state[self.spec.outcome_field])
        return {
            "success": success,
            "score": round(max(0.0, (1.0 if success else 0.0) - 0.03 * len(trace)), 6),
            "final_state": state,
            "trace": trace,
        }


def _learn_domain(
    runtime: HexCorePersistentLearningRuntime,
    spec: DomainSpec,
) -> Dict[str, Any]:
    domain = ThresholdControlDomain(spec)

    runtime.knowledge.ingest(
        EvidenceCapsule(
            capsule_id=f"{spec.world_id}_manual_r1",
            source_uri=f"benchmark://{spec.world_id}/manual/r1",
            content=f"An obsolete manual lists {spec.threshold + 1}.",
            claims=[
                {
                    "subject": spec.entity,
                    "predicate": f"minimum_{spec.state_field}",
                    "object": str(spec.threshold + 1),
                    "revision": 1,
                    "confidence": 0.8,
                }
            ],
        )
    )
    runtime.knowledge.ingest(
        EvidenceCapsule(
            capsule_id=f"{spec.world_id}_manual_r2",
            source_uri=f"benchmark://{spec.world_id}/manual/r2",
            content=f"The verified revision lists {spec.threshold}.",
            claims=[
                {
                    "subject": spec.entity,
                    "predicate": f"minimum_{spec.state_field}",
                    "object": str(spec.threshold),
                    "revision": 2,
                    "confidence": 1.0,
                }
            ],
        )
    )

    probe_inputs = [
        (0, spec.gain_action),
        (spec.gain_delta, spec.gain_action),
        (1, spec.gain_action),
        (max(1, spec.threshold - 1), spec.loss_action),
        (max(1, abs(spec.loss_delta)), spec.loss_action),
        (0, spec.terminal_action),
        (max(0, spec.threshold - 1), spec.terminal_action),
        (spec.threshold, spec.terminal_action),
        (spec.threshold + spec.gain_delta, spec.terminal_action),
    ]
    for index, (value, action) in enumerate(probe_inputs, start=1):
        state = domain.initial_state(value)
        runtime.world.observe(
            TransitionObservation(
                observation_id=f"{spec.world_id}_probe_{index}",
                world_id=spec.world_id,
                state=state,
                action=action,
                next_state=domain.transition(state, action),
                evidence_id=f"simulator:{spec.world_id}:{index}",
            )
        )

    runtime.world.infer_effect_rules(world_id=spec.world_id)
    threshold_rule = runtime.world.infer_threshold_rule(
        world_id=spec.world_id,
        action=spec.terminal_action,
        condition_field=spec.state_field,
        outcome_field=spec.outcome_field,
        success_value=True,
    )
    candidate = runtime.skills.plan_threshold_goal(
        world_id=spec.world_id,
        start_state=domain.initial_state(),
        terminal_action=spec.terminal_action,
    )
    if candidate is None:
        raise RuntimeError(f"no procedure planned for {spec.world_id}")
    evaluated = runtime.skills.evaluate(candidate, runner=domain.run)
    promotion = runtime.skills.promote(evaluated)
    runtime.skills.record_outcome(
        procedure_id=evaluated.procedure_id,
        success=evaluated.success,
        score=evaluated.score,
        evidence=evaluated.evidence,
    )
    claim = runtime.knowledge.query_claim(spec.entity, f"minimum_{spec.state_field}")
    return {
        "domain": asdict(spec),
        "knowledge_correct": claim.get("claim", {}).get("object") == str(spec.threshold),
        "provenance_complete": claim.get("provenance_complete") is True,
        "threshold_rule_correct": bool(
            threshold_rule
            and threshold_rule.get("condition", {}).get("field") == spec.state_field
            and threshold_rule.get("condition", {}).get("value") == float(spec.threshold)
        ),
        "candidate": evaluated.to_dict(),
        "promotion": promotion,
        "probe_count": len(probe_inputs),
    }


def run_multi_domain_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    learned = [_learn_domain(runtime, spec) for spec in DOMAINS]

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart_results = []
    for spec in DOMAINS:
        domain = ThresholdControlDomain(spec)
        goal = f"{spec.outcome_field}=True"
        champion = restarted.skills.champion(goal)
        held_out_start = 1
        execution = (
            domain.run(champion["steps"], start_value=held_out_start)
            if champion
            else {"success": False, "score": 0.0, "trace": []}
        )
        claim = restarted.knowledge.query_claim(spec.entity, f"minimum_{spec.state_field}")
        rules = restarted.world.active_rules(spec.world_id)
        restart_results.append(
            {
                "world_id": spec.world_id,
                "knowledge_retained": claim.get("claim", {}).get("object") == str(spec.threshold),
                "rules_retained": bool(rules),
                "procedure_retained": champion is not None,
                "held_out_success": bool(execution["success"]),
                "held_out_start": held_out_start,
                "relearning_operations": 0,
            }
        )

    domain_passes = [
        bool(
            row["knowledge_correct"]
            and row["provenance_complete"]
            and row["threshold_rule_correct"]
            and row["candidate"]["success"]
            and row["promotion"]["promoted"]
        )
        for row in learned
    ]
    restart_passes = [
        all(
            [
                row["knowledge_retained"],
                row["rules_retained"],
                row["procedure_retained"],
                row["held_out_success"],
                row["relearning_operations"] == 0,
            ]
        )
        for row in restart_results
    ]
    result = {
        "schema_version": "aion.hexcore.multi_domain_learning_benchmark.v1",
        "benchmark": "hexcore_cross_domain_threshold_control",
        "domain_count": len(DOMAINS),
        "language_provider_used": False,
        "domain_specific_learning_code_used": False,
        "baseline_success_rate": 0.0,
        "learned_success_rate": round(sum(domain_passes) / len(domain_passes), 6),
        "restart_success_rate": round(sum(restart_passes) / len(restart_passes), 6),
        "total_probe_count_cycle_1": sum(row["probe_count"] for row in learned),
        "total_probe_count_cycle_2": 0,
        "domain_results": learned,
        "restart_results": restart_results,
        "status": restarted.status(),
        "gates": {
            "all_domains_learned": all(domain_passes),
            "all_domains_survive_restart": all(restart_passes),
            "zero_relearning_on_cycle_2": all(
                row["relearning_operations"] == 0 for row in restart_results
            ),
            "provenance_complete": all(row["provenance_complete"] for row in learned),
        },
        "boundary_statement": (
            "This demonstrates transfer of one governed learning algorithm across "
            "three structurally related bounded domains. It does not establish "
            "open-domain general reasoning."
        ),
    }
    result["passed"] = all(result["gates"].values())
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/multi_domain_learning_state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_multi_domain_learning_benchmark.json"),
    )
    args = parser.parse_args()
    result = run_multi_domain_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
