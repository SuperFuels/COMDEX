from __future__ import annotations

import base64
import copy
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.aion_flow_authority import AionFlowWorkspaceAuthority
from backend.modules.aion_business.runtime.aion_flow_production import AionFlowProductionService
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository


def graph(version: str = "one"):
    return {
        "workflow_id": "wf-production",
        "name": version,
        "nodes": [
            {"id": "ingress", "type": "AION Brain", "config": {"purpose": "test"}},
            {"id": "receipt", "type": "Verification", "config": {}},
        ],
        "edges": [{"from": "ingress", "to": "receipt"}],
        "groups": [{"id": "group-1", "nodes": ["ingress", "receipt"]}],
        "subflows": [],
    }


def actor(person_id="person.owner", role="untrusted-browser-claim"):
    return {"person_id": person_id, "role": role, "organisation_id": "space-1", "workspace_id": "space-1"}


def service(tmp_path):
    workspaces = WorkspaceRepository(tmp_path / "workspaces")
    workspaces.save(WorkspaceSpec(id="space-1", name="Test", business_type="test", owner="person.owner"))
    organisations = OrganizationAuthorityService(BusinessContainerRepository(tmp_path / "containers"))
    model = organisations.empty("space-1")
    model["people"] = [
        {"id": "person.owner", "name": "Owner", "status": "active", "employment_type": "owner", "role_ids": ["role.owner_director"], "department_ids": []},
        {"id": "person.viewer", "name": "Viewer", "status": "active", "employment_type": "employee", "role_ids": ["role.employee"], "department_ids": []},
    ]
    organisations.save("space-1", model, expected_revision=0)
    authority = AionFlowWorkspaceAuthority(workspaces=workspaces, organisations=organisations)
    return AionFlowProductionService(tmp_path / "production", authority=authority)


def test_least_privilege_and_responsive_review_contract(tmp_path):
    production = service(tmp_path)
    denied = production.qualify(graph(), actor=actor("person.viewer", "owner"), mode="author")
    assert denied["ok"] is False
    assert "canonical_authority_denied:capability_not_granted" in denied["errors"]
    assert denied["authority"]["claimed_role_ignored"] is True
    review = production.qualify(graph(), actor=actor(), mode="review")
    assert review["ok"] is True
    assert review["review_only"] is True
    assert review["responsive_surfaces"]["mobile_read_only"] is True


def test_signed_revision_conflict_and_diff(tmp_path):
    production = service(tmp_path)
    first = production.commit(graph(), actor=actor(), base_revision=0)
    assert first["revision"] == 1 and first["mother_signature"]
    changed = graph("two"); changed["nodes"].append({"id": "validator", "type": "Evidence", "config": {}})
    changed["edges"] = [{"from": "ingress", "to": "validator"}, {"from": "validator", "to": "receipt"}]
    second = production.commit(changed, actor=actor(), base_revision=1)
    assert second["revision"] == 2
    assert production.diff("wf-production", 1, 2, actor=actor())["added_nodes"] == ["validator"]
    with pytest.raises(RuntimeError, match="revision_conflict"):
        production.commit(changed, actor=actor(), base_revision=1)


def test_encrypted_export_import_and_wrong_password(tmp_path):
    production = service(tmp_path)
    package = production.encrypted_export(graph(), password="a-strong-passphrase", actor=actor())
    assert "wf-production" not in package["ciphertext"]
    imported = production.encrypted_import(package, password="a-strong-passphrase", actor=actor())
    assert imported["graph"]["workflow_id"] == "wf-production"
    assert imported["authority_granted"] is False
    with pytest.raises(Exception):
        production.encrypted_import(package, password="wrong-password-value", actor=actor())


def test_zero_content_telemetry_and_large_graph_benchmark(tmp_path):
    production = service(tmp_path)
    payload = graph(); payload["nodes"][0]["config"]["secret_business_text"] = "DO-NOT-LEAK"
    telemetry = production.telemetry(payload, actor=actor(), operational={"status_counts": {"verified": 2}, "latency_buckets_ms": [10, 25]})
    assert telemetry["contains_content"] is False
    assert "DO-NOT-LEAK" not in str(telemetry)
    measured = production.benchmark(payload, actor=actor(), iterations=10)
    assert measured["iterations"] == 10
    assert measured["external_writes"] == 0


def test_signed_load_qualification_covers_large_parallel_and_recovery_profiles(tmp_path):
    production = service(tmp_path)
    report = production.load_qualification(
        actor=actor(), large_nodes=150, parallel_routes=24, checkpoints=20
    )
    assert report["passed"] is True
    assert set(report["profiles"]) == {"large_graph", "parallel_routes", "long_running"}
    assert report["profiles"]["large_graph"]["nodes"] == 150
    assert report["profiles"]["parallel_routes"]["deterministic"] is True
    assert report["profiles"]["long_running"]["recovered_sequence"] == 20
    assert report["external_writes"] == 0
    assert report["contains_customer_content"] is False
    unsigned = {key: value for key, value in report.items() if key not in {"mother_signature", "mother_public_key"}}
    assert DeviceIdentity.verify(
        report["mother_public_key"], canonical_bytes(unsigned), report["mother_signature"]
    )


