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

  function canRender(node) {
    const haystack = [
      node?.title,
      node?.type,
      node?.app,
      node?.connector,
      node?.action_id,
      node?.module_id,
      node?.kind,
      node?.config?.title,
      node?.config?.type,
      node?.config?.app,
      node?.config?.connector,
      node?.config?.action_id,
      node?.config?.module_id,
      node?.config?.kind,
    ].map((value) => String(value || "").toLowerCase()).join(" ");

    return haystack.includes("merge") || haystack.includes("logic.merge");
  }

  function render(node) {
    const config = node?.config && typeof node.config === "object" ? node.config : {};
    const strategy = config.merge_strategy || "append_items";

    return `
      <div class="aion-node-editor-note">
        Merge collects items from multiple incoming route branches and emits one merged output item.
      </div>

      <label class="aion-node-editor-field">
        <span>Merge strategy</span>
        <select data-aion-node-editor-config-input="merge_strategy">
          ${[
            ["append_items", "Append all incoming items"],
            ["first_available", "First available branch"],
            ["wait_for_all", "Wait for all branches"],
            ["merge_by_key", "Merge by key"],
          ].map(([value, label]) => `
            <option value="${escapeHtml(value)}" ${String(strategy) === value ? "selected" : ""}>
              ${escapeHtml(label)}
            </option>
          `).join("")}
        </select>
      </label>

      <label class="aion-node-editor-field">
        <span>Merge key</span>
        <input
          data-aion-node-editor-config-input="merge_key"
          value="${escapeHtml(config.merge_key || "")}"
          placeholder="email, customer_id, lead_id"
        />
        <em>Used later for merge_by_key.</em>
      </label>
    `;
  }

  window.AionWorkflowNodeEditorConfigs = window.AionWorkflowNodeEditorConfigs || [];
  window.AionWorkflowNodeEditorConfigs.push({
    id: "merge",
    canRender,
    render,
  });
})();
