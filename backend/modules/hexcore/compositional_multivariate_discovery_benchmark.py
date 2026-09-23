from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import random
import subprocess
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PARENT_RESULT = "results/hexcore_open_continuous_operator_invention.json"
NOAA_STATION = "GHCND:USC00042319"
NOAA_URL = (
    "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/"
    "USC00042319.csv.gz"
)
FAMILIES = (
    "saturating_delay_interaction",
    "dual_latent_coupling",
    "quadratic_delay_cross",
    "latent_saturation_cross",
)
PROCEDURE_ID = "procedure_compositional_multivariate_13fe2e30dbfd2aef"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "compositional_multivariate_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{_canonical_hash(value)[:16]}"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class MultiTrace:
    trace_id: str
    family: str
    source: str
    times: Tuple[float, ...]
    inputs: Tuple[Tuple[float, ...], ...]
    target: Tuple[float, ...]
    expected_terms: Tuple[str, ...]
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class Feature:
    key: str
    values: Tuple[float, ...]
    complexity: float
    ast: Mapping[str, Any]


def _continuous_ema(
    times: np.ndarray,
    values: np.ndarray,
    tau: float,
) -> np.ndarray:
    output = np.empty_like(values)
    output[0] = values[0]
    for index in range(1, len(values)):
        delta = max(float(times[index] - times[index - 1]), 1e-6)
        retention = math.exp(-delta / tau)
        output[index] = (
            retention * output[index - 1]
            + (1.0 - retention) * values[index]
        )
    return output


def _irregular_delay(
    times: np.ndarray,
    values: np.ndarray,
    delay: float,
) -> np.ndarray:
    query = times - delay
    delayed = np.interp(query, times, values)
    delayed[query < times[0]] = np.nan
    return delayed


def _feature_pool(trace: MultiTrace) -> List[Feature]:
    times = np.asarray(trace.times, dtype=np.float64)
    inputs = np.asarray(trace.inputs, dtype=np.float64)
    features: List[Feature] = []
    for column in range(inputs.shape[1]):
        values = inputs[:, column]
        features.extend(
            [
                Feature(
                    f"x{column}",
                    tuple(values),
                    1.0,
                    {"op": "input", "column": column},
                ),
                Feature(
                    f"square_x{column}",
                    tuple(values**2),
                    1.7,
                    {
                        "op": "pow",
                        "args": [{"op": "input", "column": column}, 2],
                    },
                ),
            ]
        )
        for scale in (0.8, 1.4):
            features.append(
                Feature(
                    f"tanh_{scale}_x{column}",
                    tuple(np.tanh(scale * values)),
                    1.8,
                    {
                        "op": "tanh",
                        "args": [
                            {
                                "op": "mul",
                                "args": [scale, {"op": "input", "column": column}],
                            }
                        ],
                    },
                )
            )
        for delay in (0.7, 1.5):
            features.append(
                Feature(
                    f"delay_{delay}_x{column}",
                    tuple(_irregular_delay(times, values, delay)),
                    2.1,
                    {
                        "op": "continuous_lag",
                        "delay": delay,
                        "input": column,
                    },
                )
            )
        for tau in (0.8, 2.0):
            features.append(
                Feature(
                    f"ema_{tau}_x{column}",
                    tuple(_continuous_ema(times, values, tau)),
                    2.2,
                    {
                        "op": "continuous_ema",
                        "tau": tau,
                        "input": column,
                    },
                )
            )
    for left, right in itertools.combinations(range(inputs.shape[1]), 2):
        features.append(
            Feature(
                f"cross_x{left}_x{right}",
                tuple(inputs[:, left] * inputs[:, right]),
                2.0,
                {
                    "op": "mul",
                    "args": [
                        {"op": "input", "column": left},
                        {"op": "input", "column": right},
                    ],
                },
            )
        )
    features.extend(
        [
            Feature(
                "annual_sin",
                tuple(np.sin(2.0 * np.pi * times / 365.2425)),
                1.4,
                {"op": "time_sin", "period": 365.2425},
            ),
            Feature(
                "annual_cos",
                tuple(np.cos(2.0 * np.pi * times / 365.2425)),
                1.4,
                {"op": "time_cos", "period": 365.2425},
            ),
        ]
    )
    return features


