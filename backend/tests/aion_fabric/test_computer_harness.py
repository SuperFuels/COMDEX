from pathlib import Path

import pytest

from backend.modules.aion_fabric.computer_harness import (
    ComputerHarnessStore,
    coerce_computer_proposal,
    computer_tool_contract,
    computer_plan_repair_prompt,
    extract_computer_plan,
    infer_explicit_desktop_app,
    is_research_pages_request,
    normalise_computer_steps,
    proposal_from_attachment_request,
    proposal_from_user_request,
    proposal_from_research_evidence,
    research_query_from_pages_request,
)


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop" / "mac" / "src" / "app.js"
PRELOAD = ROOT / "desktop" / "mac" / "electron" / "preload.js"
MAIN = ROOT / "desktop" / "mac" / "electron" / "main.js"
RUNTIME = ROOT / "backend" / "modules" / "local_node" / "local_node_runtime.py"


def test_contract_is_provider_neutral_and_local_work_runs_with_receipts() -> None:
    contract = computer_tool_contract()
    assert contract["provider_neutral"] is True
    assert "open_app" in contract["operations"]
    assert "inspect_app" in contract["operations"]
    assert "click_control" in contract["operations"]
    assert "type_text" in contract["operations"]
    assert contract["approval_required_operations"] == []
    assert contract["default_local_write_policy"] == "execute_then_show_receipt"
    assert "sending email or messages" in contract["approval_required_effects"]


def test_extract_and_normalise_notes_plan() -> None:
    proposal = extract_computer_plan(
        '<AION_COMPUTER_PLAN>{"objective":"Write a note","steps":['
        '{"operation":"open_app","target":{"app":"Notes"}},'
        '{"operation":"create_note","target":{"app":"Notes"},"title":"Test","value":"Something"}'
        ']}</AION_COMPUTER_PLAN>'
    )
    assert proposal is not None
    steps = normalise_computer_steps(proposal["steps"])
    assert steps[0]["approval_required"] is False
    assert steps[1]["approval_required"] is False
    assert steps[1]["value"] == "Something"


def test_extract_accepts_small_model_marker_without_angle_or_closing_tag() -> None:
    proposal = extract_computer_plan(
        'AION_COMPUTER_PLAN>{"objective":"Open Pages","steps":["open_app","inspect_app"]}'
    )
    assert proposal == {"objective": "Open Pages", "steps": ["open_app", "inspect_app"]}


def test_unapproved_apps_are_rejected() -> None:
    with pytest.raises(ValueError, match="computer_app_blocked"):
        normalise_computer_steps([{"operation": "open_app", "target": {"app": "Terminal"}}])


def test_generic_reversible_local_plan_runs_without_interrupting_for_approval() -> None:
    steps = normalise_computer_steps([
        {"operation": "open_app", "target": {"app": "Pages"}},
        {"operation": "inspect_app", "target": {"app": "Pages"}, "max_elements": 60},
        {"operation": "click_control", "target": {"app": "Pages", "control": "New Document"}},
        {"operation": "type_text", "target": {"app": "Pages", "control": "Body"}, "value": "A governed draft."},
        {"operation": "verify_text", "target": {"app": "Pages"}, "expected_text": "A governed draft."},
    ])
    assert [step["approval_required"] for step in steps] == [False, False, False, False, False]
    assert steps[2]["control"] == "New Document"
    assert steps[3]["value"] == "A governed draft."


def test_generic_harness_blocks_sensitive_fields_and_unsafe_keys() -> None:
    with pytest.raises(ValueError, match="computer_sensitive_field_blocked"):
        normalise_computer_steps([
            {"operation": "type_text", "target": {"app": "Safari", "control": "Password"}, "value": "not-allowed"},
        ])


def test_repair_prompt_is_provider_neutral_and_preserves_validation_boundary() -> None:
    prompt = computer_plan_repair_prompt(
        user_request="Create a document in Pages",
        proposal={"objective": "draft", "steps": [{"operation": "create_presentation", "target": {"app": "Pages"}}]},
        error="computer_presentation_content_required",
    )
    assert "nothing was executed" in prompt
    assert "create_presentation ONLY for Keynote" in prompt
    assert "Use generic click_control" in prompt


