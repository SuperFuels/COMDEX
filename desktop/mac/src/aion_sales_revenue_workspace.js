(function installAionSalesRevenueWorkspace(global) {
  'use strict';

  const API = 'http://127.0.0.1:8080';
  const state = { workspaceId: '', data: null, actorId: '', panel: null, selectedId: '', selectedAgentId: '', busy: false, loading: false, error: '', message: '', intakeToken: '', intakeError: '', intakeMessage: '', enquiryDraft: {}, enquiryFocus: null, formDrafts: {}, formFocus: null, commercialDrafts: {}, customerPilotSessions: {}, customerTab: 'work', leadSourceFilter: 'all', pipelineFilter: 'new', pipelineSearch: '', customerFinance: { loading: false, loaded: false, catalog: null, completion: null, inbox: null, xero: null, xeroInvoices: [], xeroExports: [], reconciliation: null, error: '' } };
  let scheduled = false;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const label = (value) => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
  const businessId = () => global.AionBusinessContainerClient?.resolveBusinessId?.() || '';
  const mount = () => document.querySelector('[data-aion-sales-revenue-mount="true"]')
    || document.querySelector('[data-aion-shared-department-pilot="true"][data-aion-shared-department="sales"]')
    || document.querySelector('[data-aion-sales-live-agents-workspace-o14d="true"]');
  const selected = () => (state.data?.opportunities || []).find((row) => row.opportunity_id === state.selectedId);
  const selectedSalesAgent = () => (state.data?.sales_agents || []).find((row) => row.agent_id === state.selectedAgentId) || null;
  const actors = () => state.data?.actors || [];
  const actorOptions = (selectedId = '') => actors().map((row) => `<option value="${esc(row.person_id)}" ${row.person_id === selectedId ? 'selected' : ''}>${esc(row.name)}${row.position_title ? ` · ${esc(row.position_title)}` : ''}</option>`).join('');
  const actorById = (personId) => actors().find((row) => row.person_id === personId) || null;
  const actorName = (personId) => actorById(personId)?.name || '';
  const actorStorageKey = () => `aion.sales.signedInPerson.${state.workspaceId || businessId() || 'current'}.v1`;

  function onboardingUserName() {
    try {
      const voice = JSON.parse(global.localStorage?.getItem('aion.voiceOnboarding.o19i.v1') || 'null');
      return String(voice?.user_name || '').trim();
    } catch (_) { return ''; }
  }

  function syncSignedInActor() {
    const rows = actors().filter((row) => row?.person_id);
    if (!rows.length) { state.actorId = ''; return null; }
    const desktopIdentity = global.__AION_CURRENT_USER__ || global.__AION_DESKTOP_STATE__?.currentUser || global.__AION_DESKTOP_STATE__?.current_user || {};
    let storedId = '';
    try { storedId = String(global.localStorage?.getItem(actorStorageKey()) || '').trim(); } catch (_) { /* Storage is optional. */ }
    const directId = String(desktopIdentity.person_id || desktopIdentity.personId || desktopIdentity.id || storedId || state.actorId || '').trim();
    const direct = rows.find((row) => row.person_id === directId);
    const signedInName = String(desktopIdentity.name || desktopIdentity.display_name || onboardingUserName()).trim().toLowerCase();
    const named = signedInName ? rows.find((row) => String(row.name || '').trim().toLowerCase() === signedInName || String(row.name || '').trim().toLowerCase().startsWith(`${signedInName} `)) : null;
    const resolved = direct || named || (rows.length === 1 ? rows[0] : null);
    if (resolved) {
      state.actorId = resolved.person_id;
      try { global.localStorage?.setItem(actorStorageKey(), resolved.person_id); } catch (_) { /* Storage is optional. */ }
    }
    return resolved;
  }

  function recordedByField(caption = 'Recorded by') {
    const person = actorById(state.actorId) || syncSignedInActor();
    return `<div class="srw-recorded-by"><span>${esc(caption)}</span><b>${esc(person?.name || 'Sign in to record this action')}</b>${person?.position_title ? `<small>${esc(person.position_title)}</small>` : ''}<input type="hidden" name="actor" value="${esc(person?.person_id || '')}"></div>`;
  }

  function eventActorTrail(item) {
    const details = item?.details || {};
    const recorded = actorName(item?.recorded_by_person_id);
    const approved = actorName(details.approved_by_person_id) || details.approved_by_name || '';
    const sent = actorName(details.sent_by_person_id) || details.sent_by_name || '';
    return [recorded ? `Recorded by ${recorded}` : '', approved ? `Approved by ${approved}` : '', sent ? `Sent by ${sent}` : ''].filter(Boolean).join(' · ');
  }
  const values = (form) => Object.fromEntries(new FormData(form).entries());
  const selectedOption = (value, current) => String(value) === String(current || '') ? 'selected' : '';

  const formKind = (form) => String(form?.dataset?.srwForm || '');

  function snapshotForm(form) {
    const snapshot = {};
    Array.from(form?.elements || []).forEach((field) => {
      if (!field.name || field.disabled) return;
      if (field.type === 'checkbox' || field.type === 'radio') {
        const stored = snapshot[field.name] || { type: field.type, values: [] };
        if (field.checked) stored.values.push(field.value);
        snapshot[field.name] = stored;
      } else {
        snapshot[field.name] = { type: 'value', value: field.value };
      }
    });
    return snapshot;
  }

  function rememberFormDraft(form) {
    const kind = formKind(form);
    if (!kind) return;
    state.formDrafts[kind] = snapshotForm(form);
    if (kind === 'enquiry') state.enquiryDraft = values(form);
  }

  function restoreFormDraft(anchor, kind) {
    const snapshot = state.formDrafts[kind];
    const form = anchor?.querySelector(`[data-srw-form="${kind}"]`);
    if (!snapshot || !form) return;
    Array.from(form.elements || []).forEach((field) => {
      const stored = snapshot[field.name];
      if (!stored) return;
      if (field.type === 'checkbox' || field.type === 'radio') {
        field.checked = (stored.values || []).includes(field.value);
      } else {
        field.value = stored.value;
      }
    });
  }

  function rememberFormFocus(field) {
    const form = field?.closest?.('[data-srw-form]');
    const kind = formKind(form);
    if (!kind || !field.name) return;
    state.formFocus = {
      kind,
      name: field.name,
      start: Number.isInteger(field.selectionStart) ? field.selectionStart : null,
      end: Number.isInteger(field.selectionEnd) ? field.selectionEnd : null,
    };
    if (kind === 'enquiry') state.enquiryFocus = { ...state.formFocus };
  }

  function restoreFormFocus(anchor, focusState) {
    if (!focusState?.kind || !focusState?.name) return;
    const field = anchor?.querySelector(`[data-srw-form="${focusState.kind}"] [name="${focusState.name}"]`);
    if (!field) return;
    field.focus({ preventScroll: true });
    if (typeof field.setSelectionRange === 'function' && Number.isInteger(focusState.start)) {
      try { field.setSelectionRange(focusState.start, focusState.end); } catch (_) { /* Selects do not expose a text range. */ }
    }
  }

  function clearFormDraft(kind) {
    if (!kind) return;
    delete state.formDrafts[kind];
    if (state.formFocus?.kind === kind) state.formFocus = null;
    if (kind === 'enquiry') { state.enquiryDraft = {}; state.enquiryFocus = null; }
  }

  function rememberEnquiryDraft(form) {
    if (!form || form.dataset.srwForm !== 'enquiry') return;
    rememberFormDraft(form);
  }

  function rememberEnquiryFocus(field) {
    const form = field?.closest?.('[data-srw-form="enquiry"]');
    if (!form || !field.name) return;
    rememberFormFocus(field);
  }

  function restoreEnquiryFocus(anchor, focusState) {
    restoreFormFocus(anchor, focusState?.kind ? focusState : focusState ? { kind: 'enquiry', ...focusState } : null);
  }

  async function request(path, options = {}) {
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
    const controller = new AbortController();
    const timeout = global.setTimeout(() => controller.abort(), Number(options.timeoutMs || 6000));
    const fetchOptions = { ...options }; delete fetchOptions.timeoutMs;
    try {
      const response = await fetch(`${API}${path}`, { ...fetchOptions, headers, signal: options.signal || controller.signal });
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

  function enquirySourceGroup(row) {
    const source = String(row?.source || '').toLowerCase();
    if (/email|gmail/.test(source)) return 'email';
    if (/website|web_form|marketing_campaign/.test(source)) return 'website';
    if (/agent|a2a|public_intent/.test(source)) return 'agent';
    if (/call|phone|telephone/.test(source)) return 'phone';
    return 'third_party';
  }

  function recentEnquiryLanes() {
    const rows = (state.data?.opportunities || []).slice().sort((a, b) => String(b.updated_at || b.created_at || '').localeCompare(String(a.updated_at || a.created_at || '')));
    const lanes = [
      ['email', 'Email', 'Email enquiries', 'Inbox and connected email'],
      ['website', 'Website', 'Website enquiries', 'Forms, campaigns and web intake'],
      ['agent', 'Agent-to-agent', 'Agent-to-agent enquiries', 'Authorised A2A and public agent requests'],
      ['phone', 'Phone', 'Phone enquiries', 'Inbound calls and telephone leads'],
      ['third_party', 'Third-party', 'Third-party enquiries', 'Referrals, platforms, client work and manual entry'],
    ];
    const activeKey = lanes.some(([key]) => key === state.leadSourceFilter) ? state.leadSourceFilter : 'email';
    const activeLane = lanes.find(([key]) => key === activeKey) || lanes[0];
    const [, , title, description] = activeLane;
    const matches = rows.filter((row) => enquirySourceGroup(row) === activeKey);
    const cards = matches.map((row) => {
      const contact = [row.contact?.email, row.contact?.phone].filter(Boolean).join(' · ');
      return `<button type="button" class="srw-source-card" data-srw-open="${esc(row.opportunity_id)}"><header class="srw-source-card-header"><div><span>${stageBadge(row.stage)}</span><div><b>${esc(row.contact?.name || row.title || 'Lead')}</b>${contact ? `<small>${esc(contact)}</small>` : ''}</div></div><em>${esc(label(row.source))}</em></header><p>${esc(row.enquiry || row.title || 'No enquiry summary recorded.')}</p></button>`;
    }).join('');
    const tabs = lanes.map(([key, tabLabel]) => {
      const count = rows.filter((row) => enquirySourceGroup(row) === key).length;
      return `<button type="button" role="tab" aria-selected="${key === activeKey ? 'true' : 'false'}" class="${key === activeKey ? 'active' : ''}" data-srw-source-filter="${esc(key)}">${esc(tabLabel)} <span>${count}</span></button>`;
    }).join('');
    return `<div class="srw-source-browser"><nav class="srw-source-tabs" role="tablist" aria-label="Enquiry source">${tabs}</nav><section class="srw-source-lane" data-srw-source-lane="${esc(activeKey)}"><header><div><b>${esc(title)}</b><small>${esc(description)}</small></div><div class="srw-source-controls"><span>${matches.length} ${matches.length === 1 ? 'lead' : 'leads'}</span><button type="button" data-srw-source-scroll="-1" aria-label="Previous ${esc(title.toLowerCase())}">‹</button><button type="button" data-srw-source-scroll="1" aria-label="Next ${esc(title.toLowerCase())}">›</button></div></header><div class="srw-source-strip" tabindex="0" aria-label="${esc(title)}">${cards || '<p>No enquiries in this source yet.</p>'}</div></section></div>`;
  }

  function syncSourceCarouselControls() {
    document.querySelectorAll('[data-srw-source-lane]').forEach((lane) => {
      const strip = lane.querySelector('.srw-source-strip');
      if (!strip) return;
      const previous = lane.querySelector('[data-srw-source-scroll="-1"]');
      const next = lane.querySelector('[data-srw-source-scroll="1"]');
      if (previous) previous.disabled = strip.scrollLeft <= 2;
      if (next) next.disabled = strip.scrollLeft + strip.clientWidth >= strip.scrollWidth - 2;
    });
  }

  function pipeline() {
    const allRows = (state.data?.opportunities || []).slice().sort((a, b) => String(b.updated_at || b.created_at || '').localeCompare(String(a.updated_at || a.created_at || '')));
    const sourceOptions = [['all', 'All sources'], ['email', 'Email'], ['website', 'Website'], ['agent', 'Agent-to-agent'], ['phone', 'Phone'], ['third_party', 'Third-party']];
    const activeSource = sourceOptions.some(([value]) => value === state.leadSourceFilter) ? state.leadSourceFilter : 'all';
    const sourceRows = activeSource === 'all' ? allRows : allRows.filter((row) => enquirySourceGroup(row) === activeSource);
    const stageGroups = [
      ['new', 'New', ['new']],
      ['contacted', 'Contacted', ['contacted', 'qualification', 'human_handoff']],
      ['qualified', 'Qualified', ['qualified', 'appointment_proposed']],
      ['appointment_booked', 'Appointment Booked', ['appointment_booked']],
      ['proposal', 'Proposal', ['proposal']],
      ['won', 'Won', ['won']],
      ['closed', 'Closed', ['lost']],
    ];
    const active = stageGroups.some(([value]) => value === state.pipelineFilter) ? state.pipelineFilter : 'all';
    const activeStages = stageGroups.find(([value]) => value === active)?.[2] || [];
    const stageRows = active === 'all' ? sourceRows : sourceRows.filter((row) => activeStages.includes(row.stage));
    const query = String(state.pipelineSearch || '').trim().toLowerCase();
    const rows = query ? stageRows.filter((row) => [
      row.contact?.name, row.contact?.company_name, row.contact?.email, row.contact?.phone,
      row.title, row.enquiry, row.source, row.relationship?.next_action,
    ].filter(Boolean).join(' ').toLowerCase().includes(query)) : stageRows;
    const filters = [['all', 'All', sourceRows.length], ...stageGroups.map(([value, text, members]) => [value, text, sourceRows.filter((row) => members.includes(row.stage)).length])];
    const sourceFilters = sourceOptions.map(([value, text]) => [value, text, value === 'all' ? allRows.length : allRows.filter((row) => enquirySourceGroup(row) === value).length]);
    const cards = rows.map((row) => {
      const owner = actorName(row.owner_person_id) || 'Unassigned';
      const next = row.relationship?.next_action || (row.stage === 'new' ? 'Qualify enquiry' : `Review ${label(row.stage).toLowerCase()}`);
      const value = row.deal?.estimated_value == null ? '' : `${esc(row.deal.currency || 'GBP')} ${Number(row.deal.estimated_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      return `<button type="button" class="srw-deal-card" data-srw-open="${esc(row.opportunity_id)}"><header>${stageBadge(row.stage)}<span>${value || `${esc(row.qualification?.score || 0)}% qualified`}</span></header><b>${esc(row.contact?.name || 'Lead')}</b><p>${esc(row.title || row.enquiry || '')}</p><footer><small>${esc(next)}</small><em>${esc(owner)}</em></footer></button>`;
    }).join('');
    const resultLabel = query ? `${rows.length} matching ${rows.length === 1 ? 'lead' : 'leads'}` : `${stageRows.length} ${stageRows.length === 1 ? 'lead' : 'leads'}`;
    const empty = query ? '<div class="srw-empty"><b>No matching clients or leads</b><p>Try a different client name, email, phone number or enquiry.</p></div>' : '<div class="srw-empty"><b>No leads at this stage</b><p>Choose another source or stage.</p></div>';
    return `<div class="srw-commercial-flow"><div class="srw-unified-filter"><small>Lead source</small><nav class="srw-source-tabs" aria-label="Filter by lead source">${sourceFilters.map(([value, text, count]) => `<button type="button" class="${activeSource === value ? 'active' : ''}" data-srw-source-filter="${esc(value)}">${esc(text)} <span>${count}</span></button>`).join('')}</nav></div><div class="srw-deal-controls"><label class="srw-stage-select"><span>Stage</span><select data-srw-pipeline-filter aria-label="Filter by sales stage">${filters.map(([value, text, count]) => `<option value="${esc(value)}" ${active === value ? 'selected' : ''}>${esc(text)} (${count})</option>`).join('')}</select></label><label class="srw-deal-search"><span>Find client or lead</span><input type="search" data-srw-deal-search value="${esc(state.pipelineSearch)}" placeholder="Start typing a client name…" autocomplete="off"></label><div><small data-srw-deal-count>${esc(resultLabel)}</small><button type="button" data-srw-deal-scroll="-1" aria-label="Previous leads">‹</button><button type="button" data-srw-deal-scroll="1" aria-label="Next leads">›</button></div></div><div class="srw-deal-strip" tabindex="0" aria-label="${esc(resultLabel)}">${cards || empty}</div></div>`;
  }

  function syncDealCarouselControls() {
    const strip = document.querySelector('[data-aion-sales-revenue] .srw-deal-strip');
    if (!strip) return;
    const previous = document.querySelector('[data-srw-deal-scroll="-1"]');
    const next = document.querySelector('[data-srw-deal-scroll="1"]');
    if (previous) previous.disabled = strip.scrollLeft <= 2;
    if (next) next.disabled = strip.scrollLeft + strip.clientWidth >= strip.scrollWidth - 2;
  }

  function playbook() {
    const row = state.data?.playbook || {};
    const setup = row.agent_setup || {};
    const passed = Boolean(row.simulation?.all_passed);
    const promoted = row.status === 'promoted_for_controlled_use';
    const status = promoted
      ? ['Call plan approved', 'It can now be used when a person prepares and approves a call.']
      : passed
        ? ['Ready for your approval', 'The safety check passed. Approve this call plan before using it with a lead.']
        : row.status === 'simulation_failed'
          ? ['Changes required', 'One or more safety checks failed. Review the call settings and test again.']
          : ['Safety check required', 'Save the call plan, then check it before it can be used.'];
    const desiredOutcome = {
      human_review_request: 'Collect the facts for human review',
      human_callback_request: 'Arrange a human callback',
      site_visit_request: 'Request a site visit',
    }[setup.primary_goal] || 'Collect the facts for human review';
    const fallback = { email: 'continue by email', sms: 'continue by SMS', whatsapp: 'continue by WhatsApp', none: 'send to human review' }[setup.contact_sequence?.fallback_channel] || 'continue by email';
    return `<section class="srw-studio srw-caller-setup"><header><div><span>AI SALES CALLER</span><h3>Follow up new enquiries by phone</h3><p>This caller contacts a selected lead, asks the approved questions and records the answers. It does not answer incoming calls or call anyone automatically.</p></div><div class="srw-caller-status ${promoted ? 'ready' : passed ? 'review' : ''}"><b>${esc(status[0])}</b><small>${esc(status[1])}</small></div></header><div class="srw-caller-steps"><article class="done"><span>1</span><div><b>Set the call plan</b><small>Choose the goal, questions and permitted follow-up.</small></div></article><article class="${passed ? 'done' : 'current'}"><span>2</span><div><b>Check it safely</b><small>${Number(row.simulation?.passed || 0)}/${Number(row.simulation?.required || 11)} scenarios passed.</small></div></article><article class="${promoted ? 'done' : passed ? 'current' : ''}"><span>3</span><div><b>Approve for use</b><small>This still does not start or schedule a call.</small></div></article></div><div class="srw-actions srw-caller-actions"><button class="primary" data-srw-agent-setup>Edit call settings</button><button data-srw-simulate>${passed ? 'Run safety check again' : 'Run safety check'}</button>${passed && !promoted ? '<button class="primary" data-srw-promote>Approve this call plan</button>' : ''}</div><details class="srw-caller-plan"><summary>Review what the caller will do</summary><div class="srw-caller-plan-grid"><article><span>Goal</span><b>${esc(desiredOutcome)}</b><small>${esc(label(setup.close_strategy || 'human_review'))} is the intended end of the conversation.</small></article><article><span>Questions</span><b>${(setup.required_fields || []).length} facts to establish</b><small>${(setup.required_fields || []).slice(0, 4).map(label).join(' · ')}${(setup.required_fields || []).length > 4 ? ' · more' : ''}</small></article><article><span>If unanswered</span><b>Try up to ${Number(setup.contact_sequence?.maximum_phone_attempts || 2)} times</b><small>Then ${esc(fallback)}. Written messages remain drafts.</small></article><article><span>Authority</span><b>Collect and prepare only</b><small>No automatic price, booking, payment, message or provider update.</small></article></div><details><summary>Full safeguards and collected information</summary><div class="srw-studio-grid"><div><b>Information to collect</b>${(setup.required_fields || []).map((item) => `<p>● ${esc(label(item))}</p>`).join('')}<b>Allowed requests and preparations</b>${(setup.allowed_actions || []).map((item) => `<p>✓ ${esc(label(item))}</p>`).join('')}</div><div><b>Always enforced</b>${(row.guardrails || []).map((item) => `<p>✓ ${esc(item)}</p>`).join('')}<p>Payment means preparing a separately approved payment link—never taking card details during the call.</p></div></div></details></details></section>`;
  }

  function callCentre() {
    const agents = state.data?.sales_agents || [];
    const active = agents.filter((row) => row.state === 'active').length;
    const ready = agents.filter((row) => row.state === 'ready').length;
    const needsWork = agents.filter((row) => ['draft', 'testing_required'].includes(row.state)).length;
    const cards = agents.map((row) => {
      const safety = row.safety || {};
      const minted = row.minted_contract || null;
      const phone = row.phone_assignment?.number || 'Number not assigned';
      const inboundNeedsConnection = ['inbound','both'].includes(row.direction) && !row.phone_assignment?.inbound_routing_confirmed;
      const next = row.state === 'draft' || row.state === 'testing_required'
        ? 'Complete the setup and run the safety check.'
        : !minted
          ? 'Mint the checked settings into an immutable call contract.'
          : row.state === 'ready' && inboundNeedsConnection
            ? 'The contract is ready. Connect this number to the contract in Connections before switching it on.'
          : row.state === 'ready'
            ? 'Switch this caller on when you are ready to use it.'
            : row.state === 'active'
              ? 'This agent can be selected for governed calls.'
              : 'This agent is paused and will not be selected for new calls.';
      const actions = `<button type="button" data-srw-edit-call-agent="${esc(row.agent_id)}">Edit setup</button>`
        + `${['draft','testing_required'].includes(row.state) ? `<button type="button" data-srw-test-call-agent="${esc(row.agent_id)}">Run safety check</button>` : ''}`
        + `${safety.all_passed && !minted ? `<button type="button" class="primary" data-srw-mint-call-agent="${esc(row.agent_id)}" data-srw-hash="${esc(row.agent_hash)}">Mint contract</button>` : ''}`
        + `${minted && row.state !== 'active' && !inboundNeedsConnection ? `<button type="button" class="primary" data-srw-state-call-agent="${esc(row.agent_id)}" data-srw-agent-state="active" data-srw-hash="${esc(row.agent_hash)}">Switch on</button>` : ''}`
        + `${minted && row.state !== 'active' && inboundNeedsConnection ? '<button type="button" disabled title="Connect the inbound number to this contract in Connections first">Connect number first</button>' : ''}`
        + `${row.state === 'active' ? `<button type="button" data-srw-state-call-agent="${esc(row.agent_id)}" data-srw-agent-state="paused" data-srw-hash="${esc(row.agent_hash)}">Pause</button>` : ''}`;
      return `<article class="srw-call-agent-card ${row.state === 'active' ? 'active' : ''}"><header><div><span>${esc(label(row.direction))}</span><h4>${esc(row.name)}</h4></div><b>${esc(label(row.state))}</b></header><div class="srw-call-agent-facts"><span>Number<b>${esc(phone)}</b></span><span>Contract<b>${minted ? `Version ${Number(minted.version || row.version)}` : 'Not minted'}</b></span><span>Safety<b>${Number(safety.passed || 0)}/${Number(safety.required || 11)}</b></span></div><p>${esc(next)}</p><footer>${actions}</footer></article>`;
    }).join('');
    return `<section class="srw-call-centre"><header><div><span>AI CALL CENTRE</span><h3>Build and run your sales callers</h3><p>Create an inbound or outbound caller, give it approved business knowledge, choose the result and information to capture, then test and mint the exact contract before switching it on.</p></div><div class="srw-call-centre-head-actions"><button type="button" data-srw-open-phone-vault>Phone connections · Twilio + Retell</button><button type="button" class="primary" data-srw-new-call-agent>+ Create sales caller</button></div></header><div class="srw-call-centre-guide"><article><span>1</span><b>Describe the job</b><small>Direction, business knowledge and intended result.</small></article><article><span>2</span><b>Choose what to capture</b><small>Standard or business-specific information.</small></article><article><span>3</span><b>Test and mint</b><small>Freeze the approved settings into a versioned contract.</small></article><article><span>4</span><b>Switch on</b><small>Inbound answers its number; outbound becomes available on leads.</small></article></div><div class="srw-phone-provider-route"><div><b>Before switching on a caller</b><span>Connect Twilio for the telephone number and Retell for the AI voice service. Credentials and routing are managed securely in Vault.</span></div><button type="button" data-srw-open-phone-vault>Open phone setup</button></div><div class="srw-call-centre-summary"><span><b>${agents.length}</b> callers</span><span><b>${active}</b> active</span><span><b>${ready}</b> ready</span><span><b>${needsWork}</b> need setup</span></div>${cards ? `<div class="srw-call-agent-grid">${cards}</div>` : '<div class="srw-call-centre-empty"><b>No sales callers yet</b><p>Create one caller for each distinct job or telephone number—for example “Website enquiry line”, “Appointment booking” or “Outbound lead qualification”.</p><button type="button" class="primary" data-srw-new-call-agent>Create your first sales caller</button></div>'}<details class="srw-call-centre-boundary"><summary>How inbound and outbound callers work</summary><div><p><b>Inbound:</b> the assigned number chooses this contract, creates or matches the caller’s lead, captures answers and prepares the configured next step.</p><p><b>Outbound:</b> open a lead, select an active caller, approve the frozen customer-specific call, then start it.</p><p>Switching on a caller does not bypass provider, consent or exact-call approval controls.</p></div></details></section>`;
  }

  function vaultWebsiteIntake() {
    const website = state.data?.intake?.website || {};
    const endpoints = website.endpoints || [];
    const connected = endpoints.some((row) => String(row.status || '').toLowerCase() === 'active');
    const endpointRows = endpoints.map((row) => `<article class="srw-vault-endpoint"><div><b>${esc(row.name || 'Website connection')}</b><small>${Number(row.accepted || 0)} lead${Number(row.accepted || 0) === 1 ? '' : 's'} received · ${esc(label(row.status || 'unknown'))}</small></div><code>${esc(row.receiver_path)}</code><button type="button" data-srw-copy-value="${esc(row.receiver_path)}">Copy endpoint</button></article>`).join('');
    if (!state.data) {
      return `<section class="operations-agents-card aion-vault-canonical-panel srw-vault-intake" data-aion-vault-website-intake="true"><div class="operations-agents-card-head"><div><div class="eyebrow">Website connections</div><h2>Connect website enquiries</h2><p class="muted">Loading website intake connections…</p></div><span class="badge">Loading</span></div></section>`;
    }
    return `<section class="operations-agents-card aion-vault-canonical-panel srw-vault-intake" data-aion-vault-website-intake="true"><div class="operations-agents-card-head"><div><div class="eyebrow">Website connections</div><h2>Connect website enquiries</h2><p class="muted">Give an existing website a secure route for creating deduplicated leads in Revenue flow.</p></div><span class="badge">${state.busy ? 'Working' : connected ? `${endpoints.length} active` : 'Not connected'}</span></div>${state.intakeError ? `<div class="srw-alert error">${esc(state.intakeError)}</div>` : ''}${state.intakeMessage ? `<div class="srw-alert good">${esc(state.intakeMessage)}</div>` : ''}<div class="srw-vault-intake-summary"><div><strong>${endpoints.length}</strong><span>Website connection${endpoints.length === 1 ? '' : 's'}</span><small>Incoming submissions become Website leads automatically.</small></div><button type="button" class="primary-btn" data-srw-create-intake>Create website connection</button></div>${endpointRows ? `<div class="srw-vault-endpoints">${endpointRows}</div>` : '<div class="srw-vault-intake-empty"><b>No website is connected yet</b><p>Create a connection, then give its endpoint and one-time secret to the person or server that manages the website.</p></div>'}${state.intakeToken ? `<div class="srw-token srw-vault-token"><b>Copy this one-time secret now</b><code>${esc(state.intakeToken)}</code><button type="button" data-srw-copy-value="${esc(state.intakeToken)}">Copy secret</button><small>Store this only in the website server. Send it as <code>X-Tessaris-Intake-Key</code>. Never place it in public browser code; Tessaris stores only its digest.</small></div>` : ''}<details class="aion-vault-advanced-details"><summary>HomeFixed queue recovery</summary><p class="muted">This is separate from the generic website connection. Use it only to pull waiting submissions from the existing HomeFixed queue.</p><button type="button" class="secondary-btn" data-srw-homefixed-poll>Import waiting HomeFixed enquiries</button></details></section>`;
  }

  function renderVaultWebsiteIntake() {
    const current = document.querySelector('[data-aion-vault-website-intake="true"]');
    if (current) current.outerHTML = vaultWebsiteIntake();
  }

  async function loadVaultWebsiteIntake() {
    const id = businessId();
    if (!id || state.loading || (state.workspaceId === id && state.data)) { renderVaultWebsiteIntake(); return; }
    state.loading = true; state.workspaceId = id; state.intakeError = '';
    renderVaultWebsiteIntake();
    try {
      state.data = await request(`/api/aion/sales/${encodeURIComponent(id)}`);
      syncSignedInActor();
    } catch (error) {
      state.intakeError = `Website connections could not load: ${error.message}`;
    } finally {
      state.loading = false;
      renderVaultWebsiteIntake();
    }
  }

  function renderVaultWebsiteIntakePanel() {
    const id = businessId();
    if (id && (state.workspaceId !== id || !state.data) && !state.loading) global.setTimeout(loadVaultWebsiteIntake, 0);
    return vaultWebsiteIntake();
  }

  function liveConsole() {
    const tel = state.data?.telephony || {}; const drafts = tel.call_drafts || []; const events = tel.events || [];
    const latestEvents = new Map();
    events.forEach((row, index) => {
      const callId = String(row.call_id || `event-${index}`);
      const timestamp = Number(row.end_timestamp || row.start_timestamp || 0) || Date.parse(row.synced_at || row.received_at || '') || index;
      const previous = latestEvents.get(callId);
      if (!previous || timestamp >= previous.timestamp) latestEvents.set(callId, { row, timestamp });
    });
    const callResults = Array.from(latestEvents.values()).map((entry) => entry.row);
    const finishedStatuses = new Set(['ended', 'completed', 'complete', 'error', 'failed']);
    const liveStatuses = new Set(['registered', 'ongoing', 'in_progress', 'ringing']);
    const finishedIds = new Set(callResults.filter((row) => finishedStatuses.has(String(row.call_status || '').toLowerCase())).map((row) => String(row.call_id || '')));
    const madeIds = new Set(callResults.map((row) => String(row.call_id || '')).filter(Boolean));
    drafts.filter((row) => row.status === 'submitted').forEach((row) => madeIds.add(String(row.provider_call_id || row.draft_id)));
    const liveIds = new Set(callResults.filter((row) => liveStatuses.has(String(row.call_status || '').toLowerCase())).map((row) => String(row.call_id || '')));
    drafts.filter((row) => row.status === 'submitted' && !finishedIds.has(String(row.provider_call_id || ''))).forEach((row) => liveIds.add(String(row.provider_call_id || row.draft_id)));
    const completedCalls = callResults.filter((row) => finishedStatuses.has(String(row.call_status || '').toLowerCase())).length;
    const totalDurationMs = callResults.reduce((sum, row) => sum + Math.max(0, Number(row.duration_ms || 0)), 0);
    const durationLabel = totalDurationMs >= 3600000
      ? `${Math.floor(totalDurationMs / 3600000)}h ${Math.floor((totalDurationMs % 3600000) / 60000)}m`
      : totalDurationMs >= 60000
        ? `${Math.floor(totalDurationMs / 60000)}m ${Math.floor((totalDurationMs % 60000) / 1000)}s`
        : `${Math.floor(totalDurationMs / 1000)}s`;
    const readiness = tel.live_execution_enabled
      ? ['Ready for approved calls', 'The phone connection is available. Every call still requires individual approval.']
      : tel.configured
        ? ['Calling is switched off', 'The phone provider is connected, but live execution is disabled. Calls can be prepared and approved but cannot start.']
        : tel.agent_configured
          ? ['Phone number required', 'The calling agent exists, but a business calling number has not been connected.']
          : ['Phone connection required', 'Connect a calling provider before placing approved calls.'];
    const draftStatus = (value) => ({ exact_approval_required: 'Waiting for approval', approved_not_executed: 'Approved · waiting to start', submitted: 'Sent to phone provider' }[value] || label(value));
    return `<section class="srw-console srw-caller-console"><header><div><span>CALLS AND RESULTS</span><h3>Approved customer calls</h3><p>Start from a lead’s customer record. Tessaris freezes that customer, phone number, call goal and minted caller contract before asking for approval.</p></div><div class="srw-call-readiness ${tel.live_execution_enabled ? 'ready' : ''}"><b>${esc(readiness[0])}</b><small>${esc(readiness[1])}</small></div></header><div class="srw-call-metrics"><article><strong>${madeIds.size}</strong><span>Calls made</span><small>Submitted to the phone provider</small></article><article><strong>${liveIds.size}</strong><span>Live or awaiting result</span><small>Refresh results to confirm completion</small></article><article><strong>${completedCalls}</strong><span>Completed calls</span><small>Verified provider outcomes</small></article><article><strong>${esc(durationLabel)}</strong><span>Total call duration</span><small>Across verified call results</small></article></div><div class="srw-console-grid"><div><div class="srw-console-column-title"><div><b>Prepared calls</b><small>${drafts.length} total · ${drafts.filter((row) => row.status === 'exact_approval_required').length} awaiting approval</small></div></div>${drafts.length ? drafts.slice(0, 5).map((row) => `<article><span>${esc(row.customer_name || row.to_number)}</span><small>${esc(draftStatus(row.status))}${row.sales_agent_name ? ` · ${esc(row.sales_agent_name)}` : ''}</small><p>${esc(row.reason || 'Follow up the customer enquiry')}</p><div class="srw-actions">${row.status === 'exact_approval_required' ? `<button data-srw-approve-call="${esc(row.draft_id)}" data-srw-hash="${esc(row.draft_hash)}">Review and approve call</button>` : ''}${row.status === 'approved_not_executed' ? `<button class="primary" data-srw-execute-call="${esc(row.draft_id)}" data-srw-hash="${esc(row.draft_hash)}" ${tel.live_execution_enabled ? '' : 'disabled'}>Start approved call</button>` : ''}</div></article>`).join('') : '<div class="srw-console-empty"><b>No calls have been prepared</b><p>Open a lead with a valid phone number and choose “Prepare production call”.</p></div>'}</div><div><div class="srw-console-column-title"><div><b>Completed call results</b><small>Verified from the connected phone provider</small></div><button data-srw-retell-sync ${tel.agent_configured ? '' : 'disabled'}>Refresh results</button></div>${callResults.length ? callResults.slice(0, 8).map((row) => `<article><span>${esc(row.call_status ? label(row.call_status) : 'Call result')}</span><small>${esc(row.call_id || '')}${row.duration_ms ? ` · ${Math.round(Number(row.duration_ms) / 1000)} seconds` : ''}</small>${(row.transcript_object || []).slice(-3).map((turn) => `<p><b>${esc(label(turn.role))}</b> ${esc(turn.content || '')}</p>`).join('')}</article>`).join('') : '<div class="srw-console-empty"><b>No completed call results yet</b><p>After a call, use “Refresh results” to bring its verified outcome and transcript into Tessaris.</p></div>'}</div></div><details class="srw-call-technical"><summary>Phone connection details</summary><div><span>Provider</span><b>${esc(label(tel.provider || 'not connected'))}</b><span>Connection</span><b>${esc(label(tel.status || 'not configured'))}</b><span>Legacy call plan</span><b>${tel.playbook_promoted ? 'Approved for controlled use' : 'Not approved'}</b><span>Security</span><b>Minted contract · exact approval · signed provider readback</b></div></details></section>`;
  }

  function customerPilotSession(row = selected()) {
    if (!row) return null;
    if (!state.customerPilotSessions[row.opportunity_id]) {
      state.customerPilotSessions[row.opportunity_id] = {
        open: false, activeMode: '', status: 'idle', error: '', input: '', pendingAction: null, attachments: [],
        quoteInterview: null,
        messages: [{ role: 'pilot', text: `I’m connected only to ${row.contact?.name || 'this customer'} and this customer’s job feed. Say “Pilot, let’s produce the quote”, “Pilot, make this note…”, “Pilot, job completed”, or “Pilot, prepare the invoice”.` }],
      };
    }
    return state.customerPilotSessions[row.opportunity_id];
  }

  function pilotMessage(session, role, text) {
    const clean = String(text || '').trim();
    if (!session || !clean) return;
    session.messages.push({ role, text: clean, createdAt: new Date().toISOString() });
    session.messages = session.messages.slice(-30);
  }

  function pilotInstructionDetail(row, session) {
    return {
      scope: 'selected_customer_only',
      opportunity_id: row.opportunity_id,
      customer_name: row.contact?.name || null,
      relationship: row.relationship || {},
      lifecycle_stage: row.work_feed?.current_stage || row.stage || null,
      transcript: (session.messages || []).slice(-12).map((item) => ({ role: item.role, text: item.text })),
    };
  }

  function pilotIntentRemainder(text, pattern) {
    return String(text || '').replace(/^\s*(?:hey\s+)?pilot[,:]?\s*/i, '').replace(pattern, '').replace(/^\s*[:,-]?\s*/, '').trim();
  }

  const quoteInterviewStages = ['scope', 'exclusions_duration', 'customer_charges', 'internal_costs', 'evidence', 'review'];

  function cleanSpokenQuoteText(value) {
    return String(value || '')
      .replace(/\b(?:um+|uh+|erm+|er+|you know|sort of|kind of)\b[,.]?/gi, ' ')
      .replace(/\s+([,.])/g, '$1')
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  function quoteInterviewQuestion(stage, row) {
    const firstName = String(actors().find((person) => person.person_id === state.actorId)?.name || '').split(/\s+/)[0];
    const hello = firstName ? `Hello ${firstName}. ` : '';
    if (stage === 'scope') return `${hello}Tell me what the customer wants done, then what you will supply, install or carry out. I’ll take the costs separately afterwards.`;
    if (stage === 'exclusions_duration') return 'Are there any exclusions or customer responsibilities to make clear, such as parking, access or making good? Also, how long should the work take?';
    if (stage === 'customer_charges') return 'Now tell me the customer charges. You can give one total or separate labour, materials, parking and subcontractor prices.';
    if (stage === 'internal_costs') return 'What should I budget internally for labour, materials, parking or third-party suppliers? These figures stay private and are used only for margin.';
    if (stage === 'evidence') return 'Would you like to attach any supporting photos or documents? You can upload them now, or say “stop and generate quote”.';
    return `The quotation draft for ${row.contact?.name || 'this customer'} is ready. Check the wording and figures below before saving or sending anything.`;
  }

  async function extractQuoteTurn(row, draft, interview, userTurn) {
    try {
      const response = await fetch(`${API}/api/boardroom/quote-interview`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_id: businessId() || state.workspaceId || 'current-business', stage: interview.stage, user_turn: userTurn, currency: commercialCurrency(row), current_draft: { scope_summary: draft.quoteScopeSummary || '', scope_items: draft.quoteScopeItems || [], exclusions: draft.quoteExclusions || [], duration: draft.quoteDuration || '', lines: draft.lines, terms: draft.terms }, requested_providers: ['gemini', 'openai', 'gemma'] }),
      });
      const payload = await response.json().catch(() => ({}));
      const parsed = response.ok && payload.status === 'extracted' && payload.extraction && typeof payload.extraction === 'object' ? payload.extraction : null;
      if (parsed && typeof parsed === 'object') return { ...parsed, provider: payload.provider_label || payload.provider_id || 'connected model' };
    } catch (_) { /* Use the strict local fallback below. */ }
    const cleaned = cleanSpokenQuoteText(userTurn);
    const result = { scope_summary: '', scope_items: [], exclusions: [], duration: '', charge_lines: [], terms: '', next_stage: quoteInterviewStages[Math.min(quoteInterviewStages.indexOf(interview.stage) + 1, quoteInterviewStages.length - 1)], quote_complete_requested: /\b(?:stop|finish|end)(?:\s+(?:and\s+)?(?:generate|create|finish))?\s+(?:the\s+)?quote\b|\bquote\s+(?:finished|ended|done)\b|\bthat(?:'s| is)\s+(?:it|all)\b/i.test(cleaned), provider: 'local structured fallback' };
    if (interview.stage === 'scope') {
      const items = cleaned.split(/(?:\.|;|,?\s+(?:and\s+)?then\s+)/i).map((item) => item.trim()).filter(Boolean);
      result.scope_summary = items.length > 1 ? 'We propose to carry out the following work:' : cleaned;
      result.scope_items = items.length > 1 ? items : [];
    }
    else if (interview.stage === 'exclusions_duration') result.exclusions = [cleaned];
    if (['customer_charges', 'internal_costs'].includes(interview.stage)) {
      const internal = interview.stage === 'internal_costs' || /\b(?:internal|cost|costs|budget|pay us|pay them)\b/i.test(cleaned);
      const matches = [...cleaned.matchAll(/(?:£|€|\$|gbp\s*|eur\s*|usd\s*)(\d+(?:[,.]\d{1,2})?)/gi)];
      matches.forEach((match) => {
        const nearby = cleaned.slice(Math.max(0, match.index - 45), Math.min(cleaned.length, (match.index || 0) + match[0].length + 35));
        const category = /parking/i.test(nearby) ? 'parking' : /material/i.test(nearby) ? 'materials' : /supplier|subcontract|third party/i.test(nearby) ? 'supplier_subcontractor' : /scaffold/i.test(nearby) ? 'scaffolding' : /skip|waste/i.test(nearby) ? 'skip_waste' : 'labour';
        result.charge_lines.push({ category, description: label(category), quantity: 1, internal_unit_cost: internal ? numericValue(match[1]) : null, customer_unit_price: internal ? null : numericValue(match[1]), person_name: '' });
      });
    }
    return result;
  }

  function applyQuoteExtraction(draft, extraction) {
    const scopeSummary = cleanSpokenQuoteText(extraction?.scope_summary);
    const scopeItems = Array.isArray(extraction?.scope_items) ? extraction.scope_items.map(cleanSpokenQuoteText).filter(Boolean) : [];
    if (scopeSummary) draft.quoteScopeSummary = scopeSummary;
    draft.quoteScopeItems = [...new Set([...(draft.quoteScopeItems || []), ...scopeItems])];
    if (scopeSummary || scopeItems.length) draft.scope = [draft.quoteScopeSummary, ...draft.quoteScopeItems.map((item) => `• ${item}`)].filter(Boolean).join('\n');
    const exclusions = Array.isArray(extraction?.exclusions) ? extraction.exclusions.map(cleanSpokenQuoteText).filter(Boolean) : [];
    draft.quoteExclusions = [...new Set([...(draft.quoteExclusions || []), ...exclusions])];
    const duration = cleanSpokenQuoteText(extraction?.duration);
    if (duration) draft.quoteDuration = duration;
    const terms = cleanSpokenQuoteText(extraction?.terms);
    if (terms) draft.terms = terms;
    (Array.isArray(extraction?.charge_lines) ? extraction.charge_lines : []).forEach((item) => {
      const category = commercialCategories.some(([key]) => key === item?.category) ? item.category : 'other';
      const description = cleanSpokenQuoteText(item?.description) || label(category);
      const quantity = item?.quantity == null ? 1 : Math.max(0, numericValue(item.quantity));
      const internalUnitCost = item?.internal_unit_cost == null ? 0 : Math.max(0, numericValue(item.internal_unit_cost));
      const customerUnitPrice = item?.customer_unit_price == null ? 0 : Math.max(0, numericValue(item.customer_unit_price));
      if (!description || (!internalUnitCost && !customerUnitPrice)) return;
      const existing = draft.lines.find((line) => line.category === category && line.description.toLowerCase() === description.toLowerCase());
      const line = existing || (draft.lines.length === 1 && !draft.lines[0].description && !numericValue(draft.lines[0].internalUnitCost) && !numericValue(draft.lines[0].customerUnitPrice) ? draft.lines[0] : newCommercialLine());
      line.category = category; line.description = description; line.quantity = String(quantity || 1);
      if (internalUnitCost) line.internalUnitCost = String(internalUnitCost);
      if (customerUnitPrice) line.customerUnitPrice = String(customerUnitPrice);
      const namedPerson = actors().find((person) => String(person.name || '').toLowerCase() === String(item?.person_name || '').toLowerCase());
      if (namedPerson) line.personId = namedPerson.person_id;
      if (!existing && !draft.lines.includes(line)) draft.lines.push(line);
    });
    draft.wording = '';
  }

  async function continueQuoteInterview(row, session, draft, command) {
    const interview = session.quoteInterview;
    const explicitFinish = /\b(?:stop|finish|end)(?:\s+(?:and\s+)?(?:generate|create|finish))?\s+(?:the\s+)?quote\b|\bquote\s+(?:finished|ended|done)\b|\bthat(?:'s| is)\s+(?:it|all)\b/i.test(command);
    const extraction = explicitFinish ? { quote_complete_requested: true, next_stage: 'review' } : await extractQuoteTurn(row, draft, interview, command);
    applyQuoteExtraction(draft, extraction);
    const requestedStage = String(extraction?.next_stage || '');
    const currentStageIndex = Math.max(0, quoteInterviewStages.indexOf(interview.stage));
    const requestedStageIndex = quoteInterviewStages.indexOf(requestedStage);
    interview.stage = extraction?.quote_complete_requested === true || explicitFinish
      ? 'review'
      : quoteInterviewStages[requestedStageIndex > currentStageIndex ? requestedStageIndex : Math.min(currentStageIndex + 1, quoteInterviewStages.length - 1)];
    interview.turns.push({ text: command, extraction, createdAt: new Date().toISOString() });
    interview.provider = extraction?.provider || interview.provider;
    interview.active = interview.stage !== 'review';
    draft.wording = generatedCustomerWording(row, draft);
    const message = quoteInterviewQuestion(interview.stage, row);
    pilotMessage(session, 'pilot', message); render();
    return { handled: true, status: interview.active ? 'quote_interview_listening' : 'quote_review_ready', label: interview.active ? `Quotation interview · ${label(interview.stage)}` : 'Quotation ready for review', message, continue_voice: interview.active };
  }

  async function handleCustomerPilotInstruction(rawText) {
    const row = selected(); const session = customerPilotSession(row);
    if (!row || !session) return { handled: false };
    readCommercialForm(document.querySelector('[data-srw-form="commercial"]'));
    const text = String(rawText || '').trim();
    if (!text) return;
    pilotMessage(session, 'user', text);
    const command = text.replace(/^\s*(?:hey\s+)?pilot[,:]?\s*/i, '').trim();
    const lower = command.toLowerCase();
    let draft = commercialDraft(row);
    session.error = ''; session.pendingAction = null;

    if (session.activeMode === 'new_quote' && session.quoteInterview?.active) {
      return continueQuoteInterview(row, session, draft, command);
    }

    if (session.activeMode === 'new_quote' && session.quoteInterview?.stage === 'review' && /\b(?:send|email|issue)\b.*\b(?:quote|quotation|estimate|it)\b|\b(?:send|email)\s+(?:it|this)\b/i.test(lower)) {
      const latestSavedQuote = (row.work_feed?.events || []).slice().reverse().find((item) => item.kind === 'quote_draft' && item.details?.commercial_record);
      if ((!draft.scope || draft.mode !== 'new_quote') && latestSavedQuote) {
        draft = commercialDraftFromSavedEvent(row, latestSavedQuote);
        state.commercialDrafts[row.opportunity_id] = draft;
      }
      const wording = draft.wording || generatedCustomerWording(row, draft);
      const firstName = String(row.contact?.name || 'there').trim().split(/\s+/)[0];
      const subject = `Your quotation${draft.reference ? ` ${draft.reference}` : ''}`;
      const body = [`Hi ${firstName},`, '', 'We have prepared your quotation for the work discussed.', '', wording, '', 'If you would like to proceed, please reply to this email or send us a WhatsApp message and we will take it from there.', '', 'Kind regards'].join('\n');
      const message = row.contact?.email
        ? `I’ve prepared the customer email and included the reviewed quotation details. Check the exact email below, then approve it before anything is sent to ${row.contact.email}.`
        : 'I’ve prepared the customer email and quotation details. Add the customer email address before approving any send.';
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'quote_email_prepared', label: 'Quotation email prepared', message, action: 'prepare_quote_email', email_to: row.contact?.email || '', email_subject: subject, email_body: body };
    }

    if (/\b(?:status|summary|what do (?:we|you) know|where are we|next action)\b/.test(lower)) {
      const message = `${row.contact?.name || 'This customer'} is at ${label(row.work_feed?.current_stage || row.stage || 'enquiry')}. ${row.enquiry ? `Recorded enquiry: ${row.enquiry}` : ''} ${row.relationship?.next_action ? `Next action: ${row.relationship.next_action}${row.relationship.next_action_due ? ` by ${row.relationship.next_action_due}` : ''}.` : ''}`.replace(/\s+/g, ' ').trim();
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'customer_context_read', label: 'Customer context read', message };
    } else if (/\b(job|work)\s+(is\s+)?(complete|completed|finished|done)\b/.test(lower) || /\bcompleted\s+(the\s+)?job\b/.test(lower)) {
      const detail = pilotIntentRemainder(command, /.*?\b(?:job|work)\s+(?:is\s+)?(?:complete|completed|finished|done)\b/i);
      session.pendingAction = { kind: 'work_completed', title: 'Job completed', summary: detail || command, lifecycleStage: 'completed' };
      const message = `I’ve prepared a “Job completed” update for ${row.contact?.name}. Confirm it below to append it to this customer feed.`;
      pilotMessage(session, 'pilot', message);
      render();
      return { handled: true, status: 'approval_required', label: 'Job completion prepared', message };
    } else if (/\binvoice\b/.test(lower)) {
      session.activeMode = 'invoice_add_on';
      draft.mode = 'invoice_add_on';
      draft.title = draft.title || `Invoice update — ${row.title || row.contact?.name || 'customer job'}`;
      const detail = pilotIntentRemainder(command, /.*?\b(?:send|prepare|create|make)?\s*(?:the\s+)?invoice(?:\s+add-on)?\b/i);
      if (detail) draft.scope = [draft.scope, detail].filter(Boolean).join('\n');
      const message = 'I’ve opened an invoice add-on draft for this customer. Add or dictate the charge lines, then review and save it. Speaking cannot send an invoice externally; exact send approval remains separate.';
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'draft_ready', label: 'Invoice add-on opened', message };
    } else if (/\bquote\s+(variation|add-on|addon)\b|\bvariation\b/.test(lower)) {
      session.activeMode = 'quote_variation';
      draft.mode = 'quote_variation';
      draft.title = draft.title || `Quote variation — ${row.title || row.contact?.name || 'customer job'}`;
      const detail = pilotIntentRemainder(command, /.*?\b(?:quote\s+)?(?:variation|add-on|addon)\b/i);
      if (detail) draft.scope = [draft.scope, detail].filter(Boolean).join('\n');
      const message = 'I’ve opened a quote variation attached to this customer. Dictate the changed scope and prices, or add charge lines below.';
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'draft_ready', label: 'Quote variation opened', message };
    } else if (/\bquote\b|\bestimate\b/.test(lower)) {
      session.activeMode = 'new_quote';
      draft.mode = 'new_quote';
      draft.title = 'Quotation'; draft.scope = ''; draft.internalNote = ''; draft.lines = [newCommercialLine()]; draft.wording = ''; draft.quoteScopeSummary = ''; draft.quoteScopeItems = []; draft.quoteExclusions = []; draft.quoteDuration = '';
      session.quoteInterview = { active: true, stage: 'scope', turns: [], provider: '', startedAt: new Date().toISOString() };
      const message = quoteInterviewQuestion('scope', row);
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'quote_interview_listening', label: 'Quotation interview started', message, continue_voice: true };
    } else if (/\bnote\b/.test(lower)) {
      session.activeMode = 'internal_note';
      draft.mode = 'internal_note';
      const detail = pilotIntentRemainder(command, /.*?\b(?:make|add|create|record|take)?\s*(?:this|a)?\s*note\b/i);
      draft.title = draft.title || `Pilot note — ${new Date().toLocaleDateString()}`;
      if (detail) draft.internalNote = [draft.internalNote, detail].filter(Boolean).join('\n');
      const message = detail ? 'I added that to an internal note for this customer. Review it below and save it to the feed.' : 'I opened an internal note for this customer. Tell me what you want recorded.';
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'draft_ready', label: 'Customer note opened', message };
    } else if (/\b(new\s+)?(job|project)\b/.test(lower)) {
      session.activeMode = 'new_job';
      draft.mode = 'new_job';
      draft.title = draft.title || `Job — ${row.title || row.contact?.name || 'customer work'}`;
      const detail = pilotIntentRemainder(command, /.*?\b(?:new\s+)?(?:job|project)\b/i);
      if (detail) draft.scope = [draft.scope, detail].filter(Boolean).join('\n');
      const message = 'I’ve opened a new job draft attached to this customer. Tell me the scope and cost lines, then review it below.';
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'draft_ready', label: 'Customer job opened', message };
    } else if (session.activeMode === 'internal_note' && draft.mode === 'internal_note') {
      draft.title = draft.title || `Pilot note — ${new Date().toLocaleDateString()}`;
      draft.internalNote = [draft.internalNote, command].filter(Boolean).join('\n');
      const message = 'I added that to this customer’s internal note.';
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'draft_ready', label: 'Customer note updated', message };
    } else if (session.activeMode) {
      draft.scope = [draft.scope, command].filter(Boolean).join('\n');
      const message = `I added that to the ${commercialModes.find(([mode]) => mode === draft.mode)?.[1]?.toLowerCase() || 'customer draft'} scope.`;
      pilotMessage(session, 'pilot', message); render();
      return { handled: true, status: 'draft_ready', label: 'Customer draft updated', message };
    }
    return { handled: false };
  }

  function formatAttachmentSize(bytes) {
    const size = Number(bytes || 0);
    if (!size) return '';
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
    return `${(size / (1024 * 1024)).toFixed(size < 10 * 1024 * 1024 ? 1 : 0)} MB`;
  }

  function attachmentTypeLabel(item) {
    const extension = String(item?.name || '').split('.').pop()?.toUpperCase();
    if (extension && extension !== String(item?.name || '').toUpperCase() && extension.length <= 5) return extension;
    const mediaType = String(item?.type || item?.media_type || '');
    if (mediaType.includes('pdf')) return 'PDF';
    if (mediaType.startsWith('image/')) return 'IMAGE';
    return 'FILE';
  }

  function addCustomerPilotAttachments(files) {
    const session = customerPilotSession();
    const added = Array.from(files || []).slice(0, Math.max(0, 20 - session.attachments.length));
    added.forEach((file) => {
      const isImage = String(file.type || '').startsWith('image/');
      session.attachments.push({ id: `pilot-attachment-${Date.now()}-${Math.random().toString(16).slice(2)}`, file, name: file.name || 'customer-file', type: file.type, size: file.size, previewUrl: isImage ? URL.createObjectURL(file) : '', uploaded: null });
    });
    if (added.length) pilotMessage(session, 'pilot', `${added.length} file${added.length === 1 ? ' is' : 's are'} attached and will be preserved with the next saved update to this customer’s work feed.`);
    render();
  }

  async function uploadCustomerPilotAttachments(row, actor) {
    const session = customerPilotSession(row); const uploaded = [];
    for (const item of session.attachments || []) {
      if (!item.uploaded) {
        const form = new FormData(); form.append('file', item.file, item.name); form.append('recorded_by_person_id', actor);
        const result = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/opportunities/${encodeURIComponent(row.opportunity_id)}/work-feed/attachments`, { method: 'POST', body: form });
        item.uploaded = result.attachment;
      }
      uploaded.push(item.uploaded);
    }
    return uploaded;
  }

  function clearCustomerPilotAttachments(row) {
    const session = customerPilotSession(row);
    (session.attachments || []).forEach((item) => { if (item.previewUrl) { try { URL.revokeObjectURL(item.previewUrl); } catch (_) { /* Best-effort preview cleanup. */ } } });
    session.attachments = [];
  }

  function customerPilotConversation(row) {
    const session = customerPilotSession(row);
    const attachments = (session.attachments || []).map((item) => `<figure class="${item.previewUrl ? 'is-image' : 'is-file'}">${item.previewUrl ? `<img src="${esc(item.previewUrl)}" alt="${esc(item.name)}">` : `<span class="srw-pilot-file-badge" aria-hidden="true">${esc(attachmentTypeLabel(item))}</span>`}<figcaption><b>${esc(item.name)}</b>${item.size ? `<small>${esc(formatAttachmentSize(item.size))}</small>` : ''}</figcaption><button type="button" data-srw-pilot-remove-attachment="${esc(item.id)}" aria-label="Remove ${esc(item.name)}">×</button></figure>`).join('');
    const pending = session.pendingAction ? `<div class="srw-pilot-pending"><b>${esc(session.pendingAction.title)}</b><p>${esc(session.pendingAction.summary)}</p><button type="button" class="primary" data-srw-pilot-confirm-action>Confirm and add to customer feed</button></div>` : '';
    const quoteProgress = session.activeMode === 'new_quote' && session.quoteInterview
      ? `<span class="srw-customer-pilot-progress">Quote ${Math.min(quoteInterviewStages.indexOf(session.quoteInterview.stage) + 1, quoteInterviewStages.length)}/${quoteInterviewStages.length} · ${esc(session.quoteInterview.active ? label(session.quoteInterview.stage) : 'ready to review')}</span>`
      : '';
    const latestPilotMessage = [...(session.messages || [])].reverse().find((item) => item.role === 'pilot')?.text
      || `Pilot is ready for ${row.contact?.name || 'this customer'}.`;
    const actionOptions = commercialModes.map(([value, text]) => `<option value="${esc(value)}" ${session.activeMode === value ? 'selected' : ''}>${esc(text)}</option>`).join('');
    return `<aside class="srw-customer-pilot-footer" data-srw-customer-pilot-footer data-aion-customer-scoped-pilot-runtime="${esc(row.opportunity_id)}"><div class="srw-customer-pilot-status" data-aion-customer-pilot-voice-status data-state="idle"><span class="srw-pilot-voice-dot" aria-hidden="true"></span><div><b data-aion-customer-pilot-voice-title>Microphone ready</b><small data-aion-customer-pilot-voice-detail>Locked to ${esc(row.contact?.name || 'this customer')} and this job.</small></div><span class="srw-customer-pilot-latest"><b>Pilot</b> ${esc(latestPilotMessage)}</span>${quoteProgress}</div>${attachments ? `<div class="srw-pilot-attachments">${attachments}</div>` : ''}${pending}<div class="srw-customer-pilot-composer"><div class="srw-customer-pilot-tools"><label title="Upload a customer file">＋ Upload file<input type="file" multiple data-srw-pilot-files></label><label title="Take a photo">⌁ Take photo<input type="file" accept="image/*" capture="environment" data-srw-pilot-camera></label></div><textarea rows="1" data-aion-pilot-mission-input aria-label="Message Pilot about ${esc(row.contact?.name || 'this customer')}" placeholder="Ask Pilot about this customer or tell Pilot what to do…"></textarea><button type="button" data-aion-pilot-create-draft-mission>Send</button><select class="srw-customer-pilot-action" data-srw-pilot-action aria-label="Choose what to create with Pilot"><option value="">New action…</option>${actionOptions}</select><button type="button" class="primary srw-customer-pilot-talk" data-srw-pilot-open>🎙 Talk to Pilot</button></div></aside>`;
  }

  function attachmentGallery(item) {
    const attachments = (item.attachments || []).filter((attachment) => attachment.source_reference);
    if (!attachments.length) return '';
    return `<div class="srw-feed-attachments">${attachments.map((attachment) => {
      const reference = String(attachment.source_reference); const url = reference.startsWith('http') ? reference : `${API}${reference}`;
      if (String(attachment.media_type || '').startsWith('image/')) return `<a class="srw-feed-image" href="${esc(url)}" target="_blank" rel="noopener"><img src="${esc(url)}" alt="${esc(attachment.name || 'Customer image')}"><span>${esc(attachment.name || 'Customer image')}</span></a>`;
      return `<a class="srw-feed-file" href="${esc(url)}" target="_blank" rel="noopener"><span>${esc(attachmentTypeLabel(attachment))}</span><b>${esc(attachment.name || 'Customer file')}</b><small>Open file</small></a>`;
    }).join('')}</div>`;
  }

  const commercialModes = [
    ['internal_note', 'New note'],
    ['new_job', 'New job / project'],
    ['new_quote', 'New quote'],
    ['quote_variation', 'Quote variation / add-on'],
    ['invoice_add_on', 'Invoice add-on'],
  ];
  const commercialCategories = [
    ['labour', 'Labour'], ['materials', 'Materials'], ['parking', 'Parking'],
    ['congestion_charge', 'Congestion charge'], ['ulez', 'ULEZ / local charge'],
    ['supplier_subcontractor', 'Supplier / subcontractor'], ['scaffolding', 'Scaffolding'],
    ['skip_waste', 'Skip / waste'], ['other', 'Other'],
  ];
  const workLifecycleStages = [
    'enquiry', 'qualification', 'appointment', 'survey', 'quote', 'negotiation',
    'won', 'scheduled', 'procurement', 'in_progress', 'completed', 'invoiced',
    'paid', 'review_requested', 'closed', 'lost',
  ];
  let commercialLineSequence = 0;

  function newCommercialLine() {
    commercialLineSequence += 1;
    return { id: `commercial-line-${Date.now()}-${commercialLineSequence}`, category: 'labour', description: '', quantity: '1', internalUnitCost: '0.00', customerUnitPrice: '0.00', personId: '' };
  }

  function defaultCommercialDraft(row) {
    syncSignedInActor();
    return {
      mode: '', reference: '', title: '', scope: '', internalNote: '',
      recordedBy: state.actorId || '', lines: [newCommercialLine()], taxRate: '20',
      terms: 'Payment is due according to the agreed schedule.', wording: '',
      customerId: row?.opportunity_id || '',
    };
  }

  function commercialDraft(row = selected()) {
    if (!row) return null;
    if (!state.commercialDrafts[row.opportunity_id]) state.commercialDrafts[row.opportunity_id] = defaultCommercialDraft(row);
    return state.commercialDrafts[row.opportunity_id];
  }

  function activateCommercialMode(mode, { fresh = false, announce = true } = {}) {
    const row = selected(); if (!row || !commercialModes.some(([value]) => value === mode)) return;
    let draft = commercialDraft(row); const wasCollapsed = !draft.mode;
    if (fresh) { draft = defaultCommercialDraft(row); state.commercialDrafts[row.opportunity_id] = draft; }
    draft.mode = mode;
    const session = customerPilotSession(row); session.activeMode = mode; session.pendingAction = null;
    let message = '';
    if (mode === 'new_quote') {
      if (fresh || wasCollapsed) {
        draft.title = 'Quotation'; draft.scope = ''; draft.internalNote = ''; draft.lines = [newCommercialLine()]; draft.wording = ''; draft.quoteScopeSummary = ''; draft.quoteScopeItems = []; draft.quoteExclusions = []; draft.quoteDuration = '';
      }
      session.quoteInterview = { active: true, stage: 'scope', turns: [], provider: '', startedAt: new Date().toISOString() };
      message = quoteInterviewQuestion('scope', row);
    } else if (mode === 'internal_note') {
      draft.title = draft.title || `Pilot note — ${new Date().toLocaleDateString()}`;
      session.quoteInterview = null;
      message = 'Tell me what you want recorded in this customer’s internal note.';
    } else if (mode === 'new_job') {
      draft.title = draft.title || `Job — ${row.title || row.contact?.name || 'customer work'}`;
      session.quoteInterview = null;
      message = 'Tell me the scope of the new job or project, then the costs and any important conditions.';
    } else if (mode === 'quote_variation') {
      draft.title = draft.title || `Quote variation — ${row.title || row.contact?.name || 'customer job'}`;
      session.quoteInterview = null;
      message = 'Tell me what has changed from the original quote and any price or timing difference.';
    } else if (mode === 'invoice_add_on') {
      draft.title = draft.title || `Invoice update — ${row.title || row.contact?.name || 'customer job'}`;
      session.quoteInterview = null;
      message = 'Tell me the additional invoice charge and why it belongs to this job.';
    }
    if (announce) pilotMessage(session, 'pilot', message);
    state.customerTab = 'work'; state.error = ''; state.message = ''; render();
    global.requestAnimationFrame(() => document.querySelector('[data-srw-form="commercial"]')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }));
  }

  function collapseCommercialWorkbench() {
    const row = selected(); if (!row) return;
    const draft = commercialDraft(row); draft.mode = '';
    const session = customerPilotSession(row); session.activeMode = ''; session.quoteInterview = null;
    render();
  }

  function commercialDraftFromSavedEvent(row, event) {
    const record = event?.details?.commercial_record || {};
    const customerFacing = event?.details?.customer_facing || {};
    const draft = defaultCommercialDraft(row);
    draft.mode = record.mode || (event?.kind === 'invoice_draft' ? 'invoice_add_on' : 'new_quote');
    draft.reference = record.reference || '';
    draft.title = record.title || event?.title || 'Quotation';
    draft.scope = record.scope || customerFacing.scope || '';
    draft.quoteScopeSummary = record.scope_summary || '';
    draft.quoteScopeItems = Array.isArray(record.scope_items) ? [...record.scope_items] : [];
    draft.quoteExclusions = Array.isArray(record.exclusions) ? [...record.exclusions] : [];
    draft.quoteDuration = record.duration || '';
    draft.internalNote = record.internal_note || '';
    draft.taxRate = String(record.totals?.tax_rate ?? customerFacing.tax_rate ?? '20');
    draft.terms = record.terms || customerFacing.terms || 'Payment is due according to the agreed schedule.';
    draft.wording = customerFacing.wording || '';
    draft.recordedBy = state.actorId || event?.recorded_by_person_id || '';
    draft.editingEventId = event?.event_id || '';
    draft.lines = (Array.isArray(record.lines) ? record.lines : []).map((line) => ({
      id: newCommercialLine().id, category: line.category || 'other', description: line.description || '',
      quantity: String(line.quantity ?? 1), internalUnitCost: String(line.internal_unit_cost ?? 0),
      customerUnitPrice: String(line.customer_unit_price ?? line.unit_price ?? 0), personId: line.person_id || '',
    }));
    if (!draft.lines.length) draft.lines = [newCommercialLine()];
    return draft;
  }

  function numericValue(value) {
    const parsed = Number(String(value ?? '').replace(/[^0-9.-]/g, ''));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function roundMoney(value) {
    return Math.round((numericValue(value) + Number.EPSILON) * 100) / 100;
  }

  function commercialCurrency(row = selected()) {
    const currency = String(row?.attribution?.currency || row?.currency || 'GBP').trim().toUpperCase();
    return /^[A-Z]{3}$/.test(currency) ? currency : 'GBP';
  }

  function money(value) {
    try {
      return new Intl.NumberFormat('en-GB', { style: 'currency', currency: commercialCurrency(), minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(roundMoney(value));
    } catch (_) {
      return `${commercialCurrency()} ${roundMoney(value).toFixed(2)}`;
    }
  }

  function commercialTotals(draft) {
    const lines = (draft?.lines || []).map((line) => {
      const quantity = Math.max(0, numericValue(line.quantity));
      const internalTotal = roundMoney(quantity * numericValue(line.internalUnitCost));
      const customerTotal = roundMoney(quantity * numericValue(line.customerUnitPrice));
      return { ...line, quantity, internalTotal, customerTotal };
    });
    const internalCost = roundMoney(lines.reduce((sum, line) => sum + line.internalTotal, 0));
    const net = roundMoney(lines.reduce((sum, line) => sum + line.customerTotal, 0));
    const taxRate = Math.max(0, numericValue(draft?.taxRate));
    const tax = roundMoney(net * taxRate / 100);
    const gross = roundMoney(net + tax);
    const grossProfit = roundMoney(net - internalCost);
    const grossMargin = net > 0 ? roundMoney(grossProfit / net * 100) : 0;
    return { lines, internalCost, net, taxRate, tax, gross, grossProfit, grossMargin };
  }

  function generatedCustomerWording(row, draft, totals = commercialTotals(draft)) {
    const heading = draft.mode === 'invoice_add_on' ? 'Invoice add-on' : draft.mode === 'quote_variation' ? 'Quote variation' : draft.mode === 'new_job' ? 'Proposed work' : 'Quotation';
    const chargeLines = totals.lines.filter((line) => line.description || line.customerTotal).map((line) => `${line.description || label(line.category)} — ${line.quantity} × ${money(line.customerUnitPrice)} = ${money(line.customerTotal)}`);
    const displayTitle = /^\s*(?:quote|quotation|estimate)\s*$/i.test(draft.title || '') ? '' : draft.title;
    return [
      `${heading}${draft.reference ? ` ${draft.reference}` : ''} for ${row.contact?.name || 'customer'}`,
      displayTitle, '', 'Scope of work', draft.scope,
      draft.quoteDuration ? `Estimated duration: ${draft.quoteDuration}` : '',
      ...(draft.quoteExclusions?.length ? ['', 'Exclusions and customer responsibilities', ...draft.quoteExclusions.map((item) => `- ${item}`)] : []),
      '', 'Charges',
      ...(chargeLines.length ? chargeLines : ['No charge lines added yet.']), '',
      `Net: ${money(totals.net)}`, `${totals.taxRate}% VAT / tax: ${money(totals.tax)}`,
      `Total: ${money(totals.gross)}`, '', 'Terms and payment schedule', draft.terms,
    ].filter((part, index, parts) => part !== undefined && part !== null && (part !== '' || parts[index - 1] !== '')).join('\n').trim();
  }

  function readCommercialForm(form) {
    const row = selected(); const draft = commercialDraft(row);
    if (!form || !draft) return draft;
    const field = (name) => form.elements.namedItem(name);
    const remember = (name, property) => { const element = field(name); if (element) draft[property] = element.value; };
    remember('reference', 'reference'); remember('title', 'title'); remember('scope', 'scope');
    remember('internal_note', 'internalNote'); remember('tax_rate', 'taxRate');
    remember('terms', 'terms'); remember('wording', 'wording');
    if (field('actor')) draft.recordedBy = field('actor').value || state.actorId;
    const lineRows = Array.from(form.querySelectorAll('[data-srw-cost-line]'));
    if (lineRows.length) draft.lines = lineRows.map((lineRow) => ({
      id: lineRow.dataset.srwCostLine || newCommercialLine().id,
      category: lineRow.querySelector('[data-srw-line-field="category"]')?.value || 'other',
      description: lineRow.querySelector('[data-srw-line-field="description"]')?.value || '',
      quantity: lineRow.querySelector('[data-srw-line-field="quantity"]')?.value || '0',
      internalUnitCost: lineRow.querySelector('[data-srw-line-field="internal_unit_cost"]')?.value || '0',
      customerUnitPrice: lineRow.querySelector('[data-srw-line-field="customer_unit_price"]')?.value || '0',
      personId: lineRow.querySelector('[data-srw-line-field="person_id"]')?.value || '',
    }));
    return draft;
  }

  function laterLifecycleStage(current, requested) {
    const currentIndex = workLifecycleStages.indexOf(current);
    const requestedIndex = workLifecycleStages.indexOf(requested);
    if (currentIndex < 0) return requested;
    return requestedIndex > currentIndex ? requested : current;
  }

  function commercialWorkbench(row) {
    const draft = commercialDraft(row); const expanded = Boolean(draft.mode); const noteMode = draft.mode === 'internal_note';
    const totals = commercialTotals(draft);
    const modeButtons = commercialModes.map(([value, text]) => `<button type="button" class="${draft.mode === value ? 'active' : ''}" data-srw-commercial-mode="${value}" aria-pressed="${draft.mode === value}">${esc(text)}</button>`).join('');
    const lines = (draft.lines || []).map((line, index) => `<div class="srw-cost-line" data-srw-cost-line="${esc(line.id)}"><label>Category<select name="${esc(line.id)}_category" data-srw-line-field="category" data-srw-commercial-recalculate>${commercialCategories.map(([value, text]) => `<option value="${value}" ${selectedOption(value, line.category)}>${esc(text)}</option>`).join('')}</select></label><label class="srw-line-description">Description<input name="${esc(line.id)}_description" data-srw-line-field="description" value="${esc(line.description)}" required placeholder="Work, material or charge"></label><label>Quantity<input name="${esc(line.id)}_quantity" type="number" min="0" step="0.01" data-srw-line-field="quantity" data-srw-commercial-recalculate value="${esc(line.quantity)}" required></label><label>Internal unit cost<input name="${esc(line.id)}_internal_cost" type="number" min="0" step="0.01" data-srw-line-field="internal_unit_cost" data-srw-commercial-recalculate value="${esc(line.internalUnitCost)}" required></label><label>Customer unit price<input name="${esc(line.id)}_customer_price" type="number" min="0" step="0.01" data-srw-line-field="customer_unit_price" data-srw-commercial-recalculate value="${esc(line.customerUnitPrice)}" required></label><label class="srw-labour-person ${line.category === 'labour' ? '' : 'hidden'}">Person<select name="${esc(line.id)}_person" data-srw-line-field="person_id" ${line.category === 'labour' ? '' : 'disabled'}><option value="">Not assigned</option>${actorOptions(line.personId)}</select></label><div class="srw-line-total"><small>Customer line total</small><b>${money(totals.lines[index]?.customerTotal || 0)}</b></div><button type="button" data-srw-remove-cost-line="${esc(line.id)}" aria-label="Remove cost line">Remove</button></div>`).join('');
    const safeLines = totals.lines.filter((line) => line.description || line.customerTotal).map((line) => `<div><span>${esc(line.description || label(line.category))}</span><span>${esc(line.quantity)} × ${esc(money(line.customerUnitPrice))}</span><b>${esc(money(line.customerTotal))}</b></div>`).join('') || '<p>No customer charge lines added yet.</p>';
    const customerIdentity = `<div class="srw-commercial-customer"><span>SELECTED CUSTOMER</span><b>${esc(row.contact?.name || 'Customer')}</b><small>${esc(row.contact?.email || '')}${row.contact?.phone ? ` · ${esc(row.contact.phone)}` : ''}</small><small>${esc(row.title || '')}</small></div>`;
    const editor = noteMode ? `<div class="srw-two"><label>Note title<input name="title" required value="${esc(draft.title)}"></label>${recordedByField()}</div><label>Internal note / details<textarea name="internal_note" rows="6" required>${esc(draft.internalNote)}</textarea></label>` : `${customerIdentity}<div class="srw-two"><label>Internal reference / job number<input name="reference" value="${esc(draft.reference)}" placeholder="For example Q-001"></label>${recordedByField()}</div><label>Job / quote title<input name="title" required value="${esc(draft.title)}"></label><label>Scope of work<textarea name="scope" rows="5" required>${esc(draft.scope)}</textarea></label><label>Internal notes <small>Never shown in the customer preview</small><textarea name="internal_note" rows="4">${esc(draft.internalNote)}</textarea></label><section class="srw-costs"><header><div><b>Private cost breakdown</b><small>Internal costs and margin stay inside Tessaris.</small></div><button type="button" data-srw-add-cost-line>+ Add cost line</button></header>${lines}</section><div class="srw-two"><label>VAT / tax percentage<input type="number" name="tax_rate" min="0" step="0.01" data-srw-commercial-recalculate value="${esc(draft.taxRate)}"></label><label>Terms and payment schedule<textarea name="terms" rows="4">${esc(draft.terms)}</textarea></label></div><section class="srw-private-totals"><div><span>Internal cost</span><b>${money(totals.internalCost)}</b></div><div><span>Customer net</span><b>${money(totals.net)}</b></div><div><span>VAT / tax</span><b>${money(totals.tax)}</b></div><div><span>Customer gross</span><b>${money(totals.gross)}</b></div><div><span>Gross profit</span><b>${money(totals.grossProfit)}</b></div><div><span>Gross margin</span><b>${totals.grossMargin.toFixed(2)}%</b></div></section><section class="srw-customer-preview"><header><div><span>CUSTOMER-FACING PREVIEW</span><b>Safe to copy into a quote or email after review</b></div><button type="button" data-srw-generate-wording>Generate / refresh wording</button></header><div class="srw-preview-scope"><b>${esc(draft.title || 'Untitled work')}</b><p>${esc(draft.scope || 'Add the scope of work above.')}</p></div><div class="srw-preview-lines">${safeLines}</div><div class="srw-preview-totals"><span>Net <b>${money(totals.net)}</b></span><span>${esc(totals.taxRate)}% VAT / tax <b>${money(totals.tax)}</b></span><span>Total <b>${money(totals.gross)}</b></span></div><p><b>Terms</b> ${esc(draft.terms)}</p><label>Generated customer wording<textarea name="wording" rows="12">${esc(draft.wording || generatedCustomerWording(row, draft, totals))}</textarea></label><small>This preview excludes internal costs, labour cost rates, internal notes, profit and margin.</small></section>`;
    return `<section class="srw-commercial-workbench ${expanded ? 'is-expanded' : 'is-collapsed'}"><header><div><span>CUSTOMER COMMERCIAL WORKBENCH</span><h3>Notes, jobs, quotes and add-ons</h3><p>${expanded ? `Everything saved here stays attached to ${esc(row.contact?.name || 'this customer')}.` : 'Choose what you want to create. Only the selected editor will open.'}</p></div>${expanded ? '<button type="button" data-srw-collapse-commercial>Close editor</button>' : ''}</header><nav class="srw-commercial-modes">${modeButtons}</nav>${expanded ? `<form data-srw-form="commercial">${noteMode ? customerIdentity : ''}${editor}<footer><button type="button" data-srw-reset-commercial>Reset draft</button><button class="primary" type="submit">${noteMode ? 'Save note to customer feed' : 'Save draft to customer feed'}</button></footer></form>` : ''}</section>`;
  }

  function customerAddress(row) {
    const answers = row?.qualification?.answers || {};
    return row?.contact?.address
      || row?.contact?.full_property_address
      || answers.full_property_address
      || answers.property_address
      || answers.location
      || row?.attribution?.address
      || row?.attribution?.property_address
      || '';
  }

  function customerRelationship(row) {
    const relationship = row.relationship || {};
    const owner = actorName(row.owner_person_id) || 'Unassigned';
    const due = relationship.next_action_due ? new Date(`${relationship.next_action_due}T00:00:00`).toLocaleDateString() : '';
    const tags = Array.isArray(relationship.tags) ? relationship.tags : [];
    return `<details class="srw-relationship"><summary><div><span>RELATIONSHIP</span><b>${esc(label(relationship.status || 'lead'))}</b></div><div><small>Lifecycle</small><b>${esc(label(row.work_feed?.current_stage || row.stage || 'enquiry'))}</b></div><div><small>Responsible</small><b>${esc(owner)}</b></div><div class="srw-relationship-next"><small>Next action${due ? ` · ${esc(due)}` : ''}</small><b>${esc(relationship.next_action || 'Not set')}</b></div><span aria-hidden="true">⌄</span></summary><form data-srw-form="relationship"><div class="srw-relationship-grid"><label>Relationship status<select name="relationship_status"><option value="lead" ${selectedOption('lead', relationship.status)}>Lead</option><option value="prospect" ${selectedOption('prospect', relationship.status)}>Prospect</option><option value="active_customer" ${selectedOption('active_customer', relationship.status)}>Active customer</option><option value="active_job" ${selectedOption('active_job', relationship.status)}>Active job</option><option value="repeat_customer" ${selectedOption('repeat_customer', relationship.status)}>Repeat customer</option><option value="on_hold" ${selectedOption('on_hold', relationship.status)}>On hold</option><option value="completed" ${selectedOption('completed', relationship.status)}>Completed</option><option value="lost" ${selectedOption('lost', relationship.status)}>Lost</option></select></label><label>Responsible person<select name="owner_person_id" required><option value="">Select person</option>${actorOptions(row.owner_person_id)}</select></label><label>Priority<select name="priority"><option value="normal" ${selectedOption('normal', relationship.priority)}>Normal</option><option value="priority" ${selectedOption('priority', relationship.priority)}>Priority</option><option value="urgent" ${selectedOption('urgent', relationship.priority)}>Urgent</option></select></label><label>Preferred contact<select name="preferred_channel"><option value="unspecified" ${selectedOption('unspecified', relationship.preferred_channel)}>Not specified</option><option value="email" ${selectedOption('email', relationship.preferred_channel)}>Email</option><option value="telephone" ${selectedOption('telephone', relationship.preferred_channel)}>Telephone</option><option value="sms" ${selectedOption('sms', relationship.preferred_channel)}>SMS</option><option value="whatsapp" ${selectedOption('whatsapp', relationship.preferred_channel)}>WhatsApp</option><option value="in_app" ${selectedOption('in_app', relationship.preferred_channel)}>In app</option></select></label><label class="wide">Customer / job address<input name="address" value="${esc(customerAddress(row))}" placeholder="Add the address AION should use"></label><label class="wide">Next action<input name="next_action" value="${esc(relationship.next_action || '')}" placeholder="For example: confirm start date or collect remaining 50%"></label><label>Due date<input type="date" name="next_action_due" value="${esc(relationship.next_action_due || '')}"></label><label>Tags<input name="tags" value="${esc(tags.join(', '))}" placeholder="Repeat customer, roofing"></label></div>${recordedByField('Updated by')}<footer><small>Saved natively for Pilot, Sales, Support, Operations, Finance and Communications.</small><button class="primary" type="submit">Save relationship details</button></footer></form></details>`;
  }

  async function optionalRequest(path) {
    try { return await request(path); } catch (_) { return null; }
  }

  async function loadCustomerFinance(row = selected()) {
    if (!row || state.customerFinance.loading) return;
    const finance = state.customerFinance;
    finance.loading = true; finance.error = ''; render();
    const workspace = encodeURIComponent(state.workspaceId);
    try {
      const [catalog, completion, inbox, xero, exportsResult, ledgerResult, reconciliationResult] = await Promise.all([
        optionalRequest(`/api/aion/finance-sales/${workspace}`),
        optionalRequest(`/api/aion/sales-completion/${workspace}`),
        optionalRequest(`/api/aion/business/finance-inbox/${workspace}`),
        optionalRequest(`/api/aion/integrations/xero/${workspace}/status`),
        optionalRequest(`/api/aion/integrations/xero/${workspace}/sales-invoice-exports`),
        optionalRequest(`/api/aion/business/department-pilots/finance-ledger?workspace_id=${workspace}`),
        optionalRequest(`/api/aion/business/department-pilots/finance-transaction-reconciliation?workspace_id=${workspace}`),
      ]);
      let xeroInvoices = [];
      const ledger = ledgerResult?.ledger;
      if (ledger?.ledger_id) {
        const records = await optionalRequest(`/api/aion/business/department-pilots/finance-ledger-records?workspace_id=${workspace}&ledger_id=${encodeURIComponent(ledger.ledger_id)}&collection=invoices&limit=1000`);
        xeroInvoices = records?.records || [];
      }
      Object.assign(finance, {
        loaded: true, catalog: catalog || null, completion: completion || null,
        inbox: inbox?.inbox || null, xero: xero?.connection || null,
        xeroInvoices, xeroExports: exportsResult?.exports || [],
        reconciliation: reconciliationResult?.latest_transaction_reconciliation || null,
      });
    } catch (error) { finance.error = error.message; }
    finally { finance.loading = false; render(); }
  }

  function customerFinanceLinks(row) {
    const completion = state.customerFinance.completion || {};
    const quotes = (completion.quotes || []).filter((item) => item.opportunity_id === row.opportunity_id);
    const handoffs = (completion.handoffs || []).filter((item) => item.opportunity_id === row.opportunity_id);
    const references = new Set([row.opportunity_id, ...quotes.map((item) => item.quote_id), ...handoffs.map((item) => item.quote_id)].filter(Boolean).map(String));
    const invoiceIds = new Set(handoffs.map((item) => item.invoice_id).filter(Boolean).map(String));
    return { quotes, handoffs, references, invoiceIds, accepted: row.stage === 'won' || quotes.some((item) => item.status === 'accepted_by_customer') || handoffs.length > 0 };
  }

  function financeMoney(value, currency = 'EUR') {
    try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: String(currency || 'EUR').toUpperCase() }).format(Number(value || 0)); }
    catch (_) { return `${Number(value || 0).toFixed(2)} ${String(currency || '')}`.trim(); }
  }

  function invoiceStatus(invoice) {
    const due = Number(invoice.amount_due ?? invoice.total ?? 0);
    if (due <= 0 || String(invoice.status || '').toUpperCase() === 'PAID') return { key: 'paid', text: 'Paid' };
    if (invoice.is_overdue || (invoice.due_date && invoice.due_date < new Date().toISOString().slice(0, 10))) return { key: 'overdue', text: 'Overdue' };
    if (String(invoice.status || '').includes('approval_required')) return { key: 'draft', text: 'Awaiting approval' };
    if (String(invoice.status || '').toUpperCase() === 'DRAFT') return { key: 'draft', text: 'Draft' };
    return { key: 'outstanding', text: 'Outstanding' };
  }

  function invoiceReconciliation(invoice) {
    const match = (state.customerFinance.reconciliation?.matches || []).find((item) => item.invoice?.invoice_id === invoice.invoice_id);
    if (!match) return '';
    if (match.review?.decision === 'accept_match') return 'Bank match reviewed · provider reconciliation pending';
    return `${label(match.confidence)} confidence bank match · review required`;
  }

  function customerJobInvoices(row) {
    const links = customerFinanceLinks(row);
    const native = (state.customerFinance.catalog?.invoices || []).filter((invoice) => links.invoiceIds.has(String(invoice.invoice_id)) || links.references.has(String(invoice.reference || '')));
    const nativeIds = new Set(native.map((invoice) => String(invoice.invoice_id)));
    const providerIds = new Set((state.customerFinance.xeroExports || []).filter((item) => nativeIds.has(String(item.invoice_id))).map((item) => String(item.verification?.resource_id || item.execution?.resource_id || '')).filter(Boolean));
    const xero = (state.customerFinance.xeroInvoices || []).filter((invoice) => links.references.has(String(invoice.reference || '')) || providerIds.has(String(invoice.invoice_id)));
    const feedDrafts = (row.work_feed?.events || []).filter((event) => event.kind === 'invoice_draft' && event.details?.commercial_record).map((event) => {
      const record = event.details.commercial_record; const totals = record.totals || {};
      return { invoice_id: event.event_id, invoice_number: record.reference || event.title || 'Invoice draft', issue_date: String(event.recorded_at || event.created_at || '').slice(0, 10), due_date: null, currency: record.currency || commercialCurrency(row), reference: record.reference || row.opportunity_id, lines: (record.lines || []).map((line) => ({ description: line.description, quantity: line.quantity, unit_amount: line.customer_unit_price, net_amount: line.customer_total })), subtotal: totals.customer_net, tax_total: totals.tax, total: totals.customer_gross, amount_due: totals.customer_gross, status: 'draft', source_system: 'customer_feed' };
    });
    return [...native.map((invoice) => ({ ...invoice, source_system: 'tessaris' })), ...xero.filter((invoice) => !providerIds.has(String(invoice.invoice_id)) || !native.some((item) => item.provider_exports?.xero?.resource_id === invoice.invoice_id)).map((invoice) => ({ ...invoice, source_system: 'xero' })), ...feedDrafts];
  }

  function invoiceCard(invoice) {
    const status = invoiceStatus(invoice); const reconciliation = invoiceReconciliation(invoice);
    const number = invoice.invoice_number || invoice.invoice_id; const issued = invoice.issue_date || invoice.date || 'Not recorded';
    const lines = invoice.lines || invoice.line_items || [];
    const sourceLabel = invoice.source_system === 'xero' ? 'XERO INVOICE' : invoice.source_system === 'customer_feed' ? 'CUSTOMER RECORD DRAFT' : 'TESSARIS INVOICE';
    return `<details class="srw-finance-record"><summary><div><span>${esc(sourceLabel)}</span><b>${esc(number)}</b><small>Issued ${esc(issued)} · due ${esc(invoice.due_date || 'not recorded')}</small></div><div><strong>${esc(financeMoney(invoice.total, invoice.currency))}</strong><span class="srw-finance-status ${esc(status.key)}">${esc(status.text)}</span></div></summary><div class="srw-invoice-detail">${lines.map((line) => `<div><span>${esc(line.description || 'Invoice line')}${Number(line.quantity || 0) ? ` · ${esc(line.quantity)} × ${esc(financeMoney(line.unit_amount, invoice.currency))}` : ''}</span><b>${esc(financeMoney(line.net_amount ?? line.line_amount ?? line.total ?? 0, invoice.currency))}</b></div>`).join('') || '<p>No line detail was returned by the accounting provider.</p>'}<footer><span>Net ${esc(financeMoney(invoice.subtotal, invoice.currency))}</span><span>Tax ${esc(financeMoney(invoice.tax_total ?? invoice.tax, invoice.currency))}</span><b>Total ${esc(financeMoney(invoice.total, invoice.currency))}</b></footer>${reconciliation ? `<small class="srw-reconciliation-state">${esc(reconciliation)}</small>` : `<small class="srw-reconciliation-state">${status.key === 'paid' ? 'Paid in the accounting record' : status.key === 'draft' ? 'Draft only · not yet issued or posted' : 'Waiting for payment and bank reconciliation'}</small>`}</div></details>`;
  }

  function customerInvoicesView(row) {
    const finance = state.customerFinance; const links = customerFinanceLinks(row); const invoices = customerJobInvoices(row);
    if (finance.loading && !finance.loaded) return '<section class="srw-customer-finance-view"><div class="srw-finance-empty"><b>Loading invoices…</b></div></section>';
    return `<section class="srw-customer-finance-view"><header><div><span>JOB → INVOICE → PAYMENT</span><h3>Invoices</h3><p>Invoices linked to this accepted job, including current payment and reconciliation state.</p></div><span class="srw-acceptance-state ${links.accepted ? 'accepted' : ''}">${links.accepted ? 'Job accepted' : 'Awaiting customer acceptance'}</span></header>${finance.error ? `<div class="srw-alert error">${esc(finance.error)}</div>` : ''}${invoices.length ? `<div class="srw-finance-list">${invoices.map(invoiceCard).join('')}</div>` : `<div class="srw-finance-empty"><b>${links.accepted ? 'No invoice has been prepared for this job yet' : 'Invoices become available once the job is accepted'}</b><p>${links.accepted ? 'Ask Pilot to prepare the invoice; Finance approval and any Xero write remain separately controlled.' : 'Customer acceptance evidence keeps invoicing tied to the correct quote and job.'}</p>${links.accepted ? '<button type="button" data-srw-pilot-invoice>Ask Pilot to prepare invoice</button>' : ''}</div>`}<footer><small>${state.customerFinance.xero?.status === 'connected' ? 'Xero connected · provider invoices are pulled into this record after sync.' : 'Provider-neutral records are shown here. Connect Xero or another accounting provider in Finance when required.'}</small></footer></section>`;
  }

  function jobExpenseDocuments(row) {
    return (state.customerFinance.inbox?.documents || []).filter((document) => String(document.ownership?.project_id || '') === String(row.opportunity_id));
  }

  function expenseStatus(document) {
    if (document.accounting?.status === 'verified_in_xero') return 'Verified in Xero';
    if (document.accounting?.status === 'posted_internal') return 'Recorded internally';
    if (document.approval?.decision === 'approve') return 'Approved for accounting';
    if (document.status === 'awaiting_approval') return 'Awaiting approval';
    if (document.extraction?.status === 'suggestions_ready') return 'Ready to review';
    if (document.extraction?.status === 'failed') return 'Reader needs attention';
    return 'Needs review';
  }

  function customerExpensesView(row) {
    const documents = jobExpenseDocuments(row); const workspace = encodeURIComponent(state.workspaceId);
    return `<section class="srw-customer-finance-view"><header><div><span>CAPTURE → READ → APPROVE → RECONCILE</span><h3>Job expenses</h3><p>Receipts and supplier invoices are allocated to this job before Finance review and bank matching.</p></div><div class="srw-expense-upload"><select data-srw-expense-type aria-label="Expense document type"><option value="receipt">Receipt</option><option value="supplier_invoice">Supplier invoice</option><option value="expense_claim">Expense claim</option><option value="credit_note">Credit note</option></select><label>＋ Upload receipt or invoice<input type="file" accept="image/*,.pdf,.csv,.xml" data-srw-expense-file></label><label>⌁ Take receipt photo<input type="file" accept="image/*" capture="environment" data-srw-expense-camera></label></div></header>${documents.length ? `<div class="srw-finance-list">${documents.map((document) => { const fields = document.extraction?.fields || {}; const original = `${API}/api/aion/business/finance-inbox/${workspace}/documents/${encodeURIComponent(document.id)}/file`; return `<article class="srw-expense-record"><div class="srw-expense-icon">${esc(attachmentTypeLabel({ name: document.source?.filename, media_type: document.source?.mime_type }))}</div><div><span>${esc(label(document.document_type))}</span><b>${esc(fields.supplier || document.source?.filename || 'Expense document')}</b><small>${fields.document_date ? `${esc(fields.document_date)} · ` : ''}${fields.total !== undefined && fields.total !== null ? esc(financeMoney(fields.total, fields.currency)) : 'Amount awaiting extraction'}</small><small>Submitted by ${esc(actorName(document.ownership?.submitted_by_person_id) || 'signed-in team member')} · ${esc(expenseStatus(document))}</small></div><a href="${esc(original)}" target="_blank" rel="noopener">Open original</a></article>`; }).join('')}</div>` : '<div class="srw-finance-empty"><b>No expenses have been allocated to this job</b><p>An engineer or manager can upload a receipt, supplier invoice or expense claim here. AION reads it and routes it into the existing Finance Inbox for human review.</p></div>'}<footer><small>Extraction creates suggestions only. Accounting approval, Xero posting and bank reconciliation remain separate recorded actions.</small></footer></section>`;
  }

  async function uploadCustomerJobExpense(file, documentType) {
    const row = selected(); const person = actorById(state.actorId) || syncSignedInActor();
    if (!row || !file) return;
    if (!person) { state.error = 'Sign in before allocating an expense to this job.'; render(); return; }
    state.busy = true; state.error = ''; state.message = 'Preserving the original expense document…'; render();
    try {
      const form = new FormData();
      form.append('file', file, file.name || 'job-expense');
      form.append('channel', 'customer_job_record');
      form.append('document_type', documentType || 'receipt');
      form.append('submitted_by_person_id', person.person_id);
      form.append('project_id', row.opportunity_id);
      form.append('source_reference', `sales-opportunity:${row.opportunity_id}`);
      const uploaded = await request(`/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/documents`, { method: 'POST', body: form, timeoutMs: 30000 });
      let extracted = false;
      try {
        await request(`/api/aion/business/finance-inbox/${encodeURIComponent(state.workspaceId)}/documents/${encodeURIComponent(uploaded.document.id)}/extract`, { method: 'POST', body: JSON.stringify({ provider: null }), timeoutMs: 60000 });
        extracted = true;
      } catch (_) { /* The protected original remains available for manual review. */ }
      state.customerFinance.loaded = false;
      state.message = extracted
        ? `${file.name || 'Expense document'} was allocated to this job. AION extracted suggestions for Finance review.`
        : `${file.name || 'Expense document'} was allocated to this job. The original is safe; Finance can review it manually or rerun the reader.`;
      await loadCustomerFinance(row);
    } catch (error) { state.error = error.message; }
    finally { state.busy = false; render(); }
  }

  function customerWorkspace() {
    const row = selected();
    if (!row) return '';
    customerPilotSession(row);
    const feed = row.work_feed || {};
    const address = customerAddress(row);
    const events = (feed.events || []).slice().reverse().slice(0, 20);
    const timeline = events.length ? events.map((item) => {
      const canOpen = Boolean(item.details?.commercial_record);
      const actorTrail = eventActorTrail(item);
      return `<article class="srw-work-event ${canOpen ? 'is-openable' : ''}"><div><b>${esc(item.title || label(item.kind))}</b><span>${esc(label(item.lifecycle_stage))} · ${esc(label(item.action?.status || 'recorded'))}</span></div><p>${esc(item.summary)}</p>${attachmentGallery(item)}${canOpen ? `<button type="button" data-srw-open-commercial-event="${esc(item.event_id)}">Open quotation · view or edit</button>` : ''}${actorTrail ? `<small class="srw-event-actors">${esc(actorTrail)}</small>` : ''}<small>${esc(label(item.source))}${item.provider ? ` · ${esc(item.provider)}` : ''} · ${esc(new Date(item.recorded_at || item.created_at).toLocaleString())}</small>${(item.attachments || []).length ? `<small>${item.attachments.length} attached file${item.attachments.length === 1 ? '' : 's'} · evidence preserved</small>` : ''}${item.action?.external_action_performed ? `<small class="srw-executed">Executed · receipt ${esc(item.action.receipt_reference)}</small>` : ''}</article>`;
    }).join('') : '<p>No lifecycle events recorded yet.</p>';
    const workView = `<div class="srw-customer-page-body"><div class="srw-customer-feed-column"><section class="srw-work-feed"><div class="srw-work-feed-title"><div><b>Customer work feed</b><p>One history from first enquiry to quote, job, invoice, payment and review.</p></div><span>${esc(label(feed.current_stage || 'enquiry'))}</span></div>${timeline}<button data-srw-panel="work_event">+ Add job update</button></section><footer class="srw-detail-actions srw-customer-toolbar"><button data-srw-panel="qualify">Qualify</button><button data-srw-panel="call">Log conversation</button>${row.contact?.phone ? '<button data-srw-prepare-call>Prepare production call</button>' : ''}<button data-srw-panel="appointment" ${row.stage === 'qualified' || row.stage === 'human_handoff' || row.stage === 'appointment_proposed' ? '' : 'disabled'}>Prepare appointment</button><button data-srw-panel="handoff">Human handoff</button>${row.stage === 'proposal' ? '<button class="primary" data-srw-stage="won">Mark won</button>' : ''}${row.stage !== 'won' && row.stage !== 'lost' ? '<button data-srw-stage="lost">Close lost</button>' : ''}</footer></div></div>`;
    const invoiceCount = customerJobInvoices(row).length; const expenseCount = jobExpenseDocuments(row).length;
    const tabView = state.customerTab === 'invoices' ? customerInvoicesView(row) : state.customerTab === 'expenses' ? customerExpensesView(row) : workView;
    return `<section class="srw-shell srw-customer-page" data-aion-sales-revenue data-srw-customer-page><header class="srw-customer-page-header"><div class="srw-customer-identity"><span>CUSTOMER · LEAD · JOB</span><h2>${esc(row.contact?.name)}</h2><div class="srw-customer-contact-line">${stageBadge(row.stage)}${row.contact?.email ? `<span><b>Email</b> ${esc(row.contact.email)}</span>` : ''}${row.contact?.phone ? `<span><b>Phone</b> ${esc(row.contact.phone)}</span>` : ''}<span><b>Address</b> ${esc(address || 'Not added')}</span></div><p>${esc(row.enquiry || row.title)}</p></div><div class="srw-customer-page-actions"><button type="button" data-srw-close>← Back to Sales</button><button type="button" data-srw-open-relationship>Customer details</button></div></header>${state.error ? `<div class="srw-alert error">${esc(state.error)}</div>` : ''}${state.message ? `<div class="srw-alert good">${esc(state.message)}</div>` : ''}${customerRelationship(row)}<nav class="srw-customer-record-tabs"><button type="button" class="${state.customerTab === 'work' ? 'active' : ''}" data-srw-customer-tab="work">Work feed</button><button type="button" class="${state.customerTab === 'invoices' ? 'active' : ''}" data-srw-customer-tab="invoices">Invoices <span>${invoiceCount}</span></button><button type="button" class="${state.customerTab === 'expenses' ? 'active' : ''}" data-srw-customer-tab="expenses">Expenses <span>${expenseCount}</span></button></nav>${tabView}${state.customerTab === 'work' ? commercialWorkbench(row) : ''}${customerPilotConversation(row)}</section>`;
  }

  function panel() {
    const row = selected();
    if (!state.panel) return '';
    const close = '<button type="button" data-srw-close aria-label="Close">×</button>';
    if (state.panel === 'prepare_call') {
      const callers = (state.data?.sales_agents || []).filter((item) => item.state === 'active' && ['outbound','both'].includes(item.direction));
      return `<aside class="srw-panel"><form data-srw-form="prepare_call"><header><div><span>PREPARE CUSTOMER CALL</span><h2>Choose the sales caller</h2><p>Tessaris will freeze this customer, the selected minted contract and the reason for calling. A separate exact approval is still required before the provider can be contacted.</p></div>${close}</header><label>Sales caller<select name="agent_id" required>${callers.map((item) => `<option value="${esc(item.agent_id)}">${esc(item.name)} · ${esc(label(item.direction))} · contract ${Number(item.minted_contract?.version || item.version)}</option>`).join('')}</select></label><label>Reason for this call<textarea name="reason" rows="3" required>Respond to the recorded customer enquiry</textarea></label><div class="srw-caller-boundary"><b>This does not start the call</b><span>It creates a customer-specific draft for review. Consent, exact approval and live provider controls remain separate.</span></div>${recordedByField('Prepared by')}<footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Prepare call for approval</button></footer></form></aside>`;
    }
    if (state.panel === 'call_agent_create') {
      return `<aside class="srw-panel srw-call-agent-builder"><form data-srw-form="call_agent_create"><header><div><span>NEW SALES CALLER</span><h2>What job should this caller perform?</h2><p>Start with one clear job. You can create another caller for another number, campaign or sales process.</p></div>${close}</header><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>1</span><div><b>Name and direction</b><small>This can be changed before the contract is minted.</small></div></div><label>Caller name<input name="name" required placeholder="For example: Website enquiry line"></label><fieldset class="srw-agent-direction"><legend>Which calls should it handle?</legend><label><input type="radio" name="direction" value="inbound" checked><b>Inbound calls</b><small>Customers call the assigned number and the agent answers.</small></label><label><input type="radio" name="direction" value="outbound"><b>Outbound calls</b><small>A person selects a lead and approves the call.</small></label><label><input type="radio" name="direction" value="both"><b>Both</b><small>Use one contract for inbound enquiries and approved outbound follow-up.</small></label></fieldset></section>${recordedByField('Created by')}<footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Create and configure</button></footer></form></aside>`;
    }
    if (state.panel === 'call_agent_builder') {
      const agent = selectedSalesAgent();
      if (!agent) return '';
      const option = (value, current, text) => `<option value="${esc(value)}" ${String(value) === String(current || '') ? 'selected' : ''}>${esc(text || label(value))}</option>`;
      const chosenFields = new Set((agent.capture_fields || []).map((item) => item.key));
      const actionSet = new Set(agent.allowed_actions || []);
      const field = (key, text) => `<label><input type="checkbox" name="capture_field" value="${esc(key)}" ${chosenFields.has(key) ? 'checked' : ''}> ${esc(text)}</label>`;
      const action = (key, text) => `<label><input type="checkbox" name="allowed_action" value="${esc(key)}" ${actionSet.has(key) ? 'checked' : ''}> ${esc(text)}</label>`;
      const standardKeys = new Set(['customer_name','customer_need','email','phone','location','full_address','timescale','budget','decision_authority','product_interest','preferred_follow_up','next_step']);
      const customFields = (agent.capture_fields || []).filter((item) => !standardKeys.has(item.key)).map((item) => `${item.label}|${item.type || 'text'}|${item.required ? 'required' : 'optional'}`).join('\n');
      const knowledge = agent.knowledge || {}; const objective = agent.objective || {}; const conversation = agent.conversation || {}; const routing = agent.routing || {}; const phone = agent.phone_assignment || {};
      return `<aside class="srw-panel srw-call-agent-builder"><form data-srw-form="call_agent_builder"><header><div><span>BUILD SALES CALLER</span><h2>${esc(agent.name)}</h2><p>These settings become the caller’s versioned contract. Saving never starts a call.</p></div>${close}</header><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>1</span><div><b>Assign the job and number</b><small>Inbound callers answer this number. Outbound callers present it as their calling route.</small></div></div><div class="srw-two"><label>Caller name<input name="name" required value="${esc(agent.name)}"></label><label>Direction<select name="direction">${option('inbound',agent.direction,'Inbound')}${option('outbound',agent.direction,'Outbound')}${option('both',agent.direction,'Inbound and outbound')}</select></label></div><label>Assigned telephone number<input name="phone_number" value="${esc(phone.number || '')}" placeholder="International format, for example +441234567890"></label></section><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>2</span><div><b>Give it approved business knowledge</b><small>The caller may use only this information and connected approved business records.</small></div></div><label>Business or brand name<input name="business_name" required value="${esc(knowledge.business_name || '')}"></label><label>What the business does<textarea name="business_summary" rows="3" required placeholder="A short, plain-language explanation of the business and who it serves.">${esc(knowledge.business_summary || '')}</textarea></label><label>Products, services or packages it may discuss<textarea name="approved_offers" rows="5" required placeholder="List approved offers and any facts the caller may explain. Include prices only when they are genuinely fixed and approved.">${esc(knowledge.approved_offers || '')}</textarea></label><div class="srw-two"><label>Areas or customers served<textarea name="service_areas" rows="3">${esc(knowledge.service_areas || '')}</textarea></label><label>Other approved facts<textarea name="approved_facts" rows="3" placeholder="Opening hours, eligibility, guarantees, common answers or exclusions.">${esc(knowledge.approved_facts || '')}</textarea></label></div><label>When the answer is not known<input name="unknown_answer" value="${esc(knowledge.unknown_answer || '')}"></label></section><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>3</span><div><b>Choose the result</b><small>Define success without implying that an appointment, price or payment is confirmed.</small></div></div><div class="srw-two"><label>Primary result<select name="primary_outcome">${option('qualify_for_human_review',objective.primary_outcome,'Qualify for human review')}${option('request_human_callback',objective.primary_outcome,'Request a human callback')}${option('request_appointment',objective.primary_outcome,'Request an appointment')}${option('request_site_visit',objective.primary_outcome,'Request a site visit')}${option('capture_quote_requirements',objective.primary_outcome,'Capture quotation requirements')}${option('explain_approved_offers',objective.primary_outcome,'Explain approved offers and agree next step')}</select></label><label>How it should finish<select name="close_strategy">${option('human_review',objective.close_strategy,'Send to human review')}${option('human_callback',objective.close_strategy,'Ask for a human callback')}${option('appointment_request',objective.close_strategy,'Prepare an appointment request')}${option('site_visit_request',objective.close_strategy,'Prepare a site-visit request')}${option('qualified_lead',objective.close_strategy,'Mark ready for sales follow-up')}</select></label></div><label>What counts as a successful call<textarea name="success_definition" rows="3" required>${esc(objective.success_definition || '')}</textarea></label></section><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>4</span><div><b>Choose what the call must capture</b><small>The caller records an answer or explicitly marks it unknown. Add business-specific fields below.</small></div></div><div class="srw-checks srw-caller-check-grid">${field('customer_name','Customer name')}${field('customer_need','What they need')}${field('email','Email address')}${field('phone','Telephone number')}${field('location','Town or general location')}${field('full_address','Full address')}${field('timescale','Timescale or required date')}${field('budget','Budget or price expectation')}${field('decision_authority','Who can approve')}${field('product_interest','Product or service interest')}${field('preferred_follow_up','Preferred follow-up')}${field('next_step','Agreed next step')}</div><label>Custom information to capture<textarea name="custom_capture_fields" rows="4" placeholder="One per line: Company size|number|required&#10;Current supplier|text|optional">${esc(customFields)}</textarea></label></section><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>5</span><div><b>Choose what it may do</b><small>These permissions still require the relevant verified tool and approval.</small></div></div><div class="srw-checks srw-caller-check-grid">${action('collect_information','Collect and record information')}${action('request_human_callback','Request a human callback')}${action('request_appointment','Prepare an appointment request')}${action('request_site_visit','Prepare a site-visit request')}${action('present_approved_offers','Explain approved products or services')}${action('prepare_follow_up','Prepare a follow-up message')}${action('prepare_terms_link','Prepare an approved terms link')}${action('prepare_payment_link','Prepare an approved payment link')}${action('transfer_to_human','Transfer or escalate to a person')}</div><div class="srw-caller-boundary"><b>Always blocked</b><span>Inventing information · taking card details · confirming unverified prices or availability · bypassing consent · changing external systems without authority</span></div></section><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>6</span><div><b>Set the conversation and routing</b><small>Give guidance rather than a rigid script so the caller can converse naturally.</small></div></div><label>Opening line<textarea name="opening" rows="2" placeholder="AI disclosure is always enforced.">${esc(conversation.opening || '')}</textarea></label><div class="srw-two"><label>Tone<input name="tone" value="${esc(conversation.tone || '')}"></label><label>Languages<input name="languages" value="${esc((conversation.languages || ['en-GB']).join(', '))}" placeholder="en-GB, es-ES"></label></div><label>Conversation guidance<textarea name="guidance" rows="5">${esc(conversation.guidance || '')}</textarea></label><label>When a person is needed<textarea name="human_handoff" rows="2">${esc(routing.human_handoff || '')}</textarea></label><div class="srw-two"><label>Maximum outbound attempts<select name="maximum_phone_attempts">${[1,2,3].map((value) => option(value,routing.maximum_phone_attempts || 1,`${value} attempt${value === 1 ? '' : 's'}`)).join('')}</select></label><label>If unanswered<select name="unanswered_action">${option('human_review',routing.unanswered_action,'Human review')}${option('prepare_email',routing.unanswered_action,'Prepare email')}${option('prepare_sms',routing.unanswered_action,'Prepare SMS')}${option('close_attempt',routing.unanswered_action,'Close this attempt')}</select></label></div></section>${recordedByField('Saved by')}<footer><small>Saving creates a new draft version and clears the previous safety result and minted contract.</small><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Save and continue</button></footer></form></aside>`;
    }
    if (state.panel === 'enquiry') {
      const draft = state.enquiryDraft || {};
      const actorId = draft.actor || state.actorId;
      const entryMode = draft.entry_mode || 'lead';
      const customerType = draft.customer_type || '';
      const personFields = `<section class="srw-enquiry-path"><span>PERSONAL CUSTOMER</span><div class="srw-two"><label>First name<input name="first_name" required value="${esc(draft.first_name || '')}"></label><label>Last name<input name="last_name" required value="${esc(draft.last_name || '')}"></label></div><label>Address<textarea name="address" rows="2" required placeholder="Home, billing or service address">${esc(draft.address || '')}</textarea></label></section>`;
      const businessFields = `<section class="srw-enquiry-path"><span>BUSINESS CONTACT</span><label>Company name<input name="company_name" required value="${esc(draft.company_name || '')}"></label><div class="srw-two"><label>Contact first name<input name="first_name" required value="${esc(draft.first_name || '')}"></label><label>Contact last name<input name="last_name" required value="${esc(draft.last_name || '')}"></label></div><div class="srw-two"><label>Title / position<input name="position_title" value="${esc(draft.position_title || '')}" placeholder="For example Operations Manager"></label><label>Department<input name="department" value="${esc(draft.department || '')}" placeholder="For example Procurement"></label></div><label>Business address<textarea name="address" rows="2" placeholder="Office, billing or service address">${esc(draft.address || '')}</textarea></label></section>`;
      const dealFields = entryMode === 'existing_deal' ? `<section class="srw-enquiry-path srw-deal-entry"><span>DEAL POSITION</span><div class="srw-two"><label>Current stage<select name="initial_stage"><option value="new" ${selectedOption('new', draft.initial_stage || 'new')}>New</option><option value="contacted" ${selectedOption('contacted', draft.initial_stage)}>Contacted</option><option value="qualified" ${selectedOption('qualified', draft.initial_stage)}>Qualified</option><option value="appointment_booked" ${selectedOption('appointment_booked', draft.initial_stage)}>Appointment booked</option><option value="proposal" ${selectedOption('proposal', draft.initial_stage)}>Proposal</option><option value="won" ${selectedOption('won', draft.initial_stage)}>Won</option><option value="lost" ${selectedOption('lost', draft.initial_stage)}>Closed</option></select></label><label>Next action<input name="next_action" value="${esc(draft.next_action || '')}" placeholder="What needs to happen next?"></label></div><div class="srw-two"><label>Estimated value<input type="number" min="0" step="0.01" name="estimated_value" value="${esc(draft.estimated_value || '')}"></label><label>Currency<select name="currency"><option value="GBP" ${selectedOption('GBP', draft.currency || 'GBP')}>GBP £</option><option value="EUR" ${selectedOption('EUR', draft.currency)}>EUR €</option><option value="USD" ${selectedOption('USD', draft.currency)}>USD $</option></select></label></div></section>` : '';
      const contactFields = customerType ? `<div class="srw-two"><label>Email<input type="email" name="email" value="${esc(draft.email || '')}"></label><label>Phone<input name="phone" value="${esc(draft.phone || '')}"></label></div>${customerType === 'business' ? `<label>Phone extension<input name="phone_extension" value="${esc(draft.phone_extension || '')}" placeholder="Optional extension"></label>` : ''}<small class="srw-form-hint">At least one contact method—email or phone—is required.</small><label>${entryMode === 'existing_deal' ? 'Deal / opportunity description' : 'What do they need?'}<textarea name="enquiry" rows="4" required>${esc(draft.enquiry || '')}</textarea></label>${dealFields}<div class="srw-two"><label>Source<select name="source"><option value="manual" ${selectedOption('manual', draft.source || 'manual')}>Manual</option><option value="website" ${selectedOption('website', draft.source)}>Website</option><option value="inbound_call" ${selectedOption('inbound_call', draft.source)}>Inbound call</option><option value="inbound_email" ${selectedOption('inbound_email', draft.source)}>Inbound email</option><option value="referral" ${selectedOption('referral', draft.source)}>Referral</option><option value="platform" ${selectedOption('platform', draft.source)}>Third-party platform</option><option value="client_work" ${selectedOption('client_work', draft.source)}>Existing client work</option><option value="marketing_campaign" ${selectedOption('marketing_campaign', draft.source)}>Marketing campaign</option></select></label><label>Campaign/reference<input name="source_reference" value="${esc(draft.source_reference || '')}"></label></div>${recordedByField('Added by')}` : '';
      return `<aside class="srw-panel"><form data-srw-form="enquiry"><header><div><span>${entryMode === 'existing_deal' ? 'NEW DEAL' : 'NEW LEAD'}</span><h2>${entryMode === 'existing_deal' ? 'Add a deal' : 'Add a customer lead'}</h2><p>${entryMode === 'existing_deal' ? 'Capture the customer, contact route, source, value, owner and current commercial position in one record.' : 'Capture the customer identity, contact route, source and requirement before Pilot begins qualification.'}</p></div>${close}</header><input type="hidden" name="entry_mode" value="${esc(entryMode)}"><fieldset class="srw-customer-type"><legend>Who is this ${entryMode === 'existing_deal' ? 'deal' : 'lead'} for?</legend><label class="${customerType === 'person' ? 'active' : ''}"><input type="radio" name="customer_type" value="person" ${customerType === 'person' ? 'checked' : ''}> <b>A person</b><small>Consumer, homeowner or individual client</small></label><label class="${customerType === 'business' ? 'active' : ''}"><input type="radio" name="customer_type" value="business" ${customerType === 'business' ? 'checked' : ''}> <b>A business</b><small>Company, organisation or professional buyer</small></label></fieldset>${customerType === 'person' ? personFields : customerType === 'business' ? businessFields : '<div class="srw-enquiry-path-prompt">Select a customer type to continue.</div>'}${contactFields}<footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit" ${customerType ? '' : 'disabled'}>${entryMode === 'existing_deal' ? 'Create deal' : 'Create lead'}</button></footer></form></aside>`;
    }
    if (state.panel === 'agent_setup') {
      const setup = state.data?.playbook?.agent_setup || {}; const has = (name) => (setup.allowed_actions || []).includes(name); const needs = (name) => (setup.required_fields || []).includes(name);
      const option = (value, current, text) => `<option value="${value}" ${value === current ? 'selected' : ''}>${esc(text || label(value))}</option>`;
      const check = (name, value, text, selected) => `<label><input type="checkbox" name="${name}" value="${value}" ${selected ? 'checked' : ''}> ${esc(text)}</label>`;
      return `<aside class="srw-panel srw-caller-settings"><form data-srw-form="agent_setup"><header><div><span>AI SALES CALLER</span><h2>Set up the enquiry follow-up call</h2><p>Choose what the caller should achieve, what it must ask and what it is allowed to prepare. Saving changes never starts a call.</p></div>${close}</header><div class="srw-caller-form-notice"><b>How this is used</b><p>A person opens a lead and prepares a call. Tessaris then applies these settings to that customer only and asks for approval before anything can be sent to the phone provider.</p></div><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>1</span><div><b>Choose the result you want</b><small>The caller gathers information and asks for the next step—it does not promise that the next step is confirmed.</small></div></div><div class="srw-two"><label>Primary result<select name="primary_goal">${option('human_review_request', setup.primary_goal, 'Collect details for human review')}${option('human_callback_request', setup.primary_goal, 'Request a human callback')}${option('site_visit_request', setup.primary_goal, 'Request a site visit')}</select></label><label>How the conversation should finish<select name="close_strategy">${option('human_review', setup.close_strategy, 'Send the details for human review')}${option('human_callback', setup.close_strategy, 'Ask for a human callback')}${option('site_visit_request', setup.close_strategy, 'Ask for a site visit')}${option('approved_booking_request', setup.close_strategy, 'Request an approved appointment')}${option('approved_payment_link_request', setup.close_strategy, 'Request an approved payment link')}</select></label></div></section><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>2</span><div><b>Choose what the caller must establish</b><small>A call can finish with an answer or with the item clearly marked unknown. Select only information genuinely needed for the next step.</small></div></div><div class="srw-checks srw-caller-check-grid">${check('required_fields','customer_name','Customer name',needs('customer_name'))}${check('required_fields','work_required','What they need',needs('work_required'))}${check('required_fields','property_location','Town or general location',needs('property_location'))}${check('required_fields','full_property_address','Full address',needs('full_property_address'))}${check('required_fields','urgency','When it is needed',needs('urgency'))}${check('required_fields','immediate_safety_risk','Any immediate safety risk',needs('immediate_safety_risk'))}${check('required_fields','customer_email','Email confirmed in writing',needs('customer_email'))}${check('required_fields','photos_or_documents_available','Whether photos or documents are available',needs('photos_or_documents_available'))}${check('required_fields','preferred_follow_up_channel','Preferred follow-up method',needs('preferred_follow_up_channel'))}${check('required_fields','preferred_follow_up_time','Best follow-up time',needs('preferred_follow_up_time'))}${check('required_fields','decision_authority','Who can approve the work',needs('decision_authority'))}${check('required_fields','budget_context','Budget or price expectation',needs('budget_context'))}</div></section><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>3</span><div><b>Choose what it may request or prepare</b><small>These permissions do not allow automatic sending, booking, charging or provider changes.</small></div></div><div class="srw-checks srw-caller-check-grid">${check('allowed_actions','collect_information','Collect and record information',has('collect_information'))}${check('allowed_actions','collect_email_in_writing','Confirm an email address in writing',has('collect_email_in_writing'))}${check('allowed_actions','request_photos','Ask for pictures or documents',has('request_photos'))}${check('allowed_actions','request_human_callback','Ask a person to call the customer',has('request_human_callback'))}${check('allowed_actions','request_site_visit','Ask for a site visit',has('request_site_visit'))}${check('allowed_actions','request_approved_booking','Request an available appointment',has('request_approved_booking'))}${check('allowed_actions','present_approved_product_options','Explain approved services or products',has('present_approved_product_options'))}${check('allowed_actions','send_approved_terms_link','Prepare an approved terms link',has('send_approved_terms_link'))}${check('allowed_actions','send_approved_payment_link','Prepare an approved payment link',has('send_approved_payment_link'))}</div><div class="srw-caller-boundary"><b>Always blocked</b><span>Taking card details · inventing prices or availability · confirming bookings · sending unapproved messages · changing an external system</span></div></section><section class="srw-caller-form-section" data-srw-contact-sequence><div class="srw-caller-form-heading"><span>4</span><div><b>Decide what happens when nobody answers</b><small>Written follow-up continues the same call goal and remains a draft for approval.</small></div></div><div class="srw-two"><label>Maximum phone attempts<select name="maximum_phone_attempts">${[1,2,3].map((value) => option(value, setup.contact_sequence?.maximum_phone_attempts || 2, `${value} attempt${value === 1 ? '' : 's'}`)).join('')}</select></label><label>Then continue by<select name="fallback_channel">${option('email', setup.contact_sequence?.fallback_channel || 'email', 'Email')}${option('sms', setup.contact_sequence?.fallback_channel, 'SMS')}${option('whatsapp', setup.contact_sequence?.fallback_channel, 'WhatsApp Business')}${option('none', setup.contact_sequence?.fallback_channel, 'Human review only')}</select></label></div><label>Questions in each written message<select name="questions_per_written_message">${[1,2,3].map((value) => option(value, setup.contact_sequence?.questions_per_written_message || 2, `${value} question${value === 1 ? '' : 's'}`)).join('')}</select></label></section><section class="srw-caller-form-section"><div class="srw-caller-form-heading"><span>5</span><div><b>Set the conversation style</b><small>Use guidance, not a rigid word-for-word script. The caller must still follow the selected facts and safeguards.</small></div></div><label>Opening style<select name="intro_style">${option('warm_direct', setup.intro_style, 'Warm and direct')}${option('permission_based', setup.intro_style, 'Ask permission to continue')}${option('problem_first', setup.intro_style, 'Begin with their enquiry')}${option('referral_context', setup.intro_style, 'Explain the referral context')}${option('custom', setup.intro_style, 'Use my opening below')}</select></label><label>Custom opening line<input name="custom_intro" value="${esc(setup.custom_intro || '')}" placeholder="Optional"></label><label>Conversation guidance<textarea name="sales_script" rows="6" placeholder="For example: Be concise, confirm the issue in the customer’s own words, and explain only services listed in the business model.">${esc(setup.sales_script || '')}</textarea></label></section><details class="srw-caller-form-advanced"><summary>Photo routing and advanced targeting</summary><div class="srw-two"><label>Calls are for<select name="business_motion">${option('inbound', setup.business_motion, 'People who have enquired')}${option('outbound', setup.business_motion, 'Approved outbound prospects')}${option('blended', setup.business_motion, 'Both')}</select></label><label>Typical lead readiness<select name="lead_temperature">${option('freezing', setup.lead_temperature, 'Very early')}${option('cold', setup.lead_temperature, 'Cold')}${option('warm', setup.lead_temperature, 'Warm')}${option('hot', setup.lead_temperature, 'Ready to act')}${option('existing_customer', setup.lead_temperature, 'Existing customer')}</select></label></div><label>How customers provide photos or documents<select name="evidence_route_mode">${option('human_follow_up_required', setup.evidence_route?.mode, 'A person confirms where to send them')}${option('reply_to_approved_sms', setup.evidence_route?.mode, 'Reply to an approved SMS')}${option('approved_email_address', setup.evidence_route?.mode, 'Send to an approved email address')}</select></label><label>Approved reply number or email address<input name="evidence_route_destination" value="${esc(setup.evidence_route?.destination || '')}" placeholder="Required only when a specific route is selected"></label></details>${recordedByField('Saved by')}<footer><small>Saving creates a new call-plan version. The safety check and approval must be completed again.</small><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Save call plan</button></footer></form></aside>`;
      return `<aside class="srw-panel"><form data-srw-form="agent_setup"><header><div><span>SALES AGENT JOB</span><h2>Define what this agent must achieve</h2><p>The selected AI may converse naturally, but it cannot change these goals or permissions.</p></div>${close}</header><div class="srw-two"><label>Sales motion<select name="business_motion">${option('inbound', setup.business_motion, 'Inbound enquiries')}${option('outbound', setup.business_motion, 'Outbound prospecting')}${option('blended', setup.business_motion, 'Inbound + outbound')}</select></label><label>Lead temperature<select name="lead_temperature">${['freezing','cold','warm','hot','existing_customer'].map((value) => option(value, setup.lead_temperature)).join('')}</select></label></div><div class="srw-two"><label>Primary outcome<select name="primary_goal">${option('human_review_request', setup.primary_goal, 'Human review')}${option('human_callback_request', setup.primary_goal, 'Human callback request')}${option('site_visit_request', setup.primary_goal, 'Site visit request')}</select></label><label>Close strategy<select name="close_strategy">${['human_review','human_callback','site_visit_request','approved_booking_request','approved_payment_link_request'].map((value) => option(value, setup.close_strategy)).join('')}</select></label></div><section class="srw-checks"><b>Information the call must collect</b>${check('required_fields','customer_name','Customer name',needs('customer_name'))}${check('required_fields','work_required','Need, issue, service or product',needs('work_required'))}${check('required_fields','property_location','Town or general location',needs('property_location'))}${check('required_fields','full_property_address','Full address',needs('full_property_address'))}${check('required_fields','urgency','Urgency or required date',needs('urgency'))}${check('required_fields','immediate_safety_risk','Immediate safety risk',needs('immediate_safety_risk'))}${check('required_fields','customer_email','Email confirmed in writing',needs('customer_email'))}${check('required_fields','photos_or_documents_available','Photos or documents available',needs('photos_or_documents_available'))}${check('required_fields','preferred_follow_up_channel','Preferred follow-up channel',needs('preferred_follow_up_channel'))}${check('required_fields','preferred_follow_up_time','Preferred follow-up time',needs('preferred_follow_up_time'))}${check('required_fields','decision_authority','Decision authority',needs('decision_authority'))}${check('required_fields','budget_context','Budget context',needs('budget_context'))}</section><section class="srw-checks"><b>Actions the agent may request or prepare</b>${check('allowed_actions','collect_information','Collect information',has('collect_information'))}${check('allowed_actions','collect_email_in_writing','Confirm email in writing',has('collect_email_in_writing'))}${check('allowed_actions','request_photos','Request pictures or documents',has('request_photos'))}${check('allowed_actions','request_human_callback','Request a human callback',has('request_human_callback'))}${check('allowed_actions','request_site_visit','Request a site visit',has('request_site_visit'))}${check('allowed_actions','request_approved_booking','Request an available appointment',has('request_approved_booking'))}${check('allowed_actions','present_approved_product_options','Present approved products, services or packages',has('present_approved_product_options'))}${check('allowed_actions','send_approved_terms_link','Prepare approved terms link',has('send_approved_terms_link'))}${check('allowed_actions','send_approved_payment_link','Prepare approved first-hour or deposit payment link',has('send_approved_payment_link'))}<small>The agent never hears card details and never sends, books or charges without the relevant verified tool and authority.</small></section><div class="srw-two"><label>Opening style<select name="intro_style">${['warm_direct','permission_based','problem_first','referral_context','custom'].map((value) => option(value, setup.intro_style)).join('')}</select></label><label>Photo/document route<select name="evidence_route_mode">${option('human_follow_up_required', setup.evidence_route?.mode, 'Person confirms route')}${option('reply_to_approved_sms', setup.evidence_route?.mode, 'Reply to approved SMS')}${option('approved_email_address', setup.evidence_route?.mode, 'Approved email')}</select></label></div><label>Evidence email or reply destination<input name="evidence_route_destination" value="${esc(setup.evidence_route?.destination || '')}" placeholder="Required only for a configured route"></label><label>Custom opening line<input name="custom_intro" value="${esc(setup.custom_intro || '')}" placeholder="Optional; AI identity disclosure is always added"></label><label>Sales script and conversation guidance<textarea name="sales_script" rows="7" placeholder="How to move from opening, through discovery and approved options, to the close">${esc(setup.sales_script || '')}</textarea></label><footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Save new agent version</button></footer></form></aside>`;
    }
    if (!row) return '';
    if (state.panel === 'detail') {
      const answer = row.qualification?.answers || {};
      const feed = row.work_feed || {};
      const events = (feed.events || []).slice().reverse().slice(0, 20);
      const timeline = events.length ? events.map((item) => `<article class="srw-work-event"><div><b>${esc(item.title || label(item.kind))}</b><span>${esc(label(item.lifecycle_stage))} · ${esc(label(item.action?.status || 'recorded'))}</span></div><p>${esc(item.summary)}</p><small>${esc(label(item.source))}${item.provider ? ` · ${esc(item.provider)}` : ''} · ${esc(new Date(item.recorded_at || item.created_at).toLocaleString())}</small>${(item.attachments || []).length ? `<small>${item.attachments.length} attached file${item.attachments.length === 1 ? '' : 's'} · evidence preserved</small>` : ''}${item.action?.external_action_performed ? `<small class="srw-executed">Executed · receipt ${esc(item.action.receipt_reference)}</small>` : ''}</article>`).join('') : '<p>No lifecycle events recorded yet.</p>';
      return `<aside class="srw-panel"><div class="srw-detail"><header><div><span>CUSTOMER · LEAD · JOB</span><h2>${esc(row.contact?.name)}</h2><p>${esc(row.title)}</p></div>${close}</header><div class="srw-detail-status">${stageBadge(row.stage)}<span>${esc(row.contact?.email || '')}</span><span>${esc(row.contact?.phone || '')}</span></div><section><b>Enquiry</b><p>${esc(row.enquiry)}</p></section><section><b>Qualification</b><p>${Number(row.qualification?.score || 0)}% · ${esc(label(row.qualification?.status))}</p>${Object.entries(answer).filter(([key]) => key !== 'risk_flags').map(([key, value]) => `<small><b>${esc(label(key))}</b> ${esc(value)}</small>`).join('')}</section><section class="srw-work-feed"><div class="srw-work-feed-title"><div><b>Customer work feed</b><p>One history from first enquiry to quote, job, invoice, payment and review.</p></div><span>${esc(label(feed.current_stage || 'enquiry'))}</span></div>${timeline}<button data-srw-panel="work_event">+ Add job update</button></section><section><b>Campaign and consent</b><p>${esc(label(row.source))} · response permission ${esc(label(row.consent?.contact_permission))}</p>${Object.entries(row.attribution || {}).map(([key, value]) => `<small><b>${esc(label(key))}</b> ${esc(value)}</small>`).join('')}<small>Outbound campaign permitted: ${row.consent?.outbound_campaign_allowed ? 'yes' : 'no'}</small></section><footer class="srw-detail-actions"><button data-srw-panel="qualify">Qualify</button><button data-srw-panel="call">Log conversation</button>${row.contact?.phone ? '<button data-srw-prepare-call>Prepare production call</button>' : ''}<button data-srw-panel="appointment" ${row.stage === 'qualified' || row.stage === 'human_handoff' || row.stage === 'appointment_proposed' ? '' : 'disabled'}>Prepare appointment</button><button data-srw-panel="handoff">Human handoff</button>${row.stage === 'proposal' ? '<button class="primary" data-srw-stage="won">Mark won</button>' : ''}${row.stage !== 'won' && row.stage !== 'lost' ? '<button data-srw-stage="lost">Close lost</button>' : ''}</footer></div></aside>`;
    }
    if (state.panel === 'work_event') {
      const contract = state.data?.work_feed_contract || {};
      const feed = row.work_feed || {};
      const stages = contract.lifecycle_stages || ['enquiry','qualification','appointment','survey','quote','negotiation','won','scheduled','procurement','in_progress','completed','invoiced','paid','review_requested','closed','lost'];
      const currentIndex = Math.max(0, stages.indexOf(feed.current_stage || 'enquiry'));
      const stageOptions = stages.slice(currentIndex).map((value) => `<option value="${esc(value)}">${esc(label(value))}</option>`).join('');
      const kinds = contract.event_kinds || ['note','photo','voice_instruction','quote_draft','customer_reply','supplier_request','material_quote','job_scheduled','work_started','work_completed','invoice_draft','payment_recorded','review_request'];
      return `<aside class="srw-panel"><form data-srw-form="work_event"><header><div><span>CUSTOMER WORK FEED</span><h2>Add a verified lifecycle update</h2><p>Record what happened, what AION prepared, or what still needs approval. Only connected adapters can mark an external action executed with a receipt.</p></div>${close}</header><div class="srw-two"><label>Update type<select name="event_kind">${kinds.map((value) => `<option value="${esc(value)}">${esc(label(value))}</option>`).join('')}</select></label><label>Lifecycle stage<select name="lifecycle_stage">${stageOptions}</select></label></div><label>Title<input name="title" required placeholder="e.g. Site survey completed"></label><label>Summary<textarea name="summary" rows="4" required placeholder="What happened, what was agreed, or what AION prepared"></textarea></label><label>Supporting details<textarea name="details" rows="4" placeholder="Scope, material costs, labour, dates, terms, customer questions or supplier requirements"></textarea></label><div class="srw-two"><label>Source<select name="source"><option value="pilot">Pilot conversation</option><option value="communications">Communications</option><option value="sales">Sales</option><option value="operations">Operations</option><option value="finance">Finance</option><option value="manual">Manual update</option></select></label><label>Status<select name="action_status"><option value="recorded">Recorded fact</option><option value="draft">Draft prepared</option><option value="approval_required">Approval required</option></select></label></div><div class="srw-two"><label>Attached file name<input name="attachment_name" placeholder="Optional"></label><label>File cabinet reference<input name="attachment_reference" placeholder="Optional local reference"></label></div>${recordedByField()}<footer><button type="button" data-srw-close>Cancel</button><button class="primary" type="submit">Add to customer feed</button></footer></form></aside>`;
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
    if (state.panel === 'detail' && selected()) return customerWorkspace();
    return `<section class="srw-shell" data-aion-sales-revenue><header><div><span>ENQUIRY · QUALIFY · BOOK · CONVERT</span><h2>Sales Revenue Spine</h2><p>One customer and opportunity record across Marketing, conversations, Operations, Finance and the Boardroom.</p></div><b>${state.busy ? 'WORKING…' : 'PROVIDER-NEUTRAL CRM'}</b></header>${state.error ? `<div class="srw-alert error">${esc(state.error)}</div>` : ''}${state.message ? `<div class="srw-alert good">${esc(state.message)}</div>` : ''}<nav><button data-srw-new>+ Add lead</button><button class="primary" data-srw-new-deal>+ Add deal</button></nav><section class="srw-deal-flow srw-unified-revenue-flow"><div class="srw-title"><div><span>LEADS AND OPPORTUNITIES</span><h3>Revenue flow</h3></div><small>One record · source to closed · no external writes</small></div>${pipeline()}</section>${callCentre()}${liveConsole()}${panel()}</section>`;
  }

  function syncActorHeaderControl() {
    document.querySelector('[data-srw-header-actor]')?.remove();
    const actions = document.querySelector('[data-aion-live-agents-sticky-header="true"] [data-aion-executive-sticky-actions="true"]');
    if (!actions || !state.data) return;
    const label = document.createElement('label');
    label.className = 'srw-header-actor';
    label.setAttribute('data-srw-header-actor', 'true');
    label.innerHTML = `<span>Signed in as</span><select data-srw-actor aria-label="Signed in as"><option value="">Select team member</option>${actorOptions(state.actorId)}</select>`;
    actions.appendChild(label);
  }

  function syncSalesWorkspaceChromeVisibility(anchor) {
    const workspace = anchor?.closest?.('[data-aion-sales-live-agents-workspace-o14d="true"]');
    if (!workspace) return;
    const customerRecordOpen = state.panel === 'detail' && Boolean(selected());
    workspace.toggleAttribute('data-srw-customer-record-open', customerRecordOpen);
    Array.from(workspace.children || []).forEach((child) => {
      if (!child.matches?.('[data-aion-unified-department-director="sales"], [data-aion-o14k-collapsed-package-dock="true"][data-aion-o14k-department="sales"]')) return;
      child.style.display = customerRecordOpen ? 'none' : '';
      child.setAttribute('aria-hidden', customerRecordOpen ? 'true' : 'false');
    });
  }

  function render() {
    const anchor = mount(); if (!anchor) return;
    syncSalesWorkspaceChromeVisibility(anchor);
    const active = document.activeElement;
    const activeForm = active?.closest?.('[data-srw-form]');
    if (activeForm) rememberFormDraft(activeForm);
    const activeKind = formKind(activeForm);
    const focusState = activeKind && active?.name ? {
      kind: activeKind,
      name: active.name,
      start: Number.isInteger(active.selectionStart) ? active.selectionStart : null,
      end: Number.isInteger(active.selectionEnd) ? active.selectionEnd : null,
    } : state.formFocus?.kind === state.panel ? state.formFocus : state.panel === 'enquiry' && state.enquiryFocus ? { kind: 'enquiry', ...state.enquiryFocus } : null;
    if (!state.data) {
      const existing = anchor.querySelector('[data-aion-sales-revenue]');
      const status = `<section class="srw-shell" data-aion-sales-revenue><header><div><span>ENQUIRY · QUALIFY · BOOK · CONVERT</span><h2>Sales Revenue Spine</h2><p>The Sales workspace is loading its customer, pipeline, voice and outreach records.</p></div><b>${state.loading ? 'LOADING…' : 'ATTENTION REQUIRED'}</b></header>${state.error ? `<div class="srw-alert error">${esc(state.error)}</div>` : ''}</section>`;
      if (existing) existing.outerHTML = status; else anchor.insertAdjacentHTML('afterbegin', status);
      return;
    }
    const current = anchor.querySelector('[data-aion-sales-revenue]');
    if (current) current.outerHTML = markup(); else anchor.insertAdjacentHTML('afterbegin', markup());
    syncActorHeaderControl();
    enhanceAgentSetupPanel(anchor);
    restoreFormDraft(anchor, state.panel);
    if (focusState?.kind === 'enquiry') restoreEnquiryFocus(anchor, focusState);
    else restoreFormFocus(anchor, focusState);
    global.requestAnimationFrame(() => { syncSourceCarouselControls(); syncDealCarouselControls(); });
  }

  async function load() {
    const id = businessId(); if (!id || !mount()) return;
    if (state.loading) return;
    state.loading = true;
    state.workspaceId = id; state.error = '';
    render();
    try {
      state.data = await request(`/api/aion/sales/${encodeURIComponent(id)}`);
      syncSignedInActor();
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
      if (state.panel === 'detail' && selected()) loadCustomerFinance(selected());
    }
    catch (error) { state.error = `Sales workspace could not load: ${error.message}`; render(); }
    finally { state.loading = false; }
  }

  async function post(path, body, message) {
    const completedPanel = state.panel;
    state.busy = true; state.error = ''; state.message = ''; render();
    try { await request(path, { method: 'POST', body: JSON.stringify(body) }); state.message = message; state.panel = null; clearFormDraft(completedPanel); await load(); }
    catch (error) { state.error = error.message; }
    finally { state.busy = false; render(); }
  }

  async function confirmCustomerPilotAction() {
    const row = selected(); const session = customerPilotSession(row); const action = session?.pendingAction;
    if (!row || !action) return;
    if (!state.actorId) { state.error = 'Select the authorised person acting on this Sales task'; render(); return; }
    state.busy = true; state.error = ''; render();
    try {
      const attachments = await uploadCustomerPilotAttachments(row, state.actorId);
      await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/opportunities/${encodeURIComponent(row.opportunity_id)}/work-feed/events`, {
        method: 'POST', body: JSON.stringify({
          kind: action.kind, title: action.title, summary: action.summary,
          details: { pilot_instruction: pilotInstructionDetail(row, session) },
          lifecycle_stage: action.lifecycleStage, source: 'pilot', provider: 'tessaris',
          source_reference: null, attachments,
          action: { status: 'recorded', external_action_performed: false },
          recorded_by_person_id: state.actorId,
        }),
      });
      session.pendingAction = null; clearCustomerPilotAttachments(row);
      state.message = `${action.title} added to ${row.contact?.name || 'the customer'} work feed.`;
      await load(); state.selectedId = row.opportunity_id; state.panel = 'detail';
    } catch (error) { state.error = error.message; }
    finally { state.busy = false; render(); }
  }

  document.addEventListener('keydown', (event) => {
    const input = event.target.closest?.('[data-srw-customer-pilot-footer] [data-aion-pilot-mission-input]');
    if (!input || event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    global.createAionPilotFrontendDraftMission?.();
  });

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-aion-sales-revenue] button, [data-aion-vault-website-intake] button'); if (!button) return;
    if (button.hasAttribute('data-srw-open-phone-vault')) {
      global.AionTelephonyVault?.open?.();
      return;
    }
    if (button.dataset.srwCopyValue) {
      try {
        await navigator.clipboard.writeText(button.dataset.srwCopyValue);
        state.intakeMessage = `${button.textContent.trim().replace(/^Copy\s+/i, '') || 'Value'} copied.`;
      } catch (_) { state.intakeError = 'This value could not be copied. Select and copy it manually.'; }
      renderVaultWebsiteIntake();
      return;
    }
    if (button.dataset.srwSourceFilter) { state.leadSourceFilter = button.dataset.srwSourceFilter; render(); return; }
    if (button.dataset.srwPipelineFilter) { state.pipelineFilter = button.dataset.srwPipelineFilter; render(); return; }
    if (button.dataset.srwSourceScroll) {
      const lane = button.closest('[data-srw-source-lane]');
      const strip = lane?.querySelector('.srw-source-strip');
      if (!strip) return;
      const direction = Number(button.dataset.srwSourceScroll) < 0 ? -1 : 1;
      strip.scrollBy({ left: direction * strip.clientWidth, behavior: 'smooth' });
      global.setTimeout(syncSourceCarouselControls, 350);
      return;
    }
    if (button.dataset.srwDealScroll) {
      const strip = button.closest('.srw-commercial-flow')?.querySelector('.srw-deal-strip');
      if (!strip) return;
      const direction = Number(button.dataset.srwDealScroll) < 0 ? -1 : 1;
      strip.scrollBy({ left: direction * Math.max(280, strip.clientWidth * .9), behavior: 'smooth' });
      global.setTimeout(syncDealCarouselControls, 350);
      return;
    }
    if (button.dataset.srwCustomerTab) {
      state.customerTab = button.dataset.srwCustomerTab;
      render();
      if (state.customerTab !== 'work' && !state.customerFinance.loaded) loadCustomerFinance();
      return;
    }
    if (button.hasAttribute('data-srw-pilot-invoice')) {
      const input = document.querySelector('[data-srw-customer-pilot-footer] [data-aion-pilot-mission-input]');
      if (input) { input.value = 'Pilot, prepare the invoice for this accepted job.'; input.focus(); }
      return;
    }
    if (button.dataset.srwOpenCommercialEvent) {
      const row = selected();
      const savedEvent = (row?.work_feed?.events || []).find((item) => item.event_id === button.dataset.srwOpenCommercialEvent);
      if (!row || !savedEvent?.details?.commercial_record) return;
      state.commercialDrafts[row.opportunity_id] = commercialDraftFromSavedEvent(row, savedEvent);
      const session = customerPilotSession(row); session.activeMode = state.commercialDrafts[row.opportunity_id].mode;
      session.quoteInterview = session.activeMode === 'new_quote' ? { active: false, stage: 'review', turns: [], provider: '', reopenedEventId: savedEvent.event_id } : session.quoteInterview;
      state.message = `${savedEvent.title || 'Quotation'} opened for review. Saving creates a traceable revision in the customer feed.`;
      render(); global.requestAnimationFrame(() => document.querySelector('[data-srw-form="commercial"]')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })); return;
    }
    if (button.dataset.srwCommercialMode) {
      readCommercialForm(button.closest('[data-aion-sales-revenue]')?.querySelector('[data-srw-form="commercial"]'));
      if (commercialDraft()?.mode === button.dataset.srwCommercialMode) collapseCommercialWorkbench();
      else activateCommercialMode(button.dataset.srwCommercialMode);
      return;
    }
    if (button.hasAttribute('data-srw-collapse-commercial')) {
      readCommercialForm(button.closest('[data-aion-sales-revenue]')?.querySelector('[data-srw-form="commercial"]'));
      collapseCommercialWorkbench(); return;
    }
    if (button.hasAttribute('data-srw-add-cost-line')) {
      const draft = readCommercialForm(button.closest('[data-srw-form="commercial"]'));
      draft.lines.push(newCommercialLine()); render(); return;
    }
    if (button.dataset.srwRemoveCostLine) {
      const draft = readCommercialForm(button.closest('[data-srw-form="commercial"]'));
      draft.lines = draft.lines.filter((line) => line.id !== button.dataset.srwRemoveCostLine);
      if (!draft.lines.length) draft.lines.push(newCommercialLine());
      render(); return;
    }
    if (button.hasAttribute('data-srw-generate-wording')) {
      const draft = readCommercialForm(button.closest('[data-srw-form="commercial"]'));
      draft.wording = generatedCustomerWording(selected(), draft); render(); return;
    }
    if (button.hasAttribute('data-srw-reset-commercial')) {
      if (!confirm('Reset this customer draft? Unsaved entries in the workbench will be cleared.')) return;
      delete state.commercialDrafts[state.selectedId]; clearFormDraft('commercial');
      const session = customerPilotSession(); if (session) { session.activeMode = ''; session.quoteInterview = null; }
      state.error = ''; state.message = 'The unsaved workbench draft was reset.'; render(); return;
    }
    if (button.hasAttribute('data-srw-pilot-open')) {
      const micState = global.getAionO21ELiveMicTranscriptState?.();
      if (micState?.recording) {
        global.stopAionO21ELiveMicTranscriptCapture?.();
        return;
      }
      const row = selected(); const session = customerPilotSession(row); session.open = true;
      global.__aionPilotVoiceConversationCancelled = false; global.__aionPilotAutoTurnTaking = true;
      global.setAionPilotRecordContext?.({ department: 'sales', opportunity_id: row.opportunity_id, customer_name: row.contact?.name || 'Customer', job_title: row.title || 'Customer job', lifecycle_stage: row.work_feed?.current_stage || row.stage, relationship: row.relationship || {}, contact: row.contact || {} });
      global.startAionPilotDictation?.();
      return;
    }
    if (button.hasAttribute('data-srw-pilot-close')) {
      customerPilotSession().open = false; global.__aionPilotVoiceConversationCancelled = true; global.__aionPilotAutoTurnTaking = false;
      if (global.getAionO21ELiveMicTranscriptState?.()?.recording) global.stopAionO21ELiveMicTranscriptCapture?.();
      global.setAionPilotRecordContext?.(null); render(); return;
    }
    if (button.hasAttribute('data-srw-pilot-confirm-action')) { await confirmCustomerPilotAction(); return; }
    if (button.dataset.srwPilotRemoveAttachment) {
      const session = customerPilotSession(); const item = session.attachments.find((entry) => entry.id === button.dataset.srwPilotRemoveAttachment);
      if (item?.previewUrl) { try { URL.revokeObjectURL(item.previewUrl); } catch (_) { /* Best-effort preview cleanup. */ } }
      session.attachments = session.attachments.filter((entry) => entry.id !== button.dataset.srwPilotRemoveAttachment); render(); return;
    }
    if (button.hasAttribute('data-srw-close')) { const closingPanel = state.panel; state.panel = null; if (closingPanel === 'detail') state.selectedId = ''; if (closingPanel === 'detail') state.customerTab = 'work'; if (closingPanel === 'detail') global.setAionPilotRecordContext?.(null); clearFormDraft(closingPanel); render(); return; }
    if (button.hasAttribute('data-srw-open-relationship')) { const details = document.querySelector('.srw-relationship'); if (details) { details.open = true; details.scrollIntoView?.({ behavior: 'smooth', block: 'start' }); } return; }
    if (button.hasAttribute('data-srw-new')) { clearFormDraft('enquiry'); state.panel = 'enquiry'; state.enquiryDraft = { actor: state.actorId, source: 'manual', entry_mode: 'lead' }; state.enquiryFocus = { name: 'customer_type', start: 0, end: 0 }; render(); return; }
    if (button.hasAttribute('data-srw-new-deal')) { clearFormDraft('enquiry'); state.panel = 'enquiry'; state.enquiryDraft = { actor: state.actorId, source: 'manual', entry_mode: 'existing_deal', initial_stage: 'new', currency: 'GBP' }; state.enquiryFocus = { name: 'customer_type', start: 0, end: 0 }; render(); return; }
    if (button.hasAttribute('data-srw-new-call-agent')) { clearFormDraft('call_agent_create'); state.selectedAgentId = ''; state.panel = 'call_agent_create'; render(); return; }
    if (button.dataset.srwEditCallAgent) { clearFormDraft('call_agent_builder'); state.selectedAgentId = button.dataset.srwEditCallAgent; state.panel = 'call_agent_builder'; render(); return; }
    if (button.dataset.srwTestCallAgent) {
      if (!state.actorId) { state.error = 'Select the authorised person running the safety check'; render(); return; }
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/call-centre/agents/${encodeURIComponent(button.dataset.srwTestCallAgent)}/test`, { run_by_person_id: state.actorId }, 'Safety check passed. Review the settings, then mint the exact contract.');
    }
    if (button.dataset.srwMintCallAgent) {
      if (!state.actorId) { state.error = 'Select the authorised person minting this contract'; render(); return; }
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/call-centre/agents/${encodeURIComponent(button.dataset.srwMintCallAgent)}/mint`, { expected_agent_hash: button.dataset.srwHash, minted_by_person_id: state.actorId }, 'The checked settings are now frozen as an immutable call contract. Switch the caller on when ready.');
    }
    if (button.dataset.srwStateCallAgent) {
      if (!state.actorId) { state.error = 'Select the authorised person changing this caller'; render(); return; }
      const nextState = button.dataset.srwAgentState;
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/call-centre/agents/${encodeURIComponent(button.dataset.srwStateCallAgent)}/state`, { state: nextState, expected_agent_hash: button.dataset.srwHash, changed_by_person_id: state.actorId }, nextState === 'active' ? 'Sales caller switched on. Provider, consent and exact-call controls remain enforced.' : 'Sales caller paused. It will not be selected for new calls.');
    }
    if (button.hasAttribute('data-srw-agent-setup')) { clearFormDraft('agent_setup'); state.panel = 'agent_setup'; render(); return; }
    if (button.dataset.srwOpen) {
      state.selectedId = button.dataset.srwOpen; state.panel = 'detail'; state.customerTab = 'work'; state.customerFinance.loaded = false;
      const row = selected(); const session = customerPilotSession(row); session.open = true;
      global.setAionPilotRecordContext?.({ department: 'sales', opportunity_id: row.opportunity_id, customer_name: row.contact?.name || 'Customer', job_title: row.title || 'Customer job', lifecycle_stage: row.work_feed?.current_stage || row.stage, relationship: row.relationship || {}, contact: row.contact || {} });
      render(); loadCustomerFinance(row); return;
    }
    if (button.dataset.srwPanel) { clearFormDraft(button.dataset.srwPanel); state.panel = button.dataset.srwPanel; render(); return; }
    if (button.hasAttribute('data-srw-create-intake')) {
      if (!state.actorId) { state.intakeError = 'A signed-in team member is required to create a website connection.'; renderVaultWebsiteIntake(); return; }
      const endpointName = String(global.prompt?.('Name this website connection', 'Website enquiry form') || '').trim();
      if (!endpointName) return;
      state.busy = true; state.intakeError = ''; state.intakeMessage = ''; renderVaultWebsiteIntake();
      try {
        const result = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/intake-endpoints`, { method: 'POST', body: JSON.stringify({ name: endpointName, created_by_person_id: state.actorId }) });
        state.intakeToken = result.endpoint.token; state.intakeMessage = 'Website connection created. Copy the endpoint and one-time secret into the website’s server setup.';
        state.data = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}`);
      } catch (error) { state.intakeError = error.message; } finally { state.busy = false; renderVaultWebsiteIntake(); }
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
      if (!state.actorId) { state.intakeError = 'A signed-in team member is required to import HomeFixed enquiries.'; renderVaultWebsiteIntake(); return; }
      state.busy = true; state.intakeError = ''; state.intakeMessage = ''; renderVaultWebsiteIntake();
      try {
        const result = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/homefixed-queue/poll`, { method: 'POST', body: JSON.stringify({ imported_by_person_id: state.actorId }) });
        state.intakeMessage = `${result.imported} new HomeFixed enquiries imported (${result.human_enquiries} human, ${result.agent_requests} agent); ${result.deduplicated} duplicates safely ignored.`;
        state.data = await request(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}`);
      } catch (error) { state.intakeError = error.message; } finally { state.busy = false; renderVaultWebsiteIntake(); }
      return;
    }
    if (button.hasAttribute('data-srw-simulate')) {
      if (!state.actorId) { state.error = 'Select the authorised person running the agent examination'; render(); return; }
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/playbooks/inbound-enquiry/simulations`, { run_by_person_id: state.actorId }, 'Safety check complete. Review the result before approving this call plan.');
    }
    if (button.hasAttribute('data-srw-promote')) {
      if (!state.actorId) { state.error = 'Select the authorised person promoting this exact agent version'; render(); return; }
      return post(`/api/aion/sales/${encodeURIComponent(state.workspaceId)}/playbooks/inbound-enquiry/promote`, { expected_playbook_hash: state.data.playbook.playbook_hash, promoted_by_person_id: state.actorId }, 'This call plan is approved for controlled use. No call was started or scheduled.');
    }
    if (button.hasAttribute('data-srw-prepare-call')) {
      if (!state.actorId) { state.error = 'Select the authorised person preparing this call'; render(); return; }
      const callers = (state.data?.sales_agents || []).filter((item) => item.state === 'active' && ['outbound','both'].includes(item.direction));
      if (!callers.length) { state.error = 'Switch on an outbound sales caller before preparing this call.'; render(); return; }
      clearFormDraft('prepare_call'); state.panel = 'prepare_call'; render(); return;
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
    if (event.target.hasAttribute('data-srw-pipeline-filter')) {
      state.pipelineFilter = event.target.value || 'new';
      render();
      return;
    }
    if (event.target.matches?.('[data-srw-form="enquiry"] [name="customer_type"]')) {
      const form = event.target.closest('[data-srw-form="enquiry"]');
      rememberEnquiryDraft(form); rememberEnquiryFocus(event.target); render(); return;
    }
    if (event.target.hasAttribute('data-srw-pilot-action')) {
      if (event.target.value) activateCommercialMode(event.target.value, { fresh: true, announce: true });
      return;
    }
    if (event.target.matches?.('[data-srw-expense-file],[data-srw-expense-camera]')) {
      const file = event.target.files?.[0];
      const type = document.querySelector('[data-srw-expense-type]')?.value || 'receipt';
      event.target.value = '';
      if (file) uploadCustomerJobExpense(file, type);
      return;
    }
    if (event.target.matches?.('[data-srw-pilot-files],[data-srw-pilot-camera]')) {
      addCustomerPilotAttachments(event.target.files); event.target.value = ''; return;
    }
    if (event.target.hasAttribute('data-srw-actor')) {
      state.actorId = event.target.value;
      try { global.localStorage?.setItem(actorStorageKey(), state.actorId); } catch (_) { /* Storage is optional. */ }
    }
    const form = event.target.closest?.('[data-srw-form]');
    if (form) {
      if (formKind(form) === 'commercial') readCommercialForm(form);
      rememberFormDraft(form); rememberFormFocus(event.target);
      if (formKind(form) === 'enquiry') { rememberEnquiryDraft(form); rememberEnquiryFocus(event.target); }
      if (formKind(form) === 'commercial' && event.target.hasAttribute('data-srw-commercial-recalculate')) render();
    }
  });

  document.addEventListener('input', (event) => {
    if (event.target.hasAttribute?.('data-srw-deal-search')) {
      const cursor = Number.isInteger(event.target.selectionStart) ? event.target.selectionStart : String(event.target.value || '').length;
      state.pipelineSearch = event.target.value;
      render();
      const search = document.querySelector('[data-srw-deal-search]');
      if (search) { search.focus({ preventScroll: true }); try { search.setSelectionRange(cursor, cursor); } catch (_) { /* Search inputs may not expose a range. */ } }
      return;
    }
    const form = event.target.closest?.('[data-srw-form]');
    if (form) {
      if (formKind(form) === 'commercial') readCommercialForm(form);
      rememberFormDraft(form); rememberFormFocus(event.target);
      if (formKind(form) === 'enquiry') { rememberEnquiryDraft(form); rememberEnquiryFocus(event.target); }
      if (formKind(form) === 'commercial' && event.target.hasAttribute('data-srw-commercial-recalculate')) render();
    }
  });

  document.addEventListener('focusin', (event) => {
    rememberFormFocus(event.target);
    if (event.target.closest?.('[data-srw-form="enquiry"]')) rememberEnquiryFocus(event.target);
  });

  document.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-aion-sales-revenue] form'); if (!form) return;
    event.preventDefault(); if (state.busy) return;
    const value = values(form); const kind = form.dataset.srwForm;
    const actor = value.actor || state.actorId;
    if (!actor) { state.error = 'Select the authorised person acting on this Sales task'; render(); return; }
    const base = `/api/aion/sales/${encodeURIComponent(state.workspaceId)}`;
    if (kind === 'call_agent_create') {
      state.busy = true; state.error = ''; render();
      try {
        const result = await request(`${base}/call-centre/agents`, { method: 'POST', body: JSON.stringify({ name: value.name, direction: value.direction || 'inbound', created_by_person_id: actor }) });
        state.selectedAgentId = result.agent.agent_id; clearFormDraft(kind); await load(); state.selectedAgentId = result.agent.agent_id; state.panel = 'call_agent_builder';
      } catch (error) { state.error = error.message; }
      finally { state.busy = false; render(); }
      return;
    }
    if (kind === 'call_agent_builder') {
      const agent = selectedSalesAgent(); if (!agent) return;
      const formData = new FormData(form);
      const standardLabels = { customer_name: 'Customer name', customer_need: 'What the customer needs', email: 'Email address', phone: 'Telephone number', location: 'Location', full_address: 'Full address', timescale: 'Timescale', budget: 'Budget or price expectation', decision_authority: 'Decision authority', product_interest: 'Product or service interest', preferred_follow_up: 'Preferred follow-up', next_step: 'Agreed next step' };
      const captureFields = formData.getAll('capture_field').map((key) => ({ key, label: standardLabels[key] || label(key), type: key === 'email' ? 'email' : key === 'phone' ? 'phone' : key === 'budget' ? 'number' : key === 'customer_need' ? 'long_text' : 'text', required: true }));
      String(value.custom_capture_fields || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean).forEach((line) => {
        const [rawLabel, rawType, rawRequired] = line.split('|').map((item) => String(item || '').trim());
        if (!rawLabel) return;
        const key = rawLabel.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 80);
        captureFields.push({ key, label: rawLabel, type: ['text','long_text','email','phone','number','date','boolean'].includes(rawType) ? rawType : 'text', required: rawRequired !== 'optional' });
      });
      const setup = {
        name: value.name, direction: value.direction,
        phone_assignment: { number: value.phone_number || null, provider: agent.phone_assignment?.provider || 'retell', provider_agent_id: agent.phone_assignment?.provider_agent_id || state.data?.telephony?.agent_id || null, inbound_routing_confirmed: Boolean(agent.phone_assignment?.inbound_routing_confirmed) },
        knowledge: { business_name: value.business_name, business_summary: value.business_summary, approved_offers: value.approved_offers, service_areas: value.service_areas, approved_facts: value.approved_facts, unknown_answer: value.unknown_answer },
        objective: { primary_outcome: value.primary_outcome, success_definition: value.success_definition, close_strategy: value.close_strategy },
        capture_fields: captureFields,
        allowed_actions: formData.getAll('allowed_action'),
        conversation: { opening: value.opening, tone: value.tone, guidance: value.guidance, languages: String(value.languages || 'en-GB').split(',').map((item) => item.trim()).filter(Boolean) },
        routing: { human_handoff: value.human_handoff, maximum_phone_attempts: Number(value.maximum_phone_attempts || 1), unanswered_action: value.unanswered_action || 'human_review' },
      };
      state.busy = true; state.error = ''; render();
      try {
        await request(`${base}/call-centre/agents/${encodeURIComponent(agent.agent_id)}`, { method: 'PUT', body: JSON.stringify({ setup, expected_agent_hash: agent.agent_hash, configured_by_person_id: actor }) });
        state.message = 'Sales caller saved. Run the safety check, then mint the exact contract.'; state.panel = null; clearFormDraft(kind); await load();
      } catch (error) { state.error = error.message; }
      finally { state.busy = false; render(); }
      return;
    }
    if (kind === 'prepare_call') {
      const agent = (state.data?.sales_agents || []).find((item) => item.agent_id === value.agent_id);
      if (!agent || agent.state !== 'active' || !['outbound','both'].includes(agent.direction)) {
        state.error = 'Choose an active outbound sales caller.'; render(); return;
      }
      return post(`${base}/opportunities/${encodeURIComponent(state.selectedId)}/calls/prepare`, {
        reason: value.reason,
        prepared_by_person_id: actor,
        agent_id: agent.agent_id,
      }, `Call prepared with ${agent.name}. It has not started and requires exact approval.`);
    }
    if (kind === 'enquiry') {
      if (!String(value.email || '').trim() && !String(value.phone || '').trim()) {
        state.error = 'Add at least one contact method: email or phone.';
        rememberEnquiryDraft(form);
        render();
        return;
      }
      const contactName = [value.first_name, value.last_name].filter(Boolean).join(' ').trim();
      return post(`${base}/enquiries`, { name: contactName, customer_type: value.customer_type,
        first_name: value.first_name || null, last_name: value.last_name || null,
        company_name: value.customer_type === 'business' ? value.company_name || null : null,
        position_title: value.customer_type === 'business' ? value.position_title || null : null,
        department: value.customer_type === 'business' ? value.department || null : null,
        phone_extension: value.customer_type === 'business' ? value.phone_extension || null : null,
        entry_mode: value.entry_mode || 'lead', initial_stage: value.initial_stage || 'new',
        estimated_value: value.estimated_value ? Number(value.estimated_value) : null,
        currency: value.currency || 'GBP', next_action: value.next_action || null,
        address: value.address || null, email: value.email || null, phone: value.phone || null,
        enquiry: value.enquiry, source: value.source, source_reference: value.source_reference || null,
        attribution: {}, consent: {}, created_by_person_id: actor },
      'Enquiry added and deduplicated against the customer ledger.');
    }
    const opportunity = `${base}/opportunities/${encodeURIComponent(state.selectedId)}`;
    if (kind === 'relationship') {
      const opportunityId = state.selectedId; state.busy = true; state.error = ''; render();
      try {
        await request(`${opportunity}/relationship`, { method: 'POST', body: JSON.stringify({
          relationship_status: value.relationship_status, priority: value.priority,
          preferred_channel: value.preferred_channel, next_action: value.next_action || null,
          next_action_due: value.next_action_due || null,
          tags: String(value.tags || '').split(',').map((item) => item.trim()).filter(Boolean),
          owner_person_id: value.owner_person_id, address: value.address || null,
          updated_by_person_id: actor,
        }) });
        state.message = 'Relationship details saved and added to the customer history.';
        await load(); state.selectedId = opportunityId; state.panel = 'detail';
      } catch (error) { state.error = error.message; }
      finally { state.busy = false; render(); }
      return;
    }
    if (kind === 'commercial') {
      const row = selected(); const draft = readCommercialForm(form); const totals = commercialTotals(draft);
      const modeLabel = commercialModes.find(([mode]) => mode === draft.mode)?.[1] || 'Commercial record';
      const currentStage = row?.work_feed?.current_stage || 'enquiry';
      const eventKind = draft.mode === 'internal_note' ? 'note' : draft.mode === 'invoice_add_on' ? 'invoice_draft' : draft.mode === 'new_job' ? 'status_update' : 'quote_draft';
      const lifecycleStage = draft.mode === 'invoice_add_on' ? laterLifecycleStage(currentStage, 'invoiced') : (draft.mode === 'new_quote' || draft.mode === 'quote_variation') ? laterLifecycleStage(currentStage, 'quote') : currentStage;
      const cleanLines = totals.lines.map((line) => ({
        category: line.category, description: line.description, quantity: line.quantity,
        internal_unit_cost: roundMoney(line.internalUnitCost), customer_unit_price: roundMoney(line.customerUnitPrice),
        internal_total: line.internalTotal, customer_total: line.customerTotal,
        person_id: line.category === 'labour' ? line.personId || null : null,
      }));
      const commercialRecord = {
        mode: draft.mode, reference: draft.reference || null, title: draft.title,
        currency: commercialCurrency(row),
        scope: draft.scope || null, scope_summary: draft.quoteScopeSummary || null,
        scope_items: draft.quoteScopeItems || [], exclusions: draft.quoteExclusions || [], duration: draft.quoteDuration || null,
        internal_note: draft.internalNote,
        lines: draft.mode === 'internal_note' ? [] : cleanLines,
        totals: draft.mode === 'internal_note' ? {} : {
          internal_cost: totals.internalCost, customer_net: totals.net, tax_rate: totals.taxRate,
          tax: totals.tax, customer_gross: totals.gross, gross_profit: totals.grossProfit,
          gross_margin_percentage: totals.grossMargin,
        },
        terms: draft.mode === 'internal_note' ? null : draft.terms,
      };
      const details = { commercial_record: commercialRecord, revision_of_event_id: draft.editingEventId || null };
      if (draft.mode !== 'internal_note') details.customer_facing = {
        wording: draft.wording || generatedCustomerWording(row, draft, totals),
        currency: commercialCurrency(row),
        scope: draft.scope, scope_summary: draft.quoteScopeSummary || '', scope_items: draft.quoteScopeItems || [], exclusions: draft.quoteExclusions || [], duration: draft.quoteDuration || null,
        lines: cleanLines.map((line) => ({ description: line.description, quantity: line.quantity, unit_price: line.customer_unit_price, total: line.customer_total })),
        net: totals.net, tax_rate: totals.taxRate, tax: totals.tax, gross: totals.gross, terms: draft.terms,
      };
      const opportunityId = state.selectedId;
      const payload = {
        kind: eventKind, title: draft.title,
        summary: draft.mode === 'internal_note' ? draft.internalNote : `${modeLabel} draft saved for ${row?.contact?.name || 'customer'}${draft.reference ? ` (${draft.reference})` : ''}. Customer total ${money(totals.gross)}.`,
        details, lifecycle_stage: lifecycleStage, source: 'sales', provider: 'tessaris',
        source_reference: draft.reference || null, attachments: [],
        action: { status: draft.mode === 'internal_note' ? 'recorded' : 'draft', external_action_performed: false },
        recorded_by_person_id: actor,
      };
      state.busy = true; state.error = ''; state.message = ''; render();
      try {
        payload.attachments = await uploadCustomerPilotAttachments(row, actor);
        await request(`${opportunity}/work-feed/events`, { method: 'POST', body: JSON.stringify(payload) });
        const pilotSession = customerPilotSession(row);
        if (draft.mode === 'new_quote' && pilotSession?.quoteInterview) { pilotSession.quoteInterview.active = false; pilotSession.quoteInterview.stage = 'review'; }
        else if (pilotSession) { pilotSession.activeMode = ''; pilotSession.quoteInterview = null; }
        delete state.commercialDrafts[opportunityId]; clearFormDraft('commercial'); clearCustomerPilotAttachments(row);
        state.selectedId = opportunityId; state.panel = 'detail';
        state.message = draft.mode === 'internal_note' ? 'Internal note saved to this customer’s work feed.' : `${modeLabel} saved as a customer-bound draft. No external action was performed.`;
        await load(); state.selectedId = opportunityId; state.panel = 'detail';
      } catch (error) { state.error = error.message; }
      finally { state.busy = false; render(); }
      return;
    }
    if (kind === 'agent_setup') {
      const data = new FormData(form); const destination = value.evidence_route_destination || null;
      state.busy = true; state.error = ''; render();
      try {
        await request(`${base}/playbooks/inbound-enquiry/agent-setup`, { method: 'PUT', body: JSON.stringify({ expected_playbook_hash: state.data.playbook.playbook_hash, configured_by_person_id: actor, setup: { business_motion: value.business_motion, lead_temperature: value.lead_temperature, primary_goal: value.primary_goal, close_strategy: value.close_strategy, intro_style: value.intro_style, custom_intro: value.custom_intro, sales_script: value.sales_script, required_fields: data.getAll('required_fields'), allowed_actions: data.getAll('allowed_actions'), evidence_route: { mode: value.evidence_route_mode, destination }, contact_sequence: { maximum_phone_attempts: Number(value.maximum_phone_attempts || 2), fallback_channel: value.fallback_channel || 'email', questions_per_written_message: Number(value.questions_per_written_message || 2) } } }) });
        state.message = 'Call plan saved. Run the safety check, then approve it before preparing customer calls.'; state.panel = null; clearFormDraft('agent_setup'); await load();
      } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
      return;
    }
    if (kind === 'work_event') {
      const attachments = value.attachment_name ? [{
        name: value.attachment_name,
        media_type: 'application/octet-stream',
        source_reference: value.attachment_reference || null,
      }] : [];
      return post(`${opportunity}/work-feed/events`, {
        kind: value.event_kind,
        title: value.title,
        summary: value.summary,
        details: value.details ? { note: value.details } : {},
        lifecycle_stage: value.lifecycle_stage,
        source: value.source,
        provider: 'tessaris',
        source_reference: value.attachment_reference || null,
        attachments,
        action: { status: value.action_status, external_action_performed: false },
        recorded_by_person_id: actor,
      }, 'Customer and job history updated. No external action was claimed.');
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
        state.message = 'Conversation outcome recorded. No external call was initiated.'; state.panel = null; clearFormDraft('call'); await load();
      } catch (error) { state.error = error.message; } finally { state.busy = false; render(); }
    }
  });

  async function recordQuoteEmailOutcome(outcome = {}) {
    const opportunityId = String(outcome.opportunity_id || state.selectedId || '').trim();
    const row = (state.data?.opportunities || []).find((item) => item.opportunity_id === opportunityId);
    const person = actorById(state.actorId) || syncSignedInActor();
    if (!row || !person) throw new Error('A signed-in authorised person is required to record quote approval and sending.');
    const latestQuote = (row.work_feed?.events || []).slice().reverse().find((item) => item.kind === 'quote_draft' && item.details?.commercial_record);
    const receipt = outcome.receipt || {};
    const receiptReference = String(receipt.receipt_hash || receipt.message_id || receipt.id || outcome.receipt_reference || '').trim() || null;
    const base = `/api/aion/sales/${encodeURIComponent(state.workspaceId)}/opportunities/${encodeURIComponent(opportunityId)}/work-feed/events`;
    const approvalDetails = {
      quote_event_id: latestQuote?.event_id || null,
      approved_by_person_id: person.person_id,
      approved_by_name: person.name,
      recipient: String(outcome.to || '').trim() || null,
      subject: String(outcome.subject || '').trim() || null,
      approval_mode: outcome.approval_granted === false ? 'standing_authority' : 'exact_user_approval',
    };
    const sendDetails = { ...approvalDetails, sent_by_person_id: person.person_id, sent_by_name: person.name };
    await request(base, { method: 'POST', body: JSON.stringify({
      kind: 'quote_approved', title: 'Quotation approved for sending',
      summary: `${person.name} approved this quotation for sending${approvalDetails.recipient ? ` to ${approvalDetails.recipient}` : ''}.`,
      details: approvalDetails, lifecycle_stage: laterLifecycleStage(row.work_feed?.current_stage || 'quote', 'quote'),
      source: 'pilot', provider: 'tessaris', source_reference: latestQuote?.event_id || null, attachments: [],
      action: { status: 'approved', external_action_performed: false, approval_type: 'quote_email_send' },
      recorded_by_person_id: person.person_id,
    }) });
    await request(base, { method: 'POST', body: JSON.stringify({
      kind: 'quote_sent', title: 'Quotation sent',
      summary: `${person.name} sent the approved quotation${sendDetails.recipient ? ` to ${sendDetails.recipient}` : ''}.`,
      details: sendDetails, lifecycle_stage: laterLifecycleStage(row.work_feed?.current_stage || 'quote', 'quote'),
      source: 'pilot', provider: 'gmail', source_reference: receiptReference, attachments: [],
      action: { status: 'executed', external_action_performed: true, approval_type: 'quote_email_send', receipt_reference: receiptReference },
      recorded_by_person_id: person.person_id,
    }) });
    await load();
    state.selectedId = opportunityId; state.panel = 'detail';
    state.message = `Quotation approved and sent by ${person.name}. The approval and Gmail receipt are recorded separately.`;
    render();
    return { ok: true, person_id: person.person_id, person_name: person.name, receipt_reference: receiptReference };
  }

  function installStyles() {
    document.getElementById('aion-sales-revenue-styles')?.remove();
    const style = document.createElement('style'); style.id = 'aion-sales-revenue-styles'; style.textContent = `.srw-shell{--ink:#102a43;--muted:#52677e;--line:#cbd9e6;--teal:#0f766e;--green:#15803d;box-sizing:border-box;background:#fff;color:var(--ink);border:2px solid #0ea5e9;margin:0 0 22px;font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}.srw-shell *{box-sizing:border-box}.srw-shell>header{display:flex;justify-content:space-between;gap:20px;padding:20px 22px;border-bottom:1px solid var(--line)}.srw-shell>header span,.srw-title span,.srw-studio>div>span,.srw-panel header span,.srw-capabilities span,.srw-console header span{color:var(--teal);font-size:10px;font-weight:900;letter-spacing:.2em}.srw-shell h2,.srw-shell h3{margin:5px 0!important}.srw-shell h2{font-size:25px!important}.srw-shell p{color:var(--muted)!important}.srw-shell button{background:#fff!important;color:#075985!important;border:1px solid #8fb3c7!important;padding:9px 12px!important;font-weight:800!important;cursor:pointer;text-align:left}.srw-shell button.primary{background:var(--green)!important;color:#fff!important;border-color:var(--green)!important}.srw-shell button:disabled{opacity:.4}.srw-shell>nav{display:flex;justify-content:flex-end;align-items:end;gap:8px;padding:12px 18px;border-bottom:1px solid var(--line)}.srw-shell>nav label{display:grid;gap:3px;margin-right:auto;font-size:9px;font-weight:900}.srw-shell select{background:#fff;color:var(--ink);border:1px solid #94a3b8;padding:8px}.srw-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:14px 18px;background:#f8fafc}.srw-metrics article{border:1px solid var(--line);background:#fff;padding:12px}.srw-metrics strong,.srw-metrics span,.srw-metrics small{display:block}.srw-metrics strong{font-size:20px}.srw-metrics span{font-size:11px;font-weight:800}.srw-metrics small{color:#64748b}.srw-capabilities{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:18px 18px 0}.srw-capabilities>article{border:1px solid var(--line);border-top:4px solid #0ea5e9;padding:14px;background:#f8fafc}.srw-capabilities small{display:block;color:#64748b}.srw-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}.srw-token,.srw-endpoint{display:grid;gap:5px;margin-top:10px;padding:9px;background:#fff7ed;border:1px solid #fdba74}.srw-token code,.srw-endpoint code{overflow-wrap:anywhere;font-size:10px}.srw-grid{display:grid;grid-template-columns:minmax(260px,.65fr) minmax(0,1.35fr);gap:14px;padding:18px}.srw-grid>section{border:1px solid var(--line);padding:14px;min-width:0}.srw-title{display:flex;justify-content:space-between;align-items:start;border-bottom:1px solid var(--line);margin-bottom:10px}.srw-queue{display:grid;gap:7px}.srw-queue>button{display:grid!important;gap:4px!important;width:100%}.srw-queue>button span{display:flex;gap:6px;align-items:center}.srw-queue small{color:#64748b}.srw-stage{display:inline-block;background:#e0f2fe;color:#075985;padding:3px 6px;font-size:9px;font-weight:900}.srw-stage.attention{background:#ffedd5;color:#9a3412}.srw-pipeline{display:flex;gap:8px;overflow:auto;padding-bottom:8px}.srw-pipeline>section{flex:0 0 190px;background:#f8fafc;border:1px solid var(--line);padding:8px}.srw-pipeline>section>header{display:flex;justify-content:space-between;margin-bottom:7px}.srw-pipeline>section>button{display:grid!important;width:100%;gap:4px;margin-bottom:6px;padding:8px!important}.srw-pipeline>section>button span,.srw-pipeline>section>button small{color:#64748b;font-size:10px}.srw-pipeline>section>p{font-size:11px;text-align:center}.srw-empty{padding:20px;text-align:center;border:1px dashed #7dd3fc;background:#f0f9ff}.srw-studio{margin:0 18px 18px;border-left:4px solid #8b5cf6;background:#f5f3ff;padding:15px;display:grid;grid-template-columns:1fr auto;gap:16px}.srw-studio-status{display:grid;align-content:start;gap:4px}.srw-studio details{grid-column:1/-1;border-top:1px solid #c4b5fd;padding-top:10px}.srw-studio summary{cursor:pointer;font-weight:900}.srw-studio-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.srw-studio-grid p{font-size:11px}.srw-console{margin:0 18px 18px;border:1px solid #94a3b8;background:#f8fafc}.srw-console>header{display:flex;justify-content:space-between;gap:14px;padding:15px;border-bottom:1px solid var(--line)}.srw-console>header>div:last-child{display:grid;text-align:right}.srw-console-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:14px}.srw-console-grid>div>article{display:grid;gap:5px;background:#fff;border:1px solid var(--line);padding:10px;margin-top:7px}.srw-console-grid article p{font-size:11px;margin:3px 0!important}.srw-console>footer{padding:10px 14px;border-top:1px solid var(--line);font-size:10px;color:#64748b}.srw-alert{margin:12px 18px 0;padding:10px;border-left:4px solid}.srw-alert.error{background:#fef2f2;border-color:#dc2626}.srw-alert.good{background:#ecfdf5;border-color:#16a34a}.srw-panel{position:fixed;z-index:11600;inset:0 0 0 auto;width:min(620px,98vw);overflow:auto;background:#fff;box-shadow:-20px 0 60px rgba(15,23,42,.28)}.srw-panel form,.srw-detail{display:grid;gap:14px;padding:24px}.srw-panel header{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:13px}.srw-panel label{display:grid;gap:5px;font-size:10px;font-weight:900}.srw-panel input,.srw-panel select,.srw-panel textarea{width:100%;background:#fff!important;color:var(--ink)!important;border:1px solid #94a3b8!important;padding:10px}.srw-panel footer{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;border-top:1px solid var(--line);padding-top:13px}.srw-two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.srw-detail-status{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.srw-detail section{border-left:3px solid #0ea5e9;padding:9px 12px;background:#f8fafc}.srw-detail section p,.srw-detail section small{display:block;margin:5px 0!important}.srw-detail-actions{justify-content:flex-start!important}.srw-customer-page{min-height:calc(100vh - 150px)}.srw-customer-page-header{align-items:center;background:#fff}.srw-customer-page-actions{display:flex;gap:8px;align-items:center}.srw-customer-page-body{display:grid;grid-template-columns:minmax(270px,.72fr) minmax(0,1.28fr);gap:18px;padding:20px;background:#f8fafc}.srw-customer-overview,.srw-customer-feed-column{display:grid;gap:14px;align-content:start}.srw-customer-card{border-left:4px solid #0ea5e9;padding:14px;background:#fff}.srw-customer-card p,.srw-customer-card small{display:block;margin:6px 0!important}.srw-work-feed{border-left:4px solid #14b8a6;padding:16px;background:#fff}.srw-work-feed-title{display:flex;justify-content:space-between;gap:12px;align-items:start}.srw-work-feed-title>span{background:#ccfbf1;color:#0f766e;padding:4px 7px;font-size:9px;font-weight:900;letter-spacing:.12em}.srw-work-event{border:1px solid var(--line);padding:12px;margin:10px 0;background:#fff}.srw-work-event>div{display:flex;justify-content:space-between;gap:10px}.srw-work-event span,.srw-work-event small{display:block;color:#64748b;font-size:10px}.srw-customer-toolbar{display:flex;gap:8px;flex-wrap:wrap;padding:14px;background:#fff;border-top:1px solid var(--line)}@media(max-width:900px){.srw-grid,.srw-capabilities,.srw-console-grid,.srw-customer-page-body{grid-template-columns:1fr}.srw-metrics{grid-template-columns:1fr 1fr}.srw-studio{grid-template-columns:1fr}.srw-studio-status,.srw-studio details{grid-column:1}.srw-studio-grid,.srw-two{grid-template-columns:1fr}.srw-customer-page-header{align-items:flex-start}.srw-customer-page-actions{flex-wrap:wrap}}`;
    style.textContent += '.srw-checks{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px;border:1px solid var(--line);background:#f8fafc}.srw-checks>b,.srw-checks>small{grid-column:1/-1}.srw-checks label{display:flex;align-items:center;gap:8px;font-size:11px}.srw-checks input{width:auto!important;padding:0!important}';
    style.textContent += '.srw-recorded-by{display:grid;align-content:center;gap:3px;min-height:58px;padding:9px 11px;border-left:4px solid #14b8a6;background:#ecfdf5}.srw-recorded-by>span{color:#0f766e;font-size:9px;font-weight:900;letter-spacing:.1em;text-transform:uppercase}.srw-recorded-by>b{color:#102a43}.srw-recorded-by>small{color:#52677e}.srw-event-actors{color:#0f766e!important;font-weight:900}';
    style.textContent += '.srw-customer-page .srw-customer-page-header{align-items:flex-start}.srw-customer-identity{display:grid;gap:7px;min-width:0}.srw-customer-identity h2{margin:0!important}.srw-customer-identity>p{margin:3px 0 0!important;font-size:16px}.srw-customer-contact-line{display:flex;align-items:center;gap:8px 18px;flex-wrap:wrap;color:#334e68}.srw-customer-contact-line>span:not(.srw-stage){font-size:11px}.srw-customer-contact-line b{color:#0f766e;font-size:9px;letter-spacing:.08em;text-transform:uppercase}.srw-customer-page .srw-customer-page-body{grid-template-columns:minmax(0,1fr)}.srw-customer-page .srw-customer-feed-column{width:100%}.srw-customer-page .srw-work-feed{width:100%}@media(max-width:700px){.srw-customer-contact-line{align-items:flex-start;flex-direction:column;gap:5px}.srw-customer-page-actions{width:100%}}';
    style.textContent += '.srw-work-feed{display:grid;gap:9px!important;border-left-color:#14b8a6!important}.srw-work-feed-title{display:flex;justify-content:space-between;gap:12px;align-items:start}.srw-work-feed-title p{margin:3px 0 0!important;font-size:11px}.srw-work-feed-title>span{white-space:nowrap;background:#ccfbf1;color:#115e59;padding:4px 7px;font-size:9px;font-weight:900;letter-spacing:.08em}.srw-work-event{display:grid;gap:4px;padding:9px 10px;border:1px solid #d8e4ec;background:#fff}.srw-work-event>header{display:flex;align-items:center;gap:7px;padding:0;border:0}.srw-work-event>header b{font-size:11px}.srw-work-event>header span{margin-left:auto;color:#64748b;font-size:9px;font-weight:800;letter-spacing:0}.srw-work-event>p{margin:0!important;font-size:11px}.srw-work-event>small{color:#64748b}.srw-work-event.srw-executed{border-left:4px solid #16a34a}.srw-work-event .srw-stage{margin-right:2px}.srw-feed-images{display:flex;gap:7px;overflow:auto;margin:5px 0}.srw-feed-images img{display:block;width:92px;height:68px;object-fit:cover;border:1px solid #cbd9e6;background:#f8fafc}';
    style.textContent += '.srw-commercial-workbench{margin:0 20px 20px;border:1px solid #b7c9d8;border-top:5px solid #0ea5e9;background:#fff}.srw-commercial-workbench>header{padding:18px 20px}.srw-commercial-workbench>header span,.srw-commercial-customer>span,.srw-customer-preview>header span{display:block;color:#0f766e;font-size:10px;font-weight:900;letter-spacing:.16em}.srw-commercial-workbench>header p{margin:4px 0 0!important}.srw-commercial-modes{display:flex;gap:7px;flex-wrap:wrap;padding:12px 20px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:#f8fafc}.srw-commercial-modes button.active{background:#075985!important;border-color:#075985!important;color:#fff!important}.srw-commercial-workbench form{display:grid;gap:16px;padding:20px}.srw-commercial-workbench label{display:grid;gap:5px;font-size:10px;font-weight:900}.srw-commercial-workbench input,.srw-commercial-workbench select,.srw-commercial-workbench textarea{width:100%;padding:10px;border:1px solid #94a3b8;background:#fff;color:var(--ink)}.srw-commercial-workbench label small{color:#b45309}.srw-commercial-workbench form>footer{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;padding-top:16px;border-top:1px solid var(--line)}.srw-commercial-customer{display:grid;gap:4px;padding:12px 14px;border-left:4px solid #0ea5e9;background:#f0f9ff}.srw-commercial-customer>b{font-size:16px}.srw-commercial-customer small{color:#52677e}.srw-costs{border:1px solid var(--line);background:#f8fafc}.srw-costs>header,.srw-customer-preview>header{display:flex;justify-content:space-between;align-items:start;gap:12px;padding:12px 14px;border-bottom:1px solid var(--line);background:#f1f5f9}.srw-costs>header div,.srw-customer-preview>header div{display:grid;gap:3px}.srw-costs>header small{color:#64748b}.srw-cost-line{display:grid;grid-template-columns:1fr minmax(180px,1.6fr) .65fr .8fr .8fr 1fr auto auto;gap:8px;align-items:end;padding:12px;border-bottom:1px solid #d8e4ec;background:#fff}.srw-cost-line:last-child{border-bottom:0}.srw-cost-line label{min-width:0}.srw-cost-line .hidden{display:none}.srw-line-total{display:grid;gap:4px;white-space:nowrap}.srw-line-total small{color:#64748b}.srw-private-totals{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;padding:12px;background:#102a43;color:#fff}.srw-private-totals>div{display:grid;gap:5px;padding:8px;border-left:2px solid #38bdf8}.srw-private-totals span{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:#bae6fd}.srw-private-totals b{font-size:16px}.srw-customer-preview{display:grid;gap:14px;border:2px solid #14b8a6;background:#fff}.srw-customer-preview>header{background:#ecfdf5;border-color:#99f6e4}.srw-preview-scope,.srw-preview-lines,.srw-preview-totals,.srw-customer-preview>p,.srw-customer-preview>label,.srw-customer-preview>small{margin:0 14px}.srw-preview-scope p{white-space:pre-wrap}.srw-preview-lines{display:grid;gap:6px}.srw-preview-lines>div{display:grid;grid-template-columns:1fr auto auto;gap:14px;padding:7px 0;border-bottom:1px solid #e2e8f0}.srw-preview-totals{display:flex;justify-content:flex-end;gap:18px;flex-wrap:wrap;padding:10px;background:#f8fafc}.srw-preview-totals span{display:grid;gap:3px}.srw-customer-preview>small{margin-bottom:14px;color:#0f766e;font-weight:800}@media(max-width:1200px){.srw-cost-line{grid-template-columns:repeat(3,1fr)}.srw-line-description{grid-column:span 2}.srw-private-totals{grid-template-columns:repeat(3,1fr)}}@media(max-width:700px){.srw-commercial-workbench{margin:0 10px 10px}.srw-commercial-workbench form{padding:14px}.srw-cost-line,.srw-private-totals{grid-template-columns:1fr}.srw-line-description{grid-column:1}.srw-preview-lines>div{grid-template-columns:1fr}.srw-preview-totals{justify-content:flex-start}}';
    style.textContent += '.srw-customer-pilot{margin:18px 20px 0;border:2px solid #0ea5e9;background:#f8fbfe}.srw-customer-pilot>header{display:flex;justify-content:space-between;align-items:start;gap:16px;padding:16px 18px;background:#fff;border-bottom:1px solid #d7e5f4}.srw-customer-pilot>header span{color:#0f766e;font-size:10px;font-weight:900;letter-spacing:.16em}.srw-customer-pilot>header p{margin:3px 0 0!important}.srw-pilot-evidence{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:12px 18px;background:#eef7ff;border-bottom:1px solid #d7e5f4}.srw-pilot-evidence>div:first-child{display:grid;gap:3px}.srw-pilot-evidence small{color:#60758c}.srw-pilot-image-actions{display:flex;gap:8px;flex-wrap:wrap}.srw-pilot-image-actions label{position:relative;overflow:hidden;padding:9px 12px;color:#075985;background:#fff;border:1px solid #8fb3c7;font-size:11px;font-weight:900;cursor:pointer}.srw-pilot-image-actions input{position:absolute;inset:0;opacity:0;cursor:pointer}.srw-pilot-images{display:flex;gap:10px;overflow:auto;padding:12px 18px;background:#fff}.srw-pilot-images figure{position:relative;flex:0 0 150px;margin:0;border:1px solid #cbd9e6;background:#f8fafc}.srw-pilot-images img{display:block;width:100%;height:105px;object-fit:cover}.srw-pilot-images figcaption{overflow:hidden;padding:6px 8px;color:#52677e;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.srw-pilot-images figure button{position:absolute;top:5px;right:5px;min-width:27px;padding:4px!important;text-align:center!important;background:#fff!important}.srw-pilot-voice-status{display:flex;align-items:center;gap:10px;padding:10px 18px;background:#f0fdf4;border-bottom:1px solid #bbf7d0}.srw-pilot-voice-status>div{display:grid;gap:2px}.srw-pilot-voice-status small{color:#52677e}.srw-pilot-voice-dot{width:10px;height:10px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 4px rgba(34,197,94,.13)}.srw-pilot-voice-status.is-recording{background:#fef2f2;border-color:#fecaca}.srw-pilot-voice-status.is-recording .srw-pilot-voice-dot{background:#dc2626;box-shadow:0 0 0 5px rgba(220,38,38,.16);animation:srwPilotPulse 1.15s infinite}.srw-pilot-voice-status.is-transcribing{background:#eff6ff;border-color:#bfdbfe}.srw-pilot-voice-status.is-transcribing .srw-pilot-voice-dot{background:#2563eb}.srw-pilot-voice-status.is-error{background:#fff7ed;border-color:#fdba74}.srw-pilot-voice-status.is-error .srw-pilot-voice-dot{background:#ea580c}.srw-shell button[data-srw-pilot-open].is-recording{background:#b91c1c!important;color:#fff!important;border-color:#991b1b!important}.srw-pilot-pending{margin:12px 18px;padding:13px 14px;border-left:4px solid #f59e0b;background:#fffbeb}.srw-pilot-pending p{margin:4px 0 8px!important}.srw-customer-pilot [data-aion-customer-scoped-pilot-runtime]{border-top:1px solid #d7e5f4}.srw-customer-pilot [data-aion-pilot-record-context]{background:#e6f6ff}.srw-customer-pilot [data-aion-shared-pilot-terminal="true"]{border:0!important;margin:0!important}.srw-customer-pilot [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header{padding-top:22px!important}.srw-customer-pilot [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header h2{font-size:27px!important}@keyframes srwPilotPulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(.72);opacity:.58}}@media(max-width:700px){.srw-customer-pilot{margin:10px 10px 0}.srw-customer-pilot>header,.srw-pilot-evidence{align-items:stretch;flex-direction:column}}';
    style.textContent += '.srw-customer-page{padding-bottom:0}.srw-customer-pilot-footer{position:sticky;z-index:11400;bottom:0;display:grid;margin:0;border-top:3px solid #15803d;background:#fff;box-shadow:0 -14px 34px rgba(15,23,42,.16)}.srw-customer-pilot-status{display:flex;align-items:center;gap:10px;min-width:0;padding:8px 18px;background:#f0fdf4;border-bottom:1px solid #bbf7d0}.srw-customer-pilot-status>div{display:grid;min-width:0;gap:1px}.srw-customer-pilot-status small{overflow:hidden;color:#52677e;text-overflow:ellipsis;white-space:nowrap}.srw-customer-pilot-status.is-recording{background:#fef2f2;border-color:#fecaca}.srw-customer-pilot-status.is-recording .srw-pilot-voice-dot{background:#dc2626;box-shadow:0 0 0 5px rgba(220,38,38,.16);animation:srwPilotPulse 1.15s infinite}.srw-customer-pilot-status.is-transcribing{background:#eff6ff;border-color:#bfdbfe}.srw-customer-pilot-status.is-transcribing .srw-pilot-voice-dot{background:#2563eb}.srw-customer-pilot-status.is-error{background:#fff7ed;border-color:#fdba74}.srw-customer-pilot-status.is-error .srw-pilot-voice-dot{background:#ea580c}.srw-customer-pilot-latest{flex:1;min-width:0;overflow:hidden;color:#334155;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.srw-customer-pilot-latest b{color:#075985}.srw-customer-pilot-progress{margin-left:auto;padding:4px 8px;background:#ede9fe;color:#6d28d9;font-size:10px;font-weight:900;white-space:nowrap}.srw-customer-pilot-composer{display:flex;align-items:stretch;gap:8px;padding:10px 18px}.srw-customer-pilot-composer textarea{flex:1;min-width:120px;min-height:42px;max-height:110px;resize:vertical;padding:10px 12px;border:1px solid #94a3b8;background:#fff;color:var(--ink);font:inherit}.srw-customer-pilot-talk{min-width:148px;text-align:center!important}.srw-customer-pilot-tools{display:flex;gap:6px}.srw-customer-pilot-tools label{position:relative;display:grid;place-items:center;overflow:hidden;padding:8px 10px;color:#075985;border:1px solid #8fb3c7;background:#fff;font-size:10px;font-weight:900;cursor:pointer;white-space:nowrap}.srw-customer-pilot-tools input{position:absolute;inset:0;opacity:0;cursor:pointer}.srw-customer-pilot-footer>.srw-pilot-images{max-height:130px;padding:8px 18px;border-bottom:1px solid #d7e5f4}.srw-customer-pilot-footer>.srw-pilot-pending{margin:8px 18px}.srw-shell button[data-srw-pilot-open].is-recording{background:#b91c1c!important;color:#fff!important;border-color:#991b1b!important}@media(max-width:760px){.srw-customer-pilot-composer{flex-wrap:wrap;padding:9px}.srw-customer-pilot-composer textarea{order:-1;flex-basis:100%}.srw-customer-pilot-tools{flex:1}.srw-customer-pilot-talk{min-width:132px}.srw-customer-pilot-status{padding:8px 10px}.srw-customer-pilot-latest{display:none}}';
    style.textContent += '.srw-quote-interview-progress{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:10px 18px;background:#f5f3ff;border-bottom:1px solid #ddd6fe}.srw-quote-interview-progress>div{display:grid;gap:2px}.srw-quote-interview-progress small{color:#5b6474}.srw-quote-interview-progress>span{padding:4px 8px;background:#ede9fe;color:#6d28d9;font-size:10px;font-weight:900;white-space:nowrap}';
    style.textContent += '.srw-pilot-attachments{display:flex;gap:10px;overflow:auto;padding:8px 18px;background:#fff;border-bottom:1px solid #d7e5f4}.srw-pilot-attachments figure{position:relative;display:flex;align-items:center;gap:9px;flex:0 0 210px;min-width:0;margin:0;padding:8px 36px 8px 8px;border:1px solid #cbd9e6;background:#f8fafc}.srw-pilot-attachments figure.is-image{align-items:stretch;padding:0 36px 0 0}.srw-pilot-attachments img{display:block;width:78px;height:58px;object-fit:cover}.srw-pilot-file-badge{display:grid;place-items:center;flex:0 0 52px;height:48px;background:#e0f2fe;color:#075985;font-size:10px;font-weight:900}.srw-pilot-attachments figcaption{display:grid;align-content:center;min-width:0;gap:2px;color:#52677e;font-size:9px}.srw-pilot-attachments figcaption b{overflow:hidden;color:#102a43;text-overflow:ellipsis;white-space:nowrap}.srw-pilot-attachments figcaption small{color:#64748b}.srw-pilot-attachments figure>button{position:absolute;top:5px;right:5px;min-width:27px;padding:4px!important;text-align:center!important;background:#fff!important}.srw-feed-attachments{display:flex;gap:8px;overflow:auto;margin:8px 0}.srw-feed-image,.srw-feed-file{display:grid;flex:0 0 170px;min-width:0;text-decoration:none}.srw-feed-image{gap:4px}.srw-feed-image img{display:block;width:112px;height:78px;object-fit:cover;border:1px solid #cbd9e6;background:#f8fafc}.srw-feed-image span{overflow:hidden;color:#52677e;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.srw-feed-file{grid-template-columns:42px 1fr;grid-template-rows:auto auto;align-items:center;gap:2px 8px;padding:8px;border:1px solid #cbd9e6;background:#f8fafc}.srw-feed-file>span{grid-row:1/3;display:grid;place-items:center;height:40px;background:#e0f2fe;color:#075985;font-size:9px;font-weight:900}.srw-feed-file b{overflow:hidden;color:#102a43;font-size:10px;text-overflow:ellipsis;white-space:nowrap}.srw-feed-file small{color:#075985;font-size:9px}@media(max-width:760px){.srw-customer-pilot-tools label{padding:8px}.srw-customer-pilot-tools label:first-child{flex:1}}';
    style.textContent += '.srw-customer-record-tabs{display:flex;gap:0;padding:0 20px;border-bottom:1px solid #cbd9e6;background:#fff}.srw-customer-record-tabs button{display:flex;align-items:center;gap:7px;padding:12px 16px!important;border:0!important;border-bottom:3px solid transparent!important}.srw-customer-record-tabs button.active{color:#0f766e!important;border-bottom-color:#0f766e!important}.srw-customer-record-tabs button span{display:grid;place-items:center;min-width:19px;height:19px;padding:0 5px;border-radius:12px;background:#e2e8f0;color:#334155;font-size:9px}.srw-customer-finance-view{margin:20px;border:1px solid #cbd9e6;background:#fff}.srw-customer-finance-view>header{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;padding:17px;border-bottom:1px solid #cbd9e6}.srw-customer-finance-view>header>div:first-child>span{color:#0f766e;font-size:9px;font-weight:900;letter-spacing:.15em}.srw-customer-finance-view>header h3{margin:4px 0!important}.srw-customer-finance-view>header p{margin:0!important}.srw-customer-finance-view>footer{padding:12px 17px;border-top:1px solid #cbd9e6;background:#f8fafc;color:#52677e}.srw-acceptance-state{padding:6px 9px;background:#fef3c7;color:#92400e;font-size:10px;font-weight:900;white-space:nowrap}.srw-acceptance-state.accepted{background:#dcfce7;color:#166534}.srw-finance-list{display:grid;gap:10px;padding:15px}.srw-finance-record{border:1px solid #cbd9e6}.srw-finance-record summary{display:flex;justify-content:space-between;align-items:center;gap:18px;padding:13px;cursor:pointer;list-style:none}.srw-finance-record summary::-webkit-details-marker{display:none}.srw-finance-record summary>div{display:grid;gap:3px}.srw-finance-record summary>div:last-child{text-align:right}.srw-finance-record summary span,.srw-finance-record summary small{color:#64748b;font-size:9px}.srw-finance-record summary strong{font-size:16px}.srw-finance-status{justify-self:end;padding:4px 7px;font-weight:900;text-transform:uppercase}.srw-finance-status.paid{background:#dcfce7;color:#166534}.srw-finance-status.outstanding{background:#dbeafe;color:#1d4ed8}.srw-finance-status.overdue{background:#fee2e2;color:#b91c1c}.srw-finance-status.draft{background:#fef3c7;color:#92400e}.srw-invoice-detail{display:grid;gap:6px;padding:13px;border-top:1px solid #cbd9e6;background:#f8fafc}.srw-invoice-detail>div,.srw-invoice-detail>footer{display:flex;justify-content:space-between;gap:14px;padding:6px 0;border-bottom:1px solid #e2e8f0}.srw-invoice-detail>footer{justify-content:flex-end;gap:18px;border:0}.srw-reconciliation-state{padding:8px;border-left:3px solid #0ea5e9;background:#eff6ff;color:#334155}.srw-finance-empty{display:grid;justify-items:start;gap:7px;padding:28px}.srw-finance-empty p{margin:0!important}.srw-expense-upload{display:flex;justify-content:flex-end;gap:7px;flex-wrap:wrap}.srw-expense-upload select{padding:8px}.srw-expense-upload label{position:relative;display:grid;place-items:center;overflow:hidden;padding:8px 10px;border:1px solid #8fb3c7;color:#075985;font-size:10px;font-weight:900;cursor:pointer}.srw-expense-upload input{position:absolute;inset:0;opacity:0;cursor:pointer}.srw-expense-record{display:grid;grid-template-columns:54px 1fr auto;align-items:center;gap:12px;padding:12px;border:1px solid #cbd9e6}.srw-expense-icon{display:grid;place-items:center;height:48px;background:#e0f2fe;color:#075985;font-size:9px;font-weight:900}.srw-expense-record>div:nth-child(2){display:grid;gap:3px}.srw-expense-record span,.srw-expense-record small{color:#64748b;font-size:9px}.srw-expense-record>a{padding:8px 10px;border:1px solid #8fb3c7;color:#075985;font-size:10px;font-weight:900;text-decoration:none}@media(max-width:760px){.srw-customer-record-tabs{padding:0}.srw-customer-record-tabs button{flex:1;justify-content:center;padding:10px 6px!important}.srw-customer-finance-view{margin:10px}.srw-customer-finance-view>header{flex-direction:column}.srw-expense-upload{justify-content:flex-start}.srw-expense-record{grid-template-columns:46px 1fr}.srw-expense-record>a{grid-column:1/-1;text-align:center}.srw-finance-record summary{align-items:flex-start}.srw-invoice-detail>div,.srw-invoice-detail>footer{flex-direction:column}}';
    style.textContent += '.srw-commercial-workbench>header{display:flex;justify-content:space-between;align-items:flex-start;gap:14px}.srw-commercial-workbench.is-collapsed{margin-bottom:14px}.srw-commercial-workbench.is-collapsed>header{padding-bottom:12px}.srw-commercial-workbench.is-collapsed .srw-commercial-modes{border-bottom:0}.srw-customer-pilot-action{min-width:138px;padding:8px 10px!important;border:1px solid #15803d!important;background:#f0fdf4!important;color:#166534!important;font-weight:900}@media(max-width:760px){.srw-customer-pilot-action{flex:1;min-width:128px}.srw-commercial-workbench>header{align-items:stretch;flex-direction:column}}';
    style.textContent += '.srw-relationship{margin:12px 20px 0;border:1px solid #cbd9e6;background:#fff}.srw-relationship>summary{display:grid;grid-template-columns:.75fr .75fr 1fr minmax(220px,2fr) auto;align-items:center;gap:16px;padding:11px 14px;cursor:pointer;list-style:none}.srw-relationship>summary::-webkit-details-marker{display:none}.srw-relationship>summary>div{display:grid;min-width:0;gap:2px}.srw-relationship>summary span,.srw-relationship>summary small{color:#64748b;font-size:9px}.srw-relationship>summary>div:first-child span{color:#0f766e;font-weight:900;letter-spacing:.14em}.srw-relationship>summary b{overflow:hidden;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.srw-relationship[open]>summary{border-bottom:1px solid #cbd9e6;background:#f8fafc}.srw-relationship>form{display:grid;gap:13px;padding:15px}.srw-relationship-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.srw-relationship label{display:grid;gap:4px;font-size:9px;font-weight:900}.srw-relationship label.wide{grid-column:span 2}.srw-relationship input,.srw-relationship select{width:100%;padding:9px;border:1px solid #94a3b8;background:#fff;color:var(--ink)}.srw-relationship>form>footer{display:flex;align-items:center;justify-content:flex-end;gap:12px;border-top:1px solid #e2e8f0;padding-top:12px}.srw-relationship>form>footer small{margin-right:auto;color:#64748b}.srw-relationship .srw-recorded-by{padding:10px}@media(max-width:850px){.srw-relationship>summary{grid-template-columns:1fr 1fr}.srw-relationship-next{grid-column:1/-1}.srw-relationship>summary>span:last-child{display:none}.srw-relationship-grid{grid-template-columns:1fr 1fr}}@media(max-width:560px){.srw-relationship{margin:10px}.srw-relationship-grid{grid-template-columns:1fr}.srw-relationship label.wide{grid-column:1}.srw-relationship>form>footer{align-items:stretch;flex-direction:column}.srw-relationship>form>footer small{margin:0}}';
    style.textContent += '.srw-customer-type{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin:0;padding:0;border:0}.srw-customer-type legend{grid-column:1/-1;margin-bottom:3px;color:#475569;font-size:10px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}.srw-customer-type>label{position:relative;display:grid!important;grid-template-columns:auto 1fr;align-items:center;gap:2px 8px;padding:12px!important;border:1px solid #94a3b8;background:#fff;cursor:pointer}.srw-customer-type>label.active{border:2px solid #0f766e;background:#f0fdfa}.srw-customer-type input{grid-row:1/3;width:auto!important;margin:0}.srw-customer-type b{font-size:13px}.srw-customer-type small{color:#64748b;font-size:9px}.srw-enquiry-path{display:grid;gap:12px;padding:13px;border-left:4px solid #0ea5e9;background:#f8fafc}.srw-enquiry-path>span{color:#0f766e;font-size:9px;font-weight:900;letter-spacing:.14em}.srw-enquiry-path-prompt{padding:20px;border:1px dashed #7dd3fc;background:#f0f9ff;color:#52677e;text-align:center}.srw-form-hint{margin-top:-8px;color:#64748b}@media(max-width:560px){.srw-customer-type{grid-template-columns:1fr}}';
    style.textContent += '.srw-lead-flow,.srw-deal-flow{margin:18px;border:1px solid var(--line);padding:14px;min-width:0}.srw-source-lanes{display:grid;gap:7px}.srw-source-lane{display:grid;grid-template-columns:190px minmax(0,1fr);align-items:stretch;border:1px solid #d8e4ec;background:#f8fafc}.srw-source-lane>header{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 11px;border-right:1px solid #d8e4ec;background:#fff}.srw-source-lane>header>div{display:grid;gap:2px}.srw-source-lane>header small{color:#64748b;font-size:8px}.srw-source-lane>header>span{display:grid;place-items:center;min-width:24px;height:24px;background:#e0f2fe;color:#075985;font-size:10px;font-weight:900}.srw-source-strip,.srw-deal-strip{display:flex;gap:7px;overflow-x:auto;overscroll-behavior-inline:contain;scroll-snap-type:x proximity;scrollbar-width:thin}.srw-source-strip{padding:7px}.srw-source-strip>p{margin:auto 8px!important;font-size:10px}.srw-source-card{display:grid!important;grid-template-columns:auto minmax(90px,.7fr) minmax(160px,1.5fr) auto;align-items:center;gap:8px;flex:0 0 min(520px,82vw);scroll-snap-align:start;padding:7px 9px!important;background:#fff!important}.srw-source-card>b,.srw-source-card>small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.srw-source-card>small{color:#52677e}.srw-source-card>em{color:#64748b;font-size:8px;font-style:normal;text-transform:uppercase}.srw-commercial-flow>nav{display:flex;gap:6px;overflow-x:auto;padding-bottom:10px}.srw-commercial-flow>nav button{display:flex;align-items:center;gap:6px;white-space:nowrap}.srw-commercial-flow>nav button.active{background:#075985!important;color:#fff!important;border-color:#075985!important}.srw-commercial-flow>nav button span{display:grid;place-items:center;min-width:19px;height:19px;border-radius:10px;background:#e2e8f0;color:#334155;font-size:9px}.srw-deal-strip{gap:10px;padding:2px 0 8px}.srw-deal-card{display:grid!important;gap:7px;flex:0 0 min(380px,86vw);min-height:128px;scroll-snap-align:start;padding:13px!important;background:#fff!important}.srw-deal-card>header,.srw-deal-card>footer{display:flex;align-items:center;justify-content:space-between;gap:10px}.srw-deal-card>header span:last-child,.srw-deal-card>footer small,.srw-deal-card>footer em{color:#64748b;font-size:9px}.srw-deal-card>p{display:-webkit-box;overflow:hidden;margin:0!important;font-size:11px;-webkit-box-orient:vertical;-webkit-line-clamp:2}.srw-deal-card>footer{margin-top:auto;border-top:1px solid #e2e8f0;padding-top:7px}.srw-deal-card>footer em{font-style:normal}.srw-swipe-hint{display:block;color:#64748b;text-align:right}.srw-deal-entry{border-left-color:#8b5cf6;background:#f5f3ff}@media(max-width:760px){.srw-lead-flow,.srw-deal-flow{margin:10px;padding:10px}.srw-source-lane{grid-template-columns:1fr}.srw-source-lane>header{border-right:0;border-bottom:1px solid #d8e4ec}.srw-source-card{grid-template-columns:auto minmax(90px,.8fr) minmax(140px,1.3fr)}.srw-source-card>em{display:none}}';
    style.textContent += '[data-aion-sales-live-agents-workspace-o14d="true"],[data-aion-sales-revenue-mount="true"],.srw-shell{width:100%;max-width:100%;min-width:0}.srw-shell{overflow-x:clip}.srw-shell>*,.srw-lead-flow,.srw-deal-flow,.srw-source-lanes,.srw-source-lane,.srw-source-strip,.srw-commercial-flow,.srw-commercial-flow>nav,.srw-deal-strip{max-width:100%;min-width:0}.srw-metrics>article,.srw-capabilities>article{min-width:0}.srw-source-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(310px,100%),1fr));overflow:visible;scroll-snap-type:none}.srw-source-card{width:100%;max-width:100%;min-width:0;grid-template-columns:auto minmax(0,.7fr) minmax(0,1.5fr) auto;overflow:hidden;flex:none;scroll-snap-align:none}.srw-source-card>*{min-width:0}.srw-commercial-flow>nav{flex-wrap:wrap;overflow:visible}.srw-deal-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));overflow:visible;scroll-snap-type:none}.srw-deal-card{width:100%;max-width:100%;min-width:0;overflow:hidden;flex:none;scroll-snap-align:none}.srw-deal-card>*{min-width:0}@media(max-width:760px){.srw-shell>header,.srw-shell>nav,.srw-title{flex-wrap:wrap}.srw-source-card{grid-template-columns:auto minmax(0,.8fr) minmax(0,1.3fr)}}';
    style.textContent += '.srw-deal-flow{container-type:inline-size}.srw-deal-controls{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:10px;padding:10px;background:#f8fafc;border:1px solid var(--line)}.srw-deal-controls label{display:grid;min-width:min(380px,100%);gap:4px}.srw-deal-controls label span{color:#475569;font-size:9px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}.srw-deal-controls input{width:100%;min-width:0;padding:10px 12px;border:1px solid #8fb3c7;background:#fff;color:var(--ink);font:inherit}.srw-deal-controls>div{display:flex;align-items:center;gap:7px}.srw-deal-controls small{margin-right:4px;color:#64748b;white-space:nowrap}.srw-deal-controls button{display:grid!important;place-items:center;width:40px;height:40px;padding:0!important;font-size:24px!important;text-align:center!important}.srw-deal-strip{display:flex;gap:10px;overflow-x:hidden;scroll-snap-type:x mandatory;scroll-behavior:smooth}.srw-deal-card{flex:0 0 calc((100% - 30px)/4);scroll-snap-align:start}.srw-deal-strip>.srw-empty{flex:1}@container(max-width:1100px){.srw-deal-card{flex-basis:calc((100% - 20px)/3)}}@container(max-width:780px){.srw-deal-card{flex-basis:calc((100% - 10px)/2)}.srw-deal-controls{align-items:stretch;flex-direction:column}.srw-deal-controls label{min-width:0;width:100%}.srw-deal-controls>div{justify-content:flex-end}}@container(max-width:520px){.srw-deal-card{flex-basis:100%}}';
    style.textContent += '.srw-source-lane>header{min-width:0}.srw-source-controls{display:flex!important;align-items:center;justify-content:flex-end;gap:5px}.srw-source-controls>span{display:grid;place-items:center;min-width:24px;height:32px;padding:0 6px;background:#e0f2fe;color:#075985;font-size:10px;font-weight:900}.srw-source-controls>button{display:grid!important;place-items:center;width:32px;height:32px;padding:0!important;font-size:20px!important;text-align:center!important}.srw-source-strip{display:flex;gap:0;overflow-x:hidden;scroll-snap-type:x mandatory;scroll-behavior:smooth;padding:7px}.srw-source-card{grid-template-columns:auto minmax(160px,.55fr) minmax(0,1.45fr) auto;flex:0 0 100%;width:100%;min-height:74px;scroll-snap-align:start;padding:11px 13px!important}.srw-source-card>div{display:grid;min-width:0;gap:3px;text-align:left}.srw-source-card>div>b,.srw-source-card>div>small,.srw-source-card>p{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.srw-source-card>div>small{color:#64748b;font-size:9px}.srw-source-card>p{margin:0!important;text-align:left}.srw-source-strip>p{margin:auto 8px!important}@media(max-width:760px){.srw-source-lane>header{align-items:center;flex-direction:row}.srw-source-card{grid-template-columns:auto minmax(0,.7fr) minmax(0,1.3fr)}.srw-source-card>em{display:none}}';
    style.textContent += '.srw-source-lanes{gap:10px}.srw-source-lane{display:grid;grid-template-columns:minmax(0,1fr);overflow:hidden;border-color:#c9d9e5;background:#fff}.srw-source-lane>header{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:9px 12px;border-right:0;border-bottom:1px solid #d8e4ec;background:#f6f9fc}.srw-source-lane>header>div:first-child{display:flex;align-items:baseline;min-width:0;gap:10px}.srw-source-lane>header>div:first-child>b{font-size:13px}.srw-source-lane>header>div:first-child>small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.srw-source-controls{flex:0 0 auto}.srw-source-controls>span{height:30px;min-width:auto;padding:0 9px;background:#e0f2fe;white-space:nowrap}.srw-source-controls>button{width:30px;height:30px;border-color:#a9c5d7!important;background:#fff!important}.srw-source-strip{min-height:84px;padding:0;background:#fff}.srw-source-card{min-height:84px;padding:14px 16px!important;border:0!important;border-left:4px solid #0ea5e9!important;background:#fff!important}.srw-source-card>div>b{font-size:14px}.srw-source-card>p{display:-webkit-box;overflow:hidden;white-space:normal;text-overflow:clip;line-height:1.4;-webkit-box-orient:vertical;-webkit-line-clamp:2}.srw-source-card>em{align-self:start;margin-top:4px;padding:4px 7px;background:#f1f5f9}.srw-source-strip>p{align-self:center;padding:0 16px;color:#64748b}@media(max-width:760px){.srw-source-lane>header{align-items:flex-start}.srw-source-lane>header>div:first-child{display:grid;gap:2px}.srw-source-controls>span{display:none}.srw-source-card{grid-template-columns:auto minmax(0,.8fr) minmax(0,1.2fr)}}';
    style.textContent += '.srw-source-browser{display:grid;min-width:0;gap:9px}.srw-source-tabs{display:flex;min-width:0;gap:6px;overflow-x:auto;padding:0 0 3px}.srw-source-tabs button{display:flex!important;align-items:center;gap:7px;flex:0 0 auto;white-space:nowrap}.srw-source-tabs button.active{border-color:#075985!important;background:#075985!important;color:#fff!important}.srw-source-tabs button span{display:grid;place-items:center;min-width:20px;height:20px;padding:0 5px;border-radius:10px;background:#e2e8f0;color:#334155;font-size:9px}.srw-source-lane{border:1px solid #c9d9e5}.srw-source-card{min-height:104px}.srw-source-card>p{font-size:12px!important}@media(max-width:760px){.srw-source-tabs{padding-bottom:6px}.srw-source-card{min-height:96px}}';
    style.textContent += '.srw-source-card{display:grid!important;grid-template-columns:minmax(0,1fr);grid-template-rows:auto 1fr;align-items:stretch;gap:10px}.srw-source-card-header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;min-width:0;padding:0 0 10px;border-bottom:1px solid #e2e8f0}.srw-source-card-header>div{display:flex;align-items:flex-start;min-width:0;gap:10px}.srw-source-card-header>div>div{display:grid;min-width:0;gap:2px;text-align:left}.srw-source-card-header b{overflow:hidden;color:#075985;font-size:15px;text-overflow:ellipsis;white-space:nowrap}.srw-source-card-header small{overflow:hidden;color:#64748b;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.srw-source-card-header em{flex:0 0 auto;padding:4px 7px;background:#f1f5f9;color:#64748b;font-size:8px;font-style:normal;text-transform:uppercase}.srw-source-card>p{display:-webkit-box;overflow:hidden;margin:0!important;max-width:100%;color:#40566e!important;font-size:12px!important;font-weight:700;line-height:1.45;text-align:left;white-space:normal;-webkit-box-orient:vertical;-webkit-line-clamp:2}.srw-source-card>span,.srw-source-card>div,.srw-source-card>em{display:none}@media(max-width:600px){.srw-source-card-header{gap:8px}.srw-source-card-header em{display:none}.srw-source-card-header>div{gap:7px}}';
    style.textContent += '.srw-capabilities{grid-template-columns:minmax(0,1fr)}';
    style.textContent += '.srw-unified-revenue-flow{margin-top:14px}.srw-unified-filter{display:grid;gap:5px;margin-bottom:9px}.srw-unified-filter>small{color:#475569;font-size:9px;font-weight:900;letter-spacing:.1em;text-transform:uppercase}.srw-unified-filter>nav{display:flex;gap:6px;max-width:100%;overflow-x:auto;padding:0 0 2px}.srw-unified-filter>nav button{display:flex!important;align-items:center;gap:6px;flex:0 0 auto;white-space:nowrap}.srw-unified-filter>nav button.active{border-color:#075985!important;background:#075985!important;color:#fff!important}.srw-unified-filter>nav button span{display:grid;place-items:center;min-width:19px;height:19px;padding:0 5px;border-radius:10px;background:#e2e8f0;color:#334155;font-size:9px}.srw-unified-revenue-flow .srw-title{margin-bottom:12px}';
    style.textContent += '.srw-deal-controls .srw-deal-search{flex:1;min-width:220px}.srw-deal-controls .srw-stage-select{flex:0 0 240px;min-width:180px}.srw-deal-controls .srw-deal-search input,.srw-deal-controls .srw-stage-select select{box-sizing:border-box;width:100%;height:42px;min-height:42px}.srw-deal-controls .srw-stage-select select{padding:9px 34px 9px 11px;border:1px solid #8fb3c7;background:#fff;color:var(--ink);font:inherit;font-weight:800}@media(max-width:760px){.srw-deal-controls .srw-stage-select{flex:1;width:100%}}';
    style.textContent += '.srw-header-actor{display:grid;align-self:center;flex:0 0 160px;gap:2px;margin-left:6px;text-align:left}.srw-header-actor>span{color:#475569;font-size:7px;font-weight:900;letter-spacing:.1em;text-transform:uppercase}.srw-header-actor>select{box-sizing:border-box;width:100%;height:36px;padding:6px 26px 6px 9px;border:1px solid #cbd5df;background:#fff;color:#102a43;font:600 10px Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}@media(max-width:1180px){.srw-header-actor{flex-basis:132px}.srw-header-actor>span{display:none}}';
    style.textContent += '.srw-vault-intake{display:grid;gap:14px}.srw-vault-intake-summary{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px;border:1px solid #cbd9e6;background:#f8fafc}.srw-vault-intake-summary>div{display:grid;gap:2px}.srw-vault-intake-summary strong{font-size:22px}.srw-vault-intake-summary span{font-weight:900}.srw-vault-intake-summary small,.srw-vault-endpoint small,.srw-vault-token small{color:#64748b}.srw-vault-endpoints{display:grid;gap:8px}.srw-vault-endpoint{display:grid;grid-template-columns:minmax(180px,.7fr) minmax(260px,1.3fr) auto;align-items:center;gap:12px;padding:11px;border:1px solid #cbd9e6}.srw-vault-endpoint>div{display:grid;gap:2px}.srw-vault-endpoint code{overflow-wrap:anywhere}.srw-vault-intake-empty{padding:20px;border:1px dashed #94a3b8}.srw-vault-token{grid-template-columns:minmax(0,1fr) auto}.srw-vault-token>b,.srw-vault-token>small{grid-column:1/-1}.srw-vault-token button,.srw-vault-endpoint button{white-space:nowrap}.srw-vault-intake .aion-vault-advanced-details{margin-top:0}@media(max-width:760px){.srw-vault-intake-summary{align-items:stretch;flex-direction:column}.srw-vault-endpoint{grid-template-columns:1fr}.srw-vault-token{grid-template-columns:1fr}}';
    style.textContent += '.srw-caller-setup{display:grid;grid-template-columns:minmax(0,1fr);gap:14px;padding:16px 18px;background:#f8fafc;border:1px solid #cbd9e6;border-left:4px solid #8b5cf6}.srw-caller-setup>header{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.srw-caller-setup>header>div:first-child{min-width:0}.srw-caller-setup>header span{color:#0f766e;font-size:10px;font-weight:900;letter-spacing:.2em}.srw-caller-setup>header p{max-width:820px;margin:7px 0 0!important}.srw-caller-status{display:grid;flex:0 0 min(360px,35%);gap:3px;padding:10px 12px;border-left:4px solid #f59e0b;background:#fffbeb}.srw-caller-status.ready{border-color:#16a34a;background:#f0fdf4}.srw-caller-status.review{border-color:#0ea5e9;background:#f0f9ff}.srw-caller-status small{color:#52677e}.srw-caller-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.srw-caller-steps article{display:flex;align-items:flex-start;gap:9px;padding:11px;border:1px solid #cbd9e6;background:#fff}.srw-caller-steps article>span{display:grid;place-items:center;flex:0 0 26px;width:26px;height:26px;border-radius:50%;background:#e2e8f0;color:#475569;font-size:11px;letter-spacing:0}.srw-caller-steps article.done>span{background:#dcfce7;color:#166534}.srw-caller-steps article.current{border-color:#0ea5e9;background:#f0f9ff}.srw-caller-steps article.current>span{background:#0ea5e9;color:#fff}.srw-caller-steps article>div{display:grid;gap:3px}.srw-caller-steps small{color:#64748b}.srw-caller-actions{margin-top:0}.srw-caller-plan{border-top:1px solid #cbd9e6;padding-top:10px}.srw-caller-plan>summary,.srw-caller-plan>details>summary{cursor:pointer;font-weight:900}.srw-caller-plan-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0}.srw-caller-plan-grid article{display:grid;gap:4px;padding:11px;border:1px solid #cbd9e6;background:#fff}.srw-caller-plan-grid span,.srw-caller-plan-grid small{color:#64748b;font-size:9px}.srw-caller-plan>details{padding:10px;border:1px solid #cbd9e6;background:#fff}.srw-caller-console{background:#fff}.srw-call-readiness{display:grid;flex:0 0 min(430px,42%);gap:4px;padding:10px 12px;border-left:4px solid #f59e0b;background:#fffbeb;text-align:left!important}.srw-call-readiness.ready{border-color:#16a34a;background:#f0fdf4}.srw-call-readiness small{color:#52677e}.srw-call-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:12px 14px;border-bottom:1px solid #cbd9e6;background:#f8fafc}.srw-call-metrics article{display:grid;gap:2px;padding:11px;border:1px solid #cbd9e6;background:#fff}.srw-call-metrics strong{font-size:20px}.srw-call-metrics span{font-size:10px;font-weight:900}.srw-call-metrics small{color:#64748b;font-size:9px}.srw-console-column-title{display:flex;align-items:center;justify-content:space-between;gap:10px}.srw-console-column-title>div{display:grid;gap:2px}.srw-console-column-title small{color:#64748b}.srw-console-empty{margin-top:8px;padding:18px;border:1px dashed #94a3b8;background:#fff}.srw-console-empty p{margin-bottom:0!important}.srw-call-technical{border-top:1px solid #cbd9e6;padding:10px 14px}.srw-call-technical>summary{cursor:pointer;font-weight:900}.srw-call-technical>div{display:grid;grid-template-columns:auto 1fr;gap:7px 14px;margin-top:10px}.srw-call-technical span{color:#64748b}.srw-caller-settings form{gap:16px}.srw-caller-form-notice{padding:12px;border-left:4px solid #0ea5e9;background:#f0f9ff}.srw-caller-form-notice p{margin:4px 0 0!important}.srw-caller-form-section{display:grid;gap:12px;padding:14px;border:1px solid #cbd9e6;background:#f8fafc}.srw-caller-form-heading{display:flex;align-items:flex-start;gap:10px}.srw-caller-form-heading>span{display:grid;place-items:center;flex:0 0 28px;width:28px;height:28px;border-radius:50%;background:#075985;color:#fff!important;font-size:11px!important;letter-spacing:0!important}.srw-caller-form-heading>div{display:grid;gap:3px}.srw-caller-form-heading small{color:#64748b}.srw-caller-check-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.srw-caller-check-grid>label{display:flex!important;align-items:flex-start;gap:8px;padding:9px;border:1px solid #d8e4ec;background:#fff;font-size:10px!important}.srw-caller-check-grid input{flex:0 0 auto;width:auto!important;margin:1px 0 0}.srw-caller-boundary{display:grid;gap:4px;padding:10px;border-left:4px solid #f59e0b;background:#fffbeb}.srw-caller-boundary span{color:#52677e;font-size:10px}.srw-caller-form-advanced{display:grid;gap:12px;padding:14px;border:1px solid #cbd9e6}.srw-caller-form-advanced>summary{cursor:pointer;font-weight:900}.srw-caller-form-advanced[open]>summary{margin-bottom:12px}.srw-caller-form-advanced>label,.srw-caller-form-advanced>.srw-two{margin-top:10px}.srw-caller-settings footer>small{margin-right:auto;color:#64748b;max-width:280px}@media(max-width:900px){.srw-caller-setup>header,.srw-caller-console>header{flex-direction:column}.srw-caller-status,.srw-call-readiness{flex-basis:auto;width:100%}.srw-caller-plan-grid,.srw-call-metrics{grid-template-columns:1fr 1fr}}@media(max-width:600px){.srw-caller-steps,.srw-caller-plan-grid,.srw-caller-check-grid,.srw-call-metrics{grid-template-columns:1fr}.srw-caller-settings .srw-two{grid-template-columns:1fr}.srw-call-technical>div{grid-template-columns:1fr}.srw-caller-settings footer{align-items:stretch;flex-direction:column}.srw-caller-settings footer>small{max-width:none;margin:0}}';
    style.textContent += '.srw-call-centre{display:grid;gap:14px;margin:0 18px 18px;padding:18px;border:1px solid #b7c9d8;border-top:5px solid #8b5cf6;background:#f8fafc}.srw-call-centre>header{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.srw-call-centre>header>div{min-width:0}.srw-call-centre>header span{color:#0f766e;font-size:10px;font-weight:900;letter-spacing:.2em}.srw-call-centre>header p{max-width:880px;margin:5px 0 0!important}.srw-call-centre-guide{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.srw-call-centre-guide article{display:grid;grid-template-columns:auto 1fr;gap:2px 9px;padding:11px;border:1px solid #d8e4ec;background:#fff}.srw-call-centre-guide article>span{display:grid;grid-row:1/3;place-items:center;width:27px;height:27px;border-radius:50%;background:#075985;color:#fff;font-size:10px;font-weight:900}.srw-call-centre-guide article>b{font-size:11px}.srw-call-centre-guide article>small{color:#64748b;font-size:9px}.srw-call-centre-summary{display:flex;gap:18px;padding:9px 12px;border:1px solid #d8e4ec;background:#eef6fb;color:#52677e}.srw-call-centre-summary b{color:#102a43}.srw-call-agent-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(330px,100%),1fr));gap:10px}.srw-call-agent-card{display:grid;gap:11px;padding:14px;border:1px solid #b7c9d8;border-left:4px solid #f59e0b;background:#fff}.srw-call-agent-card.active{border-left-color:#16a34a}.srw-call-agent-card>header{display:flex;justify-content:space-between;gap:12px}.srw-call-agent-card>header>div{display:grid;gap:3px}.srw-call-agent-card>header span{color:#0f766e;font-size:9px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}.srw-call-agent-card>header h4{margin:0;font-size:16px}.srw-call-agent-card>header>b{align-self:start;padding:4px 7px;background:#f1f5f9;color:#475569;font-size:9px;text-transform:uppercase}.srw-call-agent-card.active>header>b{background:#dcfce7;color:#166534}.srw-call-agent-facts{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.srw-call-agent-facts>span{display:grid;gap:3px;min-width:0;padding:8px;background:#f8fafc;color:#64748b;font-size:8px;text-transform:uppercase}.srw-call-agent-facts b{overflow:hidden;color:#102a43;font-size:10px;text-overflow:ellipsis;white-space:nowrap;text-transform:none}.srw-call-agent-card>p{margin:0!important;font-size:10px}.srw-call-agent-card>footer{display:flex;gap:7px;flex-wrap:wrap;padding-top:10px;border-top:1px solid #e2e8f0}.srw-call-centre-empty{display:grid;justify-items:start;gap:7px;padding:22px;border:1px dashed #94a3b8;background:#fff}.srw-call-centre-empty p{margin:0!important}.srw-call-centre-boundary{padding-top:2px}.srw-call-centre-boundary>summary{cursor:pointer;font-weight:900}.srw-call-centre-boundary>div{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}.srw-call-centre-boundary p{margin:0!important;padding:10px;background:#fff;border:1px solid #d8e4ec}.srw-call-agent-builder{width:min(760px,98vw)}.srw-agent-direction{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0;padding:0;border:0}.srw-agent-direction legend{margin-bottom:6px;font-size:10px;font-weight:900}.srw-agent-direction label{display:grid!important;grid-template-columns:auto 1fr;gap:3px 8px;padding:11px;border:1px solid #cbd9e6;background:#fff;cursor:pointer}.srw-agent-direction input{grid-row:1/3;width:auto!important}.srw-agent-direction small{color:#64748b}@media(max-width:900px){.srw-call-centre-guide{grid-template-columns:1fr 1fr}.srw-call-centre-boundary>div{grid-template-columns:1fr}.srw-call-centre>header{flex-direction:column}}@media(max-width:600px){.srw-call-centre{margin:0 10px 10px;padding:12px}.srw-call-centre-guide,.srw-agent-direction,.srw-call-agent-facts{grid-template-columns:1fr}.srw-call-centre-summary{flex-wrap:wrap}}';
    style.textContent += '.srw-call-centre-head-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap}.srw-phone-provider-route{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:11px 13px;border-left:4px solid #0ea5e9;background:#eef8fd}.srw-phone-provider-route>div{display:grid;gap:2px}.srw-phone-provider-route span{color:#52677e;font-size:10px}.srw-phone-provider-route button,.srw-call-centre-head-actions button{white-space:nowrap}@media(max-width:900px){.srw-call-centre-head-actions{justify-content:flex-start}.srw-phone-provider-route{align-items:stretch;flex-direction:column}}';
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
  global.AionSalesRevenue = {
    state, load, render, renderVaultWebsiteIntake: renderVaultWebsiteIntakePanel, loadVaultWebsiteIntake,
    getActiveActor() { return actorById(state.actorId) || syncSignedInActor(); },
    recordQuoteEmailOutcome,
    handlePilotInstruction(rawText, context = {}) {
      if (context.opportunity_id && context.opportunity_id !== state.selectedId) return { handled: false };
      return handleCustomerPilotInstruction(rawText);
    },
  };
})(window);
