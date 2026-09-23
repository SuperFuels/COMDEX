# O13E Live Agents / Pilot Render Inspection

Source: `desktop/mac/src/app.js`

## Raw hit count

2347 matching lines.

## Top-level function declarations near Pilot/Live Agent terms


### Hit line 175

```js
163: 
164: function getAgentMapFrontendState() {
165:   if (typeof state !== "undefined" && state) {
166:     return state;
167:   }
168:   return window.__aionAgentMapDashboardState;
169: }
170: 
171: function getMarketingCalendarMode() {
172:     return state.marketingCalendarMode || MARKETING_CALENDAR_MODES.DONE;
173:   }
174: 
175:   function getLiveAgentsView() {
176:     return state.liveAgentsView || LIVE_AGENT_VIEWS.STREAM;
177:   }
178: 
179:   function getInputValue(event) {
180:     return event && event.target ? event.target.value : "";
181:   }
182: 
183:   function getRuntimeAdapterDeps() {
184:     return {
185:       state,
186:       desktopStore,
187:       render,
```

### Hit line 176

```js
164: function getAgentMapFrontendState() {
165:   if (typeof state !== "undefined" && state) {
166:     return state;
167:   }
168:   return window.__aionAgentMapDashboardState;
169: }
170: 
171: function getMarketingCalendarMode() {
172:     return state.marketingCalendarMode || MARKETING_CALENDAR_MODES.DONE;
173:   }
174: 
175:   function getLiveAgentsView() {
176:     return state.liveAgentsView || LIVE_AGENT_VIEWS.STREAM;
177:   }
178: 
179:   function getInputValue(event) {
180:     return event && event.target ? event.target.value : "";
181:   }
182: 
183:   function getRuntimeAdapterDeps() {
184:     return {
185:       state,
186:       desktopStore,
187:       render,
188:       normalizeBindingsByCategory,
```

### Hit line 2099

