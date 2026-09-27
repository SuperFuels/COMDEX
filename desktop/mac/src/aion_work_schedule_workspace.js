(function installAionWorkScheduleWorkspace(global) {
  'use strict';

  const STORAGE_KEY = 'tessaris.workSchedule.workspace.v1';
  const UI_KEY = 'tessaris.workSchedule.ui.v1';
  const API_BASE = String(global.__AION_DESKTOP_STATE__?.apiBase || global.__aionDesktopState?.apiBase || 'http://127.0.0.1:8080').replace(/\/+$/, '');
  const STATUSES = ['new', 'quote_required', 'awaiting_approval', 'scheduled', 'en_route', 'in_progress', 'paused', 'completed', 'invoiced', 'paid'];
  const TYPE_LABELS = {
    job: 'Job', appointment: 'Appointment', visit: 'Visit', survey: 'Survey',
    consultation: 'Consultation', meeting: 'Meeting', project_task: 'Project task', order: 'Order'
  };

  const esc = (value) => String(value == null ? '' : value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
  const titleCase = (value) => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  const isoDate = (date) => {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  };
  const dateFromIso = (value) => {
    const bits = String(value || '').split('-').map(Number);
    return bits.length === 3 ? new Date(bits[0], bits[1] - 1, bits[2]) : new Date();
  };
  const uid = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

  function mondayOf(date) {
    const result = new Date(date);
    const day = result.getDay() || 7;
    result.setDate(result.getDate() - day + 1);
    result.setHours(0, 0, 0, 0);
    return result;
  }

  function makeInitialData() {
    const monday = mondayOf(new Date());
    const day = (offset) => {
      const value = new Date(monday);
      value.setDate(value.getDate() + offset);
      return isoDate(value);
    };
    return {
      revision: 1,
      items: [
        {
          id: 'sample_roof_installation', sample: true, title: 'New roof installation', customer: 'Client example',
          type: 'job', status: 'scheduled', date: day(1), time: '08:30', duration: 420,
          assignee: 'Kevin Robinson + team', location: 'Customer site', source: 'Back office',
          notes: 'Materials and access to be confirmed before arrival.', documents: [], updates: [],
          quote: { status: 'approved', amount: '4850.00' }, invoice: { status: 'not_created', amount: '' }
        },
        {
          id: 'sample_quote_visit', sample: true, title: 'Roof survey and quote', customer: 'New website enquiry',
          type: 'survey', status: 'quote_required', date: day(2), time: '10:00', duration: 90,
          assignee: 'James Double', location: 'Customer site', source: 'Website booking',
          notes: 'Customer uploaded two photographs with the booking.', documents: ['roof-photo-1.jpg', 'roof-photo-2.jpg'], updates: [],
          quote: { status: 'not_created', amount: '' }, invoice: { status: 'not_created', amount: '' }
        },
        {
          id: 'sample_consultation', sample: true, title: 'Client consultation', customer: 'Prospective client',
          type: 'appointment', status: 'scheduled', date: day(4), time: '14:00', duration: 60,
          assignee: 'Rebecca Newman', location: 'Video meeting', source: 'Sales agent',
          notes: 'Discuss requirements and agree the next action.', documents: [], updates: [],
          quote: { status: 'not_created', amount: '' }, invoice: { status: 'not_created', amount: '' }
        }
      ],
      intake: [
        { id: 'intake_website', channel: 'Website', title: 'Request for an estimate', customer: 'Website visitor', received: '12 minutes ago', state: 'Needs review' },
        { id: 'intake_phone', channel: 'Agent', title: 'Call-back and availability request', customer: 'New lead', received: 'Today', state: 'Ready to schedule' }
      ]
    };
  }

  function loadData() {
    try {
      const parsed = JSON.parse(global.localStorage?.getItem(STORAGE_KEY) || 'null');
      if (parsed && Array.isArray(parsed.items) && Array.isArray(parsed.intake)) return parsed;
    } catch (_) {}
    const initial = makeInitialData();
    try { global.localStorage?.setItem(STORAGE_KEY, JSON.stringify(initial)); } catch (_) {}
    return initial;
  }

  function loadUi() {
    try {
      const parsed = JSON.parse(global.localStorage?.getItem(UI_KEY) || 'null');
      if (parsed && typeof parsed === 'object') return parsed;
    } catch (_) {}
    return { view: 'calendar', week: isoDate(mondayOf(new Date())), selectedId: '', panelTab: 'overview', modal: '' };
  }

  const state = { data: loadData(), ui: loadUi(), hydrated: false, syncing: false, syncPending: false, syncError: '', conflicts: [] };
  let signatureDrawing = null;
  const workspaceId = () => String(global.AionBusinessContainerClient?.resolveBusinessId?.() || global.__aionDesktopState?.workspaceId || global.state?.activeWorkspaceId || 'home-fixed');
  const endpoint = (suffix = '') => `${API_BASE}/api/aion/business/work-schedule/${encodeURIComponent(workspaceId())}${suffix}`;
  const applyModel = (model) => {
    if (!model || !Array.isArray(model.items)) return;
    state.data = model;
    state.data.intake = Array.isArray(model.intake) ? model.intake : [];
    state.conflicts = Array.isArray(model.conflicts) ? model.conflicts : [];
    try { global.localStorage?.setItem(STORAGE_KEY, JSON.stringify(state.data)); } catch (_) {}
  };
  async function syncToBackend() {
    if (!state.hydrated) return;
    if (state.syncing) { state.syncPending = true; return; }
    state.syncing = true; state.syncError = '';
    try {
      const response = await fetch(endpoint(), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: state.data, changed_by: 'desktop_user' }) });
      const payload = await response.json();
      if (!response.ok || payload.ok === false) throw new Error(payload.detail || payload.error || 'Shared schedule could not be saved');
      applyModel(payload.model);
    } catch (error) { state.syncError = String(error?.message || error); }
    finally {
      state.syncing = false; rerender();
      if (state.syncPending) { state.syncPending = false; void syncToBackend(); }
    }
  }
  async function hydrate() {
    if (state.hydrated) return;
    state.hydrated = true;
    try {
      const response = await fetch(endpoint()); const payload = await response.json();
      if (!response.ok || !payload.model) throw new Error(payload.detail || 'Shared schedule is unavailable');
      if (Number(payload.model.revision || 0) === 0) {
        const localItems = (state.data.items || []).filter((item) => !item.sample);
        if (localItems.length || (state.data.intake || []).some((item) => !String(item.id || '').startsWith('intake_website') && !String(item.id || '').startsWith('intake_phone'))) {
          state.data.items = localItems; await syncToBackend();
        } else applyModel(payload.model);
      } else applyModel(payload.model);
    } catch (error) { state.syncError = String(error?.message || error); }
    rerender();
  }
  const persist = () => {
    state.data.revision = Number(state.data.revision || 0) + 1;
    try { global.localStorage?.setItem(STORAGE_KEY, JSON.stringify(state.data)); } catch (_) {}
    void syncToBackend();
  };
  const persistUi = () => {
    try { global.localStorage?.setItem(UI_KEY, JSON.stringify(state.ui)); } catch (_) {}
  };
  const rerender = () => {
    persistUi();
    if (typeof global.requestRender === 'function') global.requestRender();
    else if (typeof global.render === 'function') global.render();
  };
  const workItem = (id) => state.data.items.find((item) => String(item.id) === String(id));
  const addUpdate = (item, text) => {
    item.updates = [...(item.updates || []), { text, at: new Date().toLocaleString() }];
  };
  const readBase64 = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || '').split(',', 2)[1] || '');
    reader.onerror = () => reject(reader.error || new Error('File could not be read'));
    reader.readAsDataURL(file);
  });
  async function apiPost(url, body) {
    const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw new Error(payload.detail || payload.error || 'The request could not be completed');
    return payload;
  }

  function statusBadge(status) {
    return `<span class="ws-status ws-status-${esc(status)}">${esc(titleCase(status))}</span>`;
  }

  function formatDay(date) {
    return new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short' }).format(date);
  }

  function renderHeader() {
    const items = state.data.items;
    const scheduled = items.filter((item) => ['scheduled', 'en_route', 'in_progress', 'paused'].includes(item.status)).length;
    const unscheduled = items.filter((item) => !item.date).length + state.data.intake.length;
    const quotes = items.filter((item) => ['quote_required', 'awaiting_approval'].includes(item.status)).length;
    const active = items.filter((item) => !['completed', 'invoiced', 'paid'].includes(item.status)).length;
    return `<header class="ws-header">
      <div><span>WORK · BOOKINGS · DELIVERY</span><h1>Work &amp; Schedule</h1><p>One record from the first customer request through scheduling, work on site, evidence, quote and invoice.</p></div>
      <div class="ws-header-actions"><span class="ws-sync-state ${state.syncError ? 'error' : ''}">${state.syncError ? `Not synced · ${esc(state.syncError)}` : state.syncing ? 'Saving…' : state.hydrated ? 'Shared with mobile' : 'Connecting…'}</span><button type="button" data-ws-open-intake>Review intake <b>${state.data.intake.length}</b></button><button type="button" class="primary" data-ws-new>+ New work</button></div>
      <div class="ws-metrics"><article><b>${scheduled}</b><span>Scheduled</span></article><article><b>${unscheduled}</b><span>Needs scheduling</span></article><article><b>${quotes}</b><span>Quotes requiring action</span></article><article><b>${active}</b><span>Open work</span></article></div>
    </header>`;
  }

  function renderViewTabs() {
    const tabs = [['calendar', 'Calendar'], ['board', 'Job board'], ['field', 'Field workspace'], ['intake', 'Booking inbox'], ['customers', 'Customers'], ['reminders', 'Reminders'], ['stock', 'Stock & materials']];
    return `<nav class="ws-view-tabs" aria-label="Work and Schedule views">${tabs.map(([key, label]) => `<button type="button" class="${state.ui.view === key ? 'active' : ''}" data-ws-view="${key}">${label}${key === 'intake' ? `<span>${state.data.intake.length}</span>` : ''}</button>`).join('')}</nav>`;
  }

  function renderCalendar() {
    const start = mondayOf(dateFromIso(state.ui.week));
    const days = Array.from({ length: 7 }, (_, index) => {
      const value = new Date(start);
      value.setDate(value.getDate() + index);
      return value;
    });
    const end = days[6];
    const range = `${new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'long' }).format(start)} – ${new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'long', year: 'numeric' }).format(end)}`;
    return `<section class="ws-calendar-panel">
      <header class="ws-calendar-toolbar"><div><span>WEEKLY SCHEDULE</span><h2>${esc(range)}</h2></div><div><button type="button" data-ws-week="prev">‹</button><button type="button" data-ws-week="today">Today</button><button type="button" data-ws-week="next">›</button></div></header>
      <div class="ws-calendar-grid">${days.map((date) => {
        const key = isoDate(date);
        const entries = state.data.items.filter((item) => item.date === key).sort((a, b) => String(a.time).localeCompare(String(b.time)));
        const today = key === isoDate(new Date());
        return `<section class="ws-calendar-day ${today ? 'today' : ''}" data-ws-drop-date="${key}"><header><span>${esc(formatDay(date))}</span><button type="button" data-ws-new-date="${key}" aria-label="Add work on ${esc(formatDay(date))}">+</button></header><div class="ws-day-items">${entries.map((item) => `<button type="button" draggable="true" class="ws-calendar-card ws-kind-${esc(item.type)}" data-ws-item="${esc(item.id)}"><time>${esc(item.time || 'All day')}</time><strong>${esc(item.title)}</strong><small>${esc(item.customer || 'No customer')}</small><em>${esc(item.assignee || 'Unassigned')}</em>${item.sample ? '<i>Sample</i>' : ''}</button>`).join('') || `<button type="button" class="ws-empty-day" data-ws-new-date="${key}">Schedule work</button>`}</div></section>`;
      }).join('')}</div>
      <footer class="ws-calendar-footer"><span><i class="job"></i> Job</span><span><i class="appointment"></i> Appointment</span><span><i class="survey"></i> Survey / quote</span><small>Drag a card to another day. ${state.conflicts.length ? `${state.conflicts.length} scheduling clash${state.conflicts.length === 1 ? '' : 'es'} need attention.` : 'No resource clashes detected.'}</small></footer>
    </section>`;
  }

  function renderBoard() {
    const lanes = [
      ['new', 'New / unscheduled'], ['quote_required', 'Quote required'], ['awaiting_approval', 'Awaiting approval'],
      ['scheduled', 'Scheduled'], ['active_work', 'In progress / travelling'], ['completed', 'Completed']
    ];
    return `<section class="ws-board"><header><div><span>DELIVERY PIPELINE</span><h2>Job board</h2></div><p>Move every work item from request to completion without losing the customer, schedule or evidence.</p></header><div class="ws-board-lanes">${lanes.map(([status, label]) => {
      const rows = state.data.items.filter((item) => item.status === status || (status === 'active_work' && ['en_route', 'in_progress', 'paused'].includes(item.status)) || (status === 'completed' && ['completed', 'invoiced', 'paid'].includes(item.status)));
      return `<section class="ws-board-lane"><header><strong>${label}</strong><span>${rows.length}</span></header>${rows.map((item) => `<button type="button" data-ws-item="${esc(item.id)}"><small>${esc(TYPE_LABELS[item.type] || titleCase(item.type))}${item.date ? ` · ${esc(item.date)}` : ''}</small><b>${esc(item.title)}</b><span>${esc(item.customer)}</span><em>${esc(item.assignee || 'Unassigned')}</em></button>`).join('') || '<p>No work here</p>'}</section>`;
    }).join('')}</div></section>`;
  }

  function renderIntake() {
    return `<section class="ws-intake"><header><div><span>INBOUND REQUESTS</span><h2>Booking inbox</h2><p>Website bookings, calls, emails and agent-created requests arrive here before they become scheduled work.</p></div><button type="button" data-ws-new>+ Add request</button></header><div class="ws-intake-list">${state.data.intake.map((item) => `<article><div class="ws-channel">${esc(item.channel)}</div><div><strong>${esc(item.title)}</strong><span>${esc(item.customer)} · ${esc(item.received)}</span></div><small>${esc(item.state)}</small><button type="button" data-ws-convert-intake="${esc(item.id)}">Create work item</button></article>`).join('') || '<div class="ws-empty"><strong>Inbox clear</strong><span>No booking requests are waiting for review.</span></div>'}</div></section>`;
  }

  function renderCustomers() {
    const map = new Map();
    state.data.items.forEach((item) => {
      const key = item.customer || 'No customer';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(item);
    });
    return `<section class="ws-customers"><header><span>CUSTOMER HISTORY</span><h2>Customers and their work</h2><p>Every booking, visit, quote, document and invoice remains connected to the customer.</p></header><div>${Array.from(map.entries()).map(([customer, items]) => `<article><div class="ws-customer-avatar">${esc(customer.split(/\s+/).slice(0, 2).map((word) => word[0]).join('').toUpperCase())}</div><div><strong>${esc(customer)}</strong><span>${items.length} work item${items.length === 1 ? '' : 's'} · Last activity ${esc(items.slice().sort((a,b) => String(b.date).localeCompare(String(a.date)))[0]?.date || 'Not scheduled')}</span></div><button type="button" data-ws-item="${esc(items[0].id)}">Open history</button></article>`).join('')}</div></section>`;
  }

  function renderReminders() {
    const rows = state.data.reminders || [];
    return `<section class="ws-intake"><header><div><span>CUSTOMER COMMUNICATION</span><h2>Reminders ready for review</h2><p>Upcoming appointment messages are prepared here. Nothing is described as sent until a messaging provider confirms delivery.</p></div><button type="button" data-ws-prepare-all-reminders>Prepare upcoming reminders</button></header><div class="ws-intake-list">${rows.map((row) => `<article><div class="ws-channel">${esc(String(row.channel || 'manual').toUpperCase())}</div><div><strong>${esc(row.message)}</strong><span>${esc(row.recipient || 'No customer contact recorded')} · ${esc(row.prepared_at || '')}</span></div><small>${esc(titleCase(row.status || 'needs_review'))}</small><button type="button" data-ws-item="${esc(row.item_id)}">Open work</button></article>`).join('') || '<div class="ws-empty"><strong>No reminders prepared</strong><span>Open a work item to add customer contact details, or prepare reminders for upcoming scheduled work.</span></div>'}</div></section>`;
  }

  function renderStock() {
    const totals = new Map();
    (state.data.stock_movements || []).forEach((row) => {
      const key = row.name || 'Unnamed item';
      const current = totals.get(key) || { quantity: 0, unit: row.unit || 'item', movements: 0 };
      current.quantity += Number(row.quantity || 0); current.movements += 1; totals.set(key, current);
    });
    return `<section class="ws-stock"><header><div><span>STOCK · PURCHASING · RETURNS</span><h2>Materials ledger</h2><p>Record stock received, allocated to work, used on site or returned. Every movement stays tied to the shared business record.</p></div></header><form data-ws-stock-form><input required name="name" placeholder="Material or stock item"><input required type="number" min="0.01" step="0.01" name="quantity" placeholder="Quantity"><input name="unit" placeholder="Unit"><select name="movement_type"><option value="receive">Receive stock</option><option value="allocate">Allocate / use</option><option value="return">Return to stock</option><option value="adjust">Reduce / adjust</option></select><button class="primary" type="submit">Record movement</button></form><div class="ws-stock-grid">${Array.from(totals.entries()).map(([name, row]) => `<article><span>${esc(row.unit)}</span><strong>${esc(name)}</strong><b>${esc(row.quantity)}</b><small>${row.movements} recorded movement${row.movements === 1 ? '' : 's'}</small></article>`).join('') || '<div class="ws-empty"><strong>No stock recorded</strong><span>Add the first delivery or allocation above.</span></div>'}</div></section>`;
  }

  function renderDelivery(item) {
    const minutes = (item.time_entries || []).reduce((sum, row) => sum + Number(row.minutes || 0), 0);
    const route = item.location ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(item.location)}` : '';
    return `<section class="ws-delivery"><div class="ws-delivery-summary"><article><span>TIME RECORDED</span><strong>${Math.floor(minutes / 60)}h ${minutes % 60}m</strong></article><article><span>MATERIALS</span><strong>${(item.materials || []).length}</strong></article>${route ? `<a href="${route}" target="_blank" rel="noreferrer">Open route in Maps ↗</a>` : '<small>Add a location to open route planning.</small>'}</div><h3>Checklist</h3><div class="ws-checklist">${(item.checklist || []).map((row) => `<label><input type="checkbox" data-ws-check-item="${esc(item.id)}" data-ws-check-id="${esc(row.id)}" ${row.done ? 'checked' : ''}><span>${esc(row.label)}</span></label>`).join('') || '<p>No checklist steps yet.</p>'}</div><form data-ws-checklist-form="${esc(item.id)}"><input required name="label" placeholder="Add a step, inspection or evidence requirement"><button type="submit">Add step</button></form><h3>Materials used or required</h3><div class="ws-material-list">${(item.materials || []).map((row) => `<article><label><input type="checkbox" data-ws-material-item="${esc(item.id)}" data-ws-material-id="${esc(row.id)}" ${row.used ? 'checked' : ''}> Used</label><strong>${esc(row.name)}</strong><span>${esc(row.quantity)} ${esc(row.unit)}${row.unit_cost ? ` · £${esc(row.unit_cost)} each` : ''}</span></article>`).join('') || '<p>No materials recorded.</p>'}</div><form data-ws-material-form="${esc(item.id)}"><input required name="name" placeholder="Material"><input type="number" step="0.01" min="0" name="quantity" value="1"><input name="unit" placeholder="Unit" value="item"><input inputmode="decimal" name="unit_cost" placeholder="Unit cost"><button type="submit">Add material</button></form><h3>Time entries</h3><div class="ws-time-list">${(item.time_entries || []).map((row) => `<article><strong>${esc(row.minutes)} minutes</strong><span>${esc(row.note || 'Work time')} · ${esc(row.by || '')}</span></article>`).join('') || '<p>No time has been recorded.</p>'}</div><form data-ws-time-form="${esc(item.id)}"><input required type="number" min="1" max="1440" name="minutes" placeholder="Minutes"><input name="note" placeholder="What was the time for?"><button type="submit">Add time</button></form></section>`;
  }

  function renderFieldWorkspace() {
    const today = isoDate(new Date());
    const ordered = state.data.items.slice().sort((a, b) => `${a.date || '9999'} ${a.time || '99:99'}`.localeCompare(`${b.date || '9999'} ${b.time || '99:99'}`));
    let work = ordered.filter((item) => item.date === today || ['en_route', 'in_progress', 'paused'].includes(item.status));
    if (!work.length) work = ordered.filter((item) => item.date && item.date >= today && !['completed', 'invoiced', 'paid'].includes(item.status)).slice(0, 6);
    const active = work.filter((item) => ['en_route', 'in_progress', 'paused'].includes(item.status)).length;
    const missingEvidence = work.filter((item) => !(item.documents || []).length).length;
    const actionButtons = (item) => {
      if (['new', 'quote_required', 'awaiting_approval', 'scheduled'].includes(item.status)) return `<button type="button" data-ws-field-action="en_route" data-ws-field-item="${esc(item.id)}">On my way</button><button type="button" class="primary" data-ws-field-action="start" data-ws-field-item="${esc(item.id)}">Start work</button>`;
      if (item.status === 'en_route') return `<button type="button" class="primary" data-ws-field-action="start" data-ws-field-item="${esc(item.id)}">Arrived · start</button>`;
      if (item.status === 'in_progress') return `<button type="button" data-ws-field-action="pause" data-ws-field-item="${esc(item.id)}">Pause</button><button type="button" class="primary" data-ws-field-action="complete" data-ws-field-item="${esc(item.id)}">Complete work</button>`;
      if (item.status === 'paused') return `<button type="button" class="primary" data-ws-field-action="start" data-ws-field-item="${esc(item.id)}">Resume work</button>`;
      return '';
    };
    return `<section class="ws-field">
      <header><div><span>FIELD &amp; PRACTITIONER WORKSPACE</span><h2>My workday</h2><p>Complete the same work record used by scheduling: instructions, notes, evidence, customer sign-off, documents and payment outcome.</p></div><div class="ws-field-summary"><article><b>${work.length}</b><small>On this workday</small></article><article><b>${active}</b><small>Active now</small></article><article><b>${missingEvidence}</b><small>Evidence missing</small></article></div></header>
      <div class="ws-field-layout"><aside><strong>Designed for the person doing the work</strong><p>This focused view works on a desktop, tablet or phone. It shows only what is needed before, during and after the visit.</p><ul><li>Review customer and site instructions</li><li>Start, pause and complete work</li><li>Add notes, photos and certificates</li><li>Capture customer sign-off</li><li>Record time and materials</li></ul></aside>
      <div class="ws-field-device"><div class="ws-field-device-head"><div><span>${esc(formatDay(new Date()))}</span><strong>Assigned work</strong></div><small>Shared live record</small></div><div class="ws-field-list">${work.map((item, index) => `<article class="ws-field-card ${['en_route','in_progress','paused'].includes(item.status) ? 'active' : ''}"><div class="ws-field-time"><time>${esc(item.time || 'Any time')}</time><span>${Number(item.duration || 0) >= 60 ? `${Math.round(Number(item.duration) / 60 * 10) / 10} hr` : `${esc(item.duration || 0)} min`}</span></div><div class="ws-field-main"><div class="ws-field-card-top"><small>${index === 0 ? 'NEXT WORK' : esc(TYPE_LABELS[item.type] || titleCase(item.type))}</small>${statusBadge(item.status)}</div><h3>${esc(item.title)}</h3><p>${esc(item.customer)} · ${esc(item.location || 'Location not recorded')}</p><em>Assigned to ${esc(item.assignee || 'Unassigned')}</em><div class="ws-field-actions">${actionButtons(item)}<button type="button" data-ws-item="${esc(item.id)}" data-ws-panel-open="documents">Details &amp; evidence</button></div></div></article>`).join('') || '<div class="ws-empty"><strong>No assigned work</strong><span>The schedule is clear for now.</span></div>'}</div></div></div>
    </section>`;
  }

  function renderNewModal() {
    if (state.ui.modal !== 'new') return '';
    const preset = state.ui.newDraft || {};
    return `<div class="ws-modal-layer"><button class="ws-modal-backdrop" type="button" data-ws-close aria-label="Close"></button><section class="ws-modal"><header><div><span>NEW SHARED WORK RECORD</span><h2>Schedule a job or appointment</h2><p>Create it once. The customer, office, Pilot and assigned person will all work from this record.</p></div><button type="button" data-ws-close>×</button></header><form data-ws-new-form>
      <label class="wide">Work title<input required name="title" placeholder="e.g. New roof installation" value="${esc(preset.title)}"></label>
      <label>Customer<input required name="customer" placeholder="Customer or organisation" value="${esc(preset.customer)}"></label>
      <label>Work type<select name="type">${Object.entries(TYPE_LABELS).map(([key, label]) => `<option value="${key}" ${preset.type === key ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
      <label>Date<input type="date" name="date" value="${esc(preset.date || isoDate(new Date()))}"></label>
      <label>Start time<input type="time" name="time" value="${esc(preset.time || '09:00')}"></label>
      <label>Duration<select name="duration">${[[30,'30 minutes'],[60,'1 hour'],[90,'1½ hours'],[120,'2 hours'],[240,'Half day'],[480,'Full day']].map(([value,label]) => `<option value="${value}" ${Number(preset.duration || 60) === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
      <label>Assigned person or team<input name="assignee" placeholder="Choose or leave unassigned" value="${esc(preset.assignee)}"></label>
      <label>Status<select name="status">${['new','quote_required','awaiting_approval','scheduled','in_progress','completed'].map((status) => `<option value="${status}" ${status === (preset.status || 'scheduled') ? 'selected' : ''}>${titleCase(status)}</option>`).join('')}</select></label>
      <label>Origin<select name="source"><option>Back office</option><option>Website booking</option><option>Sales agent</option><option>Phone</option><option>Email</option><option>Customer portal</option></select></label>
      <label>Repeat<select name="recurrence_frequency"><option value="none">Does not repeat</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label>
      <label>Number of visits<input type="number" min="1" max="52" name="recurrence_count" value="1"></label>
      <label class="wide">Rooms, vehicles or equipment<input name="resource_ids" placeholder="e.g. Van 1, Surgery 2 (separate with commas)"></label>
      <label class="wide">Location<input name="location" placeholder="Customer site, clinic, office or video call" value="${esc(preset.location)}"></label>
      <label class="wide">Instructions and notes<textarea name="notes" placeholder="Access, requirements, preparation or customer notes">${esc(preset.notes)}</textarea></label>
      <footer><button type="button" data-ws-close>Cancel</button><button type="submit" class="primary">Create work item</button></footer>
    </form></section></div>`;
  }

  function renderDetailPanel() {
    const item = workItem(state.ui.selectedId);
    if (!item) return '';
    const panelTab = state.ui.panelTab || 'overview';
    const tabs = [['overview','Overview'],['delivery','Checklist, time & materials'],['updates','Work updates'],['documents','Files & evidence'],['signoff','Customer sign-off'],['commercial','Quotes & invoices']];
    return `<div class="ws-panel-layer"><button class="ws-panel-backdrop" type="button" data-ws-close-item aria-label="Close"></button><aside class="ws-detail-panel">
      <header><div><span>${esc(TYPE_LABELS[item.type] || titleCase(item.type))} · ${esc(item.id)}</span><h2>${esc(item.title)}</h2><p>${esc(item.customer)}</p></div><button type="button" data-ws-close-item>×</button></header>
      <div class="ws-detail-status">${statusBadge(item.status)}${item.sample ? '<span class="ws-sample">Sample record</span>' : ''}<select data-ws-status="${esc(item.id)}">${STATUSES.map((status) => `<option value="${status}" ${status === item.status ? 'selected' : ''}>${titleCase(status)}</option>`).join('')}</select></div>
      <nav>${tabs.map(([key,label]) => `<button type="button" class="${panelTab === key ? 'active' : ''}" data-ws-panel-tab="${key}">${label}</button>`).join('')}</nav>
      <div class="ws-detail-body">${panelTab === 'overview' ? `<section class="ws-overview"><dl><div><dt>Date and time</dt><dd>${esc(item.date || 'Not scheduled')} · ${esc(item.time || 'Time not set')}</dd></div><div><dt>Duration</dt><dd>${esc(item.duration || 0)} minutes</dd></div><div><dt>Assigned to</dt><dd>${esc(item.assignee || 'Unassigned')}</dd></div><div><dt>Location</dt><dd>${esc(item.location || 'Not recorded')}</dd></div><div><dt>Origin</dt><dd>${esc(item.source || 'Not recorded')}</dd></div><div><dt>Customer</dt><dd>${esc(item.customer || 'Not recorded')}</dd></div></dl><article><span>WORK INSTRUCTIONS</span><p>${esc(item.notes || 'No instructions have been added.')}</p></article><button type="button" data-ws-duplicate="${esc(item.id)}">Schedule another visit</button></section>` : ''}
      ${panelTab === 'delivery' ? renderDelivery(item) : ''}
      ${panelTab === 'updates' ? `<section class="ws-updates"><div>${(item.updates || []).map((update) => `<article><strong>${esc(update.text)}</strong><span>${esc(update.at)}</span></article>`).join('') || '<p>No work updates yet. Notes from the office or the person doing the work will appear here.</p>'}</div><form data-ws-update-form="${esc(item.id)}"><textarea name="update" required placeholder="Add a note, outcome, measurement or next action"></textarea><button class="primary" type="submit">Add update</button></form></section>` : ''}
      ${panelTab === 'documents' ? `<section class="ws-documents"><div>${(item.documents || []).map((file) => { const document = typeof file === 'string' ? { name: file } : file; return `<article><span>${esc(titleCase(document.kind || 'file'))}</span><strong>${esc(document.name || 'Attached file')}</strong><small>${document.size ? `${Math.ceil(Number(document.size) / 1024)} KB · ` : ''}Attached to this shared work record</small>${document.id && document.stored_name ? `<a href="${endpoint(`/items/${encodeURIComponent(item.id)}/files/${encodeURIComponent(document.id)}`)}" target="_blank" rel="noreferrer">Open file</a>` : ''}</article>`; }).join('') || '<p>No photographs, certificates or documents have been added.</p>'}</div><label class="ws-upload">+ Add photos, certificates or files<input type="file" multiple data-ws-file="${esc(item.id)}"></label><div class="ws-document-actions"><button type="button" data-ws-create-document="service_report" data-ws-document-item="${esc(item.id)}">Create service report</button><button type="button" data-ws-create-document="completion_certificate" data-ws-document-item="${esc(item.id)}">Create completion certificate</button></div><small class="ws-helper">Files and generated PDFs are stored in the business workspace and are available to authorised desktop and mobile users.</small></section>` : ''}
      ${panelTab === 'signoff' ? `<section class="ws-signoff">${item.customerSignature?.dataUrl ? `<div class="ws-signed"><span>CUSTOMER SIGN-OFF RECORDED</span><img src="${esc(item.customerSignature.dataUrl)}" alt="Customer signature"><strong>${esc(item.customerSignature.name || 'Customer')}</strong><small>${esc(item.customerSignature.signedAt || '')}</small><button type="button" data-ws-replace-signature="${esc(item.id)}">Replace signature</button></div>` : `<div class="ws-signoff-copy"><span>COMPLETION CONFIRMATION</span><h3>Ask the customer to sign</h3><p>The signature is stored on this work record with the customer name and time. It confirms attendance or completion; it does not replace contractual acceptance terms.</p></div><label>Customer name<input data-ws-signature-name="${esc(item.id)}" placeholder="Name of person signing"></label><canvas class="ws-signature-pad" data-ws-signature-pad="${esc(item.id)}" width="560" height="180" aria-label="Customer signature pad"></canvas><div class="ws-signature-actions"><button type="button" data-ws-clear-signature="${esc(item.id)}">Clear</button><button type="button" class="primary" data-ws-save-signature="${esc(item.id)}">Save customer sign-off</button></div>`}</section>` : ''}
      ${panelTab === 'commercial' ? `<section class="ws-commercial"><article><span>QUOTE</span><strong>${esc(item.quote?.number || titleCase(item.quote?.status || 'not_created'))}</strong><label>Description<input data-ws-quote-description="${esc(item.id)}" value="${esc(item.title)}"></label><label>Amount before tax<input inputmode="decimal" data-ws-quote-amount="${esc(item.id)}" value="${esc(item.quote?.subtotal || item.quote?.amount || '')}" placeholder="0.00"></label><label>Tax %<input inputmode="decimal" data-ws-quote-tax="${esc(item.id)}" value="${esc(item.quote?.tax_rate || '20')}"></label><button type="button" data-ws-create-quote="${esc(item.id)}">Generate numbered quote PDF</button></article><article><span>INVOICE</span><strong>${esc(item.invoice?.number || titleCase(item.invoice?.status || 'not_created'))}</strong><label>Description<input data-ws-invoice-description="${esc(item.id)}" value="${esc(item.title)}"></label><label>Amount before tax<input inputmode="decimal" data-ws-invoice-amount="${esc(item.id)}" value="${esc(item.invoice?.subtotal || item.invoice?.amount || '')}" placeholder="0.00"></label><label>Tax %<input inputmode="decimal" data-ws-invoice-tax="${esc(item.id)}" value="${esc(item.invoice?.tax_rate || '20')}"></label><button type="button" data-ws-create-invoice="${esc(item.id)}">Generate numbered invoice PDF</button></article><article class="ws-payment"><span>CUSTOMER PORTAL</span><strong>Share a limited customer view</strong><p>Customers can review this booking, request a new time or cancellation, and approve or decline a quote. They cannot see the wider schedule.</p><button type="button" data-ws-create-portal="${esc(item.id)}">Create secure customer link</button>${state.ui.portalLink ? `<label>Customer link<input readonly value="${esc(state.ui.portalLink)}"></label>` : ''}</article><p>Quotes and invoices are numbered drafts with line totals and tax. Sending them and accounting-ledger posting remain approval-controlled.</p></section>` : ''}</div>
    </aside></div>`;
  }

  function renderSurface(renderSidebar) {
    void hydrate();
    const content = state.ui.view === 'board' ? renderBoard() : state.ui.view === 'field' ? renderFieldWorkspace() : state.ui.view === 'intake' ? renderIntake() : state.ui.view === 'customers' ? renderCustomers() : state.ui.view === 'reminders' ? renderReminders() : state.ui.view === 'stock' ? renderStock() : renderCalendar();
    return `<div class="surface-shell ws-surface" data-aion-work-schedule="true">${typeof renderSidebar === 'function' ? renderSidebar() : ''}<main class="ws-shell">${renderHeader()}${renderViewTabs()}<form class="ws-pilot-bar" data-ws-pilot-form><div><span>WORK PILOT</span><strong>Delegate the booking and admin</strong><small>Say it naturally: “Book a roof survey for Alex next Tuesday at 10 and assign James.”</small></div><input name="instruction" required placeholder="Tell Work Pilot what to book or change…"><button type="submit" class="primary">Prepare</button></form>${state.ui.pilotMessage ? `<div class="ws-pilot-result">${esc(state.ui.pilotMessage)}</div>` : ''}${state.conflicts.length ? `<section class="ws-conflicts"><strong>Scheduling clashes</strong>${state.conflicts.map((row) => `<button type="button" data-ws-item="${esc(row.item_ids?.[0] || '')}">${esc(row.message)}</button>`).join('')}</section>` : ''}${content}</main>${renderNewModal()}${renderDetailPanel()}</div>`;
  }

  function openNew(preset = {}) {
    state.ui.modal = 'new';
    state.ui.newDraft = preset;
    rerender();
  }

  function bindEvents() {
    if (global.__aionWorkScheduleEventsBound) return;
    global.__aionWorkScheduleEventsBound = true;
    document.addEventListener('click', (event) => {
      const target = event.target;
      const view = target?.closest?.('[data-ws-view]');
      if (view) { state.ui.view = view.dataset.wsView; rerender(); return; }
      if (target?.closest?.('[data-ws-open-intake]')) { state.ui.view = 'intake'; rerender(); return; }
      const dated = target?.closest?.('[data-ws-new-date]');
      if (dated) { openNew({ date: dated.dataset.wsNewDate, status: 'scheduled' }); return; }
      if (target?.closest?.('[data-ws-new]')) { openNew({}); return; }
      if (target?.closest?.('[data-ws-close]')) { state.ui.modal = ''; state.ui.newDraft = {}; rerender(); return; }
      const itemButton = target?.closest?.('[data-ws-item]');
      if (itemButton) { state.ui.selectedId = itemButton.dataset.wsItem; state.ui.panelTab = itemButton.dataset.wsPanelOpen || 'overview'; rerender(); return; }
      if (target?.closest?.('[data-ws-close-item]')) { state.ui.selectedId = ''; rerender(); return; }
      const panelTab = target?.closest?.('[data-ws-panel-tab]');
      if (panelTab) { state.ui.panelTab = panelTab.dataset.wsPanelTab; rerender(); return; }
      const fieldAction = target?.closest?.('[data-ws-field-action]');
      if (fieldAction) {
        const item = workItem(fieldAction.dataset.wsFieldItem);
        const action = fieldAction.dataset.wsFieldAction;
        if (item) {
          if (action === 'en_route') { item.status = 'en_route'; addUpdate(item, 'Marked on the way to the customer.'); }
          if (action === 'start') { item.status = 'in_progress'; addUpdate(item, 'Work started.'); }
          if (action === 'pause') { item.status = 'paused'; addUpdate(item, 'Work paused.'); }
          if (action === 'complete') { item.status = 'completed'; addUpdate(item, 'Work marked complete. Evidence and customer sign-off can still be added.'); }
          persist(); rerender();
        }
        return;
      }
      const week = target?.closest?.('[data-ws-week]');
      if (week) {
        const current = mondayOf(dateFromIso(state.ui.week));
        if (week.dataset.wsWeek === 'today') state.ui.week = isoDate(mondayOf(new Date()));
        else { current.setDate(current.getDate() + (week.dataset.wsWeek === 'next' ? 7 : -7)); state.ui.week = isoDate(current); }
        rerender(); return;
      }
      const convert = target?.closest?.('[data-ws-convert-intake]');
      if (convert) {
        const intake = state.data.intake.find((row) => row.id === convert.dataset.wsConvertIntake);
        if (intake) openNew({ title: intake.title, customer: intake.customer, source: intake.channel, status: 'new' });
        return;
      }
      const duplicate = target?.closest?.('[data-ws-duplicate]');
      if (duplicate) {
        const item = workItem(duplicate.dataset.wsDuplicate);
        if (item) openNew({ title: `Follow-up · ${item.title}`, customer: item.customer, type: 'visit', assignee: item.assignee, location: item.location, notes: `Follow-up for ${item.id}`, status: 'scheduled' });
        return;
      }
      const quote = target?.closest?.('[data-ws-create-quote]');
      if (quote) {
        const item = workItem(quote.dataset.wsCreateQuote);
        const amount = document.querySelector(`[data-ws-quote-amount="${CSS.escape(item.id)}"]`)?.value || '';
        const description = document.querySelector(`[data-ws-quote-description="${CSS.escape(item.id)}"]`)?.value || item.title;
        const taxRate = document.querySelector(`[data-ws-quote-tax="${CSS.escape(item.id)}"]`)?.value || '0';
        void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/documents`), { kind: 'quote', actor_id: 'desktop_user', line_items: [{ description, quantity: 1, unit_price: amount || '0' }], tax_rate: taxRate }).then((payload) => { applyModel(payload.schedule); const changed = workItem(item.id); if (changed && changed.status === 'quote_required') changed.status = 'awaiting_approval'; rerender(); }).catch((error) => { state.syncError = String(error?.message || error); rerender(); }); return;
      }
      const invoice = target?.closest?.('[data-ws-create-invoice]');
      if (invoice) {
        const item = workItem(invoice.dataset.wsCreateInvoice);
        const amount = document.querySelector(`[data-ws-invoice-amount="${CSS.escape(item.id)}"]`)?.value || '';
        const description = document.querySelector(`[data-ws-invoice-description="${CSS.escape(item.id)}"]`)?.value || item.title;
        const taxRate = document.querySelector(`[data-ws-invoice-tax="${CSS.escape(item.id)}"]`)?.value || '0';
        void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/documents`), { kind: 'invoice', actor_id: 'desktop_user', line_items: [{ description, quantity: 1, unit_price: amount || '0' }], tax_rate: taxRate }).then((payload) => { applyModel(payload.schedule); rerender(); }).catch((error) => { state.syncError = String(error?.message || error); rerender(); }); return;
      }
      const portal = target?.closest?.('[data-ws-create-portal]');
      if (portal) {
        const item = workItem(portal.dataset.wsCreatePortal);
        void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/portal-access`), { actor_id: 'desktop_user', expires_days: 30 }).then((payload) => { applyModel(payload.schedule); state.ui.portalLink = `${location.origin}${API_BASE}/api/aion/business/work-schedule/portal/${payload.token}/page`; rerender(); }).catch((error) => { state.syncError = String(error?.message || error); rerender(); }); return;
      }
      if (target?.closest?.('[data-ws-prepare-all-reminders]')) {
        const upcoming = (state.data.items || []).filter((row) => row.date && !['completed','cancelled','paid'].includes(row.status));
        Promise.all(upcoming.map((row) => apiPost(endpoint('/actions'), { operation: 'prepare_reminder', fields: { id: row.id }, actor_id: 'desktop_user' }))).then((results) => { const latest = results[results.length - 1]; if (latest?.model) applyModel(latest.model); rerender(); }).catch((error) => { state.syncError = String(error?.message || error); rerender(); }); return;
      }
      const documentButton = target?.closest?.('[data-ws-create-document]');
      if (documentButton) {
        const item = workItem(documentButton.dataset.wsDocumentItem);
        if (item) {
          documentButton.disabled = true;
          void apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/documents`), { kind: documentButton.dataset.wsCreateDocument, actor_id: 'desktop_user' })
            .then((payload) => { applyModel(payload.schedule); rerender(); })
            .catch((error) => { state.syncError = String(error?.message || error); rerender(); });
        }
        return;
      }
      const clearSignature = target?.closest?.('[data-ws-clear-signature]');
      if (clearSignature) {
        const canvas = document.querySelector(`[data-ws-signature-pad="${CSS.escape(clearSignature.dataset.wsClearSignature)}"]`);
        canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height); return;
      }
      const saveSignature = target?.closest?.('[data-ws-save-signature]');
      if (saveSignature) {
        const item = workItem(saveSignature.dataset.wsSaveSignature);
        const canvas = document.querySelector(`[data-ws-signature-pad="${CSS.escape(item.id)}"]`);
        const name = document.querySelector(`[data-ws-signature-name="${CSS.escape(item.id)}"]`)?.value?.trim() || '';
        if (item && canvas && name) {
          item.customerSignature = { name, signedAt: new Date().toLocaleString(), dataUrl: canvas.toDataURL('image/png') };
          addUpdate(item, `Customer sign-off recorded for ${name}.`); persist(); rerender();
        } else if (!name) {
          document.querySelector(`[data-ws-signature-name="${CSS.escape(item.id)}"]`)?.focus();
        }
        return;
      }
      const replaceSignature = target?.closest?.('[data-ws-replace-signature]');
      if (replaceSignature) { const item = workItem(replaceSignature.dataset.wsReplaceSignature); if (item) { delete item.customerSignature; persist(); rerender(); } return; }
      const preparePayment = target?.closest?.('[data-ws-prepare-payment]');
      if (preparePayment) {
        const item = workItem(preparePayment.dataset.wsPreparePayment);
        const amount = document.querySelector(`[data-ws-payment-amount="${CSS.escape(item.id)}"]`)?.value || '';
        const method = document.querySelector(`[data-ws-payment-method="${CSS.escape(item.id)}"]`)?.value || 'Card';
        item.payment = { status: 'request_prepared', amount, method, recordedAt: new Date().toLocaleString() };
        addUpdate(item, `Payment request prepared${amount ? ` for £${amount}` : ''} by ${method}. Approval is still required before sending or charging.`); persist(); rerender(); return;
      }
      const recordPayment = target?.closest?.('[data-ws-record-payment]');
      if (recordPayment) {
        const item = workItem(recordPayment.dataset.wsRecordPayment);
        const amount = document.querySelector(`[data-ws-payment-amount="${CSS.escape(item.id)}"]`)?.value || '';
        const method = document.querySelector(`[data-ws-payment-method="${CSS.escape(item.id)}"]`)?.value || 'Card';
        item.payment = { status: 'received', amount, method, recordedAt: new Date().toLocaleString() };
        item.invoice = { ...(item.invoice || {}), status: 'paid', amount: item.invoice?.amount || amount }; item.status = 'paid';
        addUpdate(item, `Payment received recorded${amount ? `: £${amount}` : ''} via ${method}.`); persist(); rerender(); return;
      }
    }, true);

    document.addEventListener('pointerdown', (event) => {
      const canvas = event.target?.closest?.('[data-ws-signature-pad]');
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const context = canvas.getContext('2d');
      context.strokeStyle = '#102a43'; context.lineWidth = 2.5; context.lineCap = 'round'; context.lineJoin = 'round';
      context.beginPath(); context.moveTo((event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height);
      signatureDrawing = { canvas, context };
      canvas.setPointerCapture?.(event.pointerId); event.preventDefault();
    }, true);
    document.addEventListener('pointermove', (event) => {
      if (!signatureDrawing) return;
      const { canvas, context } = signatureDrawing;
      const rect = canvas.getBoundingClientRect();
      context.lineTo((event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height); context.stroke(); event.preventDefault();
    }, true);
    document.addEventListener('pointerup', () => { signatureDrawing = null; }, true);
    document.addEventListener('pointercancel', () => { signatureDrawing = null; }, true);

    document.addEventListener('change', (event) => {
      const status = event.target?.closest?.('[data-ws-status]');
      if (status) { const item = workItem(status.dataset.wsStatus); if (item) { item.status = status.value; persist(); rerender(); } return; }
      const checklist = event.target?.closest?.('[data-ws-check-item]');
      if (checklist) { const item = workItem(checklist.dataset.wsCheckItem); const row = item?.checklist?.find((entry) => entry.id === checklist.dataset.wsCheckId); if (row) { row.done = checklist.checked; addUpdate(item, `${row.label}: ${row.done ? 'completed' : 'reopened'}.`); persist(); rerender(); } return; }
      const material = event.target?.closest?.('[data-ws-material-item]');
      if (material) { const item = workItem(material.dataset.wsMaterialItem); const row = item?.materials?.find((entry) => entry.id === material.dataset.wsMaterialId); if (row) { row.used = material.checked; persist(); rerender(); } return; }
      const file = event.target?.closest?.('[data-ws-file]');
      if (file) {
        const item = workItem(file.dataset.wsFile);
        if (item) {
          const uploads = Array.from(file.files || []).map(async (entry) => {
            const data = await readBase64(entry);
            const payload = await apiPost(endpoint(`/items/${encodeURIComponent(item.id)}/files`), { filename: entry.name, content_type: entry.type || 'application/octet-stream', data_base64: data, actor_id: 'desktop_user' });
            applyModel(payload.schedule);
          });
          void Promise.all(uploads).then(rerender).catch((error) => { state.syncError = String(error?.message || error); rerender(); });
        }
      }
    }, true);

    document.addEventListener('dragstart', (event) => {
      const card = event.target?.closest?.('[data-ws-item][draggable="true"]');
      if (card) event.dataTransfer?.setData('text/work-item', card.dataset.wsItem || '');
    }, true);
    document.addEventListener('dragover', (event) => {
      if (event.target?.closest?.('[data-ws-drop-date]')) event.preventDefault();
    }, true);
    document.addEventListener('drop', (event) => {
      const day = event.target?.closest?.('[data-ws-drop-date]');
      const id = event.dataTransfer?.getData('text/work-item');
      const item = workItem(id);
      if (day && item) { event.preventDefault(); item.date = day.dataset.wsDropDate; addUpdate(item, `Rescheduled to ${item.date}.`); persist(); rerender(); }
    }, true);

    document.addEventListener('submit', (event) => {
      const pilot = event.target?.closest?.('[data-ws-pilot-form]');
      if (pilot) {
        event.preventDefault();
        const instruction = String(new FormData(pilot).get('instruction') || '').trim();
        if (!instruction) return;
        state.ui.pilotMessage = 'Understanding your request…'; rerender();
        void apiPost(endpoint('/interpret'), { text: instruction }).then((payload) => {
          const result = payload.interpretation || {};
          if (result.intent === 'update_work' && result.ready) {
            const words = String(result.query || '').toLowerCase().split(/\s+/).filter((word) => word.length > 2);
            const matches = state.data.items.filter((item) => {
              const haystack = `${item.title || ''} ${item.customer || ''} ${item.id || ''}`.toLowerCase();
              return words.length && words.every((word) => haystack.includes(word));
            });
            if (matches.length === 1) {
              Object.assign(matches[0], result.fields || {});
              addUpdate(matches[0], `Work Pilot applied: ${result.summary}.`);
              state.ui.pilotMessage = `${result.summary}. The shared work record has been updated.`;
              state.ui.selectedId = matches[0].id; state.ui.panelTab = 'overview'; persist(); rerender(); return;
            }
            state.ui.pilotMessage = matches.length ? `I found ${matches.length} possible work items. Open the correct one before changing it.` : `I could not find one work item matching “${result.query || ''}”.`;
            rerender(); return;
          }
          state.ui.pilotMessage = result.missing_fields?.length ? `I understood the request. Please add: ${result.missing_fields.join(', ')}.` : 'I understood the request. Check the details, then create it.';
          openNew(result.fields || {});
        }).catch((error) => { state.ui.pilotMessage = `I could not prepare that request: ${error?.message || error}`; rerender(); });
        return;
      }
      const create = event.target?.closest?.('[data-ws-new-form]');
      if (create) {
        event.preventDefault();
        const values = Object.fromEntries(new FormData(create).entries());
        values.recurrence = { frequency: values.recurrence_frequency || 'none', count: Number(values.recurrence_count || 1) };
        values.resource_ids = String(values.resource_ids || '').split(',').map((value) => value.trim()).filter(Boolean);
        delete values.recurrence_frequency; delete values.recurrence_count;
        const item = { id: uid('work'), ...values, duration: Number(values.duration || 60), sample: false, documents: [], updates: [], quote: { status: 'not_created', amount: '' }, invoice: { status: 'not_created', amount: '' } };
        state.data.items.push(item); persist(); state.ui.modal = ''; state.ui.newDraft = {}; state.ui.selectedId = item.id; rerender(); return;
      }
      const update = event.target?.closest?.('[data-ws-update-form]');
      if (update) {
        event.preventDefault();
        const item = workItem(update.dataset.wsUpdateForm);
        const text = String(new FormData(update).get('update') || '').trim();
        if (item && text) { item.updates = [...(item.updates || []), { text, at: new Date().toLocaleString() }]; persist(); rerender(); }
        return;
      }
      const checklist = event.target?.closest?.('[data-ws-checklist-form]');
      if (checklist) { event.preventDefault(); const item = workItem(checklist.dataset.wsChecklistForm); const label = String(new FormData(checklist).get('label') || '').trim(); if (item && label) { item.checklist = [...(item.checklist || []), { id: uid('check'), label, done: false }]; persist(); rerender(); } return; }
      const material = event.target?.closest?.('[data-ws-material-form]');
      if (material) { event.preventDefault(); const item = workItem(material.dataset.wsMaterialForm); const values = Object.fromEntries(new FormData(material).entries()); if (item && values.name) { item.materials = [...(item.materials || []), { id: uid('material'), name: values.name, quantity: Number(values.quantity || 0), unit: values.unit || 'item', unit_cost: values.unit_cost || '', used: false }]; persist(); rerender(); } return; }
      const time = event.target?.closest?.('[data-ws-time-form]');
      if (time) { event.preventDefault(); const item = workItem(time.dataset.wsTimeForm); const values = Object.fromEntries(new FormData(time).entries()); if (item && Number(values.minutes) > 0) { item.time_entries = [...(item.time_entries || []), { id: uid('time'), minutes: Number(values.minutes), note: values.note || '', at: new Date().toISOString(), by: 'desktop_user' }]; persist(); rerender(); } return; }
      const stock = event.target?.closest?.('[data-ws-stock-form]');
      if (stock) { event.preventDefault(); const values = Object.fromEntries(new FormData(stock).entries()); const quantity = Number(values.quantity || 0); const signed = ['receive','return'].includes(values.movement_type) ? quantity : -quantity; state.data.stock_movements = [...(state.data.stock_movements || []), { id: uid('stock'), name: values.name, quantity: signed, unit: values.unit || 'item', movement_type: values.movement_type, at: new Date().toISOString(), by: 'desktop_user' }]; persist(); rerender(); return; }
    }, true);
  }

  function ensureStyles() {
    if (document.getElementById('aion-work-schedule-styles')) return;
    const style = document.createElement('style');
    style.id = 'aion-work-schedule-styles';
    style.textContent = `
      .ws-field-device-head strong{color:#fff}.ws-detail-panel>nav button{flex:1;padding:10px 8px;font-size:10px}.ws-detail-panel>nav button:last-child{min-width:142px}
      @media(max-width:1050px){.ws-calendar-grid{grid-template-columns:repeat(7,minmax(170px,1fr))}.ws-metrics{grid-template-columns:1fr 1fr}.ws-header{grid-template-columns:1fr}.ws-header-actions{grid-row:2}.ws-intake-list article{grid-template-columns:70px 1fr}.ws-intake-list article>small,.ws-intake-list article>button{grid-column:2}.ws-calendar-footer small{display:none}.ws-field-layout{grid-template-columns:1fr}.ws-field-layout>aside{display:none}}
      @media(max-width:720px){.ws-surface{padding:0 10px 50px 76px!important}.ws-header{padding:20px 16px}.ws-header h1{font-size:26px}.ws-view-tabs{padding:0;overflow:auto}.ws-pilot-bar{align-items:flex-start;flex-direction:column}.ws-modal form{grid-template-columns:1fr}.ws-modal label.wide,.ws-modal footer{grid-column:1}.ws-overview dl,.ws-commercial{grid-template-columns:1fr}.ws-commercial>p,.ws-commercial article.ws-payment{grid-column:1}.ws-calendar-footer{overflow:auto}.ws-field>header{display:grid}.ws-field-summary{overflow:auto}.ws-field-layout{padding:8px}.ws-field-device{border-radius:0}.ws-field-card{grid-template-columns:72px 1fr}.ws-field-time{padding:12px 9px}.ws-field-actions button{flex:1}.ws-payment>div{display:grid}.ws-document-actions{display:grid!important}}
    `;
    document.head.appendChild(style);
  }

  ensureStyles();
  bindEvents();
  global.AionWorkScheduleWorkspace = { render: renderSurface, state, openNew };
})(window);
