from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_sales_revenue_workspace_is_loaded_and_replaces_placeholder_with_operating_surface():
    index = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert '<script src="./aion_sales_revenue_workspace.js"></script>' in index
    assert 'data-aion-sales-live-agents-workspace-o14d="true"' in app
    assert 'data-aion-shared-department="sales"' in sales
    assert "Sales Revenue Spine" in sales
    assert "AI SALES CALLER" in sales
    assert "external_transport_started" not in sales or "No external call was initiated" in sales
    assert "Human handoff" in sales
    assert "Prepare appointment" in sales
    assert "AI identity was disclosed" in sales
    assert "Connect website enquiries" in sales
    assert "READ-ONLY GMAIL" not in sales
    assert "Import matching enquiries now" not in sales
    assert "Run safety check" in sales
    assert "CALLS AND RESULTS" in sales
    assert "if (mount() && id && (state.workspaceId !== id || !state.data)) load()" in sales
    assert "new AbortController()" in sales


def test_sales_ui_keeps_external_actions_exactly_approved_and_fail_closed():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "This does not write to a calendar or notify the customer" in sales
    assert "no external writes" in sales.lower()
    assert "It does not initiate an external call" in sales
    assert "Review and approve call" in sales
    assert "Start this exact approved customer call now?" in sales
    assert "signed provider readback" in sales


def test_sales_caller_explains_the_real_user_workflow_in_plain_language():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "It does not answer incoming calls or call anyone automatically" in sales
    assert "Set the call plan" in sales
    assert "Check it safely" in sales
    assert "Approve for use" in sales
    assert "This still does not start or schedule a call" in sales
    assert "Edit call settings" in sales
    assert "Run safety check" in sales
    assert "Approve this call plan" in sales
    assert "Calling is switched off" in sales
    assert "Refresh results" in sales
    assert "Phone connection details" in sales
    assert "Save call plan" in sales
    assert "Calls made" in sales
    assert "Live or awaiting result" in sales
    assert "Completed calls" in sales
    assert "Total call duration" in sales
    assert "latestEvents" in sales
    assert "durationLabel" in sales


def test_open_enquiry_draft_survives_background_workspace_redraws():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "enquiryDraft" in sales
    assert "enquiryFocus" in sales
    assert "rememberEnquiryDraft(form)" in sales
    assert "rememberEnquiryFocus(event.target)" in sales
    assert "restoreEnquiryFocus(anchor, focusState)" in sales
    assert "value=\"${esc(draft.first_name || '')}\"" in sales
    assert "${esc(draft.enquiry || '')}" in sales


def test_manual_enquiry_branches_between_person_and_business_identity():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "Who is this ${entryMode" in sales
    assert 'name="customer_type" value="person"' in sales
    assert 'name="customer_type" value="business"' in sales
    assert "PERSONAL CUSTOMER" in sales
    assert "BUSINESS CONTACT" in sales
    assert 'name="first_name"' in sales
    assert 'name="last_name"' in sales
    assert 'name="address"' in sales
    assert 'name="position_title"' in sales
    assert 'name="department"' in sales
    assert 'name="phone_extension"' in sales
    assert "Select a customer type to continue." in sales
    assert "value.customer_type === 'business'" in sales


def test_sales_home_uses_one_unified_source_and_stage_flow():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    markup = sales.split("function markup()", 1)[1].split("function syncSalesWorkspaceChromeVisibility", 1)[0]
    assert "LEADS AND OPPORTUNITIES" in markup
    assert "Revenue flow" in markup
    assert "srw-unified-revenue-flow" in markup
    assert "srw-lead-flow" not in markup
    assert "recentEnquiryLanes()" not in markup
    assert "Lead source" in sales
    assert "Stage" in sales
    assert "srw-deal-strip" in sales
    assert "data-srw-source-filter" in sales
    assert "data-srw-pipeline-filter" in sales
    assert "state.pipelineFilter" in sales
    assert "pipelineFilter: 'new'" in sales
    assert '<select data-srw-pipeline-filter' in sales
    assert "state.pipelineFilter = event.target.value || 'new'" in sales
    controls = sales.split('class="srw-deal-controls"', 1)[1].split('class="srw-deal-strip"', 1)[0]
    assert controls.index('class="srw-stage-select"') < controls.index('class="srw-deal-search"')
    assert "height:42px;min-height:42px" in sales
    assert "+ Add lead" in markup
    assert "+ Add deal" in markup
    assert "Create deal" in sales
    assert 'name="initial_stage"' in sales
    assert 'name="estimated_value"' in sales
    assert "todayQueue()" not in markup
    assert "vaultWebsiteIntake()" not in markup


