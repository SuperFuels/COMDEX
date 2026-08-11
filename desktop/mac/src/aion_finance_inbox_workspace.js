(function installAionFinanceInbox(global) {
  'use strict';

  const API_BASE = 'http://127.0.0.1:8080';
  const state = { workspaceId: '', inbox: null, organisation: null, readerProviders: [], accountingProviders: [], bookkeepingDrafts: [], ledgerSummary: null, xeroConnection: null, xeroContacts: [], xeroExports: [], xeroSupplierRequests: [], templates: null, tab: 'inbox', panel: null, busy: false, error: '', message: '' };
  let scheduled = false;

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const text = (value) => String(value || '').replaceAll('_', ' ');
  const value = (item) => item === null || item === undefined ? '' : item;
  const money = (amount, currency = 'EUR') => amount === null || amount === undefined ? 'Amount required' : new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(Number(amount));

  function businessId() { return global.AionBusinessContainerClient?.resolveBusinessId?.() || ''; }
  function terminal() { return document.querySelector('[data-aion-shared-pilot-terminal="true"][data-aion-pilot-role="finance"]'); }
  function stream() { return terminal()?.querySelector?.('[data-aion-pilot-stream-window]'); }
  function people() { return (state.organisation?.people || []).filter((item) => item.status === 'active'); }
  function cards() { return (state.organisation?.assets || []).filter((item) => item.status === 'active' && item.asset_type === 'company_card'); }
  function departments() { return (state.organisation?.departments || []).filter((item) => item.status === 'active'); }
  function personName(id) { return people().find((item) => item.id === id)?.name || 'Submitter required'; }
  function departmentName(id) { return departments().find((item) => item.id === id)?.name || 'No department'; }
  function cardName(id) { const item = cards().find((card) => card.id === id); return item ? `${item.name}${item.last_four ? ` · •••• ${item.last_four}` : ''}` : 'No card'; }
  function readerProvider() { return state.inbox?.expense_policy?.receipt_reader_provider || 'auto'; }
  function readerPayload() { return { provider: readerProvider() }; }
  function providerLabel(id) { return state.readerProviders.find((item) => item.id === id)?.label || text(id); }
  function providerReadiness(item) { return item.configured ? 'ready' : item.status === 'no_verified_image_input' ? 'no verified receipt vision' : 'not connected'; }
  function bookkeepingDraft(documentId) { return state.bookkeepingDrafts.find((item) => item.source_document_id === documentId); }
  function xeroExport(draftId) { return state.xeroExports.find((item) => item.draft_id === draftId); }
  function bookkeepingAction(document) {
    if (document.status !== 'approved_for_accounting') return '';
    const draft = bookkeepingDraft(document.id);
    if (!draft) return `<button class="primary" data-fiw-prepare-bookkeeping="${esc(document.id)}">Prepare balanced entry</button><span class="fiw-no-write">Not yet in the internal ledger</span>`;
    if (draft.status === 'mapping_required') return `<button data-fiw-open-document="${esc(document.id)}">Complete account mapping</button><span class="fiw-bookkeeping-warn">Mapping required: ${esc((draft.unresolved_controls || []).map(text).join(', '))}</span>`;
    if (draft.status === 'exact_posting_approval_required') return `<button class="primary" data-fiw-approve-bookkeeping="${esc(draft.draft_id)}">Approve exact entry</button><span class="fiw-no-write">Balanced · separate posting approval required</span>`;
    if (draft.status === 'approved_for_internal_posting') return `<button class="primary" data-fiw-post-bookkeeping="${esc(draft.draft_id)}">Post to internal ledger</button><span class="fiw-no-write">Approved · no external write</span>`;
    if (draft.status === 'posted_internal' || draft.status === 'synced_to_xero') {
      const exported = xeroExport(draft.draft_id);
      if (exported?.status === 'verified_in_xero' || draft.status === 'synced_to_xero') return `<span class="fiw-posted">✓ Verified in Xero</span><span class="fiw-no-write">Read-back confirmed · ${esc(exported?.verification?.resource_id || draft.provider_exports?.xero?.resource_id || '')}</span>`;
      if (exported?.status === 'exact_provider_approval_required') return `<button class="primary" data-fiw-approve-xero="${esc(exported.export_id)}">Approve exact Xero bill</button><span class="fiw-no-write">No provider write yet</span>`;
      if (exported?.status === 'approved_for_xero_write' || exported?.status === 'resource_verified_pending_attachment') return `<button class="primary" data-fiw-execute-xero="${esc(exported.export_id)}">${exported.status === 'resource_verified_pending_attachment' ? 'Finish receipt attachment verification' : 'Create and verify in Xero'}</button><span class="fiw-bookkeeping-warn">${exported.status === 'resource_verified_pending_attachment' ? 'The Xero bill exists; only the attachment step will resume' : 'This performs the approved external write'}</span>`;
      if (exported?.status === 'verification_failed') return `<span class="fiw-bookkeeping-warn">Xero read-back did not match · manual recovery required; Tessaris will not write again</span>`;
      if (exported?.status === 'provider_rejected') return `<span class="fiw-bookkeeping-warn">Xero rejected the bill · review the exact errors</span>`;
      return `<button data-fiw-prepare-xero="${esc(draft.draft_id)}" ${state.xeroConnection?.external_writes_enabled ? '' : 'disabled'}>Prepare Xero bill</button><span class="fiw-no-write">✓ Internal ledger · ${state.xeroConnection?.external_writes_enabled ? 'ready for export' : 'connect or reauthorise Xero first'}</span>`;
    }
    return `<span class="fiw-no-write">${esc(text(draft.status))}</span>`;
  }

  async function request(path, options = {}) {
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(String(body.detail || body.error || `Request failed ${response.status}`).replaceAll('_', ' '));
    return body;
  }

  function statusLabel(status) {
    return ({ needs_submitter: 'Needs submitter', needs_review: 'Needs review', needs_information: 'Needs information', awaiting_approval: 'Awaiting approval', approved_for_accounting: 'Approved draft', rejected: 'Rejected' })[status] || text(status);
  }

  function metric(label, count, kind = '') { return `<article class="${kind}"><strong>${Number(count || 0)}</strong><span>${esc(label)}</span></article>`; }

  function documentCard(document) {
    const fields = document.extraction?.fields || {};
    const source = document.source || {};
    const warnings = document.extraction?.warnings || [];
    return `<article class="fiw-document status-${esc(document.status)}">
      <div class="fiw-doc-icon">${source.preview_kind === 'image' ? 'PHOTO' : source.preview_kind === 'pdf' ? 'PDF' : 'FILE'}</div>
      <div class="fiw-doc-main"><div><strong>${esc(fields.supplier || source.filename || 'Unreviewed document')}</strong><span>${esc(statusLabel(document.status))}</span></div>
        <p>${esc(text(document.document_type))} · ${esc(personName(document.ownership?.submitted_by_person_id))} · ${esc(departmentName(document.ownership?.department_id))}</p>
        <small>${esc(source.filename)} · received ${esc(new Date(source.received_at).toLocaleString())}${document.ownership?.card_asset_id ? ` · ${esc(cardName(document.ownership.card_asset_id))}` : ''}</small>
      </div>
      <div class="fiw-doc-value"><strong>${money(fields.total, fields.currency || 'EUR')}</strong><small>${fields.document_date ? esc(fields.document_date) : 'Date required'}</small></div>
      ${warnings.length ? `<div class="fiw-warnings">${warnings.map((item) => `<span>${esc(item)}</span>`).join('')}</div>` : ''}
      <div class="fiw-doc-actions">${document.extraction?.status === 'not_run' || document.extraction?.status === 'failed' ? `<button class="primary" data-fiw-read-document="${esc(document.id)}">Read receipt</button>` : ''}<button data-fiw-open-document="${esc(document.id)}">${document.status === 'needs_review' || document.status === 'needs_submitter' || document.status === 'needs_information' ? 'Review document' : 'View details'}</button>
      ${document.status === 'awaiting_approval' ? `<button class="primary" data-fiw-decide-document="${esc(document.id)}">Review approval</button>` : ''}
      ${bookkeepingAction(document)}</div>
    </article>`;
  }

  function inboxView() {
    const documents = [...(state.inbox?.documents || [])].reverse();
    return `<section class="fiw-body"><div class="fiw-heading"><div><span>DAILY FINANCE INBOX</span><h3>Receipts, invoices and expense evidence</h3><p>Every item keeps its original file, submitter, card, department, project, approval route and accounting destination together.</p></div><button class="primary" data-fiw-upload>+ Upload receipt or invoice</button></div>
      ${documents.length ? `<div class="fiw-list">${documents.map(documentCard).join('')}</div>` : `<div class="fiw-empty"><span>START WITH ANY DOCUMENT</span><h3>Photograph it, upload it, or send it later</h3><p>Desktop upload works now. Phone capture, a mobile share action and the Finance Agent mailbox will all feed this same inbox without changing the accounting workflow.</p><button class="primary" data-fiw-upload>Choose a photo or document</button></div>`}
    </section>`;
  }

  function channelsView() {
    return `<section class="fiw-body"><div class="fiw-heading"><div><span>ONE INBOX · MANY ROUTES</span><h3>How documents reach the Finance Agent</h3><p>The source channel changes, but the canonical document, authority and approval contract does not.</p></div></div>
      <div class="fiw-channels">${(state.inbox?.intake_channels || []).map((item) => `<article class="${item.status}"><span>${item.status === 'enabled' ? 'LIVE NOW' : 'PLANNED'}</span><strong>${esc(item.name)}</strong><p>${esc(text(item.transport))}</p></article>`).join('')}</div>
      <div class="fiw-policy"><strong>Current boundary</strong><p>Phone and mailbox delivery are adapters to build later. They must authenticate or reliably match the sender, preserve the original bytes and source metadata, and then call the same intake service used by desktop upload.</p></div>
    </section>`;
  }

  function accountingView() {
    const summary = state.ledgerSummary || {};
    const xero = state.xeroConnection || {};
    return `<section class="fiw-body"><div class="fiw-heading"><div><span>ONE BOOKKEEPING CORE · MULTIPLE PROVIDERS</span><h3>Accounting control plane</h3><p>AION prepares one balanced instruction. An adapter may later translate that exact approved entry, but cannot alter it.</p></div></div>
      <div class="fiw-ledger-summary"><article><span>INTERNAL JOURNAL</span><strong>${Number(summary.entry_count || 0)} entries</strong><p>${summary.balanced === false ? 'Integrity check failed' : 'Balanced and hash-protected'}</p></article><article><span>PROVIDER SYNC</span><strong>${esc(text(summary.provider_sync_status || 'not exported'))}</strong><p>Kept separate from provider actuals to prevent double-counting.</p></article></div>
      <div class="fiw-accounting-providers">${state.accountingProviders.map((item) => `<article class="${item.connected ? 'ready' : 'missing'}"><span>${item.connected ? 'CONNECTED' : 'NOT CONNECTED'}</span><strong>${esc(item.name)}</strong><p>${esc(text(item.implemented_mode))}</p><small>${item.external_writes_enabled ? 'Approved writes enabled' : 'External writes disabled'}</small></article>`).join('')}</div>
      <div class="fiw-policy"><strong>Xero write readiness</strong><p>${xero.connected ? `${esc(xero.tenant_name || 'Xero organisation')} is connected. ${xero.external_writes_enabled ? 'Exact-approved bill creation and read-back verification are enabled.' : `Reauthorisation is required for: ${esc((xero.missing_scopes || []).join(', '))}.`}` : 'Xero is not connected for this business.'} ${state.xeroContacts.length ? `${state.xeroContacts.length} active supplier/customer contacts are available from the latest sync.` : 'There are no synced contacts yet. Create the first supplier through the controlled flow below.'}</p><button data-fiw-new-xero-supplier ${xero.external_writes_enabled ? '' : 'disabled'}>+ Prepare new Xero supplier</button>${state.xeroSupplierRequests.map((item) => `<span class="fiw-supplier-request"><b>${esc(item.payload?.Contacts?.[0]?.Name || 'Supplier')}</b> · ${esc(text(item.status))}${item.status === 'exact_provider_approval_required' ? ` <button data-fiw-approve-xero-supplier="${esc(item.contact_request_id)}">Approve exact contact</button>` : ''}${item.status === 'approved_for_xero_write' ? ` <button data-fiw-execute-xero-supplier="${esc(item.contact_request_id)}">Create and verify contact</button>` : ''}</span>`).join('')}</div>
      <div class="fiw-policy"><strong>Honest boundary</strong><p>Tessaris can now create exact-approved Xero bills and sales invoices, then verify them by reading them back. Xero bank-statement reconciliation remains in Xero Bank Rec or Cash Coding. QuickBooks Online, Sage and FreeAgent still need their live adapters.</p></div>
    </section>`;
  }

  function policyView() {
    const policy = state.inbox?.expense_policy || {};
    return `<section class="fiw-body"><div class="fiw-heading"><div><span>BUSINESS-DEFINED RULES</span><h3>Expense policy and allowances</h3><p>These limits help route exceptions. They do not decide statutory tax treatment.</p></div></div>
      <form class="fiw-policy-form" data-fiw-policy-form><div class="fiw-provider-choice"><label>Receipt reader<select name="receipt_reader_provider"><option value="auto" ${readerProvider() === 'auto' ? 'selected' : ''}>Automatic — first available cloud reader</option>${state.readerProviders.map((item) => `<option value="${esc(item.id)}" ${readerProvider() === item.id ? 'selected' : ''} ${item.configured ? '' : 'disabled'}>${esc(item.label)} · ${esc(providerReadiness(item))}</option>`).join('')}</select></label><p>AION keeps one receipt contract whichever model you choose. An explicit choice never silently sends the document to a different external provider. Local Gemma is explicit-only because it uses substantial Mac memory.</p></div>
      <div class="fiw-provider-grid">${state.readerProviders.map((item) => `<article class="${item.configured ? 'ready' : 'missing'}"><span>${item.local ? 'ON THIS MAC · EXPLICIT ONLY' : 'EXTERNAL PROVIDER'}</span><strong>${esc(item.label)}</strong><p>${esc(item.model || 'No model selected')}</p><small>${esc(item.resource_warning || (item.status === 'no_verified_image_input' ? 'Available for text work; disabled for receipts until its API exposes image input.' : (item.configured ? 'Ready for capability check at read time' : 'Connect an API key in Settings')))}</small></article>`).join('')}</div>
      <div class="fiw-three"><label>Policy currency<input name="currency" maxlength="3" value="${esc(policy.currency || 'EUR')}"></label><label>Meal receipt limit<input type="number" min="0" step="0.01" name="meal_receipt_limit" value="${esc(value(policy.meal_receipt_limit))}" placeholder="Optional"></label><label>Daily meal allowance<input type="number" min="0" step="0.01" name="meal_daily_allowance" value="${esc(value(policy.meal_daily_allowance))}" placeholder="Optional"></label></div>
      <div class="fiw-two"><label>Mileage rate per distance unit<input type="number" min="0" step="0.001" name="mileage_rate" value="${esc(value(policy.mileage_rate))}" placeholder="Optional business policy"></label><div class="fiw-policy"><strong>Always reviewed</strong><p>Meals need purpose and attendees. Fuel needs vehicle, journey and reclaim basis. Alcohol, mixed and possible personal purchases never pass silently.</p></div></div>
      <footer><button class="primary" type="submit">Save expense rules</button></footer></form>
    </section>`;
  }

  function panel() {
    if (!state.panel) return '';
    if (state.panel.type === 'upload') {
      return `<aside class="fiw-panel"><form data-fiw-upload-form><header><div><span>NEW FINANCE DOCUMENT</span><h2>Upload a receipt or invoice</h2><p>A phone photo works when this form is opened on a mobile device.</p></div><button type="button" data-fiw-close>×</button></header>
        <label class="fiw-file">Photo, PDF or supported document<input type="file" name="file" accept="image/*,.pdf,.csv,.xml" capture="environment" required><small>JPG, PNG, WEBP, HEIC, PDF, CSV or XML · maximum 25 MB. Images and PDFs use ${esc(readerProvider() === 'auto' ? 'the first available capable reader' : providerLabel(readerProvider()))}; the protected original remains in Tessaris.</small></label>
        <div class="fiw-two"><label>Document type<select name="document_type"><option value="receipt">Receipt</option><option value="supplier_invoice">Supplier invoice</option><option value="sales_invoice">Sales invoice</option><option value="credit_note">Credit note</option><option value="expense_claim">Expense claim</option><option value="other">Other</option></select></label>
        <label>Submitted by<select name="submitted_by_person_id"><option value="">Select the person</option>${people().map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label></div>
        <div class="fiw-two"><label>Department<select name="department_id"><option value="">Use the person's department</option>${departments().map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label>
        <label>Company card<select name="card_asset_id"><option value="">Not paid on a company card</option>${cards().map((item) => `<option value="${esc(item.id)}">${esc(cardName(item.id))} · ${esc(personName(item.assigned_person_id))}</option>`).join('')}</select></label></div>
        <label>Project or job reference<input name="project_id" placeholder="Optional project, client or job"></label>
        <footer><button type="button" data-fiw-close>Cancel</button><button class="primary" type="submit">Add to Finance Inbox</button></footer>
      </form></aside>`;
    }
    const document = state.panel.document;
    if (state.panel.type === 'review') {
      const fields = document.extraction?.fields || {};
      const assessment = document.extraction?.expense_assessment || {};
      const questions = assessment.questions || [];
      const lineItems = document.extraction?.line_items || [];
      const allocation = document.allocation || {};
      const own = document.ownership || {};
      const preview = `${API_BASE}/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/documents/${encodeURIComponent(document.id)}/file`;
      return `<aside class="fiw-panel wide"><form data-fiw-review-form data-document-id="${esc(document.id)}"><header><div><span>REVIEW ORIGINAL EVIDENCE</span><h2>${esc(document.source?.filename)}</h2><p>Confirm the accounting facts. Nothing is posted to an accounting provider.</p></div><button type="button" data-fiw-close>×</button></header>
        <div class="fiw-preview">${document.source?.preview_kind === 'image' ? `<img src="${preview}" alt="Uploaded finance document">` : `<a href="${preview}" target="_blank" rel="noopener">Open original ${esc(document.source?.preview_kind || 'document')}</a>`}<small>SHA-256 protected original · ${esc(document.source?.content_hash)}</small></div>
        ${document.extraction?.method === 'not_run' || document.extraction?.status === 'failed' ? `<button class="primary" type="button" data-fiw-read-document="${esc(document.id)}">Read document and suggest the fields</button>` : `<div class="fiw-reader"><strong>Reader suggestions · human confirmation required</strong><span>${esc(document.extraction?.reader?.provider || 'vision provider')} · ${esc(document.extraction?.reader?.model || 'structured vision')} · no provider storage requested by Tessaris</span></div>`}
        ${questions.length ? `<div class="fiw-context"><strong>The receipt cannot answer these</strong>${questions.map((item) => `<label>${esc(item.label)}<input name="context_${esc(item.id)}" placeholder="Add the missing business context"></label>`).join('')}</div>` : ''}
        ${lineItems.length ? `<details class="fiw-lines"><summary>${lineItems.length} line item suggestion${lineItems.length === 1 ? '' : 's'}</summary>${lineItems.map((item) => `<div><span>${esc(item.description)}</span><b>${item.total === null ? '' : esc(money(item.total, fields.currency || 'EUR'))}</b></div>`).join('')}</details>` : ''}
        <div class="fiw-two"><label>Supplier / customer<input name="supplier" value="${esc(value(fields.supplier))}" required></label><label>Document date<input type="date" name="document_date" value="${esc(value(fields.document_date))}" required></label></div>
        <div class="fiw-three"><label>Currency<input name="currency" maxlength="3" value="${esc(fields.currency || 'EUR')}"></label><label>Net<input type="number" min="0" step="0.01" name="net" value="${esc(value(fields.net))}"></label><label>Tax<input type="number" min="0" step="0.01" name="tax" value="${esc(value(fields.tax))}"></label></div>
        <div class="fiw-two"><label>Total<input type="number" min="0" step="0.01" name="total" value="${esc(value(fields.total))}" required></label><label>Invoice / receipt number<input name="invoice_number" value="${esc(value(fields.invoice_number))}"></label></div>
        <label>Description<input name="description" value="${esc(value(fields.description))}" placeholder="What was purchased or sold?"></label>
        <div class="fiw-two"><label>Submitted by<select name="submitted_by_person_id" required><option value="">Select person</option>${people().map((item) => `<option value="${esc(item.id)}" ${own.submitted_by_person_id === item.id ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}</select></label><label>Department<select name="department_id"><option value="">No department</option>${departments().map((item) => `<option value="${esc(item.id)}" ${own.department_id === item.id ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}</select></label></div>
        <div class="fiw-two"><label>Company card<select name="card_asset_id"><option value="">No company card</option>${cards().map((item) => `<option value="${esc(item.id)}" ${own.card_asset_id === item.id ? 'selected' : ''}>${esc(cardName(item.id))} · ${esc(personName(item.assigned_person_id))}</option>`).join('')}</select></label><label>Project / job<input name="project_id" value="${esc(value(own.project_id))}"></label></div>
        <div class="fiw-three"><label>Expense category<input name="category" value="${esc(value(allocation.category))}" placeholder="e.g. materials, fuel, meals"></label><label>Account code<input name="account_code" value="${esc(value(allocation.account_code))}"></label><label>Account name<input name="account_name" value="${esc(value(allocation.account_name))}"></label></div><label>Tax code<input name="tax_code" value="${esc(value(allocation.tax_code))}"></label>
        <div class="fiw-two"><label>Accounting destination<select name="destination">${(state.inbox.accounting_destinations || []).map((item) => `<option value="${esc(item.id)}" ${document.accounting?.destination === item.id ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}</select></label><label>Reviewed by<select name="reviewed_by_person_id"><option value="">Current local user</option>${people().map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label></div>
        <footer><button type="button" data-fiw-close>Close</button><button class="primary" type="submit">Confirm and route for approval</button></footer>
      </form></aside>`;
    }
    if (state.panel.type === 'decision') {
      const fields = document.extraction?.fields || {};
      const route = document.authority?.approval_route || {};
      const candidates = route.candidates || [];
      return `<aside class="fiw-panel"><form data-fiw-decision-form data-document-id="${esc(document.id)}"><header><div><span>APPROVAL GATE</span><h2>${esc(fields.supplier || document.source?.filename)}</h2><p>${money(fields.total, fields.currency || 'EUR')} · ${esc(personName(document.ownership?.submitted_by_person_id))}</p></div><button type="button" data-fiw-close>×</button></header>
        <div class="fiw-route"><strong>${route.status === 'route_available' ? 'Authorised route found' : 'No authorised approver'}</strong>${candidates.map((item) => `<p>${esc(item.person_name)} · ${item.allowed ? 'may approve' : esc(text(item.reason))}</p>`).join('') || '<p>Add an owner, manager or Finance Controller with approval authority in HR.</p>'}${route.self_approval_only ? '<small>The only eligible route is self-approval. This remains visible in the audit record.</small>' : ''}</div>
        <label>Decision maker<select name="decided_by_person_id" required><option value="">Select approver</option>${people().map((item) => `<option value="${esc(item.id)}" ${route.recommended_approver_person_id === item.id ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}</select></label>
        <label>Note<textarea name="note" rows="3" placeholder="Optional approval, rejection or information note"></textarea></label>
        <footer><button type="submit" name="decision" value="needs_information">Request information</button><button class="danger" type="submit" name="decision" value="reject">Reject</button><button class="primary" type="submit" name="decision" value="approve">Approve accounting draft</button></footer>
      </form></aside>`;
    }
    if (state.panel.type === 'bookkeeping') {
      const draft = state.panel.draft;
      const action = state.panel.action;
      const prepare = action === 'prepare'; const approve = action === 'approve';
      return `<aside class="fiw-panel"><form data-fiw-bookkeeping-form data-action="${esc(action)}" data-document-id="${esc(state.panel.document?.id || '')}" data-draft-id="${esc(draft?.draft_id || '')}"><header><div><span>CONTROLLED BOOKKEEPING</span><h2>${prepare ? 'Prepare balanced entry' : approve ? 'Approve exact entry' : 'Post to internal ledger'}</h2><p>${prepare ? 'Create debits and credits from the approved receipt.' : approve ? 'Approve the exact hash-protected lines shown below.' : 'Record the approved entry internally. No accounting provider will be changed.'}</p></div><button type="button" data-fiw-close>×</button></header>
        ${draft ? `<div class="fiw-journal-lines">${(draft.lines || []).map((line) => `<div><span>${esc(line.account_code)} · ${esc(line.account_name)}</span><b>${line.debit ? `Dr ${money(line.debit, draft.currency)}` : `Cr ${money(line.credit, draft.currency)}`}</b></div>`).join('')}<footer><strong>Total</strong><strong>${money(draft.debit_total, draft.currency)}</strong></footer></div>` : ''}
        <label>${approve ? 'Approved by' : prepare ? 'Prepared by' : 'Posted by'}<select name="person_id" required><option value="">Select authorised person</option>${people().map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label>
        <div class="fiw-route"><strong>Authority stays separate</strong><p>The backend checks the selected person's Finance role. Preparing, approving and posting are recorded independently, and provider writes remain disabled.</p></div>
        <footer><button type="button" data-fiw-close>Cancel</button><button class="primary" type="submit">${prepare ? 'Prepare entry' : approve ? 'Approve exact entry' : 'Post internally'}</button></footer>
      </form></aside>`;
    }
    if (state.panel.type === 'xero') {
      const draft = state.panel.draft; const record = state.panel.export; const action = state.panel.action;
      const preparing = action === 'prepare'; const approving = action === 'approve';
      return `<aside class="fiw-panel"><form data-fiw-xero-form data-action="${esc(action)}" data-draft-id="${esc(draft?.draft_id || record?.draft_id || '')}" data-export-id="${esc(record?.export_id || '')}"><header><div><span>EXACT XERO EXPORT</span><h2>${preparing ? 'Prepare accounts-payable bill' : approving ? 'Approve exact Xero payload' : 'Create and verify Xero bill'}</h2><p>${preparing ? 'Map the approved expense to an existing Xero contact.' : approving ? 'The payload is frozen. Approval applies only to this exact hash.' : 'This performs the external write once, then reads the bill back before confirming success.'}</p></div><button type="button" data-fiw-close>×</button></header>
        ${preparing ? `<label>Existing Xero supplier/contact<select name="xero_contact_id" required><option value="">Select an existing Xero contact</option>${state.xeroContacts.map((item) => `<option value="${esc(item.contact_id)}">${esc(item.name || item.email || item.contact_id)}</option>`).join('')}</select></label><label>Initial Xero status<select name="target_status"><option value="DRAFT">Draft — review again in Xero</option><option value="SUBMITTED">Submitted — enter Xero approval workflow</option><option value="AUTHORISED">Authorised — affects Xero reports immediately</option></select></label>` : `<div class="fiw-xero-payload"><small>Exact approval contract hash</small><code>${esc(record?.approval_hash || '')}</code><pre>${esc(JSON.stringify({ payload: record?.payload || {}, attachment: record?.attachment || null }, null, 2))}</pre></div>`}
        <label>${preparing ? 'Prepared by' : approving ? 'Approved by' : 'Executed by'}<select name="person_id" required><option value="">Select authorised person</option>${people().map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label>
        <div class="fiw-route"><strong>${preparing ? 'No contact creation' : approving ? 'Exact approval' : 'Idempotent and verified'}</strong><p>${preparing ? 'Tessaris requires an existing Xero contact to avoid silently creating supplier duplicates.' : approving ? 'Changing any account, tax, amount, contact or status invalidates this approval.' : 'The same idempotency key prevents rapid duplicate submission; Xero read-back must match identity, type, reference, status, total and contact.'}</p></div>
        <footer><button type="button" data-fiw-close>Cancel</button><button class="primary" type="submit">${preparing ? 'Prepare exact bill' : approving ? 'Approve exact payload' : 'Create and verify in Xero'}</button></footer>
      </form></aside>`;
    }
    if (state.panel.type === 'xero_supplier') {
      const record = state.panel.record; const action = state.panel.action; const preparing = action === 'prepare';
      return `<aside class="fiw-panel"><form data-fiw-xero-supplier-form data-action="${esc(action)}" data-request-id="${esc(record?.contact_request_id || '')}"><header><div><span>XERO SUPPLIER CONTROL</span><h2>${preparing ? 'Prepare new supplier' : action === 'approve' ? 'Approve exact supplier' : 'Create and verify supplier'}</h2><p>No supplier is created until the exact payload is approved.</p></div><button type="button" data-fiw-close>×</button></header>${preparing ? '<label>Supplier name<input name="name" required maxlength="255"></label><label>Email address<input name="email" type="email"></label>' : `<div class="fiw-xero-payload"><code>${esc(record?.payload_hash || '')}</code><pre>${esc(JSON.stringify(record?.payload || {}, null, 2))}</pre></div>`}<label>${preparing ? 'Prepared by' : action === 'approve' ? 'Approved by' : 'Executed by'}<select name="person_id" required><option value="">Select authorised person</option>${people().map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label><footer><button type="button" data-fiw-close>Cancel</button><button class="primary" type="submit">${preparing ? 'Prepare exact contact' : action === 'approve' ? 'Approve exact contact' : 'Create and verify in Xero'}</button></footer></form></aside>`;
    }
    return '';
  }

  function markup() {
    const summary = state.inbox?.summary || {};
    return `<section class="fiw-shell" data-aion-finance-inbox data-fiw-revision="${Number(state.inbox?.revision || 0)}">
      <header class="fiw-hero"><div><span>CAPTURE · VERIFY · APPROVE · ACCOUNT</span><h2>Finance Inbox</h2><p>One controlled route from a receipt photo or invoice to a reviewed accounting instruction.</p></div><div><b>${state.busy ? 'WORKING…' : 'PROVIDER-NEUTRAL'}</b><small>${state.xeroConnection?.external_writes_enabled ? 'Exact-approved Xero writes enabled' : 'External writes disabled'}</small></div></header>
      ${state.error ? `<div class="fiw-alert error">${esc(state.error)}</div>` : ''}${state.message ? `<div class="fiw-alert success">${esc(state.message)}</div>` : ''}
      <div class="fiw-metrics">${metric('Needs review', summary.needs_review, 'attention')}${metric('Awaiting approval', summary.awaiting_approval, 'waiting')}${metric('Approved drafts', summary.approved_for_accounting, 'ready')}${metric('External writes', summary.external_writes)}</div>
      <nav class="fiw-tabs"><button class="${state.tab === 'inbox' ? 'active' : ''}" data-fiw-tab="inbox">Inbox</button><button class="${state.tab === 'accounting' ? 'active' : ''}" data-fiw-tab="accounting">Accounting connections</button><button class="${state.tab === 'policy' ? 'active' : ''}" data-fiw-tab="policy">Expense rules</button><button class="${state.tab === 'channels' ? 'active' : ''}" data-fiw-tab="channels">Phone, email & other routes</button><button class="primary" data-fiw-upload>+ Add document</button></nav>
      ${state.tab === 'channels' ? channelsView() : state.tab === 'policy' ? policyView() : state.tab === 'accounting' ? accountingView() : inboxView()}${panel()}
    </section>`;
  }

  function render() {
    const target = stream();
    if (!target || !state.inbox) return;
    const existing = target.querySelector('[data-aion-finance-inbox]');
    if (existing) existing.outerHTML = markup(); else target.insertAdjacentHTML('afterbegin', markup());
  }

  async function load() {
    const workspaceId = businessId();
    if (!workspaceId || !terminal()) return;
    state.workspaceId = workspaceId; state.error = '';
    try {
      const [inboxResult, organisationResult, accountingResult, draftsResult, ledgerSummary, xeroStatus, xeroContacts, xeroExports, xeroSupplierRequests] = await Promise.all([
        request(`/api/aion/business/finance-inbox/${encodeURIComponent(workspaceId)}`),
        request(`/api/aion/business/organisation/${encodeURIComponent(workspaceId)}`),
        request(`/api/aion/finance-bookkeeping/${encodeURIComponent(workspaceId)}/providers`),
        request(`/api/aion/finance-bookkeeping/${encodeURIComponent(workspaceId)}/drafts`),
        request(`/api/aion/finance-bookkeeping/${encodeURIComponent(workspaceId)}/ledger-summary`),
        request(`/api/aion/integrations/xero/${encodeURIComponent(workspaceId)}/status`),
        request(`/api/aion/integrations/xero/${encodeURIComponent(workspaceId)}/contacts`),
        request(`/api/aion/integrations/xero/${encodeURIComponent(workspaceId)}/bookkeeping-exports`),
        request(`/api/aion/integrations/xero/${encodeURIComponent(workspaceId)}/supplier-contacts`),
      ]);
      state.inbox = inboxResult.inbox; state.readerProviders = inboxResult.reader_providers || []; state.organisation = organisationResult.model; state.accountingProviders = accountingResult.providers || []; state.bookkeepingDrafts = draftsResult.drafts || []; state.ledgerSummary = ledgerSummary; state.xeroConnection = xeroStatus.connection || null; state.xeroContacts = xeroContacts.contacts || []; state.xeroExports = xeroExports.exports || []; state.xeroSupplierRequests = xeroSupplierRequests.requests || []; render();
    } catch (error) { state.error = `Finance Inbox could not load: ${error.message}`; if (state.inbox) render(); }
  }

  function currentDocument(id) { return state.inbox?.documents?.find((item) => item.id === id); }
  function formValues(form) { return Object.fromEntries(new FormData(form).entries()); }

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-aion-finance-inbox] button');
    if (!button) return;
    if (button.dataset.fiwTab) { state.tab = button.dataset.fiwTab; state.panel = null; render(); return; }
    if (button.hasAttribute('data-fiw-upload')) { state.panel = { type: 'upload' }; state.error = ''; state.message = ''; render(); return; }
    if (button.hasAttribute('data-fiw-close')) { state.panel = null; render(); return; }
    if (button.dataset.fiwReadDocument) {
      if (state.busy) return;
      state.busy = true; state.error = ''; state.message = 'Reading visible receipt facts and checking business rules…'; render();
      try {
        await request(`/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/documents/${encodeURIComponent(button.dataset.fiwReadDocument)}/extract`, { method: 'POST', body: JSON.stringify(readerPayload()) });
        state.message = 'Suggestions are ready. Confirm the facts and answer any business-context questions.'; state.panel = null; await load();
      } catch (error) { const message = error.message; await load(); state.error = message; state.message = ''; }
      finally { state.busy = false; render(); }
      return;
    }
    if (button.dataset.fiwOpenDocument) { state.panel = { type: 'review', document: currentDocument(button.dataset.fiwOpenDocument) }; render(); return; }
    if (button.dataset.fiwDecideDocument) { state.panel = { type: 'decision', document: currentDocument(button.dataset.fiwDecideDocument) }; render(); }
    if (button.dataset.fiwPrepareBookkeeping) { state.panel = { type: 'bookkeeping', action: 'prepare', document: currentDocument(button.dataset.fiwPrepareBookkeeping) }; render(); return; }
    if (button.dataset.fiwApproveBookkeeping) { state.panel = { type: 'bookkeeping', action: 'approve', draft: state.bookkeepingDrafts.find((item) => item.draft_id === button.dataset.fiwApproveBookkeeping) }; render(); return; }
    if (button.dataset.fiwPostBookkeeping) { state.panel = { type: 'bookkeeping', action: 'post', draft: state.bookkeepingDrafts.find((item) => item.draft_id === button.dataset.fiwPostBookkeeping) }; render(); }
    if (button.dataset.fiwPrepareXero) { state.panel = { type: 'xero', action: 'prepare', draft: state.bookkeepingDrafts.find((item) => item.draft_id === button.dataset.fiwPrepareXero) }; render(); return; }
    if (button.dataset.fiwApproveXero) { state.panel = { type: 'xero', action: 'approve', export: state.xeroExports.find((item) => item.export_id === button.dataset.fiwApproveXero) }; render(); return; }
    if (button.dataset.fiwExecuteXero) { state.panel = { type: 'xero', action: 'execute', export: state.xeroExports.find((item) => item.export_id === button.dataset.fiwExecuteXero) }; render(); }
    if (button.hasAttribute('data-fiw-new-xero-supplier')) { state.panel = { type: 'xero_supplier', action: 'prepare' }; render(); return; }
    if (button.dataset.fiwApproveXeroSupplier) { state.panel = { type: 'xero_supplier', action: 'approve', record: state.xeroSupplierRequests.find((item) => item.contact_request_id === button.dataset.fiwApproveXeroSupplier) }; render(); return; }
    if (button.dataset.fiwExecuteXeroSupplier) { state.panel = { type: 'xero_supplier', action: 'execute', record: state.xeroSupplierRequests.find((item) => item.contact_request_id === button.dataset.fiwExecuteXeroSupplier) }; render(); }
  });

  document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!form.closest('[data-aion-finance-inbox]')) return;
    event.preventDefault(); if (state.busy) return;
    state.busy = true; state.error = ''; state.message = ''; render();
    try {
      if (form.matches('[data-fiw-upload-form]')) {
        const data = new FormData(form); data.set('channel', 'desktop_upload');
        const result = await request(`/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/documents`, { method: 'POST', body: data });
        if (!result.duplicate && ['image', 'pdf'].includes(result.document?.source?.preview_kind)) {
          state.message = 'Document protected. Reading the visible receipt facts now…'; render();
          try {
            await request(`/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/documents/${encodeURIComponent(result.document.id)}/extract`, { method: 'POST', body: JSON.stringify(readerPayload()) });
            state.message = 'Receipt read. Confirm the suggestions and any missing business context.';
          } catch (readError) {
            state.message = 'Document is safe in the inbox. Automatic reading failed, so it remains ready for manual review.';
          }
        } else state.message = result.duplicate ? 'That exact document was already in the inbox.' : 'Document received and protected. Review the accounting details next.';
      } else if (form.matches('[data-fiw-review-form]')) {
        const values = formValues(form);
        const businessContext = Object.fromEntries(Object.entries(values).filter(([key, item]) => key.startsWith('context_') && item).map(([key, item]) => [key.slice(8), item]));
        await request(`/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/documents/${encodeURIComponent(form.dataset.documentId)}/review`, {
          method: 'PUT', body: JSON.stringify({ expected_revision: state.inbox.revision, reviewed_by_person_id: values.reviewed_by_person_id || null,
            fields: { supplier: values.supplier, document_date: values.document_date, currency: values.currency, net: values.net, tax: values.tax, total: values.total, invoice_number: values.invoice_number, description: values.description },
            ownership: { submitted_by_person_id: values.submitted_by_person_id, department_id: values.department_id || null, card_asset_id: values.card_asset_id || null, project_id: values.project_id || null },
            allocation: { category: values.category || null, account_code: values.account_code || null, account_name: values.account_name || null, tax_code: values.tax_code || null, business_context: businessContext }, destination: values.destination,
          }),
        });
        state.message = 'Document confirmed and routed to an authorised approver.';
      } else if (form.matches('[data-fiw-policy-form]')) {
        const values = formValues(form);
        await request(`/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/expense-policy`, { method: 'PUT', body: JSON.stringify({ expected_revision: state.inbox.revision, policy: { receipt_reader_provider: values.receipt_reader_provider, currency: values.currency, meal_receipt_limit: values.meal_receipt_limit, meal_daily_allowance: values.meal_daily_allowance, mileage_rate: values.mileage_rate } }) });
        state.message = 'Expense rules saved. They route exceptions without replacing human or tax authority.';
      } else if (form.matches('[data-fiw-decision-form]')) {
        const submitter = event.submitter; const values = formValues(form);
        await request(`/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/documents/${encodeURIComponent(form.dataset.documentId)}/decision`, {
          method: 'POST', body: JSON.stringify({ expected_revision: state.inbox.revision, decision: submitter?.value || values.decision, decided_by_person_id: values.decided_by_person_id, note: values.note || null }),
        });
        state.message = submitter?.value === 'approve' ? 'Approved provider-neutral accounting draft created. Nothing was posted externally.' : 'Decision recorded.';
      } else if (form.matches('[data-fiw-bookkeeping-form]')) {
        const values = formValues(form); const action = form.dataset.action;
        if (action === 'prepare') {
          await request(`/api/aion/finance-bookkeeping/${encodeURIComponent(state.workspaceId)}/documents/${encodeURIComponent(form.dataset.documentId)}/prepare`, { method: 'POST', body: JSON.stringify({ prepared_by_person_id: values.person_id }) });
          state.message = 'Balanced bookkeeping entry prepared. It still needs exact, separate approval.';
        } else if (action === 'approve') {
          const draft = state.bookkeepingDrafts.find((item) => item.draft_id === form.dataset.draftId);
          await request(`/api/aion/finance-bookkeeping/${encodeURIComponent(state.workspaceId)}/drafts/${encodeURIComponent(form.dataset.draftId)}/approve`, { method: 'POST', body: JSON.stringify({ approved_by_person_id: values.person_id, approved_draft_hash: draft.draft_hash }) });
          state.message = 'Exact bookkeeping entry approved. Nothing has been sent to an accounting provider.';
        } else {
          await request(`/api/aion/finance-bookkeeping/${encodeURIComponent(state.workspaceId)}/drafts/${encodeURIComponent(form.dataset.draftId)}/post-internal`, { method: 'POST', body: JSON.stringify({ posted_by_person_id: values.person_id }) });
          state.message = 'Entry posted to the controlled internal ledger and projected to the Boardroom. Provider actuals remain separate.';
        }
      } else if (form.matches('[data-fiw-xero-form]')) {
        const values = formValues(form); const action = form.dataset.action;
        if (action === 'prepare') {
          await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/bookkeeping-exports/prepare`, { method: 'POST', body: JSON.stringify({ draft_id: form.dataset.draftId, xero_contact_id: values.xero_contact_id, target_status: values.target_status, prepared_by_person_id: values.person_id }) });
          state.message = 'Exact Xero bill prepared. No provider write has occurred; separate approval is required.';
        } else if (action === 'approve') {
          const record = state.xeroExports.find((item) => item.export_id === form.dataset.exportId);
          await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/bookkeeping-exports/${encodeURIComponent(form.dataset.exportId)}/approve`, { method: 'POST', body: JSON.stringify({ approved_by_person_id: values.person_id, approved_payload_hash: record.approval_hash }) });
          state.message = 'Exact Xero payload approved. It has not been sent yet.';
        } else {
          await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/bookkeeping-exports/${encodeURIComponent(form.dataset.exportId)}/execute`, { method: 'POST', body: JSON.stringify({ executed_by_person_id: values.person_id }) });
          state.message = 'Xero bill created and independently verified by provider read-back. Finance and Boardroom now show the confirmed export.';
        }
      } else if (form.matches('[data-fiw-xero-supplier-form]')) {
        const values = formValues(form); const action = form.dataset.action;
        if (action === 'prepare') {
          await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/supplier-contacts/prepare`, { method: 'POST', body: JSON.stringify({ name: values.name, email: values.email || null, prepared_by_person_id: values.person_id }) }); state.message = 'Exact supplier contact prepared. No Xero write has occurred.';
        } else if (action === 'approve') {
          const record = state.xeroSupplierRequests.find((item) => item.contact_request_id === form.dataset.requestId);
          await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/supplier-contacts/${encodeURIComponent(form.dataset.requestId)}/approve`, { method: 'POST', body: JSON.stringify({ approved_by_person_id: values.person_id, approved_payload_hash: record.payload_hash }) }); state.message = 'Exact supplier contact approved. It has not been sent yet.';
        } else {
          await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/supplier-contacts/${encodeURIComponent(form.dataset.requestId)}/execute`, { method: 'POST', body: JSON.stringify({ executed_by_person_id: values.person_id }) }); state.message = 'Supplier created and verified in Xero. Sync Xero to use it on receipt bills.';
        }
      }
      state.panel = null; await load();
    } catch (error) { state.error = error.message; }
    finally { state.busy = false; render(); }
  });

  function installIfPresent() {
    scheduled = false;
    const target = stream(); const workspaceId = businessId();
    if (!target || !workspaceId) return;
    if (target.querySelector('[data-aion-finance-inbox]')) return;
    if (state.workspaceId !== workspaceId || !state.inbox) load(); else render();
  }

  function scheduleInstall() { if (scheduled) return; scheduled = true; requestAnimationFrame(installIfPresent); }

  function installStyles() {
    if (document.getElementById('aion-finance-inbox-styles')) return;
    const style = document.createElement('style'); style.id = 'aion-finance-inbox-styles'; style.textContent = `
      .fiw-shell{--ink:#102a43;--muted:#52677e;--line:#cbd9e6;--blue:#0284c7;--teal:#0f766e;--green:#15803d;box-sizing:border-box;background:#fff;color:var(--ink);border:2px solid #f59e0b;margin:0 0 20px;font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}.fiw-shell *{box-sizing:border-box}.fiw-hero{display:flex;justify-content:space-between;gap:22px;padding:20px 22px;border-bottom:1px solid var(--line)}.fiw-hero>div:first-child{max-width:780px}.fiw-hero span,.fiw-heading span,.fiw-empty>span,.fiw-panel header span{display:block;color:var(--teal);font-size:10px;font-weight:900;letter-spacing:.22em}.fiw-hero h2{margin:5px 0;font-size:27px!important}.fiw-hero p,.fiw-heading p{margin:0;color:var(--muted)!important}.fiw-hero>div:last-child{align-self:flex-start;background:#ecfdf5;border:1px solid #86efac;padding:10px 13px;text-align:right}.fiw-hero b,.fiw-hero small{display:block;color:#166534!important;font-size:10px}.fiw-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;padding:14px 18px;background:#f8fafc}.fiw-metrics article{background:#fff;border:1px solid var(--line);padding:11px 13px}.fiw-metrics strong,.fiw-metrics span{display:block}.fiw-metrics strong{font-size:21px}.fiw-metrics span{font-size:10px;color:#64748b}.fiw-metrics .attention{border-left:4px solid #f59e0b}.fiw-metrics .waiting{border-left:4px solid #0284c7}.fiw-metrics .ready{border-left:4px solid #16a34a}.fiw-tabs{display:flex;gap:7px;padding:12px 18px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);flex-wrap:wrap}.fiw-shell button{appearance:none;background:#fff!important;color:#075985!important;border:1px solid #8fb3c7!important;padding:9px 12px!important;font-weight:800!important;cursor:pointer}.fiw-shell button:disabled{opacity:.45!important;cursor:not-allowed}.fiw-shell button.primary{background:var(--green)!important;border-color:var(--green)!important;color:#fff!important}.fiw-shell button.danger{border-color:#ef4444!important;color:#b91c1c!important}.fiw-tabs button.active{background:var(--teal)!important;color:#fff!important}.fiw-tabs button:last-child{margin-left:auto}.fiw-body{padding:20px}.fiw-heading{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:17px}.fiw-heading h3{margin:5px 0!important;font-size:20px!important}.fiw-list{display:grid;gap:10px}.fiw-document{display:grid;grid-template-columns:62px 1fr auto;gap:13px;align-items:center;border:1px solid var(--line);border-left:5px solid #f59e0b;padding:13px}.fiw-document.status-approved_for_accounting{border-left-color:#16a34a}.fiw-document.status-rejected{border-left-color:#dc2626}.fiw-doc-icon{height:46px;display:grid;place-items:center;background:#e0f2fe;color:#075985;font-size:9px;font-weight:900;letter-spacing:.1em}.fiw-doc-main>div{display:flex;justify-content:space-between;gap:12px}.fiw-doc-main>div span{background:#f1f5f9;color:#475569;padding:3px 7px;font-size:9px;text-transform:uppercase}.fiw-doc-main p{margin:4px 0!important}.fiw-doc-main small,.fiw-doc-value small{display:block;color:#64748b!important}.fiw-doc-value{text-align:right}.fiw-doc-value strong{font-size:16px}.fiw-warnings{grid-column:2/-1;display:grid;gap:3px;background:#fffbeb;border-left:3px solid #f59e0b;padding:8px}.fiw-warnings span{font-size:10px;color:#92400e}.fiw-doc-actions{grid-column:2/-1;display:flex;align-items:center;gap:8px;flex-wrap:wrap}.fiw-no-write,.fiw-posted,.fiw-bookkeeping-warn{font-size:10px}.fiw-no-write,.fiw-posted{color:#166534}.fiw-bookkeeping-warn{color:#92400e}.fiw-empty{text-align:center;border:1px dashed #7dd3fc;background:#f0f9ff;padding:32px;max-width:780px;margin:12px auto}.fiw-empty h3{margin:6px!important}.fiw-empty p{color:var(--muted)!important;max-width:620px;margin:8px auto 18px!important}.fiw-channels,.fiw-accounting-providers{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.fiw-channels article,.fiw-accounting-providers article{border:1px solid var(--line);padding:15px;background:#f8fafc}.fiw-channels article.enabled,.fiw-accounting-providers article.ready{border-top:4px solid #16a34a;background:#ecfdf5}.fiw-accounting-providers article.missing{border-top:4px solid #94a3b8}.fiw-channels article>span,.fiw-accounting-providers article>span,.fiw-ledger-summary article>span{font-size:9px;color:#64748b;letter-spacing:.12em}.fiw-channels article>strong,.fiw-accounting-providers article>strong{display:block;margin:7px 0}.fiw-channels article p,.fiw-accounting-providers article p{margin:0!important;font-size:11px}.fiw-ledger-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:16px}.fiw-ledger-summary article{border:1px solid var(--line);border-left:4px solid var(--teal);padding:14px}.fiw-ledger-summary strong{display:block;margin:5px 0}.fiw-ledger-summary p{margin:0!important;font-size:11px;color:var(--muted)!important}.fiw-policy,.fiw-route{margin-top:16px;border-left:4px solid #0284c7;background:#eff6ff;padding:14px}.fiw-policy p,.fiw-route p{margin:4px 0!important}.fiw-supplier-request{display:block;margin-top:8px;padding:8px;background:#fff;border:1px solid var(--line)}.fiw-alert{margin:12px 18px 0;padding:10px 13px;border-left:4px solid}.fiw-alert.error{background:#fef2f2;border-color:#dc2626;color:#991b1b}.fiw-alert.success{background:#ecfdf5;border-color:#16a34a;color:#166534}.fiw-panel{position:fixed;z-index:11000;inset:0 0 0 auto;width:min(620px,97vw);overflow:auto;background:#fff;box-shadow:-20px 0 60px rgba(15,23,42,.28)}.fiw-panel.wide{width:min(760px,97vw)}.fiw-panel form{padding:24px;display:grid;gap:14px}.fiw-panel header{display:flex;justify-content:space-between;gap:15px;border-bottom:1px solid var(--line);padding-bottom:14px}.fiw-panel header h2{margin:4px 0!important}.fiw-panel header p{margin:0!important}.fiw-panel header button{font-size:22px!important;padding:2px 9px!important}.fiw-panel label{display:grid;gap:5px;color:#334e68;font-size:10px;font-weight:900}.fiw-panel input,.fiw-panel select,.fiw-panel textarea{width:100%;background:#fff!important;color:var(--ink)!important;border:1px solid #94a3b8!important;padding:10px;font:inherit}.fiw-panel textarea{resize:vertical}.fiw-panel footer{display:flex;justify-content:flex-end;gap:8px;border-top:1px solid var(--line);padding-top:15px}.fiw-file{border:1px dashed #38bdf8;background:#f0f9ff;padding:16px}.fiw-file small{color:#64748b}.fiw-two,.fiw-three{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.fiw-three{grid-template-columns:repeat(3,minmax(0,1fr))}.fiw-preview{display:grid;gap:7px;background:#f8fafc;border:1px solid var(--line);padding:12px}.fiw-preview img{display:block;max-width:100%;max-height:340px;margin:auto;object-fit:contain}.fiw-preview a{display:block;padding:25px;text-align:center;background:#e0f2fe;color:#075985;font-weight:900}.fiw-preview small{overflow-wrap:anywhere;color:#64748b}.fiw-route{margin:0}.fiw-route small{display:block;color:#92400e;margin-top:8px}.fiw-journal-lines{display:grid;border:1px solid var(--line)}.fiw-journal-lines>div,.fiw-journal-lines>footer{display:flex;justify-content:space-between;gap:12px;padding:9px 11px;border-bottom:1px solid var(--line)}.fiw-journal-lines>footer{border:0;background:#f8fafc}.fiw-xero-payload{min-width:0;border:1px solid var(--line);background:#f8fafc;padding:11px}.fiw-xero-payload small,.fiw-xero-payload code{display:block;overflow-wrap:anywhere}.fiw-xero-payload pre{max-height:320px;overflow:auto;white-space:pre-wrap;font-size:10px;color:#334155}
      .fiw-reader{display:grid;gap:4px;background:#ecfdf5;border-left:4px solid #16a34a;padding:11px}.fiw-reader span{font-size:10px;color:#166534}.fiw-context{display:grid;gap:9px;background:#fffbeb;border-left:4px solid #f59e0b;padding:13px}.fiw-lines{border:1px solid var(--line);padding:10px}.fiw-lines summary{cursor:pointer;font-weight:800}.fiw-lines div{display:flex;justify-content:space-between;gap:12px;padding:6px;border-top:1px solid #e2e8f0}.fiw-policy-form{display:grid;gap:16px}.fiw-policy-form label{display:grid;gap:5px;color:#334e68;font-size:10px;font-weight:900}.fiw-policy-form input,.fiw-policy-form select{width:100%;background:#fff;color:var(--ink);border:1px solid #94a3b8;padding:10px}.fiw-policy-form footer{display:flex;justify-content:flex-end;border-top:1px solid var(--line);padding-top:14px}.fiw-provider-choice{display:grid;grid-template-columns:minmax(260px,1fr) 2fr;gap:16px;align-items:end;background:#eff6ff;border-left:4px solid #0284c7;padding:14px}.fiw-provider-choice p{margin:0!important;color:#52677e!important}.fiw-provider-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px}.fiw-provider-grid article{border:1px solid var(--line);padding:10px;background:#f8fafc}.fiw-provider-grid article.ready{border-top:4px solid #16a34a;background:#ecfdf5}.fiw-provider-grid article.missing{opacity:.7}.fiw-provider-grid span,.fiw-provider-grid strong,.fiw-provider-grid small{display:block}.fiw-provider-grid span{font-size:8px;letter-spacing:.12em;color:#64748b}.fiw-provider-grid p{margin:4px 0!important;font-size:10px}.fiw-provider-grid small{color:#64748b}
      @media(max-width:900px){.fiw-hero,.fiw-heading{display:block}.fiw-hero>div:last-child{margin-top:12px;text-align:left}.fiw-metrics{grid-template-columns:repeat(2,1fr)}.fiw-document{grid-template-columns:50px 1fr}.fiw-doc-value{grid-column:2;text-align:left}.fiw-doc-actions,.fiw-warnings{grid-column:1/-1}.fiw-two,.fiw-three{grid-template-columns:1fr}.fiw-tabs{flex-wrap:wrap}.fiw-tabs button:last-child{margin-left:0}}
    `; document.head.appendChild(style);
  }

  installStyles();
  new MutationObserver(scheduleInstall).observe(document.getElementById('app') || document.body, { childList: true, subtree: true });
  scheduleInstall();
  global.AionFinanceInbox = { state, load, render };
})(window);
