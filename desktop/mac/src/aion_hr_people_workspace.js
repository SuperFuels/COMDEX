(function installAionHrPeopleWorkspace(global) {
  'use strict';

  const API_BASE = 'http://127.0.0.1:8080';
  const CAPABILITIES = [
    ['expenses.submit', 'Submit expenses'], ['expenses.read_own', 'View own expenses'],
    ['expenses.read_team', 'View team expenses'], ['expenses.read_all', 'View every expense'],
    ['expenses.approve', 'Approve expenses'], ['finance.read_summary', 'View Finance summary'],
    ['finance.read_transactions', 'View transaction detail'], ['finance.prepare', 'Prepare accounting work'],
    ['finance.approve_posting', 'Approve accounting posting'], ['boardroom.view_department', 'View department Boardroom'],
    ['boardroom.view_summary', 'View Boardroom summary'], ['boardroom.view_full', 'View full Boardroom'],
    ['people.manage', 'Manage people'], ['permissions.manage', 'Manage permissions'],
  ];
  const state = { workspaceId: '', model: null, templates: null, tab: 'people', personPage: 0, panel: null, saving: false, error: '', accessDecision: null, orgScale: 0.82, orgFullScale: 1, orgDraggingId: '', orgPositionDrag: null, orgPanDrag: null, orgFullPositions: {}, orgFullPositionsKey: '' };
  let scheduled = false;

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const id = (prefix) => `${prefix}.${Date.now().toString(36)}.${Math.random().toString(36).slice(2, 8)}`;
  const money = (value) => value === null || value === undefined || value === '' ? 'No limit' : `€${Number(value).toLocaleString()}`;

  function businessId() {
    return global.AionBusinessContainerClient?.resolveBusinessId?.() || '';
  }

  function founderDefaults() {
    try {
      const packet = JSON.parse(localStorage.getItem('aion.businessTwin.foundationPacket.v1') || '{}');
      const draft = packet.foundation_draft || packet.business || {};
      return {
        name: packet.founder_name || draft.founder_name || draft.owner_name || draft.owner || '',
        email: packet.primary_email || draft.primary_email || draft.owner_email || '',
      };
    } catch { return { name: '', email: '' }; }
  }

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
    if (!response.ok) throw new Error(await response.text() || `Request failed ${response.status}`);
    return response.json();
  }

  function host() {
    return document.querySelector(
      '[data-aion-hr-people-mount="true"], [data-aion-o18ad-department="hr"]',
    );
  }

  function personName(personId) {
    return state.model?.people?.find((item) => item.id === personId)?.name || 'Unassigned';
  }

  function departmentName(departmentId) {
    return state.model?.departments?.find((item) => item.id === departmentId)?.name || 'No department';
  }

  function roleName(roleId) {
    return state.model?.roles?.find((item) => item.id === roleId)?.name || roleId;
  }

  function employmentLabel(value) {
    return ({ owner: 'Owner / director', employee: 'Employee', self_employed: 'Self-employed', contractor: 'Contractor', freelancer: 'Freelancer', external_adviser: 'External adviser' })[value] || value;
  }

  function operations() {
    if (!state.model.people_operations) state.model.people_operations = { leave_requests: [], appraisals: [], escalations: [], onboarding_templates: [] };
    return state.model.people_operations;
  }

  function dateLabel(value) {
    if (!value) return 'Not scheduled';
    const parsed = new Date(`${String(value).slice(0, 10)}T12:00:00`);
    return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function onboardingProgress(person) {
    const checks = person.onboarding?.checks || {};
    const keys = ['contract', 'identity', 'health_safety', 'handbook', 'payroll', 'accounts', 'equipment'];
    const completed = keys.filter((key) => checks[key] === true).length;
    return { completed, total: keys.length, percent: Math.round((completed / keys.length) * 100) };
  }

  function layout(content) {
    const summary = state.model?.summary || {};
    return `
      <div class="hrw-shell" data-aion-hr-workspace>
        ${state.error ? `<div class="hrw-alert error">${esc(state.error)}</div>` : ''}
        <section class="hrw-metrics">
          <article><strong>${summary.active_people || 0}</strong><span>Active people</span></article>
          <article><strong>${summary.employees || 0}</strong><span>Employees</span></article>
          <article><strong>${summary.self_employed_and_contractors || 0}</strong><span>Self-employed / contractors</span></article>
          <article><strong>${summary.departments || 0}</strong><span>Departments</span></article>
          <article><strong>${summary.assigned_cards || 0}</strong><span>Assigned cards</span></article>
        </section>
        <nav class="hrw-tabs">
          ${[['people','People'],['operations','People operations'],['chart','Organisation chart'],['permissions','Roles & permissions'],['assets','Cards & assets'],['access','Access check']].map(([key,label]) => `<button data-hrw-tab="${key}" class="${state.tab === key ? 'active' : ''}">${label}</button>`).join('')}
        </nav>
        <main class="hrw-content">${content}</main>
        ${renderPanel()}
      </div>`;
  }

  function emptySetup() {
    return `<section class="hrw-empty">
      <span>START SIMPLE</span><h2>Who works in this business?</h2>
      <p>You do not need an HR system or an existing organisation chart. Add yourself, then add employees, self-employed people or contractors. Roles and access can be refined later.</p>
      <div class="hrw-actions">
        <button class="primary" data-hrw-add-person="owner">+ Add me as owner</button>
        <button data-hrw-add-person="employee">+ New employee</button>
        <button data-hrw-add-person="self_employed">+ New self-employed person</button>
      </div>
    </section>`;
  }

  function peopleView() {
    const people = state.model?.people || [];
    if (!people.length) return emptySetup();
    const pageSize = Number(host()?.getAttribute('data-aion-hr-directory-page-size') || 0);
    const paged = Number.isFinite(pageSize) && pageSize > 0;
    const pageCount = paged ? Math.max(1, Math.ceil(people.length / pageSize)) : 1;
    state.personPage = Math.max(0, Math.min(Number(state.personPage || 0), pageCount - 1));
    const visiblePeople = paged
      ? people.slice(state.personPage * pageSize, (state.personPage + 1) * pageSize)
      : people;
    return `<section>
      <div class="hrw-section-head hrw-people-head"><div><span>PEOPLE DIRECTORY</span><h2>Everyone who acts for the business</h2><p>Job titles describe work. Application roles separately control visibility and authority.</p></div>
        <div class="hrw-actions hrw-person-actions"><button data-hrw-add-person="employee">+ Employee</button><button data-hrw-add-person="self_employed">+ Self-employed</button><button data-hrw-add-person="contractor">+ Contractor</button></div></div>
      ${paged ? `<div class="hrw-directory-pagination"><span>Record ${state.personPage + 1} of ${people.length}</span><div><button data-hrw-person-prev ${state.personPage === 0 ? 'disabled' : ''}>Previous</button><button data-hrw-person-next ${state.personPage >= pageCount - 1 ? 'disabled' : ''}>Next</button></div></div>` : ''}
      <div class="hrw-people-grid">${visiblePeople.map((person) => `
        <article class="hrw-person ${person.status !== 'active' ? 'inactive' : ''}">
          <div class="hrw-avatar">${esc(person.name.split(/\s+/).map((part) => part[0]).slice(0,2).join('').toUpperCase())}</div>
          <div class="hrw-person-main"><div><strong>${esc(person.name)}</strong><em>${esc(person.status || 'active')}</em></div>
          <p>${esc(person.position_title || employmentLabel(person.employment_type))}</p><small>${esc(person.email || 'Email required')}${person.phone ? ` · ${esc(person.phone)}` : ''}</small></div>
          <dl><div><dt>Relationship</dt><dd>${esc(employmentLabel(person.employment_type))}</dd></div><div><dt>Manager</dt><dd>${esc(personName(person.manager_id))}</dd></div>
          <div><dt>Departments</dt><dd>${(person.department_ids || []).map(departmentName).map(esc).join(', ') || 'Unassigned'}</dd></div><div><dt>Access roles</dt><dd>${(person.role_ids || []).map(roleName).map(esc).join(', ') || 'None'}</dd></div></dl>
          <button data-hrw-edit-person="${esc(person.id)}">Edit person & authority</button>
        </article>`).join('')}</div>
    </section>`;
  }

  function operationsView() {
    const ledger = operations();
    const people = state.model?.people || [];
    const now = new Date();
    const horizon = new Date(now.getTime() + 14 * 86400000);
    const leave = (ledger.leave_requests || []).map((item) => ({ ...item, person_name: personName(item.person_id) }));
    const upcoming = leave.filter((item) => item.status === 'approved' && new Date(`${item.end_date}T23:59:59`) >= now && new Date(`${item.start_date}T00:00:00`) <= horizon).sort((a,b) => String(a.start_date).localeCompare(String(b.start_date)));
    const requested = leave.filter((item) => (item.status || 'requested') === 'requested');
    const recordedAppraisals = (ledger.appraisals || []).filter((item) => item.status !== 'completed');
    const recordedPeople = new Set(recordedAppraisals.map((item) => item.person_id));
    const appraisals = [...recordedAppraisals, ...people.filter((person) => person.next_appraisal_date && !recordedPeople.has(person.id)).map((person) => ({ person_id: person.id, due_date: person.next_appraisal_date, review_type: 'Appraisal / check-in', owner: personName(person.manager_id) }))].sort((a,b) => String(a.due_date).localeCompare(String(b.due_date)));
    const escalations = (ledger.escalations || []).filter((item) => !['resolved','closed'].includes(item.status || 'open'));
    const onboarding = people.filter((item) => item.status === 'active').map((person) => ({ person, progress: onboardingProgress(person) })).filter((item) => item.progress.completed < item.progress.total);
    return `<section class="hrw-operations">
      <div class="hrw-section-head"><div><span>PEOPLE OPERATIONS</span><h2>What needs attention next</h2><p>Upcoming absence, approvals, onboarding and review deadlines. Confidential case detail remains inside the authorised person record.</p></div><div class="hrw-actions"><button data-hrw-add-leave>+ Leave request</button><button data-hrw-add-escalation>+ Restricted issue</button></div></div>
      <div class="hrw-ops-metrics"><article><strong>${requested.length}</strong><span>Leave approvals</span></article><article><strong>${upcoming.length}</strong><span>Off in next 14 days</span></article><article><strong>${appraisals.length}</strong><span>Reviews due</span></article><article><strong>${onboarding.length}</strong><span>Onboarding incomplete</span></article><article><strong>${escalations.length}</strong><span>Restricted escalations</span></article></div>
      <div class="hrw-ops-grid">
        <section><header><strong>Upcoming absence and cover</strong><small>Next 14 days</small></header>${upcoming.length ? upcoming.map((item) => `<article><span><b>${esc(item.person_name)}</b><small>${esc(item.leave_type || 'Annual leave')} · ${esc(dateLabel(item.start_date))}–${esc(dateLabel(item.end_date))}</small></span><em>${esc(item.cover_owner || 'Cover not assigned')}</em></article>`).join('') : '<p class="hrw-muted">No approved absence is recorded for the next 14 days.</p>'}</section>
        <section><header><strong>Approval queue</strong><small>Human decision required</small></header>${requested.length ? requested.map((item) => `<article><span><b>${esc(item.person_name)}</b><small>${esc(dateLabel(item.start_date))}–${esc(dateLabel(item.end_date))}</small></span><button data-hrw-review-leave="${esc(item.id)}">Review</button></article>`).join('') : '<p class="hrw-muted">No leave request is waiting for approval.</p>'}</section>
        <section><header><strong>Appraisals and check-ins</strong><small>Scheduled reviews</small></header>${appraisals.length ? appraisals.map((item) => `<article><span><b>${esc(personName(item.person_id))}</b><small>${esc(item.review_type || 'Performance review')} · ${esc(dateLabel(item.due_date))}</small></span><em>${esc(item.owner || 'Manager')}</em></article>`).join('') : '<p class="hrw-muted">No appraisal or check-in deadline is recorded.</p>'}</section>
        <section><header><strong>Onboarding readiness</strong><small>Evidence checklist</small></header>${onboarding.length ? onboarding.map(({person,progress}) => `<article><span><b>${esc(person.name)}</b><small>${progress.completed}/${progress.total} verified · ${esc(person.email || 'work email missing')}</small></span><button data-hrw-review-person="${esc(person.id)}">Open</button></article>`).join('') : '<p class="hrw-muted">Every active person has a complete onboarding checklist.</p>'}</section>
      </div>
      <div class="hrw-policy"><b>Human authority boundary</b><p>Tessaris may remind, assemble evidence and recommend cover. Leave decisions, performance action, contract changes, disciplinary action, access grants and employee messages require an authorised person.</p></div>
    </section>`;
  }

  function organisationCanvasLayout(people, minimumWidth = 1040, minimumHeight = 540) {
    const byId = new Map(people.map((person) => [person.id, person]));
    const depthMemo = new Map();
    const depthOf = (person, trail = new Set()) => {
      if (depthMemo.has(person.id)) return depthMemo.get(person.id);
      if (!person.manager_id || !byId.has(person.manager_id) || trail.has(person.id)) return 0;
      const nextTrail = new Set(trail); nextTrail.add(person.id);
      const depth = Math.min(8, depthOf(byId.get(person.manager_id), nextTrail) + 1);
      depthMemo.set(person.id, depth);
      return depth;
    };
    const levels = new Map();
    people.forEach((person) => {
      const depth = depthOf(person);
      levels.set(depth, [...(levels.get(depth) || []), person]);
    });
    const maxAcross = Math.max(1, ...[...levels.values()].map((level) => level.length));
    const width = Math.max(minimumWidth, maxAcross * 230 + 100);
    const maxDepth = Math.max(0, ...levels.keys());
    const height = Math.max(minimumHeight, (maxDepth + 1) * 160 + 100);
    const positions = new Map();
    [...levels.entries()].sort(([a], [b]) => a - b).forEach(([depth, level]) => {
      const gap = width / (level.length + 1);
      level.sort((a, b) => String(a.name).localeCompare(String(b.name))).forEach((person, index) => {
        positions.set(person.id, { x: Math.round(gap * (index + 1) - 100), y: 55 + depth * 160 });
      });
    });
    return { width, height, positions, byId };
  }

  function reportsTo(personId, possibleManagerId) {
    const byId = new Map((state.model?.people || []).map((person) => [person.id, person]));
    let cursor = byId.get(possibleManagerId);
    const visited = new Set();
    while (cursor && !visited.has(cursor.id)) {
      if (cursor.manager_id === personId) return true;
      visited.add(cursor.id);
      cursor = byId.get(cursor.manager_id);
    }
    return false;
  }

  function chartView() {
    const people = (state.model?.people || []).filter((item) => item.status === 'active');
    const canvas = organisationCanvasLayout(people);
    const connectors = people.filter((person) => person.manager_id && canvas.positions.has(person.manager_id)).map((person) => {
      const child = canvas.positions.get(person.id); const manager = canvas.positions.get(person.manager_id);
      const startX = manager.x + 100; const startY = manager.y + 86; const endX = child.x + 100; const endY = child.y;
      const bend = Math.round((startY + endY) / 2);
      return `<path d="M ${startX} ${startY} C ${startX} ${bend}, ${endX} ${bend}, ${endX} ${endY}" />`;
    }).join('');
    const nodes = people.map((person) => {
      const point = canvas.positions.get(person.id);
      return `<article class="hrw-org-node" draggable="true" data-hrw-org-person="${esc(person.id)}" style="left:${point.x}px;top:${point.y}px">
        <div class="hrw-org-node-avatar">${esc(person.name.split(/\s+/).map((part) => part[0]).slice(0,2).join('').toUpperCase())}</div>
        <div><strong>${esc(person.name)}</strong><span>${esc(person.position_title || employmentLabel(person.employment_type))}</span><small>${person.manager_id ? `Reports to ${esc(personName(person.manager_id))}` : 'Top level'}</small></div>
        <button type="button" data-hrw-edit-person="${esc(person.id)}" aria-label="Open ${esc(person.name)}">•••</button>
      </article>`;
    }).join('');
    return `<section><div class="hrw-section-head hrw-org-heading"><div><span>REPORTING LINES</span><h2>Organisation canvas</h2><p>Drag a person onto another person to change who they report to. Drop them onto empty canvas space to make them top level.</p></div><div class="hrw-actions"><button data-hrw-standard-departments>Use standard departments</button></div></div>
      ${people.length ? `<div class="hrw-org-toolbar"><span>Move people to update reporting lines</span><div><button type="button" data-hrw-org-fullscreen>Open in Workflow Canvas ↗</button><button type="button" data-hrw-org-zoom="out" aria-label="Zoom out">−</button><strong>${Math.round(state.orgScale * 100)}%</strong><button type="button" data-hrw-org-zoom="in" aria-label="Zoom in">+</button><button type="button" data-hrw-org-zoom="reset">Fit</button></div></div><div class="hrw-org-viewport" data-hrw-org-root="true"><div class="hrw-org-stage" style="width:${canvas.width}px;height:${canvas.height}px;transform:scale(${state.orgScale})"><svg class="hrw-org-lines" viewBox="0 0 ${canvas.width} ${canvas.height}" aria-hidden="true">${connectors}</svg>${nodes}<div class="hrw-org-root-hint">Drop on empty space for top level</div></div></div>` : emptySetup()}
      <div class="hrw-departments"><div class="hrw-section-head compact"><div><h3>Departments and teams</h3></div><button data-hrw-add-department>+ Department</button></div>
      ${(state.model?.departments || []).length ? state.model.departments.map((item) => `<article><div><strong>${esc(item.name)}</strong><small>${item.parent_department_id ? `Reports into ${esc(departmentName(item.parent_department_id))}` : 'Top-level function'}</small></div><span>${state.model.people.filter((person) => (person.department_ids || []).includes(item.id) && person.status === 'active').length} people</span></article>`).join('') : '<p class="hrw-muted">No departments yet. For a very small team, people can remain business-wide.</p>'}</div>
    </section>`;
  }

  function roleColour(person) {
    const role = `${person.position_title || ''} ${employmentLabel(person.employment_type)}`.toLowerCase();
    if (/\b(ceo|chief executive|owner|director)\b/.test(role)) return '#7c3aed';
    if (/\b(coo|chief operating|operations?)\b/.test(role)) return '#2563eb';
    if (/\b(roof|roofer)\b/.test(role)) return '#d97706';
    if (/\b(account|accounts|accountant|finance|bookkeep|bookkeeper|payroll)\b/.test(role)) return '#059669';
    if (/\b(people|human resources|\bhr\b)\b/.test(role)) return '#db2777';
    if (/\b(sales|commercial)\b/.test(role)) return '#dc2626';
    if (/\b(marketing|brand)\b/.test(role)) return '#0891b2';
    if (/\b(contractor|self-employed|freelancer)\b/.test(role)) return '#475569';
    const palette = ['#4f46e5', '#0f766e', '#9333ea', '#be123c', '#0369a1', '#4d7c0f'];
    const seed = role.split('').reduce((total, char) => total + char.charCodeAt(0), 0);
    return palette[seed % palette.length];
  }

  function roleLabel(person) {
    const raw = String(person.position_title || employmentLabel(person.employment_type) || 'Team member').trim();
    const role = raw.toLowerCase();
    if (/\b(roof|roofer)\b/.test(role)) return 'Roofer';
    if (/\b(account|accounts|accountant|finance|bookkeep|bookkeeper|payroll)\b/.test(role)) return 'Accounts';
    if (/\b(people|human resources|\bhr\b)\b/.test(role)) return 'People';
    return raw;
  }

  function fullCanvasPositionKey() {
    return `aion.hr.organisationCanvas.positions.${state.workspaceId || 'default'}`;
  }

  function loadFullCanvasPositions() {
    try {
      const saved = JSON.parse(global.localStorage?.getItem(fullCanvasPositionKey()) || '{}');
      state.orgFullPositions = saved && typeof saved === 'object' ? saved : {};
      state.orgFullPositionsKey = fullCanvasPositionKey();
    } catch { state.orgFullPositions = {}; }
  }

  function saveFullCanvasPositions() {
    try { global.localStorage?.setItem(fullCanvasPositionKey(), JSON.stringify(state.orgFullPositions || {})); } catch {}
  }

  function redrawFullCanvasLines(root) {
    if (!root) return;
    root.querySelectorAll('[data-hrw-org-child]').forEach((path) => {
      const child = root.querySelector(`[data-hrw-org-person="${CSS.escape(path.dataset.hrwOrgChild || '')}"]`);
      const manager = root.querySelector(`[data-hrw-org-person="${CSS.escape(path.dataset.hrwOrgManager || '')}"]`);
      if (!child || !manager) return;
      const childX = Number.parseFloat(child.style.left || '0');
      const childY = Number.parseFloat(child.style.top || '0');
      const managerX = Number.parseFloat(manager.style.left || '0');
      const managerY = Number.parseFloat(manager.style.top || '0');
      const startX = managerX + 100; const startY = managerY + 86;
      const endX = childX + 100; const endY = childY;
      const bend = Math.round((startY + endY) / 2);
      path.setAttribute('d', `M ${startX} ${startY} C ${startX} ${bend}, ${endX} ${bend}, ${endX} ${endY}`);
    });
  }

  function renderFullCanvas() {
    const people = (state.model?.people || []).filter((item) => item.status === 'active');
    const canvas = organisationCanvasLayout(people, 1700, 900);
    if (state.orgFullPositionsKey !== fullCanvasPositionKey()) loadFullCanvasPositions();
    people.forEach((person) => {
      const saved = state.orgFullPositions?.[person.id];
      if (saved && Number.isFinite(Number(saved.x)) && Number.isFinite(Number(saved.y))) {
        canvas.positions.set(person.id, { x: Number(saved.x), y: Number(saved.y) });
      }
    });
    const connectors = people.filter((person) => person.manager_id && canvas.positions.has(person.manager_id)).map((person) => {
      const child = canvas.positions.get(person.id); const manager = canvas.positions.get(person.manager_id);
      const startX = manager.x + 100; const startY = manager.y + 86; const endX = child.x + 100; const endY = child.y;
      const bend = Math.round((startY + endY) / 2);
      return `<path data-hrw-org-child="${esc(person.id)}" data-hrw-org-manager="${esc(person.manager_id)}" d="M ${startX} ${startY} C ${startX} ${bend}, ${endX} ${bend}, ${endX} ${endY}" />`;
    }).join('');
    const nodes = people.map((person) => {
      const point = canvas.positions.get(person.id);
      return `<article class="aion-full-org-node" data-hrw-org-person="${esc(person.id)}" data-hrw-org-manager="${esc(person.manager_id || '')}" style="left:${point.x}px;top:${point.y}px">
        <div class="aion-full-org-rolebar" style="background:${roleColour(person)}"><span>${esc(roleLabel(person))}</span></div>
        <div class="aion-full-org-avatar">${esc(person.name.split(/\s+/).map((part) => part[0]).slice(0,2).join('').toUpperCase())}</div>
        <div><strong>${esc(person.name)}</strong><span>${esc(person.position_title || employmentLabel(person.employment_type))}</span><small>${person.manager_id ? `Reports to ${esc(personName(person.manager_id))}` : 'Top level'}</small></div>
      </article>`;
    }).join('');
    return `<style>
      .aion-full-org-shell{height:calc(100vh - 124px);min-height:620px;margin:38px 0 0 76px;width:calc(100% - 76px);background:#edf2f7;color:#102a43;display:flex;flex-direction:column;overflow:hidden}.aion-full-org-topbar{height:70px;flex:0 0 70px;display:flex;align-items:center;justify-content:space-between;gap:20px;padding:0 24px;border-bottom:1px solid #cbd5e1;background:#fff}.aion-full-org-title{margin-left:12px}.aion-full-org-title small{display:block;color:#0f766e;font-size:10px;font-weight:900;letter-spacing:.22em}.aion-full-org-title h2{margin:5px 0 0;font-size:22px}.aion-full-org-actions{display:flex;align-items:center;gap:7px}.aion-full-org-actions button{border:1px solid #94a3b8;background:#fff;color:#334e68;padding:8px 11px;font-weight:850;cursor:pointer}.aion-full-org-actions button:hover{border-color:#0f766e;color:#0f766e}.aion-full-org-actions strong{min-width:48px;text-align:center;font-size:12px}.aion-full-org-help{padding:8px 24px 8px 36px;border-bottom:1px solid #d7e0ea;background:#f8fafc;color:#64748b;font-size:12px}.aion-full-org-viewport{position:relative;flex:1;min-height:0;overflow:auto;cursor:grab;overscroll-behavior:contain;background-color:#f8fafc;background-image:linear-gradient(#e3eaf2 1px,transparent 1px),linear-gradient(90deg,#e3eaf2 1px,transparent 1px);background-size:24px 24px}.aion-full-org-viewport.hrw-canvas-panning{cursor:grabbing}.aion-full-org-stage-space{position:relative;display:block}.aion-full-org-stage{position:relative;display:block;margin-left:72px;transform-origin:0 0;transition:transform .15s ease}.aion-full-org-lines{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.aion-full-org-lines path{fill:none;stroke:#7890a8;stroke-width:2.5}.aion-full-org-node{position:absolute;width:200px;height:86px;display:grid;grid-template-columns:42px 1fr;align-items:center;gap:11px;background:#fff;border:1px solid #7dd3fc;border-top:4px solid #0f766e;padding:12px;box-shadow:0 6px 18px rgba(15,23,42,.1);cursor:grab;user-select:none;touch-action:none}.aion-full-org-node:active{cursor:grabbing}.aion-full-org-node.hrw-position-dragging{z-index:5;box-shadow:0 12px 28px rgba(15,23,42,.2)}.aion-full-org-rolebar{position:absolute;left:-1px;right:-1px;top:-23px;height:18px;padding:0 8px;display:flex;align-items:center;border-radius:4px 4px 0 0;color:#fff;font-size:8px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;box-shadow:0 2px 5px rgba(15,23,42,.12)}.aion-full-org-rolebar span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.aion-full-org-node.hrw-dragging{opacity:.42}.aion-full-org-node.hrw-drop-target{outline:4px solid #2dd4bf;outline-offset:4px}.aion-full-org-avatar{width:40px;height:40px;display:grid;place-items:center;background:#dbeafe;border:1px solid #7dd3fc;color:#075985;font-size:12px;font-weight:900}.aion-full-org-node strong,.aion-full-org-node>div:not(.aion-full-org-rolebar)>span,.aion-full-org-node small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.aion-full-org-node strong{font-size:13px}.aion-full-org-node>div:not(.aion-full-org-rolebar)>span{font-size:11px;color:#334e68;margin:3px 0}.aion-full-org-node small{font-size:9px;color:#64748b}.aion-full-org-root-hint{position:absolute;z-index:4;left:50%;top:24px;transform:translateX(-50%);min-width:330px;border:2px dashed #0f766e;background:rgba(240,253,250,.96);color:#115e59;padding:12px 18px;text-align:center;font-size:11px;font-weight:900;letter-spacing:.02em;box-shadow:0 5px 14px rgba(15,118,110,.1)}.aion-full-org-root-hint.hrw-drop-target{border-style:solid;background:#99f6e4;color:#134e4a;box-shadow:0 8px 22px rgba(15,118,110,.24)}
    </style><section class="aion-full-org-shell" data-aion-full-org-canvas="true"><header class="aion-full-org-topbar"><div class="aion-full-org-title"><small>PEOPLE · REPORTING LINES</small><h2>Organisation canvas</h2></div><div class="aion-full-org-actions"><button type="button" data-hrw-full-org-close>Back to People</button><button type="button" data-hrw-full-org-zoom="out" aria-label="Zoom out">−</button><strong data-hrw-full-org-scale>${Math.round(state.orgFullScale * 100)}%</strong><button type="button" data-hrw-full-org-zoom="in" aria-label="Zoom in">+</button><button type="button" data-hrw-full-org-zoom="reset">Fit</button></div></header><div class="aion-full-org-help">Drag onto another person to change manager. Drag empty canvas space to move around, pinch to zoom, or use the top-centre target to start a separate tree.</div><main class="aion-full-org-viewport" data-hrw-org-root="true"><div class="aion-full-org-stage-space" style="width:${Math.round((canvas.width * state.orgFullScale) + 72)}px;height:${Math.round(canvas.height * state.orgFullScale)}px" data-base-width="${canvas.width}" data-base-height="${canvas.height}"><div class="aion-full-org-stage" style="width:${canvas.width}px;height:${canvas.height}px;transform:scale(${state.orgFullScale})"><svg class="aion-full-org-lines" viewBox="0 0 ${canvas.width} ${canvas.height}" aria-hidden="true">${connectors}</svg>${nodes}<div class="aion-full-org-root-hint" data-hrw-org-make-top-level="true">Drop here to start a new tree · Disconnect from current manager</div></div></div></main></section>`;
  }

  function permissionsView() {
    return `<section><div class="hrw-section-head"><div><span>LEAST PRIVILEGE</span><h2>Roles and permissions</h2><p>Assign these roles to people. A position title alone never grants access.</p></div></div>
      <div class="hrw-role-grid">${(state.model?.roles || []).map((role) => `<article><header><strong>${esc(role.name)}</strong><span>${esc(role.scope || 'self')}</span></header><p>${esc(role.description || '')}</p><div>${(role.capabilities || []).map((item) => `<small>${esc(CAPABILITIES.find(([key]) => key === item)?.[1] || item)}</small>`).join('')}</div><footer>Expense approval: <b>${money(role.approval_limit)}</b></footer></article>`).join('')}</div>
      <div class="hrw-policy"><b>Built-in protection</b><p>Deny by default · job titles do not grant access · exact external actions require approval · sensitive payroll and medical records are excluded from this model.</p></div>
    </section>`;
  }

  function assetsView() {
    const assets = state.model?.assets || [];
    return `<section><div class="hrw-section-head"><div><span>RESPONSIBILITY</span><h2>Company cards and accountable assets</h2><p>Connect each card or asset to the person responsible for it. Full card numbers are never stored here.</p></div><button data-hrw-add-asset>+ Card or asset</button></div>
      ${assets.length ? `<div class="hrw-assets">${assets.map((asset) => `<article><div class="hrw-asset-icon">${asset.asset_type === 'company_card' ? 'CARD' : 'ASSET'}</div><div><strong>${esc(asset.name)}</strong><p>${esc(personName(asset.assigned_person_id))} · ${esc(asset.asset_type.replaceAll('_',' '))}${asset.last_four ? ` · •••• ${esc(asset.last_four)}` : ''}</p><small>Per transaction ${money(asset.transaction_limit)} · Monthly ${money(asset.monthly_limit)}</small></div><button data-hrw-edit-asset="${esc(asset.id)}">Edit</button></article>`).join('')}</div>` : '<div class="hrw-empty small"><h2>No cards or assets assigned</h2><p>Add them when employees use business cards, vehicles, tools, devices or financial accounts.</p></div>'}
    </section>`;
  }

  function accessView() {
    const people = (state.model?.people || []).filter((item) => item.status === 'active');
    return `<section><div class="hrw-section-head"><div><span>AUTHORITY EXPLAINED</span><h2>Check what someone can do</h2><p>This uses the same decision contract Finance and the Boardroom can call before revealing data or performing work.</p></div></div>
      <form class="hrw-access-form" data-hrw-access-form>
        <label>Person<select name="person_id" required><option value="">Select person</option>${people.map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label>
        <label>Requested access<select name="capability">${CAPABILITIES.map(([key,label]) => `<option value="${key}">${esc(label)}</option>`).join('')}</select></label>
        <label>Department<select name="department_id"><option value="">Business / not applicable</option>${(state.model?.departments || []).map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label>
        <label>Amount, if approving<input name="amount" type="number" min="0" step="0.01" placeholder="Optional"></label>
        <button class="primary" type="submit">Check authority</button>
      </form>
      ${state.accessDecision ? `<article class="hrw-decision ${state.accessDecision.allowed ? 'allowed' : 'denied'}"><strong>${state.accessDecision.allowed ? 'ALLOWED' : 'NOT ALLOWED'}</strong><p>${esc(state.accessDecision.reason.replaceAll('_',' '))}</p>${state.accessDecision.approval_limit !== null && state.accessDecision.approval_limit !== undefined ? `<small>Maximum approval: ${money(state.accessDecision.approval_limit)}</small>` : ''}</article>` : ''}
    </section>`;
  }

  function renderPanel() {
    if (!state.panel) return '';
    const panel = state.panel;
    if (panel.type === 'person') {
      const founder = panel.employmentType === 'owner' ? founderDefaults() : { name: '', email: '' };
      const initialPerson = panel.item || { id: id('person'), name: founder.name, email: founder.email, employment_type: panel.employmentType || 'employee', position_title: panel.employmentType === 'owner' ? 'Managing Director' : '', status: 'active', manager_id: null, department_ids: [], role_ids: [] };
      if (!panel.draft) panel.draft = clone(initialPerson);
      const person = panel.draft;
      const defaultRole = person.employment_type === 'owner' ? 'role.owner_director' : ['self_employed','contractor','freelancer'].includes(person.employment_type) ? 'role.self_employed_contractor' : 'role.employee';
      const selectedRoles = new Set(person.role_ids?.length ? person.role_ids : [defaultRole]);
      return `<aside class="hrw-panel"><form data-hrw-person-form data-person-id="${esc(person.id)}"><header><div><span>${panel.item ? 'EDIT PERSON' : 'ADD PERSON'}</span><h2>${panel.item ? esc(person.name) : 'Who are you adding?'}</h2></div><button type="button" data-hrw-close>×</button></header>
        <label>Full name<input name="name" value="${esc(person.name)}" required autofocus></label>
        <label>Work email<input name="email" type="email" value="${esc(person.email || '')}" placeholder="name@business.com"></label>
        <div class="hrw-two"><label>Mobile or phone<input name="phone" value="${esc(person.phone || '')}" placeholder="Work contact number"></label><label>Address<input name="address" value="${esc(person.address || '')}" placeholder="Home or work address"></label></div>
        <div class="hrw-two"><label>Relationship<select name="employment_type">${[['owner','Owner / director'],['employee','Employee'],['self_employed','Self-employed person'],['contractor','Contractor'],['freelancer','Freelancer'],['external_adviser','External adviser']].map(([key,label]) => `<option value="${key}" ${person.employment_type === key ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
        <label>Position / job title<input name="position_title" value="${esc(person.position_title || '')}" placeholder="e.g. Operations Manager"></label></div>
        <label>Reports to<select name="manager_id"><option value="">No manager / top level</option>${(state.model.people || []).filter((item) => item.id !== person.id && item.status === 'active').map((item) => `<option value="${esc(item.id)}" ${person.manager_id === item.id ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}</select></label>
        <fieldset><legend>Departments</legend><div class="hrw-checks">${(state.model.departments || []).map((item) => `<label><input type="checkbox" name="department_ids" value="${esc(item.id)}" ${(person.department_ids || []).includes(item.id) ? 'checked' : ''}>${esc(item.name)}</label>`).join('') || '<small>Add departments later if the business is still very small.</small>'}</div></fieldset>
        <fieldset><legend>Application roles</legend><div class="hrw-checks">${(state.model.roles || []).map((role) => `<label><input type="checkbox" name="role_ids" value="${esc(role.id)}" ${selectedRoles.has(role.id) ? 'checked' : ''}><span><b>${esc(role.name)}</b><small>${esc(role.description || '')}</small></span></label>`).join('')}</div></fieldset>
        <div class="hrw-two"><label>Work location<input name="work_location" value="${esc(person.work_location || '')}" placeholder="Office, remote, site"></label><label>Cost centre<input name="cost_center" value="${esc(person.cost_center || '')}" placeholder="Optional"></label></div>
        <div class="hrw-two"><label>Start date<input name="start_date" type="date" value="${esc(person.start_date || '')}"></label><label>Next appraisal / check-in<input name="next_appraisal_date" type="date" value="${esc(person.next_appraisal_date || '')}"></label></div>
        <fieldset><legend>Onboarding evidence</legend><p>Mark only items that are actually complete or verified.</p><div class="hrw-checks">${[['contract','Contract signed'],['identity','Identity / right-to-work'],['health_safety','Health & safety'],['handbook','Handbook / induction'],['payroll','Payroll details'],['accounts','Software accounts'],['equipment','Equipment / assets']].map(([key,label]) => `<label><input type="checkbox" name="onboarding_checks" value="${key}" ${person.onboarding?.checks?.[key] === true ? 'checked' : ''}>${label}</label>`).join('')}</div></fieldset>
        <label>Allocated software accounts<textarea name="software_accounts" rows="3" placeholder="One system or account per line">${esc((person.software_accounts || []).join('\n'))}</textarea></label>
        <fieldset class="hrw-costing"><legend>Confidential workforce costing</legend>
          <p>Used by Finance and job profitability calculations. Individual pay is not copied into the general Business Map.</p>
          <div class="hrw-two"><label>Pay / cost basis<select name="workforce_costing_basis">${[['hourly','Hourly'],['daily','Daily'],['monthly','Monthly salary / cost'],['per_job','Per job']].map(([key,label]) => `<option value="${key}" ${(person.workforce_costing?.basis || 'hourly') === key ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
          <label>Base rate or salary<input name="workforce_costing_base_rate" type="number" min="0" step="0.01" value="${person.workforce_costing?.base_rate ?? ''}" placeholder="Confidential"></label></div>
          <div class="hrw-two"><label>Employer on-cost %<input name="workforce_costing_employer_on_cost_percent" type="number" min="0" step="0.01" value="${person.workforce_costing?.employer_on_cost_percent ?? ''}" placeholder="Tax, pension, leave burden"></label>
          <label>Monthly bonus / allowance<input name="workforce_costing_monthly_bonus" type="number" min="0" step="0.01" value="${person.workforce_costing?.monthly_bonus ?? ''}"></label></div>
          <div class="hrw-two"><label>Commission %<input name="workforce_costing_commission_percent" type="number" min="0" step="0.01" value="${person.workforce_costing?.commission_percent ?? ''}"></label>
          <label>Productive hours / month<input name="workforce_costing_productive_hours_month" type="number" min="1" step="0.5" value="${person.workforce_costing?.productive_hours_month ?? 140}"></label></div>
          <label>Hours per working day<input name="workforce_costing_hours_per_day" type="number" min="1" max="24" step="0.25" value="${person.workforce_costing?.hours_per_day ?? 8}"></label>
          ${person.workforce_costing?.effective_hourly_cost ? `<small>Current effective planning cost: ${money(person.workforce_costing.effective_hourly_cost)} per hour · ${money(person.workforce_costing.effective_daily_cost)} per day.</small>` : '<small>Add known costs now or leave blank until payroll/contractor evidence is available.</small>'}
        </fieldset>
        <label>Personal expense approval limit<input name="expense_approval_limit" type="number" min="0" step="0.01" value="${person.expense_approval_limit ?? ''}" placeholder="Uses role limit when blank"></label>
        <footer>${panel.item && person.status === 'active' ? '<button type="button" class="danger" data-hrw-deactivate-person>Deactivate</button>' : ''}<button type="button" data-hrw-close>Cancel</button><button class="primary" type="submit">Save person</button></footer>
      </form></aside>`;
    }
    if (panel.type === 'department') {
      return `<aside class="hrw-panel"><form data-hrw-department-form><header><div><span>ADD DEPARTMENT</span><h2>Create a team or function</h2></div><button type="button" data-hrw-close>×</button></header><label>Name<input name="name" required autofocus placeholder="Operations"></label><label>Reports into<select name="parent_department_id"><option value="">Top level</option>${(state.model.departments || []).map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label><footer><button type="button" data-hrw-close>Cancel</button><button class="primary" type="submit">Add department</button></footer></form></aside>`;
    }
    if (panel.type === 'asset') {
      const asset = panel.item || { id: id('asset'), asset_type: 'company_card', name: '', assigned_person_id: '', last_four: '', transaction_limit: '', monthly_limit: '', status: 'active' };
      return `<aside class="hrw-panel"><form data-hrw-asset-form data-asset-id="${esc(asset.id)}"><header><div><span>${panel.item ? 'EDIT ASSET' : 'ADD ASSET'}</span><h2>Assign responsibility</h2></div><button type="button" data-hrw-close>×</button></header><label>Name<input name="name" value="${esc(asset.name)}" required placeholder="Operations company card"></label><label>Type<select name="asset_type">${[['company_card','Company card'],['vehicle','Vehicle'],['tool','Tool or equipment'],['device','Computer or phone'],['financial_account','Financial account'],['other','Other']].map(([key,label]) => `<option value="${key}" ${asset.asset_type === key ? 'selected' : ''}>${label}</option>`).join('')}</select></label><label>Responsible person<select name="assigned_person_id"><option value="">Unassigned</option>${(state.model.people || []).filter((item) => item.status === 'active').map((item) => `<option value="${esc(item.id)}" ${asset.assigned_person_id === item.id ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}</select></label><label>Last four digits only<input name="last_four" inputmode="numeric" maxlength="4" value="${esc(asset.last_four || '')}" placeholder="1234"></label><div class="hrw-two"><label>Transaction limit<input name="transaction_limit" type="number" min="0" step="0.01" value="${asset.transaction_limit ?? ''}"></label><label>Monthly limit<input name="monthly_limit" type="number" min="0" step="0.01" value="${asset.monthly_limit ?? ''}"></label></div><footer><button type="button" data-hrw-close>Cancel</button><button class="primary" type="submit">Save asset</button></footer></form></aside>`;
    }
    if (panel.type === 'leave') {
      const leave = panel.item || { id: id('leave'), person_id: '', leave_type: 'Annual leave', start_date: '', end_date: '', cover_owner: '', status: 'requested' };
      return `<aside class="hrw-panel"><form data-hrw-leave-form data-leave-id="${esc(leave.id)}"><header><div><span>LEAVE REQUEST</span><h2>${panel.item ? 'Review time away' : 'Record time away'}</h2></div><button type="button" data-hrw-close>×</button></header><label>Person<select name="person_id" required><option value="">Select person</option>${(state.model.people || []).filter((item) => item.status === 'active').map((item) => `<option value="${esc(item.id)}" ${leave.person_id === item.id ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}</select></label><label>Leave type<select name="leave_type">${['Annual leave','Other approved absence','Private / restricted absence'].map((label) => `<option ${leave.leave_type === label ? 'selected' : ''}>${label}</option>`).join('')}</select></label><div class="hrw-two"><label>Start<input name="start_date" type="date" required value="${esc(leave.start_date)}"></label><label>End<input name="end_date" type="date" required value="${esc(leave.end_date)}"></label></div><label>Cover owner<input name="cover_owner" value="${esc(leave.cover_owner || '')}" placeholder="Who will cover essential work?"></label><label>Status<select name="status"><option value="requested" ${leave.status === 'requested' ? 'selected' : ''}>Requested — needs approval</option><option value="approved" ${leave.status === 'approved' ? 'selected' : ''}>Approved by authorised person</option><option value="declined" ${leave.status === 'declined' ? 'selected' : ''}>Declined</option></select></label><footer><button type="button" data-hrw-close>Cancel</button><button class="primary" type="submit">Save human decision</button></footer></form></aside>`;
    }
    if (panel.type === 'escalation') {
      return `<aside class="hrw-panel"><form data-hrw-escalation-form><header><div><span>RESTRICTED PEOPLE ISSUE</span><h2>Record an escalation</h2></div><button type="button" data-hrw-close>×</button></header><label>Person<select name="person_id" required><option value="">Select person</option>${(state.model.people || []).filter((item) => item.status === 'active').map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label><label>Category<select name="category"><option value="employee_request">Employee request</option><option value="wellbeing">Wellbeing / welfare</option><option value="performance">Performance concern</option><option value="conduct">Conduct concern</option><option value="safety">Safety concern</option><option value="other">Other restricted issue</option></select></label><label>Dashboard-safe title<input name="title" required placeholder="Brief neutral description — no medical or sensitive detail"></label><label>Accountable owner<input name="owner" required placeholder="Authorised manager or People lead"></label><label>Review due<input name="due_date" type="date"></label><footer><button type="button" data-hrw-close>Cancel</button><button class="primary" type="submit">Save restricted flag</button></footer></form></aside>`;
    }
    return '';
  }

  function view() {
    if (!state.model) return '<div class="hrw-loading">Loading organisation…</div>';
    return layout(({ people: peopleView, operations: operationsView, chart: chartView, permissions: permissionsView, assets: assetsView, access: accessView })[state.tab]());
  }

  function render() {
    const target = host();
    if (!target) return;
    target.setAttribute('data-aion-hr-authority-installed', 'true');
    target.innerHTML = view();
    if (state.panel) {
      requestAnimationFrame(() => {
        const panel = target.querySelector('.hrw-panel');
        if (panel && state.panel?.scrollTop) panel.scrollTop = state.panel.scrollTop;
        const focusName = state.panel?.focusName;
        const field = focusName ? target.querySelector(`[data-hrw-person-form] [name="${CSS.escape(focusName)}"]`) : null;
        if (field) {
          field.focus({ preventScroll: true });
          if (typeof field.setSelectionRange === 'function' && Number.isInteger(state.panel.selectionStart)) {
            field.setSelectionRange(state.panel.selectionStart, state.panel.selectionEnd ?? state.panel.selectionStart);
          }
        }
      });
    }
  }

  async function load(requireVisibleMount = true) {
    const workspaceId = businessId();
    state.workspaceId = workspaceId;
    state.error = '';
    if (!workspaceId) { state.model = null; if (requireVisibleMount) render(); state.error = 'Complete the Business Foundation first so people are saved to the correct business.'; if (requireVisibleMount) render(); return; }
    try {
      const [modelResult, templateResult] = await Promise.all([
        request(`/api/aion/business/organisation/${encodeURIComponent(workspaceId)}`),
        request('/api/aion/business/organisation/templates'),
      ]);
      state.model = modelResult.model;
      state.templates = templateResult;
    } catch (error) { state.error = `HR Pilot could not load: ${error.message}`; }
    if (requireVisibleMount) {
      render();
    } else {
      // A background dashboard hydration needs to announce that data is ready.
      // A visible-workspace load must not: app.js responds to this event by
      // rendering the whole application, which replaces this mount and would
      // otherwise create an endless load -> redraw -> remount loop.
      global.dispatchEvent(new CustomEvent('aion:people-workspace-updated', { detail: { workspace_id: state.workspaceId, revision: state.model?.revision || 0 } }));
    }
  }

  async function save() {
    if (!state.model || state.saving) return;
    state.saving = true; state.error = ''; render();
    try {
      const result = await request(`/api/aion/business/organisation/${encodeURIComponent(state.workspaceId)}`, {
        method: 'PUT', body: JSON.stringify({ model: state.model, expected_revision: state.model.revision || 0, changed_by: 'hr_pilot_desktop' }),
      });
      state.model = result.model;
      try {
        localStorage.setItem(`aion.organizationAuthority.summary.${state.workspaceId}`, JSON.stringify({ revision: state.model.revision, summary: state.model.summary, updated_at: new Date().toISOString() }));
      } catch {}
    } catch (error) {
      state.error = error.message.includes('organization_revision_conflict') ? 'The organisation changed elsewhere. Reload the HR Pilot before saving again.' : `Could not save: ${error.message}`;
    } finally { state.saving = false; render(); global.dispatchEvent(new CustomEvent('aion:people-workspace-updated', { detail: { workspace_id: state.workspaceId, revision: state.model?.revision || 0 } })); global.requestRender?.(); }
  }

  function formObject(form) {
    const data = new FormData(form);
    return Object.fromEntries([...data.entries()].filter(([key]) => !['department_ids','role_ids'].includes(key)));
  }

  function syncPersonDraft(form) {
    if (!state.panel || state.panel.type !== 'person' || !form) return;
    const values = formObject(form);
    values.department_ids = [...form.querySelectorAll('[name="department_ids"]:checked')].map((item) => item.value);
    values.role_ids = [...form.querySelectorAll('[name="role_ids"]:checked')].map((item) => item.value);
    values.manager_id = values.manager_id || null;
    values.onboarding = {
      ...(state.panel.draft?.onboarding || {}),
      checks: Object.fromEntries(['contract','identity','health_safety','handbook','payroll','accounts','equipment'].map((key) => [key, Boolean(form.querySelector(`[name="onboarding_checks"][value="${key}"]`)?.checked)])),
      updated_at: new Date().toISOString(),
    };
    values.software_accounts = String(values.software_accounts || '').split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
    delete values.onboarding_checks;
    values.workforce_costing = {
      ...(state.panel.draft?.workforce_costing || {}),
      basis: values.workforce_costing_basis || 'hourly',
      base_rate: values.workforce_costing_base_rate,
      employer_on_cost_percent: values.workforce_costing_employer_on_cost_percent,
      monthly_bonus: values.workforce_costing_monthly_bonus,
      commission_percent: values.workforce_costing_commission_percent,
      productive_hours_month: values.workforce_costing_productive_hours_month,
      hours_per_day: values.workforce_costing_hours_per_day,
    };
    Object.keys(values).filter((key) => key.startsWith('workforce_costing_')).forEach((key) => delete values[key]);
    state.panel.draft = { ...(state.panel.draft || {}), ...values };
  }

  function rememberPersonDraftFocus(field) {
    if (!state.panel || state.panel.type !== 'person' || !field?.name) return;
    state.panel.focusName = field.name;
    state.panel.selectionStart = Number.isInteger(field.selectionStart) ? field.selectionStart : null;
    state.panel.selectionEnd = Number.isInteger(field.selectionEnd) ? field.selectionEnd : null;
  }

  document.addEventListener('input', (event) => {
    const form = event.target?.closest?.('[data-hrw-person-form]');
    if (form) {
      syncPersonDraft(form);
      rememberPersonDraftFocus(event.target);
    }
  }, true);

  document.addEventListener('change', (event) => {
    const form = event.target?.closest?.('[data-hrw-person-form]');
    if (form) {
      syncPersonDraft(form);
      rememberPersonDraftFocus(event.target);
    }
  }, true);

  document.addEventListener('scroll', (event) => {
    const panel = event.target?.closest?.('.hrw-panel');
    if (panel && state.panel) state.panel.scrollTop = panel.scrollTop;
  }, true);

  document.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    const node = event.target?.closest?.('[data-aion-full-org-canvas] [data-hrw-org-person]');
    if (!node) {
      const viewport = event.target?.closest?.('[data-aion-full-org-canvas] .aion-full-org-viewport');
      if (!viewport || event.target?.closest?.('button,[data-hrw-org-make-top-level]')) return;
      event.preventDefault();
      state.orgPanDrag = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        scrollLeft: viewport.scrollLeft,
        scrollTop: viewport.scrollTop,
      };
      viewport.classList.add('hrw-canvas-panning');
      try { viewport.setPointerCapture?.(event.pointerId); } catch {}
      return;
    }
    const stage = node.closest('.aion-full-org-stage');
    if (!stage) return;
    event.preventDefault();
    const scale = Math.max(0.1, Number(state.orgFullScale || 1));
    state.orgPositionDrag = {
      personId: node.dataset.hrwOrgPerson || '',
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      left: Number.parseFloat(node.style.left || '0'),
      top: Number.parseFloat(node.style.top || '0'),
      scale,
    };
    node.classList.add('hrw-position-dragging');
    try { node.setPointerCapture?.(event.pointerId); } catch {}
  }, true);

  document.addEventListener('pointermove', (event) => {
    const pan = state.orgPanDrag;
    if (pan && pan.pointerId === event.pointerId) {
      const viewport = document.querySelector('[data-aion-full-org-canvas] .aion-full-org-viewport');
      if (!viewport) return;
      event.preventDefault();
      viewport.scrollLeft = pan.scrollLeft - (event.clientX - pan.startX);
      viewport.scrollTop = pan.scrollTop - (event.clientY - pan.startY);
      return;
    }
    const drag = state.orgPositionDrag;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const root = document.querySelector('[data-aion-full-org-canvas]');
    const node = [...(root?.querySelectorAll?.('[data-hrw-org-person]') || [])]
      .find((item) => item.dataset.hrwOrgPerson === drag.personId);
    const stage = node?.closest?.('.aion-full-org-stage');
    if (!root || !node || !stage) return;
    event.preventDefault();
    const width = Number.parseFloat(stage.style.width || '1700');
    const height = Number.parseFloat(stage.style.height || '900');
    const x = Math.max(0, Math.min(width - 200, drag.left + ((event.clientX - drag.startX) / drag.scale)));
    const y = Math.max(28, Math.min(height - 86, drag.top + ((event.clientY - drag.startY) / drag.scale)));
    node.style.left = `${Math.round(x)}px`;
    node.style.top = `${Math.round(y)}px`;
    state.orgFullPositions[drag.personId] = { x: Math.round(x), y: Math.round(y) };
    root.querySelectorAll('.hrw-drop-target').forEach((item) => item.classList.remove('hrw-drop-target'));
    const dropTarget = document.elementsFromPoint(event.clientX, event.clientY)
      .map((item) => item.closest?.('[data-hrw-org-person]'))
      .find((item) => item && item !== node && root.contains(item));
    const topLevelTarget = document.elementsFromPoint(event.clientX, event.clientY)
      .map((item) => item.closest?.('[data-hrw-org-make-top-level]'))
      .find((item) => item && root.contains(item));
    if (dropTarget) dropTarget.classList.add('hrw-drop-target');
    else if (topLevelTarget) topLevelTarget.classList.add('hrw-drop-target');
    redrawFullCanvasLines(root);
  }, true);

  const finishFullCanvasPositionDrag = async (event) => {
    const drag = state.orgPositionDrag;
    if (!drag || (event?.pointerId !== undefined && drag.pointerId !== event.pointerId)) return;
    const root = document.querySelector('[data-aion-full-org-canvas]');
    const draggedNode = [...(root?.querySelectorAll?.('[data-hrw-org-person]') || [])]
      .find((item) => item.dataset.hrwOrgPerson === drag.personId);
    const elements = event?.clientX === undefined ? [] : document.elementsFromPoint(event.clientX, event.clientY);
    const targetNode = elements
      .map((item) => item.closest?.('[data-hrw-org-person]'))
      .find((item) => item && item !== draggedNode && root?.contains(item));
    const topLevelTarget = elements
      .map((item) => item.closest?.('[data-hrw-org-make-top-level]'))
      .find((item) => item && root?.contains(item));
    const person = state.model?.people?.find((item) => item.id === drag.personId);
    const requestedManagerId = targetNode?.dataset.hrwOrgPerson || (topLevelTarget ? null : undefined);

    root?.querySelectorAll('.hrw-position-dragging,.hrw-drop-target')
      .forEach((item) => item.classList.remove('hrw-position-dragging', 'hrw-drop-target'));
    state.orgPositionDrag = null;

    if (person && requestedManagerId !== undefined && requestedManagerId !== person.manager_id) {
      if (requestedManagerId && reportsTo(person.id, requestedManagerId)) {
        state.error = 'That move would create a circular reporting line.';
        render();
        return;
      }
      person.manager_id = requestedManagerId;
      delete state.orgFullPositions[person.id];
      saveFullCanvasPositions();
      await save();
      return;
    }
    saveFullCanvasPositions();
  };
  document.addEventListener('pointerup', finishFullCanvasPositionDrag, true);
  document.addEventListener('pointercancel', finishFullCanvasPositionDrag, true);

  const finishFullCanvasPan = (event) => {
    const pan = state.orgPanDrag;
    if (!pan || (event?.pointerId !== undefined && pan.pointerId !== event.pointerId)) return;
    document.querySelector('[data-aion-full-org-canvas] .aion-full-org-viewport')
      ?.classList.remove('hrw-canvas-panning');
    state.orgPanDrag = null;
  };
  document.addEventListener('pointerup', finishFullCanvasPan, true);
  document.addEventListener('pointercancel', finishFullCanvasPan, true);

  document.addEventListener('wheel', (event) => {
    const viewport = event.target?.closest?.('[data-aion-full-org-canvas] .aion-full-org-viewport');
    if (!viewport || !event.ctrlKey) return;
    const stage = viewport.querySelector('.aion-full-org-stage');
    const stageSpace = viewport.querySelector('.aion-full-org-stage-space');
    if (!stage) return;
    event.preventDefault();
    const oldScale = Math.max(0.4, Number(state.orgFullScale || 1));
    const factor = Math.exp(-event.deltaY * 0.008);
    const nextScale = Math.max(0.4, Math.min(1.5, oldScale * factor));
    if (Math.abs(nextScale - oldScale) < 0.002) return;
    const rect = viewport.getBoundingClientRect();
    const offsetLeft = stage.offsetLeft || 0;
    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top;
    const contentX = (viewport.scrollLeft + pointerX - offsetLeft) / oldScale;
    const contentY = (viewport.scrollTop + pointerY) / oldScale;
    state.orgFullScale = nextScale;
    stage.style.transform = `scale(${nextScale})`;
    if (stageSpace) {
      const baseWidth = Number(stageSpace.dataset.baseWidth || 1700);
      const baseHeight = Number(stageSpace.dataset.baseHeight || 900);
      stageSpace.style.width = `${Math.round((baseWidth * nextScale) + 72)}px`;
      stageSpace.style.height = `${Math.round(baseHeight * nextScale)}px`;
    }
    const label = document.querySelector('[data-hrw-full-org-scale]');
    if (label) label.textContent = `${Math.round(nextScale * 100)}%`;
    viewport.scrollLeft = offsetLeft + (contentX * nextScale) - pointerX;
    viewport.scrollTop = (contentY * nextScale) - pointerY;
  }, { capture: true, passive: false });

  document.addEventListener('dragstart', (event) => {
    const node = event.target?.closest?.('[data-hrw-org-person]');
    if (!node || !node.closest('[data-aion-hr-workspace], [data-aion-full-org-canvas]')) return;
    state.orgDraggingId = node.dataset.hrwOrgPerson || '';
    node.classList.add('hrw-dragging');
    event.dataTransfer?.setData('text/plain', state.orgDraggingId);
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
  });

  document.addEventListener('dragover', (event) => {
    const viewport = event.target?.closest?.('[data-hrw-org-root]');
    if (!viewport || !state.orgDraggingId) return;
    event.preventDefault();
    const node = event.target?.closest?.('[data-hrw-org-person]');
    viewport.querySelectorAll('.hrw-drop-target').forEach((item) => item.classList.remove('hrw-drop-target'));
    if (node && node.dataset.hrwOrgPerson !== state.orgDraggingId) node.classList.add('hrw-drop-target');
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
  });

  document.addEventListener('drop', async (event) => {
    const viewport = event.target?.closest?.('[data-hrw-org-root]');
    if (!viewport) return;
    event.preventDefault();
    const personId = state.orgDraggingId || event.dataTransfer?.getData('text/plain');
    const person = state.model?.people?.find((item) => item.id === personId);
    const targetNode = event.target?.closest?.('[data-hrw-org-person]');
    const managerId = targetNode?.dataset.hrwOrgPerson || null;
    viewport.querySelectorAll('.hrw-drop-target,.hrw-dragging').forEach((item) => item.classList.remove('hrw-drop-target', 'hrw-dragging'));
    state.orgDraggingId = '';
    if (!person || managerId === person.id || person.manager_id === managerId) return;
    if (managerId && reportsTo(person.id, managerId)) {
      state.error = 'That move would create a circular reporting line.';
      render();
      return;
    }
    person.manager_id = managerId;
    await save();
  });

  document.addEventListener('dragend', (event) => {
    const workspace = event.target?.closest?.('[data-aion-hr-workspace], [data-aion-full-org-canvas]');
    workspace?.querySelectorAll('.hrw-drop-target,.hrw-dragging').forEach((item) => item.classList.remove('hrw-drop-target', 'hrw-dragging'));
    state.orgDraggingId = '';
  });

  document.addEventListener('click', async (event) => {
    const target = event.target.closest('[data-aion-hr-workspace] button, [data-aion-full-org-canvas] button, .hrw-panel button');
    if (!target) return;
    if (target.dataset.hrwTab) { state.tab = target.dataset.hrwTab; state.panel = null; state.accessDecision = null; render(); return; }
    if (target.hasAttribute('data-hrw-person-prev')) { state.personPage = Math.max(0, Number(state.personPage || 0) - 1); render(); return; }
    if (target.hasAttribute('data-hrw-person-next')) { state.personPage = Number(state.personPage || 0) + 1; render(); return; }
    if (target.hasAttribute('data-hrw-close')) { state.panel = null; render(); return; }
    if (target.dataset.hrwAddPerson) { state.panel = { type: 'person', employmentType: target.dataset.hrwAddPerson }; render(); return; }
    if (target.dataset.hrwEditPerson) { state.panel = { type: 'person', item: clone(state.model.people.find((item) => item.id === target.dataset.hrwEditPerson)) }; render(); return; }
    if (target.dataset.hrwReviewPerson) { state.tab = 'people'; state.panel = { type: 'person', item: clone(state.model.people.find((item) => item.id === target.dataset.hrwReviewPerson)) }; render(); return; }
    if (target.hasAttribute('data-hrw-add-leave')) { state.panel = { type: 'leave' }; render(); return; }
    if (target.dataset.hrwReviewLeave) { state.panel = { type: 'leave', item: clone(operations().leave_requests.find((item) => item.id === target.dataset.hrwReviewLeave)) }; render(); return; }
    if (target.hasAttribute('data-hrw-add-escalation')) { state.panel = { type: 'escalation' }; render(); return; }
    if (target.dataset.hrwOrgZoom) {
      if (target.dataset.hrwOrgZoom === 'in') state.orgScale = Math.min(1.35, state.orgScale + 0.1);
      else if (target.dataset.hrwOrgZoom === 'out') state.orgScale = Math.max(0.45, state.orgScale - 0.1);
      else state.orgScale = 0.82;
      render(); return;
    }
    if (target.hasAttribute('data-hrw-org-fullscreen')) {
      state.orgFullScale = 1;
      global.dispatchEvent(new CustomEvent('aion:open-organisation-workflow-canvas', { detail: { workspace_id: state.workspaceId } }));
      return;
    }
    if (target.dataset.hrwFullOrgZoom) {
      if (target.dataset.hrwFullOrgZoom === 'in') state.orgFullScale = Math.min(1.5, state.orgFullScale + 0.1);
      else if (target.dataset.hrwFullOrgZoom === 'out') state.orgFullScale = Math.max(0.4, state.orgFullScale - 0.1);
      else state.orgFullScale = 1;
      global.requestRender?.(); return;
    }
    if (target.hasAttribute('data-hrw-full-org-close')) {
      global.dispatchEvent(new CustomEvent('aion:close-organisation-workflow-canvas'));
      return;
    }
    if (target.hasAttribute('data-hrw-deactivate-person')) {
      const personId = target.closest('form')?.dataset.personId;
      const person = state.model.people.find((item) => item.id === personId);
      if (person) { person.status = 'inactive'; state.panel = null; await save(); }
      return;
    }
    if (target.hasAttribute('data-hrw-add-department')) { state.panel = { type: 'department' }; render(); return; }
    if (target.hasAttribute('data-hrw-standard-departments')) {
      const existing = new Set((state.model.departments || []).map((item) => item.id));
      state.model.departments.push(...(state.templates?.standard_departments || []).filter((item) => !existing.has(item.id)));
      await save(); return;
    }
    if (target.hasAttribute('data-hrw-add-asset')) { state.panel = { type: 'asset' }; render(); return; }
    if (target.dataset.hrwEditAsset) { state.panel = { type: 'asset', item: clone(state.model.assets.find((item) => item.id === target.dataset.hrwEditAsset)) }; render(); }
  });

  document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!form.closest('[data-aion-hr-workspace], .hrw-panel')) return;
    event.preventDefault();
    if (form.matches('[data-hrw-person-form]')) {
      const values = formObject(form);
      values.id = form.dataset.personId;
      values.department_ids = [...form.querySelectorAll('[name="department_ids"]:checked')].map((item) => item.value);
      values.role_ids = [...form.querySelectorAll('[name="role_ids"]:checked')].map((item) => item.value);
      values.manager_id = values.manager_id || null; values.status = state.panel?.item?.status || 'active';
      values.onboarding = {
        ...(state.panel?.item?.onboarding || {}),
        checks: Object.fromEntries(['contract','identity','health_safety','handbook','payroll','accounts','equipment'].map((key) => [key, Boolean(form.querySelector(`[name="onboarding_checks"][value="${key}"]`)?.checked)])),
        updated_at: new Date().toISOString(),
      };
      values.software_accounts = String(values.software_accounts || '').split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
      delete values.onboarding_checks;
      values.expense_approval_limit = values.expense_approval_limit === '' ? null : Number(values.expense_approval_limit);
      values.workforce_costing = {
        basis: values.workforce_costing_basis || 'hourly',
        base_rate: values.workforce_costing_base_rate === '' ? null : Number(values.workforce_costing_base_rate),
        employer_on_cost_percent: values.workforce_costing_employer_on_cost_percent === '' ? 0 : Number(values.workforce_costing_employer_on_cost_percent),
        monthly_bonus: values.workforce_costing_monthly_bonus === '' ? 0 : Number(values.workforce_costing_monthly_bonus),
        commission_percent: values.workforce_costing_commission_percent === '' ? 0 : Number(values.workforce_costing_commission_percent),
        productive_hours_month: values.workforce_costing_productive_hours_month === '' ? 140 : Number(values.workforce_costing_productive_hours_month),
        hours_per_day: values.workforce_costing_hours_per_day === '' ? 8 : Number(values.workforce_costing_hours_per_day),
      };
      Object.keys(values).filter((key) => key.startsWith('workforce_costing_')).forEach((key) => delete values[key]);
      const index = state.model.people.findIndex((item) => item.id === values.id);
      if (index >= 0) state.model.people[index] = { ...state.model.people[index], ...values }; else state.model.people.push(values);
      state.panel = null; await save(); return;
    }
    if (form.matches('[data-hrw-leave-form]')) {
      const values = formObject(form); values.id = form.dataset.leaveId || id('leave'); values.created_at = state.panel?.item?.created_at || new Date().toISOString(); values.updated_at = new Date().toISOString();
      const index = operations().leave_requests.findIndex((item) => item.id === values.id);
      if (index >= 0) operations().leave_requests[index] = { ...operations().leave_requests[index], ...values }; else operations().leave_requests.push(values);
      state.panel = null; await save(); return;
    }
    if (form.matches('[data-hrw-escalation-form]')) {
      const values = formObject(form); values.id = id('people-issue'); values.status = 'open'; values.created_at = new Date().toISOString(); values.restricted = true;
      operations().escalations.push(values); state.panel = null; await save(); return;
    }
    if (form.matches('[data-hrw-department-form]')) {
      const values = formObject(form); values.id = id('department'); values.status = 'active'; values.parent_department_id = values.parent_department_id || null;
      state.model.departments.push(values); state.panel = null; await save(); return;
    }
    if (form.matches('[data-hrw-asset-form]')) {
      const values = formObject(form); values.id = form.dataset.assetId; values.status = state.panel?.item?.status || 'active';
      values.assigned_person_id = values.assigned_person_id || null;
      values.transaction_limit = values.transaction_limit === '' ? null : Number(values.transaction_limit);
      values.monthly_limit = values.monthly_limit === '' ? null : Number(values.monthly_limit);
      const index = state.model.assets.findIndex((item) => item.id === values.id);
      if (index >= 0) state.model.assets[index] = { ...state.model.assets[index], ...values }; else state.model.assets.push(values);
      state.panel = null; await save(); return;
    }
    if (form.matches('[data-hrw-access-form]')) {
      const values = formObject(form); values.amount = values.amount === '' ? null : Number(values.amount); values.department_id = values.department_id || null;
      try {
        const result = await request(`/api/aion/business/organisation/${encodeURIComponent(state.workspaceId)}/access-decision`, { method: 'POST', body: JSON.stringify(values) });
        state.accessDecision = result.decision;
      } catch (error) { state.error = `Authority check failed: ${error.message}`; }
      render();
    }
  });

  function installIfPresent() {
    scheduled = false;
    const target = host();
    if (!target || target.hasAttribute('data-aion-hr-authority-installed')) return;
    target.setAttribute('data-aion-hr-authority-installed', 'true');
    if (state.model && state.workspaceId === businessId()) {
      // Rehydrate synchronously from the canonical in-memory model if another
      // legitimate application render replaced the mount. This avoids a white
      // loading flash and an unnecessary API round trip.
      target.innerHTML = view();
      return;
    }
    target.innerHTML = '<div class="hrw-loading">Loading organisation…</div>';
    load();
  }

  function scheduleInstall() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(installIfPresent);
  }

  function installStyles() {
    if (document.getElementById('aion-hr-people-workspace-styles')) return;
    const style = document.createElement('style');
    style.id = 'aion-hr-people-workspace-styles';
    style.textContent = `
      html body [data-aion-o18ad-department="hr"]{max-width:1680px!important;margin:0 auto!important;background:#f8fafc!important;border:0!important;padding:0!important;color:#102a43!important;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important}
      .hrw-shell{min-height:760px;background:#f8fafc;color:#102a43;padding:26px;position:relative}.hrw-shell *{box-sizing:border-box}.hrw-section-head span,.hrw-empty>span,.hrw-panel header span{display:block;color:#0f766e;font-size:11px;font-weight:900;letter-spacing:.25em}.hrw-section-head p{margin:0;color:#52677e;line-height:1.55}.hrw-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:0 0 18px}.hrw-metrics article{background:#fff;border:1px solid #cbd5e1;padding:16px}.hrw-metrics strong{display:block;font-size:24px;color:#0f766e}.hrw-metrics span{font-size:12px;color:#64748b}.hrw-tabs{display:flex;gap:4px;align-items:center;overflow-x:auto;border:1px solid #d7e0ea;background:#edf2f7;padding:4px}.hrw-shell button{appearance:none;border:1px solid #94a3b8;background:#fff;color:#334e68;padding:10px 14px;font-weight:800;cursor:pointer}.hrw-shell button:hover{border-color:#0284c7;color:#0369a1}.hrw-shell button.primary{background:#15803d;border-color:#15803d;color:#fff}.hrw-shell button.danger{border-color:#ef4444;color:#b91c1c;margin-right:auto}.hrw-tabs button{flex:0 0 auto;border:1px solid transparent;background:transparent;color:#52677e;padding:7px 10px;font-size:11px;white-space:nowrap}.hrw-tabs button:hover{border-color:#cbd5e1;background:#f8fafc;color:#0f172a}.hrw-tabs button.active{background:#fff;border-color:#b8c6d5;color:#0f766e;box-shadow:0 1px 2px rgba(15,23,42,.08)}.hrw-content{background:#fff;border:1px solid #cbd5e1;border-top:4px solid #0284c7;margin-top:12px;padding:28px;min-height:520px}.hrw-section-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:22px}.hrw-section-head>div{max-width:760px}.hrw-section-head h2{font-size:24px;margin:5px 0;color:#102a43}.hrw-section-head.compact{align-items:center;margin:0 0 12px}.hrw-section-head.compact h3{margin:0}.hrw-actions{display:flex;gap:9px;flex-wrap:wrap}.hrw-people-head{align-items:center}.hrw-people-head>div{flex:1;min-width:0}.hrw-person-actions{align-items:center;gap:6px;flex-wrap:nowrap}.hrw-person-actions button{padding:7px 10px;font-size:11px;line-height:1.2;white-space:nowrap;background:#f8fafc}.hrw-empty{text-align:center;max-width:760px;margin:55px auto;padding:35px;border:1px dashed #7dd3fc;background:#f0f9ff}.hrw-empty.small{margin:30px auto}.hrw-empty h2{font-size:28px;margin:8px}.hrw-empty p{color:#52677e;line-height:1.6}.hrw-empty .hrw-actions{justify-content:center;margin-top:24px}.hrw-people-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}.hrw-person{border:1px solid #cbd5e1;padding:18px;display:grid;grid-template-columns:50px 1fr;gap:14px;background:#fff}.hrw-person.inactive{opacity:.58}.hrw-avatar{width:50px;height:50px;background:#dbeafe;border:1px solid #7dd3fc;color:#075985;display:grid;place-items:center;font-weight:900}.hrw-person-main>div{display:flex;justify-content:space-between;gap:10px}.hrw-person-main strong{font-size:17px}.hrw-person-main em{font-size:10px;text-transform:uppercase;color:#15803d}.hrw-person-main p{margin:4px 0;color:#334e68}.hrw-person-main small{color:#64748b}.hrw-person dl{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:4px 0}.hrw-person dl div{background:#f8fafc;padding:9px}.hrw-person dt{font-size:10px;text-transform:uppercase;color:#64748b}.hrw-person dd{margin:3px 0 0;font-size:12px}.hrw-person>button{grid-column:1/-1}.hrw-alert{margin:18px 0 0;border-left:4px solid #f59e0b;background:#fffbeb;padding:14px 18px}.hrw-alert.error{border-color:#ef4444;background:#fef2f2;margin:0 0 14px}.hrw-alert p{margin:5px 0;color:#7c2d12}.hrw-org-toolbar{display:flex;justify-content:space-between;align-items:center;gap:15px;border:1px solid #d7e0ea;border-bottom:0;background:#f8fafc;padding:7px 10px;color:#64748b;font-size:11px}.hrw-org-toolbar>div{display:flex;align-items:center;gap:5px}.hrw-org-toolbar button{padding:5px 9px;min-width:30px}.hrw-org-toolbar strong{min-width:42px;text-align:center;color:#334e68}.hrw-org-viewport{height:520px;overflow:auto;position:relative;border:1px solid #cbd5e1;background-color:#f8fafc;background-image:linear-gradient(#e8eef5 1px,transparent 1px),linear-gradient(90deg,#e8eef5 1px,transparent 1px);background-size:24px 24px}.hrw-org-stage{position:relative;transform-origin:0 0;transition:transform .15s ease}.hrw-org-lines{position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none}.hrw-org-lines path{fill:none;stroke:#7a92aa;stroke-width:2}.hrw-org-node{position:absolute;width:200px;height:86px;display:grid;grid-template-columns:40px 1fr 25px;align-items:center;gap:10px;background:#fff;border:1px solid #7dd3fc;border-top:4px solid #0f766e;padding:11px;box-shadow:0 4px 10px rgba(15,23,42,.08);cursor:grab;user-select:none}.hrw-org-node:active{cursor:grabbing}.hrw-org-node.hrw-dragging{opacity:.45}.hrw-org-node.hrw-drop-target{outline:3px solid #2dd4bf;outline-offset:3px}.hrw-org-node-avatar{width:38px;height:38px;display:grid;place-items:center;background:#dbeafe;border:1px solid #7dd3fc;color:#075985;font-size:12px;font-weight:900}.hrw-org-node strong,.hrw-org-node span,.hrw-org-node small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hrw-org-node strong{font-size:13px;color:#102a43}.hrw-org-node span{font-size:11px;color:#334e68;margin:3px 0}.hrw-org-node small{font-size:9px;color:#64748b}.hrw-org-node button{border:0;background:transparent;padding:5px 2px;color:#64748b;font-size:13px}.hrw-org-root-hint{position:absolute;left:18px;bottom:18px;border:1px dashed #94a3b8;background:rgba(255,255,255,.9);color:#64748b;padding:8px 10px;font-size:10px}.hrw-departments{margin-top:24px}.hrw-departments>article{display:flex;justify-content:space-between;padding:13px;border-bottom:1px solid #e2e8f0}.hrw-departments>article small{display:block;color:#64748b;margin-top:3px}.hrw-departments>article>span{color:#0f766e;font-weight:800}.hrw-role-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.hrw-role-grid article{border:1px solid #cbd5e1;padding:17px}.hrw-role-grid header{display:flex;justify-content:space-between;gap:12px}.hrw-role-grid header span{font-size:10px;text-transform:uppercase;color:#0f766e}.hrw-role-grid p{color:#52677e;min-height:42px}.hrw-role-grid article>div{display:flex;flex-wrap:wrap;gap:5px}.hrw-role-grid article>div small{background:#eff6ff;color:#1e40af;padding:4px 7px}.hrw-role-grid footer{border-top:1px solid #e2e8f0;margin-top:14px;padding-top:10px}.hrw-policy{margin-top:20px;border-left:4px solid #15803d;background:#ecfdf5;padding:16px}.hrw-policy p{margin:5px 0}.hrw-assets{display:grid;gap:10px}.hrw-assets article{display:grid;grid-template-columns:70px 1fr auto;align-items:center;gap:15px;border:1px solid #cbd5e1;padding:15px}.hrw-asset-icon{height:44px;display:grid;place-items:center;background:#102a43;color:#fff;font-size:10px;letter-spacing:.12em}.hrw-assets p{margin:4px 0;color:#334e68}.hrw-assets small{color:#64748b}.hrw-access-form{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr)) auto;gap:12px;align-items:end;background:#f8fafc;border:1px solid #cbd5e1;padding:18px}.hrw-shell label{display:grid;gap:6px;font-size:11px;font-weight:800;color:#334e68}.hrw-shell input,.hrw-shell select{width:100%;border:1px solid #94a3b8;background:#fff;color:#102a43;padding:10px;font:inherit}.hrw-decision{margin:20px 0;padding:20px;border-left:6px solid}.hrw-decision.allowed{background:#ecfdf5;border-color:#16a34a}.hrw-decision.denied{background:#fef2f2;border-color:#dc2626}.hrw-decision p{margin:5px 0;text-transform:capitalize}.hrw-panel{position:fixed;z-index:10000;inset:0 0 0 auto;width:min(620px,96vw);background:#fff;box-shadow:-20px 0 60px rgba(15,23,42,.28);overflow:auto;padding:0}.hrw-panel form{padding:26px;display:grid;gap:16px}.hrw-panel header{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid #e2e8f0;padding-bottom:15px}.hrw-panel header h2{margin:5px 0 0}.hrw-panel header button{font-size:24px;padding:2px 10px}.hrw-panel fieldset{border:1px solid #cbd5e1;padding:14px}.hrw-panel legend{padding:0 7px;font-weight:900}.hrw-two{display:grid;grid-template-columns:1fr 1fr;gap:12px}.hrw-checks{display:grid;grid-template-columns:1fr 1fr;gap:8px}.hrw-checks label{display:flex;align-items:flex-start;gap:8px;background:#f8fafc;padding:9px}.hrw-checks input{width:auto;margin-top:2px}.hrw-checks span,.hrw-checks b,.hrw-checks small{display:block}.hrw-checks small{font-weight:400;color:#64748b}.hrw-panel footer{display:flex;justify-content:flex-end;gap:9px;border-top:1px solid #e2e8f0;padding-top:18px}.hrw-loading{min-height:500px;display:grid;place-items:center;background:#fff;color:#0f766e;font-weight:900}.hrw-muted{color:#64748b}
      .hrw-shell textarea{width:100%;border:1px solid #94a3b8;background:#fff;color:#102a43;padding:10px;font:inherit;resize:vertical}.hrw-directory-pagination{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:-6px 0 14px;padding:10px 12px;background:#f8fafc;border:1px solid #e2e8f0}.hrw-directory-pagination>span{font-size:11px;font-weight:900;color:#52677e;text-transform:uppercase;letter-spacing:.08em}.hrw-directory-pagination>div{display:flex;gap:8px}.hrw-directory-pagination button:disabled{opacity:.4;cursor:not-allowed}.hrw-ops-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-bottom:18px}.hrw-ops-metrics article{border:1px solid #cbd5e1;padding:14px}.hrw-ops-metrics strong,.hrw-ops-metrics span{display:block}.hrw-ops-metrics strong{font-size:23px}.hrw-ops-metrics span{font-size:11px;color:#64748b}.hrw-ops-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.hrw-ops-grid>section{border:1px solid #cbd5e1}.hrw-ops-grid>section>header{display:flex;justify-content:space-between;gap:12px;padding:13px 15px;background:#f8fafc;border-bottom:1px solid #e2e8f0}.hrw-ops-grid>section>header small{color:#64748b}.hrw-ops-grid>section>article{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 15px;border-bottom:1px solid #e2e8f0}.hrw-ops-grid>section>article:last-child{border-bottom:0}.hrw-ops-grid article span,.hrw-ops-grid article b,.hrw-ops-grid article small{display:block}.hrw-ops-grid article small{margin-top:3px;color:#64748b}.hrw-ops-grid article em{font-size:11px;color:#475569}.hrw-ops-grid .hrw-muted{padding:16px;margin:0}
      @media(max-width:900px){.hrw-metrics,.hrw-ops-metrics{grid-template-columns:repeat(2,1fr)}.hrw-tabs{gap:4px}.hrw-ops-grid{grid-template-columns:1fr}.hrw-section-head{display:block}.hrw-actions{margin-top:14px}.hrw-access-form{grid-template-columns:1fr 1fr}.hrw-org-viewport{height:460px}.hrw-two,.hrw-checks{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }

  installStyles();
  const observer = new MutationObserver(scheduleInstall);
  observer.observe(document.getElementById('app') || document.body, { childList: true, subtree: true });
  scheduleInstall();
  global.AionHrPeopleWorkspace = {
    load, save, state, render, renderFullCanvas,
    snapshot() { return state.model ? clone(state.model) : null; },
    ensureDashboardData() { if (!state.model && !state.saving) load(false); },
    openPerson(personId) {
      const item = state.model?.people?.find((person) => person.id === personId);
      if (item) { state.tab = 'people'; state.panel = { type: 'person', item: clone(item) }; render(); }
    },
    openOperations() { state.tab = 'operations'; state.panel = null; render(); },
    openLeave(leaveId) {
      const item = state.model?.people_operations?.leave_requests?.find((row) => row.id === leaveId);
      if (item) { state.tab = 'operations'; state.panel = { type: 'leave', item: clone(item) }; render(); }
    },
  };
})(window);
