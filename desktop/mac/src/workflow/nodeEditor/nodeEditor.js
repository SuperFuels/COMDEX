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

  function getTraceRows() {
    const result = window.__aionWorkflowDryRunResult;
    return Array.isArray(result?.trace) ? result.trace : [];
  }

  function getTraceRowForNode(nodeId) {
    if (!nodeId) return null;

    return [...getTraceRows()]
      .reverse()
      .find((row) => String(row?.node_id || "") === String(nodeId)) || null;
  }

  function renderModal({ nodes = [] } = {}) {
    const nodeId = window.__aionWorkflowNodeEditorOpenId || null;
    if (!nodeId) return "";

    const node = Array.isArray(nodes)
      ? nodes.find((item) => String(item.id) === String(nodeId))
      : null;

    if (!node) return "";

    const traceRow = getTraceRowForNode(nodeId);
    const inputPreview = Array.isArray(traceRow?.input_items_preview)
      ? traceRow.input_items_preview
      : [];
    const outputPreview = Array.isArray(traceRow?.output_items_preview)
      ? traceRow.output_items_preview
      : [];

    const nodeTitle = String(node.title || "Node");
    const nodeType = String(node.type || "Action");

    const parametersHtml =
      window.AionWorkflowNodeEditorConfigRegistry?.renderParameters?.(node) ||
      `<div class="empty-state">No custom parameters for this node yet.</div>`;

    return `
      <section class="aion-node-editor-backdrop" data-aion-node-editor-backdrop="true">
        <div class="aion-node-editor-modal" role="dialog" aria-modal="true">
          <header class="aion-node-editor-header">
            <div>
              <div class="eyebrow">Node editor</div>
              <h2>${escapeHtml(nodeTitle)}</h2>
              <p>${escapeHtml(nodeType)} · ${escapeHtml(node.status || "Dry-run")}</p>
            </div>

            <button
              class="aion-node-editor-close"
              type="button"
              data-aion-node-editor-close="true"
              title="Close"
            >
              ×
            </button>
          </header>

          <div class="aion-node-editor-grid">
            <aside class="aion-node-editor-panel">
              <div class="aion-node-editor-panel-head">
                <strong>Input</strong>
                <span>${escapeHtml(String(inputPreview.length))} item(s)</span>
              </div>
              ${
                inputPreview.length
                  ? `<pre>${escapeHtml(JSON.stringify(inputPreview, null, 2))}</pre>`
                  : `<div class="empty-state">Run Execute workflow to see input data.</div>`
              }
            </aside>

            <main class="aion-node-editor-panel aion-node-editor-parameters">
              <div class="aion-node-editor-panel-head">
                <strong>Parameters</strong>
                <span>Settings</span>
              </div>

              <div class="aion-node-editor-form">
                ${parametersHtml}
              </div>

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
                  data-aion-workflow-node-id="${escapeHtml(node.id)}"
                >
                  Save node
                </button>
              </div>
            </main>

            <aside class="aion-node-editor-panel">
              <div class="aion-node-editor-panel-head">
                <strong>Output</strong>
                <span>${escapeHtml(String(outputPreview.length))} item(s)</span>
              </div>
              ${
                outputPreview.length
                  ? `<pre>${escapeHtml(JSON.stringify(outputPreview, null, 2))}</pre>`
                  : `<div class="empty-state">No output yet.</div>`
              }
            </aside>
          </div>
        </div>
      </section>
    `;
  }

  function installControls(helpers = {}) {
    if (window.__aionWorkflowNodeEditorControlsBound === true) return;
    window.__aionWorkflowNodeEditorControlsBound = true;

    const isEditableNodeEditorTarget = (target) =>
      !!target?.closest?.(
        ".aion-node-editor-modal input, " +
        ".aion-node-editor-modal textarea, " +
        ".aion-node-editor-modal select, " +
        "[data-aion-node-editor-config-input]"
      );

    const stopNodeEditorInputInterception = (event) => {
      if (!isEditableNodeEditorTarget(event.target)) return;

      // Do not preventDefault: the input still needs focus, cursor, selection and typing.
      // Only stop workflow/canvas/global handlers from stealing the event.
      event.stopPropagation();
      event.stopImmediatePropagation?.();
    };

    [
      "pointerdown",
      "pointermove",
      "pointerup",
      "mousedown",
      "mouseup",
      "click",
      "dblclick",
      "keydown",
      "keyup",
      "input",
      "change",
      "beforeinput",
    ].forEach((type) => {
      window.addEventListener(type, stopNodeEditorInputInterception, true);
    });

    const getGraph = helpers.getAionWorkflowDraftState;
    const compileGlyph = helpers.compileAndAttachAionWorkflowGlyph;
    const persist = helpers.persistAionWorkflowDraftState;
    const requestRender = helpers.requestRender;
    const desktopStore = helpers.desktopStore;

    document.addEventListener("dblclick", (event) => {
      const nodeEl = event.target.closest?.("[data-aion-workflow-node-id]");
      if (!nodeEl) return;

      const nodeId = nodeEl.getAttribute("data-aion-workflow-node-id");
      if (!nodeId) return;

      event.preventDefault();
      event.stopPropagation();

      window.__aionWorkflowNodeEditorOpenId = nodeId;
      window.__aionWorkflowSelectedNodeId = nodeId;
      window.__aionWorkflowInspectorOpen = false;
      window.__aionWorkflowPickerMode = null;

      requestRender?.();
    });

    document.addEventListener("click", (event) => {
      const insideModal = event.target.closest?.(".aion-node-editor-modal");
      if (insideModal) {
        event.stopPropagation();
      }

      const closeButton = event.target.closest?.("[data-aion-node-editor-close='true']");
      const backdrop = event.target.matches?.("[data-aion-node-editor-backdrop='true']");

      if (closeButton || backdrop) {
        event.preventDefault();
        event.stopPropagation();

        window.__aionWorkflowNodeEditorOpenId = null;
        requestRender?.();
        return;
      }

      const saveButton = event.target.closest?.("[data-aion-node-editor-save='true']");
      if (saveButton) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation?.();

        const nodeId = saveButton.getAttribute("data-aion-workflow-node-id");
        const graph = getGraph?.();
        if (!graph) return;

        const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
        const node = nodes.find((item) => String(item.id) === String(nodeId));
        if (!node) return;

        const config = { ...(node.config || {}) };

        document
          .querySelectorAll("[data-aion-node-editor-config-input]")
          .forEach((input) => {
            const inputNodeId = input.getAttribute("data-aion-workflow-node-id");
            if (String(inputNodeId) !== String(nodeId)) return;

            const key = input.getAttribute("data-aion-node-editor-config-input");
            if (!key) return;

            const rawValue = input.value;
            config[key] = key === "seconds" ? Number(rawValue || 0) : rawValue;
          });

        window.__aionWorkflowGraph = {
          ...graph,
          nodes: nodes.map((item) =>
            String(item.id) === String(nodeId)
              ? {
                  ...item,
                  config,
                }
              : item,
          ),
        };

        compileGlyph?.(window.__aionWorkflowGraph);
        persist?.();

        desktopStore?.patch?.({
          message: `Saved node config: ${node.title || "Node"} ${JSON.stringify(config)}`,
          messageTone: "success",
        });

        requestRender?.();
        return;
      }

      const testButton = event.target.closest?.("[data-aion-node-editor-test='true']");
      if (testButton) {
        event.preventDefault();
        event.stopPropagation();

        desktopStore?.patch?.({
          message: "Use Execute workflow for now. Per-node test runner comes next.",
          messageTone: "info",
        });
      }
    });
  }

  window.AionWorkflowNodeEditor = {
    renderModal,
    installControls,
    getTraceRows,
    getTraceRowForNode,
  };
})();
