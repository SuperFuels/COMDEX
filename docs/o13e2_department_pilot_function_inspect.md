# O13E.2 Department Pilot Function Inspection

Source: `desktop/mac/src/app.js`

Found 229 target hits and 114 extracted function/block windows.

## Extracted function/block windows


### Hit line 4158: `function renderDepartmentApprovalsSurface(departmentKey, selectedAgentCard) {`

```js
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
4171:         ${renderDashboardMetricCard(
4172:           "Total approvals",
4173:           counts.total,
4174:           "All recorded approval events",
4175:         )}
4176:         ${renderDashboardMetricCard(
4177:           "Pending",
4178:           counts.pending,
4179:           "Awaiting decision",
4180:         )}
4181:         ${renderDashboardMetricCard(
4182:           "Resolved",
4183:           counts.approved + counts.rejected,
4184:           `Approved ${counts.approved} · Rejected ${counts.rejected}`,
4185:         )}
4186:       </div>
4187: 
4188:       <div class="panel large-panel">
4189:         <div class="panel-title">${escapeHtml(departmentLabel)} Approval History</div>
4190: 
4191:         ${
4192:           approvals.length
4193:             ? `
4194:               <div class="list-wrap">
4195:                 ${approvals.map((item) => {
4196:                   const runId =
4197:                     item?.run_id ||
4198:                     item?.queue_item_id ||
4199:                     item?.runtime_run_id ||
4200:                     "";
4201:                   const linkedRun = findRunById(runId);
4202:                   const workflowLabel = linkedRun
4203:                     ? runtimeShared.getRunWorkflowLabel(linkedRun)
4204:                     : item?.title || "Approval";
4205:                   const agentLabel = linkedRun
4206:                     ? runtimeShared.getRunAgentLabel(linkedRun)
4207:                     : item?.requested_by || "unknown";
4208: 
4209:                   return `
4210:                     <div class="list-item">
4211:                       <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px;">
4212:                         <div>
4213:                           <div class="list-item-title">${escapeHtml(workflowLabel)}</div>
4214:                           <div class="list-item-sub">${escapeHtml(agentLabel)}</div>
4215:                         </div>
4216:                         ${renderStatusBadge(item?.status || "unknown")}
4217:                       </div>
4218: 
4219:                       ${
4220:                         item?.summary
4221:                           ? `<div class="list-item-sub">${escapeHtml(item.summary)}</div>`
4222:                           : ""
4223:                       }
4224: 
4225:                       <div class="badge-row">
4226:                         <span class="badge">Dept: ${escapeHtml(departmentLabel)}</span>
4227:                         ${
4228:                           runId
4229:                             ? `<span class="badge">Run: ${escapeHtml(runId)}</span>`
4230:                             : ""
4231:                         }
4232:                         <span class="badge">Requested: ${escapeHtml(formatDateTime(item?.requested_at || item?.created_at))}</span>
4233:                         ${
4234:                           item?.resolved_at
4235:                             ? `<span class="badge">Resolved: ${escapeHtml(formatDateTime(item.resolved_at))}</span>`
4236:                             : ""
4237:                         }
4238:                       </div>
4239: 
4240:                       ${
4241:                         item?.resolved_by
4242:                           ? `<div class="list-item-sub">Resolved by: ${escapeHtml(item.resolved_by)}</div>`
4243:                           : ""
4244:                       }
4245: 
4246:                       ${
4247:                         item?.resolution_note
4248:                           ? `<div class="list-item-sub">${escapeHtml(item.resolution_note)}</div>`
4249:                           : ""
4250:                       }
4251: 
4252:                       <div class="marketing-form-actions" style="margin-top:10px;">
4253:                         ${
4254:                           runId
4255:                             ? `
4256:                               <button
4257:                                 class="secondary-btn live-run-select-btn"
4258:                                 data-run-id="${escapeHtml(runId)}"
4259:                               >
4260:                                 Inspect run
4261:                               </button>
4262: 
4263:                               <button
4264:                                 class="secondary-btn live-run-open-replay-btn"
4265:                                 data-run-id="${escapeHtml(runId)}"
4266:                               >
4267:                                 Open replay
4268:                               </button>
4269:                             `
4270:                             : ""
4271:                         }
4272:                       </div>
4273:                     </div>
4274:                   `;
4275:                 }).join("")}
4276:               </div>
4277:             `
4278:             : `<div class="empty-state">No approval history for ${escapeHtml(
4279:                 departmentLabel,
4280:               )}.</div>`
4281:         }
4282:       </div>
4283:     </div>
4284:   `;
4285: }
```

### Hit line 7721: `const key = normaliseAionDepartmentPilotKey(departmentKey);`

```js
7720: function setAionBoardroomSelectedDepartmentPulseKey(departmentKey = "") {
7721:   const key = normaliseAionDepartmentPilotKey(departmentKey);
7722:   if (!getAionCoreDepartmentKeys().includes(key)) return false;
7723:   state.boardroomSelectedDepartmentPulseKey = key;
7724:   if (typeof requestRender === "function") requestRender();
7725:   return true;
7726: }
```

### Hit line 7729: `const key = normaliseAionDepartmentPilotKey(departmentKey);`

```js
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
7742:   if (key === "sales") {
7743:     return [
7744:       { label: "Revenue", value: formatBoardroomEuro(sales.revenue ?? center.revenue ?? "—"), sub: "Sales value" },
7745:       { label: "Orders", value: sales.orders ?? "—", sub: "Current orders" },
7746:       { label: "Conversion", value: formatBoardroomPercent(sales.conversionRate ?? sales.conversion_rate ?? "—"), sub: "Lead conversion" },
7747:       { label: "Pipeline", value: center.pipeline ?? "—", sub: "Open work" },
7748:       { label: "Follow-up", value: pendingApprovals, sub: "Needs review" },
7749:       { label: "Runs", value: runtimeRuns.length, sub: "Activity" },
7750:     ];
7751:   }
7752: 
7753:   if (key === "marketing") {
7754:     return [
7755:       { label: "Leads", value: sales.leads ?? sales.orders ?? "—", sub: "Captured demand" },
7756:       { label: "Campaigns", value: runtimeRuns.length, sub: "Draft/preview runs" },
7757:       { label: "Conversion", value: formatBoardroomPercent(sales.conversionRate ?? sales.conversion_rate ?? "—"), sub: "Sales handoff" },
7758:       { label: "Budget", value: formatBoardroomEuro(finance.marketingBudget ?? finance.marketing_budget ?? "—"), sub: "Safe spend" },
7759:       { label: "Proof", value: "—", sub: "Evidence count" },
7760:       { label: "Approvals", value: pendingApprovals, sub: "Pending" },
7761:     ];
7762:   }
7763: 
7764:   if (key === "operations") {
7765:     return [
7766:       { label: "Ops", value: ops.backlog ?? center.pipeline ?? "—", sub: "Workload" },
7767:       { label: "Fulfilment", value: formatBoardroomPercent(ops.fulfilmentRate ?? ops.fulfilment_rate ?? "—"), sub: "Delivery rate" },
7768:       { label: "Capacity", value: ops.capacity ?? "—", sub: "Available" },
7769:       { label: "Bottlenecks", value: ops.bottlenecks ?? "—", sub: "Known issues" },
7770:       { label: "Automation", value: ops.automationCandidates ?? ops.automation_candidates ?? "—", sub: "Candidates" },
7771:       { label: "Runs", value: runtimeRuns.length, sub: "Activity" },
7772:     ];
7773:   }
7774: 
7775:   if (key === "support") {
7776:     return [
7777:       { label: "Issues", value: ops.supportIssues ?? ops.support_issues ?? "—", sub: "Open issues" },
7778:       { label: "Response", value: ops.responseRate ?? ops.response_rate ?? "—", sub: "Speed" },
7779:       { label: "Quality", value: ops.serviceQuality ?? ops.service_quality ?? "—", sub: "Signal" },
7780:       { label: "Templates", value: ops.supportTemplates ?? ops.support_templates ?? "—", sub: "Available" },
7781:       { label: "Receipts", value: pendingApprovals, sub: "Review items" },
7782:       { label: "Runs", value: runtimeRuns.length, sub: "Activity" },
7783:     ];
7784:   }
7785: 
7786: 
7787:   if (key === "finance") {
7788:     return [
7789:       { label: "Cash", value: formatBoardroomEuro(cash.onHand ?? cash.on_hand ?? center.cash ?? "—"), sub: `Runway ${cash.runwayDays ?? cash.runway_days ?? "—"}d` },
7790:       { label: "Revenue", value: formatBoardroomEuro(sales.revenue ?? center.revenue ?? "—"), sub: `Orders ${sales.orders ?? "—"} · Conv ${sales.conversionRate ?? sales.conversion_rate ?? "—"}%` },
7791:       { label: "Costs", value: formatBoardroomEuro(finance.costs ?? finance.monthly_costs ?? "—"), sub: "Known costs" },
7792:       { label: "Debtors", value: finance.debtorDays ?? finance.debtor_days ?? "—", sub: `Creditor ${finance.creditorDays ?? finance.creditor_days ?? "—"}` },
7793:       { label: "Margin", value: formatBoardroomPercent(finance.grossMarginPct ?? finance.gross_margin_pct ?? "—"), sub: "Gross margin" },
7794:       { label: "Runs", value: runtimeRuns.length, sub: `${pendingApprovals} approval${pendingApprovals === 1 ? "" : "s"}` },
7795:     ];
7796:   }
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
```

### Hit line 7809: `const key = normaliseAionDepartmentPilotKey(departmentKey);`

```js
7808: function getAionDepartmentPulseAccentColor(departmentKey = "") {
7809:   const key = normaliseAionDepartmentPilotKey(departmentKey);
7810:   if (key === "marketing") return "#2563eb";
7811:   if (key === "sales") return "#16a34a";
7812:   if (key === "finance") return "#0284c7";
7813:   if (key === "operations") return "#f59e0b";
7814:   if (key === "support") return "#7c3aed";
7815:   return "#2563eb";
7816: }
```

### Hit line 7880: `const key = normaliseAionDepartmentPilotKey(departmentKey);`

```js
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
7893:         <div style="font-size:12px; letter-spacing:0.16em; text-transform:uppercase; color:${accent}; font-weight:900;">
7894:           ${escapeHtml(label)} Highlights
7895:         </div>
7896:       </div>
7897: 
7898:       <div
7899:         data-aion-phase25j-selected-department-connector="${escapeHtml(key)}"
7900:         style="
7901:           height:8px;
7902:           border-left:3px solid ${accent};
7903:           border-top:3px solid ${accent};
7904:           border-radius:10px 0 0 0;
7905:           margin:0 0 8px 18px;
7906:           opacity:0.72;
7907:         "
7908:       ></div>
7909: 
7910:       <div style="display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px;">
7911:         ${items.map((item) => renderBoardroomUnifiedMetricCard({
7912:           label: item.label,
7913:           value: item.value,
7914:           sub: item.sub,
7915:           accent,
7916:           dataAttr: `data-aion-phase25j-selected-department-highlight-card="${escapeHtml(key)}"`,
7917:         })).join("")}
7918:       </div>
7919:     </section>
7920:   `;
7921: }
```

### Hit line 8318: `function getPrimaryDepartmentAgentCard(departmentKey) {`

```js
8318: function getPrimaryDepartmentAgentCard(departmentKey) {
8319:   return liveAgentsRuntime.getPrimaryDepartmentAgentCard(state, departmentKey);
8320: }
```

### Hit line 8322: `function setLiveAgentsWorkspace(departmentKey, options = {}) {`

```js
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
```

