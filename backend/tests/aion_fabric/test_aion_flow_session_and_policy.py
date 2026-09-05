from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.aion_flow_policy import AionFlowPolicyStore
from backend.modules.aion_business.runtime.aion_flow_session_authority import AionFlowSessionAuthority


def test_signed_session_is_body_bound_short_lived_and_single_use():
    clock = lambda: 1_700_000_000
    authority = AionFlowSessionAuthority(secret=b"s" * 32, clock=clock)
    body = b'{"exact":true}'
    headers = authority.sign_for_test(
        method="POST", target="/api/workflow-capsules/aion-flow/execute", body=body,
        device_id="desktop-one", person_id="person.owner", workspace_id="space-1",
    )
    session = authority.verify(method="POST", target="/api/workflow-capsules/aion-flow/execute", body=body, headers=headers)
    assert session.actor()["role"] == "canonical_authority"
    with pytest.raises(PermissionError, match="replayed"):
        authority.verify(method="POST", target="/api/workflow-capsules/aion-flow/execute", body=body, headers=headers)

    changed = authority.sign_for_test(
        method="POST", target="/api/workflow-capsules/aion-flow/execute", body=body,
        device_id="desktop-one", person_id="person.owner", workspace_id="space-1",
    )
    with pytest.raises(PermissionError, match="body_changed"):
        authority.verify(method="POST", target="/api/workflow-capsules/aion-flow/execute", body=b'{"exact":false}', headers=changed)


def test_signed_session_rejects_expiry_and_wrong_target():
    authority = AionFlowSessionAuthority(secret=b"s" * 32, clock=lambda: 1_700_000_100, maximum_age_seconds=60)
    headers = authority.sign_for_test(
        method="GET", target="/api/workflow-capsules/aion-flow/runs", body=b"",
        device_id="desktop-one", person_id="person.owner", workspace_id="space-1",
        issued_at=1_700_000_000,
    )
    with pytest.raises(PermissionError, match="expired"):
        authority.verify(method="GET", target="/api/workflow-capsules/aion-flow/runs", body=b"", headers=headers)

    current = AionFlowSessionAuthority(secret=b"s" * 32, clock=lambda: 1_700_000_000)
    wrong = current.sign_for_test(method="GET", target="/api/workflow-capsules/aion-flow/runs", body=b"", device_id="d", person_id="p", workspace_id="w")
    with pytest.raises(PermissionError, match="invalid"):
        current.verify(method="GET", target="/api/workflow-capsules/aion-flow/evaluations", body=b"", headers=wrong)


def test_customer_execution_policy_is_signed_versioned_and_fail_closed(tmp_path):
    store = AionFlowPolicyStore(tmp_path / "policies")
    default = store.effective("space-1")
    assert default["allowed_destinations"] == ["local"]
    assert default["external_writes_allowed"] is False
    assert store.governance_policy("space-1")["policy_receipt"]["policy_hash"] == default["policy_hash"]

    changed = store.configure(
        "space-1", {"allowed_destinations": ["local", "customer_private_cloud"], "max_cost_per_run": 2.5, "ignored": "no"},
        changed_by="person.owner", expected_revision=1,
    )
    assert changed["revision"] == 2
    assert "ignored" not in changed
    with pytest.raises(RuntimeError, match="revision_conflict"):
        store.configure("space-1", {}, changed_by="person.owner", expected_revision=1)

    path = tmp_path / "policies" / "space-1.json"
    tampered = json.loads(path.read_text())
    tampered["external_writes_allowed"] = True
    path.write_text(json.dumps(tampered))
    with pytest.raises(PermissionError, match="signature_invalid"):
        store.effective("space-1")


def test_desktop_renderer_uses_main_process_request_signing():
    source = open("desktop/mac/src/app.js", encoding="utf-8").read()
    preload = open("desktop/mac/electron/preload.js", encoding="utf-8").read()
    main = open("desktop/mac/electron/main.js", encoding="utf-8").read()
    assert "aionFlowAuthenticatedFetch" in source
    assert "signAionFlowRequest" in source
    assert 'ipcRenderer.invoke("aion-flow-sign-request"' in preload
    assert 'ipcMain.handle("aion-flow-sign-request"' in main
    assert "crypto.createHmac" in main
    assert "x-aion-flow-body-sha256" in main
