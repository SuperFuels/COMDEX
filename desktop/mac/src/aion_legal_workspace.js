(function installAionLegalWorkspace(global) {
  "use strict";

  const STORAGE_KEY = "aion.legal.workspace.v1";
  const DEFAULT_STATE = {
    activeTab: "cases",
    cases: [],
    documents: [],
    signatures: [],
  };
  let signingEnvelopes = null;
  let signingLoading = false;
  let deliveryOutbox = { items: [], counts: {}, all_required_parties_confirmed: false };
  let legalMatters = null;
  let matterLoading = false;
  let legalDocuments = null;
  let documentLoading = false;
  let legalTemplates = null;
  let templateLoading = false;

  async function signingRequest(path, payload = {}) {
    const target = `/api/aion/business/legal-signing${path}`;
    const body = JSON.stringify(payload);
    if (!global.aionDesktop?.signAionFlowRequest) throw new Error("The protected desktop signing session is unavailable.");
    const headers = await global.aionDesktop.signAionFlowRequest({ method: "POST", target, body, person_id: "desktop_user", workspace_id: "home-fixed" });
    const response = await fetch(`http://127.0.0.1:8080${target}`, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json", ...headers }, body });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || `Signing request failed (${response.status})`);
    return result;
  }

  async function downloadEvidencePackage(envelopeId) {
    const path = `/envelopes/${encodeURIComponent(envelopeId)}/evidence-package/download`;
    const target = `/api/aion/business/legal-signing${path}`;
    const body = "{}";
    if (!global.aionDesktop?.signAionFlowRequest) throw new Error("The protected desktop signing session is unavailable.");
    const headers = await global.aionDesktop.signAionFlowRequest({ method: "POST", target, body, person_id: "desktop_user", workspace_id: "home-fixed" });
    const response = await fetch(`http://127.0.0.1:8080${target}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/zip", ...headers },
      body,
    });
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.detail || `Evidence download failed (${response.status})`);
    }
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match?.[1] || `${envelopeId}.tessaris-evidence.zip`;
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    return filename;
  }

  async function downloadMatterExport(matterId) {
    const path = `/matters/${encodeURIComponent(matterId)}/export`;
    const target = `/api/aion/business/legal-signing${path}`;
    const body = "{}";
    if (!global.aionDesktop?.signAionFlowRequest) throw new Error("The protected desktop signing session is unavailable.");
    const headers = await global.aionDesktop.signAionFlowRequest({ method: "POST", target, body, person_id: "desktop_user", workspace_id: "home-fixed" });
    const response = await fetch(`http://127.0.0.1:8080${target}`, {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json", ...headers }, body,
    });
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.detail || `Matter export failed (${response.status})`);
    }
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match?.[1] || `${matterId}.tessaris-legal-matter.json`;
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
    return filename;
  }

  async function refreshSigningEnvelopes(showError = false) {
    if (signingLoading) return;
    signingLoading = true;
    try {
      const result = await signingRequest("/list");
      signingEnvelopes = Array.isArray(result.envelopes) ? result.envelopes : [];
      const delivery = await signingRequest("/delivery-outbox/status");
      deliveryOutbox = delivery.outbox || { items: [], counts: {}, all_required_parties_confirmed: false };
      rerender();
    } catch (error) {
      if (showError) global.safeAionDesktopMessage?.(error.message, "error");
    } finally { signingLoading = false; }
  }

  async function refreshLegalMatters(showError = false) {
    if (matterLoading) return;
    matterLoading = true;
    try {
      const result = await signingRequest("/matters/list");
      legalMatters = Array.isArray(result.matters) ? result.matters : [];
      rerender();
    } catch (error) {
      if (showError) global.safeAionDesktopMessage?.(error.message, "error");
    } finally { matterLoading = false; }
  }

  async function refreshLegalDocuments(showError = false) {
    if (documentLoading) return;
    documentLoading = true;
    try {
      const result = await signingRequest("/documents/list");
      legalDocuments = Array.isArray(result.documents) ? result.documents : [];
      rerender();
    } catch (error) {
      if (showError) global.safeAionDesktopMessage?.(error.message, "error");
    } finally { documentLoading = false; }
  }

  async function refreshLegalTemplates(showError = false) {
    if (templateLoading) return;
    templateLoading = true;
    try {
      const result = await signingRequest("/templates/list");
      legalTemplates = Array.isArray(result.templates) ? result.templates : [];
      rerender();
    } catch (error) {
      if (showError) global.safeAionDesktopMessage?.(error.message, "error");
    } finally { templateLoading = false; }
  }

  function chooseLegalDocument() {
    return new Promise((resolve) => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".txt,.md,.csv,.pdf,.docx,.png,.jpg,.jpeg,.tif,.tiff";
      input.style.display = "none";
      input.addEventListener("change", () => { const file = input.files?.[0] || null; input.remove(); resolve(file); }, { once: true });
      document.body.appendChild(input);
      input.click();
    });
  }

  function fileBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(reader.error || new Error("The selected document could not be read."));
      reader.onload = () => resolve(String(reader.result || "").split(",", 2)[1] || "");
      reader.readAsDataURL(file);
    });
  }

  async function secureUploadFile(file, matterId = "") {
    if (!file) return null;
    if (file.size > 25 * 1024 * 1024) throw new Error("Legal documents are limited to 25 MB.");
    const extension = String(file.name).split(".").pop().toLowerCase();
    const mimeByExtension = { txt: "text/plain", md: "text/plain", csv: "text/plain", pdf: "application/pdf", docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", tif: "image/tiff", tiff: "image/tiff" };
    const result = await signingRequest("/documents", {
      filename: file.name, media_type: file.type || mimeByExtension[extension] || "application/octet-stream",
      data_base64: await fileBase64(file), matter_id: String(matterId || ""),
    });
    await refreshLegalDocuments();
    return result.document;
  }

  async function selectAndUploadDocument(matterId = "") {
    const file = await chooseLegalDocument();
    return file ? secureUploadFile(file, matterId) : null;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function readState() {
    try {
      const value = JSON.parse(global.localStorage?.getItem(STORAGE_KEY) || "null");
      return value && typeof value === "object" ? { ...DEFAULT_STATE, ...value } : { ...DEFAULT_STATE };
    } catch {
      return { ...DEFAULT_STATE };
    }
  }

  function writeState(next) {
    try { global.localStorage?.setItem(STORAGE_KEY, JSON.stringify(next)); } catch {}
    return next;
  }

  function metric(value, label) {
    return `<div class="alw-metric"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`;
  }

  function renderCases(state) {
    const matters = Array.isArray(legalMatters) ? legalMatters : state.cases;
    return `
      <section class="alw-panel">
        <div class="alw-panel-head"><div><div class="alw-eyebrow">MATTERS &amp; INTAKE</div><h3>Open legal matters</h3><p>Emails, complaints, negotiations and documents enter one evidence-backed matter.</p></div><button class="alw-button alw-button-primary" data-aion-legal-new-case>+ New matter</button></div>
        ${matters.length ? `<div class="alw-table"><div class="alw-row alw-row-head"><span>Matter</span><span>Type / law</span><span>Risk</span><span>Status / records</span></div>${matters.map((item) => `<button class="alw-row" data-aion-legal-case="${escapeHtml(item.matter_id || item.id)}"><span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.counterparty || "No counterparty")}</small></span><span>${escapeHtml(item.matter_type || item.type)}<small>${escapeHtml(item.jurisdiction?.governing_law || "Jurisdiction not migrated")}</small></span><span><b class="alw-risk alw-risk-${escapeHtml(String(item.risk || "normal").toLowerCase())}">${escapeHtml(item.risk)}</b></span><span>${escapeHtml(item.status)}<small>${item.records_governance?.legal_hold ? "LEGAL HOLD" : "Manage retention →"}</small></span></button>`).join("")}</div>` : `<div class="alw-empty"><strong>No open matters</strong><span>Create a matter or upload an email, agreement, complaint letter or other legal evidence.</span></div>`}
      </section>`;
  }

  function renderDocuments(state) {
    const documents = Array.isArray(legalDocuments) ? legalDocuments : [];
    return `
      <section class="alw-panel">
        <div class="alw-panel-head"><div><div class="alw-eyebrow">LEGAL LIBRARY</div><h3>Documents &amp; correspondence</h3><p>Originals and extracted text are encrypted locally. OCR and category suggestions never leave this device and always require human review.</p></div><button class="alw-button alw-button-primary" data-aion-legal-upload>Secure upload</button></div>
        ${documents.length ? `<div class="alw-table"><div class="alw-row alw-row-head"><span>Document</span><span>Suggested category</span><span>Extraction / review</span><span>Updated</span></div>${documents.map((item) => `<div class="alw-row"><span><strong>${escapeHtml(item.filename)}</strong><small>SHA-256 ${escapeHtml(String(item.content_sha256 || "").slice(0,16))}… · encrypted original</small></span><span>${escapeHtml(item.classification?.confirmed_category || item.classification?.suggested_category || "OTHER")}<small>${item.classification?.confirmed_category ? "Human confirmed" : "Automated suggestion only"}</small></span><span><b class="alw-status">${escapeHtml(item.extraction?.status || "UNKNOWN")}</b><small>${escapeHtml(item.review_status || "REVIEW_REQUIRED")}</small></span><span>${escapeHtml(new Date(item.updated_at).toLocaleDateString("en-GB"))}<small><button class="alw-mini" data-aion-legal-document-review="${escapeHtml(item.document_id)}">Review</button></small></span></div>`).join("")}</div>` : `<div class="alw-empty"><strong>${documentLoading ? "Loading protected documents…" : "No saved legal documents"}</strong><span>Upload received terms, a contract, complaint letter, privacy policy or other legal evidence.</span></div>`}
      </section>`;
  }

  function renderTemplates() {
    const templates = Array.isArray(legalTemplates) ? legalTemplates : [];
    return `
      <section class="alw-panel">
        <div class="alw-panel-head"><div><div class="alw-eyebrow">CONTROLLED DRAFTING</div><h3>Approved template library</h3><p>Only an exact version approved by a named qualified reviewer can produce a controlled draft. Tessaris does not label generic or AI-written wording as legally approved.</p></div><button class="alw-button alw-button-primary" data-aion-legal-new-template>+ New draft template</button></div>
        ${templates.length ? `<div class="alw-table"><div class="alw-row alw-row-head"><span>Template / version</span><span>Type / jurisdiction</span><span>Approval</span><span>Action</span></div>${templates.map((item) => `<div class="alw-row"><span><strong>${escapeHtml(item.title)}</strong><small>Version ${escapeHtml(item.version)} · ${escapeHtml(String(item.content_sha256 || "").slice(0,16))}…</small></span><span>${escapeHtml(String(item.template_type || "").replaceAll("_", " "))}<small>${escapeHtml(item.jurisdiction?.governing_law || "Not recorded")}</small></span><span><b class="alw-status">${escapeHtml(item.status)}</b><small>${item.approval ? `${escapeHtml(item.approval.reviewer_name)} · review due ${escapeHtml(item.approval.review_due_at ? new Date(item.approval.review_due_at).toLocaleDateString("en-GB") : "not scheduled")}` : "Qualified review required"}</small></span><span><button class="alw-mini" data-aion-legal-template-open="${escapeHtml(item.template_id)}">Open</button></span></div>`).join("")}</div>` : `<div class="alw-empty"><strong>${templateLoading ? "Loading protected templates…" : "No approved templates yet"}</strong><span>Create a draft structure, then have a qualified reviewer approve the exact version for its stated jurisdiction and use. No legal wording is pre-approved by Tessaris.</span></div>`}
      </section>`;
  }

  function renderSignatures(state) {
    const envelopes = Array.isArray(signingEnvelopes) ? signingEnvelopes : [];
    const actions = (item) => {
      if (item.status === "DRAFT") return `<button class="alw-mini" data-aion-legal-envelope-action="submit" data-envelope-id="${escapeHtml(item.envelope_id)}">Submit for approval</button>`;
      if (item.status === "PENDING_APPROVAL") return `<button class="alw-mini" data-aion-legal-envelope-action="approve" data-envelope-id="${escapeHtml(item.envelope_id)}" data-review-hash="${escapeHtml(item.approval?.review_hash || "")}">Review &amp; approve</button>`;
      if (item.status === "APPROVED") return `<button class="alw-mini alw-mini-primary" data-aion-legal-envelope-action="issue" data-envelope-id="${escapeHtml(item.envelope_id)}">Create secure links</button>`;
      if (["ISSUED","IN_PROGRESS"].includes(item.status)) { const signer = (item.signers || []).find((value) => value.status === "PENDING"); return signer ? `<button class="alw-mini" data-aion-legal-envelope-action="remind" data-envelope-id="${escapeHtml(item.envelope_id)}" data-signer-id="${escapeHtml(signer.signer_id)}">Prepare reminder link</button>` : ""; }
      if (item.status === "COMPLETED") {
        const deliveryItems = (deliveryOutbox.items || []).filter((delivery) => delivery.envelope_id === item.envelope_id);
        const deliveredCount = deliveryItems.filter((delivery) => delivery.status === "DELIVERED").length;
        const submitted = deliveryItems.find((delivery) => delivery.status === "SUBMITTED_TO_PROVIDER");
        const failedDelivery = deliveryItems.find((delivery) => ["BOUNCED", "REJECTED"].includes(delivery.status));
        const readyToSend = deliveryItems.some((delivery) => ["APPROVED_PENDING", "RETRY_PENDING"].includes(delivery.status));
        const proof = item.glyphchain_proof || {};
        const proofControl = proof.status === "FINALIZED"
          ? `<span class="alw-chain">GLYPHCHAIN FINAL · BLOCK ${escapeHtml(proof.block_height || "—")}</span><button class="alw-mini" data-aion-legal-envelope-action="glyphchain-verify" data-envelope-id="${escapeHtml(item.envelope_id)}">Verify proof</button>`
          : proof.status === "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"
            ? `<span class="alw-chain alw-chain-pending">LEDGER COMMITTED · QUORUM FINALITY PENDING</span><button class="alw-mini" data-aion-legal-envelope-action="glyphchain-submit" data-envelope-id="${escapeHtml(item.envelope_id)}">Check finality</button>`
          : `<span class="alw-chain alw-chain-pending">${escapeHtml(proof.status || "PROOF READY")}</span><button class="alw-mini" data-aion-legal-envelope-action="glyphchain-submit" data-envelope-id="${escapeHtml(item.envelope_id)}">Record on GlyphChain</button>`;
        const deliveryControl = !deliveryItems.length
          ? `<button class="alw-mini" data-aion-legal-envelope-action="delivery-prepare" data-envelope-id="${escapeHtml(item.envelope_id)}">Prepare approved delivery</button>`
          : readyToSend
            ? `<span class="alw-chain">DELIVERY QUEUED · ${escapeHtml(deliveredCount)}/${escapeHtml(item.signers.length)} CONFIRMED</span><button class="alw-mini" data-aion-legal-envelope-action="delivery-send" data-envelope-id="${escapeHtml(item.envelope_id)}">Send queued copies</button>`
            : submitted
              ? `<span class="alw-chain">PROVIDER ACCEPTED · DELIVERY NOT YET CONFIRMED</span><button class="alw-mini" data-aion-legal-envelope-action="delivery-confirm" data-envelope-id="${escapeHtml(item.envelope_id)}" data-delivery-id="${escapeHtml(submitted.delivery_id)}">Record provider outcome</button>`
              : failedDelivery
                ? `<span class="alw-chain alw-chain-pending">${escapeHtml(failedDelivery.status)} · ${escapeHtml(deliveredCount)}/${escapeHtml(item.signers.length)} CONFIRMED</span><button class="alw-mini" data-aion-legal-envelope-action="delivery-retry" data-envelope-id="${escapeHtml(item.envelope_id)}" data-delivery-id="${escapeHtml(failedDelivery.delivery_id)}">Authorize retry</button>`
              : deliveredCount === item.signers.length
                ? `<span class="alw-sealed">COPIES DELIVERED · ${escapeHtml(deliveredCount)}/${escapeHtml(item.signers.length)}</span>`
                : `<span class="alw-chain alw-chain-pending">DELIVERY NEEDS ATTENTION · ${escapeHtml(deliveredCount)}/${escapeHtml(item.signers.length)} CONFIRMED</span>`;
        const replacementControl = item.lifecycle?.superseded_by_envelope_id
          ? `<span class="alw-chain">SUPERSEDED</span>`
          : `<button class="alw-mini" data-aion-legal-envelope-action="replacement" data-envelope-id="${escapeHtml(item.envelope_id)}">Prepare replacement</button>`;
        return `<div class="alw-proof-actions"><span class="alw-sealed">SEALED · ${escapeHtml(String(item.signed_copy?.manifest_hash || "").slice(0,12))}…</span><button class="alw-mini alw-mini-primary" data-aion-legal-envelope-action="evidence-download" data-envelope-id="${escapeHtml(item.envelope_id)}">Download evidence</button><button class="alw-mini" data-aion-legal-envelope-action="history" data-envelope-id="${escapeHtml(item.envelope_id)}">Verify history</button>${replacementControl}${proofControl}${deliveryControl}</div>`;
      }
      return "";
    };
    return `
      <section class="alw-panel">
        <div class="alw-panel-head"><div><div class="alw-eyebrow">SIGN &amp; SHARE</div><h3>Controlled signature envelopes</h3><p>Immutable versions, signer verification, ordered signing, expiring secure links and tamper-evident history. Approved delivery uses an encrypted retry queue; provider acceptance is not shown as delivered until a delivery result is confirmed.</p></div><div style="display:flex;gap:7px;"><button class="alw-button" data-aion-legal-refresh-signatures>Refresh</button><button class="alw-button alw-button-primary" data-aion-legal-new-envelope>Prepare signature request</button></div></div>
        ${envelopes.length ? `<div class="alw-table"><div class="alw-row alw-row-head alw-sign-row"><span>Envelope</span><span>Signers</span><span>Status</span><span>Evidence / action</span></div>${envelopes.map((item) => `<div class="alw-row alw-sign-row"><span><strong>${escapeHtml(item.title)}</strong><small>Version ${escapeHtml(item.document?.version || 1)} · ${escapeHtml(String(item.document?.content_hash || "").slice(0,12))}…</small></span><span><strong>${escapeHtml((item.signers || []).map((signer) => signer.name).join(", "))}</strong><small>${escapeHtml((item.signers || []).map((signer) => `${signer.order}. ${signer.status}`).join(" · "))}</small></span><span><b class="alw-status">${escapeHtml(item.status)}</b><small>${item.records_governance?.legal_hold ? "LEGAL HOLD" : `Expires ${escapeHtml(new Date(item.expires_at).toLocaleDateString("en-GB"))}`}</small></span><span>${actions(item)}<button class="alw-mini" data-aion-legal-envelope-timeline="${escapeHtml(item.envelope_id)}">Timeline &amp; proof cabinet</button><button class="alw-mini" data-aion-legal-records-kind="envelope" data-record-id="${escapeHtml(item.envelope_id)}">Records controls</button></span></div>`).join("")}</div>` : `<div class="alw-empty"><strong>${signingLoading ? "Loading signature requests…" : "No signature requests"}</strong><span>Prepare a customer quote acceptance, contractor agreement or other approved document for signature.</span></div>`}
      </section>`;
  }

  function renderPolicies() {
    return `
      <section class="alw-panel">
        <div class="alw-panel-head"><div><div class="alw-eyebrow">BUSINESS TERMS &amp; POLICIES</div><h3>Published and working documents</h3><p>Keep the business's controlling terms visible so Legal Pilot can compare new issues against the correct version.</p></div><button class="alw-button" data-aion-legal-upload>+ Add policy</button></div>
        <div class="alw-policy-grid">
          ${[["Terms & conditions","Not added"],["Privacy notice","Not added"],["Cookie notice","Not added"],["Employee handbook","Not added"],["Supplier terms","Not added"],["Complaints policy","Not added"]].map(([name,status]) => `<button class="alw-policy" data-aion-legal-upload><span>POLICY</span><strong>${name}</strong><small>${status}</small></button>`).join("")}
        </div>
      </section>`;
  }

  function render() {
    const state = readState();
    if (legalMatters === null && !matterLoading) queueMicrotask(() => { void refreshLegalMatters(false); });
    if (legalDocuments === null && !documentLoading) queueMicrotask(() => { void refreshLegalDocuments(false); });
    if (legalTemplates === null && !templateLoading) queueMicrotask(() => { void refreshLegalTemplates(false); });
    if (state.activeTab === "signatures" && signingEnvelopes === null && !signingLoading) {
      global.setTimeout(() => { void refreshSigningEnvelopes(); }, 0);
    }
    const openCases = state.cases.filter((item) => item.status !== "Closed").length;
    const urgent = state.cases.filter((item) => item.risk === "high").length;
    const envelopeRows = Array.isArray(signingEnvelopes) ? signingEnvelopes : [];
    const waiting = envelopeRows.filter((item) => ["ISSUED", "IN_PROGRESS"].includes(item.status)).length;
    const views = { cases: renderCases, documents: renderDocuments, templates: renderTemplates, signatures: renderSignatures, policies: renderPolicies };
    const view = views[state.activeTab] || renderCases;
    return `
      <div class="alw-shell" data-aion-legal-workspace>
        <style>
          .alw-shell{--alw-blue:#2563eb;--alw-navy:#14213d;--alw-soft:#eef5ff;--alw-page:#f7f9fc;--alw-line:#d9e2ec;padding:20px;color:var(--alw-navy);font-family:Inter,ui-sans-serif,system-ui,sans-serif;box-sizing:border-box}.alw-metrics{display:grid;grid-template-columns:repeat(4,minmax(115px,1fr));gap:10px;margin-bottom:14px}.alw-metric{border:1px solid var(--alw-line);border-radius:12px;background:#fff;padding:15px}.alw-metric strong{display:block;font-size:25px;line-height:1;color:var(--alw-navy)}.alw-metric span{display:block;margin-top:7px;font-size:11px;color:#66758a}.alw-tabs{display:flex;gap:6px;flex-wrap:wrap;padding:8px;background:#f2f5f9;border:1px solid var(--alw-line);border-radius:14px;margin-bottom:14px}.alw-tab,.alw-button{border:1px solid #bdc7d2;border-radius:10px;background:#fff;color:#273446;padding:9px 12px;font:inherit;font-size:10px;font-weight:850;letter-spacing:.04em;cursor:pointer}.alw-tab[aria-selected=true]{border-color:var(--alw-blue);background:var(--alw-soft);color:var(--alw-blue)}.alw-button-primary{background:var(--alw-blue);color:#fff;border-color:var(--alw-blue)}.alw-panel{border:1px solid var(--alw-line);border-top:4px solid var(--alw-blue);border-radius:14px;background:#fff;padding:18px}.alw-panel-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding-bottom:15px;border-bottom:1px solid #dce3ea}.alw-eyebrow{color:var(--alw-blue);font-size:9px;font-weight:900;letter-spacing:.18em}.alw-panel h3{margin:6px 0 4px;font-size:20px}.alw-panel p{margin:0;color:#66758a;font-size:12px;line-height:1.45}.alw-table{margin-top:14px;border:1px solid var(--alw-line);border-radius:12px;overflow:hidden}.alw-row{width:100%;display:grid;grid-template-columns:minmax(210px,2fr) minmax(100px,1fr) minmax(90px,.7fr) minmax(100px,.8fr);gap:12px;align-items:center;padding:12px 14px;border:0;border-bottom:1px solid #e2e7ed;background:#fff;color:#283548;text-align:left;font:inherit}.alw-sign-row{grid-template-columns:minmax(190px,1.45fr) minmax(170px,1.2fr) minmax(110px,.7fr) minmax(150px,1fr)}.alw-row:last-child{border-bottom:0}.alw-row button,.alw-row[role=button]{cursor:pointer}.alw-row-head{background:#f2f5f9;color:#667588;font-size:9px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}.alw-row strong,.alw-row small{display:block}.alw-row strong{font-size:12px}.alw-row small{margin-top:4px;color:#7a8797;font-size:10px}.alw-risk,.alw-status{display:inline-block;border:1px solid #cbd5df;border-radius:999px;padding:4px 6px;font-size:8px;letter-spacing:.08em;text-transform:uppercase}.alw-mini{border:1px solid #9faebe;border-radius:9px;background:#fff;color:#324156;padding:7px 9px;font:inherit;font-size:9px;font-weight:850;cursor:pointer}.alw-mini-primary{background:var(--alw-blue);border-color:var(--alw-blue);color:#fff}.alw-sealed{color:#287247;font-size:9px;font-weight:900;letter-spacing:.06em}.alw-proof-actions{display:grid;justify-items:start;gap:6px}.alw-chain{color:#244c73;font-size:8px;font-weight:900;letter-spacing:.07em}.alw-chain-pending{color:#8a6413}.alw-risk-high{border-color:#e7a4a4;color:#9f2c2c;background:#fff4f4}.alw-empty{min-height:180px;display:grid;place-content:center;text-align:center;color:#7a8795}.alw-empty strong{color:#2b3747;font-size:14px}.alw-empty span{max-width:440px;margin-top:7px;font-size:11px;line-height:1.5}.alw-template-grid,.alw-policy-grid{display:grid;grid-template-columns:repeat(3,minmax(180px,1fr));gap:10px;margin-top:15px}.alw-template,.alw-policy{min-height:145px;border:1px solid var(--alw-line);border-radius:12px;background:#fff;padding:15px;text-align:left;color:#253247;font:inherit;cursor:pointer}.alw-template:hover,.alw-policy:hover{border-color:var(--alw-blue);background:var(--alw-soft)}.alw-template>span,.alw-policy>span{display:inline-block;border-radius:999px;background:var(--alw-soft);color:var(--alw-blue);padding:4px 6px;font-size:8px;font-weight:900;letter-spacing:.12em}.alw-template strong,.alw-template small,.alw-template b,.alw-policy strong,.alw-policy small{display:block}.alw-template strong,.alw-policy strong{margin-top:12px;font-size:13px}.alw-template small,.alw-policy small{margin-top:7px;color:#718094;font-size:10px;line-height:1.4}.alw-template b{margin-top:15px;color:var(--alw-blue);font-size:9px;text-transform:uppercase;letter-spacing:.08em}@media(max-width:1000px){.alw-template-grid,.alw-policy-grid{grid-template-columns:1fr 1fr}.alw-row{grid-template-columns:1.6fr 1fr .8fr}.alw-row>*:last-child{display:none}}@media(max-width:720px){.alw-metrics{grid-template-columns:1fr 1fr}.alw-template-grid,.alw-policy-grid{grid-template-columns:1fr}.alw-panel-head{flex-direction:column}}
        </style>
        <div class="alw-metrics">${metric(Array.isArray(legalMatters) ? legalMatters.filter((item) => item.status !== "CLOSED").length : openCases,"Open matters")}${metric(Array.isArray(legalMatters) ? legalMatters.filter((item) => ["HIGH","URGENT"].includes(item.risk)).length : urgent,"High priority")}${metric(Array.isArray(legalDocuments) ? legalDocuments.length : state.documents.length,"Documents")}${metric(waiting,"Awaiting signature")}</div>
        <nav class="alw-tabs" aria-label="Legal workspace sections">${[["cases","Matters"],["documents","Documents"],["templates","Templates"],["signatures","Signatures"],["policies","Terms & policies"]].map(([id,label]) => `<button class="alw-tab" data-aion-legal-tab="${id}" aria-selected="${state.activeTab === id}">${label}</button>`).join("")}</nav>
        <div data-aion-legal-view>${view(state)}</div>
      </div>`;
  }

  function rerender() {
    const current = document.querySelector("[data-aion-legal-workspace]");
    if (!current) return;
    const host = document.createElement("div");
    host.innerHTML = render().trim();
    current.replaceWith(host.firstElementChild);
  }

  function openEnvelopeDialog(initial = null) {
    const overlay = document.createElement("div");
    overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    overlay.innerHTML = `<form data-aion-legal-envelope-form style="width:min(680px,100%);max-height:90vh;overflow:auto;background:#fff;border-top:4px solid #7c3f63;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.32);"><div class="alw-eyebrow">CONTROLLED SIGNATURE REQUEST</div><h2 style="margin:8px 0 6px;">Lock a document version and assign its signer</h2><p style="margin:0 0 18px;color:#65758a;font-size:12px;">This creates a draft only. A separate exact-version approval is required before a secure link can be issued.</p><label style="display:grid;gap:5px;margin-bottom:12px;font-size:11px;font-weight:800;">Document title<input required name="title" placeholder="e.g. Contractor agreement · September 2026" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;margin-bottom:12px;font-size:11px;font-weight:800;">Exact document text<textarea required name="document_content" rows="10" placeholder="Paste the complete approved terms here. The exact text is locked by SHA-256 hash." style="padding:11px;border:1px solid #aeb9c5;font:inherit;resize:vertical;"></textarea></label><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;"><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">First signer full name<input required name="signer_name" autocomplete="name" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">First signer email<input required type="email" name="signer_email" autocomplete="email" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">First signer role<input name="signer_role" value="Signer" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Signer check<select name="verification_method" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"><option value="typed_name_email">Name and email</option><option value="separate_channel_code">Separate-channel code</option></select></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Link expires in<select name="expires_in_days" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"><option value="7">7 days</option><option value="14" selected>14 days</option><option value="30">30 days</option></select></label></div><label style="display:grid;gap:5px;margin-top:12px;font-size:11px;font-weight:800;">Additional signers in signing order <span style="font-weight:500;color:#718094;">Optional · Name | email | role | typed_name_email or separate_channel_code</span><textarea name="additional_signers" rows="3" placeholder="Jane Smith | jane@example.com | Director | separate_channel_code" style="padding:11px;border:1px solid #aeb9c5;font:inherit;resize:vertical;"></textarea></label><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px;"><button type="button" class="alw-button" data-aion-legal-dialog-close>Cancel</button><button class="alw-button alw-button-primary">Create controlled draft</button></div></form>`;
    document.body.appendChild(overlay);
    if (initial) {
      const form = overlay.querySelector("[data-aion-legal-envelope-form]");
      form.elements.title.value = `${initial.title || "Document"} · replacement`;
      form.elements.document_content.value = initial.document?.content || "";
      const signers = initial.signers || [];
      if (signers[0]) {
        form.elements.signer_name.value = signers[0].name || "";
        form.elements.signer_email.value = signers[0].email || "";
        form.elements.signer_role.value = signers[0].role || "Signer";
        form.elements.verification_method.value = signers[0].verification_method || "typed_name_email";
      }
      form.elements.additional_signers.value = signers.slice(1).map((signer) => `${signer.name} | ${signer.email} | ${signer.role || "Signer"} | ${signer.verification_method || "typed_name_email"}`).join("\n");
      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "supersedes_envelope_id";
      hidden.value = initial.envelope_id;
      form.appendChild(hidden);
    }
  }

  function showSecureLinks(links, heading = "Secure signing links prepared") {
    const values = Array.isArray(links) ? links : [links];
    const overlay = document.createElement("div"); overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    overlay.innerHTML = `<div style="width:min(650px,100%);background:#fff;border-top:4px solid #7c3f63;padding:22px;"><div class="alw-eyebrow">MANUAL DELIVERY · NOT SENT</div><h2 style="margin:8px 0 6px;">${escapeHtml(heading)}</h2><p style="color:#65758a;font-size:12px;line-height:1.5;">Copy each link now and deliver it through an approved channel. Tessaris stores only hashes of these credentials. Where a separate code is shown, deliver the link and code through different approved channels.</p>${values.map((item) => { const url = `http://127.0.0.1:8080/legal-sign/${encodeURIComponent(item.token)}`; const code = item.verification_code ? `<div style="margin-top:10px;padding:10px;background:#fff8e7;border:1px solid #e5c56c;"><strong>Separate-channel code: ${escapeHtml(item.verification_code)}</strong><br><small>Do not send this code in the same message as the link.</small><br><button class="alw-button" style="margin-top:8px;" data-copy-verification-code="${escapeHtml(item.verification_code)}">Copy code</button></div>` : ""; return `<div style="border:1px solid #d8e0e8;padding:12px;margin-top:10px;"><strong style="font-size:12px;">${escapeHtml(item.name)} · ${escapeHtml(item.email)}</strong><input readonly value="${escapeHtml(url)}" style="width:100%;box-sizing:border-box;margin-top:8px;padding:10px;border:1px solid #aeb9c5;font:inherit;" onclick="this.select()"><button class="alw-button" style="margin-top:8px;" data-copy-signing-link="${escapeHtml(url)}">Copy link</button>${code}</div>`; }).join("")}<div style="display:flex;justify-content:flex-end;margin-top:18px;"><button class="alw-button alw-button-primary" data-aion-legal-dialog-close>Done</button></div></div>`;
    document.body.appendChild(overlay);
  }

  function openApprovedDeliveryDialog(envelopeId) {
    const overlay = document.createElement("div"); overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    overlay.innerHTML = `<form data-aion-legal-delivery-form data-envelope-id="${escapeHtml(envelopeId)}" style="width:min(600px,100%);background:#fff;border-top:4px solid #7c3f63;padding:22px;"><div class="alw-eyebrow">APPROVED SIGNED-COPY DELIVERY</div><h2 style="margin:8px 0 6px;">Prepare one private copy for every signer</h2><p style="margin:0 0 18px;color:#65758a;font-size:12px;line-height:1.5;">Tessaris will encrypt the exact evidence package in its retry queue. This step prepares delivery only; a separate action sends it through the selected connected provider.</p><label style="display:grid;gap:5px;margin-bottom:14px;font-size:11px;font-weight:800;">Delivery provider<select name="provider" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"><option value="resend">Resend transactional email</option><option value="microsoft_graph">Microsoft 365 / Outlook</option></select></label><label style="display:flex;align-items:flex-start;gap:8px;font-size:11px;line-height:1.45;"><input required type="checkbox" name="acknowledge_external_send">I approve preparing these completed signed copies for external delivery to every signer listed on this envelope.</label><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px;"><button type="button" class="alw-button" data-aion-legal-dialog-close>Cancel</button><button class="alw-button alw-button-primary">Prepare delivery queue</button></div></form>`;
    document.body.appendChild(overlay);
  }

  function openRecordsControls(kind, item) {
    const id = kind === "matter" ? item.matter_id : item.envelope_id;
    const governance = item.records_governance || {};
    const overlay = document.createElement("div");
    overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    overlay.innerHTML = `<form data-aion-legal-records-form data-record-kind="${escapeHtml(kind)}" data-record-id="${escapeHtml(id)}" style="width:min(620px,100%);background:#fff;border-top:4px solid #7c3f63;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.32);"><div class="alw-eyebrow">RETENTION · LEGAL HOLD · EXPORT</div><h2 style="margin:8px 0 6px;">${escapeHtml(item.title || id)}</h2><p style="margin:0 0 18px;color:#65758a;font-size:12px;line-height:1.5;">Deletion is blocked until the record is closed or terminal, its retention date has passed, an export has been made, and no legal hold remains. A content-free destruction receipt is retained.</p><label style="display:grid;gap:5px;margin-bottom:12px;font-size:11px;font-weight:800;">Retain until · ISO 8601 with timezone<input name="retain_until" value="${escapeHtml(governance.retain_until || "")}" placeholder="2027-09-26T12:00:00Z" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:11px;font-weight:800;"><input type="checkbox" name="legal_hold" ${governance.legal_hold ? "checked" : ""}>Legal hold active</label><label style="display:grid;gap:5px;margin-bottom:12px;font-size:11px;font-weight:800;">Legal-hold reason<input name="legal_hold_reason" value="${escapeHtml(governance.legal_hold_reason || "")}" placeholder="Required when enabling a hold" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:18px;"><button type="button" class="alw-button" data-aion-legal-record-export>Export first</button><button type="button" class="alw-button" data-aion-legal-record-delete>Delete eligible record</button><span style="flex:1"></span><button type="button" class="alw-button" data-aion-legal-dialog-close>Cancel</button><button class="alw-button alw-button-primary">Save controls</button></div></form>`;
    document.body.appendChild(overlay);
  }

  function openMatterWorkspace(item) {
    const links = item.linked_records || [];
    const obligations = item.obligations || [];
    const escalations = item.professional_escalations || [];
    const overlay = document.createElement("div");
    overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    overlay.innerHTML = `<div data-aion-legal-matter-workspace data-matter-id="${escapeHtml(item.matter_id)}" style="width:min(900px,100%);max-height:92vh;overflow:auto;background:#fff;border-top:4px solid #7c3f63;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.32);"><div style="display:flex;justify-content:space-between;gap:12px;"><div><div class="alw-eyebrow">MATTER RECORD · OBLIGATIONS · ESCALATION</div><h2 style="margin:8px 0 5px;">${escapeHtml(item.title)}</h2><p style="margin:0;color:#65758a;font-size:12px;">${escapeHtml(item.counterparty || "No counterparty")} · ${escapeHtml(item.jurisdiction?.governing_law || "Law not recorded")}</p></div><button class="alw-button" data-aion-legal-dialog-close>Close</button></div>
      <section style="margin-top:18px;padding-top:14px;border-top:1px solid #d8e0e8;"><div class="alw-eyebrow">LINKED EVIDENCE</div><p style="font-size:11px;color:#65758a;">References link protected documents, correspondence, signature envelopes and proof receipts without copying their private contents.</p>${links.length ? `<ul>${links.map((link) => `<li><strong>${escapeHtml(link.record_type)}</strong> · ${escapeHtml(link.label || link.reference_id)}</li>`).join("")}</ul>` : `<p style="font-size:11px;color:#7a8795;">No linked evidence yet.</p>`}<form data-aion-legal-link-form style="display:grid;grid-template-columns:1fr 1fr 1.2fr auto;gap:8px;"><select name="record_type" required><option>DOCUMENT</option><option>COMMUNICATION</option><option>SIGNATURE_ENVELOPE</option><option>PROOF_RECEIPT</option></select><input required name="reference_id" placeholder="Protected record ID"><input name="label" placeholder="Label"><button class="alw-button">Link record</button></form></section>
      <section style="margin-top:18px;padding-top:14px;border-top:1px solid #d8e0e8;"><div class="alw-eyebrow">RENEWALS · EXPIRIES · OBLIGATIONS</div>${obligations.length ? `<div>${obligations.map((entry) => `<div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #edf0f3;"><span style="flex:1;"><strong>${escapeHtml(entry.title)}</strong><small style="display:block;color:#718094;">${escapeHtml(entry.obligation_type)} · due ${escapeHtml(new Date(entry.due_at).toLocaleString("en-GB"))} · ${escapeHtml(entry.status)}</small></span>${entry.status === "OPEN" ? `<button class="alw-mini" data-aion-legal-obligation-complete="${escapeHtml(entry.obligation_id)}">Mark complete</button>` : ""}</div>`).join("")}</div>` : `<p style="font-size:11px;color:#7a8795;">No obligations recorded.</p>`}<form data-aion-legal-obligation-form style="display:grid;grid-template-columns:1.5fr .8fr 1fr 1fr auto;gap:8px;margin-top:10px;"><input required name="title" placeholder="Obligation or renewal"><select name="obligation_type"><option>ACTION</option><option>RENEWAL</option><option>EXPIRY</option><option>NOTICE</option><option>REVIEW</option></select><input required type="datetime-local" name="due_at"><input type="datetime-local" name="remind_at"><button class="alw-button">Add</button></form></section>
      <section style="margin-top:18px;padding-top:14px;border-top:1px solid #d8e0e8;"><div class="alw-eyebrow">HUMAN LEGAL PROFESSIONAL</div><p style="font-size:11px;color:#65758a;">Creates a structured draft only. Tessaris never contacts or appoints a lawyer automatically.</p>${escalations.length ? `<p style="font-size:11px;"><strong>${escalations.length}</strong> escalation draft(s) recorded · external delivery not authorised</p>` : ""}<form data-aion-legal-escalation-form style="display:grid;grid-template-columns:1.6fr .7fr 1fr auto;gap:8px;"><input required name="reason" placeholder="Reason professional review is needed"><select name="urgency"><option>NORMAL</option><option>HIGH</option><option>URGENT</option></select><input name="requested_professional" placeholder="Requested specialism"><button class="alw-button">Prepare escalation</button></form></section>
      <div style="display:flex;justify-content:flex-end;margin-top:18px;"><button class="alw-button" data-aion-legal-matter-records>Retention &amp; records controls</button></div></div>`;
    document.body.appendChild(overlay);
  }

  function openEnvelopeTimeline(item) {
    const events = item.audit_events || [];
    const proof = item.glyphchain_proof || {};
    const finality = proof.quorum_finality_certificate || {};
    const overlay = document.createElement("div");
    overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    overlay.innerHTML = `<div data-aion-legal-proof-cabinet style="width:min(850px,100%);max-height:92vh;overflow:auto;background:#fff;border-top:4px solid #7c3f63;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.32);"><div style="display:flex;justify-content:space-between;gap:12px;"><div><div class="alw-eyebrow">SIGNING TIMELINE · PROOF CABINET</div><h2 style="margin:8px 0 5px;">${escapeHtml(item.title)}</h2><p style="margin:0;color:#65758a;font-size:12px;">Exact version ${escapeHtml(item.document?.version || 1)} · ${escapeHtml(item.envelope_id)}</p></div><button class="alw-button" data-aion-legal-dialog-close>Close</button></div><section style="margin-top:18px;border:1px solid #d8e0e8;padding:14px;"><div class="alw-eyebrow">PORTABLE EVIDENCE</div><dl style="display:grid;grid-template-columns:170px 1fr;gap:7px;font-size:11px;"><dt>Document SHA-256</dt><dd>${escapeHtml(item.document?.content_hash || "Not sealed")}</dd><dt>Signed manifest</dt><dd>${escapeHtml(item.signed_copy?.manifest_hash || "Not completed")}</dd><dt>GlyphChain status</dt><dd>${escapeHtml(proof.status || "Not submitted")}</dd><dt>Transaction</dt><dd>${escapeHtml(proof.tx_id || "—")}</dd><dt>Ledger commitment</dt><dd>${escapeHtml(proof.ledger_commitment || "—")}</dd><dt>Transaction root</dt><dd>${escapeHtml(proof.txs_root || finality.txs_root || "—")}</dd><dt>Finality schema</dt><dd>${escapeHtml(finality.schema_version || "—")}</dd></dl>${item.status === "COMPLETED" ? `<div style="display:flex;gap:8px;flex-wrap:wrap;"><button class="alw-button alw-button-primary" data-aion-legal-envelope-action="evidence-download" data-envelope-id="${escapeHtml(item.envelope_id)}">Download private evidence</button>${proof.status === "FINALIZED" ? `<button class="alw-button" data-aion-legal-envelope-action="glyphchain-verify" data-envelope-id="${escapeHtml(item.envelope_id)}">Verify GlyphChain proof</button>` : ""}</div>` : ""}</section><section style="margin-top:14px;border:1px solid #d8e0e8;padding:14px;"><div class="alw-eyebrow">HASH-CHAINED EVENT HISTORY</div>${events.length ? `<ol style="list-style:none;padding:0;margin:10px 0 0;">${events.map((entry) => `<li style="display:grid;grid-template-columns:170px 1fr;gap:12px;padding:9px 0;border-bottom:1px solid #edf0f3;font-size:11px;"><time>${escapeHtml(new Date(entry.occurred_at).toLocaleString("en-GB"))}</time><span><strong>${escapeHtml(entry.event_type)}</strong><small style="display:block;color:#718094;">Actor ${escapeHtml(entry.actor_id || "unknown")} · ${escapeHtml(String(entry.event_hash || "").slice(0,16))}…</small></span></li>`).join("")}</ol>` : `<p style="font-size:11px;color:#7a8795;">No recorded events.</p>`}</section><p style="font-size:10px;color:#718094;line-height:1.5;">The cabinet displays locally retained evidence. A chain entry is final only when its quorum certificate verifies against an independently trusted validator checkpoint.</p></div>`;
    document.body.appendChild(overlay);
  }

  function today() {
    return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(new Date());
  }

  function openMatterDialog() {
    const overlay = document.createElement("div");
    overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    overlay.innerHTML = `<form data-aion-legal-matter-form style="width:min(660px,100%);max-height:90vh;overflow:auto;background:#fff;border-top:4px solid #7c3f63;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.32);"><div class="alw-eyebrow">NEW LEGAL MATTER</div><h2 style="margin:8px 0 6px;">Record an issue or piece of work</h2><p style="margin:0 0 18px;color:#65758a;font-size:12px;">Choose the legal context explicitly. Tessaris records this selection but does not determine which law applies.</p><label style="display:grid;gap:5px;margin-bottom:12px;font-size:11px;font-weight:800;">Matter title<input required name="title" placeholder="e.g. Customer complaint about cancelled job" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;margin-bottom:12px;font-size:11px;font-weight:800;">Counterparty<input name="counterparty" placeholder="Customer, supplier, employee or contractor" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;margin-bottom:12px;font-size:11px;font-weight:800;">Summary<textarea name="summary" rows="3" placeholder="What happened, important dates and the outcome needed" style="padding:11px;border:1px solid #aeb9c5;font:inherit;resize:vertical;"></textarea></label><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;"><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Type<select name="type" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"><option value="CONTRACT">Contract</option><option value="COMPLAINT">Complaint</option><option value="EMPLOYMENT">Employment</option><option value="PRIVACY">Privacy</option><option value="DISPUTE">Dispute</option><option value="GENERAL_ADVICE">General guidance</option></select></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Priority<select name="risk" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"><option value="NORMAL">Normal</option><option value="HIGH">High</option><option value="URGENT">Urgent</option><option value="LOW">Low</option></select></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Country code<input required name="country_code" value="IE" maxlength="2" style="padding:11px;border:1px solid #aeb9c5;font:inherit;text-transform:uppercase;"></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Region <span style="font-weight:500;color:#718094;">Optional</span><input name="region" placeholder="State, province or nation" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Governing law<input required name="governing_law" value="Law of Ireland" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Forum <span style="font-weight:500;color:#718094;">Optional</span><input name="forum" placeholder="Courts or dispute forum" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label></div><label style="display:flex;align-items:flex-start;gap:8px;margin-top:14px;font-size:11px;line-height:1.4;"><input required type="checkbox" name="owner_confirmed">I confirm this jurisdiction and governing-law selection for the business record.</label><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px;"><button type="button" class="alw-button" data-aion-legal-dialog-close>Cancel</button><button class="alw-button alw-button-primary">Create matter</button></div></form>`;
    document.body.appendChild(overlay);
  }

  async function openDocumentReview(documentId) {
    const result = await signingRequest(`/documents/${encodeURIComponent(documentId)}`);
    const item = result.document || {};
    const categories = ["CONTRACT", "TERMS_AND_CONDITIONS", "PRIVACY", "EMPLOYMENT", "COMPLAINT", "NOTICE", "INVOICE_OR_QUOTE", "OTHER"];
    const latestReview = (item.contract_reviews || []).at(-1);
    const findings = latestReview?.findings || [];
    const overlay = document.createElement("div");
    overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    overlay.innerHTML = `<form data-aion-legal-document-review-form data-document-id="${escapeHtml(item.document_id)}" style="width:min(860px,100%);max-height:92vh;overflow:auto;background:#fff;border-top:4px solid #7c3f63;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.32);"><div style="display:flex;justify-content:space-between;gap:12px;"><div><div class="alw-eyebrow">LOCAL DOCUMENT REVIEW</div><h2 style="margin:8px 0 5px;">${escapeHtml(item.filename)}</h2><p style="margin:0;color:#65758a;font-size:11px;">SHA-256 ${escapeHtml(item.content_sha256)} · ${escapeHtml(item.extraction?.method)} · ${escapeHtml(item.extraction?.status)}</p></div><button type="button" class="alw-button" data-aion-legal-dialog-close>Close</button></div><div style="margin-top:16px;padding:12px;border:1px solid #d8e0e8;background:#f8fafc;"><strong style="font-size:11px;">Automated suggestion: ${escapeHtml(item.classification?.suggested_category || "OTHER")}</strong><p style="margin-top:6px;font-size:11px;color:#65758a;">This is local triage, not a legal determination. A person must confirm or correct it.</p></div><label style="display:grid;gap:5px;margin-top:14px;font-size:11px;font-weight:800;">Confirmed category<select name="category" style="padding:11px;border:1px solid #aeb9c5;font:inherit;">${categories.map((category) => `<option value="${category}" ${category === (item.classification?.confirmed_category || item.classification?.suggested_category) ? "selected" : ""}>${category.replaceAll("_", " ")}</option>`).join("")}</select></label><section style="margin-top:14px;border:1px solid #d8e0e8;padding:12px;"><div class="alw-eyebrow">CLAUSE &amp; RISK TRIAGE</div><div style="display:flex;gap:7px;flex-wrap:wrap;margin:9px 0;"><button type="button" class="alw-button alw-button-primary" data-aion-legal-contract-review="${escapeHtml(item.document_id)}">Run local review</button><button type="button" class="alw-button" data-aion-legal-compare="${escapeHtml(item.document_id)}">Compare version</button><button type="button" class="alw-button" data-aion-legal-redline="${escapeHtml(item.document_id)}">Draft redline</button><button type="button" class="alw-button" data-aion-legal-negotiation="${escapeHtml(item.document_id)}">Record negotiation position</button></div>${findings.length ? findings.map((finding) => `<div style="border-top:1px solid #e2e7ed;padding:9px 0;font-size:11px;"><strong>${escapeHtml(finding.title)} · ${escapeHtml(finding.severity)}</strong><small style="display:block;color:#65758a;margin-top:3px;">${escapeHtml(finding.review_guidance)} · human review required</small></div>`).join("") : `<p style="font-size:11px;color:#65758a;">No local contract review has been run. Findings are explainable rule signals, not legal conclusions.</p>`}</section><label style="display:grid;gap:5px;margin-top:14px;font-size:11px;font-weight:800;">Locally extracted text<textarea readonly rows="12" style="padding:11px;border:1px solid #aeb9c5;background:#f8fafc;font:inherit;resize:vertical;">${escapeHtml(item.extraction?.text || item.extraction?.limitation || "No text was extracted.")}</textarea></label><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:18px;"><button type="button" class="alw-button" data-aion-legal-dialog-close>Cancel</button><button class="alw-button alw-button-primary">Confirm classification</button></div></form>`;
    document.body.appendChild(overlay);
  }

  function openTemplateDraftDialog(initial = null) {
    const item = initial || {};
    const overlay = document.createElement("div");
    overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    const types = ["CUSTOMER_AGREEMENT", "SUPPLIER_AGREEMENT", "CONTRACTOR_AGREEMENT", "EMPLOYMENT_DOCUMENT", "TERMS_AND_CONDITIONS", "PRIVACY_NOTICE", "DATA_PROCESSING_AGREEMENT", "OTHER"];
    overlay.innerHTML = `<form data-aion-legal-template-form style="width:min(820px,100%);max-height:92vh;overflow:auto;background:#fff;border-top:4px solid #7c3f63;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.32);"><input type="hidden" name="source_template_id" value="${escapeHtml(item.template_id || "")}"><div class="alw-eyebrow">${item.template_id ? "NEW IMMUTABLE REVISION" : "NEW TEMPLATE DRAFT"}</div><h2 style="margin:8px 0 6px;">${item.template_id ? `Revise ${escapeHtml(item.title)}` : "Create wording for qualified review"}</h2><p style="margin:0 0 18px;color:#65758a;font-size:12px;">This remains unusable until a named qualified reviewer approves its exact SHA-256 hash, jurisdiction and intended use. Use <b>{{VARIABLE_NAME}}</b> for required fields.</p><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;"><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Title<input required name="title" value="${escapeHtml(item.title || "")}" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Type<select name="template_type" style="padding:11px;border:1px solid #aeb9c5;font:inherit;">${types.map((type) => `<option value="${type}" ${type === item.template_type ? "selected" : ""}>${type.replaceAll("_", " ")}</option>`).join("")}</select></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Country code<input required name="country_code" maxlength="2" value="${escapeHtml(item.jurisdiction?.country_code || "IE")}" style="padding:11px;border:1px solid #aeb9c5;font:inherit;text-transform:uppercase;"></label><label style="display:grid;gap:5px;font-size:11px;font-weight:800;">Governing law<input required name="governing_law" value="${escapeHtml(item.jurisdiction?.governing_law || "Law of Ireland")}" style="padding:11px;border:1px solid #aeb9c5;font:inherit;"></label></div><label style="display:grid;gap:5px;margin-top:12px;font-size:11px;font-weight:800;">Intended use<textarea required name="intended_use" rows="2" style="padding:11px;border:1px solid #aeb9c5;font:inherit;resize:vertical;">${escapeHtml(item.intended_use || "")}</textarea></label><label style="display:grid;gap:5px;margin-top:12px;font-size:11px;font-weight:800;">Exact template text<textarea required name="content" rows="14" style="padding:11px;border:1px solid #aeb9c5;font:inherit;resize:vertical;">${escapeHtml(item.content || "")}</textarea></label><label style="display:flex;align-items:flex-start;gap:8px;margin-top:12px;font-size:11px;"><input required type="checkbox" name="owner_confirmed">I confirm the recorded jurisdiction and intended use. This is not a claim that Tessaris supplied legal advice.</label><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:18px;"><button type="button" class="alw-button" data-aion-legal-dialog-close>Cancel</button><button class="alw-button alw-button-primary">Save review-required draft</button></div></form>`;
    document.body.appendChild(overlay);
  }

  async function openTemplateWorkspace(templateId) {
    const result = await signingRequest(`/templates/${encodeURIComponent(templateId)}`);
    const item = result.template || {};
    const approved = item.status === "APPROVED_FOR_CONTROLLED_USE";
    const draft = item.status === "DRAFT_REQUIRES_QUALIFIED_REVIEW";
    const reviewable = draft || ["REVIEW_OVERDUE_REQUIRES_QUALIFIED_REVIEW", "WITHDRAWN_FOR_LEGAL_CHANGE"].includes(item.status);
    const matterOptions = (legalMatters || []).filter((matter) => matter.status !== "CLOSED").map((matter) => `<option value="${escapeHtml(matter.matter_id)}">${escapeHtml(matter.title)}</option>`).join("");
    const overlay = document.createElement("div");
    overlay.className = "alw-dialog";
    overlay.style.cssText = "position:fixed;inset:0;z-index:100000;background:rgba(15,23,42,.72);display:grid;place-items:center;padding:24px;";
    const approvalSection = reviewable ? `<form data-aion-legal-template-approval-form data-review-mode="${draft ? "approve" : "renew-review"}" data-template-id="${escapeHtml(item.template_id)}" style="margin-top:16px;border:1px solid #d8e0e8;padding:14px;"><div class="alw-eyebrow">${draft ? "QUALIFIED REVIEW" : "RENEW QUALIFIED REVIEW"}</div><p style="margin:7px 0 12px;color:#65758a;font-size:11px;">Approval is bound to SHA-256 ${escapeHtml(item.content_sha256)}. Tessaris records the review assertion; it does not certify the reviewer's professional status.</p><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;"><label style="display:grid;gap:4px;font-size:10px;font-weight:800;">Reviewer name<input required name="reviewer_name" style="padding:9px;border:1px solid #aeb9c5;"></label><label style="display:grid;gap:4px;font-size:10px;font-weight:800;">Qualification / regulator<input required name="reviewer_qualification" style="padding:9px;border:1px solid #aeb9c5;"></label><label style="display:grid;gap:4px;font-size:10px;font-weight:800;">Approved jurisdiction<input required name="approved_jurisdiction" style="padding:9px;border:1px solid #aeb9c5;"></label><label style="display:grid;gap:4px;font-size:10px;font-weight:800;">Review scope<input required name="review_scope" style="padding:9px;border:1px solid #aeb9c5;"></label><label style="display:grid;gap:4px;font-size:10px;font-weight:800;">Review again in days<input required type="number" min="1" max="1825" name="review_interval_days" value="365" style="padding:9px;border:1px solid #aeb9c5;"></label></div><label style="display:flex;gap:8px;align-items:flex-start;margin-top:10px;font-size:10px;"><input required type="checkbox" name="acknowledge_qualified_review">I confirm that a suitably qualified reviewer reviewed this exact version for the stated use and jurisdiction.</label><div style="text-align:right;margin-top:10px;"><button class="alw-button alw-button-primary">${draft ? "Record exact-version approval" : "Renew exact-version review"}</button></div></form>` : "";
    const instantiateSection = approved ? `<form data-aion-legal-template-instance-form data-template-id="${escapeHtml(item.template_id)}" style="margin-top:16px;border:1px solid #d8e0e8;padding:14px;"><div class="alw-eyebrow">CREATE CONTROLLED DRAFT</div><p style="margin:7px 0 12px;color:#65758a;font-size:11px;">The generated document remains subject to final human review and is not sent automatically.</p><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">${(item.variables || []).map((name) => `<label style="display:grid;gap:4px;font-size:10px;font-weight:800;">${escapeHtml(name.replaceAll("_", " "))}<input required name="variable_${escapeHtml(name)}" data-variable-name="${escapeHtml(name)}" style="padding:9px;border:1px solid #aeb9c5;"></label>`).join("")}<label style="display:grid;gap:4px;font-size:10px;font-weight:800;">Saved filename<input required name="filename" value="${escapeHtml(item.title)}.txt" style="padding:9px;border:1px solid #aeb9c5;"></label><label style="display:grid;gap:4px;font-size:10px;font-weight:800;">Link to matter (optional)<select name="matter_id" style="padding:9px;border:1px solid #aeb9c5;"><option value="">No matter</option>${matterOptions}</select></label></div><div style="text-align:right;margin-top:10px;"><button class="alw-button alw-button-primary">Create encrypted document draft</button></div></form>` : "";
    const withdrawalSection = approved ? `<form data-aion-legal-template-withdrawal-form data-template-id="${escapeHtml(item.template_id)}" style="margin-top:16px;border:1px solid #e5c9c9;padding:14px;"><div class="alw-eyebrow">LEGAL CHANGE WITHDRAWAL</div><p style="margin:7px 0 12px;color:#65758a;font-size:11px;">Immediately stop new use without deleting or rewriting this exact approved version.</p><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;"><input required name="reason" placeholder="Reason this wording must stop being used" style="padding:9px;border:1px solid #aeb9c5;"><input required name="legal_change_reference" placeholder="Source, notice or review reference" style="padding:9px;border:1px solid #aeb9c5;"></div><label style="display:flex;gap:8px;align-items:flex-start;margin-top:10px;font-size:10px;"><input required type="checkbox" name="acknowledge_withdrawal">Withdraw this exact version from controlled use now.</label><div style="text-align:right;margin-top:10px;"><button class="alw-button">Withdraw version</button></div></form>` : "";
    overlay.innerHTML = `<section style="width:min(900px,100%);max-height:92vh;overflow:auto;background:#fff;border-top:4px solid #7c3f63;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.32);"><div style="display:flex;justify-content:space-between;gap:16px;"><div><div class="alw-eyebrow">TEMPLATE VERSION ${escapeHtml(item.version)}</div><h2 style="margin:8px 0 5px;">${escapeHtml(item.title)}</h2><p style="margin:0;color:#65758a;font-size:11px;">${escapeHtml(item.template_type)} · ${escapeHtml(item.jurisdiction?.governing_law)} · SHA-256 ${escapeHtml(item.content_sha256)}</p></div><button type="button" class="alw-button" data-aion-legal-dialog-close>Close</button></div><div style="display:flex;gap:7px;align-items:center;margin-top:14px;"><b class="alw-status">${escapeHtml(item.status)}</b>${item.approval ? `<span style="font-size:10px;color:#65758a;">Approved by ${escapeHtml(item.approval.reviewer_name)} · review due ${escapeHtml(item.approval.review_due_at ? new Date(item.approval.review_due_at).toLocaleDateString("en-GB") : "not scheduled")}</span>` : ""}<button type="button" class="alw-mini" data-aion-legal-template-revise="${escapeHtml(item.template_id)}">Create revision</button></div><label style="display:grid;gap:5px;margin-top:14px;font-size:11px;font-weight:800;">Exact version<textarea readonly rows="12" style="padding:11px;border:1px solid #aeb9c5;background:#f8fafc;font:inherit;resize:vertical;">${escapeHtml(item.content || "")}</textarea></label>${approvalSection}${instantiateSection}${withdrawalSection}</section>`;
    document.body.appendChild(overlay);
  }

  document.addEventListener("click", (event) => {
    const tab = event.target.closest?.("[data-aion-legal-tab]");
    if (tab) { const state = readState(); state.activeTab = tab.dataset.aionLegalTab; writeState(state); rerender(); if (state.activeTab === "signatures") void refreshSigningEnvelopes(true); if (state.activeTab === "documents") void refreshLegalDocuments(true); if (state.activeTab === "templates") void refreshLegalTemplates(true); return; }
    if (event.target.closest?.("[data-aion-legal-new-case]")) { openMatterDialog(); return; }
    if (event.target.closest?.("[data-aion-legal-dialog-close]")) { event.target.closest(".alw-dialog")?.remove(); return; }
    if (event.target.closest?.("[data-aion-legal-new-template]")) { openTemplateDraftDialog(); return; }
    const openTemplate = event.target.closest?.("[data-aion-legal-template-open]");
    if (openTemplate) { void openTemplateWorkspace(openTemplate.dataset.aionLegalTemplateOpen).catch((error) => global.safeAionDesktopMessage?.(error.message, "error")); return; }
    const reviseTemplate = event.target.closest?.("[data-aion-legal-template-revise]");
    if (reviseTemplate) {
      void signingRequest(`/templates/${encodeURIComponent(reviseTemplate.dataset.aionLegalTemplateRevise)}`).then((result) => { reviseTemplate.closest(".alw-dialog")?.remove(); openTemplateDraftDialog(result.template); }).catch((error) => global.safeAionDesktopMessage?.(error.message, "error"));
      return;
    }
    if (event.target.closest?.("[data-aion-legal-upload]")) {
      void (async () => {
        try {
          const document = await selectAndUploadDocument();
          if (!document) return;
          const state = readState(); state.activeTab = "documents"; writeState(state);
          global.safeAionDesktopMessage?.(`${document.filename} encrypted, hashed and queued for human review.`, "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const documentReview = event.target.closest?.("[data-aion-legal-document-review]");
    if (documentReview) { void openDocumentReview(documentReview.dataset.aionLegalDocumentReview).catch((error) => global.safeAionDesktopMessage?.(error.message, "error")); return; }
    const contractReview = event.target.closest?.("[data-aion-legal-contract-review]");
    if (contractReview) {
      void (async () => { try { await signingRequest(`/documents/${encodeURIComponent(contractReview.dataset.aionLegalContractReview)}/contract-review`); contractReview.closest(".alw-dialog")?.remove(); await refreshLegalDocuments(); await openDocumentReview(contractReview.dataset.aionLegalContractReview); } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); } })();
      return;
    }
    const compareDocument = event.target.closest?.("[data-aion-legal-compare]");
    if (compareDocument) {
      const choices = (legalDocuments || []).filter((item) => item.document_id !== compareDocument.dataset.aionLegalCompare).map((item) => `${item.document_id} · ${item.filename}`).join("\n");
      const baseId = global.prompt(`Enter the earlier document ID to compare against:\n\n${choices}`);
      if (!baseId) return;
      void signingRequest(`/documents/${encodeURIComponent(compareDocument.dataset.aionLegalCompare)}/compare`, { base_document_id: String(baseId).split(" · ")[0].trim() }).then((result) => global.alert(result.comparison?.unified_diff || "No line changes found.")).catch((error) => global.safeAionDesktopMessage?.(error.message, "error"));
      return;
    }
    const redlineDocument = event.target.closest?.("[data-aion-legal-redline]");
    if (redlineDocument) {
      const originalText = global.prompt("Paste the exact clause text from this document:"); if (!originalText) return;
      const proposedText = global.prompt("Enter the proposed replacement wording:"); if (!proposedText) return;
      const rationale = global.prompt("Record the business rationale (optional):") || "";
      void signingRequest(`/documents/${encodeURIComponent(redlineDocument.dataset.aionLegalRedline)}/redlines`, { finding_id: "", original_text: originalText, proposed_text: proposedText, rationale }).then(() => global.safeAionDesktopMessage?.("Controlled redline draft saved. The original is unchanged and nothing was sent.", "success")).catch((error) => global.safeAionDesktopMessage?.(error.message, "error"));
      return;
    }
    const negotiationDocument = event.target.closest?.("[data-aion-legal-negotiation]");
    if (negotiationDocument) {
      const issue = global.prompt("Negotiation issue:"); if (!issue) return;
      const businessPosition = global.prompt("Business position:"); if (!businessPosition) return;
      const counterpartyPosition = global.prompt("Counterparty position (optional):") || "";
      void signingRequest(`/documents/${encodeURIComponent(negotiationDocument.dataset.aionLegalNegotiation)}/negotiation-positions`, { issue, business_position: businessPosition, counterparty_position: counterpartyPosition }).then(() => global.safeAionDesktopMessage?.("Negotiation position saved locally. Nothing was sent.", "success")).catch((error) => global.safeAionDesktopMessage?.(error.message, "error"));
      return;
    }
    if (event.target.closest?.("[data-aion-legal-new-envelope]")) { openEnvelopeDialog(); return; }
    if (event.target.closest?.("[data-aion-legal-refresh-signatures]")) { void refreshSigningEnvelopes(true); return; }
    const matterRecords = event.target.closest?.("[data-aion-legal-case]");
    if (matterRecords) {
      const item = (legalMatters || []).find((value) => value.matter_id === matterRecords.dataset.aionLegalCase);
      if (item) openMatterWorkspace(item);
      return;
    }
    const matterRecordsControl = event.target.closest?.("[data-aion-legal-matter-records]");
    if (matterRecordsControl) {
      const workspace = matterRecordsControl.closest("[data-aion-legal-matter-workspace]");
      const item = (legalMatters || []).find((value) => value.matter_id === workspace?.dataset.matterId);
      workspace?.closest(".alw-dialog")?.remove();
      if (item) openRecordsControls("matter", item);
      return;
    }
    const completeObligation = event.target.closest?.("[data-aion-legal-obligation-complete]");
    if (completeObligation) {
      const workspace = completeObligation.closest("[data-aion-legal-matter-workspace]");
      void (async () => {
        try {
          await signingRequest(`/matters/${encodeURIComponent(workspace.dataset.matterId)}/obligations/${encodeURIComponent(completeObligation.dataset.aionLegalObligationComplete)}/status`, { status: "COMPLETED" });
          workspace.closest(".alw-dialog")?.remove(); await refreshLegalMatters();
          const item = (legalMatters || []).find((value) => value.matter_id === workspace.dataset.matterId); if (item) openMatterWorkspace(item);
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const envelopeRecords = event.target.closest?.("[data-aion-legal-records-kind]");
    if (envelopeRecords) {
      const item = (signingEnvelopes || []).find((value) => value.envelope_id === envelopeRecords.dataset.recordId);
      if (item) openRecordsControls("envelope", item);
      return;
    }
    const envelopeTimeline = event.target.closest?.("[data-aion-legal-envelope-timeline]");
    if (envelopeTimeline) {
      const item = (signingEnvelopes || []).find((value) => value.envelope_id === envelopeTimeline.dataset.aionLegalEnvelopeTimeline);
      if (item) openEnvelopeTimeline(item);
      return;
    }
    const recordExport = event.target.closest?.("[data-aion-legal-record-export]");
    if (recordExport) {
      const form = recordExport.closest("[data-aion-legal-records-form]");
      void (async () => {
        try {
          const filename = form.dataset.recordKind === "matter"
            ? await downloadMatterExport(form.dataset.recordId)
            : await downloadEvidencePackage(form.dataset.recordId);
          global.safeAionDesktopMessage?.(`${filename} downloaded.`, "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const recordDelete = event.target.closest?.("[data-aion-legal-record-delete]");
    if (recordDelete) {
      const form = recordDelete.closest("[data-aion-legal-records-form]");
      const id = form.dataset.recordId;
      const confirmation = global.prompt(`This permanently removes the encrypted local record after all safeguards pass. Type DELETE ${id}`);
      if (!confirmation) return;
      void (async () => {
        try {
          const prefix = form.dataset.recordKind === "matter" ? `/matters/${encodeURIComponent(id)}` : `/envelopes/${encodeURIComponent(id)}`;
          await signingRequest(`${prefix}/delete`, { confirmation });
          form.closest(".alw-dialog")?.remove();
          if (form.dataset.recordKind === "matter") await refreshLegalMatters(); else await refreshSigningEnvelopes();
          global.safeAionDesktopMessage?.("The encrypted local record was destroyed and a content-free receipt was retained.", "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const copy = event.target.closest?.("[data-copy-signing-link]");
    if (copy) { void navigator.clipboard.writeText(copy.dataset.copySigningLink || ""); global.safeAionDesktopMessage?.("Secure signing link copied.", "success"); return; }
    const codeCopy = event.target.closest?.("[data-copy-verification-code]");
    if (codeCopy) { void navigator.clipboard.writeText(codeCopy.dataset.copyVerificationCode || ""); global.safeAionDesktopMessage?.("Separate-channel code copied.", "success"); return; }
    const envelopeAction = event.target.closest?.("[data-aion-legal-envelope-action]");
    if (envelopeAction) {
      void (async () => {
        try {
          const id = envelopeAction.dataset.envelopeId; const action = envelopeAction.dataset.aionLegalEnvelopeAction;
          let result;
          if (action === "submit") result = await signingRequest(`/envelopes/${encodeURIComponent(id)}/submit-approval`);
          if (action === "approve") { if (!global.confirm("Approve this exact document version and signer list for issue?")) return; result = await signingRequest(`/envelopes/${encodeURIComponent(id)}/approve`, { review_hash: envelopeAction.dataset.reviewHash }); }
          if (action === "issue") { if (!global.confirm("Create the secure signer link(s)? Nothing will be emailed or sent automatically.")) return; result = await signingRequest(`/envelopes/${encodeURIComponent(id)}/issue`); showSecureLinks(result.envelope.secure_links); }
          if (action === "remind") { result = await signingRequest(`/envelopes/${encodeURIComponent(id)}/reminders`, { signer_id: envelopeAction.dataset.signerId }); showSecureLinks(result.envelope.secure_link, "Reminder link prepared"); }
          if (action === "delivery-prepare") { openApprovedDeliveryDialog(id); return; }
          if (action === "delivery-send") { if (!global.confirm("Send every due signed-copy package through the approved provider now? Provider acceptance will not be shown as delivery confirmation.")) return; result = await signingRequest("/delivery-outbox/send", { acknowledge_external_send: true, limit: 25, force: true }); }
          if (action === "delivery-confirm") { const outcome = String(global.prompt("Provider outcome: DELIVERED, BOUNCED or REJECTED", "DELIVERED") || "").trim().toUpperCase(); if (!["DELIVERED","BOUNCED","REJECTED"].includes(outcome)) return; const reference = global.prompt("Enter the provider delivery-event or message reference:"); if (!reference) return; result = await signingRequest(`/delivery-outbox/${encodeURIComponent(envelopeAction.dataset.deliveryId)}/confirm`, { outcome, provider_reference: reference }); }
          if (action === "delivery-retry") { const reason = global.prompt("Why is this signed copy being retried?"); if (!reason || !global.confirm("Authorize another external delivery attempt for this signer?")) return; result = await signingRequest(`/delivery-outbox/${encodeURIComponent(envelopeAction.dataset.deliveryId)}/retry`, { reason, acknowledge_external_send: true }); }
          if (action === "evidence-download") { const filename = await downloadEvidencePackage(id); global.safeAionDesktopMessage?.(`${filename} downloaded.`, "success"); return; }
          if (action === "replacement") { const item = (signingEnvelopes || []).find((value) => value.envelope_id === id); if (!item) throw new Error("The completed document could not be loaded."); openEnvelopeDialog(item); return; }
          if (action === "history") { result = await signingRequest(`/envelopes/${encodeURIComponent(id)}/history`, {}); const history = result.history || {}; global.alert(history.history_links_valid && history.all_audit_chains_valid && history.all_available_proofs_valid ? `Document history verified · ${(history.newest_to_oldest || []).length} version(s).` : "Document history needs attention."); return; }
          if (action === "glyphchain-submit") { if (!global.confirm("Record this document's private hash commitments on GlyphChain? Document text and signer identities will remain off-chain.")) return; result = await signingRequest(`/envelopes/${encodeURIComponent(id)}/proof/submit`); }
          if (action === "glyphchain-verify") { result = await signingRequest(`/envelopes/${encodeURIComponent(id)}/proof/verify`, {}); const verification = result.verification || {}; global.alert(verification.valid && verification.glyphchain_inclusion_verified ? "GlyphChain proof verified." : `Verification needs attention: ${(verification.errors || []).join(", ") || verification.glyphchain_status || "unknown"}`); }
          await refreshSigningEnvelopes();
          const message = action === "delivery-send"
            ? "The approved provider accepted the due delivery request(s). Final delivery is not yet confirmed."
            : action === "delivery-confirm"
              ? "The provider outcome was recorded."
              : action === "delivery-retry"
                ? "A new delivery attempt was authorized and queued."
                : action.startsWith("glyphchain-")
                  ? "GlyphChain proof updated."
                  : "Signature workflow updated. No external message was sent.";
          global.safeAionDesktopMessage?.(message, "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
    }
  }, true);

  document.addEventListener("submit", (event) => {
    const templateForm = event.target.closest?.("[data-aion-legal-template-form]");
    if (templateForm) {
      event.preventDefault();
      const data = new FormData(templateForm);
      void (async () => {
        try {
          await signingRequest("/templates", {
            title: String(data.get("title") || ""), template_type: String(data.get("template_type") || "OTHER"),
            content: String(data.get("content") || ""), intended_use: String(data.get("intended_use") || ""),
            source_template_id: String(data.get("source_template_id") || ""), jurisdiction: {
              country_code: String(data.get("country_code") || ""), region: "",
              governing_law: String(data.get("governing_law") || ""), forum: "",
              owner_confirmed: data.get("owner_confirmed") === "on",
            },
          });
          templateForm.closest(".alw-dialog")?.remove(); await refreshLegalTemplates();
          global.safeAionDesktopMessage?.("Review-required template version saved locally. It is not approved for use.", "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const templateApprovalForm = event.target.closest?.("[data-aion-legal-template-approval-form]");
    if (templateApprovalForm) {
      event.preventDefault();
      const data = new FormData(templateApprovalForm);
      const item = (legalTemplates || []).find((value) => value.template_id === templateApprovalForm.dataset.templateId);
      if (!item) { global.safeAionDesktopMessage?.("The exact template version could not be loaded.", "error"); return; }
      void (async () => {
        try {
          const reviewMode = templateApprovalForm.dataset.reviewMode || "approve";
          await signingRequest(`/templates/${encodeURIComponent(item.template_id)}/${reviewMode}`, {
            expected_content_sha256: item.content_sha256,
            reviewer_name: String(data.get("reviewer_name") || ""),
            reviewer_qualification: String(data.get("reviewer_qualification") || ""),
            review_scope: String(data.get("review_scope") || ""),
            approved_jurisdiction: String(data.get("approved_jurisdiction") || ""),
            acknowledge_qualified_review: data.get("acknowledge_qualified_review") === "on",
            review_interval_days: Number(data.get("review_interval_days") || 365),
          });
          templateApprovalForm.closest(".alw-dialog")?.remove(); await refreshLegalTemplates();
          global.safeAionDesktopMessage?.("Exact template version approved for controlled use.", "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const templateWithdrawalForm = event.target.closest?.("[data-aion-legal-template-withdrawal-form]");
    if (templateWithdrawalForm) {
      event.preventDefault();
      const data = new FormData(templateWithdrawalForm);
      void (async () => {
        try {
          await signingRequest(`/templates/${encodeURIComponent(templateWithdrawalForm.dataset.templateId)}/withdraw`, {
            reason: String(data.get("reason") || ""),
            legal_change_reference: String(data.get("legal_change_reference") || ""),
            acknowledge_withdrawal: data.get("acknowledge_withdrawal") === "on",
          });
          templateWithdrawalForm.closest(".alw-dialog")?.remove(); await refreshLegalTemplates();
          global.safeAionDesktopMessage?.("This exact template version is withdrawn. Its history remains preserved.", "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const templateInstanceForm = event.target.closest?.("[data-aion-legal-template-instance-form]");
    if (templateInstanceForm) {
      event.preventDefault();
      const data = new FormData(templateInstanceForm); const values = {};
      templateInstanceForm.querySelectorAll("[data-variable-name]").forEach((input) => { values[input.dataset.variableName] = input.value; });
      void (async () => {
        try {
          const result = await signingRequest(`/templates/${encodeURIComponent(templateInstanceForm.dataset.templateId)}/instantiate`, {
            values, filename: String(data.get("filename") || "draft.txt"), matter_id: String(data.get("matter_id") || ""),
          });
          templateInstanceForm.closest(".alw-dialog")?.remove(); await refreshLegalDocuments();
          const state = readState(); state.activeTab = "documents"; writeState(state); rerender();
          global.safeAionDesktopMessage?.(`${result.document.filename} created as an encrypted, final-review-required draft. Nothing was sent.`, "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const documentReviewForm = event.target.closest?.("[data-aion-legal-document-review-form]");
    if (documentReviewForm) {
      event.preventDefault();
      const data = new FormData(documentReviewForm);
      void (async () => {
        try {
          await signingRequest(`/documents/${encodeURIComponent(documentReviewForm.dataset.documentId)}/classification`, { category: String(data.get("category") || "OTHER") });
          documentReviewForm.closest(".alw-dialog")?.remove();
          await refreshLegalDocuments();
          global.safeAionDesktopMessage?.("Document classification confirmed by a person.", "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const matterLinkForm = event.target.closest?.("[data-aion-legal-link-form]");
    if (matterLinkForm) {
      event.preventDefault(); const workspace = matterLinkForm.closest("[data-aion-legal-matter-workspace]"); const data = new FormData(matterLinkForm);
      void (async () => { try { await signingRequest(`/matters/${encodeURIComponent(workspace.dataset.matterId)}/links`, { record_type: String(data.get("record_type") || ""), reference_id: String(data.get("reference_id") || ""), label: String(data.get("label") || "") }); workspace.closest(".alw-dialog")?.remove(); await refreshLegalMatters(); const item = (legalMatters || []).find((value) => value.matter_id === workspace.dataset.matterId); if (item) openMatterWorkspace(item); } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); } })();
      return;
    }
    const matterObligationForm = event.target.closest?.("[data-aion-legal-obligation-form]");
    if (matterObligationForm) {
      event.preventDefault(); const workspace = matterObligationForm.closest("[data-aion-legal-matter-workspace]"); const data = new FormData(matterObligationForm); const localIso = (value) => value ? new Date(String(value)).toISOString() : null;
      void (async () => { try { const reminder = localIso(data.get("remind_at")); await signingRequest(`/matters/${encodeURIComponent(workspace.dataset.matterId)}/obligations`, { title: String(data.get("title") || ""), obligation_type: String(data.get("obligation_type") || "ACTION"), due_at: localIso(data.get("due_at")), remind_at: reminder ? [reminder] : [] }); workspace.closest(".alw-dialog")?.remove(); await refreshLegalMatters(); const item = (legalMatters || []).find((value) => value.matter_id === workspace.dataset.matterId); if (item) openMatterWorkspace(item); } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); } })();
      return;
    }
    const matterEscalationForm = event.target.closest?.("[data-aion-legal-escalation-form]");
    if (matterEscalationForm) {
      event.preventDefault(); const workspace = matterEscalationForm.closest("[data-aion-legal-matter-workspace]"); const data = new FormData(matterEscalationForm);
      void (async () => { try { await signingRequest(`/matters/${encodeURIComponent(workspace.dataset.matterId)}/professional-escalations`, { reason: String(data.get("reason") || ""), urgency: String(data.get("urgency") || "NORMAL"), requested_professional: String(data.get("requested_professional") || "") }); workspace.closest(".alw-dialog")?.remove(); await refreshLegalMatters(); const item = (legalMatters || []).find((value) => value.matter_id === workspace.dataset.matterId); if (item) openMatterWorkspace(item); global.safeAionDesktopMessage?.("Professional escalation draft recorded. Nothing was sent.", "success"); } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); } })();
      return;
    }
    const recordsForm = event.target.closest?.("[data-aion-legal-records-form]");
    if (recordsForm) {
      event.preventDefault();
      const data = new FormData(recordsForm);
      void (async () => {
        try {
          const id = recordsForm.dataset.recordId;
          const prefix = recordsForm.dataset.recordKind === "matter" ? `/matters/${encodeURIComponent(id)}` : `/envelopes/${encodeURIComponent(id)}`;
          await signingRequest(`${prefix}/records-governance`, {
            retain_until: String(data.get("retain_until") || ""),
            legal_hold: data.get("legal_hold") === "on",
            legal_hold_reason: String(data.get("legal_hold_reason") || ""),
          });
          recordsForm.closest(".alw-dialog")?.remove();
          if (recordsForm.dataset.recordKind === "matter") await refreshLegalMatters(); else await refreshSigningEnvelopes();
          global.safeAionDesktopMessage?.("Legal records controls updated.", "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const envelopeForm = event.target.closest?.("[data-aion-legal-envelope-form]");
    if (envelopeForm) {
      event.preventDefault();
      void (async () => {
        const data = new FormData(envelopeForm);
        try {
          const signers = [{ name: String(data.get("signer_name") || ""), email: String(data.get("signer_email") || ""), role: String(data.get("signer_role") || "Signer"), verification_method: String(data.get("verification_method") || "typed_name_email") }];
          String(data.get("additional_signers") || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean).forEach((line) => { const [name, email, role, verificationMethod] = line.split("|").map((value) => value.trim()); signers.push({ name, email, role: role || "Signer", verification_method: verificationMethod || "typed_name_email" }); });
          await signingRequest("/envelopes", { title: String(data.get("title") || ""), document_content: String(data.get("document_content") || ""), expires_in_days: Number(data.get("expires_in_days") || 14), supersedes_envelope_id: String(data.get("supersedes_envelope_id") || "") || null, signers });
          envelopeForm.closest(".alw-dialog")?.remove(); await refreshSigningEnvelopes();
          global.safeAionDesktopMessage?.("Controlled signature draft created. Nothing has been sent.", "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const deliveryForm = event.target.closest?.("[data-aion-legal-delivery-form]");
    if (deliveryForm) {
      event.preventDefault();
      const data = new FormData(deliveryForm);
      void (async () => {
        try {
          await signingRequest(`/envelopes/${encodeURIComponent(deliveryForm.dataset.envelopeId)}/delivery-outbox/queue`, {
            provider: String(data.get("provider") || ""),
            acknowledge_external_send: data.get("acknowledge_external_send") === "on",
          });
          deliveryForm.closest(".alw-dialog")?.remove();
          await refreshSigningEnvelopes();
          global.safeAionDesktopMessage?.("Signed copies are encrypted in the approved delivery queue. Nothing has been sent yet.", "success");
        } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
      })();
      return;
    }
    const form = event.target.closest?.("[data-aion-legal-matter-form]");
    if (!form) return;
    event.preventDefault();
    const data = new FormData(form);
    void (async () => {
      try {
        await signingRequest("/matters", {
          title: String(data.get("title") || ""), counterparty: String(data.get("counterparty") || ""),
          matter_type: String(data.get("type") || "GENERAL_ADVICE"), risk: String(data.get("risk") || "NORMAL"),
          summary: String(data.get("summary") || ""), jurisdiction: {
            country_code: String(data.get("country_code") || ""), region: String(data.get("region") || ""),
            governing_law: String(data.get("governing_law") || ""), forum: String(data.get("forum") || ""),
            owner_confirmed: data.get("owner_confirmed") === "on",
          },
        });
        form.closest(".alw-dialog")?.remove(); await refreshLegalMatters();
        global.safeAionDesktopMessage?.("Legal matter saved to the protected workspace.", "success");
      } catch (error) { global.safeAionDesktopMessage?.(error.message, "error"); }
    })();
  }, true);

  global.AionLegalWorkspace = { render, readState, refreshSigningEnvelopes, refreshLegalMatters, refreshLegalDocuments, refreshLegalTemplates, selectAndUploadDocument };
})(window);
