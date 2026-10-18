import json
from pathlib import Path

from backend.modules.hexcore.governed_teacher_mastery_cycle import (
    INITIAL_CANDIDATE,
    REMEDIATED_CANDIDATE,
    SEALED_TEST,
    TeacherBroker,
    _criticise_teacher_advisory,
    _exam_contract,
    _execute_candidate,
    _security_audit,
    run,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_teacher_is_cached_proposal_only_and_exam_is_separate(tmp_path):
    broker = TeacherBroker(tmp_path / "teacher.json")
    first = broker.propose(subject="Python Core", target="proficient bounded")
    second = broker.propose(subject="Python Core", target="proficient bounded")
    contract = _exam_contract()
    assert first["proposal_only"] is True
    assert len(first["modules"]) == 12
    assert second["cache_hit"] is True
    assert first["proposal_hash"] == second["proposal_hash"]
    assert contract["teacher_cannot_read_answer_key"] is True
    assert contract["commitment"] not in json.dumps(first)


def test_sealed_exam_rejects_plausible_bool_bug_then_accepts_remediation():
    initial = _execute_candidate(INITIAL_CANDIDATE, SEALED_TEST)
    final = _execute_candidate(REMEDIATED_CANDIDATE, SEALED_TEST)
    assert initial["passed"] is False
    assert final["passed"] is True


def test_security_authority_rejects_unsafe_programs():
    assert _security_audit(REMEDIATED_CANDIDATE)["safe"] is True
    for source in (
        "def f(x): return eval(x)",
        "import subprocess\ndef f(): subprocess.run(['sh'])",
        "import socket\ndef f(): return socket.socket()",
        "from pathlib import Path\ndef f(p): Path(p).unlink()",
    ):
        assert _security_audit(source)["safe"] is False


def test_teacher_critic_refuses_incomplete_advisory_as_core_curriculum():
    criticism = _criticise_teacher_advisory({
        "content": {"modules": ["Fundamentals", "Data Structures", "Web Development"]}
    })
    assert criticism["status"] == "supplement_only"
    assert "security" in criticism["missing_requirements"]
    assert criticism["may_authorize_certificate"] is False


def test_full_python_core_cycle_promotes_control_plane_not_mastery(tmp_path):
    result = run(
        repo_root=REPO_ROOT,
        state_path=tmp_path / "state/state.json",
        result_path=tmp_path / "result.json",
        cache_path=tmp_path / "state/teacher.json",
    )
    assert result["passed"] is True
    assert result["gate"]["overall_score"] >= 0.90
    assert result["gate"]["initial_challenger_rejected"] is True
    assert result["gate"]["malicious_rejected"] == result["gate"]["malicious_total"] == 6
    assert result["certificate"]["level"] == "operational_bounded"
    assert result["teacher"]["live_advisory"]["exam_material_shared"] is False
    assert result["certificate"]["mastery_claim_authorized"] is False
    assert result["certificate"]["elapsed_retention_status"] == "scheduled_not_yet_elapsed"
    assert json.loads((tmp_path / "result.json").read_text())["passed"] is True