def test_website_intake_setup_lives_in_vault_not_sales_dashboard():
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "AionSalesRevenue.renderVaultWebsiteIntake()" in app
    assert 'data-aion-vault-website-intake="true"' in sales
    assert "Create website connection" in sales
    assert "X-Tessaris-Intake-Key" in sales
    assert "Never place it in public browser code" in sales
    assert "HomeFixed queue recovery" in sales


def test_sales_home_is_contained_by_the_visible_workspace_width():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert '[data-aion-sales-revenue-mount="true"],.srw-shell{width:100%;max-width:100%;min-width:0}' in sales
    assert '.srw-shell{overflow-x:clip}' in sales
    assert '.srw-source-strip{display:grid;' in sales
    assert '.srw-commercial-flow>nav{flex-wrap:wrap;overflow:visible}' in sales
    assert '.srw-source-card{width:100%;max-width:100%;min-width:0;' in sales
    assert '.srw-deal-card{width:100%;max-width:100%;min-width:0;' in sales


def test_commercial_flow_uses_a_single_row_carousel_and_client_search():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "pipelineSearch: ''" in sales
    assert 'data-srw-deal-search' in sales
    assert 'placeholder="Start typing a client name…"' in sales
    assert 'data-srw-deal-scroll="-1"' in sales
    assert 'data-srw-deal-scroll="1"' in sales
    assert "strip.scrollBy" in sales
    assert ".srw-deal-strip{display:flex;gap:10px;overflow-x:hidden" in sales
    assert ".srw-deal-card{flex:0 0 calc((100% - 30px)/4)" in sales


def test_unified_flow_filters_the_same_records_by_source_and_stage():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "activeSource === 'all' ? allRows" in sales
    assert "enquirySourceGroup(row) === activeSource" in sales
    assert "activeStages.includes(row.stage)" in sales
    assert "Find client or lead" in sales


def test_stage_chain_is_simplified_and_legacy_states_are_grouped():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    pipeline = sales.split("function pipeline()", 1)[1].split("function syncDealCarouselControls", 1)[0]
    assert "['contacted', 'Contacted', ['contacted', 'qualification', 'human_handoff']]" in pipeline
    assert "['qualified', 'Qualified', ['qualified', 'appointment_proposed']]" in pipeline
    assert "['appointment_booked', 'Appointment Booked', ['appointment_booked']]" in pipeline
    assert "['closed', 'Closed', ['lost']]" in pipeline
    assert "'Qualification'" not in pipeline
    assert "'Appointment Proposed'" not in pipeline
    assert "'Human Handoff'" not in pipeline
    assert "'Lost'" not in pipeline


def test_unified_flow_uses_source_tabs_and_defaults_to_all_sources():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "leadSourceFilter: 'all'" in sales
    assert 'data-srw-source-filter=' in sales
    assert "state.leadSourceFilter = button.dataset.srwSourceFilter" in sales
    assert ".srw-source-tabs{display:flex;min-width:0;gap:6px;overflow-x:auto" in sales
    assert ".srw-source-tabs button.active" in sales


def test_every_sales_editor_survives_workspace_redraws():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "formDrafts" in sales
    assert "rememberFormDraft(form)" in sales
    assert "restoreFormDraft(anchor, state.panel)" in sales
    assert "const form = event.target.closest?.('[data-srw-form]')" in sales
    assert 'data-srw-form="work_event"' in sales


