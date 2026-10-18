"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  createProviderAuthorityQualificationStore,
} = require("./provider-authority-qualification-store");

function fakeSafeStorage() {
  return {
    isEncryptionAvailable: () => true,
    getSelectedStorageBackend: () => "keychain",
    encryptString: (value) => Buffer.from(`sealed:${value}`, "utf8"),
    decryptString: (value) => String(value).replace(/^sealed:/, ""),
  };
}

test("main-process authority qualification keeps tokens encrypted and reconnects after revoke", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "provider-authority-main-"));
  const store = createProviderAuthorityQualificationStore({ root, safeStorage: fakeSafeStorage() });
  const state = store.exercise({ candidate: "stripe", provider: "oauth" });
  assert.deepEqual(state, {
    candidate: "stripe",
    provider: "oauth",
    connected: true,
    generation: 2,
    raw_tokens_exposed: false,
  });
  const filePath = store.authorityPath("stripe", "oauth");
  assert.equal(fs.statSync(filePath).mode & 0o077, 0);
  const wrapper = fs.readFileSync(filePath, "utf8");
  assert.equal(wrapper.includes("access_token"), false);
  assert.equal(wrapper.includes("refresh_token"), false);
  assert.equal(store.load("stripe", "oauth").generation, 2);
});

test("qualification rejects path-like provider identities", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "provider-authority-main-"));
  const store = createProviderAuthorityQualificationStore({ root, safeStorage: fakeSafeStorage() });
  assert.throws(
    () => store.exercise({ candidate: "../stripe", provider: "oauth" }),
    /provider_authority_candidate_invalid/,
  );
});
