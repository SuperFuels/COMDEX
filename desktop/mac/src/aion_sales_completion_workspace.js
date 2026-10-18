(function installSalesCompletionWorkspace(global) {
  'use strict';
  const API = 'http://127.0.0.1:8080';
  const state = { workspaceId: '', data: null, busy: false, error: '', message: '' };
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const label = (v) => String(v || '').replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const businessId = () => global.AionBusinessContainerClient?.resolveBusinessId?.() || '';
  const host = () => document.querySelector('[data-aion-sales-revenue]:not([data-srw-customer-page])');
  const salesData = () => global.AionSalesRevenue?.state?.data || {};
  const actor = () => global.AionSalesRevenue?.state?.actorId || '';
  const options = () => (salesData().opportunities || []).filter((x) => !['lost'].includes(x.stage)).map((x) =>
    `<option value="${esc(x.opportunity_id)}">${esc(x.contact?.name || 'Customer')} · ${esc(x.title)} · ${esc(label(x.stage))}</option>`).join('');
  async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, { ...options, headers: { Accept: 'application/json', ...(options.body ? {'Content-Type':'application/json'} : {}) } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(String(body.detail || body.error || `Request failed ${response.status}`).replaceAll('_', ' '));
    return body;
  }
  const metric = (v, name, note) => `<article><strong>${esc(v)}</strong><b>${esc(name)}</b><small>${esc(note)}</small></article>`;
  function readiness() {
    const r = state.data?.external_readiness || {};
    return Object.entries(r).map(([key, value]) => {
      const status = value.auth_status || value.connector_health || value.mode || (value.configured ? 'configured' : 'configuration_required');
      return `<li><b>${esc(label(key))}</b><span>${esc(label(status))}</span></li>`;
    }).join('');
  }
  function approvals() {
    const quotes = state.data?.quotes || []; const bookings = state.data?.bookings || []; const messages = state.data?.messages || [];
    const rows = [
      ...quotes.filter((x) => x.status === 'exact_approval_required').map((x) => ({kind:'quote', id:x.quote_id, hash:x.quote_hash, title:`Quote €${x.total.toFixed(2)} · ${x.customer?.name || 'Customer'}`})),
      ...bookings.filter((x) => x.status === 'exact_approval_required').map((x) => ({kind:'booking', id:x.booking_id, hash:x.booking_hash, title:`Booking ${new Date(x.starts_at).toLocaleString()} · ${x.customer?.name || 'Customer'}`})),
      ...messages.filter((x) => x.status === 'exact_approval_required').map((x) => ({kind:'message', id:x.message_id, hash:x.message_hash, title:`${label(x.payload?.channel)} · ${x.payload?.to}`})),
    ];
    if (!rows.length) return '<p class="scc-empty">No exact approvals waiting.</p>';
    return rows.map((x) => `<article><b>${esc(x.title)}</b><small>${esc(label(x.kind))} · exact payload locked</small><button data-scc-approve="${esc(x.kind)}" data-id="${esc(x.id)}" data-hash="${esc(x.hash)}">Approve exact ${esc(x.kind)}</button></article>`).join('');
  }
  function executableMessages() {
    const rows = (state.data?.messages || []).filter((x) => x.status === 'approved_not_sent');
    if (!rows.length) return '<p class="scc-empty">Approved email drafts appear here. SMS remains unavailable until a provider is configured.</p>';
    const smsReady = state.data?.external_readiness?.sms?.live_send_enabled === true;
    return rows.map((x) => `<article><b>${esc(label(x.payload?.channel))} · ${esc(x.payload?.to)}</b><small>Approved exact payload · not sent</small>${x.payload?.channel === 'email' ? `<button data-scc-execute-message="${esc(x.message_id)}" data-hash="${esc(x.message_hash)}">Create Gmail draft</button>` : smsReady ? `<button data-scc-execute-message="${esc(x.message_id)}" data-hash="${esc(x.message_hash)}">Send approved SMS</button>` : '<small>Live SMS sending is not enabled.</small>'}</article>`).join('');
  }
  function executableBookings() {
    const rows = (state.data?.bookings || []).filter((x) => x.status === 'confirmed_internal');
    if (!rows.length) return '<p class="scc-empty">Approved bookings appear here.</p>';
    return rows.map((x) => `<article><b>${esc(new Date(x.starts_at).toLocaleString())} · ${esc(x.customer?.name || 'Customer')}</b><small>Internally confirmed · customer not notified</small><button data-scc-execute-booking="${esc(x.booking_id)}" data-hash="${esc(x.booking_hash)}">Add to Google Calendar</button></article>`).join('');
  }
  function acceptedQuotes() {
    const rows = (state.data?.quotes || []).filter((x) => x.status === 'approved_not_sent' || x.status === 'accepted_by_customer');
    return rows.map((x) => `<article><b>${esc(x.customer?.name || 'Customer')} · €${Number(x.total || 0).toFixed(2)}</b><small>${esc(label(x.status))}</small>${x.status === 'approved_not_sent' ? `<form data-scc-form="accept"><input type="hidden" name="quote_id" value="${esc(x.quote_id)}"><input name="evidence_reference" placeholder="Customer email, signed quote or call reference" required><button>Record customer acceptance</button></form>` : `<button data-scc-handoffs="${esc(x.quote_id)}">Create Operations + Finance handoffs</button>`}</article>`).join('') || '<p class="scc-empty">Approved and accepted quotes appear here.</p>';
  }
  function markup() {
    const s = state.data?.summary || {};
    return `<section class="scc-shell" data-sales-completion><header><div><span>LEAD → REVENUE CONTROL</span><h2>Bookings, quotes and delivery</h2><p>Turn qualified demand into approved work, Finance records and measurable outcomes.</p></div><b>${state.busy ? 'WORKING…' : 'GOVERNED EXECUTION'}</b></header>${state.error ? `<div class="scc-alert error">${esc(state.error)}</div>` : ''}${state.message ? `<div class="scc-alert good">${esc(state.message)}</div>` : ''}<div class="scc-metrics">${metric(s.confirmed_bookings || 0,'Confirmed bookings','Internal authority')}${metric(s.accepted_quotes || 0,'Accepted quotes','Customer evidence')}${metric(s.operations_handoffs || 0,'Operations handoffs','Delivery ready')}${metric(`€${Number(s.won_value || 0).toFixed(2)}`,'Verified won value','Outcome authority')}</div><div class="scc-grid"><section><h3>Create commercial work</h3><form data-scc-form="booking"><label>Opportunity<select name="opportunity_id" required><option value="">Choose qualified lead</option>${options()}</select></label><div><label>Date and time<input type="datetime-local" name="starts_at" required></label><label>Minutes<input type="number" name="duration_minutes" value="30" min="10" max="480"></label></div><label>Channel or location<input name="channel" value="Site visit"></label><button>Prepare booking</button></form><form data-scc-form="quote"><label>Opportunity<select name="opportunity_id" required><option value="">Choose lead</option>${options()}</select></label><label>Description<input name="description" placeholder="Scope of work" required></label><div><label>Net price (€)<input type="number" step="0.01" min="0" name="unit_amount" required></label><label>Tax %<input type="number" step="0.01" min="0" name="tax_rate" value="21"></label></div><label>Terms<input name="terms" value="Scope changes require a revised written quote."></label><button>Prepare quote</button></form><form data-scc-form="message"><label>Opportunity<select name="opportunity_id" required><option value="">Choose customer</option>${options()}</select></label><div><label>Channel<select name="channel"><option value="email">Email</option><option value="sms">SMS</option></select></label><label>Subject<input name="subject" value="Your Home Fixed enquiry"></label></div><label>Approved follow-up text<textarea name="body" required></textarea></label><button>Prepare communication</button></form></section><section><h3>Exact approvals</h3><div class="scc-list">${approvals()}</div><h3>Approved external work</h3><div class="scc-list">${executableBookings()}${executableMessages()}</div><h3>Acceptance and handoff</h3><div class="scc-list">${acceptedQuotes()}</div></section><aside><h3>External readiness</h3><ul>${readiness()}</ul><p>Gmail execution creates a draft only. Calendar execution adds the approved internal booking without notifying guests. SMS and calling remain closed until their provider accounts are connected and independently enabled.</p></aside></div></section>`;
  }
  function render() {
    const anchor = host(); if (!anchor || !state.data) return;
    const current = anchor.querySelector('[data-sales-completion]');
    if (current) current.outerHTML = markup(); else anchor.insertAdjacentHTML('beforeend', markup());
  }
  async function load() {
    const id = businessId(); if (!id || !host()) return;
    state.workspaceId = id;
    try { state.data = await request(`/api/aion/sales-completion/${encodeURIComponent(id)}`); state.error = ''; render(); }
    catch (error) { state.error = error.message; render(); }
  }
  async function post(path, body, message) {
    state.busy = true; state.error = ''; render();
    try { await request(path, {method:'POST', body:JSON.stringify(body)}); state.message = message; await global.AionSalesRevenue?.load?.(); await load(); }
    catch (error) { state.error = error.message; }
    finally { state.busy = false; render(); }
  }
  document.addEventListener('submit', (event) => {
    const form = event.target.closest('[data-sales-completion] form'); if (!form) return;
    event.preventDefault(); const values = Object.fromEntries(new FormData(form).entries()); const who = actor();
    if (!who) { state.error = 'Select the authorised acting person at the top of Sales first.'; render(); return; }
    const base = `/api/aion/sales-completion/${encodeURIComponent(state.workspaceId)}`;
    if (form.dataset.sccForm === 'booking') {
      const local = new Date(values.starts_at); return post(`${base}/opportunities/${encodeURIComponent(values.opportunity_id)}/bookings`, {starts_at:local.toISOString(),duration_minutes:Number(values.duration_minutes),assigned_person_id:who,channel:values.channel,prepared_by_person_id:who}, 'Booking prepared for exact approval.');
    }
    if (form.dataset.sccForm === 'quote') return post(`${base}/opportunities/${encodeURIComponent(values.opportunity_id)}/quotes`, {lines:[{description:values.description,quantity:1,unit_amount:Number(values.unit_amount),tax_rate:Number(values.tax_rate)}],valid_days:14,terms:values.terms,prepared_by_person_id:who}, 'Quote prepared for exact approval.');
    if (form.dataset.sccForm === 'message') return post(`${base}/opportunities/${encodeURIComponent(values.opportunity_id)}/messages`, {channel:values.channel,purpose:'follow_up',subject:values.subject||null,body:values.body,prepared_by_person_id:who}, 'Communication prepared; nothing sent.');
    if (form.dataset.sccForm === 'accept') return post(`${base}/quotes/${encodeURIComponent(values.quote_id)}/acceptance`, {evidence_reference:values.evidence_reference,recorded_by_person_id:who}, 'Customer acceptance evidence recorded.');
  });
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-sales-completion] button'); if (!button || button.closest('form')) return;
    const who = actor(); if (!who) { state.error = 'Select the authorised acting person at the top of Sales first.'; render(); return; }
    const base = `/api/aion/sales-completion/${encodeURIComponent(state.workspaceId)}`;
    if (button.dataset.sccApprove) return post(`${base}/${button.dataset.sccApprove}s/${encodeURIComponent(button.dataset.id)}/approve`, {expected_hash:button.dataset.hash,approved_by_person_id:who}, `Exact ${button.dataset.sccApprove} approved.`);
    if (button.dataset.sccExecuteMessage) return post(`${base}/messages/${encodeURIComponent(button.dataset.sccExecuteMessage)}/execute`, {expected_hash:button.dataset.hash,approved_by_person_id:who}, 'Gmail draft created. It has not been sent.');
    if (button.dataset.sccExecuteBooking) return post(`${base}/bookings/${encodeURIComponent(button.dataset.sccExecuteBooking)}/execute`, {expected_hash:button.dataset.hash,approved_by_person_id:who}, 'Google Calendar event created. The customer has not been notified.');
    if (button.dataset.sccHandoffs) return post(`${base}/quotes/${encodeURIComponent(button.dataset.sccHandoffs)}/handoffs`, {operations_owner_person_id:who,created_by_person_id:who}, 'Operations job and Finance invoice draft created.');
  });
  document.getElementById('aion-sales-completion-styles')?.remove();
  const style = document.createElement('style'); style.textContent = `.scc-shell{margin:18px;border:1px solid #bfd3df;border-top:5px solid #15803d;background:#fff;color:#102a43;font:14px Inter,system-ui,sans-serif}.scc-shell *{box-sizing:border-box}.scc-shell>header{padding:18px;display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid #d7e2ea}.scc-shell>header span{font-size:10px;letter-spacing:.2em;color:#0f766e;font-weight:900}.scc-shell h2,.scc-shell h3{margin:5px 0!important}.scc-shell p,.scc-shell small{color:#60758a!important}.scc-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:12px;background:#f8fafc}.scc-metrics article{padding:10px;border:1px solid #d7e2ea}.scc-metrics strong,.scc-metrics b,.scc-metrics small{display:block}.scc-grid{display:grid;grid-template-columns:1fr 1fr .65fr;gap:12px;padding:16px}.scc-grid>section,.scc-grid>aside{border:1px solid #d7e2ea;padding:13px}.scc-shell form{display:grid;gap:8px;padding:11px;margin:8px 0;background:#f8fafc;border-left:3px solid #0ea5e9}.scc-shell form>div{display:grid;grid-template-columns:1fr 1fr;gap:8px}.scc-shell label{display:grid;gap:4px;font-size:10px;font-weight:800}.scc-shell input,.scc-shell select,.scc-shell textarea{padding:8px;background:#fff!important;color:#102a43!important;border:1px solid #94a3b8!important}.scc-shell button{padding:8px 10px!important;border:1px solid #15803d!important;background:#15803d!important;color:#fff!important;font-weight:800!important;cursor:pointer}.scc-list{display:grid;gap:7px}.scc-list>article{display:grid;gap:5px;padding:9px;border:1px solid #d7e2ea}.scc-list form{margin:2px 0}.scc-grid aside ul{list-style:none;padding:0}.scc-grid aside li{display:flex;justify-content:space-between;gap:8px;padding:8px 0;border-bottom:1px solid #d7e2ea}.scc-alert{margin:10px 16px;padding:10px;border-left:4px solid}.scc-alert.error{border-color:#dc2626;background:#fef2f2}.scc-alert.good{border-color:#16a34a;background:#ecfdf5}.scc-empty{padding:10px;border:1px dashed #94a3b8}@media(max-width:1000px){.scc-grid{grid-template-columns:1fr}.scc-metrics{grid-template-columns:1fr 1fr}}`; document.head.appendChild(style);
  style.id = 'aion-sales-completion-styles';
  style.textContent += '.scc-shell{box-sizing:border-box;width:calc(100% - 36px);max-width:calc(100% - 36px);min-width:0;overflow-x:clip;container-type:inline-size}.scc-shell>*,.scc-metrics,.scc-grid,.scc-grid>section,.scc-grid>aside,.scc-shell form,.scc-shell form>div,.scc-shell label,.scc-list,.scc-list>article{max-width:100%;min-width:0}.scc-metrics{grid-template-columns:repeat(auto-fit,minmax(min(160px,100%),1fr))}.scc-grid{grid-template-columns:repeat(auto-fit,minmax(min(360px,100%),1fr))}.scc-shell form>div{grid-template-columns:repeat(2,minmax(0,1fr))}.scc-shell input,.scc-shell select,.scc-shell textarea,.scc-shell button{width:100%;max-width:100%;min-width:0}.scc-shell p,.scc-shell small,.scc-shell b,.scc-shell span{overflow-wrap:anywhere}@container(max-width:560px){.scc-shell>header{flex-wrap:wrap}.scc-shell form>div{grid-template-columns:1fr}}';
  new MutationObserver(() => { if (host() && !document.querySelector('[data-sales-completion]')) load(); }).observe(document.getElementById('app') || document.body,{childList:true,subtree:true});
  global.setInterval(() => { if (host() && (!state.data || state.workspaceId !== businessId())) load(); }, 2500);
  global.AionSalesCompletion = {state,load,render};
})(window);
