(function installAionDepartmentPilotBackend(global) {
  'use strict';

  const API_BASE = 'http://127.0.0.1:8080';
  const API_PATH = '/api/aion/business/department-pilots';
  const PACKAGE_SCHEMA = 'aion.department_pilot.boardroom_assignment_package.v1';
  let queueRefreshTimer = null;
  let queueRefreshPromise = null;
  let observedTerminal = null;
  let observedDepartmentId = '';
  let observedWorkspaceId = '';
  let lastQueueRefreshKey = '';
  let lastQueueRefreshStartedAt = 0;
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
    const proposals = Array.isArray(envelope?.proposed_tool_calls) ? envelope.proposed_tool_calls : [];
    const approvals = Array.isArray(envelope?.approvals) ? envelope.approvals : [];
    const canRunFinance = departmentId === 'finance' && task.department_id === 'finance' && task.status === 'queued';
    return `
      <article class="aion-canonical-pilot-task" data-aion-canonical-task-id="${escapeHtml(task.task_id)}">
        <div><strong>${escapeHtml(task.title || 'Boardroom action')}</strong><span>${escapeHtml(task.status || 'queued')}</span></div>
        <p>${escapeHtml(task.objective || '')}</p>
        <small>Boardroom package ${escapeHtml(task.package_id || '')} · ${escapeHtml(task.priority || 'medium')} priority</small>
        ${canRunFinance ? `<button type="button" class="aion-finance-run-task" data-aion-finance-run-task="${escapeHtml(task.task_id)}">Run read-only Finance analysis</button>` : ''}
        ${proposals.map((proposal) => {
          const approval = approvals.find((item) => item?.tool_call_id === proposal?.tool_call_id);
          return `<section class="aion-finance-proposal">
            <strong>&gt; Controlled Finance proposal · ${escapeHtml(proposal.tool_name)}</strong>
            <pre>${escapeHtml(JSON.stringify(proposal.payload, null, 2))}</pre>
            <small>Exact payload hash: ${escapeHtml(proposal.payload_hash)} · no external action taken</small>
            ${approval ? `<p>Decision: ${escapeHtml(approval.status)} · this approval applies only to the displayed payload.</p>` : `<div>
              <button type="button" data-aion-finance-proposal-decision="approve" data-task-id="${escapeHtml(task.task_id)}" data-tool-call-id="${escapeHtml(proposal.tool_call_id)}" data-payload-hash="${escapeHtml(proposal.payload_hash)}">Approve exact payload</button>
              <button type="button" data-aion-finance-proposal-decision="reject" data-task-id="${escapeHtml(task.task_id)}" data-tool-call-id="${escapeHtml(proposal.tool_call_id)}">Reject</button>
            </div>`}
          </section>`;
        }).join('')}
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
            <button type="button" data-aion-department-task-retry="${escapeHtml(task.task_id)}" data-department-id="${escapeHtml(task.department_id)}">Retry safely</button>
          </section>` : ''}
      </article>`;
  }

  function financeRecurringPanel(payload) {
    const schedules = Array.isArray(payload?.schedules) ? payload.schedules : [];
    const signature = schedules.map((item) => item.schedule_hash || '').join('|') || 'empty';
    const definitions = [
      ['weekly_cash_update', 'Weekly cash update', 'weekly'],
      ['monthly_management_report', 'Monthly management report', 'monthly'],
      ['period_close_check', 'Period-close check', 'monthly'],
      ['exception_cash_buffer_alert', 'Cash-buffer and exception alert', 'daily'],
    ];
    return `<section class="aion-finance-recurring" data-aion-finance-recurring data-aion-finance-recurring-signature="${escapeHtml(signature)}">
      <header><strong>&gt; Finance Pilot · recurring work</strong><span>Persistent schedules</span></header>
      ${schedules.length ? schedules.map((schedule) => `<article>
        <div><strong>${escapeHtml(schedule.kind.replaceAll('_', ' '))}</strong><span>${escapeHtml(schedule.enabled ? schedule.last_run_status : 'paused')}</span></div>
        <small>Next ${escapeHtml(schedule.next_run_at)} · ${Number(schedule.run_count || 0)} runs · ${Number(schedule.failure_count || 0)} failures</small>
        ${schedule.last_error ? `<p>${escapeHtml(schedule.last_error)}</p>` : ''}
        <button type="button" data-aion-finance-schedule-run="${escapeHtml(schedule.schedule_id)}">Run now</button>
        <button type="button" data-aion-finance-schedule-enabled="${escapeHtml(schedule.schedule_id)}" data-enabled="${schedule.enabled ? 'false' : 'true'}">${schedule.enabled ? 'Pause' : 'Resume'}</button>
      </article>`).join('') : '<p>No recurring Finance work is scheduled yet.</p>'}
      <details><summary>Add a standard Finance schedule</summary><div class="aion-finance-schedule-definitions">
        ${definitions.map(([kind, label, cadence]) => `<button type="button" data-aion-finance-schedule-create="${kind}" data-cadence="${cadence}">${label}</button>`).join('')}
      </div><label>Protected cash reserve <input type="number" min="0" step="0.01" value="0" data-aion-finance-schedule-reserve></label></details>
      <small>Scheduled work is read-only. Outputs are saved under Finance / Recurring and returned to Boardroom context.</small>
    </section>`;
  }

  async function refreshFinanceRecurring(terminal, stream, workspaceId) {
    if (!terminal || !stream || terminal.getAttribute('data-aion-pilot-role') !== 'finance') return null;
    const payload = await financeRecurringSchedules(workspaceId);
    const signature = (payload?.schedules || []).map((item) => item.schedule_hash || '').join('|') || 'empty';
    const current = stream.querySelector?.('[data-aion-finance-recurring]');
    if (current?.getAttribute?.('data-aion-finance-recurring-signature') !== signature) {
      current?.remove?.();
      stream.insertAdjacentHTML?.('beforeend', financeRecurringPanel(payload));
    }
    return payload;
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

  function financeDirectorPanel(ledgerPayload, directorPayload, transactionPayload, handoffPayload) {
    const ledger = ledgerPayload?.ledger || null;
    const director = directorPayload?.finance_director || null;
    const reconciliation = transactionPayload?.latest_transaction_reconciliation || null;
    const signals = Array.isArray(director?.proactive_signals) ? director.proactive_signals : [];
    const proposals = Array.isArray(director?.boardroom_proposals) ? director.boardroom_proposals : [];
    const matches = Array.isArray(reconciliation?.matches) ? reconciliation.matches.slice(0, 25) : [];
    const exceptions = Array.isArray(reconciliation?.exceptions) ? reconciliation.exceptions.slice(0, 25) : [];
    const classifications = Array.isArray(reconciliation?.classifications) ? reconciliation.classifications.slice(0, 25) : [];
    const handoffs = Array.isArray(handoffPayload?.handoffs) ? handoffPayload.handoffs : [];
    const handoffFor = (matchId) => handoffs.find((item) => item?.payload?.match_id === matchId) || null;
    const signature = [ledger?.ledger_hash, director?.director_model_hash, reconciliation?.run_hash, ...handoffs.map((item) => item.handoff_hash)].filter(Boolean).join('|') || 'empty';
    const currency = director?.currency || ledger?.currency || 'EUR';
    const statements = director?.financial_statements || {};
    const statementQuality = director?.statement_quality || {};
    const profitAndLoss = statements.profit_and_loss || {};
    const balanceSheet = statements.balance_sheet || {};
    const cashFlowStatement = statements.cash_flow || {};
    const statementCard = (label, value, format = 'money') => `<article><small>${escapeHtml(label)}</small><strong>${value == null ? 'Required' : escapeHtml(formatFinanceValue(value, format, currency))}</strong></article>`;
    const statementPanel = statements && Object.keys(statements).length ? `
      <section class="aion-finance-statement-package" data-aion-finance-statement-package>
        <header><div><small>CANONICAL FINANCIAL VIEW</small><h3>Business model · P&amp;L · Balance sheet · Cash flow</h3><p>Accepted accounting evidence wins over approximate onboarding answers. Every missing balance-sheet field remains visible.</p></div><span>${escapeHtml(profitAndLoss.period?.label || 'Period review required')}</span></header>
        <div class="aion-finance-statement-tabs">
          <section><h4>Profit &amp; loss</h4>${(profitAndLoss.lines || []).map((line) => `<div><span>${escapeHtml(line.label)}</span><strong>${line.value == null ? '—' : escapeHtml(formatFinanceValue(line.value, 'money', currency))}</strong><em>${escapeHtml((line.verification || '').replaceAll('_', ' '))}</em></div>`).join('')}</section>
          <section><h4>Balance sheet <em>${escapeHtml(balanceSheet.status || 'partial')}</em></h4><div class="aion-finance-statement-grid">${statementCard('Cash', balanceSheet.assets?.cash)}${statementCard('Receivables', balanceSheet.assets?.accounts_receivable)}${statementCard('Inventory', balanceSheet.assets?.inventory)}${statementCard('Payables', balanceSheet.liabilities?.accounts_payable)}${statementCard('Debt', balanceSheet.liabilities?.debt_commitments)}${statementCard('Equity', balanceSheet.equity)}</div>${(balanceSheet.missing_information || []).length ? `<details><summary>Information still needed to complete and balance this statement</summary><ul>${balanceSheet.missing_information.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></details>` : ''}</section>
          <section><h4>Cash flow <em>${escapeHtml(cashFlowStatement.status || 'partial')}</em></h4><div class="aion-finance-statement-grid">${statementCard('Opening cash', cashFlowStatement.opening_cash)}${statementCard('Cash collected', cashFlowStatement.cash_collections)}${statementCard('Cash paid', cashFlowStatement.cash_payments)}${statementCard('Net cash change', cashFlowStatement.net_cash_change)}${statementCard('Closing cash', cashFlowStatement.ending_cash)}${statementCard('Protected reserve', cashFlowStatement.protected_cash_reserve)}</div></section>
        </div>
        ${(statementQuality.warnings || []).length ? `<footer>${statementQuality.warnings.map((item) => `<span>${escapeHtml(item)}</span>`).join('')}</footer>` : ''}
      </section>` : '';
    return `<section class="aion-finance-director" data-aion-finance-director data-aion-finance-director-signature="${escapeHtml(signature)}">
      <header><strong>&gt; Finance Director · live model and transaction control</strong><span>Read-only · approval gated</span></header>
      ${statementPanel}
      <div class="aion-finance-director-actions">
        <button type="button" data-aion-finance-build-ledger>${ledger ? 'Rebuild ledger from latest Xero sync' : 'Build canonical transaction ledger'}</button>
        <label>Protected cash reserve <input type="number" min="0" step="0.01" value="${escapeHtml(director?.cash_flow?.protected_reserve || 0)}" data-aion-finance-director-reserve></label>
        <button type="button" data-aion-finance-refresh-director>Refresh Finance Director model</button>
        <button type="button" data-aion-finance-run-transaction-reconciliation ${ledger ? '' : 'disabled'}>Find transaction matches</button>
      </div>
      ${ledger ? `<div class="aion-finance-director-kpis">
        <article><small>Ledger records</small><strong>${Object.values(ledger.record_counts || {}).reduce((sum, value) => sum + Number(value || 0), 0)}</strong></article>
        <article><small>Receivables</small><strong>${escapeHtml(formatFinanceValue(ledger.summaries?.accounts_receivable, 'money', currency))}</strong></article>
        <article><small>Payables</small><strong>${escapeHtml(formatFinanceValue(ledger.summaries?.accounts_payable, 'money', currency))}</strong></article>
        <article><small>Overdue receivables</small><strong>${escapeHtml(formatFinanceValue(ledger.summaries?.overdue_receivables, 'money', currency))}</strong></article>
      </div><small>Source sync ${escapeHtml(ledger.source_sync_id)} · ${escapeHtml(ledger.ledger_hash)} · records are retrieved in bounded pages</small>` : '<p>No canonical ledger exists. Sync Xero, then build the ledger.</p>'}
      ${director ? `<div class="aion-finance-director-kpis">
        <article><small>Operating profit</small><strong>${escapeHtml(formatFinanceValue(director.profit_and_loss?.operating_profit, 'money', currency))}</strong></article>
        <article><small>Gross margin</small><strong>${escapeHtml(formatFinanceValue(director.profit_and_loss?.gross_margin_percent, 'percent', currency))}</strong></article>
        <article><small>Latest cash</small><strong>${escapeHtml(formatFinanceValue(director.cash_flow?.opening_or_latest_cash, 'money', currency))}</strong></article>
        <article><small>Estimated runway</small><strong>${director.cash_flow?.estimated_runway_months == null ? 'Not available' : `${escapeHtml(director.cash_flow.estimated_runway_months)} months`}</strong></article>
      </div>
      ${signals.length ? `<details open><summary>${signals.length} Finance Director signal${signals.length === 1 ? '' : 's'}</summary>${signals.map((signal) => `<article class="aion-finance-signal is-${escapeHtml(signal.severity)}"><strong>${escapeHtml(signal.title)}</strong><p>${escapeHtml(signal.recommendation)}</p><small>For ${escapeHtml((signal.target_departments || []).join(', '))} · requires review</small></article>`).join('')}</details>` : '<p>No proactive warning is currently supported by the available evidence.</p>'}
      ${proposals.length ? `<details><summary>${proposals.length} proposed Boardroom action${proposals.length === 1 ? '' : 's'}</summary>${proposals.map((proposal) => `<article class="aion-finance-director-proposal"><strong>${escapeHtml(proposal.title)}</strong><p>${escapeHtml(proposal.rationale)}</p><small>Target: ${escapeHtml(proposal.target_department)} · payload ${escapeHtml(proposal.payload_hash)} · not routed or executed</small></article>`).join('')}</details>` : ''}` : '<p>Refresh the Finance Director model to calculate the live operating view and proactive signals.</p>'}
      ${reconciliation ? `<details open><summary>Transaction reconciliation · ${Number(reconciliation.match_count || 0)} suggested matches · ${Number(reconciliation.exception_count || 0)} exceptions</summary>
        ${matches.map((match) => { const handoff = handoffFor(match.match_id); return `<article class="aion-finance-transaction-match"><div><strong>${escapeHtml(match.match_type.replaceAll('_', ' '))}</strong><span>${escapeHtml(match.confidence)} · ${Number(match.confidence_score || 0)}%</span></div><p>${escapeHtml((match.reasons || []).join(' · '))}</p><small>${escapeHtml(match.invoice?.invoice_number || match.invoice?.invoice_id || '')} · ${escapeHtml(match.payment?.payment_id || match.bank_transaction?.bank_transaction_id || '')}</small>
          ${match.review ? `<em>${escapeHtml(match.review.decision)} · provider not changed</em>${match.review.decision === 'accept_match' ? (handoff ? `<details><summary>Xero handoff · ${escapeHtml(handoff.status.replaceAll('_', ' '))}</summary><pre>${escapeHtml(JSON.stringify(handoff.payload, null, 2))}</pre><small>Exact payload hash: ${escapeHtml(handoff.payload_hash)}</small>${handoff.status === 'exact_approval_required' ? `<div><button type="button" data-aion-xero-handoff-decision="approve" data-handoff-id="${escapeHtml(handoff.handoff_id)}" data-payload-hash="${escapeHtml(handoff.payload_hash)}">Approve this exact handoff</button><button type="button" data-aion-xero-handoff-decision="reject" data-handoff-id="${escapeHtml(handoff.handoff_id)}">Reject</button></div>` : ''}${handoff.status === 'approved_manual_handoff' ? `<button type="button" data-aion-xero-handoff-receipt data-handoff-id="${escapeHtml(handoff.handoff_id)}">Create immutable limitation receipt</button>` : ''}${handoff.status === 'manual_xero_action_required' ? `<p>Complete this reconciliation in Xero Bank Rec or Cash Coding. The limitation receipt is stored in the Finance File Cabinet.</p>` : ''}</details>` : `<button type="button" data-aion-xero-handoff-prepare data-run-id="${escapeHtml(reconciliation.run_id)}" data-match-id="${escapeHtml(match.match_id)}">Prepare exact Xero handoff</button>`) : ''}` : `<div><button type="button" data-aion-transaction-match-review="accept_match" data-run-id="${escapeHtml(reconciliation.run_id)}" data-match-id="${escapeHtml(match.match_id)}">Accept draft match</button><button type="button" data-aion-transaction-match-review="reject_match" data-run-id="${escapeHtml(reconciliation.run_id)}" data-match-id="${escapeHtml(match.match_id)}">Reject</button><button type="button" data-aion-transaction-match-review="needs_investigation" data-run-id="${escapeHtml(reconciliation.run_id)}" data-match-id="${escapeHtml(match.match_id)}">Investigate</button></div>`}
        </article>`; }).join('')}
        ${classifications.length ? `<h4>Counterparty intelligence</h4>${classifications.map((item) => `<article class="aion-finance-counterparty-suggestion"><div><strong>${escapeHtml(item.counterparty || 'Unknown counterparty')}</strong><span>${escapeHtml(item.source.replaceAll('_', ' '))} · ${Math.round(Number(item.confidence || 0) * 100)}%</span></div><p>${escapeHtml(item.rationale || '')}</p><p>${item.suggested_account ? `Suggested account: <strong>${escapeHtml(item.suggested_account.code)} · ${escapeHtml(item.suggested_account.name)}</strong>` : escapeHtml(item.question_for_human || 'Finance needs a human classification.')}</p>
          ${item.review ? `<em>${escapeHtml(item.review.decision)} · reusable mappings only come from confirmed reviews</em>` : `<div>${item.suggested_account ? `<button type="button" data-aion-counterparty-classification-review="accept_mapping" data-run-id="${escapeHtml(reconciliation.run_id)}" data-suggestion-id="${escapeHtml(item.suggestion_id)}" data-account="${escapeHtml(JSON.stringify(item.suggested_account))}">Confirm and remember</button>` : ''}<button type="button" data-aion-counterparty-classification-review="reject_mapping" data-run-id="${escapeHtml(reconciliation.run_id)}" data-suggestion-id="${escapeHtml(item.suggestion_id)}">Reject</button><button type="button" data-aion-counterparty-classification-review="needs_clarification" data-run-id="${escapeHtml(reconciliation.run_id)}" data-suggestion-id="${escapeHtml(item.suggestion_id)}">Ask me</button></div>`}
        </article>`).join('')}` : ''}
        ${exceptions.length ? `<h4>Open exceptions</h4>${exceptions.map((item) => `<article class="aion-finance-exception"><strong>${escapeHtml(item.kind.replaceAll('_', ' '))}</strong><span>${escapeHtml(item.severity)}</span><pre>${escapeHtml(JSON.stringify(item.detail, null, 2))}</pre></article>`).join('')}` : ''}
        <small>AION may suggest a category, but only a confirmed human review creates reusable mapping memory. Accepting a match never posts a reconciliation or journal to Xero.</small>
      </details>` : '<p>No transaction matching run exists.</p>'}
    </section>`;
  }

  async function refreshFinanceDirector(terminal, stream, workspaceId) {
    if (!terminal || !stream || terminal.getAttribute('data-aion-pilot-role') !== 'finance') return null;
    const [ledgerPayload, directorPayload, transactionPayload, handoffPayload] = await Promise.all([
      financeLedger(workspaceId), financeDirector(workspaceId), financeTransactionReconciliation(workspaceId), financeXeroReconciliationHandoffs(workspaceId),
    ]);
    const signature = [ledgerPayload?.ledger?.ledger_hash, directorPayload?.finance_director?.director_model_hash, transactionPayload?.latest_transaction_reconciliation?.run_hash, ...(handoffPayload?.handoffs || []).map((item) => item.handoff_hash)].filter(Boolean).join('|') || 'empty';
    const current = stream.querySelector?.('[data-aion-finance-director]');
    if (current?.getAttribute?.('data-aion-finance-director-signature') !== signature) {
      current?.remove?.();
      const scenario = stream.querySelector?.('[data-aion-finance-scenario]');
      if (scenario) scenario.insertAdjacentHTML?.('beforebegin', financeDirectorPanel(ledgerPayload, directorPayload, transactionPayload, handoffPayload));
      else stream.insertAdjacentHTML?.('beforeend', financeDirectorPanel(ledgerPayload, directorPayload, transactionPayload, handoffPayload));
    }
    return { ledgerPayload, directorPayload, transactionPayload, handoffPayload };
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

  async function performVisibleQueueRefresh() {
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
        await refreshFinanceRecurring(terminal, stream, workspaceId);
        await refreshFinanceDirector(terminal, stream, workspaceId);
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

  function refreshVisibleQueue() {
    if (queueRefreshPromise) return queueRefreshPromise;
    const terminal = global.document?.querySelector?.('[data-aion-shared-pilot-terminal="true"]') || null;
    const departmentId = terminal?.getAttribute?.('data-aion-pilot-role') || '';
    const workspaceId = resolveBusinessId() || '';
    lastQueueRefreshKey = `${workspaceId}:${departmentId}`;
    lastQueueRefreshStartedAt = Date.now();
    queueRefreshPromise = performVisibleQueueRefresh().finally(() => {
      queueRefreshPromise = null;
    });
    return queueRefreshPromise;
  }

  function scheduleVisibleQueueRefresh() {
    const terminal = global.document?.querySelector?.('[data-aion-shared-pilot-terminal="true"]') || null;
    const departmentId = terminal?.getAttribute?.('data-aion-pilot-role') || '';
    const workspaceId = resolveBusinessId() || '';
    const refreshKey = `${workspaceId}:${departmentId}`;

    // The main view may replace the terminal element while preserving the
    // same workspace and department.  Treat that as a remount, not a reason
    // to immediately download the same finance surfaces again.
    if (
      refreshKey === lastQueueRefreshKey
      && Date.now() - lastQueueRefreshStartedAt < 30000
    ) {
      observedTerminal = terminal;
      observedDepartmentId = departmentId;
      observedWorkspaceId = workspaceId;
      return;
    }

    // The old observer scheduled a network refresh for every DOM mutation.
    // A refresh itself updates the terminal DOM, creating an unbounded
    // fetch -> render -> mutation -> fetch loop.  DOM observation is only
    // needed to notice that a different terminal/department was mounted.
    if (
      terminal === observedTerminal
      && departmentId === observedDepartmentId
      && workspaceId === observedWorkspaceId
    ) {
      return;
    }

    observedTerminal = terminal;
    observedDepartmentId = departmentId;
    observedWorkspaceId = workspaceId;

    global.clearTimeout?.(queueRefreshTimer);
    if (terminal && departmentId && workspaceId) {
      queueRefreshTimer = global.setTimeout?.(refreshVisibleQueue, 80);
    }
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

  function financeRecurringSchedules(workspaceId) {
    return request(`/finance-recurring?workspace_id=${encodeURIComponent(workspaceId)}`);
  }

  function createFinanceRecurringSchedule(workspaceId, kind, cadence, minimumCashReserve = 0) {
    return request(`/finance-recurring?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: 'POST', body: JSON.stringify({
        schedule_id: kind, kind, cadence, next_run_at: new Date().toISOString(),
        created_by: 'founder', minimum_cash_reserve: minimumCashReserve,
      }),
    });
  }

  function setFinanceRecurringEnabled(workspaceId, scheduleId, enabled) {
    return request(`/finance-recurring-enabled?workspace_id=${encodeURIComponent(workspaceId)}&schedule_id=${encodeURIComponent(scheduleId)}`, {
      method: 'POST', body: JSON.stringify({ enabled }),
    });
  }

  function runFinanceRecurring(workspaceId, scheduleId) {
    return request(`/finance-recurring-run?workspace_id=${encodeURIComponent(workspaceId)}&schedule_id=${encodeURIComponent(scheduleId)}`, {
      method: 'POST', body: JSON.stringify({ actor_id: 'founder', run_at: new Date().toISOString() }),
    });
  }

  function decideFinanceProposal(workspaceId, taskId, toolCallId, approved, payloadHash) {
    return request(`/${encodeURIComponent(workspaceId)}/finance/${encodeURIComponent(taskId)}/proposals/${encodeURIComponent(toolCallId)}/decision`, {
      method: 'POST', body: JSON.stringify({
        approval_id: `finance-approval-${toolCallId}-${Date.now()}`, approved,
        decided_by: 'founder', decided_payload_hash: approved ? payloadHash : null,
        decided_at: new Date().toISOString(),
      }),
    });
  }

  function retryDepartmentTask(workspaceId, departmentId, taskId) {
    return request(`/${encodeURIComponent(workspaceId)}/${encodeURIComponent(departmentId)}/${encodeURIComponent(taskId)}/retry`, {
      method: 'POST', body: JSON.stringify({ actor_id: 'founder', occurred_at: new Date().toISOString() }),
    });
  }

  function financeScenarios(workspaceId) {
    return request(`/finance-scenarios?workspace_id=${encodeURIComponent(workspaceId)}`);
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
    return request(`/finance-reconciliations?workspace_id=${encodeURIComponent(workspaceId)}`);
  }

  function financeLedger(workspaceId) {
    return request(`/finance-ledger?workspace_id=${encodeURIComponent(workspaceId)}`);
  }

  function buildFinanceLedger(workspaceId) {
    return request(`/finance-ledger-build?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: 'POST', body: JSON.stringify({ created_by: 'finance_pilot', created_at: new Date().toISOString() }),
    });
  }

  function financeDirector(workspaceId) {
    return request(`/finance-director?workspace_id=${encodeURIComponent(workspaceId)}`);
  }

  function refreshFinanceDirectorModel(workspaceId, minimumCashReserve) {
    return request(`/finance-director-refresh?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: 'POST', body: JSON.stringify({ minimum_cash_reserve: minimumCashReserve, created_by: 'finance_pilot', created_at: new Date().toISOString() }),
    });
  }

  function financeTransactionReconciliation(workspaceId) {
    return request(`/finance-transaction-reconciliation?workspace_id=${encodeURIComponent(workspaceId)}`);
  }

  function runFinanceTransactionReconciliation(workspaceId) {
    return request(`/finance-transaction-reconciliation-run?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: 'POST', body: JSON.stringify({ amount_tolerance_percent: 1, date_window_days: 7, classify_unmatched: true, created_by: 'finance_pilot', created_at: new Date().toISOString() }),
    });
  }

  function reviewFinanceTransactionMatch(workspaceId, runId, matchId, decision) {
    return request(`/finance-transaction-match-review?workspace_id=${encodeURIComponent(workspaceId)}&run_id=${encodeURIComponent(runId)}&match_id=${encodeURIComponent(matchId)}`, {
      method: 'POST', body: JSON.stringify({ decision, reviewed_by: 'founder', reviewed_at: new Date().toISOString() }),
    });
  }

  function reviewFinanceCounterpartyClassification(workspaceId, runId, suggestionId, decision, selectedAccount = null) {
    return request(`/finance-counterparty-classification-review?workspace_id=${encodeURIComponent(workspaceId)}&run_id=${encodeURIComponent(runId)}&suggestion_id=${encodeURIComponent(suggestionId)}`, {
      method: 'POST', body: JSON.stringify({ decision, reviewed_by: 'founder', selected_account: selectedAccount, reviewed_at: new Date().toISOString() }),
    });
  }

  function financeXeroReconciliationHandoffs(workspaceId) {
    return request(`/finance-xero-reconciliation-handoffs?workspace_id=${encodeURIComponent(workspaceId)}`);
  }

  function prepareFinanceXeroReconciliationHandoff(workspaceId, runId, matchId) {
    return request(`/finance-xero-reconciliation-handoff-prepare?workspace_id=${encodeURIComponent(workspaceId)}&run_id=${encodeURIComponent(runId)}&match_id=${encodeURIComponent(matchId)}`, {
      method: 'POST', body: JSON.stringify({ prepared_by: 'founder', prepared_at: new Date().toISOString() }),
    });
  }

  function decideFinanceXeroReconciliationHandoff(workspaceId, handoffId, approved, payloadHash = null) {
    return request(`/finance-xero-reconciliation-handoff-decision?workspace_id=${encodeURIComponent(workspaceId)}&handoff_id=${encodeURIComponent(handoffId)}`, {
      method: 'POST', body: JSON.stringify({ approved, decided_by: 'founder', decided_payload_hash: approved ? payloadHash : null }),
    });
  }

  function createFinanceXeroReconciliationReceipt(workspaceId, handoffId) {
    return request(`/finance-xero-reconciliation-handoff-execute?workspace_id=${encodeURIComponent(workspaceId)}&handoff_id=${encodeURIComponent(handoffId)}`, {
      method: 'POST', body: JSON.stringify({ attempted_by: 'founder', attempted_at: new Date().toISOString() }),
    });
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

  async function handleFinanceDirectorClick(event) {
    const build = event?.target?.closest?.('[data-aion-finance-build-ledger]');
    const refresh = event?.target?.closest?.('[data-aion-finance-refresh-director]');
    const reconcile = event?.target?.closest?.('[data-aion-finance-run-transaction-reconciliation]');
    const review = event?.target?.closest?.('[data-aion-transaction-match-review]');
    const classification = event?.target?.closest?.('[data-aion-counterparty-classification-review]');
    const handoffPrepare = event?.target?.closest?.('[data-aion-xero-handoff-prepare]');
    const handoffDecision = event?.target?.closest?.('[data-aion-xero-handoff-decision]');
    const handoffReceipt = event?.target?.closest?.('[data-aion-xero-handoff-receipt]');
    if (!build && !refresh && !reconcile && !review && !classification && !handoffPrepare && !handoffDecision && !handoffReceipt) return;
    const workspaceId = resolveBusinessId();
    const terminal = event.target.closest?.('[data-aion-shared-pilot-terminal="true"]');
    const stream = terminal?.querySelector?.('[data-aion-pilot-stream-window]');
    if (!workspaceId || !terminal || !stream || event.target.disabled) return;
    event.target.disabled = true;
    const original = event.target.textContent;
    try {
      if (build) {
        event.target.textContent = 'Building ledger…';
        await buildFinanceLedger(workspaceId);
      } else if (refresh) {
        event.target.textContent = 'Refreshing model…';
        const reserve = Number(terminal.querySelector?.('[data-aion-finance-director-reserve]')?.value || 0);
        await refreshFinanceDirectorModel(workspaceId, reserve);
      } else if (reconcile) {
        event.target.textContent = 'Matching transactions…';
        await runFinanceTransactionReconciliation(workspaceId);
      } else if (review) {
        event.target.textContent = 'Recording review…';
        await reviewFinanceTransactionMatch(workspaceId, review.getAttribute('data-run-id'), review.getAttribute('data-match-id'), review.getAttribute('data-aion-transaction-match-review'));
      } else if (classification) {
        event.target.textContent = 'Recording classification…';
        let account = null;
        try { account = classification.getAttribute('data-account') ? JSON.parse(classification.getAttribute('data-account')) : null; } catch (_) { account = null; }
        await reviewFinanceCounterpartyClassification(workspaceId, classification.getAttribute('data-run-id'), classification.getAttribute('data-suggestion-id'), classification.getAttribute('data-aion-counterparty-classification-review'), account);
      } else if (handoffPrepare) {
        event.target.textContent = 'Preparing exact payload…';
        await prepareFinanceXeroReconciliationHandoff(workspaceId, handoffPrepare.getAttribute('data-run-id'), handoffPrepare.getAttribute('data-match-id'));
      } else if (handoffDecision) {
        const approved = handoffDecision.getAttribute('data-aion-xero-handoff-decision') === 'approve';
        event.target.textContent = approved ? 'Recording exact approval…' : 'Rejecting handoff…';
        await decideFinanceXeroReconciliationHandoff(workspaceId, handoffDecision.getAttribute('data-handoff-id'), approved, handoffDecision.getAttribute('data-payload-hash'));
      } else if (handoffReceipt) {
        event.target.textContent = 'Creating receipt…';
        await createFinanceXeroReconciliationReceipt(workspaceId, handoffReceipt.getAttribute('data-handoff-id'));
      }
      await refreshFinanceDirector(terminal, stream, workspaceId);
    } catch (error) {
      event.target.disabled = false;
      event.target.textContent = original;
      stream.querySelector?.('[data-aion-finance-director-error]')?.remove?.();
      stream.insertAdjacentHTML?.('afterbegin', `<section class="aion-pilot-failure" data-aion-finance-director-error><strong>&gt; Finance Director action could not complete</strong><p>${escapeHtml(String(error?.message || error))}</p></section>`);
      console.error('[AION] Finance Director action failed', error);
    }
  }

  async function handleFinanceRecurringClick(event) {
    const create = event?.target?.closest?.('[data-aion-finance-schedule-create]');
    const run = event?.target?.closest?.('[data-aion-finance-schedule-run]');
    const enabled = event?.target?.closest?.('[data-aion-finance-schedule-enabled]');
    if (!create && !run && !enabled) return;
    const workspaceId = resolveBusinessId();
    const terminal = event.target.closest?.('[data-aion-shared-pilot-terminal="true"]');
    const stream = terminal?.querySelector?.('[data-aion-pilot-stream-window]');
    if (!workspaceId || !terminal || !stream || event.target.disabled) return;
    event.target.disabled = true;
    try {
      if (create) {
        const reserve = Number(terminal.querySelector?.('[data-aion-finance-schedule-reserve]')?.value || 0);
        await createFinanceRecurringSchedule(workspaceId, create.getAttribute('data-aion-finance-schedule-create'), create.getAttribute('data-cadence'), reserve);
      } else if (run) {
        await runFinanceRecurring(workspaceId, run.getAttribute('data-aion-finance-schedule-run'));
      } else {
        await setFinanceRecurringEnabled(workspaceId, enabled.getAttribute('data-aion-finance-schedule-enabled'), enabled.getAttribute('data-enabled') === 'true');
      }
      await refreshFinanceRecurring(terminal, stream, workspaceId);
    } catch (error) {
      event.target.disabled = false;
      console.error('[AION] Finance recurring work update failed', error);
    }
  }

  async function handleFinanceProposalDecision(event) {
    const button = event?.target?.closest?.('[data-aion-finance-proposal-decision]');
    if (!button || button.disabled) return;
    const workspaceId = resolveBusinessId();
    const approved = button.getAttribute('data-aion-finance-proposal-decision') === 'approve';
    button.disabled = true;
    try {
      await decideFinanceProposal(workspaceId, button.getAttribute('data-task-id'), button.getAttribute('data-tool-call-id'), approved, button.getAttribute('data-payload-hash'));
      await refreshVisibleQueue();
    } catch (error) {
      button.disabled = false;
      console.error('[AION] Exact Finance proposal decision failed', error);
    }
  }

  async function handleDepartmentTaskRetry(event) {
    const button = event?.target?.closest?.('[data-aion-department-task-retry]');
    if (!button || button.disabled) return;
    button.disabled = true;
    try {
      await retryDepartmentTask(resolveBusinessId(), button.getAttribute('data-department-id'), button.getAttribute('data-aion-department-task-retry'));
      await refreshVisibleQueue();
    } catch (error) {
      button.disabled = false;
      console.error('[AION] Department task retry failed', error);
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
    financeConversationSession,
    financeRecurringSchedules,
    createFinanceRecurringSchedule,
    setFinanceRecurringEnabled,
    runFinanceRecurring,
    decideFinanceProposal,
    retryDepartmentTask,
    askFinance,
    financeScenarios,
    runFinanceScenario,
    financeReconciliations,
    runFinanceReconciliation,
    reviewFinanceReconciliation,
    financeLedger,
    buildFinanceLedger,
    financeDirector,
    refreshFinanceDirectorModel,
    financeTransactionReconciliation,
    runFinanceTransactionReconciliation,
    reviewFinanceTransactionMatch,
    reviewFinanceCounterpartyClassification,
    financeXeroReconciliationHandoffs,
    prepareFinanceXeroReconciliationHandoff,
    decideFinanceXeroReconciliationHandoff,
    createFinanceXeroReconciliationReceipt,
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
    global.document.addEventListener('click', handleFinanceDirectorClick, true);
    global.document.addEventListener('click', handleFinanceRecurringClick, true);
    global.document.addEventListener('click', handleFinanceProposalDecision, true);
    global.document.addEventListener('click', handleDepartmentTaskRetry, true);
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
      .aion-finance-proposal{margin:12px 0 0;padding:12px;border:1px solid #f59e0b;background:#1c1917;color:#fde68a}.aion-finance-proposal strong{color:#fbbf24}.aion-finance-proposal pre{white-space:pre-wrap;overflow:auto;padding:10px;background:#07111f;color:#e2e8f0}.aion-finance-proposal button,.aion-pilot-failure button{margin:8px 8px 0 0;padding:8px 11px;border:1px solid #f59e0b;background:#292524;color:#fef3c7;cursor:pointer}
      .aion-finance-recurring{border:1px solid rgba(74,222,128,.5);background:#07111f;padding:14px;margin:0 0 16px;color:#cbd5e1}.aion-finance-recurring>header,.aion-finance-recurring article>div{display:flex;justify-content:space-between;gap:12px}.aion-finance-recurring>header{padding-bottom:10px;border-bottom:1px solid rgba(74,222,128,.25)}.aion-finance-recurring>header strong{color:#86efac}.aion-finance-recurring>header span,.aion-finance-recurring article span{color:#7dd3fc;text-transform:uppercase;font-size:11px}.aion-finance-recurring article{padding:10px 0;border-bottom:1px solid rgba(56,189,248,.18)}.aion-finance-recurring button{margin:8px 8px 0 0;padding:8px 11px;border:1px solid #4ade80;background:#052e1a;color:#dcfce7;cursor:pointer}.aion-finance-recurring input{margin:8px;padding:8px;background:#0f172a;border:1px solid #38bdf8;color:#f8fafc}.aion-finance-schedule-definitions{display:flex;gap:8px;flex-wrap:wrap}
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
      .aion-finance-director{border:1px solid rgba(74,222,128,.55);background:#07111f;padding:14px;margin:0 0 16px;color:#cbd5e1}.aion-finance-director>header{display:flex;justify-content:space-between;gap:16px;padding-bottom:10px;border-bottom:1px solid rgba(74,222,128,.25)}.aion-finance-director>header strong{color:#86efac}.aion-finance-director>header span{color:#7dd3fc;font-size:11px;letter-spacing:.1em;text-transform:uppercase}
      .aion-finance-director-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:end;margin:12px 0}.aion-finance-director-actions label{display:grid;gap:4px;color:#94a3b8;font-size:10px}.aion-finance-director-actions input{padding:8px;background:#0f172a;border:1px solid #38bdf8;color:#f8fafc}.aion-finance-director button{padding:8px 11px;border:1px solid #4ade80;background:#052e1a;color:#dcfce7;font-weight:700;cursor:pointer}.aion-finance-director button:disabled{opacity:.5;cursor:not-allowed}
      .aion-finance-director-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:8px;margin:10px 0}.aion-finance-director-kpis article{padding:10px;border:1px solid rgba(56,189,248,.25);background:#0f172a}.aion-finance-director-kpis small,.aion-finance-director-kpis strong{display:block}.aion-finance-director-kpis small{color:#94a3b8}.aion-finance-director-kpis strong{color:#f8fafc;font-size:17px;margin-top:5px}
      .aion-finance-signal,.aion-finance-director-proposal,.aion-finance-transaction-match,.aion-finance-counterparty-suggestion,.aion-finance-exception{padding:10px;margin:8px 0;border:1px solid rgba(56,189,248,.24);background:#0f172a}.aion-finance-signal.is-critical{border-color:#ef4444}.aion-finance-signal.is-high{border-color:#f59e0b}.aion-finance-signal strong,.aion-finance-director-proposal strong{color:#fbbf24}.aion-finance-transaction-match>div,.aion-finance-counterparty-suggestion>div,.aion-finance-exception{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.aion-finance-transaction-match>div strong,.aion-finance-counterparty-suggestion>div strong{color:#7dd3fc}.aion-finance-transaction-match>div span,.aion-finance-counterparty-suggestion>div span{color:#86efac}.aion-finance-transaction-match em,.aion-finance-counterparty-suggestion em{display:block;color:#86efac;font-style:normal}.aion-finance-exception pre{flex:1 0 100%;white-space:pre-wrap;color:#cbd5e1;background:#07111f;padding:8px}
      .aion-canonical-pilot-empty{margin:12px 0 0;color:#64748b}
      .aion-department-design-gate{border:1px solid #f59e0b;background:#1c1917;padding:14px;margin:0 0 16px;color:#fde68a}
      .aion-department-design-gate strong{color:#fbbf24}.aion-department-design-gate p{color:#d6d3d1}.aion-department-design-gate ul{margin:8px 0 0;padding-left:20px;color:#a8a29e}

      /* Finance light workspace: align the permanent Finance runtime with the
         Products & Services operating-model design system. */
      html body [data-aion-shared-pilot-terminal="true"][data-aion-pilot-role="finance"]{
        --fin-ink:#102a43;--fin-muted:#52667a;--fin-line:#cbd9e6;--fin-soft:#f5f9fc;
        --fin-blue:#0284c7;--fin-blue-soft:#edf8fc;--fin-teal:#0f766e;--fin-green:#15803d;
        background:#fff !important;color:var(--fin-ink) !important;border:1px solid var(--fin-line) !important;
        border-left:5px solid #0ea5e9 !important;box-shadow:none !important;
      }
      html body [data-aion-pilot-role="finance"] .aion-pilot-stream-header,
      html body [data-aion-pilot-role="finance"] .aion-shared-pilot-role-context,
      html body [data-aion-pilot-role="finance"] .aion-pilot-stream-window{
        background:#fff !important;color:var(--fin-ink) !important;border-color:var(--fin-line) !important;
      }
      html body [data-aion-pilot-role="finance"] .aion-pilot-stream-window{padding:18px 20px !important}
      html body [data-aion-pilot-role="finance"] h1,
      html body [data-aion-pilot-role="finance"] h2,
      html body [data-aion-pilot-role="finance"] h3,
      html body [data-aion-pilot-role="finance"] h4,
      html body [data-aion-pilot-role="finance"] strong{color:var(--fin-ink) !important}
      html body [data-aion-pilot-role="finance"] p,
      html body [data-aion-pilot-role="finance"] small{color:var(--fin-muted) !important}
      html body [data-aion-pilot-role="finance"] input,
      html body [data-aion-pilot-role="finance"] select,
      html body [data-aion-pilot-role="finance"] textarea{
        background:#fff !important;color:var(--fin-ink) !important;border:1px solid #b7c8d6 !important;
      }
      html body [data-aion-pilot-role="finance"] button{
        background:#fff !important;color:#0369a1 !important;border:1px solid #8fb3c7 !important;
        font-weight:800 !important;box-shadow:none !important;
      }
      html body [data-aion-pilot-role="finance"] button:hover{background:var(--fin-blue-soft) !important;border-color:#38a3c7 !important}
      html body [data-aion-pilot-role="finance"] button[data-aion-finance-refresh-director],
      html body [data-aion-pilot-role="finance"] button[data-aion-finance-run-task],
      html body [data-aion-pilot-role="finance"] button[type="submit"]{
        background:var(--fin-green) !important;border-color:var(--fin-green) !important;color:#fff !important;
      }
      html body [data-aion-pilot-role="finance"] .aion-canonical-pilot-queue,
      html body [data-aion-pilot-role="finance"] .aion-finance-recurring,
      html body [data-aion-pilot-role="finance"] .aion-finance-director,
      html body [data-aion-pilot-role="finance"] .aion-finance-scenario,
      html body [data-aion-pilot-role="finance"] .aion-finance-reconciliation,
      html body [data-aion-pilot-role="finance"] .aion-finance-conversation,
      html body [data-aion-pilot-role="finance"] .aion-finance-management-handback{
        background:#fff !important;color:var(--fin-ink) !important;border:1px solid var(--fin-line) !important;
        border-left:4px solid var(--fin-blue) !important;padding:18px !important;margin:0 0 18px !important;
      }
      html body [data-aion-pilot-role="finance"] .aion-canonical-pilot-queue>header,
      html body [data-aion-pilot-role="finance"] .aion-finance-recurring>header,
      html body [data-aion-pilot-role="finance"] .aion-finance-director>header,
      html body [data-aion-pilot-role="finance"] .aion-finance-scenario>header,
      html body [data-aion-pilot-role="finance"] .aion-finance-reconciliation>header,
      html body [data-aion-pilot-role="finance"] .aion-finance-conversation>header{
        border-color:var(--fin-line) !important;color:var(--fin-teal) !important;
      }
      html body [data-aion-pilot-role="finance"] .aion-finance-director-kpis article,
      html body [data-aion-pilot-role="finance"] .aion-finance-management-kpis article,
      html body [data-aion-pilot-role="finance"] .aion-finance-scenario-latest>span,
      html body [data-aion-pilot-role="finance"] .aion-finance-signal,
      html body [data-aion-pilot-role="finance"] .aion-finance-director-proposal,
      html body [data-aion-pilot-role="finance"] .aion-finance-transaction-match,
      html body [data-aion-pilot-role="finance"] .aion-finance-counterparty-suggestion,
      html body [data-aion-pilot-role="finance"] .aion-finance-conversation-turn{
        background:var(--fin-soft) !important;color:var(--fin-ink) !important;border-color:var(--fin-line) !important;
      }
      .aion-finance-statement-package{margin:18px 0;border:2px solid #f59e0b;background:#fff;color:var(--fin-ink)}
      .aion-finance-statement-package>header{display:flex;justify-content:space-between;gap:20px;padding:18px 20px;border-bottom:1px solid var(--fin-line)}
      .aion-finance-statement-package>header small{color:var(--fin-teal) !important;font-weight:900;letter-spacing:.22em}
      .aion-finance-statement-package>header h3{margin:6px 0 4px;font-family:Inter,system-ui,sans-serif}
      .aion-finance-statement-package>header p{margin:0}.aion-finance-statement-package>header>span{color:#0369a1;font-weight:900}
      .aion-finance-statement-tabs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;padding:16px;background:var(--fin-soft)}
      .aion-finance-statement-tabs>section{background:#fff;border:1px solid var(--fin-line);padding:15px}
      .aion-finance-statement-tabs h4{display:flex;justify-content:space-between;margin:0 0 12px;padding-bottom:9px;border-bottom:2px solid var(--fin-teal);text-transform:uppercase;letter-spacing:.08em}
      .aion-finance-statement-tabs h4 em{color:#0369a1;font-size:10px;font-style:normal}
      .aion-finance-statement-tabs>section>div:not(.aion-finance-statement-grid){display:grid;grid-template-columns:1fr auto;gap:3px 12px;padding:7px 0;border-bottom:1px solid #e1eaf0}
      .aion-finance-statement-tabs>section>div>em{grid-column:1/-1;color:#64748b;font-size:9px;font-style:normal}
      .aion-finance-statement-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
      .aion-finance-statement-grid article{background:var(--fin-soft);border:1px solid var(--fin-line);padding:10px}
      .aion-finance-statement-grid small,.aion-finance-statement-grid strong{display:block}.aion-finance-statement-grid strong{margin-top:5px}
      .aion-finance-statement-package details{margin-top:12px;color:#b45309}.aion-finance-statement-package footer{display:grid;gap:5px;padding:12px 16px;border-top:1px solid #f5c16c;background:#fffbeb;color:#92400e;font-size:11px}
      @media(max-width:1100px){.aion-finance-statement-tabs{grid-template-columns:1fr}.aion-finance-statement-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
    `;
    global.document.head.appendChild(style);
    const observer = new MutationObserver(scheduleVisibleQueueRefresh);
    observer.observe(global.document.documentElement, { childList: true, subtree: true });
    global.setTimeout?.(scheduleVisibleQueueRefresh, 700);
    global.setInterval?.(() => {
      if (global.document.querySelector('[data-aion-shared-pilot-terminal="true"]')) refreshVisibleQueue();
    }, 60000);
    refreshProfiles();
  }
})(window);
