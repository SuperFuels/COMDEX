from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")

def source() -> str:
    return APP.read_text()

def test_phase18_replaces_founder_demo_main_label() -> None:
    text = source()
    active = text[text.find("/* PHASE 18 LOCK: Universal A2A Commercial Ticket model */"):]
    assert "A2A Job / Order Ticket" in active
    assert "A2A commercial ticket" in active
    assert "Home Fixed Website → A2A → Proof Replay" not in active[:5000]

def test_phase18_route_model_exists() -> None:
    text = source()
    for route in [
        "fixed_product",
        "hourly_service",
        "discovery_session",
        "custom_quote",
        "metered_work",
        "subscription",
        "escrow_contract",
    ]:
        assert route in text

def test_phase18_business_rule_layer_exists() -> None:
    text = source()
    assert "getAionPhase18BusinessRules" in text
    assert "first_hour_charge" in text
    assert "additional_hour_rate" in text
    assert "materials" in text
    assert "approval_threshold" in text
    assert "Business rules / rate card" in text

def test_phase18_availability_abstraction_exists() -> None:
    text = source()
    assert "getAionPhase18AvailabilityPreview" in text
    assert "requested_slot" in text
    assert "available_slot" in text
    assert "alternatives" in text
    assert "unavailable_reason" in text
    assert "Future calendar connector · preview only" in text
    assert "Single engineer now · multi-engineer ready later" in text

def test_phase18_negotiation_states_exist() -> None:
    text = source()
    for state in [
        "agent_request_received",
        "route_rules_returned",
        "customer_agent_confirming",
        "availability_requested",
        "slot_proposed",
        "customer_agent_accepted",
        "human_approval_required",
        "proof_ready",
    ]:
        assert state in text

def test_phase18_home_fixed_realistic_examples_exist() -> None:
    text = source()
    assert "home_fixed_roof_discovery" in text
    assert "home_fixed_plumber_callout" in text
    assert "Site visit / assessment required before quote" in text
    assert "First hour callout charge agreed before booking" in text
    assert "Additional hours billed at pre-agreed hourly rate" in text
    assert "Do not invent a final quote" not in text

def test_phase18_universal_examples_exist() -> None:
    text = source()
    for item in [
        "design_agency_discovery",
        "software_project_proposal",
        "digital_product_purchase",
        "physical_stock_check",
        "consultant_hourly",
        "b2b_supplier_quote",
    ]:
        assert item in text

def test_phase18_timeline_is_ticket_progress_not_button_wall() -> None:
    text = source()
    assert "aion-phase18-timeline-item" in text
    assert "aion-phase18-step-index" in text
    assert "role=\"list\"" in text
    assert ".aion-phase18-timeline button" not in text
    assert "is-completed" in text
    assert "is-current" in text
    assert "is-pending" in text

def test_phase18_guardrails_are_compact_hover_pill() -> None:
    text = source()
    assert "aion-phase18-guardrail-pill" in text
    assert "Guardrails active" in text
    assert "title=\"Preview mode · No booking · No payment · No escrow · No external message · No live chain write · Human review required\"" in text

def test_phase18_raw_enums_hidden_from_normal_display_fields() -> None:
    text = source()

    phase18_start = text.find("/* PHASE 18 LOCK")
    render_start = text.find("function renderAionPhase18CommercialTicketPanel")
    advanced_start = text.find("<details class=\"aion-phase18-advanced\">", render_start)

    phase18_source = text[phase18_start:advanced_start]
    normal_ui = text[render_start:advanced_start]

    # Phase 18 must define/render business-readable values for normal users.
    assert "Discovery / assessment visit" in phase18_source
    assert "Free or paid discovery" in phase18_source
    assert "Availability preview" in phase18_source
    assert "Single engineer now · multi-engineer ready later" in phase18_source

    # Normal visible UI must use readable ticket fields.
    assert "route.label" in normal_ui
    assert "route.pricing_label" in normal_ui
    assert "availability.status" in normal_ui
    assert "availability.resource_model" in normal_ui

    # Raw enum fields may exist in route selection values and Advanced trace,
    # but must not be direct visible summary fields.
    assert "<strong>${escapeHtml(route.route_type)}</strong>" not in normal_ui
    assert "<strong>${escapeHtml(route.pricing_model)}</strong>" not in normal_ui
    assert "<h3>${escapeHtml(calendar.status)}</h3>" not in normal_ui
    assert "<h3>${escapeHtml(calendar.resource_model)}</h3>" not in normal_ui


