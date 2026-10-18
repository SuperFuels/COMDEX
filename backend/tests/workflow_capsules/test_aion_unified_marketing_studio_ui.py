from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
WORKFLOW_RUNTIME = (
    ROOT / "backend/modules/aion_agents/runtime/workflow_execution_runtime.py"
).read_text(encoding="utf-8")


def test_marketing_workspace_separates_the_shared_workflow_into_clear_views():
    for view in ("CAMPAIGNS", "CALENDAR", "CREATE", "APPROVALS", "LIBRARY"):
        assert f"LIVE_AGENT_VIEWS.{view}" in APP
    assert "function renderMarketingOverviewSurface" in APP
    assert "function renderMarketingCampaignsSurface" in APP
    assert "function renderMarketingCalendarWorkspace" in APP
    assert "function renderMarketingCreateSurface" in APP
    assert "function renderMarketingLibrarySurface" in APP
    assert 'data-aion-phase23y-persistent-pilot-terminal-input' in APP
    assert 'data-aion-phase23y-persistent-pilot-start' in APP
    assert "Boardroom, Operations, the business owner and connected AI assistants all create the same campaign record" in APP
    assert 'window.addEventListener("pointerdown"' in APP
    assert "openMarketingWorkspaceView" in APP


def test_marketing_overview_contains_the_migrated_executive_function_snapshot():
    overview_start = APP.index("function renderMarketingPerformanceOverviewV1")
    overview_end = APP.index("function renderMarketingCampaignsSurface", overview_start)
    overview = APP[overview_start:overview_end]
    assert 'department.key === "marketing"' in overview
    assert 'data-aion-marketing-performance-overview="true"' in overview
    assert "PERFORMANCE & ACCOUNTABILITY" in overview
    assert "Marketing function snapshot" in overview
    assert "Open actions" in overview
    assert "Active KPIs" in overview
    assert "Automations" in overview
    assert "Completed runs" in overview
    assert "renderAionMarketingFunctionSnapshotV1(marketingDepartment)" in overview
    assert "renderMarketingPerformanceOverviewV1()" in overview

    dashboard_start = APP.index("function renderDashboardSurface()")
    dashboard_end = APP.index("if (!window.__aionExecutiveDashboardNavigationV1Installed", dashboard_start)
    dashboard = APP[dashboard_start:dashboard_end]
    assert "renderAionExecutiveDepartmentCarouselV1(model.departments)" in dashboard


def test_marketing_calendar_has_pipeline_and_real_week_view():
    assert "function renderMarketingWorkInProgress" in APP
    assert "function renderMarketingWeeklyCalendar" in APP
    assert 'data-marketing-calendar-workspace-view="board"' in APP
    assert 'data-marketing-calendar-workspace-view="calendar"' in APP
    assert 'data-marketing-calendar-week-shift="-7"' in APP
    assert 'data-marketing-calendar-week-today="true"' in APP
    assert "Ideas & planned" in APP
    assert "Needs review" in APP
    assert "WEEKLY CONTENT SCHEDULE" in APP
    assert 'data-aion-marketing-full-page="${escapeHtml(fullPageKey)}"' in APP
    assert "← Back to Marketing" in APP
    assert "Content pipeline & calendar" in APP
    assert "Create calendar item" not in APP
    assert "Create the content first, then approve it and allocate it to the calendar." in APP
    calendar_workspace = APP[APP.index("function renderMarketingCalendarWorkspace"):APP.index("function renderMarketingCreateSurface")]
    assert calendar_workspace.index(">Calendar</button>") < calendar_workspace.index(">+ Create content</button>")
    assert 'width:auto!important' in calendar_workspace
    weekly_calendar = APP[APP.index("function renderMarketingWeeklyCalendar"):APP.index("function renderMarketingCalendarWorkspace")]
    assert ">+ Create content</button>" not in weekly_calendar
    assert "No content scheduled" in weekly_calendar


