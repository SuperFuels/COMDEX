(function installTessarisDesktopPreferencePolicy(root, factory) {
  'use strict';
  const policy = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = policy;
  if (root) root.TessarisDesktopPreferencePolicy = Object.freeze(policy);
})(typeof window !== 'undefined' ? window : globalThis, function createPolicy() {
  'use strict';

  const exactKeys = new Set([
    'aion.forcedMainTab.v2',
    'aion.boardroomViewMode.v1',
    'aion.liveAgents.selectedDepartment',
    'aion.liveAgents.selectedDepartment.v1',
    'aion.liveAgents.focusDepartment.v1',
    'aion.selectedLiveDepartment',
    'aion.departmentPilot.selected',
    'aion.departmentPilot.package.expanded.marketing',
    'aion.communications.activeTab.v1',
    'aion.activeTab',
    'aion.activeTab.v1',
    'aion.lastActiveTab.v1',
    'aionDesktop.activeTab',
    'aionDesktop.boardroomViewMode',
    'aionDesktop.operationsFlowViewMode',
    'aionDesktop.activeZone',
    'aionDesktop.liveAgentsView',
    'aionDesktop.marketingCalendarMode',
    'aion.pilot.commandCentre.view.v1',
    'aion.pilot.voicePreferences.v1',
    'aion.chat.selected_engine.v1',
    'aion.chat.messages.v1.migrated',
    'aion.businessTwin.financeFirst.v1',
    'aion.businessTwin.financeFirstRouted.v1',
    'aion.businessTwin.financeHandoffActive.v1',
    'aion.boardroom.kpiDepartment.v1',
    'aion.finance.functionalSection.v1',
    'aion.activeBusinessContextSubtab',
    'aion.workflow.dark_mode.enabled',
    'aion_dev_legacy_drawers',
    'aion.apiBase',
    'aion.api_base',
    'aion.boardroomGoalSheet.stagedNoticeDismissed.v1',
    'aionDesktop.marketing.canvasCleared',
    'aion.founderNotes.selected.v1',
    'aion.file_cabinet.last_workspace_route.v1',
    'aion.workflow_file_cabinet.open.v1',
    'aion.boardroom.workspaceMode.v1',
    'aion.o25u.current_terminal_open.v1',
    'aion.o25f.intentionalConversationOpen.v1',
    'aion.o25ad.terminal_open.v1',
  ]);
  const dynamicKeys = [
    /^aion\.[a-z0-9_-]+\.functionalSection\.v1$/,
    /^aionDesktop\.marketing\.canvasCleared\.[A-Za-z0-9_.-]{1,120}$/,
  ];
  const tokenValue = /^[A-Za-z0-9_./:-]{0,240}$/;

  function isAllowedKey(key) {
    const value = String(key || '');
    return exactKeys.has(value) || dynamicKeys.some((pattern) => pattern.test(value));
  }

  function validateValue(key, value) {
    const encoded = String(value ?? '');
    if (key === 'aion.pilot.voicePreferences.v1') {
      let parsed;
      try { parsed = JSON.parse(encoded); } catch { throw new Error('Pilot voice preference must be JSON'); }
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Pilot voice preference must be an object');
      const keys = Object.keys(parsed);
      if (keys.some((name) => !['read_aloud', 'wake_phrase'].includes(name))) throw new Error('Unexpected Pilot voice preference');
      if (keys.some((name) => typeof parsed[name] !== 'boolean')) throw new Error('Pilot voice preferences must be booleans');
      return encoded;
    }
    if ((key === 'aion.apiBase' || key === 'aion.api_base') && !/^https?:\/\/(?:127\.0\.0\.1|localhost)(?::\d{1,5})?(?:\/[^\s]*)?$/.test(encoded)) {
      throw new Error('Desktop API preference must remain loopback-only');
    }
    if (!tokenValue.test(encoded)) throw new Error('Desktop preference accepts content-free tokens only');
    return encoded;
  }

  return { isAllowedKey, validateValue };
});
