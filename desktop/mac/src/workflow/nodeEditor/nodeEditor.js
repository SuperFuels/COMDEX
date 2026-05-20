(function () {
  "use strict";

  const DEFAULT_INPUT_WIDTH = 360;
  const DEFAULT_OUTPUT_WIDTH = 360;
  const MIN_SIDE_WIDTH = 260;
  const MAX_SIDE_WIDTH = 560;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function getGraph() {
    if (typeof window.getAionWorkflowDraftState === "function") {
      try {
        return window.getAionWorkflowDraftState();
      } catch (_) {}
    }

    return window.__aionWorkflowGraph || { nodes: [], edges: [] };
  }

  function getOpenNode(nodes = []) {
    const nodeId = window.__aionWorkflowNodeEditorOpenId || null;
    if (!nodeId) return null;

    return Array.isArray(nodes)
      ? nodes.find((item) => String(item.id) === String(nodeId)) || null
      : null;
  }

  function getNodeRuntime(node) {
    node.runtime = node.runtime || {};
    node.runtime.input_items = Array.isArray(node.runtime.input_items)
      ? node.runtime.input_items
      : [];
    node.runtime.output_items = Array.isArray(node.runtime.output_items)
      ? node.runtime.output_items
      : [];
    node.runtime.execution_status = node.runtime.execution_status || "idle";
    node.runtime.last_run_at = node.runtime.last_run_at || null;
    node.runtime.error = node.runtime.error || null;
    return node.runtime;
  }

  function getTraceRows() {
    const result = window.__aionWorkflowDryRunResult;
    return Array.isArray(result?.trace) ? result.trace : [];
  }

  function getTraceRowForNode(nodeId) {
    if (!nodeId) return null;

    return (
      [...getTraceRows()]
        .reverse()
        .find((row) => String(row?.node_id || "") === String(nodeId)) || null
    );
  }

  function getInputItemsForNode(node, nodes = []) {
    const runtime = getNodeRuntime(node);
    if (Array.isArray(runtime.input_items) && runtime.input_items.length) {
      return runtime.input_items;
    }

    const traceRow = getTraceRowForNode(node.id);
    if (Array.isArray(traceRow?.input_items_preview)) {
      return traceRow.input_items_preview;
    }

    const graph = getGraph();
    const edges = Array.isArray(graph.edges) ? graph.edges : [];
    const incomingEdges = edges.filter((edge) => String(edge.to) === String(node.id));

    if (isMergeNode(node) && incomingEdges.length) {
      return incomingEdges.flatMap((edge) => {
        const previousNode = nodes.find((item) => String(item.id) === String(edge.from));
        const outputItems = previousNode?.runtime?.output_items || [];

        return outputItems.map((item) => ({
          ...item,
          json: {
            ...(item?.json || item || {}),
            _merge_edge: {
              from: edge.from,
              to: edge.to,
              condition: edge.condition || "success",
            },
          },
        }));
      });
    }

    const previousEdge = incomingEdges[0];
    const previousNode = previousEdge
      ? nodes.find((item) => String(item.id) === String(previousEdge.from))
      : null;

    if (previousNode?.runtime?.output_items?.length) {
      return previousNode.runtime.output_items;
    }

    return [];
  }


  function getOutputItemsForNode(node) {
    const runtime = getNodeRuntime(node);
    if (runtime.output_items.length) return runtime.output_items;

    const traceRow = getTraceRowForNode(node.id);
    if (Array.isArray(traceRow?.output_items_preview)) {
      return traceRow.output_items_preview;
    }

    return [];
  }

  function isMergeNode(node) {
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
    ].map((value) => String(value || "").toLowerCase()).join(" ");

    return haystack.includes("merge") || haystack.includes("logic.merge");
  }

  function getIncomingEdgesForNode(node, graph = getGraph()) {
    const edges = Array.isArray(graph.edges) ? graph.edges : [];
    return edges.filter((edge) => String(edge.to || "") === String(node?.id || ""));
  }

  function getInputItemsFromIncomingEdges(node, nodes = [], graph = getGraph()) {
    const incomingEdges = getIncomingEdgesForNode(node, graph);

    return incomingEdges.flatMap((edge) => {
      const previousNode = nodes.find((item) => String(item.id) === String(edge.from));
      const previousRuntime = previousNode?.runtime || {};
      const outputItems = Array.isArray(previousRuntime.output_items)
        ? previousRuntime.output_items
        : [];

      return outputItems.map((item) => ({
        ...(item && typeof item === "object" ? item : { json: item }),
        _aion_merge_edge: {
          from: edge.from,
          to: edge.to,
          condition: edge.condition || "success",
          from_title: previousNode?.title || "",
        },
      }));
    });
  }

  function inferSchema(items) {
    const first = Array.isArray(items) ? items[0] : null;
    const value = first && typeof first === "object" ? first.json || first : first;

    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return [];
    }

    return Object.entries(value).map(([key, sample]) => ({
      key,
      type: Array.isArray(sample) ? "array" : typeof sample,
      sample,
    }));
  }

  function renderIoTabs(kind, active) {
    const tabs = ["schema", "table", "json"];

    return `
      <div class="aion-node-editor-io-tabs">
        ${tabs
          .map(
            (tab) => `
              <button
                type="button"
                class="${active === tab ? "active" : ""}"
                data-aion-node-editor-io-tab="${escapeHtml(kind)}:${escapeHtml(tab)}"
              >
                ${escapeHtml(tab)}
              </button>
            `,
          )
          .join("")}
      </div>
    `;
  }

  function renderSchema(items) {
    const schema = inferSchema(items);

    if (!schema.length) {
      return `
        <div class="empty-state aion-node-editor-empty-centred">
          <strong>No schema yet</strong>
          <span>Run this node or a previous node to generate data.</span>
        </div>
      `;
    }

    return `
      <div class="aion-node-editor-schema-list">
        ${schema
          .map(
            (field) => `
              <div class="aion-node-editor-schema-row">
                <strong>${escapeHtml(field.key)}</strong>
                <span>${escapeHtml(field.type)}</span>
              </div>
            `,
          )
          .join("")}
      </div>
    `;
  }

  function renderTable(items) {
    if (!Array.isArray(items) || !items.length) {
      return `
        <div class="empty-state aion-node-editor-empty-centred">
          <strong>No table data</strong>
          <span>Execute the step to populate rows.</span>
        </div>
      `;
    }

    const rows = items.map((item) =>
      item && typeof item === "object" ? item.json || item : { value: item },
    );

    const columns = Array.from(
      rows.reduce((set, row) => {
        Object.keys(row || {}).forEach((key) => set.add(key));
        return set;
      }, new Set()),
    ).slice(0, 8);

    return `
      <div class="aion-node-editor-table-wrap">
        <table>
          <thead>
            <tr>
              ${columns.map((key) => `<th>${escapeHtml(key)}</th>`).join("")}
            </tr>
          </thead>
          <tbody>
            ${rows
              .slice(0, 50)
              .map(
                (row) => `
                  <tr>
                    ${columns
                      .map((key) => `<td>${escapeHtml(formatCell(row?.[key]))}</td>`)
                      .join("")}
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function formatCell(value) {
    if (value === null || value === undefined) return "—";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function renderJson(items, emptyTitle, emptyText) {
    if (!Array.isArray(items) || !items.length) {
      return `
        <div class="empty-state aion-node-editor-empty-centred">
          <strong>${escapeHtml(emptyTitle)}</strong>
          <span>${escapeHtml(emptyText)}</span>
        </div>
      `;
    }

    return `<pre>${escapeHtml(JSON.stringify(items, null, 2))}</pre>`;
  }

  function renderIoBody(kind, active, items) {
    if (active === "schema") return renderSchema(items);
    if (active === "table") return renderTable(items);

    return renderJson(
      items,
      kind === "input" ? "No input data" : "No output data",
      kind === "input"
        ? "Run previous nodes or execute this node."
        : "Output will appear here once this node is executed.",
    );
  }

  function getActiveIoTab(kind) {
    const store = window.__aionNodeEditorIoTabs || {};
    return store[kind] || "schema";
  }

  function getActiveCenterTab() {
    return window.__aionNodeEditorCenterTab || "parameters";
  }

  function renderParameters(node) {
    return (
      window.AionWorkflowNodeEditorConfigRegistry?.renderParameters?.(node) ||
      `<div class="empty-state">No custom parameters for this node yet.</div>`
    );
  }

  function renderSettings(node) {
    const settings = node.settings || {};
    const nodeVersion = settings.node_version || node.version || "1";

    return `
      <div class="aion-node-editor-settings">
        ${renderCheckboxField("always_output_data", "Always output data", settings.always_output_data)}
        ${renderCheckboxField("execute_once", "Execute once", settings.execute_once)}
        ${renderCheckboxField("retry_on_fail", "Retry on fail", settings.retry_on_fail)}
        ${renderSelectField("on_error", "On error", settings.on_error || "stop", [
          ["stop", "Stop workflow"],
          ["continue", "Continue"],
          ["output_error", "Output error item"],
        ])}

        <label class="aion-node-editor-field">
          <span>Notes</span>
          <textarea data-aion-node-editor-setting-input="notes">${escapeHtml(settings.notes || "")}</textarea>
        </label>

        ${renderCheckboxField("display_note_in_flow", "Display note in flow", settings.display_note_in_flow)}

        <label class="aion-node-editor-field">
          <span>Node version</span>
          <input data-aion-node-editor-setting-input="node_version" value="${escapeHtml(nodeVersion)}" />
        </label>
      </div>
    `;
  }

  function renderCheckboxField(key, label, checked) {
    return `
      <label class="aion-node-editor-check-row">
        <input
          type="checkbox"
          data-aion-node-editor-setting-input="${escapeHtml(key)}"
          ${checked ? "checked" : ""}
        />
        <span>${escapeHtml(label)}</span>
      </label>
    `;
  }

  function renderSelectField(key, label, value, options) {
    return `
      <label class="aion-node-editor-field">
        <span>${escapeHtml(label)}</span>
        <select data-aion-node-editor-setting-input="${escapeHtml(key)}">
          ${options
            .map(
              ([optionValue, optionLabel]) => `
                <option value="${escapeHtml(optionValue)}" ${value === optionValue ? "selected" : ""}>
                  ${escapeHtml(optionLabel)}
                </option>
              `,
            )
            .join("")}
        </select>
      </label>
    `;
  }

  function renderCenterTabs(active) {
    return `
      <div class="aion-node-editor-center-tabs">
        <button
          type="button"
          class="${active === "parameters" ? "active" : ""}"
          data-aion-node-editor-center-tab="parameters"
        >
          Parameters
        </button>
        <button
          type="button"
          class="${active === "settings" ? "active" : ""}"
          data-aion-node-editor-center-tab="settings"
        >
          Settings
        </button>
        <button type="button" class="aion-node-editor-execute" data-aion-node-editor-test="true">
          Execute step
        </button>
      </div>
    `;
  }

  function renderModal({ nodes = [] } = {}) {
    const node = getOpenNode(nodes);
    if (!node) return "";

    const runtime = getNodeRuntime(node);
    const nodeTitle = String(node.title || "Node");
    const nodeType = String(node.type || "Action");

    const inputItems = getInputItemsForNode(node, nodes);
    const outputItems = getOutputItemsForNode(node);

    const inputTab = getActiveIoTab("input");
    const outputTab = getActiveIoTab("output");
    const centerTab = getActiveCenterTab();

    return `
      <section class="aion-node-editor-backdrop" data-aion-node-editor-backdrop="true">
        <div
          class="aion-node-editor-modal"
          role="dialog"
          aria-modal="true"
          style="
            --aion-node-editor-input-width: ${DEFAULT_INPUT_WIDTH}px;
            --aion-node-editor-output-width: ${DEFAULT_OUTPUT_WIDTH}px;
          "
        >
          <header class="aion-node-editor-header">
            <div>
              <div class="eyebrow">Node editor</div>
              <h2>${escapeHtml(nodeTitle)}</h2>
              <p>
                ${escapeHtml(nodeType)} · ${escapeHtml(runtime.execution_status || node.status || "Dry-run")}
                ${runtime.last_run_at ? ` · ${escapeHtml(runtime.last_run_at)}` : ""}
              </p>
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
            <aside class="aion-node-editor-panel aion-node-editor-input-panel">
              <div class="aion-node-editor-panel-head">
                <strong>Input</strong>
                <span>${escapeHtml(String(inputItems.length))} item(s)</span>
              </div>
              ${renderIoTabs("input", inputTab)}
              <div class="aion-node-editor-io-body">
                ${renderIoBody("input", inputTab, inputItems)}
              </div>
            </aside>

            <main class="aion-node-editor-panel aion-node-editor-parameters">
              <div class="aion-node-editor-panel-head">
                <strong>Parameters</strong>
                <span>${centerTab === "settings" ? "Settings" : "Config"}</span>
              </div>

              ${renderCenterTabs(centerTab)}

              <div class="aion-node-editor-form">
                ${centerTab === "settings" ? renderSettings(node) : renderParameters(node)}
              </div>

              ${runtime.error ? `<div class="aion-node-editor-error">${escapeHtml(runtime.error)}</div>` : ""}
            </main>

            <button
              type="button"
              class="aion-node-editor-centre-resizer"
              data-aion-node-editor-centre-resizer="true"
              aria-label="Resize input and output panels"
            >
              <span></span>
            </button>

            <aside class="aion-node-editor-panel aion-node-editor-output-panel">
              <div class="aion-node-editor-panel-head">
                <strong>Output</strong>
                <span>${escapeHtml(String(outputItems.length))} item(s)</span>
              </div>
              ${renderIoTabs("output", outputTab)}
              <div class="aion-node-editor-io-body">
                ${renderIoBody("output", outputTab, outputItems)}
              </div>
            </aside>
          </div>
        </div>
      </section>
    `;
  }

  function patchOpenNode(patch, helpers = {}) {
    const graph = helpers.getAionWorkflowDraftState?.() || getGraph();
    const nodeId = window.__aionWorkflowNodeEditorOpenId;
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];

    graph.nodes = nodes.map((node) => {
      if (String(node.id) !== String(nodeId)) return node;

      return {
        ...node,
        ...patch,
        config: {
          ...(node.config || {}),
          ...(patch.config || {}),
        },
        settings: {
          ...(node.settings || {}),
          ...(patch.settings || {}),
        },
        runtime: {
          ...(node.runtime || {}),
          ...(patch.runtime || {}),
        },
      };
    });

    graph.dirty = true;
    window.__aionWorkflowGraph = graph;

    helpers.compileAndAttachAionWorkflowGlyph?.(graph);
    helpers.persistAionWorkflowDraftState?.();
  }

  function collectConfigFromModal(modal) {
    const config = {};

    modal.querySelectorAll("[data-aion-node-editor-config-input]").forEach((input) => {
      const key = input.getAttribute("data-aion-node-editor-config-input");
      if (!key) return;

      config[key] = input.type === "checkbox" ? input.checked : input.value;
    });

    return config;
  }

  function collectSettingsFromModal(modal) {
    const settings = {};

    modal.querySelectorAll("[data-aion-node-editor-setting-input]").forEach((input) => {
      const key = input.getAttribute("data-aion-node-editor-setting-input");
      if (!key) return;

      settings[key] = input.type === "checkbox" ? input.checked : input.value;
    });

    return settings;
  }

  function getInputJson(item) {
    if (item && typeof item === "object" && Object.prototype.hasOwnProperty.call(item, "json")) {
      return item.json;
    }

    return item;
  }

  function templateValue(template, source = {}) {
    return String(template ?? "").replace(/{{\s*([^}]+)\s*}}/g, (_, rawKey) => {
      const key = String(rawKey || "").trim();
      if (!key) return "";

      if (key === "previous_step.output") return JSON.stringify(source);
      if (Object.prototype.hasOwnProperty.call(source, key)) return source[key] ?? "";

      return "";
    });
  }

  function getPayloadValue(source = {}, path = "") {
    const key = String(path || "").trim();
    if (!key) return "";

    if (Object.prototype.hasOwnProperty.call(source, key)) {
      return source[key];
    }

    return key.split(".").reduce((value, part) => {
      if (value && typeof value === "object" && Object.prototype.hasOwnProperty.call(value, part)) {
        return value[part];
      }
      return undefined;
    }, source);
  }

  function evaluateFilterCondition(source = {}, config = {}) {
    const leftKey =
      normaliseText(config.left) ||
      normaliseText(config.field) ||
      normaliseText(config.key) ||
      "email";

    const operator =
      normaliseText(config.operator) ||
      normaliseText(config.condition) ||
      "exists";

    const expectedRaw =
      config.right ??
      config.value ??
      config.expected ??
      "";

    const actual = getPayloadValue(source, leftKey);
    const actualText = normaliseText(actual);
    const expectedText = normaliseText(templateValue(expectedRaw, source));

    let passed = false;

    if (operator === "exists" || operator === "is_not_empty") {
      passed = actual !== undefined && actual !== null && actualText !== "";
    } else if (operator === "missing" || operator === "is_empty") {
      passed = actual === undefined || actual === null || actualText === "";
    } else if (operator === "equals" || operator === "eq" || operator === "==") {
      passed = actualText === expectedText;
    } else if (operator === "not_equals" || operator === "neq" || operator === "!=") {
      passed = actualText !== expectedText;
    } else if (operator === "contains") {
      passed = actualText.toLowerCase().includes(expectedText.toLowerCase());
    } else if (operator === "not_contains") {
      passed = !actualText.toLowerCase().includes(expectedText.toLowerCase());
    } else if (operator === "starts_with") {
      passed = actualText.toLowerCase().startsWith(expectedText.toLowerCase());
    } else if (operator === "ends_with") {
      passed = actualText.toLowerCase().endsWith(expectedText.toLowerCase());
    } else {
      passed = actual !== undefined && actual !== null && actualText !== "";
    }

    return {
      left: leftKey,
      operator,
      expected: expectedText,
      actual,
      actual_text: actualText,
      passed,
      route: passed ? "true" : "false",
    };
  }

  function normaliseText(value) {
    return String(value ?? "").trim();
  }

  function getActionKey(node) {
    const config = node?.config || {};
    return [
      String(config.action_id || ""),
      String(config.module_id || ""),
      String(config.app || ""),
      String(config.connector || ""),
      String(config.kind || ""),
      String(node?.action_id || ""),
      String(node?.action || ""),
      String(node?.type || ""),
      String(node?.title || ""),
    ]
      .join(" ")
      .toLowerCase();
  }

  function extractEmail(text) {
    return String(text || "").match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/)?.[0] || "";
  }

  function extractPhone(text) {
    return String(text || "").match(/(?:\+?\d[\d\s().-]{7,}\d)/)?.[0] || "";
  }

  function executeGmailWatchNode(node, inputItems) {
    const now = new Date().toISOString();

    return [
      {
        json: {
          id: `dry_email_${Date.now()}`,
          from: "customer@example.com",
          sender_name: "Example Customer",
          subject: "Quote request for villa repair",
          body: "Hi, I need help with a repair at my villa. Can you send me a quote please?",
          received_at: now,
          source: "gmail.watch_emails",
          dry_run: true,
        },
      },
    ];
  }

  function executeAiExtractNode(node, inputItems) {
    const firstInput = getInputJson(inputItems[0]) || {};
    // Only scan human-readable fields.
    // Do not scan JSON.stringify(firstInput), because dry-run ids/timestamps
    // can look like phone numbers.
    const text = [
      firstInput.sender_name,
      firstInput.from,
      firstInput.subject,
      firstInput.body,
      firstInput.text,
      firstInput.message,
      firstInput.enquiry,
    ].filter(Boolean).join("\n");

    return [
      {
        json: {
          customer_name: normaliseText(firstInput.sender_name) || "Example Customer",
          email:
            extractEmail(text) ||
            extractEmail(firstInput.from) ||
            normaliseText(firstInput.email) ||
            normaliseText(firstInput.from) ||
            "",
          phone: extractPhone(text),
          enquiry: normaliseText(firstInput.body) || normaliseText(firstInput.subject) || "Quote request",
          subject: normaliseText(firstInput.subject),
          extracted_at: new Date().toISOString(),
          source: "aion.extract_fields",
          dry_run: true,
        },
      },
    ];
  }

  function executeSetVariableNode(node, inputItems) {
    const config = node.config || {};
    const firstInput = getInputJson(inputItems[0]) || {};

    const key =
      normaliseText(config.key) ||
      normaliseText(config.variable_key) ||
      "workflow_variable";

    const rawTemplate =
      config.value ??
      config.template ??
      config.variable_value ??
      "{{previous_step.output}}";

    const value = templateValue(rawTemplate, firstInput);

    return [
      {
        json: {
          ...firstInput,
          variables: {
            ...(firstInput.variables && typeof firstInput.variables === "object"
              ? firstInput.variables
              : {}),
            [key]: value,
          },
          [key]: value,
          variable_key: key,
          variable_value: value,
          source: "tools.set_variable",
          input_count: inputItems.length,
          executed_at: new Date().toISOString(),
          dry_run: true,
        },
      },
    ];
  }

  function executeIfFilterNode(node, inputItems) {
    const config = node.config || {};
    const firstInput = getInputJson(inputItems[0]) || {};
    const result = evaluateFilterCondition(firstInput, config);

    return [
      {
        json: {
          ...firstInput,
          filter: result,
          passed: result.passed,
          route: result.route,
          condition: {
            left: result.left,
            operator: result.operator,
            expected: result.expected,
            actual: result.actual_text,
          },
          source: "logic.if_filter",
          input_count: inputItems.length,
          executed_at: new Date().toISOString(),
          dry_run: true,
        },
      },
    ];
  }

  function executeRouterNode(node, inputItems) {
    const config = node.config || {};
    const firstInput = getInputJson(inputItems[0]) || {};

    const routes = Array.isArray(config.routes) && config.routes.length
      ? config.routes
      : [
          { id: "route_1", label: "1st" },
          { id: "route_2", label: "2nd" },
          { id: "route_3", label: "3rd" },
        ];

    return routes.map((route, index) => {
      const routeId =
        typeof route === "string"
          ? route
          : String(route?.id || route?.key || route?.condition || `route_${index + 1}`);

      const routeLabel =
        typeof route === "string"
          ? route
          : String(route?.label || route?.name || routeId);

      return {
        json: {
          ...firstInput,
          route: routeId,
          route_label: routeLabel,
          route_index: index,
          routed_by: node.id,
          source: "logic.router",
          input_count: inputItems.length,
          executed_at: new Date().toISOString(),
          dry_run: true,
        },
      };
    });
  }

  function executeMergeNode(node, inputItems) {
    const config = node.config || {};
    const strategy = String(config.merge_strategy || "append_items");

    const mergedItems = Array.isArray(inputItems)
      ? inputItems.map((item) => {
          const json = getInputJson(item) || {};
          return {
            ...json,
            _merge_edge:
              json._merge_edge ||
              item?._aion_merge_edge ||
              item?._merge_edge ||
              null,
          };
        })
      : [];

    const incomingRoutes = mergedItems
      .map((item) => item.route || item._merge_edge?.condition || "")
      .filter(Boolean);

    return [
      {
        json: {
          merged: true,
          merge_strategy: strategy,
          incoming_count: mergedItems.length,
          incoming_routes: incomingRoutes,
          merged_items: mergedItems,
          source: "logic.merge",
          executed_at: new Date().toISOString(),
          dry_run: true,
        },
      },
    ];
  }

  function normaliseIteratorItems(value) {
    if (Array.isArray(value)) return value;

    if (value && typeof value === "object") {
      if (Array.isArray(value.items)) return value.items;
      if (Array.isArray(value.array)) return value.array;
      if (Array.isArray(value.results)) return value.results;
      if (Array.isArray(value.data)) return value.data;
    }

    if (typeof value === "string") {
      try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) return parsed;
        if (parsed && typeof parsed === "object") {
          if (Array.isArray(parsed.items)) return parsed.items;
          if (Array.isArray(parsed.array)) return parsed.array;
          if (Array.isArray(parsed.results)) return parsed.results;
          if (Array.isArray(parsed.data)) return parsed.data;
        }
      } catch (_) {
        return value
          .split(/\n|,/)
          .map((item) => item.trim())
          .filter(Boolean);
      }
    }

    return value === undefined || value === null ? [] : [value];
  }

  function getIteratorArrayFromInput(config = {}, firstInput = {}) {
    const configuredArray = config.array ?? config.source ?? config.items;

    if (Array.isArray(configuredArray)) return configuredArray;

    if (typeof configuredArray === "string") {
      const template = configuredArray.trim();

      if (template === "{{items}}") return normaliseIteratorItems(firstInput.items);
      if (template === "{{array}}") return normaliseIteratorItems(firstInput.array);
      if (template === "{{results}}") return normaliseIteratorItems(firstInput.results);
      if (template === "{{data}}") return normaliseIteratorItems(firstInput.data);

      const keyMatch = template.match(/^\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}$/);
      if (keyMatch) {
        const key = keyMatch[1];
        return normaliseIteratorItems(key.split(".").reduce((value, part) => value?.[part], firstInput));
      }

      return normaliseIteratorItems(templateValue(template, firstInput));
    }

    return normaliseIteratorItems(
      firstInput.items ||
      firstInput.array ||
      firstInput.results ||
      firstInput.data ||
      firstInput.merged_items ||
      firstInput
    );
  }

  function executeIteratorNode(node, inputItems) {
    const config = node.config || {};
    const firstInput = getInputJson(inputItems[0]) || {};

    const items = getIteratorArrayFromInput(config, firstInput);
    const outputKey = normaliseText(config.output || "item") || "item";
    const total = items.length;

    return items.map((value, index) => {
      const itemValue = value && typeof value === "object" && !Array.isArray(value)
        ? value
        : { value };

      return {
        json: {
          ...firstInput,
          [outputKey]: value,
          item: value,
          item_json: itemValue,
          iterator_index: index,
          iterator_number: index + 1,
          iterator_total: total,
          iterated_by: node.id,
          source: "logic.iterator",
          input_count: inputItems.length,
          executed_at: new Date().toISOString(),
          dry_run: true,
        },
      };
    });
  }

  function executeArrayAggregatorNode(node, inputItems) {
    const config = node.config || {};
    const outputKey = normaliseText(config.output || "array") || "array";
    const sourceKey = normaliseText(config.source_key || config.key || "") || "";

    const items = Array.isArray(inputItems) ? inputItems : [];

    const aggregatedItems = items.map((item, index) => {
      const json = getInputJson(item) || {};

      if (sourceKey && json[sourceKey] !== undefined) {
        return json[sourceKey];
      }

      if (json.item !== undefined) return json.item;
      if (json.item_json !== undefined) return json.item_json;

      return json;
    });

    const firstInput = getInputJson(items[0]) || {};

    return [
      {
        json: {
          ...firstInput,
          aggregated: true,
          item_count: aggregatedItems.length,
          [outputKey]: aggregatedItems,
          array: aggregatedItems,
          source: "logic.array_aggregator",
          input_count: items.length,
          executed_at: new Date().toISOString(),
          dry_run: true,
        },
      },
    ];
  }

  function executeRepeaterNode(node, inputItems) {
    const config = node.config || {};
    const rawCount =
      config.repeat_count ??
      config.count ??
      config.times ??
      config.repeats ??
      3;

    const rawMax =
      config.max_repeat_count ??
      config.max_count ??
      25;

    const maxRepeatCount = Math.max(1, Math.min(100, Number(rawMax) || 25));
    const repeatCount = Math.max(0, Math.min(maxRepeatCount, Number(rawCount) || 0));

    const sourceItems = Array.isArray(inputItems) && inputItems.length
      ? inputItems
      : [{ json: {} }];

    const executedAt = new Date().toISOString();

    return sourceItems.flatMap((inputItem, inputIndex) => {
      const inputJson = getInputJson(inputItem) || {};

      return Array.from({ length: repeatCount }, (_, repeatIndex) => ({
        json: {
          ...inputJson,
          repeat_index: repeatIndex,
          repeat_number: repeatIndex + 1,
          repeat_total: repeatCount,
          repeat_input_index: inputIndex,
          repeat_input_total: sourceItems.length,
          repeated_by: node.id,
          source: "logic.repeater",
          input_count: sourceItems.length,
          executed_at: executedAt,
          dry_run: true,
        },
      }));
    });
  }

  function normaliseRuntimeError(value) {
    if (!value) return null;

    if (value instanceof Error) {
      return {
        message: value.message || "Unknown error",
        name: value.name || "Error",
        stack: value.stack || "",
      };
    }

    if (typeof value === "string") {
      return {
        message: value,
      };
    }

    if (typeof value === "object") {
      return {
        message:
          value.message ||
          value.error ||
          value.reason ||
          value.statusText ||
          "Unknown runtime error",
        code: value.code || value.status || value.error_code || "",
        source: value.source || value.node_id || value.action_id || "",
        details: value,
      };
    }

    return {
      message: String(value),
    };
  }

  function executeIgnoreErrorNode(node, inputItems) {
    const items = Array.isArray(inputItems) && inputItems.length
      ? inputItems
      : [{ json: {} }];

    const executedAt = new Date().toISOString();

    return items.map((inputItem, index) => {
      const json = getInputJson(inputItem) || {};
      const originalError =
        normaliseRuntimeError(json.error) ||
        normaliseRuntimeError(json.runtime_error) ||
        normaliseRuntimeError(inputItem?.error) ||
        null;

      return {
        json: {
          ...json,
          ignored_error: true,
          error_was_ignored: Boolean(originalError || json.execution_status === "failed"),
          original_error: originalError,
          recovered: true,
          continue_on_error: true,
          ignore_error_index: index,
          ignore_error_total: items.length,
          ignored_by: node.id,
          source: "logic.ignore_error",
          input_count: items.length,
          executed_at: executedAt,
          dry_run: true,
          error: null,
        },
      };
    });
  }

  function executeCodePreviewNode(node, inputItems) {
    const config = node.config || {};
    const firstInput = getInputJson(inputItems[0]) || {};

    return [
      {
        json: {
          ...firstInput,
          code_preview: true,
          language: config.language || "python",
          result: firstInput,
          source: "code.preview",
          dry_run: true,
        },
      },
    ];
  }

  function executeDraftEmailNode(node, inputItems) {
    const config = node.config || {};
    const firstInput = getInputJson(inputItems[0]) || {};

    const customerName =
      normaliseText(firstInput.customer_name) ||
      normaliseText(firstInput.sender_name) ||
      "there";

    const to =
      normaliseText(templateValue(config.to || "{{email}}", firstInput)) ||
      normaliseText(firstInput.email) ||
      normaliseText(firstInput.from);

    const originalSubject =
      normaliseText(firstInput.subject) ||
      normaliseText(firstInput.enquiry) ||
      "your enquiry";

    const subject =
      normaliseText(templateValue(config.subject || "Re: {{subject}}", firstInput)) ||
      `Re: ${originalSubject}`;

    const defaultBody = [
      `Hi ${customerName},`,
      "",
      "Thanks for your message. We can help with this.",
      "",
      firstInput.enquiry ? `I have noted: ${firstInput.enquiry}` : "",
      "",
      "When would be a good time for us to discuss the job and arrange a quote?",
      "",
      "Kind regards,",
    ].filter((line, index, arr) => {
      // Keep intentional blank lines, but remove the optional blank created by a missing enquiry.
      if (line !== "") return true;
      return arr[index - 1] !== "" && arr[index + 1] !== "";
    }).join("\n");

    const body =
      normaliseText(templateValue(config.body || defaultBody, firstInput)) ||
      defaultBody;

    return [
      {
        json: {
          ...firstInput,
          draft_id: `dry_draft_${Date.now()}`,
          to,
          subject,
          body,
          status: "draft_created",
          source: "gmail.draft_email",
          input_count: inputItems.length,
          created_at: new Date().toISOString(),
          dry_run: true,
        },
      },
    ];
  }

  function executeNodeDryRun(node, inputItems) {
    const config = node.config || {};
    const title = String(config.title || node.title || "").toLowerCase();
    const actionKey = getActionKey(node);

    if (actionKey.includes("gmail.watch") || title.includes("gmail new email")) {
      return executeGmailWatchNode(node, inputItems);
    }

    // Draft/email write nodes must be checked before broad AI/extract matching.
    if (
      actionKey.includes("draft") ||
      actionKey.includes("create_draft") ||
      actionKey.includes("gmail.create_draft") ||
      title.includes("draft email") ||
      title.includes("create draft")
    ) {
      return executeDraftEmailNode(node, inputItems);
    }

    if (
      actionKey.includes("extract") ||
      actionKey.includes("ai.extract") ||
      title.includes("extract fields")
    ) {
      return executeAiExtractNode(node, inputItems);
    }

    if (actionKey.includes("set_variable") || title.includes("set variable")) {
      return executeSetVariableNode(node, inputItems);
    }

    if (
      actionKey.includes("merge") ||
      title.includes("merge")
    ) {
      return executeMergeNode(node, inputItems);
    }

    if (
      actionKey.includes("ignore_error") ||
      actionKey.includes("ignore error") ||
      title.includes("ignore error")
    ) {
      return executeIgnoreErrorNode(node, inputItems);
    }

    if (
      actionKey.includes("repeater") ||
      title.includes("repeater")
    ) {
      return executeRepeaterNode(node, inputItems);
    }

    if (
      actionKey.includes("array_aggregator") ||
      actionKey.includes("array aggregator") ||
      title.includes("array aggregator")
    ) {
      return executeArrayAggregatorNode(node, inputItems);
    }

    if (
      actionKey.includes("iterator") ||
      title.includes("iterator")
    ) {
      return executeIteratorNode(node, inputItems);
    }

    if (
      actionKey.includes("router") ||
      title.includes("router")
    ) {
      return executeRouterNode(node, inputItems);
    }

    if (
      actionKey.includes("if") ||
      actionKey.includes("filter") ||
      title.includes("if") ||
      title.includes("filter")
    ) {
      return executeIfFilterNode(node, inputItems);
    }

    if (
      actionKey.includes("code") ||
      actionKey.includes("python") ||
      title.includes("code") ||
      title.includes("python")
    ) {
      return executeCodePreviewNode(node, inputItems);
    }

    const items = Array.isArray(inputItems) && inputItems.length
      ? inputItems
      : [{ json: {} }];

    const executedAt = new Date().toISOString();

    return items.map((inputItem, index) => {
      const inputJson = getInputJson(inputItem) || {};

      return {
        json: {
          ...inputJson,
          node_id: node.id,
          title: node.title || "Node",
          type: node.type || "Action",
          connector: config.connector || node.connector || node.app || "aion",
          action_id: config.action_id || node.action_id || node.action || "generic.step",
          item_index: index,
          item_number: index + 1,
          item_total: items.length,
          executed_at: executedAt,
          input_count: items.length,
          source: "generic.step",
          dry_run: true,
        },
      };
    });
  }

  function findPreviousConnectedNode(node, nodes, edges) {
    const incoming = edges.find((edge) => String(edge.to) === String(node.id));
    if (!incoming) return null;

    return nodes.find((item) => String(item.id) === String(incoming.from)) || null;
  }

  function executePreviousNodeIfNeeded(node, nodes, edges, helpers = {}) {
    const runtime = getNodeRuntime(node);
    if (Array.isArray(runtime.input_items) && runtime.input_items.length) {
      return runtime.input_items;
    }

    const previousNode = findPreviousConnectedNode(node, nodes, edges);
    if (!previousNode) return runtime.input_items || [];

    const previousRuntime = getNodeRuntime(previousNode);
    if (!Array.isArray(previousRuntime.output_items) || !previousRuntime.output_items.length) {
      const previousInputItems = getInputItemsForNode(previousNode, nodes);
      const previousOutputItems = executeNodeDryRun(previousNode, previousInputItems);
      const executedAt = new Date().toISOString();

      previousRuntime.input_items = previousInputItems;
      previousRuntime.output_items = previousOutputItems;
      previousRuntime.execution_status = "success";
      previousRuntime.last_run_at = executedAt;
      previousRuntime.error = null;
    }

    runtime.input_items = isMergeNode(node)
      ? getInputItemsFromIncomingEdges(node, nodes, { edges })
      : previousRuntime.output_items || [];

    runtime.last_input_at = new Date().toISOString();
    runtime.error = null;

    helpers.compileAndAttachAionWorkflowGlyph?.(helpers.getAionWorkflowDraftState?.() || getGraph());
    helpers.persistAionWorkflowDraftState?.();

    return runtime.input_items;
  }

  function executeOpenNode(helpers = {}) {
    const graph = helpers.getAionWorkflowDraftState?.() || getGraph();
    const nodeId = window.__aionWorkflowNodeEditorOpenId;
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const node = nodes.find((item) => String(item.id) === String(nodeId));

    if (!node) return;

    const inputItems = getInputItemsForNode(node, nodes);
    const executedAt = new Date().toISOString();
    const outputItems = executeNodeDryRun(node, inputItems, executedAt);

    const edges = Array.isArray(graph.edges) ? graph.edges : [];
    const outgoingEdges = edges.filter((edge) => String(edge.from) === String(node.id));

    const nextNodeIds = outgoingEdges.map((edge) => String(edge.to));

    const getOutputItemsForEdge = (edge) => {
      const condition = String(edge?.condition || "").toLowerCase();

      if (condition.startsWith("route_")) {
        return outputItems.filter((item) => {
          const json = getInputJson(item) || {};
          return String(json.route || "").toLowerCase() === condition;
        });
      }

      if (condition === "true" || condition === "false") {
        const routedItems = outputItems.filter((item) => {
          const json = getInputJson(item) || {};
          const route = String(json.route || "").toLowerCase();

          if (route === condition) return true;

          if (typeof json.passed === "boolean") {
            return condition === "true" ? json.passed === true : json.passed === false;
          }

          return false;
        });

        return routedItems.length ? routedItems : outputItems;
      }

      return outputItems;
    };

    const outputItemsByNextNodeId = new Map();

    outgoingEdges.forEach((edge) => {
      const toId = String(edge.to || "");
      if (!toId) return;

      const targetNode = nodes.find((item) => String(item.id) === toId);
      const routedItems = getOutputItemsForEdge(edge);

      const preparedItems = isMergeNode(targetNode)
        ? routedItems.map((item) => {
            const base = item && typeof item === "object" ? item : { json: item };
            const json = base?.json && typeof base.json === "object" ? base.json : {};

            return {
              ...base,
              json: {
                ...json,
                _merge_edge: {
                  from: edge.from,
                  to: edge.to,
                  condition: edge.condition || "success",
                  from_title: node?.title || "",
                },
              },
            };
          })
        : routedItems;

      const currentItems = outputItemsByNextNodeId.get(toId) || [];
      outputItemsByNextNodeId.set(toId, [...currentItems, ...preparedItems]);
    });

    graph.nodes = nodes.map((item) => {
      if (String(item.id) === String(node.id)) {
        return {
          ...item,
          runtime: {
            ...(item.runtime || {}),
            input_items: inputItems,
            output_items: outputItems,
            execution_status: "success",
            last_run_at: executedAt,
            error: null,
          },
        };
      }

      if (nextNodeIds.includes(String(item.id))) {
        const routedInputItems = outputItemsByNextNodeId.get(String(item.id)) || [];
        const existingInputItems = Array.isArray(item.runtime?.input_items)
          ? item.runtime.input_items
          : [];

        const nextInputItems = isMergeNode(item)
          ? (() => {
              const byRoute = new Map();

              [...existingInputItems, ...routedInputItems].forEach((inputItem) => {
                const json = inputItem?.json && typeof inputItem.json === "object"
                  ? inputItem.json
                  : {};

                const routeKey =
                  json?._merge_edge?.condition ||
                  json?.route ||
                  `item_${byRoute.size + 1}`;

                byRoute.set(String(routeKey), inputItem);
              });

              return [...byRoute.values()];
            })()
          : routedInputItems;

        return {
          ...item,
          runtime: {
            ...(item.runtime || {}),
            input_items: nextInputItems,
            execution_status: item.runtime?.execution_status || "idle",
            last_input_at: executedAt,
            error: null,
          },
        };
      }

      return item;
    });

    graph.dirty = true;
    window.__aionWorkflowGraph = graph;

    helpers.compileAndAttachAionWorkflowGlyph?.(graph);
    helpers.persistAionWorkflowDraftState?.();

    window.__aionNodeEditorIoTabs = {
      ...(window.__aionNodeEditorIoTabs || {}),
      output: "json",
    };

    helpers.requestRender?.();
  }

  function installResizeControls() {
    if (window.__aionNodeEditorResizeControlsBound === true) return;
    window.__aionNodeEditorResizeControlsBound = true;

    let drag = null;

    document.addEventListener(
      "pointerdown",
      (event) => {
        const handle = event.target.closest?.("[data-aion-node-editor-centre-resizer='true']");
        if (!handle) return;

        const modal = handle.closest(".aion-node-editor-modal");
        if (!modal) return;

        const currentInput = Number(
          parseFloat(getComputedStyle(modal).getPropertyValue("--aion-node-editor-input-width")) ||
            DEFAULT_INPUT_WIDTH,
        );

        const currentOutput = Number(
          parseFloat(getComputedStyle(modal).getPropertyValue("--aion-node-editor-output-width")) ||
            DEFAULT_OUTPUT_WIDTH,
        );

        drag = {
          modal,
          startX: event.clientX,
          input: currentInput,
          output: currentOutput,
        };

        handle.setPointerCapture?.(event.pointerId);
        event.preventDefault();
        event.stopPropagation();
      },
      true,
    );

    document.addEventListener(
      "pointermove",
      (event) => {
        if (!drag) return;

        const dx = event.clientX - drag.startX;
        const input = Math.max(MIN_SIDE_WIDTH, Math.min(MAX_SIDE_WIDTH, drag.input + dx));
        const output = Math.max(MIN_SIDE_WIDTH, Math.min(MAX_SIDE_WIDTH, drag.output - dx));

        drag.modal.style.setProperty("--aion-node-editor-input-width", `${input}px`);
        drag.modal.style.setProperty("--aion-node-editor-output-width", `${output}px`);

        event.preventDefault();
      },
      true,
    );

    document.addEventListener(
      "pointerup",
      () => {
        drag = null;
      },
      true,
    );

    document.addEventListener(
      "pointercancel",
      () => {
        drag = null;
      },
      true,
    );
  }

  function installControls(helpers = {}) {
    if (window.__aionWorkflowNodeEditorControlsBound === true) return;
    window.__aionWorkflowNodeEditorControlsBound = true;

    installResizeControls();

    const isEditableNodeEditorTarget = (target) =>
      !!target?.closest?.(
        ".aion-node-editor-modal input, " +
          ".aion-node-editor-modal textarea, " +
          ".aion-node-editor-modal select, " +
          "[data-aion-node-editor-config-input]",
      );

    document.addEventListener(
      "pointerdown",
      (event) => {
        if (isEditableNodeEditorTarget(event.target)) {
          event.stopPropagation();
          event.stopImmediatePropagation?.();
        }
      },
      true,
    );

    document.addEventListener(
      "mousedown",
      (event) => {
        if (isEditableNodeEditorTarget(event.target)) {
          event.stopPropagation();
          event.stopImmediatePropagation?.();
        }
      },
      true,
    );

    document.addEventListener(
      "click",
      (event) => {
        if (isEditableNodeEditorTarget(event.target)) {
          event.stopPropagation();
        }
      },
      true,
    );

    document.addEventListener(
      "keydown",
      (event) => {
        if (isEditableNodeEditorTarget(event.target)) {
          event.stopPropagation();
          event.stopImmediatePropagation?.();
        }
      },
      true,
    );

    document.addEventListener(
      "keyup",
      (event) => {
        if (isEditableNodeEditorTarget(event.target)) {
          event.stopPropagation();
          event.stopImmediatePropagation?.();
        }
      },
      true,
    );

    document.addEventListener(
      "click",
      (event) => {
        const ioTab = event.target.closest?.("[data-aion-node-editor-io-tab]");
        if (ioTab) {
          event.preventDefault();
          event.stopPropagation();

          const [kind, tab] = String(ioTab.getAttribute("data-aion-node-editor-io-tab") || "").split(":");
          window.__aionNodeEditorIoTabs = {
            ...(window.__aionNodeEditorIoTabs || {}),
            [kind]: tab || "schema",
          };

          helpers.requestRender?.();
          return;
        }

        const centerTab = event.target.closest?.("[data-aion-node-editor-center-tab]");
        if (centerTab) {
          event.preventDefault();
          event.stopPropagation();

          window.__aionNodeEditorCenterTab =
            centerTab.getAttribute("data-aion-node-editor-center-tab") || "parameters";

          helpers.requestRender?.();
          return;
        }

        const close = event.target.closest?.("[data-aion-node-editor-close='true']");
        if (close) {
          event.preventDefault();
          event.stopPropagation();

          window.__aionWorkflowNodeEditorOpenId = null;
          helpers.requestRender?.();
          return;
        }

        const save = event.target.closest?.("[data-aion-node-editor-save='true']");
        if (save) {
          event.preventDefault();
          event.stopPropagation();

          const modal = save.closest(".aion-node-editor-modal");
          patchOpenNode(
            {
              config: collectConfigFromModal(modal),
              settings: collectSettingsFromModal(modal),
            },
            helpers,
          );

          helpers.requestRender?.();
          return;
        }

        const test = event.target.closest?.("[data-aion-node-editor-test='true']");
        if (test) {
          event.preventDefault();
          event.stopPropagation();

          const modal = test.closest(".aion-node-editor-modal");
          const liveConfig = collectConfigFromModal(modal);
          const liveSettings = collectSettingsFromModal(modal);

          patchOpenNode(
            {
              config: liveConfig,
              settings: liveSettings,
            },
            helpers,
          );

          const graph = helpers.getAionWorkflowDraftState?.() || getGraph();
          const nodeId = window.__aionWorkflowNodeEditorOpenId;
          const node = Array.isArray(graph.nodes)
            ? graph.nodes.find((item) => String(item.id) === String(nodeId))
            : null;

          if (node) {
            node.config = {
              ...(node.config || {}),
              ...liveConfig,
            };
            node.settings = {
              ...(node.settings || {}),
              ...liveSettings,
            };
            window.__aionWorkflowGraph = graph;
          }

          executeOpenNode(helpers);
        }
      },
      true,
    );

    const autosaveOpenNodeFromModal = (event) => {
      const modal = event.target.closest?.(".aion-node-editor-modal");
      if (!modal) return;

      const configInput = event.target.closest?.("[data-aion-node-editor-config-input]");
      const settingInput = event.target.closest?.("[data-aion-node-editor-setting-input]");

      if (!configInput && !settingInput) return;

      const nodeId =
        window.__aionWorkflowNodeEditorOpenId ||
        window.__aionWorkflowSelectedNodeId ||
        "";

      const graph = window.__aionWorkflowGraph || helpers.getAionWorkflowDraftState?.() || getGraph();
      const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
      const node = nodes.find((item) => String(item.id) === String(nodeId));

      if (!node) return;

      if (configInput) {
        const key = configInput.getAttribute("data-aion-node-editor-config-input");
        if (key) {
          node.config = {
            ...(node.config || {}),
            [key]: configInput.type === "checkbox" ? configInput.checked : configInput.value,
          };

          // Keep visible/top-level labels in sync for canvas cards.
          if (key === "title") node.title = configInput.value;
          if (key === "type") node.type = configInput.value;
          if (key === "connector") node.connector = configInput.value;
          if (key === "action_id") node.action_id = configInput.value;
        }
      }

      if (settingInput) {
        const key = settingInput.getAttribute("data-aion-node-editor-setting-input");
        if (key) {
          node.settings = {
            ...(node.settings || {}),
            [key]: settingInput.type === "checkbox" ? settingInput.checked : settingInput.value,
          };
        }
      }

      graph.dirty = true;
      window.__aionWorkflowGraph = graph;

      helpers.compileAndAttachAionWorkflowGlyph?.(graph);
      helpers.persistAionWorkflowDraftState?.();

      console.log("[node-editor] autosaved", {
        nodeId,
        config: node.config,
        settings: node.settings,
      });
    };

    document.addEventListener("input", autosaveOpenNodeFromModal, true);
    document.addEventListener("change", autosaveOpenNodeFromModal, true);

    document.addEventListener(
      "dblclick",
      (event) => {
        const node = event.target.closest?.("[data-aion-workflow-node-id]");
        if (!node) return;

        const nodeId = node.getAttribute("data-aion-workflow-node-id");
        if (!nodeId) return;

        window.__aionWorkflowNodeEditorOpenId = nodeId;
        window.__aionWorkflowSelectedNodeId = nodeId;
        helpers.requestRender?.();
      },
      true,
    );
  }

  window.AionWorkflowNodeEditor = {
    renderModal,
    installControls,
  };
})();