def test_phase18_advanced_trace_keeps_raw_enums_and_guards() -> None:
    text = source()
    assert "\"route_type\"" in text
    assert "\"pricing_model\"" in text
    for guard in [
        "booking_created",
        "payment_created",
        "escrow_created",
        "external_message_sent",
        "live_chain_write",
    ]:
        assert guard in text

def test_phase18_is_in_focused_suite() -> None:
    assert "test_aion_phase18_a2a_commercial_ticket_lock.py" in SUITE.read_text()

def test_phase18_frontend_wires_preview_api_with_local_fallback() -> None:
    text = source()
    assert "fetchAionPhase18CommercialTicketPreview" in text
    assert "normaliseAionPhase18ApiTicketForUi" in text
    assert "http://127.0.0.1:8080/api/local-node/aion/phase18/a2a-commercial-ticket-preview?scenario=" in text
    assert "Refresh API preview" in text
    assert "local_fallback" in text
    assert "Local fallback" in text
    assert "API preview unavailable" in text

def test_phase18_api_normaliser_maps_raw_backend_values_to_clean_display_labels() -> None:
    text = source()
    assert "displayAionPhase18ApiTicketId" in text
    assert "a2a_home_fixed_roof_discovery_preview" in text
    assert "A2A-HF-001" in text
    assert "displayAionPhase18ApiPricingLabel" in text
    assert "Free discovery before quote" in text
    assert "Free or paid discovery" in text
    assert "displayAionPhase18ApiResource" in text
    assert "roofer" in text
    assert "Roofer / general builder" in text

def test_phase18_api_ui_polish_locks_exist() -> None:
    text = source()

    assert "displayAionPhase18ApiTicketId" in text
    assert "raw_ticket_id" in text
    assert "AbortController" in text
    assert "Local API preview loaded" in text
    assert "Refresh API preview" in text
    assert "api_preview_status" in text
    assert "local_fallback" in text
    assert "http://127.0.0.1:8080/api/local-node/aion/phase18/a2a-commercial-ticket-preview?scenario=" in text


def test_phase18_api_url_uses_localhost_8080_intentionally() -> None:
    text = source()
    assert "http://127.0.0.1:8080/api/local-node/aion/phase18/a2a-commercial-ticket-preview?scenario=" in text

def test_phase18_loading_state_has_finally_guard() -> None:
    text = source()
    start = text.find("async function fetchAionPhase18CommercialTicketPreview")
    end = text.find("function getAionPhase18SelectedExample", start)
    block = text[start:end]
    assert "finally" in block
    assert "window.clearTimeout(timeoutId)" in block
    assert "state18.api_preview_status === \"loading\"" in block
    assert "local_fallback" in block

def test_phase18_api_success_note_is_not_fallback_warning() -> None:
    text = source()
    assert 'state18.api_preview_status === "api_preview" && state18.api_preview_error' in text
    assert 'state18.api_preview_status === "local_fallback" && state18.api_preview_error' in text
    assert "aion-phase18-api-note is-success" in text
    assert "API preview unavailable · using local fallback" in text

def test_phase18_frontend_prefers_customer_request_over_proposal_summary() -> None:
    text = source()
    assert "payload.customer_request" in text
    assert "fallbackTicket.customer_request" in text
    assert "proposalPreview.customer_visible_summary" in text

def test_phase18_ticket_protects_against_workflow_subtab_overlap() -> None:
    text = source()
    assert "PHASE 18 LOCK: hide fixed workflow slim header when A2A ticket is visible" in text
    assert "installAionPhase18HideWorkflowSlimHeader" in text
    assert "aion-phase18-hide-workflow-slim-header-style" in text
    assert "aion-phase18-ticket-visible" in text
    assert "[data-aion-selected-workflow-slim-header='true']" in text
    assert ".aion-selected-workflow-slim-header-v14" in text
    assert "display: none !important" in text

def test_phase18_removes_stale_main_workflow_overlay_runtime() -> None:
    text = source()
    assert "PHASE 18 LOCK: remove stale Main workflow overlay while A2A ticket is visible" in text
    assert "installAionPhase18RemoveMainWorkflowOverlay" in text
    assert "aion-phase18-ticket-visible" in text
    assert "data-aion-selected-workflow-slim-header" in text
    assert ".aion-selected-workflow-slim-header-v14" in text
    assert "data-aion-phase18-hidden-main-workflow-overlay" in text
    assert "MutationObserver" in text

