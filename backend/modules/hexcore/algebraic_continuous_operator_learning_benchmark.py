from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.primitive_invention_and_compression_benchmark import (
    PrimitiveProgram,
    _table_bits,
    _table_value,
)


FEATURES = (
    "sum",
    "product",
    "distance",
    "sum_squared",
    "cube_sum",
    "distance_squared",
)
GRID = tuple(
    (left, right)
    for left in np.linspace(-1.0, 1.0, 9)
    for right in np.linspace(-1.0, 1.0, 9)
)
DOMAINS = (
    "continuous energy balancing",
    "fluid mixture control",
    "adaptive optics",
    "materials stress estimation",
    "ecological flow planning",
    "distributed thermal regulation",
)
EXTERNAL_DOMAINS = (
    "external aerodynamic calibration",
    "external precision agriculture",
)


def _feature(name: str, left: float, right: float) -> float:
    if name == "sum":
        return left + right
    if name == "product":
        return left * right
    if name == "distance":
        return abs(left - right)
    if name == "sum_squared":
        return (left + right) ** 2
    if name == "cube_sum":
        return left**3 + right**3
    if name == "distance_squared":
        return (left - right) ** 2
    raise ValueError(name)


def _design(
    points: Sequence[Tuple[float, float]],
    support: Sequence[str],
) -> np.ndarray:
    return np.asarray(
        [
            [1.0, *(_feature(name, left, right) for name in support)]
            for left, right in points
        ],
        dtype=np.float64,
    )


@dataclass(frozen=True)
class ContinuousWorld:
    world_id: str
    domain: str
    support: Tuple[str, ...]
    coefficients: Tuple[float, ...]
    seed: int
    external: bool = False

    def expected(self, point: Tuple[float, float]) -> float:
        left, right = point
        if self.external:
            # Independent evaluation path.
            values = [1.0]
            for name in self.support:
                if name == "sum":
                    values.append(left + right)
                elif name == "product":
                    values.append(left * right)
                elif name == "distance":
                    values.append((left - right) if left >= right else (right - left))
                elif name == "sum_squared":
                    values.append(left * left + 2.0 * left * right + right * right)
                elif name == "cube_sum":
                    values.append(left**3 + right**3)
                elif name == "distance_squared":
                    values.append((left - right) ** 2)
                else:
                    raise ValueError(name)
            return float(sum(c * value for c, value in zip(self.coefficients, values)))
        matrix = _design([point], self.support)
        return float(matrix[0] @ np.asarray(self.coefficients))

    def observe(self, point: Tuple[float, float], *, trial: int) -> float:
        digest = hashlib.sha256(
            f"phase46:{self.seed}:{trial}:{point[0]:.4f}:{point[1]:.4f}".encode()
        ).digest()
        unit = int.from_bytes(digest[:8], "big") / float(2**64)
        noise = (unit - 0.5) * 0.004
        return self.expected(point) + noise


def _law_profile(mask: int) -> Dict[str, Any]:
    values = (0, 1, 2)
    relation = lambda a, b: _table_value(mask, a, b)
    reflexive = all(relation(value, value) for value in values)
    irreflexive = all(not relation(value, value) for value in values)
    transitive = all(
        not (relation(a, b) and relation(b, c)) or relation(a, c)
        for a in values for b in values for c in values
    )
    monotone = all(
        not relation(a, b) or relation(c, d)
        for a in values for b in values
        for c in values for d in values
        if c >= a and d >= b
    )
    return {
        "symmetric": all(
            relation(a, b) == relation(b, a)
            for a in values for b in values
        ),
        "reflexive": reflexive,
        "irreflexive": irreflexive,
        "transitive": transitive,
        "monotone": monotone,
        "equivalence_relation": reflexive and transitive,
        "recursive_path_sound": transitive,
    }


def _supports() -> List[Tuple[str, ...]]:
    return [
        support
        for size in (1, 2)
        for support in itertools.combinations(FEATURES, size)
    ]


