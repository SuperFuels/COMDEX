(function installAionSupportWorkspace(global) {
  'use strict';
  const API = 'http://127.0.0.1:8080';
  const state = { workspaceId: '', data: null, voice: null, actorId: '', selectedId: '', panel: '', busy: false, loading: false, loadedAt: 0, error: '', message: '' };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[ch]));
  const label = (value) => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
  const businessId = () => global.AionBusinessContainerClient?.resolveBusinessId?.()
    || global.__aionCanonicalBusinessId
    || '';
  const mount = () => document.querySelector('[data-aion-support-case-mount="true"], [data-aion-support-live-agents-workspace-o14d="true"]');
  const actors = () => state.data?.actors || [];
  const actorOptions = (selected = '') => actors().map((row) => `<option value="${esc(row.person_id)}" ${row.person_id === selected ? 'selected' : ''}>${esc(row.name)}${row.position_title ? ` · ${esc(row.position_title)}` : ''}</option>`).join('');
  const selected = () => (state.data?.cases || []).find((row) => row.case_id === state.selectedId);
  const selectedResponses = () => (state.data?.responses || []).filter((row) => row.case_id === state.selectedId);
  const values = (form) => Object.fromEntries(new FormData(form).entries());

  async function request(path, options = {}) {
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    if (options.body) headers['Content-Type'] = 'application/json';
    const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(`${API}${path}`, { ...options, headers, signal: controller.signal });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(String(body.detail || `Request failed ${response.status}`).replaceAll('_', ' '));
      return body;
    } finally { clearTimeout(timeout); }
  }

  function metrics() {
    const s = state.data?.summary || {};
    return `<div class="scw-metrics">${[['open','Open cases'],['urgent','Urgent'],['awaiting_human','Human review'],['overdue','Overdue'],['resolved','Resolved']].map(([key,text]) => `<article><strong>${Number(s[key] || 0)}</strong><span>${text}</span></article>`).join('')}</div>`;
  }

  function caseQueue() {
    const rows = state.data?.cases || [];
    if (!rows.length) return '<div class="scw-empty"><b>No support cases yet</b><p>Email, website, telephone and manual support contacts will enter one governed case ledger.</p></div>';
    return `<div class="scw-list">${rows.map((row) => `<button data-scw-case="${esc(row.case_id)}"><span><b>${esc(row.case_number)}</b> ${esc(label(row.category))}</span><strong>${esc(row.customer?.name || 'Customer')} · ${esc(row.subject)}</strong><small>${esc(label(row.priority))} · ${esc(label(row.status))} · ${row.conversation?.length || 0} timeline event(s)</small></button>`).join('')}</div>`;
  }

  function studio() {
    const setup = state.data?.setup || {}; const remedies = setup.remedy_policy || {};
    const polling = state.data?.polling || {}; const whatsapp = state.data?.whatsapp || {}; const voice = state.voice || {};
    return `<section class="scw-studio"><div><span>SUPPORT AGENT STUDIO</span><h3>Define how AION protects the customer and the business</h3><p>${esc(label(setup.primary_goal))} · first response ${Number(setup.first_response_minutes || 0)} minutes · resolution target ${Number(setup.resolution_target_hours || 0)} hours</p><div class="scw-actions"><button class="primary" data-scw-panel="setup">Configure support authority</button><button data-scw-panel="knowledge">Add approved FAQ, terms or rights source</button><button data-scw-poll title="Import support email and website enquiries">Check channels now</button><button data-scw-poll-toggle>${polling.enabled ? 'Pause background checks' : 'Enable background checks'}</button><button data-scw-intake>Create secured website door</button>${!voice.dedicated_support_agent ? '<button data-scw-voice>Deploy dedicated Support voice</button>' : ''}</div></div><div><b>${esc(label(setup.status))}</b><small>Background email + website: ${polling.enabled ? `active · every ${Math.round(Number(polling.interval_seconds || 300) / 60)} min` : 'off'}</small><small>Last channel check: ${esc(polling.last_poll_at || 'not yet')}</small><small>Retell Support voice: ${esc(label(voice.status || 'deployment required'))}</small><small>WhatsApp Business: ${esc(label(whatsapp.status || 'configuration required'))}</small><small>Automatic refund: ${remedies.automatic_refund_enabled ? 'enabled' : 'off'} · Legal self-authority: never</small></div></section>`;
  }

  function detail() {
    const row = selected(); if (!row) return '';
    const drafts = selectedResponses();
    return `<section class="scw-detail"><header><div><span>${esc(row.case_number)}</span><h3>${esc(row.subject)}</h3><p>${esc(row.customer?.name)} · ${esc(row.customer?.email || row.customer?.phone || 'contact route missing')}</p></div><button data-scw-close>×</button></header><div class="scw-badges"><b>${esc(label(row.category))}</b><b>${esc(label(row.priority))}</b><b>${esc(label(row.status))}</b></div>${row.risk_flags?.length ? `<div class="scw-warning"><b>Escalation flags</b><p>${row.risk_flags.map(label).join(' · ')}</p></div>` : ''}<section><b>Matched business records</b>${row.linked_records?.length ? row.linked_records.map((x) => `<p>${esc(label(x.record_type))} · ${esc(x.record_id)}</p>`).join('') : '<p>No canonical customer/order/job match yet.</p>'}</section><section><b>Conversation evidence</b>${(row.conversation || []).map((event) => `<article><small>${esc(label(event.direction))} · ${esc(label(event.channel))} · ${esc(event.recorded_at)}</small><p>${esc(event.content)}</p><code>${esc(String(event.content_hash || '').slice(0, 24))}</code></article>`).join('')}</section><section><b>Governed reply drafts</b>${drafts.length ? drafts.map((draft) => `<article><small>${esc(label(draft.status))} · ${esc(label(draft.requested_action))}</small><p>${esc(draft.body)}</p><div class="scw-actions">${draft.status === 'exact_approval_required' ? `<button data-scw-approve="${esc(draft.response_id)}" data-scw-hash="${esc(draft.response_hash)}">Approve exact reply</button>` : ''}${draft.status === 'approved_not_sent' && draft.channel === 'email' ? `<button class="primary" data-scw-gmail-draft="${esc(draft.response_id)}" data-scw-hash="${esc(draft.response_hash)}">Create Gmail draft</button>` : ''}</div></article>`).join('') : '<p>No response prepared.</p>'}</section><footer class="scw-actions"><button class="primary" data-scw-panel="response">Prepare grounded reply</button><button data-scw-panel="escalate">Escalate</button><button data-scw-panel="resolve">Record verified resolution</button><button data-scw-close>Close</button></footer></section>`;
  }

  function panel() {
    const close = '<button type="button" data-scw-close>×</button>'; const setup = state.data?.setup || {};
    if (state.panel === 'new') return `<aside class="scw-panel"><form data-scw-form="new"><header><div><span>NEW SUPPORT CASE</span><h2>Record a customer problem</h2></div>${close}</header><div class="scw-two"><label>Channel<select name="channel">${(setup.supported_channels || ['manual']).map((x) => `<option value="${esc(x)}">${esc(label(x))}</option>`).join('')}</select></label><label>Source reference<input name="source_reference" required placeholder="Email, call or internal reference"></label></div><label>Subject<input name="subject" required></label><label>Customer message<textarea name="message" rows="6" required></textarea></label><div class="scw-two"><label>Customer name<input name="customer_name"></label><label>Email<input name="email" type="email"></label></div><div class="scw-two"><label>Phone<input name="phone"></label><label>Provider thread ID<input name="provider_thread_id"></label></div><footer><button type="button" data-scw-close>Cancel</button><button class="primary">Create governed case</button></footer></form></aside>`;
    if (state.panel === 'setup') {
      const remedy = setup.remedy_policy || {}; const legal = setup.legal_policy || {};
      return `<aside class="scw-panel"><form data-scw-form="setup"><header><div><span>SUPPORT AUTHORITY</span><h2>Configure goals, service levels and remedies</h2><p>AION can understand broadly but only promise or execute what is authorised here.</p></div>${close}</header><div class="scw-two"><label>Primary goal<input name="primary_goal" value="${esc(setup.primary_goal || 'safe_verified_resolution')}"></label><label>Response tone<input name="tone" value="${esc(setup.tone || 'calm_clear_human')}"></label></div><div class="scw-two"><label>First response minutes<input type="number" min="5" name="first_response_minutes" value="${Number(setup.first_response_minutes || 240)}"></label><label>Resolution target hours<input type="number" min="1" name="resolution_target_hours" value="${Number(setup.resolution_target_hours || 48)}"></label></div><div class="scw-two"><label>Exact-approved refund ceiling<input type="number" min="0" step="0.01" name="refund_limit" value="${Number(remedy.exact_approval_refund_limit || 0)}"></label><label>Default jurisdiction<input name="jurisdiction" value="${esc(legal.default_jurisdiction || '')}" placeholder="e.g. Spain / EU"></label></div><label>Supported channels<input name="channels" value="${esc((setup.supported_channels || []).join(', '))}"></label><label>Languages<input name="languages" value="${esc((setup.languages || []).join(', '))}"></label><p class="scw-warning">Automatic refunds remain off. Legal conclusions require applicable consumer-law authority and approved business terms. Human requests, safety, vulnerability, legal threats, fraud and data rights always escalate.</p><footer><button type="button" data-scw-close>Cancel</button><button class="primary">Save controlled version</button></footer></form></aside>`;
    }
    if (state.panel === 'knowledge') return `<aside class="scw-panel"><form data-scw-form="knowledge"><header><div><span>APPROVED KNOWLEDGE</span><h2>Add policy, terms, FAQ or legal source</h2></div>${close}</header><div class="scw-two"><label>Source type<select name="source_type"><option value="approved_faq">Approved FAQ</option><option value="terms">Business terms</option><option value="consumer_law">Consumer law</option><option value="refund_policy">Refund policy</option><option value="warranty">Warranty</option><option value="product_service">Product/service</option><option value="operating_policy">Operating policy</option></select></label><label>Jurisdiction<input name="jurisdiction"></label></div><label>Title<input name="title" required></label><label>Authoritative source/reference<input name="source_reference" required placeholder="Document, URL or approved record"></label><label>Approved content<textarea name="content" rows="10" required></textarea></label><label>Effective from<input type="date" name="effective_from"></label><footer><button type="button" data-scw-close>Cancel</button><button class="primary">Approve into Support knowledge</button></footer></form></aside>`;
    if (state.panel === 'response') return `<aside class="scw-panel"><form data-scw-form="response"><header><div><span>GROUNDED RESPONSE</span><h2>Prepare—do not send—a support reply</h2></div>${close}</header><label>Requested action<select name="requested_action"><option value="prepare_reply">Reply only</option><option value="explain_verified_information">Explain verified information</option><option value="prepare_callback_or_revisit">Prepare callback or revisit</option><option value="recommend_refund_or_compensation">Recommend refund/compensation</option><option value="issue_refund">Prepare refund decision</option><option value="cancel_service">Prepare cancellation</option></select></label><label>Remedy amount, if applicable<input name="remedy_amount" type="number" min="0" step="0.01"></label><label>Proposed response<textarea name="proposed_body" rows="10" required></textarea></label><small>The resulting draft will cite matched knowledge and either require exact approval or fail closed to a person.</small><footer><button type="button" data-scw-close>Cancel</button><button class="primary">Prepare governed response</button></footer></form></aside>`;
    if (state.panel === 'escalate') return `<aside class="scw-panel"><form data-scw-form="escalate"><header><div><span>ESCALATE</span><h2>Hand this case to the correct authority</h2></div>${close}</header><label>Destination<select name="destination"><option value="human">Support person</option><option value="finance">Finance</option><option value="operations">Operations</option><option value="sales">Sales</option><option value="legal_privacy">Legal/privacy authority</option></select></label><label>Assigned person<select name="assigned_person_id"><option value="">Unassigned queue</option>${actorOptions()}</select></label><label>Reason<textarea name="reason" required></textarea></label><footer><button type="button" data-scw-close>Cancel</button><button class="primary">Create handoff</button></footer></form></aside>`;
    if (state.panel === 'resolve') return `<aside class="scw-panel"><form data-scw-form="resolve"><header><div><span>VERIFIED RESOLUTION</span><h2>Close only from independent evidence</h2></div>${close}</header><label>Outcome<textarea name="outcome" required></textarea></label><label>Authority<select name="authority_type"><option value="customer_confirmation">Customer confirmation</option><option value="owner_confirmation">Owner confirmation</option><option value="provider_verified_outcome">Provider-verified outcome</option></select></label><label>Evidence reference<input name="evidence_reference" required></label><footer><button type="button" data-scw-close>Cancel</button><button class="primary">Record resolution</button></footer></form></aside>`;
    return '';
  }

  function markup() {
    return `<section class="scw-shell" data-aion-support-cases><header><div><span>CUSTOMER · CASE · EVIDENCE · RESOLUTION</span><h2>Support Case Centre</h2><p>One protected timeline across email, website, telephone and human work—with business policy and consumer-rights safeguards.</p></div><b>${state.busy ? 'WORKING…' : 'NO AUTONOMOUS REFUNDS'}</b></header>${state.error ? `<div class="scw-alert bad">${esc(state.error)}</div>` : ''}${state.message ? `<div class="scw-alert good">${esc(state.message)}</div>` : ''}${metrics()}<nav><label>Acting as <select data-scw-actor><option value="">Select authorised person</option>${actorOptions(state.actorId)}</select></label><button class="primary" data-scw-panel="new">+ New support case</button></nav>${studio()}<section class="scw-board"><div><span>SUPPORT QUEUE</span><h3>Cases requiring attention</h3></div>${caseQueue()}</section>${detail()}${panel()}</section>`;
  }

  function styles() {
    if (document.getElementById('aion-support-case-styles')) return;
    const style = document.createElement('style'); style.id = 'aion-support-case-styles';
    style.textContent = `.scw-shell{background:#f8fbfd;color:#18324a;border:1px solid #c8dbe8;padding:24px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.scw-shell>header,.scw-studio,.scw-detail>header,.scw-panel header,.scw-shell nav{display:flex;justify-content:space-between;gap:18px;align-items:center}.scw-shell h2,.scw-shell h3{margin:5px 0}.scw-shell p{line-height:1.45}.scw-shell button,.scw-shell select,.scw-shell input,.scw-shell textarea{font:inherit;border:1px solid #9bb7ca;background:#fff;padding:10px;color:#18324a}.scw-shell button{cursor:pointer;font-weight:700}.scw-shell .primary{background:#137f6b;color:#fff;border-color:#137f6b}.scw-metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:18px 0}.scw-metrics article,.scw-studio,.scw-board,.scw-detail{background:#fff;border:1px solid #c8dbe8;padding:16px}.scw-metrics strong{font-size:26px;display:block}.scw-metrics span,.scw-shell small{display:block;color:#587087;margin-top:5px}.scw-studio{display:grid;grid-template-columns:1fr auto;gap:20px;border-left:5px solid #18a8df;margin:18px 0}.scw-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.scw-list{display:grid;gap:8px}.scw-list>button{text-align:left;display:grid;gap:5px}.scw-detail{margin-top:18px;border-left:5px solid #137f6b}.scw-badges{display:flex;gap:8px;margin:12px 0}.scw-badges b{background:#e6f2f8;padding:6px 9px}.scw-warning{background:#fff5da;border:1px solid #e8b94f;padding:12px}.scw-detail article{border-top:1px solid #d7e4ec;padding:10px 0}.scw-panel{position:fixed;z-index:10020;right:24px;top:24px;bottom:24px;width:min(680px,calc(100vw - 48px));overflow:auto;background:#fff;border:2px solid #137f6b;box-shadow:0 18px 60px #17324855;padding:20px}.scw-panel label{display:grid;gap:5px;margin:12px 0}.scw-two{display:grid;grid-template-columns:1fr 1fr;gap:12px}.scw-panel footer{display:flex;justify-content:flex-end;gap:8px;margin-top:20px}.scw-alert{padding:12px;margin:12px 0}.scw-alert.good{background:#e1f5ed}.scw-alert.bad{background:#ffe5e5}.scw-empty{padding:30px;text-align:center}@media(max-width:800px){.scw-metrics{grid-template-columns:repeat(2,1fr)}.scw-two,.scw-studio{grid-template-columns:1fr}}`;
    document.head.appendChild(style);
  }

  async function load(requireVisibleMount = true) {
    const id = businessId(); if (!id || (requireVisibleMount && !mount())) return; state.workspaceId = id;
    if (state.loading) return;
    state.loading = true;
    try {
      const [data, voice] = await Promise.all([
        request(`/api/aion/support/${encodeURIComponent(id)}`),
        request(`/api/aion/support/${encodeURIComponent(id)}/voice`).catch(() => null),
      ]);
      state.data = data; state.voice = voice || null; state.loadedAt = Date.now();
      if (requireVisibleMount) {
        render();
      } else {
        // Only background dashboard hydration announces that its data is ready.
        // A visible Support load must not request a whole-application redraw:
        // that replaces this mount and used to make the Case Centre disappear.
        global.dispatchEvent(new CustomEvent('aion:support-workspace-updated', { detail: { workspaceId: id } }));
      }
    }
    catch (error) { state.error = error.message; if (state.data) render(); }
    finally { state.loading = false; }
  }
  function render() { const root = mount(); if (!root || !state.data) return; styles(); const old = root.querySelector('[data-aion-support-cases]'); if (old) old.outerHTML = markup(); else root.insertAdjacentHTML('afterbegin', markup()); }
  async function post(path, body, message, method='POST') { state.busy=true; state.error=''; render(); try { await request(path,{method,body:JSON.stringify(body)}); state.message=message; state.panel=''; await load(); } catch(e){state.error=e.message;} finally{state.busy=false;render();} }

  document.addEventListener('change', (event) => { if (event.target.hasAttribute('data-scw-actor')) state.actorId=event.target.value; });
  document.addEventListener('click', (event) => {
    const button=event.target.closest('[data-aion-support-cases] button'); if(!button)return;
    if(button.hasAttribute('data-scw-close')){state.panel='';state.selectedId='';render();return;}
    if(button.hasAttribute('data-scw-poll')){
      if(!state.actorId){state.error='Select the authorised person checking Support channels';render();return;}
      return post(`/api/aion/support/${encodeURIComponent(state.workspaceId)}/polling/run`,{},'Email and website Support channels checked. New messages were joined to canonical cases; nothing was sent.');
    }
    if(button.hasAttribute('data-scw-poll-toggle')){
      if(!state.actorId){state.error='Select the authorised person changing background checks';render();return;}
      const p=state.data.polling;
      return post(`/api/aion/support/${encodeURIComponent(state.workspaceId)}/polling`,{expected_polling_hash:p.polling_hash,enabled:!p.enabled,interval_seconds:p.interval_seconds||300,sources:p.sources||{gmail:true,website_queue:true},gmail_query:p.gmail_query,configured_by_person_id:state.actorId},!p.enabled?'Background Support checks enabled.':'Background Support checks paused.','PUT');
    }
    if(button.hasAttribute('data-scw-voice')){
      if(!state.actorId){state.error='Select the authorised person deploying Support voice';render();return;}
      return post(`/api/aion/support/${encodeURIComponent(state.workspaceId)}/voice/deploy`,{deployed_by_person_id:state.actorId},'Dedicated governed Support voice agent deployed. It remains unbound and cannot place calls.');
    }
    if(button.hasAttribute('data-scw-intake')){
      if(!state.actorId){state.error='Select the authorised person creating the website endpoint';render();return;}
      state.busy=true;render(); request(`/api/aion/support/${encodeURIComponent(state.workspaceId)}/intake-endpoints`,{method:'POST',body:JSON.stringify({name:'Website support',created_by_person_id:state.actorId})}).then((result)=>{state.message=`Website support endpoint created: ${result.endpoint.endpoint_id}. Copy its one-time token now: ${result.endpoint.token}`;return load();}).catch((e)=>{state.error=e.message;}).finally(()=>{state.busy=false;render();}); return;
    }
    if(button.dataset.scwApprove){
      if(!state.actorId){state.error='Select the authorised person approving this exact reply';render();return;}
      return post(`/api/aion/support/${encodeURIComponent(state.workspaceId)}/responses/${encodeURIComponent(button.dataset.scwApprove)}/approve`,{expected_response_hash:button.dataset.scwHash,approved_by_person_id:state.actorId},'Exact reply approved. It has not been sent.');
    }
    if(button.dataset.scwGmailDraft){
      if(!state.actorId){state.error='Select the authorised person creating this Gmail draft';render();return;}
      return post(`/api/aion/support/${encodeURIComponent(state.workspaceId)}/responses/${encodeURIComponent(button.dataset.scwGmailDraft)}/gmail-draft`,{expected_response_hash:button.dataset.scwHash,approved_by_person_id:state.actorId},'Gmail draft created in the original thread. It has not been sent.');
    }
    if(button.dataset.scwPanel){state.panel=button.dataset.scwPanel;render();return;}
    if(button.dataset.scwCase){state.selectedId=button.dataset.scwCase;render();}
  });
  document.addEventListener('submit', async (event) => {
    const form=event.target.closest('[data-aion-support-cases] form'); if(!form)return; event.preventDefault();
    if(!state.actorId){state.error='Select the authorised person acting on this Support task';render();return;}
    const value=values(form); const base=`/api/aion/support/${encodeURIComponent(state.workspaceId)}`;
    if(form.dataset.scwForm==='new') return post(`${base}/cases`,{...value,evidence_references:[],created_by_person_id:state.actorId},'Support case created, classified and matched. No external action occurred.');
    if(form.dataset.scwForm==='knowledge') return post(`${base}/knowledge`,{...value,effective_from:value.effective_from||null,jurisdiction:value.jurisdiction||null,approved_by_person_id:state.actorId},'Approved knowledge source added with provenance.');
    if(form.dataset.scwForm==='setup') return post(`${base}/agent-setup`,{expected_setup_hash:state.data.setup.setup_hash,configured_by_person_id:state.actorId,setup:{primary_goal:value.primary_goal,tone:value.tone,first_response_minutes:Number(value.first_response_minutes),resolution_target_hours:Number(value.resolution_target_hours),supported_channels:value.channels.split(',').map(x=>x.trim()),languages:value.languages.split(',').map(x=>x.trim()),required_identity_checks:state.data.setup.required_identity_checks,knowledge_sources:state.data.setup.knowledge_sources,action_policy:state.data.setup.action_policy,mandatory_escalations:state.data.setup.mandatory_escalations,remedy_policy:{...state.data.setup.remedy_policy,exact_approval_refund_limit:Number(value.refund_limit||0)},legal_policy:{...state.data.setup.legal_policy,default_jurisdiction:value.jurisdiction||null}}},'New controlled Support Agent configuration saved.','PUT');
    if(form.dataset.scwForm==='response') return post(`${base}/cases/${encodeURIComponent(state.selectedId)}/responses`,{proposed_body:value.proposed_body,requested_action:value.requested_action,remedy_amount:value.remedy_amount?Number(value.remedy_amount):null,prepared_by_person_id:state.actorId},'Grounded response prepared. Nothing was sent or refunded.');
    if(form.dataset.scwForm==='escalate') return post(`${base}/cases/${encodeURIComponent(state.selectedId)}/escalate`,{destination:value.destination,reason:value.reason,assigned_person_id:value.assigned_person_id||null,escalated_by_person_id:state.actorId},'Case escalated internally.');
    if(form.dataset.scwForm==='resolve') return post(`${base}/cases/${encodeURIComponent(state.selectedId)}/resolve`,{outcome:value.outcome,evidence_reference:value.evidence_reference,authority_type:value.authority_type,resolved_by_person_id:state.actorId},'Verified resolution recorded.');
  });
  const attemptMount = () => {
    const root = mount();
    const id = businessId();
    if (!root || !id) return;
    if (state.workspaceId === id && state.data) {
      // A legitimate parent render may replace the mount. Restore from the
      // canonical in-memory snapshot immediately instead of flashing blank or
      // fetching again.
      if (!root.querySelector('[data-aion-support-cases]')) render();
      return;
    }
    if (!state.loading) load();
  };
  new MutationObserver(attemptMount).observe(document.documentElement, { childList: true, subtree: true });
  global.addEventListener('load', attemptMount);
  attemptMount();
  function ensureDashboardData() {
    const id = businessId();
    if (!id) return Promise.resolve(null);
    if (state.workspaceId === id && state.data && Date.now() - state.loadedAt < 30000) return Promise.resolve(state.data);
    return load(false);
  }
  function openCase(caseId) {
    state.selectedId = String(caseId || '');
    state.panel = '';
    render();
  }
  global.AionSupportCaseWorkspace={load,ensureDashboardData,openCase,snapshot:()=>state.data};
})(window);
