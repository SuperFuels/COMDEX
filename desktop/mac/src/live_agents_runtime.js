(function initTessarisDesktopLiveAgentsRuntime(window) {
  const runtimeShared = window.TessarisDesktopRuntimeShared;

  if (!runtimeShared) {
    throw new Error("TessarisDesktopRuntimeShared must load before live_agents_runtime.js");
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizeDepartmentKey(value) {
    return runtimeShared.normalizeDepartmentKey(value);
  }

  function sortRunsNewestFirst(a, b) {
    const aTime = new Date(
      a?.updated_at || a?.completed_at || a?.created_at || 0,
    ).getTime();
    const bTime = new Date(
      b?.updated_at || b?.completed_at || b?.created_at || 0,
    ).getTime();
    return bTime - aTime;
  }

  function getRunAgentId(run) {
    return (
      runtimeShared.getRunAgentId?.(run) ||
      runtimeShared.getRunAgentLabel(run)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "") ||
      "unknown_agent"
    );
  }

  function buildLiveAgentCards(runs) {
    const items = safeArray(runs);
    const grouped = new Map();

    for (const run of items) {
      const agentId = getRunAgentId(run);
      const agentLabel = runtimeShared.getRunAgentLabel(run);
      const workflowName = runtimeShared.getRunWorkflowLabel(run);
      const departmentKey = runtimeShared.getRunDepartmentKey(run);
      const status = runtimeShared.getRunStatus(run);

      if (!grouped.has(agentId)) {
        grouped.set(agentId, {
          id: agentId,
          label: agentLabel,
          departmentKey,
          queued: 0,
          running: 0,
          waitingApproval: 0,
          failed: 0,
          completed: 0,
          cancelled: 0,
          total: 0,
          latestRun: null,
          runs: [],
        });
      }

      const card = grouped.get(agentId);
      card.total += 1;
      card.runs.push(run);

      if (status === "queued") card.queued += 1;
      if (status === "running") card.running += 1;
      if (status === "waiting_approval") card.waitingApproval += 1;
      if (status === "failed") card.failed += 1;
      if (status === "completed") card.completed += 1;
      if (status === "cancelled") card.cancelled += 1;

      if (!card.latestRun || sortRunsNewestFirst(run, card.latestRun) < 0) {
        card.latestRun = { ...run, workflow_name: workflowName };
        card.departmentKey = departmentKey;
        card.label = agentLabel;
      }
    }

    return Array.from(grouped.values()).sort((a, b) => {
      const aActive = a.running + a.waitingApproval + a.queued + a.failed;
      const bActive = b.running + b.waitingApproval + b.queued + b.failed;

      if (bActive !== aActive) return bActive - aActive;
      if (b.total !== a.total) return b.total - a.total;
      return String(a.label).localeCompare(String(b.label));
    });
  }

  function getDepartmentPreferredAgentCard(state, departmentKey) {
    const normalizedDepartment = normalizeDepartmentKey(departmentKey);
    const cards = buildLiveAgentCards(state?.runs).filter(
      (card) => normalizeDepartmentKey(card?.departmentKey) === normalizedDepartment,
    );

    if (!cards.length) {
      return runtimeShared.getDepartmentRuntime(
        state?.runs,
        state?.approvals,
        normalizedDepartment,
      )?.primaryAgent || null;
    }

    return cards[0] || null;
  }

  function getDefaultSelectedLiveAgentCard(state) {
    const cards = buildLiveAgentCards(state?.runs);
    if (!cards.length) return null;

    const activeZone = normalizeDepartmentKey(state?.activeZone || "marketing");
    const preferredDepartmentCard = getDepartmentPreferredAgentCard(
      state,
      activeZone,
    );

    if (preferredDepartmentCard) {
      const exact = cards.find(
        (card) => String(card.id) === String(preferredDepartmentCard.id),
      );
      if (exact) return exact;
    }

    return cards[0] || null;
  }

  function getSelectedLiveAgentCard(state) {
    const cards = buildLiveAgentCards(state?.runs);
    if (!cards.length) return null;

    if (state?.selectedLiveAgentId) {
      const exact = cards.find(
        (card) => String(card.id) === String(state.selectedLiveAgentId),
      );
      if (exact) return exact;
    }

    return getDefaultSelectedLiveAgentCard(state);
  }

  function getRunsForSelectedLiveAgent(state) {
    const runs = safeArray(state?.runs);
    const selectedAgent = getSelectedLiveAgentCard(state);

    if (!selectedAgent) {
      const activeZone = normalizeDepartmentKey(state?.activeZone || "marketing");
      return runs
        .filter(
          (run) => runtimeShared.getRunDepartmentKey(run) === activeZone,
        )
        .sort(sortRunsNewestFirst);
    }

    return runs
      .filter((run) => String(getRunAgentId(run)) === String(selectedAgent.id))
      .sort(sortRunsNewestFirst);
  }

  function getPrimaryDepartmentAgentCard(state, departmentKey) {
    const runtime = runtimeShared.getDepartmentRuntime(
      state?.runs,
      state?.approvals,
      departmentKey,
    );

    return runtime?.primaryAgent || null;
  }


  /*
   * PHASE 21M LOCK: explicit Live Agents department selection wins.
   *
   * The Live Agents department switcher is allowed to select a department
   * even when that department has no current run-backed agent card.
   *
   * This is required for the Aion department because the Pilot cockpit is a
   * native operator surface, not a normal marketing/sales run queue card.
   */
  function getSelectedLiveDepartmentKey(state) {
    const explicitDepartment = String(
      state?.selectedLiveDepartmentKey ||
        state?.activeLiveDepartmentKey ||
        state?.activeZone ||
        "",
    )
      .trim()
      .toLowerCase();

    if (explicitDepartment) {
      return explicitDepartment;
    }

    const selectedAgentCard = getSelectedLiveAgentCard(state);
    const selectedDepartment = String(
      selectedAgentCard?.departmentKey ||
        selectedAgentCard?.department_key ||
        "",
    )
      .trim()
      .toLowerCase();

    return selectedDepartment || "marketing";
  }

  function findSelectedLiveRun(state) {
    const runs = safeArray(state?.runs).sort(sortRunsNewestFirst);
    if (!runs.length) return null;

    if (state?.selectedLiveRunId) {
      const exact = runs.find(
        (run) =>
          String(runtimeShared.getRunId?.(run) || run?.id || run?.queue_item_id || "") ===
          String(state.selectedLiveRunId),
      );

      if (exact) return exact;
    }

    const selectedAgent = getSelectedLiveAgentCard(state);
    if (selectedAgent) {
      const agentRuns = runs.filter(
        (run) => String(getRunAgentId(run)) === String(selectedAgent.id),
      );
      if (agentRuns.length) return agentRuns[0];
    }

    const activeZone = normalizeDepartmentKey(state?.activeZone || "marketing");
    const departmentRuns = runs.filter(
      (run) => runtimeShared.getRunDepartmentKey(run) === activeZone,
    );
    if (departmentRuns.length) return departmentRuns[0];

    return runs[0] || null;
  }

  function ensureLiveAgentSelection(state) {
    const selectedAgent = getSelectedLiveAgentCard(state);
    const selectedRun = findSelectedLiveRun(state);

    return {
      selectedLiveAgentId: selectedAgent?.id || null,
      selectedLiveRunId: selectedRun
        ? runtimeShared.getRunId?.(selectedRun) ||
          selectedRun?.id ||
          selectedRun?.queue_item_id ||
          null
        : null,
      selectedDepartmentKey: getSelectedLiveDepartmentKey(state),
    };
  }

  window.TessarisDesktopLiveAgentsRuntime = {
    buildLiveAgentCards,
    getSelectedLiveAgentCard,
    getRunsForSelectedLiveAgent,
    getPrimaryDepartmentAgentCard,
    getSelectedLiveDepartmentKey,
    getDepartmentPreferredAgentCard,
    getDefaultSelectedLiveAgentCard,
    findSelectedLiveRun,
    ensureLiveAgentSelection,
  };
})(window);