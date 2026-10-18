import pytest

from backend.modules.aion_fabric.browser_harness import (
    BrowserHarnessStore,
    browser_tool_contract,
    extract_browser_plan,
)


def test_contract_is_provider_neutral() -> None:
    contract = browser_tool_contract()
    assert contract["provider_neutral"] is True
    assert contract["planner_role"] == "approved_connected_model"
    assert "submit" in contract["approval_required_operations"]


def test_extracts_structured_model_proposal() -> None:
    proposal = extract_browser_plan(
        '<AION_BROWSER_PLAN>{"objective":"Read example",'
        '"steps":[{"operation":"open_page","target":{"url":"https://example.com"}},'
        '{"operation":"read_page","target":{"selector":"main"}}]}</AION_BROWSER_PLAN>'
    )
    assert proposal is not None
    assert proposal["steps"][1]["operation"] == "read_page"


def test_model_shorthand_targets_are_normalised(tmp_path) -> None:
    plan = BrowserHarnessStore(tmp_path).create_plan(
        proposal={
            "objective": "Read example",
            "steps": [
                {"operation": "open_page", "target": "https://example.com"},
                {"operation": "read_page", "target": "main"},
            ],
        },
        provider="approved-provider",
        model="approved-model",
        workspace_id="workspace-a",
        now=50,
    )
    assert plan["steps"][0]["target"]["url"] == "https://example.com"
    assert plan["steps"][1]["target"]["selector"] == "main"


def test_read_only_plan_gets_one_time_grant_and_receipt(tmp_path) -> None:
    store = BrowserHarnessStore(tmp_path)
    plan = store.create_plan(
        proposal={
            "objective": "Read example",
            "steps": [
                {"operation": "open_page", "target": {"url": "https://example.com"}},
                {"operation": "read_page", "target": {"selector": "main"}},
            ],
        },
        provider="local_model",
        model="approved-model-a",
        workspace_id="workspace-a",
        now=100,
    )
    assert plan["state"] == "ready"
    assert plan["provider_neutral"] is True
    redeemed = store.redeem_grant(
        grant_id=plan["grant_id"], execution_token=plan["execution_token"], now=101
    )
    assert redeemed["ok"] is True
    with pytest.raises(PermissionError, match="already_redeemed"):
        store.redeem_grant(
            grant_id=plan["grant_id"], execution_token=plan["execution_token"], now=102
        )
    receipt = store.record_receipt(
        grant_id=plan["grant_id"], result={"ok": True, "status": "completed"}, now=103
    )
    assert receipt["receipt_hash"].startswith("sha256:")
    assert receipt["provider"] == "local_model"


def test_write_plan_requires_exact_user_approval(tmp_path) -> None:
    store = BrowserHarnessStore(tmp_path)
    plan = store.create_plan(
        proposal={
            "objective": "Fill a form",
            "steps": [
                {"operation": "open_page", "target": {"url": "https://example.com/form"}},
                {"operation": "type_text", "target": {"selector": "input[name=email]"}, "value": "owner@example.com"},
                {"operation": "submit", "target": {"selector": "button[type=submit]"}},
            ],
        },
        provider="gemini",
        model="gemini-approved",
        workspace_id="workspace-a",
        now=200,
    )
    assert plan["state"] == "awaiting_user_approval"
    assert plan["grant_id"] is None
    with pytest.raises(ValueError, match="exact_browser_step_approval_required"):
        store.approve_plan(
            plan_id=plan["plan_id"],
            approved_step_ids=["step_2"],
            approved_by="owner",
            now=201,
        )
    approved = store.approve_plan(
        plan_id=plan["plan_id"],
        approved_step_ids=["step_2", "step_3"],
        approved_by="owner",
        now=202,
    )
    assert approved["state"] == "ready"
    assert approved["execution_token"]
    assert all(item["allowed"] for item in approved["gateway_evaluations"])


def test_model_never_bypasses_gateway(tmp_path) -> None:
    store = BrowserHarnessStore(tmp_path)
    with pytest.raises(ValueError, match="browser_url_credentials_blocked"):
        store.create_plan(
            proposal={"steps": [{"operation": "open_page", "target": {"url": "https://user:pass@example.com"}}]},
            provider="any-approved-model",
            model="any-approved-model",
            workspace_id="workspace-a",
        )
