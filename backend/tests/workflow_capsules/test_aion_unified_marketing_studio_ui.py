from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_marketing_workspace_includes_campaign_content_studio_and_calendar():
    start = APP.index("function renderPilotMarketingWorkspaceSurface")
    end = APP.index("function renderMarketingManualWorkspaceSurface", start)
    surface = APP[start:end]
    assert 'data-aion-marketing-automation-studio="true"' in surface
    assert "renderAionMarketingCampaignJourney()" in surface
    assert "renderAionMarketingContentStudio()" in surface
    assert "renderAionMarketingCreativeLab()" in surface
    assert 'data-aion-phase23y-persistent-pilot-terminal-input' in surface
    assert 'data-aion-phase23y-persistent-pilot-start' in surface


def test_manual_and_aion_creation_share_the_governed_launch_path():
    assert 'desktopStore.setMarketingField("brief", value);' in APP
    assert 'document.getElementById("launchMarketingBtn")' in APP
    assert "async function launchAionMarketingCampaign(" in APP
    assert 'apiPost("/api/local-node/marketing/launch"' in APP
    assert "buildBrandFoundationPayload()" in APP
    assert "buildCreativeAssetsPayload()" in APP
    assert 'data-aion-apply-content-edits' in APP
    assert 'data-aion-retry-campaign-image' in APP
    assert 'id="marketing-content-calendar"' in APP


def test_old_sidebar_marketing_route_redirects_to_unified_marketing_department():
    app_tabs = APP[APP.index("const APP_TABS"):APP.index("/*", APP.index("const APP_TABS"))]
    assert '{ key: "marketing_stream", label: "Marketing Stream" }' not in app_tabs
    redirect = APP[APP.index('if (state.activeTab === "marketing_stream")'):]
    redirect = redirect[: redirect.index('if (state.activeTab === "brand_foundation")')]
    assert 'state.activeTab = "live_agents";' in redirect
    assert 'state.selectedLiveAgentDepartment = "marketing";' in redirect
    assert "return renderLiveAgentsSurface();" in redirect


def test_existing_content_image_approval_and_history_capabilities_are_preserved():
    assert 'id="marketingCreativeAssetUploadInput"' in APP
    assert 'id="launchMarketingBtn"' in APP
    assert "renderMarketingApprovalCard" in APP
    assert "renderCompactRecentRuns" in APP
    assert "renderCompactResolvedApprovals" in APP
    assert "renderMarketingAssetTypeOptions" in APP


def test_boardroom_minutes_govern_cmo_production_brief():
    assert "function getAionMarketingBoardroomBrief()" in APP
    assert "function composeAionMarketingProductionBrief(" in APP
    assert '"BOARDROOM MEETING-MINUTES BRIEF (governing):"' in APP
    assert '"CMO EXECUTION DETAIL:"' in APP
    assert '"EVIDENCE AND AUTHORITY:"' in APP
    assert "const productionBrief = composeAionMarketingProductionBrief(value);" in APP
    assert "brief: productionBrief" in APP


def test_marketing_requires_real_evidence_and_labels_placeholders_honestly():
    assert "renderAionMarketingDirectorBrief()" in APP
    assert "BOARDROOM → CMO → PRODUCTION" in APP
    assert 'data-aion-strategy-assets' in APP
    assert "Campaign production is intentionally paused" in APP
    assert "Draft layout ready · original evidence still required" in APP
    assert "Layout placeholder—not finished marketing" in APP
    assert 'imageGeneration.provider === "tessaris_owned_media"' in APP


def test_generated_runtime_media_uses_the_bounded_static_route():
    assert '/local-runtime/' in APP


def test_all_marketing_workspaces_share_the_new_blue_brand_frame():
    for marker in (
        'data-aion-marketing-automation-studio="true"',
        'id="marketing-content-calendar"',
        'data-aion-marketing-creative-lab',
        'id="manual-marketing-studio"',
        'data-aion-marketing-connections-centre',
    ):
        assert marker in APP
    assert APP.count("border:2px solid #0ea5e9") >= 6
    assert APP.count("background:#f8fcff;border-bottom:1px solid #bae6fd;padding:18px") >= 5
    assert "LOCAL TIMELINE & CLIP EXPORTER" in APP
    assert "[data-aion-phase23y-pilot-marketing-workspace] .primary-btn" in APP
    assert "background:#0284c7 !important" in APP
    assert "background:#0369a1 !important" in APP
