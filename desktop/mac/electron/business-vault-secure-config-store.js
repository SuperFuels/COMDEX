"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const STORE_SCHEMA = "tessaris.business-vault-encrypted-bootstrap.v1";
const WRAPPER_FIELDS = new Set(["schema_version", "encrypted_config_b64"]);
const CONFIG_FIELDS = new Set([
  "schema_version", "business_name", "business_stable_id", "vault_path", "vault_key_b64",
]);
const CONFIG_SCHEMA = "tessaris.business-vault-bootstrap-config.v1";
const IDENTITY_BINDING_SCHEMA = "tessaris.business-vault-identity-binding.v1";
const IDENTITY_BINDING_FIELDS = new Set([
  "schema_version", "business_id", "business_name",
]);
const CUSTODY_ATTESTATION_SCHEMA = "tessaris.business-vault-custody-attestation.v1";
const SAFE_ID = /^[a-z0-9][a-z0-9-]{7,127}$/;

class BusinessVaultSecureConfigStoreError extends Error {
  constructor(code) {
    super(code);
    this.name = "BusinessVaultSecureConfigStoreError";
    this.code = code;
  }
}

function exactFields(value, expected) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length === expected.size
    && Object.keys(value).every((key) => expected.has(key)));
}

function requirePrivateFile(filePath, statSync) {
  const stat = statSync(filePath);
  if (!stat.isFile()) throw new BusinessVaultSecureConfigStoreError("business_vault_config_not_file");
  if (process.platform !== "win32" && (stat.mode & 0o077) !== 0) {
    throw new BusinessVaultSecureConfigStoreError("business_vault_config_permissions_too_open");
  }
}

function validateConfig(config) {
  if (!exactFields(config, CONFIG_FIELDS) || config.schema_version !== CONFIG_SCHEMA) {
    throw new BusinessVaultSecureConfigStoreError("business_vault_config_payload_invalid");
  }
  if (typeof config.business_name !== "string" || !config.business_name.trim()
      || config.business_name.length > 200 || !SAFE_ID.test(config.business_stable_id)) {
    throw new BusinessVaultSecureConfigStoreError("business_vault_config_identity_invalid");
  }
  if (typeof config.vault_path !== "string" || !path.isAbsolute(config.vault_path)
      || path.resolve(config.vault_path) === path.parse(path.resolve(config.vault_path)).root) {
    throw new BusinessVaultSecureConfigStoreError("business_vault_config_path_invalid");
  }
  let key;
  try { key = Buffer.from(config.vault_key_b64, "base64url"); }
  catch { throw new BusinessVaultSecureConfigStoreError("business_vault_config_key_invalid"); }
  if (key.length !== 32) {
    throw new BusinessVaultSecureConfigStoreError("business_vault_config_key_invalid");
  }
  return { ...config, vault_path: path.resolve(config.vault_path) };
}

function validateIdentityBinding(binding) {
  if (!exactFields(binding, IDENTITY_BINDING_FIELDS)
      || binding.schema_version !== IDENTITY_BINDING_SCHEMA
      || !SAFE_ID.test(String(binding.business_id || ""))
      || typeof binding.business_name !== "string"
      || !binding.business_name.trim()
      || binding.business_name.length > 200) {
    throw new BusinessVaultSecureConfigStoreError("business_vault_identity_binding_invalid");
  }
  return {
    schema_version: IDENTITY_BINDING_SCHEMA,
    business_id: String(binding.business_id),
    business_name: binding.business_name.trim(),
  };
}

function custodyAttestation(config) {
  const validated = validateConfig(config);
  return {
    schema_version: CUSTODY_ATTESTATION_SCHEMA,
    mode: "guardian",
    business_stable_id_sha256: crypto.createHash("sha256")
      .update(validated.business_stable_id, "utf8")
      .digest("hex"),
  };
}