def test_boardroom_background_refresh_does_not_redraw_other_workspaces():
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    assert "function shouldRenderOriginalBusinessMap()" in app
    assert "if (shouldRenderOriginalBusinessMap()) requestRender?.();" in app


def test_customer_record_opens_as_full_sales_workspace_with_clear_navigation():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert 'data-srw-customer-page' in sales
    assert '← Back to Sales' in sales
    assert 'data-srw-open-relationship' in sales
    assert "if (state.panel === 'detail' && selected()) return customerWorkspace();" in sales
    assert "if (closingPanel === 'detail') state.selectedId = '';" in sales


def test_customer_record_has_customer_bound_commercial_workbench():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert 'CUSTOMER COMMERCIAL WORKBENCH' in sales
    assert 'Internal note' in sales
    assert 'New job / project' in sales
    assert 'New quote' in sales
    assert 'Quote variation / add-on' in sales
    assert 'Invoice add-on' in sales
    assert 'data-srw-form="commercial"' in sales
    assert 'data-srw-commercial-mode' in sales
    assert 'data-srw-add-cost-line' in sales
    assert 'data-srw-remove-cost-line' in sales
    assert "commercialDrafts[row.opportunity_id]" in sales


def test_customer_commercial_editor_starts_collapsed_and_pilot_action_opens_one_intent():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "mode: '', reference:" in sales
    assert "const expanded = Boolean(draft.mode)" in sales
    assert "Only the selected editor will open" in sales
    assert "data-srw-collapse-commercial" in sales
    assert "data-srw-pilot-action" in sales
    assert "New action…" in sales
    assert "New note" in sales
    assert "New quote" in sales
    assert "function activateCommercialMode" in sales
    assert "session.activeMode = mode" in sales
    assert "session.quoteInterview = { active: true, stage: 'scope'" in sales
    assert "activateCommercialMode(event.target.value, { fresh: true, announce: true })" in sales


def test_commercial_workbench_calculates_private_totals_and_safe_customer_preview():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    for category in (
        "labour", "materials", "parking", "congestion_charge", "ulez",
        "supplier_subcontractor", "scaffolding", "skip_waste", "other",
    ):
        assert f"['{category}'" in sales
    assert 'function commercialTotals(draft)' in sales
    assert 'grossMargin' in sales
    assert 'CUSTOMER-FACING PREVIEW' in sales
    assert 'This preview excludes internal costs, labour cost rates, internal notes, profit and margin.' in sales
    assert "person_id: line.category === 'labour'" in sales
    assert "row?.attribution?.currency" in sales
    assert "currency: commercialCurrency(row)" in sales
    assert "return `£" not in sales


def test_commercial_save_uses_customer_feed_without_leaving_customer_page():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "if (kind === 'commercial')" in sales
    assert 'commercial_record: commercialRecord' in sales
    assert 'details.customer_facing' in sales
    assert "external_action_performed: false" in sales
    assert "delete state.commercialDrafts[opportunityId]" in sales
    assert "state.selectedId = opportunityId; state.panel = 'detail';" in sales
    assert "await request(`${opportunity}/work-feed/events`" in sales


