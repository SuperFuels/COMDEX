from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")


def test_dashboard_is_business_command_centre_not_legacy_machine_health():
    start = APP.index("function renderDashboardSurface()")
    end = APP.index("function renderMarketingRunCard", start)
    dashboard = APP[start:end]
    assert 'data-aion-executive-dashboard="true"' in dashboard
    assert "Today across the business" in dashboard
    assert "Accountable actions" in dashboard
    assert "Business KPIs" in dashboard
    assert "Automations" in dashboard
    assert "Department work queues" in dashboard
    assert "Node Status" not in dashboard
    assert "Scheduler" not in dashboard


def test_dashboard_uses_real_existing_business_sources():
    model = APP[APP.index("function getAionExecutiveDashboardModelV1"):APP.index("function renderAionExecutiveDepartmentSnapshotV1")]
    assert "getAionDepartmentIntelligence()" in model
    assert "buildAionDepartmentAssessmentFeed()" in model
    assert "readAionBoardroomSessionArtifacts()" in model
    assert "window.__aionBoardroomDepartmentTasks" in model
    assert "getDepartmentRunCounts(key)" in model
    assert "getAionExecutiveDashboardAutomationsV1()" in model


def test_dashboard_has_all_business_function_snapshots_and_accountability_fields():
    model = APP[APP.index("function getAionExecutiveDashboardModelV1"):APP.index("function renderAionExecutiveDepartmentSnapshotV1")]
    for key in ("marketing", "sales", "finance", "operations", "support", "hr", "products_services"):
        assert f'["{key}",' in model
    assert "accountable_owner" in model
    assert "due_date" in model
    assert "normaliseAionExecutiveDashboardStatusV1" in model
    assert 'data-aion-dashboard-department-open=' in APP


def test_dashboard_styles_are_clean_expandable_and_responsive():
    for selector in (
        ".aion-exec-dashboard-functions",
        ".aion-exec-dashboard-action-row",
        ".aion-exec-dashboard-kpi-group",
        ".aion-exec-dashboard-automation-row",
        ".aion-exec-dashboard-daily",
    ):
        assert selector in STYLES


def test_top_function_area_is_a_six_function_carousel_without_products_services():
    carousel = APP[APP.index("function renderAionExecutiveDepartmentCarouselV1"):APP.index("function renderAionExecutiveActionRowsV1")]
    assert 'department.key !== "products_services"' in carousel
    assert 'data-aion-dashboard-function-step="-1"' in carousel
    assert 'data-aion-dashboard-function-step="1"' in carousel
    assert "of ${functions.length}" in carousel
    assert "Open ${escapeHtml(department.label)}" in carousel
    dashboard = APP[APP.index("function renderDashboardSurface()"):APP.index("if (!window.__aionExecutiveDashboardNavigationV1Installed")]
    assert "renderAionExecutiveDepartmentCarouselV1(model.departments)" in dashboard
    assert "model.departments.map(renderAionExecutiveDepartmentSnapshotV1)" not in dashboard


def test_marketing_snapshot_uses_evidence_and_never_fakes_disconnected_zeroes():
    start = APP.index("function getAionMarketingDashboardSnapshotV1")
    end = APP.index("function renderAionMarketingMetricDetailV1", start)
    snapshot = APP[start:end]
    assert 'getItem("aion.departmentIntelligence.marketing")' in APP
    assert "getAionDepartmentIntelligence()?.marketing" in snapshot
    assert "getBoardroomPulse()" in snapshot
    for metric in ("spend_today", "spend_7d", "spend_month", "leads", "attributed_revenue", "roas", "reach", "follower_growth"):
        assert metric in snapshot
    assert 'value: formatAionMarketingMetricValueV1(raw, format)' in snapshot
    assert 'available: raw !== undefined' in snapshot
    assert 'return "Not connected"' in APP


def test_marketing_metrics_expand_to_evidence_and_interpretation():
    marketing = APP[APP.index("function renderAionMarketingMetricDetailV1"):APP.index("function renderAionExecutiveDepartmentSnapshotV1")]
    for marker in (
        "What it means",
        "Comparison",
        "Evidence source",
        "Last refresh",
        "Agent interpretation",
        'data-aion-marketing-metric=',
        "Native channel results",
        "Marketing agent briefing",
        "Best content",
        "A/B test",
        "Subscriptions",
    ):
        assert marker in marketing
    assert "Disconnected channels are not shown as zero" in marketing


