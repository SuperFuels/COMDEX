(function initTessarisDesktopRuntimeAdapter(global) {
  const contracts = global.TessarisDesktopContracts;
  const cache = global.TessarisDesktopCache;
  const liveAgentsRuntime = global.TessarisDesktopLiveAgentsRuntime;

  if (!contracts) {
    throw new Error(
      "TessarisDesktopContracts must load before desktop-runtime-adapter.js",
    );
  }

  if (!cache) {
    throw new Error(
      "TessarisDesktopCache must load before desktop-runtime-adapter.js",
    );
  }

  function resolveDeps(deps) {
    const {
      state,
      desktopStore,
      render,
      normalizeBindingsByCategory,
    } = deps || {};

    if (!state) {
      throw new Error("desktop-runtime-adapter requires deps.state");
    }

    if (!desktopStore) {
      throw new Error("desktop-runtime-adapter requires deps.desktopStore");
    }

    if (typeof render !== "function") {
      throw new Error("desktop-runtime-adapter requires deps.render");
    }

    return {
      state,
      desktopStore,
      render,
      normalizeBindingsByCategory:
        typeof normalizeBindingsByCategory === "function"
          ? normalizeBindingsByCategory
          : function fallbackNormalizeBindingsByCategory(bindings) {
              const grouped = {};
              (Array.isArray(bindings) ? bindings : []).forEach((binding) => {
                const category = binding?.category || "uncategorized";
                if (!grouped[category]) grouped[category] = [];
                grouped[category].push(binding);
              });
              return grouped;
            },
    };
  }

  function normalizeBaseUrl(value, fallback) {
    return cache.normalizeBaseUrl(value, fallback);
  }

  function isRecord(value) {
    return !!value && typeof value === "object" && !Array.isArray(value);
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
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

  function getItemsPayload(value, fallback) {
    if (Array.isArray(value?.items)) return value.items;
    if (Array.isArray(value)) return value;
    return Array.isArray(fallback) ? fallback : [];
  }

  function getSummaryPayload(value, fallback) {
    if (value && value.summary !== undefined) return value.summary;
    return value !== undefined ? value : fallback;
  }

  function getItemPayload(value, fallback) {
    if (value && value.item !== undefined) return value.item;
    return value !== undefined ? value : fallback;
  }

  function getSchedulerPayload(value, fallback) {
    if (value && value.scheduler !== undefined) return value.scheduler;
    return value !== undefined ? value : fallback;
  }

  function isBackendHealthy(status) {
    return !!(
      status &&
      (
        status.ok === true ||
        status.healthy === true ||
        status.status === "running" ||
        status.status === "ready" ||
        status?.control?.status === "running"
      )
    );
  }

  function normalizeDashboardSummary(value, workspaceId, nodeId) {
    if (typeof contracts.normalizeDashboardSummary === "function") {
      return contracts.normalizeDashboardSummary(value, workspaceId, nodeId);
    }

    return value ?? null;
  }

  function normalizeMarketingSummary(value, fallback) {
    if (typeof contracts.normalizeMarketingSummary === "function") {
      return contracts.normalizeMarketingSummary(value);
    }

    return value ?? fallback ?? null;
  }

  function normalizeBrandFoundationState(value, fallback) {
    if (typeof contracts.normalizeBrandFoundationState === "function") {
      return contracts.normalizeBrandFoundationState(value);
    }

    return value ?? fallback ?? null;
  }

  function normalizeRecoveryPayload(value) {
    if (typeof contracts.normalizeRecoveryPayload === "function") {
      return contracts.normalizeRecoveryPayload(value);
    }

    return value;
  }

  function buildDefaultBoardroomSnapshot(workspaceId) {
    if (typeof contracts.buildDefaultBoardroomSnapshot === "function") {
      return contracts.buildDefaultBoardroomSnapshot(workspaceId);
    }

    return {
      workspaceId,
      viewMode: "dashboard",
      activeZone: "coo",
      selectedSeatId: "seat_coo",
      selectedInspectorTarget: { kind: "seat", seatId: "seat_coo" },
      summary: null,
      workspace: null,
      center: null,
      pulse: null,
      seats: [],
      departments: [],
      floors: {},
      runtime: { node: null, approvals: [], runs: [] },
      topology: { nodes: [], edges: [] },
      bindingsByCategory: {},
      updatedAt: null,
    };
  }

  function deriveBoardroomWorkspace(value, workspaceId, fallback) {
    const resolved =
      value?.workspace ||
      value?.summary?.workspace ||
      fallback?.workspace ||
      null;

    if (isRecord(resolved)) {
      return clone(resolved);
    }

    return {
      id: workspaceId,
      slug: workspaceId,
      name: workspaceId,
    };
  }

  function deriveBoardroomCenter(value, fallback) {
    const resolved =
      value?.center ||
      value?.summary?.center ||
      fallback?.center ||
      null;

    return isRecord(resolved) ? clone(resolved) : {};
  }

  function deriveBoardroomPulse(value, fallback) {
    const resolved =
      value?.pulse ||
      value?.summary?.pulse ||
      fallback?.pulse ||
      null;

    return isRecord(resolved) ? clone(resolved) : {};
  }

  function deriveBoardroomSeats(value, fallback) {
    const resolved =
      value?.seats ||
      value?.summary?.seats ||
      fallback?.seats ||
      [];

    return safeArray(resolved).map(clone);
  }

  function deriveBoardroomDepartments(value, fallback) {
    const resolved =
      value?.departments ||
      value?.summary?.departments ||
      fallback?.departments ||
      [];

    return safeArray(resolved).map(clone);
  }

  function deriveBoardroomFloors(value, fallback) {
    const resolved =
      value?.floors ||
      value?.summary?.floors ||
      fallback?.floors ||
      {};

    return isRecord(resolved) ? clone(resolved) : {};
  }

  function deriveBoardroomRuntime(value, runs, approvals, status, fallback) {
    const runtimeSource =
      value?.runtime ||
      value?.summary?.runtime ||
      fallback?.runtime ||
      {};

    const runtime = isRecord(runtimeSource) ? clone(runtimeSource) : {};

    runtime.node = isRecord(runtime.node)
      ? runtime.node
      : isRecord(status?.control)
        ? clone(status.control)
        : isRecord(status)
          ? {
              status: status.status || (status.healthy ? "ready" : "unknown"),
              mode: status.mode || status?.config?.mode || "local_first",
              lastHeartbeatAt:
                status.last_heartbeat_at ||
                status.lastHeartbeatAt ||
                null,
            }
          : null;

    runtime.runs = safeArray(runs).map(clone);
    runtime.approvals = safeArray(approvals).map(clone);

    return runtime;
  }

  function deriveBoardroomTopology(value, fallback) {
    const resolved =
      value?.topology ||
      value?.summary?.topology ||
      fallback?.topology ||
      {};

    return {
      nodes: safeArray(resolved?.nodes).map(clone),
      edges: safeArray(resolved?.edges).map(clone),
    };
  }

  function normalizeBoardroomSnapshot(
    value,
    workspaceId,
    state,
    bindingsByCategory,
    refreshedAt,
    runs,
    approvals,
    status,
  ) {
    const fallback =
      isRecord(state.boardroomSnapshot)
        ? state.boardroomSnapshot
        : buildDefaultBoardroomSnapshot(workspaceId);

    const source = isRecord(value) ? value : {};

    const merged = {
      ...clone(fallback),
      ...clone(source),
      workspaceId,
      viewMode:
        state.boardroomViewMode ||
        source.viewMode ||
        fallback.viewMode ||
        "dashboard",
      activeZone:
        source.active_zone ??
        source.activeZone ??
        state.activeZone ??
        fallback.activeZone ??
        "coo",
      selectedSeatId:
        source.selected_seat_id ??
        source.selectedSeatId ??
        state.selectedSeatId ??
        fallback.selectedSeatId ??
        null,
      selectedInspectorTarget:
        source.selected_inspector_target ??
        source.selectedInspectorTarget ??
        state.selectedInspectorTarget ??
        fallback.selectedInspectorTarget ??
        null,
      summary:
        source.summary !== undefined
          ? clone(source.summary)
          : clone(source),
      workspace: deriveBoardroomWorkspace(source, workspaceId, fallback),
      center: deriveBoardroomCenter(source, fallback),
      pulse: deriveBoardroomPulse(source, fallback),
      seats: deriveBoardroomSeats(source, fallback),
      departments: deriveBoardroomDepartments(source, fallback),
      floors: deriveBoardroomFloors(source, fallback),
      runtime: deriveBoardroomRuntime(
        source,
        runs,
        approvals,
        status,
        fallback,
      ),
      topology: deriveBoardroomTopology(source, fallback),
      bindingsByCategory: clone(bindingsByCategory || {}),
      updatedAt: source.updatedAt || source.updated_at || refreshedAt,
    };

    if (typeof contracts.normalizeBoardroomSnapshot === "function") {
      return contracts.normalizeBoardroomSnapshot(merged, workspaceId);
    }

    return merged;
  }

  function normalizeLiveAgentsSnapshot(nextState, refreshedAt) {
    if (typeof contracts.buildLiveAgentsSnapshot === "function") {
      return contracts.buildLiveAgentsSnapshot({
        runs: nextState.runs,
        approvals: nextState.approvals,
        selectedLiveAgentId: nextState.selectedLiveAgentId,
        selectedLiveRunId: nextState.selectedLiveRunId,
        liveAgentsReplayOpen: nextState.liveAgentsReplayOpen,
        liveAgentsView: nextState.liveAgentsView,
        activeZone: nextState.activeZone,
        updatedAt: refreshedAt,
      });
    }

    return {
      runs: safeArray(nextState.runs).map(clone),
      approvals: safeArray(nextState.approvals).map(clone),
      selectedLiveAgentId: nextState.selectedLiveAgentId ?? null,
      selectedLiveRunId: nextState.selectedLiveRunId ?? null,
      liveAgentsReplayOpen: nextState.liveAgentsReplayOpen === true,
      liveAgentsView: nextState.liveAgentsView || "stream",
      activeZone: nextState.activeZone || "coo",
      updatedAt: refreshedAt,
    };
  }

  function normalizeOperationsFlowSnapshot(nextState, refreshedAt) {
    if (typeof contracts.buildOperationsFlowSnapshot === "function") {
      return contracts.buildOperationsFlowSnapshot({
        boardroomSnapshot: nextState.boardroomSnapshot,
        containerBindings: nextState.containerBindings,
        operationsFlowViewMode: nextState.operationsFlowViewMode,
        activeZone: nextState.activeZone,
        selectedSeatId: nextState.selectedSeatId,
        selectedInspectorTarget: nextState.selectedInspectorTarget,
        updatedAt: refreshedAt,
      });
    }

    return {
      viewMode: nextState.operationsFlowViewMode || "flat",
      activeZone: nextState.activeZone || "operations",
      selectedSeatId: nextState.selectedSeatId ?? null,
      selectedInspectorTarget: clone(nextState.selectedInspectorTarget ?? null),
      boardroomSnapshot: clone(nextState.boardroomSnapshot ?? null),
      containerBindings: safeArray(nextState.containerBindings).map(clone),
      updatedAt: refreshedAt,
    };
  }

  function buildMarketingSummaryFromState(stateLike) {
    const runs = safeArray(stateLike?.runs).filter(
      (run) => String(run?.department_key || "").toLowerCase() === "marketing",
    );

    const approvals = safeArray(stateLike?.approvals).filter((item) => {
      const departmentKey = String(item?.department_key || "").toLowerCase();
      if (departmentKey === "marketing") return true;

      const approvalClass = String(item?.approval_class || "").toLowerCase();
      const title = String(item?.title || "").toLowerCase();
      return (
        approvalClass.includes("marketing") ||
        title.includes("marketing")
      );
    });

    const sortedRuns = runs
      .slice()
      .sort((a, b) => {
        const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
        const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
        return bTime - aTime;
      });

    const sortedApprovals = approvals
      .slice()
      .sort((a, b) => {
        const aTime = new Date(
          a?.resolved_at || a?.requested_at || a?.created_at || 0,
        ).getTime();
        const bTime = new Date(
          b?.resolved_at || b?.requested_at || b?.created_at || 0,
        ).getTime();
        return bTime - aTime;
      });

    const pendingApprovals = sortedApprovals.filter(
      (item) => String(item?.status || "").toLowerCase() === "pending",
    );

    const resolvedApprovals = sortedApprovals.filter((item) => {
      const status = String(item?.status || "").toLowerCase();
      return status === "approved" || status === "rejected";
    });

    return {
      counts: {
        total: sortedRuns.length,
        queued: sortedRuns.filter((run) => run?.status === "queued").length,
        running: sortedRuns.filter((run) => run?.status === "running").length,
        waiting_approval: sortedRuns.filter(
          (run) => run?.status === "waiting_approval",
        ).length,
        completed: sortedRuns.filter((run) => run?.status === "completed").length,
        failed: sortedRuns.filter((run) => run?.status === "failed").length,
        cancelled: sortedRuns.filter((run) => run?.status === "cancelled").length,
      },
      runs: sortedRuns,
      pending_approvals: pendingApprovals,
      resolved_approvals: resolvedApprovals,
      updated_at: stateLike?.lastRefreshAt || new Date().toISOString(),
    };
  }

  function mergeMarketingSummary(apiSummary, stateLike) {
    const fallbackSummary = buildMarketingSummaryFromState(stateLike);

    if (!isRecord(apiSummary)) {
      return fallbackSummary;
    }

    return {
      ...fallbackSummary,
      ...clone(apiSummary),
      counts: {
        ...fallbackSummary.counts,
        ...(isRecord(apiSummary.counts) ? clone(apiSummary.counts) : {}),
      },
      runs: fallbackSummary.runs,
      pending_approvals: fallbackSummary.pending_approvals,
      resolved_approvals: fallbackSummary.resolved_approvals,
      updated_at:
        apiSummary.updated_at ||
        apiSummary.updatedAt ||
        fallbackSummary.updated_at,
    };
  }

  function applyLiveAgentSelection(desktopStore, refreshedState, boardroomSnapshot) {
    if (
      !liveAgentsRuntime ||
      typeof liveAgentsRuntime.ensureLiveAgentSelection !== "function"
    ) {
      return;
    }

    const selectionResult =
      liveAgentsRuntime.ensureLiveAgentSelection(refreshedState, {
        preferredDepartmentKey:
          refreshedState.activeZone ||
          boardroomSnapshot?.activeZone ||
          "marketing",
      }) || {};

    const selectionUpdates = {};

    if (Object.prototype.hasOwnProperty.call(selectionResult, "activeZone")) {
      selectionUpdates.activeZone = selectionResult.activeZone;
    }

    if (
      Object.prototype.hasOwnProperty.call(
        selectionResult,
        "selectedLiveAgentId",
      )
    ) {
      selectionUpdates.selectedLiveAgentId =
        selectionResult.selectedLiveAgentId;
    }

    if (
      Object.prototype.hasOwnProperty.call(
        selectionResult,
        "selectedLiveRunId",
      )
    ) {
      selectionUpdates.selectedLiveRunId =
        selectionResult.selectedLiveRunId;
    }

    if (
      Object.prototype.hasOwnProperty.call(
        selectionResult,
        "liveAgentsReplayOpen",
      )
    ) {
      selectionUpdates.liveAgentsReplayOpen =
        selectionResult.liveAgentsReplayOpen;
    }

    if (
      Object.prototype.hasOwnProperty.call(
        selectionResult,
        "liveAgentsView",
      )
    ) {
      selectionUpdates.liveAgentsView =
        selectionResult.liveAgentsView;
    }

    if (
      Object.prototype.hasOwnProperty.call(
        selectionResult,
        "selectedSeatId",
      ) &&
      selectionResult.selectedSeatId !== undefined
    ) {
      selectionUpdates.selectedSeatId =
        selectionResult.selectedSeatId;
    }

    if (
      Object.prototype.hasOwnProperty.call(
        selectionResult,
        "selectedInspectorTarget",
      ) &&
      selectionResult.selectedInspectorTarget !== undefined
    ) {
      selectionUpdates.selectedInspectorTarget =
        selectionResult.selectedInspectorTarget;
    }

    if (Object.keys(selectionUpdates).length) {
      desktopStore.patch(selectionUpdates);
    }
  }

  async function apiGet(deps, path) {
    const { state } = resolveDeps(deps);

    const res = await fetch(`${state.apiBase}${path}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }

    return await res.json();
  }

  async function apiGetOptional(deps, path, fallback = null) {
    try {
      return await apiGet(deps, path);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : String(error);

      if (message.includes("404") || message.includes("Not Found")) {
        return fallback;
      }

      throw error;
    }
  }

  async function apiPost(deps, path, body) {
    const { state } = resolveDeps(deps);

    const res = await fetch(`${state.apiBase}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify(body ?? {}),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }

    return await res.json();
  }

  async function loadDesktopRecovery(deps) {
    try {
      const value = await apiGet(deps, "/api/local-node/recovery");
      return normalizeRecoveryPayload(value);
    } catch (_) {
      return null;
    }
  }

  async function bindWorkspace(deps, options = {}) {
    const { state, desktopStore, render } = resolveDeps(deps);

    const {
      skipInitialRefresh = false,
      preserveMessage = false,
      defaultApiBase = contracts.DEFAULTS.apiBase,
      defaultWebBase = contracts.DEFAULTS.webBase,
      defaultWorkspaceId = contracts.DEFAULTS.workspaceId,
      defaultNodeId = contracts.DEFAULTS.nodeId,
    } = options;

    const normalizedApiBase = normalizeBaseUrl(
      state.apiBase,
      defaultApiBase,
    );
    const normalizedWebBase = normalizeBaseUrl(
      state.webBase,
      defaultWebBase,
    );
    const resolvedWorkspaceId =
      global.AionBusinessContainerClient?.resolveBusinessId?.() ||
      global.__aionCanonicalBusinessId ||
      state.workspaceId ||
      defaultWorkspaceId;
    const resolvedNodeId = state.nodeId || defaultNodeId;

    desktopStore.patch({
      apiBase: normalizedApiBase,
      webBase: normalizedWebBase,
      workspaceId: resolvedWorkspaceId,
      nodeId: resolvedNodeId,
      bound: true,
      ...(preserveMessage
        ? {}
        : {
            message: `Workspace bound: ${resolvedWorkspaceId} · API ${normalizedApiBase}`,
            messageTone: "success",
          }),
    });

    desktopStore.persistBinding();
    desktopStore.persistCache();

    render();

    if (!skipInitialRefresh) {
      await refreshAll(deps);
    }
  }

  async function refreshAll(deps) {
    const {
      state,
      desktopStore,
      render,
      normalizeBindingsByCategory,
    } = resolveDeps(deps);

    desktopStore.patch({
      loading: true,
      message:
        state.backendReady === false
          ? "Refreshing desktop state while backend starts..."
          : state.message,
      messageTone:
        state.backendReady === false
          ? "neutral"
          : state.messageTone,
    });
    render();

    try {
      const canonicalWorkspaceId =
        global.AionBusinessContainerClient?.resolveBusinessId?.() ||
        global.__aionCanonicalBusinessId ||
        state.workspaceId;
      if (canonicalWorkspaceId && canonicalWorkspaceId !== state.workspaceId) {
        desktopStore.patch({ workspaceId: canonicalWorkspaceId });
      }
      const workspaceId = encodeURIComponent(canonicalWorkspaceId);

      const requests = await Promise.allSettled([
        apiGetOptional(deps, "/api/local-node/status", state.status),
        // The repository may contain years of large workflow payloads.  The
        // desktop only renders the recent activity list, so do not hydrate the
        // renderer with the unbounded archive at startup.
        apiGetOptional(deps, `/api/local-node/runs?limit=50&compact=true&workspace_id=${workspaceId}`, { items: state.runs || [] }),
        apiGetOptional(deps, `/api/local-node/approvals?workspace_id=${workspaceId}`, { items: state.approvals || [] }),
        apiGetOptional(deps, "/api/local-node/audit", { items: state.audit || [] }),
        apiGetOptional(deps, "/api/local-node/scheduler/status", state.scheduler),
        apiGetOptional(deps, "/api/local-node/dashboard/summary", null),
        apiGetOptional(deps, "/api/local-node/marketing/stream", null),
        apiGetOptional(
          deps,
          `/api/aion/business/brand-foundation/${workspaceId}`,
          null,
        ),
        apiGetOptional(
          deps,
          `/api/aion/business/boardroom/${workspaceId}`,
          null,
        ),
        apiGetOptional(
          deps,
          `/api/aion/business/container-bindings/${workspaceId}`,
          { items: [] },
        ),
      ]);

      const [
        statusRes,
        runsRes,
        approvalsRes,
        auditRes,
        schedulerRes,
        dashboardRes,
        marketingRes,
        brandFoundationRes,
        boardroomRes,
        bindingsRes,
      ] = requests;

      const status =
        statusRes.status === "fulfilled"
          ? statusRes.value
          : state.status;

      const backendHealthy = isBackendHealthy(status);

      const resolvedWorkspaceId =
        status?.config?.workspace_id ||
        state.workspaceId;

      const resolvedNodeId =
        status?.config?.node_id ||
        state.nodeId;

      const runs =
        runsRes.status === "fulfilled"
          ? getItemsPayload(runsRes.value, state.runs)
          : safeArray(state.runs);

      const approvals =
        approvalsRes.status === "fulfilled"
          ? getItemsPayload(approvalsRes.value, state.approvals)
          : safeArray(state.approvals);

      const audit =
        auditRes.status === "fulfilled"
          ? getItemsPayload(auditRes.value, state.audit)
          : safeArray(state.audit);

      const scheduler =
        schedulerRes.status === "fulfilled"
          ? getSchedulerPayload(schedulerRes.value, state.scheduler)
          : state.scheduler;

      const containerBindings =
        bindingsRes.status === "fulfilled"
          ? getItemsPayload(bindingsRes.value, state.containerBindings)
          : safeArray(state.containerBindings);

      const bindingsByCategory =
        normalizeBindingsByCategory(containerBindings);

      const refreshedAt = new Date().toISOString();

      const dashboardSummary =
        dashboardRes.status === "fulfilled"
          ? normalizeDashboardSummary(
              getSummaryPayload(dashboardRes.value, null),
              resolvedWorkspaceId,
              resolvedNodeId,
            )
          : state.dashboardSummary;

      const provisionalState = {
        ...state,
        runs,
        approvals,
        audit,
        scheduler,
        containerBindings,
        workspaceId: resolvedWorkspaceId,
        nodeId: resolvedNodeId,
        lastRefreshAt: refreshedAt,
      };

      const marketingSummaryFromApi =
        marketingRes.status === "fulfilled"
          ? normalizeMarketingSummary(
              getSummaryPayload(marketingRes.value, state.marketingSummary),
              state.marketingSummary,
            )
          : state.marketingSummary;

      const marketingSummary = mergeMarketingSummary(
        marketingSummaryFromApi,
        provisionalState,
      );

      const brandFoundationState =
        brandFoundationRes.status === "fulfilled"
          ? normalizeBrandFoundationState(
              getItemPayload(
                brandFoundationRes.value,
                state.brandFoundationState,
              ),
              state.brandFoundationState,
            )
          : state.brandFoundationState;

      const rawBoardroomValue =
        boardroomRes.status === "fulfilled"
          ? boardroomRes.value
          : state.boardroomSnapshot;

      const boardroomSnapshot = normalizeBoardroomSnapshot(
        rawBoardroomValue,
        resolvedWorkspaceId,
        state,
        bindingsByCategory,
        refreshedAt,
        runs,
        approvals,
        status,
      );

      const nextState = {
        ...state,
        runs,
        approvals,
        audit,
        scheduler,
        dashboardSummary,
        marketingSummary,
        brandFoundationState,
        containerBindings,
        workspaceId: resolvedWorkspaceId,
        nodeId: resolvedNodeId,
        boardroomSnapshot,
        lastRefreshAt: refreshedAt,
      };

      const payload = {
        status,
        runs,
        approvals,
        audit,
        scheduler,
        dashboardSummary,
        marketingSummary,
        brandFoundationState,
        containerBindings,
        workspaceId: resolvedWorkspaceId,
        nodeId: resolvedNodeId,
        backendReady: backendHealthy,
        backendStatus: backendHealthy
          ? "ready"
          : (status?.status || state.backendStatus || "starting"),
        message: backendHealthy
          ? "Local backend ready"
          : "Desktop shell refreshed",
        messageTone: backendHealthy ? "success" : "neutral",
        boardroomSnapshot,
        liveAgentsSnapshot: normalizeLiveAgentsSnapshot(nextState, refreshedAt),
        operationsFlowSnapshot: normalizeOperationsFlowSnapshot(
          nextState,
          refreshedAt,
        ),
        lastRefreshAt: refreshedAt,
      };

      desktopStore.applyRefreshPayload(payload);

      const refreshedState = desktopStore.state;

      const rebuiltMarketingSummary = mergeMarketingSummary(
        refreshedState.marketingSummary,
        refreshedState,
      );

      desktopStore.patch({
        marketingSummary: rebuiltMarketingSummary,
        liveAgentsSnapshot: normalizeLiveAgentsSnapshot(
          {
            ...refreshedState,
            marketingSummary: rebuiltMarketingSummary,
          },
          refreshedState.lastRefreshAt || refreshedAt,
        ),
        operationsFlowSnapshot: normalizeOperationsFlowSnapshot(
          {
            ...refreshedState,
            marketingSummary: rebuiltMarketingSummary,
          },
          refreshedState.lastRefreshAt || refreshedAt,
        ),
      });

      applyLiveAgentSelection(
        desktopStore,
        desktopStore.state,
        boardroomSnapshot,
      );

      desktopStore.persistCache();
    } catch (error) {
      desktopStore.patch({
        message: error instanceof Error ? error.message : "Refresh failed",
        messageTone: "error",
      });
    } finally {
      desktopStore.patch({ loading: false });
      render();
    }
  }

  async function runControl(deps, path, body) {
    const { desktopStore, render } = resolveDeps(deps);

    try {
      desktopStore.patch({ loading: true });
      render();

      await apiPost(deps, path, body);
      await refreshAll(deps);
    } catch (error) {
      desktopStore.patch({
        message: error instanceof Error ? error.message : "Action failed",
        messageTone: "error",
        loading: false,
      });
      render();
    }
  }

  global.TessarisDesktopRuntimeAdapter = {
    normalizeBaseUrl,
    apiGetOptional,
    apiGet,
    apiPost,
    loadDesktopRecovery,
    bindWorkspace,
    refreshAll,
    runControl,
  };
})(window);
