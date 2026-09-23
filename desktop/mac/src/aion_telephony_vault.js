(function installAionTelephonyVault(global) {
  'use strict';

  const API = 'http://127.0.0.1:8080';
  const state = { workspaceId: '', status: null, loading: false, busy: '', message: '', error: '' };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const workspaceId = () => global.AionSalesRevenue?.state?.workspaceId || global.AionBusinessContainerClient?.resolveBusinessId?.() || 'costa-conexion';

  async function request(path, options = {}) {
    const controller = new AbortController();
    const timer = global.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(`${API}${path}`, {
        ...options,
        signal: controller.signal,
        headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) },
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(String(body.detail || body.error || `Request failed ${response.status}`).replaceAll('_', ' '));
      return body;
    } catch (error) {
      if (error?.name === 'AbortError') throw new Error('The local Vault did not respond. Reopen Tessaris and try again.');
      throw error;
    } finally { global.clearTimeout(timer); }
  }

  function replacePanel() {
    const current = document.querySelector('[data-aion-telephony-vault="true"]');
    if (current) current.outerHTML = render();
  }

  async function load(force = false) {
    const id = workspaceId();
    if (!id || state.loading || (!force && state.workspaceId === id && state.status)) return;
    state.workspaceId = id; state.loading = true; state.error = '';
    replacePanel();
    try { state.status = await request(`/api/vault/telephony/${encodeURIComponent(id)}`); }
    catch (error) { state.error = error.message; }
    finally { state.loading = false; replacePanel(); }
  }

  async function submit(provider, form) {
    const id = workspaceId();
    const payload = Object.fromEntries(new FormData(form).entries());
    state.busy = provider; state.error = ''; state.message = ''; replacePanel();
    try {
      state.status = await request(`/api/vault/telephony/${encodeURIComponent(id)}/${provider}`, { method: 'POST', body: JSON.stringify(payload) });
      state.message = provider === 'twilio'
        ? 'Twilio is verified and its credentials are secured in Vault.'
        : 'Retell is verified and its API key is secured in Vault.';
    } catch (error) { state.error = error.message; }
    finally { state.busy = ''; replacePanel(); }
  }

  async function refresh() {
    const id = workspaceId();
    state.busy = 'refresh'; state.error = ''; state.message = ''; replacePanel();
    try {
      state.status = await request(`/api/vault/telephony/${encodeURIComponent(id)}/refresh`, { method: 'POST' });
      state.message = 'Both providers were checked again. No calls were started.';
    } catch (error) { state.error = error.message; }
    finally { state.busy = ''; replacePanel(); }
  }

  function open() {
    if (typeof global.setAionSidebarActiveTabHardV1 === 'function') global.setAionSidebarActiveTabHardV1('vault');
    else if (typeof global.setActiveTab === 'function') {
      global.setActiveTab('vault');
      global.requestRender?.();
    }
    [80, 220, 500, 900].forEach((delay) => global.setTimeout(() => {
      const panel = document.querySelector('[data-aion-telephony-vault="true"]');
      if (!panel) return;
      panel.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
      panel.setAttribute('data-tv-focus', 'true');
      global.setTimeout(() => panel.removeAttribute('data-tv-focus'), 1800);
      void load();
    }, delay));
  }

  const badge = (ready, readyText = 'Connected') => `<span class="tv-status ${ready ? 'is-ready' : ''}">${ready ? '✓ ' + readyText : 'Setup required'}</span>`;
  const field = (name, label, placeholder, type = 'text', help = '') => `
    <label class="tv-field"><span>${esc(label)}</span><input name="${esc(name)}" type="${esc(type)}" placeholder="${esc(placeholder)}" autocomplete="off" required>${help ? `<small>${esc(help)}</small>` : ''}</label>`;

  function twilioStep(status) {
    const connected = status.connected === true;
    return `<article class="tv-step ${connected ? 'is-complete' : ''}">
      <header class="tv-step-head">
        <div class="tv-number">1</div><span class="tv-twilio-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <div><span class="tv-provider">Twilio</span><h3>Connect your telephone number</h3><p>Twilio supplies the number and carries inbound and outbound calls.</p></div>
        ${badge(connected)}
      </header>
      ${connected ? `<div class="tv-connected-summary"><strong>${esc(status.phone_number || 'Telephone number connected')}</strong><span>SIP trunk verified${status.termination_uri ? ` · ${esc(status.termination_uri)}` : ''}</span></div>` : `
      <div class="tv-instructions">
        <h4>What to do in Twilio</h4>
        <ol>
          <li><a href="https://www.twilio.com/try-twilio" target="_blank" rel="noreferrer">Create or open your Twilio account ↗</a>, add billing and buy a voice-capable number.</li>
          <li>In <b>Account → API keys &amp; tokens</b>, create a <b>Standard API key</b> called “Tessaris”. Copy the secret now—Twilio shows it once.</li>
          <li>In <b>Elastic SIP Trunking</b>, create a trunk. Set its origination URI to <code>sip:sip.retellai.com</code>, add a credential list, and attach the number to that trunk.</li>
          <li>Copy the account, key, number and trunk details into Vault below.</li>
        </ol>
      </div>
      <form class="tv-form" data-tv-form="twilio">
        <div class="tv-form-grid">
          ${field('account_sid', 'Account SID', 'AC…', 'text', 'Shown on the Twilio Console dashboard.')}
          ${field('api_key_sid', 'API Key SID', 'SK…')}
          ${field('api_key_secret', 'API Key Secret', 'Paste the one-time secret', 'password')}
          ${field('from_number', 'Twilio phone number', '+34…', 'tel', 'Use international E.164 format.')}
          ${field('termination_uri', 'Termination SIP URI', 'your-trunk.pstn.twilio.com')}
          ${field('sip_username', 'SIP username', 'Credential-list username')}
          ${field('sip_password', 'SIP password', 'Credential-list password', 'password')}
          <label class="tv-field"><span>Trunk SID <em>optional</em></span><input name="trunk_sid" placeholder="TK…" autocomplete="off"></label>
        </div>
        <button class="primary-btn" type="submit" ${state.busy ? 'disabled' : ''}>${state.busy === 'twilio' ? 'Checking…' : 'Verify and save Twilio'}</button>
      </form>`}
      <details class="tv-help"><summary>Why Tessaris needs these details</summary><p>The API key checks the Twilio account. The number and SIP trunk carry calls between Twilio and Retell. Tessaris stores secrets in the Mac system Vault and never displays them again.</p></details>
    </article>`;
  }

  function retellStep(status, twilio, routing) {
    const connected = status.connected === true;
    return `<article class="tv-step ${connected ? 'is-complete' : ''}">
      <header class="tv-step-head">
        <div class="tv-number">2</div><span class="tv-retell-mark" aria-hidden="true">R</span>
        <div><span class="tv-provider">Retell AI</span><h3>Connect the AI voice service</h3><p>Retell speaks, listens and returns the verified call result to Tessaris.</p></div>
        ${badge(connected)}
      </header>
      ${connected ? `<div class="tv-connected-summary"><strong>Retell API connected</strong><span>${Number(status.agent_count || 0)} voice agent${Number(status.agent_count || 0) === 1 ? '' : 's'} · ${Number(status.phone_number_count || 0)} imported number${Number(status.phone_number_count || 0) === 1 ? '' : 's'}</span></div>
      ${!routing.number_imported_to_retell ? `<div class="tv-instructions"><h4>Finish the telephone route in Retell</h4><ol><li>Open <a href="https://beta.retellai.com/" target="_blank" rel="noreferrer">Phone Numbers in Retell ↗</a> and choose <b>Import</b>.</li><li>Import ${twilio.phone_number ? `<b>${esc(twilio.phone_number)}</b>` : 'your Twilio number'} using the termination SIP URI and the same Twilio credential-list username/password from step 1.</li><li>Assigning an inbound or outbound agent happens later, after its Tessaris contract has been minted and approved.</li></ol></div>` : ''}` : `
      <div class="tv-instructions">
        <h4>What to do in Retell</h4>
        <ol>
          <li><a href="https://beta.retellai.com/" target="_blank" rel="noreferrer">Create or open your Retell account ↗</a> and add billing.</li>
          <li>Open <b>API Keys</b>, create a key for Tessaris and copy it below.</li>
          <li>Open <b>Phone Numbers → Import</b>. Import ${twilio.phone_number ? `<b>${esc(twilio.phone_number)}</b>` : 'your Twilio number'} using the Twilio termination SIP URI and credential-list username/password from step 1.</li>
          <li>Do not build the final script in Retell. Tessaris mints and supplies the approved call contract for each sales agent.</li>
        </ol>
      </div>
      <form class="tv-form" data-tv-form="retell">
        ${field('api_key', 'Retell API key', 'Paste your Retell API key', 'password', 'Used locally to create agents, assign numbers and read call results.')}
        <button class="primary-btn" type="submit" ${state.busy ? 'disabled' : ''}>${state.busy === 'retell' ? 'Checking…' : 'Verify and save Retell'}</button>
      </form>`}
      <details class="tv-help"><summary>What Retell is allowed to do</summary><p>Retell executes only a promoted Tessaris call plan. It receives the frozen customer and call contract at call time. It cannot change the approved goal, permissions or safeguards.</p></details>
    </article>`;
  }

  function render() {
    const status = state.status || {};
    const twilio = status.twilio || {};
    const retell = status.retell || {};
    const routing = status.routing || {};
    if (!state.status && !state.loading) queueMicrotask(() => load());
    return `<section class="operations-agents-card aion-vault-canonical-panel tv-panel" data-aion-telephony-vault="true">
      <style>${styles()}</style>
      <div class="tv-hero">
        <div><div class="eyebrow">Sales phone setup</div><h2>Connect your AI call centre</h2><p>Two services, connected once. Twilio provides the telephone line; Retell runs the approved AI conversation.</p></div>
        <div class="tv-progress"><strong>${Number(status.completed_steps || 0)}/2</strong><span>services connected</span></div>
      </div>
      ${state.message ? `<div class="tv-notice success">${esc(state.message)}</div>` : ''}
      ${state.error ? `<div class="tv-notice error">${esc(state.error)}</div>` : ''}
      ${status.completed_steps < 2 && (twilio.credential_present || retell.credential_present) ? `<div class="tv-notice info"><div><strong>Existing phone credentials found in Vault</strong><span>Verify the saved keys before replacing them. This is read-only and will not start a call.</span></div><button type="button" class="secondary-btn" data-tv-refresh="true" ${state.busy ? 'disabled' : ''}>${state.busy === 'refresh' ? 'Checking…' : 'Check existing Vault keys'}</button></div>` : ''}
      ${state.loading ? `<div class="tv-loading">Checking Vault connections…</div>` : `<div class="tv-steps">${twilioStep(twilio)}${retellStep(retell, twilio, routing)}</div>`}
      ${status.completed_steps === 2 ? `<div class="tv-next ${routing.ready_to_build_callers ? 'is-ready' : ''}">
        <div><strong>${routing.ready_to_build_callers ? '✓ Ready to build sales callers' : 'One routing check remains'}</strong><span>${routing.ready_to_build_callers ? 'Both services and the telephone route are verified. Go to Sales to create an inbound or outbound caller and mint its contract.' : `Import ${esc(twilio.phone_number || 'the Twilio number')} into Retell, then check the connections again.`}</span></div>
        <button type="button" class="secondary-btn" data-tv-refresh="true" ${state.busy ? 'disabled' : ''}>${state.busy === 'refresh' ? 'Checking…' : 'Check connections again'}</button>
      </div>` : ''}
      <p class="tv-boundary">Connecting services does not start a call, activate an agent or purchase anything. Those actions remain separate and approval-gated.</p>
    </section>`;
  }

  function styles() { return `
    .tv-panel{overflow:hidden}.tv-panel[data-tv-focus="true"]{outline:4px solid rgba(14,165,233,.28);outline-offset:4px}.tv-hero{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;padding:24px;border-bottom:1px solid #d7e3ed}.tv-hero h2{margin:4px 0 6px;font-size:27px}.tv-hero p{margin:0;color:#58708b;max-width:760px}.tv-progress{min-width:125px;text-align:right}.tv-progress strong{display:block;color:#075f8d;font-size:30px}.tv-progress span{font-size:12px;color:#65758a}.tv-steps{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px;background:#f5f8fb}.tv-step{background:#fff;border:1px solid #c9d9e6;padding:18px;min-width:0}.tv-step.is-complete{border-top:4px solid #198a45}.tv-step-head{display:grid;grid-template-columns:34px 34px minmax(0,1fr) auto;gap:11px;align-items:start}.tv-number{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;background:#075f8d;color:#fff;font-weight:800}.tv-provider{font-size:11px;font-weight:900;letter-spacing:.13em;text-transform:uppercase;color:#08766d}.tv-step h3{font-size:20px;margin:2px 0 5px}.tv-step-head p{margin:0;color:#60758c;font-size:13px;line-height:1.35}.tv-status{font-size:11px;font-weight:800;color:#8b5a00;background:#fff5dc;padding:7px 9px;white-space:nowrap}.tv-status.is-ready{color:#126e38;background:#e8f7ee}.tv-twilio-mark{position:relative;width:31px;height:31px;border:3px solid #e51b42;border-radius:50%}.tv-twilio-mark i{position:absolute;width:7px;height:7px;background:#e51b42;border-radius:50%}.tv-twilio-mark i:nth-child(1){left:5px;top:5px}.tv-twilio-mark i:nth-child(2){right:5px;top:5px}.tv-twilio-mark i:nth-child(3){left:5px;bottom:5px}.tv-twilio-mark i:nth-child(4){right:5px;bottom:5px}.tv-retell-mark{width:31px;height:31px;display:grid;place-items:center;border-radius:7px;background:#7657ff;color:#fff;font-weight:900;font-size:20px}.tv-instructions{margin:18px 0;padding:15px;background:#f7f9fc;border-left:3px solid #08a4df}.tv-instructions h4{margin:0 0 9px}.tv-instructions ol{margin:0;padding-left:20px;color:#344c64;font-size:13px;line-height:1.45}.tv-instructions li+li{margin-top:7px}.tv-instructions a{color:#075f8d;font-weight:800}.tv-instructions code{font-size:12px;background:#e9f0f6;padding:2px 4px}.tv-form{display:grid;gap:14px}.tv-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.tv-field{display:grid;gap:5px;min-width:0}.tv-field>span{font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#445970}.tv-field em{font-weight:500;letter-spacing:0;text-transform:none}.tv-field input{box-sizing:border-box;width:100%;height:46px;border:1px solid #aebfd0;background:#fff;padding:10px 12px;color:#172a3e;font:inherit}.tv-field small{color:#718297;font-size:11px}.tv-form>.tv-field{max-width:100%}.tv-form button{justify-self:start}.tv-help{margin-top:14px;border-top:1px solid #dde6ee;padding-top:11px}.tv-help summary{cursor:pointer;font-weight:800;color:#075f8d}.tv-help p{color:#60758c;font-size:13px;line-height:1.45}.tv-connected-summary{display:flex;justify-content:space-between;gap:12px;margin:18px 0;padding:16px;background:#edf8f1;color:#175f36}.tv-connected-summary span{color:#567365;text-align:right}.tv-notice{margin:14px 16px 0;padding:11px 14px;font-weight:700}.tv-notice.success{background:#e8f7ee;color:#126e38}.tv-notice.error{background:#fff0f0;color:#a72c2c}.tv-notice.info{display:flex;align-items:center;justify-content:space-between;gap:16px;background:#eaf5fb;color:#164d68}.tv-notice.info strong,.tv-notice.info span{display:block}.tv-notice.info span{margin-top:3px;font-size:12px;font-weight:500}.tv-loading{padding:30px;color:#60758c}.tv-next{margin:0 16px 16px;padding:16px;border:1px solid #efb34a;background:#fff8e7;display:flex;align-items:center;justify-content:space-between;gap:20px}.tv-next.is-ready{border-color:#61b87f;background:#edf8f1}.tv-next strong,.tv-next span{display:block}.tv-next span{margin-top:4px;color:#586f85}.tv-boundary{margin:0;padding:0 16px 18px;color:#718297;font-size:12px}@media(max-width:1050px){.tv-steps{grid-template-columns:1fr}.tv-form-grid{grid-template-columns:1fr}.tv-step-head{grid-template-columns:34px 34px minmax(0,1fr)}.tv-status{grid-column:3;justify-self:start}.tv-next,.tv-hero,.tv-notice.info{align-items:stretch;flex-direction:column}.tv-progress{text-align:left}}
  `; }

  if (!global.__aionTelephonyVaultHandlers) {
    global.__aionTelephonyVaultHandlers = true;
    document.addEventListener('submit', (event) => {
      const form = event.target?.closest?.('[data-tv-form]');
      if (!form) return;
      event.preventDefault(); void submit(form.dataset.tvForm, form);
    }, true);
    document.addEventListener('click', (event) => {
      if (!event.target?.closest?.('[data-tv-refresh]')) return;
      event.preventDefault(); void refresh();
    }, true);
  }

  global.AionTelephonyVault = { state, render, load, refresh, open };
})(window);
