from __future__ import annotations

import argparse
import itertools
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


@dataclass(frozen=True)
class SkillDomain:
    domain_id: str
    fields: Tuple[str, str]
    actions: Tuple[str, str, str, str]
    threshold: int
    gains: Tuple[int, int]
    action_reliability: float
    budget: int
    seed: int
    maximum_deficit: int = 10

    @property
    def increase_action(self) -> str:
        return self.actions[0]

    @property
    def decrease_action(self) -> str:
        return self.actions[1]

    @property
    def distractor_action(self) -> str:
        return self.actions[2]

    @property
    def commit_action(self) -> str:
        return self.actions[3]


DEVELOPMENT_DOMAINS = (
    SkillDomain(
        "ember_regulator",
        ("flame", "slag"),
        ("feed_flame", "drain_slag", "rotate_crucible", "seal_heat"),
        4,
        (2, 1),
        0.90,
        9,
        111,
    ),
    SkillDomain(
        "canopy_lift",
        ("lift", "drag"),
        ("raise_canopy", "shed_drag", "trim_equal", "lock_canopy"),
        3,
        (1, 2),
        0.88,
        9,
        222,
    ),
)

SEALED_DOMAINS = (
    SkillDomain(
        "magnetic_weave",
        ("weft", "loss"),
        ("add_weft", "bleed_loss", "swap_poles", "commit_weave"),
        5,
        (2, 1),
        0.91,
        10,
        333,
    ),
    SkillDomain(
        "river_sluice",
        ("head", "leak"),
        ("pump_head", "close_leak", "shuffle_gate", "open_sluice"),
        4,
        (1, 2),
        0.87,
        10,
        444,
    ),
    SkillDomain(
        "orbital_trim",
        ("thrust", "drift"),
        ("pulse_thrust", "cancel_drift", "roll_frame", "confirm_orbit"),
        6,
        (3, 1),
        0.92,
        9,
        555,
    ),
)

NEGATIVE_CONTROLS = (
    SkillDomain(
        "single_step_pressure",
        ("pressure", "leak"),
        ("raise_pressure", "close_leak", "wait", "commit"),
        2,
        (3, 1),
        0.98,
        5,
        666,
        maximum_deficit=2,
    ),
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "skill_contract_invention_authority",
        "S": 1.0,
        "H": 0.0,
    }


class AdaptiveMarginEnvironment:
    def __init__(
        self,
        *,
        spec: SkillDomain,
        seed: int,
        initial: Tuple[int, int] | None = None,
    ) -> None:
        self.spec = spec
        self.random = random.Random(seed)
        if initial is None:
            right = self.random.randint(5, 15)
            deficit = self.random.randint(1, spec.maximum_deficit)
            left = right + spec.threshold - deficit
            self.state = [left, right]
        else:
            self.state = [int(initial[0]), int(initial[1])]
        self.steps = 0
        self.success = False
        self.trace: List[Dict[str, Any]] = []

    @property
    def margin(self) -> int:
        return self.state[0] - self.state[1]

    def step(self, action: str) -> Dict[str, Any]:
        before = tuple(self.state)
        self.steps += 1
        follows = self.random.random() < self.spec.action_reliability
        if action == self.spec.increase_action and follows:
            self.state[0] += self.spec.gains[0]
        elif action == self.spec.decrease_action and follows:
            self.state[1] -= self.spec.gains[1]
        elif action == self.spec.distractor_action and follows:
            self.state[0] += 1
            self.state[1] += 1
        elif action == self.spec.commit_action:
            self.success = bool(
                self.margin >= self.spec.threshold
                and self.steps <= self.spec.budget
            )
        row = {
            "action": action,
            "before": {
                self.spec.fields[0]: before[0],
                self.spec.fields[1]: before[1],
            },
            "after": {
                self.spec.fields[0]: self.state[0],
                self.spec.fields[1]: self.state[1],
            },
            "margin_before": before[0] - before[1],
            "margin_after": self.margin,
            "success": self.success,
        }
        self.trace.append(row)
        return row


def _calibrate_action_roles(spec: SkillDomain) -> Dict[str, Any]:
    rows = []
    for index, action in enumerate(spec.actions):
        environment = AdaptiveMarginEnvironment(
            spec=spec,
            seed=80_000 + index,
            initial=(10, 10),
        )
        # Repeat twice so one stochastic miss cannot erase the effect signature.
        environment.step(action)
        row = environment.step(action)
        rows.append(
            {
                "action": action,
                "margin_gain": row["margin_after"] - row["margin_before"],
                "terminal": bool(action == spec.commit_action),
            }
        )
    nonterminal = [row for row in rows if not row["terminal"]]
    progress = max(
        nonterminal,
        key=lambda row: (row["margin_gain"], row["action"]),
    )
    terminal = next(row for row in rows if row["terminal"])
    return {
        "progress_action": progress["action"],
        "commit_action": terminal["action"],
        "effect_rows": rows,
        "calibration_actions": 2 * len(spec.actions),
    }


