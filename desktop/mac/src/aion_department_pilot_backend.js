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

  function formatFinanceValue(value, format, currency) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 'Not available';
    if (format === 'percent') return `${number.toFixed(1)}%`;
    if (format === 'money') {
      try {
        return new Intl.NumberFormat(undefined, {
          style: 'currency', currency: currency || 'EUR', maximumFractionDigits: 0,
        }).format(number);
      } catch {
        return `${currency || 'EUR'} ${number.toLocaleString()}`;
      }
    }
    return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
  }

  function financeManagementHandback(handback) {
    const report = handback?.metric_changes?.management_report;
    if (!report || typeof report !== 'object') return '';
    const currency = report.currency || 'EUR';
    const keys = new Set(['revenue', 'gross_profit', 'gross_margin_percent', 'operating_profit', 'ending_cash', 'debtors', 'creditors']);
    const kpis = (Array.isArray(report.kpis) ? report.kpis : [])
      .filter((item) => keys.has(item?.key) && item?.available)
      .slice(0, 7);
    const period = report.period || {};
    const freshness = report.evidence_freshness || {};
    const warnings = Array.isArray(report.warnings) ? report.warnings.slice(0, 4) : [];
    return `
      <section class="aion-finance-management-handback" data-aion-finance-management-handback>
        <header><strong>Management account</strong><span>${escapeHtml(period.label || 'Period not specified')}</span></header>
        ${kpis.length ? `<div class="aion-finance-management-kpis">${kpis.map((item) => `
          <article>
            <small>${escapeHtml(item.label || item.key)}</small>
            <strong>${escapeHtml(formatFinanceValue(item.actual, item.format, currency))}</strong>
            ${item.budget_variance_percent != null ? `<em>Budget variance ${escapeHtml(formatFinanceValue(item.budget_variance_percent, 'percent', currency))}</em>` : ''}
            ${item.previous_variance_percent != null ? `<em>Previous period ${escapeHtml(formatFinanceValue(item.previous_variance_percent, 'percent', currency))}</em>` : ''}
          </article>`).join('')}</div>` : '<p>No supported management-account figures are available.</p>'}
        <footer>
          <span>Evidence: ${escapeHtml(freshness.overall_state || 'not dated')}${freshness.latest_observed_at ? ` · latest ${escapeHtml(freshness.latest_observed_at)}` : ''}</span>
          <span>${report.comparison_coverage?.budget_available ? 'Budget comparison available' : 'No budget comparison'} · ${report.comparison_coverage?.previous_period_available ? 'Previous period available' : 'No previous period comparison'}</span>
        </footer>
        ${warnings.length ? `<details><summary>${warnings.length} evidence or reporting warning${warnings.length === 1 ? '' : 's'}</summary><ul>${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join('')}</ul></details>` : ''}
      </section>`;
  }

  function taskCard(envelope, departmentId) {
    const task = envelope?.task || {};
    const handback = envelope?.handback || null;
    const artifacts = Array.isArray(envelope?.artifacts) ? envelope.artifacts : [];
    const events = Array.isArray(envelope?.events) ? envelope.events : [];
    const latestEvent = events.length ? events[events.length - 1] : null;
    const canRunFinance = departmentId === 'finance' && task.department_id === 'finance' && task.status === 'queued';
    return `
      <article class="aion-canonical-pilot-task" data-aion-canonical-task-id="${escapeHtml(task.task_id)}">
        <div><strong>${escapeHtml(task.title || 'Boardroom action')}</strong><span>${escapeHtml(task.status || 'queued')}</span></div>
        <p>${escapeHtml(task.objective || '')}</p>
        <small>Boardroom package ${escapeHtml(task.package_id || '')} · ${escapeHtml(task.priority || 'medium')} priority</small>
        ${canRunFinance ? `<button type="button" class="aion-finance-run-task" data-aion-finance-run-task="${escapeHtml(task.task_id)}">Run read-only Finance analysis</button>` : ''}
        ${handback ? `
          <section class="aion-pilot-handback">
            <strong>&gt; Result ready for Boardroom</strong>
            <p>${escapeHtml(handback.executive_summary || '')}</p>
            ${financeManagementHandback(handback)}
            ${artifacts.length ? `<small>Saved in Finance / Reports · ${escapeHtml(artifacts[artifacts.length - 1]?.title || 'Finance report')}</small>` : ''}
          </section>` : ''}
        ${task.status === 'failed' ? `
          <section class="aion-pilot-failure">
            <strong>&gt; Action failed</strong>
            <p>${escapeHtml(latestEvent?.message || 'Finance could not complete this action. Review the error before retrying.')}</p>
          </section>` : ''}
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
        ${tasks.length ? tasks.map((item) => taskCard(item, departmentId)).join('') : '<p class="aion-canonical-pilot-empty">No approved Boardroom actions are waiting.</p>'}
      </section>`;
  }

  function financeConversationPanel(payload) {
    const turns = Array.isArray(payload?.session?.turns) ? payload.session.turns.slice(-40) : [];
    const signature = turns.map((turn) => turn?.turn_hash || '').join('|') || 'empty';
    return `
      <section class="aion-finance-conversation" data-aion-finance-conversation data-aion-finance-conversation-signature="${escapeHtml(signature)}">
        <header><strong>&gt; Finance Pilot · grounded conversation</strong><span>Read-only</span></header>
        ${turns.length ? turns.map((turn) => {
          const sources = Array.isArray(turn?.sources) ? turn.sources : [];
          const isUser = turn?.role === 'user';
          return `
            <article class="aion-finance-conversation-turn ${isUser ? 'is-user' : 'is-finance'}">
              <strong>${isUser ? 'You' : 'Finance Pilot'}</strong>
              <p>${escapeHtml(turn?.content || '')}</p>
              ${!isUser ? `<small>Reliability: ${escapeHtml(turn?.reliability || 'unverified')}${sources.length ? ` · Sources: ${sources.map((source) => escapeHtml(source?.label || source?.container_kind || '')).join(', ')}` : ''} · no external action taken</small>` : ''}
            </article>`;
        }).join('') : '<p class="aion-canonical-pilot-empty">Ask Finance about revenue, margins, costs, cash, evidence or an approved Boardroom action.</p>'}
      </section>`;
  }

  function financeScenarioPanel(payload) {
    const latest = payload?.latest_scenario || null;
    const expected = latest?.variants?.expected?.summary || null;
    const upside = latest?.variants?.upside?.summary || null;
    const downside = latest?.variants?.downside?.summary || null;
    const currency = latest?.currency || 'EUR';
    const signature = latest?.scenario_hash || 'empty';
    return `
      <section class="aion-finance-scenario" data-aion-finance-scenario data-aion-finance-scenario-signature="${escapeHtml(signature)}">
        <header><strong>&gt; Finance Pilot · forecasting and scenarios</strong><span>Planning model · not actuals</span></header>
        ${latest ? `
          <div class="aion-finance-scenario-latest">
            <strong>${escapeHtml(latest.name || 'Latest scenario')}</strong>
            <span>Expected closing cash ${escapeHtml(formatFinanceValue(expected?.closing_cash, 'money', currency))}</span>
            <span>Upside ${escapeHtml(formatFinanceValue(upside?.closing_cash, 'money', currency))}</span>
            <span>Downside ${escapeHtml(formatFinanceValue(downside?.closing_cash, 'money', currency))}</span>
            <small>${expected?.months_below_reserve?.length ? `${expected.months_below_reserve.length} expected month(s) below the protected reserve` : 'Expected case remains above the protected reserve'} · saved in Finance / Scenarios</small>
          </div>` : '<p>No saved scenario yet. Use the verified management-account baseline to test a plan.</p>'}
        <details>
          <summary>Run a Finance scenario</summary>
          <form data-aion-finance-scenario-form>
            <label>Scenario name<input name="scenario_name" value="Finance planning scenario" maxlength="160"></label>
            <label>Months<input name="forecast_months" type="number" min="1" max="36" value="12"></label>
            <label>Revenue change %<input name="revenue_change_percent" type="number" step="0.1" value="0"></label>
            <label>Annual growth %<input name="annual_revenue_growth_percent" type="number" step="0.1" value="0"></label>
            <label>Price change %<input name="price_change_percent" type="number" step="0.1" value="0"></label>
            <label>Volume change %<input name="volume_change_percent" type="number" step="0.1" value="0"></label>
            <label>Direct-cost change %<input name="direct_cost_change_percent" type="number" step="0.1" value="0"></label>
            <label>Overhead change %<input name="overhead_change_percent" type="number" step="0.1" value="0"></label>
            <label>New monthly people cost<input name="monthly_hiring_cost" type="number" min="0" step="0.01" value="0"></label>
            <label>One-off stock purchase<input name="one_off_stock_purchase" type="number" min="0" step="0.01" value="0"></label>
            <label>Stock purchase month<input name="stock_purchase_month" type="number" min="1" max="36" value="1"></label>
            <label>Protected cash reserve<input name="minimum_cash_reserve" type="number" min="0" step="0.01" value="0"></label>
            <label>Upside/downside sensitivity %<input name="sensitivity_percent" type="number" min="0" max="100" step="0.1" value="10"></label>
            <button type="submit" data-aion-finance-run-scenario>Run and save scenario</button>
          </form>
          <small>Scenarios are stored separately and never overwrite accounting evidence or accepted historical facts.</small>
        </details>
      </section>`;
  }

  async function refreshFinanceScenario(terminal, stream, workspaceId) {
    if (!terminal || !stream || terminal.getAttribute('data-aion-pilot-role') !== 'finance') return null;
    const payload = await financeScenarios(workspaceId);
    const html = financeScenarioPanel(payload);
    const nextSignature = payload?.latest_scenario?.scenario_hash || 'empty';
    const current = stream.querySelector?.('[data-aion-finance-scenario]');
    if (current?.getAttribute?.('data-aion-finance-scenario-signature') !== nextSignature) {
      current?.remove?.();
      const conversation = stream.querySelector?.('[data-aion-finance-conversation]');
      if (conversation) conversation.insertAdjacentHTML?.('beforebegin', html);
      else stream.insertAdjacentHTML?.('beforeend', html);
    }
    return payload;
  }

  function financeReconciliationPanel(payload) {
    const latest = payload?.latest_reconciliation || null;
    const counts = latest?.counts || {};
    const signature = latest?.reconciliation_hash || 'empty';
    const needsReview = latest?.status === 'review_required';
    return `
      <section class="aion-finance-reconciliation" data-aion-finance-reconciliation data-aion-finance-reconciliation-signature="${escapeHtml(signature)}">
        <header><strong>&gt; Finance Pilot · Xero and spreadsheet reconciliation</strong><span>Read-only</span></header>
        ${latest ? `<p>${Number(counts.match || 0)} matching · ${Number(counts.conflict || 0)} conflicts · ${Number(counts.period_missing || 0) + Number(counts.period_mismatch || 0)} period issues</p>
          ${(latest.warnings || []).length ? `<ul>${latest.warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
          ${needsReview ? `<div class="aion-finance-reconciliation-actions">
            <button type="button" data-aion-reconciliation-review="keep_spreadsheet" data-aion-reconciliation-id="${escapeHtml(latest.reconciliation_id)}">Keep spreadsheet</button>
            <button type="button" data-aion-reconciliation-review="prefer_xero" data-aion-reconciliation-id="${escapeHtml(latest.reconciliation_id)}">Prefer Xero</button>
            <button type="button" data-aion-reconciliation-review="needs_investigation" data-aion-reconciliation-id="${escapeHtml(latest.reconciliation_id)}">Investigate</button>
          </div>` : `<small>Review state: ${escapeHtml(latest.status || 'not reviewed')}</small>`}` : '<p>No reconciliation has been run.</p>'}
        <details><summary>Run reconciliation</summary>
          <form data-aion-finance-reconciliation-form>
            <label>Spreadsheet period from<input name="period_from" type="date"></label>
            <label>Spreadsheet period to<input name="period_to" type="date"></label>
            <label>Tolerance %<input name="tolerance_percent" type="number" min="0" max="100" step="0.1" value="1"></label>
            <button type="submit" data-aion-finance-run-reconciliation>Compare accepted files with Xero</button>
          </form>
          <small>No accepted fact is replaced by this check. A review decision is recorded separately.</small>
        </details>
      </section>`;
  }

  async function refreshFinanceReconciliation(terminal, stream, workspaceId) {
    if (!terminal || !stream || terminal.getAttribute('data-aion-pilot-role') !== 'finance') return null;
    const payload = await financeReconciliations(workspaceId);
    const signature = payload?.latest_reconciliation?.reconciliation_hash || 'empty';
    const current = stream.querySelector?.('[data-aion-finance-reconciliation]');
    if (current?.getAttribute?.('data-aion-finance-reconciliation-signature') !== signature) {
      current?.remove?.();
      const scenario = stream.querySelector?.('[data-aion-finance-scenario]');
      if (scenario) scenario.insertAdjacentHTML?.('afterend', financeReconciliationPanel(payload));
      else stream.insertAdjacentHTML?.('beforeend', financeReconciliationPanel(payload));
    }
    return payload;
  }

  async function refreshFinanceConversation(terminal, stream, workspaceId) {
    if (!terminal || !stream || terminal.getAttribute('data-aion-pilot-role') !== 'finance') return null;
    const payload = await financeConversationSession(workspaceId);
    const html = financeConversationPanel(payload);
    const nextSignature = (Array.isArray(payload?.session?.turns) ? payload.session.turns : [])
      .map((turn) => turn?.turn_hash || '').join('|') || 'empty';
    const current = stream.querySelector?.('[data-aion-finance-conversation]');
    if (current?.getAttribute?.('data-aion-finance-conversation-signature') !== nextSignature) {
      current?.remove?.();
      stream.insertAdjacentHTML?.('beforeend', html);
      stream.scrollTop = stream.scrollHeight;
    }
    const input = terminal.querySelector?.('[data-aion-pilot-mission-input]');
    const button = terminal.querySelector?.('[data-aion-pilot-create-draft-mission]');
    if (input) input.placeholder = 'Ask the Finance Pilot about revenue, margins, costs, cash or evidence…';
    if (button && !button.disabled) button.textContent = 'Ask Finance';
    return payload;
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
      if (departmentId === 'finance') {
        await refreshFinanceScenario(terminal, stream, workspaceId);
        await refreshFinanceReconciliation(terminal, stream, workspaceId);
        await refreshFinanceConversation(terminal, stream, workspaceId);
      }
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

  function financeConversationSession(workspaceId) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/conversation/session`);
  }

  function financeScenarios(workspaceId) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/scenarios`);
  }

  function runFinanceScenario(workspaceId, scenario) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/scenarios/run`, {
      method: 'POST',
      body: JSON.stringify({
        ...scenario,
        created_at: new Date().toISOString(),
        created_by: 'finance_pilot',
      }),
    });
  }

  function financeReconciliations(workspaceId) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/reconciliations`);
  }

  function runFinanceReconciliation(workspaceId, payload) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/reconciliations/run`, { method: 'POST', body: JSON.stringify(payload) });
  }

  function reviewFinanceReconciliation(workspaceId, reconciliationId, decision) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/reconciliations/${encodeURIComponent(reconciliationId)}/review`, {
      method: 'POST', body: JSON.stringify({ decision, reviewed_by: 'founder', reviewed_at: new Date().toISOString() }),
    });
  }

  function askFinance(workspaceId, userText) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/conversation/turn`, {
      method: 'POST',
      body: JSON.stringify({
        user_text: String(userText || '').trim(),
        created_at: new Date().toISOString(),
      }),
    });
  }

  function executeFinanceTask(workspaceId, taskId) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/${encodeURIComponent(taskId)}/execute-read-only`, {
      method: 'POST',
      body: JSON.stringify({
        actor_id: 'finance_pilot',
        executed_at: new Date().toISOString(),
      }),
    });
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

  async function handleFinanceExecutionClick(event) {
    const button = event?.target?.closest?.('[data-aion-finance-run-task]');
    if (!button) return;
    const workspaceId = resolveBusinessId();
    const taskId = button.getAttribute('data-aion-finance-run-task') || '';
    if (!workspaceId || !taskId || button.disabled) return;
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = 'Finance analysis running…';
    try {
      const result = await executeFinanceTask(workspaceId, taskId);
      global.dispatchEvent?.(new CustomEvent('aion:finance-pilot-task-completed', {
        detail: result,
      }));
      await refreshVisibleQueue();
    } catch (error) {
      button.disabled = false;
      button.textContent = originalLabel;
      global.dispatchEvent?.(new CustomEvent('aion:finance-pilot-task-failed', {
        detail: { task_id: taskId, message: String(error?.message || error) },
      }));
      console.error('[AION] Finance Pilot task failed', error);
    }
  }

  async function handleFinanceConversationSubmit(event) {
    const button = event?.target?.closest?.('[data-aion-pilot-create-draft-mission]');
    const terminal = button?.closest?.('[data-aion-shared-pilot-terminal="true"]');
    if (!button || terminal?.getAttribute?.('data-aion-pilot-role') !== 'finance') return;
    event.preventDefault?.();
    event.stopImmediatePropagation?.();
    const input = terminal.querySelector?.('[data-aion-pilot-mission-input]');
    const question = String(input?.value || '').trim();
    const workspaceId = resolveBusinessId();
    if (!question || !workspaceId || button.disabled) return;
    button.disabled = true;
    button.textContent = 'Finance is analysing…';
    if (input) input.disabled = true;
    try {
      const result = await askFinance(workspaceId, question);
      if (input) input.value = '';
      global.dispatchEvent?.(new CustomEvent('aion:finance-pilot-conversation-turn', { detail: result }));
      const stream = terminal.querySelector?.('[data-aion-pilot-stream-window]');
      await refreshFinanceConversation(terminal, stream, workspaceId);
    } catch (error) {
      const stream = terminal.querySelector?.('[data-aion-pilot-stream-window]');
      stream?.querySelector?.('[data-aion-finance-conversation-error]')?.remove?.();
      stream?.insertAdjacentHTML?.('beforeend', `
        <section class="aion-pilot-failure" data-aion-finance-conversation-error>
          <strong>&gt; Finance could not answer</strong>
          <p>${escapeHtml(String(error?.message || error))}</p>
        </section>`);
      global.dispatchEvent?.(new CustomEvent('aion:finance-pilot-conversation-failed', {
        detail: { message: String(error?.message || error) },
      }));
      console.error('[AION] Finance Pilot conversation failed', error);
    } finally {
      button.disabled = false;
      button.textContent = 'Ask Finance';
      if (input) {
        input.disabled = false;
        input.focus?.();
      }
    }
  }

  async function handleFinanceScenarioSubmit(event) {
    const form = event?.target?.closest?.('[data-aion-finance-scenario-form]');
    if (!form) return;
    event.preventDefault?.();
    const terminal = form.closest?.('[data-aion-shared-pilot-terminal="true"]');
    if (terminal?.getAttribute?.('data-aion-pilot-role') !== 'finance') return;
    const workspaceId = resolveBusinessId();
    const button = form.querySelector?.('[data-aion-finance-run-scenario]');
    if (!workspaceId || !button || button.disabled) return;
    const values = Object.fromEntries(new FormData(form).entries());
    const numericFields = [
      'forecast_months', 'annual_revenue_growth_percent', 'revenue_change_percent',
      'price_change_percent', 'volume_change_percent', 'direct_cost_change_percent',
      'overhead_change_percent', 'monthly_hiring_cost', 'one_off_stock_purchase',
      'stock_purchase_month', 'minimum_cash_reserve', 'sensitivity_percent',
    ];
    numericFields.forEach((field) => { values[field] = Number(values[field] || 0); });
    button.disabled = true;
    button.textContent = 'Modelling scenario…';
    try {
      const result = await runFinanceScenario(workspaceId, values);
      global.dispatchEvent?.(new CustomEvent('aion:finance-scenario-completed', { detail: result }));
      const stream = terminal.querySelector?.('[data-aion-pilot-stream-window]');
      await refreshFinanceScenario(terminal, stream, workspaceId);
    } catch (error) {
      global.dispatchEvent?.(new CustomEvent('aion:finance-scenario-failed', {
        detail: { message: String(error?.message || error) },
      }));
      console.error('[AION] Finance scenario failed', error);
    } finally {
      button.disabled = false;
      button.textContent = 'Run and save scenario';
    }
  }

  async function handleFinanceReconciliationSubmit(event) {
    const form = event?.target?.closest?.('[data-aion-finance-reconciliation-form]');
    if (!form) return;
    event.preventDefault?.();
    const terminal = form.closest?.('[data-aion-shared-pilot-terminal="true"]');
    const workspaceId = resolveBusinessId();
    const button = form.querySelector?.('[data-aion-finance-run-reconciliation]');
    if (!workspaceId || !button || button.disabled) return;
    const values = Object.fromEntries(new FormData(form).entries());
    const period = values.period_from && values.period_to ? { '*': { from: values.period_from, to: values.period_to } } : {};
    button.disabled = true; button.textContent = 'Comparing evidence…';
    try {
      await runFinanceReconciliation(workspaceId, { artifact_periods: period, tolerance_percent: Number(values.tolerance_percent || 1), created_at: new Date().toISOString() });
      await refreshFinanceReconciliation(terminal, terminal.querySelector?.('[data-aion-pilot-stream-window]'), workspaceId);
    } catch (error) { console.error('[AION] Finance reconciliation failed', error); }
    finally { button.disabled = false; button.textContent = 'Compare accepted files with Xero'; }
  }

  async function handleFinanceReconciliationReview(event) {
    const button = event?.target?.closest?.('[data-aion-reconciliation-review]');
    if (!button || button.disabled) return;
    const workspaceId = resolveBusinessId(); const reconciliationId = button.getAttribute('data-aion-reconciliation-id');
    const decision = button.getAttribute('data-aion-reconciliation-review');
    const terminal = button.closest?.('[data-aion-shared-pilot-terminal="true"]');
    if (!workspaceId || !reconciliationId || !decision) return;
    button.disabled = true;
    try {
      await reviewFinanceReconciliation(workspaceId, reconciliationId, decision);
      await refreshFinanceReconciliation(terminal, terminal.querySelector?.('[data-aion-pilot-stream-window]'), workspaceId);
    } catch (error) { button.disabled = false; console.error('[AION] Finance reconciliation review failed', error); }
  }

  global.AionDepartmentPilotBackend = Object.freeze({
    PACKAGE_SCHEMA,
    approveAndRoute,
    approveBoardroomAction,
    routeApprovedPackage,
    profiles,
    monitor,
    departmentQueue,
    financeConversationSession,
    askFinance,
    financeScenarios,
    runFinanceScenario,
    financeReconciliations,
    runFinanceReconciliation,
    reviewFinanceReconciliation,
    executeFinanceTask,
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
    global.document.addEventListener('submit', handleFinanceScenarioSubmit, true);
    global.document.addEventListener('submit', handleFinanceReconciliationSubmit, true);
    global.document.addEventListener('click', handleFinanceReconciliationReview, true);
    global.document.addEventListener('click', handleFinanceConversationSubmit, true);
    global.document.addEventListener('click', handleFinanceExecutionClick);
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
      .aion-finance-run-task{display:block;margin:12px 0 0;padding:10px 14px;border:1px solid #4ade80;background:#16a34a;color:#03150b;font:700 12px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.08em;text-transform:uppercase;cursor:pointer}
      .aion-finance-run-task:disabled{opacity:.65;cursor:wait}
      .aion-pilot-handback{margin:12px 0 0;padding:12px;border:1px solid rgba(74,222,128,.55);background:#052e1a;color:#dcfce7}
      .aion-pilot-handback strong{color:#86efac}.aion-pilot-handback p{color:#dcfce7}.aion-pilot-handback small{color:#86efac}
      .aion-finance-management-handback{margin:12px 0;padding:12px;border:1px solid rgba(125,211,252,.35);background:#07111f;color:#cbd5e1}
      .aion-finance-management-handback>header,.aion-finance-management-handback>footer{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
      .aion-finance-management-handback>header{padding-bottom:10px;border-bottom:1px solid rgba(56,189,248,.2)}
      .aion-finance-management-handback>header strong{color:#7dd3fc}.aion-finance-management-handback>header span{color:#cbd5e1;text-transform:none;letter-spacing:0;font-size:12px}
      .aion-finance-management-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:8px;margin:10px 0}
      .aion-finance-management-kpis article{padding:10px;border:1px solid rgba(56,189,248,.2);background:#0f172a}
      .aion-finance-management-kpis article small,.aion-finance-management-kpis article strong,.aion-finance-management-kpis article em{display:block}
      .aion-finance-management-kpis article small{color:#94a3b8}.aion-finance-management-kpis article strong{margin:5px 0;color:#f8fafc;font-size:17px}.aion-finance-management-kpis article em{color:#7dd3fc;font-size:10px;font-style:normal}
      .aion-finance-management-handback>footer{padding-top:8px;border-top:1px solid rgba(56,189,248,.2);color:#94a3b8;font-size:10px}
      .aion-finance-management-handback details{margin-top:8px;color:#fbbf24}.aion-finance-management-handback details ul{margin:8px 0 0;padding-left:20px;color:#fde68a}
      .aion-pilot-failure{margin:12px 0 0;padding:12px;border:1px solid #ef4444;background:#2a0a0a;color:#fecaca}
      .aion-pilot-failure strong{color:#fca5a5}.aion-pilot-failure p{color:#fecaca}
      .aion-finance-conversation{border:1px solid rgba(56,189,248,.42);background:#07111f;padding:14px;margin:0;color:#cbd5e1}
      .aion-finance-conversation>header{display:flex;justify-content:space-between;gap:16px;padding-bottom:10px;border-bottom:1px solid rgba(56,189,248,.24);color:#7dd3fc}
      .aion-finance-conversation>header span{color:#86efac;font-size:11px;letter-spacing:.12em;text-transform:uppercase}
      .aion-finance-conversation-turn{padding:12px;border-bottom:1px solid rgba(56,189,248,.16)}
      .aion-finance-conversation-turn:last-child{border-bottom:0}.aion-finance-conversation-turn.is-user{background:#0f172a}
      .aion-finance-conversation-turn.is-user strong{color:#7dd3fc}.aion-finance-conversation-turn.is-finance strong{color:#86efac}
      .aion-finance-conversation-turn p{white-space:pre-wrap;color:#e2e8f0}.aion-finance-conversation-turn small{color:#94a3b8}
      .aion-finance-scenario{border:1px solid rgba(74,222,128,.5);background:#07111f;padding:14px;margin:0 0 16px;color:#cbd5e1}
      .aion-finance-scenario>header{display:flex;justify-content:space-between;gap:16px;padding-bottom:10px;border-bottom:1px solid rgba(74,222,128,.25)}
      .aion-finance-scenario>header strong{color:#86efac}.aion-finance-scenario>header span{color:#fbbf24;font-size:11px;letter-spacing:.1em;text-transform:uppercase}
      .aion-finance-scenario-latest{display:grid;grid-template-columns:repeat(3,minmax(130px,1fr));gap:8px;padding:12px 0}
      .aion-finance-scenario-latest>strong,.aion-finance-scenario-latest>small{grid-column:1/-1;color:#e2e8f0}.aion-finance-scenario-latest>span{padding:9px;border:1px solid rgba(56,189,248,.2);color:#7dd3fc}
      .aion-finance-scenario details{margin-top:8px}.aion-finance-scenario summary{cursor:pointer;color:#86efac}
      .aion-finance-scenario form{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:9px;margin:12px 0}
      .aion-finance-scenario label{display:grid;gap:5px;color:#94a3b8;font-size:11px}.aion-finance-scenario input{border:1px solid rgba(56,189,248,.35);background:#0f172a;color:#f8fafc;padding:9px;font:inherit}
      .aion-finance-scenario button{align-self:end;padding:10px 12px;border:1px solid #4ade80;background:#16a34a;color:#03150b;font-weight:800;cursor:pointer}.aion-finance-scenario button:disabled{opacity:.65;cursor:wait}
      .aion-finance-reconciliation{border:1px solid rgba(56,189,248,.42);background:#07111f;padding:14px;margin:0 0 16px;color:#cbd5e1}
      .aion-finance-reconciliation>header{display:flex;justify-content:space-between;gap:16px;padding-bottom:10px;border-bottom:1px solid rgba(56,189,248,.24)}.aion-finance-reconciliation>header strong{color:#7dd3fc}.aion-finance-reconciliation>header span{color:#86efac}
      .aion-finance-reconciliation ul{color:#fbbf24}.aion-finance-reconciliation form{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:9px;margin:12px 0}.aion-finance-reconciliation label{display:grid;gap:5px;color:#94a3b8;font-size:11px}.aion-finance-reconciliation input{background:#0f172a;border:1px solid rgba(56,189,248,.35);color:#f8fafc;padding:9px}
      .aion-finance-reconciliation button{padding:9px 12px;border:1px solid #38bdf8;background:#0c4a6e;color:#e0f2fe;font-weight:700;cursor:pointer}.aion-finance-reconciliation-actions{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
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
