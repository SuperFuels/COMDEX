"use strict";

const fs = require("fs");
const path = require("path");

const STORE_SCHEMA = "tessaris.photon-encrypted-desktop-session.v1";
const STORE_FIELDS = new Set(["schema_version", "encrypted_session_b64"]);

class PhotonSecureSessionStoreError extends Error {
  constructor(code) {
    super(code);
    this.name = "PhotonSecureSessionStoreError";
    this.code = code;
  }
}

function exactFields(value, fields) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length === fields.size
    && Object.keys(value).every((key) => fields.has(key)));
}

function privateFile(filePath, statSync) {
  const stat = statSync(filePath);
  if (!stat.isFile()) throw new PhotonSecureSessionStoreError("photon_secure_session_not_file");
  if (process.platform !== "win32" && (stat.mode & 0o077) !== 0) {
    throw new PhotonSecureSessionStoreError("photon_secure_session_permissions_too_open");
  }
}

function createPhotonSecureSessionStore(options = {}) {
  const safeStorage = options.safeStorage;
  const filePath = path.resolve(String(options.filePath || ""));
  const readFileSync = options.readFileSync || fs.readFileSync;
  const writeFileSync = options.writeFileSync || fs.writeFileSync;
  const renameSync = options.renameSync || fs.renameSync;
  const unlinkSync = options.unlinkSync || fs.unlinkSync;
  const mkdirSync = options.mkdirSync || fs.mkdirSync;
  const statSync = options.statSync || fs.statSync;
  const existsSync = options.existsSync || fs.existsSync;

  function requireEncryption() {
    if (!safeStorage || safeStorage.isEncryptionAvailable() !== true) {
      throw new PhotonSecureSessionStoreError("photon_secure_session_encryption_unavailable");
    }
    const backend = typeof safeStorage.getSelectedStorageBackend === "function"
      ? String(safeStorage.getSelectedStorageBackend() || "")
      : "platform-default";
    if (backend === "basic_text") {
      throw new PhotonSecureSessionStoreError("photon_secure_session_insecure_linux_backend");
    }
  }

  function load() {
    if (!existsSync(filePath)) return null;
    requireEncryption();
    privateFile(filePath, statSync);
    let wrapper;
    try { wrapper = JSON.parse(readFileSync(filePath, "utf8")); }
    catch { throw new PhotonSecureSessionStoreError("photon_secure_session_wrapper_invalid"); }
    if (!exactFields(wrapper, STORE_FIELDS) || wrapper.schema_version !== STORE_SCHEMA
        || typeof wrapper.encrypted_session_b64 !== "string" || !wrapper.encrypted_session_b64) {
      throw new PhotonSecureSessionStoreError("photon_secure_session_wrapper_invalid");
    }
    try {
      const plaintext = safeStorage.decryptString(Buffer.from(wrapper.encrypted_session_b64, "base64"));
      const session = JSON.parse(plaintext);
      if (!session || typeof session !== "object" || Array.isArray(session)) throw new Error("invalid");
      return session;
    } catch {
      throw new PhotonSecureSessionStoreError("photon_secure_session_decryption_failed");
    }
  }

  function saveFromTrustedMainProcess(session) {
    requireEncryption();
    if (!session || typeof session !== "object" || Array.isArray(session)) {
      throw new PhotonSecureSessionStoreError("photon_secure_session_payload_invalid");
    }
    const plaintext = JSON.stringify(session);
    let encrypted;
    try { encrypted = safeStorage.encryptString(plaintext); }
    catch { throw new PhotonSecureSessionStoreError("photon_secure_session_encryption_failed"); }
    const directory = path.dirname(filePath);
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    const temporary = `${filePath}.tmp-${process.pid}`;
    try {
      writeFileSync(temporary, JSON.stringify({
        schema_version: STORE_SCHEMA,
        encrypted_session_b64: Buffer.from(encrypted).toString("base64"),
      }), { encoding: "utf8", mode: 0o600, flag: "wx" });
      renameSync(temporary, filePath);
    } catch (error) {
      try { unlinkSync(temporary); } catch {}
      if (error instanceof PhotonSecureSessionStoreError) throw error;
      throw new PhotonSecureSessionStoreError("photon_secure_session_write_failed");
    }
    return { saved: true, schema_version: STORE_SCHEMA };
  }

  return { load, saveFromTrustedMainProcess, filePath };
}

module.exports = {
  PhotonSecureSessionStoreError,
  STORE_SCHEMA,
  createPhotonSecureSessionStore,
};
