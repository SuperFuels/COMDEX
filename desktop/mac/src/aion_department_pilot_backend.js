(function installAionDepartmentPilotBackend(global) {
  'use strict';

  const API_BASE = 'http://127.0.0.1:8080';
  const API_PATH = '/api/aion/business/department-pilots';
  const PACKAGE_SCHEMA = 'aion.department_pilot.boardroom_assignment_package.v1';
  let queueRefreshTimer = null;
  let profilesCache = null;

  async function request(path, options = {}) {
    const response = await global.fetch(`${API_BASE}${API_PATH}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    if (!response.ok) {
      throw new Error(`Department Pilot request failed ${response.status}: ${await response.text()}`);
    }
    return response.json();
  }

  function assertCanonicalPackage(packageRecord) {
    if (!packageRecord || packageRecord.schema_version !== PACKAGE_SCHEMA) {
      throw new Error('canonical_boardroom_assignment_package_required');
    }
    if (!packageRecord.workspace_id || !packageRecord.business_id) {
      throw new Error('canonical_business_identity_required');
    }
    if (packageRecord.preview_only === true) {
      throw new Error('preview_boardroom_package_cannot_be_routed');
    }
    return packageRecord;
  }

  async function approveAndRoute(packageRecord, approval = {}) {
    const packageValue = assertCanonicalPackage(packageRecord);
    if (!['draft', 'awaiting_approval'].includes(packageValue.status)) {
      throw new Error('draft_boardroom_package_required_for_approval');
    }
    if (!approval.approval_id || !approval.approved_by) {
      throw new Error('boardroom_approval_identity_required');
    }
    const result = await request('/approve-and-route', {
      method: 'POST',
      body: JSON.stringify({
        package: packageValue,
        approval_id: approval.approval_id,
        approved_by: approval.approved_by,
        approved_at: approval.approved_at || new Date().toISOString(),
        approval_notes: approval.notes || null,
        routed_by: 'central_pilot',
      }),
    });
    notifyRouted(result);
    return result;
  }

  async function routeApprovedPackage(packageRecord) {
    const packageValue = assertCanonicalPackage(packageRecord);
    if (packageValue.status !== 'approved' || packageValue.approval?.approved !== true) {
      throw new Error('positive_boardroom_approval_required');
    }
    const result = await request('/route', {
      method: 'POST',
      body: JSON.stringify({
        package: packageValue,
        routed_at: new Date().toISOString(),
        routed_by: 'central_pilot',
      }),
    });
    return result;
  }

  async function approveBoardroomAction(actionRecord) {
    if (!actionRecord || typeof actionRecord !== 'object') {
      throw new Error('structured_boardroom_action_required');
    }
    if (!actionRecord.department_id) {
      throw new Error('explicit_boardroom_department_required');
    }
    if (!Array.isArray(actionRecord.actions) || !actionRecord.actions.length) {
      throw new Error('boardroom_action_list_required');
    }
    const result = await request('/approve-boardroom-action', {
      method: 'POST',
      body: JSON.stringify(actionRecord),
    });
    notifyRouted(result);
    return result;
  }

  function profiles() {
    return request('/profiles');
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function resolveBusinessId() {
    return global.AionBusinessContainerClient?.resolveBusinessId?.()
      || global.__aionCanonicalBusinessId
      || '';
  }

  function taskCard(envelope) {
    const task = envelope?.task || {};
    return `
      <article class="aion-canonical-pilot-task" data-aion-canonical-task-id="${escapeHtml(task.task_id)}">
        <div><strong>${escapeHtml(task.title || 'Boardroom action')}</strong><span>${escapeHtml(task.status || 'queued')}</span></div>
        <p>${escapeHtml(task.objective || '')}</p>
        <small>Boardroom package ${escapeHtml(task.package_id || '')} · ${escapeHtml(task.priority || 'medium')} priority</small>
      </article>`;
  }

  function queuePanel(payload, departmentId) {
    const tasks = Array.isArray(payload?.tasks) ? payload.tasks : [];
    const signature = tasks.map((item) => `${item?.task?.task_id || ''}:${item?.task?.status || ''}:${item?.envelope_hash || ''}`).join('|') || 'empty';
    const heading = departmentId === 'pilot'
      ? 'Central Pilot · approved work monitor'
      : `${departmentId.charAt(0).toUpperCase()}${departmentId.slice(1)} Pilot · approved Boardroom queue`;
    return `
      <section class="aion-canonical-pilot-queue" data-aion-canonical-pilot-queue="${escapeHtml(departmentId)}" data-aion-canonical-queue-signature="${escapeHtml(signature)}">
        <header><strong>&gt; ${escapeHtml(heading)}</strong><span>${tasks.length} task${tasks.length === 1 ? '' : 's'}</span></header>
        ${tasks.length ? tasks.map(taskCard).join('') : '<p class="aion-canonical-pilot-empty">No approved Boardroom actions are waiting.</p>'}
      </section>`;
  }

  function applyActivationGate(terminal, stream, payload, departmentId) {
    const profile = payload?.profile || null;
    const blocked = departmentId !== 'pilot' && profile?.activation_state !== 'enabled';
    terminal.querySelectorAll?.('[data-aion-pilot-mission-input],[data-aion-pilot-create-draft-mission]')
      .forEach((element) => { element.disabled = blocked; });
    const existingGate = stream.querySelector?.('[data-aion-department-design-gate]');
    if (!blocked) {
      existingGate?.remove?.();
      return;
    }
    if (existingGate?.getAttribute?.('data-aion-department-design-gate') === departmentId) return;
    existingGate?.remove?.();
    const topics = Array.isArray(profile?.design_topics) ? profile.design_topics : [];
    stream.insertAdjacentHTML?.('afterbegin', `
      <section class="aion-department-design-gate" data-aion-department-design-gate="${escapeHtml(departmentId)}">
        <strong>&gt; ${escapeHtml(profile?.display_name || departmentId)} · design session required</strong>
        <p>This Pilot has not been configured. Its purpose, workflows, capabilities and permissions will be agreed with you before activation.</p>
        ${topics.length ? `<ul>${topics.map((topic) => `<li>${escapeHtml(topic)}</li>`).join('')}</ul>` : ''}
      </section>`);
  }

  async function refreshVisibleQueue() {
    const terminal = global.document?.querySelector?.('[data-aion-shared-pilot-terminal="true"]');
    const stream = terminal?.querySelector?.('[data-aion-pilot-stream-window]');
    const departmentId = terminal?.getAttribute?.('data-aion-pilot-role') || '';
    const workspaceId = resolveBusinessId();
    if (!stream || !workspaceId || !departmentId) return null;

    try {
      const payload = departmentId === 'pilot'
        ? await monitor(workspaceId)
        : await departmentQueue(workspaceId, departmentId);
      const html = queuePanel(payload, departmentId);
      const signature = (Array.isArray(payload?.tasks) ? payload.tasks : [])
        .map((item) => `${item?.task?.task_id || ''}:${item?.task?.status || ''}:${item?.envelope_hash || ''}`)
        .join('|') || 'empty';
      const current = stream.querySelector?.('[data-aion-canonical-pilot-queue]');
      if (current?.getAttribute?.('data-aion-canonical-queue-signature') !== signature) {
        current?.remove?.();
        stream.insertAdjacentHTML?.('afterbegin', html);
      }
      applyActivationGate(terminal, stream, payload, departmentId);
      return payload;
    } catch (error) {
      console.warn('[AION] Department Pilot queue refresh deferred', error);
      return null;
    }
  }

  function scheduleVisibleQueueRefresh() {
    global.clearTimeout?.(queueRefreshTimer);
    queueRefreshTimer = global.setTimeout?.(refreshVisibleQueue, 80);
  }

  async function refreshProfiles() {
    try {
      profilesCache = await profiles();
      global.__aionDepartmentPilotProfiles = profilesCache;
      return profilesCache;
    } catch {
      return profilesCache;
    }
  }

  function notifyRouted(result) {
    global.dispatchEvent?.(new CustomEvent('aion:department-pilot-package-routed', {
      detail: result,
    }));
    scheduleVisibleQueueRefresh();
  }

  function monitor(workspaceId) {
    return request(`/monitor/${encodeURIComponent(workspaceId)}`);
  }

  function departmentQueue(workspaceId, departmentId) {
    return request(`/${encodeURIComponent(workspaceId)}/${encodeURIComponent(departmentId)}`);
  }

  async function handleApprovedPackageEvent(event) {
    try {
      const result = await routeApprovedPackage(event?.detail?.package);
      notifyRouted(result);
    } catch (error) {
      global.dispatchEvent?.(new CustomEvent('aion:department-pilot-package-route-failed', {
        detail: { message: String(error?.message || error) },
      }));
    }
  }

  async function handleApprovedActionEvent(event) {
    try {
      await approveBoardroomAction(event?.detail);
    } catch (error) {
      global.dispatchEvent?.(new CustomEvent('aion:department-pilot-package-route-failed', {
        detail: { message: String(error?.message || error) },
      }));
    }
  }

  global.AionDepartmentPilotBackend = Object.freeze({
    PACKAGE_SCHEMA,
    approveAndRoute,
    approveBoardroomAction,
    routeApprovedPackage,
    profiles,
    monitor,
    departmentQueue,
    refreshVisibleQueue,
    refreshProfiles,
  });

  global.addEventListener?.(
    'aion:canonical-boardroom-package-approved',
    handleApprovedPackageEvent,
  );
  global.addEventListener?.(
    'aion:canonical-boardroom-action-approved',
    handleApprovedActionEvent,
  );

  if (global.document) {
    const style = global.document.createElement('style');
    style.id = 'aion-department-pilot-backend-styles';
    style.textContent = `
      .aion-canonical-pilot-queue{border:1px solid rgba(56,189,248,.42);background:#07111f;padding:14px;margin:0 0 16px;color:#cbd5e1}
      .aion-canonical-pilot-queue>header,.aion-canonical-pilot-task>div{display:flex;justify-content:space-between;gap:16px;align-items:center}
      .aion-canonical-pilot-queue>header{color:#7dd3fc;padding-bottom:10px;border-bottom:1px solid rgba(56,189,248,.24)}
      .aion-canonical-pilot-queue>header span,.aion-canonical-pilot-task span{color:#86efac;text-transform:uppercase;font-size:11px;letter-spacing:.12em}
      .aion-canonical-pilot-task{padding:12px 0;border-bottom:1px solid rgba(56,189,248,.18)}
      .aion-canonical-pilot-task:last-child{border-bottom:0}
      .aion-canonical-pilot-task strong{color:#e2e8f0}.aion-canonical-pilot-task p{margin:7px 0;color:#cbd5e1}.aion-canonical-pilot-task small{color:#64748b}
      .aion-canonical-pilot-empty{margin:12px 0 0;color:#64748b}
      .aion-department-design-gate{border:1px solid #f59e0b;background:#1c1917;padding:14px;margin:0 0 16px;color:#fde68a}
      .aion-department-design-gate strong{color:#fbbf24}.aion-department-design-gate p{color:#d6d3d1}.aion-department-design-gate ul{margin:8px 0 0;padding-left:20px;color:#a8a29e}
    `;
    global.document.head.appendChild(style);
    const observer = new MutationObserver(scheduleVisibleQueueRefresh);
    observer.observe(global.document.documentElement, { childList: true, subtree: true });
    global.setTimeout?.(scheduleVisibleQueueRefresh, 700);
    global.setInterval?.(() => {
      if (global.document.querySelector('[data-aion-shared-pilot-terminal="true"]')) refreshVisibleQueue();
    }, 5000);
    refreshProfiles();
  }
})(window);
