'use strict';

(function installAionDevelopmentBusinessSession(root) {
  if (!root || root.AionDevelopmentBusinessSession) return;

  const VERSION = 'aion.development_business_session.v0.1';
  const PACKET_KEY = 'aion.businessTwin.foundationPacket.v1';
  const COMPLETED_KEY = 'aion.businessTwin.foundationCompleted.v1';
  const COMPLETED_AT_KEY = 'aion.businessTwin.foundationCompletedAt.v1';
  const DEVICE_KEY = 'aion.businessTwin.foundationDeviceId.v1';
  const DEFAULT_API_BASE = 'http://127.0.0.1:8080';
  const motherSync = {
    status: 'starting',
    revision: 0,
    workspace_id: null,
    last_synced_at: null,
    last_error: null,
    conflict: null,
  };
  const motherSyncByWorkspace = new Map();
  let syncQueue = Promise.resolve();
  let runtimeDeviceId = null;

  function queueFoundationPersistence(task) {
    const previous = root.__aionFoundationPersistenceQueue || Promise.resolve();
    const next = Promise.resolve(previous).catch(() => null).then(task);
    root.__aionFoundationPersistenceQueue = next;
    return next;
  }

  function parseJson(value, fallback = null) {
    try { return value ? JSON.parse(value) : fallback; } catch { return fallback; }
  }

  function apiBase() {
    const candidate = root.__AION_API_BASE__ || root.AION_API_BASE || root.state?.apiBase || DEFAULT_API_BASE;
    return String(candidate || DEFAULT_API_BASE).replace(/\/+$/, '');
  }

  function workspaceId() {
    let candidate = '';
    try { candidate = root.AionBusinessContainerClient?.resolveBusinessId?.() || ''; } catch {}
    candidate = candidate || root.state?.workspaceId || root.__AION_DESKTOP_STATE__?.workspaceId || '';
    const normalized = String(candidate).trim().toLowerCase().replace(/_/g, '-').replace(/[^a-z0-9-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
    return normalized && !['global', 'root', 'tmp', 'business-not-registered'].includes(normalized)
      ? normalized
      : '';
  }

  function deviceId() {
    const nodeId = String(
      root.__AION_DESKTOP_STATE__?.nodeId || root.state?.nodeId || '',
    ).trim().replace(/[^A-Za-z0-9_.:-]+/g, '-').slice(0, 160);
    if (nodeId) return `boardroom:${nodeId}`;
    if (!runtimeDeviceId) {
      runtimeDeviceId = `boardroom_runtime_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    }
    return runtimeDeviceId;
  }

  function publishSyncState() {
    root.__aionFoundationMotherSyncState = { ...motherSync };
    try {
      root.document?.dispatchEvent(new CustomEvent('aion:foundation-mother-sync', {
        detail: { ...motherSync },
      }));
    } catch {}
  }

  async function requestMother(path, options = {}) {
    const response = await fetch(`${apiBase()}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(body?.detail?.reason || body?.detail || `foundation_session_http_${response.status}`);
      error.status = response.status;
      error.payload = body;
      throw error;
    }
    return body;
  }

  function workspaceSyncSnapshot(id) {
    const cached = motherSyncByWorkspace.get(id);
    if (cached) return { ...cached };
    if (motherSync.workspace_id === id) return { ...motherSync };
    return {
      status: 'not_started', revision: 0, workspace_id: id,
      last_synced_at: null, last_error: null, conflict: null,
    };
  }

  function cacheMotherPacket(session = {}, expectedWorkspaceId = '') {
    const sessionWorkspaceId = String(
      expectedWorkspaceId || session?.workspace_id || workspaceId(),
    );
    const snapshot = {
      status: session?.packet ? 'synced' : session?.status === 'reset' ? 'reset' : 'not_started',
      revision: Number(session?.revision || 0),
      workspace_id: sessionWorkspaceId,
      last_synced_at: session?.updated_at || new Date().toISOString(),
      last_error: null,
      conflict: null,
    };
    motherSyncByWorkspace.set(sessionWorkspaceId, snapshot);

    // A Foundation answer can create a new canonical business id while older
    // saves are still in flight. A response for the old workspace must never
    // replace the active interview packet or its revision.
    if (workspaceId() !== sessionWorkspaceId) {
      return session?.packet || null;
    }

    const packet = session?.packet;
    Object.assign(motherSync, snapshot);
    if (packet && typeof packet === 'object') {
      root.__aionFoundationPacket = packet;
      root.__aionBusinessFoundationVoiceDiscoveryPacket = packet;
      const complete = session.status === 'completed_pending_commit';
      if (complete) {
        root.__aionBusinessFoundationCompletedPacket = packet;
      }
      // PACKET_KEY is a legacy import source only.  Once Guardian has returned
      // the session, the browser must not retain another durable business copy.
      try { localStorage.removeItem(PACKET_KEY); } catch {}
    }
    publishSyncState();
    return packet || null;
  }

  async function loadFoundationPacketFromMother() {
    const id = workspaceId();
    if (!id) {
      motherSync.status = 'awaiting_business_registration';
      motherSync.workspace_id = null;
      publishSyncState();
      return getFoundationPacket();
    }
    motherSync.status = 'loading';
    motherSync.workspace_id = id;
    publishSyncState();
    try {
      const body = await requestMother(`/api/aion/business/data/foundation-session/${encodeURIComponent(id)}`);
      const session = body?.session || {};
      if (session.packet) return cacheMotherPacket(session, id);

      motherSync.revision = Number(session.revision || 0);
      const cached = getFoundationPacket();
      if (cached && motherSync.revision === 0) {
        return persistFoundationPacketToMother(cached, {
          complete: localStorage.getItem(COMPLETED_KEY) === 'true',
          migration: true,
        });
      }
      cacheMotherPacket(session, id);
      return null;
    } catch (error) {
      motherSync.status = 'vault_unavailable_memory_only';
      motherSync.last_error = String(error?.message || error);
      publishSyncState();
      return getFoundationPacket();
    }
  }

  async function persistFoundationPacketToMother(packet = {}, options = {}) {
    const id = String(options.workspace_id || workspaceId());
    if (!id) {
      motherSync.status = 'awaiting_business_registration';
      motherSync.workspace_id = null;
      publishSyncState();
      return packet;
    }
    const active = workspaceId() === id;
    if (active) {
      motherSync.status = options.migration ? 'migrating' : 'saving';
      motherSync.workspace_id = id;
      publishSyncState();
    }
    let lastError = null;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const latestBody = await requestMother(
          `/api/aion/business/data/foundation-session/${encodeURIComponent(id)}`,
        );
        const latestSession = latestBody?.session || {};
        const latestPacket = latestSession.packet && typeof latestSession.packet === 'object'
          ? latestSession.packet
          : {};
        // Preserve section data written by other trusted onboarding surfaces,
        // while making the latest local interview packet authoritative for the
        // fields it owns. This prevents a revision conflict from silently
        // dropping the answer the founder just supplied.
        const nextPacket = { ...latestPacket, ...packet };
        const body = await requestMother(`/api/aion/business/data/foundation-session/${encodeURIComponent(id)}`, {
          method: 'PUT',
          body: JSON.stringify({
            packet: nextPacket,
            expected_revision: Number(latestSession.revision || 0),
            actor_id: 'local_owner',
            device_id: deviceId(),
            complete: options.complete === true,
          }),
        });
        return cacheMotherPacket(body.session || {}, id);
      } catch (error) {
        lastError = error;
        if (error?.status !== 409) break;
      }
    }
    if (lastError?.status === 409 && active) {
      motherSync.status = 'conflict';
      motherSync.conflict = lastError.payload?.detail || { reason: 'foundation_session_revision_conflict' };
      motherSync.last_error = 'The latest Foundation answer could not be saved after three conflict retries.';
      publishSyncState();
    } else if (active) {
      motherSync.status = 'vault_unavailable_memory_only';
      motherSync.last_error = String(lastError?.message || lastError || 'foundation_session_save_failed');
      publishSyncState();
    }
    return packet;
  }

  function queueMotherSave(packet = {}, options = {}) {
    const workspace_id = workspaceId();
    if (!workspace_id) {
      motherSync.status = 'awaiting_business_registration';
      motherSync.workspace_id = null;
      publishSyncState();
      return Promise.resolve(packet);
    }
    syncQueue = queueFoundationPersistence(
      () => persistFoundationPacketToMother(packet, { ...options, workspace_id }),
    );
    return syncQueue;
  }

  function persistFoundationPacket(packet = {}, options = {}) {
    if (!packet || typeof packet !== 'object') return null;
    const complete = options.complete === true ||
      packet.status === 'foundation_ready_for_finance_handoff' ||
      packet.next_question?.reason === 'finance_handoff_ready' ||
      packet.next_question?.action === 'route_finance_live_agent';

    root.__aionFoundationPacket = packet;
    root.__aionBusinessFoundationVoiceDiscoveryPacket = packet;
    if (complete) {
      root.__aionBusinessFoundationCompletedPacket = packet;
    }
    void queueMotherSave(packet, { ...options, complete });
    return packet;
  }

  function getFoundationPacket() {
    if (root.__aionFoundationPacket && typeof root.__aionFoundationPacket === 'object') {
      return root.__aionFoundationPacket;
    }
    const legacy = parseJson(localStorage.getItem(PACKET_KEY), null);
    if (legacy && typeof legacy === 'object') {
      root.__aionFoundationPacket = legacy;
      root.__aionBusinessFoundationVoiceDiscoveryPacket = legacy;
    }
    return legacy;
  }

  function migrateCompletedFoundationIfNeeded() {
    const existing = getFoundationPacket();
    if (existing) return existing;

    const manifest = parseJson(
      localStorage.getItem('aion.businessTwin.progressionManifest.v1'),
      null,
    );
    const draft = manifest?.foundation?.foundation_draft;
    if (!manifest?.foundation?.completed || !draft || typeof draft !== 'object') {
      return null;
    }

    const migrated = {
      schema_version: manifest.foundation.packet_version ||
        'aion.business_foundation_discovery_packet.migrated.v0.1',
      status: 'foundation_ready_for_finance_handoff',
      foundation_draft: { ...draft },
      transcript: [],
      transcript_count: Number(manifest.foundation.transcript_count || 0),
      next_question: {
        reason: 'finance_handoff_ready',
        action: 'route_finance_live_agent',
        completion: true,
        next_department: 'finance',
      },
      migrated_from_progression_manifest: true,
    };
    return persistFoundationPacket(migrated, { complete: true });
  }

  function hasCompletedBusiness() {
    const packet = getFoundationPacket();
    if (!packet || typeof packet !== 'object') return false;
    return Boolean(
      root.__aionBusinessFoundationCompletedPacket === packet ||
      packet.status === 'foundation_ready_for_finance_handoff' ||
      packet.next_question?.completion === true ||
      packet.next_question?.reason === 'finance_handoff_ready' ||
      packet.next_question?.action === 'route_finance_live_agent'
    );
  }

  function restoreCompletedBusiness() {
    if (!hasCompletedBusiness()) return null;
    const packet = getFoundationPacket();
    root.__aionBusinessFoundationVoiceDiscoveryPacket = packet;
    root.__aionBusinessFoundationCompletedPacket = packet;
    root.__aionO25ABStartupRouteHold = false;
    root.__aionO25ADTerminalOpen = false;
    root.__aionO25UConversationOpen = false;

    try {
      [
        'aion.activeTab',
        'aion.activeTab.v1',
        'aion.lastActiveTab.v1',
        'aion.forcedMainTab.v2',
        'aionDesktop.activeTab',
      ].forEach((key) => root.AionDesktopPreferences.set(key, 'live_agents'));
      [
        'aion.liveAgents.selectedDepartment.v1',
        'aion.liveAgents.selectedDepartment',
        'aion.selectedLiveDepartment',
        'aion.departmentPilot.selected',
      ].forEach((key) => root.AionDesktopPreferences.set(key, 'finance'));
    } catch {}

    return packet;
  }

  function resetForNewBusiness() {
    const exactKeys = new Set([
      PACKET_KEY,
      COMPLETED_KEY,
      COMPLETED_AT_KEY,
      'aion.approvedSmallBusinessFoundation',
      'aion.businessContextFoundation',
      'aion.businessContext.v1',
      'aion.businessFoundation.context.v1',
      'aion.smallBusinessFoundationDraft',
      'aion.smallBusinessFoundation.draft.v1',
      'aion.smallBusinessFoundation.context.v1',
      'aion.smallBusinessFoundation.approvedContext.v1',
      'aion.smallBusinessFoundationBoardroomStarted',
      'aion.businessTwin.progressionManifest.v1',
      'aion.activeTab',
      'aion.activeTab.v1',
      'aion.lastActiveTab.v1',
      'aion.forcedMainTab.v2',
      'aionDesktop.activeTab',
      'aion.liveAgents.selectedDepartment.v1',
      'aion.liveAgents.selectedDepartment',
      'aion.selectedLiveDepartment',
      'aion.departmentPilot.selected',
      'aion.o20c.mode',
      'aion.o20c.conversationMode',
      'aion.o20c.conversationOpen',
      'aion.voiceOnboarding.o19i.v1',
      'aion.voiceOnboarding.o19m.started.v1',
      'aion.voiceOnboarding.o19l.started.v1',
    ]);
    const prefixes = [
      'aion.businessTwinSetup.',
      'aion.voiceDiscovery.',
      'aion.financePilot.',
      'aion.businessContainer.sync.',
    ];

    try {
      Array.from({ length: localStorage.length }, (_, index) => localStorage.key(index))
        .filter(Boolean)
        .forEach((key) => {
          if (exactKeys.has(key) || prefixes.some((prefix) => key.startsWith(prefix))) {
            localStorage.removeItem(key);
          }
        });
    } catch {}

    try {
      sessionStorage.clear();
    } catch {}

    try {
      root.__aionBusinessFoundationVoiceDiscoveryPacket = null;
      root.__aionBusinessFoundationCompletedPacket = null;
      root.__aionFoundationPacket = null;
      root.__aionO25ABStartupRouteClaimed = false;
      root.__aionO25AYStartupRouteClaimed = false;
      root.__aionO25ABStartupRouteHold = false;
      root.__aionO25ADTerminalOpen = false;
      root.__aionO25UConversationOpen = false;
    } catch {}

    const id = workspaceId();
    if (!id) {
      root.location.reload();
      return { ok: true };
    }
    void requestMother(`/api/aion/business/data/foundation-session/${encodeURIComponent(id)}/reset`, {
      method: 'POST',
      keepalive: true,
      body: JSON.stringify({
        expected_revision: Number(motherSync.revision || 0),
        actor_id: 'local_owner',
        confirm_reset: true,
      }),
    }).finally(() => root.location.reload());
    return { ok: true };
  }

  const storedPacket = migrateCompletedFoundationIfNeeded() || getFoundationPacket();
  if (storedPacket) {
    root.__aionBusinessFoundationVoiceDiscoveryPacket = storedPacket;
    if (hasCompletedBusiness()) root.__aionBusinessFoundationCompletedPacket = storedPacket;
  }
  void loadFoundationPacketFromMother();
  // Business identity is restored asynchronously from the Vault on a cold
  // desktop start. Retry Foundation hydration when that authority boundary is
  // established so the resumed Pilot has a current revision and can save
  // safely, rather than remaining in an "awaiting registration" state.
  root.addEventListener?.('aion:business-identity-established', () => {
    void loadFoundationPacketFromMother();
  });

  root.AionDevelopmentBusinessSession = Object.freeze({
    VERSION,
    PACKET_KEY,
    COMPLETED_KEY,
    persistFoundationPacket,
    getFoundationPacket,
    hasCompletedBusiness,
    restoreCompletedBusiness,
    resetForNewBusiness,
    loadFoundationPacketFromMother,
    persistFoundationPacketToMother,
    getMotherSyncState: () => ({ ...motherSync }),
  });
  root.resetAionDevelopmentBusinessV1 = resetForNewBusiness;
})(typeof window !== 'undefined' ? window : globalThis);
