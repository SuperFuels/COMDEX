# O13J.0 Active Graph Render Source Inspect

Goal: find why department workflow id changes but canvas still renders Boardroom 7-node graph.


## Relevant hits

- 3061: `* Reuse the existing Workflow Canvas left-rail visual language instead of`
- 3347: `/* AION PATCH: Phase 25K Workflow Canvas no dead sidebar column */`
- 3354: `/* AION PATCH: Phase 25K Workflow Canvas sidebar position fix */`
- 3360: `/* AION PATCH: Phase 25K Workflow Canvas final left offset lock */`
- 3581: `${renderDashboardMetricCard("Topology Nodes", nodes.length, "Business graph nodes")}`
- 3582: `${renderDashboardMetricCard("Topology Edges", edges.length, "Business graph relationships")}`
- 9638: `(typeof window !== "undefined" && window.__aionWorkflowGraph) ||`
- 9639: `(typeof window !== "undefined" && window.__aionGoalLoopWorkflowGraph) ||`
- 10175: `window.__aionWorkflowGraph = graph;`
- 10176: `window.__aionGoalLoopWorkflowGraph = graph;`
- 10720: `status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",`
- 10724: `ab_test_count: nodes.length,`
- 10729: `status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",`
- 10730: `proposal_count: nodes.length,`
- 10731: `required_board_review: nodes.length > 0,`
- 10732: `summary: nodes.length`
- 10733: `? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.``
- 11541: `feedback_count: nodes.length,`
- 12425: `description: "Existing Workflow Canvas Goal Loop graph snapshot.",`
- 12540: `conflict_nodes: Array.isArray(conflictPreview.conflict_nodes) ? conflictPreview.conflict_nodes.length : 0,`
- 15235: `Workflow Canvas reused: ${escapeHtml(preview.canvas_reuse_check.existing_workflow_canvas_reused ? "yes" : "no")}`
- 15698: `Top-level status summary for the existing Goal Loop, central Pilot and Workflow Canvas path.`
- 16322: `Adds visible controls to the existing Workflow Canvas and Pilot surfaces. I1 is preview/staging only:`
- 16839: `<div class="card-value" data-aion-goal-loop-ab-count="true">${escapeHtml(nodes.length)}</div>`
- 16864: `nodes.length`
- 20979: `if (!nodes.length) {`
- 20997: `if (currentIndex >= nodes.length) {`
- 21342: `node_count: Array.isArray(pilotState.context_task_nodes) ? pilotState.context_task_nodes.length : 0,`
- 23345: `return renderOperationsAgentsSurface();`
- 23534: `const workflowId = String(workflow?.workflow_id || workflow?.id || "").toLowerCase();`
- 23543: `workflowId.includes("acceptance_test") ||`
- 23544: `workflowId.includes("customer_onboarding_v1") ||`
- 23545: `workflowId.includes("test_customer") ||`
- 23774: `function renderOperationsAgentsSurface() {`
- 23816: `${renderAionWorkflowCanvasPanel({ workflows, loading })}`
- 24682: `const workflowId = String(draft?.workflow_id || "");`
- 24684: `if (workflowId.includes("new_customer_onboarding")) {`
- 24688: `if (workflowId.includes("form_submission")) {`
- 24692: `if (workflowId.includes("stale_quote")) {`
- 24704: `const workflowId = String(value?.workflow_id || value?.id || "");`
- 24707: `if (workflowId.includes("form_submission")) return "email_draft";`
- 24708: `if (workflowId.includes("new_customer_onboarding")) return "onboarding_checklist";`
- 24709: `if (workflowId.includes("stale_quote")) return "chase_email";`
- 24710: `if (workflowId.includes("crm_follow_up")) return "crm_follow_up";`
- 24822: `const workflowId = String(workflow?.workflow_id || workflow?.id || "").trim();`
- 24834: `if (!workflowId) {`
- 24952: `const workflowId =`
- 25041: `workflow_id: workflowId,`
- 26195: `if (!nodes.length) return [];`
- 26222: `if (!edges.length) {`
- 26406: `window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||`
- 26408: `window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||`
- 26410: `window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||`
- 26411: `window.__aionGoalLoopWorkflowGraph?.business_container ||`
- 26413: `window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||`
- 26414: `window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"`
- 26415: `? window.__aionWorkflowGraph?.business_container`
- 26443: `window.__aionGoalLoopWorkflowGraph?.business_container ||`
- 26445: `window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||`
- 26447: `window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||`
- 26448: `window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"`
- 26449: `? window.__aionWorkflowGraph?.business_container`
- 26703: `if (!nodes.length) return [];`
- 26965: `window.__aionWorkflowGraph = glyphGraph;`
- 26974: `window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;`
- 26978: `if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {`
- 26979: `window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;`
- 26980: `return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);`
- 26993: `window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;`
- 27001: `window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;`
- 27077: `window.__aionWorkflowGraph = {`
- 27089: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`
- 27117: `window["__aionWorkflowGraph"] = graph;`
- 27155: `window.__aionWorkflowGraph = compactGraph;`
- 27160: `window.__aionWorkflowGraph = compactGraph;`
- 27180: `window["__aionWorkflowGraph"] = graph;`
- 27216: `workflowId = createAionWorkflowId(),`
- 27225: `const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";`
- 27257: `window.__aionWorkflowGraph = loadedGraph;`
- 27267: `window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||`
- 27268: `window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"`
- 27277: `window.__aionWorkflowGraph?.business_container ||`
- 27280: `const workflowId =`
- 27281: `window.__aionWorkflowGraph?.workflow_id ||`
- 27286: `workflowId,`
- 27402: `const workflowId =`
- 27414: `id: `${businessContainer}:${workflowId}`,`
- 27415: `workflow_id: workflowId,`
- 27452: `: window.__aionWorkflowGraph || {};`
- 27543: `const workflowId =`
- 27552: `workflowId ||`
- 27579: `data-workflow-id="${escapeHtml(workflowId)}"`
- 27586: `<small>${escapeHtml(workflowId)}</small>`
- 27621: `data-workflow-id="${escapeHtml(workflowId)}"`
- 27634: `* Reusable glyph workflows now live inside the normal Workflow Canvas via:`
- 27662: `window["__aionWorkflowGraph"] = window["__aionWorkflowGraph"] || {`
- 27670: `return window["__aionWorkflowGraph"];`
- 27673: `function findMasterGlyphCanvasItem(workflowId) {`
- 27674: `const needle = String(workflowId || "").trim().toLowerCase();`
- 27693: `function stageMasterGlyphToWorkflowCanvas(workflowId) {`
- 27694: `const item = findMasterGlyphCanvasItem(workflowId);`
- 27707: `workflowId;`
- 27714: `const x = 220 + (graph.nodes.length % 4) * 280;`
- 27715: `const y = 260 + Math.floor(graph.nodes.length / 4) * 180;`
- 27762: `window["__aionWorkflowGraph"] = graph;`
- 27944: `function findAionWorkflowGlyphCapsule(workflowIdOrName) {`
- 27945: `const needle = String(workflowIdOrName || "").trim().toLowerCase();`
- 28102: `window.__aionWorkflowGraph = safeGraph;`
- 29342: `if (!window.__aionWorkflowGraph) {`
- 29343: `window.__aionWorkflowGraph = {`
- 29352: `const graph = window.__aionWorkflowGraph;`
- 29363: `nodes[nodes.length - 1] ||`
- 30514: `AION Unified Workflow Canvas Builder Modes - Phase 1`
- 30838: `if (!window.__aionWorkflowGraph) {`
- 30839: `window.__aionWorkflowGraph = getAionWorkflowDraftState();`
- 30842: `const graph = window.__aionWorkflowGraph || {};`
- 30846: `let previousNode = nodes[nodes.length - 1] || null;`
- 30888: `window["__aionWorkflowGraph"] = graph;`
- 30917: `: window.__aionWorkflowGraph) || {};`
- 30974: `: window.__aionWorkflowGraph) || {};`
- 31176: `const workflowId = makeAionFileCabinetId("workflow");`
- 31180: `id: workflowId,`
- 31183: `workflow_id: workflowId,`
- 31188: `window.__aionWorkflowGraph = {`
- 31189: `workflow_id: workflowId,`
- 31216: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`
- 31347: `const workflowId = node.workflow_id || node.id;`
- 31356: `data-aion-file-cabinet-open-workflow="${escapeHtml(workflowId)}"`
- 31367: `<button type="button" title="Delete workflow" data-aion-cabinet-delete="${escapeHtml(node.id)}" data-aion-cabinet-delete-name="${escapeHtml(node.name || workflowId)}">×</button>`
- 31409: `: window.__aionWorkflowGraph) || {};`
- 31580: `<!-- LOCK: preserved Workflow Canvas mode button. Not Master Glyph Canvas. -->`
- 31585: `title="Workflow Canvas"`
- 31586: `aria-label="Workflow Canvas"`
- 31588: `Workflow Canvas`
- 31605: `function renderAionWorkflowCanvasPanel({ workflows = [], loading = false } = {}) {`
- 31616: `window["__aionWorkflowGraph"] = graph;`
- 31635: `nodes[nodes.length - 1] ||`
- 32968: `const connectorHtml = edges.length`
- 33007: `const activeGraph = typeof getAionWorkflowRenderGraphO12C === "function" ? getAionWorkflowRenderGraphO12C() : getAionWorkflowDraftState();`
- 33009: `window.__aionSelectedWorkflowId ||`
- 33010: `window.__aionActiveWorkflowId ||`
- 33011: `activeGraph.workflow_id ||`
- 33013: `const activeNodes = Array.isArray(activeGraph.nodes) ? activeGraph.nodes.length : 0;`
- 33014: `const activeEdges = Array.isArray(activeGraph.edges) ? activeGraph.edges.length : 0;`
- 33015: `const activeStatus = getAionWorkflowSaveStatus(activeGraph);`
- 33118: `nodes.length === 0`
- 33139: `style="left:${escapeHtml(String((nodes[nodes.length - 1]?.x || 160) + 260))}px; top:${escapeHtml(String((nodes[nodes.length - 1]?.y || 240) + 42))}px;"`
- 33281: `nodes.length === 0 || pickerMode === "trigger"`
- 34676: `function getActiveWorkspaceId() {`
- 34725: `const workspaceId = getActiveWorkspaceId();`
- 34752: `const workspaceId = getActiveWorkspaceId();`
- 34763: `const workspaceId = getActiveWorkspaceId();`
- 35057: `const workflowId =`
- 35151: `workflow_id: workflowId,`
- 36122: `const workflowId = item.workflow_id || item.workflow?.workflow_id || "unknown";`
- 36123: `const name = item.workflow_name || item.workflow?.name || workflowId;`
- 36136: `<p class="muted" style="margin:0;">${escapeHtml(workflowId)}</p>`
- 36151: `data-workflow-id="${escapeHtml(workflowId)}"`
- 36161: `data-workflow-id="${escapeHtml(workflowId)}"`
- 36171: `const workflowId = workflow.workflow_id || workflow.id || "unknown";`
- 36172: `const name = workflow.name || workflowId;`
- 36191: `${escapeHtml(workflowId)}`
- 36236: `data-workflow-id="${escapeHtml(workflowId)}"`
- 36245: `data-workflow-id="${escapeHtml(workflowId)}"`
- 36253: `data-workflow-id="${escapeHtml(workflowId)}"`
- 36262: `data-workflow-id="${escapeHtml(workflowId)}"`
- 36272: `data-workflow-id="${escapeHtml(workflowId)}"`
- 36282: `data-workflow-id="${escapeHtml(workflowId)}"`
- 37490: `(typeof window !== "undefined" && window.__aionWorkflowGraph) ||`
- 37491: `(typeof window !== "undefined" && window.__aionGoalLoopWorkflowGraph) ||`
- 37677: `node_count: nodeCount,`
- 37733: `<div class="card-value" data-aion-goal-loop-department-node-count="true">${escapeHtml(context.node_count || 0)} nodes</div>`
- 47951: `const workflowId = operationsAgentsButton.dataset.workflowId || "";`
- 47957: `return String(id) === String(workflowId);`
- 48121: `const workflowId = operationsAgentsButton.dataset.workflowId || "";`
- 48124: `await navigator.clipboard.writeText(workflowId);`
- 48126: `message: workflowId ? "Workflow id copied" : "No workflow id found",`
- 48127: `messageTone: workflowId ? "success" : "error",`
- 48131: `message: workflowId || "No workflow id found",`
- 48132: `messageTone: workflowId ? "neutral" : "error",`
- 48141: `const workflowId = operationsAgentsButton.dataset.workflowId || "";`
- 48143: `if (!workflowId) {`
- 48155: `message: `Running generic workflow ${workflowId}...`,`
- 48161: `workflow_id: workflowId,`
- 48177: `? `Generic workflow completed: ${result.run_id || workflowId}``
- 49568: `const workspaceId = getActiveWorkspaceId();`
- 49776: `const workflowId = operationsAgentsButton.dataset.workflowId || "";`
- 49779: `if (!workflowId) {`
- 49791: `message: `${nextEnabled ? "Enabling" : "Disabling"} workflow: ${workflowId}`,`
- 49797: ``/api/local-node/train-tasks/workflows/${encodeURIComponent(workflowId)}/toggle`,`
- 50138: `const workflowId = operationsAgentsButton.dataset.workflowId || "";`
- 50140: `if (!workflowId || workflowId === "unknown") {`
- 50153: `message: `Running workflow test: ${workflowId}`,`
- 50160: `workflowId,`
- 50181: `workflow_id: workflowId,`
- 50200: `const workflowId = operationsAgentsButton.dataset.workflowId || "";`
- 50202: `if (!workflowId || workflowId === "unknown") {`
- 50211: `const curl = `curl -X POST http://127.0.0.1:8080/api/local-node/train-tasks/workflows/${encodeURIComponent(workflowId)}/test-run \\`
- 52058: `if (!window.__aionWorkflowGraph) {`
- 52059: `window.__aionWorkflowGraph = {`
- 52068: `const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)`
- 52069: `? window.__aionWorkflowGraph.nodes`
- 52072: `const edges = Array.isArray(window.__aionWorkflowGraph.edges)`
- 52073: `? window.__aionWorkflowGraph.edges`
- 52083: `nodes[nodes.length - 1] ||`
- 52193: `window.__aionWorkflowGraph.nodes = reflowedNodes;`
- 52194: `window.__aionWorkflowGraph.edges = [...remainingEdges, ...insertedEdges];`
- 52939: `window["__aionWorkflowGraph"] = graph;`
- 53029: `const workflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";`
- 53061: `if (!canvasPayload || !Array.isArray(canvasPayload.nodes) || !canvasPayload.nodes.length) {`
- 53107: `workflow_id: workflowId,`
- 53108: `workflow_name: graph.name || workflowId,`
- 53334: `const workflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";`
- 53423: `const workflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";`
- 53551: `const workflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";`
- 53703: `window["__aionWorkflowGraph"] = graph;`
- 54454: `const graph = getAionWorkflowDraftState?.() || window.__aionWorkflowGraph || {};`
- 54460: `if (!Array.isArray(nodes) || !nodes.length) return;`
- 54511: `const hasValidCanvas = Boolean(result?.ok === true && Array.isArray(canvas?.nodes) && canvas.nodes.length);`
- 54606: `window.__aionWorkflowGraph = nextGraph;`
- 54630: `message: `Loaded Architect workflow onto canvas: ${nodes.length} nodes · ${edges.length} links`,`
- 54643: `if (!nodes.length) return;`
- 55207: `const graph = window.__aionWorkflowGraph || {};`
- 55303: `const graph = window.__aionWorkflowGraph || getAionWorkflowDraftState?.();`
- 55368: `window["__aionWorkflowGraph"] = graph;`
- 55422: `const graph = window.__aionWorkflowGraph || {};`
- 55736: `if (!window.__aionWorkflowGraph) {`
- 55737: `window.__aionWorkflowGraph = {`
- 55746: `const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)`
- 55747: `? window.__aionWorkflowGraph.nodes`
- 55750: `const edges = Array.isArray(window.__aionWorkflowGraph.edges)`
- 55751: `? window.__aionWorkflowGraph.edges`
- 55761: `nodes[nodes.length - 1] ||`
- 55856: `window.__aionWorkflowGraph.nodes = reflowedNodes;`
- 55857: `window.__aionWorkflowGraph.edges = [...remainingEdges, ...insertedEdges];`
- 55990: `const graph = window.__aionWorkflowGraph || getAionWorkflowDraftState?.();`
- 56023: `window["__aionWorkflowGraph"] = graph;`
- 56240: `if (!window.__aionWorkflowGraph) {`
- 56241: `window.__aionWorkflowGraph = {`
- 56250: `const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)`
- 56251: `? window.__aionWorkflowGraph.nodes`
- 56254: `const edges = Array.isArray(window.__aionWorkflowGraph.edges)`
- 56255: `? window.__aionWorkflowGraph.edges`
- 56265: `nodes[nodes.length - 1] ||`
- 56375: `window.__aionWorkflowGraph.nodes = reflowedNodes;`
- 56376: `window.__aionWorkflowGraph.edges = [...remainingEdges, ...insertedEdges];`
- 56608: `window["__aionWorkflowGraph"] = graph;`
- 56684: `window.__aionWorkflowGraph = {`
- 56696: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`
- 56957: `window["__aionWorkflowGraph"] = graph;`
- 57012: `if (!nodeId || !window.__aionWorkflowGraph) return;`
- 57014: `const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)`
- 57015: `? window.__aionWorkflowGraph.nodes`
- 57018: `const edges = Array.isArray(window.__aionWorkflowGraph.edges)`
- 57019: `? window.__aionWorkflowGraph.edges`
- 57022: `window.__aionWorkflowGraph.nodes = nodes.filter((node) => node.id !== nodeId);`
- 57023: `window.__aionWorkflowGraph.edges = edges.filter(`
- 57029: `window.__aionWorkflowGraph.nodes[window.__aionWorkflowGraph.nodes.length - 1]?.id ||`
- 57033: `if (!window.__aionWorkflowGraph.nodes.length) {`
- 57168: `if (!nodes.length) {`
- 57340: `const graph = getAionWorkflowDraftState?.() || window.__aionWorkflowGraph || {};`
- 57342: `if (nodes.length && typeof fitAionWorkflowCanvasToGeneratedNodes === "function") {`
- 58225: `workflowId = "workflow",`
- 58242: `<span class="badge">workflow_id: ${String(workflowId || "workflow")}</span>`
- 59649: `window.__aionWorkflowGraphDirty = true;`
- 62842: `/* AION Unified Workflow Canvas Builder Controls - Phase 1 */`
- 63995: `if (nodes.length !== 4) return false;`
- 64007: `return !graph || !Array.isArray(graph.nodes) || graph.nodes.length === 0;`
- 64014: `: window.__aionWorkflowGraph) || null;`
- 64018: `window.__aionWorkflowGraph = makeBlankWorkflowGraph();`
- 64025: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`
- 64075: `: window.__aionWorkflowGraph) || makeBlankWorkflowGraph();`
- 64086: `window.__aionWorkflowGraph = makeBlankWorkflowGraph();`
- 64092: `window["__aionWorkflowGraph"] = graph;`
- 64098: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`
- 64129: `: window.__aionWorkflowGraph) || {};`
- 64383: `: window.__aionWorkflowGraph) || {};`
- 64399: `window.__aionWorkflowGraph = makeBlankWorkflowGraph();`
- 64405: `window["__aionWorkflowGraph"] = graph;`
- 64415: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`
- 64548: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 64563: `window["__aionWorkflowGraph"] = graph;`
- 65065: `if (!window.__aionWorkflowGraph) {`
- 65066: `window.__aionWorkflowGraph = { nodes: [], edges: [] };`
- 65069: `return window["__aionWorkflowGraph"];`
- 65073: `window["__aionWorkflowGraph"] = graph;`
- 65704: `window["__aionWorkflowGraph"] = window["__aionWorkflowGraph"] || {`
- 65709: `return window["__aionWorkflowGraph"];`
- 65767: `window.__aionWorkflowGraph = g;`
- 66421: `window["__aionWorkflowGraph"] = window["__aionWorkflowGraph"] || {`
- 66429: `return window["__aionWorkflowGraph"];`
- 66433: `window["__aionWorkflowGraph"] = graph;`
- 67147: `window["__aionWorkflowGraph"] = window["__aionWorkflowGraph"] || {`
- 67155: `return window["__aionWorkflowGraph"];`
- 67159: `window["__aionWorkflowGraph"] = graph;`
- 67872: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 68312: `if (!window.__aionWorkflowGraph) {`
- 68313: `window.__aionWorkflowGraph = {`
- 68322: `return window["__aionWorkflowGraph"];`
- 68338: `window.__aionWorkflowGraph = g;`
- 68898: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 68927: `window["__aionWorkflowGraph"] = graph;`
- 70227: `return window.__aionWorkflowGraph || null;`
- 70247: `window["__aionWorkflowGraph"] = graph;`
- 70250: `window.__aionWorkflowSelectedNodeId = graph.nodes[graph.nodes.length - 1]?.id || graph.nodes[0]?.id || null;`
- 70498: `return window.__aionWorkflowGraph || null;`
- 70507: `const before = graph.nodes.length;`
- 70518: `if (graph.nodes.length === before) return false;`
- 70521: `window["__aionWorkflowGraph"] = graph;`
- 70525: `graph.nodes[graph.nodes.length - 1]?.id || graph.nodes[0]?.id || null;`
- 70865: `function findCabinetNodeByWorkflowId(workflowId) {`
- 70866: `if (!workflowId) return null;`
- 70876: `String(item.workflow_id || item.id || "") === String(workflowId) &&`
- 70894: `const workflowId = workflowNode?.workflow_id || workflowNode?.id || `workflow_${Date.now()}`;`
- 70897: `workflow_id: workflowId,`
- 70921: `function loadCabinetWorkflow(workflowId) {`
- 70922: `const workflowNode = findCabinetNodeByWorkflowId(workflowId);`
- 70937: `window["__aionWorkflowGraph"] = graph;`
- 71754: `const workflowId =`
- 71758: `if (!workflowId) return;`
- 71764: `<button type="button" title="Delete workflow" aria-label="Delete workflow" data-aion-cabinet-delete="${workflowId}">×</button>`
- 71823: `const workflowId = openWorkflow.getAttribute("data-aion-file-cabinet-open-workflow");`
- 71824: `callApi("loadWorkflow", workflowId);`
- 72102: `return window.__aionWorkflowGraph || null;`
- 72113: `function makeStarterGraph(name, workflowId) {`
- 72115: `workflow_id: workflowId || makeId("workflow"),`
- 72140: `window["__aionWorkflowGraph"] = graph;`
- 72163: `const workflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";`
- 72166: `const existing = findNodeById(tree, workflowId);`
- 72169: `existing.node.workflow_id = workflowId;`
- 72194: `id: workflowId,`
- 72197: `workflow_id: workflowId,`
- 72218: `const workflowId = makeId("workflow");`
- 72220: `const graph = makeStarterGraph(name, workflowId);`
- 72223: `id: workflowId,`
- 72226: `workflow_id: workflowId,`
- 72350: `function loadWorkflow(workflowId) {`
- 72354: `const found = findNodeById(tree, workflowId);`
- 72567: `function findWorkflow(tree, workflowId) {`
- 72571: `(String(node.id) === String(workflowId) ||`
- 72572: `String(node.workflow_id || "") === String(workflowId))`
- 72588: `return window.__aionWorkflowGraph || null;`
- 72591: `function persistCurrentGraphName(workflowId, newName) {`
- 72596: `(String(graph.workflow_id || "") === String(workflowId) ||`
- 72597: `String(window.__aionWorkflowGraph?.workflow_id || "") === String(workflowId))`
- 72602: `window["__aionWorkflowGraph"] = graph;`
- 72618: `function renameWorkflow(workflowId, newName) {`
- 72623: `const found = findWorkflow(tree, workflowId);`
- 72634: `persistCurrentGraphName(workflowId, safeName);`
- 72648: `const workflowId = workflowButton.getAttribute("data-aion-file-cabinet-open-workflow");`
- 72649: `if (!workflowId) return;`
- 72673: `renameWorkflow(workflowId, nextName);`
- 72816: `function findWorkflow(tree, workflowId) {`
- 72820: `(String(node.id) === String(workflowId) ||`
- 72821: `String(node.workflow_id || "") === String(workflowId))`
- 72837: `return window.__aionWorkflowGraph || null;`
- 72840: `function renameWorkflow(workflowId, nextName) {`
- 72845: `const found = findWorkflow(tree, workflowId);`
- 72860: `if (graph && String(graph.workflow_id || "") === String(workflowId)) {`
- 72864: `window["__aionWorkflowGraph"] = graph;`
- 72904: `const workflowId = button.getAttribute("data-aion-file-cabinet-open-workflow");`
- 72905: `if (!workflowId) return false;`
- 72929: `renameWorkflow(workflowId, nextName);`
- 74303: `function makeStarterGraph(workflowId, name, businessContainer) {`
- 74305: `workflow_id: workflowId,`
- 74344: `const workflowId = makeWorkflowId();`
- 74346: `const graph = makeStarterGraph(workflowId, name, tree.business_container || tree.workspace_id);`
- 74349: `id: workflowId,`
- 74350: `workflow_id: workflowId,`
- 74364: `window["__aionWorkflowGraph"] = graph;`
- 74369: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`
- 74736: `const workflowId = String(item?.workflow_id || "");`
- 74737: `return id !== removeId && workflowId !== removeId;`
- 74867: `return window.__aionWorkflowGraph || {};`
- 74871: `window["__aionWorkflowGraph"] = graph;`
- 74890: `function findWorkflow(tree, workflowId) {`
- 74895: `String(item.id || "") === String(workflowId) ||`
- 74896: `String(item.workflow_id || "") === String(workflowId)`
- 74913: `window.__aionSelectedWorkflowId ||`
- 74914: `window.__aionActiveWorkflowId ||`
- 74947: `workflowId: selectedWorkflowId,`
- 74952: `return { tree, graph, workflowId: selectedWorkflowId };`
- 74955: `async function loadWorkflowFromCabinet(workflowId) {`
- 74962: `const node = findWorkflow(tree, workflowId);`
- 74965: `throw new Error(`Workflow not found in cabinet: ${workflowId}`);`
- 74969: `graph.workflow_id = node.workflow_id || node.id || workflowId;`
- 74992: `window.__aionSelectedWorkflowId = graph.workflow_id;`
- 74993: `window.__aionActiveWorkflowId = graph.workflow_id;`
- 74998: `workflowId: graph.workflow_id,`
- 75000: `nodes: graph.nodes.length,`
- 75001: `edges: graph.edges.length,`
- 75023: `const workflowId = String(open.getAttribute("data-aion-file-cabinet-open-workflow") || "").trim();`
- 75024: `if (!workflowId) return;`
- 75026: `loadWorkflowFromCabinet(workflowId).catch((err) => {`
- 75039: `if (!window.__aionSelectedWorkflowId && !window.__aionActiveWorkflowId) return;`
- 75787: `return window.__aionWorkflowGraph || {};`
- 75802: `window["__aionWorkflowGraph"] = graph;`
- 78337: `return window.__aionWorkflowGraph || {};`
- 78343: `const workflowId =`
- 78344: `window.__aionSelectedWorkflowId ||`
- 78345: `window.__aionActiveWorkflowId ||`
- 78350: `const nodes = Array.isArray(graph.nodes) ? graph.nodes.length : 0;`
- 78351: `const edges = Array.isArray(graph.edges) ? graph.edges.length : 0;`
- 78370: `<code>${esc(workflowId)}</code>`
- 79452: `window.__aionWorkflowGraph = {`
- 79530: `/* RETIRED: separate Master Glyph Canvas overlay styles removed. Glyphs now live in Workflow Canvas tabs/library. */`
- 79572: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 80006: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 80449: `window.__aionWorkflowGraph = window.__aionWorkflowGraph || {`
- 80457: `return window.__aionWorkflowGraph;`
- 80541: `window.__aionWorkflowGraph = graph;`
- 80738: `if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {`
- 80739: `return window.__aionWorkflowGraph;`
- 80787: `if (window.__aionWorkflowGraph === graph) {`
- 80788: `window.__aionWorkflowGraph = graph;`
- 80846: `- × toolbar utility clears staged glyph/call nodes from window.__aionWorkflowGraph`
- 80878: `if (!window.__aionWorkflowGraph || typeof window.__aionWorkflowGraph !== "object") {`
- 80879: `window.__aionWorkflowGraph = {`
- 80886: `if (!Array.isArray(window.__aionWorkflowGraph.nodes)) {`
- 80887: `window.__aionWorkflowGraph.nodes = [];`
- 80890: `if (!Array.isArray(window.__aionWorkflowGraph.edges)) {`
- 80891: `window.__aionWorkflowGraph.edges = [];`
- 80894: `return window.__aionWorkflowGraph;`
- 80941: `const beforeNodes = graph.nodes.length;`
- 80962: `window.__aionWorkflowGraph = graph;`
- 80966: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`
- 80977: `const cleared = beforeNodes - graph.nodes.length;`
- 81076: `const workflowId = item.workflow_id || item.canonical_key || item.id || "";`
- 81087: `workflowId`
- 81088: `? `<button type="button" data-aion-master-glyph-stage-to-canvas="true" data-workflow-id="${escapeLocal(workflowId)}">Stage to workflow canvas<``
- 81373: `window.__aionWorkflowGraph ||`
- 81406: `window.__aionWorkflowGraph = graph;`
- 81984: `const workflowId =`
- 81994: `workflowId ||`
- 82005: `workflow_id: workflowId,`
- 82012: `stableCode(`${scope}:${workflowId}:${name}`, inferPrefix(item)),`
- 82044: `function stageGlyph(workflowId, code) {`
- 82046: `window.__aionWorkflowMainGraph = window.__aionWorkflowMainGraph || window.__aionWorkflowGraph || {};`
- 82047: `window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;`
- 82049: `const staged = window.__stageAionMasterGlyphToWorkflowCanvas(workflowId);`
- 82896: `window.__aionWorkflowGraph ||`
- 82921: `x: 240 + (graph.nodes.length % 4) * 280,`
- 82922: `y: 260 + Math.floor(graph.nodes.length / 4) * 180,`
- 82974: `window.__aionWorkflowGraph = graph;`
- 83061: `for (let i = 0; i < nodes.length - 1; i += 1) {`
- 83091: `window.__aionWorkflowGraph = graph;`
- 83127: `window.__aionWorkflowMainGraph = window.__aionWorkflowMainGraph || clone(window.__aionWorkflowGraph || {});`
- 84999: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 85751: `window.__aionWorkflowGraph = store[code];`
- 85801: `window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;`
- 85841: `window.__aionWorkflowGraph = graph;`
- 87742: `html body .aion-workflow-floating-toolbar [title="Workflow Canvas"],`
- 88750: `} else if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {`
- 88751: `graph = window.__aionWorkflowGraph;`
- 88754: `graph = window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 89327: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 90322: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 90621: `<button type="button" data-aion-canvas-mode="workflow" title="Workflow Canvas">Workflow Canvas</button>`
- 90647: `* - Preserve Workflow Canvas, Execute workflow, Workflow Glyph Library, and Clear staged glyph nodes.`
- 90662: `.aion-workflow-floating-toolbar-consolidated [title="Workflow Canvas"],`
- 90753: `glyph.workflowId ||`
- 91124: `function getActiveGlyphCode() {`
- 91145: `const glyphCode = getActiveGlyphCode();`
- 91153: `window.__aionWorkflowGraph ||`
- 91176: `window.__aionWorkflowGraph = graph;`
- 91192: `const glyphCode = getActiveGlyphCode();`
- 91211: `window.__aionWorkflowGraph = graph;`
- 91232: `window.__aionGetActiveWorkflowGraph = function getActiveWorkflowGraphPhase19A(...args) {`
- 91236: `return hydrateActiveGlyphWorkflowGraph() || previousGetActive?.apply?.(this, args) || window.__aionWorkflowGraph;`
- 91239: `return previousGetActive?.apply?.(this, args) || window.__aionWorkflowGraph;`
- 91250: `window.__aionWorkflowGraph = graph;`
- 91260: `window.__aionWorkflowGraph = graph;`
- 91360: `window.__aionWorkflowGraph ||`
- 91373: `window.__aionWorkflowGraph = graph;`
- 91449: `window.__aionWorkflowGraph = tab.graph;`
- 91501: `window.__aionWorkflowGraph = fresh.graph;`
- 91507: `window.__aionWorkflowGraph = next.graph;`
- 91538: `window.__aionWorkflowGraph = tab.graph;`
- 91552: `const graph = window.__aionWorkflowGraph || window.__aionWorkflowMainGraph || tab.graph;`
- 91565: `window.__aionWorkflowGraph = tab.graph;`
- 91760: `* - Main workflow uses __aionWorkflowMainGraph / __aionWorkflowGraph.`
- 91798: `window.__aionWorkflowGraph;`
- 91810: `window.__aionWorkflowGraph = graph;`
- 91837: `window.__aionWorkflowGraph = graph;`
- 91843: `function getActiveGraph() {`
- 91858: `window.__aionWorkflowGraph = next;`
- 91864: `window.__aionWorkflowGraph = next;`
- 91868: `window.__aionGetActiveWorkflowGraph = getActiveGraph;`
- 91929: `window.__aionWorkflowGraph = main;`
- 91936: `window.__aionWorkflowMainGraph = window.__aionWorkflowGraph || main;`
- 91945: `window.__stageAionMasterGlyphToWorkflowCanvas = function stageAionMasterGlyphToWorkflowCanvasMainOnly(workflowId) {`
- 91952: `const needle = String(workflowId || "").toLowerCase();`
- 92724: `return window.__aionWorkflowGraph || { nodes: [], edges: [] };`
- 96217: `* Glyph Library / Workflow Canvas tab surface.`
- 100321: `* AION PATCH: Phase 19C Workflow Canvas Navigation Cleanup Lock`
- 100324: `* - Workflow tab strip MUST only be visible while the Workflow Canvas is visible.`
- 100469: `* When the user navigates Boardroom <-> Workflow Canvas, stale body classes`
- 102814: `const workflowId = "home_fixed_new_enquiry";`
- 102820: `workflow_id: workflowId,`
- 102850: `workflow_id: workflowId,`

## Extracted windows


### Around line 3581: `${renderDashboardMetricCard("Topology Nodes", nodes.length, "Business graph nodes")}`

```js
3536:         `)
3537:         .join("")}
3538:     </div>
3539:   `;
3540: }
3541: 
3542: function renderBindingCategorySections(bindingsByCategory) {
3543:   const entries = Object.entries(bindingsByCategory || {});
3544:   if (!entries.length) {
3545:     return `<div class="empty-state">No categorized bindings available.</div>`;
3546:   }
3547: 
3548:   return `
3549:     <div class="dashboard-shell">
3550:       ${entries
3551:         .sort(([a], [b]) => a.localeCompare(b))
3552:         .map(
3553:           ([category, bindings]) => `
3554:             <div class="panel">
3555:               <div class="panel-title">${escapeHtml(prettify(category))}</div>
3556:               ${renderBindingCards(bindings)}
3557:             </div>
3558:           `,
3559:         )
3560:         .join("")}
3561:     </div>
3562:   `;
3563: }
3564: 
3565: function renderTopologySummary(topology) {
3566:   const nodes = Array.isArray(topology?.nodes) ? topology.nodes : [];
3567:   const edges = Array.isArray(topology?.edges) ? topology.edges : [];
3568: 
3569:   const nodeTypeCounts = {};
3570:   nodes.forEach((node) => {
3571:     const key = node?.node_type || "unknown";
3572:     nodeTypeCounts[key] = (nodeTypeCounts[key] || 0) + 1;
3573:   });
3574: 
3575:   const typeEntries = Object.entries(nodeTypeCounts);
3576: 
3577:   return `
3578:     <div class="dashboard-shell">
3579:       ${renderAionBusinessContextMiniCard(departmentKey)}
3580:       <div class="card-grid">
3581:         ${renderDashboardMetricCard("Topology Nodes", nodes.length, "Business graph nodes")}
3582:         ${renderDashboardMetricCard("Topology Edges", edges.length, "Business graph relationships")}
3583:         ${renderDashboardMetricCard("Node Types", typeEntries.length, "Distinct topology node types")}
3584:         ${renderDashboardMetricCard("Bindings", state.containerBindings.length, "Business container bindings")}
3585:       </div>
3586: 
3587:       <div class="panel">
3588:         <div class="panel-title">Topology Node Types</div>
3589:         ${
3590:           typeEntries.length
3591:             ? `
3592:               <div class="badge-row">
3593:                 ${typeEntries
3594:                   .sort(([a], [b]) => a.localeCompare(b))
3595:                   .map(
3596:                     ([type, count]) =>
3597:                       `<span class="badge">${escapeHtml(prettify(type))}: ${escapeHtml(count)}</span>`,
3598:                   )
3599:                   .join("")}
3600:               </div>
3601:             `
3602:             : `<div class="empty-state">No topology node data available.</div>`
3603:         }
3604:       </div>
3605:     </div>
3606:   `;
3607: }
3608: 
3609: // Phase 14L: deprecated duplicate AgentMap panel. Keep function for legacy lock tests only; do not mount in Boardroom.
3610: function renderAgentMapFrontendVisibilityPanel() {
3611:   return `
3612:     <section class="panel agentmap-machine-discovery-panel" data-agentmap-panel="machine-discovery">
3613:       <div class="panel-header">
3614:         <div>
3615:           <div class="panel-kicker">Machine Discovery</div>
3616:           <div class="panel-title">AgentMap Dashboard</div>
3617:           <div class="muted">
3618:             Generate, verify, preview, copy, download and simulate the machine-readable business twin.
3619:           </div>
3620:         </div>
3621:         <div class="status-pill status-pill--ok" data-agentmap-status="verified">
3622:           AgentMap Verified Live
3623:         </div>
3624:       </div>
3625: 
3626:       <div class="metric-grid compact">
3627:         ${renderDashboardMetricCard("agentmap_hash", "preview-ready", "Deterministic discovery hash")}
3628:         ${renderDashboardMetricCard("Live verification", "verified", "Read-only AgentMap check")}
3629:         ${renderDashboardMetricCard("Synthetic simulation", "passed", "Inbound AI agent preview")}
3630:         ${renderDashboardMetricCard("Human review bridge", "ready", "Halts before live execution")}
3631:       </div>
3632: 
3633:       <div class="list-item" data-agentmap-preview="agentmap-json">
3634:         <strong>agentmap.json Preview</strong>
3635:         <div class="muted">
3636:           Preview generated agentmap.json before publish. No booking, payment, escrow, dispatch,
3637:           external message or live chain write is enabled from this surface.
3638:         </div>
3639:       </div>
3640: 
3641:       <div class="button-row agentmap-actions">
3642:         <button class="button primary" type="button" data-agentmap-action="generate">
3643:           Generate AgentMap
3644:         </button>
3645:         <button class="button" type="button" data-agentmap-action="regenerate">
3646:           Regenerate AgentMap
3647:         </button>
3648:         <button class="button" type="button" data-agentmap-action="copy-url">
3649:           Copy AgentMap URL
3650:         </button>
3651:         <button class="button" type="button" data-agentmap-action="download-json">
3652:           Download agentmap.json
3653:         </button>
3654:         <button class="button" type="button" data-agentmap-action="copy-install-tag">
3655:           Copy website install tag
3656:         </button>
3657:       </div>
3658: 
3659:       <div class="button-row agentmap-actions">
3660:         <button class="button" type="button" data-agentmap-action="run-synthetic-simulation">
3661:           Run Synthetic Agent Simulation
3662:         </button>
3663:         <button class="button" type="button" data-agentmap-action="run-human-review-e2e">
3664:           Run Human Review E2E Simulation
3665:         </button>
3666:       </div>
3667: 
3668:       <div class="list-item">
3669:         <strong>Hosted URL</strong>
3670:         <div class="muted">/agentmap.json</div>
```

### Around line 9637: `const graph =`

```js
9592:       results: {
9593:         ...existingResults,
9594:         latest_central_preview: resultRecord,
9595:         central_preview_history: [
9596:           ...(Array.isArray(existingResults.central_preview_history) ? existingResults.central_preview_history : []),
9597:           resultRecord,
9598:         ],
9599:       },
9600:       evidence: [...(Array.isArray(entry.evidence) ? entry.evidence : []), evidenceRecord],
9601:       receipts: [...(Array.isArray(entry.receipts) ? entry.receipts : []), receiptRecord],
9602:       boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} received central AION approved action result: ${completedTask.title}. No live external action was taken.`,
9603:       confidence: "useful",
9604:       last_updated: now,
9605:     });
9606:   });
9607: 
9608:   const pilotState =
9609:     typeof getAionPilotFrontendInteractionState === "function"
9610:       ? getAionPilotFrontendInteractionState()
9611:       : null;
9612: 
9613:   if (pilotState) {
9614:     pilotState.status = "central_approved_task_completed";
9615:     pilotState.central_pilot_queue = queue;
9616:     pilotState.stream_events = [
9617:       ...(Array.isArray(pilotState.stream_events) ? pilotState.stream_events : []),
9618:       {
9619:         type: "central_approved_boardroom_action",
9620:         label: "Approved Boardroom action completed",
9621:         detail: completedTask.result_summary,
9622:         status: "completed_preview",
9623:       },
9624:     ];
9625:   }
9626: 
9627:   if (typeof requestRender === "function") {
9628:     requestRender();
9629:   }
9630: 
9631:   return completedTask;
9632: }
9633: 
9634: 
9635: /* AION GOAL LOOP CANVAS PHASE D3: Central Pilot Safe Task Queue from Goal Loop Graph */
9636: function getAionActiveGoalLoopGraphForCentralPilotQueue() {
9637:   const graph =
9638:     (typeof window !== "undefined" && window.__aionWorkflowGraph) ||
9639:     (typeof window !== "undefined" && window.__aionGoalLoopWorkflowGraph) ||
9640:     null;
9641: 
9642:   const isGoalLoop =
9643:     graph?.canvas_type === "goal_loop" ||
9644:     graph?.active_canvas_intent === "goal_loop" ||
9645:     graph?.goal_loop_contract?.goal_loop_id;
9646: 
9647:   return isGoalLoop ? graph : null;
9648: }
9649: 
9650: function buildAionGoalLoopCentralPilotTaskQueue() {
9651:   const graph = getAionActiveGoalLoopGraphForCentralPilotQueue();
9652:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
9653: 
9654:   const businessLabel =
9655:     typeof getAionWorkflowCanvasHeaderBusinessLabel === "function"
9656:       ? getAionWorkflowCanvasHeaderBusinessLabel()
9657:       : "Business not registered";
9658: 
9659:   const businessContainer =
9660:     typeof getAionWorkflowBusinessContainerId === "function"
9661:       ? getAionWorkflowBusinessContainerId()
9662:       : "business_not_registered";
9663: 
9664:   const goalLoopId = String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "not_staged");
9665:   const boardGoal = graph?.goal_loop_contract?.board_goal || {};
9666:   const boardGoalTitle = String(boardGoal.title || boardGoal.goal || "No Boardroom goal staged");
9667: 
9668:   const agentTaskNodes = nodes.filter((node) => {
9669:     const type = String(node?.node_type || node?.type || node?.data?.node_type || node?.data?.type || "").trim();
9670:     return type === "agent_task";
9671:   });
9672: 
9673:   const tasks = agentTaskNodes.map((node, index) => {
9674:     const department = normaliseAionDepartmentPilotKey(
9675:       node?.department ||
9676:       node?.data?.department ||
9677:       node?.meta?.department ||
9678:       node?.config?.department ||
9679:       node?.config?.department_goal?.department ||
9680:       "pilot"
9681:     );
9682: 
9683:     const title = String(node?.title || node?.label || `${department} Goal Loop task`);
9684:     const departmentContext =
9685:       typeof getAionActiveGoalLoopDepartmentContext === "function"
9686:         ? getAionActiveGoalLoopDepartmentContext(department)
9687:         : null;
9688: 
9689:     return {
9690:       id: String(node?.id || `${goalLoopId}_${department}_central_safe_task_${index + 1}`),
9691:       source_node_id: String(node?.id || ""),
9692:       source_node_type: "agent_task",
9693:       source: "goal_loop_graph_agent_task",
9694:       goal_loop_id: goalLoopId,
9695:       board_goal: boardGoalTitle,
9696:       business_label: businessLabel,
9697:       business_container: businessContainer,
9698:       department,
9699:       department_label:
9700:         typeof runtimeShared !== "undefined" && runtimeShared.getDepartmentLabel
9701:           ? runtimeShared.getDepartmentLabel(department)
9702:           : department,
9703:       department_child_canvas_id: String(departmentContext?.child_canvas_id || node?.child_canvas_id || ""),
9704:       title,
9705:       detail: String(
9706:         node?.description ||
9707:         node?.detail ||
9708:         node?.config?.detail ||
9709:         node?.config?.department_goal?.sub_goal ||
9710:         departmentContext?.department_sub_goal ||
9711:         "Safe internal Goal Loop task preview."
9712:       ),
9713:       status: "waiting_human_approval",
9714:       queue_status: "preview_ready",
9715:       lane: "goal_loop_safe_internal_task",
9716:       safety: "internal_preview_only",
9717:       approval_required: true,
9718:       preview_only: true,
9719:       execution_blocked: true,
9720:       no_live_external_action: true,
9721:       external_side_effects: false,
9722:       message_sent: false,
9723:       booking_created: false,
9724:       payment_created: false,
9725:       persistence_required: false,
9726:       route_mutation_required: false,
```

### Around line 9638: `(typeof window !== "undefined" && window.__aionWorkflowGraph) ||`

```js
9593:         ...existingResults,
9594:         latest_central_preview: resultRecord,
9595:         central_preview_history: [
9596:           ...(Array.isArray(existingResults.central_preview_history) ? existingResults.central_preview_history : []),
9597:           resultRecord,
9598:         ],
9599:       },
9600:       evidence: [...(Array.isArray(entry.evidence) ? entry.evidence : []), evidenceRecord],
9601:       receipts: [...(Array.isArray(entry.receipts) ? entry.receipts : []), receiptRecord],
9602:       boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} received central AION approved action result: ${completedTask.title}. No live external action was taken.`,
9603:       confidence: "useful",
9604:       last_updated: now,
9605:     });
9606:   });
9607: 
9608:   const pilotState =
9609:     typeof getAionPilotFrontendInteractionState === "function"
9610:       ? getAionPilotFrontendInteractionState()
9611:       : null;
9612: 
9613:   if (pilotState) {
9614:     pilotState.status = "central_approved_task_completed";
9615:     pilotState.central_pilot_queue = queue;
9616:     pilotState.stream_events = [
9617:       ...(Array.isArray(pilotState.stream_events) ? pilotState.stream_events : []),
9618:       {
9619:         type: "central_approved_boardroom_action",
9620:         label: "Approved Boardroom action completed",
9621:         detail: completedTask.result_summary,
9622:         status: "completed_preview",
9623:       },
9624:     ];
9625:   }
9626: 
9627:   if (typeof requestRender === "function") {
9628:     requestRender();
9629:   }
9630: 
9631:   return completedTask;
9632: }
9633: 
9634: 
9635: /* AION GOAL LOOP CANVAS PHASE D3: Central Pilot Safe Task Queue from Goal Loop Graph */
9636: function getAionActiveGoalLoopGraphForCentralPilotQueue() {
9637:   const graph =
9638:     (typeof window !== "undefined" && window.__aionWorkflowGraph) ||
9639:     (typeof window !== "undefined" && window.__aionGoalLoopWorkflowGraph) ||
9640:     null;
9641: 
9642:   const isGoalLoop =
9643:     graph?.canvas_type === "goal_loop" ||
9644:     graph?.active_canvas_intent === "goal_loop" ||
9645:     graph?.goal_loop_contract?.goal_loop_id;
9646: 
9647:   return isGoalLoop ? graph : null;
9648: }
9649: 
9650: function buildAionGoalLoopCentralPilotTaskQueue() {
9651:   const graph = getAionActiveGoalLoopGraphForCentralPilotQueue();
9652:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
9653: 
9654:   const businessLabel =
9655:     typeof getAionWorkflowCanvasHeaderBusinessLabel === "function"
9656:       ? getAionWorkflowCanvasHeaderBusinessLabel()
9657:       : "Business not registered";
9658: 
9659:   const businessContainer =
9660:     typeof getAionWorkflowBusinessContainerId === "function"
9661:       ? getAionWorkflowBusinessContainerId()
9662:       : "business_not_registered";
9663: 
9664:   const goalLoopId = String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "not_staged");
9665:   const boardGoal = graph?.goal_loop_contract?.board_goal || {};
9666:   const boardGoalTitle = String(boardGoal.title || boardGoal.goal || "No Boardroom goal staged");
9667: 
9668:   const agentTaskNodes = nodes.filter((node) => {
9669:     const type = String(node?.node_type || node?.type || node?.data?.node_type || node?.data?.type || "").trim();
9670:     return type === "agent_task";
9671:   });
9672: 
9673:   const tasks = agentTaskNodes.map((node, index) => {
9674:     const department = normaliseAionDepartmentPilotKey(
9675:       node?.department ||
9676:       node?.data?.department ||
9677:       node?.meta?.department ||
9678:       node?.config?.department ||
9679:       node?.config?.department_goal?.department ||
9680:       "pilot"
9681:     );
9682: 
9683:     const title = String(node?.title || node?.label || `${department} Goal Loop task`);
9684:     const departmentContext =
9685:       typeof getAionActiveGoalLoopDepartmentContext === "function"
9686:         ? getAionActiveGoalLoopDepartmentContext(department)
9687:         : null;
9688: 
9689:     return {
9690:       id: String(node?.id || `${goalLoopId}_${department}_central_safe_task_${index + 1}`),
9691:       source_node_id: String(node?.id || ""),
9692:       source_node_type: "agent_task",
9693:       source: "goal_loop_graph_agent_task",
9694:       goal_loop_id: goalLoopId,
9695:       board_goal: boardGoalTitle,
9696:       business_label: businessLabel,
9697:       business_container: businessContainer,
9698:       department,
9699:       department_label:
9700:         typeof runtimeShared !== "undefined" && runtimeShared.getDepartmentLabel
9701:           ? runtimeShared.getDepartmentLabel(department)
9702:           : department,
9703:       department_child_canvas_id: String(departmentContext?.child_canvas_id || node?.child_canvas_id || ""),
9704:       title,
9705:       detail: String(
9706:         node?.description ||
9707:         node?.detail ||
9708:         node?.config?.detail ||
9709:         node?.config?.department_goal?.sub_goal ||
9710:         departmentContext?.department_sub_goal ||
9711:         "Safe internal Goal Loop task preview."
9712:       ),
9713:       status: "waiting_human_approval",
9714:       queue_status: "preview_ready",
9715:       lane: "goal_loop_safe_internal_task",
9716:       safety: "internal_preview_only",
9717:       approval_required: true,
9718:       preview_only: true,
9719:       execution_blocked: true,
9720:       no_live_external_action: true,
9721:       external_side_effects: false,
9722:       message_sent: false,
9723:       booking_created: false,
9724:       payment_created: false,
9725:       persistence_required: false,
9726:       route_mutation_required: false,
9727:       creates_second_pilot: false,
```

### Around line 9639: `(typeof window !== "undefined" && window.__aionGoalLoopWorkflowGraph) ||`

```js
9594:         latest_central_preview: resultRecord,
9595:         central_preview_history: [
9596:           ...(Array.isArray(existingResults.central_preview_history) ? existingResults.central_preview_history : []),
9597:           resultRecord,
9598:         ],
9599:       },
9600:       evidence: [...(Array.isArray(entry.evidence) ? entry.evidence : []), evidenceRecord],
9601:       receipts: [...(Array.isArray(entry.receipts) ? entry.receipts : []), receiptRecord],
9602:       boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} received central AION approved action result: ${completedTask.title}. No live external action was taken.`,
9603:       confidence: "useful",
9604:       last_updated: now,
9605:     });
9606:   });
9607: 
9608:   const pilotState =
9609:     typeof getAionPilotFrontendInteractionState === "function"
9610:       ? getAionPilotFrontendInteractionState()
9611:       : null;
9612: 
9613:   if (pilotState) {
9614:     pilotState.status = "central_approved_task_completed";
9615:     pilotState.central_pilot_queue = queue;
9616:     pilotState.stream_events = [
9617:       ...(Array.isArray(pilotState.stream_events) ? pilotState.stream_events : []),
9618:       {
9619:         type: "central_approved_boardroom_action",
9620:         label: "Approved Boardroom action completed",
9621:         detail: completedTask.result_summary,
9622:         status: "completed_preview",
9623:       },
9624:     ];
9625:   }
9626: 
9627:   if (typeof requestRender === "function") {
9628:     requestRender();
9629:   }
9630: 
9631:   return completedTask;
9632: }
9633: 
9634: 
9635: /* AION GOAL LOOP CANVAS PHASE D3: Central Pilot Safe Task Queue from Goal Loop Graph */
9636: function getAionActiveGoalLoopGraphForCentralPilotQueue() {
9637:   const graph =
9638:     (typeof window !== "undefined" && window.__aionWorkflowGraph) ||
9639:     (typeof window !== "undefined" && window.__aionGoalLoopWorkflowGraph) ||
9640:     null;
9641: 
9642:   const isGoalLoop =
9643:     graph?.canvas_type === "goal_loop" ||
9644:     graph?.active_canvas_intent === "goal_loop" ||
9645:     graph?.goal_loop_contract?.goal_loop_id;
9646: 
9647:   return isGoalLoop ? graph : null;
9648: }
9649: 
9650: function buildAionGoalLoopCentralPilotTaskQueue() {
9651:   const graph = getAionActiveGoalLoopGraphForCentralPilotQueue();
9652:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
9653: 
9654:   const businessLabel =
9655:     typeof getAionWorkflowCanvasHeaderBusinessLabel === "function"
9656:       ? getAionWorkflowCanvasHeaderBusinessLabel()
9657:       : "Business not registered";
9658: 
9659:   const businessContainer =
9660:     typeof getAionWorkflowBusinessContainerId === "function"
9661:       ? getAionWorkflowBusinessContainerId()
9662:       : "business_not_registered";
9663: 
9664:   const goalLoopId = String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "not_staged");
9665:   const boardGoal = graph?.goal_loop_contract?.board_goal || {};
9666:   const boardGoalTitle = String(boardGoal.title || boardGoal.goal || "No Boardroom goal staged");
9667: 
9668:   const agentTaskNodes = nodes.filter((node) => {
9669:     const type = String(node?.node_type || node?.type || node?.data?.node_type || node?.data?.type || "").trim();
9670:     return type === "agent_task";
9671:   });
9672: 
9673:   const tasks = agentTaskNodes.map((node, index) => {
9674:     const department = normaliseAionDepartmentPilotKey(
9675:       node?.department ||
9676:       node?.data?.department ||
9677:       node?.meta?.department ||
9678:       node?.config?.department ||
9679:       node?.config?.department_goal?.department ||
9680:       "pilot"
9681:     );
9682: 
9683:     const title = String(node?.title || node?.label || `${department} Goal Loop task`);
9684:     const departmentContext =
9685:       typeof getAionActiveGoalLoopDepartmentContext === "function"
9686:         ? getAionActiveGoalLoopDepartmentContext(department)
9687:         : null;
9688: 
9689:     return {
9690:       id: String(node?.id || `${goalLoopId}_${department}_central_safe_task_${index + 1}`),
9691:       source_node_id: String(node?.id || ""),
9692:       source_node_type: "agent_task",
9693:       source: "goal_loop_graph_agent_task",
9694:       goal_loop_id: goalLoopId,
9695:       board_goal: boardGoalTitle,
9696:       business_label: businessLabel,
9697:       business_container: businessContainer,
9698:       department,
9699:       department_label:
9700:         typeof runtimeShared !== "undefined" && runtimeShared.getDepartmentLabel
9701:           ? runtimeShared.getDepartmentLabel(department)
9702:           : department,
9703:       department_child_canvas_id: String(departmentContext?.child_canvas_id || node?.child_canvas_id || ""),
9704:       title,
9705:       detail: String(
9706:         node?.description ||
9707:         node?.detail ||
9708:         node?.config?.detail ||
9709:         node?.config?.department_goal?.sub_goal ||
9710:         departmentContext?.department_sub_goal ||
9711:         "Safe internal Goal Loop task preview."
9712:       ),
9713:       status: "waiting_human_approval",
9714:       queue_status: "preview_ready",
9715:       lane: "goal_loop_safe_internal_task",
9716:       safety: "internal_preview_only",
9717:       approval_required: true,
9718:       preview_only: true,
9719:       execution_blocked: true,
9720:       no_live_external_action: true,
9721:       external_side_effects: false,
9722:       message_sent: false,
9723:       booking_created: false,
9724:       payment_created: false,
9725:       persistence_required: false,
9726:       route_mutation_required: false,
9727:       creates_second_pilot: false,
9728:       creates_second_canvas: false,
```

### Around line 9651: `const graph = getAionActiveGoalLoopGraphForCentralPilotQueue();`

```js
9606:   });
9607: 
9608:   const pilotState =
9609:     typeof getAionPilotFrontendInteractionState === "function"
9610:       ? getAionPilotFrontendInteractionState()
9611:       : null;
9612: 
9613:   if (pilotState) {
9614:     pilotState.status = "central_approved_task_completed";
9615:     pilotState.central_pilot_queue = queue;
9616:     pilotState.stream_events = [
9617:       ...(Array.isArray(pilotState.stream_events) ? pilotState.stream_events : []),
9618:       {
9619:         type: "central_approved_boardroom_action",
9620:         label: "Approved Boardroom action completed",
9621:         detail: completedTask.result_summary,
9622:         status: "completed_preview",
9623:       },
9624:     ];
9625:   }
9626: 
9627:   if (typeof requestRender === "function") {
9628:     requestRender();
9629:   }
9630: 
9631:   return completedTask;
9632: }
9633: 
9634: 
9635: /* AION GOAL LOOP CANVAS PHASE D3: Central Pilot Safe Task Queue from Goal Loop Graph */
9636: function getAionActiveGoalLoopGraphForCentralPilotQueue() {
9637:   const graph =
9638:     (typeof window !== "undefined" && window.__aionWorkflowGraph) ||
9639:     (typeof window !== "undefined" && window.__aionGoalLoopWorkflowGraph) ||
9640:     null;
9641: 
9642:   const isGoalLoop =
9643:     graph?.canvas_type === "goal_loop" ||
9644:     graph?.active_canvas_intent === "goal_loop" ||
9645:     graph?.goal_loop_contract?.goal_loop_id;
9646: 
9647:   return isGoalLoop ? graph : null;
9648: }
9649: 
9650: function buildAionGoalLoopCentralPilotTaskQueue() {
9651:   const graph = getAionActiveGoalLoopGraphForCentralPilotQueue();
9652:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
9653: 
9654:   const businessLabel =
9655:     typeof getAionWorkflowCanvasHeaderBusinessLabel === "function"
9656:       ? getAionWorkflowCanvasHeaderBusinessLabel()
9657:       : "Business not registered";
9658: 
9659:   const businessContainer =
9660:     typeof getAionWorkflowBusinessContainerId === "function"
9661:       ? getAionWorkflowBusinessContainerId()
9662:       : "business_not_registered";
9663: 
9664:   const goalLoopId = String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "not_staged");
9665:   const boardGoal = graph?.goal_loop_contract?.board_goal || {};
9666:   const boardGoalTitle = String(boardGoal.title || boardGoal.goal || "No Boardroom goal staged");
9667: 
9668:   const agentTaskNodes = nodes.filter((node) => {
9669:     const type = String(node?.node_type || node?.type || node?.data?.node_type || node?.data?.type || "").trim();
9670:     return type === "agent_task";
9671:   });
9672: 
9673:   const tasks = agentTaskNodes.map((node, index) => {
9674:     const department = normaliseAionDepartmentPilotKey(
9675:       node?.department ||
9676:       node?.data?.department ||
9677:       node?.meta?.department ||
9678:       node?.config?.department ||
9679:       node?.config?.department_goal?.department ||
9680:       "pilot"
9681:     );
9682: 
9683:     const title = String(node?.title || node?.label || `${department} Goal Loop task`);
9684:     const departmentContext =
9685:       typeof getAionActiveGoalLoopDepartmentContext === "function"
9686:         ? getAionActiveGoalLoopDepartmentContext(department)
9687:         : null;
9688: 
9689:     return {
9690:       id: String(node?.id || `${goalLoopId}_${department}_central_safe_task_${index + 1}`),
9691:       source_node_id: String(node?.id || ""),
9692:       source_node_type: "agent_task",
9693:       source: "goal_loop_graph_agent_task",
9694:       goal_loop_id: goalLoopId,
9695:       board_goal: boardGoalTitle,
9696:       business_label: businessLabel,
9697:       business_container: businessContainer,
9698:       department,
9699:       department_label:
9700:         typeof runtimeShared !== "undefined" && runtimeShared.getDepartmentLabel
9701:           ? runtimeShared.getDepartmentLabel(department)
9702:           : department,
9703:       department_child_canvas_id: String(departmentContext?.child_canvas_id || node?.child_canvas_id || ""),
9704:       title,
9705:       detail: String(
9706:         node?.description ||
9707:         node?.detail ||
9708:         node?.config?.detail ||
9709:         node?.config?.department_goal?.sub_goal ||
9710:         departmentContext?.department_sub_goal ||
9711:         "Safe internal Goal Loop task preview."
9712:       ),
9713:       status: "waiting_human_approval",
9714:       queue_status: "preview_ready",
9715:       lane: "goal_loop_safe_internal_task",
9716:       safety: "internal_preview_only",
9717:       approval_required: true,
9718:       preview_only: true,
9719:       execution_blocked: true,
9720:       no_live_external_action: true,
9721:       external_side_effects: false,
9722:       message_sent: false,
9723:       booking_created: false,
9724:       payment_created: false,
9725:       persistence_required: false,
9726:       route_mutation_required: false,
9727:       creates_second_pilot: false,
9728:       creates_second_canvas: false,
9729:     };
9730:   });
9731: 
9732:   const grouped = tasks.reduce((acc, task) => {
9733:     const key = task.department || "pilot";
9734:     acc[key] = acc[key] || [];
9735:     acc[key].push(task);
9736:     return acc;
9737:   }, {});
9738: 
9739:   return {
9740:     schema_version: "aion.goal_loop.central_pilot_safe_task_queue.v1",
```

### Around line 10043: `const graph =`

```js
9998: ];
9999: 
10000: const AION_GOAL_LOOP_METRIC_SOURCES = [
10001:   "manual",
10002:   "connector_placeholder",
10003: ];
10004: 
10005: function buildAionGoalLoopMetricSchema(overrides = {}) {
10006:   const department = normaliseAionDepartmentPilotKey(overrides.department || "marketing");
10007:   const goalId = String(overrides.goal_id || overrides.goalId || "goal_not_staged");
10008:   const sourceNodeId = String(overrides.source_node_id || overrides.sourceNodeId || "");
10009: 
10010:   return {
10011:     schema_version: "aion.goal_loop_metric.v1",
10012:     metric_id: String(overrides.metric_id || overrides.metricId || `${goalId}_${department}_metric_preview`),
10013:     goal_id: goalId,
10014:     department,
10015:     source_node_id: sourceNodeId,
10016:     name: String(overrides.name || "goal_loop_metric"),
10017:     target: overrides.target ?? null,
10018:     actual: overrides.actual ?? null,
10019:     unit: String(overrides.unit || ""),
10020:     trend: AION_GOAL_LOOP_METRIC_TRENDS.includes(String(overrides.trend || "unknown"))
10021:       ? String(overrides.trend || "unknown")
10022:       : "unknown",
10023:     confidence: AION_GOAL_LOOP_METRIC_CONFIDENCE_LEVELS.includes(String(overrides.confidence || "unknown"))
10024:       ? String(overrides.confidence || "unknown")
10025:       : "unknown",
10026:     source: AION_GOAL_LOOP_METRIC_SOURCES.includes(String(overrides.source || "manual"))
10027:       ? String(overrides.source || "manual")
10028:       : "manual",
10029:     evidence_ids: Array.isArray(overrides.evidence_ids) ? overrides.evidence_ids.map(String) : [],
10030:     status: String(overrides.status || "schema_only"),
10031:     manual_entry_supported: true,
10032:     connector_placeholder_supported: true,
10033:     connector_call_required: false,
10034:     preview_only: true,
10035:     execution_blocked: true,
10036:     persistence_required: false,
10037:     external_side_effects: false,
10038:   };
10039: }
10040: 
10041: function buildAionGoalLoopDepartmentMetricSet(departmentKey = "", options = {}) {
10042:   const key = normaliseAionDepartmentPilotKey(departmentKey);
10043:   const graph =
10044:     options.graph && typeof options.graph === "object"
10045:       ? options.graph
10046:       : typeof getAionActiveGoalLoopGraphForCentralPilotQueue === "function"
10047:         ? getAionActiveGoalLoopGraphForCentralPilotQueue()
10048:         : null;
10049: 
10050:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
10051:   const goalId = String(graph?.goal_loop_contract?.board_goal?.goal_id || graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "goal_not_staged");
10052: 
10053:   const measurementNodes = nodes.filter((node) => {
10054:     const nodeDepartment = normaliseAionDepartmentPilotKey(
10055:       node?.department ||
10056:       node?.data?.department ||
10057:       node?.meta?.department ||
10058:       node?.config?.department ||
10059:       node?.config?.department_goal?.department ||
10060:       ""
10061:     );
10062:     const nodeType = String(node?.node_type || node?.type || node?.data?.node_type || node?.data?.type || "");
10063:     return nodeDepartment === key && nodeType === "measurement_plan";
10064:   });
10065: 
10066:   const fallbackMetric = buildAionGoalLoopMetricSchema({
10067:     metric_id: `${goalId}_${key}_manual_metric_placeholder`,
10068:     goal_id: goalId,
10069:     department: key,
10070:     source_node_id: measurementNodes[0]?.id || "",
10071:     name: `${key}_goal_progress`,
10072:     target: null,
10073:     actual: null,
10074:     unit: "",
10075:     trend: "unknown",
10076:     confidence: "unknown",
10077:     source: "manual",
10078:     evidence_ids: [],
10079:   });
10080: 
10081:   const metrics = measurementNodes.length
10082:     ? measurementNodes.map((node, index) => buildAionGoalLoopMetricSchema({
10083:         metric_id: `${goalId}_${key}_metric_${index + 1}`,
10084:         goal_id: goalId,
10085:         department: key,
10086:         source_node_id: node.id || "",
10087:         name: String(node?.config?.metric_name || node?.metric_name || node?.title || `${key}_metric_${index + 1}`)
10088:           .toLowerCase()
10089:           .replace(/[^a-z0-9]+/g, "_")
10090:           .replace(/^_+|_+$/g, "")
10091:           .slice(0, 80) || `${key}_metric_${index + 1}`,
10092:         target: node?.config?.target ?? null,
10093:         actual: null,
10094:         unit: String(node?.config?.unit || ""),
10095:         trend: "unknown",
10096:         confidence: "unknown",
10097:         source: "manual",
10098:         evidence_ids: [],
10099:       }))
10100:     : [fallbackMetric];
10101: 
10102:   return {
10103:     schema_version: "aion.goal_loop_department_metric_set.v1",
10104:     department: key,
10105:     goal_id: goalId,
10106:     source: "goal_loop_measurement_plan_nodes",
10107:     metric_count: metrics.length,
10108:     metrics,
10109:     manual_entry_supported: true,
10110:     connector_placeholder_supported: true,
10111:     connector_call_required: false,
10112:     preview_only: true,
10113:     execution_blocked: true,
10114:     persistence_required: false,
10115:     external_side_effects: false,
10116:   };
10117: }
10118: 
10119: function attachAionGoalLoopMetricsToGraph(options = {}) {
10120:   const graph =
10121:     options.graph && typeof options.graph === "object"
10122:       ? options.graph
10123:       : typeof getAionActiveGoalLoopGraphForCentralPilotQueue === "function"
10124:         ? getAionActiveGoalLoopGraphForCentralPilotQueue()
10125:         : null;
10126: 
10127:   const departments = Array.isArray(graph?.department_child_canvases)
10128:     ? graph.department_child_canvases.map((canvas) => normaliseAionDepartmentPilotKey(canvas.department || "")).filter(Boolean)
10129:     : ["marketing", "sales", "finance", "operations", "support"];
10130: 
10131:   const uniqueDepartments = Array.from(new Set(departments));
10132:   const metricSets = uniqueDepartments.map((department) =>
```

### Around line 10120: `const graph =`

```js
10075:     trend: "unknown",
10076:     confidence: "unknown",
10077:     source: "manual",
10078:     evidence_ids: [],
10079:   });
10080: 
10081:   const metrics = measurementNodes.length
10082:     ? measurementNodes.map((node, index) => buildAionGoalLoopMetricSchema({
10083:         metric_id: `${goalId}_${key}_metric_${index + 1}`,
10084:         goal_id: goalId,
10085:         department: key,
10086:         source_node_id: node.id || "",
10087:         name: String(node?.config?.metric_name || node?.metric_name || node?.title || `${key}_metric_${index + 1}`)
10088:           .toLowerCase()
10089:           .replace(/[^a-z0-9]+/g, "_")
10090:           .replace(/^_+|_+$/g, "")
10091:           .slice(0, 80) || `${key}_metric_${index + 1}`,
10092:         target: node?.config?.target ?? null,
10093:         actual: null,
10094:         unit: String(node?.config?.unit || ""),
10095:         trend: "unknown",
10096:         confidence: "unknown",
10097:         source: "manual",
10098:         evidence_ids: [],
10099:       }))
10100:     : [fallbackMetric];
10101: 
10102:   return {
10103:     schema_version: "aion.goal_loop_department_metric_set.v1",
10104:     department: key,
10105:     goal_id: goalId,
10106:     source: "goal_loop_measurement_plan_nodes",
10107:     metric_count: metrics.length,
10108:     metrics,
10109:     manual_entry_supported: true,
10110:     connector_placeholder_supported: true,
10111:     connector_call_required: false,
10112:     preview_only: true,
10113:     execution_blocked: true,
10114:     persistence_required: false,
10115:     external_side_effects: false,
10116:   };
10117: }
10118: 
10119: function attachAionGoalLoopMetricsToGraph(options = {}) {
10120:   const graph =
10121:     options.graph && typeof options.graph === "object"
10122:       ? options.graph
10123:       : typeof getAionActiveGoalLoopGraphForCentralPilotQueue === "function"
10124:         ? getAionActiveGoalLoopGraphForCentralPilotQueue()
10125:         : null;
10126: 
10127:   const departments = Array.isArray(graph?.department_child_canvases)
10128:     ? graph.department_child_canvases.map((canvas) => normaliseAionDepartmentPilotKey(canvas.department || "")).filter(Boolean)
10129:     : ["marketing", "sales", "finance", "operations", "support"];
10130: 
10131:   const uniqueDepartments = Array.from(new Set(departments));
10132:   const metricSets = uniqueDepartments.map((department) =>
10133:     buildAionGoalLoopDepartmentMetricSet(department, { graph })
10134:   );
10135: 
10136:   const metrics = metricSets.flatMap((set) => Array.isArray(set.metrics) ? set.metrics : []);
10137: 
10138:   const attachment = {
10139:     schema_version: "aion.goal_loop_measurement_attachment.v1",
10140:     status: graph ? "measurement_schema_attached_preview" : "no_active_goal_loop",
10141:     goal_loop_id: String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "not_staged"),
10142:     department_count: uniqueDepartments.length,
10143:     metric_count: metrics.length,
10144:     metric_trends: AION_GOAL_LOOP_METRIC_TRENDS,
10145:     metric_confidence_levels: AION_GOAL_LOOP_METRIC_CONFIDENCE_LEVELS,
10146:     metric_sources: AION_GOAL_LOOP_METRIC_SOURCES,
10147:     department_metric_sets: metricSets,
10148:     goal_loop_metrics: metrics,
10149:     manual_entry_supported: true,
10150:     connector_placeholder_supported: true,
10151:     connector_call_required: false,
10152:     preview_only: true,
10153:     execution_blocked: true,
10154:     persistence_required: false,
10155:     external_side_effects: false,
10156:     message_sent: false,
10157:     booking_created: false,
10158:     payment_created: false,
10159:     creates_second_canvas: false,
10160:     creates_second_pilot: false,
10161:   };
10162: 
10163:   if (graph && typeof graph === "object") {
10164:     graph.goal_loop_metrics = metrics;
10165:     graph.goal_loop_metric_sets = metricSets;
10166:     graph.goal_loop_measurement_attachment = attachment;
10167: 
10168:     if (graph.goal_loop_contract && typeof graph.goal_loop_contract === "object") {
10169:       graph.goal_loop_contract.goal_loop_metrics = metrics;
10170:       graph.goal_loop_contract.goal_loop_metric_sets = metricSets;
10171:     }
10172: 
10173:     if (typeof window !== "undefined") {
10174:       window.__aionGoalLoopMeasurementAttachment = attachment;
10175:       window.__aionWorkflowGraph = graph;
10176:       window.__aionGoalLoopWorkflowGraph = graph;
10177:     }
10178:   }
10179: 
10180:   return attachment;
10181: }
10182: 
10183: 
10184: /* AION GOAL LOOP CANVAS PHASE E2: Manual Result Capture Preview */
10185: function buildAionGoalLoopManualResultSnapshot(options = {}) {
10186:   const attachment =
10187:     options.attachment && typeof options.attachment === "object"
10188:       ? options.attachment
10189:       : typeof attachAionGoalLoopMetricsToGraph === "function"
10190:         ? attachAionGoalLoopMetricsToGraph()
10191:         : { goal_loop_metrics: [], goal_loop_id: "not_staged" };
10192: 
10193:   const metrics = Array.isArray(attachment.goal_loop_metrics) ? attachment.goal_loop_metrics : [];
10194:   const selectedMetric = options.metric && typeof options.metric === "object"
10195:     ? options.metric
10196:     : metrics[0] || buildAionGoalLoopMetricSchema({});
10197: 
10198:   const department = normaliseAionDepartmentPilotKey(options.department || selectedMetric.department || "marketing");
10199:   const now = new Date().toISOString();
10200:   const actualValue = options.actual ?? selectedMetric.actual ?? "";
10201:   const confidence = AION_GOAL_LOOP_METRIC_CONFIDENCE_LEVELS.includes(String(options.confidence || "partial"))
10202:     ? String(options.confidence || "partial")
10203:     : "partial";
10204: 
10205:   return {
10206:     schema_version: "aion.goal_loop_manual_result_snapshot.v1",
10207:     result_id: String(options.result_id || `${selectedMetric.metric_id || "metric"}_manual_result_preview`),
10208:     goal_loop_id: String(options.goal_loop_id || attachment.goal_loop_id || "not_staged"),
10209:     goal_id: String(selectedMetric.goal_id || "goal_not_staged"),
```

### Around line 10175: `window.__aionWorkflowGraph = graph;`

```js
10130: 
10131:   const uniqueDepartments = Array.from(new Set(departments));
10132:   const metricSets = uniqueDepartments.map((department) =>
10133:     buildAionGoalLoopDepartmentMetricSet(department, { graph })
10134:   );
10135: 
10136:   const metrics = metricSets.flatMap((set) => Array.isArray(set.metrics) ? set.metrics : []);
10137: 
10138:   const attachment = {
10139:     schema_version: "aion.goal_loop_measurement_attachment.v1",
10140:     status: graph ? "measurement_schema_attached_preview" : "no_active_goal_loop",
10141:     goal_loop_id: String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "not_staged"),
10142:     department_count: uniqueDepartments.length,
10143:     metric_count: metrics.length,
10144:     metric_trends: AION_GOAL_LOOP_METRIC_TRENDS,
10145:     metric_confidence_levels: AION_GOAL_LOOP_METRIC_CONFIDENCE_LEVELS,
10146:     metric_sources: AION_GOAL_LOOP_METRIC_SOURCES,
10147:     department_metric_sets: metricSets,
10148:     goal_loop_metrics: metrics,
10149:     manual_entry_supported: true,
10150:     connector_placeholder_supported: true,
10151:     connector_call_required: false,
10152:     preview_only: true,
10153:     execution_blocked: true,
10154:     persistence_required: false,
10155:     external_side_effects: false,
10156:     message_sent: false,
10157:     booking_created: false,
10158:     payment_created: false,
10159:     creates_second_canvas: false,
10160:     creates_second_pilot: false,
10161:   };
10162: 
10163:   if (graph && typeof graph === "object") {
10164:     graph.goal_loop_metrics = metrics;
10165:     graph.goal_loop_metric_sets = metricSets;
10166:     graph.goal_loop_measurement_attachment = attachment;
10167: 
10168:     if (graph.goal_loop_contract && typeof graph.goal_loop_contract === "object") {
10169:       graph.goal_loop_contract.goal_loop_metrics = metrics;
10170:       graph.goal_loop_contract.goal_loop_metric_sets = metricSets;
10171:     }
10172: 
10173:     if (typeof window !== "undefined") {
10174:       window.__aionGoalLoopMeasurementAttachment = attachment;
10175:       window.__aionWorkflowGraph = graph;
10176:       window.__aionGoalLoopWorkflowGraph = graph;
10177:     }
10178:   }
10179: 
10180:   return attachment;
10181: }
10182: 
10183: 
10184: /* AION GOAL LOOP CANVAS PHASE E2: Manual Result Capture Preview */
10185: function buildAionGoalLoopManualResultSnapshot(options = {}) {
10186:   const attachment =
10187:     options.attachment && typeof options.attachment === "object"
10188:       ? options.attachment
10189:       : typeof attachAionGoalLoopMetricsToGraph === "function"
10190:         ? attachAionGoalLoopMetricsToGraph()
10191:         : { goal_loop_metrics: [], goal_loop_id: "not_staged" };
10192: 
10193:   const metrics = Array.isArray(attachment.goal_loop_metrics) ? attachment.goal_loop_metrics : [];
10194:   const selectedMetric = options.metric && typeof options.metric === "object"
10195:     ? options.metric
10196:     : metrics[0] || buildAionGoalLoopMetricSchema({});
10197: 
10198:   const department = normaliseAionDepartmentPilotKey(options.department || selectedMetric.department || "marketing");
10199:   const now = new Date().toISOString();
10200:   const actualValue = options.actual ?? selectedMetric.actual ?? "";
10201:   const confidence = AION_GOAL_LOOP_METRIC_CONFIDENCE_LEVELS.includes(String(options.confidence || "partial"))
10202:     ? String(options.confidence || "partial")
10203:     : "partial";
10204: 
10205:   return {
10206:     schema_version: "aion.goal_loop_manual_result_snapshot.v1",
10207:     result_id: String(options.result_id || `${selectedMetric.metric_id || "metric"}_manual_result_preview`),
10208:     goal_loop_id: String(options.goal_loop_id || attachment.goal_loop_id || "not_staged"),
10209:     goal_id: String(selectedMetric.goal_id || "goal_not_staged"),
10210:     metric_id: String(selectedMetric.metric_id || ""),
10211:     department,
10212:     source_node_id: String(selectedMetric.source_node_id || ""),
10213:     metric_name: String(selectedMetric.name || "goal_loop_metric"),
10214:     target: selectedMetric.target ?? null,
10215:     actual: actualValue,
10216:     unit: String(selectedMetric.unit || ""),
10217:     confidence,
10218:     note: String(options.note || "Manual result preview. Replace with real value during approved capture."),
10219:     evidence_note: String(options.evidence_note || "Evidence placeholder. Attach proof/evidence in later phase."),
10220:     evidence_ids: Array.isArray(options.evidence_ids) ? options.evidence_ids.map(String) : [],
10221:     source: "manual",
10222:     capture_mode: "manual_preview",
10223:     status: "manual_result_preview",
10224:     captured_at_preview: now,
10225:     preview_only: true,
10226:     connector_call_required: false,
10227:     ledger_mutation_required: false,
10228:     persistence_required: false,
10229:     execution_blocked: true,
10230:     external_side_effects: false,
10231:     message_sent: false,
10232:     booking_created: false,
10233:     payment_created: false,
10234:     creates_second_canvas: false,
10235:     creates_second_pilot: false,
10236:     provenance: {
10237:       source: "goal_loop_manual_result_capture_preview",
10238:       generated_by: "aion_goal_loop_phase_e2",
10239:       generated_at: now,
10240:       department,
10241:       metric_id: String(selectedMetric.metric_id || ""),
10242:     },
10243:   };
10244: }
10245: 
10246: function previewAionGoalLoopManualResultCapture(options = {}) {
10247:   const attachment =
10248:     options.attachment && typeof options.attachment === "object"
10249:       ? options.attachment
10250:       : typeof attachAionGoalLoopMetricsToGraph === "function"
10251:         ? attachAionGoalLoopMetricsToGraph()
10252:         : { goal_loop_metrics: [], goal_loop_id: "not_staged" };
10253: 
10254:   const metrics = Array.isArray(attachment.goal_loop_metrics) ? attachment.goal_loop_metrics : [];
10255:   const snapshots = metrics.map((metric) =>
10256:     buildAionGoalLoopManualResultSnapshot({
10257:       ...options,
10258:       metric,
10259:       department: metric.department,
10260:       attachment,
10261:     })
10262:   );
10263: 
10264:   const resultSnapshots = snapshots.length
```

### Around line 10176: `window.__aionGoalLoopWorkflowGraph = graph;`

```js
10131:   const uniqueDepartments = Array.from(new Set(departments));
10132:   const metricSets = uniqueDepartments.map((department) =>
10133:     buildAionGoalLoopDepartmentMetricSet(department, { graph })
10134:   );
10135: 
10136:   const metrics = metricSets.flatMap((set) => Array.isArray(set.metrics) ? set.metrics : []);
10137: 
10138:   const attachment = {
10139:     schema_version: "aion.goal_loop_measurement_attachment.v1",
10140:     status: graph ? "measurement_schema_attached_preview" : "no_active_goal_loop",
10141:     goal_loop_id: String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "not_staged"),
10142:     department_count: uniqueDepartments.length,
10143:     metric_count: metrics.length,
10144:     metric_trends: AION_GOAL_LOOP_METRIC_TRENDS,
10145:     metric_confidence_levels: AION_GOAL_LOOP_METRIC_CONFIDENCE_LEVELS,
10146:     metric_sources: AION_GOAL_LOOP_METRIC_SOURCES,
10147:     department_metric_sets: metricSets,
10148:     goal_loop_metrics: metrics,
10149:     manual_entry_supported: true,
10150:     connector_placeholder_supported: true,
10151:     connector_call_required: false,
10152:     preview_only: true,
10153:     execution_blocked: true,
10154:     persistence_required: false,
10155:     external_side_effects: false,
10156:     message_sent: false,
10157:     booking_created: false,
10158:     payment_created: false,
10159:     creates_second_canvas: false,
10160:     creates_second_pilot: false,
10161:   };
10162: 
10163:   if (graph && typeof graph === "object") {
10164:     graph.goal_loop_metrics = metrics;
10165:     graph.goal_loop_metric_sets = metricSets;
10166:     graph.goal_loop_measurement_attachment = attachment;
10167: 
10168:     if (graph.goal_loop_contract && typeof graph.goal_loop_contract === "object") {
10169:       graph.goal_loop_contract.goal_loop_metrics = metrics;
10170:       graph.goal_loop_contract.goal_loop_metric_sets = metricSets;
10171:     }
10172: 
10173:     if (typeof window !== "undefined") {
10174:       window.__aionGoalLoopMeasurementAttachment = attachment;
10175:       window.__aionWorkflowGraph = graph;
10176:       window.__aionGoalLoopWorkflowGraph = graph;
10177:     }
10178:   }
10179: 
10180:   return attachment;
10181: }
10182: 
10183: 
10184: /* AION GOAL LOOP CANVAS PHASE E2: Manual Result Capture Preview */
10185: function buildAionGoalLoopManualResultSnapshot(options = {}) {
10186:   const attachment =
10187:     options.attachment && typeof options.attachment === "object"
10188:       ? options.attachment
10189:       : typeof attachAionGoalLoopMetricsToGraph === "function"
10190:         ? attachAionGoalLoopMetricsToGraph()
10191:         : { goal_loop_metrics: [], goal_loop_id: "not_staged" };
10192: 
10193:   const metrics = Array.isArray(attachment.goal_loop_metrics) ? attachment.goal_loop_metrics : [];
10194:   const selectedMetric = options.metric && typeof options.metric === "object"
10195:     ? options.metric
10196:     : metrics[0] || buildAionGoalLoopMetricSchema({});
10197: 
10198:   const department = normaliseAionDepartmentPilotKey(options.department || selectedMetric.department || "marketing");
10199:   const now = new Date().toISOString();
10200:   const actualValue = options.actual ?? selectedMetric.actual ?? "";
10201:   const confidence = AION_GOAL_LOOP_METRIC_CONFIDENCE_LEVELS.includes(String(options.confidence || "partial"))
10202:     ? String(options.confidence || "partial")
10203:     : "partial";
10204: 
10205:   return {
10206:     schema_version: "aion.goal_loop_manual_result_snapshot.v1",
10207:     result_id: String(options.result_id || `${selectedMetric.metric_id || "metric"}_manual_result_preview`),
10208:     goal_loop_id: String(options.goal_loop_id || attachment.goal_loop_id || "not_staged"),
10209:     goal_id: String(selectedMetric.goal_id || "goal_not_staged"),
10210:     metric_id: String(selectedMetric.metric_id || ""),
10211:     department,
10212:     source_node_id: String(selectedMetric.source_node_id || ""),
10213:     metric_name: String(selectedMetric.name || "goal_loop_metric"),
10214:     target: selectedMetric.target ?? null,
10215:     actual: actualValue,
10216:     unit: String(selectedMetric.unit || ""),
10217:     confidence,
10218:     note: String(options.note || "Manual result preview. Replace with real value during approved capture."),
10219:     evidence_note: String(options.evidence_note || "Evidence placeholder. Attach proof/evidence in later phase."),
10220:     evidence_ids: Array.isArray(options.evidence_ids) ? options.evidence_ids.map(String) : [],
10221:     source: "manual",
10222:     capture_mode: "manual_preview",
10223:     status: "manual_result_preview",
10224:     captured_at_preview: now,
10225:     preview_only: true,
10226:     connector_call_required: false,
10227:     ledger_mutation_required: false,
10228:     persistence_required: false,
10229:     execution_blocked: true,
10230:     external_side_effects: false,
10231:     message_sent: false,
10232:     booking_created: false,
10233:     payment_created: false,
10234:     creates_second_canvas: false,
10235:     creates_second_pilot: false,
10236:     provenance: {
10237:       source: "goal_loop_manual_result_capture_preview",
10238:       generated_by: "aion_goal_loop_phase_e2",
10239:       generated_at: now,
10240:       department,
10241:       metric_id: String(selectedMetric.metric_id || ""),
10242:     },
10243:   };
10244: }
10245: 
10246: function previewAionGoalLoopManualResultCapture(options = {}) {
10247:   const attachment =
10248:     options.attachment && typeof options.attachment === "object"
10249:       ? options.attachment
10250:       : typeof attachAionGoalLoopMetricsToGraph === "function"
10251:         ? attachAionGoalLoopMetricsToGraph()
10252:         : { goal_loop_metrics: [], goal_loop_id: "not_staged" };
10253: 
10254:   const metrics = Array.isArray(attachment.goal_loop_metrics) ? attachment.goal_loop_metrics : [];
10255:   const snapshots = metrics.map((metric) =>
10256:     buildAionGoalLoopManualResultSnapshot({
10257:       ...options,
10258:       metric,
10259:       department: metric.department,
10260:       attachment,
10261:     })
10262:   );
10263: 
10264:   const resultSnapshots = snapshots.length
10265:     ? snapshots
```

### Around line 10720: `status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",`

```js
10675:     external_side_effects: false,
10676:     message_sent: false,
10677:     booking_created: false,
10678:     payment_created: false,
10679:     creates_second_canvas: false,
10680:     creates_second_pilot: false,
10681:     provenance: {
10682:       source: "goal_loop_evaluation_preview",
10683:       generated_by: "aion_goal_loop_phase_f1",
10684:       generated_at: now,
10685:       source_evaluation_id: String(sourceEvaluation.evaluation_id || ""),
10686:       department,
10687:     },
10688:   };
10689: }
10690: 
10691: function buildAionGoalLoopAbTestLifecyclePreview(options = {}) {
10692:   const evaluationPreview =
10693:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10694:       ? options.evaluation_preview
10695:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10696:         ? buildAionGoalLoopEvaluationPreview()
10697:         : { evaluations: [], goal_loop_id: "not_staged" };
10698: 
10699:   const evaluations = Array.isArray(evaluationPreview.evaluations) ? evaluationPreview.evaluations : [];
10700:   const abCandidates = evaluations.filter((evaluation) =>
10701:     evaluation.next_action === "propose_ab_test" ||
10702:     evaluation.status === "off_track"
10703:   );
10704: 
10705:   const nodes = (abCandidates.length ? abCandidates : evaluations.slice(0, 1)).map((evaluation) =>
10706:     buildAionGoalLoopAbTestNode({ evaluation, evaluation_preview: evaluationPreview })
10707:   );
10708: 
10709:   const lifecycleSteps = AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES.map((status, index) => ({
10710:     step_index: index + 1,
10711:     status,
10712:     label: status.replace(/_/g, " "),
10713:     preview_only: true,
10714:     approval_required: ["approved", "running", "measuring"].includes(status),
10715:     execution_blocked: true,
10716:   }));
10717: 
10718:   const preview = {
10719:     schema_version: "aion.goal_loop_ab_test_lifecycle_preview.v1",
10720:     status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",
10721:     goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10722:     lifecycle_statuses: AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES,
10723:     lifecycle_steps: lifecycleSteps,
10724:     ab_test_count: nodes.length,
10725:     ab_test_nodes: nodes,
10726:     boardroom_ab_summary: {
10727:       schema_version: "aion.goal_loop_boardroom_ab_summary.v1",
10728:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10729:       status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",
10730:       proposal_count: nodes.length,
10731:       required_board_review: nodes.length > 0,
10732:       summary: nodes.length
10733:         ? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.`
10734:         : "No A/B test proposals are ready yet.",
10735:       preview_only: true,
10736:     },
10737:     graph_ab_test_patch_preview: {
10738:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10739:       ab_test_node_additions: nodes.map((node) => ({
10740:         node_id: node.node_id,
10741:         node_type: "ab_test",
10742:         department: node.department,
10743:         source_evaluation_id: node.source_evaluation_id,
10744:         lifecycle_status: node.lifecycle_status,
10745:         approval_state: node.approval_state,
10746:         writeback_preview: true,
10747:       })),
10748:       preview_only: true,
10749:       graph_mutation_required: false,
10750:     },
10751:     preview_only: true,
10752:     approval_required: true,
10753:     campaign_launch_required: false,
10754:     connector_call_required: false,
10755:     execution_blocked: true,
10756:     persistence_required: false,
10757:     external_side_effects: false,
10758:     message_sent: false,
10759:     booking_created: false,
10760:     payment_created: false,
10761:     creates_second_canvas: false,
10762:     creates_second_pilot: false,
10763:   };
10764: 
10765:   if (typeof window !== "undefined") {
10766:     window.__aionGoalLoopAbTestLifecyclePreview = preview;
10767:   }
10768: 
10769:   return preview;
10770: }
10771: 
10772: 
10773: /* AION GOAL LOOP CANVAS PHASE F2: Generate A/B Test from Evaluation */
10774: function buildAionGoalLoopAbTestProposalFromEvaluation(evaluation = {}, options = {}) {
10775:   const safeEvaluation =
10776:     evaluation && typeof evaluation === "object" && !Array.isArray(evaluation)
10777:       ? evaluation
10778:       : {};
10779: 
10780:   const department = normaliseAionDepartmentPilotKey(
10781:     options.department ||
10782:     safeEvaluation.department ||
10783:     "marketing"
10784:   );
10785: 
10786:   const now = new Date().toISOString();
10787:   const evaluationId = String(safeEvaluation.evaluation_id || options.evaluation_id || "evaluation_preview");
10788:   const goalLoopId = String(options.goal_loop_id || safeEvaluation.goal_loop_id || "not_staged");
10789:   const goalId = String(options.goal_id || safeEvaluation.goal_id || "goal_not_staged");
10790:   const metricId = String(options.metric_id || safeEvaluation.metric_id || "");
10791:   const recommendation = String(
10792:     options.recommendation ||
10793:     safeEvaluation.recommendation ||
10794:     "Test a controlled improvement before scaling."
10795:   );
10796: 
10797:   const variantA = {
10798:     id: "variant_a",
10799:     label: String(options.variant_a_label || "Current approach"),
10800:     description: String(
10801:       options.variant_a_description ||
10802:       "Keep the current department loop unchanged as the control."
10803:     ),
10804:     source: "baseline",
10805:     preview_only: true,
10806:   };
10807: 
10808:   const variantB = {
10809:     id: "variant_b",
```

### Around line 10724: `ab_test_count: nodes.length,`

```js
10679:     creates_second_canvas: false,
10680:     creates_second_pilot: false,
10681:     provenance: {
10682:       source: "goal_loop_evaluation_preview",
10683:       generated_by: "aion_goal_loop_phase_f1",
10684:       generated_at: now,
10685:       source_evaluation_id: String(sourceEvaluation.evaluation_id || ""),
10686:       department,
10687:     },
10688:   };
10689: }
10690: 
10691: function buildAionGoalLoopAbTestLifecyclePreview(options = {}) {
10692:   const evaluationPreview =
10693:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10694:       ? options.evaluation_preview
10695:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10696:         ? buildAionGoalLoopEvaluationPreview()
10697:         : { evaluations: [], goal_loop_id: "not_staged" };
10698: 
10699:   const evaluations = Array.isArray(evaluationPreview.evaluations) ? evaluationPreview.evaluations : [];
10700:   const abCandidates = evaluations.filter((evaluation) =>
10701:     evaluation.next_action === "propose_ab_test" ||
10702:     evaluation.status === "off_track"
10703:   );
10704: 
10705:   const nodes = (abCandidates.length ? abCandidates : evaluations.slice(0, 1)).map((evaluation) =>
10706:     buildAionGoalLoopAbTestNode({ evaluation, evaluation_preview: evaluationPreview })
10707:   );
10708: 
10709:   const lifecycleSteps = AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES.map((status, index) => ({
10710:     step_index: index + 1,
10711:     status,
10712:     label: status.replace(/_/g, " "),
10713:     preview_only: true,
10714:     approval_required: ["approved", "running", "measuring"].includes(status),
10715:     execution_blocked: true,
10716:   }));
10717: 
10718:   const preview = {
10719:     schema_version: "aion.goal_loop_ab_test_lifecycle_preview.v1",
10720:     status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",
10721:     goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10722:     lifecycle_statuses: AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES,
10723:     lifecycle_steps: lifecycleSteps,
10724:     ab_test_count: nodes.length,
10725:     ab_test_nodes: nodes,
10726:     boardroom_ab_summary: {
10727:       schema_version: "aion.goal_loop_boardroom_ab_summary.v1",
10728:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10729:       status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",
10730:       proposal_count: nodes.length,
10731:       required_board_review: nodes.length > 0,
10732:       summary: nodes.length
10733:         ? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.`
10734:         : "No A/B test proposals are ready yet.",
10735:       preview_only: true,
10736:     },
10737:     graph_ab_test_patch_preview: {
10738:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10739:       ab_test_node_additions: nodes.map((node) => ({
10740:         node_id: node.node_id,
10741:         node_type: "ab_test",
10742:         department: node.department,
10743:         source_evaluation_id: node.source_evaluation_id,
10744:         lifecycle_status: node.lifecycle_status,
10745:         approval_state: node.approval_state,
10746:         writeback_preview: true,
10747:       })),
10748:       preview_only: true,
10749:       graph_mutation_required: false,
10750:     },
10751:     preview_only: true,
10752:     approval_required: true,
10753:     campaign_launch_required: false,
10754:     connector_call_required: false,
10755:     execution_blocked: true,
10756:     persistence_required: false,
10757:     external_side_effects: false,
10758:     message_sent: false,
10759:     booking_created: false,
10760:     payment_created: false,
10761:     creates_second_canvas: false,
10762:     creates_second_pilot: false,
10763:   };
10764: 
10765:   if (typeof window !== "undefined") {
10766:     window.__aionGoalLoopAbTestLifecyclePreview = preview;
10767:   }
10768: 
10769:   return preview;
10770: }
10771: 
10772: 
10773: /* AION GOAL LOOP CANVAS PHASE F2: Generate A/B Test from Evaluation */
10774: function buildAionGoalLoopAbTestProposalFromEvaluation(evaluation = {}, options = {}) {
10775:   const safeEvaluation =
10776:     evaluation && typeof evaluation === "object" && !Array.isArray(evaluation)
10777:       ? evaluation
10778:       : {};
10779: 
10780:   const department = normaliseAionDepartmentPilotKey(
10781:     options.department ||
10782:     safeEvaluation.department ||
10783:     "marketing"
10784:   );
10785: 
10786:   const now = new Date().toISOString();
10787:   const evaluationId = String(safeEvaluation.evaluation_id || options.evaluation_id || "evaluation_preview");
10788:   const goalLoopId = String(options.goal_loop_id || safeEvaluation.goal_loop_id || "not_staged");
10789:   const goalId = String(options.goal_id || safeEvaluation.goal_id || "goal_not_staged");
10790:   const metricId = String(options.metric_id || safeEvaluation.metric_id || "");
10791:   const recommendation = String(
10792:     options.recommendation ||
10793:     safeEvaluation.recommendation ||
10794:     "Test a controlled improvement before scaling."
10795:   );
10796: 
10797:   const variantA = {
10798:     id: "variant_a",
10799:     label: String(options.variant_a_label || "Current approach"),
10800:     description: String(
10801:       options.variant_a_description ||
10802:       "Keep the current department loop unchanged as the control."
10803:     ),
10804:     source: "baseline",
10805:     preview_only: true,
10806:   };
10807: 
10808:   const variantB = {
10809:     id: "variant_b",
10810:     label: String(options.variant_b_label || "Recommended improvement"),
10811:     description: String(
10812:       options.variant_b_description ||
10813:       recommendation ||
```

### Around line 10729: `status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",`

```js
10684:       generated_at: now,
10685:       source_evaluation_id: String(sourceEvaluation.evaluation_id || ""),
10686:       department,
10687:     },
10688:   };
10689: }
10690: 
10691: function buildAionGoalLoopAbTestLifecyclePreview(options = {}) {
10692:   const evaluationPreview =
10693:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10694:       ? options.evaluation_preview
10695:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10696:         ? buildAionGoalLoopEvaluationPreview()
10697:         : { evaluations: [], goal_loop_id: "not_staged" };
10698: 
10699:   const evaluations = Array.isArray(evaluationPreview.evaluations) ? evaluationPreview.evaluations : [];
10700:   const abCandidates = evaluations.filter((evaluation) =>
10701:     evaluation.next_action === "propose_ab_test" ||
10702:     evaluation.status === "off_track"
10703:   );
10704: 
10705:   const nodes = (abCandidates.length ? abCandidates : evaluations.slice(0, 1)).map((evaluation) =>
10706:     buildAionGoalLoopAbTestNode({ evaluation, evaluation_preview: evaluationPreview })
10707:   );
10708: 
10709:   const lifecycleSteps = AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES.map((status, index) => ({
10710:     step_index: index + 1,
10711:     status,
10712:     label: status.replace(/_/g, " "),
10713:     preview_only: true,
10714:     approval_required: ["approved", "running", "measuring"].includes(status),
10715:     execution_blocked: true,
10716:   }));
10717: 
10718:   const preview = {
10719:     schema_version: "aion.goal_loop_ab_test_lifecycle_preview.v1",
10720:     status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",
10721:     goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10722:     lifecycle_statuses: AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES,
10723:     lifecycle_steps: lifecycleSteps,
10724:     ab_test_count: nodes.length,
10725:     ab_test_nodes: nodes,
10726:     boardroom_ab_summary: {
10727:       schema_version: "aion.goal_loop_boardroom_ab_summary.v1",
10728:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10729:       status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",
10730:       proposal_count: nodes.length,
10731:       required_board_review: nodes.length > 0,
10732:       summary: nodes.length
10733:         ? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.`
10734:         : "No A/B test proposals are ready yet.",
10735:       preview_only: true,
10736:     },
10737:     graph_ab_test_patch_preview: {
10738:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10739:       ab_test_node_additions: nodes.map((node) => ({
10740:         node_id: node.node_id,
10741:         node_type: "ab_test",
10742:         department: node.department,
10743:         source_evaluation_id: node.source_evaluation_id,
10744:         lifecycle_status: node.lifecycle_status,
10745:         approval_state: node.approval_state,
10746:         writeback_preview: true,
10747:       })),
10748:       preview_only: true,
10749:       graph_mutation_required: false,
10750:     },
10751:     preview_only: true,
10752:     approval_required: true,
10753:     campaign_launch_required: false,
10754:     connector_call_required: false,
10755:     execution_blocked: true,
10756:     persistence_required: false,
10757:     external_side_effects: false,
10758:     message_sent: false,
10759:     booking_created: false,
10760:     payment_created: false,
10761:     creates_second_canvas: false,
10762:     creates_second_pilot: false,
10763:   };
10764: 
10765:   if (typeof window !== "undefined") {
10766:     window.__aionGoalLoopAbTestLifecyclePreview = preview;
10767:   }
10768: 
10769:   return preview;
10770: }
10771: 
10772: 
10773: /* AION GOAL LOOP CANVAS PHASE F2: Generate A/B Test from Evaluation */
10774: function buildAionGoalLoopAbTestProposalFromEvaluation(evaluation = {}, options = {}) {
10775:   const safeEvaluation =
10776:     evaluation && typeof evaluation === "object" && !Array.isArray(evaluation)
10777:       ? evaluation
10778:       : {};
10779: 
10780:   const department = normaliseAionDepartmentPilotKey(
10781:     options.department ||
10782:     safeEvaluation.department ||
10783:     "marketing"
10784:   );
10785: 
10786:   const now = new Date().toISOString();
10787:   const evaluationId = String(safeEvaluation.evaluation_id || options.evaluation_id || "evaluation_preview");
10788:   const goalLoopId = String(options.goal_loop_id || safeEvaluation.goal_loop_id || "not_staged");
10789:   const goalId = String(options.goal_id || safeEvaluation.goal_id || "goal_not_staged");
10790:   const metricId = String(options.metric_id || safeEvaluation.metric_id || "");
10791:   const recommendation = String(
10792:     options.recommendation ||
10793:     safeEvaluation.recommendation ||
10794:     "Test a controlled improvement before scaling."
10795:   );
10796: 
10797:   const variantA = {
10798:     id: "variant_a",
10799:     label: String(options.variant_a_label || "Current approach"),
10800:     description: String(
10801:       options.variant_a_description ||
10802:       "Keep the current department loop unchanged as the control."
10803:     ),
10804:     source: "baseline",
10805:     preview_only: true,
10806:   };
10807: 
10808:   const variantB = {
10809:     id: "variant_b",
10810:     label: String(options.variant_b_label || "Recommended improvement"),
10811:     description: String(
10812:       options.variant_b_description ||
10813:       recommendation ||
10814:       "Apply the recommended improvement as the challenger variant."
10815:     ),
10816:     source: "evaluation_recommendation",
10817:     preview_only: true,
10818:   };
```

### Around line 10730: `proposal_count: nodes.length,`

```js
10685:       source_evaluation_id: String(sourceEvaluation.evaluation_id || ""),
10686:       department,
10687:     },
10688:   };
10689: }
10690: 
10691: function buildAionGoalLoopAbTestLifecyclePreview(options = {}) {
10692:   const evaluationPreview =
10693:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10694:       ? options.evaluation_preview
10695:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10696:         ? buildAionGoalLoopEvaluationPreview()
10697:         : { evaluations: [], goal_loop_id: "not_staged" };
10698: 
10699:   const evaluations = Array.isArray(evaluationPreview.evaluations) ? evaluationPreview.evaluations : [];
10700:   const abCandidates = evaluations.filter((evaluation) =>
10701:     evaluation.next_action === "propose_ab_test" ||
10702:     evaluation.status === "off_track"
10703:   );
10704: 
10705:   const nodes = (abCandidates.length ? abCandidates : evaluations.slice(0, 1)).map((evaluation) =>
10706:     buildAionGoalLoopAbTestNode({ evaluation, evaluation_preview: evaluationPreview })
10707:   );
10708: 
10709:   const lifecycleSteps = AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES.map((status, index) => ({
10710:     step_index: index + 1,
10711:     status,
10712:     label: status.replace(/_/g, " "),
10713:     preview_only: true,
10714:     approval_required: ["approved", "running", "measuring"].includes(status),
10715:     execution_blocked: true,
10716:   }));
10717: 
10718:   const preview = {
10719:     schema_version: "aion.goal_loop_ab_test_lifecycle_preview.v1",
10720:     status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",
10721:     goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10722:     lifecycle_statuses: AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES,
10723:     lifecycle_steps: lifecycleSteps,
10724:     ab_test_count: nodes.length,
10725:     ab_test_nodes: nodes,
10726:     boardroom_ab_summary: {
10727:       schema_version: "aion.goal_loop_boardroom_ab_summary.v1",
10728:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10729:       status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",
10730:       proposal_count: nodes.length,
10731:       required_board_review: nodes.length > 0,
10732:       summary: nodes.length
10733:         ? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.`
10734:         : "No A/B test proposals are ready yet.",
10735:       preview_only: true,
10736:     },
10737:     graph_ab_test_patch_preview: {
10738:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10739:       ab_test_node_additions: nodes.map((node) => ({
10740:         node_id: node.node_id,
10741:         node_type: "ab_test",
10742:         department: node.department,
10743:         source_evaluation_id: node.source_evaluation_id,
10744:         lifecycle_status: node.lifecycle_status,
10745:         approval_state: node.approval_state,
10746:         writeback_preview: true,
10747:       })),
10748:       preview_only: true,
10749:       graph_mutation_required: false,
10750:     },
10751:     preview_only: true,
10752:     approval_required: true,
10753:     campaign_launch_required: false,
10754:     connector_call_required: false,
10755:     execution_blocked: true,
10756:     persistence_required: false,
10757:     external_side_effects: false,
10758:     message_sent: false,
10759:     booking_created: false,
10760:     payment_created: false,
10761:     creates_second_canvas: false,
10762:     creates_second_pilot: false,
10763:   };
10764: 
10765:   if (typeof window !== "undefined") {
10766:     window.__aionGoalLoopAbTestLifecyclePreview = preview;
10767:   }
10768: 
10769:   return preview;
10770: }
10771: 
10772: 
10773: /* AION GOAL LOOP CANVAS PHASE F2: Generate A/B Test from Evaluation */
10774: function buildAionGoalLoopAbTestProposalFromEvaluation(evaluation = {}, options = {}) {
10775:   const safeEvaluation =
10776:     evaluation && typeof evaluation === "object" && !Array.isArray(evaluation)
10777:       ? evaluation
10778:       : {};
10779: 
10780:   const department = normaliseAionDepartmentPilotKey(
10781:     options.department ||
10782:     safeEvaluation.department ||
10783:     "marketing"
10784:   );
10785: 
10786:   const now = new Date().toISOString();
10787:   const evaluationId = String(safeEvaluation.evaluation_id || options.evaluation_id || "evaluation_preview");
10788:   const goalLoopId = String(options.goal_loop_id || safeEvaluation.goal_loop_id || "not_staged");
10789:   const goalId = String(options.goal_id || safeEvaluation.goal_id || "goal_not_staged");
10790:   const metricId = String(options.metric_id || safeEvaluation.metric_id || "");
10791:   const recommendation = String(
10792:     options.recommendation ||
10793:     safeEvaluation.recommendation ||
10794:     "Test a controlled improvement before scaling."
10795:   );
10796: 
10797:   const variantA = {
10798:     id: "variant_a",
10799:     label: String(options.variant_a_label || "Current approach"),
10800:     description: String(
10801:       options.variant_a_description ||
10802:       "Keep the current department loop unchanged as the control."
10803:     ),
10804:     source: "baseline",
10805:     preview_only: true,
10806:   };
10807: 
10808:   const variantB = {
10809:     id: "variant_b",
10810:     label: String(options.variant_b_label || "Recommended improvement"),
10811:     description: String(
10812:       options.variant_b_description ||
10813:       recommendation ||
10814:       "Apply the recommended improvement as the challenger variant."
10815:     ),
10816:     source: "evaluation_recommendation",
10817:     preview_only: true,
10818:   };
10819: 
```

### Around line 10731: `required_board_review: nodes.length > 0,`

```js
10686:       department,
10687:     },
10688:   };
10689: }
10690: 
10691: function buildAionGoalLoopAbTestLifecyclePreview(options = {}) {
10692:   const evaluationPreview =
10693:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10694:       ? options.evaluation_preview
10695:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10696:         ? buildAionGoalLoopEvaluationPreview()
10697:         : { evaluations: [], goal_loop_id: "not_staged" };
10698: 
10699:   const evaluations = Array.isArray(evaluationPreview.evaluations) ? evaluationPreview.evaluations : [];
10700:   const abCandidates = evaluations.filter((evaluation) =>
10701:     evaluation.next_action === "propose_ab_test" ||
10702:     evaluation.status === "off_track"
10703:   );
10704: 
10705:   const nodes = (abCandidates.length ? abCandidates : evaluations.slice(0, 1)).map((evaluation) =>
10706:     buildAionGoalLoopAbTestNode({ evaluation, evaluation_preview: evaluationPreview })
10707:   );
10708: 
10709:   const lifecycleSteps = AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES.map((status, index) => ({
10710:     step_index: index + 1,
10711:     status,
10712:     label: status.replace(/_/g, " "),
10713:     preview_only: true,
10714:     approval_required: ["approved", "running", "measuring"].includes(status),
10715:     execution_blocked: true,
10716:   }));
10717: 
10718:   const preview = {
10719:     schema_version: "aion.goal_loop_ab_test_lifecycle_preview.v1",
10720:     status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",
10721:     goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10722:     lifecycle_statuses: AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES,
10723:     lifecycle_steps: lifecycleSteps,
10724:     ab_test_count: nodes.length,
10725:     ab_test_nodes: nodes,
10726:     boardroom_ab_summary: {
10727:       schema_version: "aion.goal_loop_boardroom_ab_summary.v1",
10728:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10729:       status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",
10730:       proposal_count: nodes.length,
10731:       required_board_review: nodes.length > 0,
10732:       summary: nodes.length
10733:         ? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.`
10734:         : "No A/B test proposals are ready yet.",
10735:       preview_only: true,
10736:     },
10737:     graph_ab_test_patch_preview: {
10738:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10739:       ab_test_node_additions: nodes.map((node) => ({
10740:         node_id: node.node_id,
10741:         node_type: "ab_test",
10742:         department: node.department,
10743:         source_evaluation_id: node.source_evaluation_id,
10744:         lifecycle_status: node.lifecycle_status,
10745:         approval_state: node.approval_state,
10746:         writeback_preview: true,
10747:       })),
10748:       preview_only: true,
10749:       graph_mutation_required: false,
10750:     },
10751:     preview_only: true,
10752:     approval_required: true,
10753:     campaign_launch_required: false,
10754:     connector_call_required: false,
10755:     execution_blocked: true,
10756:     persistence_required: false,
10757:     external_side_effects: false,
10758:     message_sent: false,
10759:     booking_created: false,
10760:     payment_created: false,
10761:     creates_second_canvas: false,
10762:     creates_second_pilot: false,
10763:   };
10764: 
10765:   if (typeof window !== "undefined") {
10766:     window.__aionGoalLoopAbTestLifecyclePreview = preview;
10767:   }
10768: 
10769:   return preview;
10770: }
10771: 
10772: 
10773: /* AION GOAL LOOP CANVAS PHASE F2: Generate A/B Test from Evaluation */
10774: function buildAionGoalLoopAbTestProposalFromEvaluation(evaluation = {}, options = {}) {
10775:   const safeEvaluation =
10776:     evaluation && typeof evaluation === "object" && !Array.isArray(evaluation)
10777:       ? evaluation
10778:       : {};
10779: 
10780:   const department = normaliseAionDepartmentPilotKey(
10781:     options.department ||
10782:     safeEvaluation.department ||
10783:     "marketing"
10784:   );
10785: 
10786:   const now = new Date().toISOString();
10787:   const evaluationId = String(safeEvaluation.evaluation_id || options.evaluation_id || "evaluation_preview");
10788:   const goalLoopId = String(options.goal_loop_id || safeEvaluation.goal_loop_id || "not_staged");
10789:   const goalId = String(options.goal_id || safeEvaluation.goal_id || "goal_not_staged");
10790:   const metricId = String(options.metric_id || safeEvaluation.metric_id || "");
10791:   const recommendation = String(
10792:     options.recommendation ||
10793:     safeEvaluation.recommendation ||
10794:     "Test a controlled improvement before scaling."
10795:   );
10796: 
10797:   const variantA = {
10798:     id: "variant_a",
10799:     label: String(options.variant_a_label || "Current approach"),
10800:     description: String(
10801:       options.variant_a_description ||
10802:       "Keep the current department loop unchanged as the control."
10803:     ),
10804:     source: "baseline",
10805:     preview_only: true,
10806:   };
10807: 
10808:   const variantB = {
10809:     id: "variant_b",
10810:     label: String(options.variant_b_label || "Recommended improvement"),
10811:     description: String(
10812:       options.variant_b_description ||
10813:       recommendation ||
10814:       "Apply the recommended improvement as the challenger variant."
10815:     ),
10816:     source: "evaluation_recommendation",
10817:     preview_only: true,
10818:   };
10819: 
10820:   return {
```

### Around line 10732: `summary: nodes.length`

```js
10687:     },
10688:   };
10689: }
10690: 
10691: function buildAionGoalLoopAbTestLifecyclePreview(options = {}) {
10692:   const evaluationPreview =
10693:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10694:       ? options.evaluation_preview
10695:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10696:         ? buildAionGoalLoopEvaluationPreview()
10697:         : { evaluations: [], goal_loop_id: "not_staged" };
10698: 
10699:   const evaluations = Array.isArray(evaluationPreview.evaluations) ? evaluationPreview.evaluations : [];
10700:   const abCandidates = evaluations.filter((evaluation) =>
10701:     evaluation.next_action === "propose_ab_test" ||
10702:     evaluation.status === "off_track"
10703:   );
10704: 
10705:   const nodes = (abCandidates.length ? abCandidates : evaluations.slice(0, 1)).map((evaluation) =>
10706:     buildAionGoalLoopAbTestNode({ evaluation, evaluation_preview: evaluationPreview })
10707:   );
10708: 
10709:   const lifecycleSteps = AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES.map((status, index) => ({
10710:     step_index: index + 1,
10711:     status,
10712:     label: status.replace(/_/g, " "),
10713:     preview_only: true,
10714:     approval_required: ["approved", "running", "measuring"].includes(status),
10715:     execution_blocked: true,
10716:   }));
10717: 
10718:   const preview = {
10719:     schema_version: "aion.goal_loop_ab_test_lifecycle_preview.v1",
10720:     status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",
10721:     goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10722:     lifecycle_statuses: AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES,
10723:     lifecycle_steps: lifecycleSteps,
10724:     ab_test_count: nodes.length,
10725:     ab_test_nodes: nodes,
10726:     boardroom_ab_summary: {
10727:       schema_version: "aion.goal_loop_boardroom_ab_summary.v1",
10728:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10729:       status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",
10730:       proposal_count: nodes.length,
10731:       required_board_review: nodes.length > 0,
10732:       summary: nodes.length
10733:         ? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.`
10734:         : "No A/B test proposals are ready yet.",
10735:       preview_only: true,
10736:     },
10737:     graph_ab_test_patch_preview: {
10738:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10739:       ab_test_node_additions: nodes.map((node) => ({
10740:         node_id: node.node_id,
10741:         node_type: "ab_test",
10742:         department: node.department,
10743:         source_evaluation_id: node.source_evaluation_id,
10744:         lifecycle_status: node.lifecycle_status,
10745:         approval_state: node.approval_state,
10746:         writeback_preview: true,
10747:       })),
10748:       preview_only: true,
10749:       graph_mutation_required: false,
10750:     },
10751:     preview_only: true,
10752:     approval_required: true,
10753:     campaign_launch_required: false,
10754:     connector_call_required: false,
10755:     execution_blocked: true,
10756:     persistence_required: false,
10757:     external_side_effects: false,
10758:     message_sent: false,
10759:     booking_created: false,
10760:     payment_created: false,
10761:     creates_second_canvas: false,
10762:     creates_second_pilot: false,
10763:   };
10764: 
10765:   if (typeof window !== "undefined") {
10766:     window.__aionGoalLoopAbTestLifecyclePreview = preview;
10767:   }
10768: 
10769:   return preview;
10770: }
10771: 
10772: 
10773: /* AION GOAL LOOP CANVAS PHASE F2: Generate A/B Test from Evaluation */
10774: function buildAionGoalLoopAbTestProposalFromEvaluation(evaluation = {}, options = {}) {
10775:   const safeEvaluation =
10776:     evaluation && typeof evaluation === "object" && !Array.isArray(evaluation)
10777:       ? evaluation
10778:       : {};
10779: 
10780:   const department = normaliseAionDepartmentPilotKey(
10781:     options.department ||
10782:     safeEvaluation.department ||
10783:     "marketing"
10784:   );
10785: 
10786:   const now = new Date().toISOString();
10787:   const evaluationId = String(safeEvaluation.evaluation_id || options.evaluation_id || "evaluation_preview");
10788:   const goalLoopId = String(options.goal_loop_id || safeEvaluation.goal_loop_id || "not_staged");
10789:   const goalId = String(options.goal_id || safeEvaluation.goal_id || "goal_not_staged");
10790:   const metricId = String(options.metric_id || safeEvaluation.metric_id || "");
10791:   const recommendation = String(
10792:     options.recommendation ||
10793:     safeEvaluation.recommendation ||
10794:     "Test a controlled improvement before scaling."
10795:   );
10796: 
10797:   const variantA = {
10798:     id: "variant_a",
10799:     label: String(options.variant_a_label || "Current approach"),
10800:     description: String(
10801:       options.variant_a_description ||
10802:       "Keep the current department loop unchanged as the control."
10803:     ),
10804:     source: "baseline",
10805:     preview_only: true,
10806:   };
10807: 
10808:   const variantB = {
10809:     id: "variant_b",
10810:     label: String(options.variant_b_label || "Recommended improvement"),
10811:     description: String(
10812:       options.variant_b_description ||
10813:       recommendation ||
10814:       "Apply the recommended improvement as the challenger variant."
10815:     ),
10816:     source: "evaluation_recommendation",
10817:     preview_only: true,
10818:   };
10819: 
10820:   return {
10821:     schema_version: "aion.goal_loop_ab_test_generated_from_evaluation.v1",
```

### Around line 10733: `? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.``

```js
10688:   };
10689: }
10690: 
10691: function buildAionGoalLoopAbTestLifecyclePreview(options = {}) {
10692:   const evaluationPreview =
10693:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10694:       ? options.evaluation_preview
10695:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10696:         ? buildAionGoalLoopEvaluationPreview()
10697:         : { evaluations: [], goal_loop_id: "not_staged" };
10698: 
10699:   const evaluations = Array.isArray(evaluationPreview.evaluations) ? evaluationPreview.evaluations : [];
10700:   const abCandidates = evaluations.filter((evaluation) =>
10701:     evaluation.next_action === "propose_ab_test" ||
10702:     evaluation.status === "off_track"
10703:   );
10704: 
10705:   const nodes = (abCandidates.length ? abCandidates : evaluations.slice(0, 1)).map((evaluation) =>
10706:     buildAionGoalLoopAbTestNode({ evaluation, evaluation_preview: evaluationPreview })
10707:   );
10708: 
10709:   const lifecycleSteps = AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES.map((status, index) => ({
10710:     step_index: index + 1,
10711:     status,
10712:     label: status.replace(/_/g, " "),
10713:     preview_only: true,
10714:     approval_required: ["approved", "running", "measuring"].includes(status),
10715:     execution_blocked: true,
10716:   }));
10717: 
10718:   const preview = {
10719:     schema_version: "aion.goal_loop_ab_test_lifecycle_preview.v1",
10720:     status: nodes.length ? "ab_test_lifecycle_preview_ready" : "no_ab_test_candidates",
10721:     goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10722:     lifecycle_statuses: AION_GOAL_LOOP_AB_TEST_LIFECYCLE_STATUSES,
10723:     lifecycle_steps: lifecycleSteps,
10724:     ab_test_count: nodes.length,
10725:     ab_test_nodes: nodes,
10726:     boardroom_ab_summary: {
10727:       schema_version: "aion.goal_loop_boardroom_ab_summary.v1",
10728:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10729:       status: nodes.length ? "ab_test_proposals_ready_for_boardroom" : "no_ab_test_proposals",
10730:       proposal_count: nodes.length,
10731:       required_board_review: nodes.length > 0,
10732:       summary: nodes.length
10733:         ? `${nodes.length} A/B test proposal(s) are ready for Boardroom review. No test has been launched.`
10734:         : "No A/B test proposals are ready yet.",
10735:       preview_only: true,
10736:     },
10737:     graph_ab_test_patch_preview: {
10738:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
10739:       ab_test_node_additions: nodes.map((node) => ({
10740:         node_id: node.node_id,
10741:         node_type: "ab_test",
10742:         department: node.department,
10743:         source_evaluation_id: node.source_evaluation_id,
10744:         lifecycle_status: node.lifecycle_status,
10745:         approval_state: node.approval_state,
10746:         writeback_preview: true,
10747:       })),
10748:       preview_only: true,
10749:       graph_mutation_required: false,
10750:     },
10751:     preview_only: true,
10752:     approval_required: true,
10753:     campaign_launch_required: false,
10754:     connector_call_required: false,
10755:     execution_blocked: true,
10756:     persistence_required: false,
10757:     external_side_effects: false,
10758:     message_sent: false,
10759:     booking_created: false,
10760:     payment_created: false,
10761:     creates_second_canvas: false,
10762:     creates_second_pilot: false,
10763:   };
10764: 
10765:   if (typeof window !== "undefined") {
10766:     window.__aionGoalLoopAbTestLifecyclePreview = preview;
10767:   }
10768: 
10769:   return preview;
10770: }
10771: 
10772: 
10773: /* AION GOAL LOOP CANVAS PHASE F2: Generate A/B Test from Evaluation */
10774: function buildAionGoalLoopAbTestProposalFromEvaluation(evaluation = {}, options = {}) {
10775:   const safeEvaluation =
10776:     evaluation && typeof evaluation === "object" && !Array.isArray(evaluation)
10777:       ? evaluation
10778:       : {};
10779: 
10780:   const department = normaliseAionDepartmentPilotKey(
10781:     options.department ||
10782:     safeEvaluation.department ||
10783:     "marketing"
10784:   );
10785: 
10786:   const now = new Date().toISOString();
10787:   const evaluationId = String(safeEvaluation.evaluation_id || options.evaluation_id || "evaluation_preview");
10788:   const goalLoopId = String(options.goal_loop_id || safeEvaluation.goal_loop_id || "not_staged");
10789:   const goalId = String(options.goal_id || safeEvaluation.goal_id || "goal_not_staged");
10790:   const metricId = String(options.metric_id || safeEvaluation.metric_id || "");
10791:   const recommendation = String(
10792:     options.recommendation ||
10793:     safeEvaluation.recommendation ||
10794:     "Test a controlled improvement before scaling."
10795:   );
10796: 
10797:   const variantA = {
10798:     id: "variant_a",
10799:     label: String(options.variant_a_label || "Current approach"),
10800:     description: String(
10801:       options.variant_a_description ||
10802:       "Keep the current department loop unchanged as the control."
10803:     ),
10804:     source: "baseline",
10805:     preview_only: true,
10806:   };
10807: 
10808:   const variantB = {
10809:     id: "variant_b",
10810:     label: String(options.variant_b_label || "Recommended improvement"),
10811:     description: String(
10812:       options.variant_b_description ||
10813:       recommendation ||
10814:       "Apply the recommended improvement as the challenger variant."
10815:     ),
10816:     source: "evaluation_recommendation",
10817:     preview_only: true,
10818:   };
10819: 
10820:   return {
10821:     schema_version: "aion.goal_loop_ab_test_generated_from_evaluation.v1",
10822:     proposal_id: String(options.proposal_id || `${evaluationId}_generated_ab_test_preview`),
```

### Around line 11541: `feedback_count: nodes.length,`

```js
11496:     pattern_id: "marketing_finance_mismatch",
11497:     departments: ["marketing", "finance"],
11498:     finding: "Marketing activity may not align with Finance efficiency targets.",
11499:     severity: "medium",
11500:     recommendation: "Review cost per result before increasing budget.",
11501:     required_action: "Request Finance approval before scaling spend.",
11502:   },
11503:   {
11504:     pattern_id: "support_sales_objection_mismatch",
11505:     departments: ["support", "sales"],
11506:     finding: "Support objections may be blocking Sales conversion.",
11507:     severity: "medium",
11508:     recommendation: "Feed Support objections into Sales scripts and offer handling.",
11509:     required_action: "Create a Sales objection handling improvement loop.",
11510:   },
11511:   {
11512:     pattern_id: "operations_support_review_mismatch",
11513:     departments: ["operations", "support"],
11514:     finding: "Operations delivery issues may be creating Support load.",
11515:     severity: "medium",
11516:     recommendation: "Review delivery quality before adding more customer demand.",
11517:     required_action: "Create an Operations quality improvement loop.",
11518:   },
11519: ];
11520: 
11521: function getAionGoalLoopDepartmentSignalFromFeedback(feedbackNodes = [], department = "") {
11522:   const key = normaliseAionDepartmentPilotKey(department);
11523:   const nodes = Array.isArray(feedbackNodes)
11524:     ? feedbackNodes.filter((node) => normaliseAionDepartmentPilotKey(node.department || "") === key)
11525:     : [];
11526: 
11527:   const needsAttention = nodes.some((node) =>
11528:     ["needs_attention", "blocked", "unknown", "off_track"].includes(String(node.department_status || ""))
11529:   );
11530: 
11531:   const riskCount = nodes.reduce((total, node) =>
11532:     total + (Array.isArray(node.risks) ? node.risks.length : 0), 0
11533:   );
11534: 
11535:   const metricCount = nodes.reduce((total, node) =>
11536:     total + (Array.isArray(node.metrics) ? node.metrics.length : 0), 0
11537:   );
11538: 
11539:   return {
11540:     department: key,
11541:     feedback_count: nodes.length,
11542:     metric_count: metricCount,
11543:     risk_count: riskCount,
11544:     needs_attention: needsAttention,
11545:     status: needsAttention || riskCount > 0 ? "needs_attention" : "stable",
11546:     preview_only: true,
11547:   };
11548: }
11549: 
11550: function buildAionGoalLoopCrossFunctionAnalysis(options = {}) {
11551:   const feedbackPreview =
11552:     options.feedback_preview && typeof options.feedback_preview === "object"
11553:       ? options.feedback_preview
11554:       : typeof previewAionGoalLoopFeedbackToBoard === "function"
11555:         ? previewAionGoalLoopFeedbackToBoard()
11556:         : { feedback_nodes: [], goal_loop_id: "not_staged" };
11557: 
11558:   const decisionPreview =
11559:     options.decision_preview && typeof options.decision_preview === "object"
11560:       ? options.decision_preview
11561:       : typeof previewAionGoalLoopBoardroomFeedbackDecision === "function"
11562:         ? previewAionGoalLoopBoardroomFeedbackDecision({ feedback_preview: feedbackPreview })
11563:         : { decisions: [] };
11564: 
11565:   const feedbackNodes = Array.isArray(feedbackPreview.feedback_nodes)
11566:     ? feedbackPreview.feedback_nodes
11567:     : [];
11568: 
11569:   const decisions = Array.isArray(decisionPreview.decisions)
11570:     ? decisionPreview.decisions
11571:     : [];
11572: 
11573:   const now = new Date().toISOString();
11574:   const goalLoopId = String(feedbackPreview.goal_loop_id || decisionPreview.goal_loop_id || "not_staged");
11575: 
11576:   const departmentSignals = ["marketing", "sales", "finance", "operations", "support"].map((department) =>
11577:     getAionGoalLoopDepartmentSignalFromFeedback(feedbackNodes, department)
11578:   );
11579: 
11580:   const findings = AION_GOAL_LOOP_CROSS_FUNCTION_PATTERNS.map((pattern) => {
11581:     const signals = pattern.departments.map((department) =>
11582:       departmentSignals.find((signal) => signal.department === department) ||
11583:       getAionGoalLoopDepartmentSignalFromFeedback(feedbackNodes, department)
11584:     );
11585: 
11586:     const relatedDecisions = decisions.filter((decision) =>
11587:       pattern.departments.includes(normaliseAionDepartmentPilotKey(decision.department || ""))
11588:     );
11589: 
11590:     const triggered =
11591:       signals.some((signal) => signal.needs_attention || signal.risk_count > 0) ||
11592:       relatedDecisions.some((decision) => ["adjust", "request_more_data"].includes(decision.decision));
11593: 
11594:     const severity = triggered
11595:       ? pattern.severity
11596:       : "low";
11597: 
11598:     return {
11599:       schema_version: "aion.goal_loop_cross_function_finding.v1",
11600:       analysis_id: `${goalLoopId}_${pattern.pattern_id}_preview`,
11601:       pattern_id: pattern.pattern_id,
11602:       goal_loop_id: goalLoopId,
11603:       finding: pattern.finding,
11604:       departments: pattern.departments,
11605:       severity,
11606:       triggered,
11607:       recommendation: pattern.recommendation,
11608:       required_action: pattern.required_action,
11609:       department_signals: signals,
11610:       related_decision_ids: relatedDecisions.map((decision) => String(decision.decision_id || "")),
11611:       boardroom_review_item: {
11612:         schema_version: "aion.goal_loop_boardroom_review_item.v1",
11613:         review_id: `${goalLoopId}_${pattern.pattern_id}_boardroom_review`,
11614:         review_type: "cross_function_analysis",
11615:         status: triggered ? "needs_board_decision" : "monitor",
11616:         title: `Cross-function review: ${pattern.departments.map((department) => runtimeShared.getDepartmentLabel(department)).join(" / ")}`,
11617:         summary: pattern.finding,
11618:         required_decision: pattern.required_action,
11619:         goal_loop_id: goalLoopId,
11620:         departments: pattern.departments,
11621:         severity,
11622:         preview_only: true,
11623:       },
11624:       graph_patch_preview: {
11625:         goal_loop_id: goalLoopId,
11626:         add_or_update_node: {
11627:           node_id: `${goalLoopId}_${pattern.pattern_id}_cross_analysis_node_preview`,
11628:           node_type: "cross_function_analysis",
11629:           pattern_id: pattern.pattern_id,
11630:           departments: pattern.departments,
```

### Around line 12540: `conflict_nodes: Array.isArray(conflictPreview.conflict_nodes) ? conflictPreview.conflict_nodes.length : 0,`

```js
12495:       storage_concept: "aion.goalLoopRevisionHistory.v1",
12496:       container_path: `${businessContainerId}/aion/goal-loops/${goalLoopId}/revisions`,
12497:       description: "Audit trail and before/after revision history for later K2.",
12498:     },
12499:   ].map((item, index) => ({
12500:     ...item,
12501:     artifact_id: `${goalLoopId}_${item.artifact_type}_${index + 1}_persistence_plan`,
12502:     business_container_id: businessContainerId,
12503:     goal_loop_id: goalLoopId,
12504:     write_required_now: false,
12505:     persistence_preview_only: true,
12506:     preview_only: true,
12507:   }));
12508: 
12509:   const departmentPersistencePlan = departmentKeys.map((department) => ({
12510:     schema_version: "aion.department_goal_loop_persistence_plan.v1",
12511:     department,
12512:     business_container_id: businessContainerId,
12513:     goal_loop_id: goalLoopId,
12514:     container_path: `${businessContainerId}/aion/goal-loops/${goalLoopId}/departments/${department}`,
12515:     stores: [
12516:       "department_canvas",
12517:       "department_tasks",
12518:       "department_metrics",
12519:       "department_results",
12520:       "department_feedback",
12521:     ],
12522:     write_required_now: false,
12523:     persistence_preview_only: true,
12524:     preview_only: true,
12525:   }));
12526: 
12527:   return {
12528:     schema_version: "aion.goal_loop_business_container_persistence_plan.v1",
12529:     status: businessContainerId === "business_not_registered"
12530:       ? "business_container_not_registered"
12531:       : "business_container_persistence_plan_ready",
12532:     business_container_id: businessContainerId,
12533:     goal_loop_id: goalLoopId,
12534:     storage_concepts: AION_GOAL_LOOP_BUSINESS_CONTAINER_STORAGE_CONCEPTS,
12535:     artifact_count: artifactPlan.length,
12536:     artifact_plan: artifactPlan,
12537:     department_persistence_plan: departmentPersistencePlan,
12538:     source_preview_counts: {
12539:       approval_requests: Array.isArray(approvalPreview.approval_requests) ? approvalPreview.approval_requests.length : 0,
12540:       conflict_nodes: Array.isArray(conflictPreview.conflict_nodes) ? conflictPreview.conflict_nodes.length : 0,
12541:     },
12542:     registered_business_resolver_used: true,
12543:     stale_legacy_business_blocked: true,
12544:     hard_coded_business_default_allowed: false,
12545:     writes_planned_for_later_phase: true,
12546:     write_required_now: false,
12547:     persistence_preview_only: true,
12548:     actual_container_write_performed: false,
12549:     external_side_effects: false,
12550:     connector_call_required: false,
12551:     message_sent: false,
12552:     booking_created: false,
12553:     payment_created: false,
12554:     creates_second_canvas: false,
12555:     creates_second_pilot: false,
12556:     created_at_preview: now,
12557:     provenance: {
12558:       source: "goal_loop_approval_and_canvas_preview",
12559:       generated_by: "aion_goal_loop_phase_j1",
12560:       generated_at: now,
12561:       business_container_id: businessContainerId,
12562:       goal_loop_id: goalLoopId,
12563:     },
12564:   };
12565: }
12566: 
12567: function previewAionGoalLoopBusinessContainerPersistence(options = {}) {
12568:   const preview = buildAionGoalLoopBusinessContainerPersistencePlan(options);
12569: 
12570:   if (typeof window !== "undefined") {
12571:     window.__aionGoalLoopBusinessContainerPersistencePreview = preview;
12572:   }
12573: 
12574:   return preview;
12575: }
12576: 
12577: 
12578: /* AION GOAL LOOP CANVAS PHASE J2: Replay / Restore Preview */
12579: const AION_GOAL_LOOP_REPLAY_RESTORE_SECTIONS = [
12580:   "active_goal_loop",
12581:   "graph_nodes",
12582:   "graph_edges",
12583:   "department_child_canvases",
12584:   "metrics",
12585:   "evaluations",
12586:   "ab_test_proposals",
12587:   "boardroom_review_state",
12588:   "feedback_nodes",
12589:   "cross_function_findings",
12590:   "conflict_nodes",
12591:   "approval_requests",
12592:   "evidence_links",
12593: ];
12594: 
12595: function buildAionGoalLoopReplayRestorePlan(options = {}) {
12596:   const now = new Date().toISOString();
12597: 
12598:   const persistencePreview =
12599:     options.persistence_preview && typeof options.persistence_preview === "object"
12600:       ? options.persistence_preview
12601:       : typeof previewAionGoalLoopBusinessContainerPersistence === "function"
12602:         ? previewAionGoalLoopBusinessContainerPersistence()
12603:         : {
12604:             business_container_id: "business_not_registered",
12605:             goal_loop_id: "not_staged",
12606:             artifact_plan: [],
12607:             department_persistence_plan: [],
12608:           };
12609: 
12610:   const businessContainerId = getAionGoalLoopPersistenceBusinessContainerId(
12611:     options.business_container_id ||
12612:     persistencePreview.business_container_id ||
12613:     ""
12614:   );
12615: 
12616:   const goalLoopId = String(
12617:     options.goal_loop_id ||
12618:     persistencePreview.goal_loop_id ||
12619:     "not_staged"
12620:   );
12621: 
12622:   const staleLegacyBlocked =
12623:     businessContainerId === "business_not_registered" ||
12624:     (
12625:       typeof isAionLegacyDemoBusinessIdentity === "function" &&
12626:       isAionLegacyDemoBusinessIdentity(businessContainerId)
12627:     );
12628: 
12629:   const artifactPlan = Array.isArray(persistencePreview.artifact_plan)
```

### Around line 16839: `<div class="card-value" data-aion-goal-loop-ab-count="true">${escapeHtml(nodes.length)}</div>`

```js
16794:           `
16795:           : `<div class="empty-state" style="margin-top:12px;">No generated A/B test proposals are available yet.</div>`
16796:       }
16797: 
16798:       <div class="notice warning" data-aion-goal-loop-generated-ab-preview-boundary="true" style="margin-top:12px;">
16799:         Safety: F2 generates A/B test proposals from evaluation only. It does not mutate the graph,
16800:         launch campaigns, call connectors, persist data, send messages, create bookings or take payments.
16801:       </div>
16802:     </section>
16803:   `;
16804: }
16805: 
16806: if (typeof window !== "undefined") {
16807:   window.buildAionGoalLoopAbTestProposalFromEvaluation = buildAionGoalLoopAbTestProposalFromEvaluation;
16808:   window.previewAionGoalLoopGeneratedAbTestsFromEvaluation = previewAionGoalLoopGeneratedAbTestsFromEvaluation;
16809:   window.renderAionGoalLoopGeneratedAbTestPanel = renderAionGoalLoopGeneratedAbTestPanel;
16810: }
16811: /* END AION GOAL LOOP CANVAS PHASE F2 */
16812: 
16813: 
16814: function renderAionGoalLoopAbTestPanel() {
16815:   const preview = buildAionGoalLoopAbTestLifecyclePreview();
16816:   const nodes = Array.isArray(preview.ab_test_nodes) ? preview.ab_test_nodes : [];
16817:   const lifecycleSteps = Array.isArray(preview.lifecycle_steps) ? preview.lifecycle_steps : [];
16818: 
16819:   return `
16820:     <section
16821:       class="panel large-panel"
16822:       data-aion-goal-loop-ab-test-panel="true"
16823:       style="background:#ffffff; margin-top:9px;"
16824:     >
16825:       <div class="panel-title">Goal Loop A/B Test Support</div>
16826:       <div class="helper-text">
16827:         A/B test node schema and lifecycle preview for Goal Loop improvement loops.
16828:         F1 does not launch campaigns, call connectors, persist data or execute tasks.
16829:       </div>
16830: 
16831:       <div class="card-grid" style="margin-top:12px;">
16832:         <div class="card">
16833:           <div class="card-label">Goal Loop</div>
16834:           <div class="card-value" data-aion-goal-loop-ab-goal-loop-id="true">${escapeHtml(preview.goal_loop_id || "not_staged")}</div>
16835:           <div class="card-sub">${escapeHtml(preview.status || "ab_test_preview")}</div>
16836:         </div>
16837:         <div class="card">
16838:           <div class="card-label">A/B Proposals</div>
16839:           <div class="card-value" data-aion-goal-loop-ab-count="true">${escapeHtml(nodes.length)}</div>
16840:           <div class="card-sub">Boardroom review required</div>
16841:         </div>
16842:         <div class="card">
16843:           <div class="card-label">Lifecycle</div>
16844:           <div class="card-value" data-aion-goal-loop-ab-lifecycle-count="true">${escapeHtml(lifecycleSteps.length)}</div>
16845:           <div class="card-sub">proposed → complete</div>
16846:         </div>
16847:         <div class="card">
16848:           <div class="card-label">Safety</div>
16849:           <div class="card-value" data-aion-goal-loop-ab-safety="true">Preview only</div>
16850:           <div class="card-sub">No campaign launch</div>
16851:         </div>
16852:       </div>
16853: 
16854:       <div class="list-wrap" style="margin-top:12px;" data-aion-goal-loop-ab-lifecycle="true">
16855:         ${lifecycleSteps.map((step) => `
16856:           <div class="list-item" data-aion-goal-loop-ab-lifecycle-step="${escapeHtml(step.status)}">
16857:             <div class="list-item-title">${escapeHtml(step.step_index)}. ${escapeHtml(step.label)}</div>
16858:             <div class="list-item-sub">Lifecycle state preview. Execution remains blocked.</div>
16859:           </div>
16860:         `).join("")}
16861:       </div>
16862: 
16863:       ${
16864:         nodes.length
16865:           ? `
16866:             <div class="list-wrap" style="margin-top:12px;" data-aion-goal-loop-ab-nodes="true">
16867:               ${nodes.map((node) => `
16868:                 <div class="list-item" data-aion-goal-loop-ab-node="${escapeHtml(node.node_id)}">
16869:                   <div class="list-item-title">${escapeHtml(node.title)}</div>
16870:                   <div class="list-item-sub">${escapeHtml(node.hypothesis)}</div>
16871: 
16872:                   <div class="card-grid" style="margin-top:8px;">
16873:                     <div class="card">
16874:                       <div class="card-label">Variant A</div>
16875:                       <div class="card-value" data-aion-goal-loop-ab-variant-a="true">${escapeHtml(node.variant_a.label)}</div>
16876:                       <div class="card-sub">${escapeHtml(node.variant_a.description)}</div>
16877:                     </div>
16878:                     <div class="card">
16879:                       <div class="card-label">Variant B</div>
16880:                       <div class="card-value" data-aion-goal-loop-ab-variant-b="true">${escapeHtml(node.variant_b.label)}</div>
16881:                       <div class="card-sub">${escapeHtml(node.variant_b.description)}</div>
16882:                     </div>
16883:                   </div>
16884: 
16885:                   <div class="badge-row" style="margin-top:8px;">
16886:                     <span class="badge">${escapeHtml(node.lifecycle_status)}</span>
16887:                     <span class="badge">${escapeHtml(node.approval_state)}</span>
16888:                     <span class="badge">Metric ${escapeHtml(node.success_metric.name || "—")}</span>
16889:                     <span class="badge">${escapeHtml(node.test_duration)}</span>
16890:                     <span class="badge">Preview only</span>
16891:                   </div>
16892:                 </div>
16893:               `).join("")}
16894:             </div>
16895:           `
16896:           : `<div class="empty-state" style="margin-top:12px;">No A/B test proposals are available yet.</div>`
16897:       }
16898: 
16899:       <div class="notice warning" data-aion-goal-loop-ab-preview-boundary="true" style="margin-top:12px;">
16900:         Safety: F1 creates A/B test schema and lifecycle previews only. It does not launch a campaign,
16901:         call connectors, execute tasks, persist data, send messages, create bookings or take payments.
16902:       </div>
16903:     </section>
16904:   `;
16905: }
16906: 
16907: if (typeof window !== "undefined") {
16908:   window.buildAionGoalLoopAbTestNode = buildAionGoalLoopAbTestNode;
16909:   window.buildAionGoalLoopAbTestLifecyclePreview = buildAionGoalLoopAbTestLifecyclePreview;
16910:   window.renderAionGoalLoopAbTestPanel = renderAionGoalLoopAbTestPanel;
16911: }
16912: /* END AION GOAL LOOP CANVAS PHASE F1 */
16913: 
16914: 
16915: function renderAionGoalLoopEvaluationEnginePanel() {
16916:   const preview = buildAionGoalLoopEvaluationPreview();
16917:   const evaluations = Array.isArray(preview.evaluations) ? preview.evaluations : [];
16918:   const summary = preview.boardroom_evaluation_summary || {};
16919: 
16920:   return `
16921:     <section
16922:       class="panel large-panel"
16923:       data-aion-goal-loop-evaluation-engine-panel="true"
16924:       style="background:#ffffff; margin-top:9px;"
16925:     >
16926:       <div class="panel-title">Goal Loop Evaluation Engine</div>
16927:       <div class="helper-text">
16928:         Compares manual result previews against metric targets and prepares Boardroom evaluation previews.
```

### Around line 16864: `nodes.length`

```js
16819:   return `
16820:     <section
16821:       class="panel large-panel"
16822:       data-aion-goal-loop-ab-test-panel="true"
16823:       style="background:#ffffff; margin-top:9px;"
16824:     >
16825:       <div class="panel-title">Goal Loop A/B Test Support</div>
16826:       <div class="helper-text">
16827:         A/B test node schema and lifecycle preview for Goal Loop improvement loops.
16828:         F1 does not launch campaigns, call connectors, persist data or execute tasks.
16829:       </div>
16830: 
16831:       <div class="card-grid" style="margin-top:12px;">
16832:         <div class="card">
16833:           <div class="card-label">Goal Loop</div>
16834:           <div class="card-value" data-aion-goal-loop-ab-goal-loop-id="true">${escapeHtml(preview.goal_loop_id || "not_staged")}</div>
16835:           <div class="card-sub">${escapeHtml(preview.status || "ab_test_preview")}</div>
16836:         </div>
16837:         <div class="card">
16838:           <div class="card-label">A/B Proposals</div>
16839:           <div class="card-value" data-aion-goal-loop-ab-count="true">${escapeHtml(nodes.length)}</div>
16840:           <div class="card-sub">Boardroom review required</div>
16841:         </div>
16842:         <div class="card">
16843:           <div class="card-label">Lifecycle</div>
16844:           <div class="card-value" data-aion-goal-loop-ab-lifecycle-count="true">${escapeHtml(lifecycleSteps.length)}</div>
16845:           <div class="card-sub">proposed → complete</div>
16846:         </div>
16847:         <div class="card">
16848:           <div class="card-label">Safety</div>
16849:           <div class="card-value" data-aion-goal-loop-ab-safety="true">Preview only</div>
16850:           <div class="card-sub">No campaign launch</div>
16851:         </div>
16852:       </div>
16853: 
16854:       <div class="list-wrap" style="margin-top:12px;" data-aion-goal-loop-ab-lifecycle="true">
16855:         ${lifecycleSteps.map((step) => `
16856:           <div class="list-item" data-aion-goal-loop-ab-lifecycle-step="${escapeHtml(step.status)}">
16857:             <div class="list-item-title">${escapeHtml(step.step_index)}. ${escapeHtml(step.label)}</div>
16858:             <div class="list-item-sub">Lifecycle state preview. Execution remains blocked.</div>
16859:           </div>
16860:         `).join("")}
16861:       </div>
16862: 
16863:       ${
16864:         nodes.length
16865:           ? `
16866:             <div class="list-wrap" style="margin-top:12px;" data-aion-goal-loop-ab-nodes="true">
16867:               ${nodes.map((node) => `
16868:                 <div class="list-item" data-aion-goal-loop-ab-node="${escapeHtml(node.node_id)}">
16869:                   <div class="list-item-title">${escapeHtml(node.title)}</div>
16870:                   <div class="list-item-sub">${escapeHtml(node.hypothesis)}</div>
16871: 
16872:                   <div class="card-grid" style="margin-top:8px;">
16873:                     <div class="card">
16874:                       <div class="card-label">Variant A</div>
16875:                       <div class="card-value" data-aion-goal-loop-ab-variant-a="true">${escapeHtml(node.variant_a.label)}</div>
16876:                       <div class="card-sub">${escapeHtml(node.variant_a.description)}</div>
16877:                     </div>
16878:                     <div class="card">
16879:                       <div class="card-label">Variant B</div>
16880:                       <div class="card-value" data-aion-goal-loop-ab-variant-b="true">${escapeHtml(node.variant_b.label)}</div>
16881:                       <div class="card-sub">${escapeHtml(node.variant_b.description)}</div>
16882:                     </div>
16883:                   </div>
16884: 
16885:                   <div class="badge-row" style="margin-top:8px;">
16886:                     <span class="badge">${escapeHtml(node.lifecycle_status)}</span>
16887:                     <span class="badge">${escapeHtml(node.approval_state)}</span>
16888:                     <span class="badge">Metric ${escapeHtml(node.success_metric.name || "—")}</span>
16889:                     <span class="badge">${escapeHtml(node.test_duration)}</span>
16890:                     <span class="badge">Preview only</span>
16891:                   </div>
16892:                 </div>
16893:               `).join("")}
16894:             </div>
16895:           `
16896:           : `<div class="empty-state" style="margin-top:12px;">No A/B test proposals are available yet.</div>`
16897:       }
16898: 
16899:       <div class="notice warning" data-aion-goal-loop-ab-preview-boundary="true" style="margin-top:12px;">
16900:         Safety: F1 creates A/B test schema and lifecycle previews only. It does not launch a campaign,
16901:         call connectors, execute tasks, persist data, send messages, create bookings or take payments.
16902:       </div>
16903:     </section>
16904:   `;
16905: }
16906: 
16907: if (typeof window !== "undefined") {
16908:   window.buildAionGoalLoopAbTestNode = buildAionGoalLoopAbTestNode;
16909:   window.buildAionGoalLoopAbTestLifecyclePreview = buildAionGoalLoopAbTestLifecyclePreview;
16910:   window.renderAionGoalLoopAbTestPanel = renderAionGoalLoopAbTestPanel;
16911: }
16912: /* END AION GOAL LOOP CANVAS PHASE F1 */
16913: 
16914: 
16915: function renderAionGoalLoopEvaluationEnginePanel() {
16916:   const preview = buildAionGoalLoopEvaluationPreview();
16917:   const evaluations = Array.isArray(preview.evaluations) ? preview.evaluations : [];
16918:   const summary = preview.boardroom_evaluation_summary || {};
16919: 
16920:   return `
16921:     <section
16922:       class="panel large-panel"
16923:       data-aion-goal-loop-evaluation-engine-panel="true"
16924:       style="background:#ffffff; margin-top:9px;"
16925:     >
16926:       <div class="panel-title">Goal Loop Evaluation Engine</div>
16927:       <div class="helper-text">
16928:         Compares manual result previews against metric targets and prepares Boardroom evaluation previews.
16929:         E3 does not mutate the graph, persist data or execute changes.
16930:       </div>
16931: 
16932:       <div class="card-grid" style="margin-top:12px;">
16933:         <div class="card">
16934:           <div class="card-label">Goal Loop</div>
16935:           <div class="card-value" data-aion-goal-loop-evaluation-goal-loop-id="true">${escapeHtml(preview.goal_loop_id || "not_staged")}</div>
16936:           <div class="card-sub">${escapeHtml(preview.status || "evaluation_preview")}</div>
16937:         </div>
16938:         <div class="card">
16939:           <div class="card-label">Evaluations</div>
16940:           <div class="card-value" data-aion-goal-loop-evaluation-count="true">${escapeHtml(evaluations.length)}</div>
16941:           <div class="card-sub">Metric result comparisons</div>
16942:         </div>
16943:         <div class="card">
16944:           <div class="card-label">Boardroom Action</div>
16945:           <div class="card-value" data-aion-goal-loop-evaluation-board-action="true">${escapeHtml(summary.recommended_board_action || "continue_loop")}</div>
16946:           <div class="card-sub">Review required: ${summary.requires_board_review ? "yes" : "no"}</div>
16947:         </div>
16948:         <div class="card">
16949:           <div class="card-label">Safety</div>
16950:           <div class="card-value" data-aion-goal-loop-evaluation-safety="true">Preview only</div>
16951:           <div class="card-sub">No graph mutation or execution</div>
16952:         </div>
16953:       </div>
```

### Around line 20979: `if (!nodes.length) {`

```js
20934:     step_index: stepIndex,
20935:     mission_plan: missionPlan,
20936:     business_context: missionMap.business_context || missionMap || {},
20937:     business_context_mission_map: missionMap,
20938:     marketing_form: state.marketingForm || state.marketing_form || {},
20939:     marketing_summary: state.marketingSummary || state.marketing_summary || {},
20940:     brand_foundation_state: state.brandFoundationState || state.brand_foundation_state || {},
20941:     provider: state.ai_provider || state.provider || "gemma4",
20942:     preview_only: true,
20943:     live_external_side_effects_enabled: false,
20944:   };
20945: }
20946: 
20947: async function fetchAionPilotExecuteSafeStep(payload = {}) {
20948:   const response = await fetch(getAionPilotExecuteSafeStepUrl(), {
20949:     method: "POST",
20950:     headers: { "Content-Type": "application/json" },
20951:     body: JSON.stringify(payload || {}),
20952:   });
20953: 
20954:   if (!response.ok) {
20955:     const errorText = await response.text().catch(() => "");
20956:     throw new Error(`Pilot safe-step execution failed: ${response.status} ${errorText}`);
20957:   }
20958: 
20959:   return await response.json();
20960: }
20961: 
20962: async function executeAndAppendAionPilotMissionMapStepOutput(payload = {}, plan = null, pilotState = null) {
20963:   const state = pilotState || getAionPilotFrontendInteractionState();
20964:   const safePlan = plan || state.plan || buildAionPilotUniversalPlan(state.last_request || "");
20965:   const nodes = Array.isArray(state.mission_loop_queue) ? state.mission_loop_queue : [];
20966:   const currentIndex = Number(state.mission_loop_index || 0);
20967: 
20968:   if (state.safe_step_execution_status === "loading") {
20969:     appendAionPilotStreamEvent({
20970:       type: "pilot_safe_step_duplicate_click_ignored",
20971:       label: "Safe step already running",
20972:       detail: "Pilot is already executing the current safe step. Duplicate Continue click ignored.",
20973:       status: "running_safe_work",
20974:     });
20975:     if (typeof requestRender === "function") requestRender();
20976:     return false;
20977:   }
20978: 
20979:   if (!nodes.length) {
20980:     appendAionPilotStepOutput({
20981:       step_number: getAionPilotStepOutputs().length + 1,
20982:       title: "Mission runtime preview",
20983:       output_label: "Mission runtime preview",
20984:       output_text: [
20985:         "Mission runtime preview",
20986:         "",
20987:         "The backend mission-preview bridge returned no executable safe internal task nodes.",
20988:         "",
20989:         "No live external side effects occurred.",
20990:       ].join("\n"),
20991:       artifact_hash: payload.runtime_preview?.state?.state_hash || "sha256:mission_preview_no_nodes",
20992:       receipt_hash: payload.timeline?.timeline_hash || "sha256:mission_preview_no_nodes_receipt",
20993:     });
20994:     return false;
20995:   }
20996: 
20997:   if (currentIndex >= nodes.length) {
20998:     appendAionPilotStepOutput({
20999:       step_number: getAionPilotStepOutputs().length + 1,
21000:       title: "No further safe mission-map work",
21001:       output_label: "No further safe mission-map work",
21002:       output_text: [
21003:         "No further safe mission-map work available",
21004:         "",
21005:         `Mission: ${safePlan.goal || state.last_request || ""}`,
21006:         "",
21007:         "No further backend mission-map task nodes are available.",
21008:         "",
21009:         "No live external side effects occurred.",
21010:       ].join("\n"),
21011:       artifact_hash: payload.runtime_preview?.state?.state_hash || "sha256:mission_preview_complete",
21012:       receipt_hash: payload.timeline?.timeline_hash || "sha256:mission_preview_complete_receipt",
21013:     });
21014:     return false;
21015:   }
21016: 
21017:   const node = nodes[currentIndex];
21018:   const title = normaliseAionPilotMissionMapNodeTitle(node, currentIndex);
21019:   const approvalRequired =
21020:     node?.requires_checkpoint === true ||
21021:     node?.requires_approval === true ||
21022:     node?.is_approval_gate === true ||
21023:     String(node?.decision || "") === "checkpoint_required";
21024: 
21025:   if (approvalRequired) {
21026:     state.pending_mission_approval_index = currentIndex;
21027:     state.pending_mission_approval_title = title;
21028:     state.status = "waiting_review";
21029:     state.safe_work_status = "waiting_review";
21030:     state.artifact_status = "waiting_review";
21031: 
21032:     appendAionPilotStepOutput({
21033:       step_number: getAionPilotStepOutputs().length + 1,
21034:       title: `Approval required: ${title}`,
21035:       output_label: `Approval required: ${title}`,
21036:       output_text: [
21037:         `Approval required`,
21038:         ``,
21039:         `Next task: ${title}`,
21040:         ``,
21041:         `Question`,
21042:         `Approval required?`,
21043:         ``,
21044:         `Runtime decision`,
21045:         `This stage was selected as a human approval checkpoint. Pilot has stopped before executing it.`,
21046:         ``,
21047:         `If approved`,
21048:         `Click Continue safe work / Approve and continue. Pilot will mark this checkpoint as approved and move to the next safe task.`,
21049:         ``,
21050:         `If not approved`,
21051:         `Click Revise or Stop.`,
21052:         ``,
21053:         `Safety boundary`,
21054:         `No live external action has been taken.`,
21055:       ].join("\n"),
21056:       artifact_hash: `sha256:mission_approval_gate_${currentIndex}`,
21057:       receipt_hash: `sha256:mission_approval_gate_${currentIndex}_receipt`,
21058:     });
21059: 
21060:     appendAionPilotStreamEvent({
21061:       type: "mission_approval_gate_reached",
21062:       label: `Approval required: ${title}`,
21063:       detail: "Pilot paused before a selected approval stage.",
21064:       status: "waiting_review",
21065:     });
21066: 
21067:     return false;
21068:   }
```

### Around line 20997: `if (currentIndex >= nodes.length) {`

```js
20952:   });
20953: 
20954:   if (!response.ok) {
20955:     const errorText = await response.text().catch(() => "");
20956:     throw new Error(`Pilot safe-step execution failed: ${response.status} ${errorText}`);
20957:   }
20958: 
20959:   return await response.json();
20960: }
20961: 
20962: async function executeAndAppendAionPilotMissionMapStepOutput(payload = {}, plan = null, pilotState = null) {
20963:   const state = pilotState || getAionPilotFrontendInteractionState();
20964:   const safePlan = plan || state.plan || buildAionPilotUniversalPlan(state.last_request || "");
20965:   const nodes = Array.isArray(state.mission_loop_queue) ? state.mission_loop_queue : [];
20966:   const currentIndex = Number(state.mission_loop_index || 0);
20967: 
20968:   if (state.safe_step_execution_status === "loading") {
20969:     appendAionPilotStreamEvent({
20970:       type: "pilot_safe_step_duplicate_click_ignored",
20971:       label: "Safe step already running",
20972:       detail: "Pilot is already executing the current safe step. Duplicate Continue click ignored.",
20973:       status: "running_safe_work",
20974:     });
20975:     if (typeof requestRender === "function") requestRender();
20976:     return false;
20977:   }
20978: 
20979:   if (!nodes.length) {
20980:     appendAionPilotStepOutput({
20981:       step_number: getAionPilotStepOutputs().length + 1,
20982:       title: "Mission runtime preview",
20983:       output_label: "Mission runtime preview",
20984:       output_text: [
20985:         "Mission runtime preview",
20986:         "",
20987:         "The backend mission-preview bridge returned no executable safe internal task nodes.",
20988:         "",
20989:         "No live external side effects occurred.",
20990:       ].join("\n"),
20991:       artifact_hash: payload.runtime_preview?.state?.state_hash || "sha256:mission_preview_no_nodes",
20992:       receipt_hash: payload.timeline?.timeline_hash || "sha256:mission_preview_no_nodes_receipt",
20993:     });
20994:     return false;
20995:   }
20996: 
20997:   if (currentIndex >= nodes.length) {
20998:     appendAionPilotStepOutput({
20999:       step_number: getAionPilotStepOutputs().length + 1,
21000:       title: "No further safe mission-map work",
21001:       output_label: "No further safe mission-map work",
21002:       output_text: [
21003:         "No further safe mission-map work available",
21004:         "",
21005:         `Mission: ${safePlan.goal || state.last_request || ""}`,
21006:         "",
21007:         "No further backend mission-map task nodes are available.",
21008:         "",
21009:         "No live external side effects occurred.",
21010:       ].join("\n"),
21011:       artifact_hash: payload.runtime_preview?.state?.state_hash || "sha256:mission_preview_complete",
21012:       receipt_hash: payload.timeline?.timeline_hash || "sha256:mission_preview_complete_receipt",
21013:     });
21014:     return false;
21015:   }
21016: 
21017:   const node = nodes[currentIndex];
21018:   const title = normaliseAionPilotMissionMapNodeTitle(node, currentIndex);
21019:   const approvalRequired =
21020:     node?.requires_checkpoint === true ||
21021:     node?.requires_approval === true ||
21022:     node?.is_approval_gate === true ||
21023:     String(node?.decision || "") === "checkpoint_required";
21024: 
21025:   if (approvalRequired) {
21026:     state.pending_mission_approval_index = currentIndex;
21027:     state.pending_mission_approval_title = title;
21028:     state.status = "waiting_review";
21029:     state.safe_work_status = "waiting_review";
21030:     state.artifact_status = "waiting_review";
21031: 
21032:     appendAionPilotStepOutput({
21033:       step_number: getAionPilotStepOutputs().length + 1,
21034:       title: `Approval required: ${title}`,
21035:       output_label: `Approval required: ${title}`,
21036:       output_text: [
21037:         `Approval required`,
21038:         ``,
21039:         `Next task: ${title}`,
21040:         ``,
21041:         `Question`,
21042:         `Approval required?`,
21043:         ``,
21044:         `Runtime decision`,
21045:         `This stage was selected as a human approval checkpoint. Pilot has stopped before executing it.`,
21046:         ``,
21047:         `If approved`,
21048:         `Click Continue safe work / Approve and continue. Pilot will mark this checkpoint as approved and move to the next safe task.`,
21049:         ``,
21050:         `If not approved`,
21051:         `Click Revise or Stop.`,
21052:         ``,
21053:         `Safety boundary`,
21054:         `No live external action has been taken.`,
21055:       ].join("\n"),
21056:       artifact_hash: `sha256:mission_approval_gate_${currentIndex}`,
21057:       receipt_hash: `sha256:mission_approval_gate_${currentIndex}_receipt`,
21058:     });
21059: 
21060:     appendAionPilotStreamEvent({
21061:       type: "mission_approval_gate_reached",
21062:       label: `Approval required: ${title}`,
21063:       detail: "Pilot paused before a selected approval stage.",
21064:       status: "waiting_review",
21065:     });
21066: 
21067:     return false;
21068:   }
21069: 
21070:   const executionPayload = buildAionPilotExecuteSafeStepPayload(node, payload, safePlan, state, currentIndex);
21071: 
21072:   state.status = "running_safe_work";
21073:   state.safe_work_status = "running_safe_work";
21074:   state.safe_step_execution_status = "loading";
21075:   state.safe_step_execution_started_at = Date.now();
21076: 
21077:   appendAionPilotStreamEvent({
21078:     type: "pilot_safe_step_execution_started",
21079:     label: `Executing safe step: ${title}`,
21080:     detail: "Pilot is calling the backend safe-step executor for the current approved safe task.",
21081:     status: "running_safe_work",
21082:   });
21083: 
21084:   if (typeof requestRender === "function") requestRender();
21085: 
21086:   try {
```

### Around line 21342: `node_count: Array.isArray(pilotState.context_task_nodes) ? pilotState.context_task_nodes.length : 0,`

```js
21297:     title: "Loading backend mission map",
21298:     output_label: "Loading backend mission map",
21299:     output_text: [
21300:       "Loading backend mission map",
21301:       "",
21302:       "Pilot clicked Continue safe work.",
21303:       "Now calling /api/local-node/aion/pilot/mission-preview.",
21304:       "",
21305:       "Expected result:",
21306:       "- business context map",
21307:       "- brand foundation context",
21308:       "- marketing context",
21309:       "- safe mission plan steps",
21310:       "- task nodes",
21311:       "- vault / OAuth checkpoints",
21312:       "- human task cards where required",
21313:       "",
21314:       "No live external side effects are allowed.",
21315:     ].join("\n"),
21316:     artifact_hash: "sha256:frontend_backend_mission_map_loading",
21317:     receipt_hash: "sha256:frontend_backend_mission_map_loading_receipt",
21318:   });
21319: 
21320:   if (typeof requestRender === "function") {
21321:     requestRender();
21322:   }
21323: 
21324:   try {
21325:     console.log("[AION Pilot] Fetching backend mission preview", buildAionPilotMissionPreviewPayload(plan, pilotState));
21326: 
21327:     const missionPayload = await fetchAionPilotMissionPreviewIntoPilotState(plan, pilotState);
21328: 
21329:     console.log("[AION Pilot] Backend mission preview received", missionPayload);
21330: 
21331:     appendAionPilotStreamEvent({
21332:       type: "business_context_mission_map_ready",
21333:       label: "Business-context mission map loaded",
21334:       detail: "Pilot received backend Mission Mode plan, safe-step queue, provider checkpoints and human task cards.",
21335:       status: "running_safe_work",
21336:     });
21337: 
21338:     const appended = await executeAndAppendAionPilotMissionMapStepOutput(missionPayload, plan, pilotState);
21339: 
21340:     console.log("[AION Pilot] Mission map output appended", {
21341:       appended,
21342:       node_count: Array.isArray(pilotState.context_task_nodes) ? pilotState.context_task_nodes.length : 0,
21343:       loop_count: Array.isArray(pilotState.mission_loop_queue) ? pilotState.mission_loop_queue.length : 0,
21344:       human_task_count: Array.isArray(pilotState.human_task_cards) ? pilotState.human_task_cards.length : 0,
21345:       credential_card_count: Array.isArray(pilotState.credential_required_cards) ? pilotState.credential_required_cards.length : 0,
21346:     });
21347: 
21348:     pilotState.artifact_status = appended ? "completed_preview" : "waiting_review";
21349:     pilotState.safe_work_status = appended ? "completed_preview" : "waiting_review";
21350:     pilotState.status = appended ? "completed_preview" : "waiting_review";
21351: 
21352:     appendAionPilotStreamEvent({
21353:       type: appended ? "mission_map_safe_step_completed" : "mission_map_waiting",
21354:       label: appended ? "Mission-map safe work completed" : "Mission-map waiting",
21355:       detail: appended
21356:         ? "Pilot completed the next safe backend mission-map node and stopped before live external actions."
21357:         : "Pilot loaded the backend mission-map but found no safe node to run.",
21358:       status: pilotState.status,
21359:     });
21360: 
21361:     appendAionPilotStreamEvent({
21362:       type: "receipt_created",
21363:       label: "Proof receipt preview created",
21364:       detail: "Pilot created a local preview receipt. No live chain write occurred.",
21365:       status: pilotState.status,
21366:     });
21367:   } catch (error) {
21368:     console.error("[AION Pilot] Backend mission preview runner failed", error);
21369: 
21370:     pilotState.status = "error";
21371:     pilotState.safe_work_status = "error";
21372:     pilotState.backend_mission_preview_status = "error";
21373:     pilotState.backend_mission_preview_started_at = null;
21374:     pilotState.backend_mission_preview_error = String(error?.message || error);
21375: 
21376:     appendAionPilotStepOutput({
21377:       step_number: getAionPilotStepOutputs().length + 1,
21378:       title: "Backend mission preview failed",
21379:       output_label: "Backend mission preview failed",
21380:       output_text: [
21381:         "Backend mission preview failed",
21382:         "",
21383:         String(error?.message || error),
21384:         "",
21385:         "Pilot did not continue because the backend did not return a usable mission-preview payload.",
21386:         "",
21387:         "No live external side effects were performed.",
21388:       ].join("\n"),
21389:       artifact_hash: "sha256:backend_mission_preview_failed",
21390:       receipt_hash: "sha256:backend_mission_preview_failed_receipt",
21391:     });
21392: 
21393:     appendAionPilotStreamEvent({
21394:       type: "mission_preview_error",
21395:       label: "Mission preview failed",
21396:       detail: String(error?.message || error),
21397:       status: "error",
21398:     });
21399:   }
21400: 
21401:   if (typeof requestRender === "function") {
21402:     requestRender();
21403:   }
21404: }
21405: /* END PHASE 21T LOCK */
21406: 
21407: 
21408: /* END PHASE 21S LOCK */
21409: 
21410: 
21411: /* END PHASE 21Q LOCK */
21412: 
21413: 
21414: /* END PHASE 21P LOCK */
21415: 
21416: 
21417: /* END PHASE 21O LOCK */
21418: 
21419: 
21420: function getAionPilotCockpitSnapshot() {
21421:   const pilotState = getAionPilotFrontendInteractionState();
21422: 
21423:   return {
21424:     status: pilotState.status || "idle",
21425:     mode: "preview_only",
21426:     identity: "AION Pilot native runtime executor, not UI automation",
21427:     business_id: "home-fixed",
21428:     mission_id: "pilot_demo_pdf_mission",
21429:     mission_run_id: "pilot_demo_run_preview",
21430:     step_id: "compose_document",
21431:     request_placeholder: "Build me a PDF document with X data",
```

### Around line 23774: `function renderOperationsAgentsSurface() {`

```js
23729: 
23730:   const target = direction === "up" ? index - 1 : index + 1;
23731:   if (target < 0 || target >= next.steps.length) return next;
23732: 
23733:   const steps = [...next.steps];
23734:   const [item] = steps.splice(index, 1);
23735:   steps.splice(target, 0, item);
23736:   next.steps = steps;
23737: 
23738:   return next;
23739: }
23740: 
23741: function duplicateStepBuilderStep(draft, stepId) {
23742:   const next = normaliseStepBuilderDraft(draft);
23743:   const index = next.steps.findIndex((step) => step.step_id === stepId);
23744: 
23745:   if (index < 0) return next;
23746: 
23747:   const original = next.steps[index];
23748:   const copyId = makeStepBuilderId("step");
23749:   const copy = {
23750:     ...original,
23751:     step_id: copyId,
23752:     name: `${original.name || "Step"} copy`,
23753:     output: original.output ? copyId.replace(/^step_/, "output_") : "",
23754:   };
23755: 
23756:   next.steps = [...next.steps];
23757:   next.steps.splice(index + 1, 0, copy);
23758: 
23759:   return next;
23760: }
23761: 
23762: function deleteStepBuilderStep(draft, stepId) {
23763:   const next = normaliseStepBuilderDraft(draft);
23764:   next.steps = next.steps.filter((step) => step.step_id !== stepId);
23765:   return next;
23766: }
23767: 
23768: function addStepBuilderStep(draft, type = "trigger") {
23769:   const next = normaliseStepBuilderDraft(draft);
23770:   next.steps = [...next.steps, createStepBuilderStep(type)];
23771:   return next;
23772: }
23773: 
23774: function renderOperationsAgentsSurface() {
23775:   const rawWorkflows = Array.isArray(state.operationsAgentsWorkflows)
23776:     ? state.operationsAgentsWorkflows
23777:     : [];
23778: 
23779:   const workflows = getVisibleTeachAionWorkflows(rawWorkflows);
23780:   const hiddenWorkflowCount = rawWorkflows.length - workflows.length;
23781:   const showDeveloperTools = isTeachAionDeveloperMode();
23782: 
23783:   const testResult = state.operationsAgentsTestResult || null;
23784: 
23785:   const tools = Array.isArray(state.operationsAgentsTools)
23786:     ? state.operationsAgentsTools
23787:     : [];
23788: 
23789:   const approvals = Array.isArray(state.operationsAgentsApprovals)
23790:     ? state.operationsAgentsApprovals
23791:     : [];
23792: 
23793:   const externalTools = Array.isArray(state.operationsAgentsExternalTools)
23794:     ? state.operationsAgentsExternalTools
23795:     : [];
23796: 
23797:   const genericWorkflows = Array.isArray(state.operationsAgentsGenericWorkflows)
23798:     ? state.operationsAgentsGenericWorkflows
23799:     : [];
23800: 
23801:   const visibleTools = tools.slice(0, 8);
23802:   const visibleExternalTools = externalTools.slice(0, 8);
23803:   const gmailConnector = state.operationsAgentsGmailConnector || null;
23804:   const loading = state.operationsAgentsLoading === true;
23805: 
23806:   const builderOpen = state.operationsAgentsStepBuilderOpen === true;
23807:   const builderValidated =
23808:     state.operationsAgentsStepBuilderCompileResult?.ok === true ||
23809:     state.operationsAgentsStepBuilderSaveResult?.ok === true;
23810: 
23811:   const builderStatusLabel = builderValidated ? "Validated" : "Draft";
23812: 
23813:   return `
23814:     <div class="surface-shell operations-agents-surface operations-agents-canvas-mode">
23815:       <div class="dashboard-shell">
23816:         ${renderAionWorkflowCanvasPanel({ workflows, loading })}
23817: 
23818:         <details class="train-collapsed-section">
23819:           <summary>
23820:             <span>
23821:               <span class="eyebrow">Browser recorder</span>
23822:               <strong>Teach Aion a browser skill</strong>
23823:             </span>
23824:             <span class="badge">Open</span>
23825:           </summary>
23826:           ${renderBrowserDesktopOperatorPanel(loading)}
23827:         </details>
23828: 
23829:         <details class="train-collapsed-section">
23830:           <summary>
23831:             <span>
23832:               <span class="eyebrow">Browser skills</span>
23833:               <strong>Saved browser micro-skills</strong>
23834:             </span>
23835:             <span class="badge">Open</span>
23836:           </summary>
23837:           ${renderBrowserMicroSkillLibrary()}
23838:         </details>
23839: 
23840:         <details class="train-collapsed-section">
23841:           <summary>
23842:             <span>
23843:               <span class="eyebrow">Workflow chain</span>
23844:               <strong>Chain browser micro-skills</strong>
23845:             </span>
23846:             <span class="badge">Open</span>
23847:           </summary>
23848:           ${renderBrowserSkillChainBuilder()}
23849:         </details>
23850: 
23851:         ${
23852:           state.operationsAgentsGmailPollResult
23853:             ? `
23854:               <section class="train-section-panel">
23855:                 <div class="train-section-head">
23856:                   <div>
23857:                     <div class="eyebrow">Gmail check result</div>
23858:                     <h2>Latest Gmail check</h2>
23859:                     <p class="muted" style="margin:6px 0 0;">
23860:                       Poll id: ${escapeHtml(state.operationsAgentsGmailPollResult.poll_id || "unknown")}
23861:                     </p>
23862:                   </div>
23863: 
```

### Around line 26195: `if (!nodes.length) return [];`

```js
26150:               }
26151:             </div>
26152:           </div>
26153:         </div>
26154: 
26155:         <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:9px;">
26156:           <button
26157:             class="secondary-btn"
26158:             data-operations-agents-action="copy-browser-skill-id"
26159:             data-skill-id="${escapeHtml(skill?.skill_id || "")}"
26160:           >
26161:             Copy skill id
26162:           </button>
26163: 
26164:           <button
26165:             class="secondary-btn"
26166:             data-operations-agents-action="duplicate-browser-skill"
26167:             data-skill-id="${escapeHtml(skill?.skill_id || "")}"
26168:           >
26169:             Duplicate skill
26170:           </button>
26171: 
26172:           <button
26173:             class="primary-btn"
26174:             data-operations-agents-action="publish-browser-skill"
26175:             data-skill-id="${escapeHtml(skill?.skill_id || "")}"
26176:           >
26177:             Mark reusable
26178:           </button>
26179:         </div>
26180:       </div>
26181:     </div>
26182:   `;
26183: }
26184: 
26185: 
26186: 
26187: const AION_WORKFLOW_DRAFT_STORAGE_KEY = "aion.workflow_builder.current_draft.v1";
26188: 
26189: const AION_WORKFLOW_GLYPH_SCHEMA_VERSION = "aion.workflow_glyph.v1";
26190: 
26191: function getAionWorkflowOrderedNodesForGlyph(graph) {
26192:   const nodes = getAionWorkflowOrderedNodesForGlyph(graph);
26193:   const edges = Array.isArray(graph?.edges) ? graph.edges : [];
26194: 
26195:   if (!nodes.length) return [];
26196: 
26197:   const nodeById = new Map(nodes.map((node) => [String(node.id), node]));
26198:   const incoming = new Map(nodes.map((node) => [String(node.id), 0]));
26199:   const outgoing = new Map(nodes.map((node) => [String(node.id), []]));
26200: 
26201:   for (const edge of edges) {
26202:     const from = String(edge?.from || "");
26203:     const to = String(edge?.to || "");
26204: 
26205:     if (!nodeById.has(from) || !nodeById.has(to)) continue;
26206: 
26207:     incoming.set(to, (incoming.get(to) || 0) + 1);
26208:     outgoing.get(from)?.push(to);
26209:   }
26210: 
26211:   const visualSort = (a, b) => {
26212:     const ax = Number(a?.x || 0);
26213:     const bx = Number(b?.x || 0);
26214:     const ay = Number(a?.y || 0);
26215:     const by = Number(b?.y || 0);
26216: 
26217:     if (ax !== bx) return ax - bx;
26218:     if (ay !== by) return ay - by;
26219:     return String(a?.id || "").localeCompare(String(b?.id || ""));
26220:   };
26221: 
26222:   if (!edges.length) {
26223:     return [...nodes].sort(visualSort);
26224:   }
26225: 
26226:   const queue = nodes
26227:     .filter((node) => (incoming.get(String(node.id)) || 0) === 0)
26228:     .sort(visualSort);
26229: 
26230:   const ordered = [];
26231:   const seen = new Set();
26232: 
26233:   while (queue.length) {
26234:     const node = queue.shift();
26235:     const nodeId = String(node.id);
26236: 
26237:     if (seen.has(nodeId)) continue;
26238: 
26239:     seen.add(nodeId);
26240:     ordered.push(node);
26241: 
26242:     const nextIds = [...(outgoing.get(nodeId) || [])]
26243:       .map((id) => nodeById.get(id))
26244:       .filter(Boolean)
26245:       .sort(visualSort);
26246: 
26247:     for (const nextNode of nextIds) {
26248:       const nextId = String(nextNode.id);
26249:       incoming.set(nextId, Math.max(0, (incoming.get(nextId) || 0) - 1));
26250: 
26251:       if ((incoming.get(nextId) || 0) === 0 && !seen.has(nextId)) {
26252:         queue.push(nextNode);
26253:       }
26254:     }
26255: 
26256:     queue.sort(visualSort);
26257:   }
26258: 
26259:   const remaining = nodes
26260:     .filter((node) => !seen.has(String(node.id)))
26261:     .sort(visualSort);
26262: 
26263:   return [...ordered, ...remaining];
26264: }
26265: 
26266: const AION_WORKFLOW_GLYPH_NAMESPACE = "aion.workflow";
26267: 
26268: const AION_WORKFLOW_OPS = Object.freeze({
26269:   SEQUENCE: "aion.workflow:sequence",
26270:   TRIGGER: "aion.workflow:trigger",
26271:   EXTRACT: "aion.workflow:extract",
26272:   CLASSIFY: "aion.workflow:classify",
26273:   ACTION: "aion.workflow:action",
26274:   APPROVAL: "aion.workflow:approval",
26275:   WAIT: "aion.workflow:wait",
26276:   ROUTE: "aion.workflow:route",
26277: });
26278: 
26279: 
26280: function normaliseAionBusinessIdentitySlug(value = "") {
26281:   const raw = String(value || "").trim();
26282:   if (!raw) return "";
26283:   return raw
26284:     .toLowerCase()
```

### Around line 26406: `window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||`

```js
26361:       item.brandName,
26362:       item.trading_name,
26363:       item.tradingName,
26364:     );
26365: 
26366:     const rawId = firstText(
26367:       item.business_id,
26368:       item.businessId,
26369:       item.business_container,
26370:       item.businessContainer,
26371:       item.workspace_id,
26372:       item.workspaceId,
26373:     );
26374: 
26375:     if (isAionLegacyDemoBusinessIdentity(name) || isAionLegacyDemoBusinessIdentity(rawId)) {
26376:       continue;
26377:     }
26378: 
26379:     const slug = normaliseAionBusinessIdentitySlug(rawId || name);
26380: 
26381:     if (name || slug) {
26382:       return {
26383:         business_id: slug || "business_not_registered",
26384:         business_name: name || slug,
26385:         registered: true,
26386:         source: "business_information_form",
26387:       };
26388:     }
26389:   }
26390: 
26391:   return {
26392:     business_id: "business_not_registered",
26393:     business_name: "Business not registered",
26394:     registered: false,
26395:     source: "missing_business_information_form",
26396:   };
26397: }
26398: 
26399: 
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
```

### Around line 26408: `window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||`

```js
26363:       item.tradingName,
26364:     );
26365: 
26366:     const rawId = firstText(
26367:       item.business_id,
26368:       item.businessId,
26369:       item.business_container,
26370:       item.businessContainer,
26371:       item.workspace_id,
26372:       item.workspaceId,
26373:     );
26374: 
26375:     if (isAionLegacyDemoBusinessIdentity(name) || isAionLegacyDemoBusinessIdentity(rawId)) {
26376:       continue;
26377:     }
26378: 
26379:     const slug = normaliseAionBusinessIdentitySlug(rawId || name);
26380: 
26381:     if (name || slug) {
26382:       return {
26383:         business_id: slug || "business_not_registered",
26384:         business_name: name || slug,
26385:         registered: true,
26386:         source: "business_information_form",
26387:       };
26388:     }
26389:   }
26390: 
26391:   return {
26392:     business_id: "business_not_registered",
26393:     business_name: "Business not registered",
26394:     registered: false,
26395:     source: "missing_business_information_form",
26396:   };
26397: }
26398: 
26399: 
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
```

### Around line 26410: `window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||`

```js
26365: 
26366:     const rawId = firstText(
26367:       item.business_id,
26368:       item.businessId,
26369:       item.business_container,
26370:       item.businessContainer,
26371:       item.workspace_id,
26372:       item.workspaceId,
26373:     );
26374: 
26375:     if (isAionLegacyDemoBusinessIdentity(name) || isAionLegacyDemoBusinessIdentity(rawId)) {
26376:       continue;
26377:     }
26378: 
26379:     const slug = normaliseAionBusinessIdentitySlug(rawId || name);
26380: 
26381:     if (name || slug) {
26382:       return {
26383:         business_id: slug || "business_not_registered",
26384:         business_name: name || slug,
26385:         registered: true,
26386:         source: "business_information_form",
26387:       };
26388:     }
26389:   }
26390: 
26391:   return {
26392:     business_id: "business_not_registered",
26393:     business_name: "Business not registered",
26394:     registered: false,
26395:     source: "missing_business_information_form",
26396:   };
26397: }
26398: 
26399: 
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
```

### Around line 26411: `window.__aionGoalLoopWorkflowGraph?.business_container ||`

```js
26366:     const rawId = firstText(
26367:       item.business_id,
26368:       item.businessId,
26369:       item.business_container,
26370:       item.businessContainer,
26371:       item.workspace_id,
26372:       item.workspaceId,
26373:     );
26374: 
26375:     if (isAionLegacyDemoBusinessIdentity(name) || isAionLegacyDemoBusinessIdentity(rawId)) {
26376:       continue;
26377:     }
26378: 
26379:     const slug = normaliseAionBusinessIdentitySlug(rawId || name);
26380: 
26381:     if (name || slug) {
26382:       return {
26383:         business_id: slug || "business_not_registered",
26384:         business_name: name || slug,
26385:         registered: true,
26386:         source: "business_information_form",
26387:       };
26388:     }
26389:   }
26390: 
26391:   return {
26392:     business_id: "business_not_registered",
26393:     business_name: "Business not registered",
26394:     registered: false,
26395:     source: "missing_business_information_form",
26396:   };
26397: }
26398: 
26399: 
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
```

### Around line 26413: `window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||`

```js
26368:       item.businessId,
26369:       item.business_container,
26370:       item.businessContainer,
26371:       item.workspace_id,
26372:       item.workspaceId,
26373:     );
26374: 
26375:     if (isAionLegacyDemoBusinessIdentity(name) || isAionLegacyDemoBusinessIdentity(rawId)) {
26376:       continue;
26377:     }
26378: 
26379:     const slug = normaliseAionBusinessIdentitySlug(rawId || name);
26380: 
26381:     if (name || slug) {
26382:       return {
26383:         business_id: slug || "business_not_registered",
26384:         business_name: name || slug,
26385:         registered: true,
26386:         source: "business_information_form",
26387:       };
26388:     }
26389:   }
26390: 
26391:   return {
26392:     business_id: "business_not_registered",
26393:     business_name: "Business not registered",
26394:     registered: false,
26395:     source: "missing_business_information_form",
26396:   };
26397: }
26398: 
26399: 
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
26501: 
26502:   if (
```

### Around line 26414: `window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"`

```js
26369:       item.business_container,
26370:       item.businessContainer,
26371:       item.workspace_id,
26372:       item.workspaceId,
26373:     );
26374: 
26375:     if (isAionLegacyDemoBusinessIdentity(name) || isAionLegacyDemoBusinessIdentity(rawId)) {
26376:       continue;
26377:     }
26378: 
26379:     const slug = normaliseAionBusinessIdentitySlug(rawId || name);
26380: 
26381:     if (name || slug) {
26382:       return {
26383:         business_id: slug || "business_not_registered",
26384:         business_name: name || slug,
26385:         registered: true,
26386:         source: "business_information_form",
26387:       };
26388:     }
26389:   }
26390: 
26391:   return {
26392:     business_id: "business_not_registered",
26393:     business_name: "Business not registered",
26394:     registered: false,
26395:     source: "missing_business_information_form",
26396:   };
26397: }
26398: 
26399: 
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
26501: 
26502:   if (
26503:     registeredBusinessId &&
```

### Around line 26415: `? window.__aionWorkflowGraph?.business_container`

```js
26370:       item.businessContainer,
26371:       item.workspace_id,
26372:       item.workspaceId,
26373:     );
26374: 
26375:     if (isAionLegacyDemoBusinessIdentity(name) || isAionLegacyDemoBusinessIdentity(rawId)) {
26376:       continue;
26377:     }
26378: 
26379:     const slug = normaliseAionBusinessIdentitySlug(rawId || name);
26380: 
26381:     if (name || slug) {
26382:       return {
26383:         business_id: slug || "business_not_registered",
26384:         business_name: name || slug,
26385:         registered: true,
26386:         source: "business_information_form",
26387:       };
26388:     }
26389:   }
26390: 
26391:   return {
26392:     business_id: "business_not_registered",
26393:     business_name: "Business not registered",
26394:     registered: false,
26395:     source: "missing_business_information_form",
26396:   };
26397: }
26398: 
26399: 
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
26501: 
26502:   if (
26503:     registeredBusinessId &&
26504:     registeredBusinessId !== "business_not_registered" &&
```

### Around line 26443: `window.__aionGoalLoopWorkflowGraph?.business_container ||`

```js
26398: 
26399: 
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
26501: 
26502:   if (
26503:     registeredBusinessId &&
26504:     registeredBusinessId !== "business_not_registered" &&
26505:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(registeredBusinessId))
26506:   ) {
26507:     return registeredBusinessId;
26508:   }
26509: 
26510:   const safeCandidate = String(candidate || "")
26511:     .trim()
26512:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26513:     || "business_not_registered";
26514: 
26515:   if (
26516:     safeCandidate &&
26517:     safeCandidate !== "business_not_registered" &&
26518:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(safeCandidate))
26519:   ) {
26520:     return safeCandidate;
26521:   }
26522: 
26523:   return "business_not_registered";
26524: }
26525: /* END AION BUSINESS ENDPOINT ID LOCK 20260630 */
26526: 
26527: 
26528: 
26529: /* AION BUSINESS ENDPOINT FETCH GUARD 20260630: block stale demo business endpoint calls */
26530: function rewriteAionStaleBusinessEndpointUrl(url = "") {
26531:   const raw = String(url || "");
26532:   if (!raw) return raw;
```

### Around line 26445: `window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||`

```js
26400: function getAionWorkflowCanvasHeaderBusinessLabel() {
26401:   /*
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
26501: 
26502:   if (
26503:     registeredBusinessId &&
26504:     registeredBusinessId !== "business_not_registered" &&
26505:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(registeredBusinessId))
26506:   ) {
26507:     return registeredBusinessId;
26508:   }
26509: 
26510:   const safeCandidate = String(candidate || "")
26511:     .trim()
26512:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26513:     || "business_not_registered";
26514: 
26515:   if (
26516:     safeCandidate &&
26517:     safeCandidate !== "business_not_registered" &&
26518:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(safeCandidate))
26519:   ) {
26520:     return safeCandidate;
26521:   }
26522: 
26523:   return "business_not_registered";
26524: }
26525: /* END AION BUSINESS ENDPOINT ID LOCK 20260630 */
26526: 
26527: 
26528: 
26529: /* AION BUSINESS ENDPOINT FETCH GUARD 20260630: block stale demo business endpoint calls */
26530: function rewriteAionStaleBusinessEndpointUrl(url = "") {
26531:   const raw = String(url || "");
26532:   if (!raw) return raw;
26533: 
26534:   const staleBusinessEndpointPattern =
```

### Around line 26447: `window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||`

```js
26402:    * Header label follows the staged Goal Loop if present and not stale demo data.
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
26501: 
26502:   if (
26503:     registeredBusinessId &&
26504:     registeredBusinessId !== "business_not_registered" &&
26505:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(registeredBusinessId))
26506:   ) {
26507:     return registeredBusinessId;
26508:   }
26509: 
26510:   const safeCandidate = String(candidate || "")
26511:     .trim()
26512:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26513:     || "business_not_registered";
26514: 
26515:   if (
26516:     safeCandidate &&
26517:     safeCandidate !== "business_not_registered" &&
26518:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(safeCandidate))
26519:   ) {
26520:     return safeCandidate;
26521:   }
26522: 
26523:   return "business_not_registered";
26524: }
26525: /* END AION BUSINESS ENDPOINT ID LOCK 20260630 */
26526: 
26527: 
26528: 
26529: /* AION BUSINESS ENDPOINT FETCH GUARD 20260630: block stale demo business endpoint calls */
26530: function rewriteAionStaleBusinessEndpointUrl(url = "") {
26531:   const raw = String(url || "");
26532:   if (!raw) return raw;
26533: 
26534:   const staleBusinessEndpointPattern =
26535:     /(\/api\/aion\/business\/(?:brand-foundation|boardroom|container-bindings)\/)(costa-conexion|costa_conexion|costaconexion|costa-connection|costa_connection|costa-conection|costa_conection|costa-conextion|costa_conextion)(?=\/|$|\?|#)/i;
26536: 
```

### Around line 26448: `window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"`

```js
26403:    * Otherwise it reads the registered business information form.
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
26501: 
26502:   if (
26503:     registeredBusinessId &&
26504:     registeredBusinessId !== "business_not_registered" &&
26505:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(registeredBusinessId))
26506:   ) {
26507:     return registeredBusinessId;
26508:   }
26509: 
26510:   const safeCandidate = String(candidate || "")
26511:     .trim()
26512:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26513:     || "business_not_registered";
26514: 
26515:   if (
26516:     safeCandidate &&
26517:     safeCandidate !== "business_not_registered" &&
26518:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(safeCandidate))
26519:   ) {
26520:     return safeCandidate;
26521:   }
26522: 
26523:   return "business_not_registered";
26524: }
26525: /* END AION BUSINESS ENDPOINT ID LOCK 20260630 */
26526: 
26527: 
26528: 
26529: /* AION BUSINESS ENDPOINT FETCH GUARD 20260630: block stale demo business endpoint calls */
26530: function rewriteAionStaleBusinessEndpointUrl(url = "") {
26531:   const raw = String(url || "");
26532:   if (!raw) return raw;
26533: 
26534:   const staleBusinessEndpointPattern =
26535:     /(\/api\/aion\/business\/(?:brand-foundation|boardroom|container-bindings)\/)(costa-conexion|costa_conexion|costaconexion|costa-connection|costa_connection|costa-conection|costa_conection|costa-conextion|costa_conextion)(?=\/|$|\?|#)/i;
26536: 
26537:   if (!staleBusinessEndpointPattern.test(raw)) {
```

### Around line 26449: `? window.__aionWorkflowGraph?.business_container`

```js
26404:    */
26405:   const fromGoalLoop =
26406:     window.__aionGoalLoopWorkflowGraph?.goal_loop_contract?.business_name ||
26407:     window.__aionGoalLoopCanvasContract?.business_name ||
26408:     window.__aionWorkflowGraph?.goal_loop_contract?.business_name ||
26409:     window.__aionGoalLoopCanvasContract?.business_id ||
26410:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26411:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26412:     (
26413:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26414:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26415:         ? window.__aionWorkflowGraph?.business_container
26416:         : ""
26417:     );
26418: 
26419:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26420:     return String(fromGoalLoop || "Business not registered");
26421:   }
26422: 
26423:   const identity =
26424:     typeof getAionRegisteredBusinessIdentity === "function"
26425:       ? getAionRegisteredBusinessIdentity()
26426:       : { business_name: "Business not registered", business_id: "business_not_registered" };
26427: 
26428:   return String(
26429:     identity.business_name ||
26430:     identity.business_id ||
26431:     getAionWorkflowBusinessContainerId() ||
26432:     "Business not registered",
26433:   );
26434: }
26435: 
26436: function getAionWorkflowBusinessContainerId() {
26437:   /*
26438:    * Active Goal Loop graph identity wins only if it is not stale demo identity.
26439:    * Otherwise the business identity must come from the registered business
26440:    * information form. Legacy workspace ids are last-resort compatibility only.
26441:    */
26442:   const fromGoalLoop =
26443:     window.__aionGoalLoopWorkflowGraph?.business_container ||
26444:     window.__aionGoalLoopCanvasContract?.business_id ||
26445:     window.__aionWorkflowGraph?.goal_loop_contract?.business_id ||
26446:     (
26447:       window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
26448:       window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
26449:         ? window.__aionWorkflowGraph?.business_container
26450:         : ""
26451:     );
26452: 
26453:   if (fromGoalLoop && !isAionLegacyDemoBusinessIdentity(fromGoalLoop)) {
26454:     return String(fromGoalLoop)
26455:       .trim()
26456:       .replace(/[^a-zA-Z0-9_-]/g, "_")
26457:       || "business_not_registered";
26458:   }
26459: 
26460:   const identity =
26461:     typeof getAionRegisteredBusinessIdentity === "function"
26462:       ? getAionRegisteredBusinessIdentity()
26463:       : { business_id: "business_not_registered" };
26464: 
26465:   const fromRegisteredBusiness = identity.business_id;
26466: 
26467:   const fromLegacyWorkspace =
26468:     window.__aionWorkspaceId ||
26469:     window.__aionBusinessContainerId ||
26470:     window.__aionWorkflowBusinessContainerId;
26471: 
26472:   const resolved = String(fromRegisteredBusiness || fromLegacyWorkspace || "business_not_registered")
26473:     .trim()
26474:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26475:     || "business_not_registered";
26476: 
26477:   return isAionLegacyDemoBusinessIdentity(resolved) ? "business_not_registered" : resolved;
26478: }
26479: 
26480: 
26481: /* AION BUSINESS ENDPOINT ID LOCK 20260630: registered business resolver for backend business endpoints */
26482: function getAionBackendBusinessEndpointId(candidate = "") {
26483:   const registeredContainer =
26484:     typeof getAionWorkflowBusinessContainerId === "function"
26485:       ? getAionWorkflowBusinessContainerId()
26486:       : "";
26487: 
26488:   const registeredIdentity =
26489:     typeof getAionRegisteredBusinessIdentity === "function"
26490:       ? getAionRegisteredBusinessIdentity()
26491:       : null;
26492: 
26493:   const registeredBusinessId = String(
26494:     registeredContainer ||
26495:     registeredIdentity?.business_id ||
26496:     "business_not_registered"
26497:   )
26498:     .trim()
26499:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26500:     || "business_not_registered";
26501: 
26502:   if (
26503:     registeredBusinessId &&
26504:     registeredBusinessId !== "business_not_registered" &&
26505:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(registeredBusinessId))
26506:   ) {
26507:     return registeredBusinessId;
26508:   }
26509: 
26510:   const safeCandidate = String(candidate || "")
26511:     .trim()
26512:     .replace(/[^a-zA-Z0-9_-]/g, "_")
26513:     || "business_not_registered";
26514: 
26515:   if (
26516:     safeCandidate &&
26517:     safeCandidate !== "business_not_registered" &&
26518:     !(typeof isAionLegacyDemoBusinessIdentity === "function" && isAionLegacyDemoBusinessIdentity(safeCandidate))
26519:   ) {
26520:     return safeCandidate;
26521:   }
26522: 
26523:   return "business_not_registered";
26524: }
26525: /* END AION BUSINESS ENDPOINT ID LOCK 20260630 */
26526: 
26527: 
26528: 
26529: /* AION BUSINESS ENDPOINT FETCH GUARD 20260630: block stale demo business endpoint calls */
26530: function rewriteAionStaleBusinessEndpointUrl(url = "") {
26531:   const raw = String(url || "");
26532:   if (!raw) return raw;
26533: 
26534:   const staleBusinessEndpointPattern =
26535:     /(\/api\/aion\/business\/(?:brand-foundation|boardroom|container-bindings)\/)(costa-conexion|costa_conexion|costaconexion|costa-connection|costa_connection|costa-conection|costa_conection|costa-conextion|costa_conextion)(?=\/|$|\?|#)/i;
26536: 
26537:   if (!staleBusinessEndpointPattern.test(raw)) {
26538:     return raw;
```

### Around line 26703: `if (!nodes.length) return [];`

```js
26658:     title: String(node?.title || "Untitled step"),
26659:     node_type: String(node?.type || "Action"),
26660:     status: String(node?.status || "draft"),
26661:     meta: String(node?.meta || ""),
26662:     position: {
26663:       x: Number(node?.x || 0),
26664:       y: Number(node?.y || 0),
26665:     },
26666:     config: node?.config && typeof node.config === "object" ? node.config : {},
26667:   };
26668: }
26669: 
26670: function isAionWorkflowSyntheticChooseNode(node) {
26671:   if (!node) return false;
26672: 
26673:   const id = String(node.id || "");
26674:   const title = String(node.title || node.label || "").trim().toLowerCase();
26675:   const actionId = String(node.action_id || node.action || node.config?.action_id || "").trim().toLowerCase();
26676: 
26677:   return (
26678:     id === "node_choose_start" ||
26679:     (
26680:       title === "choose" &&
26681:       (!actionId || actionId === "generic.step")
26682:     )
26683:   );
26684: }
26685: 
26686: function orderAionWorkflowNodesForGlyph(graph) {
26687:   const nodes = Array.isArray(graph?.nodes)
26688:     ? graph.nodes.filter((node) => !isAionWorkflowSyntheticChooseNode(node))
26689:     : [];
26690: 
26691:   const syntheticChooseIds = new Set(
26692:     Array.isArray(graph?.nodes)
26693:       ? graph.nodes
26694:           .filter((node) => isAionWorkflowSyntheticChooseNode(node))
26695:           .map((node) => String(node.id))
26696:       : [],
26697:   );
26698: 
26699:   const edges = Array.isArray(graph?.edges)
26700:     ? graph.edges.filter((edge) => !syntheticChooseIds.has(String(edge?.from || "")))
26701:     : [];
26702: 
26703:   if (!nodes.length) return [];
26704: 
26705:   const nodeById = new Map(nodes.map((node) => [String(node.id), node]));
26706:   const incoming = new Map(nodes.map((node) => [String(node.id), 0]));
26707:   const outgoing = new Map(nodes.map((node) => [String(node.id), []]));
26708: 
26709:   for (const edge of edges) {
26710:     const from = String(edge?.from || "");
26711:     const to = String(edge?.to || "");
26712:     if (!nodeById.has(from) || !nodeById.has(to)) continue;
26713:     incoming.set(to, (incoming.get(to) || 0) + 1);
26714:     outgoing.get(from)?.push(to);
26715:   }
26716: 
26717:   const queue = nodes
26718:     .filter((node) => (incoming.get(String(node.id)) || 0) === 0)
26719:     .sort((a, b) => Number(a.x || 0) - Number(b.x || 0));
26720: 
26721:   const ordered = [];
26722:   const seen = new Set();
26723: 
26724:   while (queue.length) {
26725:     const node = queue.shift();
26726:     const id = String(node.id);
26727:     if (seen.has(id)) continue;
26728: 
26729:     seen.add(id);
26730:     ordered.push(node);
26731: 
26732:     const nextIds = (outgoing.get(id) || [])
26733:       .filter((nextId) => !seen.has(nextId))
26734:       .sort((a, b) => Number(nodeById.get(a)?.x || 0) - Number(nodeById.get(b)?.x || 0));
26735: 
26736:     for (const nextId of nextIds) {
26737:       const nextIncoming = Math.max(0, (incoming.get(nextId) || 0) - 1);
26738:       incoming.set(nextId, nextIncoming);
26739:       if (nextIncoming === 0 && nodeById.has(nextId)) {
26740:         queue.push(nodeById.get(nextId));
26741:       }
26742:     }
26743:   }
26744: 
26745:   const remaining = nodes
26746:     .filter((node) => !seen.has(String(node.id)))
26747:     .sort((a, b) => Number(a.x || 0) - Number(b.x || 0));
26748: 
26749:   return [...ordered, ...remaining];
26750: }
26751: 
26752: function collectAionWorkflowRequiredConnectors(graph) {
26753:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
26754: 
26755:   return Array.from(
26756:     new Set(
26757:       nodes
26758:         .map((node) => {
26759:           const config = node?.config && typeof node.config === "object" ? node.config : {};
26760:           return String(config.connector || node.connector || config.app || "").trim();
26761:         })
26762:         .filter(Boolean)
26763:         .filter((connector) => !["logic", "tools", "tool", "flow"].includes(connector.toLowerCase())),
26764:     ),
26765:   );
26766: }
26767: 
26768: function collectAionWorkflowBoardroomEvents(graph) {
26769:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
26770: 
26771:   return Array.from(
26772:     new Set(
26773:       nodes.flatMap((node) => {
26774:         const config = node?.config && typeof node.config === "object" ? node.config : {};
26775:         const declared =
26776:           config.boardroom_events ||
26777:           config.boardroom_event ||
26778:           config.events ||
26779:           node.boardroom_events ||
26780:           [];
26781: 
26782:         if (Array.isArray(declared)) return declared;
26783:         if (typeof declared === "string") {
26784:           return declared
26785:             .split(",")
26786:             .map((item) => item.trim())
26787:             .filter(Boolean);
26788:         }
26789: 
26790:         return [];
26791:       }),
26792:     ),
```

### Around line 26965: `window.__aionWorkflowGraph = glyphGraph;`

```js
26920:           !syntheticIds.has(String(edge?.from || "")) &&
26921:           !syntheticIds.has(String(edge?.to || "")),
26922:       )
26923:     : [];
26924: 
26925:   if (syntheticIds.has(String(window.__aionWorkflowSelectedNodeId || ""))) {
26926:     window.__aionWorkflowSelectedNodeId = graph.nodes[0]?.id || null;
26927:   }
26928: 
26929:   graph.updated_at = new Date().toISOString();
26930:   graph.dirty = true;
26931: 
26932:   return graph;
26933: }
26934: 
26935: function getAionWorkflowDraftState() {
26936:   /*
26937:    * CLEAN TAB GRAPH RESOLVER
26938:    *
26939:    * Main workflow and glyph workflow tabs must never share graph objects.
26940:    * The renderer calls this function, so this is the single source of truth.
26941:    */
26942:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
26943:   const activeGlyphCode = String(
26944:     window.__aionActiveGlyphWorkflowTabCode ||
26945:     window.__aionActiveGlyphWorkflowCode ||
26946:     ""
26947:   ).trim();
26948: 
26949:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
26950:     const store =
26951:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
26952:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
26953:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
26954:         : {};
26955: 
26956:     const glyphGraph =
26957:       store[activeGlyphCode] ||
26958:       store[activeGlyphCode.toUpperCase()] ||
26959:       store[activeGlyphCode.toLowerCase()] ||
26960:       window.__aionOpenedGlyphWorkflowGraph;
26961: 
26962:     if (glyphGraph && typeof glyphGraph === "object") {
26963:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
26964:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
26965:       window.__aionWorkflowGraph = glyphGraph;
26966:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
26967:     }
26968:   }
26969: 
26970:   if (
26971:     window.__aionWorkflowMainGraph &&
26972:     typeof window.__aionWorkflowMainGraph === "object"
26973:   ) {
26974:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26975:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
26976:   }
26977: 
26978:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
26979:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
26980:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
26981:   }
26982: 
26983:   try {
26984:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
26985:     if (raw) {
26986:       const parsed = JSON.parse(raw);
26987:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
26988:         ...getDefaultAionWorkflowDraftState(),
26989:         ...parsed,
26990:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
26991:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
26992:       });
26993:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26994:       return window.__aionWorkflowMainGraph;
26995:     }
26996:   } catch (error) {
26997:     console.warn("[workflow] failed to load draft", error);
26998:   }
26999: 
27000:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
27001:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
27002:   return window.__aionWorkflowMainGraph;
27003: }
27004: 
27005: 
27006: function buildAionWorkflowSavePayload(graph) {
27007:   const safeGraph = graph || getAionWorkflowDraftState();
27008:   const compiledGlyph =
27009:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27010: 
27011:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
27012:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
27013: 
27014:   return {
27015:     schema_version: "aion.workflow_save.v1",
27016:     storage_scope: "business_container",
27017:     business_container:
27018:       compiledGlyph?.workflow?.business_container ||
27019:       safeGraph.business_container ||
27020:       getAionWorkflowBusinessContainerId(),
27021:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27022:     name: safeGraph.name || "Untitled workflow 1",
27023:     status: safeGraph.status || "draft",
27024:     canvas_layout: {
27025:       schema_version: "aion.workflow_canvas_layout.v1",
27026:       coordinate_space: "absolute_canvas_px",
27027:       nodes: nodes.map((node) => ({
27028:         node_id: node.id,
27029:         x: Number(node.x || 0),
27030:         y: Number(node.y || 0),
27031:       })),
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
```

### Around line 26974: `window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;`

```js
26929:   graph.updated_at = new Date().toISOString();
26930:   graph.dirty = true;
26931: 
26932:   return graph;
26933: }
26934: 
26935: function getAionWorkflowDraftState() {
26936:   /*
26937:    * CLEAN TAB GRAPH RESOLVER
26938:    *
26939:    * Main workflow and glyph workflow tabs must never share graph objects.
26940:    * The renderer calls this function, so this is the single source of truth.
26941:    */
26942:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
26943:   const activeGlyphCode = String(
26944:     window.__aionActiveGlyphWorkflowTabCode ||
26945:     window.__aionActiveGlyphWorkflowCode ||
26946:     ""
26947:   ).trim();
26948: 
26949:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
26950:     const store =
26951:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
26952:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
26953:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
26954:         : {};
26955: 
26956:     const glyphGraph =
26957:       store[activeGlyphCode] ||
26958:       store[activeGlyphCode.toUpperCase()] ||
26959:       store[activeGlyphCode.toLowerCase()] ||
26960:       window.__aionOpenedGlyphWorkflowGraph;
26961: 
26962:     if (glyphGraph && typeof glyphGraph === "object") {
26963:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
26964:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
26965:       window.__aionWorkflowGraph = glyphGraph;
26966:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
26967:     }
26968:   }
26969: 
26970:   if (
26971:     window.__aionWorkflowMainGraph &&
26972:     typeof window.__aionWorkflowMainGraph === "object"
26973:   ) {
26974:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26975:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
26976:   }
26977: 
26978:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
26979:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
26980:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
26981:   }
26982: 
26983:   try {
26984:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
26985:     if (raw) {
26986:       const parsed = JSON.parse(raw);
26987:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
26988:         ...getDefaultAionWorkflowDraftState(),
26989:         ...parsed,
26990:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
26991:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
26992:       });
26993:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26994:       return window.__aionWorkflowMainGraph;
26995:     }
26996:   } catch (error) {
26997:     console.warn("[workflow] failed to load draft", error);
26998:   }
26999: 
27000:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
27001:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
27002:   return window.__aionWorkflowMainGraph;
27003: }
27004: 
27005: 
27006: function buildAionWorkflowSavePayload(graph) {
27007:   const safeGraph = graph || getAionWorkflowDraftState();
27008:   const compiledGlyph =
27009:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27010: 
27011:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
27012:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
27013: 
27014:   return {
27015:     schema_version: "aion.workflow_save.v1",
27016:     storage_scope: "business_container",
27017:     business_container:
27018:       compiledGlyph?.workflow?.business_container ||
27019:       safeGraph.business_container ||
27020:       getAionWorkflowBusinessContainerId(),
27021:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27022:     name: safeGraph.name || "Untitled workflow 1",
27023:     status: safeGraph.status || "draft",
27024:     canvas_layout: {
27025:       schema_version: "aion.workflow_canvas_layout.v1",
27026:       coordinate_space: "absolute_canvas_px",
27027:       nodes: nodes.map((node) => ({
27028:         node_id: node.id,
27029:         x: Number(node.x || 0),
27030:         y: Number(node.y || 0),
27031:       })),
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
```

### Around line 26978: `if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {`

```js
26933: }
26934: 
26935: function getAionWorkflowDraftState() {
26936:   /*
26937:    * CLEAN TAB GRAPH RESOLVER
26938:    *
26939:    * Main workflow and glyph workflow tabs must never share graph objects.
26940:    * The renderer calls this function, so this is the single source of truth.
26941:    */
26942:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
26943:   const activeGlyphCode = String(
26944:     window.__aionActiveGlyphWorkflowTabCode ||
26945:     window.__aionActiveGlyphWorkflowCode ||
26946:     ""
26947:   ).trim();
26948: 
26949:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
26950:     const store =
26951:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
26952:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
26953:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
26954:         : {};
26955: 
26956:     const glyphGraph =
26957:       store[activeGlyphCode] ||
26958:       store[activeGlyphCode.toUpperCase()] ||
26959:       store[activeGlyphCode.toLowerCase()] ||
26960:       window.__aionOpenedGlyphWorkflowGraph;
26961: 
26962:     if (glyphGraph && typeof glyphGraph === "object") {
26963:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
26964:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
26965:       window.__aionWorkflowGraph = glyphGraph;
26966:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
26967:     }
26968:   }
26969: 
26970:   if (
26971:     window.__aionWorkflowMainGraph &&
26972:     typeof window.__aionWorkflowMainGraph === "object"
26973:   ) {
26974:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26975:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
26976:   }
26977: 
26978:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
26979:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
26980:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
26981:   }
26982: 
26983:   try {
26984:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
26985:     if (raw) {
26986:       const parsed = JSON.parse(raw);
26987:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
26988:         ...getDefaultAionWorkflowDraftState(),
26989:         ...parsed,
26990:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
26991:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
26992:       });
26993:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26994:       return window.__aionWorkflowMainGraph;
26995:     }
26996:   } catch (error) {
26997:     console.warn("[workflow] failed to load draft", error);
26998:   }
26999: 
27000:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
27001:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
27002:   return window.__aionWorkflowMainGraph;
27003: }
27004: 
27005: 
27006: function buildAionWorkflowSavePayload(graph) {
27007:   const safeGraph = graph || getAionWorkflowDraftState();
27008:   const compiledGlyph =
27009:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27010: 
27011:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
27012:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
27013: 
27014:   return {
27015:     schema_version: "aion.workflow_save.v1",
27016:     storage_scope: "business_container",
27017:     business_container:
27018:       compiledGlyph?.workflow?.business_container ||
27019:       safeGraph.business_container ||
27020:       getAionWorkflowBusinessContainerId(),
27021:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27022:     name: safeGraph.name || "Untitled workflow 1",
27023:     status: safeGraph.status || "draft",
27024:     canvas_layout: {
27025:       schema_version: "aion.workflow_canvas_layout.v1",
27026:       coordinate_space: "absolute_canvas_px",
27027:       nodes: nodes.map((node) => ({
27028:         node_id: node.id,
27029:         x: Number(node.x || 0),
27030:         y: Number(node.y || 0),
27031:       })),
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
```

### Around line 26979: `window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;`

```js
26934: 
26935: function getAionWorkflowDraftState() {
26936:   /*
26937:    * CLEAN TAB GRAPH RESOLVER
26938:    *
26939:    * Main workflow and glyph workflow tabs must never share graph objects.
26940:    * The renderer calls this function, so this is the single source of truth.
26941:    */
26942:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
26943:   const activeGlyphCode = String(
26944:     window.__aionActiveGlyphWorkflowTabCode ||
26945:     window.__aionActiveGlyphWorkflowCode ||
26946:     ""
26947:   ).trim();
26948: 
26949:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
26950:     const store =
26951:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
26952:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
26953:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
26954:         : {};
26955: 
26956:     const glyphGraph =
26957:       store[activeGlyphCode] ||
26958:       store[activeGlyphCode.toUpperCase()] ||
26959:       store[activeGlyphCode.toLowerCase()] ||
26960:       window.__aionOpenedGlyphWorkflowGraph;
26961: 
26962:     if (glyphGraph && typeof glyphGraph === "object") {
26963:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
26964:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
26965:       window.__aionWorkflowGraph = glyphGraph;
26966:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
26967:     }
26968:   }
26969: 
26970:   if (
26971:     window.__aionWorkflowMainGraph &&
26972:     typeof window.__aionWorkflowMainGraph === "object"
26973:   ) {
26974:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26975:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
26976:   }
26977: 
26978:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
26979:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
26980:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
26981:   }
26982: 
26983:   try {
26984:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
26985:     if (raw) {
26986:       const parsed = JSON.parse(raw);
26987:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
26988:         ...getDefaultAionWorkflowDraftState(),
26989:         ...parsed,
26990:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
26991:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
26992:       });
26993:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26994:       return window.__aionWorkflowMainGraph;
26995:     }
26996:   } catch (error) {
26997:     console.warn("[workflow] failed to load draft", error);
26998:   }
26999: 
27000:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
27001:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
27002:   return window.__aionWorkflowMainGraph;
27003: }
27004: 
27005: 
27006: function buildAionWorkflowSavePayload(graph) {
27007:   const safeGraph = graph || getAionWorkflowDraftState();
27008:   const compiledGlyph =
27009:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27010: 
27011:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
27012:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
27013: 
27014:   return {
27015:     schema_version: "aion.workflow_save.v1",
27016:     storage_scope: "business_container",
27017:     business_container:
27018:       compiledGlyph?.workflow?.business_container ||
27019:       safeGraph.business_container ||
27020:       getAionWorkflowBusinessContainerId(),
27021:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27022:     name: safeGraph.name || "Untitled workflow 1",
27023:     status: safeGraph.status || "draft",
27024:     canvas_layout: {
27025:       schema_version: "aion.workflow_canvas_layout.v1",
27026:       coordinate_space: "absolute_canvas_px",
27027:       nodes: nodes.map((node) => ({
27028:         node_id: node.id,
27029:         x: Number(node.x || 0),
27030:         y: Number(node.y || 0),
27031:       })),
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
27068:   const node = nodes.find((item) => item.id === nodeId);
```

### Around line 26980: `return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);`

```js
26935: function getAionWorkflowDraftState() {
26936:   /*
26937:    * CLEAN TAB GRAPH RESOLVER
26938:    *
26939:    * Main workflow and glyph workflow tabs must never share graph objects.
26940:    * The renderer calls this function, so this is the single source of truth.
26941:    */
26942:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
26943:   const activeGlyphCode = String(
26944:     window.__aionActiveGlyphWorkflowTabCode ||
26945:     window.__aionActiveGlyphWorkflowCode ||
26946:     ""
26947:   ).trim();
26948: 
26949:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
26950:     const store =
26951:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
26952:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
26953:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
26954:         : {};
26955: 
26956:     const glyphGraph =
26957:       store[activeGlyphCode] ||
26958:       store[activeGlyphCode.toUpperCase()] ||
26959:       store[activeGlyphCode.toLowerCase()] ||
26960:       window.__aionOpenedGlyphWorkflowGraph;
26961: 
26962:     if (glyphGraph && typeof glyphGraph === "object") {
26963:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
26964:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
26965:       window.__aionWorkflowGraph = glyphGraph;
26966:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
26967:     }
26968:   }
26969: 
26970:   if (
26971:     window.__aionWorkflowMainGraph &&
26972:     typeof window.__aionWorkflowMainGraph === "object"
26973:   ) {
26974:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26975:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
26976:   }
26977: 
26978:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
26979:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
26980:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
26981:   }
26982: 
26983:   try {
26984:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
26985:     if (raw) {
26986:       const parsed = JSON.parse(raw);
26987:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
26988:         ...getDefaultAionWorkflowDraftState(),
26989:         ...parsed,
26990:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
26991:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
26992:       });
26993:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26994:       return window.__aionWorkflowMainGraph;
26995:     }
26996:   } catch (error) {
26997:     console.warn("[workflow] failed to load draft", error);
26998:   }
26999: 
27000:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
27001:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
27002:   return window.__aionWorkflowMainGraph;
27003: }
27004: 
27005: 
27006: function buildAionWorkflowSavePayload(graph) {
27007:   const safeGraph = graph || getAionWorkflowDraftState();
27008:   const compiledGlyph =
27009:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27010: 
27011:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
27012:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
27013: 
27014:   return {
27015:     schema_version: "aion.workflow_save.v1",
27016:     storage_scope: "business_container",
27017:     business_container:
27018:       compiledGlyph?.workflow?.business_container ||
27019:       safeGraph.business_container ||
27020:       getAionWorkflowBusinessContainerId(),
27021:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27022:     name: safeGraph.name || "Untitled workflow 1",
27023:     status: safeGraph.status || "draft",
27024:     canvas_layout: {
27025:       schema_version: "aion.workflow_canvas_layout.v1",
27026:       coordinate_space: "absolute_canvas_px",
27027:       nodes: nodes.map((node) => ({
27028:         node_id: node.id,
27029:         x: Number(node.x || 0),
27030:         y: Number(node.y || 0),
27031:       })),
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
27068:   const node = nodes.find((item) => item.id === nodeId);
27069: 
```

### Around line 26993: `window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;`

```js
26948: 
26949:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
26950:     const store =
26951:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
26952:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
26953:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
26954:         : {};
26955: 
26956:     const glyphGraph =
26957:       store[activeGlyphCode] ||
26958:       store[activeGlyphCode.toUpperCase()] ||
26959:       store[activeGlyphCode.toLowerCase()] ||
26960:       window.__aionOpenedGlyphWorkflowGraph;
26961: 
26962:     if (glyphGraph && typeof glyphGraph === "object") {
26963:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
26964:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
26965:       window.__aionWorkflowGraph = glyphGraph;
26966:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
26967:     }
26968:   }
26969: 
26970:   if (
26971:     window.__aionWorkflowMainGraph &&
26972:     typeof window.__aionWorkflowMainGraph === "object"
26973:   ) {
26974:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26975:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
26976:   }
26977: 
26978:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
26979:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
26980:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
26981:   }
26982: 
26983:   try {
26984:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
26985:     if (raw) {
26986:       const parsed = JSON.parse(raw);
26987:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
26988:         ...getDefaultAionWorkflowDraftState(),
26989:         ...parsed,
26990:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
26991:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
26992:       });
26993:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26994:       return window.__aionWorkflowMainGraph;
26995:     }
26996:   } catch (error) {
26997:     console.warn("[workflow] failed to load draft", error);
26998:   }
26999: 
27000:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
27001:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
27002:   return window.__aionWorkflowMainGraph;
27003: }
27004: 
27005: 
27006: function buildAionWorkflowSavePayload(graph) {
27007:   const safeGraph = graph || getAionWorkflowDraftState();
27008:   const compiledGlyph =
27009:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27010: 
27011:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
27012:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
27013: 
27014:   return {
27015:     schema_version: "aion.workflow_save.v1",
27016:     storage_scope: "business_container",
27017:     business_container:
27018:       compiledGlyph?.workflow?.business_container ||
27019:       safeGraph.business_container ||
27020:       getAionWorkflowBusinessContainerId(),
27021:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27022:     name: safeGraph.name || "Untitled workflow 1",
27023:     status: safeGraph.status || "draft",
27024:     canvas_layout: {
27025:       schema_version: "aion.workflow_canvas_layout.v1",
27026:       coordinate_space: "absolute_canvas_px",
27027:       nodes: nodes.map((node) => ({
27028:         node_id: node.id,
27029:         x: Number(node.x || 0),
27030:         y: Number(node.y || 0),
27031:       })),
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
27068:   const node = nodes.find((item) => item.id === nodeId);
27069: 
27070:   if (!node) return null;
27071: 
27072:   const config = {
27073:     ...(node.config || {}),
27074:     ...pending,
27075:   };
27076: 
27077:   window.__aionWorkflowGraph = {
27078:     ...graph,
27079:     nodes: nodes.map((item) =>
27080:       item.id === nodeId
27081:         ? {
27082:             ...item,
```

### Around line 27001: `window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;`

```js
26956:     const glyphGraph =
26957:       store[activeGlyphCode] ||
26958:       store[activeGlyphCode.toUpperCase()] ||
26959:       store[activeGlyphCode.toLowerCase()] ||
26960:       window.__aionOpenedGlyphWorkflowGraph;
26961: 
26962:     if (glyphGraph && typeof glyphGraph === "object") {
26963:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
26964:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
26965:       window.__aionWorkflowGraph = glyphGraph;
26966:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
26967:     }
26968:   }
26969: 
26970:   if (
26971:     window.__aionWorkflowMainGraph &&
26972:     typeof window.__aionWorkflowMainGraph === "object"
26973:   ) {
26974:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26975:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
26976:   }
26977: 
26978:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
26979:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
26980:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
26981:   }
26982: 
26983:   try {
26984:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
26985:     if (raw) {
26986:       const parsed = JSON.parse(raw);
26987:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
26988:         ...getDefaultAionWorkflowDraftState(),
26989:         ...parsed,
26990:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
26991:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
26992:       });
26993:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
26994:       return window.__aionWorkflowMainGraph;
26995:     }
26996:   } catch (error) {
26997:     console.warn("[workflow] failed to load draft", error);
26998:   }
26999: 
27000:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
27001:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
27002:   return window.__aionWorkflowMainGraph;
27003: }
27004: 
27005: 
27006: function buildAionWorkflowSavePayload(graph) {
27007:   const safeGraph = graph || getAionWorkflowDraftState();
27008:   const compiledGlyph =
27009:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27010: 
27011:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
27012:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
27013: 
27014:   return {
27015:     schema_version: "aion.workflow_save.v1",
27016:     storage_scope: "business_container",
27017:     business_container:
27018:       compiledGlyph?.workflow?.business_container ||
27019:       safeGraph.business_container ||
27020:       getAionWorkflowBusinessContainerId(),
27021:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27022:     name: safeGraph.name || "Untitled workflow 1",
27023:     status: safeGraph.status || "draft",
27024:     canvas_layout: {
27025:       schema_version: "aion.workflow_canvas_layout.v1",
27026:       coordinate_space: "absolute_canvas_px",
27027:       nodes: nodes.map((node) => ({
27028:         node_id: node.id,
27029:         x: Number(node.x || 0),
27030:         y: Number(node.y || 0),
27031:       })),
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
27068:   const node = nodes.find((item) => item.id === nodeId);
27069: 
27070:   if (!node) return null;
27071: 
27072:   const config = {
27073:     ...(node.config || {}),
27074:     ...pending,
27075:   };
27076: 
27077:   window.__aionWorkflowGraph = {
27078:     ...graph,
27079:     nodes: nodes.map((item) =>
27080:       item.id === nodeId
27081:         ? {
27082:             ...item,
27083:             config,
27084:           }
27085:         : item,
27086:     ),
27087:   };
27088: 
27089:   compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
27090:   persistAionWorkflowDraftState();
```

### Around line 27065: `const graph = getAionWorkflowDraftState();`

```js
27020:       getAionWorkflowBusinessContainerId(),
27021:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27022:     name: safeGraph.name || "Untitled workflow 1",
27023:     status: safeGraph.status || "draft",
27024:     canvas_layout: {
27025:       schema_version: "aion.workflow_canvas_layout.v1",
27026:       coordinate_space: "absolute_canvas_px",
27027:       nodes: nodes.map((node) => ({
27028:         node_id: node.id,
27029:         x: Number(node.x || 0),
27030:         y: Number(node.y || 0),
27031:       })),
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
27068:   const node = nodes.find((item) => item.id === nodeId);
27069: 
27070:   if (!node) return null;
27071: 
27072:   const config = {
27073:     ...(node.config || {}),
27074:     ...pending,
27075:   };
27076: 
27077:   window.__aionWorkflowGraph = {
27078:     ...graph,
27079:     nodes: nodes.map((item) =>
27080:       item.id === nodeId
27081:         ? {
27082:             ...item,
27083:             config,
27084:           }
27085:         : item,
27086:     ),
27087:   };
27088: 
27089:   compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
27090:   persistAionWorkflowDraftState();
27091: 
27092:   return config;
27093: }
27094: 
27095: 
27096: function syncAionWorkflowInspectorInputsToGraph() {
27097:   const graph = getAionWorkflowDraftState();
27098:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27099: 
27100:   document
27101:     .querySelectorAll("[data-aion-workflow-node-config-input]")
27102:     .forEach((input) => {
27103:       const nodeId = input.getAttribute("data-aion-workflow-node-id");
27104:       const key = input.getAttribute("data-aion-workflow-node-config-input");
27105: 
27106:       if (!nodeId || !key) return;
27107: 
27108:       const node = nodes.find((item) => item.id === nodeId);
27109:       if (!node) return;
27110: 
27111:       node.config = {
27112:         ...(node.config || {}),
27113:         [key]: input.value,
27114:       };
27115:     });
27116: 
27117:   window["__aionWorkflowGraph"] = graph;
27118:   compileAndAttachAionWorkflowGlyph(graph);
27119: 
27120:   return graph;
27121: }
27122: 
27123: 
27124: function persistAionWorkflowDraftState() {
27125:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
27126:   const activeGlyphCode = String(
27127:     window.__aionActiveGlyphWorkflowTabCode ||
27128:     window.__aionActiveGlyphWorkflowCode ||
27129:     ""
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
```

### Around line 27077: `window.__aionWorkflowGraph = {`

```js
27032:       edges: edges.map((edge) => ({
27033:         from: edge.from,
27034:         to: edge.to,
27035:         condition: edge.condition || "success",
27036:       })),
27037:     },
27038:     graph: {
27039:       nodes,
27040:       edges,
27041:     },
27042:     compiled_glyph: compiledGlyph,
27043:     saved_at: new Date().toISOString(),
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
27068:   const node = nodes.find((item) => item.id === nodeId);
27069: 
27070:   if (!node) return null;
27071: 
27072:   const config = {
27073:     ...(node.config || {}),
27074:     ...pending,
27075:   };
27076: 
27077:   window.__aionWorkflowGraph = {
27078:     ...graph,
27079:     nodes: nodes.map((item) =>
27080:       item.id === nodeId
27081:         ? {
27082:             ...item,
27083:             config,
27084:           }
27085:         : item,
27086:     ),
27087:   };
27088: 
27089:   compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
27090:   persistAionWorkflowDraftState();
27091: 
27092:   return config;
27093: }
27094: 
27095: 
27096: function syncAionWorkflowInspectorInputsToGraph() {
27097:   const graph = getAionWorkflowDraftState();
27098:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27099: 
27100:   document
27101:     .querySelectorAll("[data-aion-workflow-node-config-input]")
27102:     .forEach((input) => {
27103:       const nodeId = input.getAttribute("data-aion-workflow-node-id");
27104:       const key = input.getAttribute("data-aion-workflow-node-config-input");
27105: 
27106:       if (!nodeId || !key) return;
27107: 
27108:       const node = nodes.find((item) => item.id === nodeId);
27109:       if (!node) return;
27110: 
27111:       node.config = {
27112:         ...(node.config || {}),
27113:         [key]: input.value,
27114:       };
27115:     });
27116: 
27117:   window["__aionWorkflowGraph"] = graph;
27118:   compileAndAttachAionWorkflowGlyph(graph);
27119: 
27120:   return graph;
27121: }
27122: 
27123: 
27124: function persistAionWorkflowDraftState() {
27125:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
27126:   const activeGlyphCode = String(
27127:     window.__aionActiveGlyphWorkflowTabCode ||
27128:     window.__aionActiveGlyphWorkflowCode ||
27129:     ""
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
```

### Around line 27089: `compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);`

```js
27044:   };
27045: }
27046: 
27047: function getAionWorkflowPendingNodeConfig(nodeId) {
27048:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27049:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
27050: }
27051: 
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
27068:   const node = nodes.find((item) => item.id === nodeId);
27069: 
27070:   if (!node) return null;
27071: 
27072:   const config = {
27073:     ...(node.config || {}),
27074:     ...pending,
27075:   };
27076: 
27077:   window.__aionWorkflowGraph = {
27078:     ...graph,
27079:     nodes: nodes.map((item) =>
27080:       item.id === nodeId
27081:         ? {
27082:             ...item,
27083:             config,
27084:           }
27085:         : item,
27086:     ),
27087:   };
27088: 
27089:   compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
27090:   persistAionWorkflowDraftState();
27091: 
27092:   return config;
27093: }
27094: 
27095: 
27096: function syncAionWorkflowInspectorInputsToGraph() {
27097:   const graph = getAionWorkflowDraftState();
27098:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27099: 
27100:   document
27101:     .querySelectorAll("[data-aion-workflow-node-config-input]")
27102:     .forEach((input) => {
27103:       const nodeId = input.getAttribute("data-aion-workflow-node-id");
27104:       const key = input.getAttribute("data-aion-workflow-node-config-input");
27105: 
27106:       if (!nodeId || !key) return;
27107: 
27108:       const node = nodes.find((item) => item.id === nodeId);
27109:       if (!node) return;
27110: 
27111:       node.config = {
27112:         ...(node.config || {}),
27113:         [key]: input.value,
27114:       };
27115:     });
27116: 
27117:   window["__aionWorkflowGraph"] = graph;
27118:   compileAndAttachAionWorkflowGlyph(graph);
27119: 
27120:   return graph;
27121: }
27122: 
27123: 
27124: function persistAionWorkflowDraftState() {
27125:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
27126:   const activeGlyphCode = String(
27127:     window.__aionActiveGlyphWorkflowTabCode ||
27128:     window.__aionActiveGlyphWorkflowCode ||
27129:     ""
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
27167: 
27168:   return compactGraph;
27169: }
27170: 
27171: 
27172: 
27173: 
27174: function markAionWorkflowDraftDirty(reason = "updated") {
27175:   const graph = getAionWorkflowDraftState();
27176:   graph.dirty = true;
27177:   graph.dirty_reason = reason;
27178:   graph.saved_at = graph.saved_at || null;
```

### Around line 27097: `const graph = getAionWorkflowDraftState();`

```js
27052: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
27053:   if (!nodeId || !key) return;
27054: 
27055:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
27056:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
27057:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
27058:     [key]: value,
27059:   };
27060: }
27061: 
27062: function applyAionWorkflowPendingNodeConfig(nodeId) {
27063:   if (!nodeId) return null;
27064: 
27065:   const graph = getAionWorkflowDraftState();
27066:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27067:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
27068:   const node = nodes.find((item) => item.id === nodeId);
27069: 
27070:   if (!node) return null;
27071: 
27072:   const config = {
27073:     ...(node.config || {}),
27074:     ...pending,
27075:   };
27076: 
27077:   window.__aionWorkflowGraph = {
27078:     ...graph,
27079:     nodes: nodes.map((item) =>
27080:       item.id === nodeId
27081:         ? {
27082:             ...item,
27083:             config,
27084:           }
27085:         : item,
27086:     ),
27087:   };
27088: 
27089:   compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
27090:   persistAionWorkflowDraftState();
27091: 
27092:   return config;
27093: }
27094: 
27095: 
27096: function syncAionWorkflowInspectorInputsToGraph() {
27097:   const graph = getAionWorkflowDraftState();
27098:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27099: 
27100:   document
27101:     .querySelectorAll("[data-aion-workflow-node-config-input]")
27102:     .forEach((input) => {
27103:       const nodeId = input.getAttribute("data-aion-workflow-node-id");
27104:       const key = input.getAttribute("data-aion-workflow-node-config-input");
27105: 
27106:       if (!nodeId || !key) return;
27107: 
27108:       const node = nodes.find((item) => item.id === nodeId);
27109:       if (!node) return;
27110: 
27111:       node.config = {
27112:         ...(node.config || {}),
27113:         [key]: input.value,
27114:       };
27115:     });
27116: 
27117:   window["__aionWorkflowGraph"] = graph;
27118:   compileAndAttachAionWorkflowGlyph(graph);
27119: 
27120:   return graph;
27121: }
27122: 
27123: 
27124: function persistAionWorkflowDraftState() {
27125:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
27126:   const activeGlyphCode = String(
27127:     window.__aionActiveGlyphWorkflowTabCode ||
27128:     window.__aionActiveGlyphWorkflowCode ||
27129:     ""
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
27167: 
27168:   return compactGraph;
27169: }
27170: 
27171: 
27172: 
27173: 
27174: function markAionWorkflowDraftDirty(reason = "updated") {
27175:   const graph = getAionWorkflowDraftState();
27176:   graph.dirty = true;
27177:   graph.dirty_reason = reason;
27178:   graph.saved_at = graph.saved_at || null;
27179:   compileAndAttachAionWorkflowGlyph(graph);
27180:   window["__aionWorkflowGraph"] = graph;
27181:   persistAionWorkflowDraftState();
27182:   return graph;
27183: }
27184: 
27185: function getAionWorkflowSaveStatus(graph) {
27186:   const safeGraph = graph || getAionWorkflowDraftState();
```

### Around line 27117: `window["__aionWorkflowGraph"] = graph;`

```js
27072:   const config = {
27073:     ...(node.config || {}),
27074:     ...pending,
27075:   };
27076: 
27077:   window.__aionWorkflowGraph = {
27078:     ...graph,
27079:     nodes: nodes.map((item) =>
27080:       item.id === nodeId
27081:         ? {
27082:             ...item,
27083:             config,
27084:           }
27085:         : item,
27086:     ),
27087:   };
27088: 
27089:   compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
27090:   persistAionWorkflowDraftState();
27091: 
27092:   return config;
27093: }
27094: 
27095: 
27096: function syncAionWorkflowInspectorInputsToGraph() {
27097:   const graph = getAionWorkflowDraftState();
27098:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27099: 
27100:   document
27101:     .querySelectorAll("[data-aion-workflow-node-config-input]")
27102:     .forEach((input) => {
27103:       const nodeId = input.getAttribute("data-aion-workflow-node-id");
27104:       const key = input.getAttribute("data-aion-workflow-node-config-input");
27105: 
27106:       if (!nodeId || !key) return;
27107: 
27108:       const node = nodes.find((item) => item.id === nodeId);
27109:       if (!node) return;
27110: 
27111:       node.config = {
27112:         ...(node.config || {}),
27113:         [key]: input.value,
27114:       };
27115:     });
27116: 
27117:   window["__aionWorkflowGraph"] = graph;
27118:   compileAndAttachAionWorkflowGlyph(graph);
27119: 
27120:   return graph;
27121: }
27122: 
27123: 
27124: function persistAionWorkflowDraftState() {
27125:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
27126:   const activeGlyphCode = String(
27127:     window.__aionActiveGlyphWorkflowTabCode ||
27128:     window.__aionActiveGlyphWorkflowCode ||
27129:     ""
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
27167: 
27168:   return compactGraph;
27169: }
27170: 
27171: 
27172: 
27173: 
27174: function markAionWorkflowDraftDirty(reason = "updated") {
27175:   const graph = getAionWorkflowDraftState();
27176:   graph.dirty = true;
27177:   graph.dirty_reason = reason;
27178:   graph.saved_at = graph.saved_at || null;
27179:   compileAndAttachAionWorkflowGlyph(graph);
27180:   window["__aionWorkflowGraph"] = graph;
27181:   persistAionWorkflowDraftState();
27182:   return graph;
27183: }
27184: 
27185: function getAionWorkflowSaveStatus(graph) {
27186:   const safeGraph = graph || getAionWorkflowDraftState();
27187:   const compiled = safeGraph?.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27188:   const dirty = Boolean(safeGraph?.dirty);
27189:   const savedAt = safeGraph?.saved_at || null;
27190: 
27191:   if (dirty) {
27192:     return {
27193:       label: "Unsaved",
27194:       className: "is-unsaved",
27195:       detail: "Changes not saved",
27196:     };
27197:   }
27198: 
27199:   if (savedAt) {
27200:     return {
27201:       label: "Saved",
27202:       className: "is-saved",
27203:       detail: `Saved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
27204:     };
27205:   }
27206: 
```

### Around line 27132: `const graph =`

```js
27087:   };
27088: 
27089:   compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
27090:   persistAionWorkflowDraftState();
27091: 
27092:   return config;
27093: }
27094: 
27095: 
27096: function syncAionWorkflowInspectorInputsToGraph() {
27097:   const graph = getAionWorkflowDraftState();
27098:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27099: 
27100:   document
27101:     .querySelectorAll("[data-aion-workflow-node-config-input]")
27102:     .forEach((input) => {
27103:       const nodeId = input.getAttribute("data-aion-workflow-node-id");
27104:       const key = input.getAttribute("data-aion-workflow-node-config-input");
27105: 
27106:       if (!nodeId || !key) return;
27107: 
27108:       const node = nodes.find((item) => item.id === nodeId);
27109:       if (!node) return;
27110: 
27111:       node.config = {
27112:         ...(node.config || {}),
27113:         [key]: input.value,
27114:       };
27115:     });
27116: 
27117:   window["__aionWorkflowGraph"] = graph;
27118:   compileAndAttachAionWorkflowGlyph(graph);
27119: 
27120:   return graph;
27121: }
27122: 
27123: 
27124: function persistAionWorkflowDraftState() {
27125:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
27126:   const activeGlyphCode = String(
27127:     window.__aionActiveGlyphWorkflowTabCode ||
27128:     window.__aionActiveGlyphWorkflowCode ||
27129:     ""
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
27167: 
27168:   return compactGraph;
27169: }
27170: 
27171: 
27172: 
27173: 
27174: function markAionWorkflowDraftDirty(reason = "updated") {
27175:   const graph = getAionWorkflowDraftState();
27176:   graph.dirty = true;
27177:   graph.dirty_reason = reason;
27178:   graph.saved_at = graph.saved_at || null;
27179:   compileAndAttachAionWorkflowGlyph(graph);
27180:   window["__aionWorkflowGraph"] = graph;
27181:   persistAionWorkflowDraftState();
27182:   return graph;
27183: }
27184: 
27185: function getAionWorkflowSaveStatus(graph) {
27186:   const safeGraph = graph || getAionWorkflowDraftState();
27187:   const compiled = safeGraph?.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27188:   const dirty = Boolean(safeGraph?.dirty);
27189:   const savedAt = safeGraph?.saved_at || null;
27190: 
27191:   if (dirty) {
27192:     return {
27193:       label: "Unsaved",
27194:       className: "is-unsaved",
27195:       detail: "Changes not saved",
27196:     };
27197:   }
27198: 
27199:   if (savedAt) {
27200:     return {
27201:       label: "Saved",
27202:       className: "is-saved",
27203:       detail: `Saved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
27204:     };
27205:   }
27206: 
27207:   return {
27208:     label: "Draft",
27209:     className: "is-draft",
27210:     detail: "Local draft",
27211:   };
27212: }
27213: 
27214: async function loadAionWorkflowFromBusinessContainer({
27215:   businessContainer = "",
27216:   workflowId = createAionWorkflowId(),
27217: } = {}) {
27218:   const apiBase =
27219:     state.apiBase ||
27220:     state.desktopApiBase ||
27221:     window.AION_API_BASE ||
```

### Around line 27155: `window.__aionWorkflowGraph = compactGraph;`

```js
27110: 
27111:       node.config = {
27112:         ...(node.config || {}),
27113:         [key]: input.value,
27114:       };
27115:     });
27116: 
27117:   window["__aionWorkflowGraph"] = graph;
27118:   compileAndAttachAionWorkflowGlyph(graph);
27119: 
27120:   return graph;
27121: }
27122: 
27123: 
27124: function persistAionWorkflowDraftState() {
27125:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
27126:   const activeGlyphCode = String(
27127:     window.__aionActiveGlyphWorkflowTabCode ||
27128:     window.__aionActiveGlyphWorkflowCode ||
27129:     ""
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
27167: 
27168:   return compactGraph;
27169: }
27170: 
27171: 
27172: 
27173: 
27174: function markAionWorkflowDraftDirty(reason = "updated") {
27175:   const graph = getAionWorkflowDraftState();
27176:   graph.dirty = true;
27177:   graph.dirty_reason = reason;
27178:   graph.saved_at = graph.saved_at || null;
27179:   compileAndAttachAionWorkflowGlyph(graph);
27180:   window["__aionWorkflowGraph"] = graph;
27181:   persistAionWorkflowDraftState();
27182:   return graph;
27183: }
27184: 
27185: function getAionWorkflowSaveStatus(graph) {
27186:   const safeGraph = graph || getAionWorkflowDraftState();
27187:   const compiled = safeGraph?.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27188:   const dirty = Boolean(safeGraph?.dirty);
27189:   const savedAt = safeGraph?.saved_at || null;
27190: 
27191:   if (dirty) {
27192:     return {
27193:       label: "Unsaved",
27194:       className: "is-unsaved",
27195:       detail: "Changes not saved",
27196:     };
27197:   }
27198: 
27199:   if (savedAt) {
27200:     return {
27201:       label: "Saved",
27202:       className: "is-saved",
27203:       detail: `Saved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
27204:     };
27205:   }
27206: 
27207:   return {
27208:     label: "Draft",
27209:     className: "is-draft",
27210:     detail: "Local draft",
27211:   };
27212: }
27213: 
27214: async function loadAionWorkflowFromBusinessContainer({
27215:   businessContainer = "",
27216:   workflowId = createAionWorkflowId(),
27217: } = {}) {
27218:   const apiBase =
27219:     state.apiBase ||
27220:     state.desktopApiBase ||
27221:     window.AION_API_BASE ||
27222:     "http://127.0.0.1:8080";
27223: 
27224:   const safeBusiness = String(businessContainer || getAionWorkflowBusinessContainerId()).trim() || getAionWorkflowBusinessContainerId();
27225:   const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
27226: 
27227:   const response = await fetch(
27228:     `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
27229:   );
27230: 
27231:   if (!response.ok) {
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
```

### Around line 27160: `window.__aionWorkflowGraph = compactGraph;`

```js
27115:     });
27116: 
27117:   window["__aionWorkflowGraph"] = graph;
27118:   compileAndAttachAionWorkflowGlyph(graph);
27119: 
27120:   return graph;
27121: }
27122: 
27123: 
27124: function persistAionWorkflowDraftState() {
27125:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
27126:   const activeGlyphCode = String(
27127:     window.__aionActiveGlyphWorkflowTabCode ||
27128:     window.__aionActiveGlyphWorkflowCode ||
27129:     ""
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
27167: 
27168:   return compactGraph;
27169: }
27170: 
27171: 
27172: 
27173: 
27174: function markAionWorkflowDraftDirty(reason = "updated") {
27175:   const graph = getAionWorkflowDraftState();
27176:   graph.dirty = true;
27177:   graph.dirty_reason = reason;
27178:   graph.saved_at = graph.saved_at || null;
27179:   compileAndAttachAionWorkflowGlyph(graph);
27180:   window["__aionWorkflowGraph"] = graph;
27181:   persistAionWorkflowDraftState();
27182:   return graph;
27183: }
27184: 
27185: function getAionWorkflowSaveStatus(graph) {
27186:   const safeGraph = graph || getAionWorkflowDraftState();
27187:   const compiled = safeGraph?.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27188:   const dirty = Boolean(safeGraph?.dirty);
27189:   const savedAt = safeGraph?.saved_at || null;
27190: 
27191:   if (dirty) {
27192:     return {
27193:       label: "Unsaved",
27194:       className: "is-unsaved",
27195:       detail: "Changes not saved",
27196:     };
27197:   }
27198: 
27199:   if (savedAt) {
27200:     return {
27201:       label: "Saved",
27202:       className: "is-saved",
27203:       detail: `Saved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
27204:     };
27205:   }
27206: 
27207:   return {
27208:     label: "Draft",
27209:     className: "is-draft",
27210:     detail: "Local draft",
27211:   };
27212: }
27213: 
27214: async function loadAionWorkflowFromBusinessContainer({
27215:   businessContainer = "",
27216:   workflowId = createAionWorkflowId(),
27217: } = {}) {
27218:   const apiBase =
27219:     state.apiBase ||
27220:     state.desktopApiBase ||
27221:     window.AION_API_BASE ||
27222:     "http://127.0.0.1:8080";
27223: 
27224:   const safeBusiness = String(businessContainer || getAionWorkflowBusinessContainerId()).trim() || getAionWorkflowBusinessContainerId();
27225:   const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
27226: 
27227:   const response = await fetch(
27228:     `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
27229:   );
27230: 
27231:   if (!response.ok) {
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
```

### Around line 27175: `const graph = getAionWorkflowDraftState();`

```js
27130:   ).trim();
27131: 
27132:   const graph =
27133:     activeTab === "glyph" && window.__aionOpenedGlyphWorkflowGraph
27134:       ? window.__aionOpenedGlyphWorkflowGraph
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
27167: 
27168:   return compactGraph;
27169: }
27170: 
27171: 
27172: 
27173: 
27174: function markAionWorkflowDraftDirty(reason = "updated") {
27175:   const graph = getAionWorkflowDraftState();
27176:   graph.dirty = true;
27177:   graph.dirty_reason = reason;
27178:   graph.saved_at = graph.saved_at || null;
27179:   compileAndAttachAionWorkflowGlyph(graph);
27180:   window["__aionWorkflowGraph"] = graph;
27181:   persistAionWorkflowDraftState();
27182:   return graph;
27183: }
27184: 
27185: function getAionWorkflowSaveStatus(graph) {
27186:   const safeGraph = graph || getAionWorkflowDraftState();
27187:   const compiled = safeGraph?.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27188:   const dirty = Boolean(safeGraph?.dirty);
27189:   const savedAt = safeGraph?.saved_at || null;
27190: 
27191:   if (dirty) {
27192:     return {
27193:       label: "Unsaved",
27194:       className: "is-unsaved",
27195:       detail: "Changes not saved",
27196:     };
27197:   }
27198: 
27199:   if (savedAt) {
27200:     return {
27201:       label: "Saved",
27202:       className: "is-saved",
27203:       detail: `Saved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
27204:     };
27205:   }
27206: 
27207:   return {
27208:     label: "Draft",
27209:     className: "is-draft",
27210:     detail: "Local draft",
27211:   };
27212: }
27213: 
27214: async function loadAionWorkflowFromBusinessContainer({
27215:   businessContainer = "",
27216:   workflowId = createAionWorkflowId(),
27217: } = {}) {
27218:   const apiBase =
27219:     state.apiBase ||
27220:     state.desktopApiBase ||
27221:     window.AION_API_BASE ||
27222:     "http://127.0.0.1:8080";
27223: 
27224:   const safeBusiness = String(businessContainer || getAionWorkflowBusinessContainerId()).trim() || getAionWorkflowBusinessContainerId();
27225:   const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
27226: 
27227:   const response = await fetch(
27228:     `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
27229:   );
27230: 
27231:   if (!response.ok) {
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
27250:     compiled_glyph: record.compiled_glyph || null,
27251:     backend_saved_at: record.updated_at || "",
27252:     backend_storage_path: record.path || "",
27253:     dirty: false,
27254:   };
27255: 
27256:   compileAndAttachAionWorkflowGlyph(loadedGraph);
27257:   window.__aionWorkflowGraph = loadedGraph;
27258:   persistAionWorkflowDraftState();
27259: 
27260:   return loadedGraph;
27261: }
27262: 
27263: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
27264:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
```

### Around line 27180: `window["__aionWorkflowGraph"] = graph;`

```js
27135:       : getAionWorkflowDraftState();
27136: 
27137:   const compactGraph = {
27138:     ...graph,
27139:     nodes: Array.isArray(graph.nodes) ? graph.nodes.map((node) => ({ ...node })) : [],
27140:     edges: Array.isArray(graph.edges) ? graph.edges.map((edge) => ({ ...edge })) : [],
27141:     updated_at: new Date().toISOString(),
27142:   };
27143: 
27144:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
27145:     compactGraph.glyph_code = compactGraph.glyph_code || activeGlyphCode;
27146: 
27147:     window.__aionOpenedGlyphWorkflowGraphsByCode =
27148:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
27149:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
27150:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
27151:         : {};
27152: 
27153:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
27154:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
27155:     window.__aionWorkflowGraph = compactGraph;
27156:     return compactGraph;
27157:   }
27158: 
27159:   window.__aionWorkflowMainGraph = compactGraph;
27160:   window.__aionWorkflowGraph = compactGraph;
27161: 
27162:   try {
27163:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
27164:   } catch (error) {
27165:     console.warn("[workflow] failed to save draft", error);
27166:   }
27167: 
27168:   return compactGraph;
27169: }
27170: 
27171: 
27172: 
27173: 
27174: function markAionWorkflowDraftDirty(reason = "updated") {
27175:   const graph = getAionWorkflowDraftState();
27176:   graph.dirty = true;
27177:   graph.dirty_reason = reason;
27178:   graph.saved_at = graph.saved_at || null;
27179:   compileAndAttachAionWorkflowGlyph(graph);
27180:   window["__aionWorkflowGraph"] = graph;
27181:   persistAionWorkflowDraftState();
27182:   return graph;
27183: }
27184: 
27185: function getAionWorkflowSaveStatus(graph) {
27186:   const safeGraph = graph || getAionWorkflowDraftState();
27187:   const compiled = safeGraph?.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27188:   const dirty = Boolean(safeGraph?.dirty);
27189:   const savedAt = safeGraph?.saved_at || null;
27190: 
27191:   if (dirty) {
27192:     return {
27193:       label: "Unsaved",
27194:       className: "is-unsaved",
27195:       detail: "Changes not saved",
27196:     };
27197:   }
27198: 
27199:   if (savedAt) {
27200:     return {
27201:       label: "Saved",
27202:       className: "is-saved",
27203:       detail: `Saved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
27204:     };
27205:   }
27206: 
27207:   return {
27208:     label: "Draft",
27209:     className: "is-draft",
27210:     detail: "Local draft",
27211:   };
27212: }
27213: 
27214: async function loadAionWorkflowFromBusinessContainer({
27215:   businessContainer = "",
27216:   workflowId = createAionWorkflowId(),
27217: } = {}) {
27218:   const apiBase =
27219:     state.apiBase ||
27220:     state.desktopApiBase ||
27221:     window.AION_API_BASE ||
27222:     "http://127.0.0.1:8080";
27223: 
27224:   const safeBusiness = String(businessContainer || getAionWorkflowBusinessContainerId()).trim() || getAionWorkflowBusinessContainerId();
27225:   const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
27226: 
27227:   const response = await fetch(
27228:     `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
27229:   );
27230: 
27231:   if (!response.ok) {
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
27250:     compiled_glyph: record.compiled_glyph || null,
27251:     backend_saved_at: record.updated_at || "",
27252:     backend_storage_path: record.path || "",
27253:     dirty: false,
27254:   };
27255: 
27256:   compileAndAttachAionWorkflowGlyph(loadedGraph);
27257:   window.__aionWorkflowGraph = loadedGraph;
27258:   persistAionWorkflowDraftState();
27259: 
27260:   return loadedGraph;
27261: }
27262: 
27263: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
27264:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
27265: 
27266:   if (
27267:     window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
27268:     window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
27269:   ) {
```

### Around line 27241: `const graph = record.graph || {};`

```js
27196:     };
27197:   }
27198: 
27199:   if (savedAt) {
27200:     return {
27201:       label: "Saved",
27202:       className: "is-saved",
27203:       detail: `Saved ${new Date(savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
27204:     };
27205:   }
27206: 
27207:   return {
27208:     label: "Draft",
27209:     className: "is-draft",
27210:     detail: "Local draft",
27211:   };
27212: }
27213: 
27214: async function loadAionWorkflowFromBusinessContainer({
27215:   businessContainer = "",
27216:   workflowId = createAionWorkflowId(),
27217: } = {}) {
27218:   const apiBase =
27219:     state.apiBase ||
27220:     state.desktopApiBase ||
27221:     window.AION_API_BASE ||
27222:     "http://127.0.0.1:8080";
27223: 
27224:   const safeBusiness = String(businessContainer || getAionWorkflowBusinessContainerId()).trim() || getAionWorkflowBusinessContainerId();
27225:   const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
27226: 
27227:   const response = await fetch(
27228:     `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
27229:   );
27230: 
27231:   if (!response.ok) {
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
27250:     compiled_glyph: record.compiled_glyph || null,
27251:     backend_saved_at: record.updated_at || "",
27252:     backend_storage_path: record.path || "",
27253:     dirty: false,
27254:   };
27255: 
27256:   compileAndAttachAionWorkflowGlyph(loadedGraph);
27257:   window.__aionWorkflowGraph = loadedGraph;
27258:   persistAionWorkflowDraftState();
27259: 
27260:   return loadedGraph;
27261: }
27262: 
27263: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
27264:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
27265: 
27266:   if (
27267:     window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
27268:     window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
27269:   ) {
27270:     return;
27271:   }
27272: 
27273:   window.__aionWorkflowBusinessLoadAttempted = true;
27274: 
27275:   try {
27276:     const businessContainer =
27277:       window.__aionWorkflowGraph?.business_container ||
27278:       getAionWorkflowBusinessContainerId();
27279: 
27280:     const workflowId =
27281:       window.__aionWorkflowGraph?.workflow_id ||
27282:       "workflow_draft";
27283: 
27284:     const loadedGraph = await loadAionWorkflowFromBusinessContainer({
27285:       businessContainer,
27286:       workflowId,
27287:     });
27288: 
27289:     window.__aionWorkflowLoadNotice = `Loaded saved workflow: ${loadedGraph.name || loadedGraph.workflow_id}`;
27290: 
27291:     if (window.__aionWorkflowLoadNoticeTimer) {
27292:       window.clearTimeout(window.__aionWorkflowLoadNoticeTimer);
27293:     }
27294: 
27295:     window.__aionWorkflowLoadNoticeTimer = window.setTimeout(() => {
27296:       window.__aionWorkflowLoadNotice = "";
27297:       window.__aionWorkflowLoadNoticeTimer = null;
27298:       requestRender();
27299:     }, 20000);
27300: 
27301:     safeAionDesktopPatch({
27302:       message: window.__aionWorkflowLoadNotice,
27303:       messageTone: "success",
27304:     });
27305: 
27306:     requestRender();
27307:   } catch (error) {
27308:     console.info("[workflow] no saved business-container workflow loaded", error);
27309:   }
27310: }
27311: 
27312: 
27313: async function saveAionWorkflowToBusinessContainer(graph) {
27314:   const safeGraph = graph || getAionWorkflowDraftState();
27315:   const compiledGlyph = safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27316:   const businessContainer =
27317:     compiledGlyph?.workflow?.business_container ||
27318:     safeGraph.business_container ||
27319:     getAionWorkflowBusinessContainerId();
27320: 
27321:   const payload = {
27322:     schema_version: "aion.workflow_save.v1",
27323:     business_container: businessContainer,
27324:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27325:     name: safeGraph.name || "Untitled workflow 1",
27326:     status: safeGraph.status || "draft",
27327:     graph: {
27328:       nodes: Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [],
27329:       edges: Array.isArray(safeGraph.edges) ? safeGraph.edges : [],
27330:     },
```

### Around line 27257: `window.__aionWorkflowGraph = loadedGraph;`

```js
27212: }
27213: 
27214: async function loadAionWorkflowFromBusinessContainer({
27215:   businessContainer = "",
27216:   workflowId = createAionWorkflowId(),
27217: } = {}) {
27218:   const apiBase =
27219:     state.apiBase ||
27220:     state.desktopApiBase ||
27221:     window.AION_API_BASE ||
27222:     "http://127.0.0.1:8080";
27223: 
27224:   const safeBusiness = String(businessContainer || getAionWorkflowBusinessContainerId()).trim() || getAionWorkflowBusinessContainerId();
27225:   const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
27226: 
27227:   const response = await fetch(
27228:     `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
27229:   );
27230: 
27231:   if (!response.ok) {
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
27250:     compiled_glyph: record.compiled_glyph || null,
27251:     backend_saved_at: record.updated_at || "",
27252:     backend_storage_path: record.path || "",
27253:     dirty: false,
27254:   };
27255: 
27256:   compileAndAttachAionWorkflowGlyph(loadedGraph);
27257:   window.__aionWorkflowGraph = loadedGraph;
27258:   persistAionWorkflowDraftState();
27259: 
27260:   return loadedGraph;
27261: }
27262: 
27263: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
27264:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
27265: 
27266:   if (
27267:     window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
27268:     window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
27269:   ) {
27270:     return;
27271:   }
27272: 
27273:   window.__aionWorkflowBusinessLoadAttempted = true;
27274: 
27275:   try {
27276:     const businessContainer =
27277:       window.__aionWorkflowGraph?.business_container ||
27278:       getAionWorkflowBusinessContainerId();
27279: 
27280:     const workflowId =
27281:       window.__aionWorkflowGraph?.workflow_id ||
27282:       "workflow_draft";
27283: 
27284:     const loadedGraph = await loadAionWorkflowFromBusinessContainer({
27285:       businessContainer,
27286:       workflowId,
27287:     });
27288: 
27289:     window.__aionWorkflowLoadNotice = `Loaded saved workflow: ${loadedGraph.name || loadedGraph.workflow_id}`;
27290: 
27291:     if (window.__aionWorkflowLoadNoticeTimer) {
27292:       window.clearTimeout(window.__aionWorkflowLoadNoticeTimer);
27293:     }
27294: 
27295:     window.__aionWorkflowLoadNoticeTimer = window.setTimeout(() => {
27296:       window.__aionWorkflowLoadNotice = "";
27297:       window.__aionWorkflowLoadNoticeTimer = null;
27298:       requestRender();
27299:     }, 20000);
27300: 
27301:     safeAionDesktopPatch({
27302:       message: window.__aionWorkflowLoadNotice,
27303:       messageTone: "success",
27304:     });
27305: 
27306:     requestRender();
27307:   } catch (error) {
27308:     console.info("[workflow] no saved business-container workflow loaded", error);
27309:   }
27310: }
27311: 
27312: 
27313: async function saveAionWorkflowToBusinessContainer(graph) {
27314:   const safeGraph = graph || getAionWorkflowDraftState();
27315:   const compiledGlyph = safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27316:   const businessContainer =
27317:     compiledGlyph?.workflow?.business_container ||
27318:     safeGraph.business_container ||
27319:     getAionWorkflowBusinessContainerId();
27320: 
27321:   const payload = {
27322:     schema_version: "aion.workflow_save.v1",
27323:     business_container: businessContainer,
27324:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27325:     name: safeGraph.name || "Untitled workflow 1",
27326:     status: safeGraph.status || "draft",
27327:     graph: {
27328:       nodes: Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [],
27329:       edges: Array.isArray(safeGraph.edges) ? safeGraph.edges : [],
27330:     },
27331:     compiled_glyph: compiledGlyph,
27332:   };
27333: 
27334:   const apiBase =
27335:     state.apiBase ||
27336:     state.desktopApiBase ||
27337:     window.AION_API_BASE ||
27338:     "http://127.0.0.1:8080";
27339: 
27340:   const response = await fetch(`${apiBase}/api/aion/workflows/save`, {
27341:     method: "POST",
27342:     headers: { "Content-Type": "application/json" },
27343:     body: JSON.stringify(payload),
27344:   });
27345: 
27346:   if (!response.ok) {
```

### Around line 27267: `window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||`

```js
27222:     "http://127.0.0.1:8080";
27223: 
27224:   const safeBusiness = String(businessContainer || getAionWorkflowBusinessContainerId()).trim() || getAionWorkflowBusinessContainerId();
27225:   const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
27226: 
27227:   const response = await fetch(
27228:     `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
27229:   );
27230: 
27231:   if (!response.ok) {
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
27250:     compiled_glyph: record.compiled_glyph || null,
27251:     backend_saved_at: record.updated_at || "",
27252:     backend_storage_path: record.path || "",
27253:     dirty: false,
27254:   };
27255: 
27256:   compileAndAttachAionWorkflowGlyph(loadedGraph);
27257:   window.__aionWorkflowGraph = loadedGraph;
27258:   persistAionWorkflowDraftState();
27259: 
27260:   return loadedGraph;
27261: }
27262: 
27263: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
27264:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
27265: 
27266:   if (
27267:     window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
27268:     window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
27269:   ) {
27270:     return;
27271:   }
27272: 
27273:   window.__aionWorkflowBusinessLoadAttempted = true;
27274: 
27275:   try {
27276:     const businessContainer =
27277:       window.__aionWorkflowGraph?.business_container ||
27278:       getAionWorkflowBusinessContainerId();
27279: 
27280:     const workflowId =
27281:       window.__aionWorkflowGraph?.workflow_id ||
27282:       "workflow_draft";
27283: 
27284:     const loadedGraph = await loadAionWorkflowFromBusinessContainer({
27285:       businessContainer,
27286:       workflowId,
27287:     });
27288: 
27289:     window.__aionWorkflowLoadNotice = `Loaded saved workflow: ${loadedGraph.name || loadedGraph.workflow_id}`;
27290: 
27291:     if (window.__aionWorkflowLoadNoticeTimer) {
27292:       window.clearTimeout(window.__aionWorkflowLoadNoticeTimer);
27293:     }
27294: 
27295:     window.__aionWorkflowLoadNoticeTimer = window.setTimeout(() => {
27296:       window.__aionWorkflowLoadNotice = "";
27297:       window.__aionWorkflowLoadNoticeTimer = null;
27298:       requestRender();
27299:     }, 20000);
27300: 
27301:     safeAionDesktopPatch({
27302:       message: window.__aionWorkflowLoadNotice,
27303:       messageTone: "success",
27304:     });
27305: 
27306:     requestRender();
27307:   } catch (error) {
27308:     console.info("[workflow] no saved business-container workflow loaded", error);
27309:   }
27310: }
27311: 
27312: 
27313: async function saveAionWorkflowToBusinessContainer(graph) {
27314:   const safeGraph = graph || getAionWorkflowDraftState();
27315:   const compiledGlyph = safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27316:   const businessContainer =
27317:     compiledGlyph?.workflow?.business_container ||
27318:     safeGraph.business_container ||
27319:     getAionWorkflowBusinessContainerId();
27320: 
27321:   const payload = {
27322:     schema_version: "aion.workflow_save.v1",
27323:     business_container: businessContainer,
27324:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27325:     name: safeGraph.name || "Untitled workflow 1",
27326:     status: safeGraph.status || "draft",
27327:     graph: {
27328:       nodes: Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [],
27329:       edges: Array.isArray(safeGraph.edges) ? safeGraph.edges : [],
27330:     },
27331:     compiled_glyph: compiledGlyph,
27332:   };
27333: 
27334:   const apiBase =
27335:     state.apiBase ||
27336:     state.desktopApiBase ||
27337:     window.AION_API_BASE ||
27338:     "http://127.0.0.1:8080";
27339: 
27340:   const response = await fetch(`${apiBase}/api/aion/workflows/save`, {
27341:     method: "POST",
27342:     headers: { "Content-Type": "application/json" },
27343:     body: JSON.stringify(payload),
27344:   });
27345: 
27346:   if (!response.ok) {
27347:     throw new Error(`Workflow save failed: HTTP ${response.status}`);
27348:   }
27349: 
27350:   const result = await response.json();
27351:   if (!result?.ok) {
27352:     throw new Error(result?.error || "Workflow save failed");
27353:   }
27354: 
27355:   safeGraph.business_container = result.business_container || businessContainer;
27356:   safeGraph.backend_saved_at = result.updated_at || new Date().toISOString();
```

### Around line 27268: `window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"`

```js
27223: 
27224:   const safeBusiness = String(businessContainer || getAionWorkflowBusinessContainerId()).trim() || getAionWorkflowBusinessContainerId();
27225:   const safeWorkflowId = String(workflowId || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft").trim() || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
27226: 
27227:   const response = await fetch(
27228:     `${apiBase}/api/aion/workflows/${encodeURIComponent(safeBusiness)}/${encodeURIComponent(safeWorkflowId)}`,
27229:   );
27230: 
27231:   if (!response.ok) {
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
27250:     compiled_glyph: record.compiled_glyph || null,
27251:     backend_saved_at: record.updated_at || "",
27252:     backend_storage_path: record.path || "",
27253:     dirty: false,
27254:   };
27255: 
27256:   compileAndAttachAionWorkflowGlyph(loadedGraph);
27257:   window.__aionWorkflowGraph = loadedGraph;
27258:   persistAionWorkflowDraftState();
27259: 
27260:   return loadedGraph;
27261: }
27262: 
27263: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
27264:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
27265: 
27266:   if (
27267:     window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
27268:     window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
27269:   ) {
27270:     return;
27271:   }
27272: 
27273:   window.__aionWorkflowBusinessLoadAttempted = true;
27274: 
27275:   try {
27276:     const businessContainer =
27277:       window.__aionWorkflowGraph?.business_container ||
27278:       getAionWorkflowBusinessContainerId();
27279: 
27280:     const workflowId =
27281:       window.__aionWorkflowGraph?.workflow_id ||
27282:       "workflow_draft";
27283: 
27284:     const loadedGraph = await loadAionWorkflowFromBusinessContainer({
27285:       businessContainer,
27286:       workflowId,
27287:     });
27288: 
27289:     window.__aionWorkflowLoadNotice = `Loaded saved workflow: ${loadedGraph.name || loadedGraph.workflow_id}`;
27290: 
27291:     if (window.__aionWorkflowLoadNoticeTimer) {
27292:       window.clearTimeout(window.__aionWorkflowLoadNoticeTimer);
27293:     }
27294: 
27295:     window.__aionWorkflowLoadNoticeTimer = window.setTimeout(() => {
27296:       window.__aionWorkflowLoadNotice = "";
27297:       window.__aionWorkflowLoadNoticeTimer = null;
27298:       requestRender();
27299:     }, 20000);
27300: 
27301:     safeAionDesktopPatch({
27302:       message: window.__aionWorkflowLoadNotice,
27303:       messageTone: "success",
27304:     });
27305: 
27306:     requestRender();
27307:   } catch (error) {
27308:     console.info("[workflow] no saved business-container workflow loaded", error);
27309:   }
27310: }
27311: 
27312: 
27313: async function saveAionWorkflowToBusinessContainer(graph) {
27314:   const safeGraph = graph || getAionWorkflowDraftState();
27315:   const compiledGlyph = safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27316:   const businessContainer =
27317:     compiledGlyph?.workflow?.business_container ||
27318:     safeGraph.business_container ||
27319:     getAionWorkflowBusinessContainerId();
27320: 
27321:   const payload = {
27322:     schema_version: "aion.workflow_save.v1",
27323:     business_container: businessContainer,
27324:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27325:     name: safeGraph.name || "Untitled workflow 1",
27326:     status: safeGraph.status || "draft",
27327:     graph: {
27328:       nodes: Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [],
27329:       edges: Array.isArray(safeGraph.edges) ? safeGraph.edges : [],
27330:     },
27331:     compiled_glyph: compiledGlyph,
27332:   };
27333: 
27334:   const apiBase =
27335:     state.apiBase ||
27336:     state.desktopApiBase ||
27337:     window.AION_API_BASE ||
27338:     "http://127.0.0.1:8080";
27339: 
27340:   const response = await fetch(`${apiBase}/api/aion/workflows/save`, {
27341:     method: "POST",
27342:     headers: { "Content-Type": "application/json" },
27343:     body: JSON.stringify(payload),
27344:   });
27345: 
27346:   if (!response.ok) {
27347:     throw new Error(`Workflow save failed: HTTP ${response.status}`);
27348:   }
27349: 
27350:   const result = await response.json();
27351:   if (!result?.ok) {
27352:     throw new Error(result?.error || "Workflow save failed");
27353:   }
27354: 
27355:   safeGraph.business_container = result.business_container || businessContainer;
27356:   safeGraph.backend_saved_at = result.updated_at || new Date().toISOString();
27357:   safeGraph.backend_storage_path = result.path || "";
```

### Around line 27277: `window.__aionWorkflowGraph?.business_container ||`

```js
27232:     throw new Error(`Workflow load failed: HTTP ${response.status}`);
27233:   }
27234: 
27235:   const result = await response.json();
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
27250:     compiled_glyph: record.compiled_glyph || null,
27251:     backend_saved_at: record.updated_at || "",
27252:     backend_storage_path: record.path || "",
27253:     dirty: false,
27254:   };
27255: 
27256:   compileAndAttachAionWorkflowGlyph(loadedGraph);
27257:   window.__aionWorkflowGraph = loadedGraph;
27258:   persistAionWorkflowDraftState();
27259: 
27260:   return loadedGraph;
27261: }
27262: 
27263: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
27264:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
27265: 
27266:   if (
27267:     window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
27268:     window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
27269:   ) {
27270:     return;
27271:   }
27272: 
27273:   window.__aionWorkflowBusinessLoadAttempted = true;
27274: 
27275:   try {
27276:     const businessContainer =
27277:       window.__aionWorkflowGraph?.business_container ||
27278:       getAionWorkflowBusinessContainerId();
27279: 
27280:     const workflowId =
27281:       window.__aionWorkflowGraph?.workflow_id ||
27282:       "workflow_draft";
27283: 
27284:     const loadedGraph = await loadAionWorkflowFromBusinessContainer({
27285:       businessContainer,
27286:       workflowId,
27287:     });
27288: 
27289:     window.__aionWorkflowLoadNotice = `Loaded saved workflow: ${loadedGraph.name || loadedGraph.workflow_id}`;
27290: 
27291:     if (window.__aionWorkflowLoadNoticeTimer) {
27292:       window.clearTimeout(window.__aionWorkflowLoadNoticeTimer);
27293:     }
27294: 
27295:     window.__aionWorkflowLoadNoticeTimer = window.setTimeout(() => {
27296:       window.__aionWorkflowLoadNotice = "";
27297:       window.__aionWorkflowLoadNoticeTimer = null;
27298:       requestRender();
27299:     }, 20000);
27300: 
27301:     safeAionDesktopPatch({
27302:       message: window.__aionWorkflowLoadNotice,
27303:       messageTone: "success",
27304:     });
27305: 
27306:     requestRender();
27307:   } catch (error) {
27308:     console.info("[workflow] no saved business-container workflow loaded", error);
27309:   }
27310: }
27311: 
27312: 
27313: async function saveAionWorkflowToBusinessContainer(graph) {
27314:   const safeGraph = graph || getAionWorkflowDraftState();
27315:   const compiledGlyph = safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27316:   const businessContainer =
27317:     compiledGlyph?.workflow?.business_container ||
27318:     safeGraph.business_container ||
27319:     getAionWorkflowBusinessContainerId();
27320: 
27321:   const payload = {
27322:     schema_version: "aion.workflow_save.v1",
27323:     business_container: businessContainer,
27324:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27325:     name: safeGraph.name || "Untitled workflow 1",
27326:     status: safeGraph.status || "draft",
27327:     graph: {
27328:       nodes: Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [],
27329:       edges: Array.isArray(safeGraph.edges) ? safeGraph.edges : [],
27330:     },
27331:     compiled_glyph: compiledGlyph,
27332:   };
27333: 
27334:   const apiBase =
27335:     state.apiBase ||
27336:     state.desktopApiBase ||
27337:     window.AION_API_BASE ||
27338:     "http://127.0.0.1:8080";
27339: 
27340:   const response = await fetch(`${apiBase}/api/aion/workflows/save`, {
27341:     method: "POST",
27342:     headers: { "Content-Type": "application/json" },
27343:     body: JSON.stringify(payload),
27344:   });
27345: 
27346:   if (!response.ok) {
27347:     throw new Error(`Workflow save failed: HTTP ${response.status}`);
27348:   }
27349: 
27350:   const result = await response.json();
27351:   if (!result?.ok) {
27352:     throw new Error(result?.error || "Workflow save failed");
27353:   }
27354: 
27355:   safeGraph.business_container = result.business_container || businessContainer;
27356:   safeGraph.backend_saved_at = result.updated_at || new Date().toISOString();
27357:   safeGraph.backend_storage_path = result.path || "";
27358: 
27359:   compileAndAttachAionWorkflowGlyph(safeGraph);
27360:   safeGraph.glyph_capsule_registry_item =
27361:     upsertAionWorkflowGlyphCapsuleRegistryItem(safeGraph);
27362: 
27363:   return result;
27364: }
27365: 
27366: 
```

### Around line 27281: `window.__aionWorkflowGraph?.workflow_id ||`

```js
27236:   if (!result?.ok || !result?.workflow) {
27237:     throw new Error(result?.error || "Workflow not found");
27238:   }
27239: 
27240:   const record = result.workflow;
27241:   const graph = record.graph || {};
27242: 
27243:   const loadedGraph = {
27244:     workflow_id: record.workflow_id || safeWorkflowId,
27245:     name: record.name || "Untitled workflow 1",
27246:     status: record.status || "draft",
27247:     business_container: record.business_container || safeBusiness,
27248:     nodes: Array.isArray(graph.nodes) ? graph.nodes : [],
27249:     edges: Array.isArray(graph.edges) ? graph.edges : [],
27250:     compiled_glyph: record.compiled_glyph || null,
27251:     backend_saved_at: record.updated_at || "",
27252:     backend_storage_path: record.path || "",
27253:     dirty: false,
27254:   };
27255: 
27256:   compileAndAttachAionWorkflowGlyph(loadedGraph);
27257:   window.__aionWorkflowGraph = loadedGraph;
27258:   persistAionWorkflowDraftState();
27259: 
27260:   return loadedGraph;
27261: }
27262: 
27263: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
27264:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
27265: 
27266:   if (
27267:     window.__aionWorkflowGraph?.canvas_type === "goal_loop" ||
27268:     window.__aionWorkflowGraph?.active_canvas_intent === "goal_loop"
27269:   ) {
27270:     return;
27271:   }
27272: 
27273:   window.__aionWorkflowBusinessLoadAttempted = true;
27274: 
27275:   try {
27276:     const businessContainer =
27277:       window.__aionWorkflowGraph?.business_container ||
27278:       getAionWorkflowBusinessContainerId();
27279: 
27280:     const workflowId =
27281:       window.__aionWorkflowGraph?.workflow_id ||
27282:       "workflow_draft";
27283: 
27284:     const loadedGraph = await loadAionWorkflowFromBusinessContainer({
27285:       businessContainer,
27286:       workflowId,
27287:     });
27288: 
27289:     window.__aionWorkflowLoadNotice = `Loaded saved workflow: ${loadedGraph.name || loadedGraph.workflow_id}`;
27290: 
27291:     if (window.__aionWorkflowLoadNoticeTimer) {
27292:       window.clearTimeout(window.__aionWorkflowLoadNoticeTimer);
27293:     }
27294: 
27295:     window.__aionWorkflowLoadNoticeTimer = window.setTimeout(() => {
27296:       window.__aionWorkflowLoadNotice = "";
27297:       window.__aionWorkflowLoadNoticeTimer = null;
27298:       requestRender();
27299:     }, 20000);
27300: 
27301:     safeAionDesktopPatch({
27302:       message: window.__aionWorkflowLoadNotice,
27303:       messageTone: "success",
27304:     });
27305: 
27306:     requestRender();
27307:   } catch (error) {
27308:     console.info("[workflow] no saved business-container workflow loaded", error);
27309:   }
27310: }
27311: 
27312: 
27313: async function saveAionWorkflowToBusinessContainer(graph) {
27314:   const safeGraph = graph || getAionWorkflowDraftState();
27315:   const compiledGlyph = safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
27316:   const businessContainer =
27317:     compiledGlyph?.workflow?.business_container ||
27318:     safeGraph.business_container ||
27319:     getAionWorkflowBusinessContainerId();
27320: 
27321:   const payload = {
27322:     schema_version: "aion.workflow_save.v1",
27323:     business_container: businessContainer,
27324:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
27325:     name: safeGraph.name || "Untitled workflow 1",
27326:     status: safeGraph.status || "draft",
27327:     graph: {
27328:       nodes: Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [],
27329:       edges: Array.isArray(safeGraph.edges) ? safeGraph.edges : [],
27330:     },
27331:     compiled_glyph: compiledGlyph,
27332:   };
27333: 
27334:   const apiBase =
27335:     state.apiBase ||
27336:     state.desktopApiBase ||
27337:     window.AION_API_BASE ||
27338:     "http://127.0.0.1:8080";
27339: 
27340:   const response = await fetch(`${apiBase}/api/aion/workflows/save`, {
27341:     method: "POST",
27342:     headers: { "Content-Type": "application/json" },
27343:     body: JSON.stringify(payload),
27344:   });
27345: 
27346:   if (!response.ok) {
27347:     throw new Error(`Workflow save failed: HTTP ${response.status}`);
27348:   }
27349: 
27350:   const result = await response.json();
27351:   if (!result?.ok) {
27352:     throw new Error(result?.error || "Workflow save failed");
27353:   }
27354: 
27355:   safeGraph.business_container = result.business_container || businessContainer;
27356:   safeGraph.backend_saved_at = result.updated_at || new Date().toISOString();
27357:   safeGraph.backend_storage_path = result.path || "";
27358: 
27359:   compileAndAttachAionWorkflowGlyph(safeGraph);
27360:   safeGraph.glyph_capsule_registry_item =
27361:     upsertAionWorkflowGlyphCapsuleRegistryItem(safeGraph);
27362: 
27363:   return result;
27364: }
27365: 
27366: 
27367: 
27368: 
27369: 
27370: 
```

### Around line 27449: `const graph =`

```js
27404:     safeGraph.workflow_id ||
27405:     window.__aionCreateUniqueWorkflowId?.() ||
27406:     "workflow_draft";
27407: 
27408:   const businessContainer =
27409:     compiledGlyph?.workflow?.business_container ||
27410:     safeGraph.business_container ||
27411:     getAionWorkflowBusinessContainerId();
27412: 
27413:   const item = {
27414:     id: `${businessContainer}:${workflowId}`,
27415:     workflow_id: workflowId,
27416:     name: compiledGlyph?.workflow?.name || safeGraph.name || "Untitled workflow 1",
27417:     business_container: businessContainer,
27418:     status: compiledGlyph?.workflow?.status || safeGraph.status || "draft",
27419:     glyph_type: compiledGlyph?.glyph_type || "workflow_capsule",
27420:     callable: compiledGlyph?.callable === true,
27421:     risk_tier: compiledGlyph?.risk_tier || "low",
27422:     required_connectors: Array.isArray(compiledGlyph?.required_connectors)
27423:       ? compiledGlyph.required_connectors
27424:       : [],
27425:     boardroom_events: Array.isArray(compiledGlyph?.boardroom_events)
27426:       ? compiledGlyph.boardroom_events
27427:       : [],
27428:     compiled_at: compiledGlyph?.compiled_at || new Date().toISOString(),
27429:     saved_at: new Date().toISOString(),
27430:     compiled_glyph: compiledGlyph,
27431:   };
27432: 
27433:   const registry = getAionWorkflowGlyphCapsuleRegistry();
27434:   const next = [
27435:     item,
27436:     ...registry.filter((existing) => String(existing?.id || "") !== item.id),
27437:   ].slice(0, 100);
27438: 
27439:   persistAionWorkflowGlyphCapsuleRegistry(next);
27440:   return item;
27441: }
27442: 
27443: function listAionWorkflowGlyphCapsules() {
27444:   return getAionWorkflowGlyphCapsuleRegistry();
27445: }
27446: 
27447: 
27448: function getAionWorkflowGlyphLibraryBusinessContainer() {
27449:   const graph =
27450:     typeof getAionWorkflowDraftState === "function"
27451:       ? getAionWorkflowDraftState()
27452:       : window.__aionWorkflowGraph || {};
27453: 
27454:   return String(
27455:     graph?.business_container ||
27456:     graph?.compiled_glyph?.workflow?.business_container ||
27457:     getAionWorkflowBusinessContainerId()
27458:   );
27459: }
27460: 
27461: function normaliseAionWorkflowGlyphLibraryItem(item = {}) {
27462:   const compiled = item.compiled_glyph || {};
27463:   const workflow = compiled.workflow || {};
27464: 
27465:   return {
27466:     id: String(item.id || item.workflow_id || workflow.workflow_id || "workflow_glyph"),
27467:     workflow_id: String(item.workflow_id || workflow.workflow_id || item.id || "workflow_glyph"),
27468:     name: String(item.name || item.title || workflow.name || "Untitled workflow glyph"),
27469:     business_container: String(item.business_container || workflow.business_container || getAionWorkflowBusinessContainerId()),
27470:     status: String(item.status || workflow.status || "draft"),
27471:     glyph_type: String(item.glyph_type || compiled.glyph_type || "workflow_capsule"),
27472:     callable: item.callable === true || compiled.callable === true,
27473:     risk_tier: String(item.risk_tier || compiled.risk_tier || "low"),
27474:     required_connectors: Array.isArray(item.required_connectors)
27475:       ? item.required_connectors
27476:       : Array.isArray(compiled.required_connectors)
27477:         ? compiled.required_connectors
27478:         : [],
27479:     inputs_schema: item.inputs_schema || compiled.inputs_schema || {},
27480:     outputs_schema: item.outputs_schema || compiled.outputs_schema || {},
27481:     saved_at: String(item.saved_at || item.updated_at || item.compiled_at || ""),
27482:   };
27483: }
27484: 
27485: function listAionWorkflowGlyphLibraryItems() {
27486:   const businessContainer = getAionWorkflowGlyphLibraryBusinessContainer();
27487: 
27488:   return listAionWorkflowGlyphCapsules()
27489:     .map((item) => normaliseAionWorkflowGlyphLibraryItem(item))
27490:     .filter((item) => item.business_container === businessContainer)
27491:     .sort((a, b) => String(b.saved_at || "").localeCompare(String(a.saved_at || "")));
27492: }
27493: 
27494: function summariseAionWorkflowGlyphSchema(schema = {}) {
27495:   if (!schema || typeof schema !== "object") return "—";
27496: 
27497:   const properties =
27498:     schema.properties && typeof schema.properties === "object"
27499:       ? Object.keys(schema.properties)
27500:       : Object.keys(schema);
27501: 
27502:   return properties.length ? properties.slice(0, 6).join(", ") : "Any payload";
27503: }
27504: 
27505: 
27506: function listAionMasterGlyphCanvasItems() {
27507:   if (typeof listAionWorkflowGlyphLibraryItems === "function") {
27508:     return listAionWorkflowGlyphLibraryItems()
27509:       .filter((item) => item && item.callable === true);
27510:   }
27511: 
27512:   if (typeof listAionWorkflowGlyphCapsules === "function") {
27513:     return listAionWorkflowGlyphCapsules()
27514:       .filter((item) => item && item.callable === true);
27515:   }
27516: 
27517:   return [];
27518: }
27519: 
27520: function summariseAionMasterGlyphValue(value, fallback = "None declared") {
27521:   if (Array.isArray(value)) {
27522:     if (!value.length) return fallback;
27523:     return value
27524:       .map((item) => {
27525:         if (typeof item === "string") return item;
27526:         return item?.event_type || item?.name || item?.connector || item?.id || JSON.stringify(item);
27527:       })
27528:       .filter(Boolean)
27529:       .join(", ");
27530:   }
27531: 
27532:   if (value && typeof value === "object") {
27533:     const keys = Object.keys(value);
27534:     return keys.length ? keys.slice(0, 6).join(", ") : fallback;
27535:   }
27536: 
27537:   const text = String(value || "").trim();
27538:   return text || fallback;
```

### Around line 27452: `: window.__aionWorkflowGraph || {};`

```js
27407: 
27408:   const businessContainer =
27409:     compiledGlyph?.workflow?.business_container ||
27410:     safeGraph.business_container ||
27411:     getAionWorkflowBusinessContainerId();
27412: 
27413:   const item = {
27414:     id: `${businessContainer}:${workflowId}`,
27415:     workflow_id: workflowId,
27416:     name: compiledGlyph?.workflow?.name || safeGraph.name || "Untitled workflow 1",
27417:     business_container: businessContainer,
27418:     status: compiledGlyph?.workflow?.status || safeGraph.status || "draft",
27419:     glyph_type: compiledGlyph?.glyph_type || "workflow_capsule",
27420:     callable: compiledGlyph?.callable === true,
27421:     risk_tier: compiledGlyph?.risk_tier || "low",
27422:     required_connectors: Array.isArray(compiledGlyph?.required_connectors)
27423:       ? compiledGlyph.required_connectors
27424:       : [],
27425:     boardroom_events: Array.isArray(compiledGlyph?.boardroom_events)
27426:       ? compiledGlyph.boardroom_events
27427:       : [],
27428:     compiled_at: compiledGlyph?.compiled_at || new Date().toISOString(),
27429:     saved_at: new Date().toISOString(),
27430:     compiled_glyph: compiledGlyph,
27431:   };
27432: 
27433:   const registry = getAionWorkflowGlyphCapsuleRegistry();
27434:   const next = [
27435:     item,
27436:     ...registry.filter((existing) => String(existing?.id || "") !== item.id),
27437:   ].slice(0, 100);
27438: 
27439:   persistAionWorkflowGlyphCapsuleRegistry(next);
27440:   return item;
27441: }
27442: 
27443: function listAionWorkflowGlyphCapsules() {
27444:   return getAionWorkflowGlyphCapsuleRegistry();
27445: }
27446: 
27447: 
27448: function getAionWorkflowGlyphLibraryBusinessContainer() {
27449:   const graph =
27450:     typeof getAionWorkflowDraftState === "function"
27451:       ? getAionWorkflowDraftState()
27452:       : window.__aionWorkflowGraph || {};
27453: 
27454:   return String(
27455:     graph?.business_container ||
27456:     graph?.compiled_glyph?.workflow?.business_container ||
27457:     getAionWorkflowBusinessContainerId()
27458:   );
27459: }
27460: 
27461: function normaliseAionWorkflowGlyphLibraryItem(item = {}) {
27462:   const compiled = item.compiled_glyph || {};
27463:   const workflow = compiled.workflow || {};
27464: 
27465:   return {
27466:     id: String(item.id || item.workflow_id || workflow.workflow_id || "workflow_glyph"),
27467:     workflow_id: String(item.workflow_id || workflow.workflow_id || item.id || "workflow_glyph"),
27468:     name: String(item.name || item.title || workflow.name || "Untitled workflow glyph"),
27469:     business_container: String(item.business_container || workflow.business_container || getAionWorkflowBusinessContainerId()),
27470:     status: String(item.status || workflow.status || "draft"),
27471:     glyph_type: String(item.glyph_type || compiled.glyph_type || "workflow_capsule"),
27472:     callable: item.callable === true || compiled.callable === true,
27473:     risk_tier: String(item.risk_tier || compiled.risk_tier || "low"),
27474:     required_connectors: Array.isArray(item.required_connectors)
27475:       ? item.required_connectors
27476:       : Array.isArray(compiled.required_connectors)
27477:         ? compiled.required_connectors
27478:         : [],
27479:     inputs_schema: item.inputs_schema || compiled.inputs_schema || {},
27480:     outputs_schema: item.outputs_schema || compiled.outputs_schema || {},
27481:     saved_at: String(item.saved_at || item.updated_at || item.compiled_at || ""),
27482:   };
27483: }
27484: 
27485: function listAionWorkflowGlyphLibraryItems() {
27486:   const businessContainer = getAionWorkflowGlyphLibraryBusinessContainer();
27487: 
27488:   return listAionWorkflowGlyphCapsules()
27489:     .map((item) => normaliseAionWorkflowGlyphLibraryItem(item))
27490:     .filter((item) => item.business_container === businessContainer)
27491:     .sort((a, b) => String(b.saved_at || "").localeCompare(String(a.saved_at || "")));
27492: }
27493: 
27494: function summariseAionWorkflowGlyphSchema(schema = {}) {
27495:   if (!schema || typeof schema !== "object") return "—";
27496: 
27497:   const properties =
27498:     schema.properties && typeof schema.properties === "object"
27499:       ? Object.keys(schema.properties)
27500:       : Object.keys(schema);
27501: 
27502:   return properties.length ? properties.slice(0, 6).join(", ") : "Any payload";
27503: }
27504: 
27505: 
27506: function listAionMasterGlyphCanvasItems() {
27507:   if (typeof listAionWorkflowGlyphLibraryItems === "function") {
27508:     return listAionWorkflowGlyphLibraryItems()
27509:       .filter((item) => item && item.callable === true);
27510:   }
27511: 
27512:   if (typeof listAionWorkflowGlyphCapsules === "function") {
27513:     return listAionWorkflowGlyphCapsules()
27514:       .filter((item) => item && item.callable === true);
27515:   }
27516: 
27517:   return [];
27518: }
27519: 
27520: function summariseAionMasterGlyphValue(value, fallback = "None declared") {
27521:   if (Array.isArray(value)) {
27522:     if (!value.length) return fallback;
27523:     return value
27524:       .map((item) => {
27525:         if (typeof item === "string") return item;
27526:         return item?.event_type || item?.name || item?.connector || item?.id || JSON.stringify(item);
27527:       })
27528:       .filter(Boolean)
27529:       .join(", ");
27530:   }
27531: 
27532:   if (value && typeof value === "object") {
27533:     const keys = Object.keys(value);
27534:     return keys.length ? keys.slice(0, 6).join(", ") : fallback;
27535:   }
27536: 
27537:   const text = String(value || "").trim();
27538:   return text || fallback;
27539: }
27540: 
27541: function renderAionMasterGlyphCanvasNode(item, index = 0) {
```

### Around line 27657: `const graph = getAionWorkflowDraftState();`

```js
27612: 
27613:       <div class="aion-master-glyph-readonly-note">
27614:         Master glyph source · no execution · saved glyph not mutated
27615:       </div>
27616: 
27617:       <button
27618:         type="button"
27619:         class="secondary-btn secondary-btn-small"
27620:         data-aion-master-glyph-stage-to-canvas="true"
27621:         data-workflow-id="${escapeHtml(workflowId)}"
27622:         title="Stage this callable glyph as a dry-run call_workflow_glyph node"
27623:       >
27624:         Stage to workflow canvas
27625:       </button>
27626:     </article>
27627:   `;
27628: }
27629: 
27630: function renderAionMasterGlyphCanvasPanel() {
27631:   /*
27632:    * RETIRED:
27633:    * There is no separate Master Glyph Canvas surface anymore.
27634:    * Reusable glyph workflows now live inside the normal Workflow Canvas via:
27635:    * - Glyph Library button
27636:    * - top workflow tabs
27637:    * - staged/opened call_workflow_glyph nodes
27638:    */
27639:   return "";
27640: }
27641: 
27642: function installAionMasterGlyphCanvasControls() {
27643:   if (window.__aionMasterGlyphCanvasControlsInstalled === true) return;
27644:   window.__aionMasterGlyphCanvasControlsInstalled = true;
27645: 
27646:   function cloneMasterGlyphValue(value) {
27647:     try {
27648:       return JSON.parse(JSON.stringify(value));
27649:     } catch (_) {
27650:       return value;
27651:     }
27652:   }
27653: 
27654:   function getCurrentWorkflowGraphForMasterGlyphStage() {
27655:     if (typeof getAionWorkflowDraftState === "function") {
27656:       try {
27657:         const graph = getAionWorkflowDraftState();
27658:         if (graph && typeof graph === "object") return graph;
27659:       } catch (_) {}
27660:     }
27661: 
27662:     window["__aionWorkflowGraph"] = window["__aionWorkflowGraph"] || {
27663:       workflow_id: `workflow_${Date.now()}`,
27664:       name: "Untitled workflow",
27665:       status: "draft",
27666:       nodes: [],
27667:       edges: [],
27668:     };
27669: 
27670:     return window["__aionWorkflowGraph"];
27671:   }
27672: 
27673:   function findMasterGlyphCanvasItem(workflowId) {
27674:     const needle = String(workflowId || "").trim().toLowerCase();
27675:     if (!needle) return null;
27676: 
27677:     const items = typeof listAionMasterGlyphCanvasItems === "function"
27678:       ? listAionMasterGlyphCanvasItems()
27679:       : [];
27680: 
27681:     return items.find((item) => {
27682:       const compiled = item?.compiled_glyph || {};
27683:       return [
27684:         item?.workflow_id,
27685:         item?.id,
27686:         item?.name,
27687:         compiled?.workflow?.workflow_id,
27688:         compiled?.workflow?.name,
27689:       ].some((value) => String(value || "").trim().toLowerCase() === needle);
27690:     }) || null;
27691:   }
27692: 
27693:   function stageMasterGlyphToWorkflowCanvas(workflowId) {
27694:     const item = findMasterGlyphCanvasItem(workflowId);
27695:     if (!item) {
27696:       if (typeof safePatchMessage === "function") {
27697:         safePatchMessage("Could not find callable workflow glyph to stage.", "error");
27698:       }
27699:       return null;
27700:     }
27701: 
27702:     const compiled = cloneMasterGlyphValue(item.compiled_glyph || {});
27703:     const childWorkflowId =
27704:       item.workflow_id ||
27705:       compiled?.workflow?.workflow_id ||
27706:       item.id ||
27707:       workflowId;
27708: 
27709:     const graph = getCurrentWorkflowGraphForMasterGlyphStage();
27710:     graph.nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27711:     graph.edges = Array.isArray(graph.edges) ? graph.edges : [];
27712: 
27713:     const nodeId = `call_workflow_glyph_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
27714:     const x = 220 + (graph.nodes.length % 4) * 280;
27715:     const y = 260 + Math.floor(graph.nodes.length / 4) * 180;
27716: 
27717:     const stagedNode = {
27718:       id: nodeId,
27719:       title: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27720:       label: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27721:       type: "Workflow Glyph",
27722:       icon: "⌁",
27723:       status: "Staged",
27724:       meta: "Staged from Workflow Glyph Library · dry-run only · no execution yet",
27725:       tone: "violet",
27726:       x,
27727:       y,
27728:       dry_run_only: true,
27729:       live_send_enabled: false,
27730:       action_id: "call_workflow_glyph",
27731:       module_id: "workflow.call_workflow_glyph",
27732:       config: {
27733:         action_id: "call_workflow_glyph",
27734:         module_id: "workflow.call_workflow_glyph",
27735:         workflow_id: childWorkflowId,
27736:         child_workflow_id: childWorkflowId,
27737:         glyph_id: item.id || childWorkflowId,
27738:         callable: true,
27739:         dry_run_only: true,
27740:         live_send_enabled: false,
27741:         risk_tier: item.risk_tier || compiled.risk_tier || "low",
27742:         required_connectors: cloneMasterGlyphValue(item.required_connectors || compiled.required_connectors || []),
27743:         inputs_schema: cloneMasterGlyphValue(item.inputs_schema || compiled.inputs_schema || {}),
27744:         outputs_schema: cloneMasterGlyphValue(item.outputs_schema || compiled.outputs_schema || {}),
27745:         approval_policy: cloneMasterGlyphValue(item.approval_policy || compiled.approval_policy || {}),
27746:         boardroom_events: cloneMasterGlyphValue(item.boardroom_events || compiled.boardroom_events || []),
```

### Around line 27662: `window["__aionWorkflowGraph"] = window["__aionWorkflowGraph"] || {`

```js
27617:       <button
27618:         type="button"
27619:         class="secondary-btn secondary-btn-small"
27620:         data-aion-master-glyph-stage-to-canvas="true"
27621:         data-workflow-id="${escapeHtml(workflowId)}"
27622:         title="Stage this callable glyph as a dry-run call_workflow_glyph node"
27623:       >
27624:         Stage to workflow canvas
27625:       </button>
27626:     </article>
27627:   `;
27628: }
27629: 
27630: function renderAionMasterGlyphCanvasPanel() {
27631:   /*
27632:    * RETIRED:
27633:    * There is no separate Master Glyph Canvas surface anymore.
27634:    * Reusable glyph workflows now live inside the normal Workflow Canvas via:
27635:    * - Glyph Library button
27636:    * - top workflow tabs
27637:    * - staged/opened call_workflow_glyph nodes
27638:    */
27639:   return "";
27640: }
27641: 
27642: function installAionMasterGlyphCanvasControls() {
27643:   if (window.__aionMasterGlyphCanvasControlsInstalled === true) return;
27644:   window.__aionMasterGlyphCanvasControlsInstalled = true;
27645: 
27646:   function cloneMasterGlyphValue(value) {
27647:     try {
27648:       return JSON.parse(JSON.stringify(value));
27649:     } catch (_) {
27650:       return value;
27651:     }
27652:   }
27653: 
27654:   function getCurrentWorkflowGraphForMasterGlyphStage() {
27655:     if (typeof getAionWorkflowDraftState === "function") {
27656:       try {
27657:         const graph = getAionWorkflowDraftState();
27658:         if (graph && typeof graph === "object") return graph;
27659:       } catch (_) {}
27660:     }
27661: 
27662:     window["__aionWorkflowGraph"] = window["__aionWorkflowGraph"] || {
27663:       workflow_id: `workflow_${Date.now()}`,
27664:       name: "Untitled workflow",
27665:       status: "draft",
27666:       nodes: [],
27667:       edges: [],
27668:     };
27669: 
27670:     return window["__aionWorkflowGraph"];
27671:   }
27672: 
27673:   function findMasterGlyphCanvasItem(workflowId) {
27674:     const needle = String(workflowId || "").trim().toLowerCase();
27675:     if (!needle) return null;
27676: 
27677:     const items = typeof listAionMasterGlyphCanvasItems === "function"
27678:       ? listAionMasterGlyphCanvasItems()
27679:       : [];
27680: 
27681:     return items.find((item) => {
27682:       const compiled = item?.compiled_glyph || {};
27683:       return [
27684:         item?.workflow_id,
27685:         item?.id,
27686:         item?.name,
27687:         compiled?.workflow?.workflow_id,
27688:         compiled?.workflow?.name,
27689:       ].some((value) => String(value || "").trim().toLowerCase() === needle);
27690:     }) || null;
27691:   }
27692: 
27693:   function stageMasterGlyphToWorkflowCanvas(workflowId) {
27694:     const item = findMasterGlyphCanvasItem(workflowId);
27695:     if (!item) {
27696:       if (typeof safePatchMessage === "function") {
27697:         safePatchMessage("Could not find callable workflow glyph to stage.", "error");
27698:       }
27699:       return null;
27700:     }
27701: 
27702:     const compiled = cloneMasterGlyphValue(item.compiled_glyph || {});
27703:     const childWorkflowId =
27704:       item.workflow_id ||
27705:       compiled?.workflow?.workflow_id ||
27706:       item.id ||
27707:       workflowId;
27708: 
27709:     const graph = getCurrentWorkflowGraphForMasterGlyphStage();
27710:     graph.nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27711:     graph.edges = Array.isArray(graph.edges) ? graph.edges : [];
27712: 
27713:     const nodeId = `call_workflow_glyph_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
27714:     const x = 220 + (graph.nodes.length % 4) * 280;
27715:     const y = 260 + Math.floor(graph.nodes.length / 4) * 180;
27716: 
27717:     const stagedNode = {
27718:       id: nodeId,
27719:       title: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27720:       label: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27721:       type: "Workflow Glyph",
27722:       icon: "⌁",
27723:       status: "Staged",
27724:       meta: "Staged from Workflow Glyph Library · dry-run only · no execution yet",
27725:       tone: "violet",
27726:       x,
27727:       y,
27728:       dry_run_only: true,
27729:       live_send_enabled: false,
27730:       action_id: "call_workflow_glyph",
27731:       module_id: "workflow.call_workflow_glyph",
27732:       config: {
27733:         action_id: "call_workflow_glyph",
27734:         module_id: "workflow.call_workflow_glyph",
27735:         workflow_id: childWorkflowId,
27736:         child_workflow_id: childWorkflowId,
27737:         glyph_id: item.id || childWorkflowId,
27738:         callable: true,
27739:         dry_run_only: true,
27740:         live_send_enabled: false,
27741:         risk_tier: item.risk_tier || compiled.risk_tier || "low",
27742:         required_connectors: cloneMasterGlyphValue(item.required_connectors || compiled.required_connectors || []),
27743:         inputs_schema: cloneMasterGlyphValue(item.inputs_schema || compiled.inputs_schema || {}),
27744:         outputs_schema: cloneMasterGlyphValue(item.outputs_schema || compiled.outputs_schema || {}),
27745:         approval_policy: cloneMasterGlyphValue(item.approval_policy || compiled.approval_policy || {}),
27746:         boardroom_events: cloneMasterGlyphValue(item.boardroom_events || compiled.boardroom_events || []),
27747:         compiled_glyph: compiled,
27748:       },
27749:       runtime: {
27750:         input_items: [],
27751:         output_items: [],
```

### Around line 27670: `return window["__aionWorkflowGraph"];`

```js
27625:       </button>
27626:     </article>
27627:   `;
27628: }
27629: 
27630: function renderAionMasterGlyphCanvasPanel() {
27631:   /*
27632:    * RETIRED:
27633:    * There is no separate Master Glyph Canvas surface anymore.
27634:    * Reusable glyph workflows now live inside the normal Workflow Canvas via:
27635:    * - Glyph Library button
27636:    * - top workflow tabs
27637:    * - staged/opened call_workflow_glyph nodes
27638:    */
27639:   return "";
27640: }
27641: 
27642: function installAionMasterGlyphCanvasControls() {
27643:   if (window.__aionMasterGlyphCanvasControlsInstalled === true) return;
27644:   window.__aionMasterGlyphCanvasControlsInstalled = true;
27645: 
27646:   function cloneMasterGlyphValue(value) {
27647:     try {
27648:       return JSON.parse(JSON.stringify(value));
27649:     } catch (_) {
27650:       return value;
27651:     }
27652:   }
27653: 
27654:   function getCurrentWorkflowGraphForMasterGlyphStage() {
27655:     if (typeof getAionWorkflowDraftState === "function") {
27656:       try {
27657:         const graph = getAionWorkflowDraftState();
27658:         if (graph && typeof graph === "object") return graph;
27659:       } catch (_) {}
27660:     }
27661: 
27662:     window["__aionWorkflowGraph"] = window["__aionWorkflowGraph"] || {
27663:       workflow_id: `workflow_${Date.now()}`,
27664:       name: "Untitled workflow",
27665:       status: "draft",
27666:       nodes: [],
27667:       edges: [],
27668:     };
27669: 
27670:     return window["__aionWorkflowGraph"];
27671:   }
27672: 
27673:   function findMasterGlyphCanvasItem(workflowId) {
27674:     const needle = String(workflowId || "").trim().toLowerCase();
27675:     if (!needle) return null;
27676: 
27677:     const items = typeof listAionMasterGlyphCanvasItems === "function"
27678:       ? listAionMasterGlyphCanvasItems()
27679:       : [];
27680: 
27681:     return items.find((item) => {
27682:       const compiled = item?.compiled_glyph || {};
27683:       return [
27684:         item?.workflow_id,
27685:         item?.id,
27686:         item?.name,
27687:         compiled?.workflow?.workflow_id,
27688:         compiled?.workflow?.name,
27689:       ].some((value) => String(value || "").trim().toLowerCase() === needle);
27690:     }) || null;
27691:   }
27692: 
27693:   function stageMasterGlyphToWorkflowCanvas(workflowId) {
27694:     const item = findMasterGlyphCanvasItem(workflowId);
27695:     if (!item) {
27696:       if (typeof safePatchMessage === "function") {
27697:         safePatchMessage("Could not find callable workflow glyph to stage.", "error");
27698:       }
27699:       return null;
27700:     }
27701: 
27702:     const compiled = cloneMasterGlyphValue(item.compiled_glyph || {});
27703:     const childWorkflowId =
27704:       item.workflow_id ||
27705:       compiled?.workflow?.workflow_id ||
27706:       item.id ||
27707:       workflowId;
27708: 
27709:     const graph = getCurrentWorkflowGraphForMasterGlyphStage();
27710:     graph.nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27711:     graph.edges = Array.isArray(graph.edges) ? graph.edges : [];
27712: 
27713:     const nodeId = `call_workflow_glyph_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
27714:     const x = 220 + (graph.nodes.length % 4) * 280;
27715:     const y = 260 + Math.floor(graph.nodes.length / 4) * 180;
27716: 
27717:     const stagedNode = {
27718:       id: nodeId,
27719:       title: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27720:       label: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27721:       type: "Workflow Glyph",
27722:       icon: "⌁",
27723:       status: "Staged",
27724:       meta: "Staged from Workflow Glyph Library · dry-run only · no execution yet",
27725:       tone: "violet",
27726:       x,
27727:       y,
27728:       dry_run_only: true,
27729:       live_send_enabled: false,
27730:       action_id: "call_workflow_glyph",
27731:       module_id: "workflow.call_workflow_glyph",
27732:       config: {
27733:         action_id: "call_workflow_glyph",
27734:         module_id: "workflow.call_workflow_glyph",
27735:         workflow_id: childWorkflowId,
27736:         child_workflow_id: childWorkflowId,
27737:         glyph_id: item.id || childWorkflowId,
27738:         callable: true,
27739:         dry_run_only: true,
27740:         live_send_enabled: false,
27741:         risk_tier: item.risk_tier || compiled.risk_tier || "low",
27742:         required_connectors: cloneMasterGlyphValue(item.required_connectors || compiled.required_connectors || []),
27743:         inputs_schema: cloneMasterGlyphValue(item.inputs_schema || compiled.inputs_schema || {}),
27744:         outputs_schema: cloneMasterGlyphValue(item.outputs_schema || compiled.outputs_schema || {}),
27745:         approval_policy: cloneMasterGlyphValue(item.approval_policy || compiled.approval_policy || {}),
27746:         boardroom_events: cloneMasterGlyphValue(item.boardroom_events || compiled.boardroom_events || []),
27747:         compiled_glyph: compiled,
27748:       },
27749:       runtime: {
27750:         input_items: [],
27751:         output_items: [],
27752:         execution_status: "idle",
27753:         last_run_at: null,
27754:         error: null,
27755:       },
27756:     };
27757: 
27758:     graph.nodes.push(stagedNode);
27759:     graph.dirty = true;
```

### Around line 27709: `const graph = getCurrentWorkflowGraphForMasterGlyphStage();`

```js
27664:       name: "Untitled workflow",
27665:       status: "draft",
27666:       nodes: [],
27667:       edges: [],
27668:     };
27669: 
27670:     return window["__aionWorkflowGraph"];
27671:   }
27672: 
27673:   function findMasterGlyphCanvasItem(workflowId) {
27674:     const needle = String(workflowId || "").trim().toLowerCase();
27675:     if (!needle) return null;
27676: 
27677:     const items = typeof listAionMasterGlyphCanvasItems === "function"
27678:       ? listAionMasterGlyphCanvasItems()
27679:       : [];
27680: 
27681:     return items.find((item) => {
27682:       const compiled = item?.compiled_glyph || {};
27683:       return [
27684:         item?.workflow_id,
27685:         item?.id,
27686:         item?.name,
27687:         compiled?.workflow?.workflow_id,
27688:         compiled?.workflow?.name,
27689:       ].some((value) => String(value || "").trim().toLowerCase() === needle);
27690:     }) || null;
27691:   }
27692: 
27693:   function stageMasterGlyphToWorkflowCanvas(workflowId) {
27694:     const item = findMasterGlyphCanvasItem(workflowId);
27695:     if (!item) {
27696:       if (typeof safePatchMessage === "function") {
27697:         safePatchMessage("Could not find callable workflow glyph to stage.", "error");
27698:       }
27699:       return null;
27700:     }
27701: 
27702:     const compiled = cloneMasterGlyphValue(item.compiled_glyph || {});
27703:     const childWorkflowId =
27704:       item.workflow_id ||
27705:       compiled?.workflow?.workflow_id ||
27706:       item.id ||
27707:       workflowId;
27708: 
27709:     const graph = getCurrentWorkflowGraphForMasterGlyphStage();
27710:     graph.nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27711:     graph.edges = Array.isArray(graph.edges) ? graph.edges : [];
27712: 
27713:     const nodeId = `call_workflow_glyph_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
27714:     const x = 220 + (graph.nodes.length % 4) * 280;
27715:     const y = 260 + Math.floor(graph.nodes.length / 4) * 180;
27716: 
27717:     const stagedNode = {
27718:       id: nodeId,
27719:       title: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27720:       label: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27721:       type: "Workflow Glyph",
27722:       icon: "⌁",
27723:       status: "Staged",
27724:       meta: "Staged from Workflow Glyph Library · dry-run only · no execution yet",
27725:       tone: "violet",
27726:       x,
27727:       y,
27728:       dry_run_only: true,
27729:       live_send_enabled: false,
27730:       action_id: "call_workflow_glyph",
27731:       module_id: "workflow.call_workflow_glyph",
27732:       config: {
27733:         action_id: "call_workflow_glyph",
27734:         module_id: "workflow.call_workflow_glyph",
27735:         workflow_id: childWorkflowId,
27736:         child_workflow_id: childWorkflowId,
27737:         glyph_id: item.id || childWorkflowId,
27738:         callable: true,
27739:         dry_run_only: true,
27740:         live_send_enabled: false,
27741:         risk_tier: item.risk_tier || compiled.risk_tier || "low",
27742:         required_connectors: cloneMasterGlyphValue(item.required_connectors || compiled.required_connectors || []),
27743:         inputs_schema: cloneMasterGlyphValue(item.inputs_schema || compiled.inputs_schema || {}),
27744:         outputs_schema: cloneMasterGlyphValue(item.outputs_schema || compiled.outputs_schema || {}),
27745:         approval_policy: cloneMasterGlyphValue(item.approval_policy || compiled.approval_policy || {}),
27746:         boardroom_events: cloneMasterGlyphValue(item.boardroom_events || compiled.boardroom_events || []),
27747:         compiled_glyph: compiled,
27748:       },
27749:       runtime: {
27750:         input_items: [],
27751:         output_items: [],
27752:         execution_status: "idle",
27753:         last_run_at: null,
27754:         error: null,
27755:       },
27756:     };
27757: 
27758:     graph.nodes.push(stagedNode);
27759:     graph.dirty = true;
27760:     graph.updated_at = new Date().toISOString();
27761: 
27762:     window["__aionWorkflowGraph"] = graph;
27763:     if (
27764:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
27765:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
27766:       ) {
27767:         return;
27768:       }
27769:       window.__aionWorkflowSelectedNodeId = nodeId;
27770: 
27771:     try {
27772:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
27773:         compileAndAttachAionWorkflowGlyph(graph);
27774:       }
27775:     } catch (_) {}
27776: 
27777:     try {
27778:       if (typeof persistAionWorkflowDraftState === "function") {
27779:         persistAionWorkflowDraftState();
27780:       }
27781:     } catch (_) {}
27782: 
27783:     if (typeof safePatchMessage === "function") {
27784:       safePatchMessage(`Staged workflow glyph: ${item.name || childWorkflowId}`, "success");
27785:     }
27786: 
27787:     if (typeof requestRender === "function") requestRender();
27788: 
27789:     return stagedNode;
27790:   }
27791: 
27792:   window.__stageAionMasterGlyphToWorkflowCanvas = stageMasterGlyphToWorkflowCanvas;
27793: 
27794:   document.addEventListener("click", (event) => {
27795:     const open = event.target.closest?.("[data-aion-master-glyph-canvas-open='true']");
27796:     if (open) {
27797:       event.preventDefault();
27798:       event.stopPropagation();
```

### Around line 27714: `const x = 220 + (graph.nodes.length % 4) * 280;`

```js
27669: 
27670:     return window["__aionWorkflowGraph"];
27671:   }
27672: 
27673:   function findMasterGlyphCanvasItem(workflowId) {
27674:     const needle = String(workflowId || "").trim().toLowerCase();
27675:     if (!needle) return null;
27676: 
27677:     const items = typeof listAionMasterGlyphCanvasItems === "function"
27678:       ? listAionMasterGlyphCanvasItems()
27679:       : [];
27680: 
27681:     return items.find((item) => {
27682:       const compiled = item?.compiled_glyph || {};
27683:       return [
27684:         item?.workflow_id,
27685:         item?.id,
27686:         item?.name,
27687:         compiled?.workflow?.workflow_id,
27688:         compiled?.workflow?.name,
27689:       ].some((value) => String(value || "").trim().toLowerCase() === needle);
27690:     }) || null;
27691:   }
27692: 
27693:   function stageMasterGlyphToWorkflowCanvas(workflowId) {
27694:     const item = findMasterGlyphCanvasItem(workflowId);
27695:     if (!item) {
27696:       if (typeof safePatchMessage === "function") {
27697:         safePatchMessage("Could not find callable workflow glyph to stage.", "error");
27698:       }
27699:       return null;
27700:     }
27701: 
27702:     const compiled = cloneMasterGlyphValue(item.compiled_glyph || {});
27703:     const childWorkflowId =
27704:       item.workflow_id ||
27705:       compiled?.workflow?.workflow_id ||
27706:       item.id ||
27707:       workflowId;
27708: 
27709:     const graph = getCurrentWorkflowGraphForMasterGlyphStage();
27710:     graph.nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27711:     graph.edges = Array.isArray(graph.edges) ? graph.edges : [];
27712: 
27713:     const nodeId = `call_workflow_glyph_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
27714:     const x = 220 + (graph.nodes.length % 4) * 280;
27715:     const y = 260 + Math.floor(graph.nodes.length / 4) * 180;
27716: 
27717:     const stagedNode = {
27718:       id: nodeId,
27719:       title: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27720:       label: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27721:       type: "Workflow Glyph",
27722:       icon: "⌁",
27723:       status: "Staged",
27724:       meta: "Staged from Workflow Glyph Library · dry-run only · no execution yet",
27725:       tone: "violet",
27726:       x,
27727:       y,
27728:       dry_run_only: true,
27729:       live_send_enabled: false,
27730:       action_id: "call_workflow_glyph",
27731:       module_id: "workflow.call_workflow_glyph",
27732:       config: {
27733:         action_id: "call_workflow_glyph",
27734:         module_id: "workflow.call_workflow_glyph",
27735:         workflow_id: childWorkflowId,
27736:         child_workflow_id: childWorkflowId,
27737:         glyph_id: item.id || childWorkflowId,
27738:         callable: true,
27739:         dry_run_only: true,
27740:         live_send_enabled: false,
27741:         risk_tier: item.risk_tier || compiled.risk_tier || "low",
27742:         required_connectors: cloneMasterGlyphValue(item.required_connectors || compiled.required_connectors || []),
27743:         inputs_schema: cloneMasterGlyphValue(item.inputs_schema || compiled.inputs_schema || {}),
27744:         outputs_schema: cloneMasterGlyphValue(item.outputs_schema || compiled.outputs_schema || {}),
27745:         approval_policy: cloneMasterGlyphValue(item.approval_policy || compiled.approval_policy || {}),
27746:         boardroom_events: cloneMasterGlyphValue(item.boardroom_events || compiled.boardroom_events || []),
27747:         compiled_glyph: compiled,
27748:       },
27749:       runtime: {
27750:         input_items: [],
27751:         output_items: [],
27752:         execution_status: "idle",
27753:         last_run_at: null,
27754:         error: null,
27755:       },
27756:     };
27757: 
27758:     graph.nodes.push(stagedNode);
27759:     graph.dirty = true;
27760:     graph.updated_at = new Date().toISOString();
27761: 
27762:     window["__aionWorkflowGraph"] = graph;
27763:     if (
27764:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
27765:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
27766:       ) {
27767:         return;
27768:       }
27769:       window.__aionWorkflowSelectedNodeId = nodeId;
27770: 
27771:     try {
27772:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
27773:         compileAndAttachAionWorkflowGlyph(graph);
27774:       }
27775:     } catch (_) {}
27776: 
27777:     try {
27778:       if (typeof persistAionWorkflowDraftState === "function") {
27779:         persistAionWorkflowDraftState();
27780:       }
27781:     } catch (_) {}
27782: 
27783:     if (typeof safePatchMessage === "function") {
27784:       safePatchMessage(`Staged workflow glyph: ${item.name || childWorkflowId}`, "success");
27785:     }
27786: 
27787:     if (typeof requestRender === "function") requestRender();
27788: 
27789:     return stagedNode;
27790:   }
27791: 
27792:   window.__stageAionMasterGlyphToWorkflowCanvas = stageMasterGlyphToWorkflowCanvas;
27793: 
27794:   document.addEventListener("click", (event) => {
27795:     const open = event.target.closest?.("[data-aion-master-glyph-canvas-open='true']");
27796:     if (open) {
27797:       event.preventDefault();
27798:       event.stopPropagation();
27799:       window.__aionMasterGlyphCanvasOpen = false;
27800: 
27801:       if (typeof window.__openAionWorkflowGlyphLibrary === "function") {
27802:         window.__openAionWorkflowGlyphLibrary();
27803:       } else if (typeof window.__openAionBackendGlyphLibraryModal === "function") {
```

### Around line 27715: `const y = 260 + Math.floor(graph.nodes.length / 4) * 180;`

```js
27670:     return window["__aionWorkflowGraph"];
27671:   }
27672: 
27673:   function findMasterGlyphCanvasItem(workflowId) {
27674:     const needle = String(workflowId || "").trim().toLowerCase();
27675:     if (!needle) return null;
27676: 
27677:     const items = typeof listAionMasterGlyphCanvasItems === "function"
27678:       ? listAionMasterGlyphCanvasItems()
27679:       : [];
27680: 
27681:     return items.find((item) => {
27682:       const compiled = item?.compiled_glyph || {};
27683:       return [
27684:         item?.workflow_id,
27685:         item?.id,
27686:         item?.name,
27687:         compiled?.workflow?.workflow_id,
27688:         compiled?.workflow?.name,
27689:       ].some((value) => String(value || "").trim().toLowerCase() === needle);
27690:     }) || null;
27691:   }
27692: 
27693:   function stageMasterGlyphToWorkflowCanvas(workflowId) {
27694:     const item = findMasterGlyphCanvasItem(workflowId);
27695:     if (!item) {
27696:       if (typeof safePatchMessage === "function") {
27697:         safePatchMessage("Could not find callable workflow glyph to stage.", "error");
27698:       }
27699:       return null;
27700:     }
27701: 
27702:     const compiled = cloneMasterGlyphValue(item.compiled_glyph || {});
27703:     const childWorkflowId =
27704:       item.workflow_id ||
27705:       compiled?.workflow?.workflow_id ||
27706:       item.id ||
27707:       workflowId;
27708: 
27709:     const graph = getCurrentWorkflowGraphForMasterGlyphStage();
27710:     graph.nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
27711:     graph.edges = Array.isArray(graph.edges) ? graph.edges : [];
27712: 
27713:     const nodeId = `call_workflow_glyph_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
27714:     const x = 220 + (graph.nodes.length % 4) * 280;
27715:     const y = 260 + Math.floor(graph.nodes.length / 4) * 180;
27716: 
27717:     const stagedNode = {
27718:       id: nodeId,
27719:       title: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27720:       label: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27721:       type: "Workflow Glyph",
27722:       icon: "⌁",
27723:       status: "Staged",
27724:       meta: "Staged from Workflow Glyph Library · dry-run only · no execution yet",
27725:       tone: "violet",
27726:       x,
27727:       y,
27728:       dry_run_only: true,
27729:       live_send_enabled: false,
27730:       action_id: "call_workflow_glyph",
27731:       module_id: "workflow.call_workflow_glyph",
27732:       config: {
27733:         action_id: "call_workflow_glyph",
27734:         module_id: "workflow.call_workflow_glyph",
27735:         workflow_id: childWorkflowId,
27736:         child_workflow_id: childWorkflowId,
27737:         glyph_id: item.id || childWorkflowId,
27738:         callable: true,
27739:         dry_run_only: true,
27740:         live_send_enabled: false,
27741:         risk_tier: item.risk_tier || compiled.risk_tier || "low",
27742:         required_connectors: cloneMasterGlyphValue(item.required_connectors || compiled.required_connectors || []),
27743:         inputs_schema: cloneMasterGlyphValue(item.inputs_schema || compiled.inputs_schema || {}),
27744:         outputs_schema: cloneMasterGlyphValue(item.outputs_schema || compiled.outputs_schema || {}),
27745:         approval_policy: cloneMasterGlyphValue(item.approval_policy || compiled.approval_policy || {}),
27746:         boardroom_events: cloneMasterGlyphValue(item.boardroom_events || compiled.boardroom_events || []),
27747:         compiled_glyph: compiled,
27748:       },
27749:       runtime: {
27750:         input_items: [],
27751:         output_items: [],
27752:         execution_status: "idle",
27753:         last_run_at: null,
27754:         error: null,
27755:       },
27756:     };
27757: 
27758:     graph.nodes.push(stagedNode);
27759:     graph.dirty = true;
27760:     graph.updated_at = new Date().toISOString();
27761: 
27762:     window["__aionWorkflowGraph"] = graph;
27763:     if (
27764:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
27765:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
27766:       ) {
27767:         return;
27768:       }
27769:       window.__aionWorkflowSelectedNodeId = nodeId;
27770: 
27771:     try {
27772:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
27773:         compileAndAttachAionWorkflowGlyph(graph);
27774:       }
27775:     } catch (_) {}
27776: 
27777:     try {
27778:       if (typeof persistAionWorkflowDraftState === "function") {
27779:         persistAionWorkflowDraftState();
27780:       }
27781:     } catch (_) {}
27782: 
27783:     if (typeof safePatchMessage === "function") {
27784:       safePatchMessage(`Staged workflow glyph: ${item.name || childWorkflowId}`, "success");
27785:     }
27786: 
27787:     if (typeof requestRender === "function") requestRender();
27788: 
27789:     return stagedNode;
27790:   }
27791: 
27792:   window.__stageAionMasterGlyphToWorkflowCanvas = stageMasterGlyphToWorkflowCanvas;
27793: 
27794:   document.addEventListener("click", (event) => {
27795:     const open = event.target.closest?.("[data-aion-master-glyph-canvas-open='true']");
27796:     if (open) {
27797:       event.preventDefault();
27798:       event.stopPropagation();
27799:       window.__aionMasterGlyphCanvasOpen = false;
27800: 
27801:       if (typeof window.__openAionWorkflowGlyphLibrary === "function") {
27802:         window.__openAionWorkflowGlyphLibrary();
27803:       } else if (typeof window.__openAionBackendGlyphLibraryModal === "function") {
27804:         window.__openAionBackendGlyphLibraryModal();
```

### Around line 27762: `window["__aionWorkflowGraph"] = graph;`

```js
27717:     const stagedNode = {
27718:       id: nodeId,
27719:       title: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27720:       label: `Call ${item.name || compiled?.workflow?.name || childWorkflowId}`,
27721:       type: "Workflow Glyph",
27722:       icon: "⌁",
27723:       status: "Staged",
27724:       meta: "Staged from Workflow Glyph Library · dry-run only · no execution yet",
27725:       tone: "violet",
27726:       x,
27727:       y,
27728:       dry_run_only: true,
27729:       live_send_enabled: false,
27730:       action_id: "call_workflow_glyph",
27731:       module_id: "workflow.call_workflow_glyph",
27732:       config: {
27733:         action_id: "call_workflow_glyph",
27734:         module_id: "workflow.call_workflow_glyph",
27735:         workflow_id: childWorkflowId,
27736:         child_workflow_id: childWorkflowId,
27737:         glyph_id: item.id || childWorkflowId,
27738:         callable: true,
27739:         dry_run_only: true,
27740:         live_send_enabled: false,
27741:         risk_tier: item.risk_tier || compiled.risk_tier || "low",
27742:         required_connectors: cloneMasterGlyphValue(item.required_connectors || compiled.required_connectors || []),
27743:         inputs_schema: cloneMasterGlyphValue(item.inputs_schema || compiled.inputs_schema || {}),
27744:         outputs_schema: cloneMasterGlyphValue(item.outputs_schema || compiled.outputs_schema || {}),
27745:         approval_policy: cloneMasterGlyphValue(item.approval_policy || compiled.approval_policy || {}),
27746:         boardroom_events: cloneMasterGlyphValue(item.boardroom_events || compiled.boardroom_events || []),
27747:         compiled_glyph: compiled,
27748:       },
27749:       runtime: {
27750:         input_items: [],
27751:         output_items: [],
27752:         execution_status: "idle",
27753:         last_run_at: null,
27754:         error: null,
27755:       },
27756:     };
27757: 
27758:     graph.nodes.push(stagedNode);
27759:     graph.dirty = true;
27760:     graph.updated_at = new Date().toISOString();
27761: 
27762:     window["__aionWorkflowGraph"] = graph;
27763:     if (
27764:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
27765:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
27766:       ) {
27767:         return;
27768:       }
27769:       window.__aionWorkflowSelectedNodeId = nodeId;
27770: 
27771:     try {
27772:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
27773:         compileAndAttachAionWorkflowGlyph(graph);
27774:       }
27775:     } catch (_) {}
27776: 
27777:     try {
27778:       if (typeof persistAionWorkflowDraftState === "function") {
27779:         persistAionWorkflowDraftState();
27780:       }
27781:     } catch (_) {}
27782: 
27783:     if (typeof safePatchMessage === "function") {
27784:       safePatchMessage(`Staged workflow glyph: ${item.name || childWorkflowId}`, "success");
27785:     }
27786: 
27787:     if (typeof requestRender === "function") requestRender();
27788: 
27789:     return stagedNode;
27790:   }
27791: 
27792:   window.__stageAionMasterGlyphToWorkflowCanvas = stageMasterGlyphToWorkflowCanvas;
27793: 
27794:   document.addEventListener("click", (event) => {
27795:     const open = event.target.closest?.("[data-aion-master-glyph-canvas-open='true']");
27796:     if (open) {
27797:       event.preventDefault();
27798:       event.stopPropagation();
27799:       window.__aionMasterGlyphCanvasOpen = false;
27800: 
27801:       if (typeof window.__openAionWorkflowGlyphLibrary === "function") {
27802:         window.__openAionWorkflowGlyphLibrary();
27803:       } else if (typeof window.__openAionBackendGlyphLibraryModal === "function") {
27804:         window.__openAionBackendGlyphLibraryModal();
27805:       } else if (typeof window.__renderAionWorkflowGlyphLibraryModal === "function") {
27806:         window.__renderAionWorkflowGlyphLibraryModal();
27807:       }
27808: 
27809:       if (typeof requestRender === "function") requestRender();
27810:       return;
27811:     }
27812: 
27813:     const close = event.target.closest?.("[data-aion-master-glyph-canvas-close='true']");
27814:     if (close) {
27815:       event.preventDefault();
27816:       event.stopPropagation();
27817:       window.__aionMasterGlyphCanvasOpen = false;
27818:       if (typeof requestRender === "function") requestRender();
27819:       return;
27820:     }
27821: 
27822:     const stage = event.target.closest?.("[data-aion-master-glyph-stage-to-canvas='true']");
27823:     if (stage) {
27824:       event.preventDefault();
27825:       event.stopPropagation();
27826:       stageMasterGlyphToWorkflowCanvas(stage.getAttribute("data-workflow-id"));
27827:       return;
27828:     }
27829:   }, true);
27830: }
27831: 
27832: 
27833: function renderAionWorkflowGlyphLibraryLauncher() {
27834:   return `
27835:     <button
27836:       class="btn ghost"
27837:       data-aion-workflow-glyph-library-open="true"
27838:       style="position:fixed;right:22px;bottom:22px;z-index:1200;"
27839:       title="Open Workflow Glyph Library"
27840:     >
27841:       ⌁ Glyph Library
27842:     </button>
27843:   `;
27844: }
27845: 
27846: function renderAionWorkflowGlyphLibraryDrawer() {
27847:   if (window.__aionWorkflowGlyphLibraryOpen !== true) return "";
27848: 
27849:   const businessContainer = getAionWorkflowGlyphLibraryBusinessContainer();
27850:   const items = listAionWorkflowGlyphLibraryItems();
27851: 
```

### Around line 28102: `window.__aionWorkflowGraph = safeGraph;`

```js
28057:     edges: canvasEdges,
28058:   };
28059: }
28060: 
28061: async function saveAionWorkflowCanvasAsCapsule(graph) {
28062:   const safeGraph = graph || getAionWorkflowDraftState();
28063:   const apiBase =
28064:     state.apiBase ||
28065:     state.desktopApiBase ||
28066:     window.AION_API_BASE ||
28067:     "http://127.0.0.1:8080";
28068: 
28069:   const canvas = buildAionWorkflowCanvasCapsulePayload(safeGraph);
28070: 
28071:   const response = await fetch(`${apiBase}/api/workflow-capsules/canvas/compile-save`, {
28072:     method: "POST",
28073:     headers: { "Content-Type": "application/json" },
28074:     body: JSON.stringify({
28075:       canvas,
28076:       scope: "workspace",
28077:       workspace_id: state.workspaceId || safeGraph.business_container || "default_workspace",
28078:       overwrite: true,
28079:       rebuild_registry: true,
28080:     }),
28081:   });
28082: 
28083:   if (!response.ok) {
28084:     throw new Error(`Canvas capsule save failed: HTTP ${response.status}`);
28085:   }
28086: 
28087:   const result = await response.json();
28088:   if (!result?.ok) {
28089:     const reason = Array.isArray(result?.errors)
28090:       ? result.errors.join(", ")
28091:       : result?.error || "Canvas capsule save failed";
28092:     throw new Error(reason);
28093:   }
28094: 
28095:   safeGraph.canonical_key = result.canonical_key || canvas.canonical_key;
28096:   safeGraph.display_glyph = result.display_glyph || canvas.display_glyph;
28097:   safeGraph.capsule_saved_at = new Date().toISOString();
28098:   safeGraph.capsule_path = result.path || "";
28099:   safeGraph.capsule_checksum = result.checksum || "";
28100:   safeGraph.dirty = false;
28101: 
28102:   window.__aionWorkflowGraph = safeGraph;
28103:   persistAionWorkflowDraftState();
28104: 
28105:   return result;
28106: }
28107: 
28108: function renderAionWorkflowGlyphDebugExecutionPanel() {
28109:   if (window.__aionWorkflowGlyphDebugOpen !== true) return "";
28110: 
28111:   const graph = getAionWorkflowDraftState();
28112:   const compiled = graph?.compiled_glyph || compileAionWorkflowGraphToGlyph(graph);
28113:   const stepCount = Array.isArray(compiled?.steps) ? compiled.steps.length : 0;
28114:   const linkCount = Array.isArray(compiled?.flow_links) ? compiled.flow_links.length : 0;
28115: 
28116:   return `
28117:     <div class="aion-workflow-glyph-debug-panel" data-aion-glyph-debug-panel="true">
28118:       <button
28119:         class="aion-dry-run-floating-close"
28120:         type="button"
28121:         data-aion-glyph-debug-close="true"
28122:         title="Close compiled glyph"
28123:       >
28124:         ×
28125:       </button>
28126: 
28127:       <div class="aion-workflow-glyph-debug-head">
28128:         <strong>⌁ Compiled Glyph developer/debug</strong>
28129:         <span>${escapeHtml(String(stepCount))} steps · ${escapeHtml(String(linkCount))} links</span>
28130:       </div>
28131: 
28132:       <pre>${escapeHtml(JSON.stringify(compiled, null, 2))}</pre>
28133:     </div>
28134:   `;
28135: }
28136: 
28137: 
28138: 
28139: 
28140: function getWorkflowArchitectProviderCopy(provider) {
28141:   const key = String(provider || "mock");
28142: 
28143:   if (key === "local_gemma") {
28144:     return "Uses local Ollama/Gemma if available. Still dry-run only.";
28145:   }
28146: 
28147:   if (key === "openai") {
28148:     return "Uses OpenAI provider adapter. Still dry-run only.";
28149:   }
28150: 
28151:   if (key === "claude" || key === "gemini" || key === "grok") {
28152:     return "Provider is visible for future routing but currently fail-closed.";
28153:   }
28154: 
28155:   return "Uses deterministic local mock generation. Safe for testing.";
28156: }
28157: 
28158: function getWorkflowArchitectResultErrors(result) {
28159:   const value =
28160:     result?.errors ||
28161:     result?.review?.errors ||
28162:     result?.validation_errors ||
28163:     result?.review?.validation_errors ||
28164:     [];
28165: 
28166:   if (Array.isArray(value)) {
28167:     return value.map((item) => String(item)).filter(Boolean);
28168:   }
28169: 
28170:   return value ? [String(value)] : [];
28171: }
28172: 
28173: function getWorkflowArchitectResultWarnings(result) {
28174:   const value =
28175:     result?.warnings ||
28176:     result?.review?.warnings ||
28177:     result?.validation_warnings ||
28178:     result?.review?.validation_warnings ||
28179:     [];
28180: 
28181:   if (Array.isArray(value)) {
28182:     return value.map((item) => String(item)).filter(Boolean);
28183:   }
28184: 
28185:   return value ? [String(value)] : [];
28186: }
28187: 
28188: 
28189: 
28190: /* ============================================================
28191:    AI Architect Canvas Node Builder
```

### Around line 28111: `const graph = getAionWorkflowDraftState();`

```js
28066:     window.AION_API_BASE ||
28067:     "http://127.0.0.1:8080";
28068: 
28069:   const canvas = buildAionWorkflowCanvasCapsulePayload(safeGraph);
28070: 
28071:   const response = await fetch(`${apiBase}/api/workflow-capsules/canvas/compile-save`, {
28072:     method: "POST",
28073:     headers: { "Content-Type": "application/json" },
28074:     body: JSON.stringify({
28075:       canvas,
28076:       scope: "workspace",
28077:       workspace_id: state.workspaceId || safeGraph.business_container || "default_workspace",
28078:       overwrite: true,
28079:       rebuild_registry: true,
28080:     }),
28081:   });
28082: 
28083:   if (!response.ok) {
28084:     throw new Error(`Canvas capsule save failed: HTTP ${response.status}`);
28085:   }
28086: 
28087:   const result = await response.json();
28088:   if (!result?.ok) {
28089:     const reason = Array.isArray(result?.errors)
28090:       ? result.errors.join(", ")
28091:       : result?.error || "Canvas capsule save failed";
28092:     throw new Error(reason);
28093:   }
28094: 
28095:   safeGraph.canonical_key = result.canonical_key || canvas.canonical_key;
28096:   safeGraph.display_glyph = result.display_glyph || canvas.display_glyph;
28097:   safeGraph.capsule_saved_at = new Date().toISOString();
28098:   safeGraph.capsule_path = result.path || "";
28099:   safeGraph.capsule_checksum = result.checksum || "";
28100:   safeGraph.dirty = false;
28101: 
28102:   window.__aionWorkflowGraph = safeGraph;
28103:   persistAionWorkflowDraftState();
28104: 
28105:   return result;
28106: }
28107: 
28108: function renderAionWorkflowGlyphDebugExecutionPanel() {
28109:   if (window.__aionWorkflowGlyphDebugOpen !== true) return "";
28110: 
28111:   const graph = getAionWorkflowDraftState();
28112:   const compiled = graph?.compiled_glyph || compileAionWorkflowGraphToGlyph(graph);
28113:   const stepCount = Array.isArray(compiled?.steps) ? compiled.steps.length : 0;
28114:   const linkCount = Array.isArray(compiled?.flow_links) ? compiled.flow_links.length : 0;
28115: 
28116:   return `
28117:     <div class="aion-workflow-glyph-debug-panel" data-aion-glyph-debug-panel="true">
28118:       <button
28119:         class="aion-dry-run-floating-close"
28120:         type="button"
28121:         data-aion-glyph-debug-close="true"
28122:         title="Close compiled glyph"
28123:       >
28124:         ×
28125:       </button>
28126: 
28127:       <div class="aion-workflow-glyph-debug-head">
28128:         <strong>⌁ Compiled Glyph developer/debug</strong>
28129:         <span>${escapeHtml(String(stepCount))} steps · ${escapeHtml(String(linkCount))} links</span>
28130:       </div>
28131: 
28132:       <pre>${escapeHtml(JSON.stringify(compiled, null, 2))}</pre>
28133:     </div>
28134:   `;
28135: }
28136: 
28137: 
28138: 
28139: 
28140: function getWorkflowArchitectProviderCopy(provider) {
28141:   const key = String(provider || "mock");
28142: 
28143:   if (key === "local_gemma") {
28144:     return "Uses local Ollama/Gemma if available. Still dry-run only.";
28145:   }
28146: 
28147:   if (key === "openai") {
28148:     return "Uses OpenAI provider adapter. Still dry-run only.";
28149:   }
28150: 
28151:   if (key === "claude" || key === "gemini" || key === "grok") {
28152:     return "Provider is visible for future routing but currently fail-closed.";
28153:   }
28154: 
28155:   return "Uses deterministic local mock generation. Safe for testing.";
28156: }
28157: 
28158: function getWorkflowArchitectResultErrors(result) {
28159:   const value =
28160:     result?.errors ||
28161:     result?.review?.errors ||
28162:     result?.validation_errors ||
28163:     result?.review?.validation_errors ||
28164:     [];
28165: 
28166:   if (Array.isArray(value)) {
28167:     return value.map((item) => String(item)).filter(Boolean);
28168:   }
28169: 
28170:   return value ? [String(value)] : [];
28171: }
28172: 
28173: function getWorkflowArchitectResultWarnings(result) {
28174:   const value =
28175:     result?.warnings ||
28176:     result?.review?.warnings ||
28177:     result?.validation_warnings ||
28178:     result?.review?.validation_warnings ||
28179:     [];
28180: 
28181:   if (Array.isArray(value)) {
28182:     return value.map((item) => String(item)).filter(Boolean);
28183:   }
28184: 
28185:   return value ? [String(value)] : [];
28186: }
28187: 
28188: 
28189: 
28190: /* ============================================================
28191:    AI Architect Canvas Node Builder
28192:    Separate AI build canvas, not the main workflow canvas.
28193:    ============================================================ */
28194: 
28195: function getAionArchitectCanvasState() {
28196:   const current = window.__aionArchitectCanvasState || {};
28197: 
28198:   if (!Array.isArray(current.steps) || current.steps.length === 0) {
28199:     current.steps = [
28200:       {
```

### Around line 29342: `if (!window.__aionWorkflowGraph) {`

```js
29297:     "content.fill_template": {
29298:       title: "Fill template",
29299:       type: "Content Asset",
29300:       icon: "T",
29301:       status: "Dry-run",
29302:       meta: "Fill text/email/doc template",
29303:       tone: "blue",
29304:       config: { template: "", variables: {}, output: "filled_template" },
29305:     },
29306:   };
29307: 
29308:   const mapped = map[actionId] || map[module.id] || base;
29309: 
29310:   return {
29311:     ...base,
29312:     ...mapped,
29313:     config: {
29314:       ...(base.config || {}),
29315:       ...(mapped.config || {}),
29316:       action_id: actionId,
29317:       module_id: module.id || actionId,
29318:       app,
29319:       connector: module.connector || app,
29320:       kind,
29321:       safety: module.safety || mapped.config?.safety || base.config?.safety || "dry_run",
29322:       requires_approval:
29323:         module.requires_approval === true ||
29324:         mapped.config?.approval_required === true ||
29325:         false,
29326:     },
29327:   };
29328: }
29329: 
29330: function addAionUnifiedRealNodeFromModule(module) {
29331:   const mappedNode = getAionUnifiedRealNodeFromModule(module);
29332:   if (!mappedNode) return false;
29333: 
29334:   if (mappedNode.locked === true) {
29335:     safeAionDesktopPatch({
29336:       message: `${mappedNode.title || "This module"} is visible but not wired yet.`,
29337:       messageTone: "info",
29338:     });
29339:     return false;
29340:   }
29341: 
29342:   if (!window.__aionWorkflowGraph) {
29343:     window.__aionWorkflowGraph = {
29344:       workflow_id: createAionWorkflowId(),
29345:       name: "Untitled workflow",
29346:       status: "draft",
29347:       nodes: [],
29348:       edges: [],
29349:     };
29350:   }
29351: 
29352:   const graph = window.__aionWorkflowGraph;
29353:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
29354:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
29355: 
29356:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
29357:   const selectedNode = selectedNodeId
29358:     ? nodes.find((node) => node.id === selectedNodeId)
29359:     : null;
29360: 
29361:   const anchorNode =
29362:     selectedNode ||
29363:     nodes[nodes.length - 1] ||
29364:     { id: null, x: 160, y: 240 };
29365: 
29366:   const safeId = String(mappedNode.config?.action_id || mappedNode.title || "step")
29367:     .replace(/[^a-z0-9_]+/gi, "_")
29368:     .replace(/^_+|_+$/g, "")
29369:     .toLowerCase();
29370: 
29371:   const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
29372:   const isBranchInsert =
29373:     anchorNode?.id &&
29374:     (
29375:       (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
29376:       (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
29377:     );
29378: 
29379:   const routerRoutes =
29380:     typeof getAionWorkflowRouterRoutes === "function"
29381:       ? getAionWorkflowRouterRoutes(anchorNode)
29382:       : [];
29383: 
29384:   const routerRouteIndex = routerRoutes.findIndex(
29385:     (route) => String(route.id).toLowerCase() === pendingBranchCondition,
29386:   );
29387: 
29388:   const branchYOffset =
29389:     typeof isAionWorkflowRouterNode === "function" &&
29390:     isAionWorkflowRouterNode(anchorNode) &&
29391:     routerRouteIndex >= 0
29392:       ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
29393:       : pendingBranchCondition === "false" || pendingBranchCondition === "else"
29394:         ? 170
29395:         : pendingBranchCondition === "true"
29396:           ? -130
29397:           : 0;
29398: 
29399:   const mergePlacement = getAionWorkflowMergePlacement(nodes, anchorNode);
29400: 
29401:   const newNode = {
29402:     id: `node_${safeId}_${Date.now()}`,
29403:     ...mappedNode,
29404:     x: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.x : Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
29405:     y: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.y : Number(anchorNode.y || 240) + branchYOffset,
29406:   };
29407: 
29408:   const newIsMerge = isAionWorkflowNewMergeNode(newNode);
29409: 
29410:   const anchorIndex = anchorNode?.id
29411:     ? nodes.findIndex((node) => node.id === anchorNode.id)
29412:     : -1;
29413: 
29414:   const nextNodes =
29415:     anchorIndex >= 0
29416:       ? [
29417:           ...nodes.slice(0, anchorIndex + 1),
29418:           newNode,
29419:           ...nodes.slice(anchorIndex + 1),
29420:         ]
29421:       : [...nodes, newNode];
29422: 
29423:   const outgoingEdges = anchorNode?.id
29424:     ? edges.filter((edge) => edge.from === anchorNode.id)
29425:     : [];
29426: 
29427:   const branchCondition = getAionWorkflowNewEdgeCondition(anchorNode);
29428: 
29429:   const remainingEdges = anchorNode?.id
29430:     ? isBranchInsert
29431:       ? edges.filter(
```

### Around line 29343: `window.__aionWorkflowGraph = {`

```js
29298:       title: "Fill template",
29299:       type: "Content Asset",
29300:       icon: "T",
29301:       status: "Dry-run",
29302:       meta: "Fill text/email/doc template",
29303:       tone: "blue",
29304:       config: { template: "", variables: {}, output: "filled_template" },
29305:     },
29306:   };
29307: 
29308:   const mapped = map[actionId] || map[module.id] || base;
29309: 
29310:   return {
29311:     ...base,
29312:     ...mapped,
29313:     config: {
29314:       ...(base.config || {}),
29315:       ...(mapped.config || {}),
29316:       action_id: actionId,
29317:       module_id: module.id || actionId,
29318:       app,
29319:       connector: module.connector || app,
29320:       kind,
29321:       safety: module.safety || mapped.config?.safety || base.config?.safety || "dry_run",
29322:       requires_approval:
29323:         module.requires_approval === true ||
29324:         mapped.config?.approval_required === true ||
29325:         false,
29326:     },
29327:   };
29328: }
29329: 
29330: function addAionUnifiedRealNodeFromModule(module) {
29331:   const mappedNode = getAionUnifiedRealNodeFromModule(module);
29332:   if (!mappedNode) return false;
29333: 
29334:   if (mappedNode.locked === true) {
29335:     safeAionDesktopPatch({
29336:       message: `${mappedNode.title || "This module"} is visible but not wired yet.`,
29337:       messageTone: "info",
29338:     });
29339:     return false;
29340:   }
29341: 
29342:   if (!window.__aionWorkflowGraph) {
29343:     window.__aionWorkflowGraph = {
29344:       workflow_id: createAionWorkflowId(),
29345:       name: "Untitled workflow",
29346:       status: "draft",
29347:       nodes: [],
29348:       edges: [],
29349:     };
29350:   }
29351: 
29352:   const graph = window.__aionWorkflowGraph;
29353:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
29354:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
29355: 
29356:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
29357:   const selectedNode = selectedNodeId
29358:     ? nodes.find((node) => node.id === selectedNodeId)
29359:     : null;
29360: 
29361:   const anchorNode =
29362:     selectedNode ||
29363:     nodes[nodes.length - 1] ||
29364:     { id: null, x: 160, y: 240 };
29365: 
29366:   const safeId = String(mappedNode.config?.action_id || mappedNode.title || "step")
29367:     .replace(/[^a-z0-9_]+/gi, "_")
29368:     .replace(/^_+|_+$/g, "")
29369:     .toLowerCase();
29370: 
29371:   const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
29372:   const isBranchInsert =
29373:     anchorNode?.id &&
29374:     (
29375:       (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
29376:       (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
29377:     );
29378: 
29379:   const routerRoutes =
29380:     typeof getAionWorkflowRouterRoutes === "function"
29381:       ? getAionWorkflowRouterRoutes(anchorNode)
29382:       : [];
29383: 
29384:   const routerRouteIndex = routerRoutes.findIndex(
29385:     (route) => String(route.id).toLowerCase() === pendingBranchCondition,
29386:   );
29387: 
29388:   const branchYOffset =
29389:     typeof isAionWorkflowRouterNode === "function" &&
29390:     isAionWorkflowRouterNode(anchorNode) &&
29391:     routerRouteIndex >= 0
29392:       ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
29393:       : pendingBranchCondition === "false" || pendingBranchCondition === "else"
29394:         ? 170
29395:         : pendingBranchCondition === "true"
29396:           ? -130
29397:           : 0;
29398: 
29399:   const mergePlacement = getAionWorkflowMergePlacement(nodes, anchorNode);
29400: 
29401:   const newNode = {
29402:     id: `node_${safeId}_${Date.now()}`,
29403:     ...mappedNode,
29404:     x: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.x : Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
29405:     y: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.y : Number(anchorNode.y || 240) + branchYOffset,
29406:   };
29407: 
29408:   const newIsMerge = isAionWorkflowNewMergeNode(newNode);
29409: 
29410:   const anchorIndex = anchorNode?.id
29411:     ? nodes.findIndex((node) => node.id === anchorNode.id)
29412:     : -1;
29413: 
29414:   const nextNodes =
29415:     anchorIndex >= 0
29416:       ? [
29417:           ...nodes.slice(0, anchorIndex + 1),
29418:           newNode,
29419:           ...nodes.slice(anchorIndex + 1),
29420:         ]
29421:       : [...nodes, newNode];
29422: 
29423:   const outgoingEdges = anchorNode?.id
29424:     ? edges.filter((edge) => edge.from === anchorNode.id)
29425:     : [];
29426: 
29427:   const branchCondition = getAionWorkflowNewEdgeCondition(anchorNode);
29428: 
29429:   const remainingEdges = anchorNode?.id
29430:     ? isBranchInsert
29431:       ? edges.filter(
29432:           (edge) =>
```

### Around line 29352: `const graph = window.__aionWorkflowGraph;`

```js
29307: 
29308:   const mapped = map[actionId] || map[module.id] || base;
29309: 
29310:   return {
29311:     ...base,
29312:     ...mapped,
29313:     config: {
29314:       ...(base.config || {}),
29315:       ...(mapped.config || {}),
29316:       action_id: actionId,
29317:       module_id: module.id || actionId,
29318:       app,
29319:       connector: module.connector || app,
29320:       kind,
29321:       safety: module.safety || mapped.config?.safety || base.config?.safety || "dry_run",
29322:       requires_approval:
29323:         module.requires_approval === true ||
29324:         mapped.config?.approval_required === true ||
29325:         false,
29326:     },
29327:   };
29328: }
29329: 
29330: function addAionUnifiedRealNodeFromModule(module) {
29331:   const mappedNode = getAionUnifiedRealNodeFromModule(module);
29332:   if (!mappedNode) return false;
29333: 
29334:   if (mappedNode.locked === true) {
29335:     safeAionDesktopPatch({
29336:       message: `${mappedNode.title || "This module"} is visible but not wired yet.`,
29337:       messageTone: "info",
29338:     });
29339:     return false;
29340:   }
29341: 
29342:   if (!window.__aionWorkflowGraph) {
29343:     window.__aionWorkflowGraph = {
29344:       workflow_id: createAionWorkflowId(),
29345:       name: "Untitled workflow",
29346:       status: "draft",
29347:       nodes: [],
29348:       edges: [],
29349:     };
29350:   }
29351: 
29352:   const graph = window.__aionWorkflowGraph;
29353:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
29354:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
29355: 
29356:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
29357:   const selectedNode = selectedNodeId
29358:     ? nodes.find((node) => node.id === selectedNodeId)
29359:     : null;
29360: 
29361:   const anchorNode =
29362:     selectedNode ||
29363:     nodes[nodes.length - 1] ||
29364:     { id: null, x: 160, y: 240 };
29365: 
29366:   const safeId = String(mappedNode.config?.action_id || mappedNode.title || "step")
29367:     .replace(/[^a-z0-9_]+/gi, "_")
29368:     .replace(/^_+|_+$/g, "")
29369:     .toLowerCase();
29370: 
29371:   const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
29372:   const isBranchInsert =
29373:     anchorNode?.id &&
29374:     (
29375:       (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
29376:       (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
29377:     );
29378: 
29379:   const routerRoutes =
29380:     typeof getAionWorkflowRouterRoutes === "function"
29381:       ? getAionWorkflowRouterRoutes(anchorNode)
29382:       : [];
29383: 
29384:   const routerRouteIndex = routerRoutes.findIndex(
29385:     (route) => String(route.id).toLowerCase() === pendingBranchCondition,
29386:   );
29387: 
29388:   const branchYOffset =
29389:     typeof isAionWorkflowRouterNode === "function" &&
29390:     isAionWorkflowRouterNode(anchorNode) &&
29391:     routerRouteIndex >= 0
29392:       ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
29393:       : pendingBranchCondition === "false" || pendingBranchCondition === "else"
29394:         ? 170
29395:         : pendingBranchCondition === "true"
29396:           ? -130
29397:           : 0;
29398: 
29399:   const mergePlacement = getAionWorkflowMergePlacement(nodes, anchorNode);
29400: 
29401:   const newNode = {
29402:     id: `node_${safeId}_${Date.now()}`,
29403:     ...mappedNode,
29404:     x: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.x : Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
29405:     y: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.y : Number(anchorNode.y || 240) + branchYOffset,
29406:   };
29407: 
29408:   const newIsMerge = isAionWorkflowNewMergeNode(newNode);
29409: 
29410:   const anchorIndex = anchorNode?.id
29411:     ? nodes.findIndex((node) => node.id === anchorNode.id)
29412:     : -1;
29413: 
29414:   const nextNodes =
29415:     anchorIndex >= 0
29416:       ? [
29417:           ...nodes.slice(0, anchorIndex + 1),
29418:           newNode,
29419:           ...nodes.slice(anchorIndex + 1),
29420:         ]
29421:       : [...nodes, newNode];
29422: 
29423:   const outgoingEdges = anchorNode?.id
29424:     ? edges.filter((edge) => edge.from === anchorNode.id)
29425:     : [];
29426: 
29427:   const branchCondition = getAionWorkflowNewEdgeCondition(anchorNode);
29428: 
29429:   const remainingEdges = anchorNode?.id
29430:     ? isBranchInsert
29431:       ? edges.filter(
29432:           (edge) =>
29433:             !(
29434:               String(edge.from) === String(anchorNode.id) &&
29435:               String(edge.condition || "success") === String(branchCondition)
29436:             ),
29437:         )
29438:       : edges.filter((edge) => edge.from !== anchorNode.id)
29439:     : edges;
29440: 
29441:   const insertedEdges = anchorNode?.id && !newIsMerge
```

### Around line 29363: `nodes[nodes.length - 1] ||`

```js
29318:       app,
29319:       connector: module.connector || app,
29320:       kind,
29321:       safety: module.safety || mapped.config?.safety || base.config?.safety || "dry_run",
29322:       requires_approval:
29323:         module.requires_approval === true ||
29324:         mapped.config?.approval_required === true ||
29325:         false,
29326:     },
29327:   };
29328: }
29329: 
29330: function addAionUnifiedRealNodeFromModule(module) {
29331:   const mappedNode = getAionUnifiedRealNodeFromModule(module);
29332:   if (!mappedNode) return false;
29333: 
29334:   if (mappedNode.locked === true) {
29335:     safeAionDesktopPatch({
29336:       message: `${mappedNode.title || "This module"} is visible but not wired yet.`,
29337:       messageTone: "info",
29338:     });
29339:     return false;
29340:   }
29341: 
29342:   if (!window.__aionWorkflowGraph) {
29343:     window.__aionWorkflowGraph = {
29344:       workflow_id: createAionWorkflowId(),
29345:       name: "Untitled workflow",
29346:       status: "draft",
29347:       nodes: [],
29348:       edges: [],
29349:     };
29350:   }
29351: 
29352:   const graph = window.__aionWorkflowGraph;
29353:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
29354:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
29355: 
29356:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
29357:   const selectedNode = selectedNodeId
29358:     ? nodes.find((node) => node.id === selectedNodeId)
29359:     : null;
29360: 
29361:   const anchorNode =
29362:     selectedNode ||
29363:     nodes[nodes.length - 1] ||
29364:     { id: null, x: 160, y: 240 };
29365: 
29366:   const safeId = String(mappedNode.config?.action_id || mappedNode.title || "step")
29367:     .replace(/[^a-z0-9_]+/gi, "_")
29368:     .replace(/^_+|_+$/g, "")
29369:     .toLowerCase();
29370: 
29371:   const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
29372:   const isBranchInsert =
29373:     anchorNode?.id &&
29374:     (
29375:       (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
29376:       (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
29377:     );
29378: 
29379:   const routerRoutes =
29380:     typeof getAionWorkflowRouterRoutes === "function"
29381:       ? getAionWorkflowRouterRoutes(anchorNode)
29382:       : [];
29383: 
29384:   const routerRouteIndex = routerRoutes.findIndex(
29385:     (route) => String(route.id).toLowerCase() === pendingBranchCondition,
29386:   );
29387: 
29388:   const branchYOffset =
29389:     typeof isAionWorkflowRouterNode === "function" &&
29390:     isAionWorkflowRouterNode(anchorNode) &&
29391:     routerRouteIndex >= 0
29392:       ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
29393:       : pendingBranchCondition === "false" || pendingBranchCondition === "else"
29394:         ? 170
29395:         : pendingBranchCondition === "true"
29396:           ? -130
29397:           : 0;
29398: 
29399:   const mergePlacement = getAionWorkflowMergePlacement(nodes, anchorNode);
29400: 
29401:   const newNode = {
29402:     id: `node_${safeId}_${Date.now()}`,
29403:     ...mappedNode,
29404:     x: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.x : Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
29405:     y: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.y : Number(anchorNode.y || 240) + branchYOffset,
29406:   };
29407: 
29408:   const newIsMerge = isAionWorkflowNewMergeNode(newNode);
29409: 
29410:   const anchorIndex = anchorNode?.id
29411:     ? nodes.findIndex((node) => node.id === anchorNode.id)
29412:     : -1;
29413: 
29414:   const nextNodes =
29415:     anchorIndex >= 0
29416:       ? [
29417:           ...nodes.slice(0, anchorIndex + 1),
29418:           newNode,
29419:           ...nodes.slice(anchorIndex + 1),
29420:         ]
29421:       : [...nodes, newNode];
29422: 
29423:   const outgoingEdges = anchorNode?.id
29424:     ? edges.filter((edge) => edge.from === anchorNode.id)
29425:     : [];
29426: 
29427:   const branchCondition = getAionWorkflowNewEdgeCondition(anchorNode);
29428: 
29429:   const remainingEdges = anchorNode?.id
29430:     ? isBranchInsert
29431:       ? edges.filter(
29432:           (edge) =>
29433:             !(
29434:               String(edge.from) === String(anchorNode.id) &&
29435:               String(edge.condition || "success") === String(branchCondition)
29436:             ),
29437:         )
29438:       : edges.filter((edge) => edge.from !== anchorNode.id)
29439:     : edges;
29440: 
29441:   const insertedEdges = anchorNode?.id && !newIsMerge
29442:     ? isBranchInsert
29443:       ? [
29444:           {
29445:             from: anchorNode.id,
29446:             to: newNode.id,
29447:             condition: branchCondition,
29448:           },
29449:         ]
29450:       : [
29451:           {
29452:             from: anchorNode.id,
```

### Around line 30838: `if (!window.__aionWorkflowGraph) {`

```js
30793:   }
30794: 
30795:   if (wantsApproval || fullWorkflow) {
30796:     steps.push({
30797:       id: makeId("approval"),
30798:       title: "Human approval",
30799:       type: "Flow control",
30800:       icon: "✓",
30801:       status: "Required",
30802:       meta: "Review before external write/send",
30803:       tone: "purple",
30804:       config: {
30805:         action_id: "aion.human_approval",
30806:         connector: "approval",
30807:         source: "{{gmail_draft}}",
30808:         fields: "draft, reason, risk",
30809:         outputs: "approval_decision",
30810:         approval_requirement: "required",
30811:       },
30812:     });
30813:   }
30814: 
30815:   if (!steps.length) {
30816:     steps.push({
30817:       id: makeId("aion_prompt"),
30818:       title: "Aion step",
30819:       type: "AI / Aion",
30820:       icon: "AI",
30821:       status: "Draft",
30822:       meta: "Generated from prompt",
30823:       tone: "blue",
30824:       config: {
30825:         action_id: "aion.simple_prompt",
30826:         connector: "aion",
30827:         source: prompt,
30828:         fields: "input",
30829:         outputs: "aion_result",
30830:       },
30831:     });
30832:   }
30833: 
30834:   return steps;
30835: }
30836: 
30837: function appendAionUnifiedSuggestedStepsToMainWorkflow(steps) {
30838:   if (!window.__aionWorkflowGraph) {
30839:     window.__aionWorkflowGraph = getAionWorkflowDraftState();
30840:   }
30841: 
30842:   const graph = window.__aionWorkflowGraph || {};
30843:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
30844:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
30845: 
30846:   let previousNode = nodes[nodes.length - 1] || null;
30847: 
30848:   steps.forEach((step, index) => {
30849:     const nodeId = step.id || `ai_step_${Date.now()}_${index}`;
30850:     const x = previousNode?.x != null ? Number(previousNode.x) + 320 : 360 + index * 320;
30851:     const y = previousNode?.y != null ? Number(previousNode.y) : 260;
30852: 
30853:     const node = {
30854:       id: nodeId,
30855:       title: step.title || "Aion step",
30856:       type: step.type || "AI / Aion",
30857:       icon: step.icon || "AI",
30858:       status: step.status || "Draft",
30859:       meta: step.meta || "Generated by Aion",
30860:       tone: step.tone || "blue",
30861:       x,
30862:       y,
30863:       config: {
30864:         ...(step.config || {}),
30865:         generated_by: "aion_unified_canvas_builder",
30866:         dry_run: true,
30867:       },
30868:     };
30869: 
30870:     nodes.push(node);
30871: 
30872:     if (previousNode?.id) {
30873:       edges.push({
30874:         id: `edge_${previousNode.id}_${nodeId}`,
30875:         source: previousNode.id,
30876:         target: nodeId,
30877:       });
30878:     }
30879: 
30880:     previousNode = node;
30881:   });
30882: 
30883:   graph.nodes = nodes;
30884:   graph.edges = edges;
30885:   graph.dirty = true;
30886:   graph.status = "draft";
30887: 
30888:   window["__aionWorkflowGraph"] = graph;
30889: 
30890:   if (typeof persistAionWorkflowDraftState === "function") {
30891:     persistAionWorkflowDraftState();
30892:   }
30893: 
30894:   if (typeof compileAndAttachAionWorkflowGlyph === "function") {
30895:     compileAndAttachAionWorkflowGlyph(graph);
30896:   }
30897: 
30898:   return graph;
30899: }
30900: 
30901: 
30902: 
30903: 
30904: function getAionWorkflowFileCabinetState() {
30905:   window.__aionWorkflowFileCabinetOpen =
30906:     window.__aionWorkflowFileCabinetOpen === true;
30907: 
30908:   return {
30909:     open: window.__aionWorkflowFileCabinetOpen,
30910:   };
30911: }
30912: 
30913: function getAionWorkflowFileCabinetItems() {
30914:   const graph =
30915:     (typeof getAionWorkflowDraftState === "function"
30916:       ? getAionWorkflowDraftState()
30917:       : window.__aionWorkflowGraph) || {};
30918: 
30919:   const currentWorkflowName = graph.name || "Untitled workflow";
30920:   const currentWorkflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
30921: 
30922:   return {
30923:     departments: [
30924:       {
30925:         id: "marketing",
30926:         label: "Marketing",
30927:         workflows: ["Social post workflow", "Campaign approval flow"],
```

### Around line 30839: `window.__aionWorkflowGraph = getAionWorkflowDraftState();`

```js
30794: 
30795:   if (wantsApproval || fullWorkflow) {
30796:     steps.push({
30797:       id: makeId("approval"),
30798:       title: "Human approval",
30799:       type: "Flow control",
30800:       icon: "✓",
30801:       status: "Required",
30802:       meta: "Review before external write/send",
30803:       tone: "purple",
30804:       config: {
30805:         action_id: "aion.human_approval",
30806:         connector: "approval",
30807:         source: "{{gmail_draft}}",
30808:         fields: "draft, reason, risk",
30809:         outputs: "approval_decision",
30810:         approval_requirement: "required",
30811:       },
30812:     });
30813:   }
30814: 
30815:   if (!steps.length) {
30816:     steps.push({
30817:       id: makeId("aion_prompt"),
30818:       title: "Aion step",
30819:       type: "AI / Aion",
30820:       icon: "AI",
30821:       status: "Draft",
30822:       meta: "Generated from prompt",
30823:       tone: "blue",
30824:       config: {
30825:         action_id: "aion.simple_prompt",
30826:         connector: "aion",
30827:         source: prompt,
30828:         fields: "input",
30829:         outputs: "aion_result",
30830:       },
30831:     });
30832:   }
30833: 
30834:   return steps;
30835: }
30836: 
30837: function appendAionUnifiedSuggestedStepsToMainWorkflow(steps) {
30838:   if (!window.__aionWorkflowGraph) {
30839:     window.__aionWorkflowGraph = getAionWorkflowDraftState();
30840:   }
30841: 
30842:   const graph = window.__aionWorkflowGraph || {};
30843:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
30844:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
30845: 
30846:   let previousNode = nodes[nodes.length - 1] || null;
30847: 
30848:   steps.forEach((step, index) => {
30849:     const nodeId = step.id || `ai_step_${Date.now()}_${index}`;
30850:     const x = previousNode?.x != null ? Number(previousNode.x) + 320 : 360 + index * 320;
30851:     const y = previousNode?.y != null ? Number(previousNode.y) : 260;
30852: 
30853:     const node = {
30854:       id: nodeId,
30855:       title: step.title || "Aion step",
30856:       type: step.type || "AI / Aion",
30857:       icon: step.icon || "AI",
30858:       status: step.status || "Draft",
30859:       meta: step.meta || "Generated by Aion",
30860:       tone: step.tone || "blue",
30861:       x,
30862:       y,
30863:       config: {
30864:         ...(step.config || {}),
30865:         generated_by: "aion_unified_canvas_builder",
30866:         dry_run: true,
30867:       },
30868:     };
30869: 
30870:     nodes.push(node);
30871: 
30872:     if (previousNode?.id) {
30873:       edges.push({
30874:         id: `edge_${previousNode.id}_${nodeId}`,
30875:         source: previousNode.id,
30876:         target: nodeId,
30877:       });
30878:     }
30879: 
30880:     previousNode = node;
30881:   });
30882: 
30883:   graph.nodes = nodes;
30884:   graph.edges = edges;
30885:   graph.dirty = true;
30886:   graph.status = "draft";
30887: 
30888:   window["__aionWorkflowGraph"] = graph;
30889: 
30890:   if (typeof persistAionWorkflowDraftState === "function") {
30891:     persistAionWorkflowDraftState();
30892:   }
30893: 
30894:   if (typeof compileAndAttachAionWorkflowGlyph === "function") {
30895:     compileAndAttachAionWorkflowGlyph(graph);
30896:   }
30897: 
30898:   return graph;
30899: }
30900: 
30901: 
30902: 
30903: 
30904: function getAionWorkflowFileCabinetState() {
30905:   window.__aionWorkflowFileCabinetOpen =
30906:     window.__aionWorkflowFileCabinetOpen === true;
30907: 
30908:   return {
30909:     open: window.__aionWorkflowFileCabinetOpen,
30910:   };
30911: }
30912: 
30913: function getAionWorkflowFileCabinetItems() {
30914:   const graph =
30915:     (typeof getAionWorkflowDraftState === "function"
30916:       ? getAionWorkflowDraftState()
30917:       : window.__aionWorkflowGraph) || {};
30918: 
30919:   const currentWorkflowName = graph.name || "Untitled workflow";
30920:   const currentWorkflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
30921: 
30922:   return {
30923:     departments: [
30924:       {
30925:         id: "marketing",
30926:         label: "Marketing",
30927:         workflows: ["Social post workflow", "Campaign approval flow"],
30928:         assets: ["Caption templates", "Brand voice notes"],
```

### Around line 30842: `const graph = window.__aionWorkflowGraph || {};`

```js
30797:       id: makeId("approval"),
30798:       title: "Human approval",
30799:       type: "Flow control",
30800:       icon: "✓",
30801:       status: "Required",
30802:       meta: "Review before external write/send",
30803:       tone: "purple",
30804:       config: {
30805:         action_id: "aion.human_approval",
30806:         connector: "approval",
30807:         source: "{{gmail_draft}}",
30808:         fields: "draft, reason, risk",
30809:         outputs: "approval_decision",
30810:         approval_requirement: "required",
30811:       },
30812:     });
30813:   }
30814: 
30815:   if (!steps.length) {
30816:     steps.push({
30817:       id: makeId("aion_prompt"),
30818:       title: "Aion step",
30819:       type: "AI / Aion",
30820:       icon: "AI",
30821:       status: "Draft",
30822:       meta: "Generated from prompt",
30823:       tone: "blue",
30824:       config: {
30825:         action_id: "aion.simple_prompt",
30826:         connector: "aion",
30827:         source: prompt,
30828:         fields: "input",
30829:         outputs: "aion_result",
30830:       },
30831:     });
30832:   }
30833: 
30834:   return steps;
30835: }
30836: 
30837: function appendAionUnifiedSuggestedStepsToMainWorkflow(steps) {
30838:   if (!window.__aionWorkflowGraph) {
30839:     window.__aionWorkflowGraph = getAionWorkflowDraftState();
30840:   }
30841: 
30842:   const graph = window.__aionWorkflowGraph || {};
30843:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
30844:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
30845: 
30846:   let previousNode = nodes[nodes.length - 1] || null;
30847: 
30848:   steps.forEach((step, index) => {
30849:     const nodeId = step.id || `ai_step_${Date.now()}_${index}`;
30850:     const x = previousNode?.x != null ? Number(previousNode.x) + 320 : 360 + index * 320;
30851:     const y = previousNode?.y != null ? Number(previousNode.y) : 260;
30852: 
30853:     const node = {
30854:       id: nodeId,
30855:       title: step.title || "Aion step",
30856:       type: step.type || "AI / Aion",
30857:       icon: step.icon || "AI",
30858:       status: step.status || "Draft",
30859:       meta: step.meta || "Generated by Aion",
30860:       tone: step.tone || "blue",
30861:       x,
30862:       y,
30863:       config: {
30864:         ...(step.config || {}),
30865:         generated_by: "aion_unified_canvas_builder",
30866:         dry_run: true,
30867:       },
30868:     };
30869: 
30870:     nodes.push(node);
30871: 
30872:     if (previousNode?.id) {
30873:       edges.push({
30874:         id: `edge_${previousNode.id}_${nodeId}`,
30875:         source: previousNode.id,
30876:         target: nodeId,
30877:       });
30878:     }
30879: 
30880:     previousNode = node;
30881:   });
30882: 
30883:   graph.nodes = nodes;
30884:   graph.edges = edges;
30885:   graph.dirty = true;
30886:   graph.status = "draft";
30887: 
30888:   window["__aionWorkflowGraph"] = graph;
30889: 
30890:   if (typeof persistAionWorkflowDraftState === "function") {
30891:     persistAionWorkflowDraftState();
30892:   }
30893: 
30894:   if (typeof compileAndAttachAionWorkflowGlyph === "function") {
30895:     compileAndAttachAionWorkflowGlyph(graph);
30896:   }
30897: 
30898:   return graph;
30899: }
30900: 
30901: 
30902: 
30903: 
30904: function getAionWorkflowFileCabinetState() {
30905:   window.__aionWorkflowFileCabinetOpen =
30906:     window.__aionWorkflowFileCabinetOpen === true;
30907: 
30908:   return {
30909:     open: window.__aionWorkflowFileCabinetOpen,
30910:   };
30911: }
30912: 
30913: function getAionWorkflowFileCabinetItems() {
30914:   const graph =
30915:     (typeof getAionWorkflowDraftState === "function"
30916:       ? getAionWorkflowDraftState()
30917:       : window.__aionWorkflowGraph) || {};
30918: 
30919:   const currentWorkflowName = graph.name || "Untitled workflow";
30920:   const currentWorkflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
30921: 
30922:   return {
30923:     departments: [
30924:       {
30925:         id: "marketing",
30926:         label: "Marketing",
30927:         workflows: ["Social post workflow", "Campaign approval flow"],
30928:         assets: ["Caption templates", "Brand voice notes"],
30929:       },
30930:       {
30931:         id: "sales",
```

### Around line 30846: `let previousNode = nodes[nodes.length - 1] || null;`

```js
30801:       status: "Required",
30802:       meta: "Review before external write/send",
30803:       tone: "purple",
30804:       config: {
30805:         action_id: "aion.human_approval",
30806:         connector: "approval",
30807:         source: "{{gmail_draft}}",
30808:         fields: "draft, reason, risk",
30809:         outputs: "approval_decision",
30810:         approval_requirement: "required",
30811:       },
30812:     });
30813:   }
30814: 
30815:   if (!steps.length) {
30816:     steps.push({
30817:       id: makeId("aion_prompt"),
30818:       title: "Aion step",
30819:       type: "AI / Aion",
30820:       icon: "AI",
30821:       status: "Draft",
30822:       meta: "Generated from prompt",
30823:       tone: "blue",
30824:       config: {
30825:         action_id: "aion.simple_prompt",
30826:         connector: "aion",
30827:         source: prompt,
30828:         fields: "input",
30829:         outputs: "aion_result",
30830:       },
30831:     });
30832:   }
30833: 
30834:   return steps;
30835: }
30836: 
30837: function appendAionUnifiedSuggestedStepsToMainWorkflow(steps) {
30838:   if (!window.__aionWorkflowGraph) {
30839:     window.__aionWorkflowGraph = getAionWorkflowDraftState();
30840:   }
30841: 
30842:   const graph = window.__aionWorkflowGraph || {};
30843:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
30844:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
30845: 
30846:   let previousNode = nodes[nodes.length - 1] || null;
30847: 
30848:   steps.forEach((step, index) => {
30849:     const nodeId = step.id || `ai_step_${Date.now()}_${index}`;
30850:     const x = previousNode?.x != null ? Number(previousNode.x) + 320 : 360 + index * 320;
30851:     const y = previousNode?.y != null ? Number(previousNode.y) : 260;
30852: 
30853:     const node = {
30854:       id: nodeId,
30855:       title: step.title || "Aion step",
30856:       type: step.type || "AI / Aion",
30857:       icon: step.icon || "AI",
30858:       status: step.status || "Draft",
30859:       meta: step.meta || "Generated by Aion",
30860:       tone: step.tone || "blue",
30861:       x,
30862:       y,
30863:       config: {
30864:         ...(step.config || {}),
30865:         generated_by: "aion_unified_canvas_builder",
30866:         dry_run: true,
30867:       },
30868:     };
30869: 
30870:     nodes.push(node);
30871: 
30872:     if (previousNode?.id) {
30873:       edges.push({
30874:         id: `edge_${previousNode.id}_${nodeId}`,
30875:         source: previousNode.id,
30876:         target: nodeId,
30877:       });
30878:     }
30879: 
30880:     previousNode = node;
30881:   });
30882: 
30883:   graph.nodes = nodes;
30884:   graph.edges = edges;
30885:   graph.dirty = true;
30886:   graph.status = "draft";
30887: 
30888:   window["__aionWorkflowGraph"] = graph;
30889: 
30890:   if (typeof persistAionWorkflowDraftState === "function") {
30891:     persistAionWorkflowDraftState();
30892:   }
30893: 
30894:   if (typeof compileAndAttachAionWorkflowGlyph === "function") {
30895:     compileAndAttachAionWorkflowGlyph(graph);
30896:   }
30897: 
30898:   return graph;
30899: }
30900: 
30901: 
30902: 
30903: 
30904: function getAionWorkflowFileCabinetState() {
30905:   window.__aionWorkflowFileCabinetOpen =
30906:     window.__aionWorkflowFileCabinetOpen === true;
30907: 
30908:   return {
30909:     open: window.__aionWorkflowFileCabinetOpen,
30910:   };
30911: }
30912: 
30913: function getAionWorkflowFileCabinetItems() {
30914:   const graph =
30915:     (typeof getAionWorkflowDraftState === "function"
30916:       ? getAionWorkflowDraftState()
30917:       : window.__aionWorkflowGraph) || {};
30918: 
30919:   const currentWorkflowName = graph.name || "Untitled workflow";
30920:   const currentWorkflowId = graph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft";
30921: 
30922:   return {
30923:     departments: [
30924:       {
30925:         id: "marketing",
30926:         label: "Marketing",
30927:         workflows: ["Social post workflow", "Campaign approval flow"],
30928:         assets: ["Caption templates", "Brand voice notes"],
30929:       },
30930:       {
30931:         id: "sales",
30932:         label: "Sales",
30933:         workflows: ["Lead follow-up workflow", "Quote reply workflow"],
30934:         assets: ["Sales scripts", "Objection responses"],
30935:       },
```