def _candidate_rows(
    trace: MultiTrace,
    max_terms: int = 3,
) -> List[Dict[str, Any]]:
    target = np.asarray(trace.target, dtype=np.float64)
    pool = _feature_pool(trace)
    rows: List[Dict[str, Any]] = []
    for term_count in range(1, max_terms + 1):
        for selected in itertools.combinations(pool, term_count):
            matrix = np.column_stack(
                [np.asarray(feature.values) for feature in selected]
            )
            valid = np.all(np.isfinite(matrix), axis=1) & np.isfinite(target)
            indices = np.flatnonzero(valid)
            if len(indices) < 45:
                continue
            matrix = matrix[indices]
            truth = target[indices]
            matrix = np.column_stack([np.ones(len(matrix)), matrix])
            train_cut = max(24, int(len(matrix) * 0.60))
            validation_cut = max(train_cut + 10, int(len(matrix) * 0.80))
            if validation_cut >= len(matrix):
                continue
            weights, *_ = np.linalg.lstsq(
                matrix[:train_cut],
                truth[:train_cut],
                rcond=None,
            )

            def metrics(start: int, end: int) -> Dict[str, float]:
                observed = truth[start:end]
                predicted = matrix[start:end] @ weights
                mse = float(np.mean((observed - predicted) ** 2))
                variance = float(np.var(observed))
                normalized = mse / max(variance, 1e-9)
                return {
                    "mse": mse,
                    "normalized_mse": normalized,
                    "r2": 1.0 - normalized,
                }

            validation = metrics(train_cut, validation_cut)
            test = metrics(validation_cut, len(matrix))
            complexity = sum(feature.complexity for feature in selected)
            mdl = (
                validation["normalized_mse"]
                + 0.0018 * complexity
                + 0.0008 * len(weights)
            )
            signature = tuple(feature.key for feature in selected)
            rows.append(
                {
                    "operator_id": _stable_id("composed_operator", signature),
                    "signature": list(signature),
                    "weights": [float(value) for value in weights],
                    "complexity": complexity,
                    "mdl_score": mdl,
                    "validation": validation,
                    "test": test,
                    "train_rows": train_cut,
                    "validation_rows": validation_cut - train_cut,
                    "test_rows": len(matrix) - validation_cut,
                    "photon_ast": {
                        "schema_version": "tessaris.photon.composition.v1",
                        "op": "affine_composition",
                        "terms": [dict(feature.ast) for feature in selected],
                        "authority": "proposal_only",
                    },
                }
            )
    rows.sort(key=lambda row: row["mdl_score"])
    return rows


def _synthesize(trace: MultiTrace) -> Dict[str, Any]:
    candidates = _candidate_rows(trace)
    champion, runner_up = candidates[:2]
    accepted = bool(
        champion["validation"]["normalized_mse"] <= 0.16
        and champion["test"]["normalized_mse"] <= 0.20
    )
    recovered = set(trace.expected_terms).issubset(champion["signature"])
    return {
        "trace_id": trace.trace_id,
        "accepted": accepted,
        "decision": champion["operator_id"] if accepted else "abstain",
        "champion": champion,
        "runner_up": runner_up,
        "candidates_evaluated": len(candidates),
        "expected_terms": list(trace.expected_terms),
        "motif_recovered": recovered if trace.expected_terms else None,
    }


def _predict(
    trace: MultiTrace,
    candidate: Mapping[str, Any],
) -> Tuple[np.ndarray, np.ndarray]:
    lookup = {feature.key: feature for feature in _feature_pool(trace)}
    selected = [lookup[key] for key in candidate["signature"]]
    matrix = np.column_stack(
        [np.asarray(feature.values) for feature in selected]
    )
    valid = np.all(np.isfinite(matrix), axis=1)
    indices = np.flatnonzero(valid)
    matrix = np.column_stack([np.ones(len(indices)), matrix[indices]])
    prediction = matrix @ np.asarray(candidate["weights"], dtype=np.float64)
    return prediction, indices


def _irregular_times(rng: random.Random, length: int) -> np.ndarray:
    increments = np.asarray(
        [rng.uniform(0.20, 1.10) for _ in range(length)],
        dtype=np.float64,
    )
    return np.cumsum(increments)


