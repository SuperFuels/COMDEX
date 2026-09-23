(function installAionDepartmentPilotRuntime(global) {
  'use strict';

  const DEPARTMENT_ROLES = Object.freeze({
    marketing: {
      label: 'Marketing',
      pilot_id: 'marketing_pilot',
      remit: 'Demand, positioning, campaigns, content, channels and lead generation.',
      permissions: ['read_business_context', 'read_marketing_graph', 'draft_marketing_assets', 'stage_marketing_work'],
    },
    sales: {
      label: 'Sales',
      pilot_id: 'sales_pilot',
      remit: 'Pipeline, qualification, quoting, conversion, follow-up and revenue coordination.',
      permissions: ['read_business_context', 'read_sales_graph', 'read_commerce_sources', 'draft_sales_assets', 'stage_sales_work'],
    },
    finance: {
      label: 'Finance',
      pilot_id: 'finance_pilot',
      remit: 'Pricing, costs, cash, margin, forecasts, controls and financial reporting.',
      permissions: ['read_business_context', 'read_finance_graph', 'read_finance_model', 'stage_finance_work'],
    },
    operations: {
      label: 'Operations',
      pilot_id: 'operations_pilot',
      remit: 'Delivery, capacity, scheduling, suppliers, workflows and operational risk.',
      permissions: ['read_business_context', 'read_operations_graph', 'draft_operating_assets', 'stage_operations_work'],
    },
    support: {
      label: 'Support',
      pilot_id: 'support_pilot',
      remit: 'Customer questions, service quality, complaints, retention and escalation.',
      permissions: ['read_business_context', 'read_support_graph', 'draft_support_assets', 'stage_support_work'],
    },
    hr: {
      label: 'HR',
      pilot_id: 'hr_pilot',
      remit: 'People, roles, accountability, permissions, capacity, hiring, training and policy.',
      permissions: ['read_business_context', 'read_hr_graph', 'draft_people_assets', 'stage_hr_work'],
    },
    pilot: {
      label: 'Central',
      pilot_id: 'central_pilot',
      remit: 'Cross-functional coordination, Boardroom action routing, progress and escalation.',
      permissions: ['read_business_context', 'read_department_graphs', 'route_approved_work', 'stage_cross_function_work'],
    },
  });

  const safeParse = (raw, fallback = null) => {
    try { return JSON.parse(raw); } catch { return fallback; }
  };

  function normaliseDepartment(value) {
    const key = String(value || '').trim().toLowerCase();
    return DEPARTMENT_ROLES[key] ? key : 'pilot';
  }

  function getRole(value) {
    const department = normaliseDepartment(value);
    return { department, ...DEPARTMENT_ROLES[department] };
  }

  function getDepartmentIntelligence(department) {
    const ledger = safeParse(global.localStorage?.getItem?.('aion.departmentIntelligence.v1') || '', {}) || {};
    return ledger[department] && typeof ledger[department] === 'object' ? ledger[department] : {};
  }

  function getFoundationPacket() {
    return safeParse(global.localStorage?.getItem?.('aion.businessTwin.foundationPacket.v1') || '', {}) || {};
  }

  function getGraphContext(department) {
    try {
      if (typeof global.getAionActiveGoalLoopDepartmentContext === 'function') {
        return global.getAionActiveGoalLoopDepartmentContext(department) || {};
      }
    } catch {}
    return {};
  }

  function getContext(value) {
    const role = getRole(value);
    const intelligence = role.department === 'pilot' ? {} : getDepartmentIntelligence(role.department);
    const graph = role.department === 'pilot' ? {} : getGraphContext(role.department);
    const foundation = getFoundationPacket();
    const businessName =
      foundation?.business?.business_name ||
      foundation?.business_name ||
      foundation?.company_name ||
      'Current business';

    return {
      role,
      business_name: businessName,
      graph_status: graph?.status || (role.department === 'pilot' ? 'cross_function' : 'no_goal_loop_assignment'),
      graph_id: graph?.child_canvas_id || graph?.goal_loop_id || graph?.master_canvas_id || '',
      board_goal: graph?.board_goal?.title || graph?.board_goal?.goal || '',
      department_sub_goal: graph?.department_sub_goal || '',
      intelligence_status: intelligence?.status || (role.department === 'pilot' ? 'coordinating' : 'needs_discovery'),
      boardroom_summary: intelligence?.boardroom_summary || '',
      permissions: role.permissions,
      external_actions_approval_gated: true,
    };
  }

  function installStyles() {
    if (!global.document) return;
    // Re-append on each department render so this scoped runtime remains the
    // final authority after the legacy compatibility styles have installed.
    global.document.getElementById('aion-department-pilot-runtime-styles')?.remove();
    const style = global.document.createElement('style');
    style.id = 'aion-department-pilot-runtime-styles';
    style.textContent = `
      html body:has([data-aion-o14p-live-agents-dashboard]) #aion-glyph-workflow-top-tabs-v2 {
        display:none !important;
        visibility:hidden !important;
        pointer-events:none !important;
      }
      [data-aion-shared-pilot-terminal="true"] {
        background:#ffffff !important;
        color:#14243a !important;
        border:1px solid #d7e5f4 !important;
        border-top:3px solid #78c6ff !important;
        box-shadow:0 18px 48px rgba(35,72,112,.08) !important;
        padding:0 !important;
        min-height:0 !important;
        margin-top:0 !important;
        display:grid !important;
        grid-template-rows:auto auto auto minmax(320px,auto) auto !important;
        gap:0 !important;
        font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header {
        background:#ffffff !important;
        border:0 !important;
        border-bottom:1px solid #e2ecf6 !important;
        padding:30px 32px 24px !important;
      }
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header h2,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header p,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-window,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-message,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-message p {
        color:#425875 !important;
      }
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header h2 {
        color:#101c2c !important;
        font-size:34px !important;
        line-height:1.05 !important;
        margin:7px 0 9px !important;
      }
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header p {
        max-width:820px !important;
        font-size:15px !important;
      }
      .aion-pilot-workspace-kicker {
        color:#1676c5;
        font-size:11px;
        font-weight:900;
        letter-spacing:.18em;
        text-transform:uppercase;
      }
      .aion-pilot-workspace-state {
        display:inline-flex;
        align-items:center;
        gap:8px;
        padding:8px 11px;
        color:#31506d;
        background:#f3f8fd;
        border:1px solid #cfe2f3;
        font-size:11px;
        font-weight:850;
        letter-spacing:.1em;
        text-transform:uppercase;
        white-space:nowrap;
      }
      .aion-pilot-workspace-state::before {
        content:"";
        width:8px;
        height:8px;
        border-radius:50%;
        background:#48c7a7;
        box-shadow:0 0 0 4px rgba(72,199,167,.14);
      }
      .aion-pilot-capability-path {
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        background:#f8fbfe;
        border-bottom:1px solid #e2ecf6;
        padding:0 32px;
      }
      .aion-pilot-capability-step {
        min-width:0;
        padding:15px 16px 16px 0;
        border-right:1px solid #dce8f3;
      }
      .aion-pilot-capability-step + .aion-pilot-capability-step { padding-left:16px; }
      .aion-pilot-capability-step:last-child { border-right:0; }
      .aion-pilot-capability-step span {
        display:block;
        margin-bottom:4px;
        color:#2788d4;
        font-size:10px;
        font-weight:900;
        letter-spacing:.14em;
        text-transform:uppercase;
      }
      .aion-pilot-capability-step strong {
        display:block;
        color:#1d3047;
        font-size:13px;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-window {
        background:#fbfdff !important;
        border:0 !important;
        min-height:320px !important;
        padding:28px 32px !important;
        margin:0 !important;
      }
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-message-system {
        width:min(760px,100%);
        box-sizing:border-box;
        padding:18px 20px !important;
        background:#eef7ff;
        border:1px solid #cfe5f7;
        border-left:4px solid #2da7ed;
      }
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-message-user {
        color:#14243a !important;
        background:#ffffff !important;
        border-color:#d7e5f4 !important;
        box-shadow:0 8px 28px rgba(35,72,112,.06);
      }
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-card,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-output-panel,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-panel,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-artifact-card,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-map-node,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-advanced-details {
        color:#273c55 !important;
        background:#ffffff !important;
        border-color:#d7e5f4 !important;
        box-shadow:none !important;
      }
      [data-aion-shared-pilot-terminal="true"] pre,
      [data-aion-shared-pilot-terminal="true"] code {
        color:#263e59 !important;
        background:#f5f9fc !important;
      }
      [data-aion-shared-pilot-terminal="true"] textarea {
        background:#ffffff !important;
        color:#17263a !important;
        border:1px solid #bcd2e5 !important;
      }
      [data-aion-shared-pilot-terminal="true"] button[data-aion-pilot-create-draft-mission] {
        background:#111d2d !important;
        color:#ffffff !important;
        border:1px solid #111d2d !important;
      }
      .aion-shared-pilot-role-context {
        display:flex;
        flex-wrap:wrap;
        gap:8px 14px;
        margin:0;
        padding:13px 32px;
        background:#ffffff;
        border:0;
        border-bottom:1px solid #e2ecf6;
        color:#6b7e93 !important;
        font-size:12px;
        line-height:1.5;
      }
      .aion-shared-pilot-role-context strong { color:#1c7bc5 !important; }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar {
        display:grid !important;
        grid-template-columns:minmax(0,1fr) auto !important;
        align-items:end !important;
        gap:12px !important;
        position:static !important;
        width:100% !important;
        height:auto !important;
        min-height:0 !important;
        max-height:none !important;
        visibility:visible !important;
        opacity:1 !important;
        overflow:visible !important;
        background:#ffffff !important;
        border:0 !important;
        border-top:1px solid #dbe8f3 !important;
        padding:18px 32px !important;
        margin:0 !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar::before {
        content:none !important;
        display:none !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar textarea[data-aion-pilot-mission-input] {
        display:block !important;
        box-sizing:border-box !important;
        width:100% !important;
        min-width:0 !important;
        min-height:62px !important;
        height:62px !important;
        margin:0 !important;
        padding:13px 14px !important;
        resize:vertical !important;
        background:#f8fbfe !important;
        color:#17263a !important;
        -webkit-text-fill-color:#17263a !important;
        border:1px solid #bcd2e5 !important;
        border-radius:7px !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar textarea[data-aion-pilot-mission-input]::placeholder {
        color:#718398 !important;
        -webkit-text-fill-color:#718398 !important;
        opacity:1 !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar button[data-aion-pilot-create-draft-mission] {
        display:block !important;
        min-width:132px !important;
        min-height:62px !important;
        margin:0 !important;
        padding:12px 18px !important;
        background:#111d2d !important;
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
        border:1px solid #111d2d !important;
        border-radius:7px !important;
        opacity:1 !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar button[data-aion-pilot-create-draft-mission]:hover {
        background:#187dcc !important;
        border-color:#187dcc !important;
      }
      .aion-pilot-workspace-nav {
        display:flex;
        align-items:center;
        gap:28px;
        padding:0 32px;
        min-height:52px;
        background:#fff;
        border-bottom:1px solid #dce9f4;
      }
      .aion-pilot-workspace-nav button {
        align-self:stretch;
        padding:0 2px;
        color:#60758c;
        background:transparent;
        border:0;
        border-bottom:2px solid transparent;
        font-size:13px;
        font-weight:800;
      }
      .aion-pilot-workspace-nav button:hover,
      .aion-pilot-workspace-nav button.is-active {
        color:#187dcc;
        border-bottom-color:#36aaf1;
      }
      .aion-pilot-command-panel {
        margin:0;
        padding:24px 32px;
        background:#f8fbfe;
        border-bottom:1px solid #dce9f4;
      }
      .aion-pilot-command-panel-heading {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:16px;
        margin-bottom:18px;
      }
      .aion-pilot-command-panel-heading span {
        display:block;
        margin-bottom:5px;
        color:#1885d1;
        font-size:9px;
        font-weight:900;
        letter-spacing:.16em;
      }
      .aion-pilot-command-panel-heading h3 {
        margin:0;
        color:#17263a;
        font-size:21px;
      }
      .aion-pilot-command-panel-heading small,
      .aion-pilot-command-panel-heading button {
        color:#6a7e94;
        background:#fff;
        border:1px solid #cdddeb;
        padding:9px 12px;
        font-size:11px;
        font-weight:800;
      }
      .aion-pilot-command-panel-heading .is-ready,
      .aion-pilot-capability-registry span.is-ready { color:#14845b; }
      .aion-pilot-quick-grid,
      .aion-pilot-list-grid {
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:10px;
      }
      .aion-pilot-quick-grid button,
      .aion-pilot-list-grid button {
        min-height:112px;
        padding:15px;
        text-align:left;
        color:#243a52;
        background:#fff;
        border:1px solid #d5e3ef;
        border-radius:7px;
      }
      .aion-pilot-quick-grid button:hover,
      .aion-pilot-list-grid button:hover {
        border-color:#7fc4f2;
        box-shadow:0 8px 20px rgba(38,117,180,.08);
      }
      .aion-pilot-quick-grid button span {
        display:block;
        margin-bottom:12px;
        color:#1885d1;
        font-size:9px;
        font-weight:900;
        letter-spacing:.12em;
        text-transform:uppercase;
      }
      .aion-pilot-quick-grid button strong,
      .aion-pilot-list-grid button strong { display:block; font-size:14px; }
      .aion-pilot-quick-grid button small,
      .aion-pilot-list-grid button small {
        display:block;
        margin-top:14px;
        color:#6c8298;
        font-size:10px;
      }
      .aion-pilot-list-grid button span { display:block; margin-top:7px; color:#6c8298; font-size:11px; line-height:1.45; }
      .aion-pilot-honesty-note {
        margin-bottom:16px;
        padding:12px 14px;
        color:#40566d;
        background:#eef7ff;
        border-left:3px solid #2da7ed;
        font-size:12px;
      }
      .aion-pilot-capability-registry {
        display:grid;
        grid-template-columns:repeat(2,minmax(0,1fr));
        gap:8px;
      }
      .aion-pilot-capability-registry article {
        padding:14px;
        background:#fff;
        border:1px solid #d5e3ef;
      }
      .aion-pilot-capability-registry article > div {
        display:flex;
        justify-content:space-between;
        gap:12px;
      }
      .aion-pilot-capability-registry article strong { color:#21364d; font-size:13px; }
      .aion-pilot-capability-registry article span { color:#9a6818; font-size:10px; font-weight:900; text-transform:uppercase; }
      .aion-pilot-capability-registry article p { margin:8px 0 0; color:#6b7e93; font-size:11px; line-height:1.5; }
      .aion-pilot-capability-registry article > select { box-sizing:border-box; width:100%; margin-top:10px; padding:9px 10px; color:#20364c; background:#fff; border:1px solid #cdddeb; font:inherit; }
      .aion-pilot-authority-limit { display:grid !important; grid-template-columns:minmax(0,1fr) 88px; gap:8px; margin-top:8px; }
      .aion-pilot-authority-limit input,
      .aion-pilot-authority-limit select { box-sizing:border-box; min-width:0; width:100%; padding:9px 10px; color:#20364c; background:#fff; border:1px solid #cdddeb; font:inherit; }
      .aion-pilot-knowledge-form { display:grid; grid-template-columns:minmax(0,1.4fr) minmax(260px,.8fr); gap:14px; margin-bottom:16px; }
      .aion-pilot-knowledge-inputs { display:grid; gap:8px; }
      .aion-pilot-knowledge-inputs input,
      .aion-pilot-knowledge-inputs textarea,
      .aion-pilot-knowledge-inputs select { box-sizing:border-box; width:100%; padding:11px 12px; color:#20364c; background:#fff; border:1px solid #cdddeb; font:inherit; }
      .aion-pilot-knowledge-scopes { display:flex; flex-wrap:wrap; align-content:flex-start; gap:7px 12px; margin:0; padding:12px; border:1px solid #d5e3ef; background:#fff; }
      .aion-pilot-knowledge-scopes legend { color:#587087; font-size:10px; font-weight:900; letter-spacing:.1em; text-transform:uppercase; }
      .aion-pilot-knowledge-scopes label { color:#435b73; font-size:11px; font-weight:700; }
      .aion-pilot-knowledge-actions { grid-column:1/-1; display:flex; gap:8px; flex-wrap:wrap; }
      .aion-pilot-knowledge-actions button,
      .aion-pilot-file-button,
      [data-aion-pilot-knowledge-approve] { padding:10px 13px; color:#175f95; background:#eef7ff; border:1px solid #bcdcf3; font-size:11px; font-weight:900; cursor:pointer; }
      .aion-pilot-knowledge-claims { display:grid; gap:7px; margin-top:10px; }
      .aion-pilot-knowledge-claims label { display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:10px; align-items:start; padding:10px; background:#fff; border:1px solid #dce7f0; color:#2f455b; font-size:12px; }
      .aion-pilot-knowledge-claims small { color:#71869a; font-size:9px; text-transform:uppercase; }
      .aion-pilot-empty-state { display:flex; flex-direction:column; gap:6px; padding:28px; color:#60758c; background:#fff; border:1px dashed #bfcfdd; }
      .aion-pilot-capability-path.is-hidden,
      .aion-pilot-stream-window.is-hidden { display:none !important; }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar {
        grid-template-columns:44px minmax(0,1fr) auto auto !important;
        align-items:center !important;
        position:sticky !important;
        bottom:0 !important;
        z-index:8 !important;
        box-shadow:0 -8px 22px rgba(24,71,113,.07) !important;
      }
      .aion-pilot-composer-plus {
        width:44px;
        height:44px;
        padding:0;
        color:#187dcc;
        background:#eef7ff;
        border:1px solid #bcdcf3;
        border-radius:50%;
        font-size:22px;
      }
      @media (max-width:900px) {
        .aion-pilot-knowledge-form { grid-template-columns:1fr; }
        .aion-pilot-knowledge-actions { grid-column:1; }
      }
      .aion-pilot-voice-controls { display:flex; align-items:center; gap:6px; }
      .aion-pilot-voice-controls button {
        min-height:40px;
        padding:8px 10px;
        color:#5c7086;
        background:#fff;
        border:1px solid #cadbea;
        border-radius:6px;
        font-size:11px;
        font-weight:800;
      }
      .aion-pilot-voice-controls button.is-active { color:#147bbb; background:#eaf6ff; border-color:#74bced; }
      .aion-pilot-voice-controls button.is-recording {
        color:#fff !important;
        background:#b91c1c !important;
        border-color:#991b1b !important;
      }
      @media (max-width:900px) {
        .aion-pilot-capability-path { grid-template-columns:repeat(2,minmax(0,1fr)); padding:0 20px; }
        .aion-pilot-capability-step:nth-child(2) { border-right:0; }
        html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header,
        html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-window { padding-left:20px !important; padding-right:20px !important; }
        .aion-shared-pilot-role-context { padding-left:20px; padding-right:20px; }
        .aion-pilot-command-panel { padding-left:20px; padding-right:20px; }
        .aion-pilot-quick-grid,.aion-pilot-list-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar { grid-template-columns:44px minmax(0,1fr) !important; padding:16px 20px !important; }
        .aion-pilot-voice-controls { grid-column:1 / -1; }
      }
    `;
    global.document.head.appendChild(style);
  }

  global.AionDepartmentPilotRuntime = {
    departments: Object.keys(DEPARTMENT_ROLES),
    getRole,
    getContext,
    normaliseDepartment,
    installStyles,
  };

  installStyles();
})(window);
