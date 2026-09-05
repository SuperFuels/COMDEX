from __future__ import annotations

from typing import Any, Dict, List


_CATEGORIES: Dict[str, List[tuple[str, str]]] = {
    "communication": [
        ("business_email", "Draft, review, send and reconcile business email"),
        ("email_inbox_triage", "Prioritise inboxes and prepare source-grounded replies"),
        ("outlook_mail", "Operate Microsoft Outlook mail through Graph"),
        ("gmail_mail", "Operate Gmail drafts, search, send and replies"),
        ("calendar_coordination", "Schedule and reconcile meetings and availability"),
        ("slack_messaging", "Read and send governed Slack messages"),
        ("teams_messaging", "Read and send governed Microsoft Teams messages"),
        ("whatsapp_business", "Operate approved WhatsApp Business conversations"),
        ("sms_messaging", "Send and reconcile bounded SMS messages"),
        ("business_calling", "Prepare, place and record governed phone calls"),
    ],
    "sales_crm": [
        ("hubspot_crm", "Manage contacts, deals, notes and pipeline evidence in HubSpot"),
        ("salesforce_crm", "Manage Salesforce customer and opportunity records"),
        ("pipedrive_crm", "Manage Pipedrive leads, activities and stages"),
        ("zoho_crm", "Manage Zoho CRM customer and pipeline records"),
        ("lead_qualification", "Score and route leads using approved sales policy"),
        ("quote_preparation", "Prepare source-backed quotes for approval"),
        ("proposal_writing", "Create personalised proposals from verified business facts"),
        ("sales_follow_up", "Prepare and schedule contextual follow-up"),
        ("pipeline_forecasting", "Forecast pipeline outcomes with uncertainty"),
        ("crm_data_quality", "Deduplicate and validate CRM records"),
    ],
    "finance": [
        ("xero_bookkeeping", "Read and operate scoped Xero accounting workflows"),
        ("quickbooks_bookkeeping", "Read and operate scoped QuickBooks workflows"),
        ("sage_accounting", "Read and operate scoped Sage accounting workflows"),
        ("invoice_preparation", "Prepare and verify customer invoices"),
        ("accounts_receivable", "Monitor debtors and prepare collection actions"),
        ("accounts_payable", "Validate bills and prepare controlled payments"),
        ("cashflow_forecasting", "Forecast near-term cash in, cash out and shortfalls"),
        ("bank_reconciliation", "Match bank lines to accounting evidence"),
        ("stripe_payments", "Operate governed customer payment and refund actions"),
        ("expense_control", "Classify and monitor business expenses"),
    ],
    "productivity_documents": [
        ("google_workspace", "Use Docs, Sheets, Drive and Calendar"),
        ("microsoft_365", "Use Word, Excel, PowerPoint, OneDrive and Calendar"),
        ("docx_documents", "Create and verify Word documents"),
        ("pdf_documents", "Read, create, render and verify PDF documents"),
        ("spreadsheets", "Create, analyse and verify spreadsheet workbooks"),
        ("presentations", "Create and verify presentation decks"),
        ("ocr_documents", "Extract structured evidence from scanned documents"),
        ("document_to_actions", "Convert documents into accountable action records"),
        ("meeting_minutes", "Create decisions, actions and evidence-backed minutes"),
        ("knowledge_base", "Maintain cited, versioned company knowledge"),
    ],
    "work_management": [
        ("asana", "Manage Asana projects and tasks"),
        ("trello", "Manage Trello boards and cards"),
        ("clickup", "Manage ClickUp work and status"),
        ("monday", "Manage Monday.com work items"),
        ("jira", "Manage Jira issues and delivery workflows"),
        ("notion", "Read and maintain governed Notion workspaces"),
        ("airtable", "Operate Airtable records, filters and upserts"),
        ("scheduled_jobs", "Create durable recurring governed work"),
        ("daily_briefing", "Compile verified operational briefings"),
        ("weekly_review", "Review targets, outcomes, blockers and next actions"),
    ],
    "marketing_social": [
        ("content_planning", "Plan evidence-backed multi-channel content"),
        ("social_publishing", "Prepare and publish approved social content"),
        ("x_twitter", "Search, post and message through X"),
        ("linkedin", "Prepare and publish governed LinkedIn activity"),
        ("meta_business", "Operate approved Facebook and Instagram business actions"),
        ("youtube_content", "Research and prepare YouTube content"),
        ("campaign_measurement", "Measure reach, conversion and attribution"),
        ("ab_testing", "Design and evaluate controlled marketing experiments"),
        ("competitor_monitoring", "Monitor named competitors with citations"),
        ("brand_voice", "Apply approved company tone and claims"),
    ],
    "support_people": [
        ("support_triage", "Classify and route customer cases"),
        ("support_resolution", "Prepare policy-compliant resolutions"),
        ("refund_decisions", "Prepare bounded refund recommendations"),
        ("zendesk", "Operate governed Zendesk support records"),
        ("intercom", "Operate governed Intercom conversations"),
        ("employee_onboarding", "Coordinate evidence-backed onboarding"),
        ("leave_management", "Manage leave requests and capacity impacts"),
        ("people_records", "Maintain scoped employee records and authority"),
        ("performance_reviews", "Prepare documented appraisal workflows"),
        ("hr_compliance", "Track required people evidence without legal overclaiming"),
    ],
    "research_intelligence": [
        ("grounded_citations", "Ground outputs in cited verifiable sources"),
        ("blocked_page_recovery", "Use lawful fallbacks for inaccessible pages"),
        ("rss_monitoring", "Monitor blogs and RSS/Atom feeds"),
        ("market_research", "Research markets, customers and competitors"),
        ("research_papers", "Find, assess and synthesise primary research"),
        ("source_criticism", "Assess provenance, recency and conflicts"),
        ("forecasting", "Make calibrated forecasts and score outcomes"),
        ("price_monitoring", "Track price and availability changes"),
        ("regulatory_monitoring", "Monitor relevant official regulatory changes"),
        ("knowledge_graph", "Build verified claims and cross-domain associations"),
    ],
    "software_automation": [
        ("web_research", "Browse and extract structured web evidence"),
        ("browser_control", "Operate bounded browser interactions"),
        ("computer_control", "Operate bounded desktop interactions"),
        ("workflow_automation", "Design governed multi-step automations"),
        ("api_integration", "Integrate and test external APIs"),
        ("mcp_tools", "Discover and use scoped MCP tools"),
        ("systematic_debugging", "Diagnose software failures systematically"),
        ("test_driven_development", "Build using red-green-refactor evidence"),
        ("code_review", "Review code for correctness, quality and security"),
        ("github", "Operate issues, branches, reviews and pull requests"),
    ],
    "operations_commerce": [
        ("shopify", "Read and operate governed Shopify commerce workflows"),
        ("woocommerce", "Read and operate governed WooCommerce workflows"),
        ("inventory_control", "Monitor stock, reorder points and evidence"),
        ("procurement", "Prepare supplier comparisons and purchase approvals"),
        ("order_fulfilment", "Coordinate order-to-delivery state"),
        ("shipping", "Prepare and track governed shipping activity"),
        ("field_service", "Schedule and monitor field work"),
        ("quality_control", "Record inspections, exceptions and corrective actions"),
        ("capacity_planning", "Match demand, people, equipment and time"),
        ("business_continuity", "Prepare and test operational recovery plans"),
    ],
}


_ADAPTER_LINKED = {
    "gmail_mail", "hubspot_crm", "xero_bookkeeping", "business_calling",
    "pdf_documents", "docx_documents", "spreadsheets", "presentations",
    "google_workspace", "github", "knowledge_graph", "workflow_automation",
}


def get_aion_business_skill_catalog() -> Dict[str, Any]:
    skills: List[Dict[str, Any]] = []
    for category, entries in _CATEGORIES.items():
        for name, description in entries:
            skills.append({
                "skill_id": f"aion.{category}.{name}",
                "name": name.replace("_", " ").title(),
                "category": category,
                "description": description,
                "stage": "adapter_linked" if name in _ADAPTER_LINKED else "curriculum_ready",
                "required_gates": ["knowledge_assessment", "safe_practical_test", "retention_test", "adapter_receipt_for_live_actions"],
            })
    return {
        "schema_version": "aion.business_skill_catalog.v1",
        "strategy": "Curated business core; reviewed specialist registry; no arbitrary community installation.",
        "skill_count": len(skills),
        "categories": sorted(_CATEGORIES),
        "skills": skills,
        "claim_boundary": "Catalogue membership means AION has a syllabus and action vocabulary. It is not proof of mastery or live provider authority.",
    }