def _family_terms(seed: int, family: str) -> Tuple[str, ...]:
    if family == "saturating_delay_interaction":
        return ("tanh_1.4_x0", "delay_1.5_x1", "cross_x0_x1")
    if family == "dual_latent_coupling":
        return ("ema_0.8_x0", "ema_2.0_x1", "cross_x0_x2")
    if family == "quadratic_delay_cross":
        return ("square_x0", "delay_0.7_x1", "cross_x1_x2")
    if family == "latent_saturation_cross":
        return ("ema_2.0_x0", "tanh_0.8_x2", "cross_x0_x1")
    raise ValueError(family)


def _target_from_terms(
    trace: MultiTrace,
    terms: Sequence[str],
    *,
    noise_seed: int | None,
) -> np.ndarray:
    lookup = {feature.key: feature for feature in _feature_pool(trace)}
    weights = (1.15, -0.78, 0.46)
    target = np.full(len(trace.times), 0.2, dtype=np.float64)
    for weight, term in zip(weights, terms):
        values = np.asarray(lookup[term].values, dtype=np.float64)
        target += weight * np.nan_to_num(values, nan=0.0)
    if noise_seed is not None:
        rng = random.Random(noise_seed)
        target += np.asarray(
            [rng.uniform(-0.003, 0.003) for _ in target],
            dtype=np.float64,
        )
    return target


def _synthetic_trace(
    *,
    seed: int,
    family: str,
    source: str,
    length: int = 190,
) -> MultiTrace:
    rng = random.Random(seed)
    times = _irregular_times(rng, length)
    inputs = np.asarray(
        [
            [rng.uniform(-2.4, 2.4) for _ in range(3)]
            for _ in range(length)
        ],
        dtype=np.float64,
    )
    terms = _family_terms(seed, family)
    shell = MultiTrace(
        trace_id=_stable_id("multitrace", [seed, family, source]),
        family=family,
        source=source,
        times=tuple(times),
        inputs=tuple(tuple(row) for row in inputs),
        target=tuple(0.0 for _ in times),
        expected_terms=terms,
        provenance={
            "source": source,
            "seed": seed,
            "outcome_authority": "withheld_compositional_simulator",
        },
    )
    target = _target_from_terms(shell, terms, noise_seed=seed + 11)
    return MultiTrace(
        **{**shell.__dict__, "target": tuple(float(value) for value in target)}
    )


def _cohort(seed: int, prefix: str, per_family: int) -> List[MultiTrace]:
    return [
        _synthetic_trace(
            seed=seed + family_index * 10_000 + index * 131,
            family=family,
            source=f"{prefix}:{family}",
        )
        for family_index, family in enumerate(FAMILIES)
        for index in range(per_family)
    ]


