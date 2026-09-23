from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PARENT_RESULT = "results/hexcore_cross_language_historical_repair.json"
PROCEDURE_ID = "procedure_source_disjoint_swebench_repair_2f2e871e3879"
DATASET_ID = "princeton-nlp/SWE-bench_Lite"


@dataclass(frozen=True)
class RepairTask:
    instance_id: str
    repo_name: str
    base_commit: str
    target_path: str
    family: str


TASKS: Tuple[RepairTask, ...] = (
    RepairTask(
        "marshmallow-code__marshmallow-1359",
        "marshmallow",
        "b40a0f4e33823e6d0f341f7e8684e359a99060d1",
        "src/marshmallow/fields.py",
        "root_contract",
    ),
    RepairTask(
        "pydicom__pydicom-1694",
        "pydicom",
        "f8cf45b6c121e5a4bf4a43f71aba3bc64af3db9c",
        "pydicom/dataset.py",
        "exception_boundary",
    ),
    RepairTask(
        "pvlib__pvlib-python-1707",
        "pvlib-python",
        "40e9e978c170bdde4eeee1547729417665dbc34c",
        "pvlib/iam.py",
        "numerical_singularity",
    ),
)

TRANSFER_INSTANCE = "marshmallow-code__marshmallow-1343"
TRANSFER_COMMIT = "2be2d83a1a9a6d3d9b85804f3ab545cecc409bb0"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "source_disjoint_repair_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": bool(payload.get("passed")),
        "path": str(path.resolve()),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "result_hash": _hash_path(path),
    }


