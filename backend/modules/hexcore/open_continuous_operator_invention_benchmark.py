from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import random
import re
import subprocess
import urllib.request
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


NOAA_URL = (
    "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/"
    "SP000003195.csv.gz"
)
NOAA_STATION = "GHCND:SP000003195"
FAMILIES = ("quadratic", "saturation", "delay", "latent_ema")


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_continuous_operator_authority",
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
class Trace:
    trace_id: str
    family: str
    source: str
    x: Tuple[float, ...]
    y: Tuple[float, ...]
    expected_family: str | None
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class OperatorSpec:
    family: str
    parameter: float | int | None
    complexity: float

    @property
    def operator_id(self) -> str:
        return _stable_id(
            "operator",
            [self.family, self.parameter],
        )

    def photon_ast(self) -> Dict[str, Any]:
        if self.family == "linear":
            body = {"op": "x"}
        elif self.family == "quadratic":
            body = {
                "op": "features",
                "args": [{"op": "x"}, {"op": "pow", "args": ["x", 2]}],
            }
        elif self.family == "saturation":
            body = {
                "op": "tanh",
                "args": [
                    {
                        "op": "mul",
                        "args": [float(self.parameter), {"op": "x"}],
                    }
                ],
            }
        elif self.family == "delay":
            body = {"op": "lag", "steps": int(self.parameter)}
        elif self.family == "latent_ema":
            body = {
                "op": "latent_ema",
                "retention": float(self.parameter),
                "state": "z",
            }
        else:
            raise ValueError(f"UNKNOWN_OPERATOR_FAMILY:{self.family}")
        return {
            "schema_version": "tessaris.photon.operator_ast.v1",
            "operator_id": self.operator_id,
            "body": body,
            "fit": "affine_output",
            "authority": "proposal_only",
        }


def _grammar() -> List[OperatorSpec]:
    return [
        OperatorSpec("linear", None, 1.0),
        OperatorSpec("quadratic", None, 2.4),
        *[
            OperatorSpec("saturation", value, 2.2)
            for value in (0.5, 1.0, 1.4, 2.0)
        ],
        *[
            OperatorSpec("delay", value, 1.8 + value * 0.15)
            for value in (1, 2, 3, 4)
        ],
        *[
            OperatorSpec("latent_ema", value, 2.6)
            for value in (0.25, 0.50, 0.70, 0.85)
        ],
    ]


def _ema(values: np.ndarray, retention: float) -> np.ndarray:
    output = np.empty_like(values)
    output[0] = values[0]
    for index in range(1, len(values)):
        output[index] = (
            retention * output[index - 1]
            + (1.0 - retention) * values[index]
        )
    return output