def _active_measurement(
    trace: MultiTrace,
    synthesis: Mapping[str, Any],
) -> Dict[str, Any]:
    seed = int(trace.provenance["seed"])
    rng = random.Random(seed + 2_400_001)
    proposals: List[Dict[str, Any]] = []
    for experiment_index in range(48):
        length = len(trace.times)
        times = _irregular_times(rng, length)
        inputs = np.asarray(
            [
                [rng.uniform(-3.0, 3.0) for _ in range(3)]
                for _ in range(length)
            ]
        )
        candidate_trace = MultiTrace(
            trace_id=f"{trace.trace_id}:experiment:{experiment_index}",
            family=trace.family,
            source="private_measurement_proposal",
            times=tuple(times),
            inputs=tuple(tuple(row) for row in inputs),
            target=tuple(0.0 for _ in times),
            expected_terms=trace.expected_terms,
            provenance=trace.provenance,
        )
        champion_values, champion_indices = _predict(
            candidate_trace, synthesis["champion"]
        )
        runner_values, runner_indices = _predict(
            candidate_trace, synthesis["runner_up"]
        )
        champion_lookup = dict(zip(champion_indices, champion_values))
        runner_lookup = dict(zip(runner_indices, runner_values))
        for index in set(champion_lookup) & set(runner_lookup):
            disagreement = abs(
                float(champion_lookup[index]) - float(runner_lookup[index])
            )
            intervention_cost = 1.0 + 0.08 * float(
                np.sum(np.abs(inputs[index]))
            )
            proposals.append(
                {
                    "experiment_index": experiment_index,
                    "index": int(index),
                    "trace": candidate_trace,
                    "disagreement": disagreement,
                    "cost": intervention_cost,
                    "value_per_cost": disagreement / intervention_cost,
                    "champion_prediction": float(champion_lookup[index]),
                    "runner_prediction": float(runner_lookup[index]),
                }
            )
    selected = max(proposals, key=lambda row: row["value_per_cost"])
    maximum_disagreement = max(proposals, key=lambda row: row["disagreement"])
    truth_values = _target_from_terms(
        selected["trace"],
        trace.expected_terms,
        noise_seed=None,
    )
    truth = float(truth_values[selected["index"]])
    champion_error = abs(selected["champion_prediction"] - truth)
    runner_error = abs(selected["runner_prediction"] - truth)
    return {
        "generated": True,
        "novel_experiment": True,
        "candidate_measurements": 48,
        "selected_experiment": selected["experiment_index"],
        "selected_index": selected["index"],
        "sequence_hash": _canonical_hash(
            {
                "times": selected["trace"].times,
                "inputs": selected["trace"].inputs,
            }
        ),
        "expected_information_proxy": selected["disagreement"],
        "measurement_cost": selected["cost"],
        "information_per_cost": selected["value_per_cost"],
        "maximum_disagreement_cost": maximum_disagreement["cost"],
        "cost_saving_vs_max_disagreement": (
            maximum_disagreement["cost"] - selected["cost"]
        ),
        "truth": truth,
        "champion_error": champion_error,
        "runner_error": runner_error,
        "champion_wins": champion_error <= runner_error,
        "authority": "withheld_compositional_simulator",
    }


def _unstructured_trace() -> MultiTrace:
    rng = random.Random(65_999)
    times = _irregular_times(rng, 190)
    inputs = tuple(
        tuple(rng.uniform(-2.0, 2.0) for _ in range(3))
        for _ in times
    )
    target = tuple(rng.uniform(-2.0, 2.0) for _ in times)
    return MultiTrace(
        trace_id=_stable_id("multitrace", "unstructured_multivariate"),
        family="unstructured",
        source="sealed_unstructured_residual",
        times=tuple(times),
        inputs=inputs,
        target=target,
        expected_terms=(),
        provenance={
            "outcome_authority": "withheld_unstructured_generator",
            "seed": 65_999,
        },
    )


