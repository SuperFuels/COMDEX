from pathlib import Path


WORKSPACE = Path("desktop/mac/src/aion_operating_model_workspace.js")
WORK_SCHEDULE = Path("desktop/mac/src/aion_work_schedule_workspace.js")


def workspace_source() -> str:
    return WORKSPACE.read_text(encoding="utf-8")


def test_operating_model_owns_one_scoped_light_theme():
    source = workspace_source()

    assert "id='aion-operating-model-style'" in source
    assert "--om-paper:#ffffff" in source
    assert "background:var(--om-paper) !important" in source
    assert ".om-terminal" in source


def test_operating_model_controls_remain_high_contrast_inside_global_surface():
    source = workspace_source()

    assert ".om-shell .om-input" in source
    assert "color:var(--om-ink) !important" in source
    assert ".om-shell .om-add" in source
    assert "background:var(--om-green) !important" in source
    assert ".om-shell .om-tabs button[data-active=true]" in source
    assert "background:var(--om-teal) !important" in source


def test_all_operating_model_subtabs_continue_to_share_the_theme():
    source = workspace_source()

    assert "['workforce', 'Workforce & capacity']" in source
    tabs = source.split("const TABS = [", 1)[1].split("];", 1)[0]
    assert "Jobs & quotes" not in tabs
    assert "'finance', 'Finance'" not in tabs
    assert '<section class="om-terminal">' in source
    assert '<div class="om-content">${content()}</div>' in source


def test_products_workspace_uses_the_current_command_centre_visual_language():
    source = workspace_source()
    app = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")

    assert "PILOT · PRODUCTS &amp; SERVICES COMMAND CENTRE" in source
    assert "Products &amp; services coordination" in source
    assert 'class="om-context"' in source
    assert "font-family:Inter,-apple-system" in source
    assert "border-top:4px solid var(--om-teal)" in source
    assert 'data-aion-products-services-workspace="true"' in app
    assert "position:fixed!important;top:88px!important;left:64px!important" in app
    assert 'data-aion-products-services-workspace="true"' in app and "padding:16px 32px 80px!important" in app


def test_simple_advanced_control_has_protected_width_and_cannot_clip():
    source = workspace_source()

    assert ".om-package>div:first-child{flex:1 1 auto;min-width:0}" in source
    assert ".om-mode{display:flex;flex:0 0 190px;min-width:190px" in source
    assert "white-space:nowrap" in source


def test_products_visual_refresh_keeps_all_model_controls_and_actions():
    source = workspace_source()

    for marker in (
        'data-om-mode="simple"',
        'data-om-mode="advanced"',
        'data-om-tab="${key}"',
        'data-om-import="offerings"',
        'data-om-add="offerings"',
        'data-om-remove="${listName}"',
        'data-om-save="true"',
        "importSpreadsheet(file, category)",
        "saveOperatingModel(state.model, expected)",
    ):
        assert marker in source


def test_workforce_is_hr_linked_and_work_schedule_owns_jobs_and_quotes():
    source = workspace_source()
    work_schedule = WORK_SCHEDULE.read_text(encoding="utf-8")

    assert "Select a person from HR" in source
    assert "confidential_hr_effective_planning_cost" not in source
    assert "Customer jobs and quotes live in Work &amp; Schedule" in source
    assert "Prepare a job, quote or appointment" in work_schedule
    assert "AI-ENHANCED QUOTE &amp; JOB COSTING" in work_schedule
    assert 'data-ws-cost-estimate-form' not in work_schedule
    assert "Add private cost / working rows beneath each customer quote line" in work_schedule
    assert "data-ws-add-quote-child" in work_schedule
    assert "Quotes & invoices" in work_schedule


def test_offering_costs_are_optional_and_classified_before_entry():
    source = workspace_source()

    assert "How is this costed?" in source
    assert "Labour only" in source
    assert "Varies by quote/job" in source
    assert "You do not need to fill every cost cell" in source
    assert "Est. materials" in source
    assert "Est. external costs" in source


def test_margin_targets_are_a_guided_finance_decision():
    source = workspace_source()

    assert "GUIDED FINANCE DECISION" in source
    assert "Discuss with Finance Pilot" in source
    assert "These are evidence, not targets" in source
    assert "Record only targets you already know or have agreed" in source
    assert "Default quote pricing rules" in source
    assert "Protect gross margin" in source
    assert "Add markup to cost" in source


def test_variable_jobs_use_editable_ai_pricing_with_a_margin_floor():
    work_schedule = WORK_SCHEDULE.read_text(encoding="utf-8")
    sales = Path("desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")

    assert "Variable materials and labour do not need one fixed catalogue cost" in work_schedule
    assert "data-ws-accept-ai-price" in work_schedule
    assert "data-ws-use-recommended-quote" in work_schedule
    assert "minimum_margin_percentage" in work_schedule
    assert "priceOverridden" in sales
    assert "AI pricing guidance · editable draft" in sales
    assert "below the approved minimum margin" in sales


def test_financial_foundations_are_exported_to_finance_not_duplicated_in_products():
    source = workspace_source()

    assert "renderFinanceFoundations" in source
    assert "Payment terms, overheads, borrowing and targets live in Finance" in source
    assert "Stock and purchasing come from Stock &amp; Procurement" in source