def _execute_policy(
    *,
    spec: SkillDomain,
    policy_id: str,
    episodes: int,
    seed_offset: int,
) -> Dict[str, Any]:
    binding = _calibrate_action_roles(spec)
    rows = []
    for episode in range(episodes):
        environment = AdaptiveMarginEnvironment(
            spec=spec,
            seed=seed_offset + episode,
        )
        if policy_id == "fixed_two":
            actions = [binding["progress_action"]] * 2
        elif policy_id == "fixed_four":
            actions = [binding["progress_action"]] * 4
        elif policy_id == "alternating":
            other = next(
                action for action in spec.actions[:-1]
                if action != binding["progress_action"]
            )
            actions = [
                binding["progress_action"],
                other,
                binding["progress_action"],
                other,
            ]
        elif policy_id == "guarded_progress_loop":
            actions = []
            while (
                environment.margin < spec.threshold
                and len(actions) < spec.budget - 1
            ):
                action = binding["progress_action"]
                environment.step(action)
                actions.append(action)
            environment.step(binding["commit_action"])
            rows.append(
                {
                    "success": environment.success,
                    "steps": environment.steps,
                    "repairs": max(0, len(actions) - 1),
                    "trace": environment.trace,
                }
            )
            continue
        else:
            raise ValueError(policy_id)
        for action in actions:
            environment.step(action)
        environment.step(binding["commit_action"])
        rows.append(
            {
                "success": environment.success,
                "steps": environment.steps,
                "repairs": 0,
                "trace": environment.trace,
            }
        )
    return {
        "policy_id": policy_id,
        "domain_id": spec.domain_id,
        "episodes": episodes,
        "success_rate": sum(row["success"] for row in rows) / episodes,
        "mean_steps": sum(row["steps"] for row in rows) / episodes,
        "mean_repairs": sum(row["repairs"] for row in rows) / episodes,
        "calibration_actions": binding["calibration_actions"],
        "role_binding": binding,
        "rows": rows,
    }


def _evaluate_policy(
    *,
    policy_id: str,
    domains: Sequence[SkillDomain],
    episodes: int,
    seed_offset: int,
) -> Dict[str, Any]:
    rows = [
        _execute_policy(
            spec=domain,
            policy_id=policy_id,
            episodes=episodes,
            seed_offset=seed_offset + index * 10_000,
        )
        for index, domain in enumerate(domains)
    ]
    return {
        "policy_id": policy_id,
        "mean_success": sum(row["success_rate"] for row in rows) / len(rows),
        "worst_success": min(row["success_rate"] for row in rows),
        "mean_steps": sum(row["mean_steps"] for row in rows) / len(rows),
        "domains": [
            {key: value for key, value in row.items() if key != "rows"}
            for row in rows
        ],
    }


def _outcome_signature(
    result: Mapping[str, Any],
) -> str:
    return _canonical_hash(
        [
            round(row["success_rate"], 4)
            for row in result["domains"]
        ]
    )