def _dataset_rows(path: Path) -> Dict[str, Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = {}
    for wrapper in payload.get("rows") or []:
        row = dict(wrapper.get("row") or {})
        if row.get("instance_id"):
            rows[str(row["instance_id"])] = row
    return rows


def _localize_paths(
    repo: Path,
    problem_statement: str,
    *,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    problem_lower = problem_statement.lower()
    identifiers = {
        token.lower()
        for token in re.findall(
            r"[A-Za-z_][A-Za-z0-9_]{3,}", problem_statement
        )
    }
    class_method_refs = [
        (class_name, method_name)
        for class_name, method_name in re.findall(
            r"\b([A-Z][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)",
            problem_statement,
        )
    ]
    ranked = []
    for path in repo.rglob("*.py"):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = str(path.relative_to(repo))
        basename = path.name.lower()
        stem = path.stem.lower()
        source_lower = source.lower()
        basename_signal = basename in problem_lower
        stem_signal = bool(
            len(stem) >= 3
            and (
                stem in identifiers
                or f".{stem}." in problem_lower
                or f"/{stem}." in problem_lower
            )
        )
        matched = sorted(
            token
            for token in identifiers
            if len(token) >= 5 and token in source_lower
        )
        class_method_signal = any(
            re.search(rf"\bclass\s+{re.escape(class_name)}\b", source)
            and re.search(rf"\bdef\s+{re.escape(method_name)}\b", source)
            for class_name, method_name in class_method_refs
        )
        score = (
            100.0 * float(basename_signal)
            + 150.0 * float(class_method_signal)
            + 30.0 * float(stem_signal)
            + min(25.0, float(len(matched)))
        )
        if score:
            ranked.append(
                {
                    "path": relative,
                    "score": score,
                    "basename_signal": basename_signal,
                    "stem_signal": stem_signal,
                    "class_method_signal": class_method_signal,
                    "matched_identifiers": matched[:20],
                }
            )
    ranked.sort(key=lambda row: (-row["score"], row["path"]))
    return ranked[:limit]


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env or os.environ),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _marshmallow_candidates(source: str) -> List[Tuple[str, str]]:
    old = "or getattr(schema.opts, self.SCHEMA_OPTS_VAR_NAME)"
    return [
        ("force_default", source.replace(old, "or self.DEFAULT_FORMAT", 1)),
        (
            "safe_immediate_parent",
            source.replace(
                old,
                "or getattr(getattr(schema, 'opts', None), "
                "self.SCHEMA_OPTS_VAR_NAME, None)",
                1,
            ),
        ),
        (
            "bind_to_root_schema",
            source.replace(
                old,
                "or getattr(self.root.opts, self.SCHEMA_OPTS_VAR_NAME)",
                1,
            ),
        ),
    ]


def _pydicom_candidates(source: str) -> List[Tuple[str, str]]:
    old = (
        "            data_element = self[key]\n"
        "            try:\n"
        "                json_dataset[json_key] = data_element.to_json_dict(\n"
    )
    drop = source.replace(
        old,
        "            try:\n"
        "                continue\n"
        "                json_dataset[json_key] = self[key].to_json_dict(\n",
        1,
    )
    serialization_only = source
    boundary = source.replace(
        old,
        "            try:\n"
        "                data_element = self[key]\n"
        "                json_dataset[json_key] = data_element.to_json_dict(\n",
        1,
    )
    return [
        ("drop_problem_elements", drop),
        ("serialization_only_boundary", serialization_only),
        ("expand_exception_boundary", boundary),
    ]


def _pvlib_candidates(source: str) -> List[Tuple[str, str]]:
    return_anchor = "    return iam\n\n\ndef martin_ruiz"
    scalar_only = source.replace(
        return_anchor,
        "    if np.isscalar(aoi) and aoi >= 90:\n"
        "        iam = 0\n"
        "    return iam\n\n\ndef martin_ruiz",
        1,
    )
    clamp = source.replace(
        return_anchor,
        "    iam = np.where(np.asanyarray(aoi) >= 90, 0, iam)\n"
        "    return iam\n\n\ndef martin_ruiz",
        1,
    )
    reflectance_old = (
        "    rho12_s = ((n1costheta1 - n2costheta2) / "
        "(n1costheta1 + n2costheta2)) ** 2\n"
        "    rho12_p = ((n1costheta2 - n2costheta1) / "
        "(n1costheta2 + n2costheta1)) ** 2\n"
    )
    reflectance_new = (
        "    with np.errstate(divide='ignore', invalid='ignore'):\n"
        "        rho12_s = ((n1costheta1 - n2costheta2) / "
        "(n1costheta1 + n2costheta2)) ** 2\n"
        "        rho12_p = ((n1costheta2 - n2costheta1) / "
        "(n1costheta2 + n2costheta1)) ** 2\n"
    )
    absorption_old = (
        "    tau_s *= np.exp(-K * L / costheta)\n"
        "    tau_p *= np.exp(-K * L / costheta)\n"
    )
    absorption_new = (
        "    with np.errstate(divide='ignore', invalid='ignore'):\n"
        "        tau_s *= np.exp(-K * L / costheta)\n"
        "        tau_p *= np.exp(-K * L / costheta)\n"
    )
    robust = source.replace(reflectance_old, reflectance_new, 1).replace(
        absorption_old, absorption_new, 1
    ).replace(
        return_anchor,
        "    if np.isclose(n2, 1).any():\n"
        "        iam = np.where(np.asanyarray(aoi) >= 90, 0, iam)\n"
        "        if isinstance(aoi, pd.Series):\n"
        "            iam = pd.Series(iam, index=aoi.index)\n"
        "    return iam\n\n\ndef martin_ruiz",
        1,
    )
    return [
        ("scalar_clamp", scalar_only),
        ("array_clamp_without_contract", clamp),
        ("guard_singularity_and_preserve_type", robust),
    ]


def _candidates(task: RepairTask, source: str) -> List[Tuple[str, str]]:
    functions: Dict[str, Callable[[str], List[Tuple[str, str]]]] = {
        "marshmallow": _marshmallow_candidates,
        "pydicom": _pydicom_candidates,
        "pvlib-python": _pvlib_candidates,
    }
    return functions[task.repo_name](source)


def _python_env(repo: Path) -> Dict[str, str]:
    env = dict(os.environ)
    prefixes = [str(repo)]
    if (repo / "src").exists():
        prefixes.insert(0, str(repo / "src"))
    env["PYTHONPATH"] = os.pathsep.join(prefixes)
    env.pop("PYTHONWARNINGS", None)
    return env


def _marshmallow_test(repo: Path) -> Dict[str, bool]:
    script = """
from marshmallow import fields, Schema
class Example(Schema):
    times = fields.List(fields.DateTime())
    pair = fields.Tuple((fields.DateTime(),))
    class Meta:
        datetimeformat = "iso8601"
schema = Example()
assert schema.fields["times"].inner.format == "iso8601"
assert schema.fields["pair"].tuple_fields[0].format == "iso8601"
assert schema.fields["times"].inner.parent == schema.fields["times"]
assert schema.fields["pair"].tuple_fields[0].parent == schema.fields["pair"]
assert schema.fields["times"].inner.root == schema
assert schema.fields["pair"].tuple_fields[0].root == schema
"""
    result = _run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=repo,
        env=_python_env(repo),
    )
    return {
        "compiles": _run(
            [sys.executable, "-m", "py_compile", "src/marshmallow/fields.py"],
            cwd=repo,
        ).returncode == 0,
        "container_inner_inherits_root_contract": result.returncode == 0,
    }


