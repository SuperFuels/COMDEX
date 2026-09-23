(function initDesktopOperationsRenderer(global) {
  function ensureThree() {
    if (!global.THREE) {
      throw new Error("THREE must be loaded before desktop-operations-renderer.js");
    }
    return global.THREE;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function prettify(value) {
    return String(value ?? "—").replaceAll("_", " ");
  }

  function formatMoney(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "—";
    return `£${value.toLocaleString("en-GB")}`;
  }

  function formatPct(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "—";
    return `${value}%`;
  }

  function clone(value) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_) {
      return value;
    }
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function asRecord(value) {
    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : null;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function seatStateColor(state) {
    if (state === "blocked") return "#ef4444";
    if (state === "warning") return "#f59e0b";
    if (state === "escalated") return "#f97316";
    if (state === "failed") return "#ef4444";
    if (state === "waiting_approval") return "#f59e0b";
    if (state === "running") return "#1a8aff";
    return "#22c55e";
  }

  function seatStateColorHex(state) {
    if (state === "blocked") return 0xef4444;
    if (state === "warning") return 0xf59e0b;
    if (state === "escalated") return 0xf97316;
    if (state === "failed") return 0xef4444;
    if (state === "waiting_approval") return 0xf59e0b;
    if (state === "running") return 0x1a8aff;
    return 0x22c55e;
  }

  function runtimeStatusTone(status) {
    if (status === "running") return "#1a8aff";
    if (status === "waiting_approval") return "#f59e0b";
    if (status === "failed") return "#ef4444";
    if (status === "completed") return "#22c55e";
    if (status === "queued") return "#64748b";
    return "#8b5cf6";
  }

  function runtimeStatusToneHex(status) {
    if (status === "running") return 0x1a8aff;
    if (status === "waiting_approval") return 0xf59e0b;
    if (status === "failed") return 0xef4444;
    if (status === "completed") return 0x22c55e;
    if (status === "queued") return 0x64748b;
    return 0x8b5cf6;
  }

  function flowTone(flow) {
    if (!flow) return "#64748b";
    if (flow.exception || (flow.blockedCount ?? 0) > 0) return "#ef4444";
    if (flow.bottleneck) return "#f59e0b";
    return seatStateColor(flow.state);
  }

  function flowToneHex(flow) {
    if (!flow) return 0x64748b;
    if (flow.exception || (flow.blockedCount ?? 0) > 0) return 0xef4444;
    if (flow.bottleneck) return 0xf59e0b;
    return seatStateColorHex(flow.state);
  }

  function getSnapshotRoot(snapshot) {
    return asRecord(snapshot) || {};
  }

  function getWorkspace(snapshot) {
    const root = getSnapshotRoot(snapshot);
    return (
      asRecord(root.workspace) ||
      asRecord(root.summary?.workspace) ||
      { workspace_id: root.workspaceId || "workspace", name: root.workspaceId || "workspace" }
    );
  }

  function getPulse(snapshot) {
    const root = getSnapshotRoot(snapshot);
    return asRecord(root.pulse) || asRecord(root.summary?.pulse) || {};
  }

  function getRuntime(snapshot) {
    const root = getSnapshotRoot(snapshot);
    return asRecord(root.runtime) || asRecord(root.summary?.runtime) || {};
  }

  function getTopology(snapshot) {
    const root = getSnapshotRoot(snapshot);
    return asRecord(root.topology) || asRecord(root.summary?.topology) || { nodes: [], edges: [] };
  }

  function getFloors(snapshot) {
    const root = getSnapshotRoot(snapshot);
    return asRecord(root.floors) || asRecord(root.summary?.floors) || {};
  }

  function getSeats(snapshot) {
    const root = getSnapshotRoot(snapshot);
    return safeArray(root.seats || root.summary?.seats);
  }

  function getDepartments(snapshot) {
    const root = getSnapshotRoot(snapshot);
    return safeArray(root.departments || root.summary?.departments);
  }

  function getBindingsByCategory(snapshot) {
    const root = getSnapshotRoot(snapshot);
    return asRecord(root.bindingsByCategory) || {};
  }

  function getRuns(snapshot) {
    const runtime = getRuntime(snapshot);
    return safeArray(runtime.runs);
  }

  function getApprovals(snapshot) {
    const runtime = getRuntime(snapshot);
    return safeArray(runtime.approvals);
  }

  function getSeatById(seats, seatId) {
    return safeArray(seats).find((seat) => seat?.id === seatId) || null;
  }

  function getSeatByDepartmentKey(seats, departmentKey) {
    const items = safeArray(seats);

    return (
      items.find((seat) => seat?.departmentKey === departmentKey) ||
      items.find((seat) => seat?.department_key === departmentKey) ||
      items.find((seat) => seat?.key === departmentKey) ||
      items.find((seat) => seat?.slug === departmentKey) ||
      items.find((seat) => seat?.department?.key === departmentKey) ||
      items.find((seat) => seat?.department?.slug === departmentKey) ||
      items.find((seat) => {
        const id = String(seat?.id || "").toLowerCase();
        if (departmentKey === "operations") return id === "seat_ops" || id.includes("operations");
        return id === `seat_${departmentKey}` || id.includes(departmentKey);
      }) ||
      null
    );
  }

  function getSeatIdForZone(zone) {
    switch (zone) {
      case "marketing":
        return "seat_marketing";
      case "sales":
        return "seat_sales";
      case "operations":
        return "seat_ops";
      case "finance":
        return "seat_finance";
      case "support":
        return "seat_support";
      case "hr":
        return "seat_hr";
      default:
        return null;
    }
  }

  function getInspectorKindForZoneFlow(zone) {
    switch (zone) {
      case "marketing":
        return "marketing_flow";
      case "sales":
        return "sales_flow";
      case "operations":
        return "operations_flow";
      case "finance":
        return "finance_flow";
      case "support":
        return "support_flow";
      case "hr":
        return "hr_flow";
      default:
        return "seat";
    }
  }

  function getInspectorKindForZoneStage(zone) {
    switch (zone) {
      case "marketing":
        return "marketing_stage";
      case "sales":
        return "sales_stage";
      case "operations":
        return "operations_stage";
      case "finance":
        return "finance_stage";
      case "support":
        return "support_stage";
      case "hr":
        return "hr_stage";
      default:
        return "seat";
    }
  }

  function getInspectorKindForZoneAgent(zone) {
    switch (zone) {
      case "marketing":
        return "marketing_agent";
      case "sales":
        return "sales_agent";
      case "operations":
        return "operations_agent";
      case "finance":
        return "finance_agent";
      case "support":
        return "support_agent";
      case "hr":
        return "hr_agent";
      default:
        return "seat";
    }
  }

  function isTargetActive(target, kind, key, value) {
    return !!target && target.kind === kind && target[key] === value;
  }

  function getFlowStageLabel(flow, stages, side) {
    const stageId = side === "from" ? flow?.fromStageId : flow?.toStageId;
    const found = safeArray(stages).find((stage) => stage?.id === stageId);
    return found?.label || stageId || "—";
  }

  function flowOverlayValue(flow) {
    if (!flow) return "—";
    const parts = [`${flow.count ?? 0}`];

    if (typeof flow.value === "number") {
      parts.push(formatMoney(flow.value));
    }

    if (typeof flow.cycleTimeDays === "number") {
      parts.push(`${flow.cycleTimeDays}d`);
    }

    if ((flow.blockedCount ?? 0) > 0) {
      parts.push(`${flow.blockedCount} blocked`);
    }

    return parts.join(" · ");
  }

  function getDepartmentRuntimeCounts(snapshot, departmentKey) {
    const runs = getRuns(snapshot).filter(
      (run) => String(run?.department_key || "").toLowerCase() === String(departmentKey || "").toLowerCase(),
    );

    const approvals = getApprovals(snapshot).filter(
      (item) => String(item?.department_key || "").toLowerCase() === String(departmentKey || "").toLowerCase(),
    );

    return {
      totalRuns: runs.length,
      queued: runs.filter((run) => run?.status === "queued").length,
      running: runs.filter((run) => run?.status === "running").length,
      waitingApproval: runs.filter((run) => run?.status === "waiting_approval").length,
      failed: runs.filter((run) => run?.status === "failed").length,
      completed: runs.filter((run) => run?.status === "completed").length,
      pendingApprovals: approvals.filter((item) => item?.status === "pending").length,
      runs,
      approvals,
    };
  }

  function metricCard(label, value, sub, accent) {
    return `
      <div style="
        border:1px solid rgba(148,163,184,0.18);
        background:#ffffff;
        border-radius:16px;
        padding:14px 16px;
        min-height:92px;
        box-shadow:0 10px 24px rgba(15,23,42,0.04);
      ">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">${escapeHtml(label)}</div>
        <div style="margin-top:6px;font-size:24px;font-weight:800;color:${escapeHtml(accent || "#0f172a")};line-height:1.1;">
          ${escapeHtml(value)}
        </div>
        <div style="margin-top:6px;font-size:12px;color:#64748b;line-height:1.35;">
          ${escapeHtml(sub || "")}
        </div>
      </div>
    `;
  }

  function seatCard(seat, zone, ctx, opts) {
    const active = ctx.selectedSeatId === seat?.id;
    const border = active
      ? "1px solid rgba(26,138,255,0.45)"
      : "1px solid rgba(148,163,184,0.18)";

    const counts = getDepartmentRuntimeCounts(ctx.snapshot, zone);

    return `
      <button
        type="button"
        data-seat-id="${escapeHtml(seat?.id || "")}"
        data-zone="${escapeHtml(zone)}"
        style="
          width:100%;
          text-align:left;
          border:${border};
          background:${active ? "rgba(26,138,255,0.08)" : "#ffffff"};
          border-radius:18px;
          padding:14px 16px;
          cursor:pointer;
          box-shadow:0 10px 24px rgba(15,23,42,0.04);
        "
      >
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;">
          <div>
            <div style="font-size:16px;font-weight:800;color:#0f172a;">${escapeHtml(seat?.label || prettify(zone))}</div>
            <div style="margin-top:4px;font-size:12px;color:#64748b;">${escapeHtml(seat?.owner || "Department seat")}</div>
          </div>
          <div style="
            border-radius:999px;
            padding:5px 9px;
            font-size:11px;
            font-weight:800;
            background:rgba(15,23,42,0.04);
            color:${escapeHtml(seatStateColor(seat?.state))};
            border:1px solid rgba(148,163,184,0.18);
            text-transform:uppercase;
          ">${escapeHtml(seat?.state || "healthy")}</div>
        </div>

        <div style="
          display:grid;
          grid-template-columns:repeat(3,minmax(0,1fr));
          gap:8px;
          margin-top:12px;
        ">
          <div style="padding:8px 10px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#64748b;">Open</div>
            <div style="margin-top:4px;font-size:16px;font-weight:800;color:#0f172a;">${escapeHtml(seat?.openTasks ?? 0)}</div>
          </div>
          <div style="padding:8px 10px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#64748b;">Blocked</div>
            <div style="margin-top:4px;font-size:16px;font-weight:800;color:#0f172a;">${escapeHtml(seat?.blockedTasks ?? 0)}</div>
          </div>
          <div style="padding:8px 10px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#64748b;">Due today</div>
            <div style="margin-top:4px;font-size:16px;font-weight:800;color:#0f172a;">${escapeHtml(seat?.dueToday ?? 0)}</div>
          </div>
        </div>

        <div style="
          display:grid;
          grid-template-columns:repeat(4,minmax(0,1fr));
          gap:8px;
          margin-top:10px;
        ">
          <div style="padding:8px 10px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#64748b;">Queued</div>
            <div style="margin-top:4px;font-size:15px;font-weight:800;color:#0f172a;">${escapeHtml(counts.queued)}</div>
          </div>
          <div style="padding:8px 10px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#64748b;">Running</div>
            <div style="margin-top:4px;font-size:15px;font-weight:800;color:#0f172a;">${escapeHtml(counts.running)}</div>
          </div>
          <div style="padding:8px 10px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#64748b;">Review</div>
            <div style="margin-top:4px;font-size:15px;font-weight:800;color:#0f172a;">${escapeHtml(counts.waitingApproval)}</div>
          </div>
          <div style="padding:8px 10px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#64748b;">Failed</div>
            <div style="margin-top:4px;font-size:15px;font-weight:800;color:#0f172a;">${escapeHtml(counts.failed)}</div>
          </div>
        </div>

        ${
          opts && opts.summary
            ? `<div style="margin-top:12px;font-size:12px;color:#475569;line-height:1.4;">${escapeHtml(opts.summary)}</div>`
            : ""
        }
      </button>
    `;
  }

  function stageCard(stage, zone, target) {
    const active = isTargetActive(
      target,
      getInspectorKindForZoneStage(zone),
      "stageId",
      stage?.id,
    );

    return `
      <button
        type="button"
        data-stage-id="${escapeHtml(stage?.id || "")}"
        data-stage-zone="${escapeHtml(zone)}"
        style="
          border:${active ? "1px solid rgba(26,138,255,0.45)" : "1px solid rgba(148,163,184,0.18)"};
          background:${active ? "rgba(26,138,255,0.08)" : "#ffffff"};
          border-radius:14px;
          padding:10px 12px;
          cursor:pointer;
          text-align:left;
        "
      >
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
          <div style="font-size:13px;font-weight:700;color:#0f172a;">${escapeHtml(stage?.label || "Stage")}</div>
          <div style="
            width:10px;height:10px;border-radius:999px;background:${escapeHtml(seatStateColor(stage?.state))};
          "></div>
        </div>
        <div style="margin-top:8px;font-size:22px;font-weight:800;color:#0f172a;">${escapeHtml(stage?.count ?? 0)}</div>
        ${
          typeof stage?.value === "number"
            ? `<div style="margin-top:4px;font-size:12px;color:#64748b;">${escapeHtml(formatMoney(stage.value))}</div>`
            : ""
        }
      </button>
    `;
  }

  function agentCard(agent, zone, target) {
    const active = isTargetActive(
      target,
      getInspectorKindForZoneAgent(zone),
      "agentId",
      agent?.id,
    );

    return `
      <button
        type="button"
        data-agent-id="${escapeHtml(agent?.id || "")}"
        data-agent-zone="${escapeHtml(zone)}"
        style="
          border:${active ? "1px solid rgba(26,138,255,0.45)" : "1px solid rgba(148,163,184,0.18)"};
          background:${active ? "rgba(26,138,255,0.08)" : "#ffffff"};
          border-radius:14px;
          padding:10px 12px;
          cursor:pointer;
          text-align:left;
        "
      >
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
          <div style="font-size:13px;font-weight:700;color:#0f172a;">${escapeHtml(agent?.label || "Agent")}</div>
          <div style="
            border-radius:999px;
            padding:4px 8px;
            font-size:10px;
            font-weight:800;
            color:${escapeHtml(seatStateColor(agent?.state))};
            background:rgba(15,23,42,0.04);
            border:1px solid rgba(148,163,184,0.16);
          ">${escapeHtml(agent?.displayTag || "UNIT")}</div>
        </div>
        <div style="margin-top:4px;font-size:12px;color:#64748b;">${escapeHtml(agent?.role || "—")}</div>
        <div style="margin-top:8px;font-size:12px;color:#475569;">
          Load ${escapeHtml(agent?.workload ?? 0)}
          ${typeof agent?.assignedCount === "number" ? ` · Assigned ${agent.assignedCount}` : ""}
          ${typeof agent?.throughput === "number" ? ` · Throughput ${agent.throughput}` : ""}
        </div>
      </button>
    `;
  }

  function flowCard(flow, zone, stages, target) {
    const active = isTargetActive(
      target,
      getInspectorKindForZoneFlow(zone),
      "flowId",
      flow?.id,
    );
    const tone = flowTone(flow);

    return `
      <button
        type="button"
        data-flow-id="${escapeHtml(flow?.id || "")}"
        data-flow-zone="${escapeHtml(zone)}"
        style="
          border:${active ? "1px solid rgba(26,138,255,0.45)" : "1px solid rgba(148,163,184,0.18)"};
          background:${active ? "rgba(26,138,255,0.08)" : "#ffffff"};
          border-radius:14px;
          padding:10px 12px;
          cursor:pointer;
          text-align:left;
        "
      >
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
          <div style="font-size:13px;font-weight:700;color:#0f172a;">
            ${escapeHtml(getFlowStageLabel(flow, stages, "from"))} → ${escapeHtml(getFlowStageLabel(flow, stages, "to"))}
          </div>
          <div style="
            width:10px;height:10px;border-radius:999px;background:${escapeHtml(tone)};
          "></div>
        </div>
        <div style="margin-top:8px;font-size:12px;color:${escapeHtml(tone)};font-weight:700;">
          ${escapeHtml(flowOverlayValue(flow))}
        </div>
        <div style="margin-top:6px;font-size:11px;color:#64748b;">
          ${escapeHtml(flow?.label || prettify(flow?.state || "flow"))}
        </div>
      </button>
    `;
  }

  function departmentSection(title, zone, seat, floor, target, snapshot) {
    const stages = safeArray(floor?.stages);
    const agents = safeArray(floor?.agents);
    const flows = safeArray(floor?.flows);
    const counts = getDepartmentRuntimeCounts(snapshot, zone);

    return `
      <section style="
        border:1px solid rgba(148,163,184,0.18);
        background:rgba(255,255,255,0.9);
        border-radius:20px;
        padding:16px;
        display:grid;
        gap:14px;
      ">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;">
          <div>
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">${escapeHtml(title)}</div>
            <div style="margin-top:4px;font-size:20px;font-weight:800;color:#0f172a;">${escapeHtml(seat?.label || title)}</div>
          </div>
          <div style="
            border-radius:999px;
            padding:6px 10px;
            font-size:11px;
            font-weight:800;
            background:rgba(15,23,42,0.04);
            color:${escapeHtml(seatStateColor(seat?.state))};
            border:1px solid rgba(148,163,184,0.16);
            text-transform:uppercase;
          ">${escapeHtml(seat?.state || "healthy")}</div>
        </div>

        ${seatCard(seat, zone, { snapshot, selectedSeatId: null }, { summary: seat?.owner || "" })}

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;">
          ${metricCard("Queued", counts.queued, "Run queue", runtimeStatusTone("queued"))}
          ${metricCard("Running", counts.running, "Executing", runtimeStatusTone("running"))}
          ${metricCard("Review", counts.waitingApproval, "Waiting approval", runtimeStatusTone("waiting_approval"))}
          ${metricCard("Failed", counts.failed, "Needs attention", runtimeStatusTone("failed"))}
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;">
          ${stages.map((stage) => stageCard(stage, zone, target)).join("") || `
            <div style="grid-column:1 / -1;font-size:12px;color:#64748b;">No stage data.</div>
          `}
        </div>

        <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">
          ${flows.map((flow) => flowCard(flow, zone, stages, target)).join("") || `
            <div style="grid-column:1 / -1;font-size:12px;color:#64748b;">No flow data.</div>
          `}
        </div>

        <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">
          ${agents.map((agent) => agentCard(agent, zone, target)).join("") || `
            <div style="grid-column:1 / -1;font-size:12px;color:#64748b;">No agent data.</div>
          `}
        </div>
      </section>
    `;
  }

  function renderOperationsFlowHtml(ctx) {
    const snapshot = ctx.snapshot || {};
    const pulse = getPulse(snapshot);
    const runtime = getRuntime(snapshot);
    const workspace = getWorkspace(snapshot);
    const topology = getTopology(snapshot);
    const seats = getSeats(snapshot);
    const floors = getFloors(snapshot);
    const bindingsByCategory = getBindingsByCategory(snapshot);

    const marketingSeat = getSeatByDepartmentKey(seats, "marketing");
    const salesSeat = getSeatByDepartmentKey(seats, "sales");
    const operationsSeat = getSeatByDepartmentKey(seats, "operations");
    const financeSeat = getSeatByDepartmentKey(seats, "finance");
    const supportSeat = getSeatByDepartmentKey(seats, "support");
    const hrSeat = getSeatByDepartmentKey(seats, "hr");

    const runs = safeArray(runtime.runs);
    const approvals = safeArray(runtime.approvals);
    const topologyNodes = safeArray(topology.nodes);
    const topologyEdges = safeArray(topology.edges);

    return `
      <div style="
        min-height:100%;
        padding:18px;
        display:grid;
        gap:16px;
        background:
          radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.08), transparent 55%),
          radial-gradient(1000px 500px at 80% 20%, rgba(244,26,255,0.04), transparent 55%),
          linear-gradient(180deg, #f7f9fc, #edf2f8);
      ">
        <section style="
          border:1px solid rgba(148,163,184,0.18);
          background:rgba(255,255,255,0.92);
          border-radius:22px;
          padding:18px;
          box-shadow:0 18px 50px rgba(15,23,42,0.06);
        ">
          <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap;">
            <div>
              <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">Aion Business Desktop</div>
              <div style="margin-top:4px;font-size:28px;font-weight:800;color:#0f172a;">Operating system map</div>
              <div style="margin-top:6px;font-size:13px;color:#64748b;max-width:780px;">
                Supporting topology for the COO command loop. This map shows loaded runtime structure; business performance belongs in the evidence-backed COO briefing above.
              </div>
              <div style="margin-top:8px;font-size:12px;color:#475569;">
                ${escapeHtml(workspace.name || workspace.workspace_id || "Workspace")} ·
                ${escapeHtml(workspace.business_type || workspace.industry || workspace.slug || "Local runtime")}
              </div>
            </div>

            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              ${["marketing", "sales", "operations", "finance", "support", "hr"]
                .map((zone) => {
                  const active = ctx.activeZone === zone;
                  return `
                    <button
                      type="button"
                      data-zone-select="${escapeHtml(zone)}"
                      style="
                        border:${active ? "1px solid rgba(26,138,255,0.55)" : "1px solid rgba(191,206,224,0.9)"};
                        background:${active ? "rgba(26,138,255,0.14)" : "rgba(255,255,255,0.85)"};
                        color:${active ? "#0f4ea8" : "#1f2937"};
                        border-radius:999px;
                        padding:8px 12px;
                        font-size:12px;
                        font-weight:700;
                        cursor:pointer;
                      "
                    >${escapeHtml(prettify(zone))}</button>
                  `;
                })
                .join("")}
            </div>
          </div>

          <div style="
            margin-top:16px;
            display:grid;
            grid-template-columns:repeat(5,minmax(0,1fr));
            gap:12px;
          ">
            ${metricCard("Department Seats", seats.length, "Loaded operating functions", "#1a8aff")}
            ${metricCard("Runtime Runs", runs.length, "Boardroom runtime snapshot", "#0f172a")}
            ${metricCard("Pending Approvals", approvals.filter((item) => item?.status === "pending").length, "Decision queue", "#f59e0b")}
            ${metricCard("Topology Nodes", topologyNodes.length, "Spatial/runtime graph", "#1a8aff")}
            ${metricCard("Binding Groups", Object.keys(bindingsByCategory).length, "Container categories", "#8b5cf6")}
          </div>
        </section>

        <section style="
          border:1px solid rgba(148,163,184,0.18);
          background:rgba(255,255,255,0.92);
          border-radius:22px;
          padding:18px;
          box-shadow:0 18px 50px rgba(15,23,42,0.06);
          overflow:auto;
        ">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">Linear Chain</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              <button
                type="button"
                data-operations-view="flat"
                style="
                  border:${ctx.viewMode === "flat" ? "1px solid rgba(26,138,255,0.55)" : "1px solid rgba(191,206,224,0.9)"};
                  background:${ctx.viewMode === "flat" ? "rgba(26,138,255,0.14)" : "rgba(255,255,255,0.85)"};
                  color:${ctx.viewMode === "flat" ? "#0f4ea8" : "#1f2937"};
                  border-radius:999px;
                  padding:8px 12px;
                  font-size:12px;
                  font-weight:700;
                  cursor:pointer;
                "
              >Flat View</button>
              <button
                type="button"
                data-operations-view="spatial"
                style="
                  border:${ctx.viewMode === "spatial" ? "1px solid rgba(26,138,255,0.55)" : "1px solid rgba(191,206,224,0.9)"};
                  background:${ctx.viewMode === "spatial" ? "rgba(26,138,255,0.14)" : "rgba(255,255,255,0.85)"};
                  color:${ctx.viewMode === "spatial" ? "#0f4ea8" : "#1f2937"};
                  border-radius:999px;
                  padding:8px 12px;
                  font-size:12px;
                  font-weight:700;
                  cursor:pointer;
                "
              >3D View</button>
            </div>
          </div>

          <div style="margin-top:12px;display:grid;grid-template-columns:repeat(5,minmax(220px,1fr));gap:14px;align-items:start;">
            ${seatCard(marketingSeat, "marketing", ctx, { summary: "Channels → engine → funnel" })}
            ${seatCard(salesSeat, "sales", ctx, { summary: "Qualify → quote → close" })}
            ${seatCard(operationsSeat, "operations", ctx, { summary: "Schedule → dispatch → fulfil" })}
            ${seatCard(financeSeat, "finance", ctx, { summary: "Invoice → collect → settle" })}
            ${seatCard(supportSeat, "support", ctx, { summary: "Triage → resolve → retain" })}
          </div>

          <div style="margin-top:14px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;align-items:center;">
            <div style="height:10px;border-radius:999px;background:linear-gradient(90deg,#1a8aff,#60a5fa);"></div>
            <div style="height:10px;border-radius:999px;background:linear-gradient(90deg,#3b82f6,#22c55e);"></div>
            <div style="height:10px;border-radius:999px;background:linear-gradient(90deg,#8b5cf6,#22c55e);"></div>
            <div style="height:10px;border-radius:999px;background:linear-gradient(90deg,#22c55e,#06b6d4);"></div>
          </div>

          ${
            hrSeat
              ? `
                <div style="margin-top:14px;">
                  ${seatCard(hrSeat, "hr", ctx, { summary: "Onboarding · admin · compliance overlay" })}
                </div>
              `
              : ""
          }
        </section>

        <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;">
          ${departmentSection("Marketing Engine", "marketing", marketingSeat, floors.marketing, ctx.selectedInspectorTarget, snapshot)}
          ${departmentSection("Sales Unit", "sales", salesSeat, floors.sales, ctx.selectedInspectorTarget, snapshot)}
          ${departmentSection("Operations Unit", "operations", operationsSeat, floors.operations, ctx.selectedInspectorTarget, snapshot)}
          ${departmentSection("Finance Bank", "finance", financeSeat, floors.finance, ctx.selectedInspectorTarget, snapshot)}
          ${departmentSection("Support Hub", "support", supportSeat, floors.support, ctx.selectedInspectorTarget, snapshot)}
          ${departmentSection("HR / Admin Overlay", "hr", hrSeat, floors.hr, ctx.selectedInspectorTarget, snapshot)}
        </div>
      </div>
    `;
  }

  function makeTextSprite(text, options) {
    const THREE = ensureThree();
    const opts = options || {};

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    const fontSize = opts.fontSize || 42;
    const fontWeight = opts.fontWeight || 800;
    const paddingX = opts.paddingX || 24;
    const paddingY = opts.paddingY || 16;
    const color = opts.color || "#0f172a";
    const background = opts.background || "rgba(255,255,255,0)";
    const fontFamily =
      opts.fontFamily ||
      "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

    ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
    const metrics = ctx.measureText(String(text));
    const width = Math.max(64, Math.ceil(metrics.width) + paddingX * 2);
    const height = Math.max(48, fontSize + paddingY * 2);

    canvas.width = width;
    canvas.height = height;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, width, height);
    ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = color;
    ctx.fillText(String(text), width / 2, height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    if (THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;

    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });

    const sprite = new THREE.Sprite(material);
    const aspect = width / height;
    const heightWorld = opts.heightWorld || 1;
    sprite.scale.set(heightWorld * aspect, heightWorld, 1);
    return sprite;
  }

  function addLine(parent, a, b, color, opacity) {
    const THREE = ensureThree();
    const geometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(a[0], a[1], a[2]),
      new THREE.Vector3(b[0], b[1], b[2]),
    ]);

    const material = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity: opacity == null ? 0.4 : opacity,
    });

    const line = new THREE.Line(geometry, material);
    parent.add(line);
    return line;
  }

  function createRoundedPad(width, depth, color) {
    const THREE = ensureThree();
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(width, 0.18, depth),
      new THREE.MeshStandardMaterial({
        color: color == null ? 0xffffff : color,
        roughness: 0.94,
        metalness: 0.02,
      }),
    );
    return mesh;
  }

  function buildStageTower(label, count, accent, heightUnits, active) {
    const THREE = ensureThree();
    const group = new THREE.Group();
    const towerHeight = 1 + heightUnits * 0.25;

    const base = new THREE.Mesh(
      new THREE.BoxGeometry(1.8, 0.16, 1.24),
      new THREE.MeshStandardMaterial({ color: 0xeef3f8, roughness: 0.96 }),
    );
    base.position.y = 0.08;
    group.add(base);

    const tower = new THREE.Mesh(
      new THREE.BoxGeometry(1.34, towerHeight, 0.92),
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.93 }),
    );
    tower.position.y = towerHeight / 2 + 0.16;
    group.add(tower);

    const cap = new THREE.Mesh(
      new THREE.BoxGeometry(1.34, 0.05, 0.92),
      new THREE.MeshBasicMaterial({
        color: accent,
        transparent: true,
        opacity: active ? 0.34 : 0.18,
      }),
    );
    cap.position.y = towerHeight + 0.185;
    group.add(cap);

    if (active) {
      const glow = new THREE.Mesh(
        new THREE.BoxGeometry(1.46, towerHeight + 0.08, 1.04),
        new THREE.MeshBasicMaterial({
          color: 0x1a8aff,
          transparent: true,
          opacity: 0.12,
        }),
      );
      glow.position.y = towerHeight / 2 + 0.16;
      group.add(glow);
    }

    const labelSprite = makeTextSprite(label, {
      fontSize: 18,
      fontWeight: 700,
      color: "#64748b",
      heightWorld: 0.18,
    });
    labelSprite.position.set(0, 0.4, 0.72);
    group.add(labelSprite);

    const countSprite = makeTextSprite(String(count ?? 0), {
      fontSize: 28,
      fontWeight: 800,
      color: "#0f172a",
      heightWorld: 0.24,
    });
    countSprite.position.set(0, 0.08, 0.72);
    group.add(countSprite);

    return group;
  }

  function buildBot(label, role, tint, active, runtimeMeta) {
    const THREE = ensureThree();
    const group = new THREE.Group();

    const base = new THREE.Mesh(
      new THREE.BoxGeometry(0.92, 0.12, 0.92),
      new THREE.MeshStandardMaterial({ color: 0xdfe7f1, roughness: 0.96 }),
    );
    base.position.y = 0.08;
    group.add(base);

    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.34, 0.82, 0.34),
      new THREE.MeshStandardMaterial({ color: 0xf7f9fc, roughness: 0.72 }),
    );
    body.position.y = 0.58;
    group.add(body);

    const head = new THREE.Mesh(
      new THREE.BoxGeometry(0.3, 0.24, 0.24),
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.66 }),
    );
    head.position.y = 1.12;
    group.add(head);

    const visor = new THREE.Mesh(
      new THREE.PlaneGeometry(0.16, 0.08),
      new THREE.MeshBasicMaterial({ color: 0x0b2545 }),
    );
    visor.position.set(0, 1.12, 0.125);
    group.add(visor);

    const eyeL = new THREE.Mesh(
      new THREE.CircleGeometry(0.012, 16),
      new THREE.MeshBasicMaterial({ color: tint }),
    );
    eyeL.position.set(-0.03, 1.12, 0.13);
    group.add(eyeL);

    const eyeR = new THREE.Mesh(
      new THREE.CircleGeometry(0.012, 16),
      new THREE.MeshBasicMaterial({ color: tint }),
    );
    eyeR.position.set(0.03, 1.12, 0.13);
    group.add(eyeR);

    if (runtimeMeta?.status) {
      const halo = new THREE.Mesh(
        new THREE.TorusGeometry(0.4, 0.024, 16, 40),
        new THREE.MeshBasicMaterial({
          color: runtimeStatusToneHex(runtimeMeta.status),
          transparent: true,
          opacity: 0.28,
        }),
      );
      halo.rotation.x = Math.PI / 2;
      halo.position.y = 0.16;
      group.add(halo);
    }

    if (active) {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.34, 0.035, 16, 40),
        new THREE.MeshBasicMaterial({ color: 0x1a8aff }),
      );
      ring.rotation.x = Math.PI / 2;
      ring.position.y = 0.5;
      group.add(ring);
    }

    const labelSprite = makeTextSprite(label, {
      fontSize: 16,
      fontWeight: 700,
      color: "#0f172a",
      heightWorld: 0.14,
    });
    labelSprite.position.set(0, 0.34, 0.58);
    group.add(labelSprite);

    const roleSprite = makeTextSprite(role || "—", {
      fontSize: 13,
      fontWeight: 700,
      color: "#64748b",
      heightWorld: 0.12,
    });
    roleSprite.position.set(0, 0.12, 0.58);
    group.add(roleSprite);

    if (runtimeMeta?.count > 0) {
      const runSprite = makeTextSprite(`${runtimeMeta.count} run`, {
        fontSize: 12,
        fontWeight: 800,
        color: runtimeStatusTone(runtimeMeta.status),
        heightWorld: 0.1,
      });
      runSprite.position.set(0, -0.08, 0.58);
      group.add(runSprite);
    }

    return { group, mesh: body };
  }

  function buildFlowBadge(label, value, tone, active) {
    const THREE = ensureThree();
    const group = new THREE.Group();

    const box = new THREE.Mesh(
      new THREE.BoxGeometry(3.1, 0.8, 1.05),
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.94 }),
    );
    group.add(box);

    const top = new THREE.Mesh(
      new THREE.BoxGeometry(3.1, 0.04, 1.05),
      new THREE.MeshBasicMaterial({
        color: tone,
        transparent: true,
        opacity: active ? 0.3 : 0.14,
      }),
    );
    top.position.y = 0.42;
    group.add(top);

    if (active) {
      const glow = new THREE.Mesh(
        new THREE.BoxGeometry(3.22, 0.88, 1.13),
        new THREE.MeshBasicMaterial({
          color: 0x1a8aff,
          transparent: true,
          opacity: 0.12,
        }),
      );
      group.add(glow);
    }

    const labelSprite = makeTextSprite(label, {
      fontSize: 16,
      fontWeight: 700,
      color: "#64748b",
      heightWorld: 0.12,
    });
    labelSprite.position.set(0, 0.14, 0.56);
    group.add(labelSprite);

    const valueSprite = makeTextSprite(value, {
      fontSize: 18,
      fontWeight: 800,
      color: "#0f172a",
      heightWorld: 0.14,
    });
    valueSprite.position.set(0, -0.12, 0.56);
    group.add(valueSprite);

    return { group, mesh: box };
  }

  function buildConveyor(width) {
    const THREE = ensureThree();
    const group = new THREE.Group();

    const base = new THREE.Mesh(
      new THREE.BoxGeometry(width, 0.18, 1.5),
      new THREE.MeshStandardMaterial({ color: 0xb9c7d8, roughness: 0.88 }),
    );
    group.add(base);

    const belt = new THREE.Mesh(
      new THREE.BoxGeometry(width - 0.34, 0.05, 0.88),
      new THREE.MeshStandardMaterial({ color: 0x374151, roughness: 0.58 }),
    );
    belt.position.y = 0.04;
    group.add(belt);

    return group;
  }

  function createRuntimePill(color, phase, scaleX, startX, endX) {
    const THREE = ensureThree();
    const group = new THREE.Group();

    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.42 * scaleX, 0.14, 0.22),
      new THREE.MeshBasicMaterial({ color }),
    );
    group.add(body);

    const head = new THREE.Mesh(
      new THREE.ConeGeometry(0.12, 0.22, 3),
      new THREE.MeshBasicMaterial({ color }),
    );
    head.position.x = 0.24 * scaleX;
    head.rotation.z = -Math.PI / 2;
    group.add(head);

    group.userData.animate = function animate(timeSeconds) {
      const t = (Math.sin(timeSeconds * 1.45 + phase) + 1) / 2;
      const x = startX + (endX - startX) * t;
      group.position.x = x;
    };

    return group;
  }

  function addAnimatedObject(object) {
    if (!current || !object) return;
    current.animatables.push(object);
  }

  function registerInteractive(mesh, meta) {
    if (!current || !mesh) return;
    current.interactives.push({ mesh, meta });
  }

  function clearInteractiveObjects() {
    if (!current) return;
    current.interactives = [];
    current.animatables = [];
  }

  function disposeMaterial(material) {
    if (!material) return;
    if (Array.isArray(material)) {
      material.forEach(disposeMaterial);
      return;
    }
    if (material.map) material.map.dispose?.();
    if (material.alphaMap) material.alphaMap.dispose?.();
    material.dispose?.();
  }

  function disposeObject(object) {
    if (!object) return;
    object.traverse?.((child) => {
      if (child.geometry) child.geometry.dispose?.();
      if (child.material) disposeMaterial(child.material);
    });
  }

  let current = null;
  let currentMount = null;
  let currentCtx = null;

  function disposeSpatialScene() {
    if (!current) return;

    if (current.rafId) {
      global.cancelAnimationFrame(current.rafId);
    }

    if (current.onResize) {
      global.removeEventListener("resize", current.onResize);
    }

    if (current.controlsCleanup) {
      current.controlsCleanup();
    }

    if (current.pointerCleanup) {
      current.pointerCleanup();
    }

    if (current.rootGroup) {
      current.scene.remove(current.rootGroup);
      disposeObject(current.rootGroup);
    }

    if (current.scene) {
      disposeObject(current.scene);
    }

    if (current.renderer) {
      current.renderer.dispose?.();
      current.renderer.forceContextLoss?.();
      if (current.renderer.domElement?.parentNode) {
        current.renderer.domElement.parentNode.removeChild(current.renderer.domElement);
      }
    }

    current = null;
  }

  function buildContext(rendererState) {
    return {
      snapshot: clone(rendererState?.snapshot || {}),
      viewMode: rendererState?.viewMode === "spatial" ? "spatial" : "flat",
      activeZone: rendererState?.activeZone || "operations",
      selectedSeatId: rendererState?.selectedSeatId || null,
      selectedInspectorTarget: clone(rendererState?.selectedInspectorTarget || null),
      onViewModeChange: rendererState?.onViewModeChange,
      onActiveZoneChange: rendererState?.onActiveZoneChange,
      onSeatSelect: rendererState?.onSeatSelect,
      onInspectorTargetChange: rendererState?.onInspectorTargetChange,
      requestRender: rendererState?.requestRender,
    };
  }

  function bindEvents(mount, ctx) {
    mount.querySelectorAll("[data-zone-select]").forEach((el) => {
      el.addEventListener("click", () => {
        const zone = el.getAttribute("data-zone-select");
        if (!zone) return;

        const seatId = getSeatIdForZone(zone);
        ctx.onActiveZoneChange?.(zone);
        if (seatId) {
          ctx.onSeatSelect?.(seatId, zone);
          ctx.onInspectorTargetChange?.({ kind: "seat", seatId });
        }
        ctx.requestRender?.();
      });
    });

    mount.querySelectorAll("[data-seat-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const seatId = el.getAttribute("data-seat-id");
        const zone = el.getAttribute("data-zone");
        if (!seatId || !zone) return;

        ctx.onActiveZoneChange?.(zone);
        ctx.onSeatSelect?.(seatId, zone);
        ctx.onInspectorTargetChange?.({ kind: "seat", seatId });
        ctx.requestRender?.();
      });
    });

    mount.querySelectorAll("[data-stage-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const stageId = el.getAttribute("data-stage-id");
        const zone = el.getAttribute("data-stage-zone");
        if (!stageId || !zone) return;

        const seatId = getSeatIdForZone(zone);
        const kind = getInspectorKindForZoneStage(zone);

        ctx.onActiveZoneChange?.(zone);
        if (seatId) ctx.onSeatSelect?.(seatId, zone);
        ctx.onInspectorTargetChange?.({ kind, stageId });
        ctx.requestRender?.();
      });
    });

    mount.querySelectorAll("[data-agent-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const agentId = el.getAttribute("data-agent-id");
        const zone = el.getAttribute("data-agent-zone");
        if (!agentId || !zone) return;

        const seatId = getSeatIdForZone(zone);
        const kind = getInspectorKindForZoneAgent(zone);

        ctx.onActiveZoneChange?.(zone);
        if (seatId) ctx.onSeatSelect?.(seatId, zone);
        ctx.onInspectorTargetChange?.({ kind, agentId });
        ctx.requestRender?.();
      });
    });

    mount.querySelectorAll("[data-flow-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const flowId = el.getAttribute("data-flow-id");
        const zone = el.getAttribute("data-flow-zone");
        if (!flowId || !zone) return;

        const seatId = getSeatIdForZone(zone);
        const kind = getInspectorKindForZoneFlow(zone);

        ctx.onActiveZoneChange?.(zone);
        if (seatId) ctx.onSeatSelect?.(seatId, zone);
        ctx.onInspectorTargetChange?.({ kind, flowId });
        ctx.requestRender?.();
      });
    });

    mount.querySelectorAll("[data-operations-view]").forEach((el) => {
      el.addEventListener("click", () => {
        const mode = el.getAttribute("data-operations-view");
        if (!mode) return;

        ctx.onViewModeChange?.(mode);
        ctx.requestRender?.();
      });
    });
  }

  function renderFlatIntoMount(mount, rendererState) {
    const ctx = buildContext(rendererState);
    currentCtx = ctx;
    mount.innerHTML = renderOperationsFlowHtml(ctx);
    bindEvents(mount, ctx);
  }

  function buildSceneShell(scene) {
    const THREE = ensureThree();

    scene.background = new THREE.Color("#eef3f9");
    scene.fog = new THREE.Fog("#eef3f9", 55, 185);

    const ambient = new THREE.AmbientLight(0xffffff, 1.12);
    scene.add(ambient);

    const key = new THREE.DirectionalLight(0xffffff, 1.15);
    key.position.set(12, 18, 10);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0xffffff, 0.45);
    fill.position.set(-10, 10, -12);
    scene.add(fill);

    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(220, 100),
      new THREE.MeshStandardMaterial({
        color: 0xedf2f8,
        roughness: 0.98,
        metalness: 0.02,
      }),
    );
    plane.rotation.x = -Math.PI / 2;
    plane.position.set(16, -0.96, 0);
    scene.add(plane);

    const grid = new THREE.GridHelper(
      220,
      140,
      new THREE.Color("#bfd3ea"),
      new THREE.Color("#dce8f5"),
    );
    grid.position.set(16, -0.94, 0);
    grid.material.transparent = true;
    grid.material.opacity = 0.48;
    scene.add(grid);
  }

  function applyCameraPose(camera, pose) {
    camera.position.set(
      pose.radius * Math.sin(pose.theta) * Math.cos(pose.phi) + pose.targetX,
      pose.y,
      pose.radius * Math.cos(pose.theta) * Math.cos(pose.phi) + pose.targetZ,
    );
    camera.lookAt(pose.targetX, pose.targetY, pose.targetZ);
  }

  function setupSimpleOrbitControls(renderer, camera) {
    const state = {
      isDragging: false,
      lastX: 0,
      lastY: 0,
      theta: 0.12,
      phi: 0.44,
      radius: 56,
      y: 16,
      targetX: 18,
      targetY: 1.6,
      targetZ: 0,
    };

    applyCameraPose(camera, state);

    function onMouseDown(event) {
      state.isDragging = true;
      state.lastX = event.clientX;
      state.lastY = event.clientY;
    }

    function onMouseMove(event) {
      if (!state.isDragging) return;
      const dx = event.clientX - state.lastX;
      const dy = event.clientY - state.lastY;
      state.lastX = event.clientX;
      state.lastY = event.clientY;

      state.theta -= dx * 0.008;
      state.phi = clamp(state.phi - dy * 0.004, 0.14, 1.12);
      applyCameraPose(camera, state);
    }

    function onMouseUp() {
      state.isDragging = false;
    }

    function onWheel(event) {
      event.preventDefault();
      state.radius = clamp(state.radius + event.deltaY * 0.04, 20, 95);
      state.y = clamp(state.radius * 0.32, 8, 34);
      applyCameraPose(camera, state);
    }

    const el = renderer.domElement;
    el.addEventListener("mousedown", onMouseDown);
    global.addEventListener("mousemove", onMouseMove);
    global.addEventListener("mouseup", onMouseUp);
    el.addEventListener("wheel", onWheel, { passive: false });

    return function cleanup() {
      el.removeEventListener("mousedown", onMouseDown);
      global.removeEventListener("mousemove", onMouseMove);
      global.removeEventListener("mouseup", onMouseUp);
      el.removeEventListener("wheel", onWheel);
    };
  }

  function handleSpatialSelection(meta) {
    if (!current || !meta) return;
    const options = current.options || {};

    if (meta.type === "view_mode") {
      options.onViewModeChange?.(meta.mode);
      options.requestRender?.();
      return;
    }

    if (meta.type === "seat") {
      options.activeZone = meta.zone;
      options.selectedSeatId = meta.seatId;
      options.selectedInspectorTarget = { kind: "seat", seatId: meta.seatId };

      options.onActiveZoneChange?.(meta.zone);
      options.onSeatSelect?.(meta.seatId, meta.zone);
      options.onInspectorTargetChange?.({ kind: "seat", seatId: meta.seatId });
    }

    if (meta.type === "stage") {
      const kind = getInspectorKindForZoneStage(meta.zone);
      const seatId = getSeatIdForZone(meta.zone);

      options.activeZone = meta.zone;
      options.selectedSeatId = seatId;
      options.selectedInspectorTarget = { kind, stageId: meta.stageId };

      options.onActiveZoneChange?.(meta.zone);
      if (seatId) options.onSeatSelect?.(seatId, meta.zone);
      options.onInspectorTargetChange?.({ kind, stageId: meta.stageId });
    }

    if (meta.type === "agent") {
      const kind = getInspectorKindForZoneAgent(meta.zone);
      const seatId = getSeatIdForZone(meta.zone);

      options.activeZone = meta.zone;
      options.selectedSeatId = seatId;
      options.selectedInspectorTarget = { kind, agentId: meta.agentId };

      options.onActiveZoneChange?.(meta.zone);
      if (seatId) options.onSeatSelect?.(seatId, meta.zone);
      options.onInspectorTargetChange?.({ kind, agentId: meta.agentId });
    }

    if (meta.type === "flow") {
      const kind = getInspectorKindForZoneFlow(meta.zone);
      const seatId = getSeatIdForZone(meta.zone);

      options.activeZone = meta.zone;
      options.selectedSeatId = seatId;
      options.selectedInspectorTarget = { kind, flowId: meta.flowId };

      options.onActiveZoneChange?.(meta.zone);
      if (seatId) options.onSeatSelect?.(seatId, meta.zone);
      options.onInspectorTargetChange?.({ kind, flowId: meta.flowId });
    }

    rebuildSpatialWorld(options.snapshot, options);

    if (typeof options.requestRender === "function") {
      options.requestRender();
    }
  }

  function setupPointerInteraction(renderer, camera) {
    const THREE = ensureThree();
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    function getHit(event) {
      if (!current) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);

      const hits = raycaster.intersectObjects(
        current.interactives.map((item) => item.mesh),
        false,
      );

      if (!hits.length) return null;
      const found = current.interactives.find((item) => item.mesh === hits[0].object);
      return found ? found.meta : null;
    }

    function onClick(event) {
      const meta = getHit(event);
      if (meta) handleSpatialSelection(meta);
    }

    function onMove(event) {
      const meta = getHit(event);
      renderer.domElement.style.cursor = meta ? "pointer" : "default";
    }

    renderer.domElement.addEventListener("click", onClick);
    renderer.domElement.addEventListener("mousemove", onMove);

    return function cleanup() {
      renderer.domElement.removeEventListener("click", onClick);
      renderer.domElement.removeEventListener("mousemove", onMove);
      renderer.domElement.style.cursor = "default";
    };
  }

  function buildTopRightViewToggleGroup(options) {
    const THREE = ensureThree();
    const group = new THREE.Group();

    const flatActive = options.viewMode !== "spatial";
    const spatialActive = options.viewMode === "spatial";

    function makeButton(label, active, x, mode) {
      const btn = new THREE.Group();

      const box = new THREE.Mesh(
        new THREE.BoxGeometry(3.1, 0.68, 0.2),
        new THREE.MeshStandardMaterial({
          color: 0xffffff,
          roughness: 0.92,
          metalness: 0.02,
        }),
      );
      box.position.set(x, 0, 0);
      btn.add(box);

      const top = new THREE.Mesh(
        new THREE.BoxGeometry(3.1, 0.035, 0.2),
        new THREE.MeshBasicMaterial({
          color: active ? 0x1a8aff : 0x94a3b8,
          transparent: true,
          opacity: active ? 0.26 : 0.12,
        }),
      );
      top.position.set(x, 0.34, 0);
      btn.add(top);

      const text = makeTextSprite(label, {
        fontSize: 16,
        fontWeight: 800,
        color: active ? "#0f4ea8" : "#334155",
        heightWorld: 0.16,
      });
      text.position.set(x, 0, 0.14);
      btn.add(text);

      registerInteractive(box, { type: "view_mode", mode });
      return btn;
    }

    group.add(makeButton("Flat View", flatActive, 0, "flat"));
    group.add(makeButton("3D View", spatialActive, 3.7, "spatial"));

    return group;
  }

  function buildOperationsWorld(snapshot, options) {
    const THREE = ensureThree();
    const root = new THREE.Group();

    const pulse = getPulse(snapshot);
    const runtime = getRuntime(snapshot);
    const workspace = getWorkspace(snapshot);
    const topology = getTopology(snapshot);
    const floors = getFloors(snapshot);
    const seats = getSeats(snapshot);
    const bindingsByCategory = getBindingsByCategory(snapshot);

    const marketingSeat = getSeatByDepartmentKey(seats, "marketing");
    const salesSeat = getSeatByDepartmentKey(seats, "sales");
    const operationsSeat = getSeatByDepartmentKey(seats, "operations");
    const financeSeat = getSeatByDepartmentKey(seats, "finance");
    const supportSeat = getSeatByDepartmentKey(seats, "support");
    const hrSeat = getSeatByDepartmentKey(seats, "hr");

    const selectedSeatId = options?.selectedSeatId || null;
    const selectedInspectorTarget = options?.selectedInspectorTarget || null;

    const marketingX = -16;
    const funnelX = -5.2;
    const salesX = 8;
    const operationsX = 20;
    const financeX = 32;
    const supportX = 44;
    const hrX = 44;

    const base = new THREE.Mesh(
      new THREE.BoxGeometry(102, 0.18, 28),
      new THREE.MeshStandardMaterial({
        color: 0xdfe7f1,
        roughness: 0.96,
        metalness: 0.02,
      }),
    );
    base.position.set(14, -0.78, 0);
    root.add(base);

    const baseGlow = new THREE.Mesh(
      new THREE.BoxGeometry(102.6, 0.04, 28.6),
      new THREE.MeshBasicMaterial({
        color: 0xcfd9e6,
        transparent: true,
        opacity: 0.55,
      }),
    );
    baseGlow.position.set(14, -0.92, 0);
    root.add(baseGlow);

    const heroText = makeTextSprite("Operations Flow", {
      fontSize: 52,
      fontWeight: 900,
      color: "#0f172a",
      heightWorld: 1.12,
    });
    heroText.position.set(14, 8.8, -7.4);
    root.add(heroText);

    const heroSub = makeTextSprite("desktop-native 3D runtime chain", {
      fontSize: 22,
      fontWeight: 800,
      color: "#64748b",
      heightWorld: 0.34,
    });
    heroSub.position.set(14, 7.9, -7.4);
    root.add(heroSub);

    const workspaceLabel = makeTextSprite(
      `${workspace.name || workspace.workspace_id || "Workspace"} · ${workspace.business_type || workspace.industry || workspace.slug || "local runtime"}`,
      {
        fontSize: 16,
        fontWeight: 800,
        color: "#1a8aff",
        heightWorld: 0.18,
      },
    );
    workspaceLabel.position.set(14, 7.2, -7.4);
    root.add(workspaceLabel);

    const viewToggle = buildTopRightViewToggleGroup(options || {});
    viewToggle.position.set(33, 8.8, -7.2);
    root.add(viewToggle);

    const channelSpecs = [
      { key: "meta", label: "Meta Ads", subtitle: "Paid social", x: marketingX - 10.5, z: -5.2, accent: 0x1a8aff },
      { key: "tiktok", label: "TikTok", subtitle: "Organic + paid", x: marketingX - 6.4, z: -5.2, accent: 0x8b5cf6 },
      { key: "website", label: "Website", subtitle: "Direct + SEO", x: marketingX - 2.3, z: -5.2, accent: 0x22c55e },
      { key: "email", label: "Email", subtitle: "Lifecycle + nurture", x: marketingX + 1.8, z: -5.2, accent: 0xf59e0b },
      { key: "referrals", label: "Referrals", subtitle: "Word of mouth", x: marketingX + 5.9, z: -5.2, accent: 0x10b981 },
      { key: "marketplace", label: "Marketplace", subtitle: "External", x: marketingX + 10.0, z: -5.2, accent: 0x06b6d4 },
    ];

    channelSpecs.forEach((channel) => {
      const group = new THREE.Group();

      const box = new THREE.Mesh(
        new THREE.BoxGeometry(2.9, 1.2, 1.8),
        new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.94 }),
      );
      group.add(box);

      const top = new THREE.Mesh(
        new THREE.BoxGeometry(2.9, 0.05, 1.8),
        new THREE.MeshBasicMaterial({
          color: channel.accent,
          transparent: true,
          opacity: selectedSeatId === "seat_marketing" ? 0.3 : 0.16,
        }),
      );
      top.position.y = 0.62;
      group.add(top);

      const label = makeTextSprite(channel.label, {
        fontSize: 18,
        fontWeight: 800,
        color: "#0f172a",
        heightWorld: 0.2,
      });
      label.position.set(0, 0.12, 0.98);
      group.add(label);

      const subtitle = makeTextSprite(channel.subtitle, {
        fontSize: 14,
        fontWeight: 700,
        color: "#64748b",
        heightWorld: 0.14,
      });
      subtitle.position.set(0, -0.18, 0.98);
      group.add(subtitle);

      group.position.set(channel.x, 4.25, channel.z);
      root.add(group);
      registerInteractive(box, { type: "seat", zone: "marketing", seatId: "seat_marketing" });

      const conveyor = buildConveyor(2.8);
      conveyor.position.set(channel.x + 3.1, -0.16, channel.z);
      root.add(conveyor);

      addLine(root, [channel.x + 1.45, 4.2, channel.z], [marketingX - 3.2, 2.55, channel.z * 0.22], channel.accent, 0.38);
    });

    const marketingEngine = new THREE.Group();
    const engineBase = new THREE.Mesh(
      new THREE.BoxGeometry(5.4, 0.36, 2.5),
      new THREE.MeshStandardMaterial({ color: 0xd9e7f5, roughness: 0.92 }),
    );
    engineBase.position.set(0, -1.15, 0);
    marketingEngine.add(engineBase);

    const engineBody = new THREE.Mesh(
      new THREE.BoxGeometry(1.8, 1.48, 1.22),
      new THREE.MeshStandardMaterial({ color: 0xc7d6e6, roughness: 0.9 }),
    );
    engineBody.position.set(-0.1, -0.14, -0.08);
    marketingEngine.add(engineBody);

    const engineWheel = new THREE.Mesh(
      new THREE.CylinderGeometry(2.25, 2.25, 0.52, 48),
      new THREE.MeshStandardMaterial({ color: 0xeef4fb, roughness: 0.82, metalness: 0.08 }),
    );
    engineWheel.rotation.x = Math.PI / 2;
    engineWheel.position.set(0, 0.15, 0.15);
    marketingEngine.add(engineWheel);

    const engineRing = new THREE.Mesh(
      new THREE.TorusGeometry(1.56, 0.18, 18, 60),
      new THREE.MeshStandardMaterial({ color: 0xdbe7f3, roughness: 0.76, metalness: 0.06 }),
    );
    engineRing.position.set(0, 0.15, 0.44);
    marketingEngine.add(engineRing);

    const marketingTitle = makeTextSprite("Marketing Engine", {
      fontSize: 36,
      fontWeight: 900,
      color: "#0f172a",
      heightWorld: 0.52,
    });
    marketingTitle.position.set(0, 3.15, 0.2);
    marketingEngine.add(marketingTitle);

    const marketingCounts = getDepartmentRuntimeCounts(snapshot, "marketing");
    const marketingSub = makeTextSprite(
      `${pulse?.sales?.orders ?? "—"} input events · ${marketingCounts.running} running`,
      {
        fontSize: 18,
        fontWeight: 800,
        color: "#1a8aff",
        heightWorld: 0.2,
      },
    );
    marketingSub.position.set(0, 2.1, 0.2);
    marketingEngine.add(marketingSub);

    marketingEngine.position.set(marketingX, 2.6, 0);
    root.add(marketingEngine);
    registerInteractive(engineWheel, { type: "seat", zone: "marketing", seatId: "seat_marketing" });
    engineWheel.userData.animate = function animate() {
      engineWheel.rotation.z += 0.01;
      engineRing.rotation.z -= 0.004;
    };
    addAnimatedObject(engineWheel);

    const funnel = new THREE.Group();
    const funnelMesh = new THREE.Mesh(
      new THREE.CylinderGeometry(2.15, 0.78, 2.95, 32, 1, true),
      new THREE.MeshStandardMaterial({
        color: 0x7dd3fc,
        transparent: true,
        opacity: 0.42,
        roughness: 0.32,
        metalness: 0.02,
        side: THREE.DoubleSide,
      }),
    );
    funnelMesh.position.y = 1.5;
    funnel.add(funnelMesh);

    const funnelTop = new THREE.Mesh(
      new THREE.CylinderGeometry(2.18, 2.18, 0.09, 32),
      new THREE.MeshBasicMaterial({
        color: 0x67e8f9,
        transparent: true,
        opacity: 0.62,
      }),
    );
    funnelTop.position.y = 2.84;
    funnel.add(funnelTop);

    const funnelArrow = new THREE.Mesh(
      new THREE.ConeGeometry(0.42, 1.1, 3),
      new THREE.MeshBasicMaterial({ color: 0x3b82f6 }),
    );
    funnelArrow.rotation.z = -Math.PI / 2;
    funnelArrow.position.set(0, 3.82, 0);
    funnel.add(funnelArrow);

    const funnelLabel = makeTextSprite("Traffic", {
      fontSize: 40,
      fontWeight: 900,
      color: "#0f172a",
      heightWorld: 0.56,
    });
    funnelLabel.position.set(0, 6.08, 0.1);
    funnel.add(funnelLabel);

    funnel.position.set(funnelX, 0.25, 0);
    root.add(funnel);
    registerInteractive(funnelMesh, { type: "seat", zone: "marketing", seatId: "seat_marketing" });

    addLine(root, [marketingX + 4.25, 2.7, 0], [funnelX - 2.3, 2.7, 0], 0x3b82f6, 0.58);
    addLine(root, [funnelX - 2.3, 2.7, 0], [funnelX - 2.3, 3.85, 0], 0x3b82f6, 0.58);
    addLine(root, [funnelX - 2.3, 3.85, 0], [funnelX, 3.85, 0], 0x3b82f6, 0.58);

    function buildDepartmentBlock(params) {
      const zone = params.zone;
      const x = params.x;
      const title = params.title;
      const subtitle = params.subtitle;
      const seatId = params.seatId;
      const active = selectedSeatId === seatId;
      const stages = safeArray(params.stages);
      const agents = safeArray(params.agents);
      const flows = safeArray(params.flows);
      const stageAccent = params.accent;
      const runtimeCounts = getDepartmentRuntimeCounts(snapshot, zone);

      const runtimeMap = {};
      runtimeCounts.runs.forEach((run) => {
        const agentId = run?.agent_id;
        if (!agentId) return;
        if (!runtimeMap[agentId]) {
          runtimeMap[agentId] = { count: 1, status: run?.status || "queued" };
          return;
        }
        runtimeMap[agentId].count += 1;
        runtimeMap[agentId].status = run?.status || runtimeMap[agentId].status;
      });

      const baseGroup = new THREE.Group();

      const platform = new THREE.Mesh(
        new THREE.BoxGeometry(10.8, 0.24, 5.2),
        new THREE.MeshStandardMaterial({ color: 0xe8eef6, roughness: 0.96 }),
      );
      platform.position.y = 0.05;
      baseGroup.add(platform);

      const surface = new THREE.Mesh(
        new THREE.BoxGeometry(9.8, 0.22, 4.32),
        new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.93 }),
      );
      surface.position.y = 0.28;
      baseGroup.add(surface);

      const accent = new THREE.Mesh(
        new THREE.BoxGeometry(9.8, 0.04, 4.32),
        new THREE.MeshBasicMaterial({
          color: stageAccent,
          transparent: true,
          opacity: active ? 0.3 : 0.16,
        }),
      );
      accent.position.y = 0.42;
      baseGroup.add(accent);

      if (active) {
        const glow = new THREE.Mesh(
          new THREE.BoxGeometry(10.02, 0.05, 4.54),
          new THREE.MeshBasicMaterial({
            color: 0x1a8aff,
            transparent: true,
            opacity: 0.16,
          }),
        );
        glow.position.y = 0.47;
        baseGroup.add(glow);
      }

      const titleWall = new THREE.Mesh(
        new THREE.BoxGeometry(7.8, 1.8, 0.18),
        new THREE.MeshStandardMaterial({ color: 0xf8fbff, roughness: 0.94 }),
      );
      titleWall.position.set(0, 1.3, -2.1);
      baseGroup.add(titleWall);

      const titleStripe = new THREE.Mesh(
        new THREE.BoxGeometry(7.8, 0.08, 0.08),
        new THREE.MeshBasicMaterial({
          color: stageAccent,
          transparent: true,
          opacity: 0.3,
        }),
      );
      titleStripe.position.set(0, 2.14, -2.04);
      baseGroup.add(titleStripe);

      const titleSprite = makeTextSprite(title, {
        fontSize: 34,
        fontWeight: 900,
        color: "#0f172a",
        heightWorld: 0.5,
      });
      titleSprite.position.set(0, 1.8, -1.86);
      baseGroup.add(titleSprite);

      const subtitleSprite = makeTextSprite(
        `${subtitle} · ${runtimeCounts.running} running · ${runtimeCounts.waitingApproval} review`,
        {
          fontSize: 16,
          fontWeight: 700,
          color: "#64748b",
          heightWorld: 0.16,
        },
      );
      subtitleSprite.position.set(0, 1.15, -1.86);
      baseGroup.add(subtitleSprite);

      registerInteractive(platform, { type: "seat", zone, seatId });

      const stageXs = [-3.25, -1.05, 1.15, 3.35];
      stages.slice(0, 4).forEach((stage, index) => {
        const activeStage = isTargetActive(
          selectedInspectorTarget,
          getInspectorKindForZoneStage(zone),
          "stageId",
          stage?.id,
        );
        const tower = buildStageTower(
          stage?.label || `Stage ${index + 1}`,
          stage?.count ?? 0,
          seatStateColorHex(stage?.state),
          Math.max(2, Math.min(8, (stage?.count ?? 1) / 2)),
          activeStage,
        );
        tower.position.set(stageXs[index], 0, 1.65);
        baseGroup.add(tower);

        const stageMesh = tower.children[1];
        if (stageMesh) {
          registerInteractive(stageMesh, {
            type: "stage",
            zone,
            stageId: stage?.id,
          });
        }
      });

      const flowBadgeZ = 3.3;
      flows.slice(0, 2).forEach((flow, index) => {
        const activeFlow = isTargetActive(
          selectedInspectorTarget,
          getInspectorKindForZoneFlow(zone),
          "flowId",
          flow?.id,
        );
        const flowBadge = buildFlowBadge(
          `${getFlowStageLabel(flow, stages, "from")} → ${getFlowStageLabel(flow, stages, "to")}`,
          flowOverlayValue(flow),
          flowToneHex(flow),
          activeFlow,
        );
        flowBadge.group.position.set(-1.8 + index * 3.8, 0.35, flowBadgeZ);
        baseGroup.add(flowBadge.group);
        registerInteractive(flowBadge.mesh, {
          type: "flow",
          zone,
          flowId: flow?.id,
        });
      });

      agents.slice(0, 4).forEach((agent, index) => {
        const ax = -2.5 + index * 1.7;
        const activeAgent = isTargetActive(
          selectedInspectorTarget,
          getInspectorKindForZoneAgent(zone),
          "agentId",
          agent?.id,
        );
        const bot = buildBot(
          agent?.label || "Agent",
          agent?.role || "unit",
          seatStateColorHex(agent?.state),
          activeAgent,
          runtimeMap[agent?.id],
        );
        bot.group.position.set(ax, 0, -2.95);
        baseGroup.add(bot.group);
        registerInteractive(bot.mesh, {
          type: "agent",
          zone,
          agentId: agent?.id,
        });
      });

      if (zone !== "support" && zone !== "hr") {
        const conveyor = buildConveyor(7.4);
        conveyor.position.set(0, -0.16, 0);
        baseGroup.add(conveyor);
      }

      baseGroup.position.set(x, 0, 0);
      return baseGroup;
    }

    const salesGroup = buildDepartmentBlock({
      zone: "sales",
      x: salesX,
      title: "Sales Unit",
      subtitle: "qualify · quote · follow-up · close",
      seatId: "seat_sales",
      stages: floors?.sales?.stages,
      agents: floors?.sales?.agents,
      flows: floors?.sales?.flows,
      accent: 0x22c55e,
    });
    root.add(salesGroup);

    const operationsGroup = buildDepartmentBlock({
      zone: "operations",
      x: operationsX,
      title: "Operations Unit",
      subtitle: "schedule · dispatch · fulfil · complete",
      seatId: "seat_ops",
      stages: floors?.operations?.stages,
      agents: floors?.operations?.agents,
      flows: floors?.operations?.flows,
      accent: 0xf59e0b,
    });
    root.add(operationsGroup);

    const financeGroup = buildDepartmentBlock({
      zone: "finance",
      x: financeX,
      title: "Finance Bank",
      subtitle: "invoice · collect · settle · cash control",
      seatId: "seat_finance",
      stages: floors?.finance?.stages,
      agents: floors?.finance?.agents,
      flows: floors?.finance?.flows,
      accent: 0x15803d,
    });
    root.add(financeGroup);

    const supportGroup = buildDepartmentBlock({
      zone: "support",
      x: supportX,
      title: "Support Hub",
      subtitle: "triage · resolve · escalate · retain",
      seatId: "seat_support",
      stages: floors?.support?.stages,
      agents: floors?.support?.agents,
      flows: floors?.support?.flows,
      accent: 0x22c55e,
    });
    root.add(supportGroup);

    const hrGroup = buildDepartmentBlock({
      zone: "hr",
      x: hrX - 0.5,
      title: "HR / Admin Overlay",
      subtitle: "onboarding · documents · compliance",
      seatId: "seat_hr",
      stages: floors?.hr?.stages,
      agents: floors?.hr?.agents,
      flows: floors?.hr?.flows,
      accent: 0x8b5cf6,
    });
    hrGroup.position.z = 6.2;
    root.add(hrGroup);

    addLine(root, [funnelX + 0.88, 0.76, 0], [salesX - 2.8, 0.3, 0], 0x3b82f6, 0.55);
    addLine(root, [12.2, 0.24, 0], [13.8, 0.24, 0], 0x3b82f6, 0.65);
    addLine(root, [24.2, 0.24, 0], [25.8, 0.24, 0], 0x3b82f6, 0.65);
    addLine(root, [36.2, 0.24, 0], [37.8, 0.24, 0], 0x3b82f6, 0.65);

    const pillA = createRuntimePill(0x3b82f6, 0, 1, 12.2, 13.8);
    pillA.position.set(12.2, 0.24, 0);
    root.add(pillA);
    addAnimatedObject(pillA);

    const pillB = createRuntimePill(0x3b82f6, 0.8, 1, 24.2, 25.8);
    pillB.position.set(24.2, 0.24, 0);
    root.add(pillB);
    addAnimatedObject(pillB);

    const pillC = createRuntimePill(0x3b82f6, 1.6, 1, 36.2, 37.8);
    pillC.position.set(36.2, 0.24, 0);
    root.add(pillC);
    addAnimatedObject(pillC);

    const stats = [
      { label: "Seats", value: `${seats.length}`, x: -4.5, z: -9.2, accent: 0x1a8aff },
      { label: "Runs", value: `${safeArray(runtime.runs).length}`, x: 1.2, z: -9.2, accent: 0x22c55e },
      { label: "Approvals", value: `${safeArray(runtime.approvals).filter((item) => item?.status === "pending").length}`, x: 6.9, z: -9.2, accent: 0xf59e0b },
      { label: "Nodes", value: `${safeArray(topology.nodes).length}`, x: 12.6, z: -9.2, accent: 0x1a8aff },
      { label: "Edges", value: `${safeArray(topology.edges).length}`, x: 18.3, z: -9.2, accent: 0x22c55e },
      { label: "Floors", value: `${floors.length}`, x: 24.0, z: -9.2, accent: 0x1a8aff },
      { label: "Bindings", value: `${Object.keys(bindingsByCategory).length}`, x: 29.7, z: -9.2, accent: 0x8b5cf6 },
      { label: "Mode", value: "LIVE", x: 35.4, z: -9.2, accent: 0x15803d },
    ];

    stats.forEach((item) => {
      const pad = createRoundedPad(4.2, 1.6, 0xffffff);
      pad.position.set(item.x, 6.7, item.z);
      root.add(pad);

      const stripe = new THREE.Mesh(
        new THREE.BoxGeometry(4.2, 0.03, 1.6),
        new THREE.MeshBasicMaterial({
          color: item.accent,
          transparent: true,
          opacity: 0.14,
        }),
      );
      stripe.position.set(item.x, 6.79, item.z);
      root.add(stripe);

      const label = makeTextSprite(item.label, {
        fontSize: 16,
        fontWeight: 800,
        color: "#64748b",
        heightWorld: 0.16,
      });
      label.position.set(item.x, 6.92, item.z + 0.18);
      root.add(label);

      const value = makeTextSprite(item.value, {
        fontSize: 24,
        fontWeight: 900,
        color: "#0f172a",
        heightWorld: 0.22,
      });
      value.position.set(item.x, 6.58, item.z + 0.18);
      root.add(value);
    });

    const activeZoneLabel = makeTextSprite(`Active: ${prettify(options?.activeZone || "operations")}`, {
      fontSize: 18,
      fontWeight: 900,
      color: "#0f4ea8",
      heightWorld: 0.18,
    });
    activeZoneLabel.position.set(43, 6.95, -9.15);
    root.add(activeZoneLabel);

    return root;
  }

  function rebuildSpatialWorld(snapshot, options) {
    if (!current) return;

    clearInteractiveObjects();

    if (current.rootGroup) {
      current.scene.remove(current.rootGroup);
      disposeObject(current.rootGroup);
      current.rootGroup = null;
    }

    current.rootGroup = buildOperationsWorld(snapshot || {}, options || {});
    current.scene.add(current.rootGroup);
    current.options = {
      ...(current.options || {}),
      ...(options || {}),
      snapshot: snapshot || {},
    };
  }

  function mountSpatialIntoMount(mount, rendererState) {
    const THREE = ensureThree();
    const ctx = buildContext(rendererState);
    currentCtx = ctx;

    disposeSpatialScene();

    const width = Math.max(1, mount.clientWidth);
    const height = Math.max(1, mount.clientHeight);

    const scene = new THREE.Scene();
    buildSceneShell(scene);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 400);
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
    });

    renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    if (THREE.SRGBColorSpace) renderer.outputColorSpace = THREE.SRGBColorSpace;

    mount.innerHTML = "";
    mount.appendChild(renderer.domElement);

    const controlsCleanup = setupSimpleOrbitControls(renderer, camera);
    const pointerCleanup = setupPointerInteraction(renderer, camera);

    const onResize = function onResize() {
      if (!current || !current.container) return;
      const nextWidth = Math.max(1, current.container.clientWidth);
      const nextHeight = Math.max(1, current.container.clientHeight);
      current.camera.aspect = nextWidth / nextHeight;
      current.camera.updateProjectionMatrix();
      current.renderer.setSize(nextWidth, nextHeight);
    };

    global.addEventListener("resize", onResize);

    current = {
      container: mount,
      renderer,
      scene,
      camera,
      onResize,
      controlsCleanup,
      pointerCleanup,
      rafId: null,
      interactives: [],
      animatables: [],
      rootGroup: null,
      options: {
        snapshot: ctx.snapshot || {},
        viewMode: "spatial",
        activeZone: ctx.activeZone || "operations",
        selectedSeatId: ctx.selectedSeatId || null,
        selectedInspectorTarget: ctx.selectedInspectorTarget || null,
        onViewModeChange: ctx.onViewModeChange,
        onActiveZoneChange: ctx.onActiveZoneChange,
        onSeatSelect: ctx.onSeatSelect,
        onInspectorTargetChange: ctx.onInspectorTargetChange,
        requestRender: ctx.requestRender,
      },
    };

    rebuildSpatialWorld(current.options.snapshot, current.options);

    const animate = function animate() {
      if (!current) return;
      const timeSeconds = performance.now() / 1000;

      current.animatables.forEach((item) => {
        if (item && typeof item.userData?.animate === "function") {
          item.userData.animate(timeSeconds);
        }
      });

      current.renderer.render(current.scene, current.camera);
      current.rafId = global.requestAnimationFrame(animate);
    };

    animate();
  }

  function updateSpatialIntoMount(rendererState) {
    if (!current) return;
    const ctx = buildContext(rendererState);
    currentCtx = ctx;

    const merged = {
      ...(current.options || {}),
      snapshot: ctx.snapshot,
      viewMode: "spatial",
      activeZone: ctx.activeZone,
      selectedSeatId: ctx.selectedSeatId,
      selectedInspectorTarget: ctx.selectedInspectorTarget,
      onViewModeChange: ctx.onViewModeChange,
      onActiveZoneChange: ctx.onActiveZoneChange,
      onSeatSelect: ctx.onSeatSelect,
      onInspectorTargetChange: ctx.onInspectorTargetChange,
      requestRender: ctx.requestRender,
    };

    rebuildSpatialWorld(merged.snapshot, merged);
  }

  function renderIntoMount(mount, rendererState) {
    const mode = rendererState?.viewMode === "spatial" ? "spatial" : "flat";

    if (mode === "spatial") {
      mountSpatialIntoMount(mount, rendererState);
      return;
    }

    disposeSpatialScene();
    renderFlatIntoMount(mount, rendererState);
  }

  function mountOperationsFlow(mount, rendererState) {
    currentMount = mount;
    renderIntoMount(mount, rendererState);
  }

  function updateOperationsFlow(rendererState) {
    currentMount = currentMount || null;
    if (!currentMount) return;

    const mode = rendererState?.viewMode === "spatial" ? "spatial" : "flat";

    if (mode === "spatial") {
      if (current) {
        updateSpatialIntoMount(rendererState);
      } else {
        mountSpatialIntoMount(currentMount, rendererState);
      }
      return;
    }

    disposeSpatialScene();
    renderFlatIntoMount(currentMount, rendererState);
  }

  function disposeOperationsFlow() {
    disposeSpatialScene();

    if (currentMount) {
      currentMount.innerHTML = "";
      delete currentMount.dataset.operationsMounted;
    }

    currentMount = null;
    currentCtx = null;
  }

  global.TessarisDesktopOperationsRenderer = {
    mountOperationsFlow,
    updateOperationsFlow,
    disposeOperationsFlow,
  };
})(window);
