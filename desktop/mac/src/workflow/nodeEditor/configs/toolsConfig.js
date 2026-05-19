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

  function fieldHtml({ key, label, value, placeholder = "", multiline = false, help = "", nodeId = "" }) {
    const common = `
      data-aion-node-editor-config-input="${escapeHtml(key)}"
      data-aion-workflow-node-id="${escapeHtml(nodeId)}"
      placeholder="${escapeHtml(placeholder)}"
    `;

    return `
      <label class="aion-node-editor-field">
        <span>${escapeHtml(label)}</span>
        ${
          multiline
            ? `<textarea ${common}>${escapeHtml(value || "")}</textarea>`
            : `<input ${common} value="${escapeHtml(value || "")}" />`
        }
        ${help ? `<em>${escapeHtml(help)}</em>` : ""}
      </label>
    `;
  }

  function canRender(node) {
    return String(node?.type || "") === "Tools";
  }

  function render(node) {
    const config = node?.config && typeof node.config === "object" ? node.config : {};
    const title = String(node?.title || "");
    const nodeId = String(node?.id || "");

    if (title === "Set variable") {
      return `
        ${fieldHtml({
          nodeId,
          key: "key",
          label: "Variable key",
          value: config.key || "lead_summary",
          placeholder: "lead_summary",
        })}
        ${fieldHtml({
          nodeId,
          key: "value",
          label: "Value template",
          value: config.value || "{{customer_name}} / {{email}} / {{subject}}",
          placeholder: "{{customer_name}} / {{email}} / {{subject}}",
          multiline: true,
          help: "Uses values from the previous step payload, for example {{customer_name}}, {{email}}, {{subject}}, or {{previous_step.output}}.",
        })}
      `;
    }

    if (title === "Get variable") {
      return fieldHtml({
        nodeId,
        key: "key",
        label: "Variable key",
        value: config.key || "workflow_variable",
        placeholder: "workflow_variable",
      });
    }

    if (title === "Compose string") {
      return fieldHtml({
        nodeId,
        key: "template",
        label: "Template",
        value: config.template || "Variable value: {{value}}",
        placeholder: "Variable value: {{value}}",
        multiline: true,
        help: "Use values from the previous step payload, for example {{value}}, {{first_match}}, {{route}}, or {{urgency}}.",
      });
    }

    if (title === "Sleep / delay") {
      return fieldHtml({
        nodeId,
        key: "seconds",
        label: "Seconds",
        value: String(config.seconds || 5),
        placeholder: "5",
        help: "Preview only. Does not block the app during dry-run.",
      });
    }

    return "";
  }

  window.AionWorkflowNodeEditorConfigs = window.AionWorkflowNodeEditorConfigs || [];
  window.AionWorkflowNodeEditorConfigs.push({
    id: "tools",
    canRender,
    render,
  });
})();
