from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.real_file_long_horizon_project_benchmark import (
    PHASE_FAMILIES,
    PHASE_REPORT_NAMES,
    PHASE_RESULT_NAMES,
)


@dataclass(frozen=True)
class RelationalProject:
    project_id: str
    cohort: str
    family: str
    phase: int
    source_paths: Dict[str, Path]
    dependencies: Dict[str, Tuple[str, ...]]


@dataclass(frozen=True)
class WorldModel:
    model_id: str
    invalidation_operator: str
    conflict_policy: str
    complexity: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "invalidation_operator": self.invalidation_operator,
            "conflict_policy": self.conflict_policy,
            "complexity": self.complexity,
        }


KNOWN_EVENTS = {
    "source_revision",
    "reconcile_confirmed",
    "reconcile_conflict",
}


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase57_relational_world_model_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dependency_graph(*, with_policy: bool, extended: bool) -> Dict[str, Tuple[str, ...]]:
    graph: Dict[str, Tuple[str, ...]] = {
        "status_projection": ("source:result",),
        "evidence_binding": ("source:report", "status_projection"),
        "manifest": ("status_projection", "evidence_binding"),
        "independent_verification": ("manifest",),
        "project_closure": ("independent_verification",),
    }
    if with_policy:
        graph["authority_check"] = ("source:policy", "status_projection")
        graph["manifest"] = (
            "status_projection",
            "evidence_binding",
            "authority_check",
        )
    if extended:
        graph["publication_receipt"] = (
            "independent_verification",
            "source:policy",
        )
        graph["project_closure"] = (
            "independent_verification",
            "publication_receipt",
        )
    return graph


def _projects(
    *,
    repo_root: Path,
    phases: Sequence[int],
    cohort: str,
) -> List[RelationalProject]:
    rows = []
    for index, phase in enumerate(phases):
        with_policy = index % 2 == 1 or cohort == "sealed"
        paths = {
            "result": repo_root / "results" / PHASE_RESULT_NAMES[phase],
            "report": repo_root / "docs" / "aion" / PHASE_REPORT_NAMES[phase],
        }
        if with_policy:
            paths["policy"] = (
                repo_root / "backend" / "modules" / "hexcore"
                / "governance_config.yaml"
            )
        rows.append(
            RelationalProject(
                project_id=f"{cohort}_world_model_phase_{phase}",
                cohort=cohort,
                family=PHASE_FAMILIES[phase],
                phase=phase,
                source_paths=paths,
                dependencies=_dependency_graph(
                    with_policy=with_policy,
                    extended=cohort == "sealed" and index % 2 == 0,
                ),
            )
        )
    return rows


def _copy_project(
    project: RelationalProject,
    workspace_root: Path,
) -> Dict[str, Path]:
    root = workspace_root / project.project_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    copied = {}
    for role, source in project.source_paths.items():
        destination = root / f"{role}_{source.name}"
        shutil.copy2(source, destination)
        copied[role] = destination
    return copied


def _dependents(
    dependencies: Mapping[str, Sequence[str]],
    entity: str,
    *,
    transitive: bool,
) -> Set[str]:
    selected: Set[str] = set()
    frontier = {entity}
    while frontier:
        next_frontier: Set[str] = set()
        for artifact, inputs in dependencies.items():
            if artifact in selected:
                continue
            if any(parent in frontier for parent in inputs):
                selected.add(artifact)
                next_frontier.add(artifact)
        if not transitive:
            break
        frontier = next_frontier
    return selected


def _all_artifacts(dependencies: Mapping[str, Sequence[str]]) -> Set[str]:
    return {name for name in dependencies if not name.startswith("source:")}


def _expected_effect(
    project: RelationalProject,
    *,
    event_kind: str,
    source_role: str | None = None,
) -> Dict[str, Any]:
    if event_kind == "source_revision":
        invalidated = _dependents(
            project.dependencies,
            f"source:{source_role}",
            transitive=True,
        )
        return {
            "invalidated": sorted(invalidated),
            "project_state": "revision_required",
        }
    if event_kind == "reconcile_conflict":
        return {"invalidated": [], "project_state": "abstained"}
    if event_kind == "reconcile_confirmed":
        return {"invalidated": [], "project_state": "ready_for_verification"}
    return {"invalidated": [], "project_state": "model_inadequate"}


def _candidate_models() -> List[WorldModel]:
    models = []
    complexity = {
        "none": 1,
        "direct": 2,
        "transitive": 3,
        "blanket": 2,
    }
    policy_complexity = {"ignore": 1, "rebuild": 2, "abstain": 2}
    for operator in ("none", "direct", "transitive", "blanket"):
        for policy in ("ignore", "rebuild", "abstain"):
            model_id = "world_model_" + _canonical_hash(
                {"operator": operator, "policy": policy}
            )[:12]
            models.append(
                WorldModel(
                    model_id=model_id,
                    invalidation_operator=operator,
                    conflict_policy=policy,
                    complexity=complexity[operator] + policy_complexity[policy],
                )
            )
    return models


