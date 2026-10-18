from pathlib import Path


WORK_SCHEDULE_JS = Path("desktop/mac/src/aion_work_schedule_workspace.js")
WORK_SCHEDULE_CSS = Path("desktop/mac/src/aion_work_schedule_workspace.css")
APP_JS = Path("desktop/mac/src/app.js")


def test_work_items_open_as_a_durable_full_page_record():
    source = WORK_SCHEDULE_JS.read_text(encoding="utf-8")

    assert 'class="ws-detail-panel ws-record-page"' in source
    assert "WORK RECORD ·" in source
    assert "Record reference" in source
    assert "linked work ${customerRecords === 1 ? 'record' : 'records'}" in source
    assert "← Back to ${esc(returnLabels[state.ui.view]" in source
    assert "const selectedRecord = !creationPage && state.ui.selectedId ? renderDetailPanel() : ''" in source
    assert "${creationPage || selectedRecord || workspace}" in source
    assert "ws-panel-backdrop" not in source
    assert "ws-panel-layer" not in source


def test_work_record_uses_the_normal_tessaris_page_surface_not_a_drawer():
    styles = WORK_SCHEDULE_CSS.read_text(encoding="utf-8")

    assert ".ws-record-header" in styles
    assert ".ws-record-summary" in styles
    assert ".ws-record-tabs" in styles
    assert "grid-template-columns: repeat(6, minmax(0, 1fr))" in styles
    assert ".ws-record-tabs button.active" in styles
    assert "border-radius: 0 !important" in styles
    assert "box-shadow: none !important" in styles
    assert "position: relative; width: 100%; min-height:" in styles
    assert ".ws-panel-backdrop" not in styles
    assert ".ws-panel-layer" not in styles


def test_inbound_request_opens_a_full_review_page_not_a_modal():
    source = WORK_SCHEDULE_JS.read_text(encoding="utf-8")
    styles = WORK_SCHEDULE_CSS.read_text(encoding="utf-8")

    assert ">Review request</button>" in source
    assert "Review request and prepare the work" in source
    assert "Human review" in source
    assert "Approve and create work record" in source
    assert "You will continue in its Quotes & invoices tab." in source
    assert "LINKED INBOUND REQUEST" in source
    assert "source_request:" in source
    assert "date: intake.date || ''" in source
    assert "time: intake.time || ''" in source
    assert "location: intake.service_address || intake.location" in source
    assert "sales_opportunity_id: sourceRequest.sales_opportunity_id || ''" in source
    assert "state.ui.panelTab = intakeId || item.type === 'quote' ? 'commercial' : 'overview'" in source
    assert "Source — where this request came from" in source
    assert "'Google search', 'Google Ads', 'Facebook', 'Instagram', 'LinkedIn', 'TikTok', 'X', 'Pinterest'" in source
    assert '<dt>Source</dt>' in source
    assert '<dt>Origin</dt>' not in source
    assert "Internal scheduling and record details" in source
    assert "Select the saved customer for this work" in source
    assert "data-ws-customer-select" in source
    assert "automatically appear on the quotation, invoice and prepared email" in source
    assert "data-ws-new-customer" in source
    assert "data-ws-customer-form" in source
    assert "Create a new customer" in source
    assert "Save the contact and address once" in source
    assert "data-ws-edit-customer" in source
    assert "data-ws-same-address" in source
    assert "Use the billing address as the service address" in source
    assert "data-ws-customer-quote" in source
    assert ">+ New quote</button>" in source
    assert "function openCustomerQuote" in source
    assert "state.ui.panelTab = 'commercial'" in source
    assert "data-ws-customer-work" not in source
    assert "customerForItem(item)" in source
    assert "emailState.to || customer.email" in source
    assert "QUOTATION FOR" in source
    assert "DESCRIPTION OF WORK" in source
    assert "TOTAL QUOTE" in source
    assert "Business → Terms &amp; Conditions" in source
    assert "Create numbered quotation PDF" in source
    assert "QUOTE TO INVOICE" in source
    assert "Customer acceptance automatically created the invoice" in source
    assert "deliver it using the payment methods configured" in source
    assert "hasNumberedQuote ? ''" in source
    commercial = source[source.index("function renderCommercial"):source.index("function renderDetailPanel")]
    assert commercial.index('class="ws-quote-to-invoice"') < commercial.index("${renderQuoteDelivery(item)}")
    assert ".ws-commercial article.ws-quotation" in styles
    assert 'class="ws-detail-panel ws-create-page"' in source
    assert "state.ui.modal === 'customer' ? renderCustomerPage()" in source
    assert "${creationPage || selectedRecord || workspace}" in source
    new_work_page = source[source.index("function renderNewModal"):source.index("function refreshNewQuoteGuidance")]
    assert "ws-modal-layer" not in new_work_page
    assert '<option value="">Create a new customer</option>' not in new_work_page
    assert "data-ws-new-customer-from-work" in new_work_page
    assert ".ws-create-form" in styles
    assert ".ws-create-stage" in styles
    assert ".ws-commercial article.ws-source-request" in styles


