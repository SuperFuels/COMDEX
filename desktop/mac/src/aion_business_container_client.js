(function installAionBusinessContainerClient(global) {
  'use strict';

  const API_BASE = 'http://127.0.0.1:8080';
  const FOUNDATION_KEY = 'aion.businessTwin.foundationPacket.v1';
  const SYNC_PREFIX = 'aion.businessContainer.sync.';
  let financeSyncTimer = null;

  function clean(value) { return String(value || '').trim(); }

  function canonicalBusinessId(value) {
    const normalized = clean(value).toLowerCase().replaceAll('_', '-').replace(/[^a-z0-9-]+/g, '-').replace(/-+/g, '-').replace(/^-+|-+$/g, '');
    return normalized && !['global', 'root', 'tmp', 'temp', 'business-not-registered'].includes(normalized) ? normalized : '';
  }

  function readFoundationPacket() {
    try { return JSON.parse(localStorage.getItem(FOUNDATION_KEY) || 'null'); } catch { return null; }
  }

  function resolveBusinessId(packetInput) {
    const packet = packetInput && typeof packetInput === 'object' ? packetInput : readFoundationPacket() || {};
    const draft = packet.foundation_draft || {};
    const candidates = [
      packet.business_id,
      packet.workspace_id,
      draft.business_id,
      draft.business_name,
      global.__AION_DESKTOP_STATE__?.workspaceId,
      global.state?.workspaceId,
    ];
    for (const candidate of candidates) {
      const value = canonicalBusinessId(candidate);
      if (value) return value;
    }
    return '';
  }

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { Accept: 'application/json', ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(options.headers || {}) },
    });
    if (!response.ok) throw new Error(`Business Container request failed ${response.status}: ${await response.text()}`);
    return response.json();
  }

  async function commitFoundationPacket(packetInput) {
    const packet = packetInput && typeof packetInput === 'object' ? packetInput : readFoundationPacket();
    if (!packet) return { ok: false, reason: 'foundation_packet_missing' };
    const businessId = resolveBusinessId(packet);
    if (!businessId) return { ok: false, reason: 'registered_business_id_missing' };
    const result = await request(`/api/aion/business/data/foundation/${encodeURIComponent(businessId)}`, {
      method: 'POST',
      body: JSON.stringify({ packet, source: 'desktop_business_foundation' }),
    });
    localStorage.setItem(`${SYNC_PREFIX}foundation.${businessId}`, JSON.stringify({ synced_at: new Date().toISOString(), receipts: result.containers || {} }));
    global.__aionCanonicalBusinessId = result.business_id;
    return result;
  }

  function financeModelFromState(state) {
    const answers = state.answers || {};
    return {
      model_status: state.status === 'complete' ? 'complete' : 'discovery_in_progress',
      currency: answers.currency || null,
      period_basis: 'annual',
      discovery_state: state,
      revenue_model: {
        charging_and_prices: answers.revenue_model || null,
        average_monthly_revenue: answers.revenue_monthly || null,
        revenue_pattern: answers.revenue_pattern || null,
      },
      direct_cost_model: { direct_costs: answers.direct_costs || null, owner_labour: answers.labour_owner || null },
      overhead_model: { fixed_costs: answers.fixed_costs || null },
      cashflow_model: { cash_position: answers.cash_position || null, receivables: answers.receivables || null, payables: answers.payables || null },
      tax_context: { tax_and_vat: answers.tax_vat || null, debt_and_finance: answers.debt_finance || null },
      integration_evidence: {
        accounting_platforms: state.accounting_platforms || [],
        other_accounting_platform: state.other_accounting_platform || '',
        evidence_sources: state.evidence_sources || [],
      },
      metrics: {},
      assumptions: [],
      missing_information: [],
      evidence_refs: (state.source_records || []).filter((item) => item.canonical_record).map((item) => item.canonical_record),
      provenance: { source: 'finance_pilot_discovery', updated_at: new Date().toISOString() },
      completion_receipt: state.status === 'complete' ? { completed_at: state.completed_at, source: 'finance_pilot' } : {},
    };
  }

  function financeFactsFromState(state) {
    return Object.entries(state.answers || {}).map(([field, value]) => ({
      function: 'finance',
      field,
      category: field.split('_')[0] || 'finance',
      value,
      classification: 'founder_provided_fact',
      confidence: 0.88,
      verification_status: 'unverified',
      source_ref: `finance_discovery:${field}`,
      evidence_refs: [],
      observed_at: new Date().toISOString(),
    }));
  }

  async function syncFinanceStateNow(state) {
    const businessId = resolveBusinessId();
    if (!businessId) return { ok: false, reason: 'registered_business_id_missing' };
    const financeModel = financeModelFromState(state);
    const modelResult = await request(`/api/aion/business/data/finance-model/${encodeURIComponent(businessId)}`, {
      method: 'PUT', body: JSON.stringify({ payload: financeModel, source: 'desktop_finance_pilot' }),
    });
    const ledgerResult = await request(`/api/aion/business/data/department-intelligence/${encodeURIComponent(businessId)}`, {
      method: 'PUT',
      body: JSON.stringify({
        payload: {
          departments: {
            finance: {
              department: 'finance',
              status: state.status,
              discovery: state.answers || {},
              integration_state: {
                accounting_platforms: state.accounting_platforms || [],
                evidence_sources: state.evidence_sources || [],
              },
              evidence: state.source_records || [],
              model_ref: modelResult.receipt || {},
              boardroom_summary: `Finance discovery ${state.question_index || 0}/${global.AionFinanceDiscoverySchema?.questions?.length || 0}; status ${state.status}.`,
              updated_at: new Date().toISOString(),
            },
          },
        },
        source: 'desktop_finance_pilot',
      }),
    });
    const mapResult = await request(`/api/aion/business/data/business-map/${encodeURIComponent(businessId)}/facts`, {
      method: 'POST', body: JSON.stringify({ facts: financeFactsFromState(state), source: 'desktop_finance_pilot' }),
    });
    const sync = { synced_at: new Date().toISOString(), finance_model: modelResult.receipt, department_intelligence: ledgerResult.receipt, business_map: mapResult.receipt };
    localStorage.setItem(`${SYNC_PREFIX}finance.${businessId}`, JSON.stringify(sync));
    global.dispatchEvent(new CustomEvent('aion:finance-container-synced', { detail: sync }));
    return { ok: true, business_id: businessId, ...sync };
  }

  function syncFinanceState(state, delay = 350) {
    clearTimeout(financeSyncTimer);
    financeSyncTimer = setTimeout(() => {
      syncFinanceStateNow(state).catch((error) => {
        console.warn('[AION] Finance Business Container sync failed; local cache retained', error);
        global.dispatchEvent(new CustomEvent('aion:finance-container-sync-failed', { detail: { error: String(error) } }));
      });
    }, delay);
  }

  async function uploadFinanceArtifact(file, category) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    const body = new FormData();
    body.append('category', category || 'spreadsheets');
    body.append('file', file, file.name);
    return request(`/api/aion/business/data/finance-artifacts/${encodeURIComponent(businessId)}`, { method: 'POST', body });
  }

  async function getBoardroomContext() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/boardroom-context/${encodeURIComponent(businessId)}`);
  }

  async function bootstrap() {
    const packet = readFoundationPacket();
    if (!packet) return;
    const businessId = resolveBusinessId(packet);
    if (!businessId) return;
    if (localStorage.getItem(`${SYNC_PREFIX}foundation.${businessId}`)) {
      global.__aionCanonicalBusinessId = businessId;
    } else {
      try { await commitFoundationPacket(packet); }
      catch (error) { console.warn('[AION] Canonical Foundation commit deferred until backend is available', error); }
    }
    try {
      const financeState = JSON.parse(localStorage.getItem('aion.financePilot.discoveryState.v1') || 'null');
      if (financeState && typeof financeState === 'object') await syncFinanceStateNow(financeState);
    } catch (error) {
      console.warn('[AION] Canonical Finance resume sync deferred until backend is available', error);
    }
  }

  global.AionBusinessContainerClient = { canonicalBusinessId, resolveBusinessId, commitFoundationPacket, syncFinanceState, syncFinanceStateNow, uploadFinanceArtifact, getBoardroomContext };
  setTimeout(bootstrap, 600);
})(window);