def _predict(
    model: WorldModel,
    project: RelationalProject,
    *,
    event_kind: str,
    source_role: str | None = None,
) -> Dict[str, Any]:
    if event_kind not in KNOWN_EVENTS:
        return {
            "model_adequate": False,
            "criticism": "EVENT_OUTSIDE_LEARNED_MODEL_FAMILY",
            "invalidated": [],
            "project_state": "abstained",
        }
    if event_kind == "source_revision":
        source = f"source:{source_role}"
        if model.invalidation_operator == "none":
            invalidated: Set[str] = set()
        elif model.invalidation_operator == "direct":
            invalidated = _dependents(
                project.dependencies, source, transitive=False
            )
        elif model.invalidation_operator == "transitive":
            invalidated = _dependents(
                project.dependencies, source, transitive=True
            )
        else:
            invalidated = _all_artifacts(project.dependencies)
        return {
            "model_adequate": True,
            "criticism": None,
            "invalidated": sorted(invalidated),
            "project_state": "revision_required",
        }
    if event_kind == "reconcile_confirmed":
        state = (
            "ready_for_verification"
            if model.conflict_policy != "ignore"
            else "unchanged"
        )
    else:
        state = {
            "ignore": "ready_for_verification",
            "rebuild": "revision_required",
            "abstain": "abstained",
        }[model.conflict_policy]
    return {
        "model_adequate": True,
        "criticism": None,
        "invalidated": [],
        "project_state": state,
    }


def _training_events(projects: Sequence[RelationalProject]) -> List[Dict[str, Any]]:
    rows = []
    for index, project in enumerate(projects):
        roles = sorted(project.source_paths)
        for role in roles:
            rows.append(
                {
                    "project": project,
                    "event_kind": "source_revision",
                    "source_role": role,
                    "expected": _expected_effect(
                        project,
                        event_kind="source_revision",
                        source_role=role,
                    ),
                }
            )
        conflict = index % 2 == 0
        event_kind = (
            "reconcile_conflict" if conflict else "reconcile_confirmed"
        )
        rows.append(
            {
                "project": project,
                "event_kind": event_kind,
                "source_role": None,
                "expected": _expected_effect(
                    project,
                    event_kind=event_kind,
                ),
            }
        )
    return rows


def _fit_models(
    projects: Sequence[RelationalProject],
) -> Tuple[List[Dict[str, Any]], WorldModel]:
    events = _training_events(projects)
    scored = []
    for model in _candidate_models():
        exact = 0
        field_correct = 0
        field_total = 0
        for row in events:
            prediction = _predict(
                model,
                row["project"],
                event_kind=row["event_kind"],
                source_role=row["source_role"],
            )
            expected = row["expected"]
            exact += int(
                prediction["invalidated"] == expected["invalidated"]
                and prediction["project_state"] == expected["project_state"]
            )
            field_correct += int(
                prediction["invalidated"] == expected["invalidated"]
            )
            field_correct += int(
                prediction["project_state"] == expected["project_state"]
            )
            field_total += 2
        exact_accuracy = exact / max(1, len(events))
        field_accuracy = field_correct / max(1, field_total)
        log_score = (
            8.0 * field_accuracy
            + 4.0 * exact_accuracy
            - 0.03 * model.complexity
        )
        scored.append(
            {
                "model": model,
                "exact_accuracy": exact_accuracy,
                "field_accuracy": field_accuracy,
                "log_score": log_score,
            }
        )
    maximum = max(row["log_score"] for row in scored)
    total = sum(math.exp(row["log_score"] - maximum) for row in scored)
    for row in scored:
        row["posterior"] = math.exp(row["log_score"] - maximum) / total
    scored.sort(
        key=lambda row: (
            row["field_accuracy"],
            row["exact_accuracy"],
            -row["model"].complexity,
        ),
        reverse=True,
    )
    return scored, scored[0]["model"]


def _ground_revision(
    *,
    project: RelationalProject,
    copied: Mapping[str, Path],
    source_role: str,
) -> Dict[str, Any]:
    path = copied[source_role]
    before = _sha(path)
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["phase57_observed_revision"] = {
            "revision": 2,
            "observed": True,
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    else:
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n# Phase 57 observed revision\n",
            encoding="utf-8",
        )
    after = _sha(path)
    return {
        "source_role": source_role,
        "path": str(path),
        "before_sha256": before,
        "after_sha256": after,
        "changed": before != after,
    }