def test_business_terms_are_saved_as_reusable_quote_defaults():
    source = APP_JS.read_text(encoding="utf-8")

    assert '["terms_conditions", "Terms & Conditions"]' in source
    assert 'data-aion-business-terms="true"' in source
    assert '"include_terms_on_quotes"' in source
    assert '"quote_valid_days"' in source
    assert '"quotation_terms"' in source
    assert '"invoice_terms"' in source
    assert '"quote_email_subject"' in source
    assert '"quote_email_body"' in source
    assert "{customer_name}" in source
    assert "data-aion-rewrite-quote-email" in source
    assert "Rewrite email professionally with SI" in source
    assert "rewrite-quote-email-template" in source
    assert "Nothing is saved until you choose Save terms" in source


def test_numbered_quote_pdf_has_email_save_and_share_delivery_paths():
    source = WORK_SCHEDULE_JS.read_text(encoding="utf-8")
    styles = WORK_SCHEDULE_CSS.read_text(encoding="utf-8")

    assert "SEND OR SHARE QUOTE" in source
    assert "Send quotation to customer" in source
    assert "data-ws-save-quote" in source
    assert "data-ws-share-quote" in source
    assert "data-ws-send-quote-email" in source
    assert "quote-email-send" in source
    assert "Gmail is not connected" in source
    assert "data-ws-connect-gmail" in source
    assert "hydrateGmailHealth" in source
    assert "/api/local-node/connectors/gmail/health" in source
    assert "Edit this templated email in Business settings" in source
    assert "data-ws-edit-quote-email-template" in source
    assert "openAionBusinessQuoteEmailSettings" in source
    assert 'setAionBusinessContextSubtab("terms_conditions")' in APP_JS.read_text(encoding="utf-8")
    assert "openAionGmailConnectionSettings" in APP_JS.read_text(encoding="utf-8")
    assert "AUTOMATIC PAYMENT" in source
    assert "if (!document) return '';" in source
    assert source.index("ws-quote-to-invoice") < source.index("${renderQuoteDelivery(item)}")
    assert "The earlier connection error is no longer current" not in source
    assert "The email remains a draft in Gmail" not in source
    assert "Quote sent / awaiting acceptance" in source
    assert "Create secure quote link" not in source
    assert ".ws-quote-delivery" in styles


def test_quote_draft_uses_the_same_shared_gmail_vault_as_oauth():
    source = Path("backend/modules/aion_business/api/work_schedule_api.py").read_text(encoding="utf-8")
    start = source.index("def create_quote_email_draft(")
    end = source.index("\n\n@router.post", start)
    block = source[start:end]
    assert "runtime = get_runtime()" in block
    assert "runtime = get_runtime(key)" not in block
    assert '"schedule": schedule' in block
    assert 'scheduled_item["quote_email_draft"]' in block
    assert 'schedule = service.save(' in block
    assert 'acceptance_url = f"{public_base}/api/aion/business/work-schedule/portal/{portal[\'token\']}/accept"' in block

    ui = WORK_SCHEDULE_JS.read_text(encoding="utf-8")
    assert "if (payload.schedule) applyModel(payload.schedule)" in ui

    acceptance = source[source.index("def customer_quote_acceptance_page("):]
    assert "Your acceptance has been sent to" in acceptance
    assert "You can now close this window" in acceptance
    assert "appointment or schedule of works" in acceptance
    assert "function showAccepted(delivery='')" in acceptance


def test_quote_send_is_immediate_and_records_the_waiting_for_acceptance_state():
    source = Path("backend/modules/aion_business/api/work_schedule_api.py").read_text(encoding="utf-8")
    start = source.index("def send_quote_email(")
    end = source.index("\n\n@router.post", start)
    block = source[start:end]
    assert "runtime._send_gmail_message(" in block
    assert 'quote_state.update({"status": "sent"' in block
    assert 'scheduled_item["status"] = "awaiting_approval"' in block
    assert 'scheduled_item["quote_email_delivery"]' in block
    assert "awaiting customer acceptance" in block

    assert '_business_display_name(business, str(payload.get("workspace_id") or ""))' in source
    assert '"your business"' in source