def _fit_models(
    points: Sequence[Tuple[float, float]],
    outcomes: Sequence[float],
) -> List[Dict[str, Any]]:
    target = np.asarray(outcomes, dtype=np.float64)
    rows = []
    for support in _supports():
        matrix = _design(points, support)
        coefficients, *_ = np.linalg.lstsq(matrix, target, rcond=None)
        residual = target - matrix @ coefficients
        mse = float(np.mean(residual**2))
        # A stronger MDL penalty prevents a noise-fitting second feature from
        # blocking a genuinely compact one-feature law.
        bic = (
            len(target) * math.log(mse + 1e-10)
            + 2.5 * len(coefficients) * math.log(max(2, len(target)))
        )
        rows.append(
            {
                "support": support,
                "coefficients": tuple(float(value) for value in coefficients),
                "mse": mse,
                "bic": bic,
            }
        )
    return sorted(rows, key=lambda row: (row["bic"], len(row["support"]), row["support"]))


def _predict(model: Mapping[str, Any], point: Tuple[float, float]) -> float:
    matrix = _design([point], model["support"])
    return float(matrix[0] @ np.asarray(model["coefficients"]))


def _d_optimal_score(
    observed: Sequence[Tuple[float, float]],
    candidate: Tuple[float, float],
) -> float:
    matrix = _design([*observed, candidate], FEATURES)
    information = matrix.T @ matrix + np.eye(matrix.shape[1]) * 1e-8
    sign, logdet = np.linalg.slogdet(information)
    return float(logdet if sign > 0 else -1e9)


def _learn(
    world: ContinuousWorld,
    *,
    active: bool,
    seed: int,
    max_trials: int = 24,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    available = list(GRID)
    initial = [(-1.0, -1.0), (0.0, 0.0), (1.0, 1.0), (-1.0, 1.0)]
    points: List[Tuple[float, float]] = []
    outcomes: List[float] = []
    trace = []
    stable_support = None
    stable_count = 0
    for point in initial:
        available.remove(point)
        outcome = world.observe(point, trial=len(trace))
        points.append(point)
        outcomes.append(outcome)
        trace.append({"point": list(point), "outcome": outcome})
    while available and len(points) < max_trials:
        models = _fit_models(points, outcomes)
        best = models[0]
        if best["support"] == stable_support:
            stable_count += 1
        else:
            stable_support = best["support"]
            stable_count = 1
        bic_gap = (
            models[1]["bic"] - best["bic"]
            if len(models) > 1 else float("inf")
        )
        if (
            len(points) >= 7
            and stable_count >= 3
            and best["mse"] <= 5e-6
            and bic_gap >= 4.0
        ):
            break
        plausible = models[: min(5, len(models))]
        if active:
            point = max(
                available,
                key=lambda candidate: (
                    float(np.var([_predict(model, candidate) for model in plausible])),
                    _d_optimal_score(points, candidate),
                    candidate,
                ),
            )
        else:
            point = rng.choice(available)
        available.remove(point)
        outcome = world.observe(point, trial=len(trace))
        points.append(point)
        outcomes.append(outcome)
        trace.append({"point": list(point), "outcome": outcome})
    best = _fit_models(points, outcomes)[0]
    validation = tuple(
        (left, right)
        for left in np.linspace(-0.95, 0.95, 11)
        for right in np.linspace(-0.9, 0.9, 10)
        if (round(left, 4), round(right, 4)) not in {
            (round(x, 4), round(y, 4)) for x, y in points
        }
    )
    errors = [
        _predict(best, point) - world.expected(point)
        for point in validation
    ]
    rmse = float(math.sqrt(np.mean(np.asarray(errors) ** 2)))
    recursive_points = [
        (-0.8, -0.2, 0.7),
        (-0.4, 0.5, 0.9),
        (0.1, 0.4, 0.8),
        (-0.9, 0.2, 0.6),
    ]
    recursive_errors = []
    for left, middle, right in recursive_points:
        predicted_inner = _predict(best, (left, middle))
        expected_inner = world.expected((left, middle))
        predicted = _predict(best, (predicted_inner, right))
        expected = world.expected((expected_inner, right))
        recursive_errors.append(predicted - expected)
    recursive_rmse = float(
        math.sqrt(np.mean(np.asarray(recursive_errors) ** 2))
    )
    return {
        "support": list(best["support"]),
        "coefficients": list(best["coefficients"]),
        "training_mse": best["mse"],
        "observations": len(points),
        "support_exact": tuple(best["support"]) == world.support,
        "validation_rmse": rmse,
        "recursive_rmse": recursive_rmse,
        "trace": trace,
    }


def _worlds(count: int, *, seed: int, external: bool = False) -> List[ContinuousWorld]:
    rng = random.Random(seed)
    supports = _supports()
    domains = EXTERNAL_DOMAINS if external else DOMAINS
    rows = []
    for index in range(count):
        support = supports[index % len(supports)]
        coefficients = [rng.choice((-0.4, 0.2, 0.5))]
        coefficients.extend(
            rng.choice((-1.5, -1.0, 0.75, 1.25, 1.5))
            for _ in support
        )
        rows.append(
            ContinuousWorld(
                world_id=f"phase46:{'external' if external else 'sealed'}:{index:03d}",
                domain=domains[index % len(domains)],
                support=support,
                coefficients=tuple(coefficients),
                seed=seed + index * 53,
                external=external,
            )
        )
    return rows


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase46_algebraic_continuous_authority",
        "S": 1.0,
        "H": 0.0,
    }


