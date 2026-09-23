from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.experience_compiled_project_intelligence import run


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_experience_compiler_generalises_without_family_labels(tmp_path: Path) -> None:
    objectives = []
    authorities = (
        "later_public_technical_source",
        "fresh_subprocess_plus_later_public_row",
        "delayed_deterministic_integer_checker",
        "delayed_immutable_source_reread",
        "later_public_environmental_sensor",
        "later_multi_authority_acquisition_row",
    )
    source = tmp_path / "source.txt"; source.write_text("verified passage", encoding="utf-8")
    import hashlib
    for cycle in range(22):
        for index, authority in enumerate(authorities):
            base = tmp_path / "artifacts" / f"{cycle}_{index}"; base.mkdir(parents=True)
            if authority == "later_public_technical_source":
                artifact = base / "brief.md"; artifact.write_text("Source: public\nObserved value: stable", encoding="utf-8")
                objective, criterion = "Assess a later technical revision", "later source confirms revision"
                evaluation = {"authority": authority, "passed": True, "expected": "stable", "observed": "stable"}
            elif authority == "fresh_subprocess_plus_later_public_row":
                artifact = base / "guard.py"
                artifact.write_text("import json,sys\nr=json.load(open(sys.argv[1]));raise SystemExit(0 if r['ok'] else 1)\n", encoding="utf-8")
                _write(base / "later_genuine.json", {"ok": True}); _write(base / "later_tampered.json", {"ok": False})
                objective, criterion = "Construct an executable guard", "fresh subprocess accepts genuine and rejects tampered"
                evaluation = {"authority": authority, "passed": True}
            elif authority == "delayed_deterministic_integer_checker":
                artifact = base / "witness.json"; n = cycle + 3
                _write(artifact, {"n": n, "constructed_sum": n*n, "claimed_closed_form": n*n})
                objective, criterion = "Certify a finite odd number witness", "delayed deterministic checker recomputes identity"
                evaluation = {"authority": authority, "passed": True}
            elif authority == "delayed_immutable_source_reread":
                artifact = base / "span.json"; raw = source.read_bytes()
                _write(artifact, {"source_path": str(source), "source_sha256": hashlib.sha256(raw).hexdigest(),
                                  "start": 0, "end": len(raw), "exact_span": raw.decode()})
                objective, criterion = "Recover exact provenance passage", "delayed immutable source reread recovers exact span"
                evaluation = {"authority": authority, "passed": True}
            elif authority == "later_public_environmental_sensor":
                artifact = base / "envelope.json"; _write(artifact, {"temperature_min": 0, "temperature_max": 50, "wind_max": 30})
                objective, criterion = "Make bounded environmental decision", "later public sensor remains inside envelope"
                evaluation = {"authority": authority, "passed": True, "temperature": 25, "wind": 5}
            else:
                artifact = base / "availability.json"; _write(artifact, {"minimum_reachable_authorities": 3, "latency_ceiling_seconds": 5})
                objective, criterion = "Assess multi authority availability", "later row retains reachable authorities and latency ceiling"
                evaluation = {"authority": authority, "passed": True, "reachable_authorities": 4, "maximum_latency_seconds": 1}
            objectives.append({"objective_id": f"p{cycle}_{index}", "objective": objective,
                               "success_criterion": criterion, "family": "hidden_family",
                               "status": "consequence_confirmed", "closed_at": f"2026-08-02T{cycle:02d}:00:00+00:00",
                               "artifact": {"path": str(artifact)}, "evaluation": evaluation})
    _write(tmp_path / "backend/modules/hexcore/data/open_useful_objectives/state.json", {"objectives": objectives})
    tier6_goal = "tier6_research_goal"
    _write(tmp_path / "data/goals/goals.json", {"completed": [], "goals": [{
        "name": tier6_goal, "created_at": "2026-08-02T21:30:00+00:00",
    }]})
    tier6_contract = {
            "objective_id": tier6_goal, "family": "research_investigation",
            "difficulty_tier": 6,
            "prospective_compiler_requirement": "compile_before_outcome",
        }
    _write(tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json", {
        "active_portfolio": [tier6_contract],
        "generations": [{"commitment": {"portfolio": [tier6_contract]}}],
    })
    prospective_artifact = tmp_path / "prospective.md"
    prospective_artifact.write_text("Source: public\nObserved value: before", encoding="utf-8")
    prospective = {"objective_id": "future_project", "family": "research_investigation",
                   "objective": "Assess a later technical revision", "success_criterion": "later source confirms revision",
                   "status": "waiting_for_later_authority", "created_at": "2026-08-02T22:00:00+00:00",
                   "artifact": {"path": str(prospective_artifact)}, "evaluation": None}
    objectives.append(prospective)
    _write(tmp_path / "backend/modules/hexcore/data/open_useful_objectives/state.json", {"objectives": objectives})
    projects = []
    for index in range(3):
        projects.append({"project_id": f"s{index}", "status": "consequence_confirmed",
            "plan": {"task_order": ["validate_schema", "compare_revisions", "separate_origin",
                                      "rank_information_actions", "emit_provenance_report", "update_competency"],
                     "expected_envelope": {"one": {}, "two": {}},
                     "capability_bundle": ["software_engineering", "mathematics"],
                     "commitment_sha256": f"hash{index}"},
            "evaluation": {"passed": True, "internal_self_repair_triggered": False,
                           "authorities_checked": ["one", "two"],
                           "ordered_actions": [{"action": "retain_and_monitor"}]}})
    _write(tmp_path / "backend/modules/hexcore/data/situated_cross_domain_projects/state.json", {"projects": projects})
    result = run(repo_root=tmp_path, state_path=tmp_path / "state.json", result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["sealed_projects"] >= 50
    assert result["gate"]["sealed_program_selection_correct"] == result["gate"]["sealed_projects"]
    assert result["gate"]["attempt_reduction_vs_cold"] >= 0.60
    assert result["gate"]["answer_book_control_success"] == 0
    assert result["gate"]["multi_authority_programs_passed"] == 3
    assert result["gate"]["family_labels_visible_during_sealed"] == 0
    assert result["gate"]["ood_abstention"] is True
    assert result["gate"]["prospective_precommitments"] == 1
    assert result["gate"]["prospective_later_receipts"] == 0
    prospective["status"] = "consequence_confirmed"
    prospective["evaluation"] = {"authority": "later_public_technical_source", "passed": True,
                                  "expected": "before", "observed": "before"}
    prospective["later_outcome_sha256"] = "later-hash"
    _write(tmp_path / "backend/modules/hexcore/data/open_useful_objectives/state.json", {"objectives": objectives})
    closed = run(repo_root=tmp_path, state_path=tmp_path / "state.json", result_path=tmp_path / "result.json")
    assert closed["gate"]["prospective_later_receipts"] == 1
    assert closed["prospective"]["receipts"][0]["goal_id"] == tier6_goal
