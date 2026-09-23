(function initTessarisDesktopRuntimeShared(window) {
  function safeArray(value) {
    return Array.isArray(value) ? value : [];
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

  function normalizeDepartmentKey(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (!raw) return "unknown";

    if (raw === "ops" || raw === "operation") return "operations";
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

  function getRunAgentId(run) {
    return firstNonEmptyString(
      run?.operator_id,
      run?.agent_id,
      run?.operator?.id,
      run?.agent?.id,
      "unknown_agent",
    );
  }

  function getRunAgentLabel(run) {
    return (
      firstNonEmptyString(
        run?.operator_name,
        run?.agent_name,
        run?.operator?.name,
        run?.agent?.name,
        run?.agent_label,
        run?.operator_label,
      ) || getRunAgentId(run)
    );
  }

  function getRunWorkflowLabel(run) {
    return (
      firstNonEmptyString(
        run?.workflow_name,
        run?.workflow_label,
        run?.workflow_title,
        run?.workflow_id,
        run?.title,
        run?.name,
      ) || "workflow"
    );
  }

  function getRunDepartmentKey(run) {
    return normalizeDepartmentKey(
      firstDefined(
        run?.department_key,
        run?.departmentKey,
        run?.department?.key,
        run?.department?.slug,
        run?.seat?.department_key,
        run?.seat?.departmentKey,
        run?.context?.department_key,
        run?.context?.departmentKey,
        run?.result?.department_key,
        run?.result?.departmentKey,
        run?.operator?.department_key,
        run?.operator?.departmentKey,
        "unknown",
      ),
    );
  }

  function getApprovalDepartmentKey(approval) {
    return normalizeDepartmentKey(
      firstDefined(
        approval?.department_key,
        approval?.departmentKey,
        approval?.department?.key,
        approval?.department?.slug,
        approval?.context?.department_key,
        approval?.context?.departmentKey,
        "unknown",
      ),
    );
  }

  function getApprovalLinkedRunId(approval) {
    return (
      approval?.run_id ||
      approval?.queue_item_id ||
      approval?.runtime_run_id ||
      null
    );
  }

  function getApprovalRunId(approval) {
    return getApprovalLinkedRunId(approval);
  }

  function getDepartmentLabel(departmentKey) {
    const map = {
      marketing: "Marketing",
      sales: "Sales",
      finance: "Finance",
      operations: "Operations",
      support: "Support",
      hr: "HR",
      ceo: "CEO",
      coo: "COO Core",
      aion: "Aion",
      openai: "OpenAI",
    };

    const normalized = normalizeDepartmentKey(departmentKey);

    return (
      map[normalized] ||
      normalized.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()) ||
      "Department"
    );
  }

  function getDepartmentRoomOrder() {
    return [
      "marketing",
      "sales",
      "finance",
      "operations",
      "support",
      "hr",
      "ceo",
      "coo",
      "aion",
    ];
  }

  function getDepartmentKeysWithRuntimeData(runs, approvals) {
    const keys = new Set(getDepartmentRoomOrder());

    safeArray(runs).forEach((run) => {
      keys.add(getRunDepartmentKey(run));
    });

    safeArray(approvals).forEach((approval) => {
      keys.add(getApprovalDepartmentKey(approval));
    });

    return Array.from(keys);
  }

  function buildDepartmentRuntimeIndex(runs, approvals) {
    const runItems = safeArray(runs);
    const approvalItems = safeArray(approvals);
    const grouped = new Map();

    function ensureDepartment(departmentKey) {
      const key = normalizeDepartmentKey(departmentKey || "unknown");

      if (!grouped.has(key)) {
        grouped.set(key, {
          key,
          label: getDepartmentLabel(key),

          totalRuns: 0,
          queued: 0,
          running: 0,
          waitingApproval: 0,
          failed: 0,
          completed: 0,
          cancelled: 0,

          totalApprovals: 0,
          pendingApprovals: 0,
          approvedApprovals: 0,
          rejectedApprovals: 0,

          agents: new Map(),
          agentCards: [],
          agentCount: 0,
          runs: [],
          approvals: [],
          latestRun: null,
          primaryAgent: null,
        });
      }

      return grouped.get(key);
    }

    getDepartmentKeysWithRuntimeData(runItems, approvalItems).forEach((key) => {
      ensureDepartment(key);
    });

    runItems.forEach((run) => {
      const department = ensureDepartment(getRunDepartmentKey(run));
      const agentId = String(getRunAgentId(run));
      const agentLabel = getRunAgentLabel(run);
      const status = getRunStatus(run);

      department.totalRuns += 1;
      department.runs.push(run);

      if (status === "queued") department.queued += 1;
      if (status === "running") department.running += 1;
      if (status === "waiting_approval") department.waitingApproval += 1;
      if (status === "failed") department.failed += 1;
      if (status === "completed") department.completed += 1;
      if (status === "cancelled") department.cancelled += 1;

      if (!department.agents.has(agentId)) {
        department.agents.set(agentId, {
          id: agentId,
          label: agentLabel,
          departmentKey: department.key,
          runs: [],
          totalRuns: 0,
          queued: 0,
          running: 0,
          waitingApproval: 0,
          failed: 0,
          completed: 0,
          cancelled: 0,
          latestRun: null,
        });
      }

      const agent = department.agents.get(agentId);
      agent.runs.push(run);
      agent.totalRuns += 1;
      if (status === "queued") agent.queued += 1;
      if (status === "running") agent.running += 1;
      if (status === "waiting_approval") agent.waitingApproval += 1;
      if (status === "failed") agent.failed += 1;
      if (status === "completed") agent.completed += 1;
      if (status === "cancelled") agent.cancelled += 1;

      const runTime = new Date(run?.updated_at || run?.created_at || 0).getTime();

      const deptLatestTime = new Date(
        department.latestRun?.updated_at || department.latestRun?.created_at || 0,
      ).getTime();

      if (!department.latestRun || runTime > deptLatestTime) {
        department.latestRun = run;
      }

      const agentLatestTime = new Date(
        agent.latestRun?.updated_at || agent.latestRun?.created_at || 0,
      ).getTime();

      if (!agent.latestRun || runTime > agentLatestTime) {
        agent.latestRun = run;
      }
    });

    approvalItems.forEach((approval) => {
      const department = ensureDepartment(getApprovalDepartmentKey(approval));
      const status = String(approval?.status || "").toLowerCase();

      department.totalApprovals += 1;
      department.approvals.push(approval);

      if (status === "pending") department.pendingApprovals += 1;
      if (status === "approved") department.approvedApprovals += 1;
      if (status === "rejected") department.rejectedApprovals += 1;
    });

    grouped.forEach((department) => {
      const agentCards = Array.from(department.agents.values()).sort((a, b) => {
        const aActive = a.running + a.waitingApproval + a.queued + a.failed;
        const bActive = b.running + b.waitingApproval + b.queued + b.failed;
        if (bActive !== aActive) return bActive - aActive;
        if (b.totalRuns !== a.totalRuns) return b.totalRuns - a.totalRuns;
        return String(a.label).localeCompare(String(b.label));
      });

      department.agentCards = agentCards;
      department.agentCount = agentCards.length;
      department.primaryAgent = agentCards[0] || null;
    });

    return grouped;
  }

  function getDepartmentRuntimeList(runs, approvals) {
    const index = buildDepartmentRuntimeIndex(runs, approvals);
    return getDepartmentKeysWithRuntimeData(runs, approvals)
      .map((key) => index.get(normalizeDepartmentKey(key)))
      .filter(Boolean);
  }

  function getDepartmentRuntime(runs, approvals, departmentKey) {
    const index = buildDepartmentRuntimeIndex(runs, approvals);
    return index.get(normalizeDepartmentKey(departmentKey || "unknown")) || null;
  }

  function getRecentDepartmentRuns(runs, approvals, departmentKey, limit = 4) {
    const runtime = getDepartmentRuntime(runs, approvals, departmentKey);
    if (!runtime) return [];

    return runtime.runs
      .slice()
      .sort((a, b) => {
        const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
        const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
        return bTime - aTime;
      })
      .slice(0, limit);
  }

  function getDepartmentExceptions(runs, limit = 10) {
    return safeArray(runs)
      .filter((run) => {
        const status = getRunStatus(run);
        return status === "waiting_approval" || status === "failed";
      })
      .slice()
      .sort((a, b) => {
        const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
        const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
        return bTime - aTime;
      })
      .slice(0, limit);
  }

  window.TessarisDesktopRuntimeShared = {
    safeArray,
    normalizeDepartmentKey,
    getRunId,
    getRunStatus,
    getRunAgentId,
    getRunAgentLabel,
    getRunWorkflowLabel,
    getRunDepartmentKey,
    getApprovalDepartmentKey,
    getApprovalLinkedRunId,
    getApprovalRunId,
    getDepartmentLabel,
    getDepartmentRoomOrder,
    buildDepartmentRuntimeIndex,
    getDepartmentRuntimeList,
    getDepartmentRuntime,
    getRecentDepartmentRuns,
    getDepartmentExceptions,
  };
})(window);