(function initTessarisDesktopRuntimeShared(global) {
  const contracts = global.TessarisDesktopContracts;

  if (!contracts) {
    throw new Error(
      "TessarisDesktopContracts must load before desktop-runtime-shared.js",
    );
  }

  const DEPARTMENT_META = {
    coo: { key: "coo", label: "COO", seatId: "seat_coo" },
    marketing: { key: "marketing", label: "Marketing", seatId: "seat_marketing" },
    sales: { key: "sales", label: "Sales", seatId: "seat_sales" },
    operations: { key: "operations", label: "Operations", seatId: "seat_ops" },
    finance: { key: "finance", label: "Finance", seatId: "seat_finance" },
    support: { key: "support", label: "Support", seatId: "seat_support" },
    hr: { key: "hr", label: "HR", seatId: "seat_hr" },
    ceo: { key: "ceo", label: "CEO", seatId: "seat_ceo" },
    aion: { key: "aion", label: "AION", seatId: "seat_aion" },
    openai: { key: "openai", label: "OpenAI", seatId: "seat_openai" },
  };

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function isRecord(value) {
    return !!value && typeof value === "object" && !Array.isArray(value);
  }

  function clone(value) {
    if (typeof contracts.clone === "function") {
      return contracts.clone(value);
    }

    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_) {
      return value;
    }
  }

  function firstDefined() {
    for (let i = 0; i < arguments.length; i += 1) {
      if (arguments[i] !== undefined && arguments[i] !== null) {
        return arguments[i];
      }
    }
    return undefined;
  }

  function firstNonEmptyString() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (typeof value === "string" && value.trim()) {
        return value.trim();
      }
    }
    return "";
  }

  function asNumber(value, fallback) {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function normalizeDepartmentKey(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (!raw) return "unknown";

    if (DEPARTMENT_META[raw]) return raw;
    if (raw === "ops") return "operations";
    if (raw === "operation") return "operations";
    if (raw === "support_hub") return "support";
    if (raw === "human_resources") return "hr";
    if (raw === "chief_operating_officer") return "coo";

    if (raw.includes("marketing")) return "marketing";
    if (raw.includes("sales")) return "sales";
    if (raw.includes("finance")) return "finance";
    if (raw.includes("support")) return "support";
    if (raw.includes("operation")) return "operations";
    if (raw === "hr" || raw.includes("human")) return "hr";
    if (raw.includes("ceo")) return "ceo";
    if (raw.includes("coo")) return "coo";
    if (raw.includes("aion")) return "aion";
    if (raw.includes("openai")) return "openai";

    return raw;
  }

  function prettifyDepartmentLabel(key) {
    const normalized = normalizeDepartmentKey(key);
    if (DEPARTMENT_META[normalized]) return DEPARTMENT_META[normalized].label;
    return normalized
      ? normalized
          .replaceAll("_", " ")
          .replace(/\b\w/g, (m) => m.toUpperCase())
      : "Unknown";
  }

  function getDepartmentMeta(key) {
    const normalized = normalizeDepartmentKey(key);
    return (
      DEPARTMENT_META[normalized] || {
        key: normalized,
        label: prettifyDepartmentLabel(normalized),
        seatId: normalized ? `seat_${normalized}` : null,
      }
    );
  }

  function getDepartmentLabel(key) {
    return getDepartmentMeta(key).label;
  }

  function getSeatIdForDepartment(key) {
    return getDepartmentMeta(key).seatId;
  }

  function parseDateMs(value) {
    if (!value) return 0;
    const ms = new Date(value).getTime();
    return Number.isFinite(ms) ? ms : 0;
  }

  function sortRunsNewestFirst(a, b) {
    return (
      parseDateMs(
        firstDefined(a?.updated_at, a?.completed_at, a?.created_at),
      ) -
      parseDateMs(
        firstDefined(b?.updated_at, b?.completed_at, b?.created_at),
      )
    ) * -1;
  }

  function sortItemsNewestFirst(a, b) {
    return (
      parseDateMs(
        firstDefined(a?.updated_at, a?.resolved_at, a?.requested_at, a?.created_at),
      ) -
      parseDateMs(
        firstDefined(b?.updated_at, b?.resolved_at, b?.requested_at, b?.created_at),
      )
    ) * -1;
  }

  function getRunDepartmentKey(run) {
    if (!run) return "unknown";

    return normalizeDepartmentKey(
      firstDefined(
        run.department_key,
        run.departmentKey,
        run.department?.key,
        run.department?.slug,
        run.seat?.department_key,
        run.seat?.departmentKey,
        run.context?.department_key,
        run.context?.departmentKey,
        run.result?.department_key,
        run.result?.departmentKey,
        run.operator?.department_key,
        run.operator?.departmentKey,
      ),
    );
  }

  function getRunId(run) {
    return firstNonEmptyString(
      run?.id,
      run?.queue_item_id,
      run?.queueItemId,
      run?.run_id,
      run?.runtime_run_id,
    );
  }

  function getRunStatus(run) {
    return firstNonEmptyString(
      run?.status,
      run?.state,
      run?.runtime_status,
      "unknown",
    );
  }

  function getRunWorkflowLabel(run) {
    if (!run) return "Workflow";

    return (
      firstNonEmptyString(
        run.workflow_name,
        run.workflow_label,
        run.workflow_title,
        run.workflow_id,
        run.operator_name,
        run.operator_label,
        run.operator_id,
        run.result?.title,
        run.title,
        run.name,
      ) || "Workflow"
    );
  }

  function getRunAgentLabel(run) {
    if (!run) return "Unknown agent";

    return (
      firstNonEmptyString(
        run.agent_label,
        run.agent_name,
        run.agent_id,
        run.operator_label,
        run.operator_name,
        run.operator_id,
        run.requested_by,
        run.assignee,
        run.result?.agent_label,
      ) || `${getDepartmentLabel(getRunDepartmentKey(run))} Agent`
    );
  }

  function getApprovalDepartmentKey(item) {
    if (!item) return "unknown";

    return normalizeDepartmentKey(
      firstDefined(
        item.department_key,
        item.departmentKey,
        item.department?.key,
        item.department?.slug,
        item.context?.department_key,
        item.context?.departmentKey,
      ),
    );
  }

  function getApprovalRunId(item) {
    return firstNonEmptyString(
      item?.run_id,
      item?.queue_item_id,
      item?.runtime_run_id,
    );
  }

  function getSnapshotSummary(snapshot) {
    if (!isRecord(snapshot)) return {};
    return isRecord(snapshot.summary) ? snapshot.summary : {};
  }

  function getSnapshotWorkspace(snapshot) {
    if (!isRecord(snapshot)) return {};
    if (isRecord(snapshot.workspace)) return snapshot.workspace;
    const summary = getSnapshotSummary(snapshot);
    if (isRecord(summary.workspace)) return summary.workspace;
    if (isRecord(summary.business)) return summary.business;
    return {};
  }

  function getSnapshotPulse(snapshot) {
    if (!isRecord(snapshot)) return {};
    if (isRecord(snapshot.pulse)) return snapshot.pulse;
    const summary = getSnapshotSummary(snapshot);
    if (isRecord(summary.pulse)) return summary.pulse;
    return {};
  }

  function getSnapshotCenter(snapshot) {
    if (!isRecord(snapshot)) return {};
    if (isRecord(snapshot.center)) return snapshot.center;
    const summary = getSnapshotSummary(snapshot);
    if (isRecord(summary.center)) return summary.center;
    return {};
  }

  function getSnapshotRuntime(snapshot) {
    if (!isRecord(snapshot)) return {};
    if (isRecord(snapshot.runtime)) return snapshot.runtime;
    const summary = getSnapshotSummary(snapshot);
    if (isRecord(summary.runtime)) return summary.runtime;
    return {};
  }

  function getSnapshotTopology(snapshot) {
    if (!isRecord(snapshot)) return { nodes: [], edges: [] };

    const topology = isRecord(snapshot.topology)
      ? snapshot.topology
      : isRecord(snapshot.summary?.topology)
        ? snapshot.summary.topology
        : {};

    return {
      nodes: safeArray(topology.nodes),
      edges: safeArray(topology.edges),
    };
  }

  function getSnapshotFloors(snapshot) {
    if (!isRecord(snapshot)) return {};
    if (isRecord(snapshot.floors)) return snapshot.floors;
    const summary = getSnapshotSummary(snapshot);
    if (isRecord(summary.floors)) return summary.floors;
    return {};
  }

  function getSnapshotSeats(snapshot) {
    if (!isRecord(snapshot)) return [];
    if (Array.isArray(snapshot.seats)) return snapshot.seats;
    const summary = getSnapshotSummary(snapshot);
    if (Array.isArray(summary.seats)) return summary.seats;
    return [];
  }

  function getSnapshotDepartments(snapshot) {
    if (!isRecord(snapshot)) return [];
    if (Array.isArray(snapshot.departments)) return snapshot.departments;
    const summary = getSnapshotSummary(snapshot);
    if (Array.isArray(summary.departments)) return summary.departments;
    return [];
  }

  function getSnapshotBindingsByCategory(snapshot) {
    if (!isRecord(snapshot)) return {};
    if (isRecord(snapshot.bindingsByCategory)) return snapshot.bindingsByCategory;
    if (isRecord(snapshot.bindings_by_category)) return snapshot.bindings_by_category;
    const summary = getSnapshotSummary(snapshot);
    if (isRecord(summary.bindingsByCategory)) return summary.bindingsByCategory;
    if (isRecord(summary.bindings_by_category)) return summary.bindings_by_category;
    return {};
  }

  function flattenBindings(bindingsByCategory) {
    const grouped = isRecord(bindingsByCategory) ? bindingsByCategory : {};
    return Object.keys(grouped).flatMap((key) =>
      safeArray(grouped[key]).map((item) => ({
        ...item,
        category: item?.category || key,
      })),
    );
  }

  function getSnapshotBindings(snapshot) {
    const flattened = flattenBindings(getSnapshotBindingsByCategory(snapshot));
    if (flattened.length) return flattened;

    if (!isRecord(snapshot)) return [];
    if (Array.isArray(snapshot.containerBindings)) return snapshot.containerBindings;
    if (Array.isArray(snapshot.container_bindings)) return snapshot.container_bindings;

    const summary = getSnapshotSummary(snapshot);
    if (Array.isArray(summary.containerBindings)) return summary.containerBindings;
    if (Array.isArray(summary.container_bindings)) return summary.container_bindings;

    return [];
  }

  function getSnapshotRuns(snapshot) {
    const runtime = getSnapshotRuntime(snapshot);
    if (Array.isArray(runtime.runs)) return runtime.runs;
    if (Array.isArray(snapshot?.runs)) return snapshot.runs;
    if (Array.isArray(snapshot?.summary?.runs)) return snapshot.summary.runs;
    return [];
  }

  function getSnapshotApprovals(snapshot) {
    const runtime = getSnapshotRuntime(snapshot);
    if (Array.isArray(runtime.approvals)) return runtime.approvals;
    if (Array.isArray(snapshot?.approvals)) return snapshot.approvals;
    if (Array.isArray(snapshot?.summary?.approvals)) return snapshot.summary.approvals;
    return [];
  }

  function groupRunsByDepartment(runs) {
    const grouped = {};
    safeArray(runs).forEach((run) => {
      const key = getRunDepartmentKey(run);
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(run);
    });
    return grouped;
  }

  function groupApprovalsByDepartment(approvals) {
    const grouped = {};
    safeArray(approvals).forEach((item) => {
      const key = getApprovalDepartmentKey(item);
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(item);
    });
    return grouped;
  }

  function getSeatDepartmentKey(seat) {
    return normalizeDepartmentKey(
      firstDefined(
        seat?.departmentKey,
        seat?.department_key,
        seat?.department?.key,
        seat?.department?.slug,
        seat?.key,
        seat?.slug,
        seat?.id,
      ),
    );
  }

  function getDepartmentRecordKey(item) {
    return normalizeDepartmentKey(
      firstDefined(
        item?.key,
        item?.departmentKey,
        item?.department_key,
        item?.slug,
        item?.id,
      ),
    );
  }

  function getSeatById(snapshotOrSeats, seatId) {
    const seats = Array.isArray(snapshotOrSeats)
      ? snapshotOrSeats
      : getSnapshotSeats(snapshotOrSeats);

    const wanted = String(seatId || "").trim();
    if (!wanted) return null;

    return (
      seats.find((seat) => String(seat?.id || "") === wanted) || null
    );
  }

  function getSeatByDepartmentKey(snapshotOrSeats, departmentKey) {
    const seats = Array.isArray(snapshotOrSeats)
      ? snapshotOrSeats
      : getSnapshotSeats(snapshotOrSeats);

    const normalized = normalizeDepartmentKey(departmentKey);

    return (
      seats.find((seat) => getSeatDepartmentKey(seat) === normalized) ||
      seats.find((seat) => String(seat?.id || "").toLowerCase() === String(getSeatIdForDepartment(normalized) || "").toLowerCase()) ||
      null
    );
  }

  function getDepartmentRecordByKey(snapshotOrDepartments, departmentKey) {
    const departments = Array.isArray(snapshotOrDepartments)
      ? snapshotOrDepartments
      : getSnapshotDepartments(snapshotOrDepartments);

    const normalized = normalizeDepartmentKey(departmentKey);

    return (
      departments.find((item) => getDepartmentRecordKey(item) === normalized) ||
      null
    );
  }

  function getFloorByDepartmentKey(snapshot, departmentKey) {
    const floors = getSnapshotFloors(snapshot);
    const normalized = normalizeDepartmentKey(departmentKey);
    return floors?.[normalized] || null;
  }

  function getTopologyNodesByDepartment(snapshot, departmentKey) {
    const normalized = normalizeDepartmentKey(departmentKey);
    return getSnapshotTopology(snapshot).nodes.filter((node) => {
      return normalizeDepartmentKey(
        firstDefined(
          node?.department_key,
          node?.departmentKey,
          node?.department?.key,
          node?.department?.slug,
          node?.zone,
        ),
      ) === normalized;
    });
  }

  function getTopologyEdgesByDepartment(snapshot, departmentKey) {
    const normalized = normalizeDepartmentKey(departmentKey);
    return getSnapshotTopology(snapshot).edges.filter((edge) => {
      return normalizeDepartmentKey(
        firstDefined(
          edge?.department_key,
          edge?.departmentKey,
          edge?.department?.key,
          edge?.department?.slug,
          edge?.zone,
        ),
      ) === normalized;
    });
  }

  function getPrimaryAgentForRuns(runs, departmentKey) {
    const counts = {};
    let latestRun = null;

    safeArray(runs).forEach((run) => {
      const label = getRunAgentLabel(run);
      if (!counts[label]) {
        counts[label] = {
          id: firstNonEmptyString(
            run?.agent_id,
            run?.operator_id,
            label.toLowerCase().replace(/\s+/g, "_"),
          ),
          label,
          departmentKey,
          total: 0,
          queued: 0,
          running: 0,
          waitingApproval: 0,
          failed: 0,
          completed: 0,
          cancelled: 0,
          latestRun: null,
        };
      }

      const status = getRunStatus(run);
      const bucket = counts[label];
      bucket.total += 1;

      if (status === "queued") bucket.queued += 1;
      if (status === "running") bucket.running += 1;
      if (status === "waiting_approval") bucket.waitingApproval += 1;
      if (status === "failed") bucket.failed += 1;
      if (status === "completed") bucket.completed += 1;
      if (status === "cancelled") bucket.cancelled += 1;

      if (
        !bucket.latestRun ||
        sortRunsNewestFirst(run, bucket.latestRun) < 0
      ) {
        bucket.latestRun = run;
      }

      if (!latestRun || sortRunsNewestFirst(run, latestRun) < 0) {
        latestRun = run;
      }
    });

    const ranked = Object.values(counts).sort((a, b) => {
      if (b.total !== a.total) return b.total - a.total;
      return sortRunsNewestFirst(a.latestRun, b.latestRun);
    });

    return ranked[0] || {
      id: `${departmentKey}_agent`,
      label: `${getDepartmentLabel(departmentKey)} Agent`,
      departmentKey,
      total: 0,
      queued: 0,
      running: 0,
      waitingApproval: 0,
      failed: 0,
      completed: 0,
      cancelled: 0,
      latestRun,
    };
  }

  function buildDepartmentRuntimeFromSnapshot(snapshot, departmentKey) {
    const normalizedKey = normalizeDepartmentKey(departmentKey);
    const runs = getSnapshotRuns(snapshot);
    const approvals = getSnapshotApprovals(snapshot);
    const pulse = getSnapshotPulse(snapshot);
    const center = getSnapshotCenter(snapshot);
    const seat = getSeatByDepartmentKey(snapshot, normalizedKey);
    const floor = getFloorByDepartmentKey(snapshot, normalizedKey);
    const department = getDepartmentRecordByKey(snapshot, normalizedKey);

    const departmentRuns = safeArray(runs)
      .filter((run) => getRunDepartmentKey(run) === normalizedKey)
      .slice()
      .sort(sortRunsNewestFirst);

    const departmentApprovals = safeArray(approvals)
      .filter((item) => getApprovalDepartmentKey(item) === normalizedKey)
      .slice()
      .sort(sortItemsNewestFirst);

    const pendingApprovals = departmentApprovals.filter(
      (item) => String(item?.status || "").toLowerCase() === "pending",
    ).length;

    const queued = departmentRuns.filter((run) => getRunStatus(run) === "queued").length;
    const running = departmentRuns.filter((run) => getRunStatus(run) === "running").length;
    const waitingApproval = departmentRuns.filter(
      (run) => getRunStatus(run) === "waiting_approval",
    ).length;
    const failed = departmentRuns.filter((run) => getRunStatus(run) === "failed").length;
    const completed = departmentRuns.filter((run) => getRunStatus(run) === "completed").length;
    const cancelled = departmentRuns.filter((run) => getRunStatus(run) === "cancelled").length;

    const primaryAgent = getPrimaryAgentForRuns(departmentRuns, normalizedKey);

    return {
      key: normalizedKey,
      label:
        firstNonEmptyString(
          seat?.label,
          department?.label,
          department?.name,
          getDepartmentLabel(normalizedKey),
        ) || getDepartmentLabel(normalizedKey),
      seatId: firstNonEmptyString(seat?.id, getSeatIdForDepartment(normalizedKey)),
      totalRuns: departmentRuns.length,
      queued,
      running,
      waitingApproval,
      failed,
      completed,
      cancelled,
      pendingApprovals,
      latestRun: departmentRuns[0] || null,
      agentCount: Array.from(
        new Set(departmentRuns.map((run) => getRunAgentLabel(run)).filter(Boolean)),
      ).length,
      primaryAgent,
      runs: departmentRuns,
      approvals: departmentApprovals,
      seat: seat || null,
      department: department || null,
      floor: floor || null,
      topologyNodes: getTopologyNodesByDepartment(snapshot, normalizedKey),
      topologyEdges: getTopologyEdgesByDepartment(snapshot, normalizedKey),
      pulse: pulse,
      center: center,
    };
  }

  function getDepartmentRuntime(runs, approvals, departmentKey) {
    const normalizedKey = normalizeDepartmentKey(departmentKey);
    const departmentRuns = safeArray(runs)
      .filter((run) => getRunDepartmentKey(run) === normalizedKey)
      .slice()
      .sort(sortRunsNewestFirst);

    const departmentApprovals = safeArray(approvals)
      .filter((item) => getApprovalDepartmentKey(item) === normalizedKey)
      .slice()
      .sort(sortItemsNewestFirst);

    const pendingApprovals = departmentApprovals.filter(
      (item) => String(item?.status || "").toLowerCase() === "pending",
    ).length;

    const queued = departmentRuns.filter((run) => getRunStatus(run) === "queued").length;
    const running = departmentRuns.filter((run) => getRunStatus(run) === "running").length;
    const waitingApproval = departmentRuns.filter(
      (run) => getRunStatus(run) === "waiting_approval",
    ).length;
    const failed = departmentRuns.filter((run) => getRunStatus(run) === "failed").length;
    const completed = departmentRuns.filter((run) => getRunStatus(run) === "completed").length;
    const cancelled = departmentRuns.filter((run) => getRunStatus(run) === "cancelled").length;

    const primaryAgent = getPrimaryAgentForRuns(departmentRuns, normalizedKey);

    return {
      key: normalizedKey,
      label: getDepartmentLabel(normalizedKey),
      seatId: getSeatIdForDepartment(normalizedKey),
      totalRuns: departmentRuns.length,
      queued,
      running,
      waitingApproval,
      failed,
      completed,
      cancelled,
      pendingApprovals,
      latestRun: departmentRuns[0] || null,
      agentCount: Array.from(
        new Set(departmentRuns.map((run) => getRunAgentLabel(run)).filter(Boolean)),
      ).length,
      primaryAgent,
      runs: departmentRuns,
      approvals: departmentApprovals,
    };
  }

  function getDepartmentRuntimeList(runs, approvals) {
    const runGroups = groupRunsByDepartment(runs);
    const approvalGroups = groupApprovalsByDepartment(approvals);

    const keys = Array.from(
      new Set([
        ...Object.keys(DEPARTMENT_META),
        ...Object.keys(runGroups),
        ...Object.keys(approvalGroups),
      ]),
    );

    return keys
      .map((key) => getDepartmentRuntime(runs, approvals, key))
      .filter((item) => {
        return (
          item.totalRuns > 0 ||
          item.pendingApprovals > 0 ||
          Object.prototype.hasOwnProperty.call(DEPARTMENT_META, item.key)
        );
      })
      .sort((a, b) => {
        const aWeight = a.totalRuns + a.pendingApprovals;
        const bWeight = b.totalRuns + b.pendingApprovals;
        if (bWeight !== aWeight) return bWeight - aWeight;
        return a.label.localeCompare(b.label);
      });
  }

  function getDepartmentRuntimeListFromSnapshot(snapshot) {
    const seats = getSnapshotSeats(snapshot);
    const departments = getSnapshotDepartments(snapshot);
    const floors = getSnapshotFloors(snapshot);
    const runs = getSnapshotRuns(snapshot);
    const approvals = getSnapshotApprovals(snapshot);

    const seatKeys = seats.map((seat) => getSeatDepartmentKey(seat));
    const departmentKeys = departments.map((item) => getDepartmentRecordKey(item));
    const floorKeys = Object.keys(floors || {}).map((key) => normalizeDepartmentKey(key));
    const runKeys = safeArray(runs).map((run) => getRunDepartmentKey(run));
    const approvalKeys = safeArray(approvals).map((item) => getApprovalDepartmentKey(item));

    const keys = Array.from(
      new Set([
        ...Object.keys(DEPARTMENT_META),
        ...seatKeys,
        ...departmentKeys,
        ...floorKeys,
        ...runKeys,
        ...approvalKeys,
      ].filter(Boolean)),
    );

    return keys
      .map((key) => buildDepartmentRuntimeFromSnapshot(snapshot, key))
      .filter((item) => {
        return (
          item.totalRuns > 0 ||
          item.pendingApprovals > 0 ||
          !!item.seat ||
          !!item.department ||
          !!item.floor ||
          Object.prototype.hasOwnProperty.call(DEPARTMENT_META, item.key)
        );
      })
      .sort((a, b) => {
        const aWeight =
          a.totalRuns +
          a.pendingApprovals +
          (a.seat ? 1 : 0) +
          (a.floor ? 1 : 0) +
          (a.department ? 1 : 0);
        const bWeight =
          b.totalRuns +
          b.pendingApprovals +
          (b.seat ? 1 : 0) +
          (b.floor ? 1 : 0) +
          (b.department ? 1 : 0);

        if (bWeight !== aWeight) return bWeight - aWeight;
        return a.label.localeCompare(b.label);
      });
  }

  function getRecentDepartmentRuns(runs, approvals, departmentKey, limit) {
    const runtime = getDepartmentRuntime(runs, approvals, departmentKey);
    return runtime.runs.slice(0, Math.max(1, limit || 4));
  }

  function getRecentDepartmentRunsFromSnapshot(snapshot, departmentKey, limit) {
    const runtime = buildDepartmentRuntimeFromSnapshot(snapshot, departmentKey);
    return runtime.runs.slice(0, Math.max(1, limit || 4));
  }

  function getDepartmentExceptions(runs, limit) {
    return safeArray(runs)
      .filter((run) => {
        const status = getRunStatus(run);
        return status === "failed" || status === "waiting_approval";
      })
      .slice()
      .sort(sortRunsNewestFirst)
      .slice(0, Math.max(1, limit || 10));
  }

  function getDepartmentExceptionsFromSnapshot(snapshot, limit) {
    return getDepartmentExceptions(getSnapshotRuns(snapshot), limit);
  }

  function getBindingsCountByCategory(snapshot) {
    const grouped = getSnapshotBindingsByCategory(snapshot);
    const out = {};
    Object.keys(grouped).forEach((key) => {
      out[key] = safeArray(grouped[key]).length;
    });
    return out;
  }

  function getWorkspaceDisplay(snapshot) {
    const workspace = getSnapshotWorkspace(snapshot);
    return {
      id: firstNonEmptyString(
        workspace?.id,
        workspace?.workspace_id,
        workspace?.slug,
        snapshot?.workspaceId,
      ),
      name: firstNonEmptyString(
        workspace?.name,
        workspace?.title,
        workspace?.slug,
        snapshot?.workspaceId,
        "Workspace",
      ),
      subtitle: firstNonEmptyString(
        workspace?.business_type,
        workspace?.industry,
        workspace?.category,
        workspace?.slug,
        "Local runtime",
      ),
    };
  }

  function buildBoardroomMetrics(snapshot) {
    const pulse = getSnapshotPulse(snapshot);
    const center = getSnapshotCenter(snapshot);
    const runtime = getSnapshotRuntime(snapshot);
    const runs = getSnapshotRuns(snapshot);
    const approvals = getSnapshotApprovals(snapshot);

    return {
      cashOnHand: firstDefined(pulse?.cash?.onHand, pulse?.cash?.on_hand, center?.cash),
      revenue: firstDefined(pulse?.sales?.revenue, center?.revenue),
      backlog: firstDefined(pulse?.ops?.backlog, center?.pipeline),
      grossMarginPct: firstDefined(pulse?.finance?.grossMarginPct, pulse?.finance?.gross_margin_pct),
      debtorDays: firstDefined(pulse?.finance?.debtorDays, pulse?.finance?.debtor_days),
      creditorDays: firstDefined(pulse?.finance?.creditorDays, pulse?.finance?.creditor_days),
      stockValue: firstDefined(pulse?.stock?.value),
      stockDaysCover: firstDefined(pulse?.stock?.daysCover, pulse?.stock?.days_cover),
      cashRisk: firstNonEmptyString(pulse?.risk?.cash, center?.health),
      nodeStatus: firstNonEmptyString(runtime?.node?.status),
      runsTotal: safeArray(runs).length,
      approvalsPending: safeArray(approvals).filter(
        (item) => String(item?.status || "").toLowerCase() === "pending",
      ).length,
    };
  }

  global.TessarisDesktopRuntimeShared = {
    normalizeDepartmentKey,
    getDepartmentMeta,
    getDepartmentLabel,
    getSeatIdForDepartment,
    getRunDepartmentKey,
    getRunId,
    getRunStatus,
    getRunWorkflowLabel,
    getRunAgentLabel,
    getApprovalDepartmentKey,
    getApprovalRunId,
    getDepartmentRuntime,
    getDepartmentRuntimeList,
    getDepartmentRuntimeListFromSnapshot,
    getRecentDepartmentRuns,
    getRecentDepartmentRunsFromSnapshot,
    getDepartmentExceptions,
    getDepartmentExceptionsFromSnapshot,
    getSeatById,
    getSeatByDepartmentKey,
    getDepartmentRecordByKey,
    getFloorByDepartmentKey,
    getSnapshotSummary,
    getSnapshotWorkspace,
    getSnapshotPulse,
    getSnapshotCenter,
    getSnapshotRuntime,
    getSnapshotTopology,
    getSnapshotFloors,
    getSnapshotSeats,
    getSnapshotDepartments,
    getSnapshotBindingsByCategory,
    getSnapshotBindings,
    getSnapshotRuns,
    getSnapshotApprovals,
    getTopologyNodesByDepartment,
    getTopologyEdgesByDepartment,
    getBindingsCountByCategory,
    getWorkspaceDisplay,
    buildBoardroomMetrics,
    clone,
  };
})(window);