def test_customer_record_uses_compact_sticky_pilot_footer_with_record_scope():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    assert 'data-srw-pilot-open' in sales
    assert 'data-srw-customer-pilot-footer' in sales
    assert 'data-aion-customer-scoped-pilot-runtime' in sales
    assert 'data-aion-pilot-mission-input' in sales
    assert 'data-aion-pilot-create-draft-mission' in sales
    assert 'position:sticky' in sales
    assert 'renderAionCustomerScopedPilotRuntime' not in sales
    assert "handlePilotInstruction(rawText" in sales
    assert "data-srw-pilot-files" in sales
    assert "＋ Upload file" in sales
    assert "srw-feed-file" in sales
    assert "addCustomerPilotAttachments" in sales
    assert "capture=\"environment\"" in sales
    assert "getAionPilotInteractionStateKey" in app
    assert "renderAionCustomerScopedPilotRuntime" in app
    assert "startAionO21ELiveMicTranscriptCapture" in app
    assert "window.startAionPilotDictation = startAionPilotDictation" in app
    assert "🔴 Stop talking" in app
    assert 'data-aion-customer-pilot-voice-status' in sales
    assert "global.startAionPilotDictation?.()" in sales
    assert "MediaRecorder.isTypeSupported(\"audio/webm;codecs=opus\")" in app
    assert "quoteInterviewStages" in sales
    assert "/api/boardroom/quote-interview" in sales
    assert "The original customer enquiry is not supplied" in (ROOT / "backend/api/boardroom_provider_router.py").read_text(encoding="utf-8")
    assert "stop and generate quote" in sales
    assert "startAionPilotSilenceTurnMonitor" in app
    assert "continueAionCustomerVoiceConversation" in app
    assert "window.createAionPilotFrontendDraftMission = createAionPilotFrontendDraftMission" in app
    assert "window.createAionPilotFrontendDraftMission?.()" in app
    assert "Open quotation · view or edit" in sales
    assert "revision_of_event_id" in sales
    assert "prepare_quote_email" in sales
    assert "scope_items" in sales
    assert "customer_scoped_pilot_turn" in app
    assert "this customer record and work feed only" in app


def test_duplicate_sales_completion_surface_is_not_loaded():
    index = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
    assert '<script src="./aion_sales_completion_workspace.js"></script>' not in index


def test_add_lead_and_add_deal_capture_the_required_customer_and_commercial_fields():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert "Add a customer lead" in sales
    assert "Add a deal" in sales
    assert 'name="customer_type"' in sales
    assert 'name="first_name"' in sales
    assert 'name="last_name"' in sales
    assert 'name="company_name"' in sales
    assert 'name="address"' in sales
    assert 'name="email"' in sales
    assert 'name="phone"' in sales
    assert 'name="enquiry"' in sales
    assert 'name="source"' in sales
    assert 'name="source_reference"' in sales
    assert 'name="initial_stage"' in sales
    assert 'name="next_action"' in sales
    assert 'name="estimated_value"' in sales
    assert 'name="currency"' in sales
    assert "initial_stage: 'new'" in sales
    assert "Add at least one contact method: email or phone." in sales
    assert "Create lead" in sales
    assert "Create deal" in sales


def test_main_sales_pilot_stays_above_sales_workspace_and_outside_customer_records():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    director_position = app.index('renderDepartmentCompactDirectorCard("sales")')
    mount_position = app.index('data-aion-sales-revenue-mount="true"', director_position)
    assert director_position < mount_position
    assert "document.querySelector('[data-aion-sales-revenue-mount=\"true\"]')" in sales
    assert "syncSalesWorkspaceChromeVisibility(anchor)" in sales
    assert "data-srw-customer-record-open" in sales
    assert "customerRecordOpen ? 'none' : ''" in sales


def test_customer_record_header_contains_contact_details_and_feed_is_full_width():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    customer_workspace = sales.split("function customerWorkspace()", 1)[1].split("function panel()", 1)[0]
    assert "srw-customer-contact-line" in customer_workspace
    assert "row.contact.email" in customer_workspace
    assert "row.contact.phone" in customer_workspace
    assert "customerAddress(row)" in customer_workspace
    assert "address || 'Not added'" in customer_workspace
    assert "srw-customer-overview" not in customer_workspace
    assert "<b>Enquiry</b>" not in customer_workspace
    assert "<b>Qualification</b>" not in customer_workspace
    assert "<b>Campaign and consent</b>" not in customer_workspace
    assert ".srw-customer-page .srw-customer-page-body{grid-template-columns:minmax(0,1fr)}" in sales


