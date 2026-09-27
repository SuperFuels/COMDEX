from __future__ import annotations

from pathlib import Path

from backend.modules.aion_business.runtime.aion_flow_execution import (
    AionFlowExecutionService,
    AionFlowRunRepository,
)


def actor():
    return {
        "person_id": "person-owner",
        "organisation_id": "org-one",
        "workspace_id": "boardroom",
        "role": "owner",
        "purpose": "operations",
    }


def policy():
    return {
        "allowed_roles": ["owner"],
        "allowed_purposes": ["operations"],
        "maximum_external_classification": "internal",
        "allowed_destinations": [],
        "allowed_residencies": [],
    }


def read_graph():
    return {
        "flow_id": "read-business-status",
        "nodes": [
            {"id": "admit", "type": "aion_ingress"},
            {"id": "govern", "type": "policy"},
            {"id": "read", "type": "capability", "capability_id": "business.status.read"},
            {"id": "verify", "type": "verification", "expected_outcome": "status returned"},
            {"id": "receipt", "type": "aion_receipt"},
        ],
        "edges": [
            {"source": "admit", "target": "govern"},
            {"source": "govern", "target": "read"},
            {"source": "read", "target": "verify"},
            {"source": "verify", "target": "receipt"},
        ],
    }


def write_graph():
    value = read_graph()
    value["flow_id"] = "approved-write"
    value["nodes"].insert(
        2,
        {
            "id": "approve",
            "type": "approval",
            "requires_approval": True,
            "approval_id": "approval-one",
            "exact_scope_hash": "scope-one",
        },
    )
    value["nodes"][3].update(
        {
            "capability_id": "crm.note.create",
            "consequential": True,
            "idempotency_key": "customer-note-one",
        }
    )
    value["edges"] = [
        {"source": "admit", "target": "govern"},
        {"source": "govern", "target": "approve"},
        {"source": "approve", "target": "read"},
        {"source": "read", "target": "verify"},
        {"source": "verify", "target": "receipt"},
    ]
    return value


def service(tmp_path: Path, executor=None):
    return AionFlowExecutionService(
        repository=AionFlowRunRepository(tmp_path / "runs"),
        capability_executor=executor,
    )


def test_read_only_flow_compiles_simulates_executes_and_issues_receipt(tmp_path):
    runtime = service(tmp_path)
    prepared = runtime.prepare(graph=read_graph(), actor=actor(), policy=policy(), inputs={"region": "south"})
    assert prepared["ok"] is True
    assert prepared["executed"] is False
    assert prepared["capsule"]["schema_version"] == "aion.workflow_capsule.v1"
    assert prepared["simulation"]["external_writes_performed"] == 0
    assert prepared["dry_run"]["predicted"]["estimated_cost"] == 0

    result = runtime.execute(
        prepared=prepared,
        review_hash=prepared["review"]["review_hash"],
        exact_confirmed=True,
        inputs={"region": "south"},
    )
    assert result["ok"] is True
    assert result["run"]["status"] == "verified"
    assert all(node["status"] == "verified" for node in result["run"]["nodes"])
    assert result["receipt"]["schema_version"] == "aion.intelligence_route_receipt.v1"
    assert result["receipt"]["external_effects_verified"] is True


def test_write_requires_exact_approval_and_executes_once_through_injected_adapter(tmp_path):
    calls = []

    def execute_capability(**kwargs):
        calls.append(kwargs["idempotency_key"])
        return {"ok": True, "verified": True, "external_effect_performed": True, "provider_receipt": "provider-123"}

    runtime = service(tmp_path, execute_capability)
    prepared = runtime.prepare(
        graph=write_graph(),
        actor=actor(),
        policy=policy(),
        approvals=[{"approval_id": "approval-one", "approved": True, "scope_hash": "scope-one", "approver_person_id": "person-owner"}],
    )
    assert prepared["review"]["executable"] is True

    blocked = runtime.execute(prepared=prepared, review_hash="wrong", exact_confirmed=True)
    assert blocked["error"] == "exact_review_required"
    assert calls == []

    result = runtime.execute(
        prepared=prepared,
        review_hash=prepared["review"]["review_hash"],
        exact_confirmed=True,
    )
    assert result["ok"] is True
    assert calls == ["customer-note-one"]
    assert result["receipt"]["status"] == "verified"
    assert result["receipt"]["external_effects_verified"] is True


def test_prepare_fails_closed_without_approval(tmp_path):
    prepared = service(tmp_path).prepare(graph=write_graph(), actor=actor(), policy=policy())
    assert prepared["governance"]["allowed"] is False
    assert prepared["review"]["executable"] is False
    assert any("Private approval" in item for item in prepared["governance"]["blocked_explanations"])

    authorized = service(tmp_path).authorize_prepared(
        prepared=prepared,
        review_hash=prepared["review"]["review_hash"],
        approver_person_id="person-owner",
        exact_confirmed=True,
    )
    assert authorized["ok"] is True
    assert authorized["prepared"]["review"]["executable"] is True