### Hit line 8905: `? normaliseAionDepartmentPilotKey(getSelectedLiveDepartmentKey())`

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
8914:     updateAionDepartmentIntelligence(pilotState.department_scope, {
8915:       status: "plan_ready",
8916:       plan: {
8917:         title: pilotState.plan?.title || "Department Pilot plan",
8918:         task_type: pilotState.plan?.task_type || "general_task",
8919:         goal: requestText,
8920:         approval_required: true,
8921:         live_external_actions_blocked: true,
8922:         source: "central_pilot_department_scope",
8923:       },
8924:       boardroom_summary: `${runtimeShared.getDepartmentLabel(pilotState.department_scope)} Pilot has prepared a scoped plan preview. No live external action has been taken.`,
8925:       last_updated: new Date().toISOString(),
8926:     });
8927:   }
8928:   pilotState.artifact_status = "draft_preview";
8929:   pilotState.artifact_hash = "sha256:frontend_draft_artifact_preview";
8930:   pilotState.receipt_hash = "sha256:frontend_draft_receipt_preview";
8931:   pilotState.replay_hash = "sha256:frontend_draft_replay_preview";
8932:   pilotState.proof_hash = "sha256:frontend_draft_proof_preview";
8933:   pilotState.contract_status = "draft_contract";
8934:   pilotState.safe_work_status = "waiting_approval";
8935:   pilotState.safe_work_approved = false;
8936:   pilotState.generated_output_text = "";
8937:   pilotState.step_outputs = [];
8938:   pilotState.current_step_index = 0;
8939:   pilotState.backend_artifact_status = "";
8940:   pilotState.backend_artifact_error = "";
8941:   pilotState.output_panel_open = false;
8942:   pilotState.output_panel_kind = "";
8943:   pilotState.output_panel_title = "";
8944:   pilotState.output_panel_body = "";
8945:   const universalPlan = pilotState.plan || buildAionPilotUniversalPlan(requestText);
8946: 
8947:   pilotState.stream_events = [
8948:     {
8949:       type: "mission_composer",
8950:       label: "Work package created",
8951:       detail: requestText,
8952:       status: "draft_only",
8953:     },
8954:     {
8955:       type: "artifact_preview",
8956:       label: getAionPilotOutputPreparedLabel(universalPlan),
8957:       detail: getAionPilotOutputPreparedDetail(universalPlan),
8958:       status: "draft_preview",
8959:     },
8960:     {
8961:       type: "safety_block",
8962:       label: "Live external actions blocked",
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
8988:   }
8989: 
8990:   if (typeof requestRender === "function") {
8991:     requestRender();
8992:   }
8993: 
8994:   return pilotState;
8995: }
```

### Hit line 9547: `const key = normaliseAionDepartmentPilotKey(departmentKey);`

```js
9527: function runAionCentralPilotApprovedTask(taskId = "") {
9528:   const queue = getAionCentralPilotQueue();
9529:   const id = String(taskId || "").trim() || String(getAionCentralPilotNextApprovedTask()?.id || "");
9530:   if (!id || !queue[id]) return null;
9531: 
9532:   const now = new Date().toISOString();
9533:   const task = queue[id];
9534: 
9535:   const completedTask = {
9536:     ...task,
9537:     status: "completed_preview",
9538:     completed_at: now,
9539:     updated_at: now,
9540:     result_summary: `${task.title || "Approved Boardroom action"} completed as a guarded internal preview. No live external action was taken.`,
9541:   };
9542: 
9543:   queue[id] = completedTask;
9544:   saveAionCentralPilotQueue(queue);
9545: 
9546:   safeArray(task.departments).forEach((departmentKey) => {
9547:     const key = normaliseAionDepartmentPilotKey(departmentKey);
9548:     if (!key) return;
9549: 
9550:     const ledger = getAionDepartmentIntelligence();
9551:     const entry = ledger[key] || normaliseAionDepartmentIntelligenceEntry(key, {});
9552:     const existingResults =
9553:       entry.results && typeof entry.results === "object" && !Array.isArray(entry.results)
9554:         ? entry.results
9555:         : {};
9556: 
9557:     const resultRecord = {
9558:       id: `${key}_${id}_central_result`,
9559:       department_key: key,
9560:       central_task_id: id,
9561:       title: completedTask.title,
9562:       status: "results_available",
9563:       result_type: "central_boardroom_action_preview",
9564:       summary: completedTask.result_summary,
9565:       created_at: now,
9566:       no_live_external_action: true,
9567:     };
9568: 
9569:     const evidenceRecord = {
9570:       id: `${key}_${id}_central_evidence`,
9571:       department_key: key,
9572:       central_task_id: id,
9573:       evidence_type: "central_boardroom_action_result",
9574:       title: completedTask.title,
9575:       summary: completedTask.result_summary,
9576:       created_at: now,
9577:       provenance: "central_aion_assessment_hook",
9578:     };
9579: 
9580:     const receiptRecord = {
9581:       id: `${key}_${id}_central_receipt`,
9582:       department_key: key,
9583:       central_task_id: id,
9584:       receipt_type: "central_safe_internal_preview",
9585:       status: "draft_receipt",
9586:       created_at: now,
9587:       no_live_external_action: true,
9588:     };
9589: 
9590:     updateAionDepartmentIntelligence(key, {
9591:       status: "central_action_preview_complete",
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
```

### Hit line 9674: `const department = normaliseAionDepartmentPilotKey(`

```js
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
9741:     status: graph ? "goal_loop_safe_queue_ready" : "no_active_goal_loop",
9742:     business_label: businessLabel,
9743:     business_container: businessContainer,
9744:     goal_loop_id: goalLoopId,
9745:     board_goal: boardGoalTitle,
9746:     task_count: tasks.length,
9747:     departments: Object.keys(grouped),
9748:     tasks,
9749:     grouped_by_department: grouped,
9750:     preview_only: true,
9751:     approval_required: true,
9752:     execution_blocked: true,
9753:     no_live_external_action: true,
9754:     external_side_effects: false,
9755:     message_sent: false,
9756:     booking_created: false,
9757:     payment_created: false,
9758:     persistence_required: false,
9759:     route_mutation_required: false,
9760:     uses_existing_central_pilot: true,
9761:     creates_second_pilot: false,
9762:     creates_second_canvas: false,
9763:   };
9764: }
```

### Hit line 9797: `const key = normaliseAionDepartmentPilotKey(departmentKey);`

```js
9796: function buildAionGoalLoopDepartmentTaskQueueWritebackPatch(departmentKey = "", options = {}) {
9797:   const key = normaliseAionDepartmentPilotKey(departmentKey);
9798:   const queue =
9799:     options.queue && typeof options.queue === "object"
9800:       ? options.queue
9801:       : typeof getAionGoalLoopCentralPilotTaskQueue === "function"
9802:         ? getAionGoalLoopCentralPilotTaskQueue()
9803:         : { grouped_by_department: {}, tasks: [] };
9804: 
9805:   const grouped = queue.grouped_by_department && typeof queue.grouped_by_department === "object"
9806:     ? queue.grouped_by_department
9807:     : {};
9808: 
9809:   const tasks = Array.isArray(grouped[key])
9810:     ? grouped[key]
9811:     : Array.isArray(queue.tasks)
9812:       ? queue.tasks.filter((task) => normaliseAionDepartmentPilotKey(task?.department || "") === key)
9813:       : [];
9814: 
9815:   const existingEntry =
9816:     typeof getAionDepartmentLedgerEntry === "function"
9817:       ? getAionDepartmentLedgerEntry(key)
9818:       : typeof getAionDepartmentPilotLedgerEntry === "function"
9819:         ? getAionDepartmentPilotLedgerEntry(key)
9820:         : {};
9821: 
9822:   const existingTasks = Array.isArray(existingEntry?.tasks) ? existingEntry.tasks : [];
9823:   const now = new Date().toISOString();
9824: 
9825:   const previewTasks = tasks.map((task, index) => ({
9826:     id: String(task.id || `${key}_goal_loop_preview_task_${index + 1}`),
9827:     title: String(task.title || `Goal Loop task ${index + 1}`),
9828:     detail: String(task.detail || "Goal Loop safe internal task preview."),
9829:     department_key: key,
9830:     source: "goal_loop_central_pilot_safe_queue",
9831:     source_goal_loop_id: String(task.goal_loop_id || queue.goal_loop_id || "not_staged"),
9832:     source_node_id: String(task.source_node_id || ""),
9833:     source_node_type: String(task.source_node_type || "agent_task"),
9834:     department_child_canvas_id: String(task.department_child_canvas_id || ""),
9835:     status: "staged",
9836:     task_status_values: AION_GOAL_LOOP_DEPARTMENT_TASK_STATUS_VALUES,
9837:     approval_state: "awaiting_approval",
9838:     approval_required: true,
9839:     safety: "internal_preview_only",
9840:     preview_only: true,
9841:     execution_blocked: true,
9842:     no_live_external_action: true,
9843:     external_side_effects: false,
9844:     message_sent: false,
9845:     booking_created: false,
9846:     payment_created: false,
9847:     persistence_required: false,
9848:     ledger_mutation_required: false,
9849:     route_mutation_required: false,
9850:     provenance: {
9851:       source: "goal_loop_graph_agent_task",
9852:       generated_by: "central_pilot_goal_loop_queue_preview",
9853:       department_key: key,
9854:       preview_generated_at: now,
9855:       business_container: String(task.business_container || queue.business_container || "business_not_registered"),
9856:       business_label: String(task.business_label || queue.business_label || "Business not registered"),
9857:     },
9858:   }));
9859: 
9860:   const mergedPreviewTasks = [
9861:     ...existingTasks,
9862:     ...previewTasks,
9863:   ];
9864: 
9865:   return {
9866:     schema_version: "aion.goal_loop.department_task_queue_writeback_preview.v1",
9867:     department_key: key,
9868:     business_label: String(queue.business_label || "Business not registered"),
9869:     business_container: String(queue.business_container || "business_not_registered"),
9870:     goal_loop_id: String(queue.goal_loop_id || "not_staged"),
9871:     board_goal: String(queue.board_goal || "No Boardroom goal staged"),
9872:     status: previewTasks.length ? "writeback_preview_ready" : "no_goal_loop_tasks_for_department",
9873:     task_status_values: AION_GOAL_LOOP_DEPARTMENT_TASK_STATUS_VALUES,
9874:     preview_task_count: previewTasks.length,
9875:     existing_task_count: existingTasks.length,
9876:     resulting_task_count_preview: mergedPreviewTasks.length,
9877:     preview_tasks: previewTasks,
9878:     ledger_patch_preview: {
9879:       status: previewTasks.length ? "goal_loop_task_queue_preview_ready" : existingEntry?.status || "no_goal_loop_task_queue",
9880:       department_key: key,
9881:       tasks: mergedPreviewTasks,
9882:       goal_loop_task_queue_preview: {
9883:         goal_loop_id: String(queue.goal_loop_id || "not_staged"),
9884:         board_goal: String(queue.board_goal || "No Boardroom goal staged"),
9885:         task_count: previewTasks.length,
9886:         generated_at: now,
9887:         source: "central_pilot_goal_loop_safe_task_queue",
9888:       },
9889:       boardroom_summary: previewTasks.length
9890:         ? `${runtimeShared.getDepartmentLabel(key)} has ${previewTasks.length} Goal Loop task preview(s) staged for review. No ledger mutation or live external action has occurred.`
9891:         : `${runtimeShared.getDepartmentLabel(key)} has no Goal Loop task previews staged.`,
9892:       last_updated_preview: now,
9893:     },
9894:     goal_loop_graph_patch_preview: {
9895:       goal_loop_id: String(queue.goal_loop_id || "not_staged"),
9896:       department_key: key,
9897:       node_status_updates: previewTasks.map((task) => ({
9898:         node_id: task.source_node_id,
9899:         status: "staged",
9900:         approval_state: "awaiting_approval",
9901:         writeback_preview: true,
9902:         updated_at: now,
9903:       })),
9904:       progress_rollup_patch: {
9905:         department: key,
9906:         status: previewTasks.length ? "tasks_staged_preview" : "no_tasks_staged",
9907:         task_count: previewTasks.length,
9908:         completed_task_count: 0,
9909:         evidence_count: 0,
9910:         confidence: previewTasks.length ? "partial" : "unknown",
9911:         last_updated_preview: now,
9912:       },
9913:     },
9914:     preview_only: true,
9915:     execution_blocked: true,
9916:     persistence_required: false,
9917:     ledger_mutation_required: false,
9918:     route_mutation_required: false,
9919:     external_side_effects: false,
9920:     message_sent: false,
9921:     booking_created: false,
9922:     payment_created: false,
9923:     uses_existing_department_ledger: true,
9924:     uses_existing_central_pilot: true,
9925:     creates_second_pilot: false,
9926:     creates_second_canvas: false,
9927:   };
9928: }
```

### Hit line 10006: `const department = normaliseAionDepartmentPilotKey(overrides.department || "marketing");`

```js
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
```

### Hit line 10042: `const key = normaliseAionDepartmentPilotKey(departmentKey);`

```js
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
```

### Hit line 10128: `? graph.department_child_canvases.map((canvas) => normaliseAionDepartmentPilotKey(canvas.department || "")).filter(Boolean)`

```js
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
```

### Hit line 10198: `const department = normaliseAionDepartmentPilotKey(options.department || selectedMetric.department || "marketing");`

```js
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
```

### Hit line 10290: `const key = normaliseAionDepartmentPilotKey(result.department || "");`

```js
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
10266:     : [buildAionGoalLoopManualResultSnapshot({ ...options, attachment })];
10267: 
10268:   const graphResultPatchPreview = {
10269:     schema_version: "aion.goal_loop_manual_result_graph_patch_preview.v1",
10270:     goal_loop_id: String(attachment.goal_loop_id || "not_staged"),
10271:     result_count: resultSnapshots.length,
10272:     result_node_updates: resultSnapshots.map((result) => ({
10273:       result_id: result.result_id,
10274:       metric_id: result.metric_id,
10275:       department: result.department,
10276:       source_node_id: result.source_node_id,
10277:       status: "manual_result_preview",
10278:       actual: result.actual,
10279:       confidence: result.confidence,
10280:       evidence_ids: result.evidence_ids,
10281:       writeback_preview: true,
10282:       updated_at_preview: result.captured_at_preview,
10283:     })),
10284:     preview_only: true,
10285:     persistence_required: false,
10286:     execution_blocked: true,
10287:   };
10288: 
10289:   const departmentLedgerResultPatchPreview = resultSnapshots.reduce((acc, result) => {
10290:     const key = normaliseAionDepartmentPilotKey(result.department || "");
10291:     acc[key] = acc[key] || {
10292:       department_key: key,
10293:       status: "manual_result_preview_ready",
10294:       results: [],
10295:       boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} has manual Goal Loop result preview(s). No ledger mutation has occurred.`,
10296:       ledger_mutation_required: false,
10297:       persistence_required: false,
10298:       preview_only: true,
10299:     };
10300: 
10301:     acc[key].results.push({
10302:       result_id: result.result_id,
10303:       metric_id: result.metric_id,
10304:       metric_name: result.metric_name,
10305:       actual: result.actual,
10306:       target: result.target,
10307:       unit: result.unit,
10308:       confidence: result.confidence,
10309:       note: result.note,
10310:       evidence_note: result.evidence_note,
10311:       source: "manual",
10312:       status: "manual_result_preview",
10313:       captured_at_preview: result.captured_at_preview,
10314:     });
10315: 
10316:     return acc;
10317:   }, {});
10318: 
10319:   const boardroomResultPreview = {
10320:     schema_version: "aion.goal_loop_boardroom_manual_result_preview.v1",
10321:     goal_loop_id: String(attachment.goal_loop_id || "not_staged"),
10322:     status: resultSnapshots.length ? "manual_results_ready_for_boardroom_preview" : "no_manual_results",
10323:     result_count: resultSnapshots.length,
10324:     departments: Object.keys(departmentLedgerResultPatchPreview),
10325:     summary: `${resultSnapshots.length} manual result preview(s) prepared for Boardroom review. No execution or persistence has occurred.`,
10326:     requires_review: true,
10327:     preview_only: true,
10328:   };
10329: 
10330:   const preview = {
10331:     schema_version: "aion.goal_loop_manual_result_capture_preview.v1",
10332:     status: "manual_result_capture_preview_ready",
10333:     goal_loop_id: String(attachment.goal_loop_id || "not_staged"),
10334:     result_snapshots: resultSnapshots,
10335:     graph_result_patch_preview: graphResultPatchPreview,
10336:     department_ledger_result_patch_preview: departmentLedgerResultPatchPreview,
10337:     boardroom_result_preview: boardroomResultPreview,
10338:     preview_only: true,
10339:     connector_call_required: false,
10340:     ledger_mutation_required: false,
10341:     persistence_required: false,
10342:     execution_blocked: true,
10343:     external_side_effects: false,
10344:     message_sent: false,
10345:     booking_created: false,
10346:     payment_created: false,
10347:     creates_second_canvas: false,
10348:     creates_second_pilot: false,
10349:   };
10350: 
10351:   if (typeof window !== "undefined") {
10352:     window.__aionGoalLoopManualResultCapturePreview = preview;
10353:   }
10354: 
10355:   return preview;
10356: }
```

### Hit line 10391: `const department = normaliseAionDepartmentPilotKey(safeResult.department || safeMetric.department || "marketing");`

```js
10376: function evaluateAionGoalLoopMetricResult(result = {}, metric = {}) {
10377:   const safeResult = result && typeof result === "object" && !Array.isArray(result) ? result : {};
10378:   const safeMetric = metric && typeof metric === "object" && !Array.isArray(metric) ? metric : {};
10379: 
10380:   const targetRaw = safeResult.target ?? safeMetric.target;
10381:   const actualRaw = safeResult.actual ?? safeMetric.actual;
10382:   const target = Number(targetRaw);
10383:   const actual = Number(actualRaw);
10384:   const hasTarget = targetRaw !== null && targetRaw !== "" && Number.isFinite(target);
10385:   const hasActual = actualRaw !== null && actualRaw !== "" && Number.isFinite(actual);
10386: 
10387:   const confidence = AION_GOAL_LOOP_METRIC_CONFIDENCE_LEVELS.includes(String(safeResult.confidence || safeMetric.confidence || "unknown"))
10388:     ? String(safeResult.confidence || safeMetric.confidence || "unknown")
10389:     : "unknown";
10390: 
10391:   const department = normaliseAionDepartmentPilotKey(safeResult.department || safeMetric.department || "marketing");
10392:   const metricName = String(safeResult.metric_name || safeMetric.name || "goal_loop_metric");
10393:   const unit = String(safeResult.unit || safeMetric.unit || "");
10394: 
10395:   if (!hasTarget || !hasActual) {
10396:     return {
10397:       status: "unknown",
10398:       reason: `Metric ${metricName} does not have both a target and an actual value yet.`,
10399:       recommendation: "Request more data before deciding whether the loop is working.",
10400:       next_action: "request_more_data",
10401:       confidence,
10402:       department,
10403:       metric_id: String(safeResult.metric_id || safeMetric.metric_id || ""),
10404:       goal_id: String(safeResult.goal_id || safeMetric.goal_id || "goal_not_staged"),
10405:       evidence_ids: Array.isArray(safeResult.evidence_ids) ? safeResult.evidence_ids.map(String) : [],
10406:       target: targetRaw ?? null,
10407:       actual: actualRaw ?? null,
10408:       unit,
10409:       preview_only: true,
10410:     };
10411:   }
10412: 
10413:   const lowerIsBetter = /cost|spend|complaint|cancel|churn|delay|time|defect|refund|risk/i.test(metricName);
10414:   const isComplete = lowerIsBetter ? actual <= target : actual >= target;
10415:   const delta = actual - target;
10416:   const deltaAbs = Math.abs(delta);
10417:   const deltaPct = target === 0 ? null : delta / target;
10418: 
10419:   if (isComplete) {
10420:     return {
10421:       status: "on_track",
10422:       reason: lowerIsBetter
10423:         ? `${metricName} is at or below target (${actual}${unit ? ` ${unit}` : ""} vs ${target}${unit ? ` ${unit}` : ""}).`
10424:         : `${metricName} is at or above target (${actual}${unit ? ` ${unit}` : ""} vs ${target}${unit ? ` ${unit}` : ""}).`,
10425:       recommendation: "Continue the current loop and keep measuring before scaling decisions.",
10426:       next_action: confidence === "verified" ? "mark_complete" : "continue_loop",
10427:       confidence,
10428:       department,
10429:       metric_id: String(safeResult.metric_id || safeMetric.metric_id || ""),
10430:       goal_id: String(safeResult.goal_id || safeMetric.goal_id || "goal_not_staged"),
10431:       evidence_ids: Array.isArray(safeResult.evidence_ids) ? safeResult.evidence_ids.map(String) : [],
10432:       target,
10433:       actual,
10434:       unit,
10435:       delta,
10436:       delta_abs: deltaAbs,
10437:       delta_pct: deltaPct,
10438:       preview_only: true,
10439:     };
10440:   }
10441: 
10442:   return {
10443:     status: "off_track",
10444:     reason: lowerIsBetter
10445:       ? `${metricName} is above target (${actual}${unit ? ` ${unit}` : ""} vs ${target}${unit ? ` ${unit}` : ""}).`
10446:       : `${metricName} is below target (${actual}${unit ? ` ${unit}` : ""} vs ${target}${unit ? ` ${unit}` : ""}).`,
10447:     recommendation: "Propose an improvement loop or A/B test before increasing commitment.",
10448:     next_action: "propose_ab_test",
10449:     confidence,
10450:     department,
10451:     metric_id: String(safeResult.metric_id || safeMetric.metric_id || ""),
10452:     goal_id: String(safeResult.goal_id || safeMetric.goal_id || "goal_not_staged"),
10453:     evidence_ids: Array.isArray(safeResult.evidence_ids) ? safeResult.evidence_ids.map(String) : [],
10454:     target,
10455:     actual,
10456:     unit,
10457:     delta,
10458:     delta_abs: deltaAbs,
10459:     delta_pct: deltaPct,
10460:     preview_only: true,
10461:   };
10462: }
```

### Hit line 10605: `const department = normaliseAionDepartmentPilotKey(options.department || sourceEvaluation.department || "marketing");`

```js
10591: function buildAionGoalLoopAbTestNode(options = {}) {
10592:   const evaluationPreview =
10593:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10594:       ? options.evaluation_preview
10595:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10596:         ? buildAionGoalLoopEvaluationPreview()
10597:         : { evaluations: [], goal_loop_id: "not_staged" };
10598: 
10599:   const evaluations = Array.isArray(evaluationPreview.evaluations) ? evaluationPreview.evaluations : [];
10600:   const sourceEvaluation =
10601:     options.evaluation && typeof options.evaluation === "object"
10602:       ? options.evaluation
10603:       : evaluations.find((item) => item.next_action === "propose_ab_test") || evaluations[0] || {};
10604: 
10605:   const department = normaliseAionDepartmentPilotKey(options.department || sourceEvaluation.department || "marketing");
10606:   const now = new Date().toISOString();
10607: 
10608:   return {
10609:     schema_version: "aion.goal_loop_ab_test_node.v1",
10610:     node_id: String(options.node_id || `${sourceEvaluation.evaluation_id || "evaluation"}_ab_test_preview`),
10611:     node_type: "ab_test",
10612:     goal_loop_id: String(options.goal_loop_id || evaluationPreview.goal_loop_id || sourceEvaluation.goal_loop_id || "not_staged"),
10613:     goal_id: String(options.goal_id || sourceEvaluation.goal_id || "goal_not_staged"),
10614:     department,
10615:     source_evaluation_id: String(sourceEvaluation.evaluation_id || ""),
10616:     source_metric_id: String(sourceEvaluation.metric_id || ""),
10617:     title: String(options.title || `${runtimeShared.getDepartmentLabel(department)} A/B test preview`),
10618:     hypothesis: String(
10619:       options.hypothesis ||
10620:       sourceEvaluation.recommendation ||
10621:       "Testing a controlled variant may improve the Goal Loop metric before scaling."
10622:     ),
10623:     variant_a: {
10624:       id: "variant_a",
10625:       label: String(options.variant_a_label || "Current approach"),
10626:       description: String(options.variant_a_description || "Baseline/control version of the current loop."),
10627:     },
10628:     variant_b: {
10629:       id: "variant_b",
10630:       label: String(options.variant_b_label || "Improvement variant"),
10631:       description: String(options.variant_b_description || "Proposed changed version to test against the baseline."),
10632:     },
10633:     success_metric: {
10634:       metric_id: String(options.metric_id || sourceEvaluation.metric_id || ""),
10635:       name: String(options.success_metric || sourceEvaluation.metric_id || "goal_loop_success_metric"),
10636:       target: sourceEvaluation.target ?? null,
10637:       unit: String(sourceEvaluation.unit || ""),
10638:       confidence: String(sourceEvaluation.confidence || "partial"),
10639:     },
10640:     test_duration: String(options.test_duration || "7 days preview"),
10641:     lifecycle_status: "proposed",
10642:     approval_state: "awaiting_board_approval",
10643:     result_capture_placeholder: {
10644:       status: "not_captured",
10645:       variant_a_actual: null,
10646:       variant_b_actual: null,
10647:       confidence: "unknown",
10648:       evidence_ids: [],
10649:       preview_only: true,
10650:     },
10651:     winner_decision_placeholder: {
10652:       status: "not_selected",
10653:       winner: "unknown",
10654:       reason: "Winner can only be selected after approved measurement.",
10655:       preview_only: true,
10656:     },
10657:     next_variant_proposal_placeholder: {
10658:       status: "not_proposed",
10659:       proposal: "",
10660:       preview_only: true,
10661:     },
10662:     boardroom_ab_summary: {
10663:       status: "ab_test_proposal_ready",
10664:       required_board_decision: "Approve, adjust, reject or request more data before running any test.",
10665:       summary: `${runtimeShared.getDepartmentLabel(department)} has an A/B test proposal linked to the Goal Loop evaluation.`,
10666:       preview_only: true,
10667:     },
10668:     created_at_preview: now,
10669:     preview_only: true,
10670:     approval_required: true,
10671:     campaign_launch_required: false,
10672:     connector_call_required: false,
10673:     execution_blocked: true,
10674:     persistence_required: false,
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
```

### Hit line 10780: `const department = normaliseAionDepartmentPilotKey(`

```js
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
10823:     node_id: String(options.node_id || `${evaluationId}_ab_test_generated_node_preview`),
10824:     node_type: "ab_test",
10825:     goal_loop_id: goalLoopId,
10826:     goal_id: goalId,
10827:     department,
10828:     source_evaluation_id: evaluationId,
10829:     source_metric_id: metricId,
10830:     source_status: String(safeEvaluation.status || "unknown"),
10831:     source_next_action: String(safeEvaluation.next_action || "propose_ab_test"),
10832:     title: String(options.title || `${runtimeShared.getDepartmentLabel(department)} generated A/B test`),
10833:     hypothesis: String(
10834:       options.hypothesis ||
10835:       `If ${runtimeShared.getDepartmentLabel(department)} applies the recommended improvement, the Goal Loop metric should move closer to target.`
10836:     ),
10837:     variant_a: variantA,
10838:     variant_b: variantB,
10839:     success_metric: {
10840:       metric_id: metricId,
10841:       name: String(options.success_metric || metricId || "goal_loop_success_metric"),
10842:       target: safeEvaluation.target ?? null,
10843:       actual_baseline: safeEvaluation.actual ?? null,
10844:       unit: String(safeEvaluation.unit || ""),
10845:       confidence: String(safeEvaluation.confidence || "partial"),
10846:     },
10847:     test_duration: String(options.test_duration || "7 days preview"),
10848:     approval_requirement: {
10849:       required: true,
10850:       required_by: "boardroom",
10851:       reason: "Generated A/B test proposals must be reviewed before execution.",
10852:       approval_state: "awaiting_board_approval",
10853:     },
10854:     boardroom_review_item: {
10855:       schema_version: "aion.goal_loop_boardroom_review_item.v1",
10856:       review_id: String(options.review_id || `${evaluationId}_ab_test_boardroom_review`),
10857:       review_type: "generated_ab_test_proposal",
10858:       status: "needs_board_decision",
10859:       title: `Review generated A/B test for ${runtimeShared.getDepartmentLabel(department)}`,
10860:       summary: recommendation,
10861:       required_decision: "Approve, adjust, reject or request more data.",
10862:       source_evaluation_id: evaluationId,
10863:       goal_loop_id: goalLoopId,
10864:       department,
10865:       preview_only: true,
10866:     },
10867:     graph_patch_preview: {
10868:       goal_loop_id: goalLoopId,
10869:       add_node: {
10870:         node_id: String(options.node_id || `${evaluationId}_ab_test_generated_node_preview`),
10871:         node_type: "ab_test",
10872:         department,
10873:         source_evaluation_id: evaluationId,
10874:         source_metric_id: metricId,
10875:         approval_state: "awaiting_board_approval",
10876:         preview_only: true,
10877:       },
10878:       add_edges: [
10879:         {
10880:           from: evaluationId,
10881:           to: String(options.node_id || `${evaluationId}_ab_test_generated_node_preview`),
10882:           relation: "proposes_ab_test",
10883:           preview_only: true,
10884:         },
10885:       ],
10886:       preview_only: true,
10887:       graph_mutation_required: false,
10888:     },
10889:     created_at_preview: now,
10890:     preview_only: true,
10891:     approval_required: true,
10892:     campaign_launch_required: false,
10893:     connector_call_required: false,
10894:     execution_blocked: true,
10895:     persistence_required: false,
10896:     external_side_effects: false,
10897:     message_sent: false,
10898:     booking_created: false,
10899:     payment_created: false,
10900:     creates_second_canvas: false,
10901:     creates_second_pilot: false,
10902:     provenance: {
10903:       source: "goal_loop_evaluation_preview",
10904:       generated_by: "aion_goal_loop_phase_f2",
10905:       generated_at: now,
10906:       source_evaluation_id: evaluationId,
10907:       department,
10908:     },
10909:   };
10910: }
```

### Hit line 11009: `const department = normaliseAionDepartmentPilotKey(`

```js
10976: function buildAionGoalLoopFeedbackToBoardNode(input = {}, options = {}) {
10977:   const safeInput = input && typeof input === "object" && !Array.isArray(input) ? input : {};
10978:   const now = new Date().toISOString();
10979: 
10980:   const evaluationPreview =
10981:     options.evaluation_preview && typeof options.evaluation_preview === "object"
10982:       ? options.evaluation_preview
10983:       : typeof buildAionGoalLoopEvaluationPreview === "function"
10984:         ? buildAionGoalLoopEvaluationPreview()
10985:         : { evaluations: [], goal_loop_id: "not_staged" };
10986: 
10987:   const generatedAbPreview =
10988:     options.generated_ab_preview && typeof options.generated_ab_preview === "object"
10989:       ? options.generated_ab_preview
10990:       : typeof previewAionGoalLoopGeneratedAbTestsFromEvaluation === "function"
10991:         ? previewAionGoalLoopGeneratedAbTestsFromEvaluation({ evaluation_preview: evaluationPreview })
10992:         : { generated_ab_test_proposals: [] };
10993: 
10994:   const evaluations = Array.isArray(evaluationPreview.evaluations)
10995:     ? evaluationPreview.evaluations
10996:     : [];
10997: 
10998:   const generatedProposals = Array.isArray(generatedAbPreview.generated_ab_test_proposals)
10999:     ? generatedAbPreview.generated_ab_test_proposals
11000:     : [];
11001: 
11002:   const sourceEvaluation =
11003:     safeInput.evaluation && typeof safeInput.evaluation === "object"
11004:       ? safeInput.evaluation
11005:       : evaluations.find((item) => ["off_track", "blocked", "unknown"].includes(item.status)) ||
11006:         evaluations[0] ||
11007:         {};
11008: 
11009:   const department = normaliseAionDepartmentPilotKey(
11010:     safeInput.department ||
11011:     sourceEvaluation.department ||
11012:     "marketing"
11013:   );
11014: 
11015:   const departmentEvaluations = evaluations.filter((item) =>
11016:     normaliseAionDepartmentPilotKey(item.department || "") === department
11017:   );
11018: 
11019:   const departmentProposals = generatedProposals.filter((item) =>
11020:     normaliseAionDepartmentPilotKey(item.department || "") === department
11021:   );
11022: 
11023:   const goalLoopId = String(
11024:     safeInput.goal_loop_id ||
11025:     evaluationPreview.goal_loop_id ||
11026:     sourceEvaluation.goal_loop_id ||
11027:     "not_staged"
11028:   );
11029: 
11030:   const goalId = String(
11031:     safeInput.goal_id ||
11032:     sourceEvaluation.goal_id ||
11033:     departmentEvaluations[0]?.goal_id ||
11034:     "goal_not_staged"
11035:   );
11036: 
11037:   const feedbackId = String(
11038:     safeInput.feedback_id ||
11039:     `${goalLoopId}_${department}_feedback_to_board_preview`
11040:   );
11041: 
11042:   const metrics = departmentEvaluations.map((evaluation) => ({
11043:     metric_id: String(evaluation.metric_id || ""),
11044:     status: String(evaluation.status || "unknown"),
11045:     target: evaluation.target ?? null,
11046:     actual: evaluation.actual ?? null,
11047:     unit: String(evaluation.unit || ""),
11048:     confidence: String(evaluation.confidence || "unknown"),
11049:     next_action: String(evaluation.next_action || "request_more_data"),
11050:     preview_only: true,
11051:   }));
11052: 
11053:   const risks = departmentEvaluations
11054:     .filter((evaluation) => ["off_track", "blocked", "unknown"].includes(evaluation.status))
11055:     .map((evaluation) => ({
11056:       risk_id: `${evaluation.evaluation_id || evaluation.metric_id || "metric"}_risk_preview`,
11057:       severity:
11058:         evaluation.status === "blocked"
11059:           ? "high"
11060:           : evaluation.status === "off_track"
11061:             ? "medium"
11062:             : "low",
11063:       summary: String(evaluation.reason || "Metric needs review."),
11064:       recommendation: String(evaluation.recommendation || "Request Boardroom review."),
11065:       preview_only: true,
11066:     }));
11067: 
11068:   const evidenceIds = Array.from(new Set(
11069:     departmentEvaluations.flatMap((evaluation) =>
11070:       Array.isArray(evaluation.evidence_ids) ? evaluation.evidence_ids.map(String) : []
11071:     )
11072:   ));
11073: 
11074:   const needsAttention = departmentEvaluations.some((evaluation) =>
11075:     ["off_track", "blocked", "unknown"].includes(evaluation.status)
11076:   );
11077: 
11078:   const hasGeneratedAb = departmentProposals.length > 0;
11079: 
11080:   const status = String(
11081:     safeInput.status ||
11082:     (needsAttention ? "needs_attention" : "on_track")
11083:   );
11084: 
11085:   const recommendation = String(
11086:     safeInput.recommendation ||
11087:     departmentProposals[0]?.boardroom_review_item?.summary ||
11088:     sourceEvaluation.recommendation ||
11089:     (needsAttention
11090:       ? "Review department loop before scaling."
11091:       : "Continue the current department loop and keep measuring.")
11092:   );
11093: 
11094:   const requiredDecision = String(
11095:     safeInput.required_board_decision ||
11096:     (hasGeneratedAb
11097:       ? "Approve, adjust, reject or request more data for the generated A/B test."
11098:       : needsAttention
11099:         ? "Decide whether to continue, adjust, pause or request more data."
11100:         : "Confirm whether the department loop should continue or be marked complete.")
11101:   );
11102: 
11103:   return {
11104:     schema_version: "aion.goal_loop_feedback_to_board.v1",
11105:     feedback_id: feedbackId,
11106:     node_id: String(safeInput.node_id || `${feedbackId}_node`),
11107:     node_type: "feedback_to_board",
11108:     goal_loop_id: goalLoopId,
11109:     goal_id: goalId,
11110:     department,
11111:     department_status: status,
11112:     summary: String(
11113:       safeInput.summary ||
11114:       `${runtimeShared.getDepartmentLabel(department)} feedback is ready for Boardroom review.`
11115:     ),
11116:     metrics,
11117:     risks,
11118:     evidence_ids: evidenceIds,
11119:     recommendation,
11120:     required_board_decision: requiredDecision,
11121:     source_evaluation_ids: departmentEvaluations.map((evaluation) => String(evaluation.evaluation_id || "")),
11122:     source_ab_test_proposal_ids: departmentProposals.map((proposal) => String(proposal.proposal_id || "")),
11123:     boardroom_review_item: {
11124:       schema_version: "aion.goal_loop_boardroom_review_item.v1",
11125:       review_id: String(safeInput.review_id || `${feedbackId}_boardroom_review`),
11126:       review_type: "department_feedback_to_board",
11127:       status: "needs_board_decision",
11128:       title: `Review ${runtimeShared.getDepartmentLabel(department)} feedback`,
11129:       summary: String(
11130:         safeInput.summary ||
11131:         `${runtimeShared.getDepartmentLabel(department)} has submitted Goal Loop feedback.`
11132:       ),
11133:       required_decision: requiredDecision,
11134:       goal_loop_id: goalLoopId,
11135:       goal_id: goalId,
11136:       department,
11137:       evidence_ids: evidenceIds,
11138:       preview_only: true,
11139:     },
11140:     graph_patch_preview: {
11141:       goal_loop_id: goalLoopId,
11142:       add_or_update_node: {
11143:         node_id: String(safeInput.node_id || `${feedbackId}_node`),
11144:         node_type: "feedback_to_board",
11145:         department,
11146:         status,
11147:         required_board_decision: requiredDecision,
11148:         preview_only: true,
11149:       },
11150:       add_edges: [
11151:         ...departmentEvaluations.map((evaluation) => ({
11152:           from: String(evaluation.evaluation_id || evaluation.metric_id || "evaluation_preview"),
11153:           to: String(safeInput.node_id || `${feedbackId}_node`),
11154:           relation: "reports_feedback_to_board",
11155:           preview_only: true,
11156:         })),
11157:         ...departmentProposals.map((proposal) => ({
11158:           from: String(proposal.node_id || proposal.proposal_id || "ab_test_proposal_preview"),
11159:           to: String(safeInput.node_id || `${feedbackId}_node`),
11160:           relation: "included_in_board_feedback",
11161:           preview_only: true,
11162:         })),
11163:       ],
11164:       preview_only: true,
11165:       graph_mutation_required: false,
11166:     },
11167:     created_at_preview: now,
11168:     updated_at_preview: now,
11169:     preview_only: true,
11170:     graph_mutation_required: false,
11171:     persistence_required: false,
11172:     execution_blocked: true,
11173:     external_side_effects: false,
11174:     message_sent: false,
11175:     booking_created: false,
11176:     payment_created: false,
11177:     creates_second_canvas: false,
11178:     creates_second_pilot: false,
11179:     provenance: {
11180:       source: "goal_loop_department_evaluation_preview",
11181:       generated_by: "aion_goal_loop_phase_g1",
11182:       generated_at: now,
11183:       department,
11184:       source_evaluation_count: departmentEvaluations.length,
11185:       source_ab_test_proposal_count: departmentProposals.length,
11186:     },
11187:   };
11188: }
```

### Hit line 11204: `.map((evaluation) => normaliseAionDepartmentPilotKey(evaluation.department || "marketing"))`

```js
11190: function previewAionGoalLoopFeedbackToBoard(options = {}) {
11191:   const evaluationPreview =
11192:     options.evaluation_preview && typeof options.evaluation_preview === "object"
11193:       ? options.evaluation_preview
11194:       : typeof buildAionGoalLoopEvaluationPreview === "function"
11195:         ? buildAionGoalLoopEvaluationPreview()
11196:         : { evaluations: [], goal_loop_id: "not_staged" };
11197: 
11198:   const evaluations = Array.isArray(evaluationPreview.evaluations)
11199:     ? evaluationPreview.evaluations
11200:     : [];
11201: 
11202:   const departments = Array.from(new Set(
11203:     evaluations
11204:       .map((evaluation) => normaliseAionDepartmentPilotKey(evaluation.department || "marketing"))
11205:       .filter(Boolean)
11206:   ));
11207: 
11208:   const safeDepartments = departments.length
11209:     ? departments
11210:     : ["marketing", "sales", "finance", "operations", "support"];
11211: 
11212:   const feedbackNodes = safeDepartments.map((department) =>
11213:     buildAionGoalLoopFeedbackToBoardNode({ department }, {
11214:       evaluation_preview: evaluationPreview,
11215:     })
11216:   );
11217: 
11218:   const preview = {
11219:     schema_version: "aion.goal_loop_feedback_to_board_preview.v1",
11220:     status: feedbackNodes.length ? "feedback_to_board_preview_ready" : "no_feedback_available",
11221:     goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
11222:     department_count: safeDepartments.length,
11223:     feedback_count: feedbackNodes.length,
11224:     feedback_nodes: feedbackNodes,
11225:     boardroom_review_items: feedbackNodes.map((node) => node.boardroom_review_item),
11226:     graph_patch_preview: {
11227:       goal_loop_id: String(evaluationPreview.goal_loop_id || "not_staged"),
11228:       node_updates: feedbackNodes.map((node) => node.graph_patch_preview.add_or_update_node),
11229:       edge_additions: feedbackNodes.flatMap((node) => node.graph_patch_preview.add_edges),
11230:       preview_only: true,
11231:       graph_mutation_required: false,
11232:     },
11233:     preview_only: true,
11234:     graph_mutation_required: false,
11235:     persistence_required: false,
11236:     execution_blocked: true,
11237:     external_side_effects: false,
11238:     message_sent: false,
11239:     booking_created: false,
11240:     payment_created: false,
11241:     creates_second_canvas: false,
11242:     creates_second_pilot: false,
11243:   };
11244: 
11245:   if (typeof window !== "undefined") {
11246:     window.__aionGoalLoopFeedbackToBoardPreview = preview;
11247:   }
11248: 
11249:   return preview;
11250: }
```

### Hit line 11280: `const department = normaliseAionDepartmentPilotKey(`

```js
11273: function buildAionGoalLoopBoardroomFeedbackDecision(feedbackNode = {}, options = {}) {
11274:   const safeFeedback =
11275:     feedbackNode && typeof feedbackNode === "object" && !Array.isArray(feedbackNode)
11276:       ? feedbackNode
11277:       : {};
11278: 
11279:   const now = new Date().toISOString();
11280:   const department = normaliseAionDepartmentPilotKey(
11281:     options.department ||
11282:     safeFeedback.department ||
11283:     "marketing"
11284:   );
11285: 
11286:   const decision = normaliseAionGoalLoopBoardroomFeedbackDecision(
11287:     options.decision ||
11288:     safeFeedback.decision ||
11289:     "request_more_data"
11290:   );
11291: 
11292:   const goalLoopId = String(options.goal_loop_id || safeFeedback.goal_loop_id || "not_staged");
11293:   const goalId = String(options.goal_id || safeFeedback.goal_id || "goal_not_staged");
11294:   const feedbackId = String(options.feedback_id || safeFeedback.feedback_id || `${department}_feedback_preview`);
11295:   const decisionId = String(options.decision_id || `${feedbackId}_${decision}_board_decision_preview`);
11296: 
11297:   const decisionLabels = {
11298:     accept: "Boardroom accepts the department feedback and continues the loop.",
11299:     reject: "Boardroom rejects the proposed department feedback path.",
11300:     adjust: "Boardroom adjusts the department loop before continuation.",
11301:     request_more_data: "Boardroom requests more data before deciding.",
11302:   };
11303: 
11304:   const continuationPath = {
11305:     accept: "continue_loop",
11306:     reject: "pause_or_rework_loop",
11307:     adjust: "create_board_adjustment",
11308:     request_more_data: "request_more_data",
11309:   }[decision];
11310: 
11311:   return {
11312:     schema_version: "aion.goal_loop_boardroom_feedback_decision.v1",
11313:     decision_id: decisionId,
11314:     node_id: String(options.node_id || `${decisionId}_node`),
11315:     node_type: "board_adjustment",
11316:     goal_loop_id: goalLoopId,
11317:     goal_id: goalId,
11318:     feedback_id: feedbackId,
11319:     department,
11320:     decision,
11321:     decision_label: decisionLabels[decision],
11322:     decision_note: String(
11323:       options.decision_note ||
11324:       safeFeedback.required_board_decision ||
11325:       decisionLabels[decision]
11326:     ),
11327:     continuation_path: continuationPath,
11328:     adjustment_summary: String(
11329:       options.adjustment_summary ||
11330:       (decision === "adjust"
11331:         ? "Adjust the department loop before continuing."
11332:         : "")
11333:     ),
11334:     requested_data: decision === "request_more_data"
11335:       ? [
11336:           "latest_metric_value",
11337:           "confidence_label",
11338:           "supporting_evidence",
11339:         ]
11340:       : [],
11341:     boardroom_action_preview: {
11342:       action_type: "boardroom_feedback_decision",
11343:       allowed_actions: AION_GOAL_LOOP_BOARDROOM_FEEDBACK_DECISIONS,
11344:       selected_action: decision,
11345:       status: "decision_preview_ready",
11346:       approval_required: decision === "accept" || decision === "adjust",
11347:       execution_allowed: false,
11348:       preview_only: true,
11349:     },
11350:     graph_patch_preview: {
11351:       goal_loop_id: goalLoopId,
11352:       update_feedback_node: {
11353:         node_id: String(safeFeedback.node_id || feedbackId),
11354:         feedback_id: feedbackId,
11355:         boardroom_decision: decision,
11356:         boardroom_decision_id: decisionId,
11357:         status: decision === "reject" ? "rejected" : "board_reviewed",
11358:         preview_only: true,
11359:       },
11360:       add_or_update_node: {
11361:         node_id: String(options.node_id || `${decisionId}_node`),
11362:         node_type: "board_adjustment",
11363:         department,
11364:         decision,
11365:         continuation_path: continuationPath,
11366:         preview_only: true,
11367:       },
11368:       add_edges: [
11369:         {
11370:           from: String(safeFeedback.node_id || feedbackId),
11371:           to: String(options.node_id || `${decisionId}_node`),
11372:           relation: "board_decides_feedback",
11373:           preview_only: true,
11374:         },
11375:       ],
11376:       preview_only: true,
11377:       graph_mutation_required: false,
11378:     },
11379:     audit_preview: {
11380:       schema_version: "aion.goal_loop_boardroom_decision_audit_preview.v1",
11381:       actor: "boardroom",
11382:       source: "feedback_to_board",
11383:       decision_id: decisionId,
11384:       feedback_id: feedbackId,
11385:       department,
11386:       decision,
11387:       created_at_preview: now,
11388:       provenance_required: true,
11389:       receipt_required_on_persistence: true,
11390:       preview_only: true,
11391:     },
11392:     created_at_preview: now,
11393:     updated_at_preview: now,
11394:     preview_only: true,
11395:     graph_mutation_required: false,
11396:     persistence_required: false,
11397:     execution_blocked: true,
11398:     external_side_effects: false,
11399:     message_sent: false,
11400:     booking_created: false,
11401:     payment_created: false,
11402:     creates_second_canvas: false,
11403:     creates_second_pilot: false,
11404:     provenance: {
11405:       source: "goal_loop_feedback_to_board_preview",
11406:       generated_by: "aion_goal_loop_phase_g2",
11407:       generated_at: now,
11408:       feedback_id: feedbackId,
11409:       department,
11410:       decision,
11411:     },
11412:   };
11413: }
```

### Hit line 11522: `const key = normaliseAionDepartmentPilotKey(department);`

```js
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
```

### Hit line 11587: `pattern.departments.includes(normaliseAionDepartmentPilotKey(decision.department || ""))`

```js
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
11631:           severity,
11632:           triggered,
11633:           preview_only: true,
11634:         },
11635:         add_edges: pattern.departments.map((department) => ({
11636:           from: `${goalLoopId}_${department}_feedback_to_board_preview_node`,
11637:           to: `${goalLoopId}_${pattern.pattern_id}_cross_analysis_node_preview`,
11638:           relation: "contributes_to_cross_function_analysis",
11639:           preview_only: true,
11640:         })),
11641:         preview_only: true,
11642:         graph_mutation_required: false,
11643:       },
11644:       created_at_preview: now,
11645:       preview_only: true,
11646:       graph_mutation_required: false,
11647:       persistence_required: false,
11648:       execution_blocked: true,
11649:       external_side_effects: false,
11650:     };
11651:   });
11652: 
11653:   return {
11654:     schema_version: "aion.goal_loop_cross_function_analysis.v1",
11655:     goal_loop_id: goalLoopId,
11656:     status: "cross_function_analysis_preview_ready",
11657:     department_signals: departmentSignals,
11658:     finding_count: findings.length,
11659:     triggered_count: findings.filter((finding) => finding.triggered).length,
11660:     findings,
11661:     boardroom_review_items: findings.map((finding) => finding.boardroom_review_item),
11662:     graph_patch_preview: {
11663:       goal_loop_id: goalLoopId,
11664:       node_updates: findings.map((finding) => finding.graph_patch_preview.add_or_update_node),
11665:       edge_additions: findings.flatMap((finding) => finding.graph_patch_preview.add_edges),
11666:       preview_only: true,
11667:       graph_mutation_required: false,
11668:     },
11669:     created_at_preview: now,
11670:     preview_only: true,
11671:     graph_mutation_required: false,
11672:     persistence_required: false,
11673:     execution_blocked: true,
11674:     external_side_effects: false,
11675:     message_sent: false,
11676:     booking_created: false,
11677:     payment_created: false,
11678:     creates_second_canvas: false,
11679:     creates_second_pilot: false,
11680:     provenance: {
11681:       source: "goal_loop_feedback_and_boardroom_decision_preview",
11682:       generated_by: "aion_goal_loop_phase_h1",
11683:       generated_at: now,
11684:     },
11685:   };
11686: }
```

### Hit line 11730: `? safeFinding.departments.map((department) => normaliseAionDepartmentPilotKey(department)).filter(Boolean)`

```js
11719: function buildAionGoalLoopCrossFunctionConflictNode(finding = {}, options = {}) {
11720:   const safeFinding =
11721:     finding && typeof finding === "object" && !Array.isArray(finding)
11722:       ? finding
11723:       : {};
11724: 
11725:   const now = new Date().toISOString();
11726:   const goalLoopId = String(options.goal_loop_id || safeFinding.goal_loop_id || "not_staged");
11727:   const analysisId = String(options.analysis_id || safeFinding.analysis_id || "cross_analysis_preview");
11728:   const patternId = String(options.pattern_id || safeFinding.pattern_id || "cross_function_conflict");
11729:   const departments = Array.isArray(safeFinding.departments)
11730:     ? safeFinding.departments.map((department) => normaliseAionDepartmentPilotKey(department)).filter(Boolean)
11731:     : ["marketing", "sales"];
11732: 
11733:   const conflictId = String(options.conflict_id || `${analysisId}_conflict_node_preview`);
11734:   const status = normaliseAionGoalLoopCrossFunctionConflictStatus(
11735:     options.status ||
11736:     (safeFinding.triggered ? "open" : "resolved")
11737:   );
11738: 
11739:   const severity = String(options.severity || safeFinding.severity || "medium");
11740:   const findingText = String(safeFinding.finding || "Cross-function finding requires Boardroom review.");
11741:   const recommendation = String(safeFinding.recommendation || "Review affected department loops before continuing.");
11742:   const requiredAction = String(safeFinding.required_action || "Decide whether to accept, reject, resolve or request adjustment.");
11743: 
11744:   return {
11745:     schema_version: "aion.goal_loop_cross_function_conflict_node.v1",
11746:     conflict_id: conflictId,
11747:     node_id: String(options.node_id || conflictId),
11748:     node_type: "cross_function_conflict",
11749:     goal_loop_id: goalLoopId,
11750:     source_analysis_id: analysisId,
11751:     pattern_id: patternId,
11752:     departments,
11753:     status,
11754:     severity,
11755:     finding: findingText,
11756:     recommendation,
11757:     required_action: requiredAction,
11758:     affected_department_links: departments.map((department) => ({
11759:       department,
11760:       node_id: `${goalLoopId}_${department}_feedback_to_board_preview_node`,
11761:       relation: "affected_department",
11762:       preview_only: true,
11763:     })),
11764:     boardroom_review_link: {
11765:       review_id: String(
11766:         safeFinding.boardroom_review_item?.review_id ||
11767:         `${conflictId}_boardroom_review`
11768:       ),
11769:       review_type: "cross_function_conflict",
11770:       status: status === "open" ? "needs_board_decision" : "monitor",
11771:       required_decision: "Accept, reject, resolve or request adjustment.",
11772:       preview_only: true,
11773:     },
11774:     graph_patch_preview: {
11775:       goal_loop_id: goalLoopId,
11776:       add_or_update_node: {
11777:         node_id: String(options.node_id || conflictId),
11778:         node_type: "cross_function_conflict",
11779:         source_analysis_id: analysisId,
11780:         pattern_id: patternId,
11781:         departments,
11782:         status,
11783:         severity,
11784:         preview_only: true,
11785:       },
11786:       add_edges: [
11787:         {
11788:           from: analysisId,
11789:           to: String(options.node_id || conflictId),
11790:           relation: "materialises_as_conflict_node",
11791:           preview_only: true,
11792:         },
11793:         ...departments.map((department) => ({
11794:           from: `${goalLoopId}_${department}_feedback_to_board_preview_node`,
11795:           to: String(options.node_id || conflictId),
11796:           relation: "affected_by_cross_function_conflict",
11797:           preview_only: true,
11798:         })),
11799:         {
11800:           from: String(options.node_id || conflictId),
11801:           to: String(
11802:             safeFinding.boardroom_review_item?.review_id ||
11803:             `${conflictId}_boardroom_review`
11804:           ),
11805:           relation: "requires_boardroom_review",
11806:           preview_only: true,
11807:         },
11808:       ],
11809:       preview_only: true,
11810:       graph_mutation_required: false,
11811:     },
11812:     created_at_preview: now,
11813:     updated_at_preview: now,
11814:     preview_only: true,
11815:     graph_mutation_required: false,
11816:     persistence_required: false,
11817:     execution_blocked: true,
11818:     external_side_effects: false,
11819:     message_sent: false,
11820:     booking_created: false,
11821:     payment_created: false,
11822:     creates_second_canvas: false,
11823:     creates_second_pilot: false,
11824:     provenance: {
11825:       source: "goal_loop_cross_function_analysis_preview",
11826:       generated_by: "aion_goal_loop_phase_h2",
11827:       generated_at: now,
11828:       source_analysis_id: analysisId,
11829:       pattern_id: patternId,
11830:       departments,
11831:     },
11832:   };
11833: }
```

### Hit line 12143: `const department = normaliseAionDepartmentPilotKey(options.department || safeInput.department || "marketing");`

```js
12135: function buildAionGoalLoopApprovalGateRequest(taskOrControl = {}, options = {}) {
12136:   const safeInput =
12137:     taskOrControl && typeof taskOrControl === "object" && !Array.isArray(taskOrControl)
12138:       ? taskOrControl
12139:       : {};
12140: 
12141:   const now = new Date().toISOString();
12142:   const goalLoopId = String(options.goal_loop_id || safeInput.goal_loop_id || "not_staged");
12143:   const department = normaliseAionDepartmentPilotKey(options.department || safeInput.department || "marketing");
12144:   const sourceId = String(
12145:     options.source_id ||
12146:     safeInput.task_id ||
12147:     safeInput.control_id ||
12148:     safeInput.node_id ||
12149:     "goal_loop_action_preview"
12150:   );
12151: 
12152:   const actionType = normaliseAionGoalLoopApprovalActionType(
12153:     options.action_type ||
12154:     safeInput.action_type ||
12155:     (
12156:       sourceId.includes("archive")
12157:         ? "archive_loop"
12158:         : sourceId.includes("start_safe_execution")
12159:           ? "safe_internal_execution"
12160:           : "safe_internal_execution"
12161:     )
12162:   );
12163: 
12164:   const exactApprovalRequired = [
12165:     "external_message",
12166:     "booking_confirmation",
12167:     "payment_action",
12168:     "connector_write",
12169:     "archive_loop",
12170:   ].includes(actionType);
12171: 
12172:   const approvalRequired = exactApprovalRequired || Boolean(options.approval_required || safeInput.approval_required);
12173: 
12174:   const approvalState = approvalRequired ? "required" : "not_required";
12175:   const approvalId = String(options.approval_id || `${goalLoopId}_${sourceId}_approval_request_preview`);
12176: 
12177:   return {
12178:     schema_version: "aion.goal_loop_approval_gate_request.v1",
12179:     approval_id: approvalId,
12180:     goal_loop_id: goalLoopId,
12181:     source_id: sourceId,
12182:     source_type: String(options.source_type || safeInput.node_type || safeInput.control_id ? "goal_loop_control_or_task" : "goal_loop_action"),
12183:     department,
12184:     action_type: actionType,
12185:     approval_state: approvalState,
12186:     approval_required: approvalRequired,
12187:     exact_approval_required: exactApprovalRequired,
12188:     execution_allowed: false,
12189:     execution_block_reason: approvalRequired
12190:       ? "Approval is required before this Goal Loop action can execute."
12191:       : "Execution remains blocked in I2 preview mode.",
12192:     approval_policy: {
12193:       no_external_live_action_without_explicit_approval: true,
12194:       no_payment_without_exact_approval: true,
12195:       no_booking_without_exact_approval: true,
12196:       no_customer_message_without_policy_approval: true,
12197:       provenance_required: true,
12198:       evidence_or_confidence_required: true,
12199:       boardroom_decision_auditable: true,
12200:     },
12201:     graph_node_approval_patch_preview: {
12202:       node_id: String(safeInput.node_id || sourceId),
12203:       approval_id: approvalId,
12204:       approval_state: approvalState,
12205:       approval_required: approvalRequired,
12206:       execution_allowed: false,
12207:       preview_only: true,
12208:       graph_mutation_required: false,
12209:     },
12210:     task_queue_approval_patch_preview: {
12211:       task_id: String(safeInput.task_id || sourceId),
12212:       approval_id: approvalId,
12213:       approval_state: approvalState,
12214:       approval_required: approvalRequired,
12215:       execution_allowed: false,
12216:       preview_only: true,
12217:       queue_mutation_required: false,
12218:     },
12219:     boardroom_approval_preview: {
12220:       schema_version: "aion.goal_loop_boardroom_approval_preview.v1",
12221:       review_id: `${approvalId}_boardroom_review`,
12222:       review_type: "approval_gate_request",
12223:       status: approvalRequired ? "needs_board_approval" : "monitor",
12224:       title: "Goal Loop approval request",
12225:       summary: `Approval gate preview for ${sourceId}.`,
12226:       required_decision: approvalRequired
12227:         ? "Approve, reject, adjust or request more data before execution."
12228:         : "No approval required, but execution is still blocked in preview mode.",
12229:       goal_loop_id: goalLoopId,
12230:       department,
12231:       action_type: actionType,
12232:       exact_approval_required: exactApprovalRequired,
12233:       preview_only: true,
12234:     },
12235:     audit_preview: {
12236:       schema_version: "aion.goal_loop_approval_gate_audit_preview.v1",
12237:       approval_id: approvalId,
12238:       source_id: sourceId,
12239:       actor: "boardroom_or_user_preview",
12240:       source: "goal_loop_approval_gate_preview",
12241:       created_at_preview: now,
12242:       provenance_required: true,
12243:       receipt_required_on_persistence: true,
12244:       preview_only: true,
12245:     },
12246:     created_at_preview: now,
12247:     preview_only: true,
12248:     graph_mutation_required: false,
12249:     queue_mutation_required: false,
12250:     persistence_required: false,
12251:     execution_blocked: true,
12252:     external_side_effects: false,
12253:     connector_call_required: false,
12254:     message_sent: false,
12255:     booking_created: false,
12256:     payment_created: false,
12257:     creates_second_canvas: false,
12258:     creates_second_pilot: false,
12259:     provenance: {
12260:       source: "goal_loop_canvas_execution_control_preview",
12261:       generated_by: "aion_goal_loop_phase_i2",
12262:       generated_at: now,
12263:       approval_id: approvalId,
12264:       source_id: sourceId,
12265:       department,
12266:       action_type: actionType,
12267:     },
12268:   };
12269: }
```

### Hit line 19267: `<div class="aion-pilot-department-lane" data-aion-pilot-department-lane="${escapeHtml(departmentId)}">`

```js
19252:   const renderDepartmentLane = (departmentId) => {
19253:     const departmentItems = toolItems.filter((item) => String(item.department_id || "").toLowerCase() === departmentId);
19254:     const queueDepartmentItems = queueItems.filter((item) => String(item.department_id || "").toLowerCase() === departmentId);
19255: 
19256:     if (!departmentItems.length && !queueDepartmentItems.length) {
19257:       return "";
19258:     }
19259: 
19260:     const title = departmentId === "pilot"
19261:       ? "Pilot"
19262:       : departmentId.charAt(0).toUpperCase() + departmentId.slice(1);
19263: 
19264:     const visibleItems = departmentItems.length ? departmentItems : queueDepartmentItems;
19265: 
19266:     return `
19267:       <div class="aion-pilot-department-lane" data-aion-pilot-department-lane="${escapeHtml(departmentId)}">
19268:         <div class="aion-pilot-output-card-header">
19269:           <strong>${escapeHtml(title)}</strong>
19270:           <span>${escapeHtml(String(visibleItems.length))} task(s)</span>
19271:         </div>
19272:         <div class="list-wrap">
19273:           ${visibleItems.slice(0, 8).map((item) => `
19274:             <div class="list-item">
19275:               <div class="list-item-title">${escapeHtml(item.title || item.department_capability || item.capability || "Department task")}</div>
19276:               <div class="list-item-sub">${escapeHtml(item.department_capability || item.capability || item.task_type || "")}</div>
19277:               <div class="badge-row">
19278:                 <span class="badge">${escapeHtml(item.status || "queued")}</span>
19279:                 <span class="badge">${escapeHtml(item.tool_mode || item.permission || "department_queue")}</span>
19280:                 ${item.live_external_side_effect === true ? `<span class="badge">approval required</span>` : ""}
19281:               </div>
19282:             </div>
19283:           `).join("")}
19284:         </div>
19285:       </div>
19286:     `;
19287:   };
```

### Hit line 21474: `if (document.getElementById("aion-pilot-cockpit-styles")) return;`

```js
21473: function installAionPilotCockpitStyles() {
21474:   if (document.getElementById("aion-pilot-cockpit-styles")) return;
21475:   const style = document.createElement("style");
21476:   style.id = "aion-pilot-cockpit-styles";
21477:   style.textContent = `
21478:     .aion-pilot-cockpit {
21479:       margin-top: 18px;
21480:       border: 1px solid rgba(0,0,0,.16);
21481:       background: rgba(255,255,255,.34);
21482:       padding: 18px;
21483:       display: grid;
21484:       gap: 16px;
21485:     }
21486:     .aion-pilot-header {
21487:       display: flex;
21488:       justify-content: space-between;
21489:       gap: 18px;
21490:       align-items: flex-start;
21491:     }
21492:     .aion-pilot-header h2 {
21493:       margin: 3px 0 6px;
21494:       font-size: 28px;
21495:     }
21496:     .aion-pilot-status {
21497:       border: 1px solid rgba(0,0,0,.25);
21498:       padding: 6px 10px;
21499:       font-size: 11px;
21500:       letter-spacing: .14em;
21501:       font-weight: 800;
21502:     }
21503:     .aion-pilot-safety-banner {
21504:       border: 1px solid rgba(0,0,0,.18);
21505:       background: rgba(96,119,103,.12);
21506:       padding: 12px 14px;
21507:       display: grid;
21508:       gap: 4px;
21509:     }
21510:     .aion-pilot-grid {
21511:       display: grid;
21512:       grid-template-columns: minmax(0,1fr) minmax(0,1fr);
21513:       gap: 14px;
21514:     }
21515:     .aion-pilot-grid-three {
21516:       grid-template-columns: minmax(0,1fr) minmax(0,1fr) minmax(0,1fr);
21517:     }
21518:     .aion-pilot-panel,
21519:     .aion-pilot-artifact-card,
21520:     .aion-pilot-blocked-card,
21521:     .aion-pilot-map-node {
21522:       border: 1px solid rgba(0,0,0,.14);
21523:       background: rgba(255,255,255,.42);
21524:       padding: 12px;
21525:       display: grid;
21526:       gap: 9px;
21527:       min-width: 0;
21528:     }
21529:     .aion-pilot-panel textarea,
21530:     .aion-pilot-feedback textarea {
21531:       width: 100%;
21532:       min-height: 86px;
21533:       border: 1px solid rgba(0,0,0,.18);
21534:       background: rgba(255,255,255,.55);
21535:       padding: 10px;
21536:       box-sizing: border-box;
21537:       font: inherit;
21538:     }
21539:     .aion-pilot-meta-row {
21540:       display: grid;
21541:       grid-template-columns: 120px minmax(0,1fr);
21542:       gap: 8px;
21543:       border-top: 1px solid rgba(0,0,0,.08);
21544:       padding-top: 7px;
21545:     }
21546:     .aion-pilot-meta-row span { color: #777; }
21547:     .aion-pilot-meta-row code {
21548:       white-space: normal;
21549:       overflow-wrap: anywhere;
21550:       font-size: 12px;
21551:       font-weight: 700;
21552:     }
21553:     .aion-pilot-actions,
21554:     .aion-pilot-feedback {
21555:       display: flex;
21556:       gap: 8px;
21557:       flex-wrap: wrap;
21558:       align-items: center;
21559:     }
21560:     .aion-pilot-cockpit button {
21561:       border: 1px solid rgba(0,0,0,.22);
21562:       background: rgba(255,255,255,.52);
21563:       padding: 9px 12px;
21564:       font-weight: 800;
21565:       letter-spacing: .08em;
21566:       cursor: pointer;
21567:     }
21568:     [data-aion-pilot-create-draft-mission] {
21569:       background: rgba(96,119,103,.92) !important;
21570:       color: white;
21571:     }
21572: 
21573:     .aion-pilot-simple-dashboard {
21574:       margin-top: 18px;
21575:       border: 1px solid rgba(0,0,0,.14);
21576:       background: rgba(255,255,255,.36);
21577:       padding: 18px;
21578:       display: grid;
21579:       gap: 16px;
21580:     }
21581:     .aion-pilot-simple-hero {
21582:       display: flex;
21583:       justify-content: space-between;
21584:       gap: 18px;
21585:       align-items: flex-start;
21586:     }
21587:     .aion-pilot-simple-hero h2 {
21588:       margin: 4px 0 6px;
21589:       font-size: 30px;
21590:       letter-spacing: -0.03em;
21591:     }
21592:     .aion-pilot-user-flow {
21593:       display: grid;
21594:       gap: 14px;
21595:     }
21596:     .aion-pilot-step-card {
21597:       display: grid;
21598:       grid-template-columns: 42px minmax(0,1fr);
21599:       gap: 14px;
21600:       padding: 16px;
21601:       border: 1px solid rgba(0,0,0,.13);
21602:       background: rgba(255,255,255,.52);
21603:       min-width: 0;
21604:     }
21605:     .aion-pilot-step-number {
21606:       width: 32px;
21607:       height: 32px;
21608:       border-radius: 999px;
21609:       display: flex;
21610:       align-items: center;
21611:       justify-content: center;
21612:       background: rgba(96,119,103,.92);
21613:       color: white;
21614:       font-weight: 900;
21615:     }
21616:     .aion-pilot-step-card h3 {
21617:       margin: 10px 0 6px;
21618:       font-size: 18px;
21619:     }
21620:     .aion-pilot-step-card h4 {
21621:       margin: 12px 0 6px;
21622:       font-size: 13px;
21623:       text-transform: uppercase;
21624:       letter-spacing: .09em;
21625:     }
21626:     .aion-pilot-two-list {
21627:       display: grid;
21628:       grid-template-columns: minmax(0,1fr) minmax(0,1fr);
21629:       gap: 14px;
21630:     }
21631:     .aion-pilot-result-card {
21632:       border: 1px solid rgba(0,0,0,.12);
21633:       background: rgba(255,255,255,.56);
21634:       padding: 12px;
21635:       display: grid;
21636:       gap: 8px;
21637:     }
21638:     .aion-pilot-advanced-details {
21639:       border: 1px solid rgba(0,0,0,.12);
21640:       background: rgba(255,255,255,.32);
21641:       padding: 12px;
21642:     }
21643:     .aion-pilot-advanced-details summary {
21644:       cursor: pointer;
21645:       font-weight: 900;
21646:     }
21647: 
21648: 
21649:     .aion-pilot-output-panel {
21650:       border: 1px solid rgba(0,0,0,.14);
21651:       background: rgba(255,255,255,.62);
21652:       padding: 14px;
21653:       display: grid;
21654:       gap: 10px;
21655:     }
21656:     .aion-pilot-output-panel-header {
21657:       display: flex;
21658:       justify-content: space-between;
21659:       gap: 12px;
21660:       align-items: center;
21661:     }
21662:     .aion-pilot-output-panel pre {
21663:       margin: 0;
21664:       white-space: pre-wrap;
21665:       overflow-wrap: anywhere;
21666:       background: rgba(0,0,0,.04);
21667:       border: 1px solid rgba(0,0,0,.10);
21668:       padding: 12px;
21669:       max-height: 420px;
21670:       overflow: auto;
21671:       font-size: 13px;
21672:       line-height: 1.45;
21673:     }
21674: 
21675: 
21676:     .aion-pilot-stream-shell {
21677:       min-height: 72vh;
21678:       display: grid;
21679:       grid-template-rows: auto minmax(420px, 1fr) auto;
21680:       border: 1px solid rgba(0,0,0,.14);
21681:       background: rgba(255,255,255,.28);
21682:       margin-top: 18px;
21683:     }
21684: 
21685:     .aion-pilot-stream-header {
21686:       padding: 18px 20px;
21687:       border-bottom: 1px solid rgba(0,0,0,.10);
21688:       display: flex;
21689:       align-items: flex-start;
21690:       justify-content: space-between;
21691:       gap: 16px;
21692:       background: rgba(255,255,255,.32);
21693:     }
21694: 
21695:     .aion-pilot-stream-header h2 {
21696:       margin: 3px 0 6px;
21697:       font-size: 34px;
21698:       letter-spacing: -0.04em;
21699:     }
21700: 
21701:     .aion-pilot-stream-header p {
21702:       margin: 0;
21703:       max-width: 760px;
21704:       color: rgba(17,17,17,.68);
21705:       line-height: 1.45;
21706:     }
21707: 
21708:     .aion-pilot-stream-window {
21709:       padding: 22px 20px 28px;
21710:       display: grid;
21711:       gap: 16px;
21712:       align-content: start;
21713:       overflow: auto;
21714:       background: linear-gradient(180deg, rgba(255,255,255,.22), rgba(255,255,255,.08));
21715:     }
21716: 
21717:     .aion-pilot-stream-message {
21718:       max-width: 880px;
21719:       line-height: 1.55;
21720:       color: rgba(17,17,17,.78);
21721:     }
21722: 
21723:     .aion-pilot-stream-message p {
21724:       margin: 0;
21725:       font-size: 16px;
21726:     }
21727: 
21728:     .aion-pilot-stream-message-user {
21729:       justify-self: end;
21730:       max-width: min(760px, 82%);
21731:       border: 1px solid rgba(0,0,0,.12);
21732:       background: rgba(255,255,255,.66);
21733:       border-radius: 18px 18px 4px 18px;
21734:       padding: 14px 16px;
21735:       color: #111111;
21736:     }
21737: 
21738:     .aion-pilot-stream-message-system {
21739:       justify-self: start;
21740:       padding: 2px 4px;
21741:     }
21742: 
21743:     .aion-pilot-stream-card {
21744:       width: min(980px, 100%);
21745:       border: 1px solid rgba(0,0,0,.12);
21746:       background: rgba(255,255,255,.72);
21747:       border-radius: 18px;
21748:       padding: 18px;
21749:       box-shadow: 0 16px 42px rgba(0,0,0,.045);
21750:       display: grid;
21751:       gap: 12px;
21752:     }
21753: 
21754:     .aion-pilot-safety-card {
21755:       background: rgba(96,119,103,.11);
21756:       border-color: rgba(96,119,103,.28);
21757:       box-shadow: none;
21758:     }
21759: 
21760:     .aion-pilot-safety-card span {
21761:       color: rgba(17,17,17,.72);
21762:     }
21763: 
21764:     .aion-pilot-card-kicker {
21765:       font-size: 11px;
21766:       text-transform: uppercase;
21767:       letter-spacing: .14em;
21768:       font-weight: 900;
21769:       color: rgba(17,17,17,.48);
21770:     }
21771: 
21772:     .aion-pilot-stream-card h3 {
21773:       margin: 0;
21774:       font-size: 22px;
21775:       letter-spacing: -0.02em;
21776:     }
21777: 
21778:     .aion-pilot-stream-card h4 {
21779:       margin: 4px 0 8px;
21780:       font-size: 12px;
21781:       text-transform: uppercase;
21782:       letter-spacing: .12em;
21783:       color: rgba(17,17,17,.58);
21784:     }
21785: 
21786:     .aion-pilot-stream-card p {
21787:       margin: 0;
21788:       line-height: 1.48;
21789:     }
21790: 
21791:     .aion-pilot-stream-card ul {
21792:       margin: 0;
21793:       padding-left: 20px;
21794:       display: grid;
21795:       gap: 6px;
21796:     }
21797: 
21798:     .aion-pilot-stream-columns {
21799:       display: grid;
21800:       grid-template-columns: minmax(0,1fr) minmax(0,1fr);
21801:       gap: 18px;
21802:     }
21803: 
21804:     .aion-pilot-composer-bar {
21805:       position: sticky;
21806:       bottom: 0;
21807:       padding: 14px 18px;
21808:       border-top: 1px solid rgba(0,0,0,.12);
21809:       background: rgba(250,247,241,.94);
21810:       backdrop-filter: blur(16px);
21811:       display: grid;
21812:       grid-template-columns: minmax(0,1fr) auto;
21813:       gap: 12px;
21814:       align-items: end;
21815:       z-index: 20;
21816:     }
21817: 
21818:     .aion-pilot-composer-bar textarea {
21819:       min-height: 58px;
21820:       max-height: 160px;
21821:       resize: vertical;
21822:       border: 1px solid rgba(0,0,0,.14);
21823:       background: rgba(255,255,255,.74);
21824:       border-radius: 18px;
21825:       padding: 14px 16px;
21826:       font: inherit;
21827:       line-height: 1.35;
21828:       box-sizing: border-box;
21829:       width: 100%;
21830:     }
21831: 
21832:     .aion-pilot-composer-bar button {
21833:       min-height: 52px;
21834:       border-radius: 16px;
21835:       padding: 0 20px;
21836:       background: rgba(96,119,103,.96) !important;
21837:       color: white !important;
21838:       border-color: rgba(96,119,103,.96) !important;
21839:       white-space: nowrap;
21840:     }
21841: 
21842:     .aion-pilot-output-panel {
21843:       width: min(980px, 100%);
21844:       border-radius: 18px;
21845:       box-shadow: 0 16px 42px rgba(0,0,0,.045);
21846:     }
21847: 
21848:     .aion-pilot-advanced-details {
21849:       width: min(980px, 100%);
21850:       border-radius: 18px;
21851:       background: rgba(255,255,255,.50);
21852:     }
21853: 
21854:     @media (max-width: 1100px) {
21855:       .aion-pilot-grid,
21856:       .aion-pilot-grid-three {
21857:         grid-template-columns: 1fr;
21858:       }
21859:     }
21860:   `;
21861:   document.head.appendChild(style);
21862: }
```

### Hit line 21560: `.aion-pilot-cockpit button {`

```js
21560:     .aion-pilot-cockpit button {
21561:       border: 1px solid rgba(0,0,0,.22);
21562:       background: rgba(255,255,255,.52);
21563:       padding: 9px 12px;
21564:       font-weight: 800;
21565:       letter-spacing: .08em;
21566:       cursor: pointer;
21567:     }
```

### Hit line 37220: `${renderAionDepartmentPilotPhase25CPanel(departmentKey)}`

```js
37180: function renderGenericDepartmentWorkspaceSurface(departmentKey, selectedAgentCard) {
37181:   const departmentLabel = runtimeShared.getDepartmentLabel(departmentKey);
37182:   const counts = getDepartmentRunCounts(departmentKey);
37183:   const runs = getDepartmentRuns(departmentKey)
37184:     .slice()
37185:     .sort((a, b) => {
37186:       const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
37187:       const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
37188:       return bTime - aTime;
37189:     });
37190: 
37191:   const pendingApprovals = getDepartmentPendingApprovals(departmentKey);
37192:   const recentAudit = getDepartmentRecentAudit(departmentKey);
37193:   const selectedRun = findSelectedLiveRun();
37194: 
37195:   return `
37196:     <div class="dashboard-shell">
37197:       <div class="card-grid">
37198:         ${renderDashboardMetricCard(
37199:           "Department",
37200:           departmentLabel,
37201:           selectedAgentCard?.label || "No specific agent selected",
37202:         )}
37203:         ${renderDashboardMetricCard(
37204:           "Queued / Running",
37205:           `${counts.queued} / ${counts.running}`,
37206:           "Current runtime queue",
37207:         )}
37208:         ${renderDashboardMetricCard(
37209:           "Approval / Failed",
37210:           `${counts.waitingApproval} / ${counts.failed}`,
37211:           "Exceptions needing attention",
37212:         )}
37213:         ${renderDashboardMetricCard(
37214:           "Completed",
37215:           counts.completed,
37216:           `Total runs ${counts.total}`,
37217:         )}
37218:       </div>
37219: 
37220:       ${renderAionDepartmentPilotPhase25CPanel(departmentKey)}
37221:       ${renderAionDepartmentPilotPhase25DPanel(departmentKey)}
37222:       ${renderAionDepartmentPilotPhase25EPanel(departmentKey)}
37223:       ${renderAionDepartmentPilotPhase25FPanel(departmentKey)}
37224:       ${renderAionDepartmentPilotGoalLoopContextPanel(departmentKey)}
37225: 
37226:       <div class="two-col">
37227:         <div class="panel large-panel">
37228:           <div class="panel-title">${escapeHtml(departmentLabel)} Run Queue</div>
37229:           ${
37230:             runs.length
37231:               ? `<div class="list-wrap">${runs
37232:                   .map((run) => renderLiveAgentRunRow(run))
37233:                   .join("")}</div>`
37234:               : `<div class="empty-state">No ${escapeHtml(
37235:                   departmentLabel.toLowerCase(),
37236:                 )} runs yet.</div>`
37237:           }
37238:         </div>
37239: 
37240:         <div class="panel large-panel">
37241:           <div class="panel-title">Pending Approvals</div>
37242:           ${
37243:             pendingApprovals.length
37244:               ? `<div class="list-wrap">${pendingApprovals
37245:                   .map((item) => `
37246:                     <div class="list-item">
37247:                       <div class="list-item-title">${escapeHtml(item?.title || "Approval")}</div>
37248:                       <div class="list-item-sub">${escapeHtml(item?.summary || "")}</div>
37249:                       <div class="badge-row">
37250:                         ${renderStatusBadge(item?.status)}
37251:                         <span class="badge">${escapeHtml(
37252:                           formatDateTime(item?.requested_at || item?.created_at),
37253:                         )}</span>
37254:                       </div>
37255:                     </div>
37256:                   `)
37257:                   .join("")}</div>`
37258:               : `<div class="empty-state">No pending approvals for ${escapeHtml(
37259:                   departmentLabel,
37260:                 )}.</div>`
37261:           }
37262:         </div>
37263:       </div>
37264: 
37265:       <div class="two-col">
37266:         <div class="panel large-panel">
37267:           <div class="panel-title">Selected Run Inspector</div>
37268:           ${
37269:             selectedRun &&
37270:             String(selectedRun?.department_key || "").toLowerCase() ===
37271:               String(departmentKey || "").toLowerCase()
37272:               ? `<pre class="json-block">${escapeHtml(shortJson(selectedRun))}</pre>`
37273:               : `<div class="empty-state">Select a ${escapeHtml(
37274:                   departmentLabel.toLowerCase(),
37275:                 )} run to inspect it here.</div>`
37276:           }
37277:         </div>
37278: 
37279:         <div class="panel large-panel">
37280:           <div class="panel-title">Recent Audit</div>
37281:           ${
37282:             recentAudit.length
37283:               ? `<div class="list-wrap">${recentAudit
37284:                   .map(
37285:                     (event) => `
37286:                       <div class="list-item">
37287:                         <div class="list-item-title">${escapeHtml(
37288:                           event.event_type || "event",
37289:                         )}</div>
37290:                         <div class="list-item-sub">${escapeHtml(event.message || "")}</div>
37291:                         <div class="badge-row">
37292:                           <span class="badge">${escapeHtml(event.level || "info")}</span>
37293:                           <span class="badge">${escapeHtml(
37294:                             formatDateTime(event.created_at),
37295:                           )}</span>
37296:                         </div>
37297:                       </div>
37298:                     `,
37299:                   )
37300:                   .join("")}</div>`
37301:               : `<div class="empty-state">No recent ${escapeHtml(
37302:                   departmentLabel.toLowerCase(),
37303:                 )} audit events.</div>`
37304:           }
37305:         </div>
37306:       </div>
37307:     </div>
37308:   `;
37309: }
```

### Hit line 37347: `function normaliseAionDepartmentPilotKey(departmentKey = "") {`

```js
37347: function normaliseAionDepartmentPilotKey(departmentKey = "") {
37348:   const key = String(departmentKey || "").trim().toLowerCase();
37349:   if (["marketing", "sales", "finance", "operations", "support"].includes(key)) return key;
37350:   return key || "marketing";
37351: }
```

### Hit line 37353: `function getAionDepartmentPilotProfile(departmentKey = "") {`

```js
37353: function getAionDepartmentPilotProfile(departmentKey = "") {
37354:   const key = normaliseAionDepartmentPilotKey(departmentKey);
37355:   return AION_DEPARTMENT_PILOT_PROFILES[key] || {
37356:     title: `${runtimeShared.getDepartmentLabel(key)} Pilot`,
37357:     purpose: "Scoped department discovery, planning and safe execution previews.",
37358:     missing: ["department context", "goals", "current process", "known results"],
37359:     nextAction: `Run ${runtimeShared.getDepartmentLabel(key)} discovery`,
37360:   };
37361: }
```

### Hit line 37363: `function getAionDepartmentPilotLedgerEntry(departmentKey = "") {`

```js
37363: function getAionDepartmentPilotLedgerEntry(departmentKey = "") {
37364:   const key = normaliseAionDepartmentPilotKey(departmentKey);
37365:   const ledger =
37366:     typeof getAionDepartmentIntelligence === "function"
37367:       ? getAionDepartmentIntelligence()
37368:       : {};
37369:   return ledger[key] && typeof ledger[key] === "object" ? ledger[key] : {};
37370: }
```

### Hit line 37372: `function getAionDepartmentPilotStatus(departmentKey = "") {`

```js
37372: function getAionDepartmentPilotStatus(departmentKey = "") {
37373:   const entry = getAionDepartmentPilotLedgerEntry(departmentKey);
37374:   return entry.status || "needs_discovery";
37375: }
```

### Hit line 37377: `function getAionDepartmentPilotBoardroomSummary(departmentKey = "") {`

```js
37377: function getAionDepartmentPilotBoardroomSummary(departmentKey = "") {
37378:   const entry = getAionDepartmentPilotLedgerEntry(departmentKey);
37379:   return entry.boardroom_summary || "No department intelligence has been captured yet.";
37380: }
```

### Hit line 37382: `function renderAionDepartmentPilotMissingList(departmentKey = "") {`

```js
37382: function renderAionDepartmentPilotMissingList(departmentKey = "") {
37383:   const profile = getAionDepartmentPilotProfile(departmentKey);
37384:   const entry = getAionDepartmentPilotLedgerEntry(departmentKey);
37385:   const discovery = entry.discovery && typeof entry.discovery === "object" ? entry.discovery : {};
37386:   const answered = Object.keys(discovery).filter((key) => String(discovery[key] || "").trim()).length;
37387: 
37388:   return `
37389:     <div class="list-wrap" data-aion-department-pilot-missing-list="${escapeHtml(departmentKey)}">
37390:       ${
37391:         profile.missing.map((item) => `
37392:           <div class="list-item">
37393:             <div class="list-item-title">${escapeHtml(item)}</div>
37394:             <div class="list-item-sub">
37395:               ${answered > 0 ? "Discovery has started. This item can be refined by the department Pilot." : "Not captured yet."}
37396:             </div>
37397:           </div>
37398:         `).join("")
37399:       }
37400:     </div>
37401:   `;
37402: }
```

### Hit line 37441: `function buildAionGoalLoopDepartmentPilotContextMap() {`

```js
37441: function buildAionGoalLoopDepartmentPilotContextMap() {
37442:   const graph = getAionActiveGoalLoopGraphForDepartmentContext();
37443:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
37444:   const childCanvases = Array.isArray(graph?.department_child_canvases)
37445:     ? graph.department_child_canvases
37446:     : Array.isArray(graph?.goal_loop_contract?.department_child_canvases)
37447:       ? graph.goal_loop_contract.department_child_canvases
37448:       : [];
37449:   const progressRollup = Array.isArray(graph?.department_progress_rollup)
37450:     ? graph.department_progress_rollup
37451:     : Array.isArray(graph?.goal_loop_contract?.department_progress_rollup)
37452:       ? graph.goal_loop_contract.department_progress_rollup
37453:       : [];
37454: 
37455:   const businessLabel =
37456:     typeof getAionWorkflowCanvasHeaderBusinessLabel === "function"
37457:       ? getAionWorkflowCanvasHeaderBusinessLabel()
37458:       : "Business not registered";
37459: 
37460:   const businessContainer =
37461:     typeof getAionWorkflowBusinessContainerId === "function"
37462:       ? getAionWorkflowBusinessContainerId()
37463:       : "business_not_registered";
37464: 
37465:   const contextMap = {};
37466: 
37467:   childCanvases.forEach((canvas) => {
37468:     const key = normaliseAionDepartmentPilotKey(canvas.department || "");
37469:     if (!key) return;
37470: 
37471:     contextMap[key] = {
37472:       department: key,
37473:       business_label: businessLabel,
37474:       business_container: businessContainer,
37475:       goal_loop_id: String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || canvas.parent_goal_loop_id || "not_staged"),
37476:       master_canvas_id: String(graph?.master_canvas_id || canvas.parent_canvas_id || ""),
37477:       child_canvas_id: String(canvas.canvas_id || ""),
37478:       parent_canvas_id: String(canvas.parent_canvas_id || graph?.master_canvas_id || ""),
37479:       board_goal: graph?.goal_loop_contract?.board_goal || {},
37480:       department_sub_goal: String(canvas.department_sub_goal || ""),
37481:       owner_agent: String(canvas.owner_agent || `${key}_pilot`),
37482:       open_department_canvas_action: canvas.open_department_canvas_action || null,
37483:       progress_rollup: canvas.progress_rollup || progressRollup.find((item) => item?.department === key) || {},
37484:       nodes: {
37485:         assignment: null,
37486:         sub_goal: null,
37487:         plan: null,
37488:         task: null,
37489:         measurement: null,
37490:         result: null,
37491:         evaluation: null,
37492:         ab_test: null,
37493:       },
37494:       preview_only: true,
37495:       execution_blocked: true,
37496:       persistence_required: false,
37497:       route_mutation_required: false,
37498:       uses_existing_department_pilot: true,
37499:       creates_second_pilot: false,
37500:       creates_second_canvas: false,
37501:     };
37502:   });
37503: 
37504:   nodes.forEach((node) => {
37505:     const department = normaliseAionDepartmentPilotKey(getAionGoalLoopNodeDepartment(node));
37506:     if (!department) return;
37507: 
37508:     if (!contextMap[department]) {
37509:       contextMap[department] = {
37510:         department,
37511:         business_label: businessLabel,
37512:         business_container: businessContainer,
37513:         goal_loop_id: String(graph?.goal_loop_id || graph?.goal_loop_contract?.goal_loop_id || "not_staged"),
37514:         master_canvas_id: String(graph?.master_canvas_id || ""),
37515:         child_canvas_id: "",
37516:         parent_canvas_id: String(graph?.master_canvas_id || ""),
37517:         board_goal: graph?.goal_loop_contract?.board_goal || {},
37518:         department_sub_goal: "",
37519:         owner_agent: `${department}_pilot`,
37520:         open_department_canvas_action: null,
37521:         progress_rollup: {},
37522:         nodes: {
37523:           assignment: null,
37524:           sub_goal: null,
37525:           plan: null,
37526:           task: null,
37527:           measurement: null,
37528:           result: null,
37529:           evaluation: null,
37530:           ab_test: null,
37531:         },
37532:         preview_only: true,
37533:         execution_blocked: true,
37534:         persistence_required: false,
37535:         route_mutation_required: false,
37536:         uses_existing_department_pilot: true,
37537:         creates_second_pilot: false,
37538:         creates_second_canvas: false,
37539:       };
37540:     }
37541: 
37542:     const type = getAionGoalLoopNodeType(node);
37543:     if (type === "department_assignment") contextMap[department].nodes.assignment = node;
37544:     if (type === "department_sub_goal") contextMap[department].nodes.sub_goal = node;
37545:     if (type === "department_plan") contextMap[department].nodes.plan = node;
37546:     if (type === "agent_task") contextMap[department].nodes.task = node;
37547:     if (type === "measurement_plan") contextMap[department].nodes.measurement = node;
37548:     if (type === "execution_result") contextMap[department].nodes.result = node;
37549:     if (type === "evaluation") contextMap[department].nodes.evaluation = node;
37550:     if (type === "ab_test") contextMap[department].nodes.ab_test = node;
37551: 
37552:     if (!contextMap[department].child_canvas_id && node?.child_canvas_id) {
37553:       contextMap[department].child_canvas_id = String(node.child_canvas_id);
37554:     }
37555: 
37556:     if (!contextMap[department].open_department_canvas_action && node?.open_department_canvas_action) {
37557:       contextMap[department].open_department_canvas_action = node.open_department_canvas_action;
37558:     }
37559: 
37560:     if (!contextMap[department].department_sub_goal && type === "department_sub_goal") {
37561:       contextMap[department].department_sub_goal = String(node?.title || node?.label || "");
37562:     }
37563:   });
37564: 
37565:   return contextMap;
37566: }
```

### Hit line 37569: `const key = normaliseAionDepartmentPilotKey(departmentKey);`

```js
37568: function getAionActiveGoalLoopDepartmentContext(departmentKey = "") {
37569:   const key = normaliseAionDepartmentPilotKey(departmentKey);
37570:   const contextMap = buildAionGoalLoopDepartmentPilotContextMap();
37571:   const context = contextMap[key] || null;
37572: 
37573:   if (!context) {
37574:     return {
37575:       department: key,
37576:       active: false,
37577:       status: "no_goal_loop_assignment",
37578:       message: "No active Goal Loop assignment is staged for this department.",
37579:       preview_only: true,
37580:       execution_blocked: true,
37581:       persistence_required: false,
37582:       route_mutation_required: false,
37583:       uses_existing_department_pilot: true,
37584:       creates_second_pilot: false,
37585:       creates_second_canvas: false,
37586:     };
37587:   }
37588: 
37589:   const nodeCount = Object.values(context.nodes || {}).filter(Boolean).length;
37590: 
37591:   return {
37592:     ...context,
37593:     active: true,
37594:     status: "goal_loop_assignment_ready",
37595:     node_count: nodeCount,
37596:     has_assignment: Boolean(context.nodes.assignment),
37597:     has_sub_goal: Boolean(context.nodes.sub_goal),
37598:     has_plan: Boolean(context.nodes.plan),
37599:     has_task: Boolean(context.nodes.task),
37600:     has_measurement: Boolean(context.nodes.measurement),
37601:     has_result: Boolean(context.nodes.result),
37602:     has_evaluation: Boolean(context.nodes.evaluation),
37603:     has_ab_test: Boolean(context.nodes.ab_test),
37604:   };
37605: }
```

### Hit line 37607: `function renderAionDepartmentPilotGoalLoopContextPanel(departmentKey = "") {`

```js
37607: function renderAionDepartmentPilotGoalLoopContextPanel(departmentKey = "") {
37608:   const key = normaliseAionDepartmentPilotKey(departmentKey);
37609:   const label = runtimeShared.getDepartmentLabel(key);
37610:   const context = getAionActiveGoalLoopDepartmentContext(key);
37611: 
37612:   const boardGoalTitle = String(
37613:     context.board_goal?.title ||
37614:     context.board_goal?.goal ||
37615:     "No Boardroom goal staged"
37616:   );
37617: 
37618:   const progress = context.progress_rollup || {};
37619: 
37620:   return `
37621:     <section
37622:       class="panel large-panel"
37623:       data-aion-goal-loop-department-pilot-context="true"
37624:       data-aion-goal-loop-department="${escapeHtml(key)}"
37625:       style="background:#ffffff; margin-top:9px;"
37626:     >
37627:       <div class="panel-title">${escapeHtml(label)} Goal Loop Context</div>
37628:       <div class="helper-text">
37629:         Existing ${escapeHtml(label)} Pilot context from the active Boardroom Goal Loop.
37630:         Preview-only. No persistence or execution is triggered here.
37631:       </div>
37632: 
37633:       <div class="card-grid" style="margin-top:10px;">
37634:         <div class="card">
37635:           <div class="card-label">Business</div>
37636:           <div class="card-value" data-aion-goal-loop-department-business-label="true">${escapeHtml(context.business_label || "Business not registered")}</div>
37637:           <div class="card-sub">${escapeHtml(context.business_container || "business_not_registered")}</div>
37638:         </div>
37639:         <div class="card">
37640:           <div class="card-label">Boardroom Goal</div>
37641:           <div class="card-value" data-aion-goal-loop-department-board-goal="true">${escapeHtml(boardGoalTitle)}</div>
37642:           <div class="card-sub">${escapeHtml(context.goal_loop_id || "not_staged")}</div>
37643:         </div>
37644:         <div class="card">
37645:           <div class="card-label">Department Sub-goal</div>
37646:           <div class="card-value" data-aion-goal-loop-department-sub-goal="true">${escapeHtml(context.department_sub_goal || context.message || "No department assignment staged")}</div>
37647:           <div class="card-sub">${escapeHtml(context.child_canvas_id || "No child canvas link")}</div>
37648:         </div>
37649:         <div class="card">
37650:           <div class="card-label">Graph Context</div>
37651:           <div class="card-value" data-aion-goal-loop-department-node-count="true">${escapeHtml(context.node_count || 0)} nodes</div>
37652:           <div class="card-sub">
37653:             Assignment ${context.has_assignment ? "yes" : "no"} · Plan ${context.has_plan ? "yes" : "no"} · Metrics ${context.has_measurement ? "yes" : "no"}
37654:           </div>
37655:         </div>
37656:         <div class="card">
37657:           <div class="card-label">Progress</div>
37658:           <div class="card-value" data-aion-goal-loop-department-progress="true">${escapeHtml(progress.status || context.status || "not_started")}</div>
37659:           <div class="card-sub">
37660:             Tasks ${escapeHtml(progress.completed_task_count || 0)}/${escapeHtml(progress.task_count || 0)} · Evidence ${escapeHtml(progress.evidence_count || 0)}
37661:           </div>
37662:         </div>
37663:         <div class="card">
37664:           <div class="card-label">Safety</div>
37665:           <div class="card-value" data-aion-goal-loop-department-safety="true">Blocked</div>
37666:           <div class="card-sub">No live execution, customer message, booking or payment</div>
37667:         </div>
37668:       </div>
37669: 
37670:       <div class="callout warning" data-aion-goal-loop-department-preview-boundary="true">
37671:         Department Pilot boundary: this panel only displays active Goal Loop context.
37672:         It does not create a new Pilot, create a new canvas, persist changes, execute tasks or call external services.
37673:       </div>
37674:     </section>
37675:   `;
37676: }
```

### Hit line 37687: `function renderAionDepartmentScopedPilotSurface(`

```js
37687: function renderAionDepartmentScopedPilotSurface(
37688:   departmentKey = "",
37689:   selectedRuns = [],
37690:   selectedAgentCard = null,
37691:   includeWorkflowPanels = true,
37692: ) {
37693:   const key = normaliseAionDepartmentPilotKey(departmentKey);
37694:   const label = runtimeShared.getDepartmentLabel(key);
37695:   const profile = getAionDepartmentPilotProfile(key);
37696:   const entry = getAionDepartmentPilotLedgerEntry(key);
37697:   const status = getAionDepartmentPilotStatus(key);
37698:   const runs = Array.isArray(selectedRuns) ? selectedRuns : getDepartmentRuns(key);
37699:   const tasks = Array.isArray(entry.tasks) ? entry.tasks : [];
37700:   const evidence = Array.isArray(entry.evidence) ? entry.evidence : [];
37701:   const receipts = Array.isArray(entry.receipts) ? entry.receipts : [];
37702:   const planReady = entry.plan && typeof entry.plan === "object" && Object.keys(entry.plan).length > 0;
37703: 
37704:   const completion =
37705:     typeof getAionDepartmentPilotCompletion === "function"
37706:       ? getAionDepartmentPilotCompletion(key)
37707:       : { answered: 0, total: 0, missing: [] };
37708: 
37709:   const approval =
37710:     typeof getAionDepartmentPilotApprovalState === "function"
37711:       ? getAionDepartmentPilotApprovalState(key)
37712:       : { status: "not_requested" };
37713: 
37714:   const resultStatus =
37715:     typeof getAionDepartmentResultEvidenceStatus === "function"
37716:       ? getAionDepartmentResultEvidenceStatus(entry)
37717:       : "missing";
37718: 
37719:   const specialistPlan = entry.specialist_plan || entry.plan?.specialist || null;
37720:   const nextSafeTask =
37721:     typeof getAionDepartmentPilotNextSafeTask === "function"
37722:       ? getAionDepartmentPilotNextSafeTask(key)
37723:       : null;
37724: 
37725:   const nextInstruction =
37726:     completion.answered === 0
37727:       ? `Start with ${label} discovery. Fill the fields below and press “Save discovery to ledger”.`
37728:       : !planReady
37729:         ? `Build the ${label} plan draft from the saved discovery.`
37730:         : approval.status !== "approved"
37731:           ? `Approve the ${label} plan, then build or run the safe queue.`
37732:           : nextSafeTask
37733:             ? `Run the next safe internal ${label} task. It will write results, evidence and receipts back to the Boardroom.`
37734:             : resultStatus === "results_available"
37735:               ? `${label} has Boardroom-visible results. Review the Boardroom assessment feed.`
37736:               : `Build or run the ${label} safe task queue.`;
37737: 
37738:   return `
37739:     <div
37740:       class="dashboard-shell"
37741:       data-aion-department-scoped-pilot="${escapeHtml(key)}"
37742:       data-aion-phase25b-department-scoped-pilot="true"
37743:       data-aion-phase25j-department-pilot-guided-workflow="true"
37744:     >
37745:       <section class="panel large-panel" style="background:#ffffff;">
37746:         <div class="surface-eyebrow">Department Pilot</div>
37747:         <div class="panel-title">${escapeHtml(profile.title)}</div>
37748:         <div class="helper-text">${escapeHtml(profile.purpose)}</div>
37749: 
37750:         <div class="notice warning" style="margin-top:12px;">
37751:           <strong>Next step:</strong> ${escapeHtml(nextInstruction)}
37752:         </div>
37753: 
37754:         <div class="card-grid" style="margin-top:9px;">
37755:           ${renderDashboardMetricCard("1. Discovery", `${completion.answered}/${completion.total}`, "Saved to ledger")}
37756:           ${renderDashboardMetricCard("2. Plan", planReady ? "ready" : "missing", "Draft only")}
37757:           ${renderDashboardMetricCard("3. Approval", approval.status || "not requested", "Human gated")}
37758:           ${renderDashboardMetricCard("4. Safe Queue", tasks.length, nextSafeTask ? "task ready" : "none ready")}
37759:           ${renderDashboardMetricCard("5. Evidence", evidence.length, "Boardroom proof")}
37760:           ${renderDashboardMetricCard("6. Receipts", receipts.length, "Replay / audit")}
37761:         </div>
37762: 
37763:         <div class="list-wrap" style="margin-top:9px;">
37764:           <div class="list-item">
37765:             <div class="list-item-title">How this department Pilot works</div>
37766:             <div class="list-item-sub">
37767:               Discovery, plan drafts, approvals, safe queue tasks, results, evidence and receipts all write into
37768:               <code>aion.departmentIntelligence.${escapeHtml(key)}</code>. The Boardroom reads that same ledger.
37769:             </div>
37770:           </div>
37771:           <div class="list-item">
37772:             <div class="list-item-title">Safety boundary</div>
37773:             <div class="list-item-sub">
37774:               This screen does not send, publish, spend, book, invoice, deploy or mutate external systems.
37775:               It only creates internal previews until exact human approval is added for a specific live action.
37776:             </div>
37777:           </div>
37778:         </div>
37779:       </section>
37780: 
37781:       ${
37782:         includeWorkflowPanels
37783:           ? `
37784:             ${renderAionDepartmentPilotPhase25CPanel(key)}
37785:             ${renderAionDepartmentPilotPhase25DPanel(key)}
37786:             ${renderAionDepartmentPilotPhase25EPanel(key)}
37787:             ${renderAionDepartmentPilotPhase25FPanel(key)}
37788:             ${renderAionDepartmentPilotGoalLoopContextPanel(key)}
37789:           `
37790:           : ""
37791:       }
37792: 
37793:       <div class="two-col">
37794:         <div class="panel large-panel">
37795:           <div class="panel-title">Discovery gaps</div>
37796:           ${renderAionDepartmentPilotMissingList(key)}
37797:         </div>
37798: 
37799:         <div class="panel large-panel">
37800:           <div class="panel-title">Boardroom feed</div>
37801:           <div class="list-item">
37802:             <div class="list-item-title">Current summary</div>
37803:             <div class="list-item-sub">${escapeHtml(getAionDepartmentPilotBoardroomSummary(key))}</div>
37804:             <div class="badge-row">
37805:               ${renderStatusBadge(status)}
37806:               <span class="badge">Result ${escapeHtml(resultStatus)}</span>
37807:               <span class="badge">Specialist ${specialistPlan ? "ready" : "missing"}</span>
37808:             </div>
37809:           </div>
37810:           <div class="list-item">
37811:             <div class="list-item-title">Where to see it working</div>
37812:             <div class="list-item-sub">
37813:               Open Boardroom Flat View for the Department Intelligence, Assessment Feed and Cross-Department Review panels.
37814:               Open Spatial Boardroom for the same department status as spatial seat intelligence.
37815:             </div>
37816:           </div>
37817:         </div>
37818:       </div>
37819:     </div>
37820:   `;
37821: }
```

### Hit line 37784: `${renderAionDepartmentPilotPhase25CPanel(key)}`

```js
37784:             ${renderAionDepartmentPilotPhase25CPanel(key)}
37785:             ${renderAionDepartmentPilotPhase25DPanel(key)}
```

### Hit line 37785: `${renderAionDepartmentPilotPhase25DPanel(key)}`

```js
37785:             ${renderAionDepartmentPilotPhase25DPanel(key)}
37786:             ${renderAionDepartmentPilotPhase25EPanel(key)}
```

### Hit line 37786: `${renderAionDepartmentPilotPhase25EPanel(key)}`

```js
37786:             ${renderAionDepartmentPilotPhase25EPanel(key)}
37787:             ${renderAionDepartmentPilotPhase25FPanel(key)}
```

### Hit line 37787: `${renderAionDepartmentPilotPhase25FPanel(key)}`

```js
37787:             ${renderAionDepartmentPilotPhase25FPanel(key)}
37788:             ${renderAionDepartmentPilotGoalLoopContextPanel(key)}
```

### Hit line 37788: `${renderAionDepartmentPilotGoalLoopContextPanel(key)}`

```js
37788:             ${renderAionDepartmentPilotGoalLoopContextPanel(key)}
37789:           `
```

### Hit line 37796: `${renderAionDepartmentPilotMissingList(key)}`

```js
37796:           ${renderAionDepartmentPilotMissingList(key)}
37797:         </div>
```

### Hit line 37803: `<div class="list-item-sub">${escapeHtml(getAionDepartmentPilotBoardroomSummary(key))}</div>`

```js
37803:             <div class="list-item-sub">${escapeHtml(getAionDepartmentPilotBoardroomSummary(key))}</div>
37804:             <div class="badge-row">
```

### Hit line 37825: `function applyAionDepartmentPilotAction(departmentKey = "", action = "") {`

```js
37825: function applyAionDepartmentPilotAction(departmentKey = "", action = "") {
37826:   const key = normaliseAionDepartmentPilotKey(departmentKey);
37827:   const profile = getAionDepartmentPilotProfile(key);
37828:   const now = new Date().toISOString();
37829: 
37830:   if (typeof updateAionDepartmentIntelligence !== "function") return;
37831: 
37832:   if (action === "seed_discovery") {
37833:     updateAionDepartmentIntelligence(key, {
37834:       status: "ready_to_plan",
37835:       discovery: {
37836:         scope: key,
37837:         captured_by: "department_pilot",
37838:         required_inputs: profile.missing,
37839:         source: "phase25b_department_scoped_pilot",
37840:       },
37841:       boardroom_summary: `${profile.title} discovery has started. AION can assess this department partially and will ask for missing inputs before full execution.`,
37842:       last_updated: now,
37843:     });
37844:     return;
37845:   }
37846: 
37847:   if (action === "build_plan") {
37848:     updateAionDepartmentIntelligence(key, {
37849:       status: "plan_ready",
37850:       plan: {
37851:         title: `${profile.title} plan preview`,
37852:         scope: key,
37853:         approval_required: true,
37854:         live_external_actions_blocked: true,
37855:         source: "phase25b_department_scoped_pilot",
37856:       },
37857:       boardroom_summary: `${profile.title} has a draft plan preview ready for approval. No live external action has been taken.`,
37858:       last_updated: now,
37859:     });
37860:     return;
37861:   }
37862: 
37863:   if (action === "stage_safe_queue") {
37864:     updateAionDepartmentIntelligence(key, {
37865:       status: "execution_queue_staged",
37866:       tasks: [
37867:         {
37868:           title: `${profile.title} safe draft task`,
37869:           status: "staged_preview",
37870:           approval_required_before_live_action: true,
37871:           live_external_actions_blocked: true,
37872:         },
37873:       ],
37874:       receipts: [
37875:         {
37876:           type: "preview_receipt",
37877:           source: "phase25b_department_scoped_pilot",
37878:           created_at: now,
37879:         },
37880:       ],
37881:       boardroom_summary: `${profile.title} has a staged safe execution queue. AION is stopped before public, financial or external side effects.`,
37882:       last_updated: now,
37883:     });
37884:   }
37885: }
```

### Hit line 37909: `window.getAionDepartmentPilotProfile = getAionDepartmentPilotProfile;`

```js
37909:   window.getAionDepartmentPilotProfile = getAionDepartmentPilotProfile;
37910:   window.renderAionDepartmentScopedPilotSurface = renderAionDepartmentScopedPilotSurface;
37911:   window.applyAionDepartmentPilotAction = applyAionDepartmentPilotAction;
37912: }
37913: 
37914: /* END PHASE 25B LOCK */
37915: 
37916: 
37917: /* PHASE 25C LOCK: Department Pilot Discovery Ledger Writeback */
37918: 
37919: const AION_DEPARTMENT_PILOT_DISCOVERY_TEMPLATES = {
```

### Hit line 37910: `window.renderAionDepartmentScopedPilotSurface = renderAionDepartmentScopedPilotSurface;`

```js
37910:   window.renderAionDepartmentScopedPilotSurface = renderAionDepartmentScopedPilotSurface;
37911:   window.applyAionDepartmentPilotAction = applyAionDepartmentPilotAction;
37912: }
37913: 
37914: /* END PHASE 25B LOCK */
37915: 
37916: 
37917: /* PHASE 25C LOCK: Department Pilot Discovery Ledger Writeback */
37918: 
37919: const AION_DEPARTMENT_PILOT_DISCOVERY_TEMPLATES = {
```

### Hit line 37911: `window.applyAionDepartmentPilotAction = applyAionDepartmentPilotAction;`

```js
37911:   window.applyAionDepartmentPilotAction = applyAionDepartmentPilotAction;
37912: }
37913: 
37914: /* END PHASE 25B LOCK */
37915: 
37916: 
37917: /* PHASE 25C LOCK: Department Pilot Discovery Ledger Writeback */
37918: 
37919: const AION_DEPARTMENT_PILOT_DISCOVERY_TEMPLATES = {
```

### Hit line 37965: `function getAionDepartmentPilotDiscoveryTemplate(departmentKey = "") {`

```js
37965: function getAionDepartmentPilotDiscoveryTemplate(departmentKey = "") {
37966:   const key = String(departmentKey || "").trim().toLowerCase();
37967:   return AION_DEPARTMENT_PILOT_DISCOVERY_TEMPLATES[key] || [
37968:     ["department_goal", "Department goal", "What should this department achieve?"],
37969:     ["current_process", "Current process", "How does this department work today?"],
37970:     ["known_gaps", "Known gaps", "What is missing, slow or broken?"],
37971:     ["approval_boundary", "Approval boundary", "What must Pilot ask before taking action?"],
37972:   ];
37973: }
```

### Hit line 37984: `function normaliseAionDepartmentPilotStatus(entry = {}) {`

```js
37984: function normaliseAionDepartmentPilotStatus(entry = {}) {
37985:   const status = String(entry.status || "").trim();
37986:   if (status) return status;
37987: 
37988:   if (entry.tasks && Array.isArray(entry.tasks) && entry.tasks.length) return "queue_ready";
37989:   if (entry.plan && Object.keys(asRecord(entry.plan) || {}).length) return "plan_ready";
37990:   if (entry.discovery && Object.keys(asRecord(entry.discovery) || {}).length) return "discovery_ready";
37991: 
37992:   return "needs_discovery";
37993: }
```

### Hit line 37995: `function getAionDepartmentPilotCompletion(departmentKey = "") {`

```js
37995: function getAionDepartmentPilotCompletion(departmentKey = "") {
37996:   const template = getAionDepartmentPilotDiscoveryTemplate(departmentKey);
37997:   const entry = getAionDepartmentLedgerEntry(departmentKey);
37998:   const discovery = asRecord(entry.discovery) || {};
37999: 
38000:   const answered = template.filter(([key]) => String(discovery[key] || "").trim()).length;
38001:   const total = template.length || 1;
38002: 
38003:   return {
38004:     answered,
38005:     total,
38006:     missing: template
38007:       .filter(([key]) => !String(discovery[key] || "").trim())
38008:       .map(([, label]) => label),
38009:   };
38010: }
```

### Hit line 38012: `function collectAionDepartmentPilotDiscoveryFromForm(departmentKey = "") {`

```js
38012: function collectAionDepartmentPilotDiscoveryFromForm(departmentKey = "") {
38013:   const key = String(departmentKey || "").trim().toLowerCase();
38014:   const discovery = {};
38015: 
38016:   document
38017:     .querySelectorAll(`[data-aion-department-pilot-discovery-field][data-department-key="${key}"]`)
38018:     .forEach((field) => {
38019:       const fieldKey = String(field.getAttribute("data-aion-department-pilot-discovery-field") || "").trim();
38020:       if (!fieldKey) return;
38021:       discovery[fieldKey] = String(field.value || "").trim();
38022:     });
38023: 
38024:   return discovery;
38025: }
```

### Hit line 38029: `const status = normaliseAionDepartmentPilotStatus(entry);`

```js
38027: function buildAionDepartmentBoardroomSummary(departmentKey = "", entry = {}) {
38028:   const label = runtimeShared.getDepartmentLabel(departmentKey);
38029:   const status = normaliseAionDepartmentPilotStatus(entry);
38030:   const completion = getAionDepartmentPilotCompletion(departmentKey);
38031:   const taskCount = Array.isArray(entry.tasks) ? entry.tasks.length : 0;
38032:   const resultCount = entry.results && typeof entry.results === "object" ? Object.keys(entry.results).length : 0;
38033: 
38034:   return `${label}: ${status}. Discovery ${completion.answered}/${completion.total}. Tasks ${taskCount}. Results ${resultCount}.`;
38035: }
```

### Hit line 38037: `function saveAionDepartmentPilotDiscovery(departmentKey = "", options = {}) {`

```js
38037: function saveAionDepartmentPilotDiscovery(departmentKey = "", options = {}) {
38038:   const key = String(departmentKey || "").trim().toLowerCase();
38039:   if (!key) return {};
38040: 
38041:   const current = getAionDepartmentLedgerEntry(key);
38042:   const existingDiscovery = asRecord(current.discovery) || {};
38043:   const nextDiscovery = {
38044:     ...existingDiscovery,
38045:     ...collectAionDepartmentPilotDiscoveryFromForm(key),
38046:   };
38047: 
38048:   const nextEntry = {
38049:     ...current,
38050:     status: "discovery_ready",
38051:     discovery: nextDiscovery,
38052:     last_updated: new Date().toISOString(),
38053:   };
38054: 
38055:   nextEntry.boardroom_summary = buildAionDepartmentBoardroomSummary(key, nextEntry);
38056: 
38057:   if (typeof updateAionDepartmentIntelligence === "function") {
38058:     updateAionDepartmentIntelligence(key, nextEntry);
38059:   }
38060: 
38061:   if (options.render !== false && typeof requestRender === "function") {
38062:     requestRender();
38063:   }
38064: 
38065:   return nextEntry;
38066: }
```

### Hit line 38068: `function buildAionDepartmentPilotPlanDraft(departmentKey = "", options = {}) {`

```js
38068: function buildAionDepartmentPilotPlanDraft(departmentKey = "", options = {}) {
38069:   const key = String(departmentKey || "").trim().toLowerCase();
38070:   if (!key) return {};
38071: 
38072:   const foundation =
38073:     typeof getApprovedSmallBusinessFoundationContext === "function"
38074:       ? getApprovedSmallBusinessFoundationContext()
38075:       : {};
38076:   const current = options.saveDiscoveryFirst === false
38077:     ? getAionDepartmentLedgerEntry(key)
38078:     : saveAionDepartmentPilotDiscovery(key, { render: false });
38079: 
38080:   const discovery = asRecord(current.discovery) || {};
38081:   const label = runtimeShared.getDepartmentLabel(key);
38082:   const businessName = foundation.business_name || foundation.name || state.workspaceId || "the business";
38083:   const primaryGoal = foundation.primary_goal || "improve business performance";
38084: 
38085:   const actionItems = getAionDepartmentPilotDiscoveryTemplate(key)
38086:     .filter(([fieldKey]) => String(discovery[fieldKey] || "").trim())
38087:     .slice(0, 5)
38088:     .map(([fieldKey, fieldLabel]) => ({
38089:       id: `${key}_${fieldKey}_action`,
38090:       title: `${fieldLabel} follow-up`,
38091:       detail: String(discovery[fieldKey] || "").trim(),
38092:       status: "draft_preview",
38093:       approval_required: true,
38094:     }));
38095: 
38096:   const plan = {
38097:     department: key,
38098:     title: `${label} Pilot plan`,
38099:     business_name: businessName,
38100:     objective: `${label} plan for ${businessName}: ${primaryGoal}`,
38101:     discovery_used: discovery,
38102:     action_items: actionItems.length
38103:       ? actionItems
38104:       : [
38105:           {
38106:             id: `${key}_discovery_required`,
38107:             title: "Complete discovery before planning",
38108:             detail: "Pilot needs more department context before creating a useful plan.",
38109:             status: "blocked_waiting_discovery",
38110:             approval_required: false,
38111:           },
38112:         ],
38113:     approval_boundary: [
38114:       "No external sending",
38115:       "No public posting",
38116:       "No ad spend",
38117:       "No booking",
38118:       "No payment",
38119:       "No production deploy",
38120:       "No live system mutation",
38121:     ],
38122:     created_at: new Date().toISOString(),
38123:   };
38124: 
38125:   const nextEntry = {
38126:     ...current,
38127:     status: "plan_ready",
38128:     plan,
38129:     last_updated: new Date().toISOString(),
38130:   };
38131: 
38132:   nextEntry.boardroom_summary = buildAionDepartmentBoardroomSummary(key, nextEntry);
38133: 
38134:   if (typeof updateAionDepartmentIntelligence === "function") {
38135:     updateAionDepartmentIntelligence(key, nextEntry);
38136:   }
38137: 
38138:   if (options.render !== false && typeof requestRender === "function") {
38139:     requestRender();
38140:   }
38141: 
38142:   return nextEntry;
38143: }
```

### Hit line 38145: `function buildAionDepartmentPilotSafeTaskQueue(departmentKey = "", options = {}) {`

```js
38145: function buildAionDepartmentPilotSafeTaskQueue(departmentKey = "", options = {}) {
38146:   const key = String(departmentKey || "").trim().toLowerCase();
38147:   if (!key) return {};
38148: 
38149:   const current = options.buildPlanFirst === false
38150:     ? getAionDepartmentLedgerEntry(key)
38151:     : buildAionDepartmentPilotPlanDraft(key, { render: false });
38152: 
38153:   const plan = asRecord(current.plan) || {};
38154:   const actions = Array.isArray(plan.action_items) ? plan.action_items : [];
38155: 
38156:   const tasks = actions.map((item, index) => ({
38157:     id: item.id || `${key}_safe_task_${index + 1}`,
38158:     title: item.title || `Safe ${runtimeShared.getDepartmentLabel(key)} task ${index + 1}`,
38159:     detail: item.detail || "",
38160:     status: item.status === "blocked_waiting_discovery" ? "blocked_waiting_discovery" : "queued_preview",
38161:     safety: "internal_preview_only",
38162:     approval_required: item.approval_required !== false,
38163:     no_live_side_effects: true,
38164:     created_at: new Date().toISOString(),
38165:   }));
38166: 
38167:   const nextEntry = {
38168:     ...current,
38169:     status: "queue_ready",
38170:     tasks,
38171:     last_updated: new Date().toISOString(),
38172:   };
38173: 
38174:   nextEntry.boardroom_summary = buildAionDepartmentBoardroomSummary(key, nextEntry);
38175: 
38176:   if (typeof updateAionDepartmentIntelligence === "function") {
38177:     updateAionDepartmentIntelligence(key, nextEntry);
38178:   }
38179: 
38180:   if (options.render !== false && typeof requestRender === "function") {
38181:     requestRender();
38182:   }
38183: 
38184:   return nextEntry;
38185: }
```

### Hit line 38187: `function renderAionDepartmentPilotDiscoveryPanel(departmentKey = "") {`

```js
38187: function renderAionDepartmentPilotDiscoveryPanel(departmentKey = "") {
38188:   const key = String(departmentKey || "").trim().toLowerCase();
38189:   const template = getAionDepartmentPilotDiscoveryTemplate(key);
38190:   const entry = getAionDepartmentLedgerEntry(key);
38191:   const discovery = asRecord(entry.discovery) || {};
38192:   const completion = getAionDepartmentPilotCompletion(key);
38193: 
38194:   return `
38195:     <section
38196:       class="panel large-panel"
38197:       data-aion-phase25c-department-pilot-discovery="${escapeHtml(key)}"
38198:       style="background:#ffffff; margin-top:9px;"
38199:     >
38200:       <div class="panel-title">${escapeHtml(runtimeShared.getDepartmentLabel(key))} Pilot Discovery</div>
38201:       <div class="helper-text">
38202:         Scoped discovery writes directly into <code>aion.departmentIntelligence.${escapeHtml(key)}.discovery</code>
38203:         and feeds the Boardroom automatically.
38204:       </div>
38205: 
38206:       <div class="badge-row" style="margin-top:10px;">
38207:         <span class="badge">Discovery ${escapeHtml(String(completion.answered))}/${escapeHtml(String(completion.total))}</span>
38208:         <span class="badge">Status ${escapeHtml(normaliseAionDepartmentPilotStatus(entry))}</span>
38209:         <span class="badge">Boardroom sync ready</span>
38210:       </div>
38211: 
38212:       <div style="display:grid; gap:10px; margin-top:9px;">
38213:         ${template.map(([fieldKey, label, placeholder]) => `
38214:           <label style="display:grid; gap:7px;">
38215:             <span class="card-label">${escapeHtml(label)}</span>
38216:             <textarea
38217:               class="input input-textarea input-textarea-small"
38218:               data-aion-department-pilot-discovery-field="${escapeHtml(fieldKey)}"
38219:               data-department-key="${escapeHtml(key)}"
38220:               placeholder="${escapeHtml(placeholder || "")}"
38221:               rows="2"
38222:               style="background:#ffffff;"
38223:             >${escapeHtml(discovery[fieldKey] || "")}</textarea>
38224:           </label>
38225:         `).join("")}
38226:       </div>
38227: 
38228:       <div class="marketing-form-actions" style="margin-top:9px;">
38229:         <button
38230:           type="button"
38231:           class="secondary-btn"
38232:           data-aion-phase25c-save-discovery="${escapeHtml(key)}"
38233:         >
38234:           Save discovery to ledger
38235:         </button>
38236:         <button
38237:           type="button"
38238:           class="secondary-btn"
38239:           data-aion-phase25c-build-plan="${escapeHtml(key)}"
38240:         >
38241:           Build department plan draft
38242:         </button>
38243:         <button
38244:           type="button"
38245:           class="primary-btn"
38246:           data-aion-phase25c-build-queue="${escapeHtml(key)}"
38247:         >
38248:           Build safe task queue
38249:         </button>
38250:       </div>
38251: 
38252:       <div class="notice warning" style="margin-top:12px;">
38253:         Discovery and queue creation are local preview actions only. Pilot has not posted, sent messages, spent money,
38254:         booked work, deployed changes or mutated live external systems.
38255:       </div>
38256:     </section>
38257:   `;
38258: }
```

### Hit line 38260: `function renderAionDepartmentPilotPlanPanel(departmentKey = "") {`

```js
38260: function renderAionDepartmentPilotPlanPanel(departmentKey = "") {
38261:   const key = String(departmentKey || "").trim().toLowerCase();
38262:   const entry = getAionDepartmentLedgerEntry(key);
38263:   const plan = asRecord(entry.plan) || {};
38264:   const actions = Array.isArray(plan.action_items) ? plan.action_items : [];
38265: 
38266:   return `
38267:     <section
38268:       class="panel large-panel"
38269:       data-aion-phase25c-department-pilot-plan="${escapeHtml(key)}"
38270:       style="background:#ffffff; margin-top:9px;"
38271:     >
38272:       <div class="panel-title">Department Plan Draft</div>
38273:       ${
38274:         Object.keys(plan).length
38275:           ? `
38276:             <div class="helper-text">${escapeHtml(plan.objective || "Plan draft ready.")}</div>
38277:             <div class="list-wrap" style="margin-top:12px;">
38278:               ${actions.map((item) => `
38279:                 <div class="list-item">
38280:                   <div class="list-item-title">${escapeHtml(item.title || "Action")}</div>
38281:                   <div class="list-item-sub">${escapeHtml(item.detail || "")}</div>
38282:                   <div class="badge-row">
38283:                     <span class="badge">${escapeHtml(item.status || "draft_preview")}</span>
38284:                     <span class="badge">${item.approval_required === false ? "No approval needed" : "Approval gated"}</span>
38285:                   </div>
38286:                 </div>
38287:               `).join("")}
38288:             </div>
38289:           `
38290:           : `<div class="empty-state">No ${escapeHtml(runtimeShared.getDepartmentLabel(key))} plan draft yet.</div>`
38291:       }
38292:     </section>
38293:   `;
38294: }
```

### Hit line 38296: `function renderAionDepartmentPilotSafeQueuePanel(departmentKey = "") {`

```js
38296: function renderAionDepartmentPilotSafeQueuePanel(departmentKey = "") {
38297:   const key = String(departmentKey || "").trim().toLowerCase();
38298:   const entry = getAionDepartmentLedgerEntry(key);
38299:   const tasks = Array.isArray(entry.tasks) ? entry.tasks : [];
38300: 
38301:   return `
38302:     <section
38303:       class="panel large-panel"
38304:       data-aion-phase25c-department-pilot-safe-queue="${escapeHtml(key)}"
38305:       style="background:#ffffff; margin-top:9px;"
38306:     >
38307:       <div class="panel-title">Safe Task Queue</div>
38308:       ${
38309:         tasks.length
38310:           ? `
38311:             <div class="list-wrap" style="margin-top:12px;">
38312:               ${tasks.map((task) => `
38313:                 <div class="list-item">
38314:                   <div class="list-item-title">${escapeHtml(task.title || "Safe task")}</div>
38315:                   <div class="list-item-sub">${escapeHtml(task.detail || "")}</div>
38316:                   <div class="badge-row">
38317:                     <span class="badge">${escapeHtml(task.status || "queued_preview")}</span>
38318:                     <span class="badge">${escapeHtml(task.safety || "internal_preview_only")}</span>
38319:                     <span class="badge">No live side effects</span>
38320:                   </div>
38321:                 </div>
38322:               `).join("")}
38323:             </div>
38324:           `
38325:           : `<div class="empty-state">No safe queue for ${escapeHtml(runtimeShared.getDepartmentLabel(key))} yet.</div>`
38326:       }
38327:     </section>
38328:   `;
38329: }
```

### Hit line 38331: `function renderAionDepartmentPilotLedgerSyncPanel(departmentKey = "") {`

```js
38331: function renderAionDepartmentPilotLedgerSyncPanel(departmentKey = "") {
38332:   const key = String(departmentKey || "").trim().toLowerCase();
38333:   const entry = getAionDepartmentLedgerEntry(key);
38334: 
38335:   return `
38336:     <section
38337:       class="panel large-panel"
38338:       data-aion-phase25c-department-pilot-ledger-sync="${escapeHtml(key)}"
38339:       style="background:#ffffff; margin-top:9px;"
38340:     >
38341:       <div class="panel-title">Boardroom Ledger Sync</div>
38342:       <div class="helper-text">
38343:         ${escapeHtml(entry.boardroom_summary || `${runtimeShared.getDepartmentLabel(key)} has not written a Boardroom summary yet.`)}
38344:       </div>
38345:       <div class="badge-row" style="margin-top:10px;">
38346:         <span class="badge">Ledger: aion.departmentIntelligence.${escapeHtml(key)}</span>
38347:         <span class="badge">Updated ${escapeHtml(formatDateTime(entry.last_updated))}</span>
38348:       </div>
38349:     </section>
38350:   `;
38351: }
```

### Hit line 38353: `function renderAionDepartmentPilotPhase25CPanel(departmentKey = "") {`

```js
38353: function renderAionDepartmentPilotPhase25CPanel(departmentKey = "") {
38354:   const key = String(departmentKey || "").trim().toLowerCase();
38355:   if (!key || key === "aion" || key === "pilot") return "";
38356: 
38357:   return `
38358:     <div data-aion-phase25c-department-pilot-ledger-writeback="${escapeHtml(key)}">
38359:       ${renderAionDepartmentPilotDiscoveryPanel(key)}
38360:       ${renderAionDepartmentPilotPlanPanel(key)}
38361:       ${renderAionDepartmentPilotSafeQueuePanel(key)}
38362:       ${renderAionDepartmentPilotLedgerSyncPanel(key)}
38363:     </div>
38364:   `;
38365: }
```

### Hit line 38569: `function getAionDepartmentPilotApprovalState(departmentKey = "") {`

```js
38569: function getAionDepartmentPilotApprovalState(departmentKey = "") {
38570:   const key = normaliseAionDepartmentPilotKey(departmentKey);
38571:   const ledger = getAionDepartmentIntelligence();
38572:   const entry = ledger[key] || normaliseAionDepartmentIntelligenceEntry(key, {});
38573:   return {
38574:     status: entry.plan_approval_status || "not_requested",
38575:     approved_at: entry.plan_approved_at || "",
38576:     approved_by: entry.plan_approved_by || "",
38577:     active_task_index: Number.isFinite(Number(entry.active_task_index))
38578:       ? Number(entry.active_task_index)
38579:       : 0,
38580:   };
38581: }
```

### Hit line 38583: `function approveAionDepartmentPilotPlan(departmentKey = "") {`

```js
38583: function approveAionDepartmentPilotPlan(departmentKey = "") {
38584:   const key = normaliseAionDepartmentPilotKey(departmentKey);
38585:   if (!key) return null;
38586: 
38587:   const plan =
38588:     typeof buildAionDepartmentPilotPlanDraft === "function"
38589:       ? buildAionDepartmentPilotPlanDraft(key)
38590:       : {};
38591: 
38592:   const queue =
38593:     typeof buildAionDepartmentPilotSafeTaskQueue === "function"
38594:       ? buildAionDepartmentPilotSafeTaskQueue(key)
38595:       : [];
38596: 
38597:   const now = new Date().toISOString();
38598: 
38599:   const taskQueue = queue.map((item, index) => ({
38600:     id: item.id || `${key}_safe_task_${index + 1}`,
38601:     title: item.title || item.label || `Safe task ${index + 1}`,
38602:     status: item.status || "approved",
38603:     type: item.type || "safe_internal_preview",
38604:     approval_boundary: item.approval_boundary || "no_live_external_side_effects",
38605:     created_at: item.created_at || now,
38606:     updated_at: now,
38607:   }));
38608: 
38609:   const patch = {
38610:     status: "plan_approved",
38611:     plan,
38612:     tasks: taskQueue,
38613:     plan_approval_status: "approved",
38614:     plan_approved_at: now,
38615:     plan_approved_by: "human_operator",
38616:     active_task_index: 0,
38617:     boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} plan approved. ${taskQueue.length} safe internal task(s) ready for preview execution.`,
38618:     confidence: taskQueue.length ? "useful" : "partial",
38619:     alerts: [],
38620:     last_updated: now,
38621:   };
38622: 
38623:   updateAionDepartmentIntelligence(key, patch);
38624: 
38625:   if (typeof requestRender === "function") {
38626:     requestRender();
38627:   }
38628: 
38629:   return patch;
38630: }
```

### Hit line 38632: `function getAionDepartmentPilotApprovedTaskQueue(departmentKey = "") {`

```js
38632: function getAionDepartmentPilotApprovedTaskQueue(departmentKey = "") {
38633:   const key = normaliseAionDepartmentPilotKey(departmentKey);
38634:   const ledger = getAionDepartmentIntelligence();
38635:   const entry = ledger[key] || {};
38636:   return Array.isArray(entry.tasks) ? entry.tasks : [];
38637: }
```

### Hit line 38639: `function getAionDepartmentPilotNextSafeTask(departmentKey = "") {`

```js
38639: function getAionDepartmentPilotNextSafeTask(departmentKey = "") {
38640:   const key = normaliseAionDepartmentPilotKey(departmentKey);
38641:   const queue = getAionDepartmentPilotApprovedTaskQueue(key);
38642:   return queue.find((item) => {
38643:     const status = String(item?.status || "").toLowerCase();
38644:     return status === "approved" || status === "queued" || status === "ready";
38645:   }) || null;
38646: }
```

### Hit line 38648: `function runAionDepartmentPilotNextSafeTask(departmentKey = "") {`

```js
38648: function runAionDepartmentPilotNextSafeTask(departmentKey = "") {
38649:   const key = normaliseAionDepartmentPilotKey(departmentKey);
38650:   if (!key) return null;
38651: 
38652:   const ledger = getAionDepartmentIntelligence();
38653:   const entry = ledger[key] || normaliseAionDepartmentIntelligenceEntry(key, {});
38654:   const queue = Array.isArray(entry.tasks) ? entry.tasks : [];
38655:   const now = new Date().toISOString();
38656: 
38657:   const nextIndex = queue.findIndex((item) => {
38658:     const status = String(item?.status || "").toLowerCase();
38659:     return status === "approved" || status === "queued" || status === "ready";
38660:   });
38661: 
38662:   if (nextIndex < 0) {
38663:     const patch = {
38664:       status: "safe_queue_complete",
38665:       boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} has no remaining approved safe internal preview tasks.`,
38666:       last_updated: now,
38667:     };
38668:     updateAionDepartmentIntelligence(key, patch);
38669:     if (typeof requestRender === "function") requestRender();
38670:     return patch;
38671:   }
38672: 
38673:   const task = queue[nextIndex] || {};
38674:   const completedTask = {
38675:     ...task,
38676:     status: "completed_preview",
38677:     completed_at: now,
38678:     updated_at: now,
38679:     result_summary: `${task.title || "Safe task"} completed as an internal preview. No live external action was taken.`,
38680:   };
38681: 
38682:   const nextTasks = queue.map((item, index) => (index === nextIndex ? completedTask : item));
38683: 
38684:   const runRecord = {
38685:     id: `${key}_safe_preview_run_${Date.now()}`,
38686:     department_key: key,
38687:     title: completedTask.title,
38688:     status: "completed_preview",
38689:     source: "department_pilot_safe_queue",
38690:     created_at: now,
38691:     updated_at: now,
38692:     safety_boundary: "no_live_external_side_effects",
38693:   };
38694: 
38695:   const receipt = {
38696:     id: `${key}_safe_preview_receipt_${Date.now()}`,
38697:     department_key: key,
38698:     task_id: completedTask.id,
38699:     receipt_type: "safe_internal_preview",
38700:     status: "draft_receipt",
38701:     created_at: now,
38702:     no_live_external_action: true,
38703:   };
38704: 
38705:   const resultRecord = {
38706:     id: `${key}_safe_preview_result_${Date.now()}`,
38707:     department_key: key,
38708:     task_id: completedTask.id,
38709:     title: completedTask.title,
38710:     status: "results_available",
38711:     result_type: "safe_internal_preview",
38712:     summary: completedTask.result_summary,
38713:     created_at: now,
38714:     no_live_external_action: true,
38715:   };
38716: 
38717:   const evidenceRecord = {
38718:     id: `${key}_safe_preview_evidence_${Date.now()}`,
38719:     department_key: key,
38720:     task_id: completedTask.id,
38721:     evidence_type: "safe_task_result",
38722:     title: completedTask.title,
38723:     summary: completedTask.result_summary,
38724:     receipt_id: receipt.id,
38725:     created_at: now,
38726:     provenance: "department_pilot_safe_queue",
38727:   };
38728: 
38729:   const existingResults =
38730:     entry.results && typeof entry.results === "object" && !Array.isArray(entry.results)
38731:       ? entry.results
38732:       : {};
38733: 
38734:   const patch = {
38735:     status: nextTasks.some((item) => ["approved", "queued", "ready"].includes(String(item?.status || "").toLowerCase()))
38736:       ? "executing_safe_queue"
38737:       : "safe_queue_complete",
38738:     tasks: nextTasks,
38739:     runs: [...(Array.isArray(entry.runs) ? entry.runs : []), runRecord],
38740:     results: {
38741:       ...existingResults,
38742:       latest_safe_preview: resultRecord,
38743:       safe_preview_history: [
38744:         ...(Array.isArray(existingResults.safe_preview_history) ? existingResults.safe_preview_history : []),
38745:         resultRecord,
38746:       ],
38747:     },
38748:     evidence: [...(Array.isArray(entry.evidence) ? entry.evidence : []), evidenceRecord],
38749:     receipts: [...(Array.isArray(entry.receipts) ? entry.receipts : []), receipt],
38750:     boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} safe task completed: ${completedTask.title}. Results, evidence and receipt were written to the Boardroom feed. No live external action was taken.`,
38751:     active_task_index: nextIndex + 1,
38752:     confidence: "useful",
38753:     alerts: Array.isArray(entry.alerts) ? entry.alerts : [],
38754:     last_updated: now,
38755:   };
38756: 
38757:   updateAionDepartmentIntelligence(key, patch);
38758: 
38759:   if (typeof requestRender === "function") {
38760:     requestRender();
38761:   }
38762: 
38763:   return patch;
38764: }
```

### Hit line 38766: `function renderAionDepartmentPilotPhase25DPanel(departmentKey = "") {`

```js
38766: function renderAionDepartmentPilotPhase25DPanel(departmentKey = "") {
38767:   const key = normaliseAionDepartmentPilotKey(departmentKey);
38768:   const label = runtimeShared.getDepartmentLabel(key);
38769:   const approval = getAionDepartmentPilotApprovalState(key);
38770:   const queue = getAionDepartmentPilotApprovedTaskQueue(key);
38771:   const nextTask = getAionDepartmentPilotNextSafeTask(key);
38772:   const completed = queue.filter((item) => String(item?.status || "").toLowerCase() === "completed_preview").length;
38773:   const pending = queue.length - completed;
38774: 
38775:   return `
38776:     <section
38777:       class="panel large-panel"
38778:       data-aion-phase25d-department-pilot-safe-queue="true"
38779:       data-aion-phase25d-department="${escapeHtml(key)}"
38780:       style="margin-top:9px; background:#ffffff;"
38781:     >
38782:       <div class="panel-title">${escapeHtml(label)} Plan Approval + Safe Queue</div>
38783:       <div class="helper-text">
38784:         Approve the department plan, then run safe internal preview tasks. This does not send, publish, spend, book, deploy or mutate external systems.
38785:       </div>
38786: 
38787:       <div class="card-grid" style="margin-top:12px;">
38788:         ${renderDashboardMetricCard("Plan approval", approval.status, "Human-gated")}
38789:         ${renderDashboardMetricCard("Safe tasks", queue.length, `${completed} done · ${pending} pending`)}
38790:         ${renderDashboardMetricCard("Next safe task", nextTask?.title || "None", "Preview only")}
38791:         ${renderDashboardMetricCard("Live actions", "blocked", "Exact approval required")}
38792:       </div>
38793: 
38794:       <div class="marketing-form-actions" style="margin-top:12px;">
38795:         <button
38796:           type="button"
38797:           class="primary-btn"
38798:           data-aion-phase25d-approve-plan="${escapeHtml(key)}"
38799:         >
38800:           Approve ${escapeHtml(label)} plan
38801:         </button>
38802:         <button
38803:           type="button"
38804:         data-aion-council-session-ask-board="true"
38805:           class="secondary-btn"
38806:           data-aion-phase25d-run-safe-task="${escapeHtml(key)}"
38807:           ${nextTask ? "" : "disabled"}
38808:         >
38809:           Run next safe task
38810:         </button>
38811:       </div>
38812: 
38813:       ${
38814:         queue.length
38815:           ? `
38816:             <div class="list-wrap" style="margin-top:12px;">
38817:               ${queue.map((task) => `
38818:                 <div class="list-item">
38819:                   <div class="list-item-title">${escapeHtml(task.title || task.id || "Safe task")}</div>
38820:                   <div class="list-item-sub">${escapeHtml(task.result_summary || task.approval_boundary || "Safe internal preview task")}</div>
38821:                   <div class="badge-row">
38822:                     ${renderStatusBadge(task.status || "approved")}
38823:                     <span class="badge">${escapeHtml(task.type || "safe_internal_preview")}</span>
38824:                   </div>
38825:                 </div>
38826:               `).join("")}
38827:             </div>
38828:           `
38829:           : `<div class="empty-state" style="margin-top:12px;">No approved safe queue yet. Approve the department plan to create one.</div>`
38830:       }
38831: 
38832:       <div class="notice warning" style="margin-top:12px;">
38833:         Safety: no emails, posts, ads, payments, bookings, invoices, deployments or external writes are performed by this panel.
38834:       </div>
38835:     </section>
38836:   `;
38837: }
```

### Hit line 38847: `approveAionDepartmentPilotPlan(approveButton.getAttribute("data-aion-phase25d-approve-plan"));`

```js
38847:       approveAionDepartmentPilotPlan(approveButton.getAttribute("data-aion-phase25d-approve-plan"));
38848:       return;
38849:     }
38850: 
38851:     const runButton = event.target?.closest?.("[data-aion-phase25d-run-safe-task]");
38852:     if (runButton) {
```

### Hit line 38855: `runAionDepartmentPilotNextSafeTask(runButton.getAttribute("data-aion-phase25d-run-safe-task"));`

```js
38855:       runAionDepartmentPilotNextSafeTask(runButton.getAttribute("data-aion-phase25d-run-safe-task"));
38856:     }
38857:   }, true);
38858: }
38859: 
38860: if (typeof window !== "undefined") {
```

### Hit line 38861: `window.getAionDepartmentPilotApprovalState = getAionDepartmentPilotApprovalState;`

```js
38861:   window.getAionDepartmentPilotApprovalState = getAionDepartmentPilotApprovalState;
38862:   window.approveAionDepartmentPilotPlan = approveAionDepartmentPilotPlan;
38863:   window.getAionDepartmentPilotApprovedTaskQueue = getAionDepartmentPilotApprovedTaskQueue;
38864:   window.getAionDepartmentPilotNextSafeTask = getAionDepartmentPilotNextSafeTask;
38865:   window.runAionDepartmentPilotNextSafeTask = runAionDepartmentPilotNextSafeTask;
38866: }
38867: 
38868: 
38869: 
38870: /* PHASE 25E LOCK: Department Results Evidence Boardroom Assessment Feed */
38871: 
38872: function getAionDepartmentResultEvidenceStatus(entry = {}) {
```

### Hit line 38862: `window.approveAionDepartmentPilotPlan = approveAionDepartmentPilotPlan;`

```js
38862:   window.approveAionDepartmentPilotPlan = approveAionDepartmentPilotPlan;
38863:   window.getAionDepartmentPilotApprovedTaskQueue = getAionDepartmentPilotApprovedTaskQueue;
38864:   window.getAionDepartmentPilotNextSafeTask = getAionDepartmentPilotNextSafeTask;
38865:   window.runAionDepartmentPilotNextSafeTask = runAionDepartmentPilotNextSafeTask;
38866: }
38867: 
38868: 
38869: 
38870: /* PHASE 25E LOCK: Department Results Evidence Boardroom Assessment Feed */
38871: 
38872: function getAionDepartmentResultEvidenceStatus(entry = {}) {
```

### Hit line 38863: `window.getAionDepartmentPilotApprovedTaskQueue = getAionDepartmentPilotApprovedTaskQueue;`

```js
38863:   window.getAionDepartmentPilotApprovedTaskQueue = getAionDepartmentPilotApprovedTaskQueue;
38864:   window.getAionDepartmentPilotNextSafeTask = getAionDepartmentPilotNextSafeTask;
38865:   window.runAionDepartmentPilotNextSafeTask = runAionDepartmentPilotNextSafeTask;
38866: }
38867: 
38868: 
38869: 
38870: /* PHASE 25E LOCK: Department Results Evidence Boardroom Assessment Feed */
38871: 
38872: function getAionDepartmentResultEvidenceStatus(entry = {}) {
```

### Hit line 38864: `window.getAionDepartmentPilotNextSafeTask = getAionDepartmentPilotNextSafeTask;`

```js
38864:   window.getAionDepartmentPilotNextSafeTask = getAionDepartmentPilotNextSafeTask;
38865:   window.runAionDepartmentPilotNextSafeTask = runAionDepartmentPilotNextSafeTask;
38866: }
38867: 
38868: 
38869: 
38870: /* PHASE 25E LOCK: Department Results Evidence Boardroom Assessment Feed */
38871: 
38872: function getAionDepartmentResultEvidenceStatus(entry = {}) {
```

### Hit line 38865: `window.runAionDepartmentPilotNextSafeTask = runAionDepartmentPilotNextSafeTask;`

```js
38865:   window.runAionDepartmentPilotNextSafeTask = runAionDepartmentPilotNextSafeTask;
38866: }
38867: 
38868: 
38869: 
38870: /* PHASE 25E LOCK: Department Results Evidence Boardroom Assessment Feed */
38871: 
38872: function getAionDepartmentResultEvidenceStatus(entry = {}) {
```

### Hit line 42535: `function renderAionDepartmentTasksHtmlV2() {`

```js
42535: function renderAionDepartmentTasksHtmlV2() {
42536:   const result = window.__aionBoardroomDepartmentTasks;
42537:   if (!result) return "";
42538: 
42539:   if (result.status === "blocked") {
42540:     return `
42541:       <div
42542:         data-aion-boardroom-department-tasks="blocked"
42543:         style="margin-top:12px;border:1px solid rgba(251,191,36,0.38);background:#1f1307;color:#fde68a;padding:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono',monospace;font-size:12px;line-height:1.36;"
42544:       >
42545:         <div style="font-weight:900;">&gt; Build Department Tasks blocked</div>
42546:         <div>&gt; ${escapeHtml(result.reason || "Run Debate Plan first.")}</div>
42547:       </div>
42548:     `;
42549:   }
42550: 
42551:   const tasks = safeArray(result.tasks);
42552: 
42553:   return `
42554:     <div
42555:       data-aion-boardroom-department-tasks="true"
42556:       style="
42557:         margin-top:12px;
42558:         border:1px solid rgba(168,85,247,0.42);
42559:         background:#10091f;
42560:         color:#ede9fe;
42561:         padding:14px;
42562:         font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono',monospace;
42563:         font-size:12px;
42564:         line-height:1.48;
42565:         box-shadow:inset 4px 0 0 #a855f7;
42566:       "
42567:     >
42568:       <div style="font-weight:900;color:#c4b5fd;letter-spacing:0.08em;text-transform:uppercase;">
42569:         &gt; Round 3 · department task build
42570:       </div>
42571:       <div>&gt; Status: ${escapeHtml(result.status || "")}</div>
42572:       <div>&gt; Provider mode: ${escapeHtml(result.provider_mode || "unknown")} · live fanout: ${result.live_provider_fanout ? "yes" : "no"}</div>
42573:       ${typeof renderAionGenericTaskStagingPackHtmlV1 === "function" ? renderAionGenericTaskStagingPackHtmlV1(result.generic_task_staging_pack || result) : ""}
42574: 
42575:       <div>&gt; Result hash: ${escapeHtml(result.result_hash || "")}</div>
42576:       <div>&gt; Boundary: ${escapeHtml(result.delegation_boundary || "")}</div>
42577: 
42578:       <div style="margin-top:10px;color:#ffffff;font-weight:900;">&gt; Department-owned tasks</div>
42579:       ${tasks.map((task, index) => `
42580:         <div style="margin-top:10px;padding-top:8px;border-top:1px solid rgba(196,181,253,0.18);">
42581:           <div style="color:#ffffff;font-weight:900;">&gt; Task ${index + 1} · ${escapeHtml(task.department || "")} · ${escapeHtml(task.owner || "")}</div>
42582:           <div>&gt; title: ${escapeHtml(task.task_title || "")}</div>
42583:           <div>&gt; source: ${escapeHtml(task.source_plan_item || "")}</div>
42584:           <div>&gt; objective: ${escapeHtml(task.objective || "")}</div>
42585:           <div style="margin-top:5px;color:#fbbf24;">&gt; inputs needed</div>
42586:           ${safeArray(task.inputs_needed).map((line) => `<div>&gt; + ${escapeHtml(line)}</div>`).join("") || "<div>&gt; none</div>"}
42587:           <div style="margin-top:5px;color:#fb7185;">&gt; blockers</div>
42588:           ${safeArray(task.blockers).map((line) => `<div>&gt; ! ${escapeHtml(line)}</div>`).join("") || "<div>&gt; none</div>"}
42589:           <div style="margin-top:5px;color:#86efac;">&gt; output required: ${escapeHtml(task.output_required || "")}</div>
42590:           <div>&gt; success metric: ${escapeHtml(task.success_metric || "")}</div>
42591:           <div>&gt; approval required: ${task.approval_required ? "yes" : "no"}</div>
42592:         </div>
42593:       `).join("")}
42594:       ${typeof renderAionFounderFeedbackBoxV3 === "function" ? renderAionFounderFeedbackBoxV3(
42595:         "department_tasks",
42596:         "after Round 3 department task build",
42597:         "Edit the delegation logic before sending work to department pilots. Nothing is executed until founder approval.",
42598:         `<button
42599:           type="button"
42600:           class="aion-council-session-action"
42601:           data-aion-council-session-delegate-agents="true"
42602:           style="border-color:rgba(34,197,94,0.75);background:#052e16;color:#dcfce7;"
42603:         >
42604:           Delegate to Agents
42605:         </button>`
42606:       ) : ""}
42607:     </div>
42608:   `;
42609: }
```

### Hit line 43208: `${typeof renderAionDepartmentTasksHtmlV2 === "function" ? renderAionDepartmentTasksHtmlV2() : ""}`

```js
43208:       ${typeof renderAionDepartmentTasksHtmlV2 === "function" ? renderAionDepartmentTasksHtmlV2() : ""}
43209: 
```

### Hit line 43637: `function renderAionDepartmentPilotPhase25EPanel(departmentKey = "") {`

```js
43637: function renderAionDepartmentPilotPhase25EPanel(departmentKey = "") {
43638:   const key = normaliseAionDepartmentPilotKey(departmentKey);
43639:   const ledger = getAionDepartmentIntelligence();
43640:   const entry = ledger[key] || normaliseAionDepartmentIntelligenceEntry(key, {});
43641:   const label = runtimeShared.getDepartmentLabel(key);
43642:   const results = entry.results && typeof entry.results === "object" && !Array.isArray(entry.results)
43643:     ? entry.results
43644:     : {};
43645:   const history = Array.isArray(results.safe_preview_history) ? results.safe_preview_history : [];
43646:   const latest = results.latest_safe_preview || history[history.length - 1] || null;
43647:   const evidence = Array.isArray(entry.evidence) ? entry.evidence : [];
43648:   const receipts = Array.isArray(entry.receipts) ? entry.receipts : [];
43649: 
43650:   return `
43651:     <section
43652:       class="panel large-panel"
43653:       data-aion-phase25e-department-results-evidence="true"
43654:       data-aion-phase25e-department="${escapeHtml(key)}"
43655:       style="margin-top:9px; background:#ffffff;"
43656:     >
43657:       <div class="panel-title">${escapeHtml(label)} Results / Evidence Feed</div>
43658:       <div class="helper-text">
43659:         Safe task outcomes written into the Department Intelligence Ledger for Boardroom and AION assessment.
43660:       </div>
43661: 
43662:       <div class="card-grid" style="margin-top:12px;">
43663:         ${renderDashboardMetricCard("Result status", getAionDepartmentResultEvidenceStatus(entry), "Boardroom visible")}
43664:         ${renderDashboardMetricCard("Evidence", evidence.length, "Safe internal proof records")}
43665:         ${renderDashboardMetricCard("Receipts", receipts.length, "Preview receipts")}
43666:         ${renderDashboardMetricCard("Latest result", latest?.status || "none", latest?.title || "No completed safe task yet")}
43667:       </div>
43668: 
43669:       ${
43670:         latest
43671:           ? `
43672:             <div class="list-item" style="margin-top:12px;">
43673:               <div class="list-item-title">${escapeHtml(latest.title || "Latest result")}</div>
43674:               <div class="list-item-sub">${escapeHtml(latest.summary || "No result summary yet.")}</div>
43675:               <div class="badge-row">
43676:                 ${renderStatusBadge(latest.status || "results_available")}
43677:                 <span class="badge">${escapeHtml(latest.created_at || "not dated")}</span>
43678:                 <span class="badge">No live external action</span>
43679:               </div>
43680:             </div>
43681:           `
43682:           : `<div class="empty-state" style="margin-top:12px;">No safe task result yet. Run an approved safe queue task to populate this feed.</div>`
43683:       }
43684: 
43685:       <div class="notice warning" style="margin-top:12px;">
43686:         These are internal preview results only. They can inform AION assessment, but they do not publish, spend, send, book, invoice or deploy anything.
43687:       </div>
43688:     </section>
43689:   `;
43690: }
```

### Hit line 43765: `function getAionDepartmentPilotSpecialistPlaybook(departmentKey = "") {`

```js
43765: function getAionDepartmentPilotSpecialistPlaybook(departmentKey = "") {
43766:   const key = normaliseAionDepartmentPilotKey(departmentKey);
43767:   return AION_DEPARTMENT_PILOT_SPECIALIST_PLAYBOOKS[key] || {
43768:     title: `${runtimeShared.getDepartmentLabel(key)} Specialist Pilot`,
43769:     objective: "Create a safe specialist plan for this department.",
43770:     specialist_fields: [],
43771:     outputs: ["department_plan"],
43772:     task_templates: [
43773:       [`${key}_specialist_plan`, "Prepare specialist plan", "Create a safe internal department specialist plan."],
43774:     ],
43775:   };
43776: }
```

### Hit line 43778: `function buildAionDepartmentPilotSpecialistDraft(departmentKey = "", options = {}) {`

```js
43778: function buildAionDepartmentPilotSpecialistDraft(departmentKey = "", options = {}) {
43779:   const key = normaliseAionDepartmentPilotKey(departmentKey);
43780:   if (!key) return null;
43781: 
43782:   const now = new Date().toISOString();
43783:   const playbook = getAionDepartmentPilotSpecialistPlaybook(key);
43784:   const entry = getAionDepartmentLedgerEntry(key);
43785:   const discovery = asRecord(entry.discovery) || {};
43786:   const existingPlan = asRecord(entry.plan) || {};
43787: 
43788:   const populatedFields = safeArray(playbook.specialist_fields)
43789:     .filter((fieldKey) => String(discovery[fieldKey] || "").trim())
43790:     .map((fieldKey) => ({
43791:       key: fieldKey,
43792:       value: String(discovery[fieldKey] || "").trim(),
43793:     }));
43794: 
43795:   const specialistPlan = {
43796:     department: key,
43797:     title: playbook.title,
43798:     objective: playbook.objective,
43799:     populated_fields: populatedFields,
43800:     missing_fields: safeArray(playbook.specialist_fields).filter((fieldKey) => !String(discovery[fieldKey] || "").trim()),
43801:     planned_outputs: safeArray(playbook.outputs),
43802:     task_templates: safeArray(playbook.task_templates).map(([id, title, detail]) => ({
43803:       id,
43804:       title,
43805:       detail,
43806:       status: "draft_preview",
43807:       type: "specialist_department_task",
43808:       approval_required: true,
43809:       no_live_external_action: true,
43810:     })),
43811:     safety_boundary: [
43812:       "internal_preview_only",
43813:       "approval_required_before_external_action",
43814:       "no_public_posting",
43815:       "no_external_messages",
43816:       "no_ad_spend",
43817:       "no_booking",
43818:       "no_payment",
43819:       "no_live_system_mutation",
43820:     ],
43821:     created_at: now,
43822:   };
43823: 
43824:   const patch = {
43825:     status: "specialist_plan_ready",
43826:     plan: {
43827:       ...existingPlan,
43828:       specialist: specialistPlan,
43829:     },
43830:     specialist_plan: specialistPlan,
43831:     boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} specialist plan ready. ${populatedFields.length} discovery field(s) used. ${specialistPlan.missing_fields.length} field(s) still missing.`,
43832:     confidence: populatedFields.length >= 3 ? "useful" : populatedFields.length ? "partial" : "empty",
43833:     alerts: specialistPlan.missing_fields.length
43834:       ? [`${runtimeShared.getDepartmentLabel(key)} specialist plan has missing discovery fields.`]
43835:       : [],
43836:     last_updated: now,
43837:   };
43838: 
43839:   updateAionDepartmentIntelligence(key, patch);
43840: 
43841:   if (options.render !== false && typeof requestRender === "function") {
43842:     requestRender();
43843:   }
43844: 
43845:   return patch;
43846: }
```

### Hit line 43848: `function buildAionDepartmentPilotSpecialistSafeQueue(departmentKey = "", options = {}) {`

```js
43848: function buildAionDepartmentPilotSpecialistSafeQueue(departmentKey = "", options = {}) {
43849:   const key = normaliseAionDepartmentPilotKey(departmentKey);
43850:   if (!key) return null;
43851: 
43852:   const now = new Date().toISOString();
43853:   const specialistPatch = buildAionDepartmentPilotSpecialistDraft(key, { render: false });
43854:   const entry = getAionDepartmentLedgerEntry(key);
43855:   const existingTasks = Array.isArray(entry.tasks) ? entry.tasks : [];
43856:   const specialistPlan = specialistPatch.specialist_plan || {};
43857:   const taskTemplates = Array.isArray(specialistPlan.task_templates) ? specialistPlan.task_templates : [];
43858: 
43859:   const specialistTasks = taskTemplates.map((task, index) => ({
43860:     id: task.id || `${key}_specialist_task_${index + 1}`,
43861:     title: task.title || `Specialist task ${index + 1}`,
43862:     detail: task.detail || "",
43863:     status: "approved",
43864:     type: task.type || "specialist_department_task",
43865:     safety: "internal_preview_only",
43866:     approval_boundary: "no_live_external_side_effects",
43867:     approval_required: true,
43868:     no_live_external_action: true,
43869:     created_at: now,
43870:     updated_at: now,
43871:   }));
43872: 
43873:   const existingSpecialistIds = new Set(specialistTasks.map((task) => task.id));
43874:   const retainedTasks = existingTasks.filter((task) => !existingSpecialistIds.has(task.id));
43875: 
43876:   const patch = {
43877:     status: "specialist_queue_ready",
43878:     tasks: [...retainedTasks, ...specialistTasks],
43879:     boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} specialist queue ready with ${specialistTasks.length} safe internal preview task(s).`,
43880:     confidence: specialistTasks.length ? "useful" : "partial",
43881:     last_updated: now,
43882:   };
43883: 
43884:   updateAionDepartmentIntelligence(key, patch);
43885: 
43886:   if (options.render !== false && typeof requestRender === "function") {
43887:     requestRender();
43888:   }
43889: 
43890:   return patch;
43891: }
```

### Hit line 43893: `function renderAionDepartmentPilotPhase25FPanel(departmentKey = "") {`

```js
43893: function renderAionDepartmentPilotPhase25FPanel(departmentKey = "") {
43894:   const key = normaliseAionDepartmentPilotKey(departmentKey);
43895:   const label = runtimeShared.getDepartmentLabel(key);
43896:   const playbook = getAionDepartmentPilotSpecialistPlaybook(key);
43897:   const entry = getAionDepartmentLedgerEntry(key);
43898:   const specialistPlan = asRecord(entry.specialist_plan) || asRecord(asRecord(entry.plan || {}).specialist) || {};
43899:   const specialistTasks = Array.isArray(entry.tasks)
43900:     ? entry.tasks.filter((task) => String(task?.type || "") === "specialist_department_task")
43901:     : [];
43902: 
43903:   return `
43904:     <section
43905:       class="panel large-panel"
43906:       data-aion-phase25f-department-specialist-pilot="true"
43907:       data-aion-phase25f-department="${escapeHtml(key)}"
43908:       style="margin-top:9px; background:#ffffff;"
43909:     >
43910:       <div class="panel-title">${escapeHtml(playbook.title || `${label} Specialist Pilot`)}</div>
43911:       <div class="helper-text">
43912:         ${escapeHtml(playbook.objective || "Specialist department mode.")}
43913:       </div>
43914: 
43915:       <div class="card-grid" style="margin-top:12px;">
43916:         ${renderDashboardMetricCard("Specialist status", entry.status || "needs_discovery", "Department-specific")}
43917:         ${renderDashboardMetricCard("Planned outputs", safeArray(playbook.outputs).length, safeArray(playbook.outputs).join(", ") || "none")}
43918:         ${renderDashboardMetricCard("Specialist tasks", specialistTasks.length, "Safe internal preview")}
43919:         ${renderDashboardMetricCard("Live actions", "blocked", "Exact approval required")}
43920:       </div>
43921: 
43922:       <div class="marketing-form-actions" style="margin-top:12px;">
43923:         <button
43924:           type="button"
43925:           class="secondary-btn"
43926:           data-aion-phase25f-build-specialist-plan="${escapeHtml(key)}"
43927:         >
43928:           Build ${escapeHtml(label)} specialist plan
43929:         </button>
43930:         <button
43931:           type="button"
43932:           class="primary-btn"
43933:           data-aion-phase25f-build-specialist-queue="${escapeHtml(key)}"
43934:         >
43935:           Build ${escapeHtml(label)} specialist queue
43936:         </button>
43937:       </div>
43938: 
43939:       ${
43940:         Object.keys(specialistPlan).length
43941:           ? `
43942:             <div class="list-item" style="margin-top:12px;">
43943:               <div class="list-item-title">${escapeHtml(specialistPlan.title || "Specialist plan")}</div>
43944:               <div class="list-item-sub">${escapeHtml(specialistPlan.objective || "")}</div>
43945:               <div class="badge-row">
43946:                 <span class="badge">Fields used ${escapeHtml(String(safeArray(specialistPlan.populated_fields).length))}</span>
43947:                 <span class="badge">Missing ${escapeHtml(String(safeArray(specialistPlan.missing_fields).length))}</span>
43948:                 <span class="badge">Preview only</span>
43949:               </div>
43950:             </div>
43951:           `
43952:           : `<div class="empty-state" style="margin-top:12px;">No ${escapeHtml(label)} specialist plan yet.</div>`
43953:       }
43954: 
43955:       ${
43956:         specialistTasks.length
43957:           ? `
43958:             <div class="list-wrap" style="margin-top:12px;">
43959:               ${specialistTasks.map((task) => `
43960:                 <div class="list-item">
43961:                   <div class="list-item-title">${escapeHtml(task.title || task.id || "Specialist task")}</div>
43962:                   <div class="list-item-sub">${escapeHtml(task.detail || "")}</div>
43963:                   <div class="badge-row">
43964:                     ${renderStatusBadge(task.status || "approved")}
43965:                     <span class="badge">${escapeHtml(task.safety || "internal_preview_only")}</span>
43966:                     <span class="badge">No live external action</span>
43967:                   </div>
43968:                 </div>
43969:               `).join("")}
43970:             </div>
43971:           `
43972:           : ""
43973:       }
43974: 
43975:       <div class="notice warning" style="margin-top:12px;">
43976:         Specialist Pilot expansion is still guarded. It creates internal plans, queues and previews only.
43977:       </div>
43978:     </section>
43979:   `;
43980: }
```

### Hit line 43990: `buildAionDepartmentPilotSpecialistDraft(planButton.getAttribute("data-aion-phase25f-build-specialist-plan"));`

```js
43990:       buildAionDepartmentPilotSpecialistDraft(planButton.getAttribute("data-aion-phase25f-build-specialist-plan"));
43991:       return;
43992:     }
43993: 
43994:     const queueButton = event.target?.closest?.("[data-aion-phase25f-build-specialist-queue]");
43995:     if (queueButton) {
```

### Hit line 43998: `buildAionDepartmentPilotSpecialistSafeQueue(queueButton.getAttribute("data-aion-phase25f-build-specialist-queue"));`

```js
43998:       buildAionDepartmentPilotSpecialistSafeQueue(queueButton.getAttribute("data-aion-phase25f-build-specialist-queue"));
43999:     }
44000:   }, true);
44001: }
44002: 
44003: if (typeof window !== "undefined") {
```

### Hit line 44004: `window.getAionDepartmentPilotSpecialistPlaybook = getAionDepartmentPilotSpecialistPlaybook;`

```js
44004:   window.getAionDepartmentPilotSpecialistPlaybook = getAionDepartmentPilotSpecialistPlaybook;
44005:   window.buildAionDepartmentPilotSpecialistDraft = buildAionDepartmentPilotSpecialistDraft;
44006:   window.buildAionDepartmentPilotSpecialistSafeQueue = buildAionDepartmentPilotSpecialistSafeQueue;
44007: }
44008: 
44009: 
44010: 
44011: /* PHASE 25G LOCK: Boardroom Cross-Department Review */
44012: 
44013: function classifyAionDepartmentCrossReviewState(entry = {}) {
```

### Hit line 44005: `window.buildAionDepartmentPilotSpecialistDraft = buildAionDepartmentPilotSpecialistDraft;`

```js
44005:   window.buildAionDepartmentPilotSpecialistDraft = buildAionDepartmentPilotSpecialistDraft;
44006:   window.buildAionDepartmentPilotSpecialistSafeQueue = buildAionDepartmentPilotSpecialistSafeQueue;
44007: }
44008: 
44009: 
44010: 
44011: /* PHASE 25G LOCK: Boardroom Cross-Department Review */
44012: 
44013: function classifyAionDepartmentCrossReviewState(entry = {}) {
```

### Hit line 44006: `window.buildAionDepartmentPilotSpecialistSafeQueue = buildAionDepartmentPilotSpecialistSafeQueue;`

```js
44006:   window.buildAionDepartmentPilotSpecialistSafeQueue = buildAionDepartmentPilotSpecialistSafeQueue;
44007: }
44008: 
44009: 
44010: 
44011: /* PHASE 25G LOCK: Boardroom Cross-Department Review */
44012: 
44013: function classifyAionDepartmentCrossReviewState(entry = {}) {
```

### Hit line 44723: `${renderAionDepartmentScopedPilotSurface("finance", selectedRuns, selectedAgentCard)}`

```js
44718: function renderFinanceWorkspaceSurface(selectedRuns, selectedAgentCard) {
44719:   return `
44720:     <div data-aion-finance-live-agents-workspace-v2="true">
44721:       ${renderAionRealFinance121BoardroomPanelV2()}
44722:       ${renderAionFinanceDataSetupPanelV2()}
44723:       ${renderAionDepartmentScopedPilotSurface("finance", selectedRuns, selectedAgentCard)}
44724:     </div>
44725:   `;
44726: }
```

### Hit line 44729: `return renderAionDepartmentScopedPilotSurface("sales", selectedRuns, selectedAgentCard);`

```js
44728: function renderSalesWorkspaceSurface(selectedRuns, selectedAgentCard) {
44729:   return renderAionDepartmentScopedPilotSurface("sales", selectedRuns, selectedAgentCard);
44730: }
```

### Hit line 44733: `return renderAionDepartmentScopedPilotSurface("operations", selectedRuns, selectedAgentCard);`

```js
44732: function renderOperationsWorkspaceSurface(selectedRuns, selectedAgentCard) {
44733:   return renderAionDepartmentScopedPilotSurface("operations", selectedRuns, selectedAgentCard);
44734: }
```

### Hit line 44737: `return renderAionDepartmentScopedPilotSurface("support", selectedRuns, selectedAgentCard);`

```js
44736: function renderSupportWorkspaceSurface(selectedRuns, selectedAgentCard) {
44737:   return renderAionDepartmentScopedPilotSurface("support", selectedRuns, selectedAgentCard);
44738: }
```

### Hit line 44902: `runtime.primaryAgent || getPrimaryDepartmentAgentCard(room.key);`

```js
44899: function renderMarketingDepartmentRoomCard(room, selectedAgentCard) {
44900:   const runtime = getDepartmentRuntime(room.key) || room;
44901:   const primaryCard =
44902:     runtime.primaryAgent || getPrimaryDepartmentAgentCard(room.key);
44903:   const isDepartmentSelected =
44904:     String(selectedAgentCard?.departmentKey || "").toLowerCase() ===
44905:     String((runtime.key || room.key || "")).toLowerCase();
44906: 
44907:   const latestRun = runtime.latestRun || primaryCard?.latestRun || null;
44908:   const latestRunId = latestRun?.id || latestRun?.queue_item_id || "";
44909:   const latestRunLabel = latestRun
44910:     ? runtimeShared.getRunWorkflowLabel(latestRun)
44911:     : "No recent workflow";
44912: 
44913:   return `
44914:     <div class="panel large-panel ${isDepartmentSelected ? "panel-selected" : ""}">
44915:       <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:12px;">
44916:         <div style="display:flex; gap:10px; align-items:center;">
44917:           <div style="
44918:             width:56px;
44919:             height:56px;
44920:             border-radius:13px;
44921:             border:1px solid rgba(148,163,184,0.22);
44922:             display:flex;
44923:             align-items:center;
44924:             justify-content:center;
44925:             font-weight:800;
44926:             font-size:18px;
44927:             background:linear-gradient(180deg, #f8fbff, #eef4fb);
44928:             color:#1e293b;
44929:             flex:0 0 auto;
44930:           ">M</div>
44931: 
44932:           <div>
44933:             <div class="panel-title" style="margin-bottom:4px;">${escapeHtml(runtime.label || room.label)}</div>
44934:             <div class="helper-text">
44935:               ${escapeHtml(runtime.agentCount ?? room.agentCount ?? 0)} agent(s) · ${escapeHtml(runtime.totalRuns ?? room.total ?? 0)} total runs
44936:             </div>
44937:           </div>
44938:         </div>
44939: 
44940:         ${renderStatusBadge(
44941:           runtime.running > 0
44942:             ? "running"
44943:             : runtime.waitingApproval > 0
44944:               ? "waiting_approval"
44945:               : runtime.failed > 0
44946:                 ? "failed"
44947:                 : runtime.completed > 0
44948:                   ? "completed"
44949:                   : "idle",
44950:         )}
44951:       </div>
44952: 
44953:       <div class="card-grid" style="margin-bottom:12px;">
44954:         ${renderDashboardMetricCard("Queued", runtime.queued ?? room.queued ?? 0, "Planning")}
44955:         ${renderDashboardMetricCard("Running", runtime.running ?? room.running ?? 0, "In progress")}
44956:         ${renderDashboardMetricCard("Review", runtime.waitingApproval ?? room.waitingApproval ?? 0, "Needs approval")}
44957:         ${renderDashboardMetricCard("Done", runtime.completed ?? room.completed ?? 0, "Completed")}
44958:       </div>
44959: 
44960:       <div class="list-wrap" style="margin-bottom:12px;">
44961:         <div class="list-item">
44962:           <div class="list-item-title">Latest activity</div>
44963:           <div class="list-item-sub">${escapeHtml(latestRunLabel)}</div>
44964:           <div class="badge-row">
44965:             ${renderStatusBadge(latestRun?.status || "unknown")}
44966:             <span class="badge">${escapeHtml(formatDateTime(latestRun?.updated_at || latestRun?.created_at))}</span>
44967:             <span class="badge">Approvals ${escapeHtml(runtime.pendingApprovals ?? 0)}</span>
44968:           </div>
44969:         </div>
44970:       </div>
44971: 
44972:       <div class="marketing-form-actions">
44973:         <button
44974:           class="secondary-btn live-department-open-btn"
44975:           data-department-key="${escapeHtml(runtime.key || room.key)}"
44976:           data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}"
44977:         >
44978:           Open workspace
44979:         </button>
44980:         <button
44981:           class="secondary-btn live-department-open-btn"
44982:           data-department-key="${escapeHtml(runtime.key || room.key)}"
44983:           data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}"
44984:         >
44985:           Stream
44986:         </button>
44987:         <button
44988:           class="secondary-btn live-department-open-btn"
44989:           data-department-key="${escapeHtml(runtime.key || room.key)}"
44990:           data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.CALENDAR)}"
44991:         >
44992:           Calendar
44993:         </button>
44994:         <button
44995:           class="secondary-btn live-department-open-btn"
44996:           data-department-key="${escapeHtml(runtime.key || room.key)}"
44997:           data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
44998:         >
44999:           Runs
45000:         </button>
45001:         <button
45002:           class="secondary-btn boardroom-open-approvals-btn"
45003:           data-department-key="${escapeHtml(runtime.key || room.key)}"
45004:         >
45005:           Approvals
45006:         </button>
45007:         ${
45008:           latestRunId
45009:             ? `
45010:               <button
45011:                 class="secondary-btn live-department-open-btn"
45012:                 data-department-key="${escapeHtml(runtime.key || room.key)}"
45013:                 data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
45014:                 data-open-replay="true"
45015:                 data-run-id="${escapeHtml(latestRunId)}"
45016:               >
45017:                 Replay
45018:               </button>
45019:             `
45020:             : ""
45021:         }
45022:       </div>
45023:     </div>
45024:   `;
45025: }
```

### Hit line 45030: `runtime.primaryAgent || getPrimaryDepartmentAgentCard(room.key);`

```js
45027: function renderGenericDepartmentRoomCard(room, selectedAgentCard) {
45028:   const runtime = getDepartmentRuntime(room.key) || room;
45029:   const primaryCard =
45030:     runtime.primaryAgent || getPrimaryDepartmentAgentCard(room.key);
45031:   const latestRun = runtime.latestRun || primaryCard?.latestRun || null;
45032:   const latestRunId = latestRun?.id || latestRun?.queue_item_id || "";
45033:   const latestLabel = latestRun
45034:     ? runtimeShared.getRunWorkflowLabel(latestRun)
45035:     : "No recent activity";
45036:   const isDepartmentSelected =
45037:     String(selectedAgentCard?.departmentKey || "").toLowerCase() ===
45038:     String((runtime.key || room.key || "")).toLowerCase();
45039: 
45040:   return `
45041:     <div class="panel large-panel ${isDepartmentSelected ? "panel-selected" : ""}">
45042:       <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:12px;">
45043:         <div>
45044:           <div class="panel-title" style="margin-bottom:4px;">${escapeHtml(runtime.label || room.label)}</div>
45045:           <div class="helper-text">
45046:             ${escapeHtml(runtime.agentCount ?? 0)} agent(s) · ${escapeHtml(runtime.totalRuns ?? 0)} total runs
45047:           </div>
45048:         </div>
45049: 
45050:         ${renderStatusBadge(
45051:           runtime.running > 0
45052:             ? "running"
45053:             : runtime.waitingApproval > 0
45054:               ? "waiting_approval"
45055:               : runtime.failed > 0
45056:                 ? "failed"
45057:                 : runtime.completed > 0
45058:                   ? "completed"
45059:                   : "idle",
45060:         )}
45061:       </div>
45062: 
45063:       <div class="badge-row" style="margin-bottom:12px;">
45064:         <span class="badge">Queued ${escapeHtml(runtime.queued ?? 0)}</span>
45065:         <span class="badge">Running ${escapeHtml(runtime.running ?? 0)}</span>
45066:         <span class="badge">Waiting ${escapeHtml(runtime.waitingApproval ?? 0)}</span>
45067:         <span class="badge">Failed ${escapeHtml(runtime.failed ?? 0)}</span>
45068:         <span class="badge">Approvals ${escapeHtml(runtime.pendingApprovals ?? 0)}</span>
45069:       </div>
45070: 
45071:       <div class="list-item" style="margin-bottom:12px;">
45072:         <div class="list-item-title">Latest activity</div>
45073:         <div class="list-item-sub">${escapeHtml(latestLabel)}</div>
45074:         <div class="badge-row">
45075:           ${renderStatusBadge(latestRun?.status || "unknown")}
45076:           <span class="badge">${escapeHtml(formatDateTime(latestRun?.updated_at || latestRun?.created_at))}</span>
45077:         </div>
45078:       </div>
45079: 
45080:       <div class="marketing-form-actions">
45081:         <button
45082:           class="secondary-btn live-department-open-btn"
45083:           data-department-key="${escapeHtml(runtime.key || room.key)}"
45084:           data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}"
45085:         >
45086:           Open workspace
45087:         </button>
45088: 
45089:         <button
45090:           class="secondary-btn live-department-open-btn"
45091:           data-department-key="${escapeHtml(runtime.key || room.key)}"
45092:           data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
45093:         >
45094:           Runs
45095:         </button>
45096: 
45097:         <button
45098:           class="secondary-btn boardroom-open-approvals-btn"
45099:           data-department-key="${escapeHtml(runtime.key || room.key)}"
45100:         >
45101:           Approvals
45102:         </button>
45103: 
45104:         ${
45105:           latestRunId
45106:             ? `
45107:               <button
45108:                 class="secondary-btn live-department-open-btn"
45109:                 data-department-key="${escapeHtml(runtime.key || room.key)}"
45110:                 data-live-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}"
45111:                 data-open-replay="true"
45112:                 data-run-id="${escapeHtml(latestRunId)}"
45113:               >
45114:                 Replay
45115:               </button>
45116:             `
45117:             : ""
45118:         }
45119:       </div>
45120:     </div>
45121:   `;
45122: }
```

### Hit line 45153: `function renderLiveAgentHero(selectedAgentCard) {`

```js
45153: function renderLiveAgentHero(selectedAgentCard) {
45154:   if (!selectedAgentCard) {
45155:     return `
45156:       <div class="panel large-panel">
45157:         <div class="panel-title">No agent selected</div>
45158:         <div class="empty-state">No live agent is available yet.</div>
45159:       </div>
45160:     `;
45161:   }
45162: 
45163:   const latestRun = selectedAgentCard.latestRun || null;
45164:   const departmentKey = String(selectedAgentCard.departmentKey || "").toLowerCase();
45165:   const showCalendar = departmentKey === "marketing";
45166: 
45167:   return `
45168:     <div class="panel large-panel">
45169:       <div style="display:flex; gap:10px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap;">
45170:         <div style="display:flex; gap:10px; align-items:center;">
45171:           <div style="
45172:             width:72px;
45173:             height:72px;
45174:             border-radius:20px;
45175:             border:1px solid rgba(148,163,184,0.25);
45176:             display:flex;
45177:             align-items:center;
45178:             justify-content:center;
45179:             font-weight:800;
45180:             font-size:22px;
45181:             background:linear-gradient(180deg, #f8fbff, #eef4fb);
45182:             color:#1e293b;
45183:           ">
45184:             ${escapeHtml(String(selectedAgentCard.label || "A").slice(0, 1).toUpperCase())}
45185:           </div>
45186: 
45187:           <div>
45188:             <div class="surface-eyebrow">Agent Workspace</div>
45189:             <div class="surface-title" style="font-size:34px;">${escapeHtml(selectedAgentCard.label)}</div>
45190:             <div class="surface-subtitle">
45191:               ${escapeHtml(runtimeShared.getDepartmentLabel(selectedAgentCard.departmentKey || "unknown"))} · ${escapeHtml(selectedAgentCard.total)} total runs
45192:             </div>
45193:             <div class="badge-row" style="margin-top:10px;">
45194:               <span class="badge">Queued ${escapeHtml(selectedAgentCard.queued)}</span>
45195:               <span class="badge">Running ${escapeHtml(selectedAgentCard.running)}</span>
45196:               <span class="badge">Waiting ${escapeHtml(selectedAgentCard.waitingApproval)}</span>
45197:               <span class="badge">Failed ${escapeHtml(selectedAgentCard.failed)}</span>
45198:               <span class="badge">Last active ${escapeHtml(formatDateTime(latestRun?.updated_at || latestRun?.created_at))}</span>
45199:             </div>
45200:           </div>
45201:         </div>
45202: 
45203:         <div class="marketing-form-actions">
45204:           <button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.STREAM)}">View Stream</button>
45205:           ${
45206:             showCalendar
45207:               ? `<button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.CALENDAR)}">Open Calendar<`
45208:               : ""
45209:           }
45210:           <button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.RUNS)}">Runs</button>
45211:           <button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.APPROVALS)}">Approvals</button>
45212:           <button class="secondary-btn live-agents-view-btn" data-live-agents-view="${escapeHtml(LIVE_AGENT_VIEWS.SETTINGS)}">Settings</button>
45213:         </div>
45214:       </div>
45215:     </div>
45216:   `;
45217: }
```

### Hit line 45653: `${renderAionDepartmentScopedPilotSurface("marketing", selectedRuns, selectedAgentCard)}`

```js
45614: function renderPilotMarketingWorkspaceSurface(selectedRuns, selectedAgentCard) {
45615:   const artifacts = getAionPilotMarketingWorkspaceArtifacts();
45616:   const groupedArtifacts = groupAionPilotMarketingArtifacts(artifacts);
45617:   const pilotState = getAionPilotFrontendInteractionState();
45618: 
45619:   const groupedHtml = groupedArtifacts.length
45620:     ? groupedArtifacts.map((group) => `
45621:         <section
45622:           data-aion-phase23z-pilot-marketing-deliverable-group
45623:           style="
45624:             display:grid;
45625:             gap:10px;
45626:             margin-top:16px;
45627:           "
45628:         >
45629:           <div style="
45630:             font-size:12px;
45631:             font-weight:800;
45632:             letter-spacing:0.12em;
45633:             text-transform:uppercase;
45634:             color:rgba(15,23,42,0.62);
45635:           ">
45636:             ${escapeHtml(group.group)}
45637:           </div>
45638: 
45639:           <div class="list-wrap">
45640:             ${group.artifacts.map((item) => renderAionPilotMarketingArtifactCard(item)).join("")}
45641:           </div>
45642:         </section>
45643:       `).join("")
45644:     : `
45645:       <div class="empty-state" data-aion-phase23y-pilot-marketing-empty>
45646:         No Pilot-generated marketing artifacts yet. Run a Pilot marketing mission, then continue safe work.
45647:       </div>
45648:     `;
45649: 
45650:   return `
45651:     <div data-aion-phase23y-pilot-marketing-workspace>
45652:       ${renderLiveAgentsMarketingWorkspaceTabs()}
45653:       ${renderAionDepartmentScopedPilotSurface("marketing", selectedRuns, selectedAgentCard)}
45654: 
45655:       <div class="panel large-panel" style="background:#ffffff;">
45656:         <div class="panel-title">Pilot Marketing workspace</div>
45657:         <div class="helper-text">
45658:           Marketing work generated by Pilot missions is grouped here into strategy, messaging, channel plan, lead flow, content assets and approval-blocked live actions.
45659:         </div>
45660: 
45661:         <div class="badge-row" style="margin-top:10px;">
45662:           <span class="badge">Pilot status ${escapeHtml(pilotState.status || "idle")}</span>
45663:           <span class="badge">Safe work ${escapeHtml(pilotState.safe_work_status || "idle")}</span>
45664:           <span class="badge">Artifacts ${escapeHtml(artifacts.length)}</span>
45665:           <span class="badge">Groups ${escapeHtml(groupedArtifacts.length)}</span>
45666:         </div>
45667: 
45668:         ${groupedHtml}
45669:       </div>
45670: 
45671:       <!-- Phase 25C-F panels are already mounted inside renderAionDepartmentScopedPilotSurface("marketing"). -->
45672:     </div>
45673:   `;
45674: }
```

### Hit line 45871: `function renderLiveAgentStreamView(selectedRuns, selectedAgentCard) {`

```js
45871: function renderLiveAgentStreamView(selectedRuns, selectedAgentCard) {
45872:   const completedRuns = selectedRuns
45873:     .filter((run) => run?.status === "completed")
45874:     .slice()
45875:     .sort((a, b) => {
45876:       const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
45877:       const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
45878:       return bTime - aTime;
45879:     });
45880: 
45881:   const waitingApprovalRuns = selectedRuns
45882:     .filter((run) => run?.status === "waiting_approval")
45883:     .slice()
45884:     .sort((a, b) => {
45885:       const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
45886:       const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
45887:       return bTime - aTime;
45888:     });
45889: 
45890:   const inProgressRuns = selectedRuns
45891:     .filter(
45892:       (run) => run?.status === "queued" || run?.status === "running",
45893:     )
45894:     .slice()
45895:     .sort((a, b) => {
45896:       const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
45897:       const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
45898:       return bTime - aTime;
45899:     });
45900: 
45901:   const selectedRun = findSelectedLiveRun();
45902:   const activeStreamTab = ["approval", "progress", "completed"].includes(
45903:     String(state.liveAgentsStreamTab || "approval").toLowerCase(),
45904:   )
45905:     ? String(state.liveAgentsStreamTab || "approval").toLowerCase()
45906:     : "approval";
45907: 
45908:   const streamTabs = [
45909:     {
45910:       key: "approval",
45911:       label: "Waiting on Approval",
45912:       count: waitingApprovalRuns.length,
45913:     },
45914:     {
45915:       key: "progress",
45916:       label: "Work in Progress",
45917:       count: inProgressRuns.length,
45918:     },
45919:     {
45920:       key: "completed",
45921:       label: "Completed Content",
45922:       count: completedRuns.length,
45923:     },
45924:   ];
45925: 
45926:   let streamTitle = "Waiting on Approval";
45927:   let streamEmpty = "No items waiting on approval right now.";
45928:   let visibleRuns = waitingApprovalRuns;
45929: 
45930:   if (activeStreamTab === "progress") {
45931:     streamTitle = "Work in Progress";
45932:     streamEmpty = "No queued or running work right now.";
45933:     visibleRuns = inProgressRuns;
45934:   } else if (activeStreamTab === "completed") {
45935:     streamTitle = "Completed Content";
45936:     streamEmpty = "No completed content yet for this agent.";
45937:     visibleRuns = completedRuns;
45938:   }
45939: 
45940:   return `
45941:     <div>
45942:       <div style="
45943:         display:flex;
45944:         gap:24px;
45945:         align-items:center;
45946:         flex-wrap:wrap;
45947:         margin-bottom:10px;
45948:       ">
45949:         ${streamTabs
45950:           .map((tab) => {
45951:             const isActive = activeStreamTab === tab.key;
45952:             return `
45953:               <button
45954:                 type="button"
45955:                 data-live-agents-stream-tab="${escapeHtml(tab.key)}"
45956:                 style="
45957:                   appearance:none;
45958:                   -webkit-appearance:none;
45959:                   border:0;
45960:                   border-bottom:${isActive ? "2px" : "1px"} solid #111111;
45961:                   background:transparent;
45962:                   color:${isActive ? "#111111" : "rgba(17,17,17,0.62)"};
45963:                   padding:0 0 4px 0;
45964:                   font-size:12px;
45965:                   font-weight:${isActive ? "700" : "600"};
45966:                   cursor:pointer;
45967:                 "
45968:               >
45969:                 ${escapeHtml(tab.label)}${tab.count ? ` <span style="opacity:0.7;">(${escapeHtml(tab.count)})</span>` : ""}
45970:               </button>
45971:             `;
45972:           })
45973:           .join("")}
45974:       </div>
45975: 
45976:       <div class="panel large-panel">
45977:         <div class="panel-title">${escapeHtml(streamTitle)}</div>
45978:         ${
45979:           visibleRuns.length
45980:             ? activeStreamTab === "completed"
45981:               ? `<div class="marketing-runs-grid">${visibleRuns
45982:                   .map((run) => renderMarketingRunCard(run))
45983:                   .join("")}</div>`
45984:               : `<div class="list-wrap">${visibleRuns
45985:                   .map((run) => renderLiveAgentRunRow(run))
45986:                   .join("")}</div>`
45987:             : `<div class="empty-state">${escapeHtml(streamEmpty)}</div>`
45988:         }
45989:       </div>
45990:     </div>
45991: 
45992:     <div style="margin-top:16px;">
45993:       ${renderSelectedRunInspector(selectedRun)}
45994:     </div>
45995:   `;
45996: }
```

### Hit line 46474: `function renderLiveAgentRunsView(selectedRuns, selectedAgentCard) {`

```js
46474: function renderLiveAgentRunsView(selectedRuns, selectedAgentCard) {
46475:   const sortedRuns = selectedRuns
46476:     .slice()
46477:     .sort((a, b) => {
46478:       const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
46479:       const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
46480:       return bTime - aTime;
46481:     });
46482: 
46483:   const selectedRun = findSelectedLiveRun();
46484:   const visibleRuns = sortedRuns.slice(0, 8);
46485: 
46486:   return `
46487:     <div class="dashboard-shell" style="
46488:       display:grid;
46489:       gap:10px;
46490:       width:100%;
46491:     ">
46492:       <div style="width:100%;">
46493:         ${renderSelectedRunInspector(selectedRun)}
46494:       </div>
46495: 
46496:       <div class="panel large-panel" style="
46497:         width:100%;
46498:         box-sizing:border-box;
46499:       ">
46500:         <div style="
46501:           display:flex;
46502:           align-items:flex-start;
46503:           justify-content:space-between;
46504:           gap:10px;
46505:           flex-wrap:wrap;
46506:           margin-bottom:12px;
46507:         ">
46508:           <div>
46509:             <div class="panel-title">Run history</div>
46510:             <div class="helper-text">
46511:               Showing latest ${escapeHtml(Math.min(visibleRuns.length, sortedRuns.length))} of ${escapeHtml(sortedRuns.length)} run(s).
46512:             </div>
46513:           </div>
46514: 
46515:           <div class="badge-row">
46516:             <span class="badge">Agent ${escapeHtml(selectedAgentCard?.label || "—")}</span>
46517:             <span class="badge">Total ${escapeHtml(sortedRuns.length)}</span>
46518:           </div>
46519:         </div>
46520: 
46521:         ${
46522:           visibleRuns.length
46523:             ? `
46524:               <div class="list-wrap" style="
46525:                 display:grid;
46526:                 grid-template-columns:repeat(auto-fit, minmax(260px, 1fr));
46527:                 gap:10px;
46528:               ">
46529:                 ${visibleRuns.map((run) => renderLiveAgentRunRow(run)).join("")}
46530:               </div>
46531:             `
46532:             : `<div class="empty-state">No runs for this agent yet.</div>`
46533:         }
46534:       </div>
46535:     </div>
46536:   `;
46537: }
```

### Hit line 46539: `function renderLiveAgentSettingsView(selectedAgentCard) {`

```js
46539: function renderLiveAgentSettingsView(selectedAgentCard) {
46540:   return `
46541:     <div class="two-col">
46542:       <div class="panel large-panel">
46543:         <div class="panel-title">Agent settings</div>
46544:         <div class="list-wrap">
46545:           <div class="list-item">
46546:             <div class="list-item-title">Agent identity</div>
46547:             <div class="list-item-sub">${escapeHtml(selectedAgentCard?.label || "—")}</div>
46548:           </div>
46549:           <div class="list-item">
46550:             <div class="list-item-title">Department</div>
46551:             <div class="list-item-sub">${escapeHtml(selectedAgentCard?.departmentKey || "—")}</div>
46552:           </div>
46553:           <div class="list-item">
46554:             <div class="list-item-title">Persona image</div>
46555:             <div class="list-item-sub">Next pass: add avatar/headshot upload or generated persona art.</div>
46556:           </div>
46557:           <div class="list-item">
46558:             <div class="list-item-title">Compliance</div>
46559:             <div class="list-item-sub">Keep compliance history behind run-level inspect, not main agent view.</div>
46560:           </div>
46561:         </div>
46562:       </div>
46563: 
46564:       <div class="panel large-panel">
46565:         <div class="panel-title">Workspace notes</div>
46566:         <div class="helper-text">
46567:           This screen is moving from queue-monitoring into agent-office mode:
46568:           stream, calendar, approvals, runs, settings.
46569:         </div>
46570:       </div>
46571:     </div>
46572:   `;
46573: }
```

### Hit line 46729: `function renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard) {`

```js
46729: function renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard) {
46730:   const activeView = getLiveAgentsView();
46731:   const departmentKey = getSelectedLiveDepartmentKey();
46732: 
46733:   /*
46734:    * PHASE 25J HOTFIX:
46735:    * The Live Agents department tab is the source of truth for department scope.
46736:    * Do not let a stale selectedAgentCard from another department render Finance inside Marketing,
46737:    * Sales inside Operations, etc.
46738:    */
46739:   const scopedSelectedAgentCard =
46740:     selectedAgentCard && typeof selectedAgentCard === "object"
46741:       ? {
46742:           ...selectedAgentCard,
46743:           departmentKey,
46744:           department: departmentKey,
46745:         }
46746:       : selectedAgentCard;
46747: 
46748:   if (departmentKey === "aion") {
46749:     if (activeView === LIVE_AGENT_VIEWS.APPROVALS) {
46750:       return renderDepartmentApprovalsSurface(departmentKey, scopedSelectedAgentCard);
46751:     }
46752: 
46753:     return renderAionWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);
46754:   }
46755: 
46756:   if (departmentKey === "pilot") {
46757:     if (activeView === LIVE_AGENT_VIEWS.APPROVALS) {
46758:       return renderDepartmentApprovalsSurface(departmentKey, scopedSelectedAgentCard);
46759:     }
46760: 
46761:     return renderAionWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);
46762:   }
46763: 
46764:   if (activeView === LIVE_AGENT_VIEWS.APPROVALS) {
46765:     return renderDepartmentApprovalsSurface(departmentKey, scopedSelectedAgentCard);
46766:   }
46767: 
46768:   if (departmentKey === "marketing") {
46769:     if (activeView === LIVE_AGENT_VIEWS.CALENDAR) {
46770:       return renderLiveAgentCalendarView(selectedRuns, scopedSelectedAgentCard);
46771:     }
46772: 
46773:     if (activeView === LIVE_AGENT_VIEWS.RUNS) {
46774:       return renderLiveAgentRunsView(selectedRuns, scopedSelectedAgentCard);
46775:     }
46776: 
46777:     if (activeView === LIVE_AGENT_VIEWS.SETTINGS) {
46778:       return renderLiveAgentSettingsView(scopedSelectedAgentCard);
46779:     }
46780: 
46781:     if (getLiveAgentsMarketingWorkspaceMode() === "manual") {
46782:       return renderMarketingManualWorkspaceSurface();
46783:     }
46784: 
46785:     return renderPilotMarketingWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);
46786:   }
46787: 
46788:   if (activeView === LIVE_AGENT_VIEWS.SETTINGS) {
46789:     return renderLiveAgentSettingsView(scopedSelectedAgentCard);
46790:   }
46791: 
46792:   if (activeView === LIVE_AGENT_VIEWS.RUNS) {
46793:     return renderLiveAgentRunsView(selectedRuns, scopedSelectedAgentCard);
46794:   }
46795: 
46796:   if (departmentKey === "finance") {
46797:     return renderFinanceWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);
46798:   }
46799: 
46800:   if (departmentKey === "sales") {
46801:     return renderSalesWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);
46802:   }
46803: 
46804:   if (departmentKey === "operations") {
46805:     return renderOperationsWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);
46806:   }
46807: 
46808:   if (departmentKey === "support") {
46809:     return renderSupportWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);
46810:   }
46811: 
46812:   if (departmentKey === "builder") {
46813:     return renderGenericDepartmentWorkspaceSurface("builder", selectedAgentCard);
46814:   }
46815: 
46816:   return renderGenericDepartmentWorkspaceSurface(departmentKey, selectedAgentCard);
46817: }
```

### Hit line 46969: `${renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard)}`

```js
46917: function renderLiveAgentsSurface() {
46918:   if (typeof document !== "undefined") {
46919:     document.documentElement.style.background = "#ffffff";
46920:     document.body.style.background = "#ffffff";
46921:     document.body.classList.add("aion-phase23y-live-agents-white");
46922:     const appRoot = document.getElementById("app");
46923:     if (appRoot) {
46924:       appRoot.style.background = "#ffffff";
46925:       appRoot.style.backgroundColor = "#ffffff";
46926:     }
46927:   }
46928: 
46929:   const selectedRuns = getRunsForSelectedLiveAgent();
46930:   const selectedAgentCard = getSelectedLiveAgentCard();
46931:   const departmentKey = getSelectedLiveDepartmentKey();
46932:   const departmentLabel = runtimeShared.getDepartmentLabel(departmentKey);
46933: 
46934:   return `
46935:     <div
46936:       class="surface-shell aion-phase23y-live-agents-white-shell"
46937:       style="min-height:100vh; padding-bottom:96px; background:#ffffff; background-color:#ffffff;"
46938:     >
46939:       <div class="surface-header surface-header-unified">
46940:         <div class="surface-header-unified-top">
46941:           <div class="surface-header-unified-main">
46942:             <div class="surface-eyebrow">Aion Business Desktop</div>
46943:             <div class="surface-title">Live Agents</div>
46944:             <div class="surface-subtitle">
46945:               Minimal local command surface for department agents.
46946:             </div>
46947:           </div>
46948:         </div>
46949:       </div>
46950: 
46951:       ${renderAppTabs()}
46952:       ${renderMinimalDepartmentSwitcher()}
46953:       ${renderLiveAgentsSubviewTabs()}
46954: 
46955:       <div class="dashboard-shell">
46956:         <div class="live-agents-workspace-meta">
46957:           <div class="live-agents-workspace-copy">
46958:             <div class="surface-eyebrow">Workspace</div>
46959:             <div class="live-agents-workspace-title">
46960:               ${escapeHtml(selectedAgentCard?.label || departmentLabel)}
46961:             </div>
46962:             <div class="live-agents-workspace-sub">
46963:               ${escapeHtml(departmentLabel)} · ${escapeHtml(selectedAgentCard?.total || 0)} total runs
46964:             </div>
46965:           </div>
46966: 
46967:         </div>
46968: 
46969:         ${renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard)}
46970:       </div>
46971: 
46972:       ${renderLiveAgentsPersistentPilotTerminal()}
46973:     </div>
46974:   `;
46975: }
```

### Hit line 50654: `setLiveAgentsWorkspace(departmentKey, {`

```js
50654:         setLiveAgentsWorkspace(departmentKey, {
50655:           preferredView,
50656:           openReplay,
50657:           runId,
50658:         });
```

### Hit line 118092: `function buildAllDepartmentPilotTaskPacketsO13C() {`

```js
118092:   function buildAllDepartmentPilotTaskPacketsO13C() {
118093:     const departmentSheets = getDepartmentSheetsO13C();
118094: 
118095:     const packetsByDepartment = {};
118096:     const allPackets = [];
118097: 
118098:     DEPARTMENT_ORDER.forEach((department) => {
118099:       const sheet = departmentSheets[department];
118100:       if (!sheet) {
118101:         packetsByDepartment[department] = [];
118102:         return;
118103:       }
118104: 
118105:       const packets = buildPilotTaskPacketsForDepartmentSheetO13C({
118106:         ...sheet,
118107:         department,
118108:       });
118109: 
118110:       packetsByDepartment[department] = packets;
118111:       allPackets.push(...packets);
118112:     });
118113: 
118114:     const queue = {
118115:       queue_id: `goal_sheet_pilot_queue_${Date.now().toString(36)}`,
118116:       created_at: nowIsoO13C(),
118117:       source: "department_goal_sheets",
118118:       business_container: getBusinessContainerO13C(window.__aionWorkflowGraph),
118119:       preview_only: true,
118120:       approval_required: true,
118121:       execution_allowed_now: false,
118122:       connector_call_required: false,
118123:       external_side_effects: false,
118124:       creates_second_canvas: false,
118125:       creates_second_pilot: false,
118126:       queue_state: "staged_preview",
118127:       departments: DEPARTMENT_ORDER,
118128:       packets_by_department: packetsByDepartment,
118129:       packets: allPackets,
118130:       packet_count: allPackets.length,
118131:       central_pilot_handoff: {
118132:         visible_in_existing_central_pilot: true,
118133:         existing_central_pilot_reused: true,
118134:         queue_state: "staged_preview",
118135:         approval_required: true,
118136:       },
118137:       department_pilot_handoff: {
118138:         visible_in_existing_department_pilots: true,
118139:         existing_department_pilots_reused: true,
118140:         departments: DEPARTMENT_ORDER,
118141:       },
118142:     };
118143: 
118144:     window.__aionGoalSheetPilotTaskQueueO13C = queue;
118145:     window.__aionGoalLoopPilotQueuePreview = queue;
118146:     window.__aionCentralPilotGoalSheetTaskQueuePreview = queue;
118147: 
118148:     console.info("[AION] O13C built department Goal Sheet Pilot task queue", {
118149:       packet_count: queue.packet_count,
118150:       departments: queue.departments,
118151:       preview_only: queue.preview_only,
118152:     });
118153: 
118154:     return queue;
118155:   }
```

### Hit line 118157: `function buildActiveDepartmentPilotTaskPacketsO13C() {`

```js
118157:   function buildActiveDepartmentPilotTaskPacketsO13C() {
118158:     const activeSheet = getActiveDepartmentSheetO13C();
118159:     if (!activeSheet) return null;
118160: 
118161:     const department = normaliseDepartmentO13C(activeSheet.department, activeSheet);
118162:     const packets = buildPilotTaskPacketsForDepartmentSheetO13C({
118163:       ...activeSheet,
118164:       department,
118165:     });
118166: 
118167:     const queue = {
118168:       queue_id: `goal_sheet_${department}_pilot_queue_${Date.now().toString(36)}`,
118169:       created_at: nowIsoO13C(),
118170:       source: "active_department_goal_sheet",
118171:       business_container: getBusinessContainerO13C(activeSheet),
118172:       preview_only: true,
118173:       approval_required: true,
118174:       execution_allowed_now: false,
118175:       connector_call_required: false,
118176:       external_side_effects: false,
118177:       creates_second_canvas: false,
118178:       creates_second_pilot: false,
118179:       queue_state: "staged_preview",
118180:       department,
118181:       department_label: DEPARTMENT_LABELS[department],
118182:       packets,
118183:       packet_count: packets.length,
118184:       central_pilot_handoff: {
118185:         visible_in_existing_central_pilot: true,
118186:         existing_central_pilot_reused: true,
118187:         queue_state: "staged_preview",
118188:       },
118189:       department_pilot_handoff: {
118190:         visible_in_existing_department_pilot: true,
118191:         existing_department_pilot_reused: true,
118192:         department,
118193:         pilot_surface: `live_agents.${department}`,
118194:       },
118195:     };
118196: 
118197:     window.__aionGoalSheetActiveDepartmentPilotTaskQueueO13C = queue;
118198:     window.__aionGoalLoopPilotQueuePreview = queue;
118199: 
118200:     console.info("[AION] O13C built active department Pilot task queue", {
118201:       department,
118202:       packet_count: queue.packet_count,
118203:       preview_only: queue.preview_only,
118204:     });
118205: 
118206:     return queue;
118207:   }
```

### Hit line 118283: `buildActiveDepartmentPilotTaskPacketsO13C();`

```js
118265:   function syncPilotTaskPacketToolbarO13C() {
118266:     ensurePilotTaskPacketToolbarO13C();
118267: 
118268:     const toolbar = document.getElementById("aion-o13c-pilot-task-toolbar");
118269:     if (!toolbar) return;
118270: 
118271:     const graph = window.__aionWorkflowGraph || {};
118272:     toolbar.setAttribute("data-visible", isDepartmentGoalSheetO13C(graph) ? "true" : "false");
118273:   }
```

### Hit line 118298: `window.aionBuildAllDepartmentPilotTaskPacketsO13C = buildAllDepartmentPilotTaskPacketsO13C;`

```js
118288:     const wrapped = function renderWithO13CPilotToolbar(...args) {
118289:       const result = originalRender.apply(this, args);
118290:       window.setTimeout(syncPilotTaskPacketToolbarO13C, 0);
118291:       return result;
118292:     };
```

### Hit line 118339: `if (!queue && typeof window.aionBuildAllDepartmentPilotTaskPacketsO13C === "function") {`

```js
118332:   function ensurePilotQueueO13D() {
118333:     let queue =
118334:       window.__aionGoalLoopPilotQueuePreview ||
118335:       window.__aionGoalSheetPilotTaskQueueO13C ||
118336:       window.__aionCentralPilotGoalSheetTaskQueuePreview ||
118337:       null;
118338: 
118339:     if (!queue && typeof window.aionBuildAllDepartmentPilotTaskPacketsO13C === "function") {
118340:       queue = window.aionBuildAllDepartmentPilotTaskPacketsO13C();
118341:     }
118342: 
118343:     if (!queue) {
118344:       queue = {
118345:         queue_id: `goal_sheet_empty_pilot_queue_${Date.now().toString(36)}`,
118346:         created_at: nowIsoO13D(),
118347:         source: "empty_goal_sheet_preview",
118348:         preview_only: true,
118349:         approval_required: true,
118350:         execution_allowed_now: false,
118351:         connector_call_required: false,
118352:         external_side_effects: false,
118353:         queue_state: "staged_preview",
118354:         departments: DEPARTMENT_ORDER,
118355:         packets_by_department: Object.fromEntries(DEPARTMENT_ORDER.map((department) => [department, []])),
118356:         packets: [],
118357:         packet_count: 0,
118358:       };
118359:     }
118360: 
118361:     queue.preview_only = true;
118362:     queue.approval_required = true;
118363:     queue.execution_allowed_now = false;
118364:     queue.connector_call_required = false;
118365:     queue.external_side_effects = false;
118366:     queue.queue_state = "staged_preview";
118367: 
118368:     window.__aionGoalLoopPilotQueuePreview = queue;
118369:     window.__aionGoalSheetPilotTaskQueueO13C = queue;
118370:     window.__aionCentralPilotGoalSheetTaskQueuePreview = queue;
118371: 
118372:     return queue;
118373:   }
```

### Hit line 118449: `window.__aionExistingDepartmentPilotPreviewQueues = state.departments;`

```js
118375:   function buildPilotPreviewStateO13D(queueInput) {
118376:     const queue = queueInput || ensurePilotQueueO13D();
118377:     const packets = Array.isArray(queue.packets) ? queue.packets : [];
118378:     const byDepartment = queue.packets_by_department || {};
118379: 
118380:     const departmentStates = {};
118381: 
118382:     DEPARTMENT_ORDER.forEach((department) => {
118383:       const departmentPackets = Array.isArray(byDepartment[department])
118384:         ? byDepartment[department]
118385:         : packets.filter((packet) => String(packet.department || "").toLowerCase() === department);
118386: 
118387:       departmentStates[department] = {
118388:         department,
118389:         label: DEPARTMENT_LABELS[department],
118390:         pilot_id: `${department}_pilot`,
118391:         surface_id: `live_agents.${department}`,
118392:         page_status: "preview_queue_ready",
118393:         dummy_page_replacement_state: "receiving_goal_sheet_preview_tasks",
118394:         preview_only: true,
118395:         approval_required: true,
118396:         execution_allowed_now: false,
118397:         connector_call_required: false,
118398:         external_side_effects: false,
118399:         task_count: departmentPackets.length,
118400:         tasks: departmentPackets,
118401:         run_state_counts: departmentPackets.reduce((counts, packet) => {
118402:           const state = String(packet.run_state || "staged_preview");
118403:           counts[state] = (counts[state] || 0) + 1;
118404:           return counts;
118405:         }, {}),
118406:         evidence_pending_count: departmentPackets.filter((packet) => packet.evidence_required !== false).length,
118407:       };
118408:     });
118409: 
118410:     const state = {
118411:       state_id: `goal_sheet_live_agents_preview_${Date.now().toString(36)}`,
118412:       created_at: nowIsoO13D(),
118413:       source: "goal_sheet_pilot_task_queue",
118414:       queue_id: queue.queue_id,
118415:       preview_only: true,
118416:       approval_required: true,
118417:       execution_allowed_now: false,
118418:       connector_call_required: false,
118419:       external_side_effects: false,
118420:       no_live_agent_execution: true,
118421:       no_connector_calls: true,
118422:       no_customer_messages: true,
118423:       central_pilot: {
118424:         pilot_id: "central_pilot",
118425:         surface_id: "live_agents.central_pilot",
118426:         page_status: "preview_queue_ready",
118427:         role: "coordinator_guarded_executor",
118428:         existing_central_pilot_reused: true,
118429:         preview_only: true,
118430:         approval_required: true,
118431:         execution_allowed_now: false,
118432:         task_count: packets.length,
118433:         tasks: packets,
118434:         department_summary: Object.fromEntries(
118435:           DEPARTMENT_ORDER.map((department) => [
118436:             department,
118437:             departmentStates[department].task_count,
118438:           ])
118439:         ),
118440:       },
118441:       departments: departmentStates,
118442:       packets,
118443:       packet_count: packets.length,
118444:       queue,
118445:     };
118446: 
118447:     window.__aionLiveAgentsPilotPreviewStateO13D = state;
118448:     window.__aionExistingCentralPilotPreviewQueue = state.central_pilot;
118449:     window.__aionExistingDepartmentPilotPreviewQueues = state.departments;
118450:     window.__aionLiveAgentsGoalSheetPreviewTasks = packets;
118451: 
118452:     return state;
118453:   }
```

### Hit line 118763: `const originalBuildAll = window.aionBuildAllDepartmentPilotTaskPacketsO13C;`

```js
118717:   function publishPilotPreviewStateO13D() {
118718:     const queue = ensurePilotQueueO13D();
118719:     const state = buildPilotPreviewStateO13D(queue);
118720: 
118721:     try {
118722:       document.dispatchEvent(new CustomEvent("aion:goal-sheet-pilot-preview-state", { detail: state }));
118723:       window.dispatchEvent(new CustomEvent("aion:goal-sheet-pilot-preview-state", { detail: state }));
118724:     } catch {}
118725: 
118726:     return state;
118727:   }
```

### Hit line 118765: `const wrappedBuildAll = function wrappedBuildAllDepartmentPilotTaskPacketsO13D(...args) {`

```js
118765:     const wrappedBuildAll = function wrappedBuildAllDepartmentPilotTaskPacketsO13D(...args) {
118766:       const queue = originalBuildAll.apply(this, args);
118767:       const state = buildPilotPreviewStateO13D(queue);
118768:       renderPilotPreviewPanelO13D(state);
118769:       return queue;
118770:     };
```

### Hit line 118777: `const wrappedBuildActive = function wrappedBuildActiveDepartmentPilotTaskPacketsO13D(...args) {`

```js
118777:     const wrappedBuildActive = function wrappedBuildActiveDepartmentPilotTaskPacketsO13D(...args) {
118778:       const queue = originalBuildActive.apply(this, args);
118779:       const state = buildPilotPreviewStateO13D(queue || undefined);
118780:       renderPilotPreviewPanelO13D(state);
118781:       return queue;
118782:     };
```

### Hit line 119134: `function openDepartmentPilotFromQueueO13E(department) {`

```js
119134:   function openDepartmentPilotFromQueueO13E(department) {
119135:     window.__aionPreferredLiveAgentDepartment = department;
119136:     window.__aionLiveAgentsFocusDepartment = department;
119137:     window.__aionLiveAgentsSelectedTab = department;
119138: 
119139:     try {
119140:       if (typeof setLiveAgentsWorkspace === "function") {
119141:         setLiveAgentsWorkspace(department, {
119142:           view: "stream",
119143:           openReplay: false,
119144:           source: "goal_sheet_pilot_queue",
119145:         });
119146:       }
119147:     } catch (error) {
119148:       console.warn("[AION] O13E setLiveAgentsWorkspace failed", error);
119149:     }
119150: 
119151:     try {
119152:       if (typeof requestRender === "function") requestRender();
119153:       else if (typeof window.requestRender === "function") window.requestRender();
119154:     } catch {}
119155: 
119156:     return department;
119157:   }
```

### Hit line 119160: `if (typeof renderLiveAgentsWorkspaceBody !== "function") {`

```js
119159:   function wrapLiveAgentsWorkspaceBodyO13E() {
119160:     if (typeof renderLiveAgentsWorkspaceBody !== "function") {
119161:       console.warn("[AION] O13E renderLiveAgentsWorkspaceBody not found yet");
119162:       return false;
119163:     }
119164: 
119165:     if (renderLiveAgentsWorkspaceBody.__aionO13EWrapped === true) return true;
119166: 
119167:     const original = renderLiveAgentsWorkspaceBody;
119168: 
119169:     renderLiveAgentsWorkspaceBody = function renderLiveAgentsWorkspaceBodyWithGoalSheetQueue(selectedRuns, selectedAgentCard) {
119170:       ensureStylesO13E();
119171: 
119172:       const originalHtml = original.call(this, selectedRuns, selectedAgentCard);
119173:       const queueHtml = renderLiveAgentsGoalSheetPilotQueuePanelO13E(selectedRuns, selectedAgentCard);
119174: 
119175:       return `${queueHtml}${originalHtml}`;
119176:     };
119177: 
119178:     renderLiveAgentsWorkspaceBody.__aionO13EWrapped = true;
119179:     renderLiveAgentsWorkspaceBody.__aionO13EOriginal = original;
119180: 
119181:     return true;
119182:   }
```

## High-confidence function names

- `activateAionPilotRevisionCommandContext`
- `activePilotDepartmentScope`
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
- `closeAionPilotOutputPanel`
- `closeAionPilotStepOutput`
- `closeDepartmentChooserO13B`
- `closePilotPreviewPanelO13D`
- `collectAionDepartmentPilotDiscoveryFromForm`
- `createAionPilotFrontendDraftMission`
- `crossDepartmentReview`
- `deriveAionPilotFollowOnWorkItems`
- `detectSelectedDepartmentO13E`
- `downloadAionPilotOutputPreview`
- `ensureAionPhase23YLiveAgentsWhiteSurfaceStyles`
- `ensureDepartmentSheetRegistryO13B`
- `ensureLiveAgentSelection`
- `ensurePilotQueueO13D`
- `ensurePilotTaskPacketToolbarO13C`
- `executeAndAppendAionPilotMissionMapStepOutput`
- `extractAionPilotReplacementOperation`
- `fetchAionLrmPilotContextPreviewIntoPilotState`
- `fetchAionPilotArtifactPreviewIntoPilotState`
- `fetchAionPilotExecuteSafeStep`
- `fetchAionPilotMissionPreviewIntoPilotState`
- `filterAionLinesForDepartmentOrItemV1`
- `gateDepartment`
- `getActiveDepartmentO13D`
- `getActiveDepartmentSheetO13C`
- `getAionActiveGoalLoopDepartmentContext`
- `getAionActiveGoalLoopGraphForCentralPilotQueue`
- `getAionActiveGoalLoopGraphForDepartmentContext`
- `getAionBoardroomSelectedDepartmentPulseKey`
- `getAionCentralPilotNextApprovedTask`
- `getAionCentralPilotQueue`
- `getAionCoreDepartmentKeys`
- `getAionCouncilDepartmentContextPacketLines`
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
- `inferAionDepartmentFromPlanLineV2`
- `inferAionDepartmentFromTaskDraftV1`
- `inferAionDepartmentFromTextV3`
- `inferAionDiscoveryDepartmentFromGateV1`
- `inferAionDiscoveryDepartmentV1`
- `inferAionTaskOwnerFromDepartmentV1`
- `initialDepartmentSheets`
- `installAionO13BLinkedDepartmentGoalSheetOpener`
- `installAionO13CDepartmentGoalSheetPilotTaskPackets`
- `installAionO13DLiveAgentsPilotPreviewStateBridge`
- `installAionO13ELiveAgentsWorkspaceGoalSheetQueueInjection`
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
- `isDepartmentGoalSheetO13C`
- `isDepartmentLinksNode`
- `isDepartmentSelected`
- `itemDepartment`
- `linkedDepartmentSheets`
- `liveDepartmentOpenButton`
- `maybeOpenDepartmentChooserFromNodeO13B`
- `nodeDepartment`
- `normaliseAionDepartmentIntelligenceEntry`
- `normaliseAionDepartmentIntelligenceEntryEarlyCompatV1`
- `normaliseAionDepartmentKeyV1`
- `normaliseAionDepartmentPilotKey`
- `normaliseAionDepartmentPilotStatus`
- `normaliseAionGoalLoopDepartmentKey`
- `normaliseAionPilotFollowOnLabel`
- `normaliseAionPilotMarketingWorkspaceText`
- `normaliseAionPilotMissionMapNodeTitle`
- `normaliseAionPilotMissionPreviewQueues`
- `normaliseAionPilotPreviewText`
- `normaliseDepartmentO13C`
- `normalizedDepartment`
- `openAionPilotOutputPreview`
- `openAionPilotStepOutput`
- `openDepartmentButton`
- `openDepartmentGoalSheetO13B`
- `openDepartmentPilotFromQueueO13E`
- `openDepartmentWorkspaceFromBoardroom`
- `packetsByDepartment`
- `previewAionGoalLoopDepartmentTaskQueueWriteback`
- `primaryDepartment`
- `publishPilotPreviewStateO13D`
- `queueDepartmentItems`
- `rawDepartmentMap`
- `readAionCentralPilotStorageObject`
- `renderAionDepartmentPilotDiscoveryPanel`
- `renderAionDepartmentPilotGoalLoopContextPanel`
- `renderAionDepartmentPilotLedgerSyncPanel`
- `renderAionDepartmentPilotMissingList`
- `renderAionDepartmentPilotPhase25CPanel`
- `renderAionDepartmentPilotPhase25DPanel`
- `renderAionDepartmentPilotPhase25EPanel`
- `renderAionDepartmentPilotPhase25FPanel`
- `renderAionDepartmentPilotPlanPanel`
- `renderAionDepartmentPilotSafeQueuePanel`
- `renderAionDepartmentScopedPilotSurface`
- `renderAionDepartmentTasksHtmlV2`
- `renderAionGoalLoopCentralPilotTaskQueuePanel`
- `renderAionGoalLoopDepartmentTaskQueueWritebackPanel`
- `renderAionLrmPilotContextReadonlyCard`
- `renderAionPilotAdvancedTechnicalDetails`
- `renderAionPilotCockpitPanel`
- `renderAionPilotDepartmentQueueSummary`
- `renderAionPilotFollowOnWorkQueue`
- `renderAionPilotFrontendStreamEvents`
- `renderAionPilotHumanApprovalChecklist`
- `renderAionPilotMarketingArtifactCard`
- `renderAionPilotOutputPanel`
- `renderAionPilotReasoningMiniStatus`
- `renderAionPilotSimpleTaskStream`
- `renderAionPilotStepCheckpointCard`
- `renderAionPilotStepOutputCards`
- `renderAionPilotTrackedDraftLine`
- `renderAionPilotTrackedDraftText`
- `renderAionPilotWorkPackageCard`
- `renderBoardroomCrossDepartmentReviewPanel`
- `renderBoardroomCrossDepartmentReviewPanelFallbackV1`
- `renderBoardroomDepartmentIntelligencePanel`
- `renderBoardroomDepartments`
- `renderBoardroomSpatialCrossDepartmentReviewPanel`
- `renderBusinessDepartmentContextSubtab`
- `renderDashboardDepartmentCards`
- `renderDepartmentApprovalsSurface`
- `renderDepartmentChooserO13B`
- `renderDepartmentLane`
- `renderDepartmentQueueRowsO13E`
- `renderGenericDepartmentRoomCard`
- `renderGenericDepartmentWorkspaceSurface`
- `renderLiveAgentCalendarView`
- `renderLiveAgentHero`
- `renderLiveAgentRunRow`
- `renderLiveAgentRunsView`
- `renderLiveAgentSettingsView`
- `renderLiveAgentStreamView`
- `renderLiveAgentsGoalSheetPilotQueuePanelO13E`
- `renderLiveAgentsMarketingWorkspaceTabs`
- `renderLiveAgentsPersistentPilotTerminal`
- `renderLiveAgentsReplayOverlay`
- `renderLiveAgentsStatsStrip`
- `renderLiveAgentsSubviewTabs`
- `renderLiveAgentsSurface`
- `renderLiveAgentsWorkspaceBody`
- `renderLiveAgentsWorkspaceBodyWithGoalSheetQueue`
- `renderMarketingDepartmentRoomCard`
- `renderMinimalDepartmentSwitcher`
- `renderPilotMarketingWorkspaceSurface`
- `renderPilotPreviewPanelO13D`
- `renderWithO13CPilotToolbar`
- `reviseAionPilotMissionContract`
- `runAionCentralPilotApprovedTask`
- `runAionDepartmentPilotNextSafeTask`
- `runAionPilotSafeWorkPreview`
- `safeDepartment`
- `safeDepartmentSheets`
- `safeDepartments`
- `saveAionCentralPilotQueue`
- `saveAionDepartmentPilotDiscovery`
- `selectedDepartment`
- `selectedDepartmentKey`
- `setAionBoardroomSelectedDepartmentPulseKey`
- `setAionDepartmentIntelligence`
- `setAionDepartmentIntelligenceEarlyCompatV1`
- `setLiveAgentsWorkspace`
- `splitAionPilotCompoundAddInstruction`
- `startPilotTask`
- `supportingDepartments`
- `syncPilotTaskPacketToolbarO13C`
- `toggleAionPilotFollowOnApprovalStage`
- `toggleAionPilotFollowOnQueueExpanded`
- `toggleAionPilotHumanApprovalStage`
- `uniqueDepartments`
- `updateAionDepartmentIntelligence`
- `updateAionDepartmentIntelligenceEarlyCompatV1`
- `usefulDepartments`
- `viewAionPilotReceiptPreview`
- `wrapLiveAgentsWorkspaceBodyO13E`
- `wrappedBuildActiveDepartmentPilotTaskPacketsO13D`
- `wrappedBuildAllDepartmentPilotTaskPacketsO13D`
- `writeAionCentralPilotStorageObject`