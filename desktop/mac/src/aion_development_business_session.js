'use strict';

(function installAionDevelopmentBusinessSession(root) {
  if (!root || root.AionDevelopmentBusinessSession) return;

  const VERSION = 'aion.development_business_session.v0.1';
  const PACKET_KEY = 'aion.businessTwin.foundationPacket.v1';
  const COMPLETED_KEY = 'aion.businessTwin.foundationCompleted.v1';
  const COMPLETED_AT_KEY = 'aion.businessTwin.foundationCompletedAt.v1';

  function parseJson(value, fallback = null) {
    try { return value ? JSON.parse(value) : fallback; } catch { return fallback; }
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

    root.location.reload();
    return { ok: true };
  }

  const storedPacket = migrateCompletedFoundationIfNeeded() || getFoundationPacket();
  if (storedPacket) {
    root.__aionBusinessFoundationVoiceDiscoveryPacket = storedPacket;
    if (hasCompletedBusiness()) root.__aionBusinessFoundationCompletedPacket = storedPacket;
  }

  root.AionDevelopmentBusinessSession = Object.freeze({
    VERSION,
    PACKET_KEY,
    COMPLETED_KEY,
    persistFoundationPacket,
    getFoundationPacket,
    hasCompletedBusiness,
    restoreCompletedBusiness,
    resetForNewBusiness,
  });
  root.resetAionDevelopmentBusinessV1 = resetForNewBusiness;
})(typeof window !== 'undefined' ? window : globalThis);
