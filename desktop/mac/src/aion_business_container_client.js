(function installAionBusinessContainerClient(global) {
  'use strict';

  function apiBase() {
    return String(
      global.aionDesktop?.backendApiBase
      || global.__AION_DESKTOP_STATE__?.apiBase
      || global.__aionDesktopState?.apiBase
      || 'http://127.0.0.1:8080'
    ).replace(/\/+$/, '');
  }
  const FOUNDATION_KEY = 'aion.businessTwin.foundationPacket.v1';
  let financeSyncTimer = null;
  let foundationSaveChain = Promise.resolve();

  function queueFoundationPersistence(task) {
    const previous = global.__aionFoundationPersistenceQueue || Promise.resolve();
    const next = Promise.resolve(previous).catch(() => null).then(task);
    global.__aionFoundationPersistenceQueue = next;
    return next;
  }
  let trainAgentWorkspaceSaveChain = Promise.resolve();
  let businessWorkingStateSaveChain = Promise.resolve();
  let bootstrapReadyResolve;
  const bootstrapReady = new Promise((resolve) => { bootstrapReadyResolve = resolve; });
  let financeStateHydrated = false;
  let trainAgentWorkspaceHydrated = false;
  let founderNotesHydrated = false;
  let financeStateHydrationPromise = null;
  let trainAgentWorkspaceHydrationPromise = null;
  let founderNotesHydrationPromise = null;
  const TRAIN_AGENT_WORKFLOW_TABS_KEY = 'aion.workflow_builder.workflow_tabs.v1';
  const BUSINESS_WORKING_STATE_KEYS = new Set([
    'aion.chat.sessions.v3',
    'aion.chat.message_streams.v2',
    'aion.chat.messages.v1',
    'aion.workflow_builder.current_draft.v1',
    'aion.workflow_builder.closed_tab_ids.v1',
    'aion.workflow_builder.recent_tabs.v1',
    'aion.boardroom.discovery_answers.v1',
    'aion.chat.board_meeting_context.v1',
    'aion.businessEntryMode.v1',
    'aion.selectedBusinessEntryMode.v1',
    'aion.business_entry_mode.v1',
    'aion.finance.data_points.v1',
    'aion.goal_engine.multi_agent_execution_replay.history.v1',
    'aion.cooOperatingLedger.v1',
    'aion.executiveCoordination.v1',
    'tessaris.aion.executive-status.v2',
    'aion.boardroom.model_display_names.v1',
    'aion.boardroom.selected_provider_ids.v1',
    'aion.smallBusinessFoundationBoardroomStarted',
    'aion.business_twin.boardroom_activation_status.v1',
    'aion.businessTwin.progressionManifest.v1',
    'aion.legal.workspace.v1',
    'aion.centralApprovedBoardroomActions',
    'aion.centralPilotQueue',
    'aion.boardroom.nextMeeting.v1',
    'aion.boardroomCouncil.sessionArtifacts.v1',
    'aion.boardroomCouncil.userContext.v1',
    'aion.communicationStyle.v1',
    'aion.boardroom.baselineMeeting.completed.v1',
    'aion.workflow.glyph_capsules.v1',
    'aion.workflow_capsule.autonomy_state.v1',
    'aion.workflow.draft.v1',
    'tessaris.businessPaymentSettings.v1',
    'aion.voiceOnboarding.o19i.v1',
    'aion.voiceOnboarding.o19m.started.v1',
    'aion.voiceDiscovery.activeSessionId',
    'aion.o20c.conversationOpen',
    'aion.o20c.conversationMode',
    'aion.o20c.mode',
    'aion.boardroom.businessMapConfirmation.v1',
    'aion.boardroom.founderRatification.v1',
    'aion.finance.preferred.accounting_provider',
    'aion.marketingPilot.conversationTerminal.live',
    'aion.marketingPilot.conversationTerminal.v1',
    'aion.marketingPilot.discoveryQuestionIndex',
    'aion.departmentPilot.package.selected',
    'aion.departmentPilot.package.source',
    'aion.departmentPilot.package.status',
    'aion.departmentPilot.package.openedAt',
  ]);
  const BUSINESS_WORKING_STATE_PREFIXES = [
    'aion.pilot.runtimeState.',
    'aion.departmentPilot.conversationTerminal.',
  ];
  const BUSINESS_WORKING_STATE_DEPARTMENT_TERMINAL = /^aion\.[A-Za-z0-9_-]+\.conversationTerminal\.v1$/;
  const BUSINESS_WORKING_STATE_ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$/;
  const businessWorkingStateVersions = new Map();
  global.__aionBusinessWorkingStateJson = global.__aionBusinessWorkingStateJson || Object.create(null);

  function clean(value) { return String(value || '').trim(); }

  function canonicalBusinessId(value) {
    const normalized = clean(value).toLowerCase().replaceAll('_', '-').replace(/[^a-z0-9-]+/g, '-').replace(/-+/g, '-').replace(/^-+|-+$/g, '');
    return normalized && !['global', 'root', 'tmp', 'temp', 'business-not-registered'].includes(normalized) ? normalized : '';
  }

  function readFoundationPacket() {
    if (global.__aionFoundationPacket && typeof global.__aionFoundationPacket === 'object') {
      return global.__aionFoundationPacket;
    }
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

  function publishBusinessIdentity(businessId, businessName) {
    const canonical = canonicalBusinessId(businessId);
    if (!canonical) throw new Error('Registered business ID missing');
    global.__aionCanonicalBusinessId = canonical;
    global.dispatchEvent(new CustomEvent('aion:business-identity-established', {
      detail: { business_id: canonical, business_name: clean(businessName) },
    }));
    return canonical;
  }

  async function request(path, options = {}) {
    const response = await fetch(`${apiBase()}${path}`, {
      ...options,
      headers: { Accept: 'application/json', ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(options.headers || {}) },
    });
    if (!response.ok) {
      const error = new Error(`Business Container request failed ${response.status}: ${await response.text()}`);
      error.status = response.status;
      throw error;
    }
    return response.json();
  }

  async function getTrainAgentWorkspaceState(stateId) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/pilot-team/${encodeURIComponent(businessId)}/workspace-state/${encodeURIComponent(String(stateId || 'workspace-state'))}`);
  }

  async function getFounderNotes() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/founder-notes/${encodeURIComponent(businessId)}`);
  }

  async function saveFounderNotes(notes) {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/founder-notes/${encodeURIComponent(businessId)}`, {
      method: 'PUT',
      body: JSON.stringify({ notes: Array.isArray(notes) ? notes : [], actor_id: 'desktop-founder-notes' }),
    });
  }

  function isBusinessWorkingStateKey(key) {
    const value = String(key || '');
    if (!BUSINESS_WORKING_STATE_ID.test(value)) return false;
    return BUSINESS_WORKING_STATE_KEYS.has(value)
      || BUSINESS_WORKING_STATE_PREFIXES.some((prefix) => value.startsWith(prefix))
      || BUSINESS_WORKING_STATE_DEPARTMENT_TERMINAL.test(value);
  }

  function businessWorkingStateVersionKey(businessId, stateId) {
    return `${canonicalBusinessId(businessId)}:${String(stateId || '')}`;
  }

  async function listBusinessWorkingState() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/working-state/${encodeURIComponent(businessId)}`);
  }

  async function getBusinessWorkingState(stateId) {
    const businessId = resolveBusinessId();
    const safeStateId = String(stateId || '');
    if (!businessId) throw new Error('Registered business ID missing');
    if (!isBusinessWorkingStateKey(safeStateId)) throw new Error('Business working-state key is not registered');
    return request(`/api/aion/business/data/working-state/${encodeURIComponent(businessId)}/${encodeURIComponent(safeStateId)}`);
  }

  function saveBusinessWorkingState(stateId, encodedValue) {
    const safeStateId = String(stateId || '');
    const value = String(encodedValue ?? '');
    if (!isBusinessWorkingStateKey(safeStateId)) {
      return Promise.reject(new Error('Business working-state key is not registered'));
    }
    // Capture the authority boundary when the save is requested. Onboarding can
    // switch workspaces while earlier saves are still queued; resolving the
    // business later would write the old workspace's state into the new Vault.
    const businessId = resolveBusinessId();
    if (!businessId) return Promise.reject(new Error('Registered business ID missing'));
    const versionKey = businessWorkingStateVersionKey(businessId, safeStateId);
    businessWorkingStateSaveChain = businessWorkingStateSaveChain
      .catch(() => null)
      .then(async () => {
        const path = `/api/aion/business/data/working-state/${encodeURIComponent(businessId)}/${encodeURIComponent(safeStateId)}`;
        const write = async (expectedVersion) => {
          const body = {
            payload: {
              storage_key: safeStateId,
              value,
              encoding: 'local-storage-string',
            },
            actor_id: 'desktop:business-working-state',
          };
          if (Number.isInteger(expectedVersion)) body.expected_version = expectedVersion;
          return request(path, { method: 'PUT', body: JSON.stringify(body) });
        };
        try {
          const result = await write(businessWorkingStateVersions.get(versionKey));
          businessWorkingStateVersions.set(versionKey, Number(result?.version || 0));
          return result;
        } catch (error) {
          if (!String(error).includes(' 409:')) throw error;
          // Another authorised writer may have advanced the record. Refresh the
          // current revision and retry once; repeated conflicts remain fail-closed.
          const current = await request(path);
          const currentVersion = Number(current?.version || 0);
          businessWorkingStateVersions.set(versionKey, currentVersion);
          const result = await write(currentVersion);
          businessWorkingStateVersions.set(versionKey, Number(result?.version || 0));
          return result;
        }
      });
    return businessWorkingStateSaveChain;
  }

  async function deleteBusinessWorkingState(stateId) {
    const businessId = resolveBusinessId();
    const safeStateId = String(stateId || '');
    if (!businessId) throw new Error('Registered business ID missing');
    if (!isBusinessWorkingStateKey(safeStateId)) throw new Error('Business working-state key is not registered');
    const result = await request(`/api/aion/business/data/working-state/${encodeURIComponent(businessId)}/${encodeURIComponent(safeStateId)}`, {
      method: 'DELETE',
    });
    businessWorkingStateVersions.delete(businessWorkingStateVersionKey(businessId, safeStateId));
    return result;
  }

  function readBusinessWorkingStateString(stateId) {
    const safeStateId = String(stateId || '');
    if (!isBusinessWorkingStateKey(safeStateId)) return null;
    if (Object.prototype.hasOwnProperty.call(global.__aionBusinessWorkingStateJson, safeStateId)) {
      return global.__aionBusinessWorkingStateJson[safeStateId];
    }
    return global.localStorage?.getItem(safeStateId) ?? null;
  }

  function writeBusinessWorkingStateString(stateId, value) {
    const safeStateId = String(stateId || '');
    const encoded = String(value ?? '');
    if (!isBusinessWorkingStateKey(safeStateId)) throw new Error('Business working-state key is not registered');
    global.__aionBusinessWorkingStateJson[safeStateId] = encoded;
    saveBusinessWorkingState(safeStateId, encoded).catch((error) => {
      console.warn('[AION] Business working-state Vault save deferred; state remains in session memory', safeStateId, error);
    });
    return encoded;
  }

  function clearBusinessWorkingState(stateId) {
    const safeStateId = String(stateId || '');
    if (!isBusinessWorkingStateKey(safeStateId)) return false;
    delete global.__aionBusinessWorkingStateJson[safeStateId];
    deleteBusinessWorkingState(safeStateId).catch((error) => {
      if (!String(error).includes('404')) console.warn('[AION] Business working-state Vault delete deferred', safeStateId, error);
    });
    return true;
  }

  function saveTrainAgentWorkspaceState(stateId, payload) {
    const safePayload = payload && typeof payload === 'object' ? payload : {};
    trainAgentWorkspaceSaveChain = trainAgentWorkspaceSaveChain
      .catch(() => null)
      .then(async () => {
        const businessId = resolveBusinessId();
        if (!businessId) throw new Error('Registered business ID missing');
        return request(`/api/aion/business/pilot-team/${encodeURIComponent(businessId)}/workspace-state/${encodeURIComponent(String(stateId || 'workspace-state'))}`, {
          method: 'PUT',
          body: JSON.stringify({ payload: safePayload, saved_by: 'desktop:train-agent' }),
        });
      });
    return trainAgentWorkspaceSaveChain;
  }

  function readTrainAgentWorkflowTabsString() {
    if (typeof global.__aionTrainAgentWorkflowTabsJson === 'string') {
      return global.__aionTrainAgentWorkflowTabsJson;
    }
    return global.localStorage?.getItem(TRAIN_AGENT_WORKFLOW_TABS_KEY) ?? null;
  }

  function writeTrainAgentWorkflowTabsString(value) {
    const encoded = String(value ?? '');
    global.__aionTrainAgentWorkflowTabsJson = encoded;
    try {
      const parsed = JSON.parse(encoded || '{}');
      saveTrainAgentWorkspaceState('workflow-tabs', parsed).catch((error) => {
        console.warn('[AION] Train Agent workflow-tab Vault save deferred; state remains in session memory', error);
      });
    } catch (error) {
      console.warn('[AION] Train Agent workflow-tab state was not valid JSON', error);
    }
    return encoded;
  }

  function installTrainAgentWorkflowTabVaultShim() {
    if (global.__aionTrainAgentWorkflowTabVaultShimInstalled === true) return;
    global.__aionTrainAgentWorkflowTabVaultShimInstalled = true;
    const storage = global.localStorage;
    if (!storage) return;
    const prototype = Object.getPrototypeOf(storage);
    const nativeGet = prototype.getItem;
    const nativeSet = prototype.setItem;
    const nativeRemove = prototype.removeItem;

    prototype.getItem = function vaultAwareGetItem(key) {
      if (String(key) !== TRAIN_AGENT_WORKFLOW_TABS_KEY) {
        return nativeGet.call(this, key);
      }
      if (typeof global.__aionTrainAgentWorkflowTabsJson === 'string') {
        return global.__aionTrainAgentWorkflowTabsJson;
      }
      const legacy = nativeGet.call(this, key);
      if (legacy) {
        global.__aionTrainAgentWorkflowTabsJson = legacy;
        try {
          const parsed = JSON.parse(legacy);
          saveTrainAgentWorkspaceState('workflow-tabs', parsed).catch((error) => {
            console.warn('[AION] Legacy Train Agent workflow-tab Vault import deferred', error);
          });
          nativeRemove.call(this, key);
        } catch (error) {
          console.warn('[AION] Invalid legacy Train Agent workflow-tab cache ignored', error);
        }
      }
      return legacy;
    };

    prototype.setItem = function vaultAwareSetItem(key, value) {
      if (String(key) !== TRAIN_AGENT_WORKFLOW_TABS_KEY) {
        return nativeSet.call(this, key, value);
      }
      const encoded = String(value || '');
      global.__aionTrainAgentWorkflowTabsJson = encoded;
      nativeRemove.call(this, key);
      try {
        const parsed = JSON.parse(encoded || '{}');
        saveTrainAgentWorkspaceState('workflow-tabs', parsed).catch((error) => {
          console.warn('[AION] Train Agent workflow-tab Vault save deferred', error);
        });
      } catch (error) {
        console.warn('[AION] Train Agent workflow-tab state was not valid JSON', error);
      }
      return undefined;
    };

    prototype.removeItem = function vaultAwareRemoveItem(key) {
      if (String(key) === TRAIN_AGENT_WORKFLOW_TABS_KEY) {
        global.__aionTrainAgentWorkflowTabsJson = null;
      }
      return nativeRemove.call(this, key);
    };
  }

  installTrainAgentWorkflowTabVaultShim();

  function installBusinessWorkingStateVaultShim() {
    if (global.__aionBusinessWorkingStateVaultShimInstalled === true) return;
    global.__aionBusinessWorkingStateVaultShimInstalled = true;
    const storage = global.localStorage;
    if (!storage) return;
    const prototype = Object.getPrototypeOf(storage);
    const nativeGet = prototype.getItem;
    const nativeSet = prototype.setItem;
    const nativeRemove = prototype.removeItem;
    global.__aionBusinessWorkingStateNativeGet = (key) => nativeGet.call(storage, key);
    global.__aionBusinessWorkingStateNativeRemove = (key) => nativeRemove.call(storage, key);

    prototype.getItem = function vaultAwareBusinessGetItem(key) {
      const safeKey = String(key || '');
      if (!isBusinessWorkingStateKey(safeKey)) return nativeGet.call(this, key);
      if (Object.prototype.hasOwnProperty.call(global.__aionBusinessWorkingStateJson, safeKey)) {
        return global.__aionBusinessWorkingStateJson[safeKey];
      }
      const legacy = nativeGet.call(this, key);
      if (legacy !== null) {
        global.__aionBusinessWorkingStateJson[safeKey] = legacy;
        saveBusinessWorkingState(safeKey, legacy)
          .then(() => nativeRemove.call(this, key))
          .catch((error) => console.warn('[AION] Legacy business working-state Vault import deferred', safeKey, error));
      }
      return legacy;
    };

    prototype.setItem = function vaultAwareBusinessSetItem(key, value) {
      const safeKey = String(key || '');
      if (!isBusinessWorkingStateKey(safeKey)) return nativeSet.call(this, key, value);
      const encoded = String(value ?? '');
      global.__aionBusinessWorkingStateJson[safeKey] = encoded;
      nativeRemove.call(this, key);
      saveBusinessWorkingState(safeKey, encoded).catch((error) => {
        console.warn('[AION] Business working-state Vault save deferred; state remains in session memory', safeKey, error);
      });
      return undefined;
    };

    prototype.removeItem = function vaultAwareBusinessRemoveItem(key) {
      const safeKey = String(key || '');
      if (!isBusinessWorkingStateKey(safeKey)) return nativeRemove.call(this, key);
      delete global.__aionBusinessWorkingStateJson[safeKey];
      nativeRemove.call(this, key);
      deleteBusinessWorkingState(safeKey).catch((error) => {
        if (!String(error).includes('404')) console.warn('[AION] Business working-state Vault delete deferred', safeKey, error);
      });
      return undefined;
    };
  }

  installBusinessWorkingStateVaultShim();

  async function migrateLegacyBusinessWorkingState() {
    const storage = global.localStorage;
    const nativeGet = global.__aionBusinessWorkingStateNativeGet;
    const nativeRemove = global.__aionBusinessWorkingStateNativeRemove;
    if (!storage || typeof nativeGet !== 'function' || typeof nativeRemove !== 'function') return [];
    const keys = [];
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (isBusinessWorkingStateKey(key)) keys.push(String(key));
    }
    const migrated = [];
    for (const key of keys) {
      const legacy = nativeGet(key);
      if (legacy === null) continue;
      global.__aionBusinessWorkingStateJson[key] = legacy;
      await saveBusinessWorkingState(key, legacy);
      nativeRemove(key);
      migrated.push(key);
    }
    return migrated;
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
    global.__aionBusinessContainerSync = global.__aionBusinessContainerSync || {};
    global.__aionBusinessContainerSync[`foundation.${businessId}`] = {
      synced_at: new Date().toISOString(),
      receipt_count: Object.keys(result.containers || {}).length,
    };
    const businessName = clean(packet?.foundation_draft?.business_name)
      || clean(packet?.business_name)
      || result.business_id;
    if (typeof global.aionDesktop?.bindBusinessVaultIdentity !== 'function') {
      throw new Error('OS-protected business identity binding unavailable');
    }
    const binding = await global.aionDesktop.bindBusinessVaultIdentity({
      business_id: result.business_id,
      business_name: businessName,
    });
    if (binding?.registered !== true || canonicalBusinessId(binding?.business_id) !== canonicalBusinessId(result.business_id)) {
      throw new Error('OS-protected business identity binding failed');
    }
    global.__aionFoundationPacket = packet;
    publishBusinessIdentity(result.business_id, businessName);
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
    global.__aionBusinessContainerSync = global.__aionBusinessContainerSync || {};
    global.__aionBusinessContainerSync[`finance.${businessId}`] = sync;
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

  async function getFinanceModel() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/finance-model/${encodeURIComponent(businessId)}`);
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

  async function getDepartmentIntelligence() {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/department-intelligence/${encodeURIComponent(businessId)}`);
  }

  async function saveDepartmentIntelligence(payload = {}, source = 'desktop_department_intelligence') {
    const businessId = resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/department-intelligence/${encodeURIComponent(businessId)}`, {
      method: 'PUT',
      body: JSON.stringify({
        payload: payload && typeof payload === 'object' ? payload : {},
        source,
      }),
    });
  }

  async function getFoundationSession(candidate) {
    const businessId = canonicalBusinessId(candidate) || resolveBusinessId();
    if (!businessId) throw new Error('Registered business ID missing');
    return request(`/api/aion/business/data/foundation-session/${encodeURIComponent(businessId)}`);
  }

  function saveFoundationSection(sectionKey, value, { complete = false } = {}) {
    const businessId = resolveBusinessId();
    const key = clean(sectionKey);
    if (!businessId) return Promise.reject(new Error('Registered business ID missing'));
    if (!key) return Promise.reject(new Error('Foundation section key missing'));
    foundationSaveChain = queueFoundationPersistence(async () => {
      let lastError = null;
      for (let attempt = 0; attempt < 3; attempt += 1) {
        try {
          const current = await getFoundationSession(businessId);
          const session = current?.session || {};
          const packet = session.packet && typeof session.packet === 'object' ? session.packet : {};
          const nextPacket = { ...packet, [key]: value };
          const saved = await request(`/api/aion/business/data/foundation-session/${encodeURIComponent(businessId)}`, {
            method: 'PUT',
            body: JSON.stringify({
              packet: nextPacket,
              expected_revision: Number(session.revision || 0),
              actor_id: 'desktop_foundation_runtime',
              device_id: String(global.__AION_DESKTOP_STATE__?.nodeId || 'local_desktop'),
              complete: complete === true,
            }),
          });
          global.__aionFoundationPacket = saved?.session?.packet || nextPacket;
          global.dispatchEvent(new CustomEvent('aion:foundation-session-loaded', {
            detail: saved?.session || { packet: nextPacket },
          }));
          return saved;
        } catch (error) {
          lastError = error;
          if (error?.status !== 409) throw error;
        }
      }
      throw lastError || new Error('foundation_session_save_failed');
    });
    return foundationSaveChain;
  }

  async function saveDepartmentContext(departmentKey, values = {}) {
    const businessId = resolveBusinessId();
    const department = clean(departmentKey).toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '');
    if (!businessId) throw new Error('Registered business ID missing');
    if (!department) throw new Error('Department identifier missing');
    return request(`/api/aion/business/data/department-intelligence/${encodeURIComponent(businessId)}`, {
      method: 'PUT',
      body: JSON.stringify({
        payload: {
          departments: {
            [department]: {
              department,
              ...((values && typeof values === 'object') ? values : {}),
              updated_at: new Date().toISOString(),
            },
          },
        },
        source: 'desktop_department_context',
      }),
    });
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

  async function hydrateFinanceState() {
    if (financeStateHydrated) return global.__aionFinancePilotDiscoveryState || null;
    if (!financeStateHydrationPromise) {
      financeStateHydrationPromise = (async () => {
        const financeState = JSON.parse(localStorage.getItem('aion.financePilot.discoveryState.v1') || 'null');
        if (financeState && typeof financeState === 'object') {
          global.__aionFinancePilotDiscoveryState = financeState;
          await syncFinanceStateNow(financeState);
          localStorage.removeItem('aion.financePilot.discoveryState.v1');
          localStorage.removeItem('aion.financePilot.businessFinancialModel.v1');
          localStorage.removeItem('aion.businessTwin.financePacket.v1');
        } else {
          const model = await getFinanceModel();
          const restored = model?.payload?.discovery_state;
          if (restored && typeof restored === 'object') {
            global.__aionFinancePilotDiscoveryState = restored;
            global.dispatchEvent(new CustomEvent('aion:finance-state-loaded', { detail: restored }));
          }
        }
        financeStateHydrated = true;
        global.requestRender?.();
        return global.__aionFinancePilotDiscoveryState || null;
      })().finally(() => { financeStateHydrationPromise = null; });
    }
    return financeStateHydrationPromise;
  }

  async function hydrateTrainAgentWorkspaceState() {
    if (trainAgentWorkspaceHydrated) return;
    if (!trainAgentWorkspaceHydrationPromise) {
      trainAgentWorkspaceHydrationPromise = (async () => {
        const record = await getTrainAgentWorkspaceState('workflow-tabs');
        const workspaceState = record?.payload || {};
        global.__aionTrainAgentWorkflowTabsJson = JSON.stringify(workspaceState);
        if (Array.isArray(workspaceState.tabs)) {
          global.__aionWorkflowTabs = workspaceState.tabs;
          global.__aionActiveWorkflowTabId = workspaceState.active_id || workspaceState.tabs[0]?.id || '';
          global.__aionWorkflowTabsAllowEmpty = workspaceState.allow_empty === true && workspaceState.tabs.length === 0;
        }
        global.dispatchEvent(new CustomEvent('aion:train-agent-workspace-state-loaded', {
          detail: workspaceState,
        }));
        trainAgentWorkspaceHydrated = true;
        global.requestRender?.();
      })().finally(() => { trainAgentWorkspaceHydrationPromise = null; });
    }
    return trainAgentWorkspaceHydrationPromise;
  }

  async function hydrateFounderNotes() {
    if (founderNotesHydrated) return global.__aionFounderNotes || [];
    if (!founderNotesHydrationPromise) {
      founderNotesHydrationPromise = (async () => {
        const notes = await getFounderNotes();
        global.__aionFounderNotes = Array.isArray(notes?.notes) ? notes.notes : [];
        global.dispatchEvent(new CustomEvent('aion:founder-notes-loaded', {
          detail: { notes: global.__aionFounderNotes },
        }));
        founderNotesHydrated = true;
        global.requestRender?.();
        return global.__aionFounderNotes;
      })().finally(() => { founderNotesHydrationPromise = null; });
    }
    return founderNotesHydrationPromise;
  }

  async function bootstrap() {
    const packet = readFoundationPacket();
    let businessId = resolveBusinessId(packet);
    if (!businessId && typeof global.aionDesktop?.getBusinessVaultIdentity === 'function') {
      try {
        const binding = await global.aionDesktop.getBusinessVaultIdentity();
        if (binding?.registered === true) {
          businessId = canonicalBusinessId(binding.business_id);
          if (businessId) publishBusinessIdentity(businessId, binding.business_name);
        }
      } catch (error) {
        console.warn('[AION] OS-protected business identity restore failed closed', error);
      }
    }
    if (!businessId) {
      bootstrapReadyResolve?.();
      return;
    }
    if (!global.__aionCanonicalBusinessId) publishBusinessIdentity(businessId, '');
    if (packet) {
      try {
        await commitFoundationPacket(packet);
        await saveFoundationSection('legacy_foundation_packet', packet, { complete: true });
        try { localStorage.removeItem(FOUNDATION_KEY); } catch {}
      } catch (error) {
        console.warn('[AION] Canonical Foundation commit deferred until backend is available', error);
      }
    } else {
      try {
        const foundation = await getFoundationSession(businessId);
        global.__aionFoundationPacket = foundation?.session?.packet || null;
        global.dispatchEvent(new CustomEvent('aion:foundation-session-loaded', {
          detail: foundation?.session || {},
        }));
      } catch (error) {
        console.warn('[AION] Foundation Vault load deferred until backend is available', error);
      }
    }
    try {
      await migrateLegacyBusinessWorkingState();
      const workingState = await listBusinessWorkingState();
      for (const record of Array.isArray(workingState?.states) ? workingState.states : []) {
        const stateId = String(record?.state_id || '');
        const stored = record?.payload?.value;
        if (!isBusinessWorkingStateKey(stateId) || !stored || typeof stored !== 'object') continue;
        global.__aionBusinessWorkingStateJson[stateId] = String(stored.value ?? '');
        businessWorkingStateVersions.set(stateId, Number(record?.version || 0));
      }
      global.dispatchEvent(new CustomEvent('aion:business-working-state-loaded', {
        detail: { keys: Object.keys(global.__aionBusinessWorkingStateJson) },
      }));
      global.requestRender?.();
    } catch (error) {
      console.warn('[AION] Business working-state Vault load deferred until backend is available', error);
    }
    try {
      const ledger = await getDepartmentIntelligence();
      global.dispatchEvent(new CustomEvent('aion:department-context-loaded', {
        detail: { departments: ledger?.payload?.departments || {} },
      }));
    } catch (error) {
      console.warn('[AION] Department context load deferred until backend is available', error);
    }
    bootstrapReadyResolve?.();
  }

  global.AionBusinessContainerClient = {
    canonicalBusinessId, resolveBusinessId, commitFoundationPacket,
    syncFinanceState, syncFinanceStateNow,
    uploadFinanceArtifact, listFinanceArtifacts, analyseFinanceArtifact, acceptFinanceArtifactFacts,
    getXeroStatus, connectXero, selectXeroTenant, syncXero, disconnectXero,
    getOperatingModel, getFinanceModel, saveOperatingModel, importOperatingModelSpreadsheet, completeFinanceFoundation,
    getBoardroomContext, askFinanceAgent, getBusinessMap,
    getDepartmentIntelligence, saveDepartmentIntelligence, saveDepartmentContext,
    getFoundationSession, saveFoundationSection,
    getBusinessKnowledge, addBusinessKnowledgeText, uploadBusinessKnowledgeFile,
    approveBusinessKnowledgeClaims, searchBusinessKnowledge,
    getOrganizationAuthority, getPilotScheduledWork, createPilotScheduledWork,
    setPilotScheduledWorkEnabled, runPilotScheduledWork,
    getTrainAgentWorkspaceState, saveTrainAgentWorkspaceState,
    hydrateFinanceState, hydrateTrainAgentWorkspaceState, hydrateFounderNotes,
    readTrainAgentWorkflowTabsString, writeTrainAgentWorkflowTabsString,
    getFounderNotes, saveFounderNotes,
    listBusinessWorkingState, getBusinessWorkingState,
    saveBusinessWorkingState, deleteBusinessWorkingState,
    readBusinessWorkingStateString, writeBusinessWorkingStateString,
    clearBusinessWorkingState, isBusinessWorkingStateKey,
    migrateLegacyBusinessWorkingState,
    whenReady: () => bootstrapReady,
  };
  setTimeout(bootstrap, 600);
})(window);
