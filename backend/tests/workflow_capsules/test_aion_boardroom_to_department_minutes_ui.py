from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_visible_ask_board_uses_the_live_provider_route():
    assert 'data-aion-council-session-run="true"' in APP
    assert "runAionLiveVisibleAskBoardResultV1(sessionType, runId)" in APP
    assert 'fetch("http://127.0.0.1:8080/api/boardroom/ask"' in APP


def test_safe_department_task_button_is_not_an_accidental_boardroom_trigger():
    start = APP.index("function renderAionDepartmentPilotPhase25DPanel")
    end = APP.index("if (!window.__aionPhase25DDepartmentPilotHandlersInstalled)", start)
    panel = APP[start:end]
    assert 'data-aion-phase25d-run-safe-task=' in panel
    assert 'data-aion-council-session-ask-board="true"' not in panel


def test_live_board_outcomes_refresh_department_packages():
    assert APP.count("window.aionStageBoardroomPackagesToDepartmentPilotsO14A?.();") >= 3
    assert "function latestBoardroomOutcomeO14A(department)" in APP
    assert "source_board_meeting_id" in APP
    assert "source_boardroom_result_hash" in APP
    assert "boardroom_brief: boardroomBrief" in APP
    assert "meeting_minutes:" in APP
    assert "assigned_tasks: finalBoardDirectionReady ? outcome.tasks : []" in APP


def test_boardroom_package_includes_hr_and_remains_approval_gated():
    assert 'const DEPARTMENTS = ["marketing", "sales", "finance", "operations", "support", "hr"]' in APP
    assert 'status: finalBoardDirectionReady ? "boardroom_task_ready" : "discovery_required"' in APP
    assert "execution_allowed_now: false" in APP
    assert "approval_required: true" in APP


def test_boardroom_uses_the_original_persisted_business_map_container():
    assert "function loadOriginalBusinessMap()" in APP
    assert "AionBusinessContainerClient.getBusinessMap" in APP
    assert 'kind: "business_map"' in APP
    assert 'aion.boardroom.businessMapConfirmation.v1' in APP
    assert "business_map_snapshot: packet.business_map_snapshot || null" in APP
    assert "business_map_confirmation: packet.business_map_confirmation || null" in APP
    assert 'data-aion-confirm-original-business-map="true"' in APP
    assert 'data-aion-council-session-run=\'true\'' in APP
    assert "Confirm the original persisted Business Map before asking the Board" in APP
    assert 'schema_version: "aion.business_map_confirmation.v2"' in APP
    assert "business_map_payload_hash" in APP
    assert "business_map_revision" in APP


def test_boardroom_terminal_uses_live_container_envelope_and_real_provider_registry():
    assert "getAionLiveBusinessContextPacketLinesV2" in APP
    assert "persistent_truth_source" in APP
    assert "business_containers" in APP
    assert "/api/boardroom/providers/status" in APP
    assert "getAionLiveSelectedBoardroomProviderIdsV2()" in APP
    assert '|| "no connected Board members selected"' in APP
    assert "Source revisions: Business Map" in APP
    assert 'source: liveDepartmentLedger ? "canonical_department_intelligence_container"' in APP
    assert "canonical_context_envelope: packet.canonical_context_envelope || null" in APP
    assert "business_map_projection: liveBoardroomContext.business_map_projection" in APP


def test_boardroom_ask_fails_visibly_instead_of_silently():
    assert "No connected Board members are selected" in APP
    assert "Board meeting locked: confirm the current original Business Map revision first." in APP
    assert "Live Boardroom ask failed:" in APP


def test_boardroom_sequence_requires_debate_and_founder_ratification_before_tasks():
    assert "function ratifyBoardDirection()" in APP
    assert 'aion.boardroom.founderRatification.v1' in APP
    assert 'data-aion-ratify-board-direction="true"' in APP
    assert "The founder must ratify the debated Board direction before department tasks can be built." in APP
    assert "original_business_map_confirmed: mapConfirmation.valid" in APP
    assert "founder_direction_ratified: founderRatification.valid" in APP
    assert "department_task_build_complete:" in APP


def test_parallel_localstorage_business_map_compiler_is_inert():
    marker = 'Superseded by the original BusinessMapContainer bridge below.'
    assert marker in APP
    disabled = APP.index(marker)
    legacy_builder = APP.index("function buildCanonicalBusinessMap()")
    assert disabled < legacy_builder
    assert "return;" in APP[disabled:legacy_builder]


def test_discovery_workspace_buttons_route_through_the_department_pilot_authority():
    assert 'data-aion-open-discovery-section=' in APP
    assert 'window.aionSetLiveAgentsDepartmentAuthorityO14M(destination)' in APP
    assert 'state.activeTab = "live_agents";' in APP
    assert 'window.AionOperatingModelWorkspace.state.activeTab = section;' in APP
    assert 'event.stopImmediatePropagation?.();' in APP


def test_boardroom_analysis_uses_a_light_reading_surface_with_coloured_gates():
    visible_start = APP.index("function renderAionVisibleAskBoardResultHtmlV1")
    visible_end = APP.index("/* END AION PATCH: Visible Ask Board Result v1 */", visible_start)
    visible = APP[visible_start:visible_end]
    assert "background:#ffffff;" in visible
    assert "color:#29465b;" in visible

    inbox_start = APP.index("function renderAionDiscoveryQuestionInboxHtmlV1")
    inbox_end = APP.index("function installAionDiscoveryQuestionInboxBindingsV1", inbox_start)
    inbox = APP[inbox_start:inbox_end]
    assert "background:#f7fbfd;" in inbox
    assert "background:#fffbeb" in inbox
