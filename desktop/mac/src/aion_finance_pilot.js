(function installAionFinancePilot(global) {
  'use strict';

  const STORAGE_KEY = 'aion.financePilot.discoveryState.v1';
  const MODEL_KEY = 'aion.financePilot.businessFinancialModel.v1';
  const BOARDROOM_PACKET_KEY = 'aion.businessTwin.financePacket.v1';
  const schema = global.AionFinanceDiscoverySchema;
  if (!schema) return;

  const now = () => new Date().toISOString();
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));

  function ensureVisualStyles() {
    const id = 'aion-finance-pilot-visual-system-v1';
    document.getElementById(id)?.remove();
    const style = document.createElement('style');
    style.id = id;
    style.textContent = `
      html body [data-aion-finance-workspace="true"] {
        background:#ffffff !important;
      }
      html body [data-aion-finance-workspace="true"] p {
        color:#cbd5e1 !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting],
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence] {
        appearance:none !important;
        -webkit-appearance:none !important;
        background:#07111f !important;
        background-image:linear-gradient(145deg,rgba(14,165,233,.08),transparent 58%) !important;
        border:1px solid rgba(56,189,248,.42) !important;
        color:#f8fafc !important;
        box-shadow:inset 3px 0 0 rgba(14,165,233,.42) !important;
        transition:border-color 140ms ease,background 140ms ease,transform 140ms ease !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting]:hover,
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence]:hover {
        background:#0b1b2d !important;
        border-color:#38bdf8 !important;
        transform:translateY(-1px) !important;
      }
      html body [data-aion-finance-workspace="true"] [aria-pressed="true"] {
        background:#06281f !important;
        background-image:linear-gradient(145deg,rgba(34,197,94,.18),transparent 62%) !important;
        border:2px solid #4ade80 !important;
        box-shadow:inset 3px 0 0 #22c55e,0 0 0 1px rgba(34,197,94,.16) !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting] strong,
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence] strong {
        color:#f8fafc !important;
      }
      html body [data-aion-finance-workspace="true"] [aria-pressed="true"] strong {
        color:#86efac !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-accounting] span,
      html body [data-aion-finance-workspace="true"] [data-aion-finance-evidence] span {
        color:#94a3b8 !important;
      }
      html body [data-aion-finance-workspace="true"] [data-aion-finance-continue],
      html body [data-aion-finance-workspace="true"] [data-aion-finance-finalise] {
        background:#22c55e !important;
        background-image:linear-gradient(135deg,#4ade80,#22c55e) !important;
        color:#052e16 !important;
        border:1px solid #86efac !important;
        box-shadow:0 8px 24px rgba(34,197,94,.18) !important;
      }
    `;
    document.head.appendChild(style);
  }

  window.setTimeout(ensureVisualStyles, 0);

  function initialState() {
    return {
      schema_version: schema.version,
      status: 'data_sources',
      accounting_platforms: [],
      other_accounting_platform: '',
      evidence_sources: [],
      source_records: [],
      connector_policy: 'read_only_discovery',
      question_index: 0,
      answers: {},
      transcript: [],
      created_at: now(),
      updated_at: now(),
      completed_at: null,
    };
  }

  function load() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      return value && typeof value === 'object' ? { ...initialState(), ...value } : initialState();
    } catch { return initialState(); }
  }

  function save(next) {
    const value = { ...next, updated_at: now() };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    global.AionBusinessContainerClient?.syncFinanceState?.(value);
    return value;
  }

  function toggle(list, value) {
    const set = new Set(Array.isArray(list) ? list : []);
    if (set.has(value)) set.delete(value); else set.add(value);
    return [...set];
  }

  function buildBusinessFinancialModel(state) {
    const model = {
      schema_version: 'aion.business_financial_model.v1',
      status: 'draft_for_board_review',
      source_discovery: {
        accounting_platforms: state.accounting_platforms,
        other_accounting_platform: state.other_accounting_platform,
        evidence_sources: state.evidence_sources,
        source_records: state.source_records,
        connector_policy: state.connector_policy,
      },
      discovery_answers: state.answers,
      evidence_quality: 'user_supplied_unverified',
      boardroom_handoff: {
        ready: true,
        requested_outputs: ['financial_baseline', 'margin_model', 'cash_risk', 'cost_opportunities', 'finance_actions'],
      },
      created_at: now(),
      updated_at: now(),
    };
    localStorage.setItem(MODEL_KEY, JSON.stringify(model));
    let foundationPacket = null;
    try { foundationPacket = JSON.parse(localStorage.getItem('aion.businessTwin.foundationPacket.v1') || 'null'); } catch {}
    localStorage.setItem(BOARDROOM_PACKET_KEY, JSON.stringify({
      schema_version: 'aion.business_twin.finance_packet.v1',
      department: 'finance',
      status: 'ready_for_boardroom_review',
      foundation_packet_ref: foundationPacket?.packet_id || foundationPacket?.business_id || null,
      financial_model: model,
      permissions: {
        discovery_read: true,
        external_writes: false,
        payments: false,
        filings: false,
        approval_required: true,
      },
      created_at: now(),
    }));
    return model;
  }

  function refresh() {
    const root = document.querySelector('[data-aion-finance-workspace="true"]');
    if (root) root.outerHTML = render();
  }

  function card(item, selected, attr) {
    return `<button type="button" ${attr}="${esc(item.id)}" aria-pressed="${selected}" style="text-align:left;padding:14px;border:${selected ? '2px solid #22c55e' : '1px solid rgba(125,211,252,.4)'};background:${selected ? 'rgba(20,83,45,.48)' : 'rgba(8,47,73,.42)'};color:#e2e8f0;cursor:pointer;min-height:92px"><strong style="display:block;color:${selected ? '#86efac' : '#7dd3fc'};font-size:14px">${esc(item.label)}</strong><span style="display:block;margin-top:7px;color:#cbd5e1;font-size:12px;line-height:1.4">${esc(item.description)}</span></button>`;
  }

  function packageHeader(state) {
    const label = state.status === 'complete' ? 'Financial model ready for Boardroom review' : 'Finance discovery and evidence capture in progress';
    return `<section style="border:2px solid #f59e0b;background:#fff;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:14px"><div><div style="color:#0f766e;font-size:11px;letter-spacing:.28em;text-transform:uppercase;font-weight:900">Boardroom Package</div><div style="font-size:20px;font-weight:900;color:#0f172a;margin-top:6px">Finance assignment package</div><div style="font-size:13px;font-weight:650;color:#475569;margin-top:6px">${esc(label)} · read-only discovery · approval gated</div></div><button type="button" data-aion-finance-package style="padding:12px 18px;background:#fff;border:1px solid rgba(15,23,42,.22);font-size:11px;letter-spacing:.18em;text-transform:uppercase;font-weight:900">Open Package</button></section>`;
  }

  function renderSources(state) {
    const platforms = schema.accountingPlatforms.map((x) => card(x, state.accounting_platforms.includes(x.id), 'data-aion-finance-accounting')).join('');
    const evidence = schema.evidenceSources.map((x) => card(x, state.evidence_sources.includes(x.id), 'data-aion-finance-evidence')).join('');
    const other = state.accounting_platforms.includes('other') ? `<label style="display:block;margin-top:12px;color:#bae6fd">Other accounting software<input data-aion-finance-other value="${esc(state.other_accounting_platform)}" placeholder="Enter software name" style="display:block;width:100%;box-sizing:border-box;margin-top:7px;padding:10px;background:#e2e8f0;color:#0f172a;border:0"></label>` : '';
    const files = state.source_records.length
      ? state.source_records.map((file) => `<div style="display:flex;justify-content:space-between;gap:12px;padding:7px 9px;border-top:1px solid rgba(56,189,248,.18)"><span style="color:#e2e8f0">${esc(file.name)}</span><span style="color:${file.status === 'committed_to_business_container' ? '#86efac' : file.status === 'upload_failed' ? '#fca5a5' : '#facc15'}">${esc(file.type_label)} · ${esc(file.status || 'upload pending')}</span></div>`).join('')
      : '<div style="color:#64748b;padding:8px 0">No local finance files staged.</div>';
    return `<div style="color:#86efac;font-weight:900;letter-spacing:.2em;text-transform:uppercase">&gt; Finance Setup · Existing Data Discovery</div><p style="color:#cbd5e1;line-height:1.55;max-width:900px">First, tell the Finance Pilot where the financial truth currently lives. Selecting a source records it for setup; it does not connect, change, or send any data.</p><div style="color:#facc15;margin:18px 0 10px;font-weight:800">&gt; Accounting software</div><div style="display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px">${platforms}</div>${other}<div style="color:#facc15;margin:22px 0 10px;font-weight:800">&gt; Other records available to Finance</div><div style="display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px">${evidence}</div><div style="margin-top:18px;border:1px solid rgba(56,189,248,.34);background:#07111f;padding:12px"><div style="display:flex;justify-content:space-between;align-items:center;gap:14px"><div><div style="color:#7dd3fc;font-weight:900">&gt; Add files to the Finance Business Container</div><div style="color:#94a3b8;margin-top:4px;font-size:12px">Original bytes, hash and receipt are stored first. Parsing and accepting extracted values remain separate permissions.</div></div><div style="display:flex;gap:8px;align-items:center"><select data-aion-finance-file-category style="background:#07111f;color:#bae6fd;border:1px solid #38bdf8;padding:8px"><option value="spreadsheets">Spreadsheets</option><option value="bank-statements">Bank Statements</option><option value="invoices-receipts">Invoices & Receipts</option><option value="management-accounts">Management Accounts</option><option value="vat-tax">VAT & Tax</option><option value="payroll">Payroll</option><option value="payment-processors">Payment Processors</option><option value="crm-sales">CRM & Sales</option></select><label style="padding:8px 12px;border:1px solid #38bdf8;color:#bae6fd;cursor:pointer">Choose files<input data-aion-finance-files type="file" multiple accept=".csv,.xlsx,.xls,.pdf,.ofx,.qif,.xml,.json" style="display:none"></label></div></div><div style="margin-top:8px">${files}</div></div><div style="display:flex;justify-content:flex-end;margin-top:22px"><button type="button" data-aion-finance-continue style="padding:11px 18px;background:#22c55e;color:#052e16;border:0;font-weight:900;letter-spacing:.12em;text-transform:uppercase;cursor:pointer">Save sources & begin discovery</button></div>`;
  }

  function renderDiscovery(state) {
    const question = schema.questions[state.question_index];
    if (!question) return renderReview(state);
    const history = state.transcript.slice(-4).map((turn) => `<div style="margin:7px 0"><span style="color:#94a3b8">&gt; You:</span> ${esc(turn.answer)}</div>`).join('');
    return `<div style="color:#86efac;font-weight:900;letter-spacing:.2em;text-transform:uppercase">&gt; Finance Pilot · Financial Discovery</div><div style="margin-top:16px;border:1px solid rgba(14,165,233,.55);background:rgba(8,47,73,.55);padding:14px 16px;line-height:1.55"><div style="color:#7dd3fc;font-weight:900;text-transform:uppercase;letter-spacing:.16em">&gt; Discovery Question Inbox</div><div>&gt; Answered: ${state.question_index} / ${schema.questions.length}</div><div>&gt; Sources selected: ${state.accounting_platforms.length + state.evidence_sources.length}</div><br><div style="color:#bae6fd">&gt; Current question: ${esc(question.prompt)}</div></div><div style="margin-top:16px;line-height:1.55">${history}<div style="color:#86efac;margin-top:12px">&gt; Finance Pilot: ${esc(question.prompt)}</div></div><div style="position:absolute;left:18px;right:18px;bottom:18px;display:flex;gap:10px;align-items:center"><span>&gt;</span><input data-aion-finance-answer placeholder="Answer the Finance Pilot..." style="flex:1;padding:9px;background:#cbd5e1;color:#0f172a;border:0"><button type="button" data-aion-finance-answer-send style="padding:9px 15px;font-weight:900;text-transform:uppercase">Send</button></div>`;
  }

  function renderReview(state) {
    const rows = schema.questions.map((q, index) => `<div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;padding:9px 0;border-bottom:1px solid rgba(148,163,184,.2)"><div><div style="color:#7dd3fc">${esc(q.prompt)}</div><div style="color:#e2e8f0;margin-top:4px">${esc(state.answers[q.id] || 'Not answered')}</div></div><button type="button" data-aion-finance-edit-answer="${index}" style="align-self:center;background:transparent;color:#7dd3fc;border:1px solid rgba(56,189,248,.5);padding:6px 9px">Edit</button></div>`).join('');
    return `<div style="color:#86efac;font-weight:900;letter-spacing:.2em;text-transform:uppercase">&gt; Finance Discovery · Review</div><p style="color:#cbd5e1">Review the captured baseline. Finalising creates the first Business Financial Model for the Boardroom; it does not authorise payments or external changes.</p><div style="max-height:380px;overflow:auto">${rows}</div><div style="display:flex;justify-content:space-between;margin-top:18px"><button data-aion-finance-back style="padding:10px 16px">Back</button><button data-aion-finance-finalise style="padding:10px 16px;background:#22c55e;color:#052e16;border:0;font-weight:900">Build Financial Model</button></div>`;
  }

  function renderComplete() {
    return `<div style="color:#86efac;font-weight:900;letter-spacing:.2em;text-transform:uppercase">&gt; Finance Pilot · Operational Stream</div><div style="margin-top:18px;border:1px solid rgba(34,197,94,.55);background:rgba(20,83,45,.32);padding:16px;line-height:1.55;color:#bbf7d0">&gt; Financial baseline captured.<br>&gt; Business Financial Model created for Boardroom review.<br>&gt; External actions remain approval gated.</div><p style="color:#cbd5e1;line-height:1.6">This stream is now the permanent direct portal to your Finance Pilot. Ask for finance updates, margins, cash position, fixed costs, debtor follow-up, or cost-reduction analysis.</p><div style="position:absolute;left:18px;right:18px;bottom:18px;display:flex;gap:10px"><span>&gt;</span><input disabled placeholder="Operational Finance conversation is the next module" style="flex:1;padding:9px;background:#94a3b8;color:#0f172a;border:0"><button disabled style="padding:9px 15px">Send</button></div>`;
  }

  function render() {
    const state = load();
    const body = state.status === 'data_sources' ? renderSources(state) : state.status === 'discovery' ? renderDiscovery(state) : state.status === 'review' ? renderReview(state) : renderComplete(state);
    return `<section class="panel large-panel" data-aion-finance-workspace="true" style="padding:16px;border:1px solid rgba(15,23,42,.14)">${packageHeader(state)}<section style="position:relative;background:#0f172a;color:#cbd5e1;min-height:590px;padding:18px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;box-shadow:inset 4px 0 0 #0284c7">${body}</section></section>`;
  }

  document.addEventListener('click', (event) => {
    const accounting = event.target.closest?.('[data-aion-finance-accounting]');
    const evidence = event.target.closest?.('[data-aion-finance-evidence]');
    const action = event.target.closest?.('[data-aion-finance-continue],[data-aion-finance-answer-send],[data-aion-finance-back],[data-aion-finance-finalise],[data-aion-finance-package],[data-aion-finance-edit-answer]');
    if (!accounting && !evidence && !action) return;
    event.preventDefault();
    let state = load();
    if (accounting) {
      const id = accounting.dataset.aionFinanceAccounting;
      let values = toggle(state.accounting_platforms, id);
      if (id === 'none' && values.includes('none')) values = ['none'];
      else if (id !== 'none') values = values.filter((x) => x !== 'none');
      state.accounting_platforms = values;
    } else if (evidence) {
      state.evidence_sources = toggle(state.evidence_sources, evidence.dataset.aionFinanceEvidence);
    } else if (action.matches('[data-aion-finance-continue]')) {
      state.status = 'discovery';
    } else if (action.matches('[data-aion-finance-answer-send]')) {
      const input = document.querySelector('[data-aion-finance-answer]');
      const answer = String(input?.value || '').trim();
      if (!answer) return;
      const question = schema.questions[state.question_index];
      state.answers[question.id] = answer;
      state.transcript.push({ question_id: question.id, prompt: question.prompt, answer, captured_at: now() });
      state.question_index += 1;
      const allAnswered = schema.questions.every((item) => String(state.answers[item.id] || '').trim());
      state.status = allAnswered || state.question_index >= schema.questions.length ? 'review' : 'discovery';
    } else if (action.matches('[data-aion-finance-back]')) {
      state.status = 'discovery';
      state.question_index = Math.max(0, schema.questions.length - 1);
    } else if (action.matches('[data-aion-finance-edit-answer]')) {
      state.status = 'discovery';
      state.question_index = Number(action.dataset.aionFinanceEditAnswer || 0);
    } else if (action.matches('[data-aion-finance-finalise]')) {
      state.status = 'complete';
      state.completed_at = now();
      buildBusinessFinancialModel(state);
    } else if (action.matches('[data-aion-finance-package]')) {
      const model = localStorage.getItem(MODEL_KEY);
      alert(model ? 'Finance package is ready in the Business Financial Model.' : 'Finance discovery must be completed before this package is ready.');
      return;
    }
    save(state); refresh();
  }, true);

  document.addEventListener('change', (event) => {
    if (event.target.matches?.('[data-aion-finance-other]')) {
      const state = load(); state.other_accounting_platform = String(event.target.value || '').trim(); save(state); return;
    }
    if (event.target.matches?.('[data-aion-finance-files]')) {
      const state = load();
      const category = String(document.querySelector('[data-aion-finance-file-category]')?.value || 'spreadsheets');
      const existing = new Set(state.source_records.map((item) => `${item.name}:${item.size}`));
      const uploads = [];
      Array.from(event.target.files || []).forEach((file) => {
        const signature = `${file.name}:${file.size}`;
        if (existing.has(signature)) return;
        const item = {
          id: `finance_source_${Date.now()}_${Math.random().toString(16).slice(2)}`,
          name: file.name,
          size: file.size,
          mime_type: file.type || 'application/octet-stream',
          type_label: (file.name.split('.').pop() || 'file').toUpperCase(),
          category,
          status: 'upload_pending',
          local_path_stored: false,
          content_stored: false,
          selected_at: now(),
        };
        state.source_records.push(item);
        uploads.push({ file, itemId: item.id });
      });
      save(state); refresh();
      uploads.forEach(({ file, itemId }) => {
        global.AionBusinessContainerClient?.uploadFinanceArtifact?.(file, category)
          .then((result) => {
            const latest = load();
            latest.source_records = latest.source_records.map((item) => item.id === itemId ? {
              ...item,
              status: 'committed_to_business_container',
              local_path_stored: true,
              content_stored: true,
              canonical_record: result.record,
              file_cabinet_pointer: result.file_cabinet_pointer,
            } : item);
            save(latest); refresh();
          })
          .catch((error) => {
            const latest = load();
            latest.source_records = latest.source_records.map((item) => item.id === itemId ? { ...item, status: 'upload_failed', error: String(error) } : item);
            save(latest); refresh();
          });
      });
    }
  }, true);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target.matches?.('[data-aion-finance-answer]')) {
      event.preventDefault(); document.querySelector('[data-aion-finance-answer-send]')?.click();
    }
  }, true);

  global.AionFinancePilot = { load, save, render, buildBusinessFinancialModel, reset: () => { localStorage.removeItem(STORAGE_KEY); localStorage.removeItem(MODEL_KEY); localStorage.removeItem(BOARDROOM_PACKET_KEY); refresh(); } };
})(window);