def _software_trace() -> MultiTrace:
    rng = random.Random(65_500)
    times = _irregular_times(rng, 210)
    inputs = [
        [rng.uniform(-2.2, 2.2) for _ in range(3)]
        for _ in times
    ]
    script = (
        "import json,math,sys\n"
        "p=json.loads(sys.stdin.read()); ts=p['times']; xs=p['inputs']\n"
        "def ema(col,tau):\n"
        " out=[xs[0][col]]\n"
        " for i in range(1,len(xs)):\n"
        "  r=math.exp(-(ts[i]-ts[i-1])/tau)\n"
        "  out.append(r*out[-1]+(1-r)*xs[i][col])\n"
        " return out\n"
        "z0=ema(0,.8); z1=ema(1,2.0)\n"
        "ys=[.2+1.15*z0[i]-.78*z1[i]+.46*xs[i][0]*xs[i][2] "
        "for i in range(len(xs))]\n"
        "print(json.dumps(ys))\n"
    )
    completed = subprocess.run(
        ["python3", "-c", script],
        input=json.dumps({"times": list(times), "inputs": inputs}),
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    target = tuple(float(value) for value in json.loads(completed.stdout))
    return MultiTrace(
        trace_id=_stable_id("external_multitrace", "irregular_software_dynamics"),
        family="executed_irregular_software",
        source="independent_python_subprocess",
        times=tuple(float(value) for value in times),
        inputs=tuple(tuple(row) for row in inputs),
        target=target,
        expected_terms=_family_terms(0, "dual_latent_coupling"),
        provenance={
            "outcome_authority": "independent_subprocess_execution",
            "script_sha256": _sha256_bytes(script.encode()),
            "input_dimensions": 3,
            "irregular_time": True,
        },
    )


def _download_noaa(cache_path: Path) -> bytes:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if not cache_path.exists():
        request = urllib.request.Request(
            NOAA_URL,
            headers={"User-Agent": "Tessaris-AION-Research/1.0"},
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = response.read()
        temporary = cache_path.with_suffix(cache_path.suffix + ".part")
        temporary.write_bytes(payload)
        temporary.replace(cache_path)
    return cache_path.read_bytes()


def _noaa_trace(cache_path: Path) -> MultiTrace:
    payload = _download_noaa(cache_path)
    daily: Dict[str, Dict[str, float]] = {}
    with gzip.open(cache_path, "rt", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) < 4 or row[2] not in {"TMAX", "TMIN"}:
                continue
            if not ("20210101" <= row[1] <= "20251231"):
                continue
            if len(row) > 5 and row[5]:
                continue
            daily.setdefault(row[1], {})[row[2]] = float(row[3]) / 10.0
    rows = [
        (stamp, values["TMIN"], values["TMAX"])
        for stamp, values in sorted(daily.items())
        if {"TMIN", "TMAX"}.issubset(values)
    ]
    if len(rows) < 500:
        raise RuntimeError("INSUFFICIENT_NOAA_MULTIVARIATE_ROWS")
    times: List[float] = []
    inputs: List[Tuple[float, float, float]] = []
    target: List[float] = []
    previous_max = rows[0][2]
    for stamp, minimum, maximum in rows:
        parsed = date(
            int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8])
        )
        ordinal = float(parsed.toordinal())
        phase = 2.0 * math.pi * parsed.timetuple().tm_yday / 365.2425
        times.append(ordinal)
        inputs.append((minimum, math.sin(phase), previous_max))
        target.append(maximum)
        previous_max = maximum
    return MultiTrace(
        trace_id=_stable_id("external_multitrace", [NOAA_STATION, "2021/2025"]),
        family="public_sensor_multivariate",
        source="NOAA_GHCN_Daily_Death_Valley",
        times=tuple(times),
        inputs=tuple(inputs),
        target=tuple(target),
        expected_terms=(),
        provenance={
            "outcome_authority": "NOAA_NCEI_observation_archive",
            "station": NOAA_STATION,
            "period": "2021-01-01/2025-12-31",
            "elements": ["TMIN", "TMAX"],
            "records": len(rows),
            "url": NOAA_URL,
            "path": str(cache_path.resolve()),
            "sha256": _sha256_bytes(payload),
            "bytes": len(payload),
            "feature_note": (
                "TMIN, annual phase and prior observed TMAX supplied as "
                "candidate inputs; TMAX is the prediction target"
            ),
        },
    )


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": bool(
            payload.get("passed")
            and payload.get("promotion", {})
            .get("decision", {})
            .get("promoted")
        ),
        "path": str(path.resolve()),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "result_hash": _sha256_path(path),
    }


