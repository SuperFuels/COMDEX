from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP_JS = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
SALES_JS = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
HR_JS = (ROOT / "desktop/mac/src/aion_hr_people_workspace.js").read_text(encoding="utf-8")


def test_operating_departments_use_compact_directors_except_operations_command_centre():
    for key in ("marketing", "sales", "finance", "support", "hr"):
        assert f'{key}: {{' in APP_JS
        assert f'renderDepartmentCompactDirectorCard("{key}")' in APP_JS
        assert f'renderAionO14KCollapsedPackageDockUnderBoardroom("{key}")' in APP_JS

    assert 'renderOperationsCommandCentre()' in APP_JS

    assert 'data-aion-unified-department-director=' in APP_JS
    assert 'grid-template-columns:minmax(360px,1fr) 260px' in APP_JS
    assert 'width:260px' in APP_JS
    assert 'height:260px' in APP_JS
    assert 'data-aion-character-media' in APP_JS
    assert 'width:177.683316%' in APP_JS
    assert 'left:-58.262487%' in APP_JS
    assert 'data-aion-unified-department-conversation=' in APP_JS
    assert "openUnifiedDepartmentPilotConversation" in APP_JS
    assert "department-scoped conversation" in APP_JS


def test_compact_directors_use_clickable_character_identity_portraits_not_robot_canvases():
    expected_portraits = {
        "marketing": "marketing-character-v3.png",
        "sales": "sales-character-v2.png",
        "finance": "finance-character-v2.png",
        "operations": "operations-character-v2.png",
        "support": "support-character-v2.png",
        "hr": "hr-character-v2.png",
    }
    for key, filename in expected_portraits.items():
        assert f'portrait: "./assets/department-pilots/{filename}"' in APP_JS
        assert (ROOT / f"desktop/mac/src/assets/department-pilots/{filename}").is_file()

    compact_director = APP_JS.split("function renderDepartmentCompactDirectorCard", 1)[1].split(
        "function openUnifiedDepartmentPilotConversation", 1
    )[0]
    assert 'data-aion-unified-department-portrait=' in compact_director
    assert "renderAionAnchoredCharacterMedia(config, key" in compact_director
    assert "Synthetic agent · ready" in compact_director
    assert 'data-aion-o14d-department-121-spatial-boardroom-mount="true"' not in compact_director
    assert 'data-aion-unified-department-conversation="${escapeHtml(key)}"' in compact_director
    assert 'data-aion-character-stage=' in compact_director
    assert "function renderAionAnchoredCharacterMedia" in APP_JS


def test_talk_to_pilot_uses_a_shared_runtime_registry_and_safe_renderer_fallback():
    assert "window.AION_UNIFIED_DEPARTMENT_SHELLS = AION_UNIFIED_DEPARTMENT_SHELLS" in APP_JS
    assert "const identityRegistry = window.AION_UNIFIED_DEPARTMENT_SHELLS || {}" in APP_JS
    assert "const renderers = [" in APP_JS
    assert "window.renderAionO18AADepartmentConversationCockpit" in APP_JS
    assert "window.renderAionO18ADDepartmentConversationCockpit" in APP_JS
    assert "Department Pilot conversation renderer failed" in APP_JS
    assert "document.body.appendChild(dialog);\n  return true;" in APP_JS


def test_people_landing_page_is_the_full_width_resizable_command_centre():
    assert "function renderHRWorkspaceSurface(selectedRuns, selectedAgentCard)" in APP_JS
    assert "return renderPeoplePilotCommandCentre();" in APP_JS
    assert "function renderPeoplePilotCommandCentre()" in APP_JS
    assert 'data-aion-people-command-centre="true"' in APP_JS
    assert 'data-aion-people-split-handle="true"' in APP_JS
    assert 'data-aion-people-pilot-pane="true"' in APP_JS
    assert 'data-aion-people-workspace-pane="true"' in APP_JS
    assert 'data-aion-hr-directory-page-size="1"' in APP_JS
    assert 'data-aion-people-pilot-thread' in APP_JS
    assert 'data-aion-people-pilot-form' in APP_JS
    assert 'department_id: "people"' in APP_JS
    assert 'data-aion-people-open-package="true"' in APP_JS
    assert 'data-aion-people-command-close' not in APP_JS
    assert 'data-aion-people-live-agents-workspace="true"' in APP_JS
    assert 'left:64px!important;right:0!important;bottom:0!important' in APP_JS
    assert 'padding:16px 32px 80px!important' in APP_JS
    assert 'min-height:calc(100vh - 190px);height:calc(100vh - 190px)' in APP_JS


