from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
RUNTIME = (ROOT / "desktop/mac/src/aion_department_pilot_runtime.js").read_text(encoding="utf-8")
DESKTOP_APP = (ROOT / "backend/desktop_app.py").read_text(encoding="utf-8")


def function_block(name: str) -> str:
    start = APP.index(f"function {name}")
    end = APP.find("\nfunction ", start + len(name) + 9)
    return APP[start:] if end == -1 else APP[start:end]


def test_central_pilot_exposes_the_governed_work_lifecycle():
    block = function_block("renderAionPilotSimpleTaskStream")
    for token in (
        "AION CENTRAL PILOT",
        "01 · Understand",
        "02 · Plan",
        "03 · Produce",
        "04 · Govern",
        "pause before external action",
    ):
        assert token in block


def test_final_runtime_skin_is_light_and_preserves_core_controls():
    assert "background:#ffffff !important" in RUNTIME
    assert "border-top:3px solid #78c6ff" in RUNTIME
    assert "font-family:Inter,-apple-system" in RUNTIME
    assert "background:#07111f !important" not in RUNTIME
    assert "background:#0f172a !important" not in RUNTIME
    assert '[data-aion-pilot-create-draft-mission]' in RUNTIME
    assert '[data-aion-pilot-mission-input]' in RUNTIME


def test_technical_proof_remains_available_but_is_not_duplicated():
    block = function_block("renderAionPilotSimpleTaskStream")
    label = "Advanced details: safety, reasoning, proof, hashes and blocked actions"
    assert block.count(label) == 1
    assert "renderAionPilotAdvancedTechnicalDetails(snapshot)" in block


def test_pilot_command_centre_exposes_real_work_surfaces():
    for token in (
        '"work", "Work"',
        '"knowledge", "Business Brain"',
        '"scheduled", "Scheduled"',
        '"capabilities", "Capabilities"',
        '"channels", "Channels"',
        '"artifacts", "Outputs"',
        "Delegate useful work",
        "Recurring business jobs",
        "What Pilot can genuinely use",
        "Where Pilot can work with you",
    ):
        assert token in APP


def test_private_business_brain_is_review_gated_and_recalled_by_pilot():
    for token in (
        "data-aion-pilot-business-knowledge-workspace",
        "pending_owner_review",
        "data-aion-pilot-knowledge-approve",
        "searchBusinessKnowledge",
        "business_knowledge_receipt",
    ):
        assert token in APP


def test_read_only_questions_bypass_mission_planning_and_approval():
    classifier = function_block("classifyAionPilotRequestMode")
    dispatcher = function_block("createAionPilotFrontendDraftMission")
    answer = function_block("answerAionPilotDirectQuestion")
    renderer = function_block("renderAionPilotDirectAnswer")

    assert '"direct_answer"' in classifier
    assert '"safe_draft"' in classifier
    assert '"governed_action"' in classifier
    assert 'requestMode.mode === "direct_answer"' in dispatcher
    assert "answerAionPilotDirectQuestion" in dispatcher
    assert 'contract_status = "not_required_read_only"' in answer
    assert "searchBusinessKnowledge" in answer
    assert "Question answered directly; no execution or approval was required." in answer
    assert "approval not required" in renderer
    assert "data-aion-pilot-direct-answer" in renderer


def test_pilot_separates_questions_drafts_and_external_actions():
    classifier = function_block("classifyAionPilotRequestMode")
    script = classifier + "\nconsole.log(JSON.stringify([\n" + \
        "classifyAionPilotRequestMode('What makes CarbonCore different?'),\n" + \
        "classifyAionPilotRequestMode('write me a client email explaining CarbonCore'),\n" + \
        "classifyAionPilotRequestMode('write me a client email to explain the benefits of carbon core and why they should purchase it'),\n" + \
        "classifyAionPilotRequestMode('send this email to the client'),\n" + \
        "classifyAionPilotRequestMode('write the email and then send it'),\n" + \
        "classifyAionPilotRequestMode('purchase this item')\n]));"
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    modes = [item["mode"] for item in json.loads(result.stdout)]
    assert modes == [
        "direct_answer",
        "safe_draft",
        "safe_draft",
        "governed_action",
        "governed_action",
        "governed_action",
    ]


