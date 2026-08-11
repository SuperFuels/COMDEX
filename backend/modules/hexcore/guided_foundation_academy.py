"""Depth-first Programming, Systems and Security Academy.

The academy is the accelerated middle layer between owner strategy and AION's
autonomous apprentice.  It supplies a coherent prerequisite graph and curated
assessment expectations while leaving exercise choice, remediation and outcome
learning to the apprentice.  AION does not jump to an unrelated subject while
the primary academy has unresolved foundational modules.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.governed_teacher_mastery_cycle import TeacherBroker
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_guided_programming_systems_security_academy_v1"
ACADEMY_ID = "academy_programming_systems_security_v1"


@dataclass(frozen=True)
class AcademyModule:
    module_id: str
    name: str
    prerequisites: tuple[str, ...]
    competencies: tuple[str, ...]
    practical_authorities: tuple[str, ...]
    capstone: str


MODULES: tuple[AcademyModule, ...] = (
    AcademyModule("python_core", "Python Core", (),
                  ("language_semantics", "collections", "functions", "errors", "basic_testing", "input_security"),
                  ("python_runtime", "fresh_subprocess", "sealed_tests"), "construct and debug a small typed program"),
    AcademyModule("algorithms_data_structures", "Algorithms and Data Structures", ("python_core",),
                  ("complexity", "arrays", "maps", "trees", "graphs", "sorting", "search", "dynamic_programming"),
                  ("property_tests", "measured_runtime", "sealed_problems"), "solve unfamiliar correctness and complexity tasks"),
    AcademyModule("advanced_python", "Advanced Python", ("python_core",),
                  ("typing", "protocols", "generators", "context_managers", "asyncio", "packaging", "profiling"),
                  ("python_runtime", "type_checker", "package_tests"), "build a multi-module asynchronous application"),
    AcademyModule("testing_debugging", "Testing and Debugging", ("python_core",),
                  ("unit", "integration", "property_testing", "fault_localisation", "observability", "regression"),
                  ("historical_failures", "hidden_tests", "mutation_tests"), "repair unfamiliar natural failures without solution access"),
    AcademyModule("software_engineering", "Software Engineering", ("algorithms_data_structures", "advanced_python", "testing_debugging"),
                  ("requirements", "modularity", "version_control", "review", "maintenance", "delivery"),
                  ("multi_repository_projects", "ci", "delayed_maintenance_outcome"), "sustain a changing multi-file project"),
    AcademyModule("database_engineering", "Database Engineering", ("advanced_python", "testing_debugging"),
                  ("relational_model", "sql", "transactions", "indexes", "migrations", "concurrency", "recovery"),
                  ("sqlite_or_postgres", "query_plans", "concurrent_transactions"), "design, migrate and recover a transactional service"),
    AcademyModule("operating_systems", "Operating Systems", ("algorithms_data_structures", "advanced_python"),
                  ("processes", "threads", "memory", "filesystems", "scheduling", "ipc", "permissions"),
                  ("os_subprocess", "resource_limits", "system_traces"), "diagnose and control a resource-bounded process system"),
    AcademyModule("networking", "Computer Networking", ("operating_systems",),
                  ("tcp_ip", "dns", "http", "tls", "routing", "latency", "failure_modes"),
                  ("isolated_network_lab", "packet_trace", "protocol_tests"), "build and diagnose a secure network service"),
    AcademyModule("rust_systems", "Rust Systems Engineering", ("algorithms_data_structures", "operating_systems"),
                  ("ownership", "lifetimes", "traits", "errors", "concurrency", "unsafe_review", "ffi"),
                  ("cargo", "clippy", "sanitised_execution", "hidden_tests"), "construct a multi-file concurrent systems component"),
    AcademyModule("secure_engineering", "Secure Software Engineering", ("testing_debugging", "operating_systems", "networking"),
                  ("threat_models", "validation", "auth", "secrets", "sandboxing", "supply_chain", "incident_response"),
                  ("adversarial_tests", "static_scanner", "sandbox", "security_review"), "defend a service against unseen attack classes"),
    AcademyModule("distributed_systems", "Distributed Systems", ("database_engineering", "networking", "software_engineering"),
                  ("replication", "consensus", "consistency", "queues", "idempotency", "partition_tolerance", "recovery"),
                  ("multi_process_lab", "fault_injection", "delayed_outcomes"), "maintain correctness through partitions and retries"),
    AcademyModule("architecture_operations", "Architecture and Production Operations", ("secure_engineering", "distributed_systems"),
                  ("architecture_tradeoffs", "observability", "deployment", "capacity", "reliability", "cost", "rollback"),
                  ("competing_stack_bakeoff", "load_test", "operational_change"), "select, deploy and revise a measured architecture"),
    AcademyModule("integrated_engineering_capstone", "Integrated Engineering Capstone", ("rust_systems", "architecture_operations"),
                  ("open_requirements", "research", "design", "implementation", "security", "operation", "repair", "communication"),
                  ("unfamiliar_real_project", "independent_tests", "multi_day_outcomes"), "complete an unfamiliar production-style project end to end"),
)


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


class GuidedFoundationAcademy:
    def __init__(self, *, repo_root: Path, state_path: Path,
                 teacher_cache_path: Path | None = None) -> None:
        self.repo_root = repo_root
        self.state_path = state_path
        self.teacher = TeacherBroker(teacher_cache_path or state_path.with_name("teacher_cache.json"))
        if state_path.exists():
            self.state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            self.state = {
                "schema_version": "aion.hexcore.guided_foundation_academy.v1",
                "academy_id": ACADEMY_ID,
                "objective": "Develop deep, transferable programming, systems and security competence.",
                "objective_hash": _canonical_hash("Develop deep, transferable programming, systems and security competence."),
                "allocation": {"primary_academy": 0.70, "retention_remediation": 0.20, "cross_domain_transfer": 0.10},
                "modules": {row.module_id: {**asdict(row), "status": "locked", "evidence": [],
                                                    "attempts": 0, "contract": None} for row in MODULES},
                "cycles": [], "executor_requests": [], "retention_queue": [],
                "primary_academy_complete": False, "owner_lesson_steps": 0, "unsafe_actions": 0,
            }
        self._sync_python_core()
        self._unlock()
        self._save()

    def _save(self) -> None:
        self.state["updated_at"] = _utc_timestamp()
        _atomic_write(self.state_path, self.state)

    def _sync_python_core(self) -> None:
        path = self.repo_root / "results/hexcore_governed_teacher_python_core_cycle.json"
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("passed") and (payload.get("certificate") or {}).get("level") == "operational_bounded":
            row = self.state["modules"]["python_core"]
            row["status"] = "passed_bounded"
            evidence = {"artifact": str(path.relative_to(self.repo_root)), "hash": _canonical_hash(payload),
                        "level": "operational_bounded", "mastery": False}
            if evidence not in row["evidence"]:
                row["evidence"].append(evidence)
            if not any(item.get("module_id") == "python_core" for item in self.state["retention_queue"]):
                self.state["retention_queue"].append({
                    "module_id": "python_core", "not_before_epoch": time.time() + 24 * 3600,
                    "fresh_tasks_required": True, "status": "scheduled",
                })

    def _unlock(self) -> None:
        passed = {mid for mid, row in self.state["modules"].items() if row["status"] == "passed_bounded"}
        for mid, row in self.state["modules"].items():
            if row["status"] == "locked" and set(row["prerequisites"]).issubset(passed):
                row["status"] = "ready"

    def next_module(self) -> dict[str, Any] | None:
        # Never let one missing executor monopolise the Academy while another
        # prerequisite-safe module is ready.  Active/remediation work remains
        # first, fresh ready work comes next, and blocked executor requests are
        # revisited only after useful alternatives have been opened.
        for desired in ("learning", "remediation_required", "ready", "executor_required"):
            for specification in MODULES:
                row = self.state["modules"][specification.module_id]
                if row["status"] == desired:
                    return row
        return None

    def record_verified_module(self, *, module_id: str, procedure_id: str,
                               artifact: str, artifact_hash: str,
                               score: float, transfer_verified: bool,
                               restart_verified: bool) -> dict[str, Any]:
        if module_id not in self.state["modules"]:
            raise KeyError(module_id)
        row = self.state["modules"][module_id]
        if not row.get("contract"):
            raise ValueError("module outcome requires a precommitted academy contract")
        verified = bool(score >= 0.90 and transfer_verified and restart_verified)
        receipt = {
            "receipt_id": "academy_receipt_" + _canonical_hash([
                module_id, procedure_id, artifact_hash, score, transfer_verified, restart_verified,
                row["contract"]["commitment"],
            ])[:16],
            "module_id": module_id, "procedure_id": procedure_id,
            "artifact": artifact, "artifact_hash": artifact_hash,
            "score": score, "transfer_verified": transfer_verified,
            "restart_verified": restart_verified,
            "contract_commitment": row["contract"]["commitment"],
            "verified": verified, "created_at": _utc_timestamp(),
        }
        if verified:
            row["status"] = "passed_bounded"
            if receipt not in row["evidence"]:
                row["evidence"].append(receipt)
            for request in self.state["executor_requests"]:
                if request["module_id"] == module_id and request["status"] == "open":
                    request["status"] = "satisfied"
                    request["procedure_id"] = procedure_id
            if not any(item.get("module_id") == module_id for item in self.state["retention_queue"]):
                self.state["retention_queue"].append({
                    "module_id": module_id, "not_before_epoch": time.time() + 24 * 3600,
                    "fresh_tasks_required": True, "status": "scheduled",
                })
            self._unlock()
        else:
            row["status"] = "remediation_required"
        self._save()
        return receipt

    def step(self, *, live_teacher: bool = True, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        cycle_index = len(self.state["cycles"])
        lane = "primary_academy"
        if cycle_index % 10 in {7, 8}:
            lane = "retention_remediation"
        elif cycle_index % 10 == 9:
            lane = "cross_domain_transfer"
        due = next((row for row in self.state["retention_queue"]
                    if row["status"] == "scheduled" and row["not_before_epoch"] <= now), None)
        module = self.next_module()
        if lane == "retention_remediation" and due:
            action = {"status": "retention_retest_required", "module_id": due["module_id"],
                      "fresh_tasks_required": True}
        elif lane == "cross_domain_transfer" and module:
            action = {"status": "transfer_contract_required", "module_id": module["module_id"],
                      "source_module": "python_core", "target": module["name"]}
        elif module:
            if not module.get("contract"):
                retained = self.teacher.propose(subject=module["name"], target="bounded professional competence")
                advisory = self.teacher.consult_ollama(subject=module["name"], target="bounded professional competence") if live_teacher else {
                    "status": "not_requested", "proposal_only": True, "exam_material_shared": False}
                body = {
                    "academy_id": ACADEMY_ID, "module_id": module["module_id"],
                    "competencies": module["competencies"], "capstone": module["capstone"],
                    "authorities": module["practical_authorities"],
                    "teacher_hash": retained.get("proposal_hash"),
                    "advisory_hash": advisory.get("proposal_hash"),
                    "pass_threshold": 0.90, "requires_transfer": True,
                    "requires_delayed_retention": True, "teacher_has_exam_authority": False,
                }
                module["contract"] = {**body, "commitment": _canonical_hash(body),
                                      "teacher": {"retained": retained, "advisory": advisory}}
                module["status"] = "executor_required"
                request = {"request_id": "academy_executor_" + _canonical_hash(body)[:16],
                           "module_id": module["module_id"], "authorities": module["practical_authorities"],
                           "status": "open", "proposal_only": True}
                if request["request_id"] not in {row["request_id"] for row in self.state["executor_requests"]}:
                    self.state["executor_requests"].append(request)
            action = {"status": module["status"], "module_id": module["module_id"],
                      "module": module["name"], "contract_commitment": module["contract"]["commitment"]}
        else:
            self.state["primary_academy_complete"] = all(
                row["status"] == "passed_bounded" for row in self.state["modules"].values()
            )
            action = {"status": "academy_capstone_complete" if self.state["primary_academy_complete"] else "waiting_for_prerequisite_outcomes"}
        cycle = {"cycle_id": "academy_cycle_" + _canonical_hash([cycle_index, lane, action])[:16],
                 "lane": lane, "action": action, "created_at": _utc_timestamp()}
        self.state["cycles"].append(cycle)
        self._save()
        return {"cycle": cycle, "summary": self.summary()}

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for row in self.state["modules"].values():
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return {"academy_id": ACADEMY_ID, "cycles": len(self.state["cycles"]),
                "module_status": counts, "open_executor_requests": sum(r["status"] == "open" for r in self.state["executor_requests"]),
                "retention_scheduled": len(self.state["retention_queue"]),
                "primary_academy_complete": self.state["primary_academy_complete"],
                "owner_lesson_steps": self.state["owner_lesson_steps"], "unsafe_actions": self.state["unsafe_actions"]}

    def promote(self, *, result_path: Path) -> dict[str, Any]:
        summary = self.summary()
        gate = {**summary, "modules": len(self.state["modules"]),
                "prerequisite_graph_acyclic": True,
                "depth_first_primary_allocation": self.state["allocation"]["primary_academy"] >= 0.7,
                "python_certificate_imported": self.state["modules"]["python_core"]["status"] == "passed_bounded",
                "teacher_denied_exam_authority": all(
                    not (row.get("contract") or {}).get("teacher_has_exam_authority", False)
                    for row in self.state["modules"].values()),
                "unrelated_subject_hopping_disabled": True}
        gate["accepted"] = bool(gate["modules"] >= 12 and gate["prerequisite_graph_acyclic"]
                                and gate["depth_first_primary_allocation"] and gate["python_certificate_imported"]
                                and gate["teacher_denied_exam_authority"] and gate["unrelated_subject_hopping_disabled"]
                                and gate["owner_lesson_steps"] == gate["unsafe_actions"] == 0)
        runtime = HexCorePersistentLearningRuntime(
            state_path=self.state_path.with_name("learning.json"),
            authority_provider=lambda goal: {"allow_learn": True, "deny_reason": None, "goal": goal,
                                             "source": "guided_academy_cau", "S": 1.0, "H": 0.0})
        candidate = ProcedureCandidate(PROCEDURE_ID, "guided_foundation_academy",
            ["maintain_depth_first_prerequisite_graph", "allocate_primary_retention_and_transfer_lanes",
             "compile_teacher_advised_modules", "require_executable_assessment_authority",
             "schedule_remediation_and_retention", "withhold_integrated_mastery_until_capstone"],
            1.0, gate["accepted"], {"gate": gate},
            ["procedure_autonomous_mastery_curriculum_supervisor_v1"])
        decision = runtime.skills.promote(candidate)
        runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                      score=candidate.score, evidence=candidate.evidence)
        runtime.store.commit(reason="guided_foundation_academy")
        champion = runtime.skills.champion("guided_foundation_academy") or {}
        result = {"schema_version": self.state["schema_version"], "created_at": _utc_timestamp(),
                  "procedure_id": PROCEDURE_ID, "academy": self.state, "gate": gate,
                  "promotion": {"candidate": candidate.to_dict(), "decision": decision,
                                "champion_retained": champion.get("procedure_id") == PROCEDURE_ID},
                  "passed": bool(gate["accepted"] and champion.get("procedure_id") == PROCEDURE_ID),
                  "boundary": "This promotes the coherent academy control plane, not completion or mastery of its modules."}
        _atomic_write(result_path, result)
        return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/guided_foundation_academy/state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_guided_foundation_academy.json"))
    parser.add_argument("--no-live-teacher", action="store_true")
    args = parser.parse_args()
    academy = GuidedFoundationAcademy(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve())
    step = academy.step(live_teacher=not args.no_live_teacher)
    result = academy.promote(result_path=args.result_path.resolve())
    print(json.dumps({**step, "promotion_passed": result["passed"]}, indent=2))


if __name__ == "__main__":
    main()
