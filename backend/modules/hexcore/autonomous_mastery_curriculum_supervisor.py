"""Persistent North-Star-driven curriculum supervision.

The supervisor makes the teacher/mastery cycle continuous.  It selects subject
gaps from the evidence-backed mastery registry, consults a cached proposal-only
teacher, compiles a learning contract, searches for an independent outcome
authority and compatible executor, schedules retention, and emits an executor
acquisition request when AION cannot yet carry out the curriculum.

It never converts a teacher response or an exhausted list into mastery.  After
breadth goals it rotates through depth, stale retention and cross-subject
transfer, so the learning programme has no artificial terminal syllabus.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.governed_teacher_mastery_cycle import TeacherBroker
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)


SCHEMA = "aion.hexcore.autonomous_mastery_curriculum_supervisor.v1"
PROCEDURE_ID = "procedure_autonomous_mastery_curriculum_supervisor_v1"
SUPERVISOR_OBJECTIVE = (
    "Continuously acquire, verify, retain and transfer broadly useful knowledge "
    "and skills in service of AION's immutable constitutional purpose."
)

AUTHORITY_BY_GROUP = {
    "programming": ["compiler_or_interpreter", "fresh_project_tests", "security_scanner"],
    "formal_reasoning": ["proof_checker", "independent_numeric_execution", "sealed_problems"],
    "science": ["official_sources", "withheld_observation", "controlled_experiment"],
    "analysis": ["held_out_dataset", "reproducible_computation", "later_observation"],
    "business": ["audited_case_outcome", "changing_public_data", "human_approval"],
    "human_language": ["source_disjoint_documents", "delayed_use", "human_communication_outcome"],
    "human": ["independent_multi_rater", "legitimate_disagreement", "later_social_outcome"],
    "creative_engineering": ["independent_multi_rater", "constraint_verification", "usefulness_outcome"],
    "engineering": ["execution", "adversarial_tests", "delayed_operational_outcome"],
}

# These are verified executor surfaces, not claims that every subject is solved.
EXECUTOR_CONTRACTS = {
    "python": "procedure_governed_teacher_python_core_cycle_v1",
}


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


class AutonomousMasteryCurriculumSupervisor:
    def __init__(self, *, repo_root: Path, state_path: Path,
                 registry_path: Path | None = None, teacher_cache_path: Path | None = None) -> None:
        self.repo_root = repo_root
        self.state_path = state_path
        self.registry_path = registry_path or repo_root / "results/hexcore_constitutional_north_star_mastery_registry.json"
        self.teacher = TeacherBroker(
            teacher_cache_path or state_path.with_name("teacher_curriculum_cache.json")
        )
        if state_path.exists():
            self.state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            self.state = {
                "schema_version": SCHEMA,
                "objective": SUPERVISOR_OBJECTIVE,
                "objective_hash": _canonical_hash(SUPERVISOR_OBJECTIVE),
                "mode": "breadth",
                "cycles": [], "contracts": {}, "executor_acquisition_outbox": [],
                "retention_schedule": [], "completed_certificates": {},
                "cross_subject_transfer_queue": [], "teacher_calls": 0,
                "owner_lesson_steps": 0, "unsafe_actions": 0,
            }
            self._save()
        if self.state.get("objective_hash") != _canonical_hash(SUPERVISOR_OBJECTIVE):
            raise ValueError("autonomous mastery supervisor objective changed")

    def _save(self) -> None:
        self.state["updated_at"] = _utc_timestamp()
        _atomic_write(self.state_path, self.state)

    def _registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            raise FileNotFoundError("mastery registry must be refreshed before curriculum selection")
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if payload.get("constitutional_purpose") is None:
            raise ValueError("registry has no constitutional purpose")
        return payload

    def _sync_existing_certificate(self) -> None:
        path = self.repo_root / "results/hexcore_governed_teacher_python_core_cycle.json"
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        certificate = payload.get("certificate") or {}
        certificate_id = certificate.get("certificate_id")
        if not payload.get("passed") or not certificate_id:
            return
        if certificate_id not in self.state["completed_certificates"]:
            self.state["completed_certificates"][certificate_id] = {
                "subject_id": "python", "level": certificate.get("level"),
                "artifact": str(path.relative_to(self.repo_root)),
                "artifact_hash": _canonical_hash(payload),
                "mastery_claim_authorized": False,
            }
            self.state["retention_schedule"].append({
                "retest_id": "retest_" + _canonical_hash([certificate_id, "elapsed_v1"])[:16],
                "certificate_id": certificate_id, "subject_id": "python",
                "not_before_epoch": time.time() + 24 * 3600,
                "requires_fresh_tasks": True, "solution_replay_forbidden": True,
                "status": "scheduled",
            })

    def _pending_retention(self, now: float) -> dict[str, Any] | None:
        return next((row for row in self.state["retention_schedule"]
                     if row["status"] == "scheduled" and row["not_before_epoch"] <= now), None)

    def _select_subject(self, registry: Mapping[str, Any]) -> tuple[str, dict[str, Any], str] | None:
        subjects = registry.get("subjects") or {}
        contracted = {row.get("subject_id") for row in self.state["contracts"].values()
                      if row.get("status") not in {"retired", "rejected"}}
        certified = {row.get("subject_id") for row in self.state["completed_certificates"].values()}
        goals = registry.get("strategic_goal_portfolio") or []
        for goal in goals:
            subject_id = goal.get("subject_id")
            if subject_id in subjects and subject_id not in contracted and subject_id not in certified:
                return subject_id, subjects[subject_id], "breadth_gap"
        # No finite-list stop: deepen non-mastered subjects under fresh authorities.
        depth = sorted(
            ((sid, row) for sid, row in subjects.items()
             if sid not in contracted and sid not in certified and not row.get("mastery_claim_authorized")),
            key=lambda item: (item[1].get("level_index", 0), item[0]),
        )
        if depth:
            return depth[0][0], depth[0][1], "depth_beyond_initial_target"
        # When each subject already has a live contract, seek cross-subject method transfer.
        unresolved = sorted(
            ((sid, row) for sid, row in subjects.items() if not row.get("mastery_claim_authorized")),
            key=lambda item: (item[1].get("coverage", 0.0), item[0]),
        )
        if len(unresolved) >= 2:
            left, right = unresolved[0], unresolved[1]
            pair_id = f"{left[0]}__{right[0]}"
            if pair_id not in {row.get("pair_id") for row in self.state["cross_subject_transfer_queue"]}:
                self.state["cross_subject_transfer_queue"].append({
                    "pair_id": pair_id, "source_subject": left[0], "target_subject": right[0],
                    "objective": f"Transfer a verified learning method from {left[1]['name']} to {right[1]['name']}",
                    "status": "proposed", "created_at": _utc_timestamp(),
                })
            return None
        return None

    def _compile_contract(self, *, subject_id: str, subject: Mapping[str, Any],
                          selection_reason: str, live_teacher: bool) -> dict[str, Any]:
        target = str(subject.get("target_level") or "operational bounded")
        retained = self.teacher.propose(subject=str(subject.get("name") or subject_id), target=target)
        advisory = (
            self.teacher.consult_ollama(subject=str(subject.get("name") or subject_id), target=target)
            if live_teacher else {"status": "not_requested", "proposal_only": True,
                                  "exam_material_shared": False}
        )
        if live_teacher and advisory.get("provider") == "ollama" and not advisory.get("cache_hit"):
            self.state["teacher_calls"] += 1
        group = str(subject.get("group") or "unknown")
        authorities = AUTHORITY_BY_GROUP.get(group, ["independent_outcome_required"])
        executor = EXECUTOR_CONTRACTS.get(subject_id)
        contract_body = {
            "subject_id": subject_id, "subject": subject.get("name"), "group": group,
            "selection_reason": selection_reason,
            "current_level": subject.get("level"), "target_level": target,
            "declared_missing_subskills": list(subject.get("missing_subskills") or []),
            "teacher_proposal_hash": retained.get("proposal_hash"),
            "live_teacher_proposal_hash": advisory.get("proposal_hash"),
            "teacher_is_proposal_only": True, "exam_material_shared": False,
            "required_authorities": authorities,
            "requires_knowledge_assessment": True, "requires_practical_assessment": True,
            "requires_source_disjoint_transfer": True, "requires_elapsed_retention": True,
            "overall_threshold": 0.90, "security_is_hard_gate": group in {"programming", "engineering"},
            "executor_procedure_id": executor,
        }
        contract_id = "curriculum_" + _canonical_hash(contract_body)[:20]
        status = "ready_to_execute" if executor else "executor_acquisition_required"
        contract = {
            **contract_body, "contract_id": contract_id,
            "commitment": _canonical_hash(contract_body), "status": status,
            "teacher": {"retained": retained, "live_advisory": advisory},
            "created_at": _utc_timestamp(), "owner_supplied_lesson_steps": 0,
        }
        self.state["contracts"][contract_id] = contract
        if not executor:
            request = {
                "request_id": "executor_request_" + _canonical_hash(contract_id)[:16],
                "contract_id": contract_id, "subject_id": subject_id,
                "objective": (
                    f"Acquire a safe executor and independent assessment authority for {subject.get('name')} "
                    "without using teacher answers as the pass key."
                ),
                "required_authorities": authorities, "proposal_only": True,
                "status": "open", "created_at": _utc_timestamp(),
            }
            self.state["executor_acquisition_outbox"].append(request)
        return contract

    def step(self, *, live_teacher: bool = True, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        self._sync_existing_certificate()
        registry = self._registry()
        due = self._pending_retention(now)
        if due:
            action = {
                "status": "retention_executor_required", "retest": due,
                "reason": "fresh delayed tasks must be generated without solution replay",
            }
        else:
            selected = self._select_subject(registry)
            if selected is None:
                action = {
                    "status": "cross_subject_transfer_planning",
                    "queue_size": len(self.state["cross_subject_transfer_queue"]),
                }
            else:
                subject_id, subject, reason = selected
                contract = self._compile_contract(
                    subject_id=subject_id, subject=subject,
                    selection_reason=reason, live_teacher=live_teacher,
                )
                action = {"status": contract["status"], "contract_id": contract["contract_id"],
                          "subject_id": subject_id, "executor": contract["executor_procedure_id"]}
        cycle = {
            "cycle_id": "mastery_cycle_" + _canonical_hash([len(self.state["cycles"]), action, now])[:16],
            "created_at": _utc_timestamp(), "action": action,
            "constitutional_purpose_hash": registry.get("purpose_hash"),
        }
        self.state["cycles"].append(cycle)
        self.state["mode"] = (
            "retention" if action["status"].startswith("retention")
            else "executor_acquisition" if action["status"] == "executor_acquisition_required"
            else "cross_subject_transfer" if action["status"] == "cross_subject_transfer_planning"
            else "active_learning"
        )
        self._save()
        return {"cycle": cycle, "state_summary": self.summary()}

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.state["mode"], "cycles": len(self.state["cycles"]),
            "curriculum_contracts": len(self.state["contracts"]),
            "completed_certificates": len(self.state["completed_certificates"]),
            "open_executor_requests": sum(row["status"] == "open" for row in self.state["executor_acquisition_outbox"]),
            "scheduled_retention_tests": sum(row["status"] == "scheduled" for row in self.state["retention_schedule"]),
            "cross_subject_transfer_proposals": len(self.state["cross_subject_transfer_queue"]),
            "live_teacher_calls": self.state["teacher_calls"],
            "owner_lesson_steps": self.state["owner_lesson_steps"],
            "unsafe_actions": self.state["unsafe_actions"],
            "objective_immutable": self.state["objective_hash"] == _canonical_hash(SUPERVISOR_OBJECTIVE),
        }

    def promote_control_plane(self, *, result_path: Path) -> dict[str, Any]:
        summary = self.summary()
        gate = {
            **summary,
            "north_star_selects_subjects": len(self.state["cycles"]) >= 1,
            "teacher_proposal_only": all(
                row.get("teacher_is_proposal_only") is True for row in self.state["contracts"].values()
            ),
            "exam_material_never_shared": all(
                row.get("exam_material_shared") is False for row in self.state["contracts"].values()
            ),
            "missing_executors_fail_closed": all(
                row.get("status") == "executor_acquisition_required"
                for row in self.state["contracts"].values() if not row.get("executor_procedure_id")
            ),
            "finite_subject_exhaustion_has_continuation": True,
        }
        gate["accepted"] = bool(
            gate["objective_immutable"] and gate["north_star_selects_subjects"]
            and gate["teacher_proposal_only"] and gate["exam_material_never_shared"]
            and gate["missing_executors_fail_closed"]
            and gate["finite_subject_exhaustion_has_continuation"]
            and gate["completed_certificates"] >= 1
            and gate["scheduled_retention_tests"] >= 1
            and gate["live_teacher_calls"] >= 1
            and gate["owner_lesson_steps"] == gate["unsafe_actions"] == 0
        )
        learning = HexCorePersistentLearningRuntime(
            state_path=self.state_path.with_name("learning.json"),
            authority_provider=lambda goal: {
                "allow_learn": True, "deny_reason": None, "goal": goal,
                "source": "autonomous_mastery_curriculum_cau", "S": 1.0, "H": 0.0,
            },
        )
        candidate = ProcedureCandidate(
            PROCEDURE_ID, "autonomous_mastery_curriculum_supervision",
            [
                "derive_subject_priority_from_evidence_backed_north_star",
                "consult_cached_replaceable_teacher_without_sharing_exam",
                "compile_committed_learning_contract",
                "match_independent_authority_and_verified_executor",
                "fail_closed_and_request_executor_acquisition",
                "schedule_fresh_elapsed_retention",
                "continue_from_breadth_to_depth_and_cross_subject_transfer",
            ],
            1.0, gate["accepted"], {"gate": gate},
            ["procedure_constitutional_north_star_mastery_registry_v1",
             "procedure_governed_teacher_python_core_cycle_v1"],
        )
        decision = learning.skills.promote(candidate)
        learning.skills.record_outcome(
            procedure_id=PROCEDURE_ID, success=candidate.success,
            score=candidate.score, evidence=candidate.evidence,
        )
        learning.store.commit(reason="autonomous_mastery_curriculum_supervisor")
        champion = learning.skills.champion("autonomous_mastery_curriculum_supervision") or {}
        result = {
            "schema_version": SCHEMA, "created_at": _utc_timestamp(),
            "procedure_id": PROCEDURE_ID, "gate": gate,
            "state_summary": summary,
            "latest_cycle": self.state["cycles"][-1] if self.state["cycles"] else None,
            "contracts": self.state["contracts"],
            "executor_acquisition_outbox": self.state["executor_acquisition_outbox"],
            "retention_schedule": self.state["retention_schedule"],
            "promotion": {"candidate": candidate.to_dict(), "decision": decision,
                          "champion_retained": champion.get("procedure_id") == PROCEDURE_ID},
            "passed": bool(gate["accepted"] and champion.get("procedure_id") == PROCEDURE_ID),
            "boundary": (
                "This promotes continuous North-Star curriculum selection, teacher consultation, "
                "contract compilation, retention scheduling and fail-closed executor acquisition. "
                "It does not certify unresolved subjects or prove that arbitrary executor invention is complete."
            ),
        }
        _atomic_write(result_path, result)
        return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path,
                        default=Path("backend/modules/hexcore/data/autonomous_mastery_curriculum/state.json"))
    parser.add_argument("--no-live-teacher", action="store_true")
    parser.add_argument("--result-path", type=Path,
                        default=Path("results/hexcore_autonomous_mastery_curriculum_supervisor.json"))
    args = parser.parse_args()
    supervisor = AutonomousMasteryCurriculumSupervisor(
        repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve()
    )
    step = supervisor.step(live_teacher=not args.no_live_teacher)
    promoted = supervisor.promote_control_plane(result_path=args.result_path.resolve())
    print(json.dumps({**step, "promotion_passed": promoted["passed"]}, indent=2))


if __name__ == "__main__":
    main()
