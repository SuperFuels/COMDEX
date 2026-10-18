const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "..", "src", "business-data-browser-storage-discovery.js"),
  "utf8",
);

function browserFixture(enabled) {
  class Storage {
    constructor() { this.values = new Map(); }
    setItem(key, value) { this.values.set(String(key), String(value)); }
    removeItem(key) { this.values.delete(String(key)); }
    clear() { this.values.clear(); }
  }
  const records = [];
  const window = {
    Storage,
    localStorage: new Storage(),
    sessionStorage: new Storage(),
    aionDesktop: {
      businessDataDiscoveryEnabled: enabled,
      recordBusinessDataBrowserWrite(payload) { records.push(payload); },
    },
  };
  vm.runInNewContext(source, { window, Map, Object, String });
  return { window, records };
}

test("renderer storage discovery is inert outside explicit discovery mode", () => {
  const { window, records } = browserFixture(false);
  window.localStorage.setItem("customer-key", "PRIVATE VALUE");
  assert.deepEqual(records, []);
});

test("renderer storage discovery reports operations and keys but never values", () => {
  const { window, records } = browserFixture(true);
  window.localStorage.setItem("customer-key", "PRIVATE VALUE");
  window.sessionStorage.removeItem("transient-key");
  window.localStorage.clear();
  assert.equal(records.length, 3);
  assert.deepEqual(JSON.parse(JSON.stringify(records[0])), {
    operation: "set",
    storageArea: "local",
    key: "customer-key",
  });
  assert.equal(JSON.stringify(records).includes("PRIVATE VALUE"), false);
});