function matchesCustodyAttestation(candidate, config) {
  const expected = custodyAttestation(config);
  return Boolean(candidate && typeof candidate === "object" && !Array.isArray(candidate)
    && candidate.schema_version === expected.schema_version
    && candidate.mode === expected.mode
    && candidate.business_stable_id_sha256 === expected.business_stable_id_sha256);
}

function createBusinessVaultSecureConfigStore(options = {}) {
  const safeStorage = options.safeStorage;
  const filePath = path.resolve(String(options.filePath || ""));
  const readFileSync = options.readFileSync || fs.readFileSync;
  const writeFileSync = options.writeFileSync || fs.writeFileSync;
  const renameSync = options.renameSync || fs.renameSync;
  const unlinkSync = options.unlinkSync || fs.unlinkSync;
  const mkdirSync = options.mkdirSync || fs.mkdirSync;
  const statSync = options.statSync || fs.statSync;
  const existsSync = options.existsSync || fs.existsSync;
  const randomBytes = options.randomBytes || crypto.randomBytes;
  const randomUUID = options.randomUUID || crypto.randomUUID;
  const onSecretStoreAccess = typeof options.onSecretStoreAccess === "function"
    ? options.onSecretStoreAccess : () => {};
  const identityBindingPath = `${filePath}.identity`;

  function requireEncryption() {
    if (!safeStorage || safeStorage.isEncryptionAvailable() !== true) {
      throw new BusinessVaultSecureConfigStoreError("business_vault_secret_store_unavailable");
    }
    const backend = typeof safeStorage.getSelectedStorageBackend === "function"
      ? String(safeStorage.getSelectedStorageBackend() || "") : "platform-default";
    if (backend === "basic_text") {
      throw new BusinessVaultSecureConfigStoreError("business_vault_secret_store_insecure");
    }
  }

  function load() {
    if (!existsSync(filePath)) return null;
    requireEncryption();
    requirePrivateFile(filePath, statSync);
    let wrapper;
    try { wrapper = JSON.parse(readFileSync(filePath, "utf8")); }
    catch { throw new BusinessVaultSecureConfigStoreError("business_vault_config_wrapper_invalid"); }
    if (!exactFields(wrapper, WRAPPER_FIELDS) || wrapper.schema_version !== STORE_SCHEMA
        || typeof wrapper.encrypted_config_b64 !== "string" || !wrapper.encrypted_config_b64) {
      throw new BusinessVaultSecureConfigStoreError("business_vault_config_wrapper_invalid");
    }
    try {
      const plaintext = safeStorage.decryptString(Buffer.from(wrapper.encrypted_config_b64, "base64"));
      const config = validateConfig(JSON.parse(plaintext));
      onSecretStoreAccess("secret_store", "load");
      return config;
    } catch (error) {
      if (error instanceof BusinessVaultSecureConfigStoreError) throw error;
      throw new BusinessVaultSecureConfigStoreError("business_vault_config_decryption_failed");
    }
  }

  function saveNew(config) {
    if (existsSync(filePath)) {
      throw new BusinessVaultSecureConfigStoreError("business_vault_config_already_exists");
    }
    requireEncryption();
    const validated = validateConfig(config);
    let encrypted;
    try { encrypted = safeStorage.encryptString(JSON.stringify(validated)); }
    catch { throw new BusinessVaultSecureConfigStoreError("business_vault_config_encryption_failed"); }
    const directory = path.dirname(filePath);
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    const temporary = `${filePath}.tmp-${process.pid}`;
    try {
      writeFileSync(temporary, JSON.stringify({
        schema_version: STORE_SCHEMA,
        encrypted_config_b64: Buffer.from(encrypted).toString("base64"),
      }), { encoding: "utf8", mode: 0o600, flag: "wx" });
      renameSync(temporary, filePath);
    } catch (error) {
      try { unlinkSync(temporary); } catch {}
      if (error instanceof BusinessVaultSecureConfigStoreError) throw error;
      throw new BusinessVaultSecureConfigStoreError("business_vault_config_write_failed");
    }
    onSecretStoreAccess("secret_store", "provision");
    return validated;
  }

  function loadIdentityBinding() {
    if (!existsSync(identityBindingPath)) return null;
    requireEncryption();
    requirePrivateFile(identityBindingPath, statSync);
    let wrapper;
    try { wrapper = JSON.parse(readFileSync(identityBindingPath, "utf8")); }
    catch { throw new BusinessVaultSecureConfigStoreError("business_vault_identity_binding_wrapper_invalid"); }
    if (!exactFields(wrapper, WRAPPER_FIELDS) || wrapper.schema_version !== STORE_SCHEMA
        || typeof wrapper.encrypted_config_b64 !== "string" || !wrapper.encrypted_config_b64) {
      throw new BusinessVaultSecureConfigStoreError("business_vault_identity_binding_wrapper_invalid");
    }
    try {
      const plaintext = safeStorage.decryptString(Buffer.from(wrapper.encrypted_config_b64, "base64"));
      const binding = validateIdentityBinding(JSON.parse(plaintext));
      onSecretStoreAccess("secret_store", "identity_load");
      return binding;
    } catch (error) {
      if (error instanceof BusinessVaultSecureConfigStoreError) throw error;
      throw new BusinessVaultSecureConfigStoreError("business_vault_identity_binding_decryption_failed");
    }
  }

  function bindIdentity({ businessId, businessName } = {}) {
    const binding = validateIdentityBinding({
      schema_version: IDENTITY_BINDING_SCHEMA,
      business_id: businessId,
      business_name: businessName,
    });
    const existing = loadIdentityBinding();
    if (existing) {
      if (existing.business_id !== binding.business_id) {
        throw new BusinessVaultSecureConfigStoreError("business_vault_identity_already_bound");
      }
      return existing;
    }
    requireEncryption();
    let encrypted;
    try { encrypted = safeStorage.encryptString(JSON.stringify(binding)); }
    catch { throw new BusinessVaultSecureConfigStoreError("business_vault_identity_binding_encryption_failed"); }
    const directory = path.dirname(identityBindingPath);
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    const temporary = `${identityBindingPath}.tmp-${process.pid}`;
    try {
      writeFileSync(temporary, JSON.stringify({
        schema_version: STORE_SCHEMA,
        encrypted_config_b64: Buffer.from(encrypted).toString("base64"),
      }), { encoding: "utf8", mode: 0o600, flag: "wx" });
      renameSync(temporary, identityBindingPath);
    } catch (error) {
      try { unlinkSync(temporary); } catch {}
      if (error instanceof BusinessVaultSecureConfigStoreError) throw error;
      throw new BusinessVaultSecureConfigStoreError("business_vault_identity_binding_write_failed");
    }
    onSecretStoreAccess("secret_store", "identity_bind");
    return binding;
  }

  function loadOrProvision({ defaultVaultBase, businessName = "Unregistered business" } = {}) {
    const existing = load();
    if (existing) return existing;
    const stableId = `business-${String(randomUUID()).toLowerCase()}`;
    return saveNew({
      schema_version: CONFIG_SCHEMA,
      business_name: businessName,
      business_stable_id: stableId,
      vault_path: path.join(path.resolve(defaultVaultBase), stableId),
      vault_key_b64: Buffer.from(randomBytes(32)).toString("base64url"),
    });
  }

  return {
    filePath, identityBindingPath, load, saveNew, loadOrProvision,
    loadIdentityBinding, bindIdentity,
  };
}

module.exports = {
  BusinessVaultSecureConfigStoreError,
  CONFIG_SCHEMA,
  IDENTITY_BINDING_SCHEMA,
  CUSTODY_ATTESTATION_SCHEMA,
  STORE_SCHEMA,
  custodyAttestation,
  matchesCustodyAttestation,
  createBusinessVaultSecureConfigStore,
};
