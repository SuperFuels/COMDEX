const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

function loadPreferences() {
  const values = new Map();
  const storage = { setItem(key, value) { values.set(String(key), String(value)); } };
  const window = { localStorage: storage, sessionStorage: storage };
  const policySource = fs.readFileSync(path.join(__dirname, '..', 'src', 'desktop-preference-policy.js'), 'utf8');
  vm.runInNewContext(policySource, { window });
  const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'aion_desktop_preferences.js'), 'utf8');
  vm.runInNewContext(source, { window });
  return { preferences: window.AionDesktopPreferences, values };
}

test('stores only registered content-free preferences', () => {
  const { preferences, values } = loadPreferences();
  preferences.set('aion.activeTab.v1', 'boardroom');
  assert.equal(values.get('aion.activeTab.v1'), 'boardroom');
  assert.throws(() => preferences.set('aion.customer.notes', 'customer secret'), /Unregistered/);
  assert.throws(() => preferences.set('aion.activeTab.v1', 'customer secret with spaces'), /content-free/);
});

test('restricts API location and Pilot voice preference shape', () => {
  const { preferences } = loadPreferences();
  preferences.set('aion.apiBase', 'http://127.0.0.1:8080');
  assert.throws(() => preferences.set('aion.apiBase', 'https://example.com/customer'), /loopback-only/);
  preferences.set('aion.pilot.voicePreferences.v1', JSON.stringify({ read_aloud: true, wake_phrase: false }));
  assert.throws(() => preferences.set('aion.pilot.voicePreferences.v1', JSON.stringify({ transcript: 'private' })), /Unexpected/);
});
