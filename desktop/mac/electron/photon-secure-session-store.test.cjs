"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createPhotonSecureSessionStore } = require("./photon-secure-session-store");

function fakeSafeStorage(backend = "keychain") {
  const key = crypto.randomBytes(32);
  return {
    isEncryptionAvailable: () => true,
    getSelectedStorageBackend: () => backend,
    encryptString(value) {
      const nonce = crypto.randomBytes(12);
      const cipher = crypto.createCipheriv("aes-256-gcm", key, nonce);
      const ciphertext = Buffer.concat([cipher.update(value, "utf8"), cipher.final()]);
      return Buffer.concat([nonce, cipher.getAuthTag(), ciphertext]);
    },
    decryptString(value) {
      const decipher = crypto.createDecipheriv("aes-256-gcm", key, value.subarray(0, 12));
      decipher.setAuthTag(value.subarray(12, 28));
      return Buffer.concat([decipher.update(value.subarray(28)), decipher.final()]).toString("utf8");
    },
  };
}

test("stores a Photon session as owner-only OS-encrypted material", (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-photon-secure-store-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const filePath = path.join(root, "security", "session.enc.json");
  const store = createPhotonSecureSessionStore({ safeStorage: fakeSafeStorage(), filePath });
  const session = { schema_version: "test", access_token: { secret: "never-plaintext" } };
  store.saveFromTrustedMainProcess(session);
  const raw = fs.readFileSync(filePath, "utf8");
  assert.equal(raw.includes("never-plaintext"), false);
  assert.deepEqual(store.load(), session);
  if (process.platform !== "win32") assert.equal(fs.statSync(filePath).mode & 0o077, 0);
});

test("fails closed when Electron reports insecure or unavailable encryption", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-photon-secure-store-"));
  try {
    const filePath = path.join(root, "session.enc.json");
    const insecure = createPhotonSecureSessionStore({ safeStorage: fakeSafeStorage("basic_text"), filePath });
    assert.throws(() => insecure.saveFromTrustedMainProcess({ value: 1 }), /photon_secure_session_insecure_linux_backend/);
    const unavailable = createPhotonSecureSessionStore({
      safeStorage: { isEncryptionAvailable: () => false }, filePath,
    });
    assert.throws(() => unavailable.saveFromTrustedMainProcess({ value: 1 }), /photon_secure_session_encryption_unavailable/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