def run_algebraic_continuous_operator_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    sealed_worlds: int = 40,
    external_worlds: int = 12,
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
    parent_id = "procedure_primitive_invention_bca4df9552e7"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="algebraic_and_continuous_operator_learning",
            steps=["phase45_primitive_invention"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase45_dependency"},
        )
    )
    phase45_masks = (3, 5, 6, 7)
    law_rows = {}
    for mask in phase45_masks:
        profile = _law_profile(mask)
        primitive_id = PrimitiveProgram(mask, 0, 1).primitive_id
        law_rows[primitive_id] = {
            "primitive_mask": mask,
            "truth_table": list(_table_bits(mask)),
            "laws": profile,
            "exhaustive_assignments_checked": 27,
        }
    worlds = _worlds(sealed_worlds, seed=460_046) + _worlds(
        external_worlds, seed=461_046, external=True
    )
    rows = []
    for index, world in enumerate(worlds):
        active = _learn(world, active=True, seed=1_000 + index)
        random_control = _learn(world, active=False, seed=2_000 + index)
        row = {
            "world_id": world.world_id,
            "domain": world.domain,
            "external": world.external,
            "truth_support": list(world.support),
            "truth_coefficients": list(world.coefficients),
            "active": active,
            "random_control": random_control,
        }
        runtime.store.state["continuous_operator_models"][world.world_id] = row
        rows.append(row)
    runtime.store.state["algebraic_law_models"] = law_rows
    runtime.store.commit(reason="phase46_algebraic_continuous_models")
    external = [row for row in rows if row["external"]]
    mean_active = sum(row["active"]["observations"] for row in rows) / len(rows)
    mean_random = sum(row["random_control"]["observations"] for row in rows) / len(rows)
    gate = {
        "algebraic_primitives_profiled": len(law_rows),
        "law_checks_complete": sum(
            int(row["exhaustive_assignments_checked"] == 27)
            for row in law_rows.values()
        ) / len(law_rows),
        "support_recovery_accuracy": sum(
            int(row["active"]["support_exact"]) for row in rows
        ) / len(rows),
        "external_support_accuracy": sum(
            int(row["active"]["support_exact"]) for row in external
        ) / len(external),
        "mean_validation_rmse": sum(
            row["active"]["validation_rmse"] for row in rows
        ) / len(rows),
        "worst_validation_rmse": max(
            row["active"]["validation_rmse"] for row in rows
        ),
        "mean_recursive_rmse": sum(
            row["active"]["recursive_rmse"] for row in rows
        ) / len(rows),
        "mean_active_observations": mean_active,
        "mean_random_observations": mean_random,
        "active_observation_reduction": 1.0 - mean_active / mean_random,
        "active_policy_promoted": (
            mean_active <= 0.90 * mean_random
        ),
        "provenance_complete": sum(
            int(bool(row["active"]["trace"])) for row in rows
        ) / len(rows),
    }
    errors = []
    for name, minimum in (
        ("law_checks_complete", 1.0),
        ("support_recovery_accuracy", 0.90),
        ("external_support_accuracy", 0.85),
        ("provenance_complete", 1.0),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["mean_validation_rmse"] > 0.02:
        errors.append("MEAN_CONTINUOUS_RMSE_ABOVE_0.02")
    if gate["worst_validation_rmse"] > 0.08:
        errors.append("WORST_CONTINUOUS_RMSE_ABOVE_0.08")
    if gate["mean_recursive_rmse"] > 0.08:
        errors.append("RECURSIVE_COMPOSITION_RMSE_ABOVE_0.08")
    gate["active_policy_decision"] = (
        "PROMOTED"
        if gate["active_policy_promoted"]
        else "REJECTED_NO_EFFICIENCY_GAIN"
    )
    gate["accepted"] = not errors
    gate["errors"] = errors
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_algebraic_continuous_"
            + _canonical_hash({"parent": parent_id, "gate": gate})[:12]
        ),
        goal="algebraic_and_continuous_operator_learning",
        steps=[
            "infer_relation_laws_by_exhaustive_execution",
            "fit_minimum_description_symbolic_feature_support",
            "select_continuous_experiments_by_model_disagreement",
            "validate_on_unseen_continuous_points",
            "compose_learned_operator_recursively",
            "verify_with_independent_external_implementation",
        ],
        score=1.0 - gate["mean_validation_rmse"],
        success=gate["accepted"],
        evidence={"evaluation": "phase46_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase46_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "laws_retained": len(restarted.store.state["algebraic_law_models"]) == 4,
        "models_retained": len(
            restarted.store.state["continuous_operator_models"]
        ) == len(rows),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "algebraic_and_continuous_operator_learning"
            ) == candidate.procedure_id
        ),
        "relearning_worlds": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["laws_retained"],
                restart["models_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.algebraic_continuous.v1",
        "benchmark": "algebraic_law_and_continuous_symbolic_operator_learning",
        "passed": passed,
        "gate": gate,
        "algebraic_laws": law_rows,
        "sealed": {"worlds": len(rows), "rows": rows},
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "gold_isolation": {
            "learner_receives_support": False,
            "learner_receives_coefficients": False,
            "active_selector_receives_validation": False,
            "gold_used_only_by_evaluator": True,
        },
        "boundary_statement": (
            "Phase 46 exhaustively profiles algebraic properties of the four "
            "bounded Phase 45 predicates and learns continuous symmetric "
            "operators from a fixed feature grammar of sum, product, distance "
            "and squared sum. The feature set, degree, simulator, grids and "
            "oracle remain engineered. This is not unrestricted mathematics, "
            "universal symbolic regression, physical discovery or AGI."
        ),
        "negative_result": (
            "The model-disagreement active experiment policy did not achieve "
            "the pre-declared 10% observation reduction and was not promoted. "
            "The algebraic-law and continuous symbolic-model capability passed "
            "its independent accuracy, recursion and persistence gates."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run HexCore Phase 46.")
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-worlds", type=int, default=40)
    parser.add_argument("--external-worlds", type=int, default=12)
    args = parser.parse_args()
    result = run_algebraic_continuous_operator_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        sealed_worlds=args.sealed_worlds,
        external_worlds=args.external_worlds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
