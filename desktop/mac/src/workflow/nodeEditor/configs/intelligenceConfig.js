(function () {
  "use strict";

  const VAULT_BINDINGS_URL = "http://127.0.0.1:8080/api/vault/aion-flow/bindings";
  let bindingCache = [];
  let bindingLoad = null;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function configFor(node) {
    return node?.config && typeof node.config === "object" ? node.config : {};
  }

  function canRender(node) {
    const config = configFor(node);
    const moduleId = String(config.module_id || node?.module_id || "");
    return config.intelligence_stack === true || moduleId.startsWith("intelligence.");
  }

  const FIELD_COPY = {
    model_manifest_id: ["Model", "Select a signed model manifest already installed or registered with this brain."],
    version: ["Model version", "Pin the tested model version; upgrades should create a new comparison run."],
    temperature: ["Creativity / temperature", "Lower values are more repeatable. Use 0–0.3 for most business work."],
    context_limit: ["Maximum context tokens", "Hard ceiling for the context supplied to this model invocation."],
    structured_output: ["Require structured output", "Require the model to return the declared machine-readable result."],
    endpoint_binding_ref: ["Private endpoint credential", "Choose an opaque vault:// binding. Never paste an API key here."],
    active_space: ["Active space", "The Personal, Workspace or Boardroom boundary in which this route is allowed to work."],
    purpose: ["Permitted purpose", "The specific purpose AION must admit before any model receives context."],
    memory_scope: ["Memory scope", "Use only the minimum memory required for this task."],
    retention: ["Retention", "How long working context may remain associated with this workflow."],
    query: ["Query / context request", "Describe exactly what this node should retrieve or ask."],
    include: ["Include", "One permitted field, source or Business Map region per line."],
    exclude: ["Exclude", "One prohibited field or region per line."],
    minimum_context: ["Minimum context only", "Prevent unnecessary business context from entering the route."],
    region: ["Hosting region", "The approved compute or data-residency region."],
    timeout_seconds: ["Timeout (seconds)", "Stop the provider call when this ceiling is reached."],
    harness_manifest_id: ["Harness", "Select the signed, versioned harness used independently of the model."],
    allowed_tools: ["Allowed tools", "One explicitly allowed tool identifier per line."],
    rollback_version: ["Rollback version", "Known-safe harness version used if this release is withdrawn."],
    target: ["Compute destination", "Choose where this work will run."],
    residency: ["Data residency", "Where data is permitted to be processed and retained."],
    accelerator: ["Accelerator", "CPU, Apple silicon, NVIDIA, or another qualified target."],
    memory_bytes: ["Memory ceiling (bytes)", "Maximum working memory available to this compute job."],
    network_policy: ["Network policy", "The egress boundary enforced for this compute job."],
    max_seconds: ["Maximum runtime (seconds)", "A hard time limit for this node or deliberation loop."],
    max_cost: ["Maximum cost", "A hard monetary ceiling. Zero means no paid compute is authorized."],
    max_energy_wh: ["Maximum energy (Wh)", "Optional energy ceiling for local or customer-owned compute."],
    max_concurrency: ["Maximum concurrent jobs", "Hard parallel-execution ceiling."],
    source_bindings: ["Evidence sources", "One permitted evidence source binding per line."],
    freshness_seconds: ["Maximum evidence age (seconds)", "Reject evidence older than this limit."],
    required_confidence: ["Required confidence", "Minimum accepted evidence confidence from 0 to 1."],
    fail_closed: ["Fail closed", "Stop rather than inventing or silently weakening the requirement."],
    validator_type: ["Validation method", "The deterministic validation performed outside the model."],
    rule_ref: ["Validation rule", "Reference to the schema, calculation, policy or business rule."],
    participant_bindings: ["Independent participants", "One model or specialist binding per line."],
    independence_required: ["Require independent participants", "Avoid treating duplicated model routes as independent agreement."],
    max_iterations: ["Maximum iterations", "Hard ceiling preventing unbounded refinement loops."],
    exit_criteria: ["Exit criteria", "The measurable condition that ends deliberation."],
    arbitration: ["Disagreement handling", "How conflicting candidates are reconciled."],
    data_classes: ["Data classes", "One class of information allowed through this boundary per line."],
    destination: ["Destination", "Exact external or customer-controlled destination receiving the data."],
    redact: ["Redact", "One field or data class to remove per line."],
    encryption_required: ["Require encryption", "Block the route unless transport protection is verified."],
    fallback_may_expand_disclosure: ["Allow broader fallback disclosure", "Keep disabled unless a separately reviewed policy permits it."],
    approval_surface: ["Approval surface", "The trusted private surface where the person reviews the exact action."],
    approval_ttl_seconds: ["Approval lifetime (seconds)", "The exact authorization expires after this interval."],
    capability_id: ["Capability", "The signed capability that may perform the authorized action."],
    idempotency_required: ["Require idempotency", "Prevent retries from repeating the same external effect."],
    verification_method: ["Verification method", "How AION proves the real-world outcome independently of the proposal."],
    receipt_scope: ["Receipt contents", "One normalized result or evidence field per line."],
  };

  function titleFor(name) {
    return FIELD_COPY[name]?.[0] || String(name || "Setting").replaceAll("_", " ");
  }

  function helpFor(name, spec) {
    const tailored = FIELD_COPY[name]?.[1];
    if (tailored) return tailored;
    return spec?.required === true ? "Required before this route can be compiled." : "Optional configuration for this node.";
  }

  function defaultValue(spec = {}) {
    if (Object.prototype.hasOwnProperty.call(spec, "default")) return spec.default;
    if (spec.type === "boolean") return false;
    if (spec.type === "array") return [];
    return "";
  }

  function valueFor(node, name, spec) {
    const config = configFor(node);
    if (Object.prototype.hasOwnProperty.call(config, name)) return config[name];
    if (Object.prototype.hasOwnProperty.call(config.intelligence_settings || {}, name)) {
      return config.intelligence_settings[name];
    }
    return defaultValue(spec);
  }

  function renderField(node, name, spec = {}) {
    const value = valueFor(node, name, spec);
    const common = `data-aion-node-editor-config-input="${escapeHtml(name)}" data-aion-intelligence-canonical-field="true"`;
    const required = spec.required === true ? " <b>Required</b>" : "";
    let control = "";

    if (spec.type === "boolean") {
      control = `<select ${common}><option value="true" ${value === true || value === "true" ? "selected" : ""}>Yes</option><option value="false" ${value !== true && value !== "true" ? "selected" : ""}>No</option></select>`;
    } else if (spec.type === "enum") {
      control = `<select ${common}>${(spec.values || []).map((item) => `<option value="${escapeHtml(item)}" ${String(value) === String(item) ? "selected" : ""}>${escapeHtml(String(item).replaceAll("_", " "))}</option>`).join("")}</select>`;
    } else if (spec.type === "array") {
      control = `<textarea ${common} data-aion-intelligence-value-type="array" placeholder="One value per line">${escapeHtml(Array.isArray(value) ? value.join("\n") : value)}</textarea>`;
    } else if (spec.type === "vault_reference") {
      const current = String(value || "");
      control = `
        <div class="aion-vault-binding-picker" data-aion-vault-binding-picker="${escapeHtml(name)}">
          <div class="aion-vault-binding-picker__select-row">
            <select ${common} data-aion-vault-reference="true" data-aion-vault-selected-reference="${escapeHtml(current)}">
              <option value="">Choose a protected credential…</option>
              ${current ? `<option value="${escapeHtml(current)}" selected>${escapeHtml(current)} · loading…</option>` : ""}
            </select>
            <button type="button" class="secondary-btn" data-aion-vault-binding-new="${escapeHtml(name)}">New binding</button>
          </div>
          <div class="aion-vault-binding-picker__status" data-aion-vault-binding-status="${escapeHtml(name)}">Loading safe vault references…</div>
          <div class="aion-vault-binding-picker__create" data-aion-vault-binding-create-panel="${escapeHtml(name)}" hidden>
            <label><span>Binding name</span><input type="text" maxlength="80" autocomplete="off" data-aion-vault-binding-id placeholder="for example gemini-research" /></label>
            <label><span>Provider or destination</span><select data-aion-vault-binding-provider>
              <option value="gemini">Gemini</option><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option>
              <option value="private_endpoint">Private endpoint</option><option value="nvidia_nim">NVIDIA NIM</option>
              <option value="aws">AWS</option><option value="google_cloud">Google Cloud</option><option value="azure">Azure</option>
              <option value="prem">Prem</option><option value="connector">Business connector</option><option value="other">Other</option>
            </select></label>
            <label><span>Display label</span><input type="text" maxlength="100" autocomplete="off" data-aion-vault-binding-label placeholder="Private research model" /></label>
            <label><span>Credential</span><input type="password" maxlength="65536" autocomplete="new-password" data-aion-vault-binding-secret placeholder="Stored immediately in the encrypted mother vault" /></label>
            <p>Only the resulting opaque reference is attached to this node. The credential is never written to the canvas, workflow history, logs or receipts.</p>
            <div><button type="button" class="primary-btn" data-aion-vault-binding-create="${escapeHtml(name)}">Create protected binding</button><button type="button" class="secondary-btn" data-aion-vault-binding-cancel="${escapeHtml(name)}">Cancel</button></div>
          </div>
        </div>`;
    } else {
      const numeric = spec.type === "number" || spec.type === "integer";
      control = `<input ${common} type="${numeric ? "number" : "text"}" value="${escapeHtml(value)}" ${numeric ? 'step="any"' : ""} ${spec.minimum !== undefined ? `min="${escapeHtml(spec.minimum)}"` : ""} ${spec.maximum !== undefined ? `max="${escapeHtml(spec.maximum)}"` : ""}/>`;
    }

    const tag = spec.type === "vault_reference" ? "div" : "label";
    return `<${tag} class="aion-node-editor-field aion-intelligence-config-field"><span>${escapeHtml(titleFor(name))}${required}</span>${control}<em>${escapeHtml(helpFor(name, spec))}</em></${tag}>`;
  }

  function render(node) {
    const config = configFor(node);
    const schema = config.config_schema && typeof config.config_schema === "object" ? config.config_schema : {};
    const fields = Object.entries(schema).map(([name, spec]) => renderField(node, name, spec || {})).join("");
    const subgroup = config.subgroup || "Intelligence Stack";

    return `
      <section class="aion-intelligence-native-config" data-aion-intelligence-config-native="true">
        <div class="aion-intelligence-native-config__head">
          <div><small>${escapeHtml(subgroup)}</small><strong>${escapeHtml(node?.title || "Intelligence node")}</strong></div>
          <span>${escapeHtml(config.location || "unspecified")}</span>
        </div>
        <p>${escapeHtml(node?.meta || "Configure this governed intelligence step.")}</p>
        <div class="aion-intelligence-native-config__badges">
          <span>Credentials · ${escapeHtml(config.credentials || "none")}</span>
          <span>Cost · ${escapeHtml(config.estimated_cost || "unknown")}</span>
          <span>Risk · ${escapeHtml(config.risk || "unknown")}</span>
          <span>${config.causes_external_effect ? "External effect possible" : "No external effect"}</span>
        </div>
        <div class="aion-intelligence-native-config__notice">Only the declared data classes may enter this node. Raw passwords, keys and tokens cannot be stored in the canvas; remote credentials must use a mother-brain vault reference.</div>
        <div class="aion-intelligence-native-config__fields">${fields || '<div class="empty-state">This node has no configurable parameters.</div>'}</div>
        <div class="aion-node-editor-actions">
          <button class="secondary-btn" type="button" data-aion-node-editor-test="true">Validate configuration</button>
          <button class="primary-btn" type="button" data-aion-node-editor-save="true" data-aion-workflow-node-id="${escapeHtml(node?.id || "")}">Save node</button>
        </div>
      </section>
    `;
  }

  function secretShaped(value) {
    return /(?:sk-[a-z0-9_-]{12,}|AIza[a-z0-9_-]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:password|api[_ -]?key|secret|token)\s*[:=]\s*\S+)/i.test(String(value || ""));
  }

  function describeBinding(binding) {
    const label = binding.label || binding.binding_id || "Protected credential";
    return `${label} · ${binding.provider || "provider"} · revision ${binding.revision || 1}`;
  }

  function applyBindingsToPickers() {
    document.querySelectorAll("[data-aion-vault-binding-picker]").forEach((picker) => {
      const select = picker.querySelector("select[data-aion-vault-reference='true']");
      const status = picker.querySelector("[data-aion-vault-binding-status]");
      if (!select) return;
      const selected = select.value || select.getAttribute("data-aion-vault-selected-reference") || "";
      const active = bindingCache.filter((item) => item && item.status === "active" && item.reference);
      select.innerHTML = `<option value="">Choose a protected credential…</option>${active.map((item) => `<option value="${escapeHtml(item.reference)}" ${item.reference === selected ? "selected" : ""}>${escapeHtml(describeBinding(item))}</option>`).join("")}${selected && !active.some((item) => item.reference === selected) ? `<option value="${escapeHtml(selected)}" selected>${escapeHtml(selected)} · unavailable</option>` : ""}`;
      if (status) status.textContent = active.length ? `${active.length} protected binding${active.length === 1 ? "" : "s"} available. No secrets are exposed.` : "No protected bindings yet. Create one for this mother brain.";
    });
  }

  async function loadBindings(force = false) {
    if (!force && bindingLoad) return bindingLoad;
    bindingLoad = fetch(VAULT_BINDINGS_URL, { headers: { Accept: "application/json" }, cache: "no-store" })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok || body.ok !== true) throw new Error(body.detail || body.error || "Vault bindings unavailable");
        bindingCache = Array.isArray(body.bindings) ? body.bindings : [];
        applyBindingsToPickers();
        return bindingCache;
      })
      .catch((error) => {
        document.querySelectorAll("[data-aion-vault-binding-status]").forEach((item) => { item.textContent = `Vault unavailable: ${error.message}`; });
        return [];
      })
      .finally(() => { bindingLoad = null; });
    return bindingLoad;
  }

  function panelFor(control) {
    return control.closest?.("[data-aion-vault-binding-picker]") || null;
  }

  document.addEventListener("click", async (event) => {
    const open = event.target.closest?.("[data-aion-vault-binding-new]");
    if (open) {
      event.preventDefault();
      event.stopPropagation();
      const panel = panelFor(open)?.querySelector("[data-aion-vault-binding-create-panel]");
      if (panel) panel.hidden = false;
      return;
    }
    const cancel = event.target.closest?.("[data-aion-vault-binding-cancel]");
    if (cancel) {
      event.preventDefault();
      event.stopPropagation();
      const panel = panelFor(cancel)?.querySelector("[data-aion-vault-binding-create-panel]");
      if (panel) panel.hidden = true;
      return;
    }
    const create = event.target.closest?.("[data-aion-vault-binding-create]");
    if (!create) return;
    event.preventDefault();
    event.stopPropagation();
    const picker = panelFor(create);
    const idInput = picker?.querySelector("[data-aion-vault-binding-id]");
    const providerInput = picker?.querySelector("[data-aion-vault-binding-provider]");
    const labelInput = picker?.querySelector("[data-aion-vault-binding-label]");
    const secretInput = picker?.querySelector("[data-aion-vault-binding-secret]");
    const status = picker?.querySelector("[data-aion-vault-binding-status]");
    const bindingId = String(idInput?.value || "").trim().toLowerCase();
    const secret = String(secretInput?.value || "");
    if (!/^[a-z0-9][a-z0-9_.-]{0,79}$/.test(bindingId)) {
      if (status) status.textContent = "Use a short binding name containing letters, numbers, dots, dashes or underscores.";
      idInput?.focus();
      return;
    }
    if (!secret.trim()) {
      if (status) status.textContent = "Enter the credential that should be protected.";
      secretInput?.focus();
      return;
    }
    if (secretInput) secretInput.value = "";
    create.disabled = true;
    if (status) status.textContent = "Encrypting credential in the mother-brain vault…";
    try {
      const response = await fetch(VAULT_BINDINGS_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json", "X-AION-Vault-Intent": "create-aion-flow-binding-v1" },
        body: JSON.stringify({ binding_id: bindingId, provider: providerInput?.value || "other", label: labelInput?.value || "", secret }),
      });
      const body = await response.json();
      if (!response.ok || body.ok !== true) throw new Error(body.detail || body.error || "Binding could not be created");
      await loadBindings(true);
      const select = picker.querySelector("select[data-aion-vault-reference='true']");
      if (select) {
        select.value = body.binding.reference;
        select.setAttribute("data-aion-vault-selected-reference", body.binding.reference);
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      const panel = picker.querySelector("[data-aion-vault-binding-create-panel]");
      if (panel) panel.hidden = true;
      if (status) status.textContent = `${describeBinding(body.binding)} selected. Only ${body.binding.reference} is stored with this node.`;
    } catch (error) {
      if (status) status.textContent = `Binding not created: ${error.message}`;
    } finally {
      create.disabled = false;
    }
  }, true);

  const pickerObserver = new MutationObserver(() => {
    if (document.querySelector("[data-aion-vault-binding-picker]")) loadBindings();
  });
  pickerObserver.observe(document.documentElement, { childList: true, subtree: true });

  document.addEventListener("input", (event) => {
    const input = event.target.closest?.("[data-aion-intelligence-canonical-field='true']");
    if (!input) return;
    if (secretShaped(input.value)) {
      input.value = "";
      input.setCustomValidity("Raw credentials cannot be stored here. Use a mother-brain vault binding.");
      input.reportValidity?.();
      return;
    }
    if (input.getAttribute("data-aion-vault-reference") === "true" && input.value && !String(input.value).startsWith("vault://")) {
      input.setCustomValidity("Use an opaque vault:// binding reference; never paste the credential.");
      return;
    }
    input.setCustomValidity("");
  }, true);

  window.AionWorkflowNodeEditorConfigs = window.AionWorkflowNodeEditorConfigs || [];
  window.AionWorkflowNodeEditorConfigs.unshift({ id: "intelligence-stack", canRender, render });
})();
