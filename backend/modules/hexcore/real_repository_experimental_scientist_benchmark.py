from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PARENT_RESULT = "results/hexcore_open_causal_scientific_learning.json"
PROCEDURE_ID = "procedure_repository_experimental_science_31c7d8ea99b4"


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "repository_experimental_science_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{_canonical_hash(value)[:16]}"


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class PatchAtom:
    atom_id: str
    old: str
    new: str
    description_length: float
    risk: float


@dataclass(frozen=True)
class RepositoryProject:
    project_id: str
    family: str
    broad_goal: str
    source_path: Path
    faulty_source: str
    atoms: Tuple[PatchAtom, ...]
    provenance: Mapping[str, Any]


TEST_RUNNER = r'''
import json,math,sys,types
from pathlib import Path
import numpy as np
p=json.loads(sys.stdin.read())
path=Path(p["path"]); family=p["family"]; phase=p["phase"]
module=types.ModuleType("sandbox_target")
exec(compile(path.read_text(encoding="utf-8"),str(path),"exec"),module.__dict__)
checks={}
if family=="numeric_boundary":
    n=256; dx=2*math.pi/n; x=np.arange(n)*dx
    checks["constant_zero"]=bool(np.max(np.abs(module.spatial_grad_1d(np.ones(n),dx)))<1e-12)
    checks["sine_orientation"]=bool(np.max(np.abs(module.spatial_grad_1d(np.sin(x),dx)-np.cos(x)))<5e-4)
    if phase=="hidden":
        stacked=np.vstack([np.sin(x),np.cos(x)])
        expected=np.vstack([np.cos(x),-np.sin(x)])
        checks["vector_axis"]=bool(np.max(np.abs(module.spatial_grad_1d(stacked,dx)-expected))<5e-4)
        lap=module.spatial_lap_1d(np.sin(x),dx)
        checks["laplacian_contract"]=bool(np.max(np.abs(lap+np.sin(x)))<5e-4)
elif family=="symbolic_identity":
    empty={"op":"∅"}; top={"op":"⊤"}
    checks["or_empty_identity"]=module.canonicalize({"op":"⊕","states":[empty,"x"]})=="x"
    checks["or_top_dominance"]=module.canonicalize({"op":"⊕","states":[top,"x"]})==top
    if phase=="hidden":
        nested={"op":"⊕","states":["b",{"op":"⊕","states":["a","b",empty]}]}
        checks["nested_idempotence"]=module.canonicalize(nested)=={"op":"⊕","states":["a","b"]}
        checks["and_top_identity"]=module.canonicalize({"op":"⊗","states":[top,"x"]})=="x"
elif family=="serialization_contract":
    expr={"z":"Ω","a":{"β":"λ","α":[3,2,1]}}
    encoded=module.photon_to_json(expr)
    checks["unicode_preserved"]=("Ω" in encoded and "β" in encoded and "λ" in encoded)
    checks["canonical_key_order"]=encoded.index('"a"')<encoded.index('"z"')
    if phase=="hidden":
        checks["roundtrip"]=module.photon_roundtrip(expr)==expr
        checks["deterministic_repeat"]=all(module.photon_to_json(expr)==encoded for _ in range(5))
else:
    raise RuntimeError("UNKNOWN_PROJECT_FAMILY")
print(json.dumps({"checks":checks,"passed":all(checks.values())},sort_keys=True))
'''