def test_small_model_shorthand_is_coerced_into_reversible_local_work() -> None:
    proposal = coerce_computer_proposal(
        {"objective": "Open Pages and make a blank document", "steps": ["open_app", "inspect_app", "type_text", "verify_text"]},
        user_request="Open Pages, create a blank document, type the title Advanced AI Operations, and verify it.",
    )
    steps = normalise_computer_steps(proposal["steps"])
    assert [step["operation"] for step in steps] == ["open_app", "inspect_app", "press_key", "type_text", "verify_text"]
    assert steps[2]["approval_required"] is False
    assert steps[3]["control"] == "focused control"
    assert steps[3]["value"] == "Advanced AI Operations"


def test_small_model_control_key_schema_drift_is_repaired_semantically() -> None:
    proposal = coerce_computer_proposal(
        {"objective": "Open Pages", "steps": [
            {"control": "open_app", "app": "Pages"},
            {"control": "inspect_app", "app": "Pages"},
            {"app": "Pages", "control": "New Document"},
            {"app": "Pages", "control": "document_title", "value": "Advanced AI Operations"},
            {"app": "Pages", "control": "document_title", "expected_text": "Advanced AI Operations"},
        ]},
        user_request="Open Pages and type Advanced AI Operations",
    )
    steps = normalise_computer_steps(proposal["steps"])
    assert [step["operation"] for step in steps] == ["open_app", "inspect_app", "click_control", "type_text", "verify_text"]
    assert steps[2]["approval_required"] is False
    assert steps[3]["control"] == "focused control"
    with pytest.raises(ValueError, match="computer_modifier_not_allowed"):
        normalise_computer_steps([
            {"operation": "press_key", "target": {"app": "Pages"}, "key": "return", "modifiers": ["function"]},
        ])


def test_explicit_user_app_overrides_a_model_app_mixup() -> None:
    proposal = coerce_computer_proposal(
        {"objective": "Create a Pages document", "steps": [
            {"operation": "open_app", "target": {"app": "Pages"}},
            {"operation": "press_key", "target": {"app": "Notes"}, "key": "n", "modifiers": ["command"]},
            {"operation": "type_text", "target": {"app": "Pages", "control": "focused control"}, "value": "Title"},
        ]},
        user_request="Open Pages and create a document",
    )
    assert {step["target"]["app"] for step in proposal["steps"]} == {"Pages"}


def test_create_document_click_does_not_duplicate_new_document_shortcut() -> None:
    proposal = coerce_computer_proposal(
        {"objective": "Create a document", "steps": [
            {"operation": "open_app", "target": {"app": "Pages"}},
            {"app": "Pages", "control": "create_document"},
            {"app": "Pages", "control": "document_title", "value": "Title"},
        ]},
        user_request="Open Pages, create a blank document, and type the title Title.",
    )
    operations = [step.get("operation") for step in proposal["steps"]]
    assert operations == ["open_app", "click_control", "type_text"]


def test_plain_language_notes_request_is_compiled_without_model_prompt_leakage() -> None:
    proposal = proposal_from_user_request("Open my Notes app on the desktop and write something")
    assert proposal is not None
    assert proposal["steps"][1]["value"] == "Something"
    assert "TOOL CONTRACT" not in proposal["steps"][1]["value"]


def test_desktop_app_hint_is_catalogue_assisted_but_not_catalogue_limited() -> None:
    assert infer_explicit_desktop_app("Open Pages, create a document") == "Pages"
    assert infer_explicit_desktop_app("Launch Acme Studio app and inspect it") == "Acme Studio"
    assert infer_explicit_desktop_app("Open Terminal and run a command") is None


def test_keynote_request_is_not_misclassified_as_notes() -> None:
    proposal = proposal_from_user_request("open key note on the desktop and produce a slide about ai")
    assert proposal is not None
    assert proposal["steps"][0]["target"]["app"] == "Keynote"
    assert proposal["steps"][1]["operation"] == "create_presentation"
    assert proposal["steps"][1]["target"]["app"] == "Keynote"
    assert proposal["steps"][1]["title"] == "Artificial Intelligence"


