from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.modules.hexcore.standalone_task_governance import (
    current_task_intelligence,
    governed_standalone_task,
    migration_status,
)


def test_standalone_task_retrieves_context_and_does_not_invent_memory_use(tmp_path):
    assert current_task_intelligence() == {}
    with governed_standalone_task(
        repo_root=tmp_path,
        service_id="test_service",
        task_text="Build an HTML website",
        operation_id="operation-1",
    ) as task:
        assert task.context["status"] == "prepared"
        assert current_task_intelligence()["trace_id"] == task.context["trace_id"]
        result = task.finish({"status": "passed"}, verified=False)
        assert result["recorded"] is True
        assert result["outcome"]["used_memory_ids"] == []
        assert result["outcome"]["used_skill_ids"] == []
    assert current_task_intelligence() == {}


def test_concurrent_service_traces_are_not_lost(tmp_path):
    def execute(index):
        with governed_standalone_task(
            repo_root=tmp_path,
            service_id=f"service-{index}",
            task_text=f"Execute governed operation {index}",
            operation_id=f"operation-{index}",
        ) as task:
            task.finish({"status": "complete", "index": index}, verified=False)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(execute, range(24)))

    state = json.loads(
        (tmp_path / "data/hexcore/first_class_cognitive_control_plane.json").read_text()
    )
    assert len(state["task_traces"]) == 24
    assert len(state["retrieval_outcomes"]) == 24


def test_every_active_supervised_learning_entrypoint_is_migrated():
    repo_root = Path(__file__).resolve().parents[2]
    status = migration_status(repo_root)

    assert status["status"] == "fully_migrated"
    assert status["active_service_entrypoints"] == 8
    assert status["migrated_entrypoints"] == 8
    assert status["unmigrated_entrypoints"] == 0