def test_operations_and_ceo_form_the_governed_cross_functional_chain():
    chain = APP[APP.index("function renderAionMarketingDecisionChainV1"):APP.index("function renderAionMarketingFunctionSnapshotV1")]
    assert "Signal → Operations → CEO → Decision" in chain
    assert "Operations / COO" in chain
    assert "Checks delivery capacity, staffing, Sales follow-up and Finance constraints" in chain
    assert "Validates the coordinated proposal against the approved company and Board plan" in chain
    assert "Only a material, decision-ready proposal is escalated to the user" in chain
    assert "It does not publish, spend or contact anyone" in chain


def test_operations_review_checks_sales_finance_capacity_and_board_plan_before_approval():
    start = APP.index("function buildAionMarketingOperationsReviewV1")
    end = APP.index("function renderAionMarketingFunctionSnapshotV1", start)
    review = APP[start:end]
    assert 'check("operations", "Delivery capacity and operational risk")' in review
    assert 'check("sales", "Lead handling and sales follow-up")' in review
    assert 'check("finance", "Budget, margin and return constraints")' in review
    assert "hasBoardPlan" in review
    assert 'status: hasBoardPlan && !gaps.length ? "decision_ready" : "blocked"' in review
    assert "approval_required: true" in review
    assert "live_external_execution: false" in review


def test_marketing_decision_handler_is_internal_and_external_execution_stays_blocked():
    handlers = APP[APP.index("if (!window.__aionExecutiveDashboardNavigationV1Installed)"):APP.index("function renderMarketingRunCard")]
    assert 'data-aion-marketing-decision' in handlers
    assert 'live_external_execution: false' in handlers
    assert "No external action or spend was executed" in handlers
    assert "aion.executiveCoordination.v1" in APP


def test_sales_snapshot_covers_revenue_conversion_cost_margin_and_activity():
    start = APP.index("function getAionSalesDashboardSnapshotV1")
    end = APP.index("function renderAionSalesLeadSourceV1", start)
    sales = APP[start:end]
    for metric in (
        "new_leads",
        "contacts_made",
        "open_quotes",
        "sales_won",
        "conversion_rate",
        "revenue",
        "cost_per_sale",
        "gross_margin_pct",
    ):
        assert metric in sales
    assert "lead_sources" in sales
    assert "sales_activities" in sales
    assert "opportunities" in sales
    assert 'available: raw !== undefined' in sales


def test_sales_intelligence_detects_stalled_quotes_low_conversion_and_uncontacted_leads():
    start = APP.index("function getAionSalesDashboardSnapshotV1")
    end = APP.index("function renderAionSalesLeadSourceV1", start)
    sales = APP[start:end]
    assert "days_since_activity" in sales
    assert "stalled_quotes" in sales
    assert "conversion_below_target" in sales
    assert "uncontacted_leads" in sales
    assert "Any discount or revised commercial term requires Finance margin validation" in sales
    assert "before buying more demand" in sales


def test_sales_reactive_chain_routes_through_operations_finance_marketing_and_ceo():
    chain = APP[APP.index("function renderAionSalesDecisionChainV1"):APP.index("function renderAionSalesFunctionSnapshotV1")]
    assert "Sales signal → Operations → CEO → Decision" in chain
    assert "Operations / COO" in chain
    assert "Marketing source quality" in chain
    assert "Finance margin constraints" in chain
    assert 'check("marketing", "Lead source quality and acquisition context")' in chain
    assert 'check("finance", "Price, discount, margin and cash constraints")' in chain
    assert "live_external_execution: false" in chain
    assert "approval_required: true" in chain


def test_sales_user_decision_never_executes_calls_emails_discounts_or_external_actions():
    handlers = APP[APP.index("if (!window.__aionExecutiveDashboardNavigationV1Installed)"):APP.index("function renderMarketingRunCard")]
    assert "data-aion-sales-operations-review" in handlers
    assert "data-aion-sales-decision" in handlers
    assert "No call, email, discount or external action was executed" in handlers
    assert "calls, emails, discounts, pricing and external communication remain approval-gated" in handlers