def test_keynote_presentation_runs_as_local_reversible_work() -> None:
    steps = normalise_computer_steps([
        {"operation": "open_app", "target": {"app": "Keynote"}},
        {
            "operation": "create_presentation",
            "target": {"app": "Keynote"},
            "title": "Artificial Intelligence",
            "body": "AI helps businesses work faster.",
        },
    ])
    assert steps[0]["approval_required"] is False
    assert steps[1]["approval_required"] is False
    assert steps[1]["body"] == "AI helps businesses work faster."


def test_common_apple_apps_compile_without_model_state_leakage() -> None:
    pages = proposal_from_user_request(
        'Open Pages, create a blank document, and type the heading “Advanced AI Operations”.'
    )
    numbers = proposal_from_user_request(
        'Open Numbers, create a new spreadsheet, and enter “January Sales” in the first available cell.'
    )
    calendar = proposal_from_user_request(
        "Open Calendar and inspect the visible controls. Tell me what is available without changing anything."
    )
    mail = proposal_from_user_request(
        'Open Mail and draft an email with the subject “Harness Test” and the body “This is a test draft.” Do not send it.'
    )
    assert [step["operation"] for step in pages["steps"]] == ["open_app", "create_document"]
    assert pages["steps"][1]["target"]["app"] == "Pages"
    assert pages["steps"][1]["value"] == "Advanced AI Operations"
    assert [step["operation"] for step in numbers["steps"]] == ["open_app", "create_spreadsheet"]
    assert numbers["steps"][1]["value"] == "January Sales"
    assert [step["operation"] for step in calendar["steps"]] == ["open_app", "inspect_app"]
    assert {step["target"]["app"] for step in calendar["steps"]} == {"Calendar"}
    assert [step["operation"] for step in mail["steps"]] == ["open_app", "create_email_draft"]
    assert mail["steps"][1]["subject"] == "Harness Test"
    assert mail["steps"][1]["body"] == "This is a test draft."


def test_research_to_pages_compiles_evidence_into_saved_report() -> None:
    prompt = (
        "Research three recent AI automation developments, create a Pages document "
        "summarising them with source links, and save the document locally."
    )
    evidence = [
        {
            "title": f"Automation development {index}",
            "url": f"https://example.com/development-{index}",
            "summary": f"Verified development summary {index}.",
            "published_at": f"2026-10-0{index}",
        }
        for index in range(1, 4)
    ]
    assert is_research_pages_request(prompt) is True
    assert research_query_from_pages_request(prompt) == "three recent AI automation developments"
    proposal = proposal_from_research_evidence(prompt, evidence)
    assert proposal is not None
    steps = normalise_computer_steps(proposal["steps"])
    assert [step["operation"] for step in steps] == ["open_app", "create_document"]
    assert steps[1]["file_name"] == "AI Automation Developments"
    assert "Verified development summary 1." in steps[1]["value"]
    assert "https://example.com/development-3" in steps[1]["value"]


def test_attached_pages_document_compiles_to_reversible_style_work(tmp_path: Path) -> None:
    source = tmp_path / "Basic Brief.pages"
    source.mkdir()
    proposal = proposal_from_attachment_request(
        "Style this document professionally using our branding.",
        [{"path": str(source), "name": source.name, "extension": ".pages", "kind": "file"}],
    )
    assert proposal is not None
    steps = normalise_computer_steps(proposal["steps"])
    assert [step["operation"] for step in steps] == ["open_app", "style_document"]
    assert steps[1]["file_path"] == str(source.resolve())
    assert steps[1]["approval_required"] is False


def test_send_open_mail_draft_is_still_approval_gated() -> None:
    proposal = proposal_from_user_request("Send the draft email.")
    steps = normalise_computer_steps(proposal["steps"])
    assert steps[0]["target"]["app"] == "Mail"
    assert steps[1]["control"] == "Send"
    assert steps[1]["approval_required"] is True


def test_current_user_turn_overrides_apps_in_conversation_history() -> None:
    proposal = coerce_computer_proposal(
        {
            "objective": "Open Calendar",
            "steps": [
                {"operation": "open_app", "target": {"app": "Calendar"}},
                {"operation": "inspect_app", "target": {"app": "Calendar"}},
            ],
        },
        user_request='Open Mail and draft an email with subject “Harness Test”.',
    )
    assert {step["target"]["app"] for step in proposal["steps"]} == {"Mail"}