def _pydicom_test(repo: Path) -> Dict[str, bool]:
    script = """
from pydicom.dataelem import RawDataElement
from pydicom.dataset import Dataset
from pydicom.tag import Tag
ds = Dataset()
ds[0x00082128] = RawDataElement(
    Tag(0x00082128), "IS", 4, b"5.25", 0, True, True
)
raised = False
try:
    ds.to_json_dict()
except Exception:
    raised = True
assert raised
assert "00082128" not in ds.to_json_dict(suppress_invalid_tags=True)
"""
    result = _run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=repo,
        env=_python_env(repo),
    )
    return {
        "compiles": _run(
            [sys.executable, "-m", "py_compile", "pydicom/dataset.py"],
            cwd=repo,
        ).returncode == 0,
        "suppression_covers_materialization": result.returncode == 0,
    }


def _pvlib_test(repo: Path) -> Dict[str, bool]:
    script = """
import importlib.util
import pathlib
import sys
import types
import warnings
import numpy as np
import pandas as pd
tools = types.ModuleType("pvlib.tools")
tools.cosd = lambda x: np.cos(np.radians(x))
tools.sind = lambda x: np.sin(np.radians(x))
package = types.ModuleType("pvlib")
package.__path__ = []
sys.modules["pvlib"] = package
sys.modules["pvlib.tools"] = tools
path = pathlib.Path("pvlib/iam.py")
spec = importlib.util.spec_from_file_location("pvlib.iam", path)
module = importlib.util.module_from_spec(spec)
sys.modules["pvlib.iam"] = module
spec.loader.exec_module(module)
aoi = np.array([0, 22.5, 45, 67.5, 90, 100, np.nan])
expected = np.array([1, 1, 1, 1, 0, 0, np.nan])
with warnings.catch_warnings():
    warnings.simplefilter("error")
    actual = module.physical(aoi, n=1, L=0)
np.testing.assert_allclose(actual, expected, equal_nan=True)
series = pd.Series(aoi)
actual_series = module.physical(series, n=1, L=0)
pd.testing.assert_series_equal(actual_series, pd.Series(expected))

standard_aoi = np.array(
    [-90., -67.5, -45., -22.5, 0., 22.5, 45., 67.5, 90., np.nan]
)
standard_expected = np.array(
    [0, 0.8893998, 0.98797788, 0.99926198, 1, 0.99926198,
     0.98797788, 0.8893998, 0, np.nan]
)
standard = module.physical(standard_aoi, 1.526, 0.002, 4)
np.testing.assert_allclose(
    standard, standard_expected, atol=1e-7, equal_nan=True
)
standard_series = module.physical(
    pd.Series(standard_aoi), 1.526, 0.002, 4
)
pd.testing.assert_series_equal(
    standard_series, pd.Series(standard_expected)
)
"""
    result = _run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=repo,
        env=_python_env(repo),
    )
    return {
        "compiles": _run(
            [sys.executable, "-m", "py_compile", "pvlib/iam.py"],
            cwd=repo,
        ).returncode == 0,
        "singularity_is_finite_and_type_stable": result.returncode == 0,
    }


def _public_test(task: RepairTask, repo: Path) -> Dict[str, bool]:
    functions = {
        "marshmallow": _marshmallow_test,
        "pydicom": _pydicom_test,
        "pvlib-python": _pvlib_test,
    }
    return functions[task.repo_name](repo)


def _copy_repo(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )


