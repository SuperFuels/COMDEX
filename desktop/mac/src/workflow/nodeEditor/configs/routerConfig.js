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

    return haystack.includes("router") || haystack.includes("logic.router");
  }

  function normaliseRoutes(config) {
    if (Array.isArray(config.routes) && config.routes.length) {
      return config.routes;
    }

    return [
      { id: "route_1", label: "1st", match: "" },
      { id: "route_2", label: "2nd", match: "" },
      { id: "route_3", label: "3rd", match: "" },
    ];
  }

  function render(node) {
    const config = node?.config && typeof node.config === "object" ? node.config : {};
    const routes = normaliseRoutes(config);

    return `
      <div class="aion-node-editor-note">
        Router sends the incoming item down one of several labelled routes. In dry-run mode, it emits one preview item per route.
      </div>

      <label class="aion-node-editor-field">
        <span>Route source field</span>
        <input
          data-aion-node-editor-config-input="route_field"
          value="${escapeHtml(config.route_field || "route")}"
          placeholder="route, category, service_type"
        />
        <em>Optional field used later for route matching.</em>
      </label>

      ${routes.map((route, index) => {
        const id = typeof route === "string" ? route : route?.id;
        const label = typeof route === "string" ? route : route?.label;
        const match = typeof route === "string" ? "" : route?.match;

        return `
          <div class="aion-node-editor-note" style="margin-top:12px;">
            <strong>Route ${index + 1}</strong>
          </div>

          <label class="aion-node-editor-field">
            <span>Route ${index + 1} ID</span>
            <input
              data-aion-node-editor-config-input="routes.${index}.id"
              value="${escapeHtml(id || `route_${index + 1}`)}"
              placeholder="route_${index + 1}"
            />
          </label>

          <label class="aion-node-editor-field">
            <span>Route ${index + 1} label</span>
            <input
              data-aion-node-editor-config-input="routes.${index}.label"
              value="${escapeHtml(label || `${index + 1}`)}"
              placeholder="1st, 2nd, urgent, sales"
            />
          </label>

          <label class="aion-node-editor-field">
            <span>Route ${index + 1} match value</span>
            <input
              data-aion-node-editor-config-input="routes.${index}.match"
              value="${escapeHtml(match || "")}"
              placeholder="optional dry-run match value"
            />
          </label>
        `;
      }).join("")}
    `;
  }

  window.AionWorkflowNodeEditorConfigs = window.AionWorkflowNodeEditorConfigs || [];
  window.AionWorkflowNodeEditorConfigs.push({
    id: "router",
    canRender,
    render,
  });
})();