def test_one_time_grant_and_receipt(tmp_path: Path) -> None:
    store = ComputerHarnessStore(tmp_path)
    plan = store.create_plan(
        proposal={"objective": "Write a note", "steps": [
            {"operation": "open_app", "target": {"app": "Notes"}},
            {"operation": "create_note", "target": {"app": "Notes"}, "value": "Something"},
        ]},
        provider="local_model",
        model="qwen-test",
        workspace_id="test",
        now=100,
    )
    assert plan["state"] == "ready"
    assert plan["auto_execute"] is True
    authority = store.redeem_grant(
        grant_id=plan["grant_id"], execution_token=plan["execution_token"], now=102,
    )
    assert authority["steps"][1]["operation"] == "create_note"
    with pytest.raises(PermissionError, match="already_redeemed"):
        store.redeem_grant(grant_id=plan["grant_id"], execution_token=plan["execution_token"], now=103)
    receipt = store.record_receipt(
        grant_id=plan["grant_id"], result={"ok": True, "status": "computer_task_completed"}, now=104,
    )
    assert receipt["ok"] is True
    assert receipt["provider_neutral"] is True


def test_consequential_actions_still_require_exact_approval(tmp_path: Path) -> None:
    steps = normalise_computer_steps([
        {"operation": "open_app", "target": {"app": "Mail"}},
        {"operation": "type_text", "target": {"app": "Mail", "control": "Message body"}, "value": "Draft only"},
        {"operation": "click_control", "target": {"app": "Mail", "control": "Send"}},
    ])
    assert [step["approval_required"] for step in steps] == [False, False, True]
    store = ComputerHarnessStore(tmp_path)
    plan = store.create_plan(
        proposal={"objective": "Draft and send an email", "steps": steps},
        provider="local_model", model="qwen-test", workspace_id="test", now=100,
    )
    assert plan["state"] == "awaiting_user_approval"
    assert plan["approval_step_ids"] == ["step_3"]


def test_desktop_shell_and_chat_ui_expose_governed_executor() -> None:
    app = APP.read_text(encoding="utf-8")
    preload = PRELOAD.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    assert "renderAionComputerPlanCardV1" in app
    assert "data-aion-computer-plan-run" in app
    assert "executeGovernedComputerPlan" in app
    assert "__aionComputerPendingAutoRunPlanIdV1 === autoPlanId" in app
    assert "executeGovernedComputerPlan" in preload
    assert "prepareDesktopPermissions" in preload
    assert 'ipcMain.handle("aion-execute-governed-computer-plan"' in main
    assert "Exact approval is required before creating a note" in main
    assert "Exact approval is required before creating a presentation" in main
    assert "inspectGovernedDesktopApp" in main
    assert "click_control" in main
    assert "type_text" in main
    assert "Sensitive fields cannot be automated" in main
    assert "Prepare desktop applications once" in main
    assert "isTrustedAccessibilityClient(true)" in main
    assert 'operation === "create_document"' in main
    assert 'operation === "style_document"' in main
    assert 'operation === "create_spreadsheet"' in main
    assert 'operation === "create_email_draft"' in main
    assert "summarizeGovernedDesktopInspection" in main
    assert "document_created_and_saved" in main
    assert "document_styled_and_saved" in main
    assert "chooseChatAttachments" in preload
    assert 'ipcMain.handle("aion-choose-chat-attachments"' in main
    assert "aionChatAttachBtn" in app
    assert 'path.join(os.homedir(), "Documents", "Tessaris")' in main
    assert "ignore identical subsequent heartbeats" in app
    assert "getAionChatRenderSignatureV3" in app
    assert "shouldSuppressUnchangedAionChatRenderV3" in app
    assert "__aionChatSuppressedBackgroundRendersV3" in app
    assert "if (shouldSuppressUnchangedAionChatRenderV3()) return;" in app
    runtime = RUNTIME.read_text(encoding="utf-8")
    assert "Review and approve the exact Notes action" not in runtime
    assert "A completion receipt will appear here" in runtime
    assert "coerce_computer_proposal(computer_proposal, user_request=intent_prompt)" in runtime
    assert "proposal_from_research_evidence" in runtime
    assert 'direct_tools_used.insert(0, "web.search_and_read")' in runtime