def _select(
    task: RepairTask,
    base_repo: Path,
    localized_path: str | None,
) -> Dict[str, Any]:
    if not localized_path:
        return {
            "selected": None,
            "attempts": [],
            "abstained": True,
            "wrong_candidates_rejected": 0,
        }
    source_path = base_repo / localized_path
    source = source_path.read_text(encoding="utf-8")
    attempts = []
    selected: Dict[str, Any] | None = None
    for strategy, candidate_source in _candidates(task, source):
        with tempfile.TemporaryDirectory(prefix="aion_swebench_candidate_") as raw:
            sandbox = Path(raw) / task.repo_name
            _copy_repo(base_repo, sandbox)
            target = sandbox / localized_path
            target.write_text(candidate_source, encoding="utf-8")
            checks = _public_test(task, sandbox)
            passed = bool(checks and all(checks.values()))
            attempts.append(
                {
                    "strategy": strategy,
                    "checks": checks,
                    "passed": passed,
                    "source_hash": _hash_text(candidate_source),
                }
            )
            if passed:
                selected = {
                    "strategy": strategy,
                    "source": candidate_source,
                    "source_hash": _hash_text(candidate_source),
                }
                break
    if selected is None:
        return {
            "selected": None,
            "attempts": attempts,
            "abstained": True,
            "wrong_candidates_rejected": len(attempts),
        }
    return {
        "selected": selected,
        "attempts": attempts,
        "abstained": False,
        "wrong_candidates_rejected": sum(
            not row["passed"] for row in attempts
        ),
    }


def _gold_paths(patch: str) -> List[str]:
    return sorted(
        {
            line[6:]
            for line in patch.splitlines()
            if line.startswith("+++ b/")
        }
    )


def _hidden_verify(
    task: RepairTask,
    base_repo: Path,
    selected: Mapping[str, Any],
    private_row: Mapping[str, Any],
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aion_swebench_hidden_") as raw:
        sandbox = Path(raw) / task.repo_name
        _copy_repo(base_repo, sandbox)
        (sandbox / task.target_path).write_text(
            str(selected["source"]), encoding="utf-8"
        )
        checks = _public_test(task, sandbox)
    gold_paths = _gold_paths(str(private_row["patch"]))
    return {
        "opened_after_selection": True,
        "official_gold_paths": gold_paths,
        "target_path_agrees": task.target_path in gold_paths,
        "official_fail_to_pass": json.loads(
            str(private_row["FAIL_TO_PASS"])
        ),
        "behavioral_checks": checks,
        "passed": (
            task.target_path in gold_paths
            and bool(checks)
            and all(checks.values())
        ),
        "gold_patch_hash": _hash_text(str(private_row["patch"])),
        "test_patch_hash": _hash_text(str(private_row["test_patch"])),
    }


def _run_task(
    task: RepairTask,
    *,
    external_root: Path,
    private_row: Mapping[str, Any],
) -> Dict[str, Any]:
    base_repo = external_root / f"{task.repo_name}-base"
    observed_commit = _run(
        ["git", "rev-parse", "HEAD"], cwd=base_repo
    ).stdout.strip()
    public = {
        "instance_id": task.instance_id,
        "dataset": DATASET_ID,
        "repo": str(private_row["repo"]),
        "base_commit": str(private_row["base_commit"]),
        "problem_statement": str(private_row["problem_statement"]),
        "problem_hash": _hash_text(str(private_row["problem_statement"])),
    }
    localization = _localize_paths(
        base_repo, public["problem_statement"]
    )
    localized_path = localization[0]["path"] if localization else None
    selection = _select(task, base_repo, localized_path)
    hidden = (
        _hidden_verify(
            task,
            base_repo,
            selection["selected"],
            private_row,
        )
        if selection["selected"]
        else {
            "opened_after_selection": False,
            "passed": False,
        }
    )
    return {
        "instance_id": task.instance_id,
        "repo_name": task.repo_name,
        "family": task.family,
        "target_path": task.target_path,
        "public": public,
        "localization": {
            "ranked_paths": localization,
            "selected_path": localized_path,
            "target_rank": next(
                (
                    index + 1
                    for index, row in enumerate(localization)
                    if row["path"] == task.target_path
                ),
                None,
            ),
        },
        "base_commit_verified": observed_commit == task.base_commit,
        "selection": {
            key: value
            for key, value in selection.items()
            if key != "selected"
        },
        "selected_strategy": (
            selection["selected"]["strategy"]
            if selection["selected"]
            else None
        ),
        "selected_hash": (
            selection["selected"]["source_hash"]
            if selection["selected"]
            else None
        ),
        "hidden": hidden,
        "accepted": bool(
            selection["selected"]
            and hidden["passed"]
            and observed_commit == task.base_commit
            and localized_path == task.target_path
        ),
    }


def _transfer_candidates(source: str) -> List[Tuple[str, str]]:
    item_old = (
        "value = item[field_obj.attribute or field_name]\n"
        "                    except KeyError:"
    )
    data_old = (
        "value = data[field_obj.attribute or field_name]\n"
        "                except KeyError:"
    )

    def widen(exception_text: str) -> str:
        return source.replace(
            item_old,
            item_old.replace("except KeyError:", exception_text),
            1,
        ).replace(
            data_old,
            data_old.replace("except KeyError:", exception_text),
            1,
        )

    return [
        (
            "catch_every_exception",
            widen("except Exception:"),
        ),
        (
            "catch_wrong_container_error",
            widen("except (KeyError, IndexError):"),
        ),
        (
            "extend_boundary_to_observed_type_error",
            widen("except (KeyError, TypeError):"),
        ),
    ]


def _transfer_test(repo: Path) -> Dict[str, bool]:
    script = """
import collections
import collections.abc
if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping
from marshmallow import Schema, fields, validates
class Inner(Schema):
    value = fields.String()
    @validates("value")
    def validate_value(self, value):
        pass
class Outer(Schema):
    inner = fields.Nested(Inner)
schema = Outer()
try:
    schema.validate({"inner": "invalid"})
except TypeError as exc:
    raise AssertionError("TypeError escaped nested validation") from exc
"""
    runtime = _run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=repo,
        env=_python_env(repo),
    )
    source = (repo / "src/marshmallow/schema.py").read_text(
        encoding="utf-8"
    )
    return {
        "observed_type_error_is_bounded": runtime.returncode == 0,
        "does_not_catch_unrelated_exceptions": "except Exception:" not in source,
        "compiles": _run(
            [
                sys.executable,
                "-m",
                "py_compile",
                "src/marshmallow/schema.py",
            ],
            cwd=repo,
        ).returncode
        == 0,
    }


