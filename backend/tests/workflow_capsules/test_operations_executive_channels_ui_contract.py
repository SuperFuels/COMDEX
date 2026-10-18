from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
ROUTER = Path("backend/api/workflow_capsule_router.py").read_text(encoding="utf-8")
DESKTOP_BACKEND = Path("backend/desktop_app.py").read_text(encoding="utf-8")


def test_operations_command_centre_has_live_department_channel_controls():
    for marker in (
        'data-aion-operations-run-briefing',
        'data-aion-operations-channel-thread',
        'data-aion-operations-channel-form',
        'data-aion-operations-channel-input',
        'data-aion-operations-briefing-mode',
    ):
        assert marker in APP


def test_operations_frontend_calls_protected_executive_routes():
    for route in ("executive-status", "channel-history", "channel-turn", "morning-briefing"):
        assert f'"{route}"' in APP
        assert f'operations-conversation/{route}' in ROUTER


def test_si_executive_team_reuses_the_operations_morning_briefing_record():
    executive = APP[
        APP.index("function normaliseAionExecutiveBriefingItemsV1"):
        APP.index("function renderBoardroomSpatialView")
    ]
    for marker in (
        'data-aion-executive-run-morning-briefing',
        'data-aion-executive-terminal',
        'data-aion-executive-meeting-workspace',
    ):
        assert marker in executive
    assert 'aionOperationsConversationRequest("executive-status"' in executive
    assert 'aionOperationsConversationRequest("morning-briefing"' in executive
    assert "Live with the mobile executive network" not in executive
    assert 'source.length >= 4' in executive
    assert 'source.join("").trim()' in executive
    assert "Legacy operating record needs refresh" in executive
    assert "Live business activity" not in executive
    assert "Verified signals moving through the operating system" not in executive
    assert "aion-executive-console-grid" in executive
    assert "aion-executive-terminal-bank" in executive
    assert "aion-live-terminal-report" in executive
    assert "awaiting new work" in executive
    assert "data-aion-executive-terminal-tab" in executive
    assert "CEO / Board" in executive
    assert "aion-executive-briefing-lower" not in executive
    assert "aion-executive-briefing-history" not in executive
    assert "End-of-day operating reviews" not in executive
    assert "aion-executive-department-minutes" not in executive
    assert "COO · central operating terminal" in executive
    assert 'item.key !== "people"' in executive
    assert 'displayActions = actions.filter' in executive
    assert 'displayFeedback = feedback.filter' in executive
    assert 'displayChannels = channels.filter' in executive
    assert 'toLowerCase() !== "people"' in executive
    assert "The live operating layer of the business" not in executive
    assert "Operating chair" not in executive
    assert "Close operating day" in executive
    assert "aionExecutiveStatusSignatureV2" in executive
    assert "readCachedAionExecutiveStatusV2" in executive
    assert "cacheAionExecutiveStatusV2" in executive
    assert "renderAionExecutiveTerminalShellV2" in executive
    assert '[["marketing", 0], ["sales", 1], ["finance", 2], ["support", 3]]' in executive
    assert "getAionExecutiveMarketingChannelLinesV2" in executive
    assert "getAionExecutiveCooReportsV2" in executive
    assert "RED FLAG · COMMERCIAL BOTTLENECK" in executive
    assert "Marketing → Sales → Cash flow" in executive
    assert "Channels: ${channelResults.join" in executive
    assert "Decision requested: ${decisions.join" in executive
    assert 'kind: "bottleneck"' in executive
    assert 'kind: "department-report"' in executive
    assert 'department: signal.key' in executive
    assert 'priority: 100' in executive
    assert '.sort((a, b) => String(a.at).localeCompare(String(b.at))' in executive
    assert 'class="aion-coo-terminal-stream aion-live-terminal-scroll"' in executive
    assert 'class="aion-coo-terminal-line aion-coo-awaiting"' in executive
    assert '<b>${escapeHtml(item.from)} &gt;</b>' in executive
    assert 'scope.querySelectorAll(".aion-live-terminal-scroll")' in executive
    assert "No positive Marketing outcome has been recorded across the available channels yet." in executive
    assert "Generate the first measurable acquisition result through an available channel" in executive
    for status_line in (
        "Inbox & Email · new sales enquiries",
        "Agent-to-Agent · new sales requests",
        "Social accounts",
        "Scheduled posts",
        "Adverts live",
    ):
        assert status_line in executive
    assert "window.__aionWebsiteEnquiryFeedRows" in executive
    assert "sampleRows" not in executive
    terminal_renderer = executive[
        executive.index("function renderAionExecutiveTerminalV2"):
        executive.index("function renderAionExecutiveBriefingWorkspaceContentV1")
    ]
    assert terminal_renderer.index("channelLines.map") > terminal_renderer.index('renderAionExecutiveTerminalReportLinesV2("action"')
    assert terminal_renderer.index("channelLines.map") < terminal_renderer.index("awaiting new work")
    assert 'class="aion-live-terminal-scroll"' in terminal_renderer
    assert "background:#fff!important" in APP
    assert "font:500 11px/1.5" in APP
    assert ".aion-live-terminal-line { display:block;" in APP
    assert "overflow-wrap:anywhere" in APP
    assert ".aion-live-terminal-line>b { display:inline;" in APP
    assert ".aion-live-terminal-line { display:block;" in APP
    assert "color:#111827!important; text-align:left!important" in APP
    assert '.aion-live-terminal-line[data-tone="risk"]>b { color:#b77900!important; }' in APP
    assert '.aion-live-terminal-line[data-tone="decision"]>b { color:#7c3aed!important; }' in APP
    assert ".aion-live-terminal-line>span { display:inline;" in APP
    assert '"channels &gt;"' in executive
    assert "[channels]" not in executive
    assert 'article[data-kind="bottleneck"]' in APP
    assert ".aion-coo-terminal-line { display:block;" in APP
    assert '.aion-coo-terminal-line[data-kind="signal"],.aion-coo-terminal-line[data-kind="action"],.aion-coo-terminal-line[data-kind="issue"] { color:#111827!important; }' in APP
    for department in ("marketing", "sales", "finance", "support"):
        assert f'[data-department="{department}"]' in APP
    assert "function scrollAionExecutiveTerminalsToLatestV2" in executive
    assert "history.scrollTop = history.scrollHeight" in executive
    assert '.aion-live-terminal-awaiting { margin:11px 0 0!important; padding:0 0 4px; border:0!important; background:transparent!important' in APP
    assert terminal_renderer.index("channelLines.map") < terminal_renderer.index("awaiting new work") < terminal_renderer.index('</div>\n      </div>')
    assert "Connecting the Executive operations network" not in executive
    assert "The Executive briefing could not be loaded." not in executive


