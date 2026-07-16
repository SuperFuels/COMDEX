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
        background:#0f172a !important;
        color:#cbd5e1 !important;
        border:1px solid rgba(14,165,233,.52) !important;
        box-shadow:inset 4px 0 0 #0284c7 !important;
        padding:18px !important;
        min-height:0 !important;
        margin-top:0 !important;
        display:grid !important;
        grid-template-rows:auto auto minmax(320px,auto) auto !important;
        gap:0 !important;
        font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header {
        background:#0f172a !important;
        border:0 !important;
        border-bottom:1px solid rgba(56,189,248,.34) !important;
        padding:0 0 14px !important;
      }
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header h2,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header p,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-window,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-message,
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-message p {
        color:#cbd5e1 !important;
      }
      [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-header h2 { color:#86efac !important; }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-stream-window {
        background:#07111f !important;
        border:1px solid rgba(56,189,248,.28) !important;
        min-height:320px !important;
        padding:18px !important;
        margin:0 !important;
      }
      [data-aion-shared-pilot-terminal="true"] textarea {
        background:#07111f !important;
        color:#e2e8f0 !important;
        border:1px solid rgba(56,189,248,.42) !important;
      }
      [data-aion-shared-pilot-terminal="true"] button[data-aion-pilot-create-draft-mission] {
        background:#22c55e !important;
        color:#052e16 !important;
        border:1px solid #86efac !important;
      }
      .aion-shared-pilot-role-context {
        display:flex;
        flex-wrap:wrap;
        gap:8px 14px;
        margin:0;
        padding:11px 12px;
        background:#07111f;
        border:1px solid rgba(56,189,248,.28);
        color:#94a3b8 !important;
        font-size:12px;
        line-height:1.5;
      }
      .aion-shared-pilot-role-context strong { color:#7dd3fc !important; }
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
        background:#0f172a !important;
        border:0 !important;
        border-top:1px solid rgba(56,189,248,.34) !important;
        padding:14px 0 0 !important;
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
        min-height:68px !important;
        height:68px !important;
        margin:0 !important;
        padding:13px 14px !important;
        resize:vertical !important;
        background:#07111f !important;
        color:#e2e8f0 !important;
        -webkit-text-fill-color:#e2e8f0 !important;
        border:1px solid rgba(56,189,248,.42) !important;
        border-radius:0 !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar textarea[data-aion-pilot-mission-input]::placeholder {
        color:#64748b !important;
        -webkit-text-fill-color:#64748b !important;
        opacity:1 !important;
      }
      html body [data-aion-shared-pilot-terminal="true"] .aion-pilot-composer-bar button[data-aion-pilot-create-draft-mission] {
        display:block !important;
        min-width:132px !important;
        min-height:48px !important;
        margin:0 !important;
        padding:12px 18px !important;
        background:#22c55e !important;
        color:#052e16 !important;
        -webkit-text-fill-color:#052e16 !important;
        border:1px solid #86efac !important;
        border-radius:0 !important;
        opacity:1 !important;
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
