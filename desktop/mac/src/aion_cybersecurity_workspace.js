(function installAionCybersecurityWorkspace(global) {
  "use strict";

  let state = null;
  let loading = false;
  let activeTab = "posture";

  const esc = (value) => String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#039;");

  async function request(path, payload = {}) {
    const target = `/api/aion/business/cybersecurity${path}`;
    const body = JSON.stringify(payload);
    if (!global.aionDesktop?.signAionFlowRequest) throw new Error("The protected desktop security session is unavailable.");
    const headers = await global.aionDesktop.signAionFlowRequest({ method: "POST", target, body, person_id: "desktop_user", workspace_id: "home-fixed" });
    const response = await fetch(`http://127.0.0.1:8080${target}`, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json", ...headers }, body });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || `Security Guard request failed (${response.status})`);
    return result;
  }

  function notify(message, kind = "info") {
    if (global.safeAionDesktopMessage) global.safeAionDesktopMessage(message, kind);
  }

  async function refresh(showError = false) {
    if (loading) return;
    loading = true;
    try {
      state = (await request("/status")).state;
      rerender();
    } catch (error) {
      if (showError) notify(error.message, "error");
    } finally { loading = false; }
  }

  async function safeScan() {
    loading = true; rerender();
    try {
      state = (await request("/scan/safe")).state;
      notify("Safe local security review completed. No configuration was changed.", "success");
    } catch (error) { notify(error.message, "error"); }
    finally { loading = false; rerender(); }
  }

  function badge(value, tone = "blue") {
    return `<span class="acw-badge acw-badge-${tone}">${esc(String(value || "UNKNOWN").replaceAll("_", " "))}</span>`;
  }

  function renderPosture() {
    const findings = state?.findings || [];
    const assets = state?.assets || [];
    const incidents = state?.incidents || [];
    const high = findings.filter((item) => ["HIGH", "CRITICAL"].includes(item.severity)).length;
    const coverage = findings.filter((item) => item.status === "COVERAGE_GAP").length;
    const sentinel = state?.sentinel || { state: "offline" };
    const sentinelTone = sentinel.state === "urgent" ? "red" : sentinel.state === "review" ? "amber" : sentinel.state === "offline" ? "grey" : "blue";
    return `<section class="acw-panel">
      <div class="acw-panel-head"><div><div class="acw-eyebrow">LOCAL SECURITY POSTURE</div><h3>Guard overview</h3><p>Deterministic evidence from this device. A green screen is not a guarantee that no threat exists.</p></div><button class="acw-button acw-primary" data-acw-safe-scan>${loading ? "Reviewing…" : "Run safe local review"}</button></div>
      <div class="acw-sentinel"><div><strong>AION Security Sentinel</strong><span>Independent local guard · continues when the Tessaris window is closed</span></div>${badge(sentinel.state, sentinelTone)}<small>${esc(sentinel.recent_event_count || 0)} recent event(s) · ${esc(sentinel.last_event?.title || sentinel.detail || "No urgent evidence")}</small><button class="acw-button" data-acw-review-complete>Mark review complete</button></div>
      <div class="acw-metrics"><div><strong>${assets.length}</strong><span>Observed assets</span></div><div><strong>${findings.length}</strong><span>Open findings</span></div><div><strong>${high}</strong><span>High / critical</span></div><div><strong>${coverage}</strong><span>Coverage gaps</span></div><div><strong>${incidents.filter((x) => x.status !== "CLOSED").length}</strong><span>Open incidents</span></div></div>
      <div class="acw-boundary"><strong>Guard boundary</strong><span>Read-only collection is available. Active probing, quarantine, blocking, deletion, access changes and service interruption are never automatic.</span></div>
      <div class="acw-grid">
        <article><b>Device &amp; applications</b><span>${esc(state?.capabilities?.device_inventory || "AVAILABLE")}</span><small>Operating system, architecture and bounded application inventory. Licence entitlement remains manual evidence.</small></article>
        <article><b>Network &amp; firewall</b><span>${esc(state?.capabilities?.listening_services || "UNKNOWN")}</span><small>Listening-service and firewall-state observation only.</small></article>
        <article><b>Updates &amp; vulnerabilities</b><span>${esc(state?.capabilities?.vulnerability_feed || "NOT CONFIGURED")}</span><small>A signed vulnerability feed must be configured before CVE claims are shown.</small></article>
        <article><b>Backups</b><span>${esc(state?.capabilities?.backup || "UNKNOWN")}</span><small>Coverage and freshness where the operating system exposes evidence.</small></article>
        <article><b>Attachments &amp; phishing</b><span>${esc(state?.capabilities?.attachment_analysis || "EXPLICIT FILE REQUIRED")}</span><small>Only files deliberately submitted by the user enter analysis.</small></article>
        <article><b>Domains &amp; certificates</b><span>${esc(state?.capabilities?.domain_security || "EXPLICIT TARGET REQUIRED")}</span><small>No background internet probing without a configured business target.</small></article>
      </div>
    </section>`;
  }

  function renderAssets() {
    const assets = state?.assets || [];
    return `<section class="acw-panel"><div class="acw-panel-head"><div><div class="acw-eyebrow">ASSET INVENTORY</div><h3>Devices and observed software</h3><p>Local inventory is evidence for review, not remote-device management.</p></div></div>${assets.length ? `<div class="acw-table"><div class="acw-row acw-row-head"><span>Asset</span><span>Operating system</span><span>Architecture</span><span>Applications</span></div>${assets.map((item) => `<div class="acw-row"><span><strong>${esc(item.display_name)}</strong><small>${esc(item.asset_id)}</small></span><span>${esc(item.operating_system)} ${esc(item.os_release)}</span><span>${esc(item.architecture)}</span><span>${esc(item.application_count)}</span></div>`).join("")}</div>` : `<div class="acw-empty">Run a safe local review to create the first asset record.</div>`}</section>`;
  }

  function renderFindings() {
    const findings = state?.findings || [];
    return `<section class="acw-panel"><div class="acw-panel-head"><div><div class="acw-eyebrow">PRIORITISED FINDINGS</div><h3>Evidence requiring attention</h3><p>Every item names its affected asset, source, confidence and evidence digest.</p></div></div>${findings.length ? `<div class="acw-table"><div class="acw-row acw-findings acw-row-head"><span>Finding</span><span>Asset / source</span><span>Confidence</span><span>Status</span></div>${findings.map((item) => `<div class="acw-row acw-findings"><span><strong>${esc(item.title)}</strong><small>${esc(item.summary)}</small></span><span>${esc(item.affected_asset_id)}<small>${esc(item.source)} · ${esc(String(item.evidence_digest || "").slice(0, 16))}…</small></span><span>${badge(item.severity, ["HIGH","CRITICAL"].includes(item.severity) ? "red" : "blue")}<small>${esc(item.confidence)}</small></span><span>${badge(item.status, item.status === "OPEN" ? "amber" : "grey")}</span></div>`).join("")}</div>` : `<div class="acw-empty">No findings are recorded yet. Run a safe local review; absence of findings is not proof of absence.</div>`}</section>`;
  }

  function renderIncidents() {
    const incidents = state?.incidents || [];
    return `<section class="acw-panel"><div class="acw-panel-head"><div><div class="acw-eyebrow">INCIDENT CONTROL</div><h3>Containment, recovery and verification</h3><p>Incident timelines are append-only. Response actions remain separately approval-gated.</p></div><button class="acw-button" data-acw-new-incident>Open incident</button></div>${incidents.length ? incidents.map((item) => `<article class="acw-incident"><div><strong>${esc(item.title)}</strong><small>${esc(item.summary || "No summary")}</small></div>${badge(item.severity, ["HIGH","CRITICAL"].includes(item.severity) ? "red" : "amber")}${badge(item.status, "blue")}</article>`).join("") : `<div class="acw-empty">No security incidents have been opened.</div>`}</section>`;
  }

  function renderAuthority() {
    const actions = state?.action_proposals || [];
    return `<section class="acw-panel"><div class="acw-panel-head"><div><div class="acw-eyebrow">AUTHORITY &amp; RESPONSE</div><h3>Approval-gated security actions</h3><p>AION may recommend a response. It cannot silently execute a disruptive operation.</p></div><button class="acw-button" data-acw-propose>Propose response</button></div><div class="acw-boundary"><strong>Execution is currently disabled</strong><span>Approval records intent but does not yet invoke a quarantine, firewall or endpoint-response engine.</span></div>${actions.length ? actions.map((item) => `<article class="acw-action"><div><strong>${esc(item.action_type.replaceAll("_", " "))}</strong><span>${esc(item.target)}</span><small>${esc(item.reason)}</small></div>${badge(item.status, "amber")}</article>`).join("") : `<div class="acw-empty">No disruptive response has been proposed.</div>`}</section>`;
  }

  function renderChecks() {
    const attachments = state?.attachment_analyses || [];
    const domains = state?.domain_checks || [];
    const secrets = state?.secret_scans || [];
    const restores = state?.restore_tests || [];
    const updates = state?.update_checks || [];
    return `<section class="acw-panel"><div class="acw-panel-head"><div><div class="acw-eyebrow">EXPLICIT SECURITY CHECKS</div><h3>Run a bounded check</h3><p>These checks run only when selected. Attachments are not retained, secret values are redacted, and domain checks contact only the hostname entered.</p></div></div>
      <div class="acw-check-actions"><button class="acw-button" data-acw-attachment>Analyse attachment</button><button class="acw-button" data-acw-domain>Check domain &amp; TLS</button><button class="acw-button" data-acw-secrets>Scan approved folder for secrets</button><button class="acw-button" data-acw-updates>Check available updates</button><button class="acw-button" data-acw-vulnerabilities ${state?.vulnerability_feed ? "" : "disabled"}>Assess signed vulnerability feed</button><button class="acw-button" data-acw-restore>Record restore test</button></div>
      <div class="acw-grid" style="margin-top:16px">
        <article><b>Signed vulnerability feed</b><span>${esc(state?.capabilities?.vulnerability_feed || "NOT CONFIGURED")}</span><small>${state?.vulnerability_feed ? `${esc(state.vulnerability_feed.feed_id)} · ${esc(state.vulnerability_feed.entry_count)} entries` : "Requires a feed signed by the separately configured Tessaris trust key."}</small></article>
        <article><b>Latest update check</b><span>${updates[0] ? esc(new Date(updates[0].checked_at).toLocaleString()) : "Not run"}</span><small>No update is installed by this check.</small></article>
        <article><b>Latest attachment</b><span>${attachments[0] ? esc(attachments[0].filename) : "Not analysed"}</span><small>${attachments[0] ? `${esc(attachments[0].indicators?.length || 0)} static indicator(s) · content not retained` : "Submit a file deliberately for local static inspection."}</small></article>
        <article><b>Latest domain</b><span>${domains[0] ? esc(domains[0].hostname) : "Not checked"}</span><small>${domains[0] ? `${esc(domains[0].tls_protocol)} · expires ${esc(domains[0].certificate_expires_at || "unknown")} · headers ${domains[0].http_headers_assessed ? "assessed" : "unavailable"}` : "DNS, TLS and public security headers are checked; DNSSEC remains unassessed."}</small></article>
        <article><b>Latest secret scan</b><span>${secrets[0] ? `${esc(secrets[0].match_count)} possible match(es)` : "Not run"}</span><small>${secrets[0] ? `${esc(secrets[0].scanned_files)} files · raw values not retained` : "Only a configured allowed folder can be scanned."}</small></article>
        <article><b>Latest restore test</b><span>${restores[0] ? esc(restores[0].result) : "No evidence"}</span><small>${restores[0] ? esc(restores[0].backup_system) : "Backup existence is not the same as a verified restore."}</small></article>
      </div></section>`;
  }

  function renderRight() {
    if (!state) return `<section class="acw-panel"><div class="acw-empty">${loading ? "Loading Security Guard…" : "Security Guard is ready to load."}</div></section>`;
    return activeTab === "assets" ? renderAssets() : activeTab === "findings" ? renderFindings() : activeTab === "checks" ? renderChecks() : activeTab === "incidents" ? renderIncidents() : activeTab === "authority" ? renderAuthority() : renderPosture();
  }

  function styles() { return `<style>
    .acw-shell{background:#f8fbfd;border-top:4px solid #184f75;color:#142334}.acw-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;padding:22px 20px 18px}.acw-head h2{margin:7px 0 0}.acw-eyebrow{color:#17698a;font-size:10px;letter-spacing:.2em;font-weight:950}.acw-split{display:grid;grid-template-columns:minmax(330px,34fr) 30px minmax(620px,66fr);height:calc(100vh - 190px);min-height:680px;border-top:1px solid #cad8e2;overflow:hidden}.acw-pilot{display:flex;flex-direction:column;min-width:0;padding:20px;background:#f5fafc}.acw-pilot-title{display:flex;justify-content:space-between;gap:10px;padding-bottom:14px;border-bottom:1px solid #bdd4e0}.acw-pilot-thread{flex:1;overflow:auto;padding:18px 0;display:flex;flex-direction:column;gap:12px}.acw-message{max-width:88%;padding:14px 16px;line-height:1.5;background:#eaf4f8;border:1px solid #b7d5e2;border-radius:4px 16px 16px;color:#153e56}.acw-message.user{align-self:flex-end;background:#184f75;color:#fff;border-radius:16px 4px 16px 16px}.acw-form{display:flex;gap:8px;padding-top:13px;border-top:1px solid #bdd4e0}.acw-form textarea{flex:1;padding:10px;border:1px solid #7ca9bd;resize:vertical}.acw-button{border:1px solid #8badbd;background:#fff;color:#184f75;padding:10px 13px;font-weight:850;cursor:pointer}.acw-primary{background:#184f75;color:#fff;border-color:#184f75}.acw-resizer{display:grid;place-items:center;border-left:1px solid #d7e1e8;border-right:1px solid #d7e1e8;background:#f4f7f9}.acw-resizer span{padding:24px 5px;border:1px solid #91b7c8;border-radius:9px;color:#184f75}.acw-work{min-width:0;overflow:auto;background:#f7f9fb}.acw-tabs{display:flex;gap:5px;padding:12px;border-bottom:1px solid #d8e2e8;background:#edf3f6;position:sticky;top:0;z-index:2}.acw-tabs button{border:1px solid #b9cbd5;background:#fff;padding:8px 11px;font-weight:800;cursor:pointer}.acw-tabs button.active{background:#184f75;color:#fff}.acw-content{padding:14px}.acw-panel{border:1px solid #cbd9e2;border-top:4px solid #2d83aa;background:#fff;padding:20px}.acw-panel-head{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;padding-bottom:15px;border-bottom:1px solid #dce5ea}.acw-panel-head h3{margin:5px 0}.acw-panel-head p{margin:0;color:#64748b;line-height:1.45}.acw-sentinel{display:grid;grid-template-columns:1fr auto;gap:4px 14px;align-items:center;margin:16px 0;padding:13px 15px;border:1px solid #a9c9d8;background:#f3f9fc}.acw-sentinel div{display:grid;gap:3px}.acw-sentinel span,.acw-sentinel small{color:#64748b}.acw-sentinel small{grid-column:1/-1}.acw-metrics{display:grid;grid-template-columns:repeat(5,minmax(110px,1fr));gap:10px;margin:16px 0}.acw-metrics div{border:1px solid #d5e0e6;padding:14px}.acw-metrics strong{display:block;font-size:25px}.acw-metrics span{color:#64748b;font-size:11px}.acw-boundary{display:flex;gap:14px;padding:14px;border-left:4px solid #d28a24;background:#fff9ef;margin:14px 0}.acw-boundary span{color:#6b7280}.acw-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.acw-grid article{border:1px solid #d6e1e7;padding:14px;display:grid;gap:6px}.acw-grid article span,.acw-grid article small{color:#64748b}.acw-table{margin-top:14px;border:1px solid #d7e1e7}.acw-row{display:grid;grid-template-columns:2fr 1.2fr 1fr .8fr;gap:12px;padding:13px;border-bottom:1px solid #d7e1e7;align-items:center}.acw-row:last-child{border-bottom:0}.acw-row span{min-width:0}.acw-row small{display:block;color:#64748b;margin-top:4px;overflow-wrap:anywhere}.acw-row-head{background:#eef3f6;color:#53697b;font-size:10px;font-weight:900;letter-spacing:.1em;text-transform:uppercase}.acw-badge{display:inline-block;padding:4px 6px;border:1px solid;font-size:9px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}.acw-badge-red{color:#9f2f2f;border-color:#e0aaaa;background:#fff5f5}.acw-badge-amber{color:#8a5a11;border-color:#e6c98f;background:#fffaf0}.acw-badge-blue{color:#184f75;border-color:#a9c9d8;background:#f3f9fc}.acw-badge-grey{color:#596674;border-color:#cbd5dc;background:#f7f9fa}.acw-empty{padding:30px;text-align:center;color:#64748b}.acw-incident,.acw-action{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:14px;border-bottom:1px solid #d9e3e8}.acw-incident small,.acw-action small,.acw-action span{display:block;color:#64748b;margin-top:4px}.acw-status{border:1px solid #9fbcca;padding:7px 9px;font-size:9px;font-weight:900;letter-spacing:.1em;text-transform:uppercase}.acw-help{margin-top:12px;border:1px solid #a9c9d8;background:#fff;border-radius:10px}.acw-help summary{cursor:pointer;padding:11px 13px;font-weight:800}.acw-help div{padding:0 13px 12px;color:#64748b;font-size:11px;line-height:1.5}.acw-form button{border:0;background:#184f75;color:#fff;padding:10px 14px;font-weight:900;cursor:pointer}.acw-check-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
    .acw-shell{--acw-blue:#2563eb;--acw-navy:#14213d;--acw-soft:#eef5ff;--acw-page:#f7f9fc;--acw-line:#d9e2ec;background:var(--acw-page);border-top-color:var(--acw-blue);color:var(--acw-navy);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.acw-eyebrow{color:var(--acw-blue)}.acw-status{border:1px solid #bfd2fb;border-radius:999px;background:var(--acw-soft);color:var(--acw-blue);padding:7px 10px}.acw-split{border:1px solid var(--acw-line);border-radius:18px;box-shadow:0 1px 2px rgba(11,23,57,.04);overflow:hidden}.acw-pilot{background:#fbfcfe}.acw-pilot-title,.acw-form{border-color:var(--acw-line)}.acw-help{border-color:var(--acw-line);border-radius:12px}.acw-message{border-color:#c8d8fb;background:var(--acw-soft);color:var(--acw-navy);border-radius:16px 16px 16px 4px}.acw-message.user{background:var(--acw-navy);border-color:var(--acw-navy);border-radius:16px 16px 4px 16px}.acw-form{padding:7px;border:1px solid var(--acw-line);border-radius:17px;background:#fff}.acw-form:focus-within{border-color:var(--acw-blue);box-shadow:0 0 0 3px rgba(37,99,235,.12)}.acw-form textarea{border:0;border-radius:12px;outline:0;resize:none}.acw-form button,.acw-button{border-radius:12px}.acw-form button,.acw-primary{background:var(--acw-blue);border-color:var(--acw-blue)}.acw-resizer{border-color:var(--acw-line);background:var(--acw-page)}.acw-resizer span{border-color:#bfd2fb;background:var(--acw-soft);color:var(--acw-blue)}.acw-work{background:var(--acw-page)}.acw-tabs{border-color:var(--acw-line);background:#fff}.acw-tabs button{border-color:var(--acw-line);border-radius:10px;color:#475569}.acw-tabs button.active{border-color:var(--acw-blue);background:var(--acw-soft);color:var(--acw-blue)}.acw-panel{border-color:var(--acw-line);border-top-color:var(--acw-blue);border-radius:14px}.acw-sentinel,.acw-metrics div,.acw-grid article,.acw-table{border-color:var(--acw-line);border-radius:12px}.acw-row-head{background:#f2f5f9}.acw-badge-blue{color:var(--acw-blue);border-color:#bfd2fb;background:var(--acw-soft)}
    @media(max-width:1180px){.acw-split{display:block;height:auto;overflow:auto}.acw-resizer{display:none}.acw-pilot,.acw-work{min-height:650px}.acw-metrics{grid-template-columns:repeat(2,1fr)}}
  </style>`; }

  function render() {
    if (!state && !loading) setTimeout(() => refresh(false), 0);
    return `${styles()}<section class="acw-shell" data-aion-cybersecurity-workspace>
      <header class="acw-head"><div><div class="acw-eyebrow">PILOT · CYBERSECURITY COMMAND CENTRE</div><h2>Cybersecurity coordination</h2></div><span class="acw-status">Local-first · approval gated</span></header>
      <div class="acw-split"><section class="acw-pilot"><div class="acw-pilot-title"><div><strong>Security Pilot</strong><div style="color:#64748b;font-size:12px;margin-top:3px">Local evidence, investigation and response adviser</div></div><span class="acw-status">Read-only guard</span></div>
      <details class="acw-help"><summary>What can I ask Security Pilot to do? ＋</summary><div>Ask it to explain findings, review coverage, build an incident timeline or propose a controlled response. AION is an evidence-grounded coordinator, not a certification authority, and cannot silently take disruptive action.</div></details>
      <div class="acw-pilot-thread" data-acw-thread><div class="acw-message"><strong style="display:block;font-size:10px;letter-spacing:.1em;margin-bottom:5px">SECURITY PILOT</strong>I can review local guard evidence, show what is covered and what is not, and prepare an approval-gated response. Run the safe local review to establish the first evidence snapshot.</div></div>
      <form class="acw-form" data-acw-form><textarea rows="2" data-acw-input placeholder="Ask Security Pilot about this device…"></textarea><button type="submit">Send</button></form></section>
      <div class="acw-resizer"><span>⋮<br>⋮</span></div><section class="acw-work"><nav class="acw-tabs">${[["posture","Posture"],["assets","Assets"],["findings","Findings"],["checks","Checks"],["incidents","Incidents"],["authority","Authority"]].map(([key,label]) => `<button data-acw-tab="${key}" class="${activeTab===key?"active":""}">${label}</button>`).join("")}</nav><div class="acw-content">${renderRight()}</div></section></div></section>`;
  }

  function rerender() {
    const root = document.querySelector("[data-aion-cybersecurity-workspace]");
    if (!root) return;
    const holder = document.createElement("div"); holder.innerHTML = render();
    root.replaceWith(holder.firstElementChild);
  }

  document.addEventListener("click", async (event) => {
    const tab = event.target.closest?.("[data-acw-tab]");
    if (tab) { activeTab = tab.dataset.acwTab; rerender(); return; }
    if (event.target.closest?.("[data-acw-safe-scan]")) { await safeScan(); return; }
    if (event.target.closest?.("[data-acw-review-complete]")) {
      try { await request("/sentinel/review-complete"); notify("Sentinel review marked complete.", "success"); await refresh(true); } catch (error) { notify(error.message, "error"); }
      return;
    }
    if (event.target.closest?.("[data-acw-new-incident]")) {
      const title = prompt("Incident title"); if (!title) return;
      const summary = prompt("What happened? Record facts only.") || "";
      try { await request("/incidents", { title, severity: "MEDIUM", summary }); await refresh(true); } catch (error) { notify(error.message, "error"); }
    }
    if (event.target.closest?.("[data-acw-propose]")) {
      const action_type = prompt("Response type: quarantine_file, block_address, change_firewall, stop_process, stop_service, revoke_access or isolate_device"); if (!action_type) return;
      const target = prompt("Exact target") || ""; const reason = prompt("Evidence-based reason") || "";
      try { await request("/actions/propose", { action_type, target, reason }); await refresh(true); } catch (error) { notify(error.message, "error"); }
    }
    if (event.target.closest?.("[data-acw-updates]")) {
      try { notify("Checking update availability. Nothing will be installed."); await request("/updates/check"); await refresh(true); } catch (error) { notify(error.message, "error"); }
    }
    if (event.target.closest?.("[data-acw-vulnerabilities]")) {
      try { await request("/vulnerabilities/assess"); await refresh(true); } catch (error) { notify(error.message, "error"); }
    }
    if (event.target.closest?.("[data-acw-domain]")) {
      const hostname = prompt("Business domain to check (for example, example.com)"); if (!hostname) return;
      try { await request("/domains/check", { hostname, port: 443 }); await refresh(true); } catch (error) { notify(error.message, "error"); }
    }
    if (event.target.closest?.("[data-acw-secrets]")) {
      const scope = prompt("Exact approved folder to scan. Values are redacted and only configured roots are allowed."); if (!scope) return;
      try { await request("/secrets/scan", { scope, maximum_files: 2000 }); await refresh(true); } catch (error) { notify(error.message, "error"); }
    }
    if (event.target.closest?.("[data-acw-restore]")) {
      const backup_system = prompt("Backup system used"); if (!backup_system) return;
      const result = (prompt("Restore result: PASSED, PARTIAL or FAILED", "PASSED") || "").toUpperCase();
      const evidence_reference = prompt("Evidence reference, ticket or saved report") || ""; if (!evidence_reference) return;
      try { await request("/backups/restore-tests", { backup_system, tested_at: new Date().toISOString(), result, evidence_reference, notes: "" }); await refresh(true); } catch (error) { notify(error.message, "error"); }
    }
    if (event.target.closest?.("[data-acw-attachment]")) {
      const input = document.createElement("input"); input.type = "file"; input.style.display = "none";
      input.addEventListener("change", async () => {
        const file = input.files?.[0]; input.remove(); if (!file) return;
        if (file.size > 25 * 1024 * 1024) { notify("Attachments are limited to 25 MB.", "error"); return; }
        try {
          const data_base64 = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onerror = () => reject(reader.error); reader.onload = () => resolve(String(reader.result || "").split(",", 2)[1] || ""); reader.readAsDataURL(file); });
          await request("/attachments/analyse", { filename: file.name, media_type: file.type || "application/octet-stream", data_base64 }); await refresh(true);
        } catch (error) { notify(error.message, "error"); }
      }, { once: true });
      document.body.appendChild(input); input.click();
    }
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest?.("[data-acw-form]"); if (!form) return;
    event.preventDefault(); const input = form.querySelector("[data-acw-input]"); const question = String(input?.value || "").trim(); if (!question) return;
    const thread = form.closest(".acw-pilot")?.querySelector("[data-acw-thread]");
    thread?.insertAdjacentHTML("beforeend", `<div class="acw-message user"><strong style="display:block;font-size:10px;letter-spacing:.1em;margin-bottom:5px">YOU</strong>${esc(question)}</div>`); input.value = "";
    try {
      const result = await request("/investigate", { question });
      const evidence = result.investigation;
      let answer = evidence.answer;
      if (typeof global.aionOperationsConversationRequest === "function") {
        try {
          const aion = await global.aionOperationsConversationRequest("turn", {
            department_id: "cybersecurity",
            user_text: `${question}\n\nVerified local guard context: ${evidence.answer}\nFinding IDs: ${(evidence.finding_ids || []).join(", ") || "none"}. Stay within this evidence, identify unknowns, and do not execute or imply approval for any response action.`,
            attachments: [],
          });
          answer = aion?.conversation?.turn?.content || aion?.history?.turns?.slice(-1)?.[0]?.content || answer;
          answer = `${answer}\n\nEvidence boundary: ${evidence.answer}`;
        } catch { /* Deterministic guard summary remains the fail-closed answer. */ }
      }
      thread?.insertAdjacentHTML("beforeend", `<div class="acw-message"><strong style="display:block;font-size:10px;letter-spacing:.1em;margin-bottom:5px">SECURITY PILOT</strong>${esc(answer).replace(/\n/g, "<br>")}</div>`);
      thread.scrollTop = thread.scrollHeight;
    } catch (error) { notify(error.message, "error"); }
  });

  global.AionCybersecurityWorkspace = { render, refresh };

  // This is intentionally a safe-read-only heartbeat. It runs while the Tessaris
  // desktop runtime is active and never invokes the approval-gated response path.
  if (!global.__aionCybersecurityGuardTimer) {
    global.setTimeout(async () => {
      try { state = (await request("/scan/safe")).state; rerender(); } catch {}
    }, 20 * 1000);
    global.__aionCybersecurityGuardTimer = global.setInterval(async () => {
      try {
        const result = await request("/scan/safe");
        state = result.state;
        rerender();
      } catch { /* Backend/offline state is shown when the workspace is opened. */ }
    }, 30 * 60 * 1000);
  }
})(window);
