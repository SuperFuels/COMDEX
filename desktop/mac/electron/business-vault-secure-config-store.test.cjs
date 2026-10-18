"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  BusinessVaultSecureConfigStoreError,
  custodyAttestation,
  matchesCustodyAttestation,
  createBusinessVaultSecureConfigStore,
} = require("./business-vault-secure-config-store");

function fakeSafeStorage(backend = "keychain") {
  return {
    isEncryptionAvailable: () => true,
    getSelectedStorageBackend: () => backend,
    encryptString: (value) => Buffer.from(`sealed:${value}`, "utf8"),
    decryptString: (value) => {
      const text = value.toString("utf8");
      if (!text.startsWith("sealed:")) throw new Error("not sealed");
      return text.slice(7);
    },
  };
}

test("provisions and restores one OS-encrypted business Vault bootstrap", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-vault-config-"));
  const accesses = [];
  const store = createBusinessVaultSecureConfigStore({
    safeStorage: fakeSafeStorage(),
    filePath: path.join(root, "security", "vault.enc.json"),
    randomUUID: () => "12345678-1234-1234-1234-123456789abc",
    randomBytes: () => Buffer.alloc(32, 7),
    onSecretStoreAccess: (...args) => accesses.push(args),
  });
  const created = store.loadOrProvision({ defaultVaultBase: path.join(root, "businesses") });
  assert.equal(created.business_stable_id, "business-12345678-1234-1234-1234-123456789abc");
  assert.equal(store.load().vault_key_b64, created.vault_key_b64);
  const wrapper = fs.readFileSync(store.filePath, "utf8");
  assert.equal(wrapper.includes(created.vault_key_b64), false);
  assert.equal(wrapper.includes("Unregistered business"), false);
  if (process.platform !== "win32") {
    assert.equal(fs.statSync(store.filePath).mode & 0o077, 0);
  }
  assert.deepEqual(accesses, [["secret_store", "provision"], ["secret_store", "load"]]);
});

test("fails closed without a protected operating-system backend", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-vault-config-"));
  const store = createBusinessVaultSecureConfigStore({
    safeStorage: fakeSafeStorage("basic_text"),
    filePath: path.join(root, "vault.enc.json"),
  });
  assert.throws(
    () => store.loadOrProvision({ defaultVaultBase: path.join(root, "businesses") }),
    (error) => error instanceof BusinessVaultSecureConfigStoreError
      && error.code === "business_vault_secret_store_insecure",
  );
});

test("binds one registered business identity once and restores it encrypted", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-vault-identity-"));
  const store = createBusinessVaultSecureConfigStore({
    safeStorage: fakeSafeStorage(),
    filePath: path.join(root, "security", "vault.enc.json"),
  });
  const bound = store.bindIdentity({ businessId: "journey-one-ltd", businessName: "Journey One Ltd" });
  assert.equal(bound.business_id, "journey-one-ltd");
  assert.deepEqual(store.loadIdentityBinding(), bound);
  const wrapper = fs.readFileSync(store.identityBindingPath, "utf8");
  assert.equal(wrapper.includes("Journey One Ltd"), false);
  assert.equal(wrapper.includes("journey-one-ltd"), false);
  assert.deepEqual(
    store.bindIdentity({ businessId: "journey-one-ltd", businessName: "Renamed input ignored" }),
    bound,
  );
  assert.throws(
    () => store.bindIdentity({ businessId: "different-business", businessName: "Different Business" }),
    /business_vault_identity_already_bound/,
  );
});

test("rejects replacement and invalid decrypted configuration", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-vault-config-"));
  const store = createBusinessVaultSecureConfigStore({
    safeStorage: fakeSafeStorage(),
    filePath: path.join(root, "vault.enc.json"),
    randomUUID: () => "12345678-1234-1234-1234-123456789abc",
    randomBytes: () => Buffer.alloc(32, 9),
  });
  const created = store.loadOrProvision({ defaultVaultBase: path.join(root, "businesses") });
  assert.throws(() => store.saveNew(created), /business_vault_config_already_exists/);
  fs.chmodSync(store.filePath, 0o600);
  const wrapper = JSON.parse(fs.readFileSync(store.filePath, "utf8"));
  wrapper.encrypted_config_b64 = Buffer.from("sealed:{}", "utf8").toString("base64");
  fs.writeFileSync(store.filePath, JSON.stringify(wrapper), { mode: 0o600 });
  assert.throws(() => store.load(), /business_vault_config_payload_invalid/);
});

test("binds backend custody to the encrypted business identity without exposing it", () => {
  const config = {
    schema_version: "tessaris.business-vault-bootstrap-config.v1",
    business_name: "Example business",
    business_stable_id: "business-12345678",
    vault_path: path.join(os.tmpdir(), "business-12345678"),
    vault_key_b64: Buffer.alloc(32, 7).toString("base64url"),
  };
  const attestation = custodyAttestation(config);
  assert.equal(attestation.mode, "guardian");
  assert.equal(attestation.business_stable_id_sha256.length, 64);
  assert.equal(JSON.stringify(attestation).includes(config.business_stable_id), false);
  assert.equal(matchesCustodyAttestation(attestation, config), true);
  assert.equal(matchesCustodyAttestation({ ...attestation, mode: "legacy" }, config), false);
  assert.equal(matchesCustodyAttestation({
    ...attestation,
    business_stable_id_sha256: "0".repeat(64),
  }, config), false);
});
