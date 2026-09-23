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
      global.__aionCanonicalBusinessId,
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
    const calculated = global.AionFinanceModelBuilder?.build?.(state) || {};
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
      pricing_model: calculated.pricing_model || {},
      direct_cost_model: { direct_costs: answers.direct_costs || null, owner_labour: answers.labour_owner || null, ...(calculated.direct_cost_model || {}) },
      overhead_model: { fixed_costs: answers.fixed_costs || null },
      cashflow_model: {
        cash_position: answers.cash_position || null,
        minimum_cash_buffer_policy: answers.cash_buffer_policy || null,
        receivables: answers.receivables || null,
        payables: answers.payables || null,
        unrecorded_liabilities: answers.unrecorded_liabilities || null,
      },
      tax_context: { tax_and_vat: answers.tax_context || answers.tax_vat || null, debt_and_finance: answers.debt_finance || null },
      integration_evidence: {
        accounting_platforms: state.accounting_platforms || [],
        other_accounting_platform: state.other_accounting_platform || '',
        evidence_sources: state.evidence_sources || [],
      },
      capacity_model: calculated.capacity_model || {},
      metrics: calculated.metrics || {},
      assumptions: calculated.assumptions || [],
      missing_information: calculated.missing_information || [],
      evidence_refs: (state.source_records || []).filter((item) => item.canonical_record).map((item) => item.canonical_record),
      provenance: { source: 'finance_pilot_discovery', updated_at: new Date().toISOString() },
      completion_receipt: state.status === 'complete' ? { completed_at: state.completed_at, source: 'finance_pilot' } : {},
      finance_priorities: answers.finance_priorities || null,
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
            ...(state.status === 'complete' ? {
              operations: {
                department: 'operations',
                status: 'ready_to_activate',
                unlocked_by: 'business_twin_orchestrator',
                predecessor: 'finance',
                activation_requires_user_or_orchestrator_route: true,
                updated_at: new Date().toISOString(),
              },
              boardroom: {
                department: 'boardroom',
                status: 'finance_context_ready',
                finance_model_ref: modelResult.receipt || {},
                provider_memory_mutation_allowed: false,
                updated_at: new Date().toISOString(),
              },
            } : {}),
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

  async function listFinanceArtifacts() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/finance-artifacts/${encodeURIComponent(businessId)}`);
  }

  async function analyseFinanceArtifact(artifactId) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/finance-artifacts/${encodeURIComponent(businessId)}/${encodeURIComponent(artifactId)}/analyse`, { method: 'POST' });
  }

  async function acceptFinanceArtifactFacts(artifactId, factIds = []) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/finance-artifacts/${encodeURIComponent(businessId)}/${encodeURIComponent(artifactId)}/accept`, {
      method: 'POST',
      body: JSON.stringify({ fact_ids: Array.isArray(factIds) ? factIds : [] }),
    });
  }

  async function getXeroStatus() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/integrations/xero/${encodeURIComponent(businessId)}/status`);
  }

  async function connectXero() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/integrations/xero/${encodeURIComponent(businessId)}/connect`, { method: 'POST' });
  }

  async function selectXeroTenant(tenantId) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/integrations/xero/${encodeURIComponent(businessId)}/tenant`, {
      method: 'POST', body: JSON.stringify({ tenant_id: String(tenantId || '') }),
    });
  }

  async function syncXero() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/integrations/xero/${encodeURIComponent(businessId)}/sync`, { method: 'POST' });
  }

  async function disconnectXero() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/integrations/xero/${encodeURIComponent(businessId)}`, { method: 'DELETE' });
  }

  async function getBoardroomContext() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/boardroom-context/${encodeURIComponent(businessId)}`);
  }

  async function getOperatingModel() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/operating-model/${encodeURIComponent(businessId)}`);
  }

  async function completeFinanceFoundation() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/finance-completion/${encodeURIComponent(businessId)}`, {
      method: 'POST',
    });
  }

  async function saveOperatingModel(payload, expectedRevision = null) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/operating-model/${encodeURIComponent(businessId)}`, {
      method: 'PUT',
      body: JSON.stringify({
        payload: payload && typeof payload === 'object' ? payload : {},
        source: 'desktop_products_services_workspace',
        expected_revision: expectedRevision,
      }),
    });
  }

  async function importOperatingModelSpreadsheet(file, category) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    const body = new FormData();
    body.append('category', category);
    body.append('file', file, file.name);
    return request(`/api/aion/business/data/operating-model/${encodeURIComponent(businessId)}/import`, { method: 'POST', body });
  }

  async function askFinanceAgent(userText) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/finance-agent/${encodeURIComponent(businessId)}/turn`, {
      method: 'POST', body: JSON.stringify({ user_text: String(userText || '').trim() }),
    });
  }

  async function getBusinessMap(candidate) {
    const businessId = canonicalBusinessId(candidate) || resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/business-map/${encodeURIComponent(businessId)}`);
  }

  async function getBusinessKnowledge() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/business-knowledge/${encodeURIComponent(businessId)}`);
  }

  async function addBusinessKnowledgeText({ title, text, scopes, confidentiality } = {}) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/business-knowledge/${encodeURIComponent(businessId)}/text`, {
      method: 'POST',
      body: JSON.stringify({
        title: String(title || 'Owner-provided business knowledge'),
        text: String(text || ''),
        scopes: Array.isArray(scopes) && scopes.length ? scopes : ['all'],
        confidentiality: String(confidentiality || 'internal'),
      }),
    });
  }

  async function uploadBusinessKnowledgeFile(file, { scopes, confidentiality } = {}) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    const body = new FormData();
    body.append('file', file, file.name);
    body.append('scopes', (Array.isArray(scopes) && scopes.length ? scopes : ['all']).join(','));
    body.append('confidentiality', String(confidentiality || 'internal'));
    return request(`/api/aion/business/data/business-knowledge/${encodeURIComponent(businessId)}/file`, { method: 'POST', body });
  }

  async function approveBusinessKnowledgeClaims(claimIds = []) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/business-knowledge/${encodeURIComponent(businessId)}/claims/approve`, {
      method: 'POST',
      body: JSON.stringify({ claim_ids: Array.isArray(claimIds) ? claimIds : [], actor: 'business_owner' }),
    });
  }

  async function searchBusinessKnowledge(query, actorScope = 'pilot', limit = 8) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/business-knowledge/${encodeURIComponent(businessId)}/search`, {
      method: 'POST',
      body: JSON.stringify({ query: String(query || ''), actor_scope: String(actorScope || 'pilot'), limit }),
    });
  }

  async function getOrganizationAuthority() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/organisation/${encodeURIComponent(businessId)}`);
  }

  async function getPilotScheduledWork() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/pilot/scheduled-work/${encodeURIComponent(businessId)}`);
  }

  async function createPilotScheduledWork(payload = {}) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/pilot/scheduled-work/${encodeURIComponent(businessId)}`, {
      method: 'POST', body: JSON.stringify(payload),
    });
  }

  async function setPilotScheduledWorkEnabled(scheduleId, enabled, changedByPersonId) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/pilot/scheduled-work/${encodeURIComponent(businessId)}/${encodeURIComponent(scheduleId)}/enabled`, {
      method: 'POST', body: JSON.stringify({ enabled: enabled === true, changed_by_person_id: String(changedByPersonId || '') }),
    });
  }

  async function runPilotScheduledWork(scheduleId) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/pilot/scheduled-work/${encodeURIComponent(businessId)}/${encodeURIComponent(scheduleId)}/run`, { method: 'POST' });
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

  global.AionBusinessContainerClient = {
    canonicalBusinessId, resolveBusinessId, commitFoundationPacket,
    syncFinanceState, syncFinanceStateNow,
    uploadFinanceArtifact, listFinanceArtifacts, analyseFinanceArtifact, acceptFinanceArtifactFacts,
    getXeroStatus, connectXero, selectXeroTenant, syncXero, disconnectXero,
    getOperatingModel, saveOperatingModel, importOperatingModelSpreadsheet, completeFinanceFoundation,
    getBoardroomContext, askFinanceAgent, getBusinessMap,
    getBusinessKnowledge, addBusinessKnowledgeText, uploadBusinessKnowledgeFile,
    approveBusinessKnowledgeClaims, searchBusinessKnowledge,
    getOrganizationAuthority, getPilotScheduledWork, createPilotScheduledWork,
    setPilotScheduledWorkEnabled, runPilotScheduledWork,
  };
  setTimeout(bootstrap, 600);
})(window);
