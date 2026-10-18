from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore import academy_executor_acquisition_worker as worker_module
from backend.modules.hexcore.academy_executor_acquisition_worker import AcademyExecutorAcquisitionWorker
from backend.modules.hexcore.guided_foundation_academy import GuidedFoundationAcademy


REPO_ROOT = Path(__file__).resolve().parents[2]


def _academy_with_request(tmp_path: Path) -> GuidedFoundationAcademy:
    academy = GuidedFoundationAcademy(
        repo_root=REPO_ROOT, state_path=tmp_path / "academy.json",
        teacher_cache_path=tmp_path / "teacher.json",
    )
    academy.state["modules"]["algorithms_data_structures"]["status"] = "passed_bounded"
    advanced = academy.state["modules"]["advanced_python"]
    advanced["status"] = "executor_required"
    advanced["contract"] = {
        "commitment": "advanced-contract", "pass_threshold": 0.9,
        "requires_transfer": True, "requires_delayed_retention": True,
    }
    academy.state["executor_requests"].append({
        "request_id": "request-advanced", "module_id": "advanced_python",
        "authorities": ["python_runtime", "type_checker", "package_tests"],
        "status": "open", "proposal_only": True,
    })
    academy._save()
    return academy


def test_ready_module_is_selected_before_a_blocked_executor(tmp_path):
    academy = _academy_with_request(tmp_path)
    assert academy.state["modules"]["testing_debugging"]["status"] == "ready"
    assert academy.next_module()["module_id"] == "testing_debugging"


def test_worker_consumes_verified_result_and_registers_receipt(tmp_path, monkeypatch):
    academy = _academy_with_request(tmp_path)

    def fake_runner(repo_root, state_path, result_path):
        del repo_root, state_path
        result = {
            "procedure_id": "procedure_test_advanced_executor",
            "passed": True,
            "gate": {"accepted": True, "score": 1.0, "source_disjoint_transfer": True},
            "restart": {"champion_retained": True},
        }
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result), encoding="utf-8")
        return result

    monkeypatch.setitem(worker_module.RUNNERS, "advanced_python", fake_runner)
    worker = AcademyExecutorAcquisitionWorker(
        repo_root=tmp_path, academy_state_path=academy.state_path,
        state_path=tmp_path / "worker.json",
    )
    outcome = worker.step()
    assert outcome["progressed"] is True
    restarted = GuidedFoundationAcademy(repo_root=tmp_path, state_path=academy.state_path)
    assert restarted.state["modules"]["advanced_python"]["status"] == "passed_bounded"
    assert restarted.state["executor_requests"][0]["status"] == "satisfied"
    assert worker.status()["stalled"] is False


def test_missing_runner_becomes_visible_blocker_not_false_activity(tmp_path, monkeypatch):
    academy = _academy_with_request(tmp_path)
    monkeypatch.delitem(worker_module.RUNNERS, "advanced_python")
    worker = AcademyExecutorAcquisitionWorker(
        repo_root=tmp_path, academy_state_path=academy.state_path,
        state_path=tmp_path / "worker.json",
    )
    outcomes = [worker.step() for _ in range(3)]
    assert outcomes[-1]["status"] == "blocked_no_verified_executor"
    assert worker.status()["stalled"] is True
    assert worker.status()["consecutive_no_progress"] == 3