def test_create_view_uses_one_content_record_instead_of_two_open_studios():
    assert "activeView === LIVE_AGENT_VIEWS.CALENDAR || activeView === LIVE_AGENT_VIEWS.CREATE || activeView === LIVE_AGENT_VIEWS.LIBRARY" in APP
    assert 'const fullPageKey = isCreatePage ? "create" : isLibraryPage ? "library" : "calendar";' in APP
    assert 'const fullPageTitle = isCreatePage ? "Create marketing content"' in APP
    assert "Preview, edit and schedule the same item" not in APP
    assert "DRAFT · NOT PUBLISHED" not in APP
    assert "CURRENT CONTENT RECORD" in APP
    assert "data-aion-marketing-create-split" in APP
    assert "data-aion-marketing-create-split-handle" in APP
    assert 'aria-label="Resize creator and current content record"' in APP
    assert "marketingCreateBriefPercent" in APP
    assert "function installMarketingCreateSplitter" in APP
    assert "One brief, one content record" not in APP
    assert "SHORT VIDEO WHEN SUPPORTED" not in APP
    create_surface = APP[APP.index("function renderMarketingCreateSurface"):APP.index("function renderMarketingLibrarySurface")]
    assert "renderAionMarketingManualQuickStudio()" in create_surface
    assert "renderAionMarketingContentStudio()" in create_surface
    assert create_surface.index("data-aion-marketing-create-brief-pane") < create_surface.index("data-aion-marketing-create-record-pane")


def test_marketing_library_opens_as_its_own_full_width_page():
    assert "const isLibraryPage = activeView === LIVE_AGENT_VIEWS.LIBRARY;" in APP
    assert 'isLibraryPage ? "MARKETING · BRAND & ASSET LIBRARY"' in APP
    assert 'isLibraryPage ? "Marketing library"' in APP
    assert 'data-aion-marketing-full-page="${escapeHtml(fullPageKey)}"' in APP
    assert '[data-aion-marketing-full-page="library"] .aion-marketing-library-grid' in APP


def test_marketing_library_is_a_visual_filtered_content_board():
    assert "function renderMarketingVisualLibrarySurface" in APP
    assert "data-marketing-library-board" in APP
    assert "data-marketing-library-card-status" in APP
    assert "data-marketing-library-card-platform" in APP
    assert "data-marketing-library-status-filter" in APP
    assert "data-marketing-library-platform-filter" in APP
    for label in ("Saved", "Scheduled", "Posted", "All platforms"):
        assert label in APP
    assert "marketingLibraryStatusFilter" in APP
    assert "marketingLibraryPlatformFilter" in APP


def test_creator_can_clear_repurpose_save_post_and_schedule_content():
    assert 'data-aion-clear-marketing-canvas' in APP
    assert "function clearAionMarketingCanvas()" in APP
    assert 'desktopStore.setMarketingField(field, ["aionCampaignPlan", "aionCampaignLatestRun"].includes(field) ? null' in APP
    assert "function applyAionMarketingTemplateToOpenDraft(template, key)" in APP
    assert '"Repurposing the open draft for " + template.label' in APP
    assert "void regenerateAionMarketingCampaign(sourceBrief);" in APP
    assert 'templateKey: lab.createTemplate || "facebook_feed"' in APP
    for control in (
        "data-aion-save-current-to-library",
        "data-aion-manual-post-current",
        "data-aion-schedule-current-content",
    ):
        assert control in APP
    assert "savedLibraryItems" in APP
    assert 'status: "saved"' in APP
    assert 'sourceRunId: String(run.id || lab.campaignRunId || "")' in APP
    assert "Saved to Library ✓" in APP
    assert "requestRender();" in APP
    assert "Content saved to the Marketing Library." in APP
    assert "Content scheduled on the Marketing calendar. It has not been published." in APP
    assert "Tessaris has not published it." in APP


def test_clear_canvas_is_durable_and_removes_working_assets():
    assert 'desktopStore.setMarketingField("aionCampaignCanvasCleared", true);' in APP
    assert "function setAionMarketingCanvasDurablyCleared(cleared)" in APP
    assert 'AionDesktopPreferences.set(key, "true")' in APP
    assert 'AionDesktopPreferences.set(globalKey, "true")' in APP
    assert 'const canvasWasCleared = Boolean(storedForm.aionCampaignCanvasCleared) || isAionMarketingCanvasDurablyCleared();' in APP
    assert 'if (!canvasWasCleared && !window.__aionMarketingCreativeLab.campaignResult' in APP
    clear_canvas = APP[APP.index("function clearAionMarketingCanvas()"):APP.index("function renderAionMarketingContentStudio()")]
    assert '"creativeAssets"' in clear_canvas
    assert 'subjectOfferingId: ""' in clear_canvas
    assert 'campaignResult: null' in clear_canvas
    workspace = APP[APP.index("function renderPilotMarketingWorkspaceSurface"):APP.index("function renderMarketingManualWorkspaceSurface")]
    assert 'const shouldHydrateLatestRun = !canvasWasCleared && latestCampaignRun' in workspace
    assert 'if (!hydrated?.id || isAionMarketingCanvasDurablyCleared()) return;' in workspace


