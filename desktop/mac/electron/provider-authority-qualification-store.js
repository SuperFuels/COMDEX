"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const STORE_SCHEMA = "tessaris.provider-authority-qualification.v1";
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

class ProviderAuthorityQualificationStoreError extends Error {
  constructor(code) {
    super(code);
    this.name = "ProviderAuthorityQualificationStoreError";
    this.code = code;
  }
}

function safeIdentifier(value, code) {
  const identifier = String(value || "").trim();
  if (!SAFE_ID.test(identifier)) throw new ProviderAuthorityQualificationStoreError(code);
  return identifier;
}

function createProviderAuthorityQualificationStore(options = {}) {
  const safeStorage = options.safeStorage;
  const root = path.resolve(String(options.root || ""));
  const fsModule = options.fsModule || fs;
  const randomBytes = options.randomBytes || crypto.randomBytes;

  function requireEncryption() {
    if (!safeStorage || safeStorage.isEncryptionAvailable() !== true) {
      throw new ProviderAuthorityQualificationStoreError("provider_authority_encryption_unavailable");
    }
    const backend = typeof safeStorage.getSelectedStorageBackend === "function"
      ? String(safeStorage.getSelectedStorageBackend() || "")
      : "platform-default";
    if (backend === "basic_text") {
      throw new ProviderAuthorityQualificationStoreError("provider_authority_insecure_linux_backend");
    }
  }

  function authorityPath(candidate, provider) {
    const safeCandidate = safeIdentifier(candidate, "provider_authority_candidate_invalid");
    const safeProvider = safeIdentifier(provider, "provider_authority_provider_invalid");
    return path.join(root, "provider-authority-qualification", safeCandidate, `${safeProvider}.enc.json`);
  }

  function publicState(candidate, provider, generation, connected) {
    return {
      candidate: safeIdentifier(candidate, "provider_authority_candidate_invalid"),
      provider: safeIdentifier(provider, "provider_authority_provider_invalid"),
      connected: Boolean(connected),
      generation: Number.isSafeInteger(generation) && generation > 0 ? generation : 0,
      raw_tokens_exposed: false,
    };
  }

  function load(candidate, provider) {
    const filePath = authorityPath(candidate, provider);
    if (!fsModule.existsSync(filePath)) return null;
    requireEncryption();
    const stat = fsModule.statSync(filePath);
    if (!stat.isFile()) throw new ProviderAuthorityQualificationStoreError("provider_authority_not_file");
    if (process.platform !== "win32" && (stat.mode & 0o077) !== 0) {
      throw new ProviderAuthorityQualificationStoreError("provider_authority_permissions_too_open");
    }
    let wrapper;
    try { wrapper = JSON.parse(fsModule.readFileSync(filePath, "utf8")); }
    catch { throw new ProviderAuthorityQualificationStoreError("provider_authority_wrapper_invalid"); }
    if (!wrapper || wrapper.schema_version !== STORE_SCHEMA
        || typeof wrapper.encrypted_authority_b64 !== "string" || !wrapper.encrypted_authority_b64
        || Object.keys(wrapper).length !== 2) {
      throw new ProviderAuthorityQualificationStoreError("provider_authority_wrapper_invalid");
    }
    try {
      const payload = JSON.parse(safeStorage.decryptString(
        Buffer.from(wrapper.encrypted_authority_b64, "base64"),
      ));
      if (!payload || payload.schema_version !== STORE_SCHEMA
          || payload.candidate !== String(candidate) || payload.provider !== String(provider)
          || !Number.isSafeInteger(payload.generation) || payload.generation <= 0
          || typeof payload.access_token !== "string" || payload.access_token.length < 32
          || typeof payload.refresh_token !== "string" || payload.refresh_token.length < 32) {
        throw new Error("invalid");
      }
      return payload;
    } catch {
      throw new ProviderAuthorityQualificationStoreError("provider_authority_decryption_failed");
    }
  }

  function save(payload) {
    requireEncryption();
    const filePath = authorityPath(payload.candidate, payload.provider);
    const directory = path.dirname(filePath);
    fsModule.mkdirSync(directory, { recursive: true, mode: 0o700 });
    let encrypted;
    try { encrypted = safeStorage.encryptString(JSON.stringify(payload)); }
    catch { throw new ProviderAuthorityQualificationStoreError("provider_authority_encryption_failed"); }
    const temporary = `${filePath}.tmp-${process.pid}-${randomBytes(6).toString("hex")}`;
    try {
      fsModule.writeFileSync(temporary, JSON.stringify({
        schema_version: STORE_SCHEMA,
        encrypted_authority_b64: Buffer.from(encrypted).toString("base64"),
      }), { encoding: "utf8", mode: 0o600, flag: "wx" });
      fsModule.renameSync(temporary, filePath);
      if (process.platform !== "win32") fsModule.chmodSync(filePath, 0o600);
    } catch {
      try { fsModule.unlinkSync(temporary); } catch {}
      throw new ProviderAuthorityQualificationStoreError("provider_authority_write_failed");
    }
  }

  function exercise({ candidate, provider } = {}) {
    safeIdentifier(candidate, "provider_authority_candidate_invalid");
    safeIdentifier(provider, "provider_authority_provider_invalid");
    const existing = load(candidate, provider);
    const generation = (existing?.generation || 0) + 1;
    save({
      schema_version: STORE_SCHEMA,
      candidate: String(candidate),
      provider: String(provider),
      generation,
      access_token: randomBytes(32).toString("base64url"),
      refresh_token: randomBytes(48).toString("base64url"),
    });
    const connected = load(candidate, provider);
    const filePath = authorityPath(candidate, provider);
    fsModule.unlinkSync(filePath);
    if (fsModule.existsSync(filePath)) {
      throw new ProviderAuthorityQualificationStoreError("provider_authority_revoke_failed");
    }
    save({
      schema_version: STORE_SCHEMA,
      candidate: String(candidate),
      provider: String(provider),
      generation: connected.generation + 1,
      access_token: randomBytes(32).toString("base64url"),
      refresh_token: randomBytes(48).toString("base64url"),
    });
    const reconnected = load(candidate, provider);
    return publicState(candidate, provider, reconnected.generation, true);
  }

  return { authorityPath, exercise, load };
}

module.exports = {
  ProviderAuthorityQualificationStoreError,
  STORE_SCHEMA,
  createProviderAuthorityQualificationStore,
};