def test_accepted_quote_shows_recovery_when_payment_delivery_is_blocked():
    source = WORK_SCHEDULE_JS.read_text(encoding="utf-8")
    styles = WORK_SCHEDULE_CSS.read_text(encoding="utf-8")
    api = Path("backend/modules/aion_business/api/work_schedule_api.py").read_text(encoding="utf-8")
    app = APP_JS.read_text(encoding="utf-8")

    assert "✓ Accepted" in source
    assert "Payment setup required" in source
    assert "data-ws-retry-payment-delivery" in source
    assert "retry-payment-delivery" in source
    assert "Open Financial Information" in source
    assert "openAionBusinessFinancialSettings" in app
    assert ".ws-board-card-flags .accepted" in styles
    assert "def retry_payment_delivery(" in api
    assert 'runtime._send_gmail_message(' in api


def test_generated_documents_have_distinct_open_and_save_actions():
    source = WORK_SCHEDULE_JS.read_text(encoding="utf-8")
    api = Path("backend/modules/aion_business/api/work_schedule_api.py").read_text(encoding="utf-8")
    service = Path("backend/modules/aion_business/runtime/work_schedule_service.py").read_text(encoding="utf-8")
    assert "Open document" in source
    assert "Save PDF…" in source
    assert "?inline=true" in source
    assert "f\"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(filename)}\"" in api
    assert 'kind in {"quote", "invoice"} and commercial' in service
    assert 'document_label = "INVOICE" if is_invoice else "QUOTATION"' in service
    assert "BANK TRANSFER DETAILS" in service
    assert "def refresh_invoice_document(" in service


def test_business_payment_details_and_quote_payment_schedule_are_connected():
    app = APP_JS.read_text(encoding="utf-8")
    source = WORK_SCHEDULE_JS.read_text(encoding="utf-8")

    assert '["financial_information", "Financial Information"]' in app
    assert "tessaris.businessPaymentSettings.v1" in app
    assert '"bank_account_name"' in app
    assert '"bank_iban"' in app
    assert '"payment_reference_template"' in app
    assert '"Default deposit %"' in app
    assert 'paymentSettings.default_deposit_percent || ""' in app
    assert 'paymentSettings.default_deposit_percent || "50"' not in app
    assert 'draft.default_deposit_percent || "50"' not in app
    assert "current.default_deposit_percent_explicit = true" in app
    assert "legacy_default_deposit_cleared" in app
    assert "data-aion-open-stripe-connection" in app
    assert "data-ws-payment-preset" in source
    assert "Deposit + balance" in source
    assert "Phased payments" in source
    assert "data-ws-payment-stage-field" in source
    assert "Payment reference" in source
    assert "AUTOMATIC PAYMENT" in source
    assert "Acceptance creates the invoice for the amount currently due" in source
    assert "data-ws-prepare-scheduled-payment" not in source
    assert "payments.default_deposit_percent || 50" not in source
    assert "quoteIdentity().defaultDepositPercent || 50" not in source
    assert "legacyImplicitDeposit" in source
    assert "preset = 'unplanned'" in source
    assert "Enter each payment amount or percentage" in source
    assert "const totals = quoteTotals(item);" in source
    assert "const subtotal = totals.subtotal;" in source


def test_quote_builder_keeps_private_workings_out_of_customer_lines():
    source = WORK_SCHEDULE_JS.read_text(encoding="utf-8")
    styles = WORK_SCHEDULE_CSS.read_text(encoding="utf-8")
    app = APP_JS.read_text(encoding="utf-8")

    assert "INTERNAL · HIDDEN FROM CUSTOMER" in source
    assert "data-ws-add-quote-line" in source
    assert "data-ws-quote-description" in source
    assert "Description of work shown to the customer" in source
    assert "This appears on the quotation and PDF" in source
    assert "description_of_work:item.quote?.description_of_work" in source
    assert "+ Add another customer quote line" in source
    assert "data-ws-add-quote-child" in source
    assert "Person / contractor" in source
    assert "Manual labour cost" in source
    assert "data-ws-labour-person" in source
    assert "data-ws-labour-basis" in source
    assert "Day rate" in source
    assert "data-daily" in source
    assert "labour_resources" in source
    assert 'data-ws-quote-child-field="cost_price"' in source
    assert 'data-ws-quote-child-field="margin_percent"' in source
    assert "Gross margin %" in source
    assert "A ${margin.toFixed(2).replace(/\\.00$/, '')}% markup would instead be" in source
    assert "data-ws-rewrite-description" in source
    assert "Rewrite professionally with SI" in source
    assert "endpoint('/rewrite-description')" in source
    assert "black rows are shown to the customer" in source.lower()
    assert "identity.name.slice(0,2)" not in source
    assert "Upload logo" in source
    assert "data-aion-business-logo-upload" in app
    assert "quote_logo_data_url" in app
    assert ".ws-quote-child" in styles
    assert ".ws-quote-child.is-labour" in styles
    assert ".ws-add-quote-line-row" in styles
    assert "background:#eef4ff !important" in styles
