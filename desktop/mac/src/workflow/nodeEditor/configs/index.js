(function () {
  "use strict";

  window.AionWorkflowNodeEditorConfigRegistry = {
    getRenderer(node) {
      const configs = Array.isArray(window.AionWorkflowNodeEditorConfigs)
        ? window.AionWorkflowNodeEditorConfigs
        : [];

      return configs.find((config) => {
        try {
          return config && typeof config.canRender === "function" && config.canRender(node);
        } catch {
          return false;
        }
      }) || null;
    },

    renderParameters(node) {
      const renderer = this.getRenderer(node);

      if (!renderer || typeof renderer.render !== "function") {
        return `
          <div class="empty-state">
            No custom parameters for this node yet.
          </div>
        `;
      }

      return renderer.render(node);
    },
  };
})();
