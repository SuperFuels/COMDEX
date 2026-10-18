(function installAionBoardroomDepartmentPilotProducer(global) {
  'use strict';

  if (global.__aionBoardroomDepartmentPilotProducerInstalled === true) return;
  global.__aionBoardroomDepartmentPilotProducerInstalled = true;

  const LIVE_TASK_BUILD_SCHEMA = 'aion.department_task_build.live.v1';
  const DEFAULT_ROUTABLE_DEPARTMENTS = ['marketing', 'sales', 'finance', 'operations', 'support', 'hr'];
  const DEPARTMENT_CAPABILITIES = {
    marketing: 'marketing.boardroom_projection',
    finance: 'finance.boardroom_analysis',
    sales: 'sales.boardroom_projection',
    operations: 'operations.boardroom_projection',
    support: 'support.boardroom_projection',
    hr: 'hr.boardroom_summary',
  };
  let routingPromise = null;

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function slug(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function compactId(value, fallback) {
    const token = String(value || '')
      .replace(/^sha256:/, '')
      .replace(/[^a-zA-Z0-9]+/g, '')
      .slice(0, 24);
    return token || fallback;
  }

  function resolveBusinessId() {
    return global.AionBusinessContainerClient?.resolveBusinessId?.()
      || global.getAionBoardroomBusinessContainerId?.()
      || global.__aionCanonicalBusinessId
      || '';
  }

  function resolveApprover() {
    const foundation = global.getEditableBusinessContextFoundation?.()
      || global.getApprovedSmallBusinessFoundationContext?.()
      || {};
    const name = foundation.owner
      || foundation.owner_name
      || foundation.founder_name
      || foundation.user_name
      || 'founder';
    return `founder:${slug(name) || 'founder'}`;
  }

  function assertLiveFounderReviewedTaskBuild(result) {
    if (!result || result.schema_version !== LIVE_TASK_BUILD_SCHEMA) {
      throw new Error('live_boardroom_department_task_build_required');
    }
    if (result.status !== 'tasks_ready_for_delegation_preview') {
      throw new Error('boardroom_tasks_not_ready_for_founder_approval');
    }
    if (result.live_provider_fanout !== true || result.simulated_responses === true) {
      throw new Error('canonical_routing_requires_live_non_simulated_boardroom_tasks');
    }
    if (!String(result.result_hash || '').startsWith('sha256:')) {
      throw new Error('boardroom_task_build_hash_required');
    }
    return result;
  }

  function departmentTasks(result, departmentId) {
    return safeArray(result.tasks).filter((task) => {
      return String(task?.department || '').toLowerCase() === departmentId
        && task?.approval_required === true
        && task?.live_external_side_effects_performed !== true;
    });
  }

  function buildDepartmentApproval(result, departmentId) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('canonical_business_identity_required');

    const department = String(departmentId || '').toLowerCase();
    const tasks = departmentTasks(result, department);
    if (!tasks.length) throw new Error(`no_${department}_actions_in_current_boardroom_plan`);

    const resultToken = compactId(result.result_hash, `result${Date.now()}`);
    const debate = global.__aionBoardroomDebateRound || {};
    const boardResult = global.__aionVisibleAskBoardResult || {};
    const sessionId = String(
      debate.source_session_id
      || boardResult.session_id
      || `boardroom-session-${resultToken}`
    );

    const actions = tasks.map((task, index) => {
      const taskToken = compactId(task.task_id, `${index + 1}`);
      const boardBrief = String(task.board_brief || '').trim();
      return {
        schema_version: 'aion.department_pilot.assignment_action.v1',
        action_id: `${department}-action-${resultToken}-${taskToken}`,
        title: String(task.task_title || task.title || `${department} action ${index + 1}`),
        objective: [
          String(task.objective || task.task_title || `Prepare Boardroom-requested ${department} execution output.`),
          boardBrief ? `Signed Board brief: ${boardBrief}` : '',
        ].filter(Boolean).join(' '),
        department_id: department,
        capability: DEPARTMENT_CAPABILITIES[department],
        priority: String(task.priority || 'high'),
        acceptance_criteria: [
          String(task.output_required || '').trim(),
          String(task.success_metric || '').trim(),
          'Execute the signed Board brief; do not redefine the enterprise strategy, audience, location, offer, channel or commercial guardrails.',
          'Every material figure must retain provenance and verification state.',
        ].filter(Boolean),
        dependency_action_ids: [],
        requested_artifact_types: [`${department}_boardroom_report`],
        due_at: null,
      };
    });

    return {
      workspace_id: businessId,
      business_id: businessId,
      boardroom_session_id: sessionId,
      boardroom_decision_id: `boardroom-decision-${resultToken}`,
      package_id: `boardroom-${department}-${resultToken}`,
      title: `${department} actions approved by the Boardroom`,
      objective: `Complete ${actions.length} founder-approved ${department} action${actions.length === 1 ? '' : 's'} from the live Boardroom plan.`,
      department_id: department,
      actions,
      context_refs: [],
      constraints: [
        String(result.delegation_boundary || '').trim(),
        ...tasks.flatMap((task) => safeArray(task.decision_refs).map((line) => `Board decision: ${String(line)}`)),
        ...tasks.map((task) => String(task.board_brief || '').trim() ? `Signed Board brief: ${String(task.board_brief).trim()}` : '').filter(Boolean),
        ...tasks.flatMap((task) => safeArray(task.blockers).map(String)),
        'Internal planning and evidence work only; no publishing, customer messages, spend, or other external side effects.',
      ].filter(Boolean),
      approval_id: `founder-approval-${resultToken}`,
      approved_by: resolveApprover(),
      approved_at: new Date().toISOString(),
      approval_notes: `Founder approved ${department} delegation from the live Boardroom task build.`,
    };
  }

  function buildFinanceApproval(result) {
    return buildDepartmentApproval(result, 'finance');
  }

  function updateBoardroomMessage(message, tone) {
    global.safeAionDesktopPatch?.({ message, messageTone: tone });
    global.requestRender?.();
  }

  async function approveAndRouteCurrentPlan() {
    if (routingPromise) return routingPromise;
    routingPromise = (async () => {
      const taskBuild = assertLiveFounderReviewedTaskBuild(
        global.__aionBoardroomDepartmentTasks,
      );
      const profileRegistry = await global.AionDepartmentPilotBackend.profiles();
      const enabledDepartments = safeArray(profileRegistry?.enabled_department_ids)
        .map((value) => String(value || '').toLowerCase())
        .filter((department) => DEPARTMENT_CAPABILITIES[department]);
      const routableDepartments = (enabledDepartments.length ? enabledDepartments : DEFAULT_ROUTABLE_DEPARTMENTS)
        .filter((department) => departmentTasks(taskBuild, department).length);
      const stagedDepartments = Array.from(new Set(
        safeArray(taskBuild.tasks)
          .map((task) => String(task?.department || '').toLowerCase())
          .filter((department) => department && !routableDepartments.includes(department))
      ));
      if (!routableDepartments.length) throw new Error('no_enabled_department_actions_in_current_boardroom_plan');

      updateBoardroomMessage(`Approving and routing Boardroom work to ${routableDepartments.join(', ')}…`, 'neutral');
      const routed = [];
      for (const department of routableDepartments) {
        const request = buildDepartmentApproval(taskBuild, department);
        routed.push(await global.AionDepartmentPilotBackend.approveBoardroomAction(request));
      }
      const result = {
        routed_departments: routableDepartments,
        staged_departments: stagedDepartments,
        task_count: routed.reduce((total, item) => total + Number(item?.task_count || 0), 0),
        results: routed,
      };
      global.__aionCanonicalBoardroomDelegation = {
        schema_version: 'aion.canonical_boardroom_delegation_result.v1',
        status: 'enabled_departments_approved_and_routed',
        routed_at: new Date().toISOString(),
        result,
      };
      updateBoardroomMessage(
        `${result.task_count} Boardroom task(s) routed to ${routableDepartments.join(', ')}.${stagedDepartments.length ? ` Draft packages staged for ${stagedDepartments.join(', ')} pending their governed Pilot activation.` : ''}`,
        'success',
      );
      global.dispatchEvent?.(new CustomEvent('aion:boardroom-department-actions-routed', {
        detail: result,
      }));
      return result;
    })().catch((error) => {
      const message = String(error?.message || error);
      global.__aionCanonicalBoardroomDelegation = {
        schema_version: 'aion.canonical_boardroom_delegation_result.v1',
        status: 'routing_failed',
        failed_at: new Date().toISOString(),
        error: message,
      };
      updateBoardroomMessage(`Finance delegation was not routed: ${message}`, 'error');
      throw error;
    }).finally(() => {
      routingPromise = null;
    });
    return routingPromise;
  }

  async function approveAndRouteCurrentFinancePlan() {
    return approveAndRouteCurrentPlan();
  }

  global.AionBoardroomDepartmentPilotProducer = Object.freeze({
    buildFinanceApproval,
    buildDepartmentApproval,
    approveAndRouteCurrentFinancePlan,
    approveAndRouteCurrentPlan,
  });

  global.document?.addEventListener?.('click', (event) => {
    const button = event.target?.closest?.('[data-aion-council-session-delegate-agents="true"]');
    if (!button) return;
    button.disabled = true;
    approveAndRouteCurrentPlan().catch(() => {}).finally(() => {
      if (button.isConnected) button.disabled = false;
    });
  }, true);
})(window);