def test_adversarial_graph_rejects_dangling_edges_and_excessive_size(tmp_path):
    production = service(tmp_path)
    bad = graph(); bad["edges"] = [{"from": "ingress", "to": "missing"}]
    assert "edge_target_missing" in production.qualify(bad, actor=actor())["errors"]
    oversized = graph(); oversized["nodes"] = [{"id": f"n-{index}"} for index in range(5001)]; oversized["edges"] = []
    assert "graph_production_limit_exceeded" in production.qualify(oversized, actor=actor())["errors"]


def test_cross_workspace_and_forged_role_fail_closed(tmp_path):
    production = service(tmp_path)
    forged = actor("person.viewer", "owner")
    with pytest.raises(PermissionError, match="capability_not_granted"):
        production.commit(graph(), actor=forged, base_revision=0)
    wrong_workspace = {**actor(), "workspace_id": "missing-space", "organisation_id": "missing-space"}
    denied = production.qualify(graph(), actor=wrong_workspace)
    assert "canonical_authority_denied:workspace_not_found" in denied["errors"]


def test_same_workflow_id_is_isolated_between_canonical_workspaces(tmp_path):
    production = service(tmp_path)
    production.authority.workspaces.save(WorkspaceSpec(id="space-2", name="Second", business_type="test", owner="person.second"))
    model = production.authority.organisations.empty("space-2")
    model["people"] = [{"id": "person.second", "name": "Second owner", "status": "active", "employment_type": "owner", "role_ids": ["role.owner_director"], "department_ids": []}]
    production.authority.organisations.save("space-2", model, expected_revision=0)
    second_actor = {"person_id": "person.second", "workspace_id": "space-2", "organisation_id": "space-2", "role": "viewer"}

    production.commit(graph("first workspace"), actor=actor(), base_revision=0)
    production.commit(graph("second workspace"), actor=second_actor, base_revision=0)

    assert production.history("wf-production", actor=actor())["revision"] == 1
    assert production.history("wf-production", actor=second_actor)["revision"] == 1


@pytest.mark.parametrize(
    "mutation,expected",
    [
        (lambda value: value.update(nodes=["not-a-node"]), "node_record_invalid"),
        (lambda value: value.update(edges=["not-an-edge"]), "edge_record_invalid"),
        (lambda value: value.update(workflow_id="unsafe:scope"), "workflow_id_invalid"),
        (lambda value: value.update(nodes={"id": "not-a-list"}), "graph_nodes_invalid"),
    ],
)
def test_malformed_graphs_fail_closed_without_server_errors(tmp_path, mutation, expected):
    production = service(tmp_path)
    payload = graph()
    mutation(payload)
    result = production.qualify(payload, actor=actor())
    assert result["ok"] is False
    assert expected in result["errors"]
    assert result["graph_hash"] is None


def test_deep_cyclic_and_oversized_graph_content_is_rejected_before_hashing(tmp_path):
    production = service(tmp_path)
    deep = graph()
    nested = {}
    deep["nodes"][0]["config"] = nested
    for _ in range(40):
        nested["next"] = {}
        nested = nested["next"]
    assert "graph_structure_bounds_exceeded" in production.qualify(deep, actor=actor())["errors"]

    cyclic = graph()
    cyclic["nodes"][0]["config"] = cyclic
    assert "graph_structure_bounds_exceeded" in production.qualify(cyclic, actor=actor())["errors"]

    huge = graph()
    huge["nodes"][0]["config"]["prompt"] = "x" * (1024 * 1024 + 1)
    assert "graph_structure_bounds_exceeded" in production.qualify(huge, actor=actor())["errors"]


def test_import_rejects_untrusted_headers_encoding_and_transfer_bounds(tmp_path):
    production = service(tmp_path)
    package = production.encrypted_export(graph(), password="a-strong-passphrase", actor=actor())

    bad_header = copy.deepcopy(package)
    bad_header["header"]["kdf"] = "attacker-controlled-kdf"
    with pytest.raises(ValueError, match="import_header_not_supported"):
        production.encrypted_import(bad_header, password="a-strong-passphrase", actor=actor())

    bad_encoding = copy.deepcopy(package)
    bad_encoding["nonce"] = "not valid base64!!"
    with pytest.raises(ValueError, match="import_encoding_invalid"):
        production.encrypted_import(bad_encoding, password="a-strong-passphrase", actor=actor())

    oversized = copy.deepcopy(package)
    oversized["ciphertext"] = base64.b64encode(b"x" * (8 * 1024 * 1024 + 1)).decode()
    with pytest.raises(ValueError, match="import_transfer_bounds_exceeded"):
        production.encrypted_import(oversized, password="a-strong-passphrase", actor=actor())

    with pytest.raises(ValueError, match="import_password_minimum"):
        production.encrypted_import(package, password="short", actor=actor())


def test_concurrent_writers_cannot_both_commit_the_same_base_revision(tmp_path):
    first = service(tmp_path)
    second = AionFlowProductionService(tmp_path / "production", authority=first.authority)
    barrier = threading.Barrier(2)

    def commit_once(runtime, label):
        barrier.wait(timeout=5)
        try:
            return ("committed", runtime.commit(graph(label), actor=actor(), base_revision=0)["revision"])
        except RuntimeError as error:
            return ("blocked", str(error))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda args: commit_once(*args), [(first, "first"), (second, "second")]))

    assert sorted(item[0] for item in results) == ["blocked", "committed"]
    assert first.history("wf-production", actor=actor())["revision"] == 1