def test_finance_snapshot_separates_history_liquidity_forecast_costs_and_projects():
    start = APP.index("function getAionFinanceDashboardSnapshotV1")
    end = APP.index("function renderAionFinanceLedgerRowsV1", start)
    finance = APP[start:end]
    for metric in (
        "sales_today",
        "sales_yesterday",
        "sales_7d",
        "sales_month",
        "sales_yoy",
        "gross_margin_pct",
        "ebitda",
        "cash_balance",
        "net_cash_flow",
        "pipeline_forecast",
    ):
        assert metric in finance
    for cost in ("cost_of_product", "labour_cost", "variable_costs", "fixed_costs", "cost_per_sale", "cost_of_sales"):
        assert cost in finance
    assert "project_budgets" in finance
    assert "working_capital" in finance
    assert "board_kpis" in finance


def test_finance_detects_cash_margin_collections_project_and_stock_funding_risks():
    start = APP.index("function getAionFinanceDashboardSnapshotV1")
    end = APP.index("function renderAionFinanceLedgerRowsV1", start)
    finance = APP[start:end]
    for signal in ("cash_below_buffer", "overdue_invoices", "negative_cash_flow", "margin_below_target", "project_overrun_", "stock_cash_gap"):
        assert signal in finance
    assert "Protect payroll, tax and essential commitments" in finance
    assert "deposits, supplier terms, staged purchasing or approved funding" in finance
    assert 'route: "direct_ceo"' in finance
    assert 'route: "operations_coordination"' in finance


def test_finance_cash_survival_radar_uses_dated_evidence_across_four_horizons():
    start = APP.index("function buildAionFinanceCashRadarV1")
    end = APP.index("function getAionFinanceDashboardSnapshotV1", start)
    radar = APP[start:end]
    assert "[2, 7, 14, 30]" in radar
    for source in ("receivables", "payables", "payroll_schedule", "labour_payments", "subscriptions", "tax_payments"):
        assert source in radar
    assert "incomingExpected" in radar
    assert "outgoingCommitted" in radar
    assert "amount * confidence" in radar
    assert "closedStatuses" in radar


def test_finance_cash_survival_radar_never_treats_missing_commitments_as_zero():
    start = APP.index("function renderAionFinanceCashRadarV1")
    end = APP.index("function renderAionFinanceDecisionChainV1", start)
    view = APP[start:end]
    assert 'data-aion-finance-cash-radar="true"' in view
    assert "Evidence required" in view
    assert "This is missing evidence—not zero obligations" in view
    assert "Committed bills counted in full" in view
    assert "Forecast only" in view


def test_finance_imminent_cash_gap_identifies_shortfall_and_escalates_to_ceo():
    start = APP.index("function getAionFinanceDashboardSnapshotV1")
    end = APP.index("function renderAionFinanceLedgerRowsV1", start)
    finance = APP[start:end]
    assert 'id: "imminent_cash_gap"' in finance
    assert "firstGap.projectedCash" in finance
    assert "before the forecast gap date" in finance
    assert 'route: "direct_ceo"' in finance
    assert 'id: "dated_overdue_receivables"' in finance


def test_finance_material_risks_route_directly_to_ceo_with_operations_only_consulted():
    start = APP.index("function renderAionFinanceDecisionChainV1")
    end = APP.index("function renderAionFinanceFunctionSnapshotV1", start)
    chain = APP[start:end]
    assert "Finance Director → CEO → User · Operations consulted when required" in chain
    assert "CEO · direct escalation" in chain
    assert "bypass routine Operations routing" in chain
    assert "Finance retains financial control" in chain
    assert "direct_ceo_signals" in chain
    assert "not_required_for_current_signal" in chain
    assert "live_external_execution: false" in chain
    assert "approval_required: true" in chain


def test_finance_dashboard_has_cost_working_capital_project_board_and_briefing_panels():
    start = APP.index("function renderAionFinanceFunctionSnapshotV1")
    end = APP.index("function renderAionExecutiveDepartmentSnapshotV1", start)
    view = APP[start:end]
    for label in (
        "Cost structure",
        "Cash and working capital",
        "Project economics",
        "Board objectives and KPIs",
        "Finance Director briefing",
        "Financial alerts and opportunities",
    ):
        assert label in view
    assert 'data-aion-finance-metric=' in view
    assert 'data-aion-finance-reactive-signals="true"' in view


