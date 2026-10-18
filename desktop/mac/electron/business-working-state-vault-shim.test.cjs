const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

class MemoryStorage {
  constructor(entries = {}) {
    this.values = new Map(Object.entries(entries));
  }

  get length() { return this.values.size; }
  key(index) { return [...this.values.keys()][index] ?? null; }
  getItem(key) { return this.values.has(String(key)) ? this.values.get(String(key)) : null; }
  setItem(key, value) { this.values.set(String(key), String(value)); }
  removeItem(key) { this.values.delete(String(key)); }
}

function loadClient({ entries = {}, requests = [], fetchImpl = null } = {}) {
  const storage = new MemoryStorage(entries);
  const window = {
    localStorage: storage,
    __aionCanonicalBusinessId: 'acme',
    setTimeout: () => 1,
    dispatchEvent: () => true,
    requestRender: () => {},
  };
  const context = {
    window,
    localStorage: storage,
    fetch: fetchImpl || (async (url, options = {}) => {
      requests.push({ url, options });
      return {
        ok: true,
        json: async () => ({ ok: true, version: requests.length }),
        text: async () => '',
      };
    }),
    CustomEvent: class CustomEvent {},
    FormData: class FormData {},
    console,
    setTimeout: window.setTimeout,
  };
  const source = fs.readFileSync(
    path.join(__dirname, '..', 'src', 'aion_business_container_client.js'),
    'utf8',
  );
  vm.runInNewContext(source, context, { filename: 'aion_business_container_client.js' });
  return { window, storage, requests };
}

async function flushPromises() {
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
}

test('business working state is sent to Vault and never left as a new browser record', async () => {
  const requests = [];
  const { window, storage } = loadClient({ requests });
  const value = JSON.stringify({ answers: { q1: 'Customer-owned detail' } });

  storage.setItem('aion.boardroom.discovery_answers.v1', value);
  assert.equal(storage.values.has('aion.boardroom.discovery_answers.v1'), false);
  assert.equal(storage.getItem('aion.boardroom.discovery_answers.v1'), value);
  await flushPromises();

  assert.equal(requests.length, 1);
  assert.match(requests[0].url, /\/api\/aion\/business\/data\/working-state\/acme\/aion\.boardroom\.discovery_answers\.v1$/);
  const body = JSON.parse(requests[0].options.body);
  assert.equal(body.payload.storage_key, 'aion.boardroom.discovery_answers.v1');
  assert.equal(body.payload.value, value);
  assert.equal(body.payload.encoding, 'local-storage-string');
  assert.equal(window.__aionBusinessWorkingStateJson['aion.boardroom.discovery_answers.v1'], value);
});

test('legacy business state is removed only after a successful Vault copy', async () => {
  const requests = [];
  const legacy = JSON.stringify({ session: { messages: ['Private customer discussion'] } });
  const { storage } = loadClient({
    entries: { 'aion.chat.sessions.v3': legacy },
    requests,
  });

  assert.equal(storage.getItem('aion.chat.sessions.v3'), legacy);
  assert.equal(storage.values.has('aion.chat.sessions.v3'), true);
  await flushPromises();

  assert.equal(requests.length, 1);
  assert.equal(storage.values.has('aion.chat.sessions.v3'), false);
  assert.equal(storage.getItem('aion.chat.sessions.v3'), legacy);
});

test('disposable interface preferences remain local and outside business authority', async () => {
  const requests = [];
  const { storage } = loadClient({ requests });

  storage.setItem('aion.boardroomViewMode.v1', 'spatial');
  await flushPromises();

  assert.equal(storage.getItem('aion.boardroomViewMode.v1'), 'spatial');
  assert.equal(storage.values.get('aion.boardroomViewMode.v1'), 'spatial');
  assert.equal(requests.length, 0);
});

test('queued saves retain their originating business and revisions do not cross workspaces', async () => {
  const requests = [];
  const { window, storage } = loadClient({ requests });

  storage.setItem('aion.workflow_builder.current_draft.v1', 'acme-v1');
  window.__aionCanonicalBusinessId = 'beta';
  storage.setItem('aion.workflow_builder.current_draft.v1', 'beta-v1');
  await flushPromises();

  assert.equal(requests.length, 2);
  assert.match(requests[0].url, /\/working-state\/acme\/aion\.workflow_builder\.current_draft\.v1$/);
  assert.match(requests[1].url, /\/working-state\/beta\/aion\.workflow_builder\.current_draft\.v1$/);
  assert.equal(JSON.parse(requests[0].options.body).expected_version, undefined);
  assert.equal(JSON.parse(requests[1].options.body).expected_version, undefined);
});

test('a revision conflict refreshes the current Vault version and retries once', async () => {
  const requests = [];
  let putCount = 0;
  const fetchImpl = async (url, options = {}) => {
    requests.push({ url, options });
    if (options.method === 'PUT') {
      putCount += 1;
      if (putCount === 2) {
        return {
          ok: false,
          status: 409,
          json: async () => ({}),
          text: async () => '{"detail":"business_working_state_revision_conflict"}',
        };
      }
      return {
        ok: true,
        json: async () => ({ ok: true, version: putCount === 1 ? 1 : 3 }),
        text: async () => '',
      };
    }
    return {
      ok: true,
      json: async () => ({ ok: true, version: 2 }),
      text: async () => '',
    };
  };
  const { storage } = loadClient({ requests, fetchImpl });

  storage.setItem('aion.workflow_builder.current_draft.v1', 'draft-v1');
  await flushPromises();
  storage.setItem('aion.workflow_builder.current_draft.v1', 'draft-v2');
  await flushPromises();

  assert.equal(requests.length, 4);
  assert.equal(requests[1].options.method, 'PUT');
  assert.equal(JSON.parse(requests[1].options.body).expected_version, 1);
  assert.equal(requests[2].options.method, undefined);
  assert.equal(requests[3].options.method, 'PUT');
  assert.equal(JSON.parse(requests[3].options.body).expected_version, 2);
});
