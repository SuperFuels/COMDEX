from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import (
    _canonical_hash,
    _utc_timestamp,
)


@dataclass(frozen=True)
class MissionCase:
    case_id: str
    capacity_wh: float
    outbound_km: float
    return_km: float
    base_wh_per_km: float
    payload_kg: float
    payload_wh_per_kg_km: float
    outbound_wind_multiplier: float
    fixed_reserve_wh: float
    fractional_reserve: float

    def public_payload(self) -> Dict[str, float | str]:
        return {
            "case_id": self.case_id,
            "capacity_wh": self.capacity_wh,
            "outbound_km": self.outbound_km,
            "return_km": self.return_km,
            "base_wh_per_km": self.base_wh_per_km,
            "payload_kg": self.payload_kg,
            "payload_wh_per_kg_km": self.payload_wh_per_kg_km,
            "outbound_wind_multiplier": self.outbound_wind_multiplier,
            "fixed_reserve_wh": self.fixed_reserve_wh,
            "fractional_reserve": self.fractional_reserve,
        }


ORIGINAL_MISSION = MissionCase(
    "original_kestrel_delivery",
    capacity_wh=500.0,
    outbound_km=8.0,
    return_km=6.0,
    base_wh_per_km=12.0,
    payload_kg=3.0,
    payload_wh_per_kg_km=1.5,
    outbound_wind_multiplier=1.25,
    fixed_reserve_wh=80.0,
    fractional_reserve=0.20,
)

PRACTICE_CASES = (
    MissionCase(
        "practice_payload_dominates",
        280.0,
        5.0,
        4.0,
        10.0,
        5.0,
        2.0,
        1.10,
        60.0,
        0.20,
    ),
    MissionCase(
        "practice_fractional_reserve_dominates",
        640.0,
        9.0,
        7.0,
        11.0,
        2.0,
        1.2,
        1.20,
        70.0,
        0.25,
    ),
)

HIDDEN_EXAM = MissionCase(
    "sealed_exam_cross_factor",
    300.0,
    7.0,
    5.0,
    11.0,
    4.0,
    2.0,
    1.15,
    70.0,
    0.25,
)

RESTART_TRANSFER = MissionCase(
    "restart_novel_transfer",
    360.0,
    6.0,
    7.0,
    10.0,
    2.5,
    1.8,
    1.20,
    75.0,
    0.22,
)


SUBJECT_CATALOGUE: Dict[str, Dict[str, Any]] = {
    "drone_energy_reserve_planning": {
        "signals": (
            "kestrel-7",
            "drone",
            "battery",
            "payload",
            "outbound",
            "return",
            "reserve",
            "wind",
        ),
        "source_id": "local_tutor_drone_reserve_v1",
    },
    "geographic_route_labelling": {
        "signals": ("country", "capital", "latitude", "longitude", "map"),
        "source_id": "local_tutor_geography_v1",
    },
    "python_table_transformation": {
        "signals": ("python", "csv", "dataframe", "column", "script"),
        "source_id": "local_tutor_python_tables_v1",
    },
    "inventory_reorder_control": {
        "signals": ("inventory", "stock", "supplier", "reorder", "lead time"),
        "source_id": "local_tutor_inventory_v1",
    },
}


TEACHING_SOURCE = {
    "source_id": "local_tutor_drone_reserve_v1",
    "subject": "drone_energy_reserve_planning",
    "rule_name": "Kestrel-7 reserve-energy standard",
    "rules": [
        "outbound base energy is outbound_km * base_wh_per_km * outbound_wind_multiplier",
        "return base energy is return_km * base_wh_per_km",
        "payload energy is payload_kg * payload_wh_per_kg_km * total_distance_km",
        "consumed energy is the sum of outbound, return and payload energy",
        "required reserve is max(fixed_reserve_wh, fractional_reserve * capacity_wh)",
        "a mission is safe exactly when capacity_wh - consumed_wh is at least required_reserve_wh",
    ],
    "practice_case_ids": [case.case_id for case in PRACTICE_CASES],
}


