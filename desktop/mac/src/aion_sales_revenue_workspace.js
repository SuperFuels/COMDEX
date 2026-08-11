(function installAionSalesRevenueWorkspace(global) {
  'use strict';

  const API = 'http://127.0.0.1:8080';
  const state = { workspaceId: '', data: null, actorId: '', panel: null, selectedId: '', busy: false, loading: false, error: '', message: '', intakeToken: '' };
  let scheduled = false;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const label = (value) => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
  const businessId = () => global.AionBusinessContainerClient?.resolveBusinessId?.() || '';
  const mount = () => document.querySelector(
    '[data-aion-sales-revenue-mount="true"], ' +
    '[data-aion-sales-live-agents-workspace-o14d="true"], ' +
    '[data-aion-shared-department-pilot="true"][data-aion-shared-department="sales"]',
  );
  const selected = () => (state.data?.opportunities || []).find((row) => row.opportunity_id === state.selectedId);
  const actors = () => state.data?.actors || [];
  const actorOptions = (selectedId = '') => actors().map((row) => `<option value="${esc(row.person_id)}" ${row.person_id === selectedId ? 'selected' : ''}>${esc(row.name)}${row.position_title ? ` · ${esc(row.position_title)}` : ''}</option>`).join('');
  const values = (form) => Object.fromEntries(new FormData(form).entries());

  async function request(path, options = {}) {
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    if (options.body) headers['Content-Type'] = 'application/json';
    const controller = new AbortController();
    const timeout = global.setTimeout(() => controller.abort(), 6000);
    try {
      const response = await fetch(`${API}${path}`, { ...options, headers, signal: options.signal || controller.signal });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(String(body.detail || body.error || `Request failed ${response.status}`).replaceAll('_', ' '));
      return body;
    } finally { global.clearTimeout(timeout); }
  }

  function stageBadge(stage) {
    const attention = stage === 'human_handoff' ? ' attention' : '';
    return `<span class="srw-stage${attention}">${esc(label(stage))}</span>`;
  }

  function metric(value, text, note) {
    return `<article><strong>${esc(value)}</strong><span>${esc(text)}</span><small>${esc(note)}</small></article>`;
  }

  function todayQueue() {
    const rows = state.data?.today_queue || [];
    if (!rows.length) return '<div class="srw-empty"><b>No open Sales work</b><p>New Marketing enquiries and manually added leads will appear here.</p></div>';
    return `<div class="srw-queue">${rows.map((row) => `<button data-srw-open="${esc(row.opportunity_id)}"><span>${stageBadge(row.stage)} ${esc(row.next_action)}</span><b>${esc(row.contact?.name || row.title)}</b><small>${esc(row.title)}</small></button>`).join('')}</div>`;
  }

  function pipeline() {
    const rows = state.data?.opportunities || [];
    const stages = ['new', 'contacted', 'qualification', 'qualified', 'appointment_proposed', 'appointment_booked', 'human_handoff', 'proposal', 'won', 'lost'];
    return `<div class="srw-pipeline">${stages.map((stage) => {
      const items = rows.filter((row) => row.stage === stage);
      return `<section><header><b>${esc(label(stage))}</b><span>${items.length}</span></header>${items.length ? items.map((row) => `<button data-srw-open="${esc(row.opportunity_id)}"><b>${esc(row.contact?.name || 'Lead')}</b><span>${esc(row.title)}</span><small>${esc(row.source)} · ${esc(row.qualification?.score || 0)}% qualified</small></button>`).join('') : '<p>Empty</p>'}</section>`;
    }).join('')}</div>`;
  }

  function playbook() {
    const row = state.data?.playbook || {};
    const setup = row.agent_setup || {};
    const passed = Boolean(row.simulation?.all_passed);
    return `<section class="srw-studio"><div><span>SALES AGENT STUDIO</span><h3>${esc(row.name || 'Sales agent')}</h3><p>${esc(label(setup.business_motion || 'inbound'))} · ${esc(label(setup.lead_temperature || 'warm'))} leads · close for ${esc(label(setup.close_strategy || 'human review'))}</p><div class="srw-actions"><button class="primary" data-srw-agent-setup>Configure agent job</button><button data-srw-simulate>Run 11 executable safety scenarios</button>${passed && row.status !== 'promoted_for_controlled_use' ? '<button class="primary" data-srw-promote>Promote this exact version</button>' : ''}</div></div><div class="srw-studio-status"><b>${esc(label(row.status || 'not configured'))}</b><small>${Number(row.simulation?.passed || 0)}/${Number(row.simulation?.required || 0)} safety simulations passed</small><small>Version ${Number(row.version || 1)} · ${row.external_deployment_performed ? 'externally deployed' : 'no external deployment'}</small></div><details><summary>Goals, permitted actions and boundaries</summary><div class="srw-studio-grid"><div><b>Required call outcomes</b>${(setup.required_fields || []).map((item) => `<p>● ${esc(label(item))}</p>`).join('')}<b>Permitted actions</b>${(setup.allowed_actions || []).map((item) => `<p>✓ ${esc(label(item))}</p>`).join('')}</div><div><b>Non-negotiable boundaries</b>${(row.guardrails || []).map((item) => `<p>✓ ${esc(item)}</p>`).join('')}<p>Payments mean a separately approved payment link—never card details spoken to the agent.</p></div></div></details></section>`;
  }

  function intake() {
    const intake = state.data?.intake || {}; const website = intake.website || {}; const gmail = intake.gmail || {};
    const gmailReady = gmail.status === 'real_readonly_import_ready';
    const endpointRows = (website.endpoints || []).map((row) => `<div class="srw-endpoint"><b>${esc(row.name)}</b><code>${esc(row.receiver_path)}</code><small>${Number(row.accepted || 0)} accepted · ${esc(label(row.status))}</small></div>`).join('');
    return `<section class="srw-capabilities"><article><span>GENUINE MARKETING INTAKE</span><h3>HomeFixed website + agents</h3><b>${esc(label(website.status))}</b><p>Human forms and authorised external agents enter one private, durable queue, then become deduplicated Tessaris opportunities.</p><small>${(website.endpoints || []).length} secured endpoint${(website.endpoints || []).length === 1 ? '' : 's'} · enquiries remain queued while this Mac is offline</small>${endpointRows}<div class="srw-actions"><button class="primary" data-srw-homefixed-poll>Import HomeFixed queue</button><button data-srw-create-intake>Create secured endpoint</button></div>${state.intakeToken ? `<div class="srw-token"><b>Copy this token now</b><code>${esc(state.intakeToken)}</code><small>Send it as X-Tessaris-Intake-Key. Only its digest is stored.</small></div>` : ''}</article><article><span>READ-ONLY GMAIL</span><h3>Real email enquiries</h3><b>${esc(label(gmail.status))}</b><p>Reads only a narrow enquiry query, creates deduplicated opportunities and leaves Gmail untouched.</p><small>${gmailReady ? 'No reply, label, read-state or deletion is performed.' : 'Reconnect Gmail in Connections before importing enquiries.'}</small><div class="srw-actions"><button data-srw-gmail-poll ${gmailReady ? '' : 'disabled'}>Import matching enquiries now</button></div></article></section>`;
  }

  function liveConsole() {
    const tel = state.data?.telephony || {}; const drafts = tel.call_drafts || []; const events = tel.events || [];
    return `<section class="srw-console"><header><div><span>LIVE CALL CONSOLE</span><h3>Supervised conversations</h3><p>Every production call is bound to a promoted agent, a customer record, consent and an exact human-approved draft.</p><div class="srw-actions"><button data-srw-retell-sync ${tel.agent_configured ? '' : 'disabled'}>Sync verified Retell outcomes</button></div></div><div><b>${esc(label(tel.status))}</b><small>${Number(tel.active_calls || 0)} active · ${drafts.length} prepared</small></div></header><div class="srw-console-grid"><div><b>Call control</b>${drafts.length ? drafts.slice(0, 5).map((row) => `<article><span>${esc(row.customer_name || row.to_number)}</span><small>${esc(label(row.status))} · ${esc(row.reason)}</small><div class="srw-actions">${row.status === 'exact_approval_required' ? `<button data-srw-approve-call="${esc(row.draft_id)}" data-srw-hash="${esc(row.draft_hash)}">Approve exact call</button>` : ''}${row.status === 'approved_not_executed' ? `<button class="primary" data-srw-execute-call="${esc(row.draft_id)}" data-srw-hash="${esc(row.draft_hash)}" ${tel.live_execution_enabled ? '' : 'disabled'}>Start approved call</button>` : ''}</div></article>`).join('') : '<p>No calls prepared. Open an opportunity with a phone number to prepare one.</p>'}</div><div><b>Verified provider events</b>${events.length ? events.slice(0, 8).map((row) => `<article><span>${esc(label(row.event))}</span><small>${esc(row.call_id)} · ${esc(label(row.call_status || row.disconnection_reason))}</small>${(row.transcript_object || []).slice(-3).map((turn) => `<p><b>${esc(label(turn.role))}</b> ${esc(turn.content || '')}</p>`).join('')}</article>`).join('') : '<p>No verified call outcomes received.</p>'}</div></div><footer>Completed calls are read back directly from the configured Retell agent under authenticated provider access. Retell webhook signatures are replay-bounded. Live callbacks remain optional; no public website holds the Retell master credential.</footer></section>`;
  }

  function panel() {
    const row = selected();
    if (!state.panel) return '';
    const close = '<button type="button" data-srw-close aria-label="Close">×</button>';
    if (state.panel === 'enquiry') return `<aside class="srw-panel"><form data-srw-form="enquiry"><header><div><span>NEW ENQUIRY</span><h2>Add a person or Marketing lead</h2><p>The customer is deduplicated; each genuine need remains a separate opportunity.</p></div>${close}</header><div class="srw-two"><label>Name<input name="name" required></label><label>Company<input name="company_name"></label></div><div class="srw-two"><label>Email<input type="email" name="email"></label><label>Phone<input name="phone"></label></div><label>What do they need?<textarea name="enquiry" rows="4" required></textarea></label><div class="srw-two"><label>Source<select name="source"><option value="manual">Manual</option><option value="website">Website</option><option value="inbound_call">Inbound call</option><option value="inbound_email">Inbound email</option><option value="referral">Referral</option><option value="marketing_campaign">Marketing campaign</option></select></label><label>Campaign/reference<input name="source_reference"></label></div><label>Added by<select name="actor" required><option value="">Select authorised person</option>${actorOptions(state.actorId)}</select></label><footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Create enquiry</button></footer></form></aside>`;
    if (state.panel === 'agent_setup') {
      const setup = state.data?.playbook?.agent_setup || {}; const has = (name) => (setup.allowed_actions || []).includes(name); const needs = (name) => (setup.required_fields || []).includes(name);
      const option = (value, current, text) => `<option value="${value}" ${value === current ? 'selected' : ''}>${esc(text || label(value))}</option>`;
      const check = (name, value, text, selected) => `<label><input type="checkbox" name="${name}" value="${value}" ${selected ? 'checked' : ''}> ${esc(text)}</label>`;
      return `<aside class="srw-panel"><form data-srw-form="agent_setup"><header><div><span>SALES AGENT JOB</span><h2>Define what this agent must achieve</h2><p>The selected AI may converse naturally, but it cannot change these goals or permissions.</p></div>${close}</header><div class="srw-two"><label>Sales motion<select name="business_motion">${option('inbound', setup.business_motion, 'Inbound enquiries')}${option('outbound', setup.business_motion, 'Outbound prospecting')}${option('blended', setup.business_motion, 'Inbound + outbound')}</select></label><label>Lead temperature<select name="lead_temperature">${['freezing','cold','warm','hot','existing_customer'].map((value) => option(value, setup.lead_temperature)).join('')}</select></label></div><div class="srw-two"><label>Primary outcome<select name="primary_goal">${option('human_review_request', setup.primary_goal, 'Human review')}${option('human_callback_request', setup.primary_goal, 'Human callback request')}${option('site_visit_request', setup.primary_goal, 'Site visit request')}</select></label><label>Close strategy<select name="close_strategy">${['human_review','human_callback','site_visit_request','approved_booking_request','approved_payment_link_request'].map((value) => option(value, setup.close_strategy)).join('')}</select></label></div><section class="srw-checks"><b>Information the call must collect</b>${check('required_fields','customer_name','Customer name',needs('customer_name'))}${check('required_fields','work_required','Need, issue, service or product',needs('work_required'))}${check('required_fields','property_location','Town or general location',needs('property_location'))}${check('required_fields','full_property_address','Full address',needs('full_property_address'))}${check('required_fields','urgency','Urgency or required date',needs('urgency'))}${check('required_fields','immediate_safety_risk','Immediate safety risk',needs('immediate_safety_risk'))}${check('required_fields','customer_email','Email confirmed in writing',needs('customer_email'))}${check('required_fields','photos_or_documents_available','Photos or documents available',needs('photos_or_documents_available'))}${check('required_fields','preferred_follow_up_channel','Preferred follow-up channel',needs('preferred_follow_up_channel'))}${check('required_fields','preferred_follow_up_time','Preferred follow-up time',needs('preferred_follow_up_time'))}${check('required_fields','decision_authority','Decision authority',needs('decision_authority'))}${check('required_fields','budget_context','Budget context',needs('budget_context'))}</section><section class="srw-checks"><b>Actions the agent may request or prepare</b>${check('allowed_actions','collect_information','Collect information',has('collect_information'))}${check('allowed_actions','collect_email_in_writing','Confirm email in writing',has('collect_email_in_writing'))}${check('allowed_actions','request_photos','Request pictures or documents',has('request_photos'))}${check('allowed_actions','request_human_callback','Request a human callback',has('request_human_callback'))}${check('allowed_actions','request_site_visit','Request a site visit',has('request_site_visit'))}${check('allowed_actions','request_approved_booking','Request an available appointment',has('request_approved_booking'))}${check('allowed_actions','present_approved_product_options','Present approved products, services or packages',has('present_approved_product_options'))}${check('allowed_actions','send_approved_terms_link','Prepare approved terms link',has('send_approved_terms_link'))}${check('allowed_actions','send_approved_payment_link','Prepare approved first-hour or deposit payment link',has('send_approved_payment_link'))}<small>The agent never hears card details and never sends, books or charges without the relevant verified tool and authority.</small></section><div class="srw-two"><label>Opening style<select name="intro_style">${['warm_direct','permission_based','problem_first','referral_context','custom'].map((value) => option(value, setup.intro_style)).join('')}</select></label><label>Photo/document route<select name="evidence_route_mode">${option('human_follow_up_required', setup.evidence_route?.mode, 'Person confirms route')}${option('reply_to_approved_sms', setup.evidence_route?.mode, 'Reply to approved SMS')}${option('approved_email_address', setup.evidence_route?.mode, 'Approved email')}</select></label></div><label>Evidence email or reply destination<input name="evidence_route_destination" value="${esc(setup.evidence_route?.destination || '')}" placeholder="Required only for a configured route"></label><label>Custom opening line<input name="custom_intro" value="${esc(setup.custom_intro || '')}" placeholder="Optional; AI identity disclosure is always added"></label><label>Sales script and conversation guidance<textarea name="sales_script" rows="7" placeholder="How to move from opening, through discovery and approved options, to the close">${esc(setup.sales_script || '')}</textarea></label><footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Save new agent version</button></footer></form></aside>`;
    }
    if (!row) return '';
    if (state.panel === 'detail') {
      const answer = row.qualification?.answers || {};
      return `<aside class="srw-panel"><div class="srw-detail"><header><div><span>OPPORTUNITY</span><h2>${esc(row.contact?.name)}</h2><p>${esc(row.title)}</p></div>${close}</header><div class="srw-detail-status">${stageBadge(row.stage)}<span>${esc(row.contact?.email || '')}</span><span>${esc(row.contact?.phone || '')}</span></div><section><b>Enquiry</b><p>${esc(row.enquiry)}</p></section><section><b>Qualification</b><p>${Number(row.qualification?.score || 0)}% · ${esc(label(row.qualification?.status))}</p>${Object.entries(answer).filter(([key]) => key !== 'risk_flags').map(([key, value]) => `<small><b>${esc(label(key))}</b> ${esc(value)}</small>`).join('')}</section><section><b>Campaign and consent</b><p>${esc(label(row.source))} · response permission ${esc(label(row.consent?.contact_permission))}</p>${Object.entries(row.attribution || {}).map(([key, value]) => `<small><b>${esc(label(key))}</b> ${esc(value)}</small>`).join('')}<small>Outbound campaign permitted: ${row.consent?.outbound_campaign_allowed ? 'yes' : 'no'}</small></section><section><b>Activity</b>${(row.activities || []).slice().reverse().slice(0, 8).map((item) => `<small><b>${esc(label(item.kind))}</b> ${esc(new Date(item.created_at).toLocaleString())}</small>`).join('')}</section><footer class="srw-detail-actions"><button data-srw-panel="qualify">Qualify</button><button data-srw-panel="call">Log conversation</button>${row.contact?.phone ? '<button data-srw-prepare-call>Prepare production call</button>' : ''}<button data-srw-panel="appointment" ${row.stage === 'qualified' || row.stage === 'human_handoff' || row.stage === 'appointment_proposed' ? '' : 'disabled'}>Prepare appointment</button><button data-srw-panel="handoff">Human handoff</button>${row.stage === 'proposal' ? '<button class="primary" data-srw-stage="won">Mark won</button>' : ''}${row.stage !== 'won' && row.stage !== 'lost' ? '<button data-srw-stage="lost">Close lost</button>' : ''}</footer></div></aside>`;
    }
    if (state.panel === 'qualify') return `<aside class="srw-panel"><form data-srw-form="qualify"><header><div><span>QUALIFICATION</span><h2>${esc(row.contact?.name)}</h2><p>Record evidence; the score recommends workflow but never rejects the person.</p></div>${close}</header><label>What do they need?<textarea name="need" required>${esc(row.qualification?.answers?.need || '')}</textarea></label><div class="srw-two"><label>Location<input name="location" required value="${esc(row.qualification?.answers?.location || '')}"></label><label>Urgency<input name="urgency" required value="${esc(row.qualification?.answers?.urgency || '')}"></label></div><div class="srw-two"><label>Decision maker<input name="decision_maker" value="${esc(row.qualification?.answers?.decision_maker || '')}"></label><label>Budget context<input name="budget_context" value="${esc(row.qualification?.answers?.budget_context || '')}"></label></div><label>Internal notes<textarea name="notes"></textarea></label><footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Save qualification</button></footer></form></aside>`;
    if (state.panel === 'appointment') return `<aside class="srw-panel"><form data-srw-form="appointment"><header><div><span>APPOINTMENT DRAFT</span><h2>Prepare the handoff booking</h2><p>This does not write to a calendar or notify the customer.</p></div>${close}</header><label>Date and time<input type="datetime-local" name="starts_at" required></label><div class="srw-two"><label>Duration minutes<input type="number" name="duration_minutes" min="5" max="480" value="30"></label><label>Channel or location<input name="location_or_channel" value="Phone"></label></div><label>Assigned person<select name="assigned_person_id" required><option value="">Select person</option>${actorOptions(row.owner_person_id)}</select></label><label>Notes<textarea name="notes"></textarea></label><footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Prepare appointment</button></footer></form></aside>`;
    if (state.panel === 'handoff') return `<aside class="srw-panel"><form data-srw-form="handoff"><header><div><span>HUMAN HANDOFF</span><h2>Place this opportunity with a person</h2></div>${close}</header><label>Assign to<select name="assigned_person_id" required><option value="">Select person</option>${actorOptions(row.owner_person_id)}</select></label><label>Reason<textarea name="reason" required></textarea></label><label>Urgency<select name="urgency"><option>normal</option><option>priority</option><option>urgent</option></select></label><footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Create handoff</button></footer></form></aside>`;
    if (state.panel === 'call') return `<aside class="srw-panel"><form data-srw-form="call"><header><div><span>CONVERSATION EVIDENCE</span><h2>Log a call or message outcome</h2><p>The current build records the outcome. It does not initiate an external call.</p></div>${close}</header><div class="srw-two"><label>Channel<select name="channel"><option value="telephone">Telephone</option><option value="app_voice">Tessaris voice</option><option value="email">Email</option><option value="sms">SMS</option><option value="web_chat">Web chat</option><option value="manual">Manual note</option></select></label><label>Provider<select name="provider"><option value="native">Tessaris native</option><option value="retell">Retell adapter</option><option value="twilio">Twilio adapter</option><option value="manual">Manual</option></select></label></div><label><input type="checkbox" name="ai_disclosure" checked> AI identity was disclosed for a voice call</label><label>Disposition<select name="disposition"><option value="qualified">Qualified</option><option value="follow_up">Follow up</option><option value="appointment_requested">Appointment requested</option><option value="human_requested">Human requested</option><option value="not_interested">Not interested</option><option value="wrong_number">Wrong number</option></select></label><label>Conversation summary<textarea name="summary" required></textarea></label><label>Next action<input name="next_action"></label><label><input type="checkbox" name="human_takeover"> A person took over or was requested</label><footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Record outcome</button></footer></form></aside>`;
    return '';
  }

  function enhanceAgentSetupPanel(anchor) {
    const form = anchor.querySelector('form[data-srw-form="agent_setup"]');
    if (!form || form.querySelector('[data-srw-contact-sequence]')) return;
    const setup = state.data?.playbook?.agent_setup || {};
    const sequence = setup.contact_sequence || {};
    const destination = form.querySelector('input[name="evidence_route_destination"]')?.closest('label');
    if (!destination) return;
    const option = (value, current, text) => `<option value="${esc(value)}" ${String(value) === String(current) ? 'selected' : ''}>${esc(text)}</option>`;
    destination.insertAdjacentHTML('beforebegin', `<section data-srw-contact-sequence><b>Unanswered-call follow-up</b><div class="srw-two"><label>Phone attempts before written follow-up<select name="maximum_phone_attempts">${[1,2,3].map((value) => option(value, sequence.maximum_phone_attempts || 2, `${value} attempt${value === 1 ? '' : 's'}`)).join('')}</select></label><label>If unanswered, continue by<select name="fallback_channel">${option('email', sequence.fallback_channel || 'email', 'Email')}${option('sms', sequence.fallback_channel, 'SMS')}${option('whatsapp', sequence.fallback_channel, 'WhatsApp Business')}${option('none', sequence.fallback_channel, 'Human review only')}</select></label></div><label>Questions per written message<select name="questions_per_written_message">${[1,2,3].map((value) => option(value, sequence.questions_per_written_message || 2, String(value))).join('')}</select></label><small>The written conversation continues the same frozen goals and never repeats confirmed facts. Messages remain drafts until exact approval; appointments remain requests until separately confirmed.</small></section>`);
  }

  function markup() {
    const summary = state.data?.summary || {};
    return `<section class="srw-shell" data-aion-sales-revenue><header><div><span>ENQUIRY · QUALIFY · BOOK · CONVERT</span><h2>Sales Revenue Spine</h2><p>One customer and opportunity record across Marketing, conversations, Operations, Finance and the Boardroom.</p></div><b>${state.busy ? 'WORKING…' : 'PROVIDER-NEUTRAL CRM'}</b></header>${state.error ? `<div class="srw-alert error">${esc(state.error)}</div>` : ''}${state.message ? `<div class="srw-alert good">${esc(state.message)}</div>` : ''}<div class="srw-metrics">${metric(summary.new || 0, 'New enquiries', 'Need first response')}${metric(summary.qualified || 0, 'Qualified', 'Fit established')}${metric(summary.appointments || 0, 'Appointments', 'Proposed or booked')}${metric(summary.human_attention || 0, 'Human attention', 'Escalated safely')}</div><nav><label>Acting as <select data-srw-actor><option value="">Select authorised person</option>${actorOptions(state.actorId)}</select></label><button class="primary" data-srw-new>+ Add enquiry</button></nav>${intake()}<div class="srw-grid"><section><div class="srw-title"><div><span>TODAY</span><h3>Next best work</h3></div><small>${Number(summary.open || 0)} open</small></div>${todayQueue()}</section><section><div class="srw-title"><div><span>PIPELINE</span><h3>Commercial flow</h3></div><small>No external writes</small></div>${pipeline()}</section></div>${playbook()}${liveConsole()}${panel()}</section>`;
  }

  function render() {
    const anchor = mount(); if (!anchor || !state.data) return;
    const current = anchor.querySelector('[data-aion-sales-revenue]');
    if (current) current.outerHTML = markup(); else anchor.insertAdjacentHTML('afterbegin', markup());
    enhanceAgentSetupPanel(anchor);
  }

  async function load() {
    const id = businessId(); if (!id || !mount()) return;
    if (state.loading) return;
    state.loading = true;
    state.workspaceId = id; state.error = '';
    try {
      state.data = await request(`/api/aion/sales/${encodeURIComponent(id)}`);
      global.__aionWebsiteEnquiryFeedRows = (state.data.opportunities || []).map((row) => ({
        id: row.opportunity_id,
        time: row.created_at ? new Date(row.created_at).toLocaleString() : '',
        customer: row.contact?.name || 'Customer',
        source: label(row.source), enquiry: row.title, message: row.enquiry,
        service: row.qualification?.answers?.need || row.title,
        location: row.qualification?.answers?.location || 'Not established',
        urgency: row.qualification?.answers?.urgency || 'Not established',
        workflow_id: 'tessaris_sales_revenue_spine',
        workflow_title: 'Sales qualification and handoff',
        workflow_status: label(row.stage), status: label(row.status),
        next: row.stage === 'new' ? 'Qualify enquiry' : label(row.stage),
        owner: actors().find((person) => person.person_id === row.owner_person_id)?.name || 'Unassigned',
      }));
      render();
    }
    catch (error) { state.error = `Sales workspace could not load: ${error.message}`; if (state.data) render(); }
    finally { state.loading = false; }
  }

  async function post(path, body, message) {
    state.busy = true; state.error = ''; state.message = ''; render();
    try { await request(path, { method: 'POST', body: JSON.stringify(body) }); state.message = message; state.panel = null; await load(); }
    catch (error) { state.error = error.message; }
    finally { state.busy = false; render(); }
  }

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-aion-sales-revenue] button'); if (!button) return;
    if (button.hasAttribute('data-srw-close')) { state.panel = null; render(); return; }
    if (button.hasAttribute('data-srw-new')) { state.panel = 'enquiry'; render(); return; }
    if (button.hasAttribute('data-srw-agent-setup')) { state.panel = 'agent_setup'; render(); return; }
    if (button.dataset.srwOpen) { state.selectedId = button.dataset.srwOpen; state.panel = 'detail'; render(); return; }
    if (button.dataset.srwPanel) { state.panel = button.dataset.srwPanel; render(); return; }
    if (button.hasAttribute('data-srw-create-intake')) {
      if (!state.actorId) { state.error = 'Select the authorised person creating this website intake'; render(); return; }
      state.busy = true; render();
      try {
        const result = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/intake-endpoints`, { method: 'POST', body: JSON.stringify({ name: 'Website enquiry form', created_by_person_id: state.actorId }) });
        state.intakeToken = result.endpoint.token; state.message = 'Secured website endpoint created. Copy the one-time token shown below.'; await load();
      } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
      return;
    }
    if (button.hasAttribute('data-srw-gmail-poll')) {
      if (!state.actorId) { state.error = 'Select the authorised person importing Gmail enquiries'; render(); return; }
      state.busy = true; render();
      try {
        const result = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/gmail/poll`, { method: 'POST', body: JSON.stringify({ imported_by_person_id: state.actorId }) });
        state.message = `${result.imported} new Gmail enquiries imported; ${result.deduplicated} duplicates ignored. Gmail was not changed.`; await load();
      } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
      return;
    }
    if (button.hasAttribute('data-srw-homefixed-poll')) {
      if (!state.actorId) { state.error = 'Select the authorised person importing HomeFixed enquiries'; render(); return; }
      state.busy = true; render();
      try {
        const result = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/homefixed-queue/poll`, { method: 'POST', body: JSON.stringify({ imported_by_person_id: state.actorId }) });
        state.message = `${result.imported} new HomeFixed enquiries imported (${result.human_enquiries} human, ${result.agent_requests} agent); ${result.deduplicated} duplicates safely ignored.`; await load();
      } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
      return;
    }
    if (button.hasAttribute('data-srw-simulate')) {
      if (!state.actorId) { state.error = 'Select the authorised person running the agent examination'; render(); return; }
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/playbooks/inbound-enquiry/simulations`, { run_by_person_id: state.actorId }, 'All required agent scenarios executed. Review the result before promotion.');
    }
    if (button.hasAttribute('data-srw-promote')) {
      if (!state.actorId) { state.error = 'Select the authorised person promoting this exact agent version'; render(); return; }
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/playbooks/inbound-enquiry/promote`, { expected_playbook_hash: state.data.playbook.playbook_hash, promoted_by_person_id: state.actorId }, 'The tested agent version is promoted for controlled use. No external deployment occurred.');
    }
    if (button.hasAttribute('data-srw-prepare-call')) {
      if (!state.actorId) { state.error = 'Select the authorised person preparing this call'; render(); return; }
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/opportunities/${encodeURIComponent(state.selectedId)}/calls/prepare`, { reason: 'Respond to the recorded customer enquiry', prepared_by_person_id: state.actorId }, 'Production call prepared. It has not started and requires exact approval.');
    }
    if (button.dataset.srwApproveCall) {
      if (!state.actorId) { state.error = 'Select the authorised person approving this exact call'; render(); return; }
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/calls/${encodeURIComponent(button.dataset.srwApproveCall)}/approve`, { expected_draft_hash: button.dataset.srwHash, approved_by_person_id: state.actorId }, 'Exact call approved. The telephone remains untouched until Start is separately selected.');
    }
    if (button.dataset.srwExecuteCall) {
      if (!state.actorId || !confirm('Start this exact approved customer call now?')) return;
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/calls/${encodeURIComponent(button.dataset.srwExecuteCall)}/execute`, { expected_draft_hash: button.dataset.srwHash, executed_by_person_id: state.actorId }, 'Approved production call submitted. Live signed events will appear in the console.');
    }
    if (button.hasAttribute('data-srw-retell-sync')) {
      if (!state.actorId) { state.error = 'Select the authorised person importing Retell call outcomes'; render(); return; }
      state.busy = true; render();
      try {
        const result = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/telephony/retell/sync`, { method: 'POST', body: JSON.stringify({ synced_by_person_id: state.actorId, limit: 100 }) });
        state.message = `${result.imported} new and ${result.updated} updated Retell call outcomes verified; ${result.unchanged} already current. No call was started.`; await load();
      } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
      return;
    }
    if (button.dataset.srwStage) {
      if (!state.actorId) { state.error = 'Select the authorised person acting on this Sales task'; render(); return; }
      await post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/opportunities/${encodeURIComponent(state.selectedId)}/stage`, { stage: button.dataset.srwStage, reason: 'Person confirmed pipeline outcome', changed_by_person_id: state.actorId }, `Opportunity marked ${label(button.dataset.srwStage)}.`);
    }
  });

  document.addEventListener('change', (event) => {
    if (event.target.hasAttribute('data-srw-actor')) state.actorId = event.target.value;
  });

  document.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-aion-sales-revenue] form'); if (!form) return;
    event.preventDefault(); if (state.busy) return;
    const value = values(form); const kind = form.dataset.srwForm;
    const actor = value.actor || state.actorId;
    if (!actor) { state.error = 'Select the authorised person acting on this Sales task'; render(); return; }
    const base = `/api/aion/sales/${encodeURIComponent(state.workspaceId)}`;
    if (kind === 'enquiry') return post(`${base}/enquiries`, { name: value.name, company_name: value.company_name || null, email: value.email || null, phone: value.phone || null, enquiry: value.enquiry, source: value.source, source_reference: value.source_reference || null, attribution: {}, consent: {}, created_by_person_id: actor }, 'Enquiry added and deduplicated against the customer ledger.');
    const opportunity = `${base}/opportunities/${encodeURIComponent(state.selectedId)}`;
    if (kind === 'agent_setup') {
      const data = new FormData(form); const destination = value.evidence_route_destination || null;
      state.busy = true; state.error = ''; render();
      try {
        await request(`${base}/playbooks/inbound-enquiry/agent-setup`, { method: 'PUT', body: JSON.stringify({ expected_playbook_hash: state.data.playbook.playbook_hash, configured_by_person_id: actor, setup: { business_motion: value.business_motion, lead_temperature: value.lead_temperature, primary_goal: value.primary_goal, close_strategy: value.close_strategy, intro_style: value.intro_style, custom_intro: value.custom_intro, sales_script: value.sales_script, required_fields: data.getAll('required_fields'), allowed_actions: data.getAll('allowed_actions'), evidence_route: { mode: value.evidence_route_mode, destination }, contact_sequence: { maximum_phone_attempts: Number(value.maximum_phone_attempts || 2), fallback_channel: value.fallback_channel || 'email', questions_per_written_message: Number(value.questions_per_written_message || 2) } } }) });
        state.message = 'New Sales agent version saved. It must pass the safety scenarios and be promoted before controlled use.'; state.panel = null; await load();
      } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
      return;
    }
    if (kind === 'qualify') return post(`${opportunity}/qualification`, { answers: { need: value.need, location: value.location, urgency: value.urgency, decision_maker: value.decision_maker, budget_context: value.budget_context }, notes: value.notes || null, qualified_by_person_id: actor }, 'Qualification evidence saved.');
    if (kind === 'appointment') return post(`${opportunity}/appointments/prepare`, { starts_at: value.starts_at, duration_minutes: Number(value.duration_minutes), assigned_person_id: value.assigned_person_id, location_or_channel: value.location_or_channel, notes: value.notes || null, prepared_by_person_id: actor }, 'Appointment prepared internally. Calendar and customer remain untouched.');
    if (kind === 'handoff') return post(`${opportunity}/handoff`, { assigned_person_id: value.assigned_person_id, reason: value.reason, urgency: value.urgency, handed_off_by_person_id: actor }, 'Human handoff created.');
    if (kind === 'call') {
      state.busy = true; state.error = ''; render();
      try {
        const started = await request(`${opportunity}/sessions`, { method: 'POST', body: JSON.stringify({ channel: value.channel, provider: value.provider, ai_disclosure: value.ai_disclosure === 'on', recording_consent: 'not_recorded', started_by_person_id: actor }) });
        const session = started.opportunity.sessions[started.opportunity.sessions.length - 1];
        await request(`${opportunity}/sessions/${encodeURIComponent(session.session_id)}/complete`, { method: 'POST', body: JSON.stringify({ disposition: value.disposition, summary: value.summary, next_action: value.next_action || null, human_takeover: value.human_takeover === 'on', completed_by_person_id: actor }) });
        state.message = 'Conversation outcome recorded. No external call was initiated.'; state.panel = null; await load();
      } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
    }
  });

  function installStyles() {
    if (document.getElementById('aion-sales-revenue-styles')) return;
    const style = document.createElement('style'); style.id = 'aion-sales-revenue-styles'; style.textContent = `.srw-shell{--ink:#102a43;--muted:#52677e;--line:#cbd9e6;--teal:#0f766e;--green:#15803d;box-sizing:border-box;background:#fff;color:var(--ink);border:2px solid #0ea5e9;margin:0 0 22px;font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}.srw-shell *{box-sizing:border-box}.srw-shell>header{display:flex;justify-content:space-between;gap:20px;padding:20px 22px;border-bottom:1px solid var(--line)}.srw-shell>header span,.srw-title span,.srw-studio>div>span,.srw-panel header span,.srw-capabilities span,.srw-console header span{color:var(--teal);font-size:10px;font-weight:900;letter-spacing:.2em}.srw-shell h2,.srw-shell h3{margin:5px 0!important}.srw-shell h2{font-size:25px!important}.srw-shell p{color:var(--muted)!important}.srw-shell button{background:#fff!important;color:#075985!important;border:1px solid #8fb3c7!important;padding:9px 12px!important;font-weight:800!important;cursor:pointer;text-align:left}.srw-shell button.primary{background:var(--green)!important;color:#fff!important;border-color:var(--green)!important}.srw-shell button:disabled{opacity:.4}.srw-shell>nav{display:flex;justify-content:flex-end;align-items:end;gap:8px;padding:12px 18px;border-bottom:1px solid var(--line)}.srw-shell>nav label{display:grid;gap:3px;margin-right:auto;font-size:9px;font-weight:900}.srw-shell select{background:#fff;color:var(--ink);border:1px solid #94a3b8;padding:8px}.srw-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:14px 18px;background:#f8fafc}.srw-metrics article{border:1px solid var(--line);background:#fff;padding:12px}.srw-metrics strong,.srw-metrics span,.srw-metrics small{display:block}.srw-metrics strong{font-size:20px}.srw-metrics span{font-size:11px;font-weight:800}.srw-metrics small{color:#64748b}.srw-capabilities{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:18px 18px 0}.srw-capabilities>article{border:1px solid var(--line);border-top:4px solid #0ea5e9;padding:14px;background:#f8fafc}.srw-capabilities small{display:block;color:#64748b}.srw-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}.srw-token,.srw-endpoint{display:grid;gap:5px;margin-top:10px;padding:9px;background:#fff7ed;border:1px solid #fdba74}.srw-token code,.srw-endpoint code{overflow-wrap:anywhere;font-size:10px}.srw-grid{display:grid;grid-template-columns:minmax(260px,.65fr) minmax(0,1.35fr);gap:14px;padding:18px}.srw-grid>section{border:1px solid var(--line);padding:14px;min-width:0}.srw-title{display:flex;justify-content:space-between;align-items:start;border-bottom:1px solid var(--line);margin-bottom:10px}.srw-queue{display:grid;gap:7px}.srw-queue>button{display:grid!important;gap:4px!important;width:100%}.srw-queue>button span{display:flex;gap:6px;align-items:center}.srw-queue small{color:#64748b}.srw-stage{display:inline-block;background:#e0f2fe;color:#075985;padding:3px 6px;font-size:9px;font-weight:900}.srw-stage.attention{background:#ffedd5;color:#9a3412}.srw-pipeline{display:flex;gap:8px;overflow:auto;padding-bottom:8px}.srw-pipeline>section{flex:0 0 190px;background:#f8fafc;border:1px solid var(--line);padding:8px}.srw-pipeline>section>header{display:flex;justify-content:space-between;margin-bottom:7px}.srw-pipeline>section>button{display:grid!important;width:100%;gap:4px;margin-bottom:6px;padding:8px!important}.srw-pipeline>section>button span,.srw-pipeline>section>button small{color:#64748b;font-size:10px}.srw-pipeline>section>p{font-size:11px;text-align:center}.srw-empty{padding:20px;text-align:center;border:1px dashed #7dd3fc;background:#f0f9ff}.srw-studio{margin:0 18px 18px;border-left:4px solid #8b5cf6;background:#f5f3ff;padding:15px;display:grid;grid-template-columns:1fr auto;gap:16px}.srw-studio-status{display:grid;align-content:start;gap:4px}.srw-studio details{grid-column:1/-1;border-top:1px solid #c4b5fd;padding-top:10px}.srw-studio summary{cursor:pointer;font-weight:900}.srw-studio-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.srw-studio-grid p{font-size:11px}.srw-console{margin:0 18px 18px;border:1px solid #94a3b8;background:#f8fafc}.srw-console>header{display:flex;justify-content:space-between;gap:14px;padding:15px;border-bottom:1px solid var(--line)}.srw-console>header>div:last-child{display:grid;text-align:right}.srw-console-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:14px}.srw-console-grid>div>article{display:grid;gap:5px;background:#fff;border:1px solid var(--line);padding:10px;margin-top:7px}.srw-console-grid article p{font-size:11px;margin:3px 0!important}.srw-console>footer{padding:10px 14px;border-top:1px solid var(--line);font-size:10px;color:#64748b}.srw-alert{margin:12px 18px 0;padding:10px;border-left:4px solid}.srw-alert.error{background:#fef2f2;border-color:#dc2626}.srw-alert.good{background:#ecfdf5;border-color:#16a34a}.srw-panel{position:fixed;z-index:11600;inset:0 0 0 auto;width:min(620px,98vw);overflow:auto;background:#fff;box-shadow:-20px 0 60px rgba(15,23,42,.28)}.srw-panel form,.srw-detail{display:grid;gap:14px;padding:24px}.srw-panel header{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:13px}.srw-panel label{display:grid;gap:5px;font-size:10px;font-weight:900}.srw-panel input,.srw-panel select,.srw-panel textarea{width:100%;background:#fff!important;color:var(--ink)!important;border:1px solid #94a3b8!important;padding:10px}.srw-panel footer{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;border-top:1px solid var(--line);padding-top:13px}.srw-two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.srw-detail-status{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.srw-detail section{border-left:3px solid #0ea5e9;padding:9px 12px;background:#f8fafc}.srw-detail section p,.srw-detail section small{display:block;margin:5px 0!important}.srw-detail-actions{justify-content:flex-start!important}@media(max-width:900px){.srw-grid,.srw-capabilities,.srw-console-grid{grid-template-columns:1fr}.srw-metrics{grid-template-columns:1fr 1fr}.srw-studio{grid-template-columns:1fr}.srw-studio-status,.srw-studio details{grid-column:1}.srw-studio-grid,.srw-two{grid-template-columns:1fr}}`;
    style.textContent += '.srw-checks{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px;border:1px solid var(--line);background:#f8fafc}.srw-checks>b,.srw-checks>small{grid-column:1/-1}.srw-checks label{display:flex;align-items:center;gap:8px;font-size:11px}.srw-checks input{width:auto!important;padding:0!important}';
    document.head.appendChild(style);
  }

  function schedule() {
    if (scheduled) return; scheduled = true;
    requestAnimationFrame(() => { scheduled = false; const id = businessId(); if (!mount() || !id) return; if (state.workspaceId !== id || !state.data) load(); else if (!document.querySelector('[data-aion-sales-revenue]')) render(); });
  }

  installStyles();
  new MutationObserver(schedule).observe(document.getElementById('app') || document.body, { childList: true, subtree: true });
  global.setInterval(() => {
    const id = businessId();
    if (mount() && id && (state.workspaceId !== id || !state.data)) load();
    else schedule();
  }, 2000);
  schedule();
  global.AionSalesRevenue = { state, load, render };
})(window);