def test_people_command_centre_directory_pages_one_record_at_a_time():
    assert "personPage: 0" in HR_JS
    assert "data-aion-hr-directory-page-size" in HR_JS
    assert "visiblePeople.map((person)" in HR_JS
    assert "data-hrw-person-prev" in HR_JS
    assert "data-hrw-person-next" in HR_JS


def test_character_identity_system_blinks_talks_and_listens_without_video_rendering():
    assert "function ensureAionCharacterIdentityStyles" in APP_JS
    assert "function renderAionCharacterFaceOverlay" in APP_JS
    assert "@keyframes aionCharacterBlink" in APP_JS
    assert "@keyframes aionCharacterTalk" in APP_JS
    assert "@keyframes aionCharacterListen" in APP_JS
    assert 'data-aion-character-eye="left"' in APP_JS
    assert "setCharacterFaceStateO18AA(key, \"speaking\", 1800)" in APP_JS
    assert "setCharacterFaceStateO18AA(key, \"listening\", 1800)" in APP_JS


def test_main_department_routes_use_the_unified_workspaces_not_legacy_black_pilots():
    expected_routes = {
        "marketing": "renderPilotMarketingWorkspaceSurface",
        "sales": "renderSalesWorkspaceSurface",
        "finance": "renderFinanceWorkspaceSurface",
        "operations": "renderOperationsWorkspaceSurface",
        "support": "renderSupportWorkspaceSurface",
        "hr": "renderHRWorkspaceSurface",
    }
    for key, renderer in expected_routes.items():
        assert f'if (departmentKey === "{key}")' in APP_JS
        assert f'return {renderer}(' in APP_JS

    assert "SUPPORTED.includes(key) && !usesUnifiedDepartmentShell" in APP_JS
    assert "AION_UNIFIED_DEPARTMENT_SHELLS" in APP_JS


def test_real_sales_and_hr_workspaces_mount_below_their_boardroom_packages():
    assert 'data-aion-sales-revenue-mount="true"' in APP_JS
    assert "'[data-aion-sales-revenue-mount=\"true\"]" in SALES_JS
    assert "if (!state.data)" in SALES_JS
    assert "Sales workspace is loading its customer, pipeline, voice and outreach records." in SALES_JS
    assert 'data-aion-hr-people-mount="true"' in APP_JS
    assert "'[data-aion-hr-people-mount=\"true\"]" in HR_JS


def test_finance_and_support_keep_their_completed_operational_workspaces():
    assert "window.AionFinancePilot.render()" in APP_JS
    assert 'data-aion-support-case-mount="true"' in APP_JS


def test_marketing_and_operations_no_longer_embed_the_legacy_terminal_surface():
    marketing_start = APP_JS.index("function renderPilotMarketingWorkspaceSurface")
    marketing_end = APP_JS.index("function renderMarketingManualWorkspaceSurface", marketing_start)
    marketing = APP_JS[marketing_start:marketing_end]
    assert "renderAionDepartmentScopedPilotSurface" not in marketing

    operations_start = APP_JS.index("function renderOperationsWorkspaceSurface")
    operations_end = APP_JS.index("function renderSupportCompactDirectorCard", operations_start)
    operations = APP_JS[operations_start:operations_end]
    assert "renderAionDepartmentScopedPilotSurface" not in operations
    assert 'data-aion-operations-command-centre="true"' in operations


def test_hr_person_modal_preserves_unsaved_draft_during_background_refreshes():
    assert "if (!panel.draft) panel.draft = clone(initialPerson);" in HR_JS
    assert "function syncPersonDraft(form)" in HR_JS
    assert "state.panel.draft = { ...(state.panel.draft || {}), ...values };" in HR_JS
    assert "function rememberPersonDraftFocus(field)" in HR_JS
    assert "field.focus({ preventScroll: true });" in HR_JS
    assert "field.setSelectionRange(state.panel.selectionStart" in HR_JS
    assert "state.panel.scrollTop = panel.scrollTop" in HR_JS
