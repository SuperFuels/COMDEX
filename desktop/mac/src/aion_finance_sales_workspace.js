(function installAionFinanceSales(global) {
  'use strict';

  const API = 'http://127.0.0.1:8080';
  const state = { workspaceId: '', catalog: null, exports: [], monthEnd: null, actorId: '', panel: null, busy: false, error: '', message: '' };
  let scheduled = false;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const text = (value) => String(value || '').replaceAll('_', ' ');
  const money = (value, currency = 'EUR') => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(Number(value || 0));
  const businessId = () => global.AionBusinessContainerClient?.resolveBusinessId?.() || '';
  const inbox = () => document.querySelector('[data-aion-finance-inbox]');
  const people = () => (global.AionFinanceInbox?.state?.organisation?.people || []).filter((row) => row.status === 'active');
  const contacts = () => global.AionFinanceInbox?.state?.xeroContacts || [];
  const exportFor = (invoiceId) => state.exports.find((row) => row.invoice_id === invoiceId);
  const formValues = (form) => Object.fromEntries(new FormData(form).entries());

  async function request(path, options = {}) {
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    if (options.body) headers['Content-Type'] = 'application/json';
    const response = await fetch(`${API}${path}`, { ...options, headers });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(String(body.detail || body.error || `Request failed ${response.status}`).replaceAll('_', ' '));
    return body;
  }

  function actions(invoice) {
    const record = exportFor(invoice.invoice_id);
    if (invoice.status === 'exact_internal_approval_required') return `<button class="primary" data-fsw-approve="${esc(invoice.invoice_id)}">Approve exact invoice</button>`;
    if (invoice.status === 'approved_for_internal_posting') return `<button class="primary" data-fsw-post="${esc(invoice.invoice_id)}">Post internal entry</button>`;
    if (record?.status === 'exact_provider_approval_required') return `<button class="primary" data-fsw-approve-xero="${esc(record.export_id)}">Approve exact Xero draft</button>`;
    if (record?.status === 'approved_for_xero_write' || record?.status === 'provider_response_received') return `<button class="primary" data-fsw-execute-xero="${esc(record.export_id)}">Create and verify in Xero</button>`;
    if (record?.status === 'verified_in_xero' || invoice.status === 'verified_in_xero') return '<span class="fsw-good">✓ Verified in Xero</span>';
    if (invoice.status === 'posted_internal') return `<button data-fsw-prepare-xero="${esc(invoice.invoice_id)}">Prepare Xero draft</button>`;
    return `<span>${esc(text(invoice.status))}</span>`;
  }

  function invoiceRows() {
    const invoices = state.catalog?.invoices || [];
    if (!invoices.length) return '<div class="fsw-empty"><b>No sales invoices yet</b><p>Create one from a customer and an offering. It remains internal until separately approved.</p></div>';
    return `<div class="fsw-list">${invoices.map((row) => `<article><div><span>${esc(row.invoice_number)}</span><strong>${esc(row.customer?.name || 'Customer')}</strong><small>Issued ${esc(row.issue_date)} · due ${esc(row.due_date)} · ${esc(text(row.collection_status))}</small></div><div class="fsw-value"><strong>${money(row.total, row.currency)}</strong><small>${esc(text(row.status))}</small></div><div class="fsw-actions">${actions(row)}${row.amount_due > 0 && row.customer?.email ? `<button data-fsw-reminder="${esc(row.invoice_id)}">Prepare reminder</button>` : ''}</div></article>`).join('')}</div>`;
  }

  function personOptions() { return people().map((row) => `<option value="${esc(row.id)}">${esc(row.name)}</option>`).join(''); }
  function panel() {
    if (!state.panel) return '';
    if (state.panel === 'customer') return `<aside class="fsw-panel"><form data-fsw-customer-form><header><div><span>NEW CUSTOMER</span><h2>Add billing customer</h2></div><button type="button" data-fsw-close>×</button></header><label>Customer name<input name="name" required></label><label>Accounts email<input name="email" type="email"></label><div class="fsw-two"><label>Tax ID<input name="tax_id"></label><label>Payment terms (days)<input name="payment_terms_days" type="number" min="0" max="365" value="14"></label></div><label>Billing address<textarea name="billing_address" rows="3"></textarea></label><label>Existing Xero customer (optional)<select name="xero_contact_id"><option value="">Link later</option>${contacts().map((row) => `<option value="${esc(row.ContactID || row.contact_id)}">${esc(row.Name || row.name || 'Xero contact')}</option>`).join('')}</select></label><label>Created by<select name="person_id" required><option value="">Select authorised person</option>${personOptions()}</select></label><footer><button type="button" data-fsw-close>Cancel</button><button class="primary" type="submit">Add customer</button></footer></form></aside>`;
    if (state.panel === 'invoice') return `<aside class="fsw-panel"><form data-fsw-invoice-form><header><div><span>SALES INVOICE</span><h2>Prepare exact invoice</h2><p>The balanced receivables entry is created at the same time.</p></div><button type="button" data-fsw-close>×</button></header><label>Customer<select name="customer_id" required><option value="">Select customer</option>${(state.catalog?.customers || []).map((row) => `<option value="${esc(row.customer_id)}">${esc(row.name)}</option>`).join('')}</select></label><label>Product or service<select name="offering_id" required><option value="">Select offering</option>${(state.catalog?.offerings || []).map((row) => `<option value="${esc(row.id)}" data-price="${Number(row.price || row.rate || 0)}">${esc(row.name)} · ${money(row.price || row.rate || 0, state.catalog.currency)}</option>`).join('')}</select></label><div class="fsw-two"><label>Quantity<input name="quantity" type="number" min="0.01" step="0.01" value="1" required></label><label>Unit price<input name="unit_amount" type="number" min="0" step="0.01" required></label></div><div class="fsw-two"><label>Issue date<input name="issue_date" type="date" required></label><label>Due date<input name="due_date" type="date"></label></div><div class="fsw-two"><label>Sales tax %<input name="tax_rate" type="number" min="0" step="0.01" value="21"></label><label>Revenue account<input name="account_code" value="200" required></label></div><label>Reference<input name="reference" placeholder="Order, project or customer reference"></label><label>Prepared by<select name="person_id" required><option value="">Select authorised person</option>${personOptions()}</select></label><footer><button type="button" data-fsw-close>Cancel</button><button class="primary" type="submit">Prepare invoice</button></footer></form></aside>`;
    return '';
  }

  function markup() {
    const summary = state.catalog?.summary || {};
    const month = state.monthEnd;
    return `<section class="fsw-shell" data-aion-finance-sales><header><div><span>QUOTE · INVOICE · COLLECT · CONTROL</span><h2>Sales, receivables & month-end</h2><p>Turn the operating model into controlled customer invoices, collection drafts and Boardroom-visible receivables.</p></div><b>${state.busy ? 'WORKING…' : 'PROVIDER-NEUTRAL'}</b></header>${state.error ? `<div class="fsw-alert error">${esc(state.error)}</div>` : ''}${state.message ? `<div class="fsw-alert good">${esc(state.message)}</div>` : ''}<div class="fsw-metrics"><article><strong>${Number(summary.invoice_count || 0)}</strong><span>Invoices</span></article><article><strong>${money(summary.outstanding, state.catalog?.currency)}</strong><span>Outstanding</span></article><article><strong>${money(summary.overdue, state.catalog?.currency)}</strong><span>Overdue</span></article><article><strong>${Number(summary.reminder_drafts || 0)}</strong><span>Reminder drafts</span></article></div><nav><label>Acting as <select data-fsw-actor><option value="">Select authorised person</option>${people().map((row) => `<option value="${esc(row.id)}" ${state.actorId === row.id ? 'selected' : ''}>${esc(row.name)}</option>`).join('')}</select></label><button data-fsw-customer>+ Customer</button><button class="primary" data-fsw-invoice ${state.catalog?.customers?.length ? '' : 'disabled'}>+ Prepare invoice</button></nav><div class="fsw-body">${invoiceRows()}<section class="fsw-month"><div><span>MONTH-END CONTROL</span><h3>${month ? esc(text(month.status)) : 'Not evaluated'}</h3><p>${month ? `${month.blocker_count} blocker(s) · ${month.warning_count} warning(s). No period was closed.` : 'Check source reports, inbox exceptions, mappings, bank evidence, receivables and provider verification.'}</p></div><button data-fsw-month-end>Evaluate current month</button></section></div>${panel()}</section>`;
  }

  function render() {
    const anchor = inbox(); if (!anchor || !state.catalog) return;
    const existing = document.querySelector('[data-aion-finance-sales]');
    if (existing) existing.outerHTML = markup(); else anchor.insertAdjacentHTML('afterend', markup());
  }

  async function load() {
    const id = businessId(); if (!id || !inbox()) return;
    state.workspaceId = id; state.error = '';
    try {
      const [catalog, exportsResult, month] = await Promise.all([
        request(`/api/aion/finance-sales/${encodeURIComponent(id)}`),
        request(`/api/aion/integrations/xero/${encodeURIComponent(id)}/sales-invoice-exports`),
        request(`/api/aion/finance-sales/${encodeURIComponent(id)}/month-end`),
      ]);
      state.catalog = catalog; state.exports = exportsResult.exports || []; state.monthEnd = month.month_end || null; render();
    } catch (error) { state.error = `Sales workspace could not load: ${error.message}`; if (state.catalog) render(); }
  }

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-aion-finance-sales] button'); if (!button) return;
    if (button.hasAttribute('data-fsw-close')) { state.panel = null; render(); return; }
    if (button.hasAttribute('data-fsw-customer')) { state.panel = 'customer'; render(); return; }
    if (button.hasAttribute('data-fsw-invoice')) { state.panel = 'invoice'; render(); setTimeout(() => { const form = document.querySelector('[data-fsw-invoice-form]'); if (form) form.issue_date.value = new Date().toISOString().slice(0, 10); }, 0); return; }
    const person = state.actorId; if (!person) { state.error = 'Select the authorised person acting on this Finance task'; render(); return; } if (state.busy) return;
    state.busy = true; state.error = ''; state.message = ''; render();
    try {
      if (button.dataset.fswApprove) {
        const row = state.catalog.invoices.find((item) => item.invoice_id === button.dataset.fswApprove);
        await request(`/api/aion/finance-sales/${encodeURIComponent(state.workspaceId)}/invoices/${encodeURIComponent(row.invoice_id)}/approve`, { method: 'POST', body: JSON.stringify({ approved_by_person_id: person, approved_invoice_hash: row.invoice_hash }) }); state.message = 'Exact invoice approved. No external write occurred.';
      } else if (button.dataset.fswPost) {
        await request(`/api/aion/finance-sales/${encodeURIComponent(state.workspaceId)}/invoices/${encodeURIComponent(button.dataset.fswPost)}/post-internal`, { method: 'POST', body: JSON.stringify({ posted_by_person_id: person }) }); state.message = 'Receivables entry posted internally and sent to Boardroom context.';
      } else if (button.dataset.fswPrepareXero) {
        const invoice = state.catalog.invoices.find((row) => row.invoice_id === button.dataset.fswPrepareXero);
        const customer = state.catalog.customers.find((row) => row.customer_id === invoice.customer_id);
        const contactId = customer?.provider_links?.xero?.contact_id;
        if (!contactId) throw new Error('Link this customer to the matching Xero contact first');
        await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/sales-invoice-exports/prepare`, { method: 'POST', body: JSON.stringify({ invoice_id: invoice.invoice_id, xero_contact_id: contactId, target_status: 'DRAFT', prepared_by_person_id: person }) }); state.message = 'Xero draft prepared. It has not been sent.';
      } else if (button.dataset.fswApproveXero) {
        const record = state.exports.find((row) => row.export_id === button.dataset.fswApproveXero);
        await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/sales-invoice-exports/${encodeURIComponent(record.export_id)}/approve`, { method: 'POST', body: JSON.stringify({ approved_by_person_id: person, approved_payload_hash: record.approval_hash }) }); state.message = 'Exact Xero payload approved. No provider write yet.';
      } else if (button.dataset.fswExecuteXero) {
        await request(`/api/aion/integrations/xero/${encodeURIComponent(state.workspaceId)}/sales-invoice-exports/${encodeURIComponent(button.dataset.fswExecuteXero)}/execute`, { method: 'POST', body: JSON.stringify({ executed_by_person_id: person }) }); state.message = 'Xero sales invoice created and independently verified by read-back.';
      } else if (button.dataset.fswReminder) {
        await request(`/api/aion/finance-sales/${encodeURIComponent(state.workspaceId)}/invoices/${encodeURIComponent(button.dataset.fswReminder)}/reminders/prepare`, { method: 'POST', body: JSON.stringify({ tone: 'friendly', prepared_by_person_id: person }) }); state.message = 'Reminder drafted only. Nothing was sent.';
      } else if (button.hasAttribute('data-fsw-month-end')) {
        const now = new Date(); const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);
        await request(`/api/aion/finance-sales/${encodeURIComponent(state.workspaceId)}/month-end/evaluate`, { method: 'POST', body: JSON.stringify({ period_end: end, prepared_by_person_id: person }) }); state.message = 'Month-end readiness checked. No period was closed and no tax was filed.';
      }
      await load();
    } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
  });

  document.addEventListener('change', (event) => {
    if (event.target.hasAttribute('data-fsw-actor')) { state.actorId = event.target.value; return; }
    if (event.target.name !== 'offering_id') return;
    const option = event.target.selectedOptions[0]; const form = event.target.form;
    if (option && form) form.unit_amount.value = option.dataset.price || '';
  });

  document.addEventListener('submit', async (event) => {
    const form = event.target; if (!form.closest('[data-aion-finance-sales]')) return;
    event.preventDefault(); if (state.busy) return; state.busy = true; state.error = ''; render();
    try {
      const value = formValues(form);
      if (form.matches('[data-fsw-customer-form]')) {
        const result = await request(`/api/aion/finance-sales/${encodeURIComponent(state.workspaceId)}/customers`, { method: 'POST', body: JSON.stringify({ name: value.name, email: value.email || null, tax_id: value.tax_id || null, billing_address: value.billing_address || null, payment_terms_days: Number(value.payment_terms_days), created_by_person_id: value.person_id }) });
        if (value.xero_contact_id) await request(`/api/aion/finance-sales/${encodeURIComponent(state.workspaceId)}/customers/${encodeURIComponent(result.customer.customer_id)}/provider-link`, { method: 'POST', body: JSON.stringify({ provider: 'xero', provider_contact_id: value.xero_contact_id, linked_by_person_id: value.person_id }) });
      }
      else await request(`/api/aion/finance-sales/${encodeURIComponent(state.workspaceId)}/invoices/prepare`, { method: 'POST', body: JSON.stringify({ customer_id: value.customer_id, issue_date: value.issue_date, due_date: value.due_date || null, currency: state.catalog.currency, reference: value.reference || null, prepared_by_person_id: value.person_id, lines: [{ offering_id: value.offering_id, quantity: Number(value.quantity), unit_amount: Number(value.unit_amount), tax_rate: Number(value.tax_rate), account_code: value.account_code, account_name: 'Sales', tax_type: Number(value.tax_rate) ? 'OUTPUT' : 'NONE' }] }) });
      state.message = form.matches('[data-fsw-customer-form]') ? 'Customer added to the provider-neutral ledger.' : 'Balanced sales invoice prepared. Exact approval is still required.'; state.panel = null; await load();
    } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
  });

  function installStyles() {
    if (document.getElementById('aion-finance-sales-styles')) return;
    const style = document.createElement('style'); style.id = 'aion-finance-sales-styles'; style.textContent = `.fsw-shell{--ink:#102a43;--muted:#52677e;--line:#cbd9e6;--green:#15803d;box-sizing:border-box;background:#fff;color:var(--ink);border:2px solid #0ea5e9;margin:0 0 22px;font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}.fsw-shell *{box-sizing:border-box}.fsw-shell>header{display:flex;justify-content:space-between;gap:20px;padding:20px 22px;border-bottom:1px solid var(--line)}.fsw-shell>header span,.fsw-month span,.fsw-panel header span{color:#0f766e;font-size:10px;font-weight:900;letter-spacing:.2em}.fsw-shell h2{margin:5px 0!important;font-size:25px!important}.fsw-shell h3{margin:5px 0!important}.fsw-shell p{margin:0!important;color:var(--muted)!important}.fsw-shell button{background:#fff!important;color:#075985!important;border:1px solid #8fb3c7!important;padding:9px 12px!important;font-weight:800!important;cursor:pointer}.fsw-shell button.primary{background:var(--green)!important;color:#fff!important;border-color:var(--green)!important}.fsw-shell button:disabled{opacity:.45}.fsw-shell>nav{display:flex;justify-content:flex-end;align-items:end;gap:8px;padding:12px 18px;border-bottom:1px solid var(--line)}.fsw-shell>nav label{display:grid;gap:3px;margin-right:auto;font-size:9px;font-weight:900}.fsw-shell>nav select{background:#fff;color:var(--ink);border:1px solid #94a3b8;padding:8px}.fsw-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:14px 18px;background:#f8fafc}.fsw-metrics article{border:1px solid var(--line);background:#fff;padding:12px}.fsw-metrics strong,.fsw-metrics span{display:block}.fsw-metrics strong{font-size:19px}.fsw-metrics span{font-size:10px;color:#64748b}.fsw-body{padding:18px}.fsw-list{display:grid;gap:9px}.fsw-list article{display:grid;grid-template-columns:1fr auto;gap:10px;border:1px solid var(--line);border-left:4px solid #0ea5e9;padding:13px}.fsw-list article span,.fsw-list article small{display:block;color:#64748b;font-size:10px}.fsw-value{text-align:right}.fsw-actions{grid-column:1/-1;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.fsw-good{color:#166534!important;font-weight:900}.fsw-empty{padding:24px;text-align:center;border:1px dashed #7dd3fc;background:#f0f9ff}.fsw-month{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-top:16px;padding:15px;border-left:4px solid #f59e0b;background:#fffbeb}.fsw-alert{margin:12px 18px 0;padding:10px;border-left:4px solid}.fsw-alert.error{background:#fef2f2;border-color:#dc2626}.fsw-alert.good{background:#ecfdf5;border-color:#16a34a}.fsw-panel{position:fixed;z-index:11500;inset:0 0 0 auto;width:min(600px,97vw);overflow:auto;background:#fff;box-shadow:-20px 0 60px rgba(15,23,42,.28)}.fsw-panel form{display:grid;gap:14px;padding:24px}.fsw-panel header{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:13px}.fsw-panel label{display:grid;gap:5px;font-size:10px;font-weight:900}.fsw-panel input,.fsw-panel select,.fsw-panel textarea{width:100%;background:#fff!important;color:var(--ink)!important;border:1px solid #94a3b8!important;padding:10px}.fsw-panel footer{display:flex;justify-content:flex-end;gap:8px;border-top:1px solid var(--line);padding-top:13px}.fsw-two{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:800px){.fsw-metrics{grid-template-columns:1fr 1fr}.fsw-month,.fsw-shell>header{display:block}.fsw-month button{margin-top:10px}.fsw-two{grid-template-columns:1fr}}`;
    document.head.appendChild(style);
  }

  function schedule() { if (scheduled) return; scheduled = true; requestAnimationFrame(() => { scheduled = false; const id = businessId(); if (!inbox() || !id) return; if (state.workspaceId !== id || !state.catalog) load(); else if (!document.querySelector('[data-aion-finance-sales]')) render(); }); }
  installStyles(); new MutationObserver(schedule).observe(document.getElementById('app') || document.body, { childList: true, subtree: true }); schedule();
  global.AionFinanceSales = { state, load, render };
})(window);