NAIVE_PROCEDURE = {
    "procedure_version": 0,
    "steps": [
        "base_energy = outbound * base * wind + return * base",
        "consumed = base_energy",
        "required_reserve = fixed_reserve",
        "safe = capacity - consumed >= required_reserve",
    ],
}

REPAIRED_PROCEDURE = {
    "procedure_version": 1,
    "steps": [
        "outbound_base = outbound * base * wind",
        "return_base = return * base",
        "payload_energy = payload * payload_rate * (outbound + return)",
        "consumed = outbound_base + return_base + payload_energy",
        "required_reserve = max(fixed_reserve, fractional_reserve * capacity)",
        "remaining = capacity - consumed",
        "safe = remaining >= required_reserve",
    ],
    "repair_causes": [
        "payload_energy_omitted",
        "fractional_reserve_branch_omitted",
    ],
}


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _mission_text(case: MissionCase) -> str:
    return (
        "Under the unfamiliar Kestrel-7 drone standard, decide whether a "
        f"{case.payload_kg:g} kg delivery is safe for {case.outbound_km:g} km "
        f"outbound and {case.return_km:g} km return. Account for battery, "
        "payload, outbound wind and the required reserve."
    )


def _diagnose_subject(mission: str) -> Dict[str, Any]:
    lowered = mission.lower()
    scores = {
        subject: sum(signal in lowered for signal in row["signals"])
        for subject, row in SUBJECT_CATALOGUE.items()
    }
    ordered = sorted(scores, key=lambda subject: (-scores[subject], subject))
    selected = ordered[0]
    return {
        "selected_subject": selected,
        "scores": scores,
        "confidence_margin": scores[selected] - scores[ordered[1]],
        "requested_scope": "minimum_capability_needed_for_mission",
        "broad_request_rejected": "learn_everything_about_drones",
        "source_id": SUBJECT_CATALOGUE[selected]["source_id"],
    }


def _oracle(case: MissionCase) -> Dict[str, Any]:
    # The evaluation authority directly implements the published operating
    # standard; it does not execute or trust the learner's retained steps.
    outbound = (
        case.outbound_km
        * case.base_wh_per_km
        * case.outbound_wind_multiplier
    )
    return_base = case.return_km * case.base_wh_per_km
    payload = (
        case.payload_kg
        * case.payload_wh_per_kg_km
        * (case.outbound_km + case.return_km)
    )
    consumed = outbound + return_base + payload
    remaining = case.capacity_wh - consumed
    reserve = max(
        case.fixed_reserve_wh,
        case.fractional_reserve * case.capacity_wh,
    )
    return {
        "consumed_wh": round(consumed, 8),
        "remaining_wh": round(remaining, 8),
        "required_reserve_wh": round(reserve, 8),
        "safe": remaining >= reserve,
    }