def test_safe_drafts_are_generated_without_an_approval_gate():
    dispatcher = function_block("createAionPilotFrontendDraftMission")
    producer = function_block("createAionPilotSafeDraft")
    renderer = function_block("renderAionPilotSafeDraft")
    assert 'requestMode.mode === "safe_draft"' in dispatcher
    assert 'contract_status = "not_required_safe_draft"' in producer
    assert "/api/boardroom/pilot-draft" in producer
    assert "getBoardroomContext" in producer
    assert "getOrganizationAuthority" in producer
    assert "business_context: businessContext" in producer
    assert "role.owner_director" in producer
    assert "Nothing has been sent" in renderer
    assert "verified identity fields" in renderer
    assert "data-aion-pilot-draft-followup" in renderer
    assert "Tell me the next outcome you want" in renderer
    assert "identify the capability required" in renderer
    assert "renderAionPilotWorkPackageCard" not in renderer


def test_retained_email_drafts_require_exact_gmail_payload_approval():
    for token in (
        "prepareAionPilotEmailFollowup",
        "executeAionPilotApprovedEmailSend",
        "/api/local-node/pilot/email/prepare",
        "/api/local-node/connectors/gmail/health",
        "/api/local-node/pilot/email/${encodeURIComponent(action.approval_id)}/send",
        "data-aion-pilot-email-followup",
        "data-aion-pilot-approve-email-send",
        "Approve and send",
        "Nothing is sent until you click Approve and send.",
        "Gmail needs to be reconnected in Vault",
    ):
        assert token in APP


def test_pilot_has_generic_capability_resolution_and_standing_authority_controls():
    for token in (
        "resolveAionPilotRequestedCapability",
        '"authority", "Authority"',
        "Choose when AION may act without asking",
        "Ask me each time",
        "Act automatically",
        "Full access",
        "Never allow or ask",
        "/api/local-node/pilot/authority",
        "Change standing authority",
        "I will not ask again unless you change it in Authority.",
        "I can prepare the work, but I will not pretend it was executed.",
    ):
        assert token in APP


def test_legacy_work_package_buttons_redirect_harmless_requests_to_the_real_draft_lane():
    approval = function_block("approveAionPilotMissionContract")
    runner = function_block("runAionPilotSafeWorkPreview")
    for block in (approval, runner):
        assert "classifyAionPilotRequestMode" in block
        assert 'currentMode.mode === "safe_draft"' in block
        assert "createAionPilotSafeDraft(currentRequest, pilotState)" in block
        assert 'currentMode.mode === "direct_answer"' in block
        assert "answerAionPilotDirectQuestion(currentRequest, pilotState)" in block


def test_obsolete_pilot_session_cache_is_not_reloaded():
    state_loader = function_block("getAionPilotFrontendInteractionState")
    assert "aion.pilot.runtimeState.${previousScope}.v3" in state_loader
    assert "aion.pilot.runtimeState.${scope}.v3" in state_loader
    assert "runtimeState.${scope}.v1" not in state_loader


def test_recurring_jobs_use_the_durable_governed_scheduler():
    for token in (
        "getPilotScheduledWork",
        "createPilotScheduledWork",
        "setPilotScheduledWorkEnabled",
        "runPilotScheduledWork",
        "Sales inbox enquiry monitor",
        "No user job is silently active.",
        "exact approval decision",
    ):
        assert token in APP


def test_desktop_runtime_mounts_and_runs_the_durable_scheduler():
    for token in (
        "pilot_scheduled_work_router",
        "app.include_router(router)",
        "PilotScheduledWorkService",
        "_desktop_pilot_scheduler_loop",
        "service.run_due(workspace.name)",
    ):
        assert token in DESKTOP_APP


def test_pilot_never_presents_unconnected_execution_as_live():
    for token in (
        "No user job is silently active.",
        "approval before external action",
        "Adapter required",
        "Universal computer control",
        "Each real tool requires a named adapter and permission.",
    ):
        assert token in APP


def test_pilot_voice_controls_are_opt_in_and_use_runtime_capabilities():
    for token in (
        "data-aion-pilot-dictate",
        "data-aion-pilot-read-aloud",
        "data-aion-pilot-wake-phrase",
        "window.SpeechRecognition || window.webkitSpeechRecognition",
        "window.aionDesktop?.playLocalVoice",
    ):
        assert token in APP


def test_pilot_workspace_has_compact_command_centre_styling():
    for token in (
        ".aion-pilot-workspace-nav",
        ".aion-pilot-command-panel",
        ".aion-pilot-quick-grid",
        ".aion-pilot-capability-registry",
        ".aion-pilot-voice-controls",
    ):
        assert token in RUNTIME
