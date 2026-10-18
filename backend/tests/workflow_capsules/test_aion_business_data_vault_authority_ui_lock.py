from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
CLIENT = (ROOT / "desktop/mac/src/aion_business_container_client.js").read_text(encoding="utf-8")
PREFERENCES = (ROOT / "desktop/mac/src/aion_desktop_preferences.js").read_text(encoding="utf-8")
PILOT = (ROOT / "desktop/mac/src/aion_department_pilot_runtime.js").read_text(encoding="utf-8")
SESSION = (ROOT / "desktop/mac/src/aion_development_business_session.js").read_text(encoding="utf-8")
FINANCE = (ROOT / "desktop/mac/src/aion_finance_pilot.js").read_text(encoding="utf-8")
OPERATING_MODEL = (ROOT / "desktop/mac/src/aion_operating_model_workspace.js").read_text(encoding="utf-8")
BUSINESS_TWIN = (ROOT / "desktop/mac/src/aion_business_twin_orchestrator.js").read_text(encoding="utf-8")
LEGAL = (ROOT / "desktop/mac/src/aion_legal_workspace.js").read_text(encoding="utf-8")
HR = (ROOT / "desktop/mac/src/aion_hr_people_workspace.js").read_text(encoding="utf-8")
SALES = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
WORK_SCHEDULE = (ROOT / "desktop/mac/src/aion_work_schedule_workspace.js").read_text(encoding="utf-8")


def test_department_intelligence_is_memory_backed_and_guardian_saved():
    assert "window.__aionDepartmentIntelligenceMemory = ledger" in APP
    assert "AionBusinessContainerClient?.saveDepartmentIntelligence" in APP
    assert 'localStorage.setItem("aion.departmentIntelligence.v1"' not in APP
    assert 'localStorage.removeItem("aion.departmentIntelligence.v1")' in APP
    assert "global.getAionDepartmentIntelligence()" in PILOT


def test_foundation_and_voice_onboarding_write_to_vault_sections():
    assert 'saveFoundationSection?.(\n    approved ? "approved_business_context"' in APP
    assert 'saveFoundationSection?.(\n      "voice_discovery"' in APP
    assert 'saveFoundationSection?.(\n      "confirmed_foundation"' in APP
    assert "foundationSaveChain" in CLIENT
    assert "expected_revision: Number(session.revision || 0)" in CLIENT


def test_marketing_transcripts_are_department_intelligence_not_browser_records():
    assert "conversation_terminal: existing.concat" in APP
    assert "cockpit_transcript" in APP
    assert 'localStorage.setItem("aion.marketingPilot.conversationTerminal.v1"' not in APP
    assert 'localStorage.setItem("aion.marketingPilotCockpit.transcript.v1"' not in APP


def test_legacy_business_context_is_imported_then_purged():
    assert 'window.localStorage?.removeItem(key)' in APP
    assert 'window.__aionFoundationPacket = foundationPacket' in APP
    assert "AionBusinessContainerClient?.commitFoundationPacket?.(foundationPacket)" in APP


def test_foundation_session_packet_is_not_durably_duplicated_in_browser():
    assert "root.__aionFoundationPacket = packet" in SESSION
    assert "localStorage.removeItem(PACKET_KEY)" in SESSION
    assert "localStorage.setItem(PACKET_KEY, JSON.stringify(packet))" not in SESSION
    assert "vault_unavailable_memory_only" in SESSION


def test_train_agent_workflow_tabs_are_vault_backed_not_browser_backed():
    assert "installTrainAgentWorkflowTabVaultShim" in CLIENT
    assert "saveTrainAgentWorkspaceState('workflow-tabs'" in CLIENT
    assert "getTrainAgentWorkspaceState('workflow-tabs')" in CLIENT
    assert "nativeRemove.call(this, key)" in CLIENT
    assert "/workspace-state/" in CLIENT


