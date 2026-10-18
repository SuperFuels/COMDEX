(function installAionUsageBillingWorkspace(global) {
  "use strict";

  const API_BASE = "http://127.0.0.1:8080";
  const SECTIONS = [
    ["business", "Business configuration"],
    ["overview", "Overview"],
    ["usage", "Usage"],
    ["limits", "Limits"],
    ["billing", "Billing & receipts"],
    ["privacy", "Privacy"],
  ];
  const state = {
    loading: false,
    loaded: false,
    error: "",
    section: "business",
    tenantId: "",
    commercial: null,
    photonSnapshot: null,
    photonCommercialStatus: null,
    billingRecords: [],
    exportMessage: "",
    businessLoaded: false,
    businessLoading: false,
    businessError: "",
    businessMessage: "",
    businessIdentity: null,
    businessMapRevision: null,
    businessPolicy: "",
    customDepartmentRevision: null,
    customDepartments: [],
  };

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
  const rows = (value) => Array.isArray(value) ? value : [];
  const label = (value) => String(value || "").replaceAll("_", " ");
  const renderNow = () => {
    if (typeof global.requestRender === "function") global.requestRender();
    else if (typeof global.render === "function") global.render();
  };
  const currentTenant = () => {
    const candidates = [
      global.AionBusinessContainerClient?.resolveBusinessId?.(),
      global.getAionBoardroomBusinessContainerId?.(),
      global.state?.workspaceId,
    ];
    for (const candidate of candidates) {
      const canonical = global.AionBusinessContainerClient?.canonicalBusinessId?.(candidate)
        || "";
      if (canonical) return canonical;
    }
    return "business-not-registered";
  };

  async function requestJson(path, init = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json; charset=utf-8" } : {}),
        ...(init.headers || {}),
      },
    });
    let payload = {};
    try { payload = await response.json(); } catch (_) {}
    if (!response.ok) {
      const detail = typeof payload?.detail === "string"
        ? payload.detail : payload?.detail?.reason || `Request failed (${response.status})`;
      throw new Error(String(detail).replaceAll("_", " "));
    }
    return payload;
  }

  async function loadBusinessConfiguration(force = false) {
    const tenantId = currentTenant();
    if (state.businessLoading || (state.businessLoaded && !force && state.tenantId === tenantId)) return;
    state.businessLoading = true;
    state.tenantId = tenantId;
    try {
      const [identity, businessMap, governance, departments] = await Promise.all([
        requestJson(`/api/aion/business/data/business-identity/${encodeURIComponent(tenantId)}`),
        requestJson(`/api/aion/business/data/business-map/${encodeURIComponent(tenantId)}`),
        requestJson(`/api/aion/business/data/business-map/${encodeURIComponent(tenantId)}/governance/queues`),
        requestJson(`/api/aion/business/data/custom-departments/${encodeURIComponent(tenantId)}`),
      ]);
      state.businessIdentity = identity.payload || {};
      state.businessMapRevision = Number(governance.revision || 0);
      const facts = rows(businessMap?.payload?.facts);
      state.businessPolicy = String(
        facts.filter((item) => item?.field === "operating_policy").at(-1)?.value || ""
      );
      state.customDepartmentRevision = Number(departments.revision || 0);
      state.customDepartments = rows(departments.departments);
      state.businessLoaded = true;
      state.businessError = "";
    } catch (error) {
      state.businessError = String(error?.message || error);
    } finally {
      state.businessLoading = false;
      renderNow();
    }
  }

  async function load(force = false) {
    const tenantId = currentTenant();
    if (state.loading || (state.loaded && !force && state.tenantId === tenantId)) return;
    state.loading = true;
    state.tenantId = tenantId;
    try {
      const response = await fetch(`${API_BASE}/api/aion/business/commercial/${encodeURIComponent(tenantId)}`, {
        headers: { Accept: "application/json" }, cache: "no-store",
      });
      if (!response.ok) throw new Error(`Usage controls unavailable (${response.status})`);
      const commercial = await response.json();
      if (commercial?.private_content_included !== false) {
        throw new Error("Usage response did not pass the content-free boundary");
      }
      state.commercial = commercial;
      const broker = global.aionDesktop?.getPhotonBillingView;
      if (typeof broker === "function") {
        const verified = await broker(tenantId);
        if (verified?.connected === true
            && verified?.tenant_id === tenantId
            && verified?.customer_content_included === false
            && verified?.local_model_tokens_billed === false) {
          state.photonSnapshot = { payload: verified.wallet };
          state.photonCommercialStatus = verified.commercial_status || null;
          state.billingRecords = rows(verified.billing_records);
        } else {
          state.photonSnapshot = null;
          state.photonCommercialStatus = null;
          state.billingRecords = [];
        }
      }
      state.loaded = true;
      state.error = "";
    } catch (error) {
      state.error = String(error?.message || error);
    } finally {
      state.loading = false;
      renderNow();
    }
  }

  function renderNavigation() {
    return `<nav class="aion-usage-billing-tabs" aria-label="Usage and billing sections">
      ${SECTIONS.map(([key, title]) => `<button type="button" data-aion-usage-billing-section="${key}" aria-pressed="${state.section === key ? "true" : "false"}">${esc(title)}</button>`).join("")}
    </nav>`;
  }

  function activeTrials() {
    return rows(state.commercial?.trials).filter((item) =>
      ["active", "paid_active", "review_only"].includes(String(item?.state || ""))
    );
  }

  function renderBusinessConfiguration() {
    const identity = state.businessIdentity || {};
    const departments = rows(state.customDepartments);
    return `<section class="aion-usage-billing-panel aion-business-configuration" data-aion-business-configuration="true">
      <header><div><span>BUSINESS VAULT</span><h2>Business configuration</h2><p>These settings and every future department are stored outside the Tessaris application in your encrypted Business Vault.</p></div></header>
      ${state.businessError ? `<div class="aion-usage-billing-error">${esc(state.businessError)}</div>` : ""}
      ${state.businessMessage ? `<div class="aion-business-configuration-success">${esc(state.businessMessage)}</div>` : ""}
      <form data-aion-business-identity-form="true" class="aion-business-configuration-form">
        <div><label for="aion-setting-trading-name">Trading name</label><input id="aion-setting-trading-name" name="trading_name" value="${esc(identity.trading_name || identity.legal_name || "")}" required></div>
        <div><label for="aion-setting-email">Primary business email</label><input id="aion-setting-email" name="primary_email" type="email" value="${esc(identity.primary_email || "")}"></div>
        <div><label for="aion-setting-timezone">Timezone</label><input id="aion-setting-timezone" name="timezone" value="${esc(identity.timezone || "")}" placeholder="Europe/Madrid"></div>
        <div><label for="aion-setting-currency">Currency</label><input id="aion-setting-currency" name="currency" value="${esc(identity.currency || "")}" maxlength="12" placeholder="EUR"></div>
        <button type="submit">Save business settings</button>
      </form>
      <form data-aion-business-policy-form="true" class="aion-business-configuration-block">
        <div><span>VERSIONED POLICY</span><h3>Operating policy</h3><p>A change is proposed and founder-approved as one controlled action, retaining its revision history.</p></div>
        <textarea name="operating_policy" rows="4" required placeholder="State the policy that every department should follow.">${esc(state.businessPolicy)}</textarea>
        <button type="submit">Save policy with approval receipt</button>
      </form>
      <section class="aion-business-configuration-block">
        <div><span>FUTURE DEPARTMENTS</span><h3>Departments created for this business</h3><p>New departments introduced now or by a later Tessaris update use the wildcard Vault domains automatically.</p></div>
        <div class="aion-business-department-list">${departments.length
          ? departments.map((item) => `<article><strong>${esc(item.name)}</strong><span>${esc(item.pilot_title || item.template)} · ${esc(item.mandate)}</span></article>`).join("")
          : `<div class="aion-usage-empty">No founder-created departments yet.</div>`}</div>
        <form data-aion-custom-department-form="true" class="aion-business-configuration-form department">
          <div><label for="aion-department-name">Department name</label><input id="aion-department-name" name="name" required placeholder="e.g. Quality Assurance"></div>
          <div><label for="aion-department-template">Starting template</label><select id="aion-department-template" name="template"><option value="innovation">Innovation</option><option value="legal">Legal &amp; compliance</option><option value="compliance">Compliance</option><option value="it">IT</option><option value="technical">Technical</option><option value="product">Product</option><option value="research">Research</option><option value="partnerships">Partnerships</option></select></div>
          <div class="wide"><label for="aion-department-mandate">Pilot mandate</label><textarea id="aion-department-mandate" name="mandate" rows="3" required placeholder="Explain what this department owns and when it must ask for approval."></textarea></div>
          <label class="wide aion-business-confirm"><input type="checkbox" name="confirm_founder_authority" required> I confirm I am authorised to add this department to the business.</label>
          <button type="submit">Create department in Business Vault</button>
        </form>
      </section>
    </section>`;
  }

  function renderOverview() {
    const snapshot = state.photonSnapshot?.payload || null;
    const trials = activeTrials();
    const hold = state.photonCommercialStatus?.commercial_hold === true;
    return `${hold ? `<section class="aion-usage-billing-error"><strong>Billing review required</strong><p>A final payment dispute could not yet be fully reversed because some Photons were already consumed. Paid automation is held while the billing team resolves the content-free payment record. Your Business Vault and local data remain available.</p></section>` : ""}<div class="aion-usage-billing-grid">
      <section class="aion-usage-billing-card emphasis">
        <span>Photon balance</span>
        <strong>${snapshot ? esc(Number(snapshot.available_photons || 0).toLocaleString()) : "—"}</strong>
        <p>${snapshot ? `${esc(Number(snapshot.reserved_photons || 0).toLocaleString())} reserved` : "A signed billing session has not been connected to this Node."}</p>
      </section>
      <section class="aion-usage-billing-card">
        <span>Active services</span><strong>${trials.length}</strong>
        <p>${trials.length ? trials.map((item) => esc(label(item.department))).join(" · ") : "No active paid or trial department service."}</p>
      </section>
      <section class="aion-usage-billing-card">
        <span>Verified outcomes</span><strong>${esc(Number(state.commercial?.value?.verified_actions || 0).toLocaleString())}</strong>
        <p>Only completed published outcomes can consume Photons.</p>
      </section>
      <section class="aion-usage-billing-card">
        <span>Automatic overage</span><strong>Off</strong>
        <p>No automatic top-up is enabled in this foundation.</p>
      </section>
    </div>
    <section class="aion-usage-billing-callout">
      <strong>Your local intelligence is free.</strong>
      <p>Tessaris does not charge for your local model, local tokens, private data, reading, reasoning, retries or failed work. Photons apply only to published, verifiable business outcomes.</p>
    </section>`;
  }

  function renderUsage() {
    const trials = activeTrials();
    const content = trials.length ? trials.map((item) => {
      const used = Number(item.verified_actions || 0);
      const limit = Number(item.action_limit || 0);
      const ratio = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
      return `<article class="aion-usage-row"><div><strong>${esc(label(item.department))}</strong><span>${esc(item.state)} · ${used.toLocaleString()} of ${limit.toLocaleString()} verified outcomes</span></div><div class="aion-usage-meter"><i style="width:${ratio}%"></i></div></article>`;
    }).join("") : `<div class="aion-usage-empty">No verified outcome usage is available yet.</div>`;
    return `<section class="aion-usage-billing-panel"><header><div><span>Content-free activity</span><h2>Usage by service</h2></div></header>${content}<p class="aion-usage-note">Private prompts, customer documents and local model-token counts never appear here.</p></section>`;
  }

  function renderLimits() {
    const controls = rows(state.commercial?.controls);
    return `<section class="aion-usage-billing-panel"><header><div><span>Founder controls</span><h2>Limits and overage</h2></div></header>
      ${controls.length ? controls.map((item) => `<article class="aion-usage-limit"><div><strong>${esc(label(item.department))}</strong><span>${esc(Number(item.monthly_action_limit || 0).toLocaleString())} outcomes per month</span></div><b>${item.overage_allowed ? "Approved overage" : "Hard stop"}</b></article>`).join("") : `<div class="aion-usage-empty">No department limits have been published. Automatic overage remains off.</div>`}
      <p class="aion-usage-note">Changing commercial limits requires an authenticated founder action and an immutable approval receipt.</p>
    </section>`;
  }

  function renderBilling() {
    const records = rows(state.billingRecords);
    return `<section class="aion-usage-billing-panel"><header><div><span>Payments</span><h2>Billing and receipts</h2></div></header>
      ${records.length ? records.map((item) => `<article class="aion-usage-limit"><div><strong>${esc(item.receipt_id)}</strong><span>${esc(item.currency)} ${(Number(item.amount_minor || 0) / 100).toFixed(2)} · ${esc(item.provider_state)}${item.disputed_minor ? ` · disputed ${(Number(item.disputed_minor) / 100).toFixed(2)}` : ""}</span></div><b>${item.commercial_hold ? "Review required" : `${esc(Number(item.photons_granted || 0).toLocaleString())} Photons`}</b></article>`).join("") : `<div class="aion-usage-empty"><strong>No signed billing records are connected.</strong><span>The app will show verified payments and downloadable receipts only after this Node has an authenticated Photon billing session.</span></div>`}
      <div class="aion-usage-actions"><button type="button" data-aion-usage-billing-refresh="true">Refresh</button><button type="button" data-aion-usage-billing-export="true" ${records.length ? "" : "disabled"} title="${records.length ? "Export verified billing evidence" : "Available after authenticated billing connection"}">Export receipts</button></div>
      ${state.exportMessage ? `<p class="aion-usage-note">${esc(state.exportMessage)}</p>` : ""}
      <p class="aion-usage-note">Payment cards stay with Revolut. A payment receipt is not presented as a statutory tax invoice unless invoice numbering and tax treatment have passed their release gate.</p>
    </section>`;
  }

  function renderPrivacy() {
    return `<section class="aion-usage-billing-panel"><header><div><span>Billing boundary</span><h2>What Tessaris receives</h2></div></header>
      <div class="aion-usage-privacy-grid">
        <article><b>Received</b><p>Tenant commitment, outcome type, Photon amount, receipt hash, device signature, price-book version and payment identifiers.</p></article>
        <article><b>Never received</b><p>Prompts, conversations, customer documents, file paths, secrets, private keys or local-model token counts.</p></article>
      </div>
      <p class="aion-usage-note">Business data remains in the external Business Vault. Billing records live in the separate content-free control plane.</p>
    </section>`;
  }

  function render(renderSidebar) {
    if (state.section === "business") {
      if (!state.businessLoaded && !state.businessLoading) queueMicrotask(() => loadBusinessConfiguration());
    } else if (!state.loaded && !state.loading) queueMicrotask(() => load());
    const body = state.section === "business" ? renderBusinessConfiguration()
      : state.section === "usage" ? renderUsage()
      : state.section === "limits" ? renderLimits()
      : state.section === "billing" ? renderBilling()
      : state.section === "privacy" ? renderPrivacy()
      : renderOverview();
    return `<div class="surface-shell aion-usage-billing-shell" data-aion-usage-billing="true">
      ${typeof renderSidebar === "function" ? renderSidebar() : ""}
      <main class="aion-usage-billing-main">
        <header class="aion-usage-billing-head"><div><span>SETTINGS · LOCAL BUSINESS CONTROL</span><h1>Settings</h1><p>Manage Vault-backed business configuration, departments, usage and billing.</p></div><button type="button" data-aion-usage-billing-refresh="true">${state.loading || state.businessLoading ? "Refreshing…" : "Refresh"}</button></header>
        ${state.section !== "business" && state.error ? `<div class="aion-usage-billing-error">${esc(state.error)}</div>` : ""}
        ${renderNavigation()}${body}
      </main>
    </div>`;
  }

  function installStyles() {
    if (document.getElementById("aion-usage-billing-styles-v1")) return;
    const style = document.createElement("style");
    style.id = "aion-usage-billing-styles-v1";
    style.textContent = `
      .aion-usage-billing-main{margin-left:64px;padding:34px;min-height:100vh;background:#f7f9fc;color:#111827}.aion-usage-billing-head{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;background:#fff;border:1px solid #dbe4f0;border-top:4px solid #2563eb;border-radius:18px;padding:28px}.aion-usage-billing-head span,.aion-usage-billing-panel header span,.aion-business-configuration-block>div>span{font-size:11px;letter-spacing:.2em;font-weight:900;color:#2563eb}.aion-usage-billing-head h1{font-size:38px;margin:8px 0}.aion-usage-billing-head p{margin:0;color:#64748b}.aion-usage-billing-head button,.aion-usage-actions button,.aion-business-configuration button{border:0;border-radius:10px;background:#2563eb;color:#fff;font-weight:850;padding:11px 18px}.aion-usage-billing-tabs{display:flex;gap:8px;margin:20px 0}.aion-usage-billing-tabs button{border:1px solid #cbd5e1;background:#fff;border-radius:999px;padding:9px 15px;font-weight:800;color:#334155}.aion-usage-billing-tabs button[aria-pressed=true]{border-color:#2563eb;background:#eef5ff;color:#1d4ed8}.aion-usage-billing-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.aion-usage-billing-card,.aion-usage-billing-panel{background:#fff;border:1px solid #dbe4f0;border-radius:16px;padding:20px}.aion-usage-billing-card span{font-size:12px;font-weight:850;color:#64748b}.aion-usage-billing-card strong{display:block;font-size:30px;margin:8px 0}.aion-usage-billing-card p,.aion-usage-note{color:#64748b;margin:0;line-height:1.5}.aion-usage-billing-card.emphasis{background:#eef5ff;border-color:#bfd2fb}.aion-usage-billing-callout{margin-top:14px;background:#ecfdf3;border:1px solid #a7f3d0;border-radius:14px;padding:18px;color:#166534}.aion-usage-billing-callout p{margin:6px 0 0}.aion-usage-billing-panel header h2{margin:6px 0 18px}.aion-usage-row,.aion-usage-limit{display:grid;grid-template-columns:minmax(0,1fr) 240px;gap:18px;align-items:center;padding:14px 0;border-top:1px solid #edf2f7}.aion-usage-row span,.aion-usage-limit span,.aion-usage-empty span{display:block;color:#64748b;margin-top:4px}.aion-usage-meter{height:9px;background:#e2e8f0;border-radius:999px;overflow:hidden}.aion-usage-meter i{display:block;height:100%;background:#2563eb}.aion-usage-limit b{text-align:right;color:#334155}.aion-usage-empty{padding:24px;border:1px dashed #cbd5e1;border-radius:12px;color:#64748b}.aion-usage-privacy-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px}.aion-usage-privacy-grid article{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px}.aion-usage-privacy-grid p{color:#475569;line-height:1.5}.aion-usage-actions{display:flex;gap:10px;margin-top:16px}.aion-usage-actions button:disabled{background:#cbd5e1}.aion-usage-billing-error{margin:14px 0;background:#fff1f2;border:1px solid #fecdd3;color:#9f1239;border-radius:12px;padding:12px}.aion-business-configuration header p,.aion-business-configuration-block p{color:#64748b;line-height:1.5}.aion-business-configuration-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:18px 0 26px}.aion-business-configuration-form div,.aion-business-configuration-form label{display:grid;gap:7px;font-weight:800;color:#334155}.aion-business-configuration input,.aion-business-configuration select,.aion-business-configuration textarea{box-sizing:border-box;width:100%;border:1px solid #cbd5e1;border-radius:10px;padding:11px 12px;font:inherit;color:#111827;background:#fff}.aion-business-configuration-form button{align-self:end}.aion-business-configuration-block{border-top:1px solid #e2e8f0;padding:24px 0 8px}.aion-business-configuration-block h3{margin:6px 0}.aion-business-configuration-block>textarea{margin:12px 0}.aion-business-configuration-block>button{display:block}.aion-business-configuration-form.department{margin-bottom:0}.aion-business-configuration-form .wide{grid-column:1/-1}.aion-business-confirm{display:flex!important;grid-column:1/-1;grid-template-columns:auto 1fr!important;align-items:center}.aion-business-confirm input{width:auto}.aion-business-department-list article{padding:12px 0;border-top:1px solid #edf2f7}.aion-business-department-list article span{display:block;color:#64748b;margin-top:4px}.aion-business-configuration-success{margin:14px 0;background:#ecfdf3;border:1px solid #a7f3d0;color:#166534;border-radius:12px;padding:12px;font-weight:750}@media(max-width:1000px){.aion-usage-billing-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:650px){.aion-usage-billing-main{padding:18px}.aion-usage-billing-head{display:block}.aion-usage-billing-grid,.aion-usage-privacy-grid,.aion-business-configuration-form{grid-template-columns:1fr}.aion-usage-row,.aion-usage-limit{grid-template-columns:1fr}.aion-usage-limit b{text-align:left}.aion-usage-billing-tabs{overflow:auto}}
    `;
    document.head.appendChild(style);
  }

  async function saveBusinessIdentity(form) {
    const values = new FormData(form);
    const payload = {
      trading_name: String(values.get("trading_name") || "").trim(),
      primary_email: String(values.get("primary_email") || "").trim(),
      timezone: String(values.get("timezone") || "").trim(),
      currency: String(values.get("currency") || "").trim(),
      actor_id: "desktop-business-settings",
    };
    const result = await requestJson(
      `/api/aion/business/data/business-identity/${encodeURIComponent(currentTenant())}`,
      { method: "PUT", body: JSON.stringify(payload) },
    );
    state.businessIdentity = result.payload || state.businessIdentity;
    state.businessMessage = "Business settings saved securely in the Business Vault.";
  }

  async function saveBusinessPolicy(form) {
    const values = new FormData(form);
    const value = String(values.get("operating_policy") || "").trim();
    if (!value) throw new Error("Operating policy is required");
    const proposed = await requestJson(
      `/api/aion/business/data/business-map/${encodeURIComponent(currentTenant())}/governance/facts`,
      {
        method: "POST",
        body: JSON.stringify({
          field: "operating_policy",
          value,
          source_ref: "desktop:settings:business-configuration",
          confidence: 1,
          proposed_by: "desktop-business-settings",
          function: "business",
          category: "operating_policy",
          review_owner_id: "founder",
          expected_revision: state.businessMapRevision,
        }),
      },
    );
    const reviewed = await requestJson(
      `/api/aion/business/data/business-map/${encodeURIComponent(currentTenant())}/governance/facts/${encodeURIComponent(proposed.fact.fact_id)}/review`,
      {
        method: "POST",
        body: JSON.stringify({
          action: "approve",
          actor_id: "desktop-business-settings",
          expected_revision: proposed.revision,
          reason: "Founder approved in Business configuration settings",
        }),
      },
    );
    state.businessMapRevision = Number(reviewed.revision || proposed.revision || 0);
    state.businessPolicy = value;
    state.businessMessage = "Operating policy saved with a founder approval receipt.";
  }

  async function createCustomDepartment(form) {
    const values = new FormData(form);
    const result = await requestJson(
      `/api/aion/business/data/custom-departments/${encodeURIComponent(currentTenant())}`,
      {
        method: "POST",
        body: JSON.stringify({
          name: String(values.get("name") || "").trim(),
          template: String(values.get("template") || "").trim(),
          mandate: String(values.get("mandate") || "").trim(),
          actor_id: "desktop-business-settings",
          expected_revision: state.customDepartmentRevision,
          confirm_founder_authority: values.get("confirm_founder_authority") === "on",
        }),
      },
    );
    state.customDepartments = [...state.customDepartments, result.department];
    state.customDepartmentRevision = Number(result.revision || 0);
    state.businessMessage = `${result.department.name} was created in the Business Vault and will survive application updates.`;
    form.reset();
  }

  document.addEventListener("click", (event) => {
    const section = event.target?.closest?.("[data-aion-usage-billing-section]");
    if (section) {
      state.section = String(section.getAttribute("data-aion-usage-billing-section") || "overview");
      renderNow();
      return;
    }
    if (event.target?.closest?.("[data-aion-usage-billing-refresh]")) {
      if (state.section === "business") loadBusinessConfiguration(true);
      else load(true);
      return;
    }
    if (event.target?.closest?.("[data-aion-usage-billing-export]")) {
      const exportRecords = global.aionDesktop?.exportPhotonBillingRecords;
      if (typeof exportRecords !== "function" || !state.billingRecords.length) return;
      state.exportMessage = "Preparing verified receipt export…";
      renderNow();
      exportRecords(state.tenantId).then((result) => {
        state.exportMessage = result?.ok
          ? `${Number(result.record_count || 0).toLocaleString()} verified receipt record(s) exported.`
          : result?.canceled ? "Export cancelled." : "Receipt export is unavailable until billing is securely connected.";
        renderNow();
      }).catch(() => {
        state.exportMessage = "Receipt export is unavailable until billing is securely connected.";
        renderNow();
      });
    }
  }, true);

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    let operation = null;
    if (form.matches("[data-aion-business-identity-form]")) operation = saveBusinessIdentity;
    else if (form.matches("[data-aion-business-policy-form]")) operation = saveBusinessPolicy;
    else if (form.matches("[data-aion-custom-department-form]")) operation = createCustomDepartment;
    if (!operation) return;
    event.preventDefault();
    state.businessError = "";
    state.businessMessage = "Saving…";
    renderNow();
    operation(form).then(() => {
      state.businessError = "";
      renderNow();
    }).catch((error) => {
      state.businessMessage = "";
      state.businessError = String(error?.message || error);
      renderNow();
    });
  }, true);

  installStyles();
  global.AionUsageBillingWorkspace = {
    render,
    load,
    loadBusinessConfiguration,
    /* Signed wallet and receipt state is intentionally not renderer-settable.
       A future authenticated Electron/backend broker must verify authority
       signatures and tenant binding before populating these internal fields. */
    state,
  };
})(window);