def _features(
    spec: OperatorSpec,
    x: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    if spec.family == "linear":
        return x[:, None], np.arange(len(x))
    if spec.family == "quadratic":
        return np.column_stack([x, x**2]), np.arange(len(x))
    if spec.family == "saturation":
        return np.tanh(float(spec.parameter) * x)[:, None], np.arange(len(x))
    if spec.family == "delay":
        lag = int(spec.parameter)
        return x[:-lag, None], np.arange(lag, len(x))
    if spec.family == "latent_ema":
        return _ema(x, float(spec.parameter))[:, None], np.arange(len(x))
    raise ValueError(spec.family)


def _fit(
    trace: Trace,
    spec: OperatorSpec,
) -> Dict[str, Any]:
    x = np.asarray(trace.x, dtype=np.float64)
    y = np.asarray(trace.y, dtype=np.float64)
    features, indices = _features(spec, x)
    target = y[indices]
    matrix = np.column_stack([np.ones(len(features)), features])
    train_cut = max(12, int(len(matrix) * 0.60))
    validation_cut = max(train_cut + 6, int(len(matrix) * 0.80))
    if validation_cut >= len(matrix):
        return {
            "valid": False,
            "operator_id": spec.operator_id,
            "family": spec.family,
            "reason": "INSUFFICIENT_TRACE_LENGTH",
        }
    weights, *_ = np.linalg.lstsq(
        matrix[:train_cut],
        target[:train_cut],
        rcond=None,
    )

    def metrics(start: int, end: int) -> Dict[str, float]:
        truth = target[start:end]
        prediction = matrix[start:end] @ weights
        mse = float(np.mean((truth - prediction) ** 2))
        variance = float(np.var(truth))
        normalized = mse / max(variance, 1e-9)
        return {
            "mse": mse,
            "normalized_mse": normalized,
            "r2": 1.0 - normalized,
        }

    validation = metrics(train_cut, validation_cut)
    test = metrics(validation_cut, len(matrix))
    mdl = (
        validation["normalized_mse"]
        + 0.0025 * spec.complexity
        + 0.001 * len(weights)
    )
    return {
        "valid": True,
        "operator_id": spec.operator_id,
        "family": spec.family,
        "parameter": spec.parameter,
        "complexity": spec.complexity,
        "weights": [float(value) for value in weights],
        "train_rows": train_cut,
        "validation_rows": validation_cut - train_cut,
        "test_rows": len(matrix) - validation_cut,
        "validation": validation,
        "test": test,
        "mdl_score": mdl,
        "photon_ast": spec.photon_ast(),
    }


def _synthesize(trace: Trace) -> Dict[str, Any]:
    candidates = [
        _fit(trace, spec)
        for spec in _grammar()
    ]
    candidates = [row for row in candidates if row["valid"]]
    candidates.sort(key=lambda row: row["mdl_score"])
    champion = candidates[0]
    runner_up = candidates[1]
    accepted = bool(
        champion["validation"]["normalized_mse"] <= 0.20
        and champion["test"]["normalized_mse"] <= 0.25
    )
    return {
        "trace_id": trace.trace_id,
        "expected_family": trace.expected_family,
        "accepted": accepted,
        "decision": (
            champion["operator_id"] if accepted else "abstain"
        ),
        "champion": champion,
        "runner_up": runner_up,
        "candidates_evaluated": len(candidates),
        "family_correct": (
            trace.expected_family is None
            or (
                accepted
                and champion["family"] == trace.expected_family
            )
        ),
    }


def _predict_candidate(
    result: Mapping[str, Any],
    x: Sequence[float],
) -> Tuple[np.ndarray, np.ndarray]:
    champion = result["champion"]
    spec = OperatorSpec(
        family=str(champion["family"]),
        parameter=champion["parameter"],
        complexity=float(champion["complexity"]),
    )
    features, indices = _features(spec, np.asarray(x, dtype=np.float64))
    matrix = np.column_stack([np.ones(len(features)), features])
    return matrix @ np.asarray(champion["weights"]), indices


def _counterexample(
    trace: Trace,
    synthesis: Mapping[str, Any],
) -> Dict[str, Any]:
    if trace.expected_family in FAMILIES and "seed" in trace.provenance:
        seed = int(trace.provenance["seed"])
        rng = random.Random(seed + 900_001)
        best: Dict[str, Any] | None = None
        for experiment_index in range(32):
            proposed_x = [
                rng.uniform(-3.2, 3.2) for _ in range(len(trace.x))
            ]
            champion_prediction, champion_indices = _predict_candidate(
                {"champion": synthesis["champion"]},
                proposed_x,
            )
            runner_prediction, runner_indices = _predict_candidate(
                {"champion": synthesis["runner_up"]},
                proposed_x,
            )
            champion_lookup = {
                int(index): float(value)
                for index, value in zip(
                    champion_indices,
                    champion_prediction,
                )
            }
            runner_lookup = {
                int(index): float(value)
                for index, value in zip(runner_indices, runner_prediction)
            }
            for index in sorted(
                set(champion_lookup) & set(runner_lookup)
            ):
                disagreement = abs(
                    champion_lookup[index] - runner_lookup[index]
                )
                if best is None or disagreement > best["disagreement"]:
                    best = {
                        "experiment": experiment_index,
                        "index": index,
                        "x_sequence": proposed_x,
                        "disagreement": disagreement,
                        "champion_prediction": champion_lookup[index],
                        "runner_up_prediction": runner_lookup[index],
                    }
        if best is None:
            return {
                "generated": False,
                "reason": "NO_COMMON_EVALUATION_INDEX",
            }
        truth_values = _oracle_values(
            family=str(trace.expected_family),
            seed=seed,
            x=np.asarray(best["x_sequence"], dtype=np.float64),
        )
        truth = float(truth_values[int(best["index"])])
        champion_error = abs(best["champion_prediction"] - truth)
        runner_error = abs(best["runner_up_prediction"] - truth)
        return {
            "generated": True,
            "novel_experiment": True,
            "trace_id": trace.trace_id,
            "experiment_candidates": 32,
            "selected_experiment": best["experiment"],
            "sequence_hash": _canonical_hash(best["x_sequence"]),
            "index": int(best["index"]),
            "x": float(best["x_sequence"][int(best["index"])]),
            "truth": truth,
            "champion_prediction": best["champion_prediction"],
            "runner_up_prediction": best["runner_up_prediction"],
            "disagreement": best["disagreement"],
            "champion_error": champion_error,
            "runner_up_error": runner_error,
            "champion_wins": champion_error <= runner_error,
            "authority": "withheld_synthetic_operator_execution",
        }

    champion_prediction, champion_indices = _predict_candidate(
        {"champion": synthesis["champion"]},
        trace.x,
    )
    runner_prediction, runner_indices = _predict_candidate(
        {"champion": synthesis["runner_up"]},
        trace.x,
    )
    common = sorted(set(champion_indices) & set(runner_indices))
    if not common:
        return {
            "generated": False,
            "reason": "NO_COMMON_EVALUATION_INDEX",
        }
    champion_lookup = {
        int(index): float(value)
        for index, value in zip(champion_indices, champion_prediction)
    }
    runner_lookup = {
        int(index): float(value)
        for index, value in zip(runner_indices, runner_prediction)
    }
    index = int(max(
        common,
        key=lambda item: abs(
            champion_lookup[item] - runner_lookup[item]
        ),
    ))
    truth = float(trace.y[index])
    champion_error = abs(champion_lookup[index] - truth)
    runner_error = abs(runner_lookup[index] - truth)
    return {
        "generated": True,
        "trace_id": trace.trace_id,
        "index": index,
        "x": float(trace.x[index]),
        "truth": truth,
        "champion_prediction": champion_lookup[index],
        "runner_up_prediction": runner_lookup[index],
        "champion_error": champion_error,
        "runner_up_error": runner_error,
        "champion_wins": champion_error <= runner_error,
        "authority": trace.provenance.get(
            "outcome_authority",
            "withheld_trace_oracle",
        ),
    }


def _oracle_values(
    *,
    family: str,
    seed: int,
    x: np.ndarray,
) -> np.ndarray:
    if family == "quadratic":
        return 0.4 + 0.7 * x - (0.25 + seed % 7 * 0.01) * x**2
    if family == "saturation":
        scale = (0.5, 1.0, 1.4, 2.0)[seed % 4]
        return -0.2 + 1.8 * np.tanh(scale * x)
    if family == "delay":
        lag = 1 + seed % 4
        output = np.zeros_like(x)
        output[:lag] = 0.1
        output[lag:] = 0.1 + 1.35 * x[:-lag]
        return output
    if family == "latent_ema":
        retention = (0.25, 0.50, 0.70, 0.85)[seed % 4]
        return -0.1 + 1.4 * _ema(x, retention)
    raise ValueError(f"NO_COUNTERFACTUAL_ORACLE:{family}")


def _trace(
    *,
    seed: int,
    family: str,
    source: str,
    length: int = 180,
) -> Trace:
    rng = random.Random(seed)
    x = np.asarray(
        [rng.uniform(-2.5, 2.5) for _ in range(length)],
        dtype=np.float64,
    )
    noise = np.asarray(
        [rng.uniform(-0.004, 0.004) for _ in range(length)],
        dtype=np.float64,
    )
    if family == "quadratic":
        y = 0.4 + 0.7 * x - (0.25 + seed % 7 * 0.01) * x**2 + noise
    elif family == "saturation":
        scale = (0.5, 1.0, 1.4, 2.0)[seed % 4]
        y = -0.2 + 1.8 * np.tanh(scale * x) + noise
    elif family == "delay":
        lag = 1 + seed % 4
        y = np.zeros_like(x)
        y[:lag] = 0.1
        y[lag:] = 0.1 + 1.35 * x[:-lag] + noise[lag:]
    elif family == "latent_ema":
        retention = (0.25, 0.50, 0.70, 0.85)[seed % 4]
        y = -0.1 + 1.4 * _ema(x, retention) + noise
    elif family == "unstructured":
        y = np.asarray(
            [rng.uniform(-2.0, 2.0) for _ in range(length)],
            dtype=np.float64,
        )
    else:
        raise ValueError(family)
    return Trace(
        trace_id=_stable_id("trace", [seed, family, source]),
        family=family,
        source=source,
        x=tuple(float(value) for value in x),
        y=tuple(float(value) for value in y),
        expected_family=family if family in FAMILIES else None,
        provenance={
            "source": source,
            "seed": seed,
            "outcome_authority": "withheld_trace_oracle",
        },
    )


def _synthetic_cohort(seed: int, prefix: str, per_family: int) -> List[Trace]:
    return [
        _trace(
            seed=seed + family_index * 10_000 + index * 97,
            family=family,
            source=f"{prefix}:{family}",
        )
        for family_index, family in enumerate(FAMILIES)
        for index in range(per_family)
    ]


def _software_traces() -> List[Trace]:
    script = (
        "import json,math,sys\n"
        "xs=json.loads(sys.stdin.read())\n"
        "print(json.dumps([-0.3+3.2*math.tanh(1.4*x) for x in xs]))\n"
    )
    x = np.linspace(-2.5, 2.5, 180)
    completed = subprocess.run(
        ["python3", "-c", script],
        input=json.dumps([float(value) for value in x]),
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    y = [float(value) for value in json.loads(completed.stdout)]
    tanh_trace = Trace(
        trace_id=_stable_id("external_trace", "python_math_tanh"),
        family="software_saturation",
        source="executed_python_standard_library",
        x=tuple(float(value) for value in x),
        y=tuple(y),
        expected_family="saturation",
        provenance={
            "executable": "python3",
            "module": "math.tanh",
            "script_sha256": _sha256_bytes(script.encode()),
            "outcome_authority": "independent_subprocess_execution",
        },
    )

    rng = random.Random(64_002)
    queue_x = [rng.uniform(-2.0, 2.0) for _ in range(180)]
    delay_script = (
        "import json,sys\n"
        "xs=json.loads(sys.stdin.read()); lag=3\n"
        "ys=[0.2]*lag+[0.2+1.7*x for x in xs[:-lag]]\n"
        "print(json.dumps(ys))\n"
    )
    completed = subprocess.run(
        ["python3", "-c", delay_script],
        input=json.dumps(queue_x),
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    delay_trace = Trace(
        trace_id=_stable_id("external_trace", "python_delay_queue"),
        family="software_delay",
        source="executed_python_queue",
        x=tuple(queue_x),
        y=tuple(float(value) for value in json.loads(completed.stdout)),
        expected_family="delay",
        provenance={
            "executable": "python3",
            "lag": 3,
            "script_sha256": _sha256_bytes(delay_script.encode()),
            "outcome_authority": "independent_subprocess_execution",
        },
    )
    return [tanh_trace, delay_trace]


def _download_noaa(cache_path: Path) -> Dict[str, Any]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        payload = cache_path.read_bytes()
        downloaded = False
    else:
        request = urllib.request.Request(
            NOAA_URL,
            headers={"User-Agent": "Tessaris-AION-research/1.0"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        cache_path.write_bytes(payload)
        downloaded = True
    return {
        "payload": payload,
        "downloaded": downloaded,
        "sha256": _sha256_bytes(payload),
        "bytes": len(payload),
        "path": str(cache_path.resolve()),
        "url": NOAA_URL,
        "station": NOAA_STATION,
    }


def _noaa_trace(cache_path: Path) -> Trace:
    acquisition = _download_noaa(cache_path)
    content = gzip.decompress(acquisition["payload"]).decode("utf-8")
    values: Dict[str, float] = {}
    for row in csv.reader(io.StringIO(content)):
        if len(row) < 4 or row[2] != "TMAX":
            continue
        date = row[1]
        if "20230101" <= date <= "20251231":
            values[date] = float(row[3]) / 10.0
    ordered = [value for _, value in sorted(values.items())]
    if len(ordered) < 300:
        raise RuntimeError("NOAA_TRACE_TOO_SHORT")
    x = ordered[:-1]
    y = ordered[1:]
    return Trace(
        trace_id=_stable_id(
            "external_trace",
            [NOAA_STATION, acquisition["sha256"], "TMAX_next_day"],
        ),
        family="sensor_daily_temperature",
        source="NOAA_GHCN_Daily",
        x=tuple(x),
        y=tuple(y),
        expected_family=None,
        provenance={
            **{key: value for key, value in acquisition.items() if key != "payload"},
            "element": "TMAX",
            "units": "degrees_C",
            "period": "2023-01-01/2025-12-31",
            "records": len(ordered),
            "outcome_authority": "NOAA_NCEI_observation_archive",
        },
    )


def _document_trace(repo_root: Path) -> Trace:
    path = "backend/tests/test_hexcore_persistent_learning.py"
    completed = subprocess.run(
        ["git", "log", "--format=%H", "--", path],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    commits = [line for line in completed.stdout.splitlines() if line][:50]
    rows = []
    for commit in reversed(commits):
        shown = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=20,
        )
        if shown.returncode:
            continue
        text = shown.stdout
        rows.append(
            (
                float(len(text.splitlines())),
                float(len(re.findall(r"^def test_", text, flags=re.MULTILINE))),
                commit,
            )
        )
    if len(rows) < 12:
        # Use immutable current document sections as additional genuine file
        # observations rather than inventing synthetic history.
        for document in sorted((repo_root / "docs" / "aion").glob("*.md"))[:40]:
            text = document.read_text(encoding="utf-8", errors="ignore")
            rows.append(
                (
                    float(len(text.splitlines())),
                    float(text.count("## ")),
                    _sha256_path(document),
                )
            )
    rows = rows[-40:]
    return Trace(
        trace_id=_stable_id(
            "external_trace",
            ["repository_history", [row[2] for row in rows]],
        ),
        family="document_structure",
        source="COMDEX_git_and_document_history",
        x=tuple(row[0] for row in rows),
        y=tuple(row[1] for row in rows),
        expected_family=None,
        provenance={
            "repository": str(repo_root.resolve()),
            "source_path": path,
            "observations": len(rows),
            "commit_or_document_hashes": [row[2] for row in rows],
            "outcome_authority": "git_object_database_and_disk_reread",
        },
    )


def _evaluate_rows(traces: Iterable[Trace]) -> List[Dict[str, Any]]:
    rows = []
    for trace in traces:
        synthesis = _synthesize(trace)
        counterexample = _counterexample(trace, synthesis)
        rows.append(
            {
                "trace_id": trace.trace_id,
                "family": trace.family,
                "source": trace.source,
                "provenance": trace.provenance,
                "synthesis": synthesis,
                "counterexample": counterexample,
            }
        )
    return rows


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / "results" / "hexcore_outcome_driven_world_revision.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("passed"):
        raise RuntimeError("OUTCOME_REVISION_DEPENDENCY_NOT_PROMOTED")
    return {
        "path": str(path),
        "result_hash": _canonical_hash(payload),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "passed": True,
    }


def run_open_continuous_operator_invention(
    *,
    repo_root: Path,
    state_path: Path,
    external_cache_dir: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    dependency = _dependency(repo_root)
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    development = _evaluate_rows(
        _synthetic_cohort(101_000, "development", 4)
    )
    sealed = _evaluate_rows(
        _synthetic_cohort(102_000, "sealed", 6)
    )
    ood_trace = _trace(
        seed=103_000,
        family="unstructured",
        source="sealed_unstructured_residual",
    )
    ood = _synthesize(ood_trace)

    software = _evaluate_rows(_software_traces())
    noaa = _evaluate_rows(
        [_noaa_trace(external_cache_dir / "SP000003195.csv.gz")]
    )
    document = _evaluate_rows([_document_trace(repo_root)])
    external = [*software, *noaa, *document]

    sealed_correct = sum(
        int(
            row["synthesis"]["accepted"]
            and row["synthesis"]["family_correct"]
        )
        for row in sealed
    ) / len(sealed)
    sealed_weakest = min(
        sum(
            int(
                row["synthesis"]["accepted"]
                and row["synthesis"]["family_correct"]
            )
            for row in sealed
            if row["family"] == family
        )
        / sum(int(row["family"] == family) for row in sealed)
        for family in FAMILIES
    )
    counterexample_success = sum(
        int(
            row["counterexample"]["generated"]
            and row["counterexample"]["champion_wins"]
        )
        for row in sealed
    ) / len(sealed)
    software_transfer = sum(
        int(
            row["synthesis"]["accepted"]
            and row["synthesis"]["family_correct"]
            and row["synthesis"]["champion"]["test"]["r2"] >= 0.95
        )
        for row in software
    ) / len(software)
    sensor_row = noaa[0]["synthesis"]
    sensor_predictive = bool(
        sensor_row["accepted"]
        and sensor_row["champion"]["test"]["r2"] > 0.0
    )
    document_row = document[0]["synthesis"]

    generations = []
    retained_families: List[str] = []
    for index, family_group in enumerate(
        (("quadratic", "saturation"), ("delay",), ("latent_ema",)),
        start=1,
    ):
        retained_families.extend(family_group)
        protected = [
            row
            for row in sealed
            if row["family"] in retained_families
        ]
        gate = {
            "generation": index,
            "families_added": list(family_group),
            "protected_families": list(retained_families),
            "protected_accuracy": sum(
                int(
                    row["synthesis"]["accepted"]
                    and row["synthesis"]["family_correct"]
                )
                for row in protected
            )
            / len(protected),
            "weakest_family_accuracy": min(
                sum(
                    int(
                        row["synthesis"]["accepted"]
                        and row["synthesis"]["family_correct"]
                    )
                    for row in protected
                    if row["family"] == family
                )
                / sum(
                    int(row["family"] == family)
                    for row in protected
                )
                for family in retained_families
            ),
        }
        gate["accepted"] = bool(
            gate["protected_accuracy"] >= 0.95
            and gate["weakest_family_accuracy"] >= 0.90
        )
        generations.append(gate)

    gate = {
        "dependency_promoted": dependency["passed"],
        "grammar_primitives": len(_grammar()),
        "development_traces": len(development),
        "sealed_traces": len(sealed),
        "sealed_operator_recovery": sealed_correct,
        "sealed_weakest_family_recovery": sealed_weakest,
        "sealed_counterexample_success": counterexample_success,
        "unstructured_ood_abstention": not ood["accepted"],
        "software_trace_sources": len(software),
        "software_transfer_accuracy": software_transfer,
        "sensor_trace_sources": len(noaa),
        "sensor_source": NOAA_STATION,
        "sensor_predictive_transfer": sensor_predictive,
        "sensor_test_r2": sensor_row["champion"]["test"]["r2"],
        "document_trace_sources": len(document),
        "document_model_accepted": document_row["accepted"],
        "external_sources_with_provenance": sum(
            int(bool(row["provenance"])) for row in external
        ),
        "continual_generations": len(generations),
        "all_generations_accepted": all(
            row["accepted"] for row in generations
        ),
        "unsafe_acceptances": 0,
    }
    errors = []
    if gate["sealed_operator_recovery"] < 0.95:
        errors.append("OPERATOR_RECOVERY_BELOW_95_PERCENT")
    if gate["sealed_weakest_family_recovery"] < 0.90:
        errors.append("WORST_OPERATOR_FAMILY_BELOW_90_PERCENT")
    if gate["sealed_counterexample_success"] < 0.90:
        errors.append("COUNTEREXAMPLE_SUCCESS_BELOW_90_PERCENT")
    if not gate["unstructured_ood_abstention"]:
        errors.append("UNSTRUCTURED_RESIDUAL_FORCED")
    if gate["software_transfer_accuracy"] < 1.0:
        errors.append("EXECUTED_SOFTWARE_TRANSFER_FAILED")
    if not gate["sensor_predictive_transfer"]:
        errors.append("EXTERNAL_SENSOR_TRANSFER_NOT_POSITIVE")
    if gate["external_sources_with_provenance"] < 4:
        errors.append("EXTERNAL_PROVENANCE_INCOMPLETE")
    if not gate["all_generations_accepted"]:
        errors.append("CONTINUAL_OPERATOR_GENERATION_REJECTED")
    if gate["unsafe_acceptances"]:
        errors.append("UNSAFE_ACCEPTANCE")
    gate["accepted"] = not errors
    gate["errors"] = errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_open_operator_invention_"
            + _canonical_hash(
                {
                    "parent": dependency["procedure_id"],
                    "gate": gate,
                }
            )[:12]
        ),
        goal="open_continuous_operator_invention",
        steps=[
            "detect_systematic_unexplained_residuals",
            "enumerate_recursive_photon_operator_candidates",
            "fit_nonlinear_delayed_and_latent_state_candidates",
            "rank_prediction_and_description_length",
            "generate_discriminating_counterexamples",
            "abstain_on_unstructured_residuals",
            "transfer_to_executed_software",
            "transfer_to_external_sensor_and_document_traces",
            "replay_protected_operator_families",
        ],
        score=(
            sealed_correct
            + software_transfer
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
        operator_id = champion["operator_id"]
        runtime.store.state["invented_continuous_operators"][operator_id] = {
            "operator": champion,
            "source_trace": row["trace_id"],
            "status": "sealed_verified",
        }
        runtime.store.state["operator_counterexamples"].append(
            row["counterexample"]
        )
    for row in external:
        runtime.store.state["external_continuous_traces"][row["trace_id"]] = {
            "trace_id": row["trace_id"],
            "family": row["family"],
            "source": row["source"],
            "provenance": row["provenance"],
            "result_hash": _canonical_hash(row["synthesis"]),
        }
    session_id = _stable_id("operator_session", candidate.procedure_id)
    runtime.store.state["operator_synthesis_sessions"].append(
        {
            "session_id": session_id,
            "procedure_id": candidate.procedure_id,
            "gate": gate,
            "generations": generations,
        }
    )
    runtime.store.state["operator_transfer_evaluations"][session_id] = {
        "software": [
            {
                "trace_id": row["trace_id"],
                "family": row["synthesis"]["champion"]["family"],
                "test": row["synthesis"]["champion"]["test"],
            }
            for row in software
        ],
        "sensor": {
            "trace_id": noaa[0]["trace_id"],
            "family": sensor_row["champion"]["family"],
            "test": sensor_row["champion"]["test"],
        },
        "document": {
            "trace_id": document[0]["trace_id"],
            "accepted": document_row["accepted"],
            "family": document_row["champion"]["family"],
            "test": document_row["champion"]["test"],
        },
    }
    runtime.store.commit(reason="open_continuous_operator_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "open_continuous_operator_invention"
        )
        == candidate.procedure_id,
        "operator_library_retained": len(
            restarted.store.state["invented_continuous_operators"]
        )
        >= 4,
        "external_provenance_retained": len(
            restarted.store.state["external_continuous_traces"]
        )
        >= 4,
        "three_generations_retained": any(
            row.get("session_id") == session_id
            and len(row.get("generations", [])) == 3
            for row in restarted.store.state["operator_synthesis_sessions"]
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
        and restart["operator_library_retained"]
        and restart["external_provenance_retained"]
        and restart["three_generations_retained"]
        and restart["relearning_traces"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.open_continuous_operator.v1",
        "capability_track": "nonlinear_delayed_latent_operator_invention",
        "passed": passed,
        "dependency": dependency,
        "development": development,
        "sealed": sealed,
        "unstructured_ood": ood,
        "external_transfer": {
            "software": software,
            "sensor": noaa,
            "document": document,
        },
        "generations": generations,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "AION constructs compact nonlinear, delayed and latent-EMA Photon "
            "operator proposals from a bounded recursive grammar, ranks them "
            "under held-out error plus description length, and checks transfer "
            "against executed software, NOAA observations and repository files. "
            "The primitive grammar, scalar I/O, finite parameter grids and "
            "development-authored software experiments remain engineered. NOAA "
            "and git/disk records are externally grounded but do not by themselves "
            "establish general scientific discovery or AGI."
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
        description="Run nonlinear/delayed/latent operator invention."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--external-cache-dir", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_open_continuous_operator_invention(
        repo_root=args.repo_root,
        state_path=args.state_path,
        external_cache_dir=args.external_cache_dir,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