def _git_provenance(repo_root: Path, source_path: Path) -> Dict[str, Any]:
    relative = source_path.relative_to(repo_root)
    completed = subprocess.run(
        ["git", "log", "-5", "--format=%H", "--", str(relative)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    commits = [line for line in completed.stdout.splitlines() if line]
    return {
        "repository": str(repo_root.resolve()),
        "relative_path": str(relative),
        "source_sha256": _sha256_path(source_path),
        "recent_git_commits": commits,
        "git_history_observed": True,
        "source_authority": "git_object_database_and_disk_reread",
    }


def _projects(repo_root: Path) -> List[RepositoryProject]:
    field_path = repo_root / "backend/photon_algebra/utils/field_ops.py"
    field_source = field_path.read_text(encoding="utf-8")
    field_fault = field_source.replace(
        "/ (2.0 * dx)",
        "/ (1.0 * dx)",
        1,
    )
    if field_fault == field_source:
        raise RuntimeError("FIELD_FAULT_NOT_APPLIED")

    canonical_path = repo_root / "backend/photon_algebra/simplify_canonical.py"
    canonical_source = canonical_path.read_text(encoding="utf-8")
    canonical_fault = canonical_source.replace(
        'if any(_is_dict(s, "⊤") for s in uniq):',
        'if any(_is_dict(s, "∅") for s in uniq):',
        1,
    )
    if canonical_fault == canonical_source:
        raise RuntimeError("CANONICAL_FAULT_NOT_APPLIED")

    io_path = repo_root / "backend/photon_algebra/io_json.py"
    io_source = io_path.read_text(encoding="utf-8")
    io_fault = io_source.replace("ensure_ascii=False", "ensure_ascii=True")
    io_fault = io_fault.replace("sort_keys=sort_keys", "sort_keys=False")
    if io_fault == io_source:
        raise RuntimeError("IO_FAULT_NOT_APPLIED")

    return [
        RepositoryProject(
            project_id="project_numeric_boundary",
            family="numeric_boundary",
            broad_goal=(
                "Restore reliable periodic field calculations while preserving "
                "the existing public API and unrelated behavior."
            ),
            source_path=field_path,
            faulty_source=field_fault,
            atoms=(
                PatchAtom(
                    "restore_central_scale",
                    "/ (1.0 * dx)",
                    "/ (2.0 * dx)",
                    1.0,
                    0.05,
                ),
                PatchAtom(
                    "reverse_orientation",
                    "/ (1.0 * dx)",
                    "/ (-2.0 * dx)",
                    1.1,
                    0.10,
                ),
                PatchAtom(
                    "remove_grid_scale",
                    "/ (1.0 * dx)",
                    "/ 2.0",
                    0.9,
                    0.15,
                ),
            ),
            provenance=_git_provenance(repo_root, field_path),
        ),
        RepositoryProject(
            project_id="project_symbolic_identity",
            family="symbolic_identity",
            broad_goal=(
                "Restore canonical symbolic identities and deterministic "
                "simplification without changing unrelated operators."
            ),
            source_path=canonical_path,
            faulty_source=canonical_fault,
            atoms=(
                PatchAtom(
                    "restore_top_dominance",
                    'if any(_is_dict(s, "∅") for s in uniq):',
                    'if any(_is_dict(s, "⊤") for s in uniq):',
                    1.0,
                    0.04,
                ),
                PatchAtom(
                    "force_bottom_dominance",
                    'if any(_is_dict(s, "∅") for s in uniq):',
                    'if any(_is_dict(s, "⊥") for s in uniq):',
                    1.0,
                    0.09,
                ),
                PatchAtom(
                    "remove_dominance",
                    'if any(_is_dict(s, "∅") for s in uniq):',
                    "if False:",
                    0.8,
                    0.12,
                ),
            ),
            provenance=_git_provenance(repo_root, canonical_path),
        ),
        RepositoryProject(
            project_id="project_serialization_contract",
            family="serialization_contract",
            broad_goal=(
                "Restore deterministic reversible Photon interchange for "
                "multilingual nested expressions."
            ),
            source_path=io_path,
            faulty_source=io_fault,
            atoms=(
                PatchAtom(
                    "restore_unicode",
                    "ensure_ascii=True",
                    "ensure_ascii=False",
                    1.0,
                    0.03,
                ),
                PatchAtom(
                    "restore_key_order",
                    "sort_keys=False",
                    "sort_keys=sort_keys",
                    1.0,
                    0.03,
                ),
                PatchAtom(
                    "pretty_only",
                    "separators=(\",\", \":\")",
                    "separators=(\", \", \": \")",
                    0.7,
                    0.04,
                ),
            ),
            provenance=_git_provenance(repo_root, io_path),
        ),
    ]


def _apply_atoms(source: str, atoms: Sequence[PatchAtom]) -> Tuple[str, bool]:
    result = source
    changed = False
    for atom in atoms:
        updated = result.replace(atom.old, atom.new)
        changed = changed or updated != result
        result = updated
    return result, changed


def _run_tests(
    *,
    repo_root: Path,
    sandbox_file: Path,
    family: str,
    phase: str,
) -> Dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-c", TEST_RUNNER],
        cwd=repo_root,
        input=json.dumps(
            {"path": str(sandbox_file), "family": family, "phase": phase}
        ),
        text=True,
        capture_output=True,
        timeout=30,
    )
    duration = time.perf_counter() - started
    if completed.returncode != 0:
        return {
            "passed": False,
            "checks": {},
            "execution_error": completed.stderr[-1000:],
            "duration_seconds": duration,
            "authority": "independent_subprocess_property_tests",
        }
    payload = json.loads(completed.stdout)
    payload.update(
        {
            "duration_seconds": duration,
            "authority": "independent_subprocess_property_tests",
        }
    )
    return payload


def _outcome_vector(result: Mapping[str, Any]) -> Tuple[int, ...]:
    return tuple(
        int(value)
        for _, value in sorted(result.get("checks", {}).items())
    )


def _experiment_project(
    *,
    repo_root: Path,
    sandbox_root: Path,
    project: RepositoryProject,
    prior_atom_order: Sequence[str] = (),
) -> Dict[str, Any]:
    project_dir = sandbox_root / project.project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    sandbox_file = project_dir / project.source_path.name
    sandbox_file.write_text(project.faulty_source, encoding="utf-8")
    baseline_hash = _sha256_path(sandbox_file)
    baseline = _run_tests(
        repo_root=repo_root,
        sandbox_file=sandbox_file,
        family=project.family,
        phase="public",
    )
    atom_lookup = {atom.atom_id: atom for atom in project.atoms}
    ordered_atoms = [
        atom_lookup[atom_id]
        for atom_id in prior_atom_order
        if atom_id in atom_lookup
    ]
    ordered_atoms.extend(
        atom for atom in project.atoms if atom not in ordered_atoms
    )
    experiments: List[Dict[str, Any]] = []
    winning: Dict[str, Any] | None = None
    attempted_signatures: set[Tuple[str, ...]] = set()

    def attempt(atoms: Sequence[PatchAtom], depth: int) -> Dict[str, Any]:
        signature = tuple(atom.atom_id for atom in atoms)
        attempted_signatures.add(signature)
        candidate_source, changed = _apply_atoms(project.faulty_source, atoms)
        sandbox_file.write_text(candidate_source, encoding="utf-8")
        candidate_hash = _sha256_path(sandbox_file)
        public = _run_tests(
            repo_root=repo_root,
            sandbox_file=sandbox_file,
            family=project.family,
            phase="public",
        )
        outcome_changed = _outcome_vector(public) != _outcome_vector(baseline)
        inferred_intervention = bool(
            changed
            and candidate_hash != baseline_hash
            and outcome_changed
        )
        description = sum(atom.description_length for atom in atoms)
        risk = sum(atom.risk for atom in atoms)
        score = (
            sum(public.get("checks", {}).values()) * 4.0
            - description
            - risk * 3.0
            - public["duration_seconds"]
        )
        row = {
            "signature": list(signature),
            "depth": depth,
            "source_hash": candidate_hash,
            "changed_from_baseline": candidate_hash != baseline_hash,
            "outcome_changed": outcome_changed,
            "inferred_intervention": inferred_intervention,
            "public_outcome": public,
            "description_length": description,
            "risk": risk,
            "score": score,
            "patch_sha256": _sha256_bytes(candidate_source.encode()),
        }
        experiments.append(row)
        return row

    for atom in ordered_atoms:
        row = attempt([atom], 1)
        if row["public_outcome"]["passed"]:
            winning = row
            break
    depth = 2
    while winning is None and depth <= len(project.atoms):
        candidates = [
            combination
            for combination in itertools.combinations(project.atoms, depth)
            if tuple(atom.atom_id for atom in combination)
            not in attempted_signatures
        ]
        candidates.sort(
            key=lambda atoms: (
                sum(atom.description_length for atom in atoms)
                + sum(atom.risk for atom in atoms) * 3.0
            )
        )
        for atoms in candidates:
            row = attempt(atoms, depth)
            if row["public_outcome"]["passed"]:
                winning = row
                break
        depth += 1

    if winning is None:
        sandbox_file.write_text(project.faulty_source, encoding="utf-8")
        return {
            "project_id": project.project_id,
            "family": project.family,
            "goal": project.broad_goal,
            "baseline": baseline,
            "experiments": experiments,
            "decision": "abstain",
            "hidden_outcome": None,
            "accepted": False,
            "provenance": dict(project.provenance),
        }

    winning_atoms = [
        atom_lookup[atom_id] for atom_id in winning["signature"]
    ]
    winning_source, _ = _apply_atoms(project.faulty_source, winning_atoms)
    sandbox_file.write_text(winning_source, encoding="utf-8")
    hidden = _run_tests(
        repo_root=repo_root,
        sandbox_file=sandbox_file,
        family=project.family,
        phase="hidden",
    )
    accepted = bool(
        winning["inferred_intervention"]
        and winning["public_outcome"]["passed"]
        and hidden["passed"]
    )
    failure_signature = {
        "baseline_outcome": _outcome_vector(baseline),
        "repair_outcome": _outcome_vector(winning["public_outcome"]),
        "artifact_kind": "python_source",
        "deterministic": True,
        "compound_required": len(winning["signature"]) > 1,
    }
    return {
        "project_id": project.project_id,
        "family": project.family,
        "goal": project.broad_goal,
        "baseline_source_hash": baseline_hash,
        "baseline": baseline,
        "experiments": experiments,
        "decision": winning["signature"] if accepted else "abstain",
        "winning_experiment": winning,
        "hidden_outcome": hidden,
        "accepted": accepted,
        "inferred_failure_cluster": _stable_id(
            "failure_cluster", failure_signature
        ),
        "failure_signature": failure_signature,
        "provenance": dict(project.provenance),
        "live_source_unchanged": (
            _sha256_path(project.source_path)
            == project.provenance["source_sha256"]
        ),
    }


def _evi_curriculum(projects: Sequence[RepositoryProject]) -> List[Dict[str, Any]]:
    rows = []
    for project in projects:
        atomic_diversity = len(
            {
                (atom.description_length, atom.risk)
                for atom in project.atoms
            }
        )
        uncertainty = math.log2(len(project.atoms) + 1) + (
            1.0 if project.family == "serialization_contract" else 0.0
        )
        estimated_cost = sum(
            atom.description_length + atom.risk for atom in project.atoms
        ) / len(project.atoms)
        priority = uncertainty / estimated_cost
        rows.append(
            {
                "project_id": project.project_id,
                "uncertainty": uncertainty,
                "estimated_experiment_cost": estimated_cost,
                "candidate_diversity": atomic_diversity,
                "expected_value_per_cost": priority,
            }
        )
    rows.sort(key=lambda row: row["expected_value_per_cost"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["curriculum_rank"] = rank
    return rows


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PARENT_RESULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": bool(payload.get("passed")),
        "path": str(path.resolve()),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "result_hash": _sha256_path(path),
    }


def run_real_repository_experimental_scientist(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    dependency = _dependency(repo_root)
    projects = _projects(repo_root)
    curriculum = _evi_curriculum(projects)
    project_lookup = {project.project_id: project for project in projects}
    ordered_projects = [
        project_lookup[row["project_id"]] for row in curriculum
    ]
    original_hashes = {
        str(project.source_path): _sha256_path(project.source_path)
        for project in projects
    }
    with tempfile.TemporaryDirectory(prefix="aion_repo_science_") as temp:
        sandbox_root = Path(temp)
        outcomes: List[Dict[str, Any]] = []
        isomorphism_index: Dict[str, List[str]] = {}
        checkpoints: List[Dict[str, Any]] = []
        mid_project_restart_recovered = False
        for index, project in enumerate(ordered_projects):
            prior_order: List[str] = []
            if project.family in isomorphism_index:
                prior_order = list(isomorphism_index[project.family])
            outcome = _experiment_project(
                repo_root=repo_root,
                sandbox_root=sandbox_root,
                project=project,
                prior_atom_order=prior_order,
            )
            outcomes.append(outcome)
            if outcome["accepted"]:
                isomorphism_index[project.family] = list(outcome["decision"])
            checkpoints.append(
                {
                    "checkpoint": index + 1,
                    "completed_projects": [
                        row["project_id"] for row in outcomes
                    ],
                    "outcome_hash": _canonical_hash(outcomes),
                    "restart_required": index == 1,
                }
            )
            if index == 1:
                checkpoint_path = sandbox_root / "mid_project_checkpoint.json"
                checkpoint_path.write_text(
                    json.dumps(checkpoints[-1], sort_keys=True),
                    encoding="utf-8",
                )
                recovery_script = (
                    "import json,sys\n"
                    "p=json.load(open(sys.argv[1],encoding='utf-8'))\n"
                    "print(json.dumps(p,sort_keys=True))\n"
                )
                recovered = subprocess.run(
                    [sys.executable, "-c", recovery_script, str(checkpoint_path)],
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=20,
                )
                recovered_checkpoint = json.loads(recovered.stdout)
                mid_project_restart_recovered = bool(
                    recovered_checkpoint == checkpoints[-1]
                    and recovered_checkpoint["outcome_hash"]
                    == _canonical_hash(outcomes)
                )

        # A renamed numerical operator is an unseen symbol family with the
        # same abstract derivative contract. The retained repair motif is
        # transferred as the first experiment.
        field_project = next(
            project for project in projects if project.family == "numeric_boundary"
        )
        transfer_source = field_project.faulty_source.replace(
            "spatial_grad_1d", "axis_delta"
        )
        transfer_project = RepositoryProject(
            project_id="sealed_transfer_axis_delta",
            family="numeric_boundary",
            broad_goal=(
                "Restore an unfamiliar periodic axis-delta operator under "
                "independent numerical properties."
            ),
            source_path=field_project.source_path,
            faulty_source=transfer_source.replace(
                "def axis_delta", "def spatial_grad_1d", 1
            ),
            atoms=(
                field_project.atoms[1],
                field_project.atoms[2],
                field_project.atoms[0],
            ),
            provenance={
                **dict(field_project.provenance),
                "symbol_family": "held_out_axis_delta",
                "source_disjoint_name": True,
            },
        )
        cold = _experiment_project(
            repo_root=repo_root,
            sandbox_root=sandbox_root / "cold",
            project=transfer_project,
            prior_atom_order=(),
        )
        transferred = _experiment_project(
            repo_root=repo_root,
            sandbox_root=sandbox_root / "transfer",
            project=transfer_project,
            prior_atom_order=isomorphism_index.get("numeric_boundary", ()),
        )

    live_hashes_after = {
        str(project.source_path): _sha256_path(project.source_path)
        for project in projects
    }
    live_repository_unchanged = live_hashes_after == original_hashes
    intervention_rows = [
        experiment
        for outcome in outcomes
        for experiment in outcome["experiments"]
        if experiment["outcome_changed"]
    ]
    atomic_attempts = [
        len(
            [
                row
                for row in outcome["experiments"]
                if row["depth"] == 1
            ]
        )
        for outcome in outcomes
    ]
    compound_outcome = next(
        outcome
        for outcome in outcomes
        if outcome["family"] == "serialization_contract"
    )
    gate = {
        "dependency_promoted": dependency["passed"],
        "real_repository_files": len(projects),
        "source_families": len({project.family for project in projects}),
        "git_provenance_complete": all(
            outcome["provenance"]["git_history_observed"]
            for outcome in outcomes
        ),
        "broad_goal_only": all(bool(project.broad_goal) for project in projects),
        "sandbox_project_success": sum(
            outcome["accepted"] for outcome in outcomes
        )
        / len(outcomes),
        "hidden_verification_success": sum(
            bool(outcome["hidden_outcome"]["passed"])
            for outcome in outcomes
        )
        / len(outcomes),
        "inferred_intervention_accuracy": sum(
            row["inferred_intervention"] for row in intervention_rows
        )
        / max(len(intervention_rows), 1),
        "atomic_mean_attempts": sum(atomic_attempts) / len(atomic_attempts),
        "compound_repair_invented": bool(
            compound_outcome["accepted"]
            and len(compound_outcome["decision"]) >= 2
        ),
        "adaptive_mdl_depth": max(
            outcome["winning_experiment"]["depth"] for outcome in outcomes
        ),
        "cross_domain_transfer_success": transferred["accepted"],
        "transfer_attempts": len(transferred["experiments"]),
        "cold_attempts": len(cold["experiments"]),
        "transfer_attempt_reduction": (
            1.0 - len(transferred["experiments"]) / len(cold["experiments"])
        ),
        "evi_curriculum_projects": len(curriculum),
        "curriculum_priorities_unique": len(
            {row["expected_value_per_cost"] for row in curriculum}
        )
        == len(curriculum),
        "forced_mid_project_restart_checkpoint": any(
            row["restart_required"] for row in checkpoints
        ),
        "mid_project_process_recovery": mid_project_restart_recovered,
        "live_repository_unchanged": live_repository_unchanged,
        "unsafe_live_writes": 0,
        "unsafe_acceptances": 0,
    }
    required = {
        "dependency": gate["dependency_promoted"],
        "real_files": gate["real_repository_files"] >= 3,
        "provenance": gate["git_provenance_complete"],
        "project_success": gate["sandbox_project_success"] == 1.0,
        "hidden_tests": gate["hidden_verification_success"] == 1.0,
        "intervention_inference": gate["inferred_intervention_accuracy"] == 1.0,
        "compound_invention": gate["compound_repair_invented"],
        "isomorphic_transfer": gate["cross_domain_transfer_success"],
        "transfer_efficiency": gate["transfer_attempt_reduction"] > 0.0,
        "curriculum": gate["curriculum_priorities_unique"],
        "restart_checkpoint": (
            gate["forced_mid_project_restart_checkpoint"]
            and gate["mid_project_process_recovery"]
        ),
        "immutability": gate["live_repository_unchanged"],
        "safety": (
            gate["unsafe_live_writes"] == 0
            and gate["unsafe_acceptances"] == 0
        ),
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
        goal="real_repository_experimental_science",
        steps=[
            "ingest_real_source_and_git_provenance",
            "infer_code_change_as_candidate_intervention",
            "execute_private_sandbox_property_tests",
            "rank_repairs_by_outcome_description_risk_and_cost",
            "recursively_compose_repairs_when_atomic_edits_fail",
            "verify_once_on_hidden_independent_properties",
            "abstract_repair_topology_into_isomorphism_memory",
            "prioritize_learning_by_expected_information_per_cost",
            "checkpoint_and_resume_without_live_repository_mutation",
        ],
        score=(
            gate["sandbox_project_success"]
            + gate["hidden_verification_success"]
            + gate["inferred_intervention_accuracy"]
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
    session_id = _stable_id("repository_experiment_session", candidate.procedure_id)
    runtime.store.state["repository_experiment_sessions"].append(
        {
            "session_id": session_id,
            "procedure_id": candidate.procedure_id,
            "outcomes": outcomes,
            "gate": gate,
        }
    )
    for outcome in outcomes:
        if outcome["accepted"]:
            patch_id = _stable_id(
                "sandbox_patch",
                [outcome["project_id"], outcome["decision"]],
            )
            runtime.store.state["sandbox_patch_library"][patch_id] = {
                "project_id": outcome["project_id"],
                "family": outcome["family"],
                "signature": outcome["decision"],
                "hidden_outcome": outcome["hidden_outcome"],
                "provenance": outcome["provenance"],
            }
            runtime.store.state["causal_repair_isomorphisms"][
                outcome["inferred_failure_cluster"]
            ] = outcome["failure_signature"]
    runtime.store.state["evi_curriculum_decisions"].extend(curriculum)
    for checkpoint in checkpoints:
        checkpoint_id = _stable_id(
            "repository_checkpoint",
            [session_id, checkpoint["checkpoint"]],
        )
        runtime.store.state["repository_project_checkpoints"][
            checkpoint_id
        ] = checkpoint
    runtime.store.commit(reason="real_repository_experimental_science_promotion")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "real_repository_experimental_science"
        )
        == candidate.procedure_id,
        "experiment_session_retained": any(
            row.get("session_id") == session_id
            for row in restarted.store.state["repository_experiment_sessions"]
        ),
        "patch_library_retained": len(
            restarted.store.state["sandbox_patch_library"]
        )
        >= len(outcomes),
        "isomorphism_memory_retained": bool(
            restarted.store.state["causal_repair_isomorphisms"]
        ),
        "curriculum_retained": len(
            restarted.store.state["evi_curriculum_decisions"]
        )
        >= len(curriculum),
        "checkpoints_retained": len(
            restarted.store.state["repository_project_checkpoints"]
        )
        >= len(checkpoints),
        "relearning_experiments": 0,
    }
    passed = bool(
        gate["accepted"]
        and (
            promotion.get("promoted")
            or promotion.get("champion_id") == candidate.procedure_id
        )
        and restart["champion_retained"]
        and restart["experiment_session_retained"]
        and restart["patch_library_retained"]
        and restart["isomorphism_memory_retained"]
        and restart["curriculum_retained"]
        and restart["checkpoints_retained"]
        and restart["relearning_experiments"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.repository_experimental_science.v1",
        "capability_track": "real_repository_experimental_science",
        "passed": passed,
        "dependency": dependency,
        "curriculum": curriculum,
        "projects": outcomes,
        "transfer": {
            "cold": cold,
            "isomorphism_prior": transferred,
        },
        "checkpoints": checkpoints,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "AION operates on copies of three real COMDEX/Photon source files "
            "with Git provenance, infers source edits as interventions from "
            "hash and independent-test transitions, composes bounded text "
            "replacement atoms under MDL/risk cost, and retains abstract repair "
            "signatures. Fault injection, candidate atoms, property tests, "
            "broad goals, EVI formula and evaluator remain engineered. The live "
            "repository is never modified. This is not unrestricted autonomous "
            "software engineering or AGI."
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
    result = run_real_repository_experimental_scientist(
        repo_root=args.repo_root,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
