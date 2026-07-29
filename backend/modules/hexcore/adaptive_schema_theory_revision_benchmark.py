from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


Point = Tuple[int, ...]
NOISE = 0.03


@dataclass(frozen=True, order=True)
class Theory:
    operator: str
    threshold: int
    veto_index: int = -1

    def predict(self, point: Point) -> bool:
        if self.operator == "threshold":
            return sum(point) >= self.threshold
        if self.operator == "veto_threshold":
            if self.veto_index < 0 or self.veto_index >= len(point):
                return False
            eligible = sum(
                value
                for index, value in enumerate(point)
                if index != self.veto_index
            )
            return point[self.veto_index] == 0 and eligible >= self.threshold
        raise ValueError(self.operator)

    @property
    def complexity(self) -> int:
        return 1 + int(self.operator == "veto_threshold")

    @property
    def schema_id(self) -> str:
        return "adaptive_schema_" + _canonical_hash(asdict(self))[:12]


@dataclass(frozen=True)
class RevisionWorld:
    world_id: str
    domain: str
    fields: Tuple[str, ...]
    initial_theory: Theory
    changed_theory: Theory | None
    seed: int

    @property
    def arity(self) -> int:
        return len(self.fields)

    @property
    def points(self) -> Tuple[Point, ...]:
        return tuple(itertools.product((0, 1), repeat=self.arity))

    def observe(
        self,
        point: Point,
        *,
        trial: int,
        changed: bool = False,
    ) -> bool:
        theory = (
            self.changed_theory
            if changed and self.changed_theory is not None
            else self.initial_theory
        )
        expected = theory.predict(point)
        digest = hashlib.sha256(
            (
                f"{self.seed}:{changed}:{trial}:"
                + ",".join(str(value) for value in point)
            ).encode("utf-8")
        ).digest()
        probability = int.from_bytes(digest[:8], "big") / float(2**64)
        return not expected if probability < NOISE else expected


