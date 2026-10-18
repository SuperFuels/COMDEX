(function () {
  "use strict";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function getValue(node, key, fallback = "") {
    return node?.config?.[key] ?? node?.[key] ?? fallback;
  }

  function renderGenericParameters(node) {
    const type = getValue(node, "type", node?.type || "step");
    const connector = getValue(node, "connector", node?.connector || node?.app || "Aion");
    const actionId = getValue(
      node,
      "action_id",
      node?.action_id || node?.action || "gmail.watch_emails, tools.set_variable, text.match_pattern",
    );
    const title = getValue(node, "title", node?.title || "Choose");
    const fields = getValue(node, "fields", "sender, subject, body, received_at");
    const outputs = getValue(node, "outputs", "new_email_event, customer_details, draft_reply");
    const approval = getValue(node, "approval_requirement", "auto");

    return `
      <label class="aion-node-editor-field">
        <span>What kind of step is this?</span>
        <select data-aion-node-editor-config-input="type">
          ${["step", "trigger", "app_action", "logic", "ai", "code", "email"]
            .map(
              (option) => `
                <option value="${escapeHtml(option)}" ${String(type) === option ? "selected" : ""}>
                  ${escapeHtml(option.replaceAll("_", " "))}
                </option>
              `,
            )
            .join("")}
        </select>
      </label>

      <label class="aion-node-editor-field">
        <span>Use this app / system</span>
        <input data-aion-node-editor-config-input="connector" value="${escapeHtml(connector)}" />
      </label>

      <label class="aion-node-editor-field">
        <span>Action ID</span>
        <input
          data-aion-node-editor-config-input="action_id"
          value="${escapeHtml(actionId)}"
          placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
        />
      </label>

      <label class="aion-node-editor-field">
        <span>Step label</span>
        <input data-aion-node-editor-config-input="title" value="${escapeHtml(title)}" />
      </label>

      <label class="aion-node-editor-field">
        <span>Aion should collect / use</span>
        <textarea data-aion-node-editor-config-input="fields">${escapeHtml(fields)}</textarea>
      </label>

      <label class="aion-node-editor-field">
        <span>Pass this to next step as</span>
        <textarea data-aion-node-editor-config-input="outputs">${escapeHtml(outputs)}</textarea>
      </label>

      <label class="aion-node-editor-field">
        <span>Approval / safety</span>
        <select data-aion-node-editor-config-input="approval_requirement">
          ${["auto", "review", "approval_required"]
            .map(
              (option) => `
                <option value="${escapeHtml(option)}" ${String(approval) === option ? "selected" : ""}>
                  ${escapeHtml(option.replaceAll("_", " "))}
                </option>
              `,
            )
            .join("")}
        </select>
      </label>

      <div class="aion-node-editor-actions">
        <button
          class="secondary-btn"
          type="button"
          data-aion-node-editor-test="true"
        >
          Test node
        </button>

        <button
          class="primary-btn"
          type="button"
          data-aion-node-editor-save="true"
          data-aion-workflow-node-id="${escapeHtml(node?.id || "")}"
        >
          Save node
        </button>
      </div>
    `;
  }

  window.AionWorkflowNodeEditorConfigRegistry = {
    renderParameters(node) {
      const configs = Array.isArray(window.AionWorkflowNodeEditorConfigs)
        ? window.AionWorkflowNodeEditorConfigs
        : [];

      const nodeType = String(node?.type || "").toLowerCase();
      const actionId = String(node?.config?.action_id || node?.action_id || node?.action || "").toLowerCase();
      const connector = String(node?.config?.connector || node?.connector || node?.app || "").toLowerCase();

      const match = configs.find((config) => {
        if (typeof config?.matches === "function") {
          return config.matches(node);
        }

        if (typeof config?.canRender === "function") {
          try {
            return config.canRender(node);
          } catch {
            return false;
          }
        }

        const types = Array.isArray(config?.types) ? config.types.map((item) => String(item).toLowerCase()) : [];
        const actions = Array.isArray(config?.actions) ? config.actions.map((item) => String(item).toLowerCase()) : [];
        const connectors = Array.isArray(config?.connectors)
          ? config.connectors.map((item) => String(item).toLowerCase())
          : [];

        return (
          types.includes(nodeType) ||
          actions.includes(actionId) ||
          connectors.includes(connector)
        );
      });

      if (match?.renderParameters) {
        return match.renderParameters(node);
      }

      if (match?.render) {
        const rendered = match.render(node);
        if (String(rendered || "").trim()) {
          return rendered;
        }
      }

      return renderGenericParameters(node);
    },
  };
})();
