(function initTessarisDesktopBoardroomRuntime(window) {
  const runtimeShared = window.TessarisDesktopRuntimeShared;
  const liveRuntime = window.TessarisDesktopLiveAgentsRuntime;

  function openDepartmentWorkspaceFromBoardroom(deps, departmentKey, nextView, runId, openReplay) {
    const { desktopStore, state, render } = deps;

    const runtime = runtimeShared.getDepartmentRuntime(state.runs, state.approvals, departmentKey);
    const primaryAgent = runtime?.primaryAgent || null;
    const resolvedView = nextView || "stream";
    const resolvedRunId =
      runId ||
      runtime?.latestRun?.id ||
      runtime?.latestRun?.queue_item_id ||
      null;

    desktopStore.updateBoardroomSelection({
      activeZone: departmentKey || state.activeZone || "coo",
      selectedSeatId: state.selectedSeatId || null,
      selectedInspectorTarget: {
        kind: resolvedView === "approvals" ? "department_approvals" : "department_runtime",
        departmentKey: departmentKey || "unknown",
        runId: resolvedRunId || null,
      },
    });

    if (primaryAgent?.id) {
      desktopStore.setSelectedLiveAgentId(primaryAgent.id);
    } else {
      desktopStore.setSelectedLiveAgentId(null);
    }

    if (resolvedRunId) {
      desktopStore.setSelectedLiveRunId(resolvedRunId);
    } else {
      desktopStore.setSelectedLiveRunId(null);
    }

    desktopStore.patch({
      activeTab: "live_agents",
      liveAgentsView: resolvedView,
      activeZone: String(departmentKey || "unknown").toLowerCase(),
    });

    desktopStore.setLiveAgentsReplayOpen(openReplay === true);
    desktopStore.persistBinding();
    desktopStore.persistCache();
    render();
  }

  function setLiveAgentsWorkspace(deps, departmentKey, options = {}) {
    const { desktopStore, state, LIVE_AGENT_VIEWS } = deps;
    const {
      preferredView = LIVE_AGENT_VIEWS.STREAM,
      openReplay = false,
      runId = null,
    } = options;

    const primaryCard = liveRuntime.getPrimaryDepartmentAgentCard(state, departmentKey);
    const normalizedDepartment = String(departmentKey || "").toLowerCase();

    if (primaryCard?.id) {
      desktopStore.setSelectedLiveAgentId(primaryCard.id);
    } else {
      desktopStore.setSelectedLiveAgentId(null);
    }

    if (runId) {
      desktopStore.setSelectedLiveRunId(runId);
    } else if (primaryCard?.latestRun?.id || primaryCard?.latestRun?.queue_item_id) {
      desktopStore.setSelectedLiveRunId(
        primaryCard.latestRun.id || primaryCard.latestRun.queue_item_id,
      );
    } else {
      desktopStore.setSelectedLiveRunId(null);
    }

    desktopStore.patch({
      activeTab: "live_agents",
      liveAgentsView: preferredView,
      activeZone: normalizedDepartment === "operations" ? "operations" : normalizedDepartment,
    });

    desktopStore.setLiveAgentsReplayOpen(openReplay === true);
    desktopStore.persistBinding();
    desktopStore.persistCache();
  }

  window.TessarisDesktopBoardroomRuntime = {
    openDepartmentWorkspaceFromBoardroom,
    setLiveAgentsWorkspace,
  };
})(window);