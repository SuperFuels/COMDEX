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

  function fieldHtml({ key, label, value = "", placeholder = "" }) {
    return `
      <label class="aion-node-editor-field">
        <span>${escapeHtml(label)}</span>
        <input
          data-aion-node-editor-config-input="${escapeHtml(key)}"
          value="${escapeHtml(value)}"
          placeholder="${escapeHtml(placeholder)}"
        />
      </label>
    `;
  }

  function selectHtml({ key, label, value = "exists", options = [] }) {
    return `
      <label class="aion-node-editor-field">
        <span>${escapeHtml(label)}</span>
        <select data-aion-node-editor-config-input="${escapeHtml(key)}">
          ${options.map(([optionValue, optionLabel]) => `
            <option value="${escapeHtml(optionValue)}" ${String(value) === String(optionValue) ? "selected" : ""}>
              ${escapeHtml(optionLabel)}
            </option>
          `).join("")}
        </select>
      </label>
    `;
  }

  function canRender(node) {
    const haystack = [
      node?.title,
      node?.type,
      node?.app,
      node?.connector,
      node?.action,
      node?.action_id,
      node?.module_id,
      node?.kind,
      node?.config?.title,
      node?.config?.type,
      node?.config?.app,
      node?.config?.connector,
      node?.config?.action,
      node?.config?.action_id,
      node?.config?.module_id,
      node?.config?.kind,
    ]
      .map((value) => String(value || "").toLowerCase())
      .join(" ");

    return (
      haystack.includes("if") ||
      haystack.includes("else") ||
      haystack.includes("filter") ||
      haystack.includes("logic")
    );
  }

  function render(node) {
    const config = node?.config && typeof node.config === "object" ? node.config : {};

    return `
      ${fieldHtml({
        key: "field",
        label: "Field",
        value: config.field || config.left || "email",
        placeholder: "email",
      })}

      ${selectHtml({
        key: "operator",
        label: "Operator",
        value: config.operator || config.condition || "exists",
        options: [
          ["exists", "Exists"],
          ["missing", "Missing"],
          ["equals", "Equals"],
          ["not_equals", "Not equals"],
          ["contains", "Contains"],
          ["not_contains", "Does not contain"],
          ["starts_with", "Starts with"],
          ["ends_with", "Ends with"],
        ],
      })}

      ${fieldHtml({
        key: "value",
        label: "Value",
        value: config.value || "",
        placeholder: "quote",
      })}

      <div class="aion-node-editor-note">
        Examples: email exists, enquiry contains quote, subject contains villa.
      </div>
    `;
  }

  window.AionWorkflowNodeEditorConfigs = window.AionWorkflowNodeEditorConfigs || [];
  window.AionWorkflowNodeEditorConfigs.push({
    id: "logic",
    canRender,
    render,
  });
})();