def test_finance_discovery_and_boardroom_handoff_are_memory_and_vault_backed():
    assert "global.__aionFinancePilotDiscoveryState = value" in FINANCE
    assert "global.__aionFinanceBusinessModel = model" in FINANCE
    assert "global.__aionFinanceBoardroomPacket = boardroomPacket" in FINANCE
    assert "localStorage.setItem(STORAGE_KEY" not in FINANCE
    assert "localStorage.setItem(MODEL_KEY" not in FINANCE
    assert "localStorage.setItem(BOARDROOM_PACKET_KEY" not in FINANCE
    assert "getFinanceModel" in CLIENT


def test_business_map_discovers_future_departments_dynamically():
    assert "...Object.keys(ledger || {})" in APP
    assert "...Object.keys(departmentDrafts || {})" in APP
    assert "window.__aionFinancePilotDiscoveryState || {}" in APP


def test_operating_model_drafts_are_debounced_to_vault_not_browser_storage():
    assert "draftSaveChain" in OPERATING_MODEL
    assert "AionBusinessContainerClient.saveOperatingModel" in OPERATING_MODEL
    assert "global.__aionOperatingModelDraft = state.model" in OPERATING_MODEL
    assert "localStorage.setItem(STORAGE_KEY" not in OPERATING_MODEL
    assert "localStorage.removeItem(STORAGE_KEY)" in OPERATING_MODEL


def test_founder_notes_have_an_explicit_vault_authority_and_legacy_import():
    assert "window.__aionFounderNotes = safeNotes" in APP
    assert "AionBusinessContainerClient?.saveFounderNotes" in APP
    assert "localStorage?.setItem(AION_FOUNDER_NOTES_STORAGE_KEY_V1" not in APP
    assert "getFounderNotes" in CLIENT
    assert "saveFounderNotes" in CLIENT


def test_business_bearing_browser_working_state_is_encrypted_and_migrated_to_vault():
    for key in (
        "aion.chat.sessions.v3",
        "aion.workflow_builder.current_draft.v1",
        "aion.boardroom.discovery_answers.v1",
        "aion.finance.data_points.v1",
        "aion.goal_engine.multi_agent_execution_replay.history.v1",
    ):
        assert key in CLIENT
    assert "aion.departmentPilot.conversationTerminal." in CLIENT
    assert "BUSINESS_WORKING_STATE_DEPARTMENT_TERMINAL" in CLIENT
    assert "installBusinessWorkingStateVaultShim" in CLIENT
    assert "migrateLegacyBusinessWorkingState" in CLIENT
    assert "/api/aion/business/data/working-state/" in CLIENT
    assert "nativeRemove(key);\n      migrated.push(key);" in CLIENT
    assert "state remains in session memory" in CLIENT


def test_renderer_has_no_direct_browser_write_authority():
    assert "localStorage.setItem" not in APP
    assert "localStorage?.setItem" not in APP
    assert "sessionStorage.setItem" not in APP
    assert "sessionStorage?.setItem" not in APP
    assert "AionBusinessContainerClient.writeBusinessWorkingStateString" in APP
    assert "AionDesktopPreferences.set" in APP


def test_disposable_preferences_are_exact_key_and_value_validated():
    assert "const exactKeys = new Set" in PREFERENCES
    assert "Unregistered desktop preference key" in PREFERENCES
    assert "Desktop preference accepts content-free tokens only" in PREFERENCES
    assert "Desktop API preference must remain loopback-only" in PREFERENCES
    assert "Unexpected Pilot voice preference" in PREFERENCES


def test_remaining_department_workspaces_do_not_create_browser_business_records():
    assert "writeBusinessWorkingStateString?.(\n          MANIFEST_STORAGE_KEY" in BUSINESS_TWIN
    assert "localStorage?.setItem" not in BUSINESS_TWIN
    assert "writeBusinessWorkingStateString?.(STORAGE_KEY" in LEGAL
    assert "localStorage?.setItem" not in LEGAL
    assert "localStorage?.setItem" not in HR
    assert "localStorage?.setItem" not in SALES
    assert "localStorage?.setItem" not in WORK_SCHEDULE
    assert "localStorage?.removeItem(STORAGE_KEY)" in WORK_SCHEDULE
    assert "fetch(endpoint(), { method: 'PUT'" in WORK_SCHEDULE
