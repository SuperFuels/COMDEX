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
    return String(node?.type || "") === "Text Parser";
  }

  function render(node) {
    const config = node?.config && typeof node.config === "object" ? node.config : {};
    const title = String(node?.title || "");
    const nodeId = String(node?.id || "");

    if (title === "Match pattern") {
      return fieldHtml({
        nodeId,
        key: "pattern",
        label: "Pattern",
        value: config.pattern || "[\\w.+-]+@[\\w-]+(?:\\.[\\w-]+)+",
        placeholder: "example_[a-z]+",
        help: "Regex used to find matching text.",
      });
    }

    if (title === "Replace text") {
      return `
        ${fieldHtml({
          nodeId,
          key: "pattern",
          label: "Pattern",
          value: config.pattern || "Example Customer",
          placeholder: "Example Customer",
        })}
        ${fieldHtml({
          nodeId,
          key: "replacement",
          label: "Replacement",
          value: config.replacement || "Customer",
          placeholder: "Customer",
        })}
      `;
    }

    if (title === "HTML to text") {
      return `
        <div class="aion-node-editor-note">
          Converts HTML-like input into plain text during dry-run.
        </div>
      `;
    }

    if (title === "Extract from HTML") {
      return `
        <div class="aion-node-editor-note">
          Extracts basic links, images, and table rows during dry-run.
        </div>
      `;
    }

    return "";
  }

  window.AionWorkflowNodeEditorConfigs = window.AionWorkflowNodeEditorConfigs || [];
  window.AionWorkflowNodeEditorConfigs.push({
    id: "text_parser",
    canRender,
    render,
  });
})();
