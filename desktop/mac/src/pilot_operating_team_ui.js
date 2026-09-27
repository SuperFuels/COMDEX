(function installPilotOperatingTeamUI() {
  "use strict";

  if (window.__AION_PILOT_OPERATING_TEAM_UI__) return;
  window.__AION_PILOT_OPERATING_TEAM_UI__ = true;

  const TEACH_DEPARTMENTS = [
    "coo", "finance", "marketing", "operations",
    "people", "products_services", "sales", "support",
  ];

  const runtime = {
    workspace: null,
    loadedWorkspaceId: "",
    teamVisible: false,
    trainSurfacePresent: false,
    loading: false,
    error: "",
    recording: false,
    activeTeachingDepartment: "",
    events: [],
    message: "",
    teachingByDepartment: Object.fromEntries(
      TEACH_DEPARTMENTS.map((department_id) => [department_id, { name: "", outcome: "" }]),
    ),
    routine: {
      title: "",
      department_id: "operations",
      trigger_kind: "schedule",
      interval_value: "1",
      interval_unit: "day",
      event_type: "",
      skill_id: "",
      output_type: "capability_default",
      output_instructions: "",
      output_destination: "file_cabinet",
    },
    workflowRoutine: {
      title: "",
      workflow_id: "",
      trigger_kind: "schedule",
      interval_value: "1",
      interval_unit: "day",
      event_type: "",
    },
    worker: { node_id: "", label: "", capabilities: "browser.read, files.prepare" },
    missionOutcome: "",
    editingSkill: null,
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function workspaceId() {
    try {
      const desktopState = window.__AION_DESKTOP_STATE__ || window.state || {};
      const candidates = [
        window.AionBusinessContainerClient?.resolveBusinessId?.(),
        window.__aionCanonicalBusinessId,
        desktopState.activeBusinessWorkspaceId,
        desktopState.businessWorkspace?.workspace_id,
        desktopState.activeWorkspaceId,
        desktopState.workspace_id,
        desktopState.workspaceId,
      ];
      const resolved = candidates
        .map((value) => String(value || "").trim())
        .find(Boolean);
      return resolved || "default";
    } catch (_) {
      return "default";
    }
  }

  function apiBase() {
    const desktopState = window.__AION_DESKTOP_STATE__ || window.state || {};
    return String(
      desktopState.apiBase ||
      desktopState.desktopApiBase ||
      window.__AION_API_BASE__ ||
      window.AION_API_BASE ||
      "http://127.0.0.1:8080",
    ).replace(/\/+$/, "");
  }

  async function api(path, options = {}) {
    const controller = new AbortController();
    const timeoutMs = Number(options.timeoutMs || 12000);
    const { timeoutMs: _ignoredTimeout, ...fetchOptions } = options;
    const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
      response = await fetch(`${apiBase()}/api/aion/business/pilot-team/${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...fetchOptions,
        signal: fetchOptions.signal || controller.signal,
      });
    } catch (error) {
      if (error?.name === "AbortError") {
        throw new Error("Pilot runtime did not respond. Restart Tessaris and try again.");
      }
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Pilot team request failed (${response.status})`);
    }
    return payload;
  }

  async function loadWorkspace(force = false) {
    const requestedWorkspaceId = workspaceId();
    if (runtime.loading) return runtime.workspace;
    if (runtime.workspace && runtime.loadedWorkspaceId === requestedWorkspaceId && !force) {
      return runtime.workspace;
    }
    runtime.loading = true;
    runtime.error = "";
    try {
      runtime.workspace = await api(encodeURIComponent(requestedWorkspaceId));
      runtime.loadedWorkspaceId = requestedWorkspaceId;
      syncWorkflowSkillModules();
      return runtime.workspace;
    } catch (error) {
      runtime.error = String(error?.message || error);
      return null;
    } finally {
      runtime.loading = false;
      render();
    }
  }

  function syncWorkflowSkillModules() {
    const skills = Array.isArray(runtime.workspace?.skills) ? runtime.workspace.skills : [];
    window.__aionPilotWorkflowSkillModules = skills
      .filter((skill) => skill.status === "published" && skill.validation_state === "passed")
      .map((skill) => ({
        id: `pilot.skill.${skill.skill_id}`,
        label: skill.name || "Taught process",
        kind: "capability",
        app: "pilot_skill",
        action_id: "pilot.demonstrated_skill.execute",
        capability_id: "pilot.demonstrated_skill.execute",
        description: skill.outcome || "Run a verified taught process.",
        department_id: skill.department_id,
        skill_id: skill.skill_id,
        skill_hash: skill.skill_hash,
        required_inputs: Array.isArray(skill.required_inputs) ? skill.required_inputs : [],
        output_contract: "verified_skill_result",
        requires_approval: Array.isArray(skill.approval_boundaries) && skill.approval_boundaries.length > 0,
        causes_external_effect: Array.isArray(skill.approval_boundaries) && skill.approval_boundaries.length > 0,
        safety: Array.isArray(skill.approval_boundaries) && skill.approval_boundaries.length > 0
          ? "exact_approval_at_recorded_boundaries"
          : "governed_department_computer",
        status: "Published",
        icon: "TP",
      }));
    document.dispatchEvent(new CustomEvent("aion:pilot-workflow-skills-updated", {
      detail: { count: window.__aionPilotWorkflowSkillModules.length },
    }));
  }

  function savedWorkflows() {
    let tree = {};
    try { tree = window.__aionWorkflowFileCabinetApi?.getTree?.() || {}; } catch (_) {}
    const found = [];
    const seen = new Set();
    const add = (workflow_id, name, graph) => {
      const safeGraph = graph && typeof graph === "object" ? graph : {};
      const node_count = Array.isArray(safeGraph.nodes) ? safeGraph.nodes.length : 0;
      const identity = String(name || safeGraph.name || workflow_id).toLowerCase();
      const isGoalSheet = identity.includes("goal sheet") || identity.includes("goal_sheet");
      if (!workflow_id || !node_count || seen.has(workflow_id) || isGoalSheet) return;
      seen.add(workflow_id);
      found.push({ workflow_id, name: name || safeGraph.name || workflow_id, node_count, graph: safeGraph });
    };
    const walk = (items = []) => items.forEach((item) => {
      if (item?.type === "workflow") {
        const workflow_id = String(item.workflow_id || item.id || "").trim();
        const graph = item.graph && typeof item.graph === "object" ? item.graph : {};
        add(workflow_id, item.name, graph);
      }
      walk(Array.isArray(item?.children) ? item.children : []);
    });
    walk(tree.folders || tree.root?.children || []);
    (Array.isArray(window.__aionWorkflowTabs) ? window.__aionWorkflowTabs : []).forEach((tab) => {
      const graph = tab?.graph && typeof tab.graph === "object" ? { ...tab.graph } : {};
      const tabId = String(tab.id || graph.workflow_id || "").trim();
      if (tabId) graph.workflow_id = tabId;
      add(tabId, tab.title, graph);
    });
    try {
      const persisted = JSON.parse(window.localStorage?.getItem("aion.workflow_builder.workflow_tabs.v1") || "{}");
      (Array.isArray(persisted.tabs) ? persisted.tabs : []).forEach((tab) => {
        const graph = tab?.graph && typeof tab.graph === "object" ? { ...tab.graph } : {};
        const tabId = String(tab.id || graph.workflow_id || "").trim();
        if (tabId) graph.workflow_id = tabId;
        add(tabId, tab.title, graph);
      });
    } catch (_) {}
    let current = {};
    try {
      current = typeof getAionWorkflowDraftState === "function"
        ? getAionWorkflowDraftState()
        : (window.__aionWorkflowGraph || {});
    } catch (_) {
      current = window.__aionWorkflowGraph || {};
    }
    add(String(current.workflow_id || current.id || "").trim(), current.name, current);
    [window.__aionWorkflowMainGraph, window.__aionOpenedGlyphWorkflowGraph].forEach((graph) => {
      const safeGraph = graph && typeof graph === "object" ? graph : {};
      add(String(safeGraph.workflow_id || safeGraph.id || "").trim(), safeGraph.name, safeGraph);
    });
    return found.sort((left, right) => String(left.name).localeCompare(String(right.name)));
  }

  function workflowIntervalMinutes(value, unit) {
    const amount = Math.max(1, Number(value) || 1);
    return Math.round(amount * ({ minute: 1, hour: 60, day: 1440, week: 10080 }[unit] || 1440));
  }

  const ROUTINE_OUTPUTS = [
    ["capability_default", "Use the process's normal result"],
    ["summary", "Summary"],
    ["task_list", "Task list"],
    ["report", "Report"],
    ["spreadsheet_xlsx", "Excel spreadsheet (.xlsx)"],
    ["csv", "CSV file"],
    ["pdf", "PDF document"],
    ["email_draft", "Email draft"],
    ["notification", "Notification"],
    ["update_records", "Update connected records (approval required)"],
    ["action_only", "Perform the action only"],
  ];

  function selectedRoutineSkill() {
    return (runtime.workspace?.skills || []).find((skill) => skill.skill_id === runtime.routine.skill_id) || null;
  }

  function routineAccessContract() {
    const draft = runtime.routine;
    const skill = selectedRoutineSkill();
    const sources = Array.isArray(skill?.source_systems) ? skill.source_systems.filter(Boolean) : [];
    const inputs = Array.isArray(skill?.required_inputs) ? skill.required_inputs.filter(Boolean) : [];
    return {
      mode: "vault_grants_only",
      department_id: draft.department_id,
      skill_id: skill?.skill_id || null,
      required_sources: sources,
      required_inputs: inputs,
      credentials_policy: "vault_or_user_provided",
    };
  }

  function routineOutputContract() {
    const draft = runtime.routine;
    const selected = ROUTINE_OUTPUTS.find(([value]) => value === draft.output_type) || ROUTINE_OUTPUTS[0];
    const fileOutput = ["spreadsheet_xlsx", "csv", "pdf"].includes(draft.output_type);
    return {
      type: draft.output_type,
      label: selected[1],
      instructions: String(draft.output_instructions || "").trim(),
      destination: fileOutput ? draft.output_destination : null,
      completion_receipt: true,
    };
  }

  function routineAccessSummary() {
    const contract = routineAccessContract();
    const department = contract.department_id.replaceAll("_", " ");
    const namedSources = contract.required_sources.length
      ? contract.required_sources.join(", ")
      : `${department} sources required by the selected process`;
    return `Uses: ${namedSources}. Connections, keys and permission grants are checked in Vault before running.`;
  }

  async function createWorkflowRoutine() {
    const draft = runtime.workflowRoutine;
    const workflow = savedWorkflows().find((item) => item.workflow_id === draft.workflow_id);
    if (!workflow) {
      runtime.error = "Choose a saved workflow. A one-node workflow is also supported.";
      render();
      return;
    }
    if (!String(draft.title || "").trim()) {
      runtime.error = "Give this automation a name.";
      render();
      return;
    }
    const scheduled = draft.trigger_kind === "schedule";
    if (!scheduled && !String(draft.event_type || "").trim()) {
      runtime.error = "Enter the business event that should trigger this workflow.";
      render();
      return;
    }
    try {
      await api(`${encodeURIComponent(workspaceId())}/routines`, {
        method: "POST",
        body: JSON.stringify({
          title: String(draft.title).trim(),
          department_id: "coo",
          owner_id: "workflow_scheduler",
          workflow_id: workflow.workflow_id,
          workflow_name: workflow.name,
          workflow_graph: workflow.graph,
          schedule: scheduled ? {
            interval_minutes: workflowIntervalMinutes(draft.interval_value, draft.interval_unit),
            interval_value: Math.max(1, Number(draft.interval_value) || 1),
            interval_unit: draft.interval_unit,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
          } : null,
          event_trigger: scheduled ? null : { event_type: String(draft.event_type).trim() },
          input_source: `saved_workflow:${workflow.workflow_id}`,
          expected_result: `Execute ${workflow.name} and produce governed receipts`,
        }),
      });
      runtime.message = "Workflow automation saved as an off draft. Review its safe test, then enable autopilot.";
      runtime.workflowRoutine.title = "";
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  function addSkillToWorkflow(skillId) {
    const module = (window.__aionPilotWorkflowSkillModules || [])
      .find((item) => item.skill_id === skillId);
    if (!module || typeof window.addAionUnifiedRealNodeFromModule !== "function") {
      runtime.error = "The workflow canvas is not ready for this taught process.";
      render();
      return;
    }
    const added = window.addAionUnifiedRealNodeFromModule({
      ...module,
      group: "Taught Processes",
      group_id: "taught_processes",
    });
    if (!added) return;
    runtime.teamVisible = false;
    runtime.message = `${module.label} was added to the current workflow as an executable taught-process node.`;
    window.requestRender?.();
    render();
  }

  async function queueWorkflowSkillNode(node, inputItems = []) {
    const config = node?.config && typeof node.config === "object" ? node.config : {};
    const skillId = String(config.skill_id || node?.skill_id || "").trim();
    const skillHash = String(config.skill_hash || node?.skill_hash || "").trim();
    if (!skillId || !skillHash) {
      throw new Error("This taught-process node is missing its published skill identity.");
    }

    const graph = window.__aionWorkflowGraph || {};
    const workflowId = String(graph.workflow_id || "workflow_draft");
    const workflowNodeId = String(node?.id || "");
    const inputs = Array.isArray(inputItems)
      ? inputItems.map((item) => item?.json ?? item)
      : [];
    const idempotencyKey = [workflowId, workflowNodeId, skillHash, Date.now()].join(":");

    return api(
      `${encodeURIComponent(workspaceId())}/skills/${encodeURIComponent(skillId)}/runs`,
      {
        method: "POST",
        body: JSON.stringify({
          skill_hash: skillHash,
          workflow_id: workflowId,
          workflow_node_id: workflowNodeId,
          inputs: { items: inputs },
          idempotency_key: idempotencyKey,
          requested_by: "person:founder",
        }),
      },
    );
  }

  window.__aionQueuePilotWorkflowSkillNode = queueWorkflowSkillNode;

  async function bootstrap() {
    runtime.loading = true;
    runtime.error = "";
    try {
      await api(`${encodeURIComponent(workspaceId())}/bootstrap`, {
        method: "POST",
        body: JSON.stringify({ actor_id: "person:founder" }),
      });
      runtime.message = "Persistent Department Pilot workspaces are ready.";
      runtime.workspace = null;
      runtime.loadedWorkspaceId = "";
      runtime.loading = false;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
    } finally {
      runtime.loading = false;
      render();
    }
  }

  async function transferControl(departmentId, human) {
    runtime.loading = true;
    try {
      await api(
        `${encodeURIComponent(workspaceId())}/capsules/${encodeURIComponent(departmentId)}/control`,
        {
          method: "POST",
          body: JSON.stringify({
            control_state: human ? "human" : "pilot",
            controller_id: human ? "person:founder" : `department_pilot:${departmentId}`,
            reason: human ? "Founder took control from live work view" : "Founder returned control to Pilot",
          }),
        },
      );
      runtime.message = human
        ? `You now control the ${departmentId} computer.`
        : `Control returned to the ${departmentId} Pilot.`;
      runtime.workspace = null;
      runtime.loading = false;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
    } finally {
      runtime.loading = false;
      render();
    }
  }

  async function openComputer(departmentId) {
    const capsule = (runtime.workspace?.capsules || []).find((item) => item.department_id === departmentId);
    if (!window.aionDesktop?.openBrowserOperatorIsolatedBrowser) {
      runtime.error = "The native isolated-browser bridge is not available in this build.";
      render();
      return;
    }
    await window.aionDesktop.openBrowserOperatorIsolatedBrowser({
      workspace_id: workspaceId(),
      department_id: departmentId,
      browser_profile_id: capsule?.browser_profile_id,
      mode: "department_computer_capsule",
      mission_id: capsule?.active_mission_id || "",
      task_id: capsule?.active_task_id || "",
      activity_state: capsule?.activity_state || "idle",
      objective: capsule?.current_objective || "",
    });
  }

  async function validateSkill(skillId) {
    const skill = (runtime.workspace?.skills || []).find((item) => item.skill_id === skillId);
    if (!skill) return;
    if (!window.aionDesktop?.replayBrowserSkill) {
      runtime.error = "Semantic replay is not available in this desktop build.";
      render();
      return;
    }
    await openComputer(skill.department_id);
    const result = await window.aionDesktop.replayBrowserSkill({
      steps: skill.steps || [],
      mode: "dry_run",
      inputs: {},
    });
    if (!result?.ok) {
      runtime.error = `Safe validation stopped at ${result?.stopped_at_step_id || "the browser"}: ${result?.status || result?.error || "unknown failure"}.`;
      render();
      return;
    }
    const observed = window.confirm(
      "Every recorded browser target was found. Have you also checked the expected result in a safe test account? " +
      "Choose OK to publish this skill, or Cancel to keep it as a draft.",
    );
    try {
      await api(
        `${encodeURIComponent(workspaceId())}/skills/${encodeURIComponent(skillId)}/validate`,
        {
          method: "POST",
          body: JSON.stringify({
            validated_by: "person:founder",
            publish: observed,
            checks: {
              safe_inputs: true,
              selectors_resolved: true,
              outputs_verified: observed,
              approval_stops_verified: Array.isArray(skill.approval_boundaries),
            },
          }),
        },
      );
      runtime.message = observed
        ? `${skill.name} passed safe validation and is published.`
        : `${skill.name} targets validated; it remains a draft until its outcome is confirmed.`;
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  function editSkill(skillId) {
    const skill = (runtime.workspace?.skills || []).find((item) => item.skill_id === skillId);
    if (!skill) return;
    runtime.editingSkill = { skill_id: skillId, name: skill.name || "", outcome: skill.outcome || "" };
    runtime.error = "";
    render();
  }

  async function saveSkillEdits(skillId) {
    const draft = runtime.editingSkill;
    if (!draft || draft.skill_id !== skillId) return;
    if (!String(draft.name || "").trim() || !String(draft.outcome || "").trim()) {
      runtime.error = "Add both a title and a description before saving.";
      render();
      return;
    }
    try {
      await api(`${encodeURIComponent(workspaceId())}/skills/${encodeURIComponent(skillId)}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: String(draft.name).trim(),
          outcome: String(draft.outcome).trim(),
          updated_by: "person:founder",
        }),
      });
      runtime.editingSkill = null;
      runtime.message = "Taught-process details updated. Existing workflow copies remain executable; new copies use the updated title and description.";
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  async function deleteSkill(skillId) {
    const skill = (runtime.workspace?.skills || []).find((item) => item.skill_id === skillId);
    if (!skill) return;
    const confirmed = window.confirm(
      `Delete “${skill.name}” from the taught-process library?\n\n` +
      "It will no longer be available for new workflows. Existing workflow copies will remain visible but cannot start a new run.",
    );
    if (!confirmed) return;
    try {
      await api(`${encodeURIComponent(workspaceId())}/skills/${encodeURIComponent(skillId)}`, {
        method: "DELETE",
        body: JSON.stringify({ deleted_by: "person:founder" }),
      });
      if (runtime.editingSkill?.skill_id === skillId) runtime.editingSkill = null;
      runtime.message = `${skill.name} was removed from the taught-process library.`;
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  function teachingFields(departmentId) {
    const department_id = TEACH_DEPARTMENTS.includes(departmentId) ? departmentId : "operations";
    const draft = runtime.teachingByDepartment[department_id] || { name: "", outcome: "" };
    return {
      department_id,
      name: draft.name || "Demonstrated browser skill",
      outcome: draft.outcome || "Complete the demonstrated task",
    };
  }

  async function startTeaching(departmentId) {
    const fields = teachingFields(departmentId);
    runtime.events = [];
    runtime.error = "";
    if (!window.aionDesktop?.startBrowserRecording) {
      runtime.error = "The native browser recorder is not available.";
      render();
      return;
    }
    await window.aionDesktop.startBrowserRecording();
    runtime.recording = true;
    runtime.activeTeachingDepartment = fields.department_id;
    runtime.message = "Teaching session started. Demonstrate one short process in the isolated browser.";
    render();
    await openComputer(fields.department_id);
    if (window.aionDesktop?.startCaptureNextClick) {
      const captured = await window.aionDesktop.startCaptureNextClick();
      if (!captured?.ok && runtime.recording) {
        runtime.error = captured?.message || "The next browser click could not be captured.";
        render();
      }
    }
  }

  async function stopTeaching(departmentId) {
    const fields = teachingFields(runtime.activeTeachingDepartment || departmentId);
    if (window.aionDesktop?.stopBrowserRecording) {
      await window.aionDesktop.stopBrowserRecording();
    }
    runtime.recording = false;
    runtime.activeTeachingDepartment = "";
    if (!runtime.events.length) {
      runtime.error = "No browser interactions were captured. Keep the browser open and try the demonstration again.";
      render();
      return;
    }
    try {
      const skill = await api(`${encodeURIComponent(workspaceId())}/skills/demonstrations`, {
        method: "POST",
        body: JSON.stringify({
          ...fields,
          observed_steps: runtime.events,
          created_by: "person:founder",
          source_systems: [...new Set(runtime.events.map((event) => event.url).filter(Boolean))],
          failure_policy: "stop_and_report",
        }),
      });
      runtime.message = `Draft skill created with ${skill.steps?.length || 0} semantic steps. Test and review it before publishing.`;
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  async function createMission() {
    const outcome = String(runtime.missionOutcome || "").trim();
    if (!outcome) {
      runtime.error = "Describe the business outcome for the COO mission.";
      render();
      return;
    }
    runtime.loading = true;
    runtime.message = "The COO is planning the mission with the selected Vault model and routing governed department work.";
    render();
    try {
      const mission = await api(`${encodeURIComponent(workspaceId())}/missions/launch`, {
        method: "POST",
        timeoutMs: 120000,
        body: JSON.stringify({
          outcome,
          requested_by: "person:founder",
          constraints: ["External changes require exact approval"],
          deliverables: ["Evidence-backed completion pack"],
        }),
      });
      const count = mission.assignments?.length || 0;
      runtime.message = mission.planner_status === "proposal_ready"
        ? `Mission launched with ${count} governed department assignment${count === 1 ? "" : "s"}.`
        : `Mission saved, but planning is waiting: ${mission.planner_reason || "the selected Vault model is unavailable"}.`;
      runtime.missionOutcome = "";
      runtime.workspace = null;
      runtime.loading = false;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      runtime.loading = false;
      render();
    }
  }

  async function createRoutine() {
    const draft = runtime.routine;
    if (!String(draft.title).trim()) {
      runtime.error = "Give the routine a name.";
      render();
      return;
    }
    const output = routineOutputContract();
    if (output.type !== "capability_default" && !output.instructions) {
      runtime.error = "Describe what the selected result must contain or do, so Pilot does not invent the format.";
      render();
      return;
    }
    const scheduled = draft.trigger_kind === "schedule";
    if (!scheduled && !String(draft.event_type).trim()) {
      runtime.error = "Choose the business event that should start this routine.";
      render();
      return;
    }
    const skill = selectedRoutineSkill();
    const access = routineAccessContract();
    const expectedResult = output.type === "capability_default"
      ? String(skill?.outcome || `Complete the selected ${draft.department_id.replaceAll("_", " ")} capability`)
      : `${output.label}: ${output.instructions}`;
    try {
      await api(`${encodeURIComponent(workspaceId())}/routines`, {
        method: "POST",
        body: JSON.stringify({
          title: draft.title,
          department_id: draft.department_id,
          owner_id: `department_pilot:${draft.department_id}`,
          skill_id: draft.skill_id || null,
          schedule: scheduled ? {
            interval_minutes: workflowIntervalMinutes(draft.interval_value, draft.interval_unit),
            interval_value: Math.max(1, Number(draft.interval_value) || 1),
            interval_unit: draft.interval_unit,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
          } : null,
          event_trigger: scheduled ? null : { event_type: draft.event_type },
          input_source: access.required_sources.length
            ? `vault_sources:${access.required_sources.join(",")}`
            : `vault_grants:${draft.department_id}`,
          expected_result: expectedResult,
          access_contract: access,
          output_contract: output,
        }),
      });
      runtime.message = "Routine saved as a disabled draft. Review its safe test before switching it on.";
      runtime.routine.title = "";
      runtime.routine.output_instructions = "";
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  async function reviewRoutine(routineId) {
    const routine = (runtime.workspace?.routines || []).find((item) => item.routine_id === routineId);
    if (!routine) return;
    const confirmed = window.confirm(
      `Safe-test review for “${routine.title}”\n\n` +
      `Input: ${routine.input_source}\nResult: ${routine.expected_result}\n\n` +
      "Confirm only after checking the current input, output format, audit trail, approval stop and failure behaviour. No external action will be run by this review.",
    );
    if (!confirmed) return;
    try {
      await api(`${encodeURIComponent(workspaceId())}/routines/${encodeURIComponent(routineId)}/test`, {
        method: "POST",
        body: JSON.stringify({
          tested_by: "person:founder",
          checks: {
            current_inputs_selected: true,
            output_format_valid: true,
            audit_trail_complete: true,
            approval_stop_verified: true,
            failure_states_explicit: true,
          },
        }),
      });
      runtime.message = `${routine.title} passed its founder-reviewed safe test. It remains off until enabled.`;
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  async function toggleRoutine(routineId, enabled) {
    try {
      await api(`${encodeURIComponent(workspaceId())}/routines/${encodeURIComponent(routineId)}/enabled`, {
        method: "POST",
        body: JSON.stringify({ enabled, changed_by: "person:founder" }),
      });
      runtime.message = enabled ? "Routine enabled." : "Routine paused. No new runs will be queued.";
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  async function saveTemplate(templateType, sourceId, name) {
    try {
      await api(`${encodeURIComponent(workspaceId())}/templates`, {
        method: "POST",
        body: JSON.stringify({
          name,
          template_type: templateType,
          source_id: sourceId,
          created_by: "person:founder",
          include_sensitive_configuration: false,
        }),
      });
      runtime.message = `${name} is now a reusable template. Credentials, sessions and business memory were excluded.`;
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  async function instantiateTemplate(templateId) {
    try {
      await api(`${encodeURIComponent(workspaceId())}/templates/${encodeURIComponent(templateId)}/instantiate`, {
        method: "POST",
        body: JSON.stringify({ created_by: "person:founder" }),
      });
      runtime.message = "A safe draft was created from the template. It must be tested again before use.";
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  async function registerWorker() {
    const worker = runtime.worker;
    if (!String(worker.node_id).trim() || !String(worker.label).trim()) {
      runtime.error = "Give the user-owned worker a stable ID and a name.";
      render();
      return;
    }
    try {
      await api(`${encodeURIComponent(workspaceId())}/worker-nodes`, {
        method: "POST",
        body: JSON.stringify({
          node_id: worker.node_id,
          label: worker.label,
          registered_by: "person:founder",
          capabilities: String(worker.capabilities).split(",").map((item) => item.trim()).filter(Boolean),
          availability: "when_online",
        }),
      });
      runtime.message = "User-owned worker registered. Its heartbeat cannot add capabilities or bypass approval.";
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  async function controlMission(missionId, command) {
    let instruction = "";
    if (command === "redirect") {
      instruction = window.prompt("What should the COO change about the remaining work?", "") || "";
      if (!instruction.trim()) return;
    }
    try {
      await api(
        `${encodeURIComponent(workspaceId())}/missions/${encodeURIComponent(missionId)}/control`,
        {
          method: "POST",
          body: JSON.stringify({ command, actor_id: "person:founder", instruction }),
        },
      );
      runtime.message = `Mission ${command} recorded. Completed actions remain in its history.`;
      runtime.workspace = null;
      await loadWorkspace(true);
    } catch (error) {
      runtime.error = String(error?.message || error);
      render();
    }
  }

  function missionRows() {
    const missions = [...(runtime.workspace?.missions || [])].reverse().slice(0, 5);
    if (!missions.length) return `<p class="pilot-team-empty">No COO missions yet.</p>`;
    return missions.map((mission) => {
      const paused = mission.state === "paused";
      const terminal = ["completed", "failed", "stopped"].includes(mission.state);
      return `
        <article class="pilot-mission-row">
          <div>
            <strong>${escapeHtml(mission.outcome)}</strong>
            <small>${escapeHtml(mission.state)} · ${mission.assignments?.length || 0} department assignments · ${escapeHtml(mission.planner_status || "manual mission")} · revision ${mission.revision || 1}</small>
            ${mission.proposal?.answer ? `<p>${escapeHtml(mission.proposal.answer)}</p>` : ""}
            ${mission.planner_reason ? `<p class="pilot-mission-reason">Waiting: ${escapeHtml(mission.planner_reason)}</p>` : ""}
            ${(mission.assignments || []).length ? `<div class="pilot-assignment-chips">${mission.assignments.map((assignment) => `
              <span>${escapeHtml(assignment.department_id)} · ${escapeHtml(assignment.capability || "task")} · ${escapeHtml(assignment.state)}</span>
            `).join("")}</div>` : ""}
          </div>
          <footer>
            ${terminal ? "" : `
              <button type="button" data-pilot-mission-command="${paused ? "resume" : "pause"}" data-mission-id="${escapeHtml(mission.mission_id)}">${paused ? "Resume" : "Pause"}</button>
              <button type="button" data-pilot-mission-command="redirect" data-mission-id="${escapeHtml(mission.mission_id)}">Redirect</button>
              <button type="button" data-pilot-mission-command="stop" data-mission-id="${escapeHtml(mission.mission_id)}">Stop</button>
            `}
          </footer>
        </article>
      `;
    }).join("");
  }

  function skillRows() {
    const skills = [...(runtime.workspace?.skills || [])]
      .filter((skill) => skill.status !== "archived")
      .reverse();
    if (!skills.length) return `<p class="pilot-team-empty">Demonstrated skills will appear here.</p>`;
    return skills.map((skill) => {
      const editing = runtime.editingSkill?.skill_id === skill.skill_id;
      return `
      <article class="pilot-mission-row">
        <div class="pilot-skill-details">
          ${editing ? `
            <label>Process title<input data-pilot-edit-skill-name value="${escapeHtml(runtime.editingSkill.name)}" /></label>
            <label>Description<textarea data-pilot-edit-skill-outcome>${escapeHtml(runtime.editingSkill.outcome)}</textarea></label>
          ` : `
            <strong>${escapeHtml(skill.name)}</strong>
            <p class="pilot-skill-description">${escapeHtml(skill.outcome || "No description yet.")}</p>
            <small>${escapeHtml(skill.department_id)} · ${skill.steps?.length || 0} steps · ${escapeHtml(skill.status)} · ${escapeHtml(skill.validation_state)}</small>
          `}
        </div>
        <footer>
          ${editing ? `
            <button type="button" data-pilot-save-skill-edit="${escapeHtml(skill.skill_id)}">Save changes</button>
            <button type="button" data-pilot-cancel-skill-edit>Cancel</button>
          ` : `
            <button type="button" data-pilot-edit-skill="${escapeHtml(skill.skill_id)}">Edit details</button>
          `}
          <button type="button" data-pilot-validate-skill="${escapeHtml(skill.skill_id)}">
            ${skill.status === "published" ? "Revalidate targets" : "Validate and publish"}
          </button>
          <button type="button" data-pilot-save-template="${escapeHtml(skill.skill_id)}" data-template-type="skill" data-template-name="${escapeHtml(skill.name)}">Save template</button>
          ${skill.status === "published" && skill.validation_state === "passed" ? `
            <button type="button" data-pilot-add-skill-node="${escapeHtml(skill.skill_id)}">Add to workflow</button>
          ` : ""}
          <button class="pilot-skill-delete" type="button" data-pilot-delete-skill="${escapeHtml(skill.skill_id)}">Delete</button>
        </footer>
      </article>
    `;
    }).join("");
  }

  function routineRows() {
    const routines = [...(runtime.workspace?.routines || [])].reverse().slice(0, 8);
    if (!routines.length) return `<p class="pilot-team-empty">No routines yet. Create one from a department capability or a published demonstrated skill.</p>`;
    return routines.map((routine) => `
      <article class="pilot-mission-row">
        <div>
          <strong>${escapeHtml(routine.title)}</strong>
          <small>${routine.workflow_target ? `${escapeHtml(routine.workflow_target.workflow_name)} · ${routine.workflow_target.node_count} node${routine.workflow_target.node_count === 1 ? "" : "s"} · ` : `${escapeHtml(routine.department_id)} · `}${escapeHtml(routine.trigger?.kind)} · ${routine.enabled ? "on" : "off"} · test ${escapeHtml(routine.test_state)}</small>
        </div>
        <footer>
          ${routine.test_state === "passed" ? "" : `<button type="button" data-pilot-test-routine="${escapeHtml(routine.routine_id)}">Review safe test</button>`}
          <button type="button" data-pilot-toggle-routine="${escapeHtml(routine.routine_id)}" data-enabled="${routine.enabled ? "false" : "true"}">
            ${routine.enabled ? "Pause" : "Enable"}
          </button>
          <button type="button" data-pilot-save-template="${escapeHtml(routine.routine_id)}" data-template-type="routine" data-template-name="${escapeHtml(routine.title)}">Save template</button>
        </footer>
      </article>
    `).join("");
  }

  function completionRows() {
    const packs = [...(runtime.workspace?.completion_packs || [])].reverse().slice(0, 5);
    if (!packs.length) return `<p class="pilot-team-empty">Completion packs will separate verified facts, assumptions, completed actions, waiting approvals and unresolved questions.</p>`;
    return packs.map((pack) => `
      <article class="pilot-mission-row">
        <div>
          <strong>Mission completion pack</strong>
          <small>${pack.facts?.length || 0} facts · ${pack.actions_completed?.length || 0} actions · ${pack.approvals_waiting?.length || 0} approvals waiting · ${pack.unresolved_questions?.length || 0} questions</small>
        </div>
        <footer><span class="pilot-team-receipt">Receipt ${escapeHtml(String(pack.pack_hash || "").slice(0, 16))}</span></footer>
      </article>
    `).join("");
  }

  function templateRows() {
    const templates = [...(runtime.workspace?.templates || [])].reverse().slice(0, 6);
    if (!templates.length) return `<p class="pilot-team-empty">Reusable Pilot, routine and skill templates will appear here without credentials, sessions or business memory.</p>`;
    return templates.map((template) => `
      <article class="pilot-mission-row">
        <div><strong>${escapeHtml(template.name)}</strong><small>${escapeHtml(template.template_type)} · safe blueprint · ${escapeHtml(template.source_status)}</small></div>
        <footer><button type="button" data-pilot-use-template="${escapeHtml(template.template_id)}" ${template.source_status !== "resolved" ? "disabled" : ""}>Create fresh draft</button></footer>
      </article>
    `).join("");
  }

  function capsuleRows() {
    const capsules = runtime.workspace?.capsules || [];
    if (!capsules.length) {
      return `<div class="pilot-team-empty">No Department Pilot workspaces have been created yet.</div>`;
    }
    return capsules.map((capsule) => {
      const human = capsule.control_state === "human";
      const departmentId = capsule.department_id;
      const teaching = runtime.teachingByDepartment[departmentId] || { name: "", outcome: "" };
      const isRecording = runtime.recording && runtime.activeTeachingDepartment === departmentId;
      const anotherRecording = runtime.recording && !isRecording;
      const active = (capsule.active_mission_id || capsule.active_task_id) && capsule.current_objective;
      return `
        <article class="pilot-capsule-card">
          <header>
            <span>${escapeHtml(capsule.department_id.replaceAll("_", " "))}</span>
            <b class="${human ? "human" : "pilot"}">${human ? "Human control" : "Pilot control"}</b>
          </header>
          <p>Isolated browser · scoped files · department grants</p>
          <small>${escapeHtml(capsule.browser_profile_id || "")}</small>
          <div class="pilot-capsule-activity ${active ? "active" : "idle"}">
            <b>${active ? escapeHtml(capsule.activity_state || "queued") : "Idle"}</b>
            <span>${active ? escapeHtml(capsule.current_objective) : "No mission assigned"}</span>
          </div>
          <footer>
            <button type="button" data-pilot-open-computer="${escapeHtml(departmentId)}">Watch computer</button>
            <button type="button" data-pilot-control="${escapeHtml(departmentId)}" data-human="${human ? "false" : "true"}">
              ${human ? "Return to Pilot" : "Take control"}
            </button>
          </footer>
          <section class="pilot-capsule-teaching" data-aion-pilot-teaching="${escapeHtml(departmentId)}">
            <span class="eyebrow">Teach by demonstration · v2</span>
            <strong>Show this Pilot one short process</strong>
            <input data-pilot-teach-name data-department="${escapeHtml(departmentId)}" value="${escapeHtml(teaching.name)}" placeholder="Skill name" />
            <input data-pilot-teach-outcome data-department="${escapeHtml(departmentId)}" value="${escapeHtml(teaching.outcome)}" placeholder="Expected result" />
            <button type="button" class="primary-btn" data-pilot-teach-toggle="${escapeHtml(departmentId)}" ${anotherRecording ? "disabled" : ""}>
              ${isRecording ? `Stop and create draft (${runtime.events.length} events)` : "Start teaching"}
            </button>
          </section>
        </article>
      `;
    }).join("");
  }

  function trainPanel() {
    const data = runtime.workspace || {};
    const audit = data.audit || {};
    const workflows = savedWorkflows();
    return `
      <section class="pilot-team-panel pilot-team-overlay" data-aion-pilot-operating-team>
        <div class="pilot-team-heading">
          <div>
            <span class="eyebrow">Pilot Operating Team · native AION runtime</span>
            <h2>Teach, watch and direct your operating team</h2>
            <p>The selected Vault model plans the work. AION owns authority, computer access, approvals, memory and receipts.</p>
          </div>
          <div class="pilot-team-actions">
            <button type="button" data-pilot-team-refresh>Refresh</button>
            <button type="button" class="primary-btn" data-pilot-team-bootstrap>
              ${(data.capsules || []).length ? "Repair workspaces" : "Set up operating team"}
            </button>
          </div>
        </div>
        ${runtime.error ? `<div class="pilot-team-message error">${escapeHtml(runtime.error)}</div>` : ""}
        ${runtime.message ? `<div class="pilot-team-message">${escapeHtml(runtime.message)}</div>` : ""}
        <div class="pilot-team-metrics">
          <article><strong>${(data.capsules || []).length}</strong><span>Department computers</span></article>
          <article><strong>${(data.skills || []).length}</strong><span>Demonstrated skills</span></article>
          <article><strong>${(data.routines || []).length}</strong><span>Routines</span></article>
          <article><strong>${(data.missions || []).length}</strong><span>COO missions</span></article>
          <article><strong>${audit.ok === false ? "Check" : audit.count || 0}</strong><span>Audit events</span></article>
        </div>
        <div class="pilot-capsule-grid">${capsuleRows()}</div>
        <div class="pilot-team-workbench pilot-mission-workbench">
          <section>
            <span class="eyebrow">COO Mission Room</span>
            <h3>Delegate an outcome, not a list of clicks</h3>
            <textarea data-pilot-mission-outcome placeholder="Example: improve cash collection this week without contacting customers who have unresolved complaints">${escapeHtml(runtime.missionOutcome)}</textarea>
            <p>The selected Vault model plans the mission, the capability router assigns registered Department Pilot work, and AION's gateway blocks external changes until exact approval.</p>
            <button type="button" data-pilot-create-mission ${runtime.loading ? "disabled" : ""}>${runtime.loading ? "Planning mission…" : "Plan and launch mission"}</button>
          </section>
        </div>
        <section class="pilot-routine-builder" data-aion-pilot-routines>
          <span class="eyebrow">Scheduled and event-driven routines</span>
          <h3>Put any saved workflow on autopilot</h3>
          <div class="pilot-workflow-routine-fields">
            <input data-pilot-workflow-routine-title value="${escapeHtml(runtime.workflowRoutine.title)}" placeholder="Automation name" />
            <select data-pilot-workflow-routine-id>
              <option value="">Select a saved workflow</option>
              ${workflows.map((item) => `<option value="${escapeHtml(item.workflow_id)}" ${runtime.workflowRoutine.workflow_id === item.workflow_id ? "selected" : ""}>${escapeHtml(item.name)} · ${item.node_count} node${item.node_count === 1 ? "" : "s"}</option>`).join("")}
            </select>
            <select data-pilot-workflow-routine-trigger>
              <option value="schedule" ${runtime.workflowRoutine.trigger_kind === "schedule" ? "selected" : ""}>Run on a schedule</option>
              <option value="event" ${runtime.workflowRoutine.trigger_kind === "event" ? "selected" : ""}>Run when an event happens</option>
            </select>
            ${runtime.workflowRoutine.trigger_kind === "schedule" ? `
              <div class="pilot-workflow-interval">
                <input type="number" min="1" data-pilot-workflow-interval-value value="${escapeHtml(runtime.workflowRoutine.interval_value)}" />
                <select data-pilot-workflow-interval-unit>
                  ${["minute", "hour", "day", "week"].map((unit) => `<option value="${unit}" ${runtime.workflowRoutine.interval_unit === unit ? "selected" : ""}>${unit}${Number(runtime.workflowRoutine.interval_value) === 1 ? "" : "s"}</option>`).join("")}
                </select>
              </div>
            ` : `<input data-pilot-workflow-event-type value="${escapeHtml(runtime.workflowRoutine.event_type)}" placeholder="Business event, e.g. sales.lead_received" />`}
            <button type="button" data-pilot-create-workflow-routine>Create off draft</button>
          </div>
          <p>Select a complete saved workflow or a workflow containing one node. Scheduled runs are checked every minute; event runs start when AION receives the matching business event. External changes still stop for exact approval.</p>
          ${workflows.length ? "" : `<p class="pilot-team-message">Save a workflow in the Workflow Canvas or File Cabinet first.</p>`}
        </section>
        <section class="pilot-routine-builder" data-aion-pilot-department-routines>
          <span class="eyebrow">Routines and business events</span>
          <h3>Turn a Department Pilot capability into recurring work</h3>
          <div class="pilot-routine-fields">
            <input data-pilot-routine-title value="${escapeHtml(runtime.routine.title)}" placeholder="Routine name" />
            <select data-pilot-routine-department>
              ${["operations", "finance", "people", "sales", "marketing", "support", "products_services"].map(
                (item) => `<option value="${item}" ${runtime.routine.department_id === item ? "selected" : ""}>${escapeHtml(item.replaceAll("_", " "))}</option>`,
              ).join("")}
            </select>
            <select data-pilot-routine-trigger>
              <option value="schedule" ${runtime.routine.trigger_kind === "schedule" ? "selected" : ""}>Run on a schedule</option>
              <option value="event" ${runtime.routine.trigger_kind === "event" ? "selected" : ""}>Run when an event happens</option>
            </select>
            ${runtime.routine.trigger_kind === "schedule"
              ? `<div class="pilot-routine-interval"><span>Every</span><input type="number" min="1" data-pilot-routine-interval-value value="${escapeHtml(runtime.routine.interval_value)}" aria-label="Run every" /><select data-pilot-routine-interval-unit aria-label="Schedule unit">${["minute", "hour", "day", "week"].map((unit) => `<option value="${unit}" ${runtime.routine.interval_unit === unit ? "selected" : ""}>${unit}${Number(runtime.routine.interval_value) === 1 ? "" : "s"}</option>`).join("")}</select></div>`
              : `<input data-pilot-routine-event value="${escapeHtml(runtime.routine.event_type)}" placeholder="Event, e.g. support.complaint_opened" />`}
            <select data-pilot-routine-skill>
              <option value="">Use registered department capabilities</option>
              ${(data.skills || []).filter((skill) => skill.status === "published").map(
                (skill) => `<option value="${escapeHtml(skill.skill_id)}" ${runtime.routine.skill_id === skill.skill_id ? "selected" : ""}>${escapeHtml(skill.name)}</option>`,
              ).join("")}
            </select>
            <select data-pilot-routine-output aria-label="What should Pilot produce?">
              ${ROUTINE_OUTPUTS.map(([value, label]) => `<option value="${value}" ${runtime.routine.output_type === value ? "selected" : ""}>${escapeHtml(label)}</option>`).join("")}
            </select>
            ${runtime.routine.output_type === "capability_default" ? "" : `
              <input class="pilot-routine-output-instructions" data-pilot-routine-output-instructions value="${escapeHtml(runtime.routine.output_instructions)}" placeholder="What must the result contain or do?" />
            `}
            ${["spreadsheet_xlsx", "csv", "pdf"].includes(runtime.routine.output_type) ? `
              <select data-pilot-routine-output-destination aria-label="Save result to">
                <option value="file_cabinet" ${runtime.routine.output_destination === "file_cabinet" ? "selected" : ""}>Save to File Cabinet</option>
                <option value="department_workspace" ${runtime.routine.output_destination === "department_workspace" ? "selected" : ""}>Save to Department workspace</option>
                <option value="downloads" ${runtime.routine.output_destination === "downloads" ? "selected" : ""}>Save to Downloads</option>
              </select>
            ` : ""}
            <button type="button" data-pilot-create-routine>Create disabled draft</button>
          </div>
          <div class="pilot-routine-access-summary">
            <strong>Data access</strong>
            <span>${escapeHtml(routineAccessSummary())}</span>
            <small>Missing credentials or grants pause the routine and ask you to connect or approve access. They are never accepted as free text.</small>
          </div>
          <p>A completion receipt is always created automatically. Every routine starts off, stops on stale or unsafe data and queues external changes for exact approval.</p>
        </section>
        <section class="pilot-routine-builder" data-aion-pilot-workers>
          <span class="eyebrow">Optional user-owned worker</span>
          <h3>Register a machine that can stay available when AION is not in front of you</h3>
          <div class="pilot-routine-fields">
            <input data-pilot-worker-id value="${escapeHtml(runtime.worker.node_id)}" placeholder="Stable node ID, e.g. office-mac" />
            <input data-pilot-worker-label value="${escapeHtml(runtime.worker.label)}" placeholder="Friendly name" />
            <input data-pilot-worker-capabilities value="${escapeHtml(runtime.worker.capabilities)}" placeholder="Approved capabilities, comma separated" />
            <button type="button" data-pilot-register-worker>Register worker</button>
          </div>
          <p>${(data.worker_nodes || []).length} registered · user-owned · registered destinations only · exact approvals still apply.</p>
        </section>
        <div class="pilot-mission-list">
          <span class="eyebrow">Taught process library</span>
          ${skillRows()}
        </div>
        <div class="pilot-mission-list">
          <span class="eyebrow">Governed routines</span>
          ${routineRows()}
        </div>
        <div class="pilot-mission-list">
          <span class="eyebrow">Active and recent missions</span>
          ${missionRows()}
        </div>
        <div class="pilot-mission-list">
          <span class="eyebrow">Evidence and completion packs</span>
          ${completionRows()}
        </div>
        <div class="pilot-mission-list">
          <span class="eyebrow">Reusable team templates</span>
          ${templateRows()}
        </div>
      </section>
    `;
  }

  function replacePanelWithoutLosingPlace(existing, next) {
    const active = document.activeElement;
    const editing = active && existing.contains(active) && active.matches("input, textarea, select");
    if (editing) return;
    const scrollTop = existing.scrollTop;
    const scrollLeft = existing.scrollLeft;
    existing.replaceWith(next);
    next.scrollTop = scrollTop;
    next.scrollLeft = scrollLeft;
  }

  function updateVisibleIntervalUnitLabels(input, selectSelector) {
    const container = input.closest(".pilot-routine-interval, .pilot-workflow-interval");
    const select = container?.querySelector(selectSelector);
    if (!select) return;
    const singular = Number(input.value) === 1;
    Array.from(select.options).forEach((option) => {
      option.textContent = `${option.value}${singular ? "" : "s"}`;
    });
  }

  function render() {
    const train = document.querySelector(".operations-agents-surface .dashboard-shell");
    const existing = document.querySelector("body > [data-aion-pilot-operating-team]");
    const organisationCanvasOpen =
      (typeof window.__aionIsOrganisationWorkflowTabActive === "function"
        ? window.__aionIsOrganisationWorkflowTabActive()
        : window.__aionFullOrganisationCanvas === true) &&
      !!document.querySelector("[data-aion-full-org-canvas]");
    if (organisationCanvasOpen) {
      runtime.trainSurfacePresent = false;
      existing?.remove();
    } else if (train) {
      // The canvas is the primary Train Agent surface. Pilot Team is opened
      // deliberately from its toggle and must not cover a selected worksheet.
      if (!runtime.trainSurfacePresent) runtime.teamVisible = false;
      runtime.trainSurfacePresent = true;
      const toggleHost = train.querySelector("[data-pilot-team-header-toggle-host='true']");
      if (toggleHost) {
        let toggle = toggleHost.querySelector("[data-pilot-team-header-toggle='true']");
        if (!toggle) {
          toggle = document.createElement("button");
          toggle.type = "button";
          toggle.setAttribute("data-pilot-team-header-toggle", "true");
          toggleHost.append(toggle);
        }
        toggle.textContent = runtime.teamVisible ? "Workflow canvas" : "Pilot Team";
        toggle.setAttribute(
          "aria-label",
          runtime.teamVisible ? "Show workflow canvas" : "Show Pilot Team",
        );
      }
      if (runtime.teamVisible) {
        const wrapper = document.createElement("div");
        wrapper.innerHTML = trainPanel();
        const next = wrapper.firstElementChild;
        if (!existing) document.body.append(next);
        else if (existing.outerHTML !== next.outerHTML) replacePanelWithoutLosingPlace(existing, next);
      } else {
        existing?.remove();
      }
    } else {
      runtime.trainSurfacePresent = false;
      existing?.remove();
    }

    // Computer controls belong in the Workflow Canvas/Pilot Team workspace.
    // Remove any legacy copies from department landing pages, including copies
    // left behind by a previous render of a nested department surface.
    document
      .querySelectorAll("[data-aion-shared-department-pilot] [data-pilot-department-computer-panel]")
      .forEach((panel) => panel.remove());
  }

  document.addEventListener("input", (event) => {
    if (event.target.matches("input")) event.target.setAttribute("value", event.target.value);
    if (event.target.matches("[data-pilot-teach-name], [data-pilot-teach-outcome]")) {
      const departmentId = event.target.getAttribute("data-department") || "operations";
      const draft = runtime.teachingByDepartment[departmentId] || { name: "", outcome: "" };
      if (event.target.matches("[data-pilot-teach-name]")) draft.name = event.target.value;
      if (event.target.matches("[data-pilot-teach-outcome]")) draft.outcome = event.target.value;
      runtime.teachingByDepartment[departmentId] = draft;
    }
    if (event.target.matches("[data-pilot-mission-outcome]")) runtime.missionOutcome = event.target.value;
    if (event.target.matches("[data-pilot-routine-title]")) runtime.routine.title = event.target.value;
    if (event.target.matches("[data-pilot-routine-interval-value]")) {
      runtime.routine.interval_value = event.target.value;
      updateVisibleIntervalUnitLabels(event.target, "[data-pilot-routine-interval-unit]");
    }
    if (event.target.matches("[data-pilot-routine-event]")) runtime.routine.event_type = event.target.value;
    if (event.target.matches("[data-pilot-routine-output-instructions]")) runtime.routine.output_instructions = event.target.value;
    if (event.target.matches("[data-pilot-worker-id]")) runtime.worker.node_id = event.target.value;
    if (event.target.matches("[data-pilot-worker-label]")) runtime.worker.label = event.target.value;
    if (event.target.matches("[data-pilot-worker-capabilities]")) runtime.worker.capabilities = event.target.value;
    if (event.target.matches("[data-pilot-edit-skill-name]") && runtime.editingSkill) runtime.editingSkill.name = event.target.value;
    if (event.target.matches("[data-pilot-edit-skill-outcome]") && runtime.editingSkill) runtime.editingSkill.outcome = event.target.value;
    if (event.target.matches("[data-pilot-workflow-routine-title]")) runtime.workflowRoutine.title = event.target.value;
    if (event.target.matches("[data-pilot-workflow-interval-value]")) {
      runtime.workflowRoutine.interval_value = event.target.value;
      updateVisibleIntervalUnitLabels(event.target, "[data-pilot-workflow-interval-unit]");
    }
    if (event.target.matches("[data-pilot-workflow-event-type]")) runtime.workflowRoutine.event_type = event.target.value;
  });

  // A worksheet tab is an explicit request to work on that canvas.  Keep the
  // Pilot Team available through its header toggle, but never let its overlay
  // conceal a newly selected or newly created worksheet.
  window.addEventListener("click", (event) => {
    const workflowTab = event.target?.closest?.(
      "[data-aion-workflow-main-tab-select], [data-aion-workflow-new-blank='true']",
    );
    if (!workflowTab) return;
    runtime.teamVisible = false;
    window.setTimeout(render, 0);
  }, true);
  document.addEventListener("change", (event) => {
    if (event.target.matches("[data-pilot-routine-department]")) {
      runtime.routine.department_id = event.target.value;
      runtime.routine.skill_id = "";
      render();
    }
    if (event.target.matches("[data-pilot-routine-trigger]")) {
      runtime.routine.trigger_kind = event.target.value;
      render();
    }
    if (event.target.matches("[data-pilot-routine-skill]")) {
      runtime.routine.skill_id = event.target.value;
      const skill = selectedRoutineSkill();
      if (skill?.department_id) runtime.routine.department_id = skill.department_id;
      render();
    }
    if (event.target.matches("[data-pilot-routine-interval-unit]")) runtime.routine.interval_unit = event.target.value;
    if (event.target.matches("[data-pilot-routine-output]")) {
      runtime.routine.output_type = event.target.value;
      runtime.routine.output_instructions = "";
      render();
    }
    if (event.target.matches("[data-pilot-routine-output-destination]")) runtime.routine.output_destination = event.target.value;
    if (event.target.matches("[data-pilot-workflow-routine-id]")) runtime.workflowRoutine.workflow_id = event.target.value;
    if (event.target.matches("[data-pilot-workflow-routine-trigger]")) {
      runtime.workflowRoutine.trigger_kind = event.target.value;
      render();
    }
    if (event.target.matches("[data-pilot-workflow-interval-unit]")) runtime.workflowRoutine.interval_unit = event.target.value;
  });

  document.addEventListener("click", async (event) => {
    const button = event.target.closest(
      "[data-pilot-team-bootstrap], [data-pilot-team-refresh], [data-pilot-open-computer], " +
      "[data-pilot-team-header-toggle], " +
      "[data-pilot-control], [data-pilot-teach-toggle], [data-pilot-create-mission], " +
      "[data-pilot-mission-command], [data-pilot-validate-skill], [data-pilot-create-routine], " +
      "[data-pilot-create-workflow-routine], " +
      "[data-pilot-add-skill-node], [data-pilot-edit-skill], [data-pilot-save-skill-edit], " +
      "[data-pilot-cancel-skill-edit], [data-pilot-delete-skill], " +
      "[data-pilot-test-routine], [data-pilot-toggle-routine], [data-pilot-save-template], " +
      "[data-pilot-use-template], [data-pilot-register-worker]",
    );
    if (!button) return;
    if (button.hasAttribute("data-pilot-team-header-toggle")) {
      runtime.teamVisible = !runtime.teamVisible;
      render();
      return;
    }
    if (button.hasAttribute("data-pilot-team-bootstrap")) return bootstrap();
    if (button.hasAttribute("data-pilot-team-refresh")) {
      runtime.workspace = null;
      return loadWorkspace(true);
    }
    if (button.hasAttribute("data-pilot-open-computer")) {
      return openComputer(button.getAttribute("data-pilot-open-computer"));
    }
    if (button.hasAttribute("data-pilot-control")) {
      return transferControl(
        button.getAttribute("data-pilot-control"),
        button.getAttribute("data-human") === "true",
      );
    }
    if (button.hasAttribute("data-pilot-teach-toggle")) {
      const departmentId = button.getAttribute("data-pilot-teach-toggle") || "operations";
      return runtime.recording ? stopTeaching(departmentId) : startTeaching(departmentId);
    }
    if (button.hasAttribute("data-pilot-create-mission")) return createMission();
    if (button.hasAttribute("data-pilot-create-routine")) return createRoutine();
    if (button.hasAttribute("data-pilot-create-workflow-routine")) return createWorkflowRoutine();
    if (button.hasAttribute("data-pilot-register-worker")) return registerWorker();
    if (button.hasAttribute("data-pilot-save-template")) {
      return saveTemplate(
        button.getAttribute("data-template-type"),
        button.getAttribute("data-pilot-save-template"),
        button.getAttribute("data-template-name"),
      );
    }
    if (button.hasAttribute("data-pilot-use-template")) {
      return instantiateTemplate(button.getAttribute("data-pilot-use-template"));
    }
    if (button.hasAttribute("data-pilot-test-routine")) {
      return reviewRoutine(button.getAttribute("data-pilot-test-routine"));
    }
    if (button.hasAttribute("data-pilot-toggle-routine")) {
      return toggleRoutine(
        button.getAttribute("data-pilot-toggle-routine"),
        button.getAttribute("data-enabled") === "true",
      );
    }
    if (button.hasAttribute("data-pilot-validate-skill")) {
      return validateSkill(button.getAttribute("data-pilot-validate-skill"));
    }
    if (button.hasAttribute("data-pilot-edit-skill")) {
      return editSkill(button.getAttribute("data-pilot-edit-skill"));
    }
    if (button.hasAttribute("data-pilot-save-skill-edit")) {
      return saveSkillEdits(button.getAttribute("data-pilot-save-skill-edit"));
    }
    if (button.hasAttribute("data-pilot-cancel-skill-edit")) {
      runtime.editingSkill = null;
      runtime.error = "";
      render();
      return;
    }
    if (button.hasAttribute("data-pilot-delete-skill")) {
      return deleteSkill(button.getAttribute("data-pilot-delete-skill"));
    }
    if (button.hasAttribute("data-pilot-add-skill-node")) {
      return addSkillToWorkflow(button.getAttribute("data-pilot-add-skill-node"));
    }
    if (button.hasAttribute("data-pilot-mission-command")) {
      return controlMission(
        button.getAttribute("data-mission-id"),
        button.getAttribute("data-pilot-mission-command"),
      );
    }
  });

  if (window.aionDesktop?.onBrowserRecorderEvent) {
    window.aionDesktop.onBrowserRecorderEvent((payload) => {
      if (!runtime.recording || !payload) return;
      runtime.events.push(payload);
      render();
    });
  }

  let renderQueued = false;
  const observer = new MutationObserver(() => {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(() => {
      renderQueued = false;
      render();
      if (!runtime.workspace && !runtime.loading) loadWorkspace();
    });
  });
  observer.observe(document.body, { childList: true, subtree: true });
  loadWorkspace();
})();