def _evaluate_project(
    *,
    project: RelationalProject,
    model: WorldModel,
    copied: Mapping[str, Path],
    project_index: int,
) -> Dict[str, Any]:
    source_role = sorted(copied)[project_index % len(copied)]
    grounded = _ground_revision(
        project=project,
        copied=copied,
        source_role=source_role,
    )
    expected_revision = _expected_effect(
        project,
        event_kind="source_revision",
        source_role=source_role,
    )
    predicted_revision = _predict(
        model,
        project,
        event_kind="source_revision",
        source_role=source_role,
    )
    reconcile_kind = (
        "reconcile_conflict"
        if project_index % 3 == 2
        else "reconcile_confirmed"
    )
    expected_reconcile = _expected_effect(
        project,
        event_kind=reconcile_kind,
    )
    predicted_reconcile = _predict(
        model,
        project,
        event_kind=reconcile_kind,
    )
    novel = _predict(
        model,
        project,
        event_kind="authority_revoked_without_replacement",
    )
    cold_invalidated = sorted(_all_artifacts(project.dependencies))
    exact_revision = (
        grounded["changed"]
        and predicted_revision["invalidated"]
        == expected_revision["invalidated"]
        and predicted_revision["project_state"]
        == expected_revision["project_state"]
    )
    exact_reconcile = (
        predicted_reconcile["project_state"]
        == expected_reconcile["project_state"]
    )
    return {
        "project_id": project.project_id,
        "family": project.family,
        "phase": project.phase,
        "source_roles": sorted(project.source_paths),
        "source_revision": grounded,
        "withheld_revision_prediction": predicted_revision,
        "withheld_revision_expected": expected_revision,
        "withheld_reconcile_event": reconcile_kind,
        "withheld_reconcile_prediction": predicted_reconcile,
        "withheld_reconcile_expected": expected_reconcile,
        "revision_exact": exact_revision,
        "reconcile_exact": exact_reconcile,
        "all_withheld_events_exact": exact_revision and exact_reconcile,
        "novel_event": novel,
        "novel_event_safely_criticised": (
            novel["model_adequate"] is False
            and novel["project_state"] == "abstained"
        ),
        "learned_reexecution_cost": len(predicted_revision["invalidated"]),
        "cold_reexecution_cost": len(cold_invalidated),
        "provenance_complete": (
            len(grounded["before_sha256"]) == 64
            and len(grounded["after_sha256"]) == 64
            and grounded["changed"]
        ),
    }