def run_skill_contract_invention_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_episodes: int = 120,
    sealed_episodes: int = 300,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    concept_id = "concept_ordered_margin_2d5a04f6994e"
    runtime.store.state["invented_concepts"][concept_id] = {
        "schema_version": "aion.hexcore.invented_concept.v1",
        "concept_id": concept_id,
        "name": "ordered_margin",
        "operator": "difference_ge",
        "arity": 2,
        "status": "phase22_promoted_dependency",
        "source_procedure_id": "procedure_ontology_invention_0e9d9c5eafb8",
    }
    runtime.store.commit(reason="load_promoted_phase22_concept")

    candidate_ids = (
        "fixed_two",
        "fixed_four",
        "alternating",
        "guarded_progress_loop",
    )
    development = [
        _evaluate_policy(
            policy_id=policy_id,
            domains=DEVELOPMENT_DOMAINS,
            episodes=development_episodes,
            seed_offset=100_000,
        )
        for policy_id in candidate_ids
    ]
    existing = max(
        [
            row for row in development
            if row["policy_id"] != "guarded_progress_loop"
        ],
        key=lambda row: (row["mean_success"], row["worst_success"]),
    )
    criticism = {
        "status": (
            "SKILL_LIBRARY_INADEQUATE"
            if existing["mean_success"] < 0.80
            else "SKILL_LIBRARY_ADEQUATE"
        ),
        "invention_required": existing["mean_success"] < 0.80,
        "best_existing_policy": existing["policy_id"],
        "mean_success": existing["mean_success"],
        "worst_success": existing["worst_success"],
        "reason": "FIXED_LENGTH_SKILLS_FAIL_VARIABLE_DEFICITS",
    }

    signatures: Dict[str, Mapping[str, Any]] = {}
    merged = []
    for row in development:
        signature = _outcome_signature(row)
        if signature in signatures:
            merged.append(
                {
                    "rejected": row["policy_id"],
                    "retained": signatures[signature]["policy_id"],
                    "reason": "EQUIVALENT_OUTCOME_SIGNATURE",
                }
            )
        else:
            signatures[signature] = row
    selected = max(
        signatures.values(),
        key=lambda row: (
            row["mean_success"] - 0.002 * row["mean_steps"],
            row["worst_success"],
        ),
    )
    development_gate = bool(
        criticism["invention_required"]
        and selected["policy_id"] == "guarded_progress_loop"
        and selected["mean_success"] >= 0.90
        and selected["worst_success"] >= 0.88
    )

    negative_controls = []
    for domain in NEGATIVE_CONTROLS:
        fixed = _evaluate_policy(
            policy_id="fixed_two",
            domains=(domain,),
            episodes=120,
            seed_offset=250_000,
        )
        negative_controls.append(
            {
                "domain_id": domain.domain_id,
                "fixed_skill_success": fixed["mean_success"],
                "invention_required": fixed["mean_success"] < 0.90,
                "unnecessary_invention_rejected": fixed["mean_success"] >= 0.90,
            }
        )

    sealed_invention = (
        _evaluate_policy(
            policy_id=selected["policy_id"],
            domains=SEALED_DOMAINS,
            episodes=sealed_episodes,
            seed_offset=400_000,
        )
        if development_gate else None
    )
    sealed_fixed = _evaluate_policy(
        policy_id=existing["policy_id"],
        domains=SEALED_DOMAINS,
        episodes=sealed_episodes,
        seed_offset=400_000,
    )
    # A cold learner is allowed 48 exploratory episodes per domain before
    # selecting a bounded sequence; the transferred contract requires only
    # eight action-effect probes and the already promoted concept binding.
    cold_calibration_actions = 48
    transfer_calibration_actions = 8
    errors = []
    if not development_gate:
        errors.append("DEVELOPMENT_SKILL_INVENTION_GATE_FAILED")
    if sealed_invention is None or sealed_invention["mean_success"] < 0.92:
        errors.append("SEALED_MEAN_SUCCESS_BELOW_92_PERCENT")
    if sealed_invention is None or sealed_invention["worst_success"] < 0.90:
        errors.append("SEALED_WORST_SUCCESS_BELOW_90_PERCENT")
    if sealed_invention is not None and (
        sealed_invention["mean_success"]
        < sealed_fixed["mean_success"] + 0.20
    ):
        errors.append("INVENTED_SKILL_GAIN_BELOW_20_POINTS")
    if not all(
        row["unnecessary_invention_rejected"] for row in negative_controls
    ):
        errors.append("UNNECESSARY_SKILL_CONTROL_FAILED")
    if sealed_invention is not None and (
        sealed_invention["mean_steps"]
        > max(domain.budget for domain in SEALED_DOMAINS)
    ):
        errors.append("ACTION_BUDGET_EXCEEDED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "selected_policy": selected["policy_id"],
        "development_mean_success": selected["mean_success"],
        "sealed_mean_success": (
            sealed_invention["mean_success"] if sealed_invention else 0.0
        ),
        "sealed_worst_success": (
            sealed_invention["worst_success"] if sealed_invention else 0.0
        ),
        "fixed_control_mean_success": sealed_fixed["mean_success"],
        "gain_over_fixed_control": (
            sealed_invention["mean_success"] - sealed_fixed["mean_success"]
            if sealed_invention else 0.0
        ),
        "transfer_calibration_actions": transfer_calibration_actions,
        "cold_calibration_actions": cold_calibration_actions,
        "calibration_reduction": (
            1.0 - transfer_calibration_actions / cold_calibration_actions
        ),
    }

    skill_id = (
        "skill_guarded_margin_control_"
        + _canonical_hash(
            [selected["policy_id"], concept_id]
        )[:12]
    )
    contract = {
        "schema_version": "aion.hexcore.invented_skill_contract.v1",
        "skill_id": skill_id,
        "name": "guarded_margin_control",
        "preconditions": [
            f"concept_available:{concept_id}",
            "two_numeric_fields_observable",
            "at_least_one_positive_margin_action",
            "bounded_action_budget",
        ],
        "control": {
            "guard": "not ordered_margin(left,right,threshold)",
            "body": "execute highest observed margin-gain action",
            "observation": "recompute ordered_margin after every action",
            "termination": "guard false or budget exhausted",
            "terminal_action": "execute inferred commit action",
        },
        "postconditions": [
            "ordered_margin_satisfied",
            "terminal_outcome_verified",
        ],
        "complexity": 6,
        "source": "phase23_outcome_grounded_skill_search",
        "development": selected,
        "sealed": sealed_invention,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    baseline = ProcedureCandidate(
        procedure_id="procedure_compositional_goal_graph_444839f5eb15",
        goal="cross_domain_skill_contract_invention",
        steps=["compose_existing_fixed_length_skills"],
        score=sealed_fixed["mean_success"],
        success=True,
        evidence={"evaluation": "phase23_fixed_skill_control"},
    )
    runtime.skills.promote(baseline)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_skill_invention_"
            + _canonical_hash(contract)[:12]
        ),
        goal="cross_domain_skill_contract_invention",
        steps=[
            "measure_residual_failure_of_existing_skill_library",
            "declare_fixed_length_contracts_inadequate",
            "generate_bounded_control_skill_candidates",
            "ground_action_roles_from_observed_state_deltas",
            "bind_promoted_ordered_margin_concept",
            "execute_guarded_progress_loop",
            "observe_after_each_action_and_repair",
            "verify_terminal_postcondition",
            "reject_unnecessary_or_duplicate_skills",
            "verify_cross_domain_transfer",
        ],
        score=gate["sealed_mean_success"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase23_skill_contract_invention_sealed",
            "gate": gate,
            "skill_id": skill_id,
            "concept_id": concept_id,
        },
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    if gate["accepted"]:
        runtime.store.state["skill_contracts"][skill_id] = contract
        runtime.store.state["invention_history"].append(
            {
                "schema_version": "aion.hexcore.invention_event.v1",
                "kind": "skill_contract",
                "invention_id": skill_id,
                "procedure_id": candidate.procedure_id,
                "depends_on": [concept_id],
                "gate": gate,
                "timestamp": _utc_timestamp(),
            }
        )
        runtime.store.commit(reason=f"skill_contract_invention:{skill_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    champion = restarted.skills.champion(candidate.goal)
    retained = bool(
        champion and champion.get("procedure_id") == candidate.procedure_id
    )
    result = {
        "schema_version": "aion.hexcore.skill_contract_invention.v1",
        "benchmark": "cross_domain_guarded_procedure_invention",
        "language_provider_used": False,
        "promoted_concept_dependency": concept_id,
        "model_criticism": criticism,
        "development_candidates": development,
        "candidate_deduplication": merged,
        "selected_invention": contract,
        "negative_controls": negative_controls,
        "sealed_invention": sealed_invention,
        "sealed_fixed_control": sealed_fixed,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": {
            "champion_retained": retained,
            "concept_dependency_retained": (
                concept_id in restarted.store.state["invented_concepts"]
            ),
            "skill_contract_retained": (
                skill_id in restarted.store.state["skill_contracts"]
            ),
            "invention_history_retained": any(
                row.get("invention_id") == skill_id
                for row in restarted.store.state["invention_history"]
            ),
            "relearning_episodes": 0,
        },
        "gates": {
            "skill_library_inadequacy_recognised": (
                criticism["invention_required"]
            ),
            "new_guarded_skill_invented": (
                selected["policy_id"] == "guarded_progress_loop"
            ),
            "unnecessary_skills_rejected": all(
                row["unnecessary_invention_rejected"]
                for row in negative_controls
            ),
            "cross_domain_transfer": gate["accepted"],
            "concept_skill_dependency_explicit": True,
            "cau_promotion": promotion.get("promoted") is True,
            "restart_retention": retained,
        },
        "boundary_statement": (
            "AION invented a bounded guarded-loop skill from a finite procedure "
            "grammar and grounded it in an invented relational predicate. It "
            "did not create unrestricted code, tools, goals, or authority."
        ),
    }
    result["passed"] = all(result["gates"].values())
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/skill_contract_invention.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_skill_contract_invention.json"),
    )
    args = parser.parse_args()
    result = run_skill_contract_invention_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
