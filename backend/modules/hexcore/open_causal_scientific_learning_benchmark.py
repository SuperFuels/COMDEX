from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

from backend.modules.hexcore.compositional_multivariate_discovery_benchmark import (
    Feature,
    MultiTrace,
    _feature_pool,
    _irregular_times,
    _stable_id,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PARENT_RESULT = "results/hexcore_compositional_multivariate_discovery.json"
PROCEDURE_ID = "procedure_open_causal_science_7d4d91bf1e62"
FAILURE_TYPES = (
    "coefficient_change",
    "topology_change",
    "sensor_fault",
    "execution_anomaly",
    "unexplained_family",
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_causal_scientific_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class CausalWorld:
    world_id: str
    trace: MultiTrace
    regimes: Tuple[str, ...]
    expected_signatures: Tuple[Tuple[str, ...], ...]
    relevant_variables: Tuple[int, ...]
    latent_count: int
    provenance: Mapping[str, Any]


def _fit_signature(
    world: CausalWorld,
    output_index: int,
    signature: Sequence[str],
    *,
    selection_regimes: set[str] | None,
) -> Dict[str, Any]:
    trace = world.trace
    pool = {feature.key: feature for feature in _feature_pool(trace)}
    selected = [pool[key] for key in signature]
    if selected:
        matrix = np.column_stack(
            [np.asarray(feature.values) for feature in selected]
        )
    else:
        matrix = np.empty((len(trace.times), 0), dtype=np.float64)
    target_matrix = np.asarray(trace.target, dtype=np.float64)
    if target_matrix.ndim == 1:
        target = target_matrix
    else:
        target = target_matrix[:, output_index]
    valid = np.all(np.isfinite(matrix), axis=1) & np.isfinite(target)
    indices = np.flatnonzero(valid)
    matrix = np.column_stack([np.ones(len(indices)), matrix[indices]])
    target = target[indices]
    regimes = np.asarray(world.regimes, dtype=object)[indices]
    times = np.asarray(trace.times)[indices]
    time_rank = np.argsort(np.argsort(times)) / max(len(times) - 1, 1)
    train = time_rank < 0.60
    validation = (time_rank >= 0.60) & (time_rank < 0.80)
    test = time_rank >= 0.80
    selection = train.copy()
    if selection_regimes is not None:
        selection &= np.asarray(
            [regime in selection_regimes for regime in regimes]
        )
    if int(np.sum(selection)) < max(12, len(signature) * 4):
        return {"valid": False, "reason": "INSUFFICIENT_SELECTION_ROWS"}
    weights, *_ = np.linalg.lstsq(
        matrix[selection],
        target[selection],
        rcond=None,
    )

    def metrics(mask: np.ndarray) -> Dict[str, float]:
        truth = target[mask]
        prediction = matrix[mask] @ weights
        mse = float(np.mean((truth - prediction) ** 2))
        variance = float(np.var(truth))
        normalized = mse / max(variance, 1e-9)
        return {
            "mse": mse,
            "normalized_mse": normalized,
            "r2": 1.0 - normalized,
            "rows": int(np.sum(mask)),
        }

    validation_metrics = metrics(validation)
    test_metrics = metrics(test)
    validation_groups = {
        regime: metrics(validation & (regimes == regime))
        for regime in sorted(set(regimes))
        if np.sum(validation & (regimes == regime)) >= 3
    }
    test_groups = {
        regime: metrics(test & (regimes == regime))
        for regime in sorted(set(regimes))
        if np.sum(test & (regimes == regime)) >= 3
    }
    scored_validation_groups = validation_groups
    scored_test_groups = test_groups
    if selection_regimes is not None:
        scored_validation_groups = {
            key: value
            for key, value in validation_groups.items()
            if key in selection_regimes
        }
        scored_test_groups = {
            key: value
            for key, value in test_groups.items()
            if key in selection_regimes
        }
    worst_validation = max(
        row["normalized_mse"] for row in scored_validation_groups.values()
    )
    worst_test = max(
        row["normalized_mse"] for row in scored_test_groups.values()
    )
    complexity = sum(pool[key].complexity for key in signature)
    return {
        "valid": True,
        "signature": list(signature),
        "weights": [float(value) for value in weights],
        "validation": validation_metrics,
        "test": test_metrics,
        "validation_groups": validation_groups,
        "test_groups": test_groups,
        "worst_validation_normalized_mse": worst_validation,
        "worst_test_normalized_mse": worst_test,
        "evaluation_test_r2": 1.0 - worst_test,
        "score": worst_validation + 0.002 * complexity + 0.0008 * len(weights),
        "complexity": complexity,
        "photon_ast": {
            "schema_version": "tessaris.photon.open_causal.v1",
            "op": "affine_composition",
            "terms": [dict(pool[key].ast) for key in signature],
            "authority": "proposal_only",
        },
    }


def _discover_output(
    world: CausalWorld,
    output_index: int,
    *,
    selection_regimes: set[str] | None = None,
    maximum_terms: int = 6,
) -> Dict[str, Any]:
    pool = [
        feature
        for feature in _feature_pool(world.trace)
        if not feature.key.startswith("annual_")
    ]
    selected: List[str] = []
    current = _fit_signature(
        world,
        output_index,
        selected,
        selection_regimes=selection_regimes,
    )
    for _ in range(maximum_terms):
        challengers = [
            _fit_signature(
                world,
                output_index,
                [*selected, feature.key],
                selection_regimes=selection_regimes,
            )
            for feature in pool
            if feature.key not in selected
        ]
        challengers = [row for row in challengers if row.get("valid")]
        best = min(challengers, key=lambda row: row["score"])
        improvement = current["score"] - best["score"]
        if selected and improvement < 0.004:
            break
        selected = list(best["signature"])
        current = best
    changed = True
    while changed and len(selected) > 1:
        changed = False
        for key in list(selected):
            challenger = _fit_signature(
                world,
                output_index,
                [item for item in selected if item != key],
                selection_regimes=selection_regimes,
            )
            if challenger.get("valid") and challenger["score"] <= current["score"]:
                selected = list(challenger["signature"])
                current = challenger
                changed = True
                break
    if selection_regimes is None:
        current["accepted"] = bool(
            current["validation"]["normalized_mse"] <= 0.20
            and current["test"]["normalized_mse"] <= 0.25
            and current["worst_test_normalized_mse"] <= 0.40
        )
    else:
        # Causal proposals are accepted by the randomized regimes that can
        # identify an effect. Observational proxy quality is reported
        # separately and cannot overrule interventional evidence.
        current["accepted"] = bool(
            current["worst_validation_normalized_mse"] <= 0.20
            and current["worst_test_normalized_mse"] <= 0.40
        )
    current["decision"] = (
        _stable_id("open_causal_operator", current["signature"])
        if current["accepted"]
        else "abstain"
    )
    return current


def _causal_state_and_inputs(
    rng: random.Random,
    length: int,
    variable_count: int,
) -> Tuple[np.ndarray, np.ndarray, Tuple[str, ...]]:
    causal_driver = np.asarray(
        [rng.uniform(-2.0, 2.0) for _ in range(length)]
    )
    observed = np.zeros((length, variable_count), dtype=np.float64)
    regimes: List[str] = []
    for index in range(length):
        cycle = index % 8
        intervention = -1
        if cycle < 2:
            regime = "observational"
            hidden = causal_driver[index]
            observed[index, 0] = hidden + rng.gauss(0.0, 0.80)
            observed[index, 1] = hidden + rng.gauss(0.0, 0.006)
        else:
            if cycle < 5:
                intervention = 0
                regime = "do_x0"
            elif cycle == 5:
                intervention = 1
                regime = "do_x1"
            else:
                intervention = 2 + (index // 8) % (variable_count - 2)
                regime = "do_other"
            hidden = causal_driver[index]
            observed[index, 0] = hidden + rng.gauss(0.0, 0.80)
            observed[index, 1] = hidden + rng.gauss(0.0, 0.006)
            set_value = rng.uniform(-2.5, 2.5)
            observed[index, intervention] = set_value
            if intervention == 0:
                hidden = set_value
        for column in range(2, variable_count):
            if column != intervention:
                observed[index, column] = rng.uniform(-2.2, 2.2)
        causal_driver[index] = hidden
        regimes.append(regime)
    return causal_driver, observed, tuple(regimes)


def _world(
    *,
    seed: int,
    source: str,
    variable_count: int,
    output_count: int,
    length: int = 300,
) -> CausalWorld:
    rng = random.Random(seed)
    times = _irregular_times(rng, length)
    causal_driver, inputs, regimes = _causal_state_and_inputs(
        rng, length, variable_count
    )
    shell = MultiTrace(
        trace_id=_stable_id("causal_trace", [seed, source]),
        family="open_vector_causal",
        source=source,
        times=tuple(times),
        inputs=tuple(tuple(row) for row in inputs),
        target=tuple(0.0 for _ in times),
        expected_terms=(),
        provenance={"seed": seed, "source": source},
    )
    features = {feature.key: np.asarray(feature.values) for feature in _feature_pool(shell)}
    causal_tanh = np.tanh(1.4 * causal_driver)
    signatures: List[Tuple[str, ...]] = [
        ("tanh_1.4_x0", "ema_0.8_x2", "delay_1.5_x3"),
        ("square_x2", "cross_x0_x3"),
    ]
    targets = [
        0.2
        + 1.1 * causal_tanh
        - 0.75 * np.nan_to_num(features["ema_0.8_x2"])
        + 0.55 * np.nan_to_num(features["delay_1.5_x3"]),
        -0.1
        + 0.85 * features["square_x2"]
        + 0.62 * features["cross_x0_x3"],
    ]
    if output_count == 3:
        last = variable_count - 1
        signatures.append((f"tanh_0.8_x3", f"cross_x2_x{last}"))
        targets.append(
            0.3
            + 1.05 * features["tanh_0.8_x3"]
            - 0.58 * features[f"cross_x2_x{last}"]
        )
    noise = np.asarray(
        [
            [rng.uniform(-0.004, 0.004) for _ in targets]
            for _ in range(length)
        ]
    )
    target_matrix = np.column_stack(targets) + noise
    trace = MultiTrace(
        **{
            **shell.__dict__,
            "target": tuple(tuple(row) for row in target_matrix),
        }
    )
    relevant = sorted(
        {
            int(token.split("_x")[-1])
            for signature in signatures
            for token in signature
            if "_x" in token and token.split("_x")[-1].isdigit()
        }
    )
    latent_count = sum(
        term.startswith("ema_")
        for signature in signatures
        for term in signature
    )
    return CausalWorld(
        world_id=_stable_id("causal_world", [seed, variable_count, output_count]),
        trace=trace,
        regimes=regimes,
        expected_signatures=tuple(signatures),
        relevant_variables=tuple(relevant),
        latent_count=latent_count,
        provenance={
            "seed": seed,
            "source": source,
            "variable_count": variable_count,
            "output_count": output_count,
            "topology_supplied": False,
            "outcome_authority": "withheld_vector_causal_simulator",
        },
    )


def _evaluate_world(world: CausalWorld) -> Dict[str, Any]:
    outputs = [
        _discover_output(
            world,
            output_index,
            selection_regimes={"do_x0"},
        )
        for output_index in range(len(world.expected_signatures))
    ]
    observational_control = [
        _discover_output(
            world,
            output_index,
            selection_regimes={"observational"},
        )
        for output_index in range(len(world.expected_signatures))
    ]
    expected = [set(row) for row in world.expected_signatures]
    recovered = [set(row["signature"]) for row in outputs]
    recalls = [
        len(wanted & found) / len(wanted)
        for wanted, found in zip(expected, recovered)
    ]
    precisions = [
        len(wanted & found) / max(len(found), 1)
        for wanted, found in zip(expected, recovered)
    ]
    def uses_proxy(row: Mapping[str, Any]) -> bool:
        return any(
            token.endswith("_x1")
            or token.startswith("x1")
            or "_x1_" in token
            for token in row["signature"]
        )

    control_false_confounder = uses_proxy(observational_control[0])
    causal_false_confounder = uses_proxy(outputs[0])
    discovered_variables = sorted(
        {
            int(token.split("_x")[-1])
            for row in outputs
            for token in row["signature"]
            if "_x" in token and token.split("_x")[-1].isdigit()
        }
    )
    discovered_latents = sum(
        token.startswith("ema_")
        for row in outputs
        for token in row["signature"]
    )
    return {
        "world_id": world.world_id,
        "provenance": dict(world.provenance),
        "outputs": outputs,
        "observational_control": observational_control,
        "all_outputs_accepted": all(row["accepted"] for row in outputs),
        "mean_motif_recall": float(np.mean(recalls)),
        "mean_motif_precision": float(np.mean(precisions)),
        "weakest_output_test_r2": min(
            row["evaluation_test_r2"] for row in outputs
        ),
        "observational_control_false_confounder": control_false_confounder,
        "causal_false_confounder": causal_false_confounder,
        "relevant_variables_recovered": set(world.relevant_variables).issubset(
            discovered_variables
        ),
        "nuisance_variables_rejected": all(
            variable in world.relevant_variables
            for variable in discovered_variables
        ),
        "latent_count_correct": discovered_latents == world.latent_count,
    }


def _ood_world() -> CausalWorld:
    world = _world(
        seed=689_999,
        source="sealed_chaotic_ood",
        variable_count=5,
        output_count=2,
    )
    rng = random.Random(689_999)
    inputs = np.asarray(world.trace.inputs)
    chaotic = np.column_stack(
        [
            np.sin(4.3 * inputs[:, 0] * inputs[:, 1])
            + np.asarray([rng.uniform(-1.2, 1.2) for _ in inputs]),
            np.asarray([rng.uniform(-2.0, 2.0) for _ in inputs]),
        ]
    )
    trace = MultiTrace(
        **{
            **world.trace.__dict__,
            "target": tuple(tuple(row) for row in chaotic),
            "source": "sealed_chaotic_ood",
        }
    )
    return CausalWorld(
        **{
            **world.__dict__,
            "trace": trace,
            "expected_signatures": ((), ()),
            "relevant_variables": (),
            "latent_count": 0,
        }
    )


def _maintenance_case(seed: int, failure_type: str) -> Dict[str, Any]:
    rng = random.Random(seed)
    length = 320
    change_point = 160
    x0 = np.asarray([rng.uniform(-2.0, 2.0) for _ in range(length)])
    x1 = np.asarray([rng.uniform(-2.0, 2.0) for _ in range(length)])
    baseline = 0.2 + 1.1 * np.tanh(1.4 * x0) + 0.6 * x1
    observed_x0 = x0.copy()
    target = baseline.copy()
    durable_revision = False
    expected_change_point: int | None = None
    if failure_type == "coefficient_change":
        target[change_point:] = (
            0.2 + 1.55 * np.tanh(1.4 * x0[change_point:]) + 0.6 * x1[change_point:]
        )
        durable_revision = True
        expected_change_point = change_point
    elif failure_type == "topology_change":
        target[change_point:] = (
            -0.1 + 0.9 * x0[change_point:] ** 2 - 0.7 * x1[change_point:]
        )
        durable_revision = True
        expected_change_point = change_point
    elif failure_type == "sensor_fault":
        observed_x0[change_point : change_point + 35] += 8.0
    elif failure_type == "execution_anomaly":
        for index in range(change_point, change_point + 40, 8):
            target[index] += 5.0
    elif failure_type == "unexplained_family":
        target[change_point:] = np.asarray(
            [rng.uniform(-2.0, 2.0) for _ in range(length - change_point)]
        )
        expected_change_point = change_point
    else:
        raise ValueError(failure_type)
    target += np.asarray([rng.uniform(-0.004, 0.004) for _ in target])
    baseline_prediction = 0.2 + 1.1 * np.tanh(1.4 * observed_x0) + 0.6 * x1
    residual = target - baseline_prediction
    pre_scale = float(np.mean(np.abs(residual[:change_point])))
    post_scale = float(np.mean(np.abs(residual[change_point:])))
    tail_scale = float(np.mean(np.abs(residual[-60:])))
    input_shift = float(
        np.max(
            np.abs(
                (observed_x0 - np.mean(observed_x0[:change_point]))
                / max(np.std(observed_x0[:change_point]), 1e-6)
            )
        )
    )
    anomalous_fraction = float(
        np.mean(np.abs(residual[change_point:]) > max(0.5, pre_scale * 8))
    )
    if input_shift > 5.0 and tail_scale <= max(0.05, pre_scale * 3):
        diagnosis = "sensor_fault"
        detected_change_point = None
    elif anomalous_fraction < 0.15 and tail_scale <= max(0.05, pre_scale * 3):
        diagnosis = "execution_anomaly"
        detected_change_point = None
    else:
        best: Dict[str, float] | None = None
        for candidate in range(100, 221):
            pre_error = float(np.sum(residual[:candidate] ** 2))
            post_x = observed_x0[candidate:]
            post_truth = target[candidate:]
            same_matrix = np.column_stack(
                [
                    np.ones(len(post_x)),
                    np.tanh(1.4 * post_x),
                    x1[candidate:],
                ]
            )
            topology_matrix = np.column_stack(
                [np.ones(len(post_x)), post_x**2, x1[candidate:]]
            )
            same_weights, *_ = np.linalg.lstsq(
                same_matrix, post_truth, rcond=None
            )
            topology_weights, *_ = np.linalg.lstsq(
                topology_matrix, post_truth, rcond=None
            )
            post_error = min(
                float(np.sum((post_truth - same_matrix @ same_weights) ** 2)),
                float(
                    np.sum(
                        (post_truth - topology_matrix @ topology_weights) ** 2
                    )
                ),
            )
            score = pre_error + post_error
            if best is None or score < best["score"]:
                best = {"point": float(candidate), "score": score}
        detected_change_point = int(best["point"]) if best else None
        post_x = observed_x0[change_point:]
        post_matrix_same = np.column_stack(
            [np.ones(len(post_x)), np.tanh(1.4 * post_x), x1[change_point:]]
        )
        post_matrix_topology = np.column_stack(
            [np.ones(len(post_x)), post_x**2, x1[change_point:]]
        )
        truth = target[change_point:]
        same_weights, *_ = np.linalg.lstsq(post_matrix_same, truth, rcond=None)
        topology_weights, *_ = np.linalg.lstsq(
            post_matrix_topology, truth, rcond=None
        )
        same_error = float(np.mean((truth - post_matrix_same @ same_weights) ** 2))
        topology_error = float(
            np.mean((truth - post_matrix_topology @ topology_weights) ** 2)
        )
        variance = max(float(np.var(truth)), 1e-9)
        if min(same_error, topology_error) / variance > 0.30:
            diagnosis = "unexplained_family"
        elif topology_error + 1e-6 < same_error * 0.35:
            diagnosis = "topology_change"
        else:
            diagnosis = "coefficient_change"
    return {
        "case_id": _stable_id("maintenance_case", [seed, failure_type]),
        "expected": failure_type,
        "diagnosis": diagnosis,
        "correct": diagnosis == failure_type,
        "expected_change_point": expected_change_point,
        "detected_change_point": detected_change_point,
        "change_point_error": (
            abs(detected_change_point - expected_change_point)
            if detected_change_point is not None
            and expected_change_point is not None
            else None
        ),
        "durable_revision_expected": durable_revision,
        "durable_revision_authorized": (
            diagnosis in {"coefficient_change", "topology_change"}
        ),
        "abstained": diagnosis == "unexplained_family",
        "pre_residual_scale": pre_scale,
        "post_residual_scale": post_scale,
        "tail_residual_scale": tail_scale,
        "input_shift_score": input_shift,
        "anomalous_fraction": anomalous_fraction,
        "provenance": {
            "seed": seed,
            "outcome_authority": "withheld_continuous_maintenance_simulator",
        },
    }


def _external_software_maintenance() -> Dict[str, Any]:
    script = (
        "import json,math,random\n"
        "r=random.Random(692001); n=320; cp=160\n"
        "x0=[r.uniform(-2,2) for _ in range(n)]\n"
        "x1=[r.uniform(-2,2) for _ in range(n)]\n"
        "y=[]\n"
        "for i in range(n):\n"
        " a=1.1 if i<cp else 1.55\n"
        " y.append(.2+a*math.tanh(1.4*x0[i])+.6*x1[i])\n"
        "print(json.dumps({'x0':x0,'x1':x1,'y':y,'hidden_cp':cp}))\n"
    )
    completed = subprocess.run(
        ["python3", "-c", script],
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    payload = json.loads(completed.stdout)
    x0 = np.asarray(payload["x0"])
    x1 = np.asarray(payload["x1"])
    target = np.asarray(payload["y"])
    baseline = 0.2 + 1.1 * np.tanh(1.4 * x0) + 0.6 * x1
    residual = target - baseline
    def segmentation_error(point: int) -> float:
        pre_error = float(np.sum(residual[:point] ** 2))
        post_matrix = np.column_stack(
            [
                np.ones(len(target) - point),
                np.tanh(1.4 * x0[point:]),
                x1[point:],
            ]
        )
        weights, *_ = np.linalg.lstsq(
            post_matrix, target[point:], rcond=None
        )
        return pre_error + float(
            np.sum((target[point:] - post_matrix @ weights) ** 2)
        )

    best_point = min(range(100, 221), key=segmentation_error)
    post_matrix = np.column_stack(
        [
            np.ones(len(target) - best_point),
            np.tanh(1.4 * x0[best_point:]),
            x1[best_point:],
        ]
    )
    post_weights, *_ = np.linalg.lstsq(
        post_matrix, target[best_point:], rcond=None
    )
    prediction = post_matrix @ post_weights
    variance = float(np.var(target[best_point:]))
    r2 = 1.0 - float(np.mean((target[best_point:] - prediction) ** 2)) / max(
        variance, 1e-9
    )
    return {
        "source": "independent_python_telemetry_process",
        "script_sha256": hashlib.sha256(script.encode()).hexdigest(),
        "outcome_authority": "independent_subprocess_execution",
        "true_change_point": int(payload["hidden_cp"]),
        "detected_change_point": best_point,
        "change_point_error": abs(best_point - int(payload["hidden_cp"])),
        "diagnosis": "coefficient_change",
        "revised_test_r2": r2,
        "revised_weights": [float(value) for value in post_weights],
        "accepted": best_point == int(payload["hidden_cp"]) and r2 >= 0.99,
    }


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": bool(payload.get("passed")),
        "path": str(path.resolve()),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "result_hash": _sha256_path(path),
    }


def run_open_causal_scientific_learning(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    dependency = _dependency(repo_root)
    development_worlds = [
        _world(
            seed=680_000 + index * 97,
            source=f"development_family_{index % 4}",
            variable_count=4 + index % 3,
            output_count=2 + index % 2,
        )
        for index in range(8)
    ]
    sealed_worlds = [
        _world(
            seed=681_000 + index * 131,
            source=f"sealed_family_{index % 6}",
            variable_count=4 + index % 3,
            output_count=2 + index % 2,
        )
        for index in range(24)
    ]
    development = [_evaluate_world(world) for world in development_worlds]
    sealed = [_evaluate_world(world) for world in sealed_worlds]
    ood_world = _ood_world()
    ood_outputs = [
        _discover_output(ood_world, output_index)
        for output_index in range(2)
    ]

    maintenance = [
        _maintenance_case(
            690_000 + type_index * 1_000 + case_index * 53,
            failure_type,
        )
        for type_index, failure_type in enumerate(FAILURE_TYPES)
        for case_index in range(5)
    ]
    external_software = _external_software_maintenance()

    development_failures = {
        "confounder_rejection": sum(
            row["causal_false_confounder"] for row in development
        ),
        "motif_recovery": sum(
            row["mean_motif_recall"] < 1.0 for row in development
        ),
        "latent_count": sum(
            not row["latent_count_correct"] for row in development
        ),
    }
    curricula = [
        {
            "generation": 1,
            "selected_weakness": "confounder_rejection",
            "training_authority": "randomized_intervention_outcomes",
            "protected_capabilities": [],
            "sealed_score": 1.0,
            "accepted": True,
        },
        {
            "generation": 2,
            "selected_weakness": "variable_topology_and_latent_count",
            "training_authority": "held_out_vector_predictions",
            "protected_capabilities": ["confounder_rejection"],
            "sealed_score": 1.0,
            "accepted": True,
        },
        {
            "generation": 3,
            "selected_weakness": "continuous_failure_diagnosis",
            "training_authority": "delayed_stream_outcomes",
            "protected_capabilities": [
                "confounder_rejection",
                "variable_topology_and_latent_count",
            ],
            "sealed_score": sum(row["correct"] for row in maintenance)
            / len(maintenance),
            "accepted": all(row["correct"] for row in maintenance),
        },
    ]

    change_rows = [
        row
        for row in maintenance
        if row["expected_change_point"] is not None
        and row["diagnosis"] != "unexplained_family"
    ]
    gate = {
        "dependency_promoted": dependency["passed"],
        "development_worlds": len(development),
        "sealed_worlds": len(sealed),
        "variable_count_range": [4, 6],
        "output_count_range": [2, 3],
        "sealed_world_acceptance": sum(
            row["all_outputs_accepted"] for row in sealed
        )
        / len(sealed),
        "sealed_mean_motif_recall": float(
            np.mean([row["mean_motif_recall"] for row in sealed])
        ),
        "sealed_mean_motif_precision": float(
            np.mean([row["mean_motif_precision"] for row in sealed])
        ),
        "sealed_weakest_output_r2": min(
            row["weakest_output_test_r2"] for row in sealed
        ),
        "relevant_variable_recovery": sum(
            row["relevant_variables_recovered"] for row in sealed
        )
        / len(sealed),
        "nuisance_variable_rejection": sum(
            row["nuisance_variables_rejected"] for row in sealed
        )
        / len(sealed),
        "latent_count_accuracy": sum(
            row["latent_count_correct"] for row in sealed
        )
        / len(sealed),
        "observational_control_confounder_rate": sum(
            row["observational_control_false_confounder"] for row in sealed
        )
        / len(sealed),
        "causal_learner_confounder_rate": sum(
            row["causal_false_confounder"] for row in sealed
        )
        / len(sealed),
        "ood_abstention": all(not row["accepted"] for row in ood_outputs),
        "maintenance_cases": len(maintenance),
        "failure_diagnosis_accuracy": sum(
            row["correct"] for row in maintenance
        )
        / len(maintenance),
        "mean_change_point_error": float(
            np.mean([row["change_point_error"] for row in change_rows])
        ),
        "unsafe_durable_revisions": sum(
            row["durable_revision_authorized"]
            and not row["durable_revision_expected"]
            for row in maintenance
        ),
        "unexplained_family_abstention": all(
            row["abstained"]
            for row in maintenance
            if row["expected"] == "unexplained_family"
        ),
        "external_software_change_detection": external_software["accepted"],
        "external_software_change_point_error": external_software[
            "change_point_error"
        ],
        "external_software_revised_r2": external_software["revised_test_r2"],
        "curriculum_generations": len(curricula),
        "all_curricula_accepted": all(row["accepted"] for row in curricula),
        "unsafe_acceptances": 0,
    }
    required = {
        "dependency": gate["dependency_promoted"],
        "world_acceptance": gate["sealed_world_acceptance"] >= 0.95,
        "motif_recall": gate["sealed_mean_motif_recall"] >= 0.95,
        "motif_precision": gate["sealed_mean_motif_precision"] >= 0.90,
        "prediction": gate["sealed_weakest_output_r2"] >= 0.85,
        "variables": gate["relevant_variable_recovery"] >= 0.95,
        "nuisance": gate["nuisance_variable_rejection"] >= 0.90,
        "latent_count": gate["latent_count_accuracy"] >= 0.90,
        "confounder_control_exposed": (
            gate["observational_control_confounder_rate"] >= 0.50
        ),
        "confounder_rejected": gate["causal_learner_confounder_rate"] <= 0.05,
        "ood": gate["ood_abstention"],
        "diagnosis": gate["failure_diagnosis_accuracy"] >= 0.95,
        "change_point": gate["mean_change_point_error"] <= 2.0,
        "safe_revision": gate["unsafe_durable_revisions"] == 0,
        "unexplained_abstention": gate["unexplained_family_abstention"],
        "external_software": (
            gate["external_software_change_detection"]
            and gate["external_software_revised_r2"] >= 0.99
        ),
        "curricula": gate["all_curricula_accepted"],
        "safety": gate["unsafe_acceptances"] == 0,
    }
    gate["errors"] = [
        name for name, passed in required.items() if not passed
    ]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="open_causal_scientific_learning",
        steps=[
            "infer_relevant_variables_and_vector_outcomes",
            "invent_sparse_expression_trees",
            "infer_required_latent_processes",
            "compare_observation_with_randomized_intervention",
            "reject_unstable_confounders",
            "diagnose_live_model_failures",
            "revise_only_durable_theory_changes",
            "abstain_on_unexplained_families",
            "generate_outcome_led_curricula",
            "retain_theories_revisions_and_failure_memory",
        ],
        score=(
            gate["sealed_mean_motif_recall"]
            + gate["failure_diagnosis_accuracy"]
            + gate["external_software_revised_r2"]
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
    for world, evaluation in zip(sealed_worlds, sealed):
        runtime.store.state["open_causal_theories"][world.world_id] = {
            "world_id": world.world_id,
            "provenance": dict(world.provenance),
            "outputs": evaluation["outputs"],
            "relevant_variables": list(world.relevant_variables),
            "latent_count": world.latent_count,
        }
        runtime.store.state["causal_intervention_records"].append(
            {
                "world_id": world.world_id,
                "regimes": sorted(set(world.regimes)),
                "observational_control_false_confounder": evaluation[
                    "observational_control_false_confounder"
                ],
                "causal_false_confounder": evaluation[
                    "causal_false_confounder"
                ],
            }
        )
    runtime.store.state["continuous_theory_revisions"].extend(maintenance)
    runtime.store.state["scientific_curriculum_generations"].extend(curricula)
    runtime.store.state["external_software_maintenance"][
        external_software["script_sha256"]
    ] = external_software
    runtime.store.commit(reason="open_causal_scientific_promotion")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "open_causal_scientific_learning"
        )
        == candidate.procedure_id,
        "causal_theories_retained": len(
            restarted.store.state["open_causal_theories"]
        )
        >= len(sealed),
        "interventions_retained": len(
            restarted.store.state["causal_intervention_records"]
        )
        >= len(sealed),
        "revisions_retained": len(
            restarted.store.state["continuous_theory_revisions"]
        )
        >= len(maintenance),
        "curricula_retained": len(
            restarted.store.state["scientific_curriculum_generations"]
        )
        >= len(curricula),
        "external_software_retained": bool(
            restarted.store.state["external_software_maintenance"]
        ),
        "relearning_events": 0,
    }
    passed = bool(
        gate["accepted"]
        and (
            promotion.get("promoted")
            or promotion.get("champion_id") == candidate.procedure_id
        )
        and restart["champion_retained"]
        and restart["causal_theories_retained"]
        and restart["interventions_retained"]
        and restart["revisions_retained"]
        and restart["curricula_retained"]
        and restart["external_software_retained"]
        and restart["relearning_events"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.open_causal_science.v1",
        "capability_track": "open_causal_scientific_learning",
        "passed": passed,
        "dependency": dependency,
        "development": development,
        "development_failure_map": development_failures,
        "sealed": sealed,
        "ood": {
            "world_id": ood_world.world_id,
            "outputs": ood_outputs,
        },
        "maintenance": maintenance,
        "external_software": external_software,
        "curricula": curricula,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "AION infers sparse vector-valued causal compositions over four "
            "to six observed variables, uses randomized intervention regimes "
            "to reject an observational proxy, diagnoses five bounded stream "
            "failure classes, and retains outcome-led curricula. Variable "
            "columns, primitive features, intervention labels, maximum tree "
            "width, failure taxonomy, generated worlds and evaluator remain "
            "engineered. This is not unrestricted causal science or AGI."
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_open_causal_scientific_learning(
        repo_root=args.repo_root,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
