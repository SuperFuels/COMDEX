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
  let syncQueue = Promise.resolve();

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
    candidate = candidate || root.state?.workspaceId || root.__AION_DESKTOP_STATE__?.workspaceId || 'home-fixed';
    const normalized = String(candidate).trim().toLowerCase().replace(/_/g, '-').replace(/[^a-z0-9-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
    return normalized && !['global', 'root', 'tmp', 'business-not-registered'].includes(normalized)
      ? normalized
      : 'home-fixed';
  }

  function deviceId() {
    let value = '';
    try { value = localStorage.getItem(DEVICE_KEY) || ''; } catch {}
    if (!value) {
      value = `boardroom_${Date.now()}_${Math.random().toString(16).slice(2)}`;
      try { localStorage.setItem(DEVICE_KEY, value); } catch {}
    }
    return value;
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

  function cacheMotherPacket(session = {}) {
    const packet = session?.packet;
    motherSync.revision = Number(session?.revision || 0);
    motherSync.workspace_id = session?.workspace_id || workspaceId();
    motherSync.last_synced_at = session?.updated_at || new Date().toISOString();
    motherSync.status = packet ? 'synced' : session?.status === 'reset' ? 'reset' : 'not_started';
    motherSync.last_error = null;
    motherSync.conflict = null;
    if (packet && typeof packet === 'object') {
      try { localStorage.setItem(PACKET_KEY, JSON.stringify(packet)); } catch {}
      root.__aionBusinessFoundationVoiceDiscoveryPacket = packet;
      const complete = session.status === 'completed_pending_commit';
      if (complete) {
        try { localStorage.setItem(COMPLETED_KEY, 'true'); } catch {}
        root.__aionBusinessFoundationCompletedPacket = packet;
      }
    }
    publishSyncState();
    return packet || null;
  }

  async function loadFoundationPacketFromMother() {
    const id = workspaceId();
    motherSync.status = 'loading';
    motherSync.workspace_id = id;
    publishSyncState();
    try {
      const body = await requestMother(`/api/aion/business/data/foundation-session/${encodeURIComponent(id)}`);
      const session = body?.session || {};
      if (session.packet) return cacheMotherPacket(session);

      motherSync.revision = Number(session.revision || 0);
      const cached = getFoundationPacket();
      if (cached && motherSync.revision === 0) {
        return persistFoundationPacketToMother(cached, {
          complete: localStorage.getItem(COMPLETED_KEY) === 'true',
          migration: true,
        });
      }
      cacheMotherPacket(session);
      return null;
    } catch (error) {
      motherSync.status = 'offline_cache';
      motherSync.last_error = String(error?.message || error);
      publishSyncState();
      return getFoundationPacket();
    }
  }

  async function persistFoundationPacketToMother(packet = {}, options = {}) {
    const id = workspaceId();
    motherSync.status = options.migration ? 'migrating' : 'saving';
    motherSync.workspace_id = id;
    publishSyncState();
    try {
      const body = await requestMother(`/api/aion/business/data/foundation-session/${encodeURIComponent(id)}`, {
        method: 'PUT',
        body: JSON.stringify({
          packet,
          expected_revision: Number(motherSync.revision || 0),
          actor_id: 'local_owner',
          device_id: deviceId(),
          complete: options.complete === true,
        }),
      });
      return cacheMotherPacket(body.session || {});
    } catch (error) {
      if (error?.status === 409) {
        motherSync.status = 'conflict';
        motherSync.conflict = error.payload?.detail || { reason: 'foundation_session_revision_conflict' };
        motherSync.last_error = 'A newer foundation interview exists on another trusted surface.';
        publishSyncState();
        try {
          const latest = await requestMother(`/api/aion/business/data/foundation-session/${encodeURIComponent(id)}`);
          return cacheMotherPacket(latest.session || {});
        } catch {}
      }
      motherSync.status = 'offline_cache';
      motherSync.last_error = String(error?.message || error);
      publishSyncState();
      return packet;
    }
  }

  function queueMotherSave(packet = {}, options = {}) {
    syncQueue = syncQueue.then(
      () => persistFoundationPacketToMother(packet, options),
      () => persistFoundationPacketToMother(packet, options),
    );
    return syncQueue;
  }

  function persistFoundationPacket(packet = {}, options = {}) {
    if (!packet || typeof packet !== 'object') return null;
    const complete = options.complete === true ||
      packet.status === 'foundation_ready_for_finance_handoff' ||
      packet.next_question?.reason === 'finance_handoff_ready' ||
      packet.next_question?.action === 'route_finance_live_agent';

    try {
      localStorage.setItem(PACKET_KEY, JSON.stringify(packet));
      if (complete) {
        localStorage.setItem(COMPLETED_KEY, 'true');
        localStorage.setItem(COMPLETED_AT_KEY, new Date().toISOString());
      }
    } catch {}

    root.__aionBusinessFoundationVoiceDiscoveryPacket = packet;
    if (complete) root.__aionBusinessFoundationCompletedPacket = packet;
    void queueMotherSave(packet, { ...options, complete });
    return packet;
  }

  function getFoundationPacket() {
    return parseJson(localStorage.getItem(PACKET_KEY), null);
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
    if (localStorage.getItem(COMPLETED_KEY) !== 'true') return false;
    const packet = getFoundationPacket();
    return Boolean(packet && typeof packet === 'object');
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
      localStorage.setItem('aion.activeTab', 'live_agents');
      localStorage.setItem('aion.activeTab.v1', 'live_agents');
      localStorage.setItem('aion.lastActiveTab.v1', 'live_agents');
      localStorage.setItem('aion.forcedMainTab.v2', 'live_agents');
      localStorage.setItem('aionDesktop.activeTab', 'live_agents');
      localStorage.setItem('aion.liveAgents.selectedDepartment.v1', 'finance');
      localStorage.setItem('aion.liveAgents.selectedDepartment', 'finance');
      localStorage.setItem('aion.selectedLiveDepartment', 'finance');
      localStorage.setItem('aion.departmentPilot.selected', 'finance');
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
      root.__aionO25ABStartupRouteClaimed = false;
      root.__aionO25AYStartupRouteClaimed = false;
      root.__aionO25ABStartupRouteHold = false;
      root.__aionO25ADTerminalOpen = false;
      root.__aionO25UConversationOpen = false;
    } catch {}

    const id = workspaceId();
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