def test_visible_platform_and_format_are_authoritative_for_manual_generation():
    assert 'platform: "facebook_reels"' in APP
    launch = APP[APP.index("async function launchAionMarketingCampaign"):APP.index("async function regenerateAionMarketingCampaign")]
    assert 'if (mode === "manual")' in launch
    assert 'lab.platforms = [selectedTemplate.platform];' in launch
    assert 'lab.formats = [selectedTemplate.format];' in launch
    assert 'desktopStore.setMarketingField("aionCampaignCanvasCleared", false);' in launch


def test_marketing_selects_one_or_more_saved_personas_without_replacing_brand_rules():
    assert "data-marketing-persona-selector" in APP
    assert "data-marketing-persona-summary" in APP
    assert "Select audience" in APP
    assert "data-marketing-persona-select" in APP
    assert 'desktopStore.setMarketingField("selectedPersonaIds", selectedIds);' in APP
    assert 'desktopStore.setMarketingField("targetAudience", audienceSummary);' not in APP
    assert "+ Create audience" in APP
    assert "Manage audiences" in APP
    assert "selected_personas: selectedPersonaProfiles" in APP
    assert "Tone of voice, core messaging and visual rules remain governed by Brand Foundation." in APP


def test_guided_creator_starts_with_platform_and_uses_brand_foundation():
    assert "const MARKETING_CREATE_TEMPLATES" in APP
    assert "const MARKETING_PLATFORM_FORMATS" in APP
    for label in ("Facebook", "Instagram", "LinkedIn", "Google Business", "TikTok", "YouTube"):
        assert label in APP
    for format_label in ("Single image post", "Carousel", "Story", "Reel / video"):
        assert format_label in APP
    assert "data-marketing-create-platform" in APP
    assert 'data-marketing-create-template=' in APP
    assert "Recommended canvas" in APP
    assert "Copy structure" in APP
    assert "Brand Foundation applied automatically" in APP
    assert 'id="marketingFunnelGoalInput"' in APP
    assert 'id="marketingCampaignNotesInput"' in APP
    assert "Any AI-assisted image remains a draft until reviewed." in APP
    assert "brandFoundationState: foundation" in APP
    assert "brand_map: foundation.brand_map || foundation.brandMap || {}" in APP
    assert "window.__tessarisMarketingWorkspaceView = nextView" in APP
    assert "cleanMarketingLegacySeed" in APP
    assert "Only saved workspace facts are used." in APP
    assert 'placeholder="Choose a Brand Foundation audience or describe one"' in APP


def test_model_returns_a_structured_design_brief_for_each_creative():
    assert "_parse_marketing_design_brief" in WORKFLOW_RUNTIME
    for field in (
        "headline",
        "supporting_copy",
        "purpose",
        "image_focal_point",
        "crop",
        "text_position",
        "typography_hierarchy",
        "brand_colours",
        "logo_position",
        "cta_treatment",
        "selected_template",
        "verified_facts_used",
    ):
        assert field in WORKFLOW_RUNTIME
        assert field in APP
    assert "Structured design brief" in APP


def test_marketing_choice_buttons_do_not_resize_when_selected():
    assert 'class="secondary-btn marketing-platform-choice"' in APP
    assert 'class="secondary-btn marketing-creation-method-choice"' in APP
    assert "width:auto!important;min-width:0!important;flex:0 0 auto!important" in APP


def test_platform_guidance_is_editable_and_can_be_reset():
    for field in ("canvasSize", "aspectRatio", "copyStructure", "creativeDirection"):
        assert f'data-marketing-specification-field="{field}"' in APP
    assert "getMarketingCreateSpecification" in APP
    assert "templateOverrides" in APP
    assert "data-marketing-reset-specification" in APP