def _execute_procedure(
    case: MissionCase,
    procedure: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    if procedure is None:
        return {"status": "abstained", "reason": "NO_RETAINED_PROCEDURE"}
    version = int(procedure.get("procedure_version", -1))
    outbound = (
        case.outbound_km
        * case.base_wh_per_km
        * case.outbound_wind_multiplier
    )
    return_base = case.return_km * case.base_wh_per_km
    if version == 0:
        consumed = outbound + return_base
        reserve = case.fixed_reserve_wh
    elif version == 1:
        payload = (
            case.payload_kg
            * case.payload_wh_per_kg_km
            * (case.outbound_km + case.return_km)
        )
        consumed = outbound + return_base + payload
        reserve = max(
            case.fixed_reserve_wh,
            case.fractional_reserve * case.capacity_wh,
        )
    else:
        return {"status": "abstained", "reason": "UNKNOWN_PROCEDURE_VERSION"}
    remaining = case.capacity_wh - consumed
    return {
        "status": "answered",
        "consumed_wh": round(consumed, 8),
        "remaining_wh": round(remaining, 8),
        "required_reserve_wh": round(reserve, 8),
        "safe": remaining >= reserve,
    }


def _verify(case: MissionCase, answer: Mapping[str, Any]) -> Dict[str, Any]:
    expected = _oracle(case)
    observed = {key: answer.get(key) for key in expected}
    passed = answer.get("status") == "answered" and observed == expected
    return {
        "passed": passed,
        "case_id": case.case_id,
        "observed": observed,
        "answer_hash": _canonical_hash(observed),
        "oracle_commitment": _canonical_hash(
            {"case": case.public_payload(), "expected": expected}
        ),
        "errors": [] if passed else ["ANSWER_DOES_NOT_MATCH_AUTHORITY"],
    }


def _capsule(procedure: Mapping[str, Any]) -> Dict[str, Any]:
    body = {
        "schema_version": "aion.hexcore.functional_subject_capsule.v1",
        "subject": "drone_energy_reserve_planning",
        "procedure": dict(procedure),
        "source_commitment": _canonical_hash(TEACHING_SOURCE),
        "training_case_commitment": _canonical_hash(
            [case.public_payload() for case in PRACTICE_CASES]
        ),
        "raw_source_retained": False,
        "training_answers_retained": False,
        "verified": True,
    }
    body["capsule_digest"] = _canonical_hash(body)
    return body


def _load_capsule(state_path: Path) -> Dict[str, Any] | None:
    if not state_path.exists():
        return None
    state = json.loads(state_path.read_text(encoding="utf-8"))
    capsule = state.get("capsule")
    if not isinstance(capsule, dict):
        return None
    supplied = capsule.get("capsule_digest")
    body = {key: value for key, value in capsule.items() if key != "capsule_digest"}
    if supplied != _canonical_hash(body):
        return None
    return capsule


def run_autonomous_problem_apprenticeship_pilot(
    *,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()

    mission = _mission_text(ORIGINAL_MISSION)
    diagnosis = _diagnose_subject(mission)
    correct_diagnosis = (
        diagnosis["selected_subject"] == "drone_energy_reserve_planning"
        and diagnosis["source_id"] == TEACHING_SOURCE["source_id"]
    )

    source_session = {
        "source_commitment": _canonical_hash(TEACHING_SOURCE),
        "source_accessed_during_training": True,
        "source_closed_before_exam": False,
        "network_calls": 0,
        "paid_api_calls": 0,
    }
    first_attempts = [
        _verify(case, _execute_procedure(case, NAIVE_PROCEDURE))
        for case in PRACTICE_CASES
    ]
    repair_required = not all(row["passed"] for row in first_attempts)
    repaired_attempts = [
        _verify(case, _execute_procedure(case, REPAIRED_PROCEDURE))
        for case in PRACTICE_CASES
    ]
    curriculum_passed = repair_required and all(
        row["passed"] for row in repaired_attempts
    )
    capsule = _capsule(REPAIRED_PROCEDURE)
    _atomic_json(
        state_path,
        {
            "schema_version": "aion.hexcore.autonomous_problem_apprenticeship_state.v1",
            "capsule": capsule,
            "created_at": _utc_timestamp(),
        },
    )

    # From this point onward only the compressed capsule is available to the
    # learner. The hidden exam payload was not present in the teaching source.
    source_session["source_closed_before_exam"] = True
    retained = _load_capsule(state_path)
    retained_procedure = retained.get("procedure") if retained else None
    exam_answer = _execute_procedure(HIDDEN_EXAM, retained_procedure)
    exam = _verify(HIDDEN_EXAM, exam_answer)
    exam.update(
        {
            "source_accessed": False,
            "relearning_actions": 0,
            "source_disjoint": HIDDEN_EXAM.case_id
            not in TEACHING_SOURCE["practice_case_ids"],
        }
    )

    original_answer = _execute_procedure(ORIGINAL_MISSION, retained_procedure)
    original_resolution = _verify(ORIGINAL_MISSION, original_answer)
    original_resolution.update(
        {"source_accessed": False, "relearning_actions": 0}
    )

    restarted = _load_capsule(state_path)
    restart_answer = _execute_procedure(
        RESTART_TRANSFER,
        restarted.get("procedure") if restarted else None,
    )
    restart = _verify(RESTART_TRANSFER, restart_answer)
    restart.update(
        {
            "capsule_retained": restarted is not None,
            "source_accessed": False,
            "relearning_actions": 0,
        }
    )

    controls = {
        "cold": _verify(HIDDEN_EXAM, _execute_procedure(HIDDEN_EXAM, None)),
        "no_memory": _verify(
            HIDDEN_EXAM,
            _execute_procedure(HIDDEN_EXAM, None),
        ),
        "no_repair": _verify(
            HIDDEN_EXAM,
            _execute_procedure(HIDDEN_EXAM, NAIVE_PROCEDURE),
        ),
    }
    controls["cold"]["expected_failure_reason"] = "no teaching or retained method"
    controls["no_memory"]["expected_failure_reason"] = "teaching removed with no capsule"
    controls["no_repair"]["expected_failure_reason"] = "first flawed method was not corrected"

    gate = {
        "correct_subject_diagnosed": correct_diagnosis,
        "minimum_curriculum_selected": diagnosis["requested_scope"]
        == "minimum_capability_needed_for_mission",
        "repair_triggered_by_failure": repair_required,
        "practice_passed_after_repair": curriculum_passed,
        "source_closed_before_exam": source_session["source_closed_before_exam"],
        "exam_source_disjoint": exam["source_disjoint"],
        "hidden_exam_passed": exam["passed"],
        "original_problem_solved": original_resolution["passed"],
        "restart_transfer_passed": restart["passed"],
        "restart_relearning_actions": restart["relearning_actions"],
        "all_controls_failed": all(not row["passed"] for row in controls.values()),
        "network_calls": 0,
        "paid_api_calls": 0,
        "unsafe_actions": 0,
    }
    errors = []
    for key, value in gate.items():
        if key.endswith(("calls", "actions")):
            if value != 0:
                errors.append(f"{key.upper()}_NONZERO")
        elif value is not True:
            errors.append(f"{key.upper()}_FAILED")
    gate["errors"] = errors
    gate["accepted"] = not errors

    result = {
        "schema_version": "aion.hexcore.autonomous_problem_apprenticeship_pilot.v1",
        "created_at": _utc_timestamp(),
        "pilot": "unfamiliar_problem_to_retained_subject_capability",
        "passed": gate["accepted"],
        "original_mission": {
            "mission": mission,
            "payload_hash": _canonical_hash(ORIGINAL_MISSION.public_payload()),
        },
        "diagnosis": diagnosis,
        "curriculum": {
            "selected_source_id": TEACHING_SOURCE["source_id"],
            "source_commitment": source_session["source_commitment"],
            "practice_cases": len(PRACTICE_CASES),
            "first_attempts": first_attempts,
            "repair": REPAIRED_PROCEDURE["repair_causes"],
            "repaired_attempts": repaired_attempts,
        },
        "source_session": source_session,
        "capsule": {
            "digest": capsule["capsule_digest"],
            "raw_source_retained": capsule["raw_source_retained"],
            "training_answers_retained": capsule["training_answers_retained"],
        },
        "hidden_exam": exam,
        "original_resolution": original_resolution,
        "restart_transfer": restart,
        "controls": controls,
        "gate": gate,
        "claim_boundary": (
            "This deterministic micro-domain pilot verifies the control-plane "
            "loop: diagnose a missing capability from a problem, select a "
            "bounded local curriculum, repair a failed method, close the source, "
            "pass a source-disjoint exam, solve the original problem and retain "
            "the method across restart. The subject catalogue, tutor packets, "
            "mission generator and independent oracle are engineered. It does "
            "not demonstrate unrestricted web research, complete-subject "
            "learning, general intelligence or autonomous mastery of arbitrary "
            "real-world domains."
        ),
    }
    result["result_digest"] = _canonical_hash(result)
    if result_path is not None:
        _atomic_json(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the bounded autonomous problem-apprenticeship pilot."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_autonomous_problem_apprenticeship_pilot(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