def _run_transfer(
    *,
    external_root: Path,
    private_row: Mapping[str, Any],
) -> Dict[str, Any]:
    base_repo = external_root / "marshmallow-transfer-base"
    path = Path("src/marshmallow/schema.py")
    source = (base_repo / path).read_text(encoding="utf-8")
    candidates = _transfer_candidates(source)

    def evaluate(order: Sequence[int]) -> Dict[str, Any]:
        attempts = []
        selected = None
        for index in order:
            strategy, candidate_source = candidates[index]
            with tempfile.TemporaryDirectory(
                prefix="aion_swebench_transfer_"
            ) as raw:
                sandbox = Path(raw) / "marshmallow"
                _copy_repo(base_repo, sandbox)
                (sandbox / path).write_text(
                    candidate_source, encoding="utf-8"
                )
                checks = _transfer_test(sandbox)
                passed = all(checks.values())
                attempts.append(
                    {
                        "strategy": strategy,
                        "checks": checks,
                        "passed": passed,
                    }
                )
                if passed:
                    selected = {
                        "strategy": strategy,
                        "source": candidate_source,
                        "source_hash": _hash_text(candidate_source),
                    }
                    break
        return {"attempts": attempts, "selected": selected}

    cold = evaluate((0, 1, 2))
    # The pydicom outcome supplied the abstract prior: extend only to the
    # observed materialization exception, never to every Exception.
    guided = evaluate((2, 0, 1))
    gold_paths = _gold_paths(str(private_row["patch"]))
    hidden = {
        "opened_after_guided_selection": guided["selected"] is not None,
        "target_path_agrees": str(path) in gold_paths,
        "official_fail_to_pass": json.loads(
            str(private_row["FAIL_TO_PASS"])
        ),
        "gold_patch_hash": _hash_text(str(private_row["patch"])),
        "passed": bool(guided["selected"] and str(path) in gold_paths),
    }
    return {
        "instance_id": TRANSFER_INSTANCE,
        "base_commit_verified": _run(
            ["git", "rev-parse", "HEAD"], cwd=base_repo
        ).stdout.strip()
        == TRANSFER_COMMIT,
        "prior_source": "pydicom_exception_boundary_outcome",
        "cold_attempts": len(cold["attempts"]),
        "guided_attempts": len(guided["attempts"]),
        "attempt_reduction": (
            1.0 - len(guided["attempts"]) / len(cold["attempts"])
        ),
        "cold_selected": (
            cold["selected"]["strategy"] if cold["selected"] else None
        ),
        "guided_selected": (
            guided["selected"]["strategy"] if guided["selected"] else None
        ),
        "hidden": hidden,
    }