def test_department_channels_do_not_render_the_old_placeholder():
    command = APP[APP.index("function renderOperationsCommandCentre"):]
    assert "Once the Mission bridge is connected" not in command[:18_000]


def test_connections_page_lists_priority_social_channels_with_connection_controls():
    governance_start = APP.rindex("function renderGovernancePanel")
    governance = APP[governance_start:APP.index("window.aionRenderOriginalBusinessMapGovernanceV2", governance_start)]
    assert 'activeConnectionCategory = "apps"' in APP
    assert 'data-aion-connection-category=' in governance
    assert 'data-aion-connection-category-panel=' in governance
    assert 'grid-template-columns:190px minmax(0,1fr)' in governance
    assert 'overflow-x:auto' not in governance
    for category in ("Business apps", "Social media", "Advertising", "Accounting", "Files", "MCP tools", "AI models"):
        assert f'label: "{category}"' in governance
    assert "const socialProviderCatalogue = [" in governance
    assert "const liveSocialConnections = new Map(" in governance
    assert "const socialConnections = socialProviderCatalogue.map" in governance
    assert "const businessAppCatalogue = [" in governance
    assert "const modelProviderCatalogue = [" in governance
    assert "A slow status request must never make the actual business apps vanish" in governance
    assert "Checking connection…" in governance
    assert 'const leadActionLabel = provider.is_lead ? "Lead model" : canChooseLead ? "Use as lead" : "Connect first"' in governance
    assert 'data-aion-set-lead-model="${escapeHtml(provider.id)}"' in governance
    assert 'marketingPermissionTier: canAuthorize ? "advertising" : ""' in governance
    assert 'disabled: !canAuthorize' in governance
    assert 'data-aion-platform-credentials="meta"' in governance
    assert 'data-aion-save-platform-credentials="meta"' in governance
    assert 'data-aion-social-connection-list="true"' in governance
    assert 'data-aion-social-connection-row="${escapeHtml(provider)}"' in governance
    assert 'Connect ${escapeHtml(platformLabel)}' in governance
    assert 'data-aion-sync-marketing-metrics="${escapeHtml(provider)}"' in governance
    assert '"meta:page": "Facebook Page"' in governance
    assert '"meta:instagram": "Instagram profile"' in governance
    assert '"meta:ad_account": "Ad account"' in governance
    assert 'data-aion-exam-marketing-provider="${escapeHtml(provider)}"' in governance
    assert "api/aion/marketing/connections/meta/callback" in governance
    assert 'data-aion-connect-marketing-provider' in governance
    assert "window.__aionMarketingConnectionStateV1" in governance
    assert "window.__aionLoadMarketingConnectionsV1" in governance
    assert "connectionStatusIsStale" in governance
    assert "aionMarketingConnectionState?.loading" not in governance
    for provider in ("meta", "linkedin", "youtube", "tiktok", "x", "pinterest", "google_business", "google_ads", "microsoft_ads"):
        assert f'"{provider}"' in governance


def test_social_connection_tiles_always_start_oauth_on_a_dedicated_click_path():
    assert "activateAionMarketingProviderTile" in APP
    assert "await connectAionMarketingProvider(normalizedProvider)" in APP
    assert "async function getAionMarketingActingPersonId()" in APP
    assert 'person.role_ids.includes("role.owner_director")' in APP
    assert "const acting_person_id = await getAionMarketingActingPersonId()" in APP
    assert "window.__aionMarketingProviderTileOAuthHandlerV1" in APP
    assert 'window.addEventListener("click", (event) =>' in APP
    assert 'event.target?.closest?.("[data-aion-connect-marketing-provider]")' in APP
    assert "event.stopImmediatePropagation()" in APP
    assert 'connection?.connected && String(connection.permission_tier || "analytics") === normalizedTier' not in APP
    assert "opened === true || opened?.ok === true" in APP
    assert "getAionMarketingProviderTileCopy" in APP
    assert 'detail: `Connect Tessaris to your ${account}`' in APP
    assert 'aria-label="${escapeHtml(actionLabel)}"' in APP
    assert 'approve “Connect Tessaris”' in APP
    assert "Connected to Tessaris · tested · reporting" in APP
    assert "Pinterest approval pending · available after app review" in APP


def test_desktop_scheduler_runs_due_morning_briefing_without_operations_page_open():
    assert "executive_briefings.status(workspace.name)" in DESKTOP_BACKEND
    assert 'if briefing_status.get("briefing_due")' in DESKTOP_BACKEND
    assert "executive_briefings.run_morning_briefing" in DESKTOP_BACKEND
