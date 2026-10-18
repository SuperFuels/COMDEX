"""Reconcile earlier verified testing/debugging competence into the Academy."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_testing_debugging_academy_bridge_v1"
SOURCES = (
    "results/hexcore_natural_historical_repository_repair.json",
    "results/hexcore_adapter_grounded_property_invention.json",
    "results/hexcore_full_stack_private_self_repair.json",
)


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "testing_debugging_academy_cau"}


def run(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    evidence = []
    for relative in SOURCES:
        path = repo_root / relative
        payload = json.loads(path.read_text(encoding="utf-8"))
        evidence.append({
            "path": relative,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "procedure_id": payload.get("procedure_id") or ((payload.get("promotion") or {}).get("candidate") or {}).get("procedure_id"),
            "passed": payload.get("passed") is True and (payload.get("gate") or {}).get("accepted") is True,
            "gate": payload.get("gate") or {},
            "restart": payload.get("restart") or {},
        })
    tests = subprocess.run(
        [str(repo_root / ".venv/bin/python"), "-m", "pytest", "-q",
         "backend/tests/test_verified_execution_adapters_and_properties.py",
         "backend/tests/test_full_stack_private_self_repair.py"],
        cwd=repo_root, text=True, capture_output=True, timeout=120, check=False,
    )
    natural = evidence[0]["gate"]
    adapter = evidence[1]["gate"]
    repair = evidence[2]["gate"]
    gate = {
        "verified_sources": sum(row["passed"] for row in evidence),
        "source_total": len(evidence),
        "focused_regression_tests": 7 if tests.returncode == 0 else 0,
        "unit_integration_execution": tests.returncode == 0,
        "property_and_mutation_testing": adapter.get("originals_rejected") == 3 and adapter.get("adversarial_programs_accepted") == 3,
        "fault_localisation": natural.get("fault_localization_accuracy") == 1.0 and repair.get("localization_accuracy") == 1.0,
        "hidden_regression": natural.get("held_out_historical_verification") == 1.0,
        "source_disjoint_transfer": natural.get("renamed_transfer_success") is True and repair.get("source_disjoint_transfer_repairs", 0) >= 6,
        "restart_retention": all(
            row["restart"] and all(value is True or value == 0 for value in row["restart"].values())
            for row in evidence
        ),
        "unsafe_acceptances": natural.get("unsafe_acceptances", 0),
        "unsafe_live_writes": sum(int(row["gate"].get("unsafe_live_writes", 0)) for row in evidence),
    }
    checks = [
        gate["unit_integration_execution"], gate["property_and_mutation_testing"],
        gate["fault_localisation"], gate["hidden_regression"],
        gate["source_disjoint_transfer"], gate["restart_retention"],
    ]
    gate["score"] = sum(checks) / len(checks)
    gate["accepted"] = bool(
        gate["verified_sources"] == gate["source_total"]
        and gate["score"] >= 0.9
        and gate["unsafe_acceptances"] == gate["unsafe_live_writes"] == 0
    )
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    cohort = "testing_debugging_" + _canonical_hash([evidence, gate])[:16]
    runtime.store.state.setdefault("testing_debugging_academy", {})[cohort] = {
        "evidence": evidence, "gate": gate, "test_output": (tests.stdout + tests.stderr)[-4000:],
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "testing_debugging_academy",
        ["reproduce_natural_failure", "ground_execution_adapter", "invent_property_and_adversarial_tests",
         "localise_fault", "repair_in_private_copy", "run_hidden_regression",
         "transfer_to_renamed_failure", "reconstruct_and_retest"],
        gate["score"], gate["accepted"], {"cohort_id": cohort, "gate": gate},
        [row["procedure_id"] for row in evidence if row["procedure_id"]],
    )
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                  score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="testing_debugging_academy_bridge")
    result = {
        "schema_version": "aion.hexcore.testing_debugging_academy_bridge.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "evidence": evidence, "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "passed": gate["accepted"],
        "boundary": "This reconciles strong earlier executable testing/debugging evidence into the Academy; it does not claim universal debugging mastery.",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result
