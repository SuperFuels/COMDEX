(function initDesktopCache(global) {
  const contracts = global.TessarisDesktopContracts;

  if (!contracts) {
    throw new Error("TessarisDesktopContracts is required before desktop-cache.js");
  }

  function readJsonStorage(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return fallback;
      return JSON.parse(raw);
    } catch (_) {
      return fallback;
    }
  }

  function writeJsonStorage(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (_) {
      // ignore storage failure
    }
  }

  function readTextStorage(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw == null || raw === "" ? fallback : raw;
    } catch (_) {
      return fallback;
    }
  }

  function writeTextStorage(key, value) {
    try {
      localStorage.setItem(key, String(value ?? ""));
    } catch (_) {
      // ignore storage failure
    }
  }

  function normalizeBaseUrl(value, fallback) {
    const raw = String(value ?? "").trim();
    if (!raw) return fallback;

    try {
      const url = new URL(raw);
      return `${url.protocol}//${url.host}`;
    } catch (_) {
      return raw.replace(/\/+$/, "");
    }
  }

  function isObject(value) {
    return value && typeof value === "object" && !Array.isArray(value);
  }

  function cloneValue(value) {
    if (value == null) return value;

    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_) {
      return value;
    }
  }

  function normalizeMarketingForm(value) {
    if (typeof contracts.normalizeMarketingForm === "function") {
      return contracts.normalizeMarketingForm(value);
    }

    return {
      ...contracts.buildDefaultMarketingForm(),
      ...(isObject(value) ? value : {}),
    };
  }

  function normalizeBrandFoundationState(value, marketingForm) {
    if (typeof contracts.normalizeBrandFoundationState === "function") {
      return contracts.normalizeBrandFoundationState(value, marketingForm);
    }

    return {
      ...contracts.buildDefaultBrandFoundationState(marketingForm),
      ...(isObject(value) ? value : {}),
    };
  }

  function normalizeRecoveryPayload(value) {
    if (typeof contracts.normalizeRecoveryPayload === "function") {
      return contracts.normalizeRecoveryPayload(value);
    }

    return isObject(value) ? cloneValue(value) : null;
  }

  function buildLiveAgentsSnapshotSeed(next) {
    return next.liveAgentsSnapshot || {
      runs: next.runs,
      approvals: next.approvals,
      selectedLiveAgentId: next.selectedLiveAgentId,
      selectedLiveRunId: next.selectedLiveRunId,
      liveAgentsReplayOpen: next.liveAgentsReplayOpen,
      liveAgentsView: next.liveAgentsView,
      activeZone: next.activeZone,
      updatedAt: next.lastRefreshAt,
    };
  }

  function buildOperationsFlowSnapshotSeed(next) {
    return next.operationsFlowSnapshot || {
      viewMode: next.operationsFlowViewMode,
      activeZone: next.activeZone,
      selectedSeatId: next.selectedSeatId,
      selectedInspectorTarget: next.selectedInspectorTarget,
      boardroomSnapshot: next.boardroomSnapshot,
      containerBindings: next.containerBindings,
      workspace:
        next.operationsFlowSnapshot?.workspace ??
        next.boardroomSnapshot?.workspace ??
        null,
      pulse:
        next.operationsFlowSnapshot?.pulse ??
        next.boardroomSnapshot?.pulse ??
        null,
      runtime:
        next.operationsFlowSnapshot?.runtime ??
        next.boardroomSnapshot?.runtime ??
        null,
      topology:
        next.operationsFlowSnapshot?.topology ??
        next.boardroomSnapshot?.topology ??
        null,
      updatedAt: next.lastRefreshAt,
    };
  }

  function extractRecoveredBrandFoundation(recoveryPayload) {
    const recovery = normalizeRecoveryPayload(recoveryPayload);

    if (!recovery || typeof recovery !== "object") {
      return null;
    }

    return (
      recovery.brandFoundationState ??
      recovery.brand_foundation_state ??
      recovery.brand_foundation ??
      recovery.brandFoundation ??
      null
    );
  }

  function normalizeSeed(seed) {
    const baseSeed = seed && typeof seed === "object" ? seed : {};
    const next = contracts.buildDefaultState(baseSeed);

    next.apiBase = normalizeBaseUrl(
      next.apiBase,
      contracts.DEFAULTS.apiBase,
    );

    next.webBase = normalizeBaseUrl(
      next.webBase,
      contracts.DEFAULTS.webBase,
    );

    next.workspaceId = String(
      next.workspaceId || contracts.DEFAULTS.workspaceId,
    );

    next.nodeId = String(
      next.nodeId || contracts.DEFAULTS.nodeId,
    );

    next.activeTab = contracts.normalizeActiveTab(next.activeTab);

    next.boardroomViewMode = contracts.normalizeBoardroomViewMode(
      next.boardroomViewMode,
    );

    next.operationsFlowViewMode = contracts.normalizeOperationsFlowViewMode(
      next.operationsFlowViewMode,
    );

    next.activeZone = contracts.normalizeActiveZone(next.activeZone);

    next.selectedSeatId = contracts.normalizeSelectedSeatId(
      next.selectedSeatId,
    );

    next.selectedInspectorTarget = contracts.normalizeSelectedInspectorTarget(
      next.selectedInspectorTarget,
    );

    next.selectedLiveAgentId = contracts.normalizeSelectedLiveAgentId(
      next.selectedLiveAgentId,
    );

    next.selectedLiveRunId = contracts.normalizeSelectedLiveRunId(
      next.selectedLiveRunId,
    );

    next.liveAgentsReplayOpen = contracts.normalizeLiveAgentsReplayOpen(
      next.liveAgentsReplayOpen,
    );

    next.liveAgentsView = contracts.normalizeLiveAgentsView(
      next.liveAgentsView,
    );

    next.marketingCalendarMode = contracts.normalizeMarketingCalendarMode(
      next.marketingCalendarMode,
    );

    next.containerBindings = contracts.normalizeContainerBindings(
      next.containerBindings,
    );

    next.marketingForm = normalizeMarketingForm(next.marketingForm);

    next.brandFoundationState = normalizeBrandFoundationState(
      next.brandFoundationState,
      next.marketingForm,
    );

    next.dashboardSummary = contracts.normalizeDashboardSummary(
      next.dashboardSummary,
      next.workspaceId,
      next.nodeId,
    );

    next.boardroomSnapshot = contracts.normalizeBoardroomSnapshot(
      next.boardroomSnapshot,
      next.workspaceId,
    );

    next.liveAgentsSnapshot = contracts.normalizeLiveAgentsSnapshot(
      buildLiveAgentsSnapshotSeed(next),
    );

    next.operationsFlowSnapshot = contracts.normalizeOperationsFlowSnapshot(
      buildOperationsFlowSnapshotSeed(next),
    );

    next.recoveryPayload = normalizeRecoveryPayload(next.recoveryPayload);

    const recoveredBrandFoundation = extractRecoveredBrandFoundation(
      next.recoveryPayload,
    );

    if (recoveredBrandFoundation) {
      next.brandFoundationState = normalizeBrandFoundationState(
        recoveredBrandFoundation,
        next.marketingForm,
      );
    }

    next.syncBoundary = isObject(next.syncBoundary)
      ? cloneValue(next.syncBoundary)
      : contracts.buildDefaultSyncBoundary();

    return next;
  }

  function loadSeedFromStorage() {
    const workspaceId = readTextStorage(
      contracts.STORAGE_KEYS.workspaceId,
      contracts.DEFAULTS.workspaceId,
    );

    const nodeId = readTextStorage(
      contracts.STORAGE_KEYS.nodeId,
      contracts.DEFAULTS.nodeId,
    );

    const marketingForm = normalizeMarketingForm(
      readJsonStorage(
        contracts.CACHE_KEYS.marketingForm,
        contracts.buildDefaultMarketingForm(),
      ),
    );

    const brandFoundationState = normalizeBrandFoundationState(
      readJsonStorage(
        contracts.CACHE_KEYS.brandFoundationState,
        contracts.buildDefaultBrandFoundationState(marketingForm),
      ),
      marketingForm,
    );

    const liveAgentsViewFromStorage = readTextStorage(
      contracts.STORAGE_KEYS.liveAgentsView,
      readJsonStorage(
        contracts.CACHE_KEYS.liveAgentsView,
        contracts.DEFAULTS.liveAgentsView,
      ),
    );

    const marketingCalendarModeFromStorage = readTextStorage(
      contracts.STORAGE_KEYS.marketingCalendarMode,
      readJsonStorage(
        contracts.CACHE_KEYS.marketingCalendarMode,
        contracts.DEFAULTS.marketingCalendarMode,
      ),
    );

    const boardroomSnapshotFromCache = readJsonStorage(
      contracts.CACHE_KEYS.boardroomSnapshot,
      contracts.buildDefaultBoardroomSnapshot(workspaceId),
    );

    const liveAgentsSnapshotFromCache = readJsonStorage(
      contracts.CACHE_KEYS.liveAgentsSnapshot,
      contracts.buildDefaultLiveAgentsSnapshot(),
    );

    const operationsFlowSnapshotFromCache = readJsonStorage(
      contracts.CACHE_KEYS.operationsFlowSnapshot,
      contracts.buildDefaultOperationsFlowSnapshot(),
    );

    const recoveryPayloadFromCache = readJsonStorage(
      contracts.CACHE_KEYS.recoveryPayload,
      null,
    );

    return normalizeSeed({
      apiBase: readTextStorage(
        contracts.STORAGE_KEYS.apiBase,
        contracts.DEFAULTS.apiBase,
      ),

      webBase: readTextStorage(
        contracts.STORAGE_KEYS.webBase,
        contracts.DEFAULTS.webBase,
      ),

      workspaceId,
      nodeId,

      activeTab: readTextStorage(
        contracts.STORAGE_KEYS.activeTab,
        contracts.DEFAULTS.activeTab,
      ),

      boardroomViewMode: readTextStorage(
        contracts.STORAGE_KEYS.boardroomViewMode,
        contracts.DEFAULTS.boardroomViewMode,
      ),

      operationsFlowViewMode: readTextStorage(
        contracts.STORAGE_KEYS.operationsFlowViewMode,
        contracts.DEFAULTS.operationsFlowViewMode,
      ),

      activeZone: readTextStorage(
        contracts.STORAGE_KEYS.activeZone,
        contracts.DEFAULTS.activeZone,
      ),

      selectedSeatId: readTextStorage(
        contracts.STORAGE_KEYS.selectedSeatId,
        contracts.DEFAULTS.selectedSeatId,
      ),

      selectedInspectorTarget: readJsonStorage(
        contracts.STORAGE_KEYS.selectedInspectorTarget,
        contracts.DEFAULTS.selectedInspectorTarget,
      ),

      selectedLiveAgentId: readTextStorage(
        contracts.STORAGE_KEYS.selectedLiveAgentId,
        contracts.DEFAULTS.selectedLiveAgentId,
      ),

      selectedLiveRunId: readTextStorage(
        contracts.STORAGE_KEYS.selectedLiveRunId,
        contracts.DEFAULTS.selectedLiveRunId,
      ),

      liveAgentsReplayOpen: readJsonStorage(
        contracts.STORAGE_KEYS.liveAgentsReplayOpen,
        contracts.DEFAULTS.liveAgentsReplayOpen,
      ),

      liveAgentsView: liveAgentsViewFromStorage,
      marketingCalendarMode: marketingCalendarModeFromStorage,

      status: readJsonStorage(
        contracts.CACHE_KEYS.status,
        null,
      ),

      runs: readJsonStorage(
        contracts.CACHE_KEYS.runs,
        [],
      ),

      approvals: readJsonStorage(
        contracts.CACHE_KEYS.approvals,
        [],
      ),

      audit: readJsonStorage(
        contracts.CACHE_KEYS.audit,
        [],
      ),

      scheduler: readJsonStorage(
        contracts.CACHE_KEYS.scheduler,
        null,
      ),

      dashboardSummary: readJsonStorage(
        contracts.CACHE_KEYS.dashboardSummary,
        contracts.buildDefaultDashboardSummary(workspaceId, nodeId),
      ),

      marketingSummary: readJsonStorage(
        contracts.CACHE_KEYS.marketingSummary,
        null,
      ),

      boardroomSnapshot: boardroomSnapshotFromCache,
      liveAgentsSnapshot: liveAgentsSnapshotFromCache,
      operationsFlowSnapshot: operationsFlowSnapshotFromCache,
      recoveryPayload: recoveryPayloadFromCache,

      brandFoundationState,

      containerBindings: readJsonStorage(
        contracts.CACHE_KEYS.containerBindings,
        [],
      ),

      syncBoundary: readJsonStorage(
        contracts.CACHE_KEYS.syncBoundary,
        contracts.buildDefaultSyncBoundary(),
      ),

      marketingForm,

      lastRefreshAt: readJsonStorage(
        contracts.CACHE_KEYS.lastRefreshAt,
        null,
      ),
    });
  }

  function persistBinding(state) {
    const normalized = normalizeSeed(state);

    writeTextStorage(contracts.STORAGE_KEYS.apiBase, normalized.apiBase);
    writeTextStorage(contracts.STORAGE_KEYS.webBase, normalized.webBase);
    writeTextStorage(contracts.STORAGE_KEYS.workspaceId, normalized.workspaceId);
    writeTextStorage(contracts.STORAGE_KEYS.nodeId, normalized.nodeId);
    writeTextStorage(contracts.STORAGE_KEYS.activeTab, normalized.activeTab);
    writeTextStorage(
      contracts.STORAGE_KEYS.boardroomViewMode,
      normalized.boardroomViewMode,
    );
    writeTextStorage(
      contracts.STORAGE_KEYS.operationsFlowViewMode,
      normalized.operationsFlowViewMode,
    );
    writeTextStorage(contracts.STORAGE_KEYS.activeZone, normalized.activeZone);

    writeTextStorage(
      contracts.STORAGE_KEYS.selectedSeatId,
      normalized.selectedSeatId == null ? "" : normalized.selectedSeatId,
    );

    writeJsonStorage(
      contracts.STORAGE_KEYS.selectedInspectorTarget,
      normalized.selectedInspectorTarget,
    );

    writeTextStorage(
      contracts.STORAGE_KEYS.selectedLiveAgentId,
      normalized.selectedLiveAgentId == null
        ? ""
        : normalized.selectedLiveAgentId,
    );

    writeTextStorage(
      contracts.STORAGE_KEYS.selectedLiveRunId,
      normalized.selectedLiveRunId == null
        ? ""
        : normalized.selectedLiveRunId,
    );

    writeJsonStorage(
      contracts.STORAGE_KEYS.liveAgentsReplayOpen,
      normalized.liveAgentsReplayOpen,
    );

    writeTextStorage(
      contracts.STORAGE_KEYS.liveAgentsView,
      normalized.liveAgentsView,
    );

    writeTextStorage(
      contracts.STORAGE_KEYS.marketingCalendarMode,
      normalized.marketingCalendarMode,
    );
  }

  function persistCache(state) {
    const normalized = normalizeSeed(state);

    writeJsonStorage(contracts.CACHE_KEYS.status, normalized.status);
    writeJsonStorage(contracts.CACHE_KEYS.runs, normalized.runs);
    writeJsonStorage(contracts.CACHE_KEYS.approvals, normalized.approvals);
    writeJsonStorage(contracts.CACHE_KEYS.audit, normalized.audit);
    writeJsonStorage(contracts.CACHE_KEYS.scheduler, normalized.scheduler);
    writeJsonStorage(
      contracts.CACHE_KEYS.dashboardSummary,
      normalized.dashboardSummary,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.marketingSummary,
      normalized.marketingSummary,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.boardroomSnapshot,
      normalized.boardroomSnapshot,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.liveAgentsSnapshot,
      normalized.liveAgentsSnapshot,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.operationsFlowSnapshot,
      normalized.operationsFlowSnapshot,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.recoveryPayload,
      normalized.recoveryPayload,
    );

    writeJsonStorage(
      contracts.CACHE_KEYS.brandFoundationState,
      normalizeBrandFoundationState(
        normalized.brandFoundationState,
        normalized.marketingForm,
      ),
    );

    writeJsonStorage(
      contracts.CACHE_KEYS.containerBindings,
      normalized.containerBindings,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.syncBoundary,
      normalized.syncBoundary,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.marketingForm,
      normalized.marketingForm,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.lastRefreshAt,
      normalized.lastRefreshAt,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.liveAgentsView,
      normalized.liveAgentsView,
    );
    writeJsonStorage(
      contracts.CACHE_KEYS.marketingCalendarMode,
      normalized.marketingCalendarMode,
    );
  }

  function clearCacheOnly() {
    [
      contracts.CACHE_KEYS.status,
      contracts.CACHE_KEYS.runs,
      contracts.CACHE_KEYS.approvals,
      contracts.CACHE_KEYS.audit,
      contracts.CACHE_KEYS.scheduler,
      contracts.CACHE_KEYS.dashboardSummary,
      contracts.CACHE_KEYS.marketingSummary,
      contracts.CACHE_KEYS.boardroomSnapshot,
      contracts.CACHE_KEYS.liveAgentsSnapshot,
      contracts.CACHE_KEYS.operationsFlowSnapshot,
      contracts.CACHE_KEYS.recoveryPayload,
      contracts.CACHE_KEYS.brandFoundationState,
      contracts.CACHE_KEYS.containerBindings,
      contracts.CACHE_KEYS.syncBoundary,
      contracts.CACHE_KEYS.marketingForm,
      contracts.CACHE_KEYS.lastRefreshAt,
      contracts.CACHE_KEYS.liveAgentsView,
      contracts.CACHE_KEYS.marketingCalendarMode,
    ].forEach((key) => {
      try {
        localStorage.removeItem(key);
      } catch (_) {
        // ignore storage failure
      }
    });
  }

  global.TessarisDesktopCache = {
    readJsonStorage,
    writeJsonStorage,
    readTextStorage,
    writeTextStorage,
    normalizeBaseUrl,
    normalizeMarketingForm,
    normalizeBrandFoundationState,
    normalizeSeed,
    loadSeedFromStorage,
    persistBinding,
    persistCache,
    clearCacheOnly,
  };
})(window);