def test_branded_template_studio_is_connected_to_the_creator():
    assert 'label: "Select a branded template"' in APP
    assert "data-marketing-open-template-builder" in APP
    assert "data-marketing-template-builder=\"true\"" in APP
    assert "data-marketing-template-builder-assets" in APP
    assert "renderMarketingTemplateInspirationAssets" in APP
    assert 'data-marketing-remove-template-asset' in APP
    assert '"+ Add more"' in APP
    assert "Preview unavailable" in APP
    assert "previous_template: previousTemplate" in APP
    assert "generation_index: generationIndex" in APP
    assert 'full_bleed:' in APP
    assert 'modular:' in APP
    assert 'Template image placeholder' in APP
    assert 'Inspiration images guide the style only and are never inserted into the saved template.' in APP
    assert 'alt="Inspiration preview"' not in APP
    assert "data-marketing-generate-brand-template" in APP
    assert "data-marketing-save-brand-template" in APP
    assert "/api/local-node/marketing/brand-templates/generate" in APP
    assert "selectedBrandedTemplateId" in APP
    assert "branded_template: activeBrandedTemplate" in APP
    assert "desktopStore.persistCache();\n  requestRender();" in APP
    assert "Reset to recommended" in APP
    assert "canvas_size: activeSpecification.canvasSize" in APP
    assert "aspect_ratio: activeSpecification.aspectRatio" in APP
    assert "copy_structure: activeSpecification.copyStructure" in APP
    assert "creative_direction: activeSpecification.creativeDirection" in APP


def test_marketing_can_promote_a_catalogue_product_with_its_image_and_link():
    assert "Promote a product or service" in APP
    assert "data-marketing-product-offering" in APP
    assert 'id="marketingDestinationUrlInput"' in APP
    assert "getAionMarketingSelectedOffering" in APP
    assert "aionMarketingOfferingAsset" in APP
    assert "subject_offering_name" in APP
    assert "product_url" in APP
    assert "product_image_url" in APP
    assert "catalogue_source" in APP


def test_marketing_chat_splitter_is_interactive_and_accessible():
    assert "function installMarketingWorkspaceSplitter" in APP
    assert 'data-aion-marketing-split-handle="true"' in APP
    assert 'aria-label="Resize Marketing Pilot chat"' in APP
    assert 'window.addEventListener("pointermove"' in APP
    assert 'window.addEventListener("pointerup", finishResize' in APP
    assert 'marketingPilotPanePercent' in APP


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


def test_manual_creation_shows_progress_and_opens_the_created_record():
    assert 'data-aion-marketing-create-status' in APP
    assert 'aria-live="polite"' in APP
    assert 'Creating draft…' in APP
    assert 'data-aion-marketing-current-record' in APP
    assert '<section data-aion-marketing-current-record' in APP
    assert 'Facebook draft ready for review' in APP
    assert 'document.querySelector("[data-aion-marketing-current-record]")' in APP


def test_facebook_carousel_navigation_preserves_the_preview_position():
    assert 'data-facebook-post-mockup="${escapeHtml(previewKey)}"' in APP
    assert 'event.preventDefault();' in APP
    assert 'const previewTop = currentPreview?.getBoundingClientRect?.().top;' in APP
    assert 'scrollHost.scrollTop += delta;' in APP


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


def test_marketing_review_is_a_clickable_content_approval_queue():
    assert "function renderMarketingReviewSurface" in APP
    assert "function renderMarketingReviewItem" in APP
    assert "function findMarketingRunForApproval" in APP
    assert 'data-marketing-review-item=' in APP
    assert "renderMarketingRunCard(linkedRun)" in APP
    assert "Approve draft" in APP
    assert "Reject / request changes" in APP
    assert "It does not publish automatically." in APP
    assert "Publishing remains a separate action." in APP
    assert 'return renderMarketingReviewSurface(selectedAgentCard);' in APP


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
    assert "[data-aion-marketing-command-centre] [data-aion-marketing-overview] .panel" in APP
    assert "border-top:4px solid #2563eb" in APP
    assert "LOCAL TIMELINE & CLIP EXPORTER" in APP
    assert "[data-aion-phase23y-pilot-marketing-workspace] .primary-btn" in APP
    assert "background:#0284c7 !important" in APP
    assert "background:#0369a1 !important" in APP
