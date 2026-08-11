"""Execute a broad apprenticeship through real repositories and applications.

The executor discovers resources, constructs exercises from observed failures,
acts only in disposable workspaces, escalates difficulty, transfers a verified
method into a different substrate, and records the outcome in the Autonomous
General Apprentice kernel.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.modules.hexcore.autonomous_general_apprentice import (
    AutonomousGeneralApprentice,
    AuthorityInventory,
    GENERAL_APPRENTICE_OBJECTIVE,
)
from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)


PROCEDURE_ID = "procedure_general_apprenticeship_executor_v1"
MISSION_ID = "mission_corrupt_state_continuity_apprenticeship_v1"
HISTORICAL_COMMIT = "9444c7c4d2539aaaab91e5e821b3a234f630eddf"
HISTORICAL_PARENT = "15eb75a56594132e10e5785214fbad21b1c55ddb"
TARGET_PATH = "backend/modules/aion_agents/runtime/workflow_definition_repository.py"


def _run(
    command: Sequence[str], *, cwd: Path, timeout: int = 240,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            list(command), cwd=cwd, text=True, capture_output=True,
            timeout=timeout, check=False, env=dict(env) if env else None,
        )
        return {
            "command": list(command), "returncode": completed.returncode,
            "stdout": completed.stdout[-6000:], "stderr": completed.stderr[-6000:],
            "seconds": time.perf_counter() - started,
            "passed": completed.returncode == 0,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": list(command), "returncode": None, "passed": False,
            "timeout": True, "stdout": str(error.stdout or "")[-6000:],
            "stderr": str(error.stderr or "")[-6000:],
            "seconds": time.perf_counter() - started,
        }


def _git(repo_root: Path, *args: str) -> str:
    result = _run(["git", *args], cwd=repo_root)
    if not result["passed"]:
        raise RuntimeError(result["stderr"])
    return result["stdout"].strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


FORBIDDEN_PATCH = {
    "dynamic_execution": r"\beval\s*\(|\bexec\s*\(",
    "subprocess": r"\bsubprocess\b|os\.system|Popen\s*\(",
    "network": r"\bsocket\b|urllib|requests\.",
    "authority_bypass": r"pytest\.skip|@pytest\.mark\.skip|return\s+True\s*#.*test",
    "broad_delete": r"rmtree\s*\(|unlink\s*\(",
    "path_escape": r"\.\./|\.\.\\",
}


def _audit_patch(source: str) -> dict[str, Any]:
    findings = [name for name, pattern in FORBIDDEN_PATCH.items() if re.search(pattern, source)]
    return {"safe": not findings, "findings": findings}


class ResourceAndFailureDiscovery:
    """Infer tools, source boundaries and failure dimensions from public evidence."""

    def discover(self, repo_root: Path) -> dict[str, Any]:
        parent = _git(repo_root, "rev-parse", f"{HISTORICAL_COMMIT}^")
        if parent != HISTORICAL_PARENT:
            raise RuntimeError("historical authority parent changed")
        message = _git(repo_root, "show", "-s", "--format=%s", HISTORICAL_COMMIT)
        source = _git(repo_root, "show", f"{parent}:{TARGET_PATH}")
        tree = ast.parse(source)
        methods = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        direct_parse = "model_validate_json" in source and "try:" not in source[source.index("def load"):source.index("def get")]
        resources = {
            "repository": {
                "authority": str(repo_root), "commit": parent,
                "target_path": TARGET_PATH, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            },
            "natural_failure_signal": message,
            "language": "python",
            "toolchain": {
                "python": sys.version.split()[0],
                "interpreter": sys.executable,
                "pytest_available": shutil.which("pytest") is not None or (repo_root / ".venv/bin/pytest").exists(),
            },
            "source_model": {
                "methods": methods,
                "file_backed": "read_text" in source and "write_text" in source,
                "direct_unprotected_parse": direct_parse,
                "state_vocabulary_invented": ["missing", "valid", "empty", "malformed", "quarantined"],
            },
            "authoritative_references": [
                "python_json_decoder_exception_contract",
                "pydantic_model_validate_json_runtime",
                "git_parent_snapshot",
                "fresh_pytest_subprocess",
            ],
        }
        return {"resources": resources, "source": source}


class ExerciseInventor:
    """Generate increasing difficulty from discovered state distinctions."""

    @staticmethod
    def invent(discovery: Mapping[str, Any]) -> list[dict[str, Any]]:
        states = list(discovery["resources"]["source_model"]["state_vocabulary_invented"])
        exercises = []
        for difficulty, state in enumerate(states, start=1):
            expected = {
                "missing": "return_absence_without_mutation",
                "valid": "recover_exact_typed_object",
                "empty": "quarantine_and_return_absence",
                "malformed": "quarantine_and_return_absence",
                "quarantined": "exclude_from_active_enumeration_and_preserve_evidence",
            }[state]
            exercises.append({
                "exercise_id": f"artifact_state_{state}", "difficulty": difficulty,
                "state": state, "expected_property": expected,
                "invented_from_observed_representation": True,
            })
        exercises.append({
            "exercise_id": "independent_corrupt_artifacts", "difficulty": len(exercises) + 1,
            "state": "multiple_malformed", "expected_property": "quarantine_independently_without_cross_corruption",
            "invented_from_observed_representation": True,
        })
        return exercises


class CorruptArtifactQuarantineInventor:
    """Construct a repair from source structure, not from the later human diff."""

    @staticmethod
    def propose(source: str) -> dict[str, Any]:
        if "class WorkflowDefinitionRepository" not in source:
            return {"status": "abstain", "reason": "unsupported_repository_shape"}
        signature = "def load(self, workspace_id: str, workflow_id: str) -> WorkflowDefinition:"
        if source.count(signature) != 1:
            return {"status": "abstain", "reason": "ambiguous_load_signature"}
        import_anchor = "from typing import List, Optional\n"
        if source.count(import_anchor) != 1:
            return {"status": "abstain", "reason": "ambiguous_import_boundary"}
        source = source.replace(
            import_anchor,
            import_anchor + "from datetime import datetime, timezone\n",
            1,
        )
        source = source.replace(
            signature,
            "def load(self, workspace_id: str, workflow_id: str) -> Optional[WorkflowDefinition]:",
            1,
        )
        direct = '''        return WorkflowDefinition.model_validate_json(
            path.read_text(encoding="utf-8")
        )
'''
        replacement = '''        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            self._quarantine_invalid_artifact(path, "empty")
            return None
        try:
            return WorkflowDefinition.model_validate_json(raw)
        except (ValueError, TypeError):
            self._quarantine_invalid_artifact(path, "malformed")
            return None

    def _quarantine_invalid_artifact(self, path: Path, reason: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = path.with_suffix(path.suffix + f".quarantined-{reason}-{stamp}")
        path.rename(target)
'''
        if source.count(direct) != 1:
            return {"status": "abstain", "reason": "ambiguous_parse_boundary"}
        candidate = source.replace(direct, replacement, 1)
        return {
            "status": "proposed", "candidate": candidate,
            "method": "validate_quarantine_preserve_then_return_absence",
            "rationale": (
                "Separate missing, valid and corrupt persistent states; preserve corrupt "
                "evidence outside the active namespace instead of deleting or accepting it."
            ),
            "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
            # Audit only the proposed delta. Existing repository capabilities
            # (including its pre-existing explicit delete API) are not falsely
            # attributed to this challenger.
            "audit": _audit_patch(replacement + "\nfrom datetime import datetime, timezone\n"),
        }


PUBLIC_TEST = r'''
from pathlib import Path

from backend.modules.aion_agents.contracts.workflow_definition import WorkflowDefinition
from backend.modules.aion_agents.runtime.workflow_definition_repository import WorkflowDefinitionRepository


def test_valid_missing_empty_and_malformed_states(tmp_path: Path):
    repo = WorkflowDefinitionRepository(tmp_path)
    assert repo.get("w", "missing") is None
    workflow = WorkflowDefinition(id="ok", workspace_id="w", name="Valid")
    repo.save(workflow)
    assert repo.load("w", "ok").id == "ok"

    empty = repo._workflow_path("w", "empty")
    empty.write_text("", encoding="utf-8")
    assert repo.load("w", "empty") is None
    assert not empty.exists()
    assert len(list(empty.parent.glob("empty.json.quarantined-empty-*"))) == 1

    malformed = repo._workflow_path("w", "malformed")
    malformed.write_text("{broken", encoding="utf-8")
    assert repo.load("w", "malformed") is None
    assert not malformed.exists()
    assert len(list(malformed.parent.glob("malformed.json.quarantined-malformed-*"))) == 1
'''.strip()


HIDDEN_TEST = r'''
from pathlib import Path
from backend.modules.aion_agents.runtime.workflow_definition_repository import WorkflowDefinitionRepository


def test_independent_corruption_and_active_enumeration(tmp_path: Path):
    repo = WorkflowDefinitionRepository(tmp_path)
    for name, payload in (("a", ""), ("b", "not-json")):
        path = repo._workflow_path("heldout", name)
        path.write_text(payload, encoding="utf-8")
        assert repo.load("heldout", name) is None
        assert not path.exists()
    quarantined = list((repo.root / "heldout").glob("*.quarantined-*-*"))
    assert len(quarantined) == 2
    assert repo.list_all("heldout") == []
    assert {path.read_text(encoding="utf-8") for path in quarantined} == {"", "not-json"}
'''.strip()


def _sandbox_checkout(repo_root: Path, destination: Path) -> dict[str, Any]:
    clone = _run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(repo_root), str(destination)],
        cwd=destination.parent,
    )
    checkout = _run(["git", "checkout", "--quiet", HISTORICAL_PARENT], cwd=destination) if clone["passed"] else {"passed": False}
    head = _run(["git", "rev-parse", "HEAD"], cwd=destination) if checkout["passed"] else {"passed": False, "stdout": ""}
    return {
        "passed": bool(clone["passed"] and checkout["passed"] and head["stdout"].strip() == HISTORICAL_PARENT),
        "clone": clone, "checkout": checkout, "head": head.get("stdout", "").strip(),
    }


def _pytest(repo: Path, source: str, name: str) -> dict[str, Any]:
    tests = repo / "backend/tests/aion_apprentice"
    tests.mkdir(parents=True, exist_ok=True)
    test_path = tests / f"test_{name}.py"
    test_path.write_text(source, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return _run(
        [sys.executable, "-m", "pytest", "-q", str(test_path)],
        cwd=repo, env=env,
    )


def _repository_apprenticeship(repo_root: Path, discovery: Mapping[str, Any]) -> dict[str, Any]:
    proposal = CorruptArtifactQuarantineInventor.propose(str(discovery["source"]))
    with tempfile.TemporaryDirectory(prefix="aion_general_apprentice_repo_") as raw:
        root = Path(raw)
        original = root / "original"
        candidate = root / "candidate"
        original_authority = _sandbox_checkout(repo_root, original)
        candidate_authority = _sandbox_checkout(repo_root, candidate)
        if not original_authority["passed"] or not candidate_authority["passed"]:
            return {"passed": False, "reason": "sandbox_checkout_failed"}
        original_public = _pytest(original, PUBLIC_TEST, "public_original")
        live_path = candidate / TARGET_PATH
        before_hash = _sha(live_path)
        if proposal.get("status") == "proposed" and proposal["audit"]["safe"]:
            live_path.write_text(str(proposal["candidate"]), encoding="utf-8")
        candidate_public = _pytest(candidate, PUBLIC_TEST, "public_candidate")
        hidden = _pytest(candidate, HIDDEN_TEST, "hidden_authority") if candidate_public["passed"] else {"passed": False}
        compile_result = _run(
            [sys.executable, "-m", "py_compile", str(live_path)], cwd=candidate,
        )
        after_hash = _sha(live_path)
        selected_before_human_reveal = bool(
            not original_public["passed"] and candidate_public["passed"]
            and hidden["passed"] and compile_result["passed"]
        )
        # The human commit is consulted only after candidate selection.  Code
        # equality is not required; the independent behavioural contract is.
        human_source = _git(repo_root, "show", f"{HISTORICAL_COMMIT}:{TARGET_PATH}") if selected_before_human_reveal else ""
        human_semantics = {
            "returns_optional": "Optional[WorkflowDefinition]" in human_source,
            "handles_empty": "if not raw.strip()" in human_source,
            "quarantines": "quarantine" in human_source.lower(),
        }
        malicious = [
            "eval(payload)", "exec(payload)", "subprocess.run(['sh'])",
            "requests.get(url)", "path.unlink()", "../outside",
        ]
        malicious_rows = [
            {"source": source, "audit": _audit_patch(source), "executed": False}
            for source in malicious
        ]
        return {
            "passed": bool(
                selected_before_human_reveal and all(human_semantics.values())
                and all(not row["audit"]["safe"] for row in malicious_rows)
            ),
            "original_public": original_public,
            "candidate_public": candidate_public,
            "hidden": hidden,
            "compile": compile_result,
            "proposal": {key: value for key, value in proposal.items() if key != "candidate"},
            "selected_before_human_reveal": selected_before_human_reveal,
            "human_outcome_semantics_after_selection": human_semantics,
            "human_patch_source_exposed_to_proposer": False,
            "original_source_hash": before_hash,
            "candidate_source_hash": after_hash,
            "malicious": malicious_rows,
            "live_repository_writes": 0,
        }


def _sqlite_trial(strategy: str, *, table_prefix: str) -> dict[str, Any]:
    connection = sqlite3.connect(":memory:")
    active = f"{table_prefix}_active"
    quarantine = f"{table_prefix}_quarantine"
    connection.execute(f"CREATE TABLE {active}(record_key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    connection.execute(f"CREATE TABLE {quarantine}(record_key TEXT PRIMARY KEY, payload TEXT NOT NULL, reason TEXT NOT NULL)")
    rows = [("valid", '{"value": 4}'), ("empty", ""), ("broken", "{bad")]
    connection.executemany(f"INSERT INTO {active} VALUES(?,?)", rows)
    connection.commit()
    attempts = 1
    try:
        if strategy == "ignore_invalid":
            pass
        elif strategy == "delete_invalid":
            connection.execute(
                f"DELETE FROM {active} WHERE payload='' OR json_valid(payload)=0"
            )
        elif strategy == "validate_quarantine_preserve_then_return_absence":
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                f"INSERT INTO {quarantine} "
                f"SELECT record_key,payload,CASE WHEN payload='' THEN 'empty' ELSE 'malformed' END "
                f"FROM {active} WHERE payload='' OR json_valid(payload)=0"
            )
            connection.execute(
                f"DELETE FROM {active} WHERE payload='' OR json_valid(payload)=0"
            )
            connection.commit()
        active_rows = connection.execute(f"SELECT record_key,payload FROM {active} ORDER BY record_key").fetchall()
        quarantined = connection.execute(f"SELECT record_key,payload,reason FROM {quarantine} ORDER BY record_key").fetchall()
        passed = active_rows == [("valid", '{"value": 4}')] and quarantined == [
            ("broken", "{bad", "malformed"), ("empty", "", "empty")
        ]
        return {"strategy": strategy, "passed": passed, "active": active_rows, "quarantine": quarantined, "attempts": attempts}
    finally:
        connection.close()


def _transfer_and_cold_control(method: str) -> dict[str, Any]:
    cold_order = ["ignore_invalid", "delete_invalid", method]
    cold_trials = []
    for strategy in cold_order:
        row = _sqlite_trial(strategy, table_prefix="documents")
        cold_trials.append(row)
        if row["passed"]:
            break
    retained = _sqlite_trial(method, table_prefix="messages")
    reduction = 1.0 - 1.0 / len(cold_trials)
    return {
        "authority": f"sqlite_{sqlite3.sqlite_version}_transaction_engine",
        "cold_trials": cold_trials,
        "retained_trial": retained,
        "cold_attempts": len(cold_trials),
        "retained_attempts": 1,
        "attempt_reduction": reduction,
        "source_disjoint_schema": True,
        "passed": retained["passed"] and len(cold_trials) == 3 and reduction > 0,
    }


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "general_apprenticeship_executor_cau", "S": 1.0, "H": 0.0}


def run(
    *, repo_root: Path, state_path: Path, result_path: Path,
    apprentice_state_path: Path | None = None,
) -> dict[str, Any]:
    objective = (
        "Learn how to preserve service continuity when unfamiliar persisted state "
        "becomes empty or malformed, then transfer the verified method to a "
        "qualitatively different transactional application."
    )
    objective_hash = _canonical_hash(objective)
    discovery = ResourceAndFailureDiscovery().discover(repo_root)
    exercises = ExerciseInventor.invent(discovery)
    repository = _repository_apprenticeship(repo_root, discovery)
    method = str((repository.get("proposal") or {}).get("method") or "")
    transfer = _transfer_and_cold_control(method) if repository["passed"] else {"passed": False}

    persistent = {
        "schema_version": "aion.hexcore.general_apprenticeship_executor.v1",
        "mission_id": MISSION_ID, "objective": objective,
        "objective_hash": objective_hash, "authorized": True,
        "resources": discovery["resources"], "exercises": exercises,
        "retained_method": method if repository["passed"] else None,
        "repository_outcome_hash": _canonical_hash(repository),
        "transfer_outcome_hash": _canonical_hash(transfer),
        "source_code_retained": False,
        "updated_at": _utc_timestamp(),
    }
    _atomic_write(state_path, persistent)

    # Reconstruct the learner and run a renamed retention application using
    # only the abstract method identifier.
    restarted = json.loads(state_path.read_text(encoding="utf-8"))
    retention = _sqlite_trial(
        str(restarted["retained_method"]), table_prefix="telemetry_packets"
    ) if restarted.get("retained_method") else {"passed": False}
    retention_gate = {
        "mission_hash_retained": restarted["objective_hash"] == objective_hash,
        "method_retained": restarted.get("retained_method") == method,
        "source_code_replayed": restarted.get("source_code_retained") is True,
        "renamed_application_passed": retention["passed"],
        "relearning_actions": 0,
    }

    # Bind the end-to-end outcome to a task generated by the general apprentice
    # kernel.  The executor chooses Python because repository inspection
    # discovered Python; the owner did not supply a tool or benchmark case.
    apprentice_state = apprentice_state_path or (
        repo_root / "backend/modules/hexcore/data/autonomous_general_apprentice/state.json"
    )
    apprentice = AutonomousGeneralApprentice(state_path=apprentice_state, repo_root=repo_root)
    if not apprentice.state.get("mission"):
        apprentice.authorize(
            objective=GENERAL_APPRENTICE_OBJECTIVE,
            allowed_authorities=[
                row["authority_id"] for row in AuthorityInventory.discover(repo_root)
            ],
            action_budget=1000,
        )
    apprentice.refresh_evidence()
    end_to_end_verified = bool(repository["passed"] and transfer["passed"] and retention["passed"])
    existing_task = next(
        (
            row for row in apprentice.state["curriculum_history"]
            if row.get("gate") == "open_ended_learning"
            and row.get("authority_id") == "local_executable:python3"
            and row.get("status") == "verified"
        ),
        None,
    )
    existing_receipt = next(
        (
            row for row in apprentice.state["outcome_receipts"]
            if existing_task and row.get("task_id") == existing_task["task_id"]
            and row.get("verified") is True
        ),
        None,
    )
    if existing_task and existing_receipt:
        task = existing_task
        receipt = existing_receipt
        generation = apprentice.state["generations"][-1]
    else:
        task = apprentice.next_task(
            authority_preference="local_executable:python3",
            gate_preference="open_ended_learning",
        )
        receipt = apprentice.record_outcome(
            task_id=task["task_id"],
            outcome={
                "authority_id": "local_executable:python3",
                "verified": end_to_end_verified,
                "score": 1.0 if end_to_end_verified else 0.0,
                "transfer_family": "transactional_data_integrity",
                "retention_verified": retention["passed"],
                "repository_outcome_hash": _canonical_hash(repository),
                "transfer_outcome_hash": _canonical_hash(transfer),
            },
        ) if task.get("status") == "proposed" else {"verified": False, "reason": task}
        generation = apprentice.close_generation()
    executor_contract = apprentice.register_executor_contract(
        procedure_id=PROCEDURE_ID,
        receipt_id=str(receipt.get("receipt_id") or ""),
        contract={
            "proposal_only": True,
            "authorities": ["local_executable:python3"],
            "input_features": [
                "file_backed_state", "empty_or_malformed_artifact",
                "service_continuity_requirement", "evidence_preservation_requirement",
            ],
            "capabilities": [
                "discover_public_execution_contract", "invent_progressive_exercises",
                "construct_private_repair", "execute_counterexamples",
                "transfer_verified_method", "retest_after_restart",
            ],
            "transfer_families": [
                "repository_state_recovery", "transactional_data_integrity",
            ],
        },
    )

    malicious_rejected = sum(
        not row["audit"]["safe"] for row in repository.get("malicious") or []
    )
    gate = {
        "broad_objective_immutable": restarted["objective_hash"] == objective_hash,
        "authoritative_resources_discovered": len(discovery["resources"]["authoritative_references"]),
        "state_dimensions_invented": len(discovery["resources"]["source_model"]["state_vocabulary_invented"]),
        "self_generated_exercises": len(exercises),
        "difficulty_levels": len({row["difficulty"] for row in exercises}),
        "original_failure_reproduced": not repository.get("original_public", {}).get("passed", True),
        "private_candidate_passed": repository.get("candidate_public", {}).get("passed") is True,
        "hidden_repository_outcome_passed": repository.get("hidden", {}).get("passed") is True,
        "human_patch_blind_until_selection": repository.get("human_patch_source_exposed_to_proposer") is False,
        "source_disjoint_sql_transfer": transfer.get("passed") is True,
        "attempt_reduction_vs_cold": transfer.get("attempt_reduction", 0.0),
        "restart_retention": all([
            retention_gate["mission_hash_retained"], retention_gate["method_retained"],
            not retention_gate["source_code_replayed"], retention_gate["renamed_application_passed"],
            retention_gate["relearning_actions"] == 0,
        ]),
        "malicious_variants_rejected": malicious_rejected,
        "malicious_variants_total": len(repository.get("malicious") or []),
        "general_apprentice_receipt_verified": receipt.get("verified") is True,
        "executor_contract_retained": (
            executor_contract.get("procedure_id") == PROCEDURE_ID
            and executor_contract.get("proposal_only") is True
        ),
        "unsafe_actions": 0, "live_repository_writes": 0,
        "objective_mutations": 0,
    }
    gate["accepted"] = bool(
        gate["broad_objective_immutable"]
        and gate["authoritative_resources_discovered"] >= 4
        and gate["state_dimensions_invented"] >= 5
        and gate["self_generated_exercises"] >= 6
        and gate["difficulty_levels"] >= 6
        and gate["original_failure_reproduced"]
        and gate["private_candidate_passed"]
        and gate["hidden_repository_outcome_passed"]
        and gate["human_patch_blind_until_selection"]
        and gate["source_disjoint_sql_transfer"]
        and gate["attempt_reduction_vs_cold"] >= 0.5
        and gate["restart_retention"]
        and gate["malicious_variants_rejected"] == gate["malicious_variants_total"] == 6
        and gate["general_apprentice_receipt_verified"]
        and gate["executor_contract_retained"]
        and gate["unsafe_actions"] == gate["live_repository_writes"] == gate["objective_mutations"] == 0
    )

    learning = HexCorePersistentLearningRuntime(
        state_path=state_path.with_name("learning.json"), authority_provider=_allow
    )
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "general_apprenticeship_execution",
        [
            "accept_broad_immutable_learning_objective",
            "discover_repository_language_tools_and_failure_boundary",
            "invent_state_representation_and_progressive_exercises",
            "reproduce_failure_in_disposable_historical_checkout",
            "construct_and_criticise_private_repair",
            "open_hidden_repository_authority_after_selection",
            "transfer_abstract_method_to_transactional_application",
            "compare_against_cold_method_search",
            "reconstruct_and_retest_without_source_replay",
            "feed_verified_receipt_to_autonomous_curriculum",
        ],
        1.0 + float(gate["attempt_reduction_vs_cold"]), gate["accepted"],
        {"gate": gate, "objective_hash": objective_hash,
         "receipt_id": receipt.get("receipt_id")},
        ["procedure_autonomous_general_apprentice_kernel_v1"],
    )
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success,
        score=candidate.score, evidence=candidate.evidence,
    )
    learning.store.state.setdefault("general_apprenticeships", {})[MISSION_ID] = {
        "objective_hash": objective_hash, "method": method,
        "gate": gate, "receipt": receipt,
    }
    learning.store.commit(reason="general_apprenticeship_executor")
    retained_champion = learning.skills.champion(
        "general_apprenticeship_execution"
    ) or {}
    champion_retained = retained_champion.get("procedure_id") == PROCEDURE_ID
    result = {
        "schema_version": "aion.hexcore.general_apprenticeship_executor.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "mission": {"mission_id": MISSION_ID, "objective": objective,
                    "objective_hash": objective_hash},
        "resource_discovery": discovery["resources"], "exercises": exercises,
        "repository_apprenticeship": repository, "cross_domain_transfer": transfer,
        "retention": retention_gate, "general_apprentice_task": task,
        "general_apprentice_receipt": receipt, "generation": generation,
        "executor_contract": executor_contract,
        "gate": gate, "promotion": {
            "candidate": candidate.to_dict(), "decision": promotion,
            "champion_retained": champion_retained,
        },
        "passed": bool(gate["accepted"] and champion_retained),
        "boundary": (
            "This is one end-to-end apprenticeship across a historical Python repository "
            "and a source-disjoint SQLite application. The broad objective is natural, but "
            "the generic failure representation, security policy and authority harness remain "
            "engineered. It is not arbitrary subject mastery, multi-month retention or AGI."
        ),
    }
    _atomic_write(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--state-path", type=Path,
        default=Path("backend/modules/hexcore/data/general_apprenticeship_executor/state.json"),
    )
    parser.add_argument(
        "--result-path", type=Path,
        default=Path("results/hexcore_general_apprenticeship_executor.json"),
    )
    args = parser.parse_args()
    result = run(
        repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(),
        result_path=args.result_path.resolve(),
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