def test_signed_in_person_is_automatically_recorded_for_customer_work_and_quote_send():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    assert "function syncSignedInActor()" in sales
    assert "aion.voiceOnboarding.o19i.v1" in sales
    assert "aion.sales.signedInPerson." in sales
    assert "Signed in as" in sales
    markup = sales.split("function markup()", 1)[1].split("function syncActorHeaderControl", 1)[0]
    assert "data-srw-actor" not in markup
    assert "function syncActorHeaderControl()" in sales
    assert 'data-aion-live-agents-sticky-header="true"' in sales
    assert 'data-aion-executive-sticky-actions="true"' in sales
    assert "actions.appendChild(label)" in sales
    assert ".srw-header-actor" in sales
    assert "function recordedByField" in sales
    assert "Sign in to record this action" in sales
    assert "Recorded by<select" not in sales
    assert "kind: 'quote_approved'" in sales
    assert "kind: 'quote_sent'" in sales
    assert "approved_by_person_id" in sales
    assert "sent_by_person_id" in sales
    assert "recordQuoteEmailOutcome" in sales
    assert "recordQuoteEmailOutcome" in app
    assert "opportunity_id: String(recordContext.opportunity_id" in app
    assert "executed_by: activeActor?.person_id" in app
    assert "approved and sent by" in app


def test_customer_record_links_job_invoices_expenses_and_existing_finance_controls():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    assert 'data-srw-customer-tab="invoices"' in sales
    assert 'data-srw-customer-tab="expenses"' in sales
    assert "customerJobInvoices" in sales
    assert "/api/aion/finance-sales/" in sales
    assert "finance-ledger-records" in sales
    assert "finance-transaction-reconciliation" in sales
    assert "Paid" in sales
    assert "Outstanding" in sales
    assert "Overdue" in sales
    assert "data-srw-expense-file" in sales
    assert "data-srw-expense-camera" in sales
    assert "project_id', row.opportunity_id" in sales
    assert "source_reference', `sales-opportunity:${row.opportunity_id}`" in sales
    assert "/extract" in sales
    assert "Extraction creates suggestions only" in sales
    assert "Accounting approval, Xero posting and bank reconciliation remain separate" in sales


def test_customer_relationship_core_is_compact_expandable_and_pilot_native():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    api = (ROOT / "backend/modules/aion_business/api/sales_revenue_api.py").read_text(encoding="utf-8")
    service = (ROOT / "backend/modules/aion_business/runtime/sales_revenue_service.py").read_text(encoding="utf-8")
    assert '<details class="srw-relationship">' in sales
    assert "Customer details" in sales
    assert "Relationship status" in sales
    assert "Responsible person" in sales
    assert "Preferred contact" in sales
    assert "Next action" in sales
    assert "Saved natively for Pilot, Sales, Support, Operations, Finance and Communications." in sales
    assert "relationship: row.relationship || {}" in sales
    assert 'data-srw-form="relationship"' in sales
    assert '/relationship`' in sales
    assert 'opportunities/{opportunity_id}/relationship' in api
    assert "def update_relationship" in service


def test_sales_call_centre_is_guided_multi_agent_and_uses_minted_contracts():
    sales = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
    api = (ROOT / "backend/modules/aion_business/api/sales_revenue_api.py").read_text(encoding="utf-8")
    service = (ROOT / "backend/modules/aion_business/runtime/sales_revenue_service.py").read_text(encoding="utf-8")
    assert "Build and run your sales callers" in sales
    assert "Describe the job" in sales
    assert "Choose what to capture" in sales
    assert "Test and mint" in sales
    assert "Phone connections · Twilio + Retell" in sales
    assert "data-srw-open-phone-vault" in sales
    assert "AionTelephonyVault?.open?.()" in sales
    assert "Connect number first" in sales
    assert 'data-srw-form="call_agent_create"' in sales
    assert 'data-srw-form="call_agent_builder"' in sales
    assert 'data-srw-form="prepare_call"' in sales
    assert "Products, services or packages it may discuss" in sales
    assert "Custom information to capture" in sales
    assert "agent_id: agent.agent_id" in sales
    assert 'call-centre/agents/{agent_id}/mint' in api
    assert '"schema_version": "aion.sales.agent_contract.v1"' in service
    assert '"schema_version": "aion.sales.call_goal_contract.v2"' in service
    assert "inbound_phone_routing_confirmation_required" in service