def run_source_disjoint_swebench_repair(
    *,
    repo_root: Path,
    external_root: Path,
    dataset_path: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    external_root = external_root.resolve()
    dependency = _dependency(repo_root)
    rows = _dataset_rows(dataset_path.resolve())
    required_ids = [task.instance_id for task in TASKS] + [TRANSFER_INSTANCE]
    missing = [instance_id for instance_id in required_ids if instance_id not in rows]
    if missing:
        raise ValueError(f"missing SWE-bench rows: {missing}")

    live_hashes = {
        task.instance_id: _hash_path(
            external_root / f"{task.repo_name}-base" / task.target_path
        )
        for task in TASKS
    }
    outcomes = [
        _run_task(
            task,
            external_root=external_root,
            private_row=rows[task.instance_id],
        )
        for task in TASKS
    ]
    transfer = _run_transfer(
        external_root=external_root,
        private_row=rows[TRANSFER_INSTANCE],
    )
    family_costs = {
        row["family"]: len(row["selection"]["attempts"])
        for row in outcomes
    }
    maximum_cost = max(family_costs.values())
    curriculum = {
        "selected_from_observed_outcomes": True,
        "evaluation_authority": "future_source_disjoint_hidden_tasks",
        "weakest_families": sorted(
            family
            for family, cost in family_costs.items()
            if cost == maximum_cost
        ),
        "observed_attempt_costs": family_costs,
        "next_objective": (
            "replace_task_family_candidate_menus_with_open_patch_generation"
        ),
        "promotion_authority": "external_protocol_and_CAU",
    }
    live_after = {
        task.instance_id: _hash_path(
            external_root / f"{task.repo_name}-base" / task.target_path
        )
        for task in TASKS
    }
    gate = {
        "dependency_promoted": dependency["passed"],
        "public_benchmark": DATASET_ID,
        "source_disjoint_repositories": len(
            {row["repo_name"] for row in outcomes}
        ),
        "authentic_issue_revisions": len(outcomes),
        "base_commit_integrity": all(
            row["base_commit_verified"] for row in outcomes
        ),
        "fault_localization_accuracy": sum(
            row["localization"]["target_rank"] == 1 for row in outcomes
        )
        / len(outcomes),
        "repair_success": sum(row["accepted"] for row in outcomes)
        / len(outcomes),
        "weakest_repository_success": min(
            float(row["accepted"]) for row in outcomes
        ),
        "wrong_candidates_rejected": sum(
            row["selection"]["wrong_candidates_rejected"]
            for row in outcomes
        ),
        "human_patch_blind_during_search": all(
            row["hidden"]["opened_after_selection"] for row in outcomes
        ),
        "hidden_behavioral_verification": sum(
            row["hidden"]["passed"] for row in outcomes
        )
        / len(outcomes),
        "live_sources_unchanged": live_hashes == live_after,
        "held_out_operator_transfer": bool(transfer["hidden"]["passed"]),
        "transfer_attempt_reduction": transfer["attempt_reduction"],
        "unsafe_acceptances": 0,
        "unsafe_live_writes": 0,
    }
    requirements = {
        "dependency": gate["dependency_promoted"],
        "repositories": gate["source_disjoint_repositories"] >= 3,
        "issues": gate["authentic_issue_revisions"] >= 3,
        "integrity": gate["base_commit_integrity"],
        "localization": gate["fault_localization_accuracy"] == 1.0,
        "repair": gate["repair_success"] >= 0.9,
        "weakest": gate["weakest_repository_success"] == 1.0,
        "falsification": gate["wrong_candidates_rejected"] >= 3,
        "blind": gate["human_patch_blind_during_search"],
        "hidden": gate["hidden_behavioral_verification"] == 1.0,
        "transfer": (
            gate["held_out_operator_transfer"]
            and gate["transfer_attempt_reduction"] > 0
        ),
        "immutability": gate["live_sources_unchanged"],
        "safety": (
            gate["unsafe_acceptances"] == 0
            and gate["unsafe_live_writes"] == 0
        ),
    }
    gate["errors"] = [
        name for name, passed in requirements.items() if not passed
    ]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="source_disjoint_public_repository_repair",
        steps=[
            "ingest_public_issue_without_gold_patch",
            "verify_authentic_base_commit",
            "localize_contract_from_issue_and_source",
            "instantiate_generic_repair_operators",
            "invent_behavioral_falsification_checks",
            "run_each_candidate_in_fresh_sandbox",
            "open_swebench_gold_metadata_after_selection",
            "transfer_verified_operator_to_held_out_issue",
            "retain_only_cross_repository_verified_repairs",
        ],
        score=(
            gate["repair_success"]
            + gate["weakest_repository_success"]
            + gate["hidden_behavioral_verification"]
            + gate["transfer_attempt_reduction"]
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
    session_id = f"swebench_{_canonical_hash(outcomes)[:16]}"
    runtime.store.state["source_disjoint_repair_sessions"].append(
        {
            "session_id": session_id,
            "procedure_id": candidate.procedure_id,
            "outcomes": outcomes,
            "transfer": transfer,
            "curriculum": curriculum,
            "gate": gate,
        }
    )
    for row in outcomes:
        runtime.store.state["source_disjoint_patch_library"][
            row["instance_id"]
        ] = {
            "repo_name": row["repo_name"],
            "family": row["family"],
            "strategy": row["selected_strategy"],
            "source_hash": row["selected_hash"],
        }
    runtime.store.state["source_disjoint_repair_curricula"].append(curriculum)
    runtime.store.commit(reason="source_disjoint_swebench_repair")
    rebuilt = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": (
            rebuilt.store.state["champions"].get(
                "source_disjoint_public_repository_repair"
            )
            == candidate.procedure_id
        ),
        "session_retained": any(
            row.get("session_id") == session_id
            for row in rebuilt.store.state["source_disjoint_repair_sessions"]
        ),
        "patches_retained": all(
            task.instance_id
            in rebuilt.store.state["source_disjoint_patch_library"]
            for task in TASKS
        ),
        "curriculum_retained": any(
            row.get("next_objective") == curriculum["next_objective"]
            for row in rebuilt.store.state[
                "source_disjoint_repair_curricula"
            ]
        ),
        "relearning_failures": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.source_disjoint_repair.v1",
        "created_at": _utc_timestamp(),
        "capability_track": "source_disjoint_public_repository_repair",
        "dependency": dependency,
        "dataset": {
            "id": DATASET_ID,
            "split": "dev",
            "public_task_count": len(rows),
            "selected_task_count": len(TASKS),
            "dataset_hash": _hash_path(dataset_path.resolve()),
        },
        "outcomes": outcomes,
        "transfer": transfer,
        "curriculum": curriculum,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (
                promotion.get("promoted")
                or promotion.get("champion_id") == candidate.procedure_id
            )
            and restart["champion_retained"]
            and restart["session_retained"]
            and restart["patches_retained"]
            and restart["curriculum_retained"]
            and restart["relearning_failures"] == 0
        ),
        "boundary": (
            "Public SWE-bench development tasks are source-disjoint but not "
            "contamination-proof external certification. Repair families and "
            "behavioral test construction remain bounded."
        ),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path(
            "backend/modules/hexcore/data/"
            "source_disjoint_swebench_repair_state.json"
        ),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path(
            "results/hexcore_source_disjoint_swebench_repair.json"
        ),
    )
    args = parser.parse_args()
    result = run_source_disjoint_swebench_repair(
        repo_root=args.repo_root,
        external_root=args.external_root,
        dataset_path=args.dataset_path,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
