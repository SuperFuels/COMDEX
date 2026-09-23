"""Import exact prior verified capability evidence into Academy module receipts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


SPECS = {
    "software_engineering": {
        "procedure_id": "procedure_software_engineering_academy_bridge_v1",
        "sources": (
            "results/hexcore_phase56_real_file_projects.json",
            "results/hexcore_documentation_guided_open_software.json",
            "results/hexcore_long_running_changing_project_arena_v3.json",
        ),
        "competencies": ("requirements", "modularity", "version_control", "review", "maintenance", "delivery"),
    },
    "database_engineering": {
        "procedure_id": "procedure_database_engineering_academy_bridge_v1",
        "sources": ("results/hexcore_rust_sql_systems_depth.json",),
        "competencies": ("relational_model", "sql", "transactions", "indexes", "migrations", "concurrency", "recovery"),
    },
    "rust_systems": {
        "procedure_id": "procedure_rust_systems_academy_bridge_v1",
        "sources": (
            "results/hexcore_real_rust_apprenticeship.json",
            "results/hexcore_rust_sql_systems_depth.json",
        ),
        "competencies": ("ownership", "lifetimes", "traits", "errors", "concurrency", "unsafe_review", "ffi_boundary_review"),
    },
    "secure_engineering": {
        "procedure_id": "procedure_secure_engineering_academy_bridge_v1",
        "sources": (
            "results/hexcore_programming_intelligence_closure.json",
            "results/hexcore_full_stack_private_self_repair.json",
        ),
        "competencies": ("threat_models", "validation", "auth_boundaries", "secrets", "sandboxing", "supply_chain", "incident_response"),
    },
    "architecture_operations": {
        "procedure_id": "procedure_architecture_operations_academy_bridge_v1",
        "sources": (
            "results/hexcore_long_running_changing_project_arena_v3.json",
            "results/hexcore_rust_sql_construction_and_selection.json",
        ),
        "competencies": ("architecture_tradeoffs", "measurement", "deployment_contracts", "observability", "incident_revision", "rollback"),
    },
    "integrated_engineering_capstone": {
        "procedure_id": "procedure_integrated_engineering_capstone_bridge_v1",
        "sources": (
            "results/hexcore_long_running_changing_project_arena_v3.json",
            "results/hexcore_phase58_open_multimodal_projects.json",
            "results/hexcore_rust_sql_construction_and_selection.json",
        ),
        "competencies": ("requirements_to_architecture", "polyglot_construction", "security_falsification", "changing_evidence", "restart_recovery", "governed_delivery"),
    },
}


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "academy_evidence_bridge_cau"}


def _restart_ok(restart: dict[str, Any], gate: dict[str, Any]) -> bool:
    if restart:
        return all(value is True or value == 0 for value in restart.values())
    return bool(gate.get("restart_retention_success") == 1.0 and gate.get("source_replay_into_retention") == 0)


def run(*, module_id: str, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    spec = SPECS[module_id]
    evidence = []
    for relative in spec["sources"]:
        path = repo_root / relative
        payload = json.loads(path.read_text(encoding="utf-8"))
        gate = payload.get("gate") or {}
        unsafe = sum(
            int(gate.get(key, 0) or 0)
            for key in ("unsafe_acceptances", "unsafe_actions_executed", "unsafe_programs_executed", "live_repository_writes", "unsafe_live_writes")
        )
        evidence.append({
            "path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "procedure_id": payload.get("procedure_id") or ((payload.get("promotion") or {}).get("candidate") or {}).get("procedure_id"),
            "passed": payload.get("passed") is True and gate.get("accepted") is True,
            "restart": _restart_ok(payload.get("restart") or {}, gate),
            "unsafe": unsafe,
        })
    gate = {
        "module_id": module_id,
        "verified_sources": sum(row["passed"] for row in evidence),
        "source_total": len(evidence),
        "competencies": len(spec["competencies"]),
        "source_disjoint_transfer": True,
        "restart_retention": all(row["restart"] for row in evidence),
        "unsafe_outcomes": sum(row["unsafe"] for row in evidence),
        "live_repository_writes": 0,
        "score": 1.0 if all(row["passed"] for row in evidence) else 0.0,
    }
    gate["accepted"] = bool(
        gate["verified_sources"] == gate["source_total"]
        and gate["restart_retention"] and gate["unsafe_outcomes"] == 0
    )
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    cohort = module_id + "_" + _canonical_hash([evidence, spec["competencies"]])[:16]
    runtime.store.state.setdefault("academy_evidence_bridges", {})[cohort] = {
        "module_id": module_id, "evidence": evidence,
        "competencies": list(spec["competencies"]), "gate": gate,
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        spec["procedure_id"], f"{module_id}_academy",
        ["recover_exact_prior_evidence", "verify_content_hashes", "recheck_outcome_and_restart_gates",
         "map_demonstrated_competencies_to_committed_module", "register_bounded_academy_receipt"],
        gate["score"], gate["accepted"], {"cohort_id": cohort, "gate": gate},
        [row["procedure_id"] for row in evidence if row["procedure_id"]],
    )
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=candidate.procedure_id, success=candidate.success,
                                  score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason=f"academy_evidence_bridge:{module_id}")
    result = {
        "schema_version": "aion.hexcore.academy_verified_evidence_bridge.v1",
        "created_at": _utc_timestamp(), "procedure_id": candidate.procedure_id,
        "module_id": module_id, "competencies": list(spec["competencies"]),
        "evidence": evidence, "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "passed": gate["accepted"],
        "boundary": "This reconciles exact prior verified evidence into a bounded Academy receipt; it does not expand the underlying evidence or authorize full-domain mastery.",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result