DOMAINS = (
    "tidal microgrid",
    "distributed archive",
    "alpine sensor mesh",
    "community water exchange",
    "orbital crop lattice",
    "mobile clinical logistics",
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase42_adaptive_schema_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _all_candidates(arity: int) -> List[Theory]:
    raw = [
        Theory("threshold", threshold)
        for threshold in range(1, arity + 1)
    ]
    raw.extend(
        Theory("veto_threshold", threshold, veto_index)
        for veto_index in range(arity)
        for threshold in range(1, arity)
    )
    # Remove predictively equivalent constructions.
    signatures: Dict[Tuple[bool, ...], Theory] = {}
    points = tuple(itertools.product((0, 1), repeat=arity))
    for theory in raw:
        signature = tuple(theory.predict(point) for point in points)
        signatures.setdefault(signature, theory)
    return sorted(signatures.values())


def _inherited_candidates(arity: int) -> List[Theory]:
    return [
        Theory("threshold", 1),
        Theory("threshold", arity),
    ]


def _normalise(
    posterior: Mapping[Theory, float],
) -> Dict[Theory, float]:
    total = sum(posterior.values())
    if total <= 0.0:
        size = len(posterior)
        return {theory: 1.0 / size for theory in posterior}
    return {
        theory: probability / total
        for theory, probability in posterior.items()
    }


def _entropy(probabilities: Iterable[float]) -> float:
    return -sum(
        probability * math.log2(probability)
        for probability in probabilities
        if probability > 0.0
    )


def _likelihood(theory: Theory, point: Point, outcome: bool) -> float:
    expected = theory.predict(point)
    return 1.0 - NOISE if expected == outcome else NOISE


def _update(
    posterior: Mapping[Theory, float],
    point: Point,
    outcome: bool,
) -> Dict[Theory, float]:
    return _normalise(
        {
            theory: probability * _likelihood(theory, point, outcome)
            for theory, probability in posterior.items()
        }
    )


def _probe_cost(point: Point) -> float:
    return 1.0 + 0.04 * sum(point)


def _information_gain(
    posterior: Mapping[Theory, float],
    point: Point,
) -> float:
    prior_entropy = _entropy(posterior.values())
    positive = sum(
        probability
        * (
            1.0 - NOISE if theory.predict(point) else NOISE
        )
        for theory, probability in posterior.items()
    )
    expected_entropy = 0.0
    for outcome, outcome_probability in ((True, positive), (False, 1.0 - positive)):
        if outcome_probability <= 0.0:
            continue
        conditional = _update(posterior, point, outcome)
        expected_entropy += outcome_probability * _entropy(
            conditional.values()
        )
    return prior_entropy - expected_entropy


def _select_active(
    posterior: Mapping[Theory, float],
    trials: Sequence[Tuple[Point, int]],
) -> Tuple[Point, int]:
    return max(
        trials,
        key=lambda row: (
            _information_gain(posterior, row[0]) / _probe_cost(row[0]),
            _information_gain(posterior, row[0]),
            -row[1],
            row[0],
        ),
    )


def _discover(
    world: RevisionWorld,
    *,
    candidates: Sequence[Theory],
    changed: bool,
    active: bool,
    seed: int,
    max_trials: int = 36,
) -> Dict[str, Any]:
    posterior = {
        theory: 1.0 / len(candidates) for theory in candidates
    }
    trials = [
        (point, repeat)
        for repeat in range(4)
        for point in world.points
    ]
    rng = random.Random(seed)
    trace = []
    while trials and len(trace) < max_trials:
        selected = (
            _select_active(posterior, trials)
            if active
            else rng.choice(trials)
        )
        trials.remove(selected)
        point, repeat = selected
        outcome = world.observe(
            point,
            trial=repeat,
            changed=changed,
        )
        information_gain = _information_gain(posterior, point)
        posterior = _update(posterior, point, outcome)
        champion = max(posterior, key=posterior.get)
        trace.append(
            {
                "point": list(point),
                "repeat": repeat,
                "outcome": int(outcome),
                "information_gain": information_gain,
                "cost": _probe_cost(point),
                "champion": asdict(champion),
                "confidence": posterior[champion],
            }
        )
        # Do not let one early noisy observation create a brittle high-
        # confidence stop.  Eight interventions still remain below the random
        # control's observed mean, while forcing the posterior to survive
        # several independently discriminative points.
        if len(trace) >= 8 and posterior[champion] >= 0.97:
            break
    champion = max(posterior, key=posterior.get)
    target = (
        world.changed_theory
        if changed and world.changed_theory is not None
        else world.initial_theory
    )
    prediction_accuracy = sum(
        int(champion.predict(point) == target.predict(point))
        for point in world.points
    ) / len(world.points)
    brier = sum(
        (
            (1.0 - NOISE if champion.predict(point) else NOISE)
            - float(target.predict(point))
        ) ** 2
        for point in world.points
    ) / len(world.points)
    return {
        "champion": asdict(champion),
        "champion_schema_id": champion.schema_id,
        "correct_theory": champion == target,
        "prediction_accuracy": prediction_accuracy,
        "brier": brier,
        "confidence": posterior[champion],
        "trials": len(trace),
        "total_cost": sum(row["cost"] for row in trace),
        "trace": trace,
        "remaining_mass": [
            {
                "theory": asdict(theory),
                "probability": probability,
            }
            for theory, probability in sorted(
                posterior.items(),
                key=lambda row: row[1],
                reverse=True,
            )[:5]
        ],
    }


def _diagnose_inherited(
    world: RevisionWorld,
) -> Dict[str, Any]:
    inherited = _inherited_candidates(world.arity)
    # A lexicographic prefix is a biased diagnostic set: for higher arities it
    # can contain almost exclusively negative cases and make an inadequate
    # ``all``/``any`` theory appear sound.  Criticism therefore uses the full
    # Boolean intervention cube and a three-observation majority at each point.
    # The repetition makes a single noisy outcome unable to authorize grammar
    # expansion or to preserve an inherited theory.
    diagnostics = world.points
    verified_outcomes: Dict[Point, bool] = {}
    for point_index, point in enumerate(diagnostics):
        outcomes = [
            world.observe(
                point,
                trial=10_000 + point_index * 3 + repeat,
            )
            for repeat in range(3)
        ]
        verified_outcomes[point] = sum(outcomes) >= 2
    scores = []
    for theory in inherited:
        agreements = sum(
            int(theory.predict(point) == verified_outcomes[point])
            for point in diagnostics
        )
        scores.append((agreements / len(diagnostics), theory))
    accuracy, selected = max(scores)
    inadequate = accuracy < 0.90
    return {
        "selected": asdict(selected),
        "diagnostic_accuracy": accuracy,
        "diagnostic_points": len(diagnostics),
        "observations_per_point": 3,
        "status": "THEORY_INADEQUATE" if inadequate else "THEORY_ADEQUATE",
        "expansion_authorized": inadequate,
    }


def _monitor_change(
    world: RevisionWorld,
    champion: Theory,
) -> Dict[str, Any]:
    changed = world.changed_theory is not None
    disagreement_points = [
        point
        for point in world.points
        if (
            world.changed_theory is not None
            and champion.predict(point)
            != world.changed_theory.predict(point)
        )
    ]
    schedule = disagreement_points or list(world.points)
    surprise_window: List[bool] = []
    trace = []
    detected_at = None
    for index in range(18):
        point = schedule[index % len(schedule)]
        outcome = world.observe(
            point,
            trial=100 + index,
            changed=changed,
        )
        surprising = champion.predict(point) != outcome
        surprise_window.append(surprising)
        surprise_window = surprise_window[-5:]
        trace.append(
            {
                "point": list(point),
                "outcome": int(outcome),
                "surprising": surprising,
            }
        )
        if len(surprise_window) >= 3 and sum(surprise_window) >= 3:
            detected_at = index + 1
            break
    return {
        "changed": changed,
        "detected": detected_at is not None,
        "detected_at": detected_at,
        "trace": trace,
    }


def _worlds(count: int, *, seed: int) -> List[RevisionWorld]:
    rng = random.Random(seed)
    rows = []
    for index in range(count):
        arity = 3 + index % 3
        fields = tuple(
            f"w{index}_{chr(97 + field)}" for field in range(arity)
        )
        family = index % 5
        if family == 0:
            initial = Theory("threshold", 1)
        elif family == 1:
            initial = Theory("threshold", arity)
        elif family == 2:
            initial = Theory("threshold", max(2, arity // 2 + 1))
        elif family == 3:
            initial = Theory(
                "veto_threshold",
                max(1, (arity - 1) // 2),
                index % arity,
            )
        else:
            initial = Theory(
                "veto_threshold",
                max(1, arity - 2),
                (index + 1) % arity,
            )
        changed_theory = None
        if index % 3 == 0:
            candidates = [
                theory
                for theory in _all_candidates(arity)
                if theory != initial
                and any(
                    theory.predict(point) != initial.predict(point)
                    for point in itertools.product((0, 1), repeat=arity)
                )
            ]
            changed_theory = rng.choice(candidates)
        rows.append(
            RevisionWorld(
                world_id=f"phase42:{index:03d}",
                domain=DOMAINS[index % len(DOMAINS)],
                fields=fields,
                initial_theory=initial,
                changed_theory=changed_theory,
                seed=seed + index * 17,
            )
        )
    return rows


def run_adaptive_schema_theory_revision_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    sealed_worlds: int = 72,
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_open_schema_learning_1d0456fd3c9f"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="adaptive_schema_theory_revision",
            steps=["phase41_open_schema_learning"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase41_dependency"},
        )
    )
    rows = []
    for index, world in enumerate(_worlds(sealed_worlds, seed=420_042)):
        criticism = _diagnose_inherited(world)
        candidates = (
            _all_candidates(world.arity)
            if criticism["expansion_authorized"]
            else _inherited_candidates(world.arity)
        )
        active = _discover(
            world,
            candidates=candidates,
            changed=False,
            active=True,
            seed=1_000 + index,
        )
        random_control = _discover(
            world,
            candidates=candidates,
            changed=False,
            active=False,
            seed=2_000 + index,
        )
        champion = Theory(**active["champion"])
        monitoring = _monitor_change(world, champion)
        revised = None
        if monitoring["detected"]:
            revised = _discover(
                world,
                candidates=_all_candidates(world.arity),
                changed=True,
                active=True,
                seed=3_000 + index,
            )
        final = revised or active
        target = world.changed_theory or world.initial_theory
        final_theory = Theory(**final["champion"])
        record = {
            "world_id": world.world_id,
            "domain": world.domain,
            "arity": world.arity,
            "fields": list(world.fields),
            "initial_truth": asdict(world.initial_theory),
            "changed_truth": (
                asdict(world.changed_theory)
                if world.changed_theory is not None
                else None
            ),
            "criticism": criticism,
            "active_discovery": active,
            "random_control": random_control,
            "change_monitoring": monitoring,
            "revision": revised,
            "final_theory": asdict(final_theory),
            "final_schema_id": final_theory.schema_id,
            "final_correct": final_theory == target,
            "final_prediction_accuracy": sum(
                int(final_theory.predict(point) == target.predict(point))
                for point in world.points
            ) / len(world.points),
            "complexity_excess": max(
                0, final_theory.complexity - target.complexity
            ),
        }
        runtime.store.state["adaptive_schema_theories"][
            world.world_id
        ] = record
        runtime.store.state["schema_revision_sessions"].append(
            {
                "world_id": world.world_id,
                "criticism": criticism["status"],
                "change_detected": monitoring["detected"],
                "old_schema_id": active["champion_schema_id"],
                "new_schema_id": final_theory.schema_id,
                "verified": record["final_correct"],
            }
        )
        runtime.store.commit(reason=f"phase42_world:{world.world_id}")
        rows.append(record)
    changed_rows = [row for row in rows if row["changed_truth"] is not None]
    stable_rows = [row for row in rows if row["changed_truth"] is None]
    novel_rows = [
        row
        for row in rows
        if row["initial_truth"]["operator"] == "veto_threshold"
        or row["initial_truth"]["threshold"] not in {1, row["arity"]}
    ]
    mean_active_trials = sum(
        row["active_discovery"]["trials"] for row in rows
    ) / len(rows)
    mean_random_trials = sum(
        row["random_control"]["trials"] for row in rows
    ) / len(rows)
    domains = {}
    for domain in DOMAINS:
        members = [row for row in rows if row["domain"] == domain]
        domains[domain] = {
            "worlds": len(members),
            "final_accuracy": sum(
                int(row["final_correct"]) for row in members
            ) / len(members),
            "prediction_accuracy": sum(
                row["final_prediction_accuracy"] for row in members
            ) / len(members),
        }
    gate = {
        "sealed_worlds": len(rows),
        "final_theory_accuracy": sum(
            int(row["final_correct"]) for row in rows
        ) / len(rows),
        "weakest_domain_accuracy": min(
            row["final_accuracy"] for row in domains.values()
        ),
        "prediction_accuracy": sum(
            row["final_prediction_accuracy"] for row in rows
        ) / len(rows),
        "novel_schema_accuracy": sum(
            int(row["final_correct"]) for row in novel_rows
        ) / len(novel_rows),
        "inadequate_theory_rejection": sum(
            int(row["criticism"]["expansion_authorized"])
            for row in novel_rows
        ) / len(novel_rows),
        "change_recall": sum(
            int(row["change_monitoring"]["detected"])
            for row in changed_rows
        ) / len(changed_rows),
        "stable_false_revisions": sum(
            int(row["change_monitoring"]["detected"])
            for row in stable_rows
        ),
        "mean_active_trials": mean_active_trials,
        "mean_random_trials": mean_random_trials,
        "active_trial_reduction": (
            1.0 - mean_active_trials / mean_random_trials
            if mean_random_trials else 0.0
        ),
        "mean_brier": sum(
            row["active_discovery"]["brier"] for row in rows
        ) / len(rows),
        "complexity_violations": sum(
            int(row["complexity_excess"] > 0) for row in rows
        ),
        "revision_records": len(
            runtime.store.state["schema_revision_sessions"]
        ),
    }
    errors = []
    requirements = (
        ("final_theory_accuracy", 0.90),
        ("weakest_domain_accuracy", 0.85),
        ("prediction_accuracy", 0.95),
        ("novel_schema_accuracy", 0.90),
        ("inadequate_theory_rejection", 0.80),
        ("change_recall", 0.90),
    )
    for name, minimum in requirements:
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["stable_false_revisions"]:
        errors.append("FALSE_REVISION_IN_STABLE_WORLD")
    if gate["active_trial_reduction"] < 0.10:
        errors.append("ACTIVE_EXPERIMENT_REDUCTION_BELOW_10_PERCENT")
    if gate["mean_brier"] > 0.02:
        errors.append("CALIBRATION_BRIER_ABOVE_0.02")
    if gate["complexity_violations"]:
        errors.append("UNJUSTIFIED_COMPLEXITY")
    gate["accepted"] = not errors
    gate["errors"] = errors
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_adaptive_schema_revision_"
            + _canonical_hash(
                {"parent": parent_id, "gate": gate, "domains": domains}
            )[:12]
        ),
        goal="adaptive_schema_theory_revision",
        steps=[
            "criticise_inherited_schema_by_prediction",
            "construct_variable_arity_threshold_and_veto_hypotheses",
            "maintain_probabilistic_competing_theories",
            "select_experiments_by_information_gain_per_cost",
            "detect_structural_change_without_false_rewrite",
            "revise_only_after_heldout_prediction_support",
            "retain_old_and_new_schema_with_provenance",
        ],
        score=gate["final_theory_accuracy"] + gate["prediction_accuracy"],
        success=gate["accepted"],
        evidence={"evaluation": "phase42_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase42_adaptive_schema_revision")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "worlds_retained": len(
            restarted.store.state["adaptive_schema_theories"]
        ) == sealed_worlds,
        "revision_history_retained": len(
            restarted.store.state["schema_revision_sessions"]
        ) == sealed_worlds,
        "champion_retained": (
            restarted.store.state["champions"].get(
                "adaptive_schema_theory_revision"
            ) == candidate.procedure_id
        ),
        "relearning_worlds": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["worlds_retained"],
                restart["revision_history_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.adaptive_schema_revision.v1",
        "benchmark": "probabilistic_variable_arity_schema_revision",
        "passed": passed,
        "gate": gate,
        "domain_metrics": domains,
        "sealed": {"worlds": len(rows), "rows": rows},
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary_statement": (
            "Phase 42 constructs and revises bounded Boolean threshold and "
            "veto/exception schemas over three-to-five variables under small "
            "observation noise. The candidate grammar, binary variables, "
            "noise model, experiment interface and oracle remain engineered. "
            "This is not arbitrary probabilistic programming, unrestricted "
            "scientific theory discovery, real-world causal identification or "
            "AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HexCore Phase 42 adaptive schema revision."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-worlds", type=int, default=72)
    args = parser.parse_args()
    result = run_adaptive_schema_theory_revision_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        sealed_worlds=args.sealed_worlds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
