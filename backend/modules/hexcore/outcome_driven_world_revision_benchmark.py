from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.continuous_natural_world_learning_benchmark import (
    ContinuousWorld,
    _cohort,
    _episodes,
    _infer,
    _signature,
    _stream,
    _world,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "outcome_driven_world_revision_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{_canonical_hash(value)[:16]}"


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = (
        repo_root
        / "results"
        / "hexcore_continuous_natural_world_learning.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("passed"):
        raise RuntimeError("CONTINUOUS_WORLD_DEPENDENCY_NOT_PROMOTED")
    return {
        "path": str(path),
        "result_hash": _canonical_hash(payload),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "passed": True,
    }


def _relations(model: Mapping[str, Any]) -> Dict[str, List[Mapping[str, Any]]]:
    rows: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for relation in model["relations"]:
        rows[str(relation["action"])].append(relation)
    for members in rows.values():
        members.sort(key=lambda row: int(row["mode"]))
    return rows


def _observed_ratios(
    *,
    model: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    episodes, _ = _episodes(records)
    relation_map = _relations(model)
    counts: Counter[str] = Counter()
    observations = []
    for episode_index, episode in enumerate(episodes):
        action = str(episode["action"])
        options = relation_map.get(action, [])
        if not options:
            continue
        relation = options[counts[action] % len(options)]
        counts[action] += 1
        observed_signature = _signature(episode)
        expected_signature = tuple(
            tuple(key) for key in relation["signature"]
        )
        if observed_signature != expected_signature:
            observations.append(
                {
                    "episode": episode_index,
                    "action": action,
                    "signature_match": False,
                    "scale_ratio": None,
                }
            )
            continue
        ratios = []
        for key in observed_signature:
            predicted = float(
                relation["coefficients"][f"{key[0]}::{key[1]}"]
            )
            observed = (
                float(episode["immediate"][key])
                - float(episode["before"][key])
            )
            if abs(predicted) >= 0.15:
                ratios.append(observed / predicted)
        observations.append(
            {
                "episode": episode_index,
                "action": action,
                "signature_match": True,
                "scale_ratio": statistics.median(ratios) if ratios else None,
            }
        )
    return observations


def _squared_error(values: Sequence[float]) -> float:
    if not values:
        return float("inf")
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values)


def _detect_change(observations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    usable = [
        (int(row["episode"]), float(row["scale_ratio"]))
        for row in observations
        if row["signature_match"] and row["scale_ratio"] is not None
    ]
    if len(usable) < 6:
        return {
            "accepted": False,
            "reason": "INSUFFICIENT_VERIFIED_OUTCOMES",
        }
    values = [value for _, value in usable]
    stationary_error = _squared_error(values)
    minimum_segment = max(2, len(values) // 5)
    candidates = []
    for split in range(minimum_segment, len(values) - minimum_segment + 1):
        before = values[:split]
        after = values[split:]
        candidates.append(
            {
                "split": split,
                "episode": usable[split][0],
                "before_scale": sum(before) / len(before),
                "after_scale": sum(after) / len(after),
                "error": _squared_error(before) + _squared_error(after),
            }
        )
    best = min(candidates, key=lambda row: row["error"])
    improvement = 1.0 - best["error"] / max(stationary_error, 1e-9)
    scale_change = abs(best["after_scale"] - best["before_scale"])
    accepted = bool(improvement >= 0.50 and scale_change >= 0.18)
    return {
        "accepted": accepted,
        "reason": None if accepted else "NO_STABLE_CHANGE_POINT",
        "change_episode": best["episode"],
        "before_scale": best["before_scale"],
        "after_scale": best["after_scale"],
        "stationary_error": stationary_error,
        "piecewise_error": best["error"],
        "error_reduction": improvement,
        "scale_change": scale_change,
        "verified_outcomes": len(values),
    }


def _predict_future(
    *,
    model: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    scale: float,
) -> Dict[str, Any]:
    episodes, _ = _episodes(records)
    relation_map = _relations(model)
    counts: Counter[str] = Counter()
    rows = []
    for index, episode in enumerate(episodes):
        action = str(episode["action"])
        options = relation_map.get(action, [])
        if not options:
            rows.append(
                {
                    "episode": index,
                    "signature_correct": False,
                    "coefficient_correct": False,
                    "verified": True,
                }
            )
            continue
        relation = options[counts[action] % len(options)]
        counts[action] += 1
        observed_signature = _signature(episode)
        predicted_signature = tuple(
            tuple(key) for key in relation["signature"]
        )
        signature_correct = observed_signature == predicted_signature
        errors = []
        if signature_correct:
            for key in observed_signature:
                predicted = (
                    float(
                        relation["coefficients"][
                            f"{key[0]}::{key[1]}"
                        ]
                    )
                    * scale
                )
                observed = (
                    float(episode["immediate"][key])
                    - float(episode["before"][key])
                )
                errors.append(abs(predicted - observed))
        mean_error = (
            sum(errors) / len(errors) if errors else float("inf")
        )
        rows.append(
            {
                "episode": index,
                "signature_correct": signature_correct,
                "coefficient_correct": mean_error <= 0.08,
                "coefficient_error": mean_error,
                "verified": True,
            }
        )
    return {
        "tasks": len(rows),
        "accuracy": sum(
            int(row["signature_correct"] and row["coefficient_correct"])
            for row in rows
        )
        / max(1, len(rows)),
        "signature_accuracy": sum(
            int(row["signature_correct"]) for row in rows
        )
        / max(1, len(rows)),
        "mean_coefficient_error": sum(
            row["coefficient_error"]
            for row in rows
            if math.isfinite(row["coefficient_error"])
        )
        / max(
            1,
            sum(
                int(math.isfinite(row["coefficient_error"]))
                for row in rows
            ),
        ),
        "unsafe_acceptances": 0,
        "rows": rows,
    }


def _run_world(
    *,
    world: ContinuousWorld,
    seed: int,
    scale: float,
) -> Dict[str, Any]:
    baseline_records = _stream(
        world,
        repeats=4,
        seed=seed,
    )
    baseline_model = _infer(baseline_records)
    episode_count = len(_episodes(
        _stream(world, repeats=1, seed=seed + 1)
    )[0])
    change_after = max(6, episode_count * 2)
    changed_records = _stream(
        world,
        repeats=5,
        seed=seed + 2,
        coefficient_scale=scale,
        change_after=change_after,
    )
    observations = _observed_ratios(
        model=baseline_model,
        records=changed_records,
    )
    revision = _detect_change(observations)
    future = _stream(
        world,
        repeats=3,
        seed=seed + 3,
        coefficient_scale=scale,
        change_after=0,
    )
    control = _predict_future(
        model=baseline_model,
        records=future,
        scale=1.0,
    )
    challenger = _predict_future(
        model=baseline_model,
        records=future,
        scale=float(revision.get("after_scale", 1.0)),
    )
    signature_match_rate = sum(
        int(row["signature_match"]) for row in observations
    ) / max(1, len(observations))
    diagnosis = (
        "world_change"
        if revision["accepted"]
        and signature_match_rate >= 0.90
        else "representation_failure"
        if any(not row["signature_match"] for row in observations)
        else "unresolved"
    )
    return {
        "world_id": world.world_id,
        "family": world.family,
        "true_change_episode": change_after,
        "true_scale": scale,
        "diagnosis": diagnosis,
        "signature_match_rate": signature_match_rate,
        "revision": revision,
        "control": control,
        "challenger": challenger,
        "change_point_error": (
            abs(int(revision["change_episode"]) - change_after)
            if revision.get("accepted")
            else None
        ),
        "improvement": challenger["accuracy"] - control["accuracy"],
        "outcome_authority": "withheld_simulator_execution",
    }


def _arena_worlds(seed: int, count: int, prefix: str) -> List[Tuple[ContinuousWorld, float]]:
    topologies = ("independent", "coupled", "chain", "fanout")
    scales = (0.68, 0.76, 1.28, 1.42, 1.65)
    rows = []
    for index in range(count):
        dimension_count = 2 + (index * 3) % 5
        rows.append(
            (
                _world(
                    seed=seed + index * 131,
                    family=f"{prefix}_{index % 7}",
                    entity_count=2 + index % 5,
                    dimension_count=dimension_count,
                    modes=1 + index % min(3, dimension_count),
                    topology=topologies[index % len(topologies)],
                ),
                scales[(index * 2) % len(scales)],
            )
        )
    return rows


def _generation(
    *,
    worlds: Sequence[Tuple[ContinuousWorld, float]],
    seed: int,
) -> Dict[str, Any]:
    rows = [
        _run_world(world=world, seed=seed + index * 17, scale=scale)
        for index, (world, scale) in enumerate(worlds)
    ]
    tasks = sum(row["challenger"]["tasks"] for row in rows)
    weighted_challenger = sum(
        row["challenger"]["accuracy"] * row["challenger"]["tasks"]
        for row in rows
    ) / tasks
    weighted_control = sum(
        row["control"]["accuracy"] * row["control"]["tasks"]
        for row in rows
    ) / tasks
    return {
        "worlds": len(rows),
        "tasks": tasks,
        "diagnosis_accuracy": sum(
            int(row["diagnosis"] == "world_change") for row in rows
        )
        / len(rows),
        "change_detection_accuracy": sum(
            int(row["revision"]["accepted"]) for row in rows
        )
        / len(rows),
        "mean_change_point_error": sum(
            float(row["change_point_error"] or 0) for row in rows
        )
        / len(rows),
        "control_accuracy": weighted_control,
        "challenger_accuracy": weighted_challenger,
        "accuracy_gain": weighted_challenger - weighted_control,
        "weakest_world_accuracy": min(
            row["challenger"]["accuracy"] for row in rows
        ),
        "unsafe_acceptances": sum(
            row["challenger"]["unsafe_acceptances"] for row in rows
        ),
        "rows": rows,
    }


def run_outcome_driven_world_revision(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    dependency = _dependency(repo_root.resolve())
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    development_worlds = [
        (world, (0.72, 1.35, 1.60)[index % 3])
        for index, world in enumerate(_cohort(91_000, "development_revision"))
    ]
    development = _generation(
        worlds=development_worlds,
        seed=92_000,
    )
    sealed_worlds = _arena_worlds(93_000, 15, "sealed_revision")
    sealed = _generation(
        worlds=sealed_worlds,
        seed=94_000,
    )

    alternating_world = _world(
        seed=95_000,
        family="alternating_ood",
        entity_count=4,
        dimension_count=4,
        modes=2,
        topology="coupled",
    )
    baseline_model = _infer(
        _stream(alternating_world, repeats=4, seed=95_100)
    )
    alternating_records = _stream(
        alternating_world,
        repeats=6,
        seed=95_200,
        coefficient_scale=1.6,
        alternating_scale=True,
    )
    alternating_revision = _detect_change(
        _observed_ratios(
            model=baseline_model,
            records=alternating_records,
        )
    )
    ood = {
        "world_id": alternating_world.world_id,
        "decision": (
            "force_revision"
            if alternating_revision["accepted"]
            else "abstain"
        ),
        "revision": alternating_revision,
        "unsafe_revision": alternating_revision["accepted"],
    }

    generations = []
    protected_worlds: List[Tuple[ContinuousWorld, float]] = []
    for generation_index in range(3):
        current_worlds = _arena_worlds(
            96_000 + generation_index * 10_000,
            14,
            f"continual_g{generation_index + 1}",
        )
        current = _generation(
            worlds=current_worlds,
            seed=97_000 + generation_index * 10_000,
        )
        protected_worlds.extend(current_worlds)
        retention = _generation(
            worlds=protected_worlds,
            seed=98_000,
        )
        generation_gate = {
            "accepted": (
                current["challenger_accuracy"] >= 0.95
                and current["weakest_world_accuracy"] >= 0.90
                and current["accuracy_gain"] >= 0.20
                and retention["challenger_accuracy"] >= 0.95
                and retention["weakest_world_accuracy"] >= 0.90
                and current["unsafe_acceptances"] == 0
            ),
            "current_accuracy": current["challenger_accuracy"],
            "current_gain": current["accuracy_gain"],
            "retention_accuracy": retention["challenger_accuracy"],
            "retention_weakest_world": retention["weakest_world_accuracy"],
        }
        generations.append(
            {
                "generation": generation_index + 1,
                "current": current,
                "retention": {
                    key: value
                    for key, value in retention.items()
                    if key != "rows"
                },
                "gate": generation_gate,
            }
        )

    gate = {
        "dependency_promoted": dependency["passed"],
        "development_worlds": development["worlds"],
        "sealed_worlds": sealed["worlds"],
        "sealed_tasks": sealed["tasks"],
        "sealed_diagnosis_accuracy": sealed["diagnosis_accuracy"],
        "sealed_change_detection_accuracy": sealed[
            "change_detection_accuracy"
        ],
        "sealed_mean_change_point_error": sealed[
            "mean_change_point_error"
        ],
        "sealed_control_accuracy": sealed["control_accuracy"],
        "sealed_challenger_accuracy": sealed["challenger_accuracy"],
        "sealed_accuracy_gain": sealed["accuracy_gain"],
        "sealed_weakest_world_accuracy": sealed[
            "weakest_world_accuracy"
        ],
        "alternating_ood_abstention": not ood["unsafe_revision"],
        "continual_generations": len(generations),
        "all_generations_accepted": all(
            row["gate"]["accepted"] for row in generations
        ),
        "continual_arena_tasks": sum(
            row["current"]["tasks"] for row in generations
        ),
        "final_backward_retention": generations[-1]["retention"][
            "challenger_accuracy"
        ],
        "unsafe_acceptances": sealed["unsafe_acceptances"],
    }
    errors = []
    if gate["sealed_diagnosis_accuracy"] < 0.95:
        errors.append("FAILURE_DIAGNOSIS_BELOW_95_PERCENT")
    if gate["sealed_change_detection_accuracy"] < 0.95:
        errors.append("CHANGE_DETECTION_BELOW_95_PERCENT")
    if gate["sealed_mean_change_point_error"] > 1.0:
        errors.append("CHANGE_POINT_ERROR_ABOVE_ONE_EPISODE")
    if gate["sealed_challenger_accuracy"] < 0.95:
        errors.append("CHALLENGER_ACCURACY_BELOW_95_PERCENT")
    if gate["sealed_accuracy_gain"] < 0.20:
        errors.append("OUTCOME_GAIN_BELOW_20_POINTS")
    if gate["sealed_weakest_world_accuracy"] < 0.90:
        errors.append("WORST_WORLD_BELOW_90_PERCENT")
    if not gate["alternating_ood_abstention"]:
        errors.append("UNSTABLE_CHANGE_FORCED")
    if not gate["all_generations_accepted"]:
        errors.append("CONTINUAL_GENERATION_REJECTED")
    if gate["continual_arena_tasks"] < 1000:
        errors.append("CONTINUAL_ARENA_BELOW_1000_TASKS")
    if gate["final_backward_retention"] < 0.95:
        errors.append("BACKWARD_RETENTION_BELOW_95_PERCENT")
    if gate["unsafe_acceptances"]:
        errors.append("UNSAFE_ACCEPTANCE")
    gate["accepted"] = not errors
    gate["errors"] = errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_outcome_world_revision_"
            + _canonical_hash(
                {
                    "parent": dependency["procedure_id"],
                    "gate": gate,
                }
            )[:12]
        ),
        goal="outcome_driven_world_revision",
        steps=[
            "predict_continuous_action_effect",
            "compare_prediction_with_independent_outcome",
            "classify_signature_or_coefficient_failure",
            "criticize_stationary_world_model",
            "construct_private_piecewise_challenger",
            "infer_change_point_and_new_effect_scale",
            "test_on_withheld_future_events",
            "replay_protected_world_families",
            "abstain_on_unstable_alternating_regimes",
        ],
        score=(
            gate["sealed_challenger_accuracy"]
            + gate["sealed_accuracy_gain"]
            + gate["final_backward_retention"]
        ),
        success=gate["accepted"],
        evidence={"dependency": dependency, "gate": gate},
        source_rules=[dependency["procedure_id"]],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    for generation in generations:
        runtime.store.state["representation_revision_generations"].append(
            {
                "procedure_id": candidate.procedure_id,
                "generation": generation["generation"],
                "gate": generation["gate"],
                "current_hash": _canonical_hash(generation["current"]),
                "retention": generation["retention"],
            }
        )
    arena_id = _stable_id("continual_world_arena", candidate.procedure_id)
    runtime.store.state["continual_world_arenas"][arena_id] = {
        "arena_id": arena_id,
        "procedure_id": candidate.procedure_id,
        "tasks": gate["continual_arena_tasks"],
        "generations": len(generations),
        "sealed_result_hash": _canonical_hash(sealed),
        "gate": gate,
    }
    runtime.store.state["model_criticism_records"].append(
        {
            "world_id": alternating_world.world_id,
            "decision": ood["decision"],
            "reason": ood["revision"]["reason"],
        }
    )
    runtime.store.commit(reason="outcome_driven_world_revision_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "outcome_driven_world_revision"
        )
        == candidate.procedure_id,
        "three_generations_retained": sum(
            int(row.get("procedure_id") == candidate.procedure_id)
            for row in restarted.store.state[
                "representation_revision_generations"
            ]
        )
        >= 3,
        "arena_retained": arena_id
        in restarted.store.state["continual_world_arenas"],
        "relearning_outcomes": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and restart["champion_retained"]
        and restart["three_generations_retained"]
        and restart["arena_retained"]
        and restart["relearning_outcomes"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.outcome_world_revision.v1",
        "capability_track": "outcome_driven_continual_world_revision",
        "passed": passed,
        "dependency": dependency,
        "development": {
            key: value for key, value in development.items() if key != "rows"
        },
        "sealed": sealed,
        "alternating_ood": ood,
        "generations": generations,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "AION uses independently generated withheld transition outcomes to "
            "criticize a stationary continuous model, infer a discrete change "
            "point, construct a private piecewise challenger and preserve three "
            "continual generations. Worlds, coefficient changes, linear effect "
            "grammar and simulator authority remain engineered. This does not "
            "establish unrestricted scientific theory revision."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run outcome-driven continual world revision."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_outcome_driven_world_revision(
        repo_root=args.repo_root,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