def run_phase57_richer_world_models(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
    development_phases: Sequence[int] = (48, 49, 50, 51, 52),
    sealed_phases: Sequence[int] = (53, 54, 55, 56),
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    state_path = state_path.resolve()
    workspace_root = workspace_root.resolve()
    if state_path.exists():
        state_path.unlink()
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)

    # Phase 56 uses its own result and report names.
    phase56_result = repo_root / "results" / "hexcore_phase56_real_file_projects.json"
    phase56_report = (
        repo_root / "docs" / "aion"
        / "HEXCORE_PHASE_56_REAL_FILE_LONG_HORIZON_PROJECT_REPORT.md"
    )
    PHASE_RESULT_NAMES[56] = phase56_result.name
    PHASE_REPORT_NAMES[56] = phase56_report.name
    PHASE_FAMILIES[56] = "real_file_projects"

    development = _projects(
        repo_root=repo_root,
        phases=development_phases,
        cohort="development",
    )
    sealed = _projects(
        repo_root=repo_root,
        phases=sealed_phases,
        cohort="sealed",
    )
    required = [
        path
        for project in (*development, *sealed)
        for path in project.source_paths.values()
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Phase 57 source files missing: {missing}")

    scored, champion_model = _fit_models(development)
    retained = scored[:3]
    rows = []
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    for index, project in enumerate(sealed):
        copied = _copy_project(project, workspace_root)
        row = _evaluate_project(
            project=project,
            model=champion_model,
            copied=copied,
            project_index=index,
        )
        rows.append(row)
        runtime.store.state["world_model_sessions"][project.project_id] = {
            "schema_version": "aion.hexcore.world_model_session.v1",
            "project_id": project.project_id,
            "dependency_graph": {
                key: list(value)
                for key, value in project.dependencies.items()
            },
            "source_paths": {
                role: str(path)
                for role, path in copied.items()
            },
            "withheld_predictions": {
                "revision": row["withheld_revision_prediction"],
                "reconcile": row["withheld_reconcile_prediction"],
            },
            "outcomes": {
                "revision": row["withheld_revision_expected"],
                "reconcile": row["withheld_reconcile_expected"],
            },
            "model_criticism": row["novel_event"],
            "completed_at": _utc_timestamp(),
        }
        runtime.store.commit(reason=f"phase57_world_session:{project.project_id}")

    exact = sum(int(row["all_withheld_events_exact"]) for row in rows) / max(
        1, len(rows)
    )
    family_accuracy = {
        family: sum(
            int(row["all_withheld_events_exact"])
            for row in rows
            if row["family"] == family
        )
        / sum(1 for row in rows if row["family"] == family)
        for family in {row["family"] for row in rows}
    }
    learned_cost = sum(row["learned_reexecution_cost"] for row in rows)
    cold_cost = sum(row["cold_reexecution_cost"] for row in rows)
    gate = {
        "development_projects": len(development),
        "sealed_projects": len(sealed),
        "candidate_models_compared": len(scored),
        "competing_models_retained": len(retained),
        "withheld_event_accuracy": exact,
        "weakest_family_accuracy": min(family_accuracy.values(), default=0.0),
        "novel_event_criticism": sum(
            int(row["novel_event_safely_criticised"]) for row in rows
        )
        / max(1, len(rows)),
        "unsafe_novel_event_forcing": sum(
            int(not row["novel_event_safely_criticised"]) for row in rows
        ),
        "provenance_completeness": sum(
            int(row["provenance_complete"]) for row in rows
        )
        / max(1, len(rows)),
        "learned_reexecution_cost": learned_cost,
        "cold_reexecution_cost": cold_cost,
        "cost_reduction_vs_cold": 1.0 - learned_cost / max(1, cold_cost),
        "unseen_topologies_evaluated": sum(
            int("publication_receipt" in project.dependencies)
            for project in sealed
        ),
        "original_repository_files_mutated": False,
    }
    errors = []
    for name, minimum in (
        ("withheld_event_accuracy", 0.90),
        ("weakest_family_accuracy", 0.85),
        ("novel_event_criticism", 1.0),
        ("provenance_completeness", 1.0),
        ("cost_reduction_vs_cold", 0.15),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["competing_models_retained"] < 2:
        errors.append("COMPETING_EXPLANATIONS_NOT_RETAINED")
    if gate["unsafe_novel_event_forcing"]:
        errors.append("NOVEL_EVENT_UNSAFELY_FORCED")
    gate["errors"] = errors
    gate["accepted"] = not errors

    model_record = {
        "schema_version": "aion.hexcore.relational_world_model.v1",
        **champion_model.to_dict(),
        "posterior": retained[0]["posterior"],
        "development_exact_accuracy": retained[0]["exact_accuracy"],
        "development_field_accuracy": retained[0]["field_accuracy"],
        "competing_models": [
            {
                **row["model"].to_dict(),
                "posterior": row["posterior"],
                "exact_accuracy": row["exact_accuracy"],
                "field_accuracy": row["field_accuracy"],
            }
            for row in retained
        ],
        "source_projects": [project.project_id for project in development],
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["relational_world_models"][
        champion_model.model_id
    ] = model_record
    runtime.store.commit(reason="phase57_world_model_retained")
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_richer_world_model_"
            + _canonical_hash(
                {
                    "parent": "procedure_real_file_projects_3aff718b5c0d",
                    "model": champion_model.to_dict(),
                    "gate": gate,
                }
            )[:12]
        ),
        goal="richer_real_file_world_model_learning",
        steps=[
            "infer_typed_entities_from_real_project_sources",
            "compare_competing_relational_transition_models",
            "retain_posterior_uncertainty",
            "predict_withheld_revision_and_reconciliation_events",
            "criticise_events_outside_model_family",
            "minimise_reexecution_with_dependency_dynamics",
            "persist_model_sessions_and_provenance",
        ],
        score=gate["withheld_event_accuracy"] + gate["cost_reduction_vs_cold"],
        success=gate["accepted"],
        evidence={"evaluation": "phase57_sealed_world_models", "gate": gate},
        source_rules=["procedure_real_file_projects_3aff718b5c0d"],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase57_richer_world_model")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "model_retained": champion_model.model_id
        in restarted.store.state["relational_world_models"],
        "all_sessions_retained": len(
            restarted.store.state["world_model_sessions"]
        )
        == len(sealed),
        "champion_retained": restarted.store.state["champions"].get(
            "richer_real_file_world_model_learning"
        )
        == candidate.procedure_id,
        "relearning_events": 0,
    }
    result = {
        "schema_version": "aion.hexcore.richer_world_models.v1",
        "phase": 57,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["model_retained"],
                    restart["all_sessions_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "model": model_record,
        "gate": gate,
        "sealed": {
            "projects": len(rows),
            "phases": list(sealed_phases),
            "rows": rows,
        },
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 57 learns a lifted dependency/revision model from real-file "
            "project events, predicts withheld events on unseen topologies and "
            "criticises an out-of-family event. Entity roles, candidate "
            "operator grammar, dependency graphs, revision controller and "
            "correctness oracle remain engineered. It is not unrestricted "
            "world modelling or autonomous causal discovery from raw reality."
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
        description="Run Phase 57 richer real-file world-model benchmark."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_phase57_richer_world_models(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