def test_restart_recovery_moves_running_node_to_safe_wait_and_resumes(tmp_path):
    runtime = service(tmp_path)
    prepared = runtime.prepare(graph=read_graph(), actor=actor(), policy=policy())
    interrupted = {
        "schema_version": "aion.flow.run.v1",
        "run_id": "aflow_interrupted",
        "flow_id": prepared["manifest"]["flow_id"],
        "manifest_hash": prepared["manifest"]["manifest_hash"],
        "review_hash": prepared["review"]["review_hash"],
        "status": "running",
        "attempt": 1,
        "nodes": [
            {"node_id": node["id"], "kind": node["type"], "sequence": index + 1, "status": "running" if index == 1 else "queued"}
            for index, node in enumerate(runtime._ordered_nodes(prepared["manifest"]))
        ],
        "events": [],
        "compensations": [],
    }
    runtime.repository.save(interrupted)
    recovered = runtime.recover_interrupted()
    assert recovered["recovered_run_ids"] == ["aflow_interrupted"]
    waiting = runtime.repository.get("aflow_interrupted")
    assert waiting["status"] == "waiting"
    assert all(node["status"] != "running" for node in waiting["nodes"])
    resumed = runtime.control("aflow_interrupted", "resume", prepared=prepared)
    assert resumed["ok"] is True
    assert resumed["run"]["status"] == "verified"
    assert resumed["run"]["attempt"] == 2


def test_capability_can_pause_for_department_computer_without_running_downstream_nodes(tmp_path):
    calls = []

    def execute_capability(**kwargs):
        calls.append(kwargs["idempotency_key"])
        return {
            "ok": False,
            "verified": False,
            "waiting": True,
            "status": "waiting_for_department_computer",
            "workflow_skill_run_id": "workflow_skill_run_one",
            "external_effect_performed": False,
        }

    runtime = service(tmp_path, execute_capability)
    prepared = runtime.prepare(graph=read_graph(), actor=actor(), policy=policy())
    result = runtime.execute(
        prepared=prepared,
        review_hash=prepared["review"]["review_hash"],
        exact_confirmed=True,
    )
    assert result["ok"] is True
    assert result["waiting"] is True
    assert result["run"]["status"] == "waiting"
    states = {item["node_id"]: item["status"] for item in result["run"]["nodes"]}
    assert states["read"] == "waiting"
    assert states["verify"] == "queued"
    assert states["receipt"] == "queued"
    assert calls == [result["run"]["run_id"] + ":read"]

def test_secret_shaped_inputs_are_redacted_from_persisted_run(tmp_path):
    runtime = service(tmp_path)
    prepared = runtime.prepare(graph=read_graph(), actor=actor(), policy=policy())
    result = runtime.execute(
        prepared=prepared,
        review_hash=prepared["review"]["review_hash"],
        exact_confirmed=True,
        inputs={"api_key": "must-not-persist", "query": "safe"},
    )
    persisted = runtime.repository.get(result["run"]["run_id"])
    assert "must-not-persist" not in str(persisted)


def test_unbounded_cycle_is_rejected_before_execution(tmp_path):
    value = read_graph()
    value["edges"].append({"source": "verify", "target": "govern"})
    prepared = service(tmp_path).prepare(graph=value, actor=actor(), policy=policy())
    assert prepared["ok"] is False
    assert "unbounded_graph_cycle_not_allowed" in prepared["static_validation"]["errors"]


def test_capability_retry_is_bounded_and_receipt_does_not_claim_unperformed_effect(tmp_path):
    attempts = []

    def flaky(**kwargs):
        attempts.append(kwargs["idempotency_key"])
        return {"ok": len(attempts) == 2, "verified": len(attempts) == 2, "external_effect_performed": False}

    value = write_graph()
    next(node for node in value["nodes"] if node["type"] == "capability")["max_attempts"] = 2
    runtime = service(tmp_path, flaky)
    prepared = runtime.prepare(
        graph=value,
        actor=actor(),
        policy=policy(),
        approvals=[{"approval_id": "approval-one", "approved": True, "scope_hash": "scope-one", "approver_person_id": "person-owner"}],
    )
    result = runtime.execute(prepared=prepared, review_hash=prepared["review"]["review_hash"], exact_confirmed=True)
    assert result["ok"] is True
    assert len(attempts) == 2
    assert result["receipt"]["external_effects_verified"] is False