def test_finance_decisions_never_execute_money_or_commercial_actions():
    handlers = APP[APP.index("if (!window.__aionExecutiveDashboardNavigationV1Installed)"):APP.index("function renderMarketingRunCard")]
    assert "data-aion-finance-ceo-review" in handlers
    assert "data-aion-finance-decision" in handlers
    assert "No payment, purchase, credit, pricing or banking action was executed" in handlers
    assert "payments, purchasing, credit, banking, pricing and external actions remain separately approval-gated" in handlers


def test_support_snapshot_reads_canonical_cases_responses_deadlines_and_risk_flags():
    start = APP.index("function getAionSupportDashboardSnapshotV1")
    end = APP.index("function renderAionSupportCaseCardV1", start)
    support = APP[start:end]
    assert "AionSupportCaseWorkspace" in support
    assert "cases" in support
    assert "responses" in support
    assert "resolution_due_at" in support
    assert "first_response_due_at" in support
    assert "risk_flags" in support
    assert "human_intervention_required" in support
    for label in ("Open cases", "Solved today", "Awaiting approval", "Red flags", "Overdue", "Resolved total"):
        assert label in support


def test_support_approval_queue_exposes_case_resolution_money_and_missing_authority():
    start = APP.index("function renderAionSupportCaseCardV1")
    end = APP.index("function renderAionSupportFunctionSnapshotV1", start)
    card = APP[start:end]
    assert "Proposed resolution" in card
    assert "remedy_amount" in card
    assert "requested_action" in card
    assert "missing_authority" in card
    assert "knowledge_citations" in card
    assert "Review full case" in card
    assert "data-aion-support-case-review" in card


def test_support_dashboard_is_case_control_not_fake_zero_or_autonomous_resolution():
    start = APP.index("function renderAionSupportFunctionSnapshotV1")
    end = APP.index("function renderAionExecutiveDepartmentSnapshotV1", start)
    view = APP[start:end]
    assert 'data-aion-support-dashboard="true"' in view
    assert "Connecting Support Case Centre" in view
    assert "No missing value is being treated as zero" in view
    assert "Cases requiring attention" in view
    assert "Approval and intervention queue" in view
    assert "Recently verified resolutions" in view
    assert "Refunds, discounts, replacements, cancellations, liability admissions and customer messages remain governed" in view


def test_support_case_review_opens_the_real_support_case_centre():
    handlers = APP[APP.index("if (!window.__aionExecutiveDashboardNavigationV1Installed)"):APP.index("function renderMarketingRunCard")]
    assert "data-aion-support-case-review" in handlers
    assert "AionSupportCaseWorkspace?.openCase" in handlers
    assert 'openAionExecutiveDepartmentFromStickyHeaderV1("support")' in handlers


def test_people_dashboard_reads_canonical_people_operations_without_fake_zeroes():
    start = APP.index("function getAionPeopleDashboardSnapshotV1")
    end = APP.index("function renderAionPeopleFunctionSnapshotV1", start)
    people = APP[start:end]
    assert "AionHrPeopleWorkspace" in people
    for source in ("leave_requests", "appraisals", "escalations", "onboarding"):
        assert source in people
    for label in ("Active people", "Leave approvals", "Off next 14 days", "Reviews due", "Onboarding gaps", "Restricted issues"):
        assert label in people
    assert "Connecting to the governed People ledger" in people


def test_people_dashboard_has_calendar_cover_approvals_onboarding_and_restricted_queue():
    start = APP.index("function renderAionPeopleFunctionSnapshotV1")
    end = APP.index("function renderAionExecutiveDepartmentSnapshotV1", start)
    view = APP[start:end]
    for label in ("Upcoming absence and capacity", "Leave and cover decisions", "Appraisals and check-ins", "Onboarding and access readiness", "Restricted People escalations"):
        assert label in view
    assert "Missing records are not being treated as zero" in view
    assert "remain human-controlled" in view
    assert "data-aion-people-leave-review" in view


def test_people_dashboard_deep_links_to_governed_people_workspace():
    handlers = APP[APP.index("if (!window.__aionExecutiveDashboardNavigationV1Installed)"):APP.index("function renderMarketingRunCard")]
    assert "data-aion-people-person-review" in handlers
    assert "data-aion-people-leave-review" in handlers
    assert "data-aion-people-operations-open" in handlers
    assert 'openAionExecutiveDepartmentFromStickyHeaderV1("hr")' in handlers
