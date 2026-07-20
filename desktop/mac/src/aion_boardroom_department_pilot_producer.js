(function installAionBoardroomDepartmentPilotProducer(global) {
  'use strict';

  if (global.__aionBoardroomDepartmentPilotProducerInstalled === true) return;
  global.__aionBoardroomDepartmentPilotProducerInstalled = true;

  const LIVE_TASK_BUILD_SCHEMA = 'aion.department_task_build.live.v1';
  const ROUTABLE_DEPARTMENT = 'finance';
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

  function financeTasks(result) {
    return safeArray(result.tasks).filter((task) => {
      return String(task?.department || '').toLowerCase() === ROUTABLE_DEPARTMENT
        && task?.approval_required === true
        && task?.live_external_side_effects_performed !== true;
    });
  }

  function buildFinanceApproval(result) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('canonical_business_identity_required');

    const tasks = financeTasks(result);
    if (!tasks.length) throw new Error('no_finance_actions_in_current_boardroom_plan');

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
      return {
        schema_version: 'aion.department_pilot.assignment_action.v1',
        action_id: `finance-action-${resultToken}-${taskToken}`,
        title: String(task.task_title || task.title || `Finance action ${index + 1}`),
        objective: String(task.objective || task.task_title || 'Prepare Boardroom-requested Finance analysis.'),
        department_id: ROUTABLE_DEPARTMENT,
        capability: String(task.capability || 'finance.boardroom_analysis'),
        priority: String(task.priority || 'high'),
        acceptance_criteria: [
          String(task.output_required || '').trim(),
          String(task.success_metric || '').trim(),
          'Every material figure must retain provenance and verification state.',
        ].filter(Boolean),
        dependency_action_ids: [],
        requested_artifact_types: ['finance_boardroom_report'],
        due_at: null,
      };
    });

    const ignoredDepartments = Array.from(new Set(
      safeArray(result.tasks)
        .map((task) => String(task?.department || '').toLowerCase())
        .filter((department) => department && department !== ROUTABLE_DEPARTMENT)
    ));

    return {
      workspace_id: businessId,
      business_id: businessId,
      boardroom_session_id: sessionId,
      boardroom_decision_id: `boardroom-decision-${resultToken}`,
      package_id: `boardroom-finance-${resultToken}`,
      title: 'Finance actions approved by the Boardroom',
      objective: `Complete ${actions.length} founder-approved Finance action${actions.length === 1 ? '' : 's'} from the live Boardroom plan.`,
      department_id: ROUTABLE_DEPARTMENT,
      actions,
      context_refs: [],
      constraints: [
        String(result.delegation_boundary || '').trim(),
        ...tasks.flatMap((task) => safeArray(task.blockers).map(String)),
        'Read-only Finance work only; no accounting-system writes or external side effects.',
      ].filter(Boolean),
      approval_id: `founder-approval-${resultToken}`,
      approved_by: resolveApprover(),
      approved_at: new Date().toISOString(),
      approval_notes: ignoredDepartments.length
        ? `Finance routed now. Design-gated departments not routed: ${ignoredDepartments.join(', ')}.`
        : 'Founder approved delegation from the live Boardroom task build.',
    };
  }

  function updateBoardroomMessage(message, tone) {
    global.safeAionDesktopPatch?.({ message, messageTone: tone });
    global.requestRender?.();
  }

  async function approveAndRouteCurrentFinancePlan() {
    if (routingPromise) return routingPromise;
    routingPromise = (async () => {
      const taskBuild = assertLiveFounderReviewedTaskBuild(
        global.__aionBoardroomDepartmentTasks,
      );
      const request = buildFinanceApproval(taskBuild);
      updateBoardroomMessage('Approving and routing Finance work to the Finance Pilot…', 'neutral');
      const result = await global.AionDepartmentPilotBackend.approveBoardroomAction(request);
      global.__aionCanonicalBoardroomDelegation = {
        schema_version: 'aion.canonical_boardroom_delegation_result.v1',
        status: 'finance_approved_and_routed',
        routed_at: new Date().toISOString(),
        result,
      };
      const designGated = safeArray(taskBuild.tasks).filter(
        (task) => String(task?.department || '').toLowerCase() !== ROUTABLE_DEPARTMENT,
      ).length;
      updateBoardroomMessage(
        `Finance approved and routed: ${result.task_count || 0} task(s) now visible in Finance and Central Pilot.${designGated ? ` ${designGated} non-Finance task(s) remain design-gated.` : ''}`,
        'success',
      );
      global.dispatchEvent?.(new CustomEvent('aion:boardroom-finance-actions-routed', {
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

  global.AionBoardroomDepartmentPilotProducer = Object.freeze({
    buildFinanceApproval,
    approveAndRouteCurrentFinancePlan,
  });

  global.document?.addEventListener?.('click', (event) => {
    const button = event.target?.closest?.('[data-aion-council-session-delegate-agents="true"]');
    if (!button) return;
    button.disabled = true;
    approveAndRouteCurrentFinancePlan().catch(() => {}).finally(() => {
      if (button.isConnected) button.disabled = false;
    });
  }, true);
})(window);