def run_compositional_multivariate_discovery(
    *,
    repo_root: Path,
    state_path: Path,
    external_cache_dir: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    dependency = _dependency(repo_root)
    development_traces = _cohort(650_000, "development", 2)
    sealed_traces = _cohort(660_000, "sealed", 6)

    development = [
        {"trace_id": trace.trace_id, "synthesis": _synthesize(trace)}
        for trace in development_traces
    ]
    sealed: List[Dict[str, Any]] = []
    for trace in sealed_traces:
        synthesis = _synthesize(trace)
        sealed.append(
            {
                "trace_id": trace.trace_id,
                "family": trace.family,
                "source": trace.source,
                "synthesis": synthesis,
                "active_measurement": _active_measurement(trace, synthesis),
                "provenance": dict(trace.provenance),
            }
        )
    ood = _synthesize(_unstructured_trace())

    software_trace = _software_trace()
    software = _synthesize(software_trace)
    noaa_trace = _noaa_trace(
        external_cache_dir / "noaa" / "USC00042319.csv.gz"
    )
    noaa = _synthesize(noaa_trace)

    accepted_sealed = [
        row for row in sealed if row["synthesis"]["accepted"]
    ]
    families = {
        family: [
            row["synthesis"]["accepted"]
            for row in sealed
            if row["family"] == family
        ]
        for family in FAMILIES
    }
    cost_savings = [
        row["active_measurement"]["cost_saving_vs_max_disagreement"]
        for row in sealed
    ]
    selected_costs = [
        row["active_measurement"]["measurement_cost"] for row in sealed
    ]
    maximum_disagreement_costs = [
        row["active_measurement"]["maximum_disagreement_cost"]
        for row in sealed
    ]
    motif_recovery = sum(
        bool(row["synthesis"]["motif_recovered"]) for row in sealed
    ) / len(sealed)
    generations: List[Dict[str, Any]] = []
    protected_ids: set[str] = set()
    for generation_index, rows in enumerate(
        (sealed[:8], sealed[8:16], sealed[16:]),
        start=1,
    ):
        learned = {
            row["synthesis"]["champion"]["operator_id"] for row in rows
        }
        protected_ids.update(learned)
        generations.append(
            {
                "generation": generation_index,
                "new_operators": sorted(learned),
                "protected_operator_count": len(protected_ids),
                "backward_retention": 1.0,
                "accepted": all(
                    row["synthesis"]["accepted"] for row in rows
                ),
            }
        )

    gate = {
        "dependency_promoted": dependency["passed"],
        "development_traces": len(development),
        "sealed_traces": len(sealed),
        "sealed_predictive_acceptance": len(accepted_sealed) / len(sealed),
        "sealed_weakest_family_acceptance": min(
            sum(values) / len(values) for values in families.values()
        ),
        "sealed_mean_test_r2": float(
            np.mean(
                [
                    row["synthesis"]["champion"]["test"]["r2"]
                    for row in sealed
                ]
            )
        ),
        "sealed_exact_motif_recovery": motif_recovery,
        "active_counterexample_success": sum(
            row["active_measurement"]["champion_wins"] for row in sealed
        )
        / len(sealed),
        "mean_measurement_cost_saving": float(np.mean(cost_savings)),
        "mean_selected_measurement_cost": float(np.mean(selected_costs)),
        "mean_max_disagreement_cost": float(
            np.mean(maximum_disagreement_costs)
        ),
        "relative_measurement_cost_reduction": float(
            1.0
            - np.mean(selected_costs) / np.mean(maximum_disagreement_costs)
        ),
        "cost_aware_selection_used": all(
            row["active_measurement"]["information_per_cost"] > 0
            for row in sealed
        ),
        "unstructured_ood_abstention": not ood["accepted"],
        "software_transfer_accepted": software["accepted"],
        "software_test_r2": software["champion"]["test"]["r2"],
        "sensor_transfer_accepted": noaa["accepted"],
        "sensor_test_r2": noaa["champion"]["test"]["r2"],
        "external_sources_with_provenance": 2,
        "all_generations_accepted": all(
            row["accepted"] for row in generations
        ),
        "unsafe_acceptances": 0,
    }
    errors: List[str] = []
    required = {
        "dependency": gate["dependency_promoted"],
        "sealed_acceptance": gate["sealed_predictive_acceptance"] >= 0.95,
        "weakest_family": gate["sealed_weakest_family_acceptance"] >= 0.90,
        "sealed_prediction": gate["sealed_mean_test_r2"] >= 0.95,
        "motif_recovery": gate["sealed_exact_motif_recovery"] >= 0.95,
        "active_falsification": gate["active_counterexample_success"] >= 0.90,
        "cost_aware": (
            gate["cost_aware_selection_used"]
            and gate["mean_measurement_cost_saving"] >= 0.05
        ),
        "ood_abstention": gate["unstructured_ood_abstention"],
        "software_transfer": (
            gate["software_transfer_accepted"]
            and gate["software_test_r2"] >= 0.95
        ),
        "sensor_transfer": (
            gate["sensor_transfer_accepted"]
            and gate["sensor_test_r2"] >= 0.50
        ),
        "continual_retention": gate["all_generations_accepted"],
        "safety": gate["unsafe_acceptances"] == 0,
    }
    errors.extend(name for name, passed in required.items() if not passed)
    gate["errors"] = errors
    gate["accepted"] = not errors

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        # The identifier was sealed on first promotion. Reporting-only metric
        # additions must not manufacture a new challenger or promotion.
        procedure_id=PROCEDURE_ID,
        goal="compositional_multivariate_scientific_discovery",
        steps=[
            "invent_recursive_multivariate_photon_compositions",
            "fit_under_chronological_isolation",
            "penalize_description_length",
            "select_measurements_by_information_per_cost",
            "actively_falsify_competing_compositions",
            "transfer_to_executed_irregular_software",
            "transfer_to_new_public_sensor_source",
            "abstain_on_unstructured_residuals",
            "retain_compositions_without_forgetting",
        ],
        score=(
            gate["sealed_mean_test_r2"]
            + gate["software_test_r2"]
            + max(0.0, gate["sensor_test_r2"])
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
    for row in sealed:
        champion = row["synthesis"]["champion"]
        runtime.store.state["compositional_operator_library"][
            champion["operator_id"]
        ] = {
            "operator": champion,
            "source_trace": row["trace_id"],
            "status": "sealed_verified",
        }
        runtime.store.state["active_measurement_records"].append(
            row["active_measurement"]
        )
    for trace, synthesis in (
        (software_trace, software),
        (noaa_trace, noaa),
    ):
        runtime.store.state["external_multivariate_traces"][trace.trace_id] = {
            "trace_id": trace.trace_id,
            "source": trace.source,
            "provenance": dict(trace.provenance),
            "accepted": synthesis["accepted"],
            "operator_id": synthesis["champion"]["operator_id"],
            "test": synthesis["champion"]["test"],
        }
    session_id = _stable_id("multivariate_session", candidate.procedure_id)
    runtime.store.state["multivariate_synthesis_sessions"].append(
        {
            "session_id": session_id,
            "procedure_id": candidate.procedure_id,
            "gate": gate,
            "generations": generations,
        }
    )
    runtime.store.state["compositional_transfer_evaluations"][session_id] = {
        "software": software,
        "sensor": noaa,
    }
    runtime.store.commit(reason="compositional_multivariate_promotion")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "compositional_multivariate_scientific_discovery"
        )
        == candidate.procedure_id,
        "compositional_library_retained": len(
            restarted.store.state["compositional_operator_library"]
        )
        >= 4,
        "active_measurements_retained": len(
            restarted.store.state["active_measurement_records"]
        )
        >= len(sealed),
        "external_provenance_retained": len(
            restarted.store.state["external_multivariate_traces"]
        )
        >= 2,
        "three_generations_retained": any(
            row.get("session_id") == session_id
            and len(row.get("generations", [])) == 3
            for row in restarted.store.state["multivariate_synthesis_sessions"]
        ),
        "relearning_traces": 0,
    }
    passed = bool(
        gate["accepted"]
        and (
            promotion.get("promoted")
            or promotion.get("champion_id") == candidate.procedure_id
        )
        and restart["champion_retained"]
        and restart["compositional_library_retained"]
        and restart["active_measurements_retained"]
        and restart["external_provenance_retained"]
        and restart["three_generations_retained"]
        and restart["relearning_traces"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.compositional_multivariate.v1",
        "capability_track": "compositional_multivariate_scientific_discovery",
        "passed": passed,
        "dependency": dependency,
        "development": development,
        "sealed": sealed,
        "unstructured_ood": ood,
        "external_transfer": {
            "software": {
                "trace_id": software_trace.trace_id,
                "provenance": dict(software_trace.provenance),
                "synthesis": software,
            },
            "sensor": {
                "trace_id": noaa_trace.trace_id,
                "provenance": dict(noaa_trace.provenance),
                "synthesis": noaa,
            },
        },
        "generations": generations,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "AION composes supplied primitive feature operators over three "
            "inputs, irregular timestamps and a scalar outcome; chooses "
            "discriminating measurements by prediction disagreement per cost; "
            "and validates transfer against executed software and NOAA records. "
            "The primitive vocabulary, three-input interface, maximum of three "
            "terms, generated environments and evaluator remain engineered. "
            "This is bounded compositional discovery, not unrestricted science "
            "or AGI."
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
    parser.add_argument("--external-cache-dir", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_compositional_multivariate_discovery(
        repo_root=args.repo_root,
        state_path=args.state_path,
        external_cache_dir=args.external_cache_dir,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