```js
2087:           <div class="card-value" style="font-size:15px;">
2088:             ${escapeHtml(formatAionBusinessContextValue(value) || "Not provided")}
2089:           </div>
2090:         </div>
2091:       `;
2092:     })
2093:     .join("");
2094: }
2095: 
2096: 
2097: /* AION PATCH: Missing Business Context Mini Card helper v1
2098:  * ----------------------------------------------------------
2099:  * Some Live Agents / Pilot surfaces call this helper before the newer
2100:  * Business Twin context cards are available. Keep it generic and safe.
2101:  */
2102: function renderAionBusinessContextMiniCard(scope = "business") {
2103:   const label = String(scope || "business").trim() || "business";
2104: 
2105:   let businessName = "Business context";
2106:   let businessType = "Not confirmed";
2107:   let serviceArea = "Not confirmed";
2108:   let primaryGoal = "Not confirmed";
2109: 
2110:   try {
2111:     const foundation =
```

### Hit line 2873

```js
2861: 
2862:   return { queued, running, waiting, completed, cancelled, failed };
2863: }
2864: 
2865: function getApprovalCounts() {
2866:   const pending = state.approvals.filter((x) => x.status === "pending").length;
2867:   const approved = state.approvals.filter((x) => x.status === "approved").length;
2868:   const rejected = state.approvals.filter((x) => x.status === "rejected").length;
2869: 
2870:   return { pending, approved, rejected };
2871: }
2872: 
2873: function ensureLiveAgentSelection(options = {}) {
2874:   const result = liveAgentsRuntime.ensureLiveAgentSelection(state, options) || {};
2875:   const updates = {};
2876: 
2877:   if (Object.prototype.hasOwnProperty.call(result, "activeZone")) {
2878:     updates.activeZone = result.activeZone;
2879:   }
2880: 
2881:   if (Object.prototype.hasOwnProperty.call(result, "selectedLiveAgentId")) {
2882:     updates.selectedLiveAgentId = result.selectedLiveAgentId;
2883:   }
2884: 
2885:   if (Object.prototype.hasOwnProperty.call(result, "selectedLiveRunId")) {
```

### Hit line 2874

```js
2862:   return { queued, running, waiting, completed, cancelled, failed };
2863: }
2864: 
2865: function getApprovalCounts() {
2866:   const pending = state.approvals.filter((x) => x.status === "pending").length;
2867:   const approved = state.approvals.filter((x) => x.status === "approved").length;
2868:   const rejected = state.approvals.filter((x) => x.status === "rejected").length;
2869: 
2870:   return { pending, approved, rejected };
2871: }
2872: 
2873: function ensureLiveAgentSelection(options = {}) {
2874:   const result = liveAgentsRuntime.ensureLiveAgentSelection(state, options) || {};
2875:   const updates = {};
2876: 
2877:   if (Object.prototype.hasOwnProperty.call(result, "activeZone")) {
2878:     updates.activeZone = result.activeZone;
2879:   }
2880: 
2881:   if (Object.prototype.hasOwnProperty.call(result, "selectedLiveAgentId")) {
2882:     updates.selectedLiveAgentId = result.selectedLiveAgentId;
2883:   }
2884: 
2885:   if (Object.prototype.hasOwnProperty.call(result, "selectedLiveRunId")) {
2886:     updates.selectedLiveRunId = result.selectedLiveRunId;
```

### Hit line 2998

```js
2986:       defaultWebBase: DEFAULT_WEB_BASE,
2987:       defaultWorkspaceId: DEFAULT_WORKSPACE_ID,
2988:       defaultNodeId: DEFAULT_NODE_ID,
2989:     },
2990:   );
2991: }
2992: 
2993: async function refreshAll() {
2994:   const value = await runtimeAdapter.refreshAll(
2995:     getRuntimeAdapterDeps(),
2996:   );
2997: 
2998:   ensureLiveAgentSelection();
2999:   return value;
3000: }
3001: 
3002: async function runControl(path, body) {
3003:   return await runtimeAdapter.runControl(
3004:     getRuntimeAdapterDeps(),
3005:     path,
3006:     body,
3007:   );
3008: }
3009: 
3010: function setActiveTab(tabKey) {
```

### Hit line 3048

```js
3036: }
3037: 
3038: function renderGlobalStatusBanner() {
3039:   return "";
3040: }
3041: 
3042: function getAionMainSidebarIcon(tabKey) {
3043:   return {
3044:     boardroom: "⌂",
3045:     dashboard: "▦",
3046:     business_context: "◆",
3047:     marketing_stream: "✦",
3048:     live_agents: "◎",
3049:     aion_chat: "AI",
3050:     operations_agents: "⚙",
3051:     operations_flow: "⌁",
3052:     file_cabinet: "≡",
3053:     vault: "◈",
3054:     local_node: "▣",
3055:   }[String(tabKey || "")] || "•";
3056: }
3057: 
3058: function renderAppTabs() {
3059:   /*
3060:    * Phase 25K navigation consolidation:
```

### Hit line 3610

```js
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
```

### Hit line 4158

```js
4146: }
4147: 
4148: function findRunById(runId) {
4149:   if (!runId) return null;
4150:   const runs = Array.isArray(state.runs) ? state.runs : [];
4151:   return (
4152:     runs.find(
4153:       (run) => String(run?.id || run?.queue_item_id || "") === String(runId),
4154:     ) || null
4155:   );
4156: }
4157: 
4158: function renderDepartmentApprovalsSurface(departmentKey, selectedAgentCard) {
4159:   const departmentLabel = runtimeShared.getDepartmentLabel(departmentKey);
4160:   const approvals = getDepartmentApprovals(departmentKey);
4161:   const counts = getApprovalStatusCounts(approvals);
4162: 
4163:   return `
4164:     <div class="dashboard-shell">
4165:       <div class="card-grid">
4166:         ${renderDashboardMetricCard(
4167:           "Department",
4168:           departmentLabel,
4169:           selectedAgentCard?.label || "Department approval history",
4170:         )}
```

### Hit line 6309

```js
6297:     state.agentMapDashboardPreview || getDefaultAgentMapDashboardPreviewPayload(),
6298:   );
6299:   return state.agentMapDashboardPreview;
6300: }
6301: 
6302: function handleGenerateAgentMapClick() {
6303:   state.agentMapDashboardPreview = getDefaultAgentMapDashboardPreviewPayload();
6304:   state.agentMapGenerated = true;
6305:   state.agentMapGeneratedAt = new Date().toISOString();
6306:   requestRender?.();
6307: }
6308: 
6309: function renderAgentMapMachineDiscoveryPanel() {
6310:   const payload = getAgentMapDashboardPreviewPayload();
6311:   const escape =
6312:     typeof escapeHtml === "function"
6313:       ? escapeHtml
6314:       : (value) =>
6315:           String(value ?? "")
6316:             .replaceAll("&", "&amp;")
6317:             .replaceAll("<", "&lt;")
6318:             .replaceAll(">", "&gt;")
6319:             .replaceAll('"', "&quot;");
6320: 
6321:   const generatedLabel = state.agentMapGenerated
```

### Hit line 7301

```js
7289:         </div>
7290:         <div class="list-item">
7291:           <strong>Well-known path</strong>
7292:           <code>${escapeHtml(wellKnown)}</code>
7293:         </div>
7294:       </div>
7295: 
7296:       ${renderBoardroomCopyCodeBlock("Website install tag", installTag, "Copy tag")}
7297: 
7298:       <details class="aion-demo-details">
7299:         <summary>View full AgentMap preview</summary>
7300:         <div class="aion-demo-json-scroll">
7301:           ${renderAgentMapDashboardPanel()}
7302:         </div>
7303:       </details>
7304:     </section>
7305:   `;
7306: }
7307: 
7308: function __deprecatedPhase16Duplicate_6158_renderBoardroomWorkflowWidgetPanel(snapshot = {}) {
7309:   const formSnippet = `<form data-aion-widget="home-fixed-plumbing-enquiry">
7310:   <input name="customer_name" placeholder="Your name" required />
7311:   <input name="postcode" placeholder="Postcode / town" required />
7312:   <select name="service_type">
7313:     <option>Plumbing enquiry</option>
```

### Hit line 7417

```js
7405: 
7406:       <details class="aion-demo-details">
7407:         <summary>Show older workflow run history</summary>
7408:         ${renderBoardroomRecentRunsPanel()}
7409:       </details>
7410:     </section>
7411:   `;
7412: }
7413: /* END PHASE 16D LOCK */
7414: 
7415: 
7416: 
7417: function renderAgentMapDashboardPanel() {
7418:   const agentMapSafeFallback = {
7419:     preview_only: true,
7420:     human_review_required: true,
7421:     live_side_effects_enabled: false,
7422:   };
7423: 
7424:   const agentMapState = getAgentMapFrontendState();
7425:   const preview = getAgentMapDashboardPreviewPayload();
7426:   const agentmapJson = JSON.stringify(preview.agentmap_json, null, 2);
7427: 
7428:   return `
7429:     <section class="panel agentmap-dashboard-panel" data-agentmap-dashboard-panel="true">
```

### Hit line 7551

```js
7539: }
7540: 
7541: function __deprecatedPhase16Duplicate_6391_renderBoardroomA2ASetupPanel(snapshot = {}) {
7542:   return `
7543:     <section class="panel aion-boardroom-a2a-setup" data-aion-boardroom-a2a-setup="true">
7544:       <div class="panel-header">
7545:         <div>
7546:           <div class="panel-kicker">A2A Setup</div>
7547:           <h2>Connect Website + AgentMap</h2>
7548:           <p class="muted">Generate the machine-readable AgentMap, copy the website install tag, and verify discovery.</p>
7549:         </div>
7550:       </div>
7551:       ${renderAgentMapDashboardPanel()}
7552:     </section>
7553:   `;
7554: }
7555: 
7556: function __deprecatedPhase16Duplicate_6406_renderBoardroomWorkflowWidgetPanel(snapshot = {}) {
7557:   return `
7558:     <section class="panel aion-boardroom-workflow-widget" data-aion-boardroom-workflow-widget="true">
7559:       <div class="panel-header">
7560:         <div>
7561:           <div class="panel-kicker">Workflow → Website Form</div>
7562:           <h2>Generate Customer Intake Flow</h2>
7563:           <p class="muted">
```

### Hit line 7654

```js
7642: }
7643: 
7644: function renderBoardroomA2ASetupPanel(snapshot = {}) {
7645:   return `
7646:     <section class="panel aion-boardroom-a2a-setup" data-aion-boardroom-a2a-setup="true">
7647:       <div class="panel-header">
7648:         <div>
7649:           <div class="panel-kicker">A2A Setup</div>
7650:           <h2>Connect Website + AgentMap</h2>
7651:           <p class="muted">Generate the machine-readable AgentMap, copy the website install tag, and verify discovery.</p>
7652:         </div>
7653:       </div>
7654:       ${renderAgentMapDashboardPanel()}
7655:     </section>
7656:   `;
7657: }
7658: 
7659: function renderBoardroomWorkflowWidgetPanel(snapshot = {}) {
7660:   return `
7661:     <section class="panel aion-boardroom-workflow-widget" data-aion-boardroom-workflow-widget="true">
7662:       <div class="panel-header">
7663:         <div>
7664:           <div class="panel-kicker">Workflow → Website Form</div>
7665:           <h2>Generate Customer Intake Flow</h2>
7666:           <p class="muted">
```

### Hit line 7721

```js
7709:     </section>
7710:   `;
7711: }
7712: 
7713: 
7714: function getAionBoardroomSelectedDepartmentPulseKey() {
7715:   const key = String(state.boardroomSelectedDepartmentPulseKey || "finance").trim().toLowerCase();
7716:   if (getAionCoreDepartmentKeys().includes(key)) return key;
7717:   return "finance";
7718: }
7719: 
7720: function setAionBoardroomSelectedDepartmentPulseKey(departmentKey = "") {
7721:   const key = normaliseAionDepartmentPilotKey(departmentKey);
7722:   if (!getAionCoreDepartmentKeys().includes(key)) return false;
7723:   state.boardroomSelectedDepartmentPulseKey = key;
7724:   if (typeof requestRender === "function") requestRender();
7725:   return true;
7726: }
7727: 
7728: function getAionDepartmentPulseSummaryItems(departmentKey = getAionBoardroomSelectedDepartmentPulseKey()) {
7729:   const key = normaliseAionDepartmentPilotKey(departmentKey);
7730:   const pulse = getBoardroomPulse();
7731:   const center = getBoardroomCenter();
7732:   const runtime = getBoardroomRuntime();
7733: 
```

### Hit line 7729

```js
7717:   return "finance";
7718: }
7719: 
7720: function setAionBoardroomSelectedDepartmentPulseKey(departmentKey = "") {
7721:   const key = normaliseAionDepartmentPilotKey(departmentKey);
7722:   if (!getAionCoreDepartmentKeys().includes(key)) return false;
7723:   state.boardroomSelectedDepartmentPulseKey = key;
7724:   if (typeof requestRender === "function") requestRender();
7725:   return true;
7726: }
7727: 
7728: function getAionDepartmentPulseSummaryItems(departmentKey = getAionBoardroomSelectedDepartmentPulseKey()) {
7729:   const key = normaliseAionDepartmentPilotKey(departmentKey);
7730:   const pulse = getBoardroomPulse();
7731:   const center = getBoardroomCenter();
7732:   const runtime = getBoardroomRuntime();
7733: 
7734:   const cash = asRecord(pulse.cash) || {};
7735:   const sales = asRecord(pulse.sales) || {};
7736:   const ops = asRecord(pulse.ops) || {};
7737:   const finance = asRecord(pulse.finance) || {};
7738:   const runtimeRuns = safeArray(runtime.runs);
7739:   const runtimeApprovals = safeArray(runtime.approvals);
7740:   const pendingApprovals = runtimeApprovals.filter((item) => item?.status === "pending").length;
7741: 
```

### Hit line 7809

```js
7797: 
7798:   return [
7799:     { label: "Cash", value: formatBoardroomEuro(cash.onHand ?? cash.on_hand ?? center.cash ?? "—"), sub: `Runway ${cash.runwayDays ?? cash.runway_days ?? "—"}d` },
7800:     { label: "Revenue", value: formatBoardroomEuro(sales.revenue ?? center.revenue ?? "—"), sub: `Orders ${sales.orders ?? "—"} · Conv ${sales.conversionRate ?? sales.conversion_rate ?? "—"}%` },
7801:     { label: "Costs", value: formatBoardroomEuro(finance.costs ?? finance.monthly_costs ?? "—"), sub: "Known costs" },
7802:     { label: "Debtors", value: finance.debtorDays ?? finance.debtor_days ?? "—", sub: `Creditor ${finance.creditorDays ?? finance.creditor_days ?? "—"}` },
7803:     { label: "Margin", value: formatBoardroomPercent(finance.grossMarginPct ?? finance.gross_margin_pct ?? "—"), sub: "Gross margin" },
7804:     { label: "Runs", value: runtimeRuns.length, sub: `${pendingApprovals} approval${pendingApprovals === 1 ? "" : "s"}` },
7805:   ];
7806: }
7807: 
7808: function getAionDepartmentPulseAccentColor(departmentKey = "") {
7809:   const key = normaliseAionDepartmentPilotKey(departmentKey);
7810:   if (key === "marketing") return "#2563eb";
7811:   if (key === "sales") return "#16a34a";
7812:   if (key === "finance") return "#0284c7";
7813:   if (key === "operations") return "#f59e0b";
7814:   if (key === "support") return "#7c3aed";
7815:   return "#2563eb";
7816: }
7817: 
7818: function renderBoardroomUnifiedMetricCard({
7819:   label,
7820:   value,
7821:   sub = "",
```

### Hit line 7880

```js
7868:         color:rgba(17,17,17,0.58);
7869:         white-space:nowrap;
7870:         overflow:hidden;
7871:         text-overflow:ellipsis;
7872:       ">
7873:         ${escapeHtml(sub || state || "—")}
7874:       </div>
7875:     </div>
7876:   `;
7877: }
7878: 
7879: function renderBoardroomPulseSummaryStrip(snapshot = {}, departmentKey = getAionBoardroomSelectedDepartmentPulseKey()) {
7880:   const key = normaliseAionDepartmentPilotKey(departmentKey);
7881:   const label = getAionDepartmentLabel(key);
7882:   const items = getAionDepartmentPulseSummaryItems(key);
7883:   const accent = getAionDepartmentPulseAccentColor(key);
7884: 
7885:   return `
7886:     <section
7887:       data-aion-phase25j-boardroom-pulse-strip="true"
7888:       data-aion-phase25j-selected-department-highlights="${escapeHtml(key)}"
7889:       style="margin-top:9px;"
7890:     >
7891:       <div style="display:flex; align-items:center; gap:9px; margin-bottom:6px;">
7892:         <div style="width:9px; height:9px; border-radius:999px; background:${accent}; box-shadow:0 0 0 4px rgba(2,132,199,0.10);"></div>
```

### Hit line 8319

```js
8307:           : `
8308:             <div class="boardroom-dashboard-shell">
8309:               ${renderBoardroomDashboardView(snapshot)}
8310:             </div>
8311:           `
8312:       }
8313:     </div>
8314:   `;
8315: }
8316: 
8317: 
8318: function getPrimaryDepartmentAgentCard(departmentKey) {
8319:   return liveAgentsRuntime.getPrimaryDepartmentAgentCard(state, departmentKey);
8320: }
8321: 
8322: function setLiveAgentsWorkspace(departmentKey, options = {}) {
8323:   boardroomRuntime.setLiveAgentsWorkspace(
8324:     {
8325:       desktopStore,
8326:       state,
8327:       LIVE_AGENT_VIEWS,
8328:     },
8329:     departmentKey,
8330:     options,
8331:   );
```

### Hit line 8322

```js
8310:             </div>
8311:           `
8312:       }
8313:     </div>
8314:   `;
8315: }
8316: 
8317: 
8318: function getPrimaryDepartmentAgentCard(departmentKey) {
8319:   return liveAgentsRuntime.getPrimaryDepartmentAgentCard(state, departmentKey);
8320: }
8321: 
8322: function setLiveAgentsWorkspace(departmentKey, options = {}) {
8323:   boardroomRuntime.setLiveAgentsWorkspace(
8324:     {
8325:       desktopStore,
8326:       state,
8327:       LIVE_AGENT_VIEWS,
8328:     },
8329:     departmentKey,
8330:     options,
8331:   );
8332: }
8333: 
8334: function renderLocalNodeSurface() {
```

### Hit line 8323

```js
8311:           `
8312:       }
8313:     </div>
8314:   `;
8315: }
8316: 
8317: 
8318: function getPrimaryDepartmentAgentCard(departmentKey) {
8319:   return liveAgentsRuntime.getPrimaryDepartmentAgentCard(state, departmentKey);
8320: }
8321: 
8322: function setLiveAgentsWorkspace(departmentKey, options = {}) {
8323:   boardroomRuntime.setLiveAgentsWorkspace(
8324:     {
8325:       desktopStore,
8326:       state,
8327:       LIVE_AGENT_VIEWS,
8328:     },
8329:     departmentKey,
8330:     options,
8331:   );
8332: }
8333: 
8334: function renderLocalNodeSurface() {
8335:   const status = state.status || {};
```

### Hit line 8693

```js
8681:           : ""
8682:       }
8683:     </div>
8684:   `;
8685: }
8686: 
8687: function getDesktopAssistantTitle() {
8688:   const labels = {
8689:     boardroom: "Boardroom Assistant",
8690:     dashboard: "Dashboard Assistant",
8691:     marketing_stream: "Marketing Assistant",
8692:     brand_foundation: "Brand Assistant",
8693:     live_agents: "Agent Assistant",
8694:     aion_chat: "Aion",
8695:     operations_agents: "Train Agent Assistant",
8696:     operations_flow: "Operations Assistant",
8697:     local_node: "Local Node Assistant",
8698:   };
8699: 
8700:   return labels[state.activeTab] || "Aion Assistant";
8701: }
8702: 
8703: function getDesktopAssistantPlaceholder() {
8704:   const placeholders = {
8705:     boardroom: "Ask what needs attention in the business...",
```

### Hit line 8709

```js
8697:     local_node: "Local Node Assistant",
8698:   };
8699: 
8700:   return labels[state.activeTab] || "Aion Assistant";
8701: }
8702: 
8703: function getDesktopAssistantPlaceholder() {
8704:   const placeholders = {
8705:     boardroom: "Ask what needs attention in the business...",
8706:     dashboard: "Ask about alerts, queues, approvals, or current status...",
8707:     marketing_stream: "Ask for post ideas, captions, hooks, or campaign improvements...",
8708:     brand_foundation: "Ask for help writing or improving brand sections...",
8709:     live_agents: "Ask about this run, approval, agent, or workflow...",
8710:     operations_agents: "Ask about trained tasks, triggers, test runs, approvals, or automation setup...",
8711:     operations_flow: "Ask what is blocked or how the work is flowing...",
8712:     local_node: "Ask about backend status, runtime, scheduler, or sync...",
8713:     aion_chat: "Ask Aion anything about the business, runtime, brand, agents, code, or next action...",
8714:   };
8715: 
8716:   return placeholders[state.activeTab] || "Ask Aion anything...";
8717: }
8718: 
8719: function renderDesktopAssistantQuickActions() {
8720:   const tab = state.activeTab || "dashboard";
8721: 
```

### Hit line 8858

```js
8846:       <label class="field-label">Response</label>
8847:       <textarea
8848:         id="desktopAssistantOutputInput"
8849:         class="input input-textarea"
8850:         placeholder="Assistant response will appear here."
8851:       >${escapeHtml(state.desktopAssistantOutput || "")}</textarea>
8852:     </div>
8853:   `;
8854: }
8855: 
8856: 
8857: 
8858: /* PHASE 21X LOCK: Real frontend Pilot cockpit mount */
8859: 
8860: 
8861: /* PHASE 21N LOCK: Pilot frontend interaction smoke */
8862: 
8863: function getAionPilotFrontendInteractionState() {
8864:   if (!window.__aionPilotFrontendInteractionState) {
8865:     window.__aionPilotFrontendInteractionState = {
8866:       status: "idle",
8867:       last_request: "",
8868:       draft_created: false,
8869:       stream_events: [],
8870:       artifact_status: "draft_preview",
```

### Hit line 8861

```js
8849:         class="input input-textarea"
8850:         placeholder="Assistant response will appear here."
8851:       >${escapeHtml(state.desktopAssistantOutput || "")}</textarea>
8852:     </div>
8853:   `;
8854: }
8855: 
8856: 
8857: 
8858: /* PHASE 21X LOCK: Real frontend Pilot cockpit mount */
8859: 
8860: 
8861: /* PHASE 21N LOCK: Pilot frontend interaction smoke */
8862: 
8863: function getAionPilotFrontendInteractionState() {
8864:   if (!window.__aionPilotFrontendInteractionState) {
8865:     window.__aionPilotFrontendInteractionState = {
8866:       status: "idle",
8867:       last_request: "",
8868:       draft_created: false,
8869:       stream_events: [],
8870:       artifact_status: "draft_preview",
8871:       artifact_hash: "sha256:preview_artifact_hash",
8872:       receipt_hash: "sha256:preview_receipt_hash",
8873:       replay_hash: "sha256:preview_replay_hash",
```

### Hit line 8863

```js
8851:       >${escapeHtml(state.desktopAssistantOutput || "")}</textarea>
8852:     </div>
8853:   `;
8854: }
8855: 
8856: 
8857: 
8858: /* PHASE 21X LOCK: Real frontend Pilot cockpit mount */
8859: 
8860: 
8861: /* PHASE 21N LOCK: Pilot frontend interaction smoke */
8862: 
8863: function getAionPilotFrontendInteractionState() {
8864:   if (!window.__aionPilotFrontendInteractionState) {
8865:     window.__aionPilotFrontendInteractionState = {
8866:       status: "idle",
8867:       last_request: "",
8868:       draft_created: false,
8869:       stream_events: [],
8870:       artifact_status: "draft_preview",
8871:       artifact_hash: "sha256:preview_artifact_hash",
8872:       receipt_hash: "sha256:preview_receipt_hash",
8873:       replay_hash: "sha256:preview_replay_hash",
8874:       proof_hash: "sha256:preview_proof_hash",
8875:       blocked_live_actions: [
```

### Hit line 8864

```js
8852:     </div>
8853:   `;
8854: }
8855: 
8856: 
8857: 
8858: /* PHASE 21X LOCK: Real frontend Pilot cockpit mount */
8859: 
8860: 
8861: /* PHASE 21N LOCK: Pilot frontend interaction smoke */
8862: 
8863: function getAionPilotFrontendInteractionState() {
8864:   if (!window.__aionPilotFrontendInteractionState) {
8865:     window.__aionPilotFrontendInteractionState = {
8866:       status: "idle",
8867:       last_request: "",
8868:       draft_created: false,
8869:       stream_events: [],
8870:       artifact_status: "draft_preview",
8871:       artifact_hash: "sha256:preview_artifact_hash",
8872:       receipt_hash: "sha256:preview_receipt_hash",
8873:       replay_hash: "sha256:preview_replay_hash",
8874:       proof_hash: "sha256:preview_proof_hash",
8875:       blocked_live_actions: [
8876:         "external_send",
```

### Hit line 8865

```js
8853:   `;
8854: }
8855: 
8856: 
8857: 
8858: /* PHASE 21X LOCK: Real frontend Pilot cockpit mount */
8859: 
8860: 
8861: /* PHASE 21N LOCK: Pilot frontend interaction smoke */
8862: 
8863: function getAionPilotFrontendInteractionState() {
8864:   if (!window.__aionPilotFrontendInteractionState) {
8865:     window.__aionPilotFrontendInteractionState = {
8866:       status: "idle",
8867:       last_request: "",
8868:       draft_created: false,
8869:       stream_events: [],
8870:       artifact_status: "draft_preview",
8871:       artifact_hash: "sha256:preview_artifact_hash",
8872:       receipt_hash: "sha256:preview_receipt_hash",
8873:       replay_hash: "sha256:preview_replay_hash",
8874:       proof_hash: "sha256:preview_proof_hash",
8875:       blocked_live_actions: [
8876:         "external_send",
8877:         "production_deploy",
```

### Hit line 8886

```js
8874:       proof_hash: "sha256:preview_proof_hash",
8875:       blocked_live_actions: [
8876:         "external_send",
8877:         "production_deploy",
8878:         "payment",
8879:         "public_post",
8880:         "booking",
8881:         "escrow",
8882:       ],
8883:     };
8884:   }
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
```

### Hit line 8889

```js
8877:         "production_deploy",
8878:         "payment",
8879:         "public_post",
8880:         "booking",
8881:         "escrow",
8882:       ],
8883:     };
8884:   }
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
```

### Hit line 8890

```js
8878:         "payment",
8879:         "public_post",
8880:         "booking",
8881:         "escrow",
8882:       ],
8883:     };
8884:   }
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
```

### Hit line 8891

```js
8879:         "public_post",
8880:         "booking",
8881:         "escrow",
8882:       ],
8883:     };
8884:   }
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8903:   const activePilotDepartmentScope =
```

### Hit line 8892

```js
8880:         "booking",
8881:         "escrow",
8882:       ],
8883:     };
8884:   }
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8903:   const activePilotDepartmentScope =
8904:     typeof getSelectedLiveDepartmentKey === "function"
```

### Hit line 8893

```js
8881:         "escrow",
8882:       ],
8883:     };
8884:   }
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8903:   const activePilotDepartmentScope =
8904:     typeof getSelectedLiveDepartmentKey === "function"
8905:       ? normaliseAionDepartmentPilotKey(getSelectedLiveDepartmentKey())
```

### Hit line 8895

```js
8883:     };
8884:   }
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8903:   const activePilotDepartmentScope =
8904:     typeof getSelectedLiveDepartmentKey === "function"
8905:       ? normaliseAionDepartmentPilotKey(getSelectedLiveDepartmentKey())
8906:       : "pilot";
8907:   pilotState.department_scope = ["aion", "pilot"].includes(activePilotDepartmentScope)
```

### Hit line 8896

```js
8884:   }
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8903:   const activePilotDepartmentScope =
8904:     typeof getSelectedLiveDepartmentKey === "function"
8905:       ? normaliseAionDepartmentPilotKey(getSelectedLiveDepartmentKey())
8906:       : "pilot";
8907:   pilotState.department_scope = ["aion", "pilot"].includes(activePilotDepartmentScope)
8908:     ? "pilot"
```

### Hit line 8897

```js
8885: 
8886:   return window.__aionPilotFrontendInteractionState;
8887: }
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8903:   const activePilotDepartmentScope =
8904:     typeof getSelectedLiveDepartmentKey === "function"
8905:       ? normaliseAionDepartmentPilotKey(getSelectedLiveDepartmentKey())
8906:       : "pilot";
8907:   pilotState.department_scope = ["aion", "pilot"].includes(activePilotDepartmentScope)
8908:     ? "pilot"
8909:     : activePilotDepartmentScope;
```

### Hit line 8900

```js
8888: 
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8903:   const activePilotDepartmentScope =
8904:     typeof getSelectedLiveDepartmentKey === "function"
8905:       ? normaliseAionDepartmentPilotKey(getSelectedLiveDepartmentKey())
8906:       : "pilot";
8907:   pilotState.department_scope = ["aion", "pilot"].includes(activePilotDepartmentScope)
8908:     ? "pilot"
8909:     : activePilotDepartmentScope;
8910:   if (
8911:     pilotState.department_scope !== "pilot" &&
8912:     typeof updateAionDepartmentIntelligence === "function"
```

### Hit line 8901

```js
8889: function createAionPilotFrontendDraftMission() {
8890:   const pilotState = getAionPilotFrontendInteractionState();
8891:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8892:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8893:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8894: 
8895:   pilotState.status = "plan_ready";
8896:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8897:     return pilotState;
8898:   }
8899: 
8900:   pilotState.last_request = requestText;
8901:   pilotState.draft_created = true;
8902:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8903:   const activePilotDepartmentScope =
8904:     typeof getSelectedLiveDepartmentKey === "function"
8905:       ? normaliseAionDepartmentPilotKey(getSelectedLiveDepartmentKey())
8906:       : "pilot";
8907:   pilotState.department_scope = ["aion", "pilot"].includes(activePilotDepartmentScope)
8908:     ? "pilot"
8909:     : activePilotDepartmentScope;
8910:   if (
8911:     pilotState.department_scope !== "pilot" &&
8912:     typeof updateAionDepartmentIntelligence === "function"
8913:   ) {
```

### Hit line 8975

```js
8963:       detail: "No send, deploy, payment, post, booking or escrow without exact approval",
8964:       status: "blocked",
8965:     },
8966:     {
8967:       type: "central_aion_assessment_hook",
8968:       label: "AION assessment hook prepared",
8969:       detail: `Assessment confidence ${universalPlan.central_business_assessment?.confidence || "none"} · action proposals ${(universalPlan.central_execution_queue_proposal || []).length}`,
8970:       status: "proposal_only",
8971:     },
8972:   ];
8973: 
8974: 
8975:   if (typeof fetchAionLrmPilotContextPreviewIntoPilotState === "function") {
8976:     fetchAionLrmPilotContextPreviewIntoPilotState({
8977:       business_id: "home-fixed",
8978:       mission_id: "pilot_demo_pdf_mission",
8979:       mission_run_id: "pilot_demo_run_preview",
8980:     }).catch((error) => {
8981:       const state = getAionPilotFrontendInteractionState();
8982:       state.lrm_context_status = "error";
8983:       state.lrm_context_error = String(error?.message || error || "LRM context preview failed");
8984:       if (typeof requestRender === "function") {
8985:         requestRender();
8986:       }
8987:     });
```

### Hit line 8976

```js
8964:       status: "blocked",
8965:     },
8966:     {
8967:       type: "central_aion_assessment_hook",
8968:       label: "AION assessment hook prepared",
8969:       detail: `Assessment confidence ${universalPlan.central_business_assessment?.confidence || "none"} · action proposals ${(universalPlan.central_execution_queue_proposal || []).length}`,
8970:       status: "proposal_only",
8971:     },
8972:   ];
8973: 
8974: 
8975:   if (typeof fetchAionLrmPilotContextPreviewIntoPilotState === "function") {
8976:     fetchAionLrmPilotContextPreviewIntoPilotState({
8977:       business_id: "home-fixed",
8978:       mission_id: "pilot_demo_pdf_mission",
8979:       mission_run_id: "pilot_demo_run_preview",
8980:     }).catch((error) => {
8981:       const state = getAionPilotFrontendInteractionState();
8982:       state.lrm_context_status = "error";
8983:       state.lrm_context_error = String(error?.message || error || "LRM context preview failed");
8984:       if (typeof requestRender === "function") {
8985:         requestRender();
8986:       }
8987:     });
8988:   }
```

### Hit line 8978

```js
8966:     {
8967:       type: "central_aion_assessment_hook",
8968:       label: "AION assessment hook prepared",
8969:       detail: `Assessment confidence ${universalPlan.central_business_assessment?.confidence || "none"} · action proposals ${(universalPlan.central_execution_queue_proposal || []).length}`,
8970:       status: "proposal_only",
8971:     },
8972:   ];
8973: 
8974: 
8975:   if (typeof fetchAionLrmPilotContextPreviewIntoPilotState === "function") {
8976:     fetchAionLrmPilotContextPreviewIntoPilotState({
8977:       business_id: "home-fixed",
8978:       mission_id: "pilot_demo_pdf_mission",
8979:       mission_run_id: "pilot_demo_run_preview",
8980:     }).catch((error) => {
8981:       const state = getAionPilotFrontendInteractionState();
8982:       state.lrm_context_status = "error";
8983:       state.lrm_context_error = String(error?.message || error || "LRM context preview failed");
8984:       if (typeof requestRender === "function") {
8985:         requestRender();
8986:       }
8987:     });
8988:   }
8989: 
8990:   if (typeof requestRender === "function") {
```

### Hit line 8979

```js
8967:       type: "central_aion_assessment_hook",
8968:       label: "AION assessment hook prepared",
8969:       detail: `Assessment confidence ${universalPlan.central_business_assessment?.confidence || "none"} · action proposals ${(universalPlan.central_execution_queue_proposal || []).length}`,
8970:       status: "proposal_only",
8971:     },
8972:   ];
8973: 
8974: 
8975:   if (typeof fetchAionLrmPilotContextPreviewIntoPilotState === "function") {
8976:     fetchAionLrmPilotContextPreviewIntoPilotState({
8977:       business_id: "home-fixed",
8978:       mission_id: "pilot_demo_pdf_mission",
8979:       mission_run_id: "pilot_demo_run_preview",
8980:     }).catch((error) => {
8981:       const state = getAionPilotFrontendInteractionState();
8982:       state.lrm_context_status = "error";
8983:       state.lrm_context_error = String(error?.message || error || "LRM context preview failed");
8984:       if (typeof requestRender === "function") {
8985:         requestRender();
8986:       }
8987:     });
8988:   }
8989: 
8990:   if (typeof requestRender === "function") {
8991:     requestRender();
```

### Hit line 8981

```js
8969:       detail: `Assessment confidence ${universalPlan.central_business_assessment?.confidence || "none"} · action proposals ${(universalPlan.central_execution_queue_proposal || []).length}`,
8970:       status: "proposal_only",
8971:     },
8972:   ];
8973: 
8974: 
8975:   if (typeof fetchAionLrmPilotContextPreviewIntoPilotState === "function") {
8976:     fetchAionLrmPilotContextPreviewIntoPilotState({
8977:       business_id: "home-fixed",
8978:       mission_id: "pilot_demo_pdf_mission",
8979:       mission_run_id: "pilot_demo_run_preview",
8980:     }).catch((error) => {
8981:       const state = getAionPilotFrontendInteractionState();
8982:       state.lrm_context_status = "error";
8983:       state.lrm_context_error = String(error?.message || error || "LRM context preview failed");
8984:       if (typeof requestRender === "function") {
8985:         requestRender();
8986:       }
8987:     });
8988:   }
8989: 
8990:   if (typeof requestRender === "function") {
8991:     requestRender();
8992:   }
8993: 
```

### Hit line 8994

```js
8982:       state.lrm_context_status = "error";
8983:       state.lrm_context_error = String(error?.message || error || "LRM context preview failed");
8984:       if (typeof requestRender === "function") {
8985:         requestRender();
8986:       }
8987:     });
8988:   }
8989: 
8990:   if (typeof requestRender === "function") {
8991:     requestRender();
8992:   }
8993: 
8994:   return pilotState;
8995: }
8996: 
8997: function renderAionPilotFrontendStreamEvents(pilotState = getAionPilotFrontendInteractionState()) {
8998:   const events = Array.isArray(pilotState.stream_events) ? pilotState.stream_events : [];
8999: 
9000:   if (!events.length) {
9001:     return `
9002:       <p>Private reasoning hidden.</p>
9003:       <p>Visible actions, receipts, paths and blocked actions will appear here.</p>
9004:     `;
9005:   }
9006: 
```

### Hit line 8997

```js
8985:         requestRender();
8986:       }
8987:     });
8988:   }
8989: 
8990:   if (typeof requestRender === "function") {
8991:     requestRender();
8992:   }
8993: 
8994:   return pilotState;
8995: }
8996: 
8997: function renderAionPilotFrontendStreamEvents(pilotState = getAionPilotFrontendInteractionState()) {
8998:   const events = Array.isArray(pilotState.stream_events) ? pilotState.stream_events : [];
8999: 
9000:   if (!events.length) {
9001:     return `
9002:       <p>Private reasoning hidden.</p>
9003:       <p>Visible actions, receipts, paths and blocked actions will appear here.</p>
9004:     `;
9005:   }
9006: 
9007:   return `
9008:     <div data-aion-pilot-visible-stream-events>
9009:       ${events.map((event) => `
```

### Hit line 8998

```js
8986:       }
8987:     });
8988:   }
8989: 
8990:   if (typeof requestRender === "function") {
8991:     requestRender();
8992:   }
8993: 
8994:   return pilotState;
8995: }
8996: 
8997: function renderAionPilotFrontendStreamEvents(pilotState = getAionPilotFrontendInteractionState()) {
8998:   const events = Array.isArray(pilotState.stream_events) ? pilotState.stream_events : [];
8999: 
9000:   if (!events.length) {
9001:     return `
9002:       <p>Private reasoning hidden.</p>
9003:       <p>Visible actions, receipts, paths and blocked actions will appear here.</p>
9004:     `;
9005:   }
9006: 
9007:   return `
9008:     <div data-aion-pilot-visible-stream-events>
9009:       ${events.map((event) => `
9010:         <div class="aion-pilot-map-node" data-aion-pilot-stream-event="${escapeHtml(event.type)}">
```

### Hit line 9008

```js
8996: 
8997: function renderAionPilotFrontendStreamEvents(pilotState = getAionPilotFrontendInteractionState()) {
8998:   const events = Array.isArray(pilotState.stream_events) ? pilotState.stream_events : [];
8999: 
9000:   if (!events.length) {
9001:     return `
9002:       <p>Private reasoning hidden.</p>
9003:       <p>Visible actions, receipts, paths and blocked actions will appear here.</p>
9004:     `;
9005:   }
9006: 
9007:   return `
9008:     <div data-aion-pilot-visible-stream-events>
9009:       ${events.map((event) => `
9010:         <div class="aion-pilot-map-node" data-aion-pilot-stream-event="${escapeHtml(event.type)}">
9011:           <strong>${escapeHtml(event.label)}</strong>
9012:           <div class="aion-pilot-meta-row"><span>Status</span><code>${escapeHtml(event.status)}</code></div>
9013:           <div class="aion-pilot-meta-row"><span>Detail</span><code>${escapeHtml(event.detail)}</code></div>
9014:         </div>
9015:       `).join("")}
9016:     </div>
9017:   `;
9018: }
9019: 
9020: /* END PHASE 21N LOCK */
```

### Hit line 9010

```js
8998:   const events = Array.isArray(pilotState.stream_events) ? pilotState.stream_events : [];
8999: 
9000:   if (!events.length) {
9001:     return `
9002:       <p>Private reasoning hidden.</p>
9003:       <p>Visible actions, receipts, paths and blocked actions will appear here.</p>
9004:     `;
9005:   }
9006: 
9007:   return `
9008:     <div data-aion-pilot-visible-stream-events>
9009:       ${events.map((event) => `
9010:         <div class="aion-pilot-map-node" data-aion-pilot-stream-event="${escapeHtml(event.type)}">
9011:           <strong>${escapeHtml(event.label)}</strong>
9012:           <div class="aion-pilot-meta-row"><span>Status</span><code>${escapeHtml(event.status)}</code></div>
9013:           <div class="aion-pilot-meta-row"><span>Detail</span><code>${escapeHtml(event.detail)}</code></div>
9014:         </div>
9015:       `).join("")}
9016:     </div>
9017:   `;
9018: }
9019: 
9020: /* END PHASE 21N LOCK */
9021: 
9022: 
```

### Hit line 9012

```js
9000:   if (!events.length) {
9001:     return `
9002:       <p>Private reasoning hidden.</p>
9003:       <p>Visible actions, receipts, paths and blocked actions will appear here.</p>
9004:     `;
9005:   }
9006: 
9007:   return `
9008:     <div data-aion-pilot-visible-stream-events>
9009:       ${events.map((event) => `
9010:         <div class="aion-pilot-map-node" data-aion-pilot-stream-event="${escapeHtml(event.type)}">
9011:           <strong>${escapeHtml(event.label)}</strong>
9012:           <div class="aion-pilot-meta-row"><span>Status</span><code>${escapeHtml(event.status)}</code></div>
9013:           <div class="aion-pilot-meta-row"><span>Detail</span><code>${escapeHtml(event.detail)}</code></div>
9014:         </div>
9015:       `).join("")}
9016:     </div>
9017:   `;
9018: }
9019: 
9020: /* END PHASE 21N LOCK */
9021: 
9022: 
9023: 
9024: /* PHASE 21O LOCK: Universal Pilot task stream simple dashboard */
```

### Hit line 9013

```js
9001:     return `
9002:       <p>Private reasoning hidden.</p>
9003:       <p>Visible actions, receipts, paths and blocked actions will appear here.</p>
9004:     `;
9005:   }
9006: 
9007:   return `
9008:     <div data-aion-pilot-visible-stream-events>
9009:       ${events.map((event) => `
9010:         <div class="aion-pilot-map-node" data-aion-pilot-stream-event="${escapeHtml(event.type)}">
9011:           <strong>${escapeHtml(event.label)}</strong>
9012:           <div class="aion-pilot-meta-row"><span>Status</span><code>${escapeHtml(event.status)}</code></div>
9013:           <div class="aion-pilot-meta-row"><span>Detail</span><code>${escapeHtml(event.detail)}</code></div>
9014:         </div>
9015:       `).join("")}
9016:     </div>
9017:   `;
9018: }
9019: 
9020: /* END PHASE 21N LOCK */
9021: 
9022: 
9023: 
9024: /* PHASE 21O LOCK: Universal Pilot task stream simple dashboard */
9025: 
```

### Hit line 9024

```js
9012:           <div class="aion-pilot-meta-row"><span>Status</span><code>${escapeHtml(event.status)}</code></div>
9013:           <div class="aion-pilot-meta-row"><span>Detail</span><code>${escapeHtml(event.detail)}</code></div>
9014:         </div>
9015:       `).join("")}
9016:     </div>
9017:   `;
9018: }
9019: 
9020: /* END PHASE 21N LOCK */
9021: 
9022: 
9023: 
9024: /* PHASE 21O LOCK: Universal Pilot task stream simple dashboard */
9025: 
9026: function classifyAionPilotUniversalTask(requestText = "") {
9027:   const text = String(requestText || "").toLowerCase();
9028: 
9029:   const hasAny = (signals) => signals.some((signal) => text.includes(signal));
9030: 
9031:   const marketingPlanSignals = [
9032:     "marketing plan",
9033:     "marketing strategy",
9034:     "marketing roadmap",
9035:     "execute the marketing",
9036:     "execute marketing",
```

### Hit line 9026

```js
9014:         </div>
9015:       `).join("")}
9016:     </div>
9017:   `;
9018: }
9019: 
9020: /* END PHASE 21N LOCK */
9021: 
9022: 
9023: 
9024: /* PHASE 21O LOCK: Universal Pilot task stream simple dashboard */
9025: 
9026: function classifyAionPilotUniversalTask(requestText = "") {
9027:   const text = String(requestText || "").toLowerCase();
9028: 
9029:   const hasAny = (signals) => signals.some((signal) => text.includes(signal));
9030: 
9031:   const marketingPlanSignals = [
9032:     "marketing plan",
9033:     "marketing strategy",
9034:     "marketing roadmap",
9035:     "execute the marketing",
9036:     "execute marketing",
9037:     "grow the business",
9038:     "growth plan",
```

### Hit line 9301

```js
9289:       "No public posts",
9290:       "No ad spend",
9291:       "No bookings",
9292:       "No payments",
9293:       "No invoices",
9294:       "No deployments",
9295:       "No external writes",
9296:     ],
9297:     created_at: new Date().toISOString(),
9298:   };
9299: }
9300: 
9301: function buildAionCentralPilotExecutionQueueProposal(actionPlan = {}) {
9302:   const items = safeArray(actionPlan.items);
9303: 
9304:   return items.map((item, index) => ({
9305:     id: item.id || `central_pilot_proposed_task_${index + 1}`,
9306:     title: item.title || `Central Pilot proposed task ${index + 1}`,
9307:     source: item.source || "central_aion_assessment_hook",
9308:     status: "waiting_human_approval",
9309:     safety: "proposal_only",
9310:     approval_required: true,
9311:     no_live_external_action: true,
9312:   }));
9313: }
```

### Hit line 9305

```js
9293:       "No invoices",
9294:       "No deployments",
9295:       "No external writes",
9296:     ],
9297:     created_at: new Date().toISOString(),
9298:   };
9299: }
9300: 
9301: function buildAionCentralPilotExecutionQueueProposal(actionPlan = {}) {
9302:   const items = safeArray(actionPlan.items);
9303: 
9304:   return items.map((item, index) => ({
9305:     id: item.id || `central_pilot_proposed_task_${index + 1}`,
9306:     title: item.title || `Central Pilot proposed task ${index + 1}`,
9307:     source: item.source || "central_aion_assessment_hook",
9308:     status: "waiting_human_approval",
9309:     safety: "proposal_only",
9310:     approval_required: true,
9311:     no_live_external_action: true,
9312:   }));
9313: }
9314: 
9315: function buildAionCentralAssessmentHook(requestText = "") {
9316:   const inputBundle = buildAionCentralAssessmentInputBundle(requestText);
9317:   const assessment = buildAionCentralBusinessAssessment(inputBundle);
```

### Hit line 9306

```js
9294:       "No deployments",
9295:       "No external writes",
9296:     ],
9297:     created_at: new Date().toISOString(),
9298:   };
9299: }
9300: 
9301: function buildAionCentralPilotExecutionQueueProposal(actionPlan = {}) {
9302:   const items = safeArray(actionPlan.items);
9303: 
9304:   return items.map((item, index) => ({
9305:     id: item.id || `central_pilot_proposed_task_${index + 1}`,
9306:     title: item.title || `Central Pilot proposed task ${index + 1}`,
9307:     source: item.source || "central_aion_assessment_hook",
9308:     status: "waiting_human_approval",
9309:     safety: "proposal_only",
9310:     approval_required: true,
9311:     no_live_external_action: true,
9312:   }));
9313: }
9314: 
9315: function buildAionCentralAssessmentHook(requestText = "") {
9316:   const inputBundle = buildAionCentralAssessmentInputBundle(requestText);
9317:   const assessment = buildAionCentralBusinessAssessment(inputBundle);
9318:   const actionPlan = buildAionCentralApprovalRequiredActionPlan(inputBundle, assessment);
```

### Hit line 9319

```js
9307:     source: item.source || "central_aion_assessment_hook",
9308:     status: "waiting_human_approval",
9309:     safety: "proposal_only",
9310:     approval_required: true,
9311:     no_live_external_action: true,
9312:   }));
9313: }
9314: 
9315: function buildAionCentralAssessmentHook(requestText = "") {
9316:   const inputBundle = buildAionCentralAssessmentInputBundle(requestText);
9317:   const assessment = buildAionCentralBusinessAssessment(inputBundle);
9318:   const actionPlan = buildAionCentralApprovalRequiredActionPlan(inputBundle, assessment);
9319:   const executionQueueProposal = buildAionCentralPilotExecutionQueueProposal(actionPlan);
9320: 
9321:   return {
9322:     input_bundle: inputBundle,
9323:     assessment,
9324:     action_plan: actionPlan,
9325:     execution_queue_proposal: executionQueueProposal,
9326:     status: "assessment_ready",
9327:     created_at: new Date().toISOString(),
9328:   };
9329: }
9330: 
9331: function renderAionCentralAssessmentHookPanel(plan = null) {
```

### Hit line 9332

```js
9320: 
9321:   return {
9322:     input_bundle: inputBundle,
9323:     assessment,
9324:     action_plan: actionPlan,
9325:     execution_queue_proposal: executionQueueProposal,
9326:     status: "assessment_ready",
9327:     created_at: new Date().toISOString(),
9328:   };
9329: }
9330: 
9331: function renderAionCentralAssessmentHookPanel(plan = null) {
9332:   const safePlan = plan || buildAionPilotUniversalPlan("");
9333:   const hook =
9334:     safePlan.central_aion_assessment_hook ||
9335:     buildAionCentralAssessmentHook(safePlan.goal || "");
9336: 
9337:   const assessment = asRecord(hook.assessment) || {};
9338:   const actionPlan = asRecord(hook.action_plan) || {};
9339:   const queue = safeArray(hook.execution_queue_proposal);
9340:   const conflicts = safeArray(assessment.conflicts);
9341: 
9342:   return `
9343:     <section
9344:       class="panel large-panel"
```

### Hit line 9357

```js
9345:       data-aion-phase25h-central-assessment-hook="true"
9346:       style="background:#ffffff;"
9347:     >
9348:       <div class="panel-title">Central AION Assessment Hook</div>
9349:       <div class="helper-text">
9350:         Central AION reads the business foundation, Department Intelligence Ledger, Boardroom snapshot, runs, evidence, receipts and cross-department review before proposing any action.
9351:       </div>
9352: 
9353:       <div class="card-grid" style="margin-top:12px;">
9354:         ${renderDashboardMetricCard("Assessment", assessment.confidence || "none", assessment.scope || "not ready")}
9355:         ${renderDashboardMetricCard("Conflicts", conflicts.length, "Cross-department risks")}
9356:         ${renderDashboardMetricCard("Action Plan", safeArray(actionPlan.items).length, actionPlan.status || "proposal_only")}
9357:         ${renderDashboardMetricCard("Pilot Queue", queue.length, "Waiting approval")}
9358:       </div>
9359: 
9360:       <div class="notice warning" style="margin-top:12px;">
9361:         ${escapeHtml(assessment.summary || "AION assessment is waiting for department data.")}
9362:       </div>
9363: 
9364:       ${
9365:         queue.length
9366:           ? `
9367:             <div class="list-wrap" style="margin-top:12px;">
9368:               ${queue.map((item) => `
9369:                 <div class="list-item">
```

### Hit line 9371

```js
9359: 
9360:       <div class="notice warning" style="margin-top:12px;">
9361:         ${escapeHtml(assessment.summary || "AION assessment is waiting for department data.")}
9362:       </div>
9363: 
9364:       ${
9365:         queue.length
9366:           ? `
9367:             <div class="list-wrap" style="margin-top:12px;">
9368:               ${queue.map((item) => `
9369:                 <div class="list-item">
9370:                   <div class="list-item-title">${escapeHtml(item.title || "Proposed task")}</div>
9371:                   <div class="list-item-sub">Central Pilot proposal. Human approval required before any execution.</div>
9372:                   <div class="badge-row">
9373:                     ${renderStatusBadge(item.status || "waiting_human_approval")}
9374:                     <span class="badge">${escapeHtml(item.safety || "proposal_only")}</span>
9375:                     <span class="badge">No live external action</span>
9376:                   </div>
9377:                 </div>
9378:               `).join("")}
9379:             </div>
9380:           `
9381:           : `<div class="empty-state" style="margin-top:12px;">No central execution queue proposal yet.</div>`
9382:       }
9383:     </section>
```

### Hit line 9389

```js
9377:                 </div>
9378:               `).join("")}
9379:             </div>
9380:           `
9381:           : `<div class="empty-state" style="margin-top:12px;">No central execution queue proposal yet.</div>`
9382:       }
9383:     </section>
9384:   `;
9385: }
9386: 
9387: 
9388: const AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY = "aion.centralApprovedBoardroomActions";
9389: const AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY = "aion.centralPilotQueue";
9390: 
9391: function readAionCentralPilotStorageObject(storageKey = "") {
9392:   try {
9393:     const raw = window.localStorage?.getItem(storageKey);
9394:     if (!raw) return {};
9395:     const parsed = JSON.parse(raw);
9396:     return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
9397:   } catch (_error) {
9398:     return {};
9399:   }
9400: }
9401: 
```

### Hit line 9391

```js
9379:             </div>
9380:           `
9381:           : `<div class="empty-state" style="margin-top:12px;">No central execution queue proposal yet.</div>`
9382:       }
9383:     </section>
9384:   `;
9385: }
9386: 
9387: 
9388: const AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY = "aion.centralApprovedBoardroomActions";
9389: const AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY = "aion.centralPilotQueue";
9390: 
9391: function readAionCentralPilotStorageObject(storageKey = "") {
9392:   try {
9393:     const raw = window.localStorage?.getItem(storageKey);
9394:     if (!raw) return {};
9395:     const parsed = JSON.parse(raw);
9396:     return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
9397:   } catch (_error) {
9398:     return {};
9399:   }
9400: }
9401: 
9402: function writeAionCentralPilotStorageObject(storageKey = "", value = {}) {
9403:   try {
```

### Hit line 9402

```js
9390: 
9391: function readAionCentralPilotStorageObject(storageKey = "") {
9392:   try {
9393:     const raw = window.localStorage?.getItem(storageKey);
9394:     if (!raw) return {};
9395:     const parsed = JSON.parse(raw);
9396:     return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
9397:   } catch (_error) {
9398:     return {};
9399:   }
9400: }
9401: 
9402: function writeAionCentralPilotStorageObject(storageKey = "", value = {}) {
9403:   try {
9404:     window.localStorage?.setItem(storageKey, JSON.stringify(value || {}));
9405:   } catch (_error) {
9406:     // Local preview storage only.
9407:   }
9408:   return value || {};
9409: }
9410: 
9411: function getAionCentralApprovedBoardroomActions() {
9412:   const existing =
9413:     state.centralApprovedBoardroomActions &&
9414:     typeof state.centralApprovedBoardroomActions === "object" &&
```

### Hit line 9417

```js
9405:   } catch (_error) {
9406:     // Local preview storage only.
9407:   }
9408:   return value || {};
9409: }
9410: 
9411: function getAionCentralApprovedBoardroomActions() {
9412:   const existing =
9413:     state.centralApprovedBoardroomActions &&
9414:     typeof state.centralApprovedBoardroomActions === "object" &&
9415:     !Array.isArray(state.centralApprovedBoardroomActions)
9416:       ? state.centralApprovedBoardroomActions
9417:       : readAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY);
9418: 
9419:   state.centralApprovedBoardroomActions = existing;
9420:   return existing;
9421: }
9422: 
9423: function saveAionCentralApprovedBoardroomActions(next = {}) {
9424:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
```

### Hit line 9426

```js
9414:     typeof state.centralApprovedBoardroomActions === "object" &&
9415:     !Array.isArray(state.centralApprovedBoardroomActions)
9416:       ? state.centralApprovedBoardroomActions
9417:       : readAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY);
9418: 
9419:   state.centralApprovedBoardroomActions = existing;
9420:   return existing;
9421: }
9422: 
9423: function saveAionCentralApprovedBoardroomActions(next = {}) {
9424:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
```

### Hit line 9429

```js
9417:       : readAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY);
9418: 
9419:   state.centralApprovedBoardroomActions = existing;
9420:   return existing;
9421: }
9422: 
9423: function saveAionCentralApprovedBoardroomActions(next = {}) {
9424:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
```

### Hit line 9431

```js
9419:   state.centralApprovedBoardroomActions = existing;
9420:   return existing;
9421: }
9422: 
9423: function saveAionCentralApprovedBoardroomActions(next = {}) {
9424:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
```

### Hit line 9432

```js
9420:   return existing;
9421: }
9422: 
9423: function saveAionCentralApprovedBoardroomActions(next = {}) {
9424:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
9444:   return writeAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY, value);
```

### Hit line 9433

```js
9421: }
9422: 
9423: function saveAionCentralApprovedBoardroomActions(next = {}) {
9424:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
9444:   return writeAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY, value);
9445: }
```

### Hit line 9434

```js
9422: 
9423: function saveAionCentralApprovedBoardroomActions(next = {}) {
9424:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
9444:   return writeAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY, value);
9445: }
9446: 
```

### Hit line 9435

```js
9423: function saveAionCentralApprovedBoardroomActions(next = {}) {
9424:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
9444:   return writeAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY, value);
9445: }
9446: 
9447: function approveAionCentralBoardroomAction(actionId = "", sourceHook = null) {
```

### Hit line 9437

```js
9425:   state.centralApprovedBoardroomActions = value;
9426:   return writeAionCentralPilotStorageObject(AION_CENTRAL_APPROVED_BOARDROOM_ACTIONS_STORAGE_KEY, value);
9427: }
9428: 
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
9444:   return writeAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY, value);
9445: }
9446: 
9447: function approveAionCentralBoardroomAction(actionId = "", sourceHook = null) {
9448:   const id = String(actionId || "").trim();
9449:   if (!id) return null;
```

### Hit line 9441

```js
9429: function getAionCentralPilotQueue() {
9430:   const existing =
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
9444:   return writeAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY, value);
9445: }
9446: 
9447: function approveAionCentralBoardroomAction(actionId = "", sourceHook = null) {
9448:   const id = String(actionId || "").trim();
9449:   if (!id) return null;
9450: 
9451:   const hook = sourceHook || buildAionCentralAssessmentHook("");
9452:   const actionPlan = asRecord(hook.action_plan) || {};
9453:   const proposedItems = safeArray(actionPlan.items);
```

### Hit line 9443

```js
9431:     state.centralPilotQueue &&
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
9444:   return writeAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY, value);
9445: }
9446: 
9447: function approveAionCentralBoardroomAction(actionId = "", sourceHook = null) {
9448:   const id = String(actionId || "").trim();
9449:   if (!id) return null;
9450: 
9451:   const hook = sourceHook || buildAionCentralAssessmentHook("");
9452:   const actionPlan = asRecord(hook.action_plan) || {};
9453:   const proposedItems = safeArray(actionPlan.items);
9454:   const proposed = proposedItems.find((item) => String(item?.id || "") === id);
9455: 
```

### Hit line 9444

```js
9432:     typeof state.centralPilotQueue === "object" &&
9433:     !Array.isArray(state.centralPilotQueue)
9434:       ? state.centralPilotQueue
9435:       : readAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY);
9436: 
9437:   state.centralPilotQueue = existing;
9438:   return existing;
9439: }
9440: 
9441: function saveAionCentralPilotQueue(next = {}) {
9442:   const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
9443:   state.centralPilotQueue = value;
9444:   return writeAionCentralPilotStorageObject(AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY, value);
9445: }
9446: 
9447: function approveAionCentralBoardroomAction(actionId = "", sourceHook = null) {
9448:   const id = String(actionId || "").trim();
9449:   if (!id) return null;
9450: 
9451:   const hook = sourceHook || buildAionCentralAssessmentHook("");
9452:   const actionPlan = asRecord(hook.action_plan) || {};
9453:   const proposedItems = safeArray(actionPlan.items);
9454:   const proposed = proposedItems.find((item) => String(item?.id || "") === id);
9455: 
9456:   if (!proposed) return null;
```

### Hit line 9475

```js
9463:     id,
9464:     status: "approved",
9465:     approved_at: now,
9466:     approved_by: "human_operator",
9467:     source: proposed.source || "central_aion_assessment_hook",
9468:     approval_required: true,
9469:     no_live_external_action: true,
9470:   };
9471: 
9472:   approvedActions[id] = approved;
9473:   saveAionCentralApprovedBoardroomActions(approvedActions);
9474: 
9475:   const queue = buildAionCentralApprovedPilotQueue({ render: false });
9476:   saveAionCentralPilotQueue(queue);
9477: 
9478:   if (typeof requestRender === "function") {
9479:     requestRender();
9480:   }
9481: 
9482:   return approved;
9483: }
9484: 
9485: function buildAionCentralApprovedPilotQueue(options = {}) {
9486:   const approvedActions = getAionCentralApprovedBoardroomActions();
9487:   const existingQueue = getAionCentralPilotQueue();
```

### Hit line 9476

```js
9464:     status: "approved",
9465:     approved_at: now,
9466:     approved_by: "human_operator",
9467:     source: proposed.source || "central_aion_assessment_hook",
9468:     approval_required: true,
9469:     no_live_external_action: true,
9470:   };
9471: 
9472:   approvedActions[id] = approved;
9473:   saveAionCentralApprovedBoardroomActions(approvedActions);
9474: 
9475:   const queue = buildAionCentralApprovedPilotQueue({ render: false });
9476:   saveAionCentralPilotQueue(queue);
9477: 
9478:   if (typeof requestRender === "function") {
9479:     requestRender();
9480:   }
9481: 
9482:   return approved;
9483: }
9484: 
9485: function buildAionCentralApprovedPilotQueue(options = {}) {
9486:   const approvedActions = getAionCentralApprovedBoardroomActions();
9487:   const existingQueue = getAionCentralPilotQueue();
9488:   const now = new Date().toISOString();
```

### Hit line 9485

```js
9473:   saveAionCentralApprovedBoardroomActions(approvedActions);
9474: 
9475:   const queue = buildAionCentralApprovedPilotQueue({ render: false });
9476:   saveAionCentralPilotQueue(queue);
9477: 
9478:   if (typeof requestRender === "function") {
9479:     requestRender();
9480:   }
9481: 
9482:   return approved;
9483: }
9484: 
9485: function buildAionCentralApprovedPilotQueue(options = {}) {
9486:   const approvedActions = getAionCentralApprovedBoardroomActions();
9487:   const existingQueue = getAionCentralPilotQueue();
9488:   const now = new Date().toISOString();
9489: 
9490:   const tasks = Object.values(approvedActions).map((action, index) => {
9491:     const existing = existingQueue[action.id] || {};
9492:     return {
9493:       ...existing,
9494:       id: action.id || `central_approved_action_${index + 1}`,
9495:       title: action.title || `Approved Boardroom action ${index + 1}`,
9496:       source: action.source || "central_aion_assessment_hook",
9497:       departments: safeArray(action.departments),
```

### Hit line 9487

```js
9475:   const queue = buildAionCentralApprovedPilotQueue({ render: false });
9476:   saveAionCentralPilotQueue(queue);
9477: 
9478:   if (typeof requestRender === "function") {
9479:     requestRender();
9480:   }
9481: 
9482:   return approved;
9483: }
9484: 
9485: function buildAionCentralApprovedPilotQueue(options = {}) {
9486:   const approvedActions = getAionCentralApprovedBoardroomActions();
9487:   const existingQueue = getAionCentralPilotQueue();
9488:   const now = new Date().toISOString();
9489: 
9490:   const tasks = Object.values(approvedActions).map((action, index) => {
9491:     const existing = existingQueue[action.id] || {};
9492:     return {
9493:       ...existing,
9494:       id: action.id || `central_approved_action_${index + 1}`,
9495:       title: action.title || `Approved Boardroom action ${index + 1}`,
9496:       source: action.source || "central_aion_assessment_hook",
9497:       departments: safeArray(action.departments),
9498:       severity: action.severity || "",
9499:       status: existing.status || "approved_safe_preview",
```

### Hit line 9510

```js
9498:       severity: action.severity || "",
9499:       status: existing.status || "approved_safe_preview",
9500:       safety: "internal_preview_only",
9501:       approval_boundary: "no_live_external_side_effects",
9502:       approval_required: true,
9503:       no_live_external_action: true,
9504:       approved_at: action.approved_at || now,
9505:       updated_at: now,
9506:     };
9507:   });
9508: 
9509:   const nextQueue = Object.fromEntries(tasks.map((task) => [task.id, task]));
9510:   saveAionCentralPilotQueue(nextQueue);
9511: 
9512:   if (options.render !== false && typeof requestRender === "function") {
9513:     requestRender();
9514:   }
9515: 
9516:   return nextQueue;
9517: }
9518: 
9519: function getAionCentralPilotNextApprovedTask() {
9520:   const queue = getAionCentralPilotQueue();
9521:   return Object.values(queue).find((item) => {
9522:     const status = String(item?.status || "").toLowerCase();
```

## Data attributes / CSS classes containing live/pilot/agent

- `aion-agentmap-install-card`
- `aion-live-agents-aion-pilot-surface`
- `aion-live-agents-pilot-fixed-terminal`
- `aion-live-agents-pilot-workspace`
- `aion-o12b-pilot-queue`
- `aion-o12b-pilot-task`
- `aion-o13c-pilot-task-toolbar`
- `aion-o13c-pilot-task-toolbar-style`
- `aion-o13d-live-agents-pilot-preview`
- `aion-o13d-live-agents-pilot-preview-style`
- `aion-phase17g-live-actions`
- `aion-phase23y-live-agents-white`
- `aion-phase23y-live-agents-white-shell`
- `aion-phase23y-white-live-agents-surface-styles`
- `aion-pilot-`
- `aion-pilot-actions`
- `aion-pilot-advanced-details`
- `aion-pilot-approval-stage-list`
- `aion-pilot-approval-stage-row`
- `aion-pilot-approval-stage-task`
- `aion-pilot-approval-stage-toggle`
- `aion-pilot-approval-trace`
- `aion-pilot-approval-trace-style-phase22m`
- `aion-pilot-artifact-card`
- `aion-pilot-blocked-card`
- `aion-pilot-card-kicker`
- `aion-pilot-clean-tracked-draft-button`
- `aion-pilot-cockpit`
- `aion-pilot-cockpit-styles`
- `aion-pilot-composer-bar`
- `aion-pilot-department-lane`
- `aion-pilot-department-lane-grid`
- `aion-pilot-department-queue-summary`
- `aion-pilot-draft-preview-card`
- `aion-pilot-feedback`
- `aion-pilot-follow-on-actions`
- `aion-pilot-follow-on-completed`
- `aion-pilot-follow-on-current-grid`
- `aion-pilot-follow-on-list`
- `aion-pilot-follow-on-queue`
- `aion-pilot-follow-on-row`
- `aion-pilot-follow-on-sticky`
- `aion-pilot-follow-on-summary`
- `aion-pilot-follow-on-task`
- `aion-pilot-follow-on-toggle`
- `aion-pilot-follow-on-work-queue-style-phase22o`
- `aion-pilot-grid`
- `aion-pilot-grid-three`
- `aion-pilot-header`
- `aion-pilot-human-approval-checklist`
- `aion-pilot-human-approval-checklist-style-phase22n`
- `aion-pilot-lrm-compact-card`
- `aion-pilot-map-node`
- `aion-pilot-meta-row`
- `aion-pilot-mission-input`
- `aion-pilot-mission-thread-command-bar-style-phase22s`
- `aion-pilot-operator-identity`
- `aion-pilot-output-card`
- `aion-pilot-output-card-header`
- `aion-pilot-output-change-strip`
- `aion-pilot-output-meta`
- `aion-pilot-output-panel`
- `aion-pilot-output-panel-header`
- `aion-pilot-output-pre`
- `aion-pilot-output-revised`
- `aion-pilot-panel`
- `aion-pilot-panel-copy`
- `aion-pilot-panel-kicker`
- `aion-pilot-panel-title`
- `aion-pilot-queue-consuming-follow-on-style-phase22p`
- `aion-pilot-reasoning-mini`
- `aion-pilot-result-card`
- `aion-pilot-safety-banner`
- `aion-pilot-safety-card`
- `aion-pilot-simple-dashboard`
- `aion-pilot-simple-hero`
- `aion-pilot-simplified-header-phase22k`
- `aion-pilot-status`
- `aion-pilot-step-card`
- `aion-pilot-step-number`
- `aion-pilot-sticky-follow-on-queue-style-phase22q`
- `aion-pilot-stream-card`
- `aion-pilot-stream-columns`
- `aion-pilot-stream-header`
- `aion-pilot-stream-message`
- `aion-pilot-stream-message-system`
- `aion-pilot-stream-message-user`
- `aion-pilot-stream-shell`
- `aion-pilot-stream-window`
- `aion-pilot-terminal-output`
- `aion-pilot-terminal-output-style-phase22j`
- `aion-pilot-trace-approved`
- `aion-pilot-trace-revised`
- `aion-pilot-trace-state`
- `aion-pilot-trace-stopped`
- `aion-pilot-tracked-change-badge`
- `aion-pilot-tracked-change-strip`
- `aion-pilot-tracked-draft-edit-style-phase22w`
- `aion-pilot-tracked-line`
- `aion-pilot-tracked-line-added`
- `aion-pilot-tracked-line-removed`
- `aion-pilot-two-list`
- `aion-pilot-user-flow`
- `aion-vault-enable-live-btn`
- `aion-workflow-file-cabinet-create-workflow-live-save-v7`
- `data-aion-agentmap-install-card`
- `data-aion-boardroom-live-run-status`
- `data-aion-council-session-delegate-agents`
- `data-aion-department-pilot-action`
- `data-aion-department-pilot-discovery-field`
- `data-aion-department-pilot-missing-list`
- `data-aion-department-pilot-scope`
- `data-aion-department-scoped-pilot`
- `data-aion-finance-live-agents-workspace-v2`
- `data-aion-goal-engine-guarded-child-agent-execution-handoff`
- `data-aion-goal-engine-live-kpis`
- `data-aion-goal-engine-multi-agent-execution-replay`
- `data-aion-goal-loop-central-pilot-safe-queue`
- `data-aion-goal-loop-department-pilot-context`
- `data-aion-goal-loop-guarded-handoff-next-live-phase`
- `data-aion-live-agents-aion-pilot-workspace`
- `data-aion-lrm-pilot-context-card`
- `data-aion-lrm-pilot-context-event`
- `data-aion-lrm-pilot-context-safety`
- `data-aion-o13c-build-active-pilot-task-packets`
- `data-aion-o13c-pilot-task-toolbar`
- `data-aion-o13d-live-agents-pilot-preview`
- `data-aion-phase17g-home-fixed-live-test-card`
- `data-aion-phase17g-live-actions`
- `data-aion-phase21l-live-agents-aion-pilot-mount`
- `data-aion-phase21x-real-frontend-pilot-mount`
- `data-aion-phase23y-persistent-pilot-start`
- `data-aion-phase23y-persistent-pilot-terminal`
- `data-aion-phase23y-persistent-pilot-terminal-input`
- `data-aion-phase23y-pilot-marketing-artifact-card`
- `data-aion-phase23y-pilot-marketing-empty`
- `data-aion-phase23y-pilot-marketing-workspace`
- `data-aion-phase23z-pilot-marketing-deliverable-card`
- `data-aion-phase23z-pilot-marketing-deliverable-group`
- `data-aion-phase25b-department-scoped-pilot`
- `data-aion-phase25c-department-pilot-discovery`
- `data-aion-phase25c-department-pilot-ledger-sync`
- `data-aion-phase25c-department-pilot-ledger-writeback`
- `data-aion-phase25c-department-pilot-plan`
- `data-aion-phase25c-department-pilot-safe-queue`
- `data-aion-phase25d-department-pilot-safe-queue`
- `data-aion-phase25f-department-specialist-pilot`
- `data-aion-phase25j-department-pilot-guided-workflow`
- `data-aion-pilot-advanced-details`
- `data-aion-pilot-approval-stage-row`
- `data-aion-pilot-approval-stage-toggle`
- `data-aion-pilot-artifact-card`
- `data-aion-pilot-blocked-action`
- `data-aion-pilot-chat-pointer`
- `data-aion-pilot-close-output-panel`
- `data-aion-pilot-close-step-output`
- `data-aion-pilot-composer`
- `data-aion-pilot-continue-safe-work`
- `data-aion-pilot-create-draft-mission`
- `data-aion-pilot-department-lane`
- `data-aion-pilot-department-queue-summary`
- `data-aion-pilot-download-output`
- `data-aion-pilot-feedback-approve`
- `data-aion-pilot-feedback-revise`
- `data-aion-pilot-feedback-stop`
- `data-aion-pilot-follow-on-approval-toggle`
- `data-aion-pilot-follow-on-expand`
- `data-aion-pilot-follow-on-queue`
- `data-aion-pilot-follow-on-row`
- `data-aion-pilot-human-approval-checklist`
- `data-aion-pilot-inline-output-panel`
- `data-aion-pilot-live-agents-entry`
- `data-aion-pilot-map-node`
- `data-aion-pilot-mission-input`
- `data-aion-pilot-open-output`
- `data-aion-pilot-open-step-output`
- `data-aion-pilot-output-kind`
- `data-aion-pilot-output-panel`
- `data-aion-pilot-plan-card`
- `data-aion-pilot-ready-step-label`
- `data-aion-pilot-simple-dashboard`
- `data-aion-pilot-step-checkpoint-card`
- `data-aion-pilot-step-output-card`
- `data-aion-pilot-stream-event`
- `data-aion-pilot-stream-window`
- `data-aion-pilot-view-receipt`
- `data-aion-pilot-visible-stream-events`
- `data-aion-pilot-work-package-actions`
- `data-aion-vault-request-live-send`

## Window globals containing live/pilot/agent

- `window.__aionAgentMapDashboardState`
- `window.__aionBoardroomLivePayload`
- `window.__aionBoardroomLiveRunStatus`
- `window.__aionCentralPilotGoalSheetTaskQueuePreview`
- `window.__aionExistingCentralPilotPreviewQueue`
- `window.__aionExistingDepartmentPilotPreviewQueues`
- `window.__aionGmailLiveSendRequested`
- `window.__aionGoalEngineGuardedChildAgentExecutionHandoffPanelV1Installed`
- `window.__aionGoalEngineMultiAgentExecutionReplayV1Installed`
- `window.__aionGoalLoopPilotQueuePreview`
- `window.__aionGoalSheetActiveDepartmentPilotTaskQueueO13C`
- `window.__aionGoalSheetPilotTaskQueueO13C`
- `window.__aionLiveAgentsFocusDepartment`
- `window.__aionLiveAgentsGoalSheetPreviewTasks`
- `window.__aionLiveAgentsPilotPreviewStateO13D`
- `window.__aionLiveAgentsSelectedTab`
- `window.__aionO13CDepartmentGoalSheetPilotTaskPacketsInstalled`
- `window.__aionO13DLiveAgentsPilotPreviewStateBridgeInstalled`
- `window.__aionPhase17GLiveTestState`
- `window.__aionPhase25BDepartmentScopedPilotHandlersInstalled`
- `window.__aionPhase25CDepartmentPilotDiscoveryHandlersInstalled`
- `window.__aionPhase25DDepartmentPilotHandlersInstalled`
- `window.__aionPilotContinueSafeWorkClickHandlerInstalled`
- `window.__aionPilotFollowOnApprovalClickHandlerInstalled`
- `window.__aionPilotFollowOnQueueExpandClickHandlerInstalled`
- `window.__aionPilotFrontendInteractionState`
- `window.__aionPilotHumanApprovalStageClickHandlerInstalled`
- `window.__aionPilotRevisionCommandBarClickHandlerInstalled`
- `window.__aionPreferredLiveAgentDepartment`

## Function names containing live/pilot/agent/department

- `TessarisDesktopLiveAgentsRuntime`
- `__aionActiveDepartment`
- `__aionAgentMapDashboardState`
- `__aionBoardroomDepartmentTasks`
- `__aionBoardroomLivePayload`
- `__aionBoardroomLiveRunStatus`
- `__aionCentralPilotGoalSheetTaskQueuePreview`
- `__aionExistingCentralPilotPreviewQueue`
- `__aionExistingDepartmentPilotPreviewQueues`
- `__aionGmailLiveSendRequested`
- `__aionGoalEngineGuardedChildAgentExecutionHandoffPanelV1Installed`
- `__aionGoalEngineMultiAgentExecutionReplayV1Installed`
- `__aionGoalLoopDepartmentGoalSheets`
- `__aionGoalLoopDepartmentTaskQueueWritebackPreview`
- `__aionGoalLoopPilotQueuePreview`
- `__aionGoalSheetActiveDepartmentPilotTaskQueueO13C`
- `__aionGoalSheetPilotTaskQueueO13C`
- `__aionLiveAgentsFocusDepartment`
- `__aionLiveAgentsGoalSheetPreviewTasks`
- `__aionLiveAgentsPilotPreviewStateO13D`
- `__aionLiveAgentsSelectedTab`
- `__aionMinimalDepartmentSwitcherFastHandlerInstalled`
- `__aionO13BLastOpenedDepartmentGoalSheet`
- `__aionO13BLinkedDepartmentGoalSheetOpenerInstalled`
- `__aionO13CDepartmentGoalSheetPilotTaskPacketsInstalled`
- `__aionO13DLiveAgentsPilotPreviewStateBridgeInstalled`
- `__aionPhase17GLiveTestState`
- `__aionPhase25BDepartmentScopedPilotHandlersInstalled`
- `__aionPhase25CDepartmentPilotDiscoveryHandlersInstalled`
- `__aionPhase25DDepartmentPilotHandlersInstalled`
- `__aionPhase25FDepartmentSpecialistHandlersInstalled`
- `__aionPilotContinueSafeWorkClickHandlerInstalled`
- `__aionPilotFollowOnApprovalClickHandlerInstalled`
- `__aionPilotFollowOnQueueExpandClickHandlerInstalled`
- `__aionPilotFrontendInteractionState`
- `__aionPilotHumanApprovalStageClickHandlerInstalled`
- `__aionPilotRevisionCommandBarClickHandlerInstalled`
- `__aionPreferredLiveAgentDepartment`
- `__aionSelectedDepartment`
- `activateAionPilotRevisionCommandContext`
- `activePilotDepartmentScope`
- `aionBuildActiveDepartmentPilotTaskPacketsO13C`
- `aionBuildAllDepartmentGoalSheetsO13A`
- `aionBuildAllDepartmentPilotTaskPacketsO13C`
- `aionBuildDepartmentGoalSheetGraphO13A`
- `aionBuildPilotPreviewStateO13D`
- `aionBuildPilotTaskPacketsForDepartmentSheetO13C`
- `aionCloseDepartmentChooserO13B`
- `aionClosePilotPreviewPanelO13D`
- `aionEnsureDepartmentSheetRegistryO13B`
- `aionEnsurePilotQueueO13D`
- `aionGetDepartmentGoalSheetsO13C`
- `aionOpenDepartmentGoalSheetO13B`
- `aionPilotApprovePlanButton`
- `aionPilotCancelPlanButton`
- `aionPilotCloseOutputPanelButton`
- `aionPilotCloseStepOutputButton`
- `aionPilotContinueSafeWorkButton`
- `aionPilotCreateDraftMissionButton`
- `aionPilotDownloadOutputButton`
- `aionPilotOpenOutputButton`
- `aionPilotOpenStepOutputButton`
- `aionPilotRevisePlanButton`
- `aionPilotViewReceiptButton`
- `aionPublishPilotPreviewStateO13D`
- `aionRenderDepartmentChooserO13B`
- `aionRenderPilotPreviewPanelO13D`
- `allowedDepartments`
- `appendAionPilotStepOutput`
- `appendAionPilotStreamEvent`
- `applyAionDepartmentPilotAction`
- `applyAionGoalLoopDepartmentCanvasLinks`
- `applyAionLrmPilotContextPreviewPayload`
- `applyAionPilotArtifactPreviewPayload`
- `applyAionPilotCommandBarRevisionIfActive`
- `applyAionPilotMissionPreviewPayload`
- `applyAionPilotMissionPreviewQueuesToState`
- `applyAionPilotPrecisePlaceholderRevisionLine`
- `applyAionPilotSimpleMissionThreadRevision`
- `approveAionDepartmentPilotPlan`
- `approveAionPilotMissionContract`
- `buildActiveDepartmentPilotTaskPacketsO13C`
- `buildAgentMapDashboardPreviewPayload`
- `buildAgentMapHostedExportOptions`
- `buildAionBoardroomCrossDepartmentReview`
- `buildAionCentralApprovedPilotQueue`
- `buildAionCentralPilotExecutionQueueProposal`
- `buildAionDepartmentAssessmentFeed`
- `buildAionDepartmentBoardroomSummary`
- `buildAionDepartmentPilotPlanDraft`
- `buildAionDepartmentPilotSafeTaskQueue`
- `buildAionDepartmentPilotSpecialistDraft`
- `buildAionDepartmentPilotSpecialistSafeQueue`
- `buildAionDepartmentTasksFromDebateV2`
- `buildAionGoalLoopCentralPilotTaskQueue`
- `buildAionGoalLoopDepartmentCanvasLinks`
- `buildAionGoalLoopDepartmentMetricSet`
- `buildAionGoalLoopDepartmentPilotContextMap`
- `buildAionGoalLoopDepartmentTaskQueueWritebackPatch`
- `buildAionLiveConsensusFromProviderFanoutV1`
- `buildAionLiveDebateItemV1`
- `buildAionLiveDepartmentTasksFromDebateV1`
- `buildAionMarketingDepartmentContextV1`
- `buildAionPilotApprovalDraftOutput`
- `buildAionPilotArtifactPreviewPayload`
- `buildAionPilotBusinessPlanDraft`
- `buildAionPilotDocumentDraft`
- `buildAionPilotExecuteSafeStepPayload`
- `buildAionPilotFollowOnTaskDraftOutput`
- `buildAionPilotGeneratedOutput`
- `buildAionPilotMarketingPlanDraft`
- `buildAionPilotMissionPreviewPayload`
- `buildAionPilotPriorityStepOutput`
- `buildAionPilotRevisionDraftOutput`
- `buildAionPilotUniversalPlan`
- `buildAionPilotWorkPackage`
- `buildAllDepartmentGoalSheetsO13A`
- `buildAllDepartmentPilotTaskPacketsO13C`
- `buildDepartmentGoalSheetGraph`
- `buildDepartmentGoalSheetGraphO13A`
- `buildDepartmentRoomCards`
- `buildLiveAgentCards`
- `buildPilotPreviewStateO13D`
- `buildPilotQueuePreview`
- `buildPilotTaskPacketFromNodeO13C`
- `buildPilotTaskPacketsForDepartmentSheetO13C`
- `byDepartment`
- `cancelAionPilotMissionContract`
- `childAgentId`
- `childByDepartment`
- `classifyAionDepartmentCrossReviewState`
- `classifyAionPilotApprovalRequirementMode`
- `classifyAionPilotFollowOnWorkItem`
- `classifyAionPilotMarketingArtifact`
- `classifyAionPilotUniversalTask`
- `cleanAionPilotAddedPhrase`
- `cleanAionPilotEditPhrase`
- `cleanAionPilotTrackedDraftOutput`
- `cleanAionPilotTrackedDraftText`
- `clearAionBoardroomLiveRunStatusV1`
- `closeAionPilotOutputPanel`
- `closeAionPilotStepOutput`
- `closeDepartmentChooserO13B`
- `closePilotPreviewPanelO13D`
- `collectAionDepartmentPilotDiscoveryFromForm`
- `copyAgentMapValue`
- `createAionPilotFrontendDraftMission`
- `createWorkflowLive`
- `crossDepartmentReview`
- `delegateAgents`
- `deriveAionPilotFollowOnWorkItems`
- `downloadAionPilotOutputPreview`
- `ensureAionPhase23YLiveAgentsWhiteSurfaceStyles`
- `ensureDepartmentSheetRegistryO13B`
- `ensureLiveAgentSelection`
- `ensurePilotQueueO13D`
- `ensurePilotTaskPacketToolbarO13C`
- `executeAndAppendAionPilotMissionMapStepOutput`
- `extractAionLiveProviderStructuredJsonV1`
- `extractAionPilotReplacementOperation`
- `fetchAionLrmPilotContextPreviewIntoPilotState`
- `fetchAionPilotArtifactPreviewIntoPilotState`
- `fetchAionPilotExecuteSafeStep`
- `fetchAionPilotMissionPreviewIntoPilotState`
- `filterAionLinesForDepartmentOrItemV1`
- `findSelectedLiveRun`
- `forceSaveLiveCabinet`
- `gateDepartment`
- `getActiveDepartmentO13D`
- `getActiveDepartmentSheetO13C`
- `getAgentMapDashboardPreviewPayload`
- `getAgentMapFrontendState`
- `getAgentMapSelfHostedExportPayload`
- `getAionActiveGoalLoopDepartmentContext`
- `getAionActiveGoalLoopGraphForCentralPilotQueue`
- `getAionActiveGoalLoopGraphForDepartmentContext`
- `getAionBoardroomSelectedDepartmentPulseKey`
- `getAionCentralPilotNextApprovedTask`
- `getAionCentralPilotQueue`
- `getAionCoreDepartmentKeys`
- `getAionCouncilDepartmentContextPacketLines`
- `getAionCurrentLiveRoundOneResultV1`
- `getAionDepartmentDefaultInputsV1`
- `getAionDepartmentIntelligence`
- `getAionDepartmentIntelligenceEarlyCompatV1`
- `getAionDepartmentLedgerEntry`
- `getAionDepartmentLedgerEntryEarlyCompatV1`
- `getAionDepartmentObjectiveV1`
- `getAionDepartmentOutputRequiredV1`
- `getAionDepartmentPilotApprovalState`
- `getAionDepartmentPilotApprovedTaskQueue`
- `getAionDepartmentPilotBoardroomSummary`
- `getAionDepartmentPilotCompletion`
- `getAionDepartmentPilotDiscoveryTemplate`
- `getAionDepartmentPilotLedgerEntry`
- `getAionDepartmentPilotNextSafeTask`
- `getAionDepartmentPilotProfile`
- `getAionDepartmentPilotSpecialistPlaybook`
- `getAionDepartmentPilotStatus`
- `getAionDepartmentPulseAccentColor`
- `getAionDepartmentPulseSummaryItems`
- `getAionDepartmentResultEvidenceStatus`
- `getAionExtendedDepartmentKeys`
- `getAionGoalLoopCentralPilotTaskQueue`
- `getAionGoalLoopDepartmentSignalFromFeedback`
- `getAionGoalLoopNodeDepartment`
- `getAionLrmPilotContextPreviewUrl`
- `getAionParsedLiveProviderPayloadsV1`
- `getAionPhase17GLiveTestState`
- `getAionPilotApprovalStagePayload`
- `getAionPilotArtifactNameForPlan`
- `getAionPilotArtifactPreviewUrl`
- `getAionPilotArtifactTypeForPlan`
- `getAionPilotAvailableVaultRequirements`
- `getAionPilotCockpitSnapshot`
- `getAionPilotCommandBarContext`
- `getAionPilotCommandBarPlaceholder`
- `getAionPilotCommandBarValue`
- `getAionPilotCommandButtonLabel`
- `getAionPilotCompletedFollowOnWork`
- `getAionPilotCurrentMissionDraftText`
- `getAionPilotExecuteSafeStepUrl`
- `getAionPilotFollowOnApprovalStages`
- `getAionPilotFollowOnWorkKey`
- `getAionPilotFollowOnWorkQueue`
- `getAionPilotFrontendInteractionState`
- `getAionPilotHumanApprovalStageKey`
- `getAionPilotHumanApprovalStages`
- `getAionPilotLatestEditableOutput`
- `getAionPilotLatestEditableOutputText`
- `getAionPilotLatestOutputText`
- `getAionPilotMarketingWorkspaceArtifacts`
- `getAionPilotMissionPreviewUrl`
- `getAionPilotNextExecutableFollowOnWorkItem`
- `getAionPilotOutputPreparedDetail`
- `getAionPilotOutputPreparedLabel`
- `getAionPilotOutputPreviewText`
- `getAionPilotPendingApprovalDrafts`
- `getAionPilotReceiptPreview`
- `getAionPilotResolvedGeneratedOutput`
- `getAionPilotStepOutputTitle`
- `getAionPilotStepOutputs`
- `getAionPilotTaskSubject`
- `getAionPilotWorkPackageDraftStepsForBackend`
- `getBoardroomDepartments`
- `getBusinessDepartmentContextDraft`
- `getBusinessDepartmentDefaultStatus`
- `getCurrentPilotViewO13D`
- `getDefaultAgentMapDashboardPreviewPayload`
- `getDepartmentApprovals`
- `getDepartmentExceptions`
- `getDepartmentPendingApprovals`
- `getDepartmentRecentAudit`
- `getDepartmentRunCounts`
- `getDepartmentRuns`
- `getDepartmentRuntime`
- `getDepartmentRuntimeList`
- `getDepartmentSheetsO13C`
- `getLiveAgentsMarketingWorkspaceMode`
- `getLiveAgentsView`
- `getPrimaryDepartmentAgentCard`
- `getRecentDepartmentRuns`
- `getRunsForSelectedLiveAgent`
- `getSelectedLiveAgentCard`
- `getSelectedLiveDepartmentKey`
- `groupAionPilotMarketingArtifacts`
- `handleCopyAgentMapInstallTag`
- `handleCopyAgentMapUrl`
- `handleDownloadAgentMapJson`
- `handleGenerateAgentMapClick`
- `handleGenerateAgentMapPreview`
- `handleRegenerateAgentMapPreview`
- `inferAionDepartmentFromPlanLineV2`
- `inferAionDepartmentFromTaskDraftV1`
- `inferAionDepartmentFromTextV3`
- `inferAionDiscoveryDepartmentFromGateV1`
- `inferAionDiscoveryDepartmentV1`
- `inferAionTaskOwnerFromDepartmentV1`
- `initialDepartmentSheets`
- `installAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1`
- `installAionGoalEngineMultiAgentExecutionReplayV1`
- `installAionO13BLinkedDepartmentGoalSheetOpener`
- `installAionO13CDepartmentGoalSheetPilotTaskPackets`
- `installAionO13DLiveAgentsPilotPreviewStateBridge`
- `installAionPilotApprovalTraceStylesPhase22M`
- `installAionPilotCockpitStyles`
- `installAionPilotFollowOnWorkQueueStylesPhase22O`
- `installAionPilotHumanApprovalChecklistStylesPhase22N`
- `installAionPilotMissionThreadCommandBarStylesPhase22S`
- `installAionPilotQueueConsumingFollowOnStylesPhase22P`
- `installAionPilotSimplifiedHeaderPhase22K`
- `installAionPilotStickyFollowOnQueueStylesPhase22Q`
- `installAionPilotTerminalOutputStylesPhase22J`
- `installAionPilotTrackedDraftEditStylesPhase22W`
- `installAionVaultLiveSendRequestGuard`
- `installAionVaultLiveSendRequestGuardContractOnly`
- `installAionWorkflowFileCabinetCreateWorkflowLiveSaveV7`
- `isDepartmentGoalSheetO13C`
- `isDepartmentLinksNode`
- `isDepartmentSelected`