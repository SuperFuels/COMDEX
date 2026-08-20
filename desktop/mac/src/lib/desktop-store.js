(function initDesktopStore(global) {
  const contracts = global.TessarisDesktopContracts;
  const cache = global.TessarisDesktopCache;

  if (!contracts || !cache) {
    throw new Error(
      "TessarisDesktopContracts and TessarisDesktopCache are required before desktop-store.js",
    );
  }

  function cloneValue(value) {
    if (value == null) return value;

    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_) {
      return value;
    }
  }

  function ensureArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function ensureObject(value) {
    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : {};
  }

  function splitLines(value) {
    if (typeof contracts.splitLines === "function") {
      return contracts.splitLines(value);
    }

    return String(value || "")
      .split(/\n|,|•|·|\|/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  function normalizeMarketingForm(value) {
    if (typeof contracts.normalizeMarketingForm === "function") {
      return contracts.normalizeMarketingForm(value);
    }

    return {
      ...contracts.buildDefaultMarketingForm(),
      ...ensureObject(value),
    };
  }

  function normalizeBrandFoundationState(value, marketingForm) {
    if (typeof contracts.normalizeBrandFoundationState === "function") {
      return contracts.normalizeBrandFoundationState(value, marketingForm);
    }

    return {
      ...contracts.buildDefaultBrandFoundationState(marketingForm),
      ...ensureObject(value),
    };
  }

  function getBrandMapFromBrand(brandFoundationState) {
    const brand = ensureObject(brandFoundationState);

    return ensureObject(
      brand.brandIntelligenceMap ||
        brand.brand_intelligence_map ||
        brand.brandMap ||
        brand.brand_map ||
        brand.map ||
        {},
    );
  }

  function getBrandMap(state) {
    return getBrandMapFromBrand(state?.brandFoundationState);
  }

  function setBrandMapOnBrand(brand, nextMap) {
    return {
      ...brand,
      brandIntelligenceMap: cloneValue(nextMap),
      brandMap: cloneValue(nextMap),
    };
  }

  function syncFlatBrandFieldsFromBrandMap(state) {
    const brand = normalizeBrandFoundationState(
      state.brandFoundationState,
      state.marketingForm,
    );

    const map = getBrandMapFromBrand(brand);

    const brandCore = ensureObject(map.brandCore || map.brand_core);
    const strategy = ensureObject(map.strategy);
    const audiences = ensureObject(map.audiences || map.audience);
    const personas = ensureObject(map.personas);
    const productsServices = ensureObject(
      map.productsServices ||
        map.products_services ||
        map.productsAndServices ||
        map.products_and_services,
    );
    const offers = ensureObject(map.offers || map.offer);
    const messaging = ensureObject(map.messaging);
    const platformStrategy = ensureObject(
      map.platformStrategy || map.platform_strategy,
    );
    const contentRules = ensureObject(map.contentRules || map.content_rules);
    const campaignPlanning = ensureObject(
      map.campaignPlanning || map.campaign_planning,
    );

    const nextBrand = setBrandMapOnBrand(
      {
        ...brand,
        objective:
          strategy.objective ??
          strategy.primaryObjective ??
          strategy.primary_objective ??
          brand.objective ??
          "",
        funnelGoal:
          strategy.funnelGoal ??
          strategy.funnel_goal ??
          brand.funnelGoal ??
          "",
        targetAudience:
          audiences.primaryAudience ??
          audiences.primary_audience ??
          audiences.targetAudience ??
          audiences.target_audience ??
          brand.targetAudience ??
          "",
        persona:
          personas.primaryPersona ??
          personas.primary_persona ??
          audiences.primaryPersona ??
          audiences.persona ??
          brand.persona ??
          "",
        offer:
          offers.primaryOffer ??
          offers.primary_offer ??
          offers.offer ??
          productsServices.primaryProductOrService ??
          productsServices.primary_product_or_service ??
          brand.offer ??
          "",
        channels:
          ensureArray(campaignPlanning.channels).length
            ? campaignPlanning.channels
            : ensureArray(platformStrategy.channels).length
              ? platformStrategy.channels
              : ensureArray(brand.channels),
        hashtags:
          ensureArray(campaignPlanning.hashtags).length
            ? campaignPlanning.hashtags
            : ensureArray(messaging.hashtags).length
              ? messaging.hashtags
              : ensureArray(brand.hashtags),
        keywords:
          ensureArray(campaignPlanning.keywords).length
            ? campaignPlanning.keywords
            : ensureArray(messaging.keywords).length
              ? messaging.keywords
              : ensureArray(brand.keywords),
        hardRules:
          ensureArray(contentRules.hardRules).length
            ? contentRules.hardRules
            : ensureArray(contentRules.hard_rules).length
              ? contentRules.hard_rules
              : ensureArray(brand.hardRules),
        guidanceNotes:
          ensureArray(contentRules.guidanceNotes).length
            ? contentRules.guidanceNotes
            : ensureArray(contentRules.guidance_notes).length
              ? contentRules.guidance_notes
              : ensureArray(messaging.guidanceNotes).length
                ? messaging.guidanceNotes
                : ensureArray(brand.guidanceNotes),
        campaignNotes:
          ensureArray(contentRules.campaignNotes).length
            ? contentRules.campaignNotes
            : ensureArray(contentRules.campaign_notes).length
              ? contentRules.campaign_notes
              : ensureArray(strategy.campaignNotes).length
                ? strategy.campaignNotes
                : ensureArray(brand.campaignNotes),
        updatedAt: new Date().toISOString(),
      },
      {
        ...map,
        brandCore,
        strategy,
        audiences,
        personas,
        productsServices,
        offers,
        messaging,
        platformStrategy,
        contentRules,
        campaignPlanning,
      },
    );

    state.brandFoundationState = normalizeBrandFoundationState(
      nextBrand,
      state.marketingForm,
    );
  }

  function setNestedValue(root, path, value) {
    const parts = String(path || "")
      .split(".")
      .map((part) => part.trim())
      .filter(Boolean);

    if (!parts.length) return root;

    let cursor = root;

    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        cursor[part] = value;
        return;
      }

      if (
        !cursor[part] ||
        typeof cursor[part] !== "object" ||
        Array.isArray(cursor[part])
      ) {
        cursor[part] = {};
      }

      cursor = cursor[part];
    });

    return root;
  }

  function patchNestedObject(root, path, patchValue) {
    const current = cloneValue(root || {});
    const parts = String(path || "")
      .split(".")
      .map((part) => part.trim())
      .filter(Boolean);

    if (!parts.length) {
      return {
        ...ensureObject(current),
        ...ensureObject(patchValue),
      };
    }

    let cursor = current;

    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        cursor[part] = {
          ...ensureObject(cursor[part]),
          ...ensureObject(patchValue),
        };
        return;
      }

      if (
        !cursor[part] ||
        typeof cursor[part] !== "object" ||
        Array.isArray(cursor[part])
      ) {
        cursor[part] = {};
      }

      cursor = cursor[part];
    });

    return current;
  }

  function summarizeRuntime(runtime) {
    const safeRuntime = ensureObject(runtime);
    const runs = ensureArray(safeRuntime.runs);
    const approvals = ensureArray(safeRuntime.approvals);

    return {
      node: cloneValue(safeRuntime.node || null),
      counts: {
        runs: runs.length,
        queued: runs.filter((item) => item?.status === "queued").length,
        running: runs.filter((item) => item?.status === "running").length,
        waitingApproval: runs.filter((item) => item?.status === "waiting_approval")
          .length,
        completed: runs.filter((item) => item?.status === "completed").length,
        failed: runs.filter((item) => item?.status === "failed").length,
        cancelled: runs.filter((item) => item?.status === "cancelled").length,
        approvals: approvals.length,
        pendingApprovals: approvals.filter((item) => item?.status === "pending")
          .length,
      },
    };
  }

  function summarizeTopology(topology) {
    const safeTopology = ensureObject(topology);
    const nodes = ensureArray(safeTopology.nodes);
    const edges = ensureArray(safeTopology.edges);

    const nodeTypeCounts = nodes.reduce((acc, node) => {
      const key = node?.node_type || node?.type || "unknown";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    return {
      counts: {
        nodes: nodes.length,
        edges: edges.length,
        nodeTypes: Object.keys(nodeTypeCounts).length,
      },
      nodeTypeCounts,
    };
  }

  function summarizeBindings(bindings) {
    const items = ensureArray(bindings);

    const byCategory = items.reduce((acc, item) => {
      const key = item?.category || "uncategorized";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    return {
      total: items.length,
      byCategory,
    };
  }

  function summarizeBoardroomSnapshot(snapshot) {
    const safeSnapshot = ensureObject(snapshot);

    return {
      workspaceId: safeSnapshot.workspaceId || safeSnapshot.workspace_id || null,
      viewMode: safeSnapshot.viewMode || safeSnapshot.view_mode || null,
      activeZone: safeSnapshot.activeZone || safeSnapshot.active_zone || null,
      selectedSeatId:
        safeSnapshot.selectedSeatId ?? safeSnapshot.selected_seat_id ?? null,
      selectedInspectorTarget:
        safeSnapshot.selectedInspectorTarget ??
        safeSnapshot.selected_inspector_target ??
        null,
      workspace: cloneValue(safeSnapshot.workspace || null),
      pulse: cloneValue(safeSnapshot.pulse || null),
      topology: summarizeTopology(safeSnapshot.topology || null),
      runtime: summarizeRuntime(safeSnapshot.runtime || null),
      departmentsCount: ensureArray(safeSnapshot.departments).length,
      seatsCount: ensureArray(safeSnapshot.seats).length,
      updatedAt: safeSnapshot.updatedAt || safeSnapshot.updated_at || null,
    };
  }

  function summarizeLiveAgentsSnapshot(snapshot) {
    const safeSnapshot = ensureObject(snapshot);
    const runs = ensureArray(safeSnapshot.runs);
    const approvals = ensureArray(safeSnapshot.approvals);

    return {
      selectedLiveAgentId:
        safeSnapshot.selectedLiveAgentId ??
        safeSnapshot.selected_live_agent_id ??
        null,
      selectedLiveRunId:
        safeSnapshot.selectedLiveRunId ??
        safeSnapshot.selected_live_run_id ??
        null,
      liveAgentsReplayOpen:
        safeSnapshot.liveAgentsReplayOpen ??
        safeSnapshot.live_agents_replay_open ??
        false,
      liveAgentsView:
        safeSnapshot.liveAgentsView ?? safeSnapshot.live_agents_view ?? "stream",
      activeZone: safeSnapshot.activeZone ?? safeSnapshot.active_zone ?? null,
      counts: {
        runs: runs.length,
        approvals: approvals.length,
      },
      updatedAt: safeSnapshot.updatedAt || safeSnapshot.updated_at || null,
    };
  }

  function summarizeOperationsFlowSnapshot(snapshot) {
    const safeSnapshot = ensureObject(snapshot);

    return {
      viewMode: safeSnapshot.viewMode || safeSnapshot.view_mode || null,
      activeZone: safeSnapshot.activeZone || safeSnapshot.active_zone || null,
      selectedSeatId:
        safeSnapshot.selectedSeatId ?? safeSnapshot.selected_seat_id ?? null,
      selectedInspectorTarget:
        safeSnapshot.selectedInspectorTarget ??
        safeSnapshot.selected_inspector_target ??
        null,
      workspace: cloneValue(safeSnapshot.workspace || null),
      pulse: cloneValue(safeSnapshot.pulse || null),
      topology: summarizeTopology(safeSnapshot.topology || null),
      runtime: cloneValue(safeSnapshot.runtime || null),
      bindings: summarizeBindings(safeSnapshot.containerBindings || []),
      updatedAt: safeSnapshot.updatedAt || safeSnapshot.updated_at || null,
    };
  }

  function summarizeBrandFoundationState(brandFoundationState, marketingForm) {
    const safeMarketingForm =
      marketingForm ||
      (typeof contracts.buildDefaultMarketingForm === "function"
        ? contracts.buildDefaultMarketingForm()
        : {});

    const safeBrand = normalizeBrandFoundationState(
      brandFoundationState,
      safeMarketingForm,
    );

    const map = getBrandMapFromBrand(safeBrand);

    return {
      objective: safeBrand.objective || null,
      funnelGoal: safeBrand.funnelGoal || null,
      targetAudience: safeBrand.targetAudience || null,
      persona: safeBrand.persona || null,
      offer: safeBrand.offer || null,
      channelsCount: ensureArray(safeBrand.channels).length,
      keywordsCount: ensureArray(safeBrand.keywords).length,
      hardRulesCount: ensureArray(safeBrand.hardRules).length,
      sections: Object.keys(map),
      updatedAt: safeBrand.updatedAt || null,
    };
  }

  function normalizeActiveTab(tab) {
    return typeof contracts.normalizeActiveTab === "function"
      ? contracts.normalizeActiveTab(tab)
      : tab || "dashboard";
  }

  function normalizeBoardroomViewMode(mode) {
    return typeof contracts.normalizeBoardroomViewMode === "function"
      ? contracts.normalizeBoardroomViewMode(mode)
      : mode === "spatial"
        ? "spatial"
        : "dashboard";
  }

  function normalizeOperationsFlowViewMode(mode) {
    return typeof contracts.normalizeOperationsFlowViewMode === "function"
      ? contracts.normalizeOperationsFlowViewMode(mode)
      : mode === "spatial"
        ? "spatial"
        : "flat";
  }

  function normalizeActiveZone(zone) {
    return typeof contracts.normalizeActiveZone === "function"
      ? contracts.normalizeActiveZone(zone)
      : zone || "coo";
  }

  function normalizeSelectedSeatId(seatId) {
    return typeof contracts.normalizeSelectedSeatId === "function"
      ? contracts.normalizeSelectedSeatId(seatId)
      : seatId == null || seatId === ""
        ? null
        : String(seatId);
  }

  function normalizeSelectedInspectorTarget(target) {
    return typeof contracts.normalizeSelectedInspectorTarget === "function"
      ? contracts.normalizeSelectedInspectorTarget(target)
      : target == null
        ? null
        : cloneValue(target);
  }

  function normalizeSelectedLiveAgentId(agentId) {
    return typeof contracts.normalizeSelectedLiveAgentId === "function"
      ? contracts.normalizeSelectedLiveAgentId(agentId)
      : agentId == null || agentId === ""
        ? null
        : String(agentId);
  }

  function normalizeSelectedLiveRunId(runId) {
    return typeof contracts.normalizeSelectedLiveRunId === "function"
      ? contracts.normalizeSelectedLiveRunId(runId)
      : runId == null || runId === ""
        ? null
        : String(runId);
  }

  function normalizeLiveAgentsReplayOpen(value) {
    return typeof contracts.normalizeLiveAgentsReplayOpen === "function"
      ? contracts.normalizeLiveAgentsReplayOpen(value)
      : value === true;
  }

  function normalizeLiveAgentsView(value) {
    return typeof contracts.normalizeLiveAgentsView === "function"
      ? contracts.normalizeLiveAgentsView(value)
      : value || "stream";
  }

  function normalizeMarketingCalendarMode(value) {
    return typeof contracts.normalizeMarketingCalendarMode === "function"
      ? contracts.normalizeMarketingCalendarMode(value)
      : value || "done";
  }

  function normalizeBindings(bindings) {
    return typeof contracts.normalizeContainerBindings === "function"
      ? contracts.normalizeContainerBindings(bindings)
      : Array.isArray(bindings)
        ? bindings
        : [];
  }

  function normalizeBindingsByCategory(bindings) {
    const items = normalizeBindings(bindings);

    return items.reduce((acc, item) => {
      const key = item?.category || "uncategorized";
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    }, {});
  }

  function normalizeBoardroomSnapshot(state, snapshot) {
    if (typeof contracts.normalizeBoardroomSnapshot === "function") {
      const normalized = contracts.normalizeBoardroomSnapshot(
        snapshot,
        state.workspaceId,
      );

      return {
        ...normalized,
        workspaceId: state.workspaceId,
        viewMode: normalizeBoardroomViewMode(
          normalized.viewMode || state.boardroomViewMode,
        ),
        activeZone: normalizeActiveZone(
          normalized.activeZone || state.activeZone || "coo",
        ),
        selectedSeatId: normalizeSelectedSeatId(
          normalized.selectedSeatId !== undefined
            ? normalized.selectedSeatId
            : state.selectedSeatId,
        ),
        selectedInspectorTarget: normalizeSelectedInspectorTarget(
          normalized.selectedInspectorTarget !== undefined
            ? normalized.selectedInspectorTarget
            : state.selectedInspectorTarget,
        ),
        bindingsByCategory: normalizeBindingsByCategory(state.containerBindings),
        departments: ensureArray(normalized.departments),
        seats: ensureArray(normalized.seats),
        updatedAt: normalized.updatedAt || state.lastRefreshAt || null,
      };
    }

    return {
      ...contracts.buildDefaultBoardroomSnapshot(state.workspaceId),
      ...ensureObject(snapshot),
      workspaceId: state.workspaceId,
      bindingsByCategory: normalizeBindingsByCategory(state.containerBindings),
    };
  }

  function normalizeLiveAgentsSnapshot(state, snapshot) {
    if (typeof contracts.normalizeLiveAgentsSnapshot === "function") {
      const normalized = contracts.normalizeLiveAgentsSnapshot(snapshot);

      return {
        ...normalized,
        runs: ensureArray(normalized.runs ?? state.runs),
        approvals: ensureArray(normalized.approvals ?? state.approvals),
        selectedLiveAgentId: normalizeSelectedLiveAgentId(
          normalized.selectedLiveAgentId ?? state.selectedLiveAgentId ?? null,
        ),
        selectedLiveRunId: normalizeSelectedLiveRunId(
          normalized.selectedLiveRunId ?? state.selectedLiveRunId ?? null,
        ),
        liveAgentsReplayOpen: normalizeLiveAgentsReplayOpen(
          normalized.liveAgentsReplayOpen ?? state.liveAgentsReplayOpen ?? false,
        ),
        liveAgentsView: normalizeLiveAgentsView(
          normalized.liveAgentsView ?? state.liveAgentsView ?? "stream",
        ),
        activeZone: normalizeActiveZone(
          normalized.activeZone ?? state.activeZone ?? "coo",
        ),
        updatedAt: normalized.updatedAt || state.lastRefreshAt || null,
      };
    }

    return {
      ...(contracts.buildDefaultLiveAgentsSnapshot
        ? contracts.buildDefaultLiveAgentsSnapshot()
        : {}),
      ...ensureObject(snapshot),
      runs: ensureArray(snapshot?.runs ?? state.runs),
      approvals: ensureArray(snapshot?.approvals ?? state.approvals),
    };
  }

  function normalizeOperationsFlowSnapshot(state, snapshot) {
    if (typeof contracts.normalizeOperationsFlowSnapshot === "function") {
      const normalized = contracts.normalizeOperationsFlowSnapshot(snapshot);

      return {
        ...normalized,
        viewMode: normalizeOperationsFlowViewMode(
          normalized.viewMode ?? state.operationsFlowViewMode ?? "flat",
        ),
        activeZone: normalizeActiveZone(
          normalized.activeZone ?? state.activeZone ?? "operations",
        ),
        selectedSeatId: normalizeSelectedSeatId(
          normalized.selectedSeatId ?? state.selectedSeatId ?? null,
        ),
        selectedInspectorTarget: normalizeSelectedInspectorTarget(
          normalized.selectedInspectorTarget ??
            state.selectedInspectorTarget ??
            null,
        ),
        containerBindings: normalizeBindings(
          normalized.containerBindings ?? state.containerBindings,
        ),
        workspace:
          normalized.workspace ?? state.boardroomSnapshot?.workspace ?? null,
        pulse: normalized.pulse ?? state.boardroomSnapshot?.pulse ?? null,
        runtime:
          normalized.runtime ??
          summarizeRuntime(state.boardroomSnapshot?.runtime ?? null),
        topology:
          normalized.topology ??
          summarizeTopology(state.boardroomSnapshot?.topology ?? null),
        updatedAt: normalized.updatedAt || state.lastRefreshAt || null,
      };
    }

    return {
      ...(contracts.buildDefaultOperationsFlowSnapshot
        ? contracts.buildDefaultOperationsFlowSnapshot()
        : {}),
      ...ensureObject(snapshot),
      containerBindings: normalizeBindings(
        snapshot?.containerBindings ?? state.containerBindings,
      ),
    };
  }

  function normalizeRecoveryPayload(state, payload) {
    if (typeof contracts.normalizeRecoveryPayload === "function") {
      const normalized = contracts.normalizeRecoveryPayload(payload);
      if (normalized) return normalized;
    }

    const next = ensureObject(payload);

    return {
      ...next,
      workspaceId:
        next.workspaceId ||
        next.workspace_id ||
        state.workspaceId ||
        contracts.DEFAULTS.workspaceId,
      nodeId:
        next.nodeId || next.node_id || state.nodeId || contracts.DEFAULTS.nodeId,
      activeTab: normalizeActiveTab(
        next.activeTab || next.active_tab || state.activeTab,
      ),
      boardroomViewMode: normalizeBoardroomViewMode(
        next.boardroomViewMode ||
          next.boardroom_view_mode ||
          state.boardroomViewMode,
      ),
      operationsFlowViewMode: normalizeOperationsFlowViewMode(
        next.operationsFlowViewMode ||
          next.operations_flow_view_mode ||
          state.operationsFlowViewMode,
      ),
      activeZone: normalizeActiveZone(
        next.activeZone || next.active_zone || state.activeZone,
      ),
      selectedSeatId: normalizeSelectedSeatId(
        next.selectedSeatId ?? next.selected_seat_id ?? state.selectedSeatId,
      ),
      selectedInspectorTarget: normalizeSelectedInspectorTarget(
        next.selectedInspectorTarget ??
          next.selected_inspector_target ??
          state.selectedInspectorTarget,
      ),
      selectedLiveAgentId: normalizeSelectedLiveAgentId(
        next.selectedLiveAgentId ??
          next.selected_live_agent_id ??
          state.selectedLiveAgentId,
      ),
      selectedLiveRunId: normalizeSelectedLiveRunId(
        next.selectedLiveRunId ??
          next.selected_live_run_id ??
          state.selectedLiveRunId,
      ),
      liveAgentsReplayOpen: normalizeLiveAgentsReplayOpen(
        next.liveAgentsReplayOpen ??
          next.live_agents_replay_open ??
          state.liveAgentsReplayOpen,
      ),
      liveAgentsView: normalizeLiveAgentsView(
        next.liveAgentsView ?? next.live_agents_view ?? state.liveAgentsView,
      ),
      marketingCalendarMode: normalizeMarketingCalendarMode(
        next.marketingCalendarMode ??
          next.marketing_calendar_mode ??
          state.marketingCalendarMode,
      ),
      lastRefreshAt:
        next.lastRefreshAt ||
        next.last_refresh_at ||
        state.lastRefreshAt ||
        null,
      syncBoundary: next.syncBoundary ?? next.sync_boundary ?? state.syncBoundary,
      brandFoundationSummary:
        next.brandFoundationSummary ??
        next.brand_foundation_summary ??
        summarizeBrandFoundationState(
          state.brandFoundationState || null,
          state.marketingForm || null,
        ),
      bindingsSummary:
        next.bindingsSummary ??
        next.bindings_summary ??
        summarizeBindings(state.containerBindings || []),
      dashboardSummaryMeta:
        next.dashboardSummaryMeta ??
        next.dashboard_summary_meta ?? {
          auditEventCount:
            state.dashboardSummary?.audit_event_count ??
            ensureArray(state.dashboardSummary?.recent_audit).length,
          departmentsCount: ensureArray(state.dashboardSummary?.departments).length,
          alertsCount: ensureArray(state.dashboardSummary?.alerts).length,
        },
      boardroom:
        next.boardroom ?? summarizeBoardroomSnapshot(state.boardroomSnapshot),
      liveAgents:
        next.liveAgents ??
        next.live_agents ??
        summarizeLiveAgentsSnapshot(state.liveAgentsSnapshot),
      operationsFlow:
        next.operationsFlow ??
        next.operations_flow ??
        summarizeOperationsFlowSnapshot(state.operationsFlowSnapshot),
    };
  }

  function buildStateFromSeed(seed) {
    const normalizedSeed =
      typeof cache.normalizeSeed === "function"
        ? cache.normalizeSeed(seed || {})
        : seed || {};

    const baseState = contracts.buildDefaultState(normalizedSeed);

    baseState.activeTab = normalizeActiveTab(baseState.activeTab);
    baseState.boardroomViewMode = normalizeBoardroomViewMode(
      baseState.boardroomViewMode,
    );
    baseState.operationsFlowViewMode = normalizeOperationsFlowViewMode(
      baseState.operationsFlowViewMode,
    );
    baseState.liveAgentsView = normalizeLiveAgentsView(baseState.liveAgentsView);
    baseState.marketingCalendarMode = normalizeMarketingCalendarMode(
      baseState.marketingCalendarMode,
    );

    baseState.marketingForm = normalizeMarketingForm(baseState.marketingForm);

    baseState.brandFoundationState = normalizeBrandFoundationState(
      baseState.brandFoundationState ||
        contracts.buildDefaultBrandFoundationState(baseState.marketingForm),
      baseState.marketingForm,
    );

    syncFlatBrandFieldsFromBrandMap(baseState);

    baseState.syncBoundary = {
      ...contracts.buildDefaultSyncBoundary(),
      ...(baseState.syncBoundary || {}),
    };

    baseState.containerBindings = normalizeBindings(baseState.containerBindings);
    baseState.activeZone = normalizeActiveZone(baseState.activeZone || "coo");
    baseState.selectedSeatId = normalizeSelectedSeatId(baseState.selectedSeatId);
    baseState.selectedInspectorTarget = normalizeSelectedInspectorTarget(
      baseState.selectedInspectorTarget,
    );
    baseState.selectedLiveAgentId = normalizeSelectedLiveAgentId(
      baseState.selectedLiveAgentId,
    );
    baseState.selectedLiveRunId = normalizeSelectedLiveRunId(
      baseState.selectedLiveRunId,
    );
    baseState.liveAgentsReplayOpen = normalizeLiveAgentsReplayOpen(
      baseState.liveAgentsReplayOpen,
    );

    baseState.boardroomSnapshot = normalizeBoardroomSnapshot(
      baseState,
      baseState.boardroomSnapshot,
    );

    baseState.liveAgentsSnapshot = normalizeLiveAgentsSnapshot(
      baseState,
      baseState.liveAgentsSnapshot,
    );

    baseState.operationsFlowSnapshot = normalizeOperationsFlowSnapshot(
      baseState,
      baseState.operationsFlowSnapshot,
    );

    baseState.recoveryPayload = normalizeRecoveryPayload(
      baseState,
      baseState.recoveryPayload,
    );

    return baseState;
  }

  function createDesktopStore() {
    const state = buildStateFromSeed(cache.loadSeedFromStorage());
    let persistCacheTimer = null;

    function syncLiveAgentsSnapshotFromTopLevel() {
      state.liveAgentsSnapshot = normalizeLiveAgentsSnapshot(state, {
        ...(state.liveAgentsSnapshot || {}),
        runs: state.runs,
        approvals: state.approvals,
        selectedLiveAgentId: state.selectedLiveAgentId,
        selectedLiveRunId: state.selectedLiveRunId,
        liveAgentsReplayOpen: state.liveAgentsReplayOpen,
        liveAgentsView: state.liveAgentsView,
        activeZone: state.activeZone,
        updatedAt: state.lastRefreshAt || null,
      });
    }

    function syncOperationsFlowSnapshotFromTopLevel() {
      state.operationsFlowSnapshot = normalizeOperationsFlowSnapshot(state, {
        ...(state.operationsFlowSnapshot || {}),
        viewMode: state.operationsFlowViewMode,
        activeZone: state.activeZone,
        selectedSeatId: state.selectedSeatId,
        selectedInspectorTarget: state.selectedInspectorTarget,
        containerBindings: state.containerBindings,
        workspace: state.boardroomSnapshot?.workspace,
        pulse: state.boardroomSnapshot?.pulse,
        runtime: summarizeRuntime(state.boardroomSnapshot?.runtime || null),
        topology: summarizeTopology(state.boardroomSnapshot?.topology || null),
        updatedAt: state.lastRefreshAt || null,
      });
    }

    function syncRecoveryPayloadFromTopLevel() {
      state.recoveryPayload = normalizeRecoveryPayload(state, {
        ...(state.recoveryPayload || {}),
        workspaceId: state.workspaceId,
        nodeId: state.nodeId,
        activeTab: state.activeTab,
        boardroomViewMode: state.boardroomViewMode,
        operationsFlowViewMode: state.operationsFlowViewMode,
        activeZone: state.activeZone,
        selectedSeatId: state.selectedSeatId,
        selectedInspectorTarget: state.selectedInspectorTarget,
        selectedLiveAgentId: state.selectedLiveAgentId,
        selectedLiveRunId: state.selectedLiveRunId,
        liveAgentsReplayOpen: state.liveAgentsReplayOpen,
        liveAgentsView: state.liveAgentsView,
        marketingCalendarMode: state.marketingCalendarMode,
        lastRefreshAt: state.lastRefreshAt,
        syncBoundary: state.syncBoundary,
        brandFoundationSummary: summarizeBrandFoundationState(
          state.brandFoundationState || null,
          state.marketingForm || null,
        ),
        bindingsSummary: summarizeBindings(state.containerBindings || []),
        boardroom: summarizeBoardroomSnapshot(state.boardroomSnapshot || null),
        liveAgents: summarizeLiveAgentsSnapshot(state.liveAgentsSnapshot || null),
        operationsFlow: summarizeOperationsFlowSnapshot(
          state.operationsFlowSnapshot || null,
        ),
      });
    }

    function syncBoardroomSnapshotFromTopLevel() {
      state.activeTab = normalizeActiveTab(state.activeTab);
      state.boardroomViewMode = normalizeBoardroomViewMode(
        state.boardroomViewMode,
      );
      state.operationsFlowViewMode = normalizeOperationsFlowViewMode(
        state.operationsFlowViewMode,
      );
      state.liveAgentsView = normalizeLiveAgentsView(state.liveAgentsView);
      state.marketingCalendarMode = normalizeMarketingCalendarMode(
        state.marketingCalendarMode,
      );
      state.activeZone = normalizeActiveZone(state.activeZone || "coo");
      state.selectedSeatId = normalizeSelectedSeatId(state.selectedSeatId);
      state.selectedInspectorTarget = normalizeSelectedInspectorTarget(
        state.selectedInspectorTarget,
      );
      state.selectedLiveAgentId = normalizeSelectedLiveAgentId(
        state.selectedLiveAgentId,
      );
      state.selectedLiveRunId = normalizeSelectedLiveRunId(
        state.selectedLiveRunId,
      );
      state.liveAgentsReplayOpen = normalizeLiveAgentsReplayOpen(
        state.liveAgentsReplayOpen,
      );
      state.containerBindings = normalizeBindings(state.containerBindings);
      state.marketingForm = normalizeMarketingForm(state.marketingForm);
      state.brandFoundationState = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );

      syncFlatBrandFieldsFromBrandMap(state);

      state.boardroomSnapshot = normalizeBoardroomSnapshot(state, {
        ...(state.boardroomSnapshot || {}),
        workspaceId: state.workspaceId,
        viewMode: state.boardroomViewMode,
        activeZone: state.activeZone || "coo",
        selectedSeatId: state.selectedSeatId,
        selectedInspectorTarget: state.selectedInspectorTarget,
        bindingsByCategory: normalizeBindingsByCategory(state.containerBindings),
      });
    }

    function syncTopLevelBoardroomFromSnapshot() {
      const snapshot = normalizeBoardroomSnapshot(state, state.boardroomSnapshot);

      state.boardroomSnapshot = snapshot;
      state.boardroomViewMode = normalizeBoardroomViewMode(snapshot.viewMode);
      state.activeZone = normalizeActiveZone(snapshot.activeZone || "coo");
      state.selectedSeatId = normalizeSelectedSeatId(snapshot.selectedSeatId);
      state.selectedInspectorTarget = normalizeSelectedInspectorTarget(
        snapshot.selectedInspectorTarget,
      );
      state.containerBindings = normalizeBindings(state.containerBindings);
    }

    function syncTopLevelLiveAgentsFromSnapshot() {
      const snapshot = normalizeLiveAgentsSnapshot(
        state,
        state.liveAgentsSnapshot,
      );

      state.liveAgentsSnapshot = snapshot;
      state.liveAgentsView = normalizeLiveAgentsView(snapshot.liveAgentsView);
      state.selectedLiveAgentId = normalizeSelectedLiveAgentId(
        snapshot.selectedLiveAgentId,
      );
      state.selectedLiveRunId = normalizeSelectedLiveRunId(
        snapshot.selectedLiveRunId,
      );
      state.liveAgentsReplayOpen = normalizeLiveAgentsReplayOpen(
        snapshot.liveAgentsReplayOpen,
      );

      if (snapshot.activeZone) {
        state.activeZone = normalizeActiveZone(snapshot.activeZone);
      }
    }

    function syncTopLevelOperationsFlowFromSnapshot() {
      const snapshot = normalizeOperationsFlowSnapshot(
        state,
        state.operationsFlowSnapshot,
      );

      state.operationsFlowSnapshot = snapshot;
      state.operationsFlowViewMode = normalizeOperationsFlowViewMode(
        snapshot.viewMode,
      );
      state.activeZone = normalizeActiveZone(snapshot.activeZone || "coo");
      state.selectedSeatId = normalizeSelectedSeatId(snapshot.selectedSeatId);
      state.selectedInspectorTarget = normalizeSelectedInspectorTarget(
        snapshot.selectedInspectorTarget,
      );
    }

    function syncAllDerivedSnapshots() {
      state.marketingForm = normalizeMarketingForm(state.marketingForm);
      state.brandFoundationState = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );
      syncFlatBrandFieldsFromBrandMap(state);
      syncBoardroomSnapshotFromTopLevel();
      syncLiveAgentsSnapshotFromTopLevel();
      syncOperationsFlowSnapshotFromTopLevel();
      syncRecoveryPayloadFromTopLevel();
    }

    function patch(values) {
      Object.assign(state, values || {});

      state.activeTab = normalizeActiveTab(state.activeTab);
      state.containerBindings = normalizeBindings(state.containerBindings);
      state.marketingForm = normalizeMarketingForm(state.marketingForm);
      state.brandFoundationState = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );
      syncFlatBrandFieldsFromBrandMap(state);

      state.boardroomViewMode = normalizeBoardroomViewMode(
        state.boardroomViewMode,
      );
      state.operationsFlowViewMode = normalizeOperationsFlowViewMode(
        state.operationsFlowViewMode,
      );
      state.liveAgentsView = normalizeLiveAgentsView(state.liveAgentsView);
      state.marketingCalendarMode = normalizeMarketingCalendarMode(
        state.marketingCalendarMode,
      );
      state.activeZone = normalizeActiveZone(state.activeZone || "coo");
      state.selectedSeatId = normalizeSelectedSeatId(state.selectedSeatId);
      state.selectedInspectorTarget = normalizeSelectedInspectorTarget(
        state.selectedInspectorTarget,
      );
      state.selectedLiveAgentId = normalizeSelectedLiveAgentId(
        state.selectedLiveAgentId,
      );
      state.selectedLiveRunId = normalizeSelectedLiveRunId(
        state.selectedLiveRunId,
      );
      state.liveAgentsReplayOpen = normalizeLiveAgentsReplayOpen(
        state.liveAgentsReplayOpen,
      );

      if (
        values &&
        Object.prototype.hasOwnProperty.call(values, "workspaceId") &&
        values.workspaceId &&
        values.workspaceId !== state.boardroomSnapshot?.workspaceId
      ) {
        state.boardroomSnapshot = normalizeBoardroomSnapshot(state, {
          ...(state.boardroomSnapshot || {}),
          workspaceId: values.workspaceId,
        });
      }

      if (
        values &&
        Object.prototype.hasOwnProperty.call(values, "boardroomSnapshot")
      ) {
        syncTopLevelBoardroomFromSnapshot();
      }

      if (
        values &&
        Object.prototype.hasOwnProperty.call(values, "liveAgentsSnapshot")
      ) {
        syncTopLevelLiveAgentsFromSnapshot();
      }

      if (
        values &&
        Object.prototype.hasOwnProperty.call(values, "operationsFlowSnapshot")
      ) {
        syncTopLevelOperationsFlowFromSnapshot();
      }

      syncAllDerivedSnapshots();
      return state;
    }

    function loadFromStorage() {
      const next = buildStateFromSeed(cache.loadSeedFromStorage());
      Object.assign(state, next);

      state.activeTab = normalizeActiveTab(state.activeTab);
      state.liveAgentsView = normalizeLiveAgentsView(state.liveAgentsView);
      state.marketingCalendarMode = normalizeMarketingCalendarMode(
        state.marketingCalendarMode,
      );
      state.marketingForm = normalizeMarketingForm(state.marketingForm);
      state.brandFoundationState = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );
      syncFlatBrandFieldsFromBrandMap(state);

      syncTopLevelBoardroomFromSnapshot();
      syncTopLevelLiveAgentsFromSnapshot();
      syncTopLevelOperationsFlowFromSnapshot();
      syncRecoveryPayloadFromTopLevel();

      return state;
    }

    function persistBinding() {
      syncAllDerivedSnapshots();
      cache.persistBinding(state);
    }

    function persistCache() {
      syncAllDerivedSnapshots();
      cache.persistCache(state);
    }

    function persistCacheSoon(delay = 300) {
      if (persistCacheTimer) {
        global.clearTimeout(persistCacheTimer);
      }

      persistCacheTimer = global.setTimeout(() => {
        persistCacheTimer = null;
        persistCache();
      }, delay);
    }

    function flushPendingCachePersist() {
      if (!persistCacheTimer) return;
      global.clearTimeout(persistCacheTimer);
      persistCacheTimer = null;
      persistCache();
    }

    function hydrateLocalTruth(values) {
      patch(values || {});
      persistBinding();
      persistCache();
      return state;
    }

    function applyWorkspaceContext(nextWorkspaceId, nextNodeId) {
      const workspaceId =
        typeof nextWorkspaceId === "string" && nextWorkspaceId.trim()
          ? nextWorkspaceId.trim()
          : state.workspaceId;

      const nodeId =
        typeof nextNodeId === "string" && nextNodeId.trim()
          ? nextNodeId.trim()
          : state.nodeId;

      const workspaceChanged = workspaceId !== state.workspaceId;

      state.workspaceId = workspaceId;
      state.nodeId = nodeId;

      if (workspaceChanged) {
        state.boardroomSnapshot = normalizeBoardroomSnapshot(state, {
          ...contracts.buildDefaultBoardroomSnapshot(workspaceId),
          ...(state.boardroomSnapshot || {}),
          workspaceId,
        });

        state.liveAgentsSnapshot = normalizeLiveAgentsSnapshot(state, {
          ...(state.liveAgentsSnapshot || {}),
        });

        state.operationsFlowSnapshot = normalizeOperationsFlowSnapshot(state, {
          ...(state.operationsFlowSnapshot || {}),
        });

        state.recoveryPayload = normalizeRecoveryPayload(state, {
          ...(state.recoveryPayload || {}),
          workspaceId,
          nodeId,
        });
      } else {
        syncAllDerivedSnapshots();
      }

      persistBinding();
      persistCache();
      return state;
    }

    function setActiveTab(tabKey) {
      state.activeTab = normalizeActiveTab(tabKey);
      persistBinding();
      persistCache();
      return state.activeTab;
    }

    function setBoardroomViewMode(mode) {
      state.boardroomViewMode = normalizeBoardroomViewMode(mode);
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.boardroomViewMode;
    }

    function setOperationsFlowViewMode(mode) {
      state.operationsFlowViewMode = normalizeOperationsFlowViewMode(mode);
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.operationsFlowViewMode;
    }

    function setLiveAgentsView(view) {
      state.liveAgentsView = normalizeLiveAgentsView(view);
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.liveAgentsView;
    }

    function setMarketingCalendarMode(mode) {
      state.marketingCalendarMode = normalizeMarketingCalendarMode(mode);
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.marketingCalendarMode;
    }

    function setActiveZone(zone) {
      state.activeZone = normalizeActiveZone(zone || "coo");
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.activeZone;
    }

    function setSelectedSeatId(seatId) {
      state.selectedSeatId = normalizeSelectedSeatId(seatId);
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.selectedSeatId;
    }

    function setSelectedInspectorTarget(target) {
      state.selectedInspectorTarget =
        target == null ? null : normalizeSelectedInspectorTarget(target);
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.selectedInspectorTarget;
    }

    function setSelectedLiveAgentId(agentId) {
      state.selectedLiveAgentId = normalizeSelectedLiveAgentId(agentId);

      if (state.selectedLiveAgentId == null) {
        state.selectedLiveRunId = null;
        state.liveAgentsReplayOpen = false;
      }

      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.selectedLiveAgentId;
    }

    function setSelectedLiveRunId(runId) {
      state.selectedLiveRunId = normalizeSelectedLiveRunId(runId);
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.selectedLiveRunId;
    }

    function setLiveAgentsReplayOpen(value) {
      state.liveAgentsReplayOpen = normalizeLiveAgentsReplayOpen(value);
      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state.liveAgentsReplayOpen;
    }

    function updateBoardroomSelection(values) {
      if (values && Object.prototype.hasOwnProperty.call(values, "activeZone")) {
        state.activeZone = normalizeActiveZone(values.activeZone || "coo");
      }

      if (
        values &&
        Object.prototype.hasOwnProperty.call(values, "selectedSeatId")
      ) {
        state.selectedSeatId = normalizeSelectedSeatId(values.selectedSeatId);
      }

      if (
        values &&
        Object.prototype.hasOwnProperty.call(values, "selectedInspectorTarget")
      ) {
        state.selectedInspectorTarget =
          values.selectedInspectorTarget == null
            ? null
            : normalizeSelectedInspectorTarget(values.selectedInspectorTarget);
      }

      syncAllDerivedSnapshots();
      persistBinding();
      persistCache();
      return state;
    }

    function syncBrandFoundationFromMarketingForm() {
      state.marketingForm = normalizeMarketingForm(state.marketingForm);

      const existingBrand = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );

      const existingMap = getBrandMapFromBrand(existingBrand);

      const nextMap = {
        ...existingMap,
        strategy: {
          ...ensureObject(existingMap.strategy),
          objective: state.marketingForm.objective,
          funnelGoal: state.marketingForm.funnelGoal,
          campaignNotes: splitLines(state.marketingForm.campaignNotes),
        },
        audiences: {
          ...ensureObject(existingMap.audiences || existingMap.audience),
          primaryAudience: state.marketingForm.targetAudience,
        },
        personas: {
          ...ensureObject(existingMap.personas),
          primaryPersona: state.marketingForm.persona,
        },
        offers: {
          ...ensureObject(existingMap.offers || existingMap.offer),
          primaryOffer: state.marketingForm.offer,
        },
        messaging: {
          ...ensureObject(existingMap.messaging),
          keywords: splitLines(state.marketingForm.keywords),
          hashtags: splitLines(state.marketingForm.hashtags),
          guidanceNotes: splitLines(state.marketingForm.guidanceNotes),
        },
        campaignPlanning: {
          ...ensureObject(
            existingMap.campaignPlanning || existingMap.campaign_planning,
          ),
          channels: splitLines(state.marketingForm.channels),
          keywords: splitLines(state.marketingForm.keywords),
          hashtags: splitLines(state.marketingForm.hashtags),
        },
        contentRules: {
          ...ensureObject(existingMap.contentRules || existingMap.content_rules),
          hardRules: splitLines(state.marketingForm.hardRules),
          guidanceNotes: splitLines(state.marketingForm.guidanceNotes),
          campaignNotes: splitLines(state.marketingForm.campaignNotes),
        },
      };

      state.brandFoundationState = normalizeBrandFoundationState(
        setBrandMapOnBrand(
          {
            ...contracts.buildDefaultBrandFoundationState(state.marketingForm),
            ...existingBrand,
            objective: state.marketingForm.objective,
            funnelGoal: state.marketingForm.funnelGoal,
            targetAudience: state.marketingForm.targetAudience,
            persona: state.marketingForm.persona,
            offer: state.marketingForm.offer,
            channels: splitLines(state.marketingForm.channels),
            hashtags: splitLines(state.marketingForm.hashtags),
            keywords: splitLines(state.marketingForm.keywords),
            hardRules: splitLines(state.marketingForm.hardRules),
            guidanceNotes: splitLines(state.marketingForm.guidanceNotes),
            campaignNotes: splitLines(state.marketingForm.campaignNotes),
            updatedAt: new Date().toISOString(),
          },
          nextMap,
        ),
        state.marketingForm,
      );

      syncFlatBrandFieldsFromBrandMap(state);
      syncRecoveryPayloadFromTopLevel();
    }

    function setMarketingField(field, value) {
      const current = normalizeMarketingForm(state.marketingForm);

      state.marketingForm = normalizeMarketingForm({
        ...current,
        [field]: value,
      });

      syncBrandFoundationFromMarketingForm();
      persistCacheSoon(300);
      return state.marketingForm[field];
    }

    function setMarketingCreativeAssets(assets) {
      state.marketingForm = normalizeMarketingForm({
        ...state.marketingForm,
        creativeUploadedAssets: Array.isArray(assets) ? assets : [],
      });

      syncRecoveryPayloadFromTopLevel();
      persistCacheSoon(300);
      return state.marketingForm.creativeUploadedAssets;
    }

    function addMarketingCreativeAsset(asset) {
      const form = normalizeMarketingForm(state.marketingForm);
      const existing = Array.isArray(form.creativeUploadedAssets)
        ? form.creativeUploadedAssets
        : [];

      state.marketingForm = normalizeMarketingForm({
        ...form,
        creativeUploadedAssets: [...existing, asset],
      });

      syncRecoveryPayloadFromTopLevel();
      persistCacheSoon(300);
      return state.marketingForm.creativeUploadedAssets;
    }

    function removeMarketingCreativeAsset(assetId) {
      const form = normalizeMarketingForm(state.marketingForm);
      const existing = Array.isArray(form.creativeUploadedAssets)
        ? form.creativeUploadedAssets
        : [];

      state.marketingForm = normalizeMarketingForm({
        ...form,
        creativeUploadedAssets: existing.filter(
          (asset) => String(asset?.id || "") !== String(assetId || ""),
        ),
      });

      syncRecoveryPayloadFromTopLevel();
      persistCacheSoon(300);
      return state.marketingForm.creativeUploadedAssets;
    }

    function clearMarketingCreativeAssets() {
      state.marketingForm = normalizeMarketingForm({
        ...state.marketingForm,
        creativeUploadedAssets: [],
      });

      syncRecoveryPayloadFromTopLevel();
      persistCacheSoon(300);
      return state.marketingForm.creativeUploadedAssets;
    }

    function setBrandFoundationState(nextBrandFoundationState) {
      state.brandFoundationState = normalizeBrandFoundationState(
        nextBrandFoundationState,
        state.marketingForm,
      );

      syncFlatBrandFieldsFromBrandMap(state);
      syncRecoveryPayloadFromTopLevel();
      persistCacheSoon(300);

      return state.brandFoundationState;
    }

    function patchBrandFoundationState(patchValue) {
      return setBrandFoundationState({
        ...state.brandFoundationState,
        ...ensureObject(patchValue),
        updatedAt: new Date().toISOString(),
      });
    }

    function setBrandFoundationField(field, value) {
      return patchBrandFoundationState({
        [field]: value,
        updatedAt: new Date().toISOString(),
      });
    }

    function setBrandFoundationSection(sectionKey, sectionValue) {
      const current = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );

      const currentMap = getBrandMapFromBrand(current);

      const nextMap = {
        ...currentMap,
        [sectionKey]: cloneValue(sectionValue),
      };

      return setBrandFoundationState(
        setBrandMapOnBrand(
          {
            ...current,
            updatedAt: new Date().toISOString(),
          },
          nextMap,
        ),
      );
    }

    function patchBrandFoundationSection(sectionKey, patchValue) {
      const current = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );

      const currentMap = getBrandMapFromBrand(current);

      const nextMap = {
        ...currentMap,
        [sectionKey]: {
          ...ensureObject(currentMap[sectionKey]),
          ...ensureObject(patchValue),
        },
      };

      return setBrandFoundationState(
        setBrandMapOnBrand(
          {
            ...current,
            updatedAt: new Date().toISOString(),
          },
          nextMap,
        ),
      );
    }

    function setBrandFoundationNestedValue(path, value) {
      const current = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );

      const next = cloneValue(current);
      setNestedValue(next, path, value);

      if (String(path || "").startsWith("brandMap.")) {
        /* The edited brandMap is authoritative for this operation.  Calling
         * getBrandMapFromBrand here preferred the still-old
         * brandIntelligenceMap alias and silently discarded the edit. */
        next.brandIntelligenceMap = cloneValue(ensureObject(next.brandMap));
      }

      if (String(path || "").startsWith("brandIntelligenceMap.")) {
        next.brandMap = cloneValue(ensureObject(next.brandIntelligenceMap));
      }

      return setBrandFoundationState({
        ...next,
        updatedAt: new Date().toISOString(),
      });
    }

    function patchBrandFoundationNestedObject(path, patchValue) {
      const current = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );

      const next = patchNestedObject(current, path, patchValue);

      if (String(path || "").startsWith("brandMap.")) {
        const currentMap = getBrandMapFromBrand(next);
        next.brandIntelligenceMap = cloneValue(currentMap);
      }

      if (String(path || "").startsWith("brandIntelligenceMap.")) {
        const currentMap = getBrandMapFromBrand(next);
        next.brandMap = cloneValue(currentMap);
      }

      return setBrandFoundationState({
        ...next,
        updatedAt: new Date().toISOString(),
      });
    }

    function setBrandMapNestedValue(path, value) {
      const current = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );

      const nextMap = cloneValue(getBrandMapFromBrand(current));
      setNestedValue(nextMap, path, value);

      return setBrandFoundationState(
        setBrandMapOnBrand(
          {
            ...current,
            updatedAt: new Date().toISOString(),
          },
          nextMap,
        ),
      );
    }

    function patchBrandMapNestedObject(path, patchValue) {
      const current = normalizeBrandFoundationState(
        state.brandFoundationState,
        state.marketingForm,
      );

      const nextMap = patchNestedObject(
        getBrandMapFromBrand(current),
        path,
        patchValue,
      );

      return setBrandFoundationState(
        setBrandMapOnBrand(
          {
            ...current,
            updatedAt: new Date().toISOString(),
          },
          nextMap,
        ),
      );
    }

    function applyRecoveryPayload(payload) {
      const recovery = normalizeRecoveryPayload(state, payload);

      const nextValues = {
        workspaceId: recovery.workspaceId,
        nodeId: recovery.nodeId,
        activeTab: recovery.activeTab,
        boardroomViewMode: recovery.boardroomViewMode,
        operationsFlowViewMode: recovery.operationsFlowViewMode,
        liveAgentsView: recovery.liveAgentsView,
        marketingCalendarMode: recovery.marketingCalendarMode,
        activeZone: recovery.activeZone,
        selectedSeatId: recovery.selectedSeatId,
        selectedInspectorTarget: recovery.selectedInspectorTarget,
        selectedLiveAgentId: recovery.selectedLiveAgentId,
        selectedLiveRunId: recovery.selectedLiveRunId,
        liveAgentsReplayOpen: recovery.liveAgentsReplayOpen,
        status: recovery.status ?? state.status,
        runs: recovery.runs ?? state.runs,
        approvals: recovery.approvals ?? state.approvals,
        audit: recovery.audit ?? state.audit,
        scheduler: recovery.scheduler ?? state.scheduler,
        dashboardSummary: recovery.dashboardSummary ?? state.dashboardSummary,
        marketingSummary: recovery.marketingSummary ?? state.marketingSummary,
        boardroomSnapshot: recovery.boardroomSnapshot ?? state.boardroomSnapshot,
        liveAgentsSnapshot: recovery.liveAgentsSnapshot ?? state.liveAgentsSnapshot,
        operationsFlowSnapshot:
          recovery.operationsFlowSnapshot ?? state.operationsFlowSnapshot,
        brandFoundationState:
          recovery.brandFoundationState ??
          recovery.brand_foundation_state ??
          recovery.brand_foundation ??
          state.brandFoundationState,
        containerBindings: recovery.containerBindings ?? state.containerBindings,
        syncBoundary: recovery.syncBoundary ?? state.syncBoundary,
        lastRefreshAt:
          recovery.lastRefreshAt || state.lastRefreshAt || new Date().toISOString(),
      };

      patch(nextValues);
      persistBinding();
      persistCache();
      return state;
    }

    function applyRefreshPayload(payload) {
      payload = payload || {};

      patch({
        status: payload.status ?? state.status,
        runs: payload.runs ?? state.runs,
        approvals: payload.approvals ?? state.approvals,
        audit: payload.audit ?? state.audit,
        scheduler: payload.scheduler ?? state.scheduler,
        dashboardSummary: payload.dashboardSummary ?? state.dashboardSummary,
        marketingSummary: payload.marketingSummary ?? state.marketingSummary,
        brandFoundationState:
          payload.brandFoundationState ??
          payload.brand_foundation_state ??
          payload.brand_foundation ??
          state.brandFoundationState,
        containerBindings: payload.containerBindings ?? state.containerBindings,
        backendReady:
          payload.backendReady !== undefined
            ? payload.backendReady
            : state.backendReady,
        backendStatus:
          payload.backendStatus !== undefined
            ? payload.backendStatus
            : state.backendStatus,
        message: payload.message !== undefined ? payload.message : state.message,
        messageTone:
          payload.messageTone !== undefined
            ? payload.messageTone
            : state.messageTone,
        selectedLiveAgentId:
          payload.selectedLiveAgentId !== undefined
            ? payload.selectedLiveAgentId
            : state.selectedLiveAgentId,
        selectedLiveRunId:
          payload.selectedLiveRunId !== undefined
            ? payload.selectedLiveRunId
            : state.selectedLiveRunId,
        liveAgentsReplayOpen:
          payload.liveAgentsReplayOpen !== undefined
            ? payload.liveAgentsReplayOpen
            : state.liveAgentsReplayOpen,
        liveAgentsView:
          payload.liveAgentsView !== undefined
            ? payload.liveAgentsView
            : state.liveAgentsView,
        marketingCalendarMode:
          payload.marketingCalendarMode !== undefined
            ? payload.marketingCalendarMode
            : state.marketingCalendarMode,
      });

      state.lastRefreshAt = payload.lastRefreshAt ?? new Date().toISOString();
      state.syncBoundary = {
        ...contracts.buildDefaultSyncBoundary(),
        ...state.syncBoundary,
        updatedAt: state.lastRefreshAt,
      };

      syncAllDerivedSnapshots();
      persistCache();

      return state;
    }

    function getSnapshotBundle() {
      syncAllDerivedSnapshots();

      return {
        dashboardSummary: cloneValue(state.dashboardSummary),
        boardroomSnapshot: cloneValue(state.boardroomSnapshot),
        liveAgentsSnapshot: cloneValue(state.liveAgentsSnapshot),
        operationsFlowSnapshot: cloneValue(state.operationsFlowSnapshot),
        recoveryPayload: cloneValue(state.recoveryPayload),
        brandFoundationState: cloneValue(state.brandFoundationState),
        brandMap: cloneValue(getBrandMap(state)),
        brandIntelligenceMap: cloneValue(getBrandMap(state)),
      };
    }

    return {
      state,
      patch,
      loadFromStorage,
      persistBinding,
      persistCache,
      persistCacheSoon,
      flushPendingCachePersist,
      setActiveTab,
      setBoardroomViewMode,
      setOperationsFlowViewMode,
      setLiveAgentsView,
      setMarketingCalendarMode,
      setActiveZone,
      setSelectedSeatId,
      setSelectedInspectorTarget,
      setSelectedLiveAgentId,
      setSelectedLiveRunId,
      setLiveAgentsReplayOpen,
      updateBoardroomSelection,

      setMarketingField,
      setMarketingCreativeAssets,
      addMarketingCreativeAsset,
      removeMarketingCreativeAsset,
      clearMarketingCreativeAssets,

      syncBrandFoundationFromMarketingForm,
      setBrandFoundationState,
      patchBrandFoundationState,
      setBrandFoundationField,
      setBrandFoundationSection,
      patchBrandFoundationSection,
      setBrandFoundationNestedValue,
      patchBrandFoundationNestedObject,
      setBrandMapNestedValue,
      patchBrandMapNestedObject,

      applyRefreshPayload,
      applyRecoveryPayload,
      applyWorkspaceContext,
      hydrateLocalTruth,
      getSnapshotBundle,
    };
  }

  global.TessarisDesktopStore = {
    createDesktopStore,
  };
})(window);
