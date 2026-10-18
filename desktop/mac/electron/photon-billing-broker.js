"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const SESSION_SCHEMA = "tessaris.photon-desktop-session.v1";
const TOKEN_SCHEMA = "tessaris.photon-control-plane-token.v1";
const SNAPSHOT_SCHEMA = "tessaris.photon-wallet-snapshot.v1";
const BILLING_RECORD_SCHEMA = "tessaris.photon-billing-record.v1";
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$/;
const SESSION_FIELDS = new Set(["schema_version", "endpoint", "tenant_id", "access_token"]);
const TOKEN_FIELDS = new Set([
  "schema_version", "token_id", "subject_id", "tenant_id", "scopes", "audience",
  "issued_at", "expires_at", "customer_content_included",
]);
const SNAPSHOT_FIELDS = new Set([
  "schema_version", "tenant_id", "sequence", "available_photons", "reserved_photons",
  "lifetime_consumed_photons", "ledger_transaction_count", "ledger_anchor", "issued_at",
  "valid_until", "customer_content_included", "local_model_tokens_billed",
]);
const BILLING_RECORD_FIELDS = new Set([
  "schema_version", "document_kind", "tax_invoice", "receipt_id", "order_id",
  "external_reference", "product_id", "amount_minor", "refunded_minor",
  "disputed_minor", "currency", "photons_granted", "photons_reversed",
  "photons_dispute_reversed", "commercial_hold", "price_book_version", "provider",
  "provider_state", "paid_at", "ledger_transaction_id", "ledger_transaction_hash",
  "customer_content_included", "local_model_tokens_billed", "record_hash",
]);

class PhotonBillingBrokerError extends Error {
  constructor(code) {
    super(code);
    this.name = "PhotonBillingBrokerError";
    this.code = code;
  }
}

function exactFields(value, expected) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const fields = Object.keys(value);
  return fields.length === expected.size && fields.every((field) => expected.has(field));
}

function canonicalValue(value) {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === "object") {
    return Object.keys(value).sort().reduce((result, key) => {
      result[key] = canonicalValue(value[key]);
      return result;
    }, {});
  }
  return value;
}

function canonicalBytes(value) {
  return Buffer.from(JSON.stringify(canonicalValue(value)), "utf8");
}

function canonicalHash(value) {
  return crypto.createHash("sha256").update(canonicalBytes(value)).digest("hex");
}

function parseCurrentTime(value, code) {
  const timestamp = Date.parse(String(value || ""));
  if (!Number.isFinite(timestamp)) throw new PhotonBillingBrokerError(code);
  return timestamp;
}

function assertPrivateFile(filePath, statSync = fs.statSync) {
  const stat = statSync(filePath);
  if (!stat.isFile()) throw new PhotonBillingBrokerError("photon_session_not_file");
  if (process.platform !== "win32" && (stat.mode & 0o077) !== 0) {
    throw new PhotonBillingBrokerError("photon_session_permissions_too_open");
  }
}

function validateEndpoint(rawEndpoint, allowLoopback) {
  let endpoint;
  try {
    endpoint = new URL(rawEndpoint);
  } catch {
    throw new PhotonBillingBrokerError("photon_endpoint_invalid");
  }
  const loopback = ["127.0.0.1", "localhost", "::1"].includes(endpoint.hostname);
  if (endpoint.protocol !== "https:" && !(allowLoopback && loopback && endpoint.protocol === "http:")) {
    throw new PhotonBillingBrokerError("photon_endpoint_tls_required");
  }
  if (endpoint.username || endpoint.password || endpoint.search || endpoint.hash) {
    throw new PhotonBillingBrokerError("photon_endpoint_credentials_prohibited");
  }
  return endpoint.toString().replace(/\/$/, "");
}

function readSession({ sessionPath, sessionLoader, authorityPublicKeyPath, readFileSync, statSync, now, allowLoopback }) {
  if ((!sessionPath && !sessionLoader) || !authorityPublicKeyPath) {
    throw new PhotonBillingBrokerError("photon_billing_not_connected");
  }
  assertPrivateFile(authorityPublicKeyPath, statSync);
  let session;
  try {
    if (sessionLoader) session = sessionLoader();
    else {
      assertPrivateFile(sessionPath, statSync);
      session = JSON.parse(readFileSync(sessionPath, "utf8"));
    }
  } catch (error) {
    if (error instanceof PhotonBillingBrokerError) throw error;
    throw new PhotonBillingBrokerError("photon_session_invalid");
  }
  if (!session) throw new PhotonBillingBrokerError("photon_billing_not_connected");
  if (!exactFields(session, SESSION_FIELDS) || session.schema_version !== SESSION_SCHEMA) {
    throw new PhotonBillingBrokerError("photon_session_fields_invalid");
  }
  const tenantId = String(session.tenant_id || "");
  if (!SAFE_ID.test(tenantId)) throw new PhotonBillingBrokerError("photon_session_tenant_invalid");
  const envelope = session.access_token;
  if (!envelope || !exactFields(envelope, new Set(["payload", "signature"]))) {
    throw new PhotonBillingBrokerError("photon_access_token_invalid");
  }
  const token = envelope.payload;
  if (!exactFields(token, TOKEN_FIELDS) || token.schema_version !== TOKEN_SCHEMA) {
    throw new PhotonBillingBrokerError("photon_access_token_fields_invalid");
  }
  if (token.tenant_id !== tenantId || token.audience !== "tessaris-photon-control-plane") {
    throw new PhotonBillingBrokerError("photon_access_token_binding_invalid");
  }
  if (token.customer_content_included !== false) {
    throw new PhotonBillingBrokerError("photon_access_token_content_prohibited");
  }
  const scopes = new Set(Array.isArray(token.scopes) ? token.scopes : []);
  if (!scopes.has("wallet.read") || !scopes.has("billing.read")) {
    throw new PhotonBillingBrokerError("photon_access_token_scope_missing");
  }
  const nowMs = now().getTime();
  if (nowMs < parseCurrentTime(token.issued_at, "photon_access_token_time_invalid")
      || nowMs >= parseCurrentTime(token.expires_at, "photon_access_token_time_invalid")) {
    throw new PhotonBillingBrokerError("photon_access_token_not_current");
  }
  let publicKey;
  try {
    publicKey = crypto.createPublicKey(readFileSync(authorityPublicKeyPath, "utf8"));
    if (publicKey.asymmetricKeyType !== "ed25519") throw new Error("not Ed25519");
  } catch {
    throw new PhotonBillingBrokerError("photon_wallet_authority_key_invalid");
  }
  return {
    tenantId,
    endpoint: validateEndpoint(session.endpoint, allowLoopback),
    bearer: Buffer.from(JSON.stringify(envelope), "utf8").toString("base64url"),
    tokenExpiresAt: parseCurrentTime(token.expires_at, "photon_access_token_time_invalid"),
    publicKey,
  };
}

function verifySnapshot(envelope, { publicKey, tenantId, nowMs, minimumSequence }) {
  if (!envelope || !exactFields(envelope, new Set(["payload", "signature"]))) {
    throw new PhotonBillingBrokerError("photon_wallet_snapshot_invalid");
  }
  const payload = envelope.payload;
  if (!exactFields(payload, SNAPSHOT_FIELDS) || payload.schema_version !== SNAPSHOT_SCHEMA) {
    throw new PhotonBillingBrokerError("photon_wallet_snapshot_fields_invalid");
  }
  let signature;
  try { signature = Buffer.from(String(envelope.signature || ""), "base64url"); }
  catch { throw new PhotonBillingBrokerError("photon_wallet_snapshot_signature_invalid"); }
  if (!crypto.verify(null, canonicalBytes(payload), publicKey, signature)) {
    throw new PhotonBillingBrokerError("photon_wallet_snapshot_signature_invalid");
  }
  if (payload.tenant_id !== tenantId) throw new PhotonBillingBrokerError("photon_wallet_snapshot_tenant_mismatch");
  if (payload.customer_content_included !== false || payload.local_model_tokens_billed !== false) {
    throw new PhotonBillingBrokerError("photon_wallet_snapshot_content_prohibited");
  }
  const sequence = Number(payload.sequence);
  if (!Number.isSafeInteger(sequence) || sequence <= minimumSequence) {
    throw new PhotonBillingBrokerError("photon_wallet_snapshot_replay_or_rollback");
  }
  if (nowMs < parseCurrentTime(payload.issued_at, "photon_wallet_snapshot_time_invalid")
      || nowMs >= parseCurrentTime(payload.valid_until, "photon_wallet_snapshot_time_invalid")) {
    throw new PhotonBillingBrokerError("photon_wallet_snapshot_not_current");
  }
  for (const field of ["available_photons", "reserved_photons", "lifetime_consumed_photons", "ledger_transaction_count"]) {
    if (!Number.isSafeInteger(payload[field]) || payload[field] < 0) {
      throw new PhotonBillingBrokerError("photon_wallet_snapshot_balance_invalid");
    }
  }
  if (!/^[0-9a-f]{64}$/.test(String(payload.ledger_anchor || ""))) {
    throw new PhotonBillingBrokerError("photon_wallet_snapshot_anchor_invalid");
  }
  return payload;
}

function verifyBillingRecord(record) {
  if (!exactFields(record, BILLING_RECORD_FIELDS) || record.schema_version !== BILLING_RECORD_SCHEMA) {
    throw new PhotonBillingBrokerError("photon_billing_record_fields_invalid");
  }
  const payload = { ...record };
  delete payload.record_hash;
  if (canonicalHash(payload) !== record.record_hash) {
    throw new PhotonBillingBrokerError("photon_billing_record_hash_invalid");
  }
  if (record.document_kind !== "photon_bundle_payment_receipt" || record.tax_invoice !== false
      || record.provider !== "revolut" || record.customer_content_included !== false
      || record.local_model_tokens_billed !== false) {
    throw new PhotonBillingBrokerError("photon_billing_record_boundary_invalid");
  }
  for (const field of [
    "amount_minor", "refunded_minor", "disputed_minor", "photons_granted",
    "photons_reversed", "photons_dispute_reversed",
  ]) {
    if (!Number.isSafeInteger(record[field]) || record[field] < 0) {
      throw new PhotonBillingBrokerError("photon_billing_record_amount_invalid");
    }
  }
  if (typeof record.commercial_hold !== "boolean") {
    throw new PhotonBillingBrokerError("photon_billing_record_hold_invalid");
  }
  if (!/^[A-Z]{3}$/.test(record.currency) || !/^[0-9a-f]{64}$/.test(record.record_hash)
      || !/^[0-9a-f]{64}$/.test(record.ledger_transaction_hash)) {
    throw new PhotonBillingBrokerError("photon_billing_record_format_invalid");
  }
  return {
    receipt_id: String(record.receipt_id),
    amount_minor: record.amount_minor,
    refunded_minor: record.refunded_minor,
    disputed_minor: record.disputed_minor,
    currency: record.currency,
    photons_granted: record.photons_granted,
    photons_reversed: record.photons_reversed,
    photons_dispute_reversed: record.photons_dispute_reversed,
    commercial_hold: record.commercial_hold,
    provider_state: String(record.provider_state),
    paid_at: String(record.paid_at),
    price_book_version: String(record.price_book_version),
    record_hash: record.record_hash,
    document_kind: record.document_kind,
    tax_invoice: false,
  };
}

function createPhotonBillingBroker(options = {}) {
  const readFileSync = options.readFileSync || fs.readFileSync;
  const statSync = options.statSync || fs.statSync;
  const fetchImpl = options.fetchImpl || global.fetch;
  const now = options.now || (() => new Date());
  const randomUUID = options.randomUUID || crypto.randomUUID;
  const minimumSequences = new Map();

  async function post(endpoint, pathName, bearer, payload) {
    const response = await fetchImpl(`${endpoint}${pathName}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: `Bearer ${bearer}` },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    if (!response.ok) throw new PhotonBillingBrokerError(`photon_control_plane_${response.status}`);
    return await response.json();
  }

  return {
    async getView(expectedTenantId) {
      const tenant = String(expectedTenantId || "").trim();
      if (!SAFE_ID.test(tenant)) throw new PhotonBillingBrokerError("photon_requested_tenant_invalid");
      const session = readSession({
        sessionPath: options.sessionPath,
        sessionLoader: options.sessionLoader,
        authorityPublicKeyPath: options.authorityPublicKeyPath,
        readFileSync, statSync, now,
        allowLoopback: options.allowLoopback === true,
      });
      if (session.tenantId !== tenant) throw new PhotonBillingBrokerError("photon_requested_tenant_mismatch");
      const issuedAt = now();
      const validUntilMs = Math.min(issuedAt.getTime() + 5 * 60_000, session.tokenExpiresAt - 1_000);
      if (validUntilMs <= issuedAt.getTime()) throw new PhotonBillingBrokerError("photon_access_token_expiring");
      const [snapshotEnvelope, billingEnvelope, commercialEnvelope] = await Promise.all([
        post(session.endpoint, "/api/control-plane/photon/wallet-snapshot", session.bearer, {
          request_id: `desktop-wallet-${randomUUID()}`,
          valid_until: new Date(validUntilMs).toISOString(),
        }),
        post(session.endpoint, "/api/control-plane/photon/billing-records", session.bearer, {
          request_id: `desktop-billing-${randomUUID()}`,
          limit: 50,
          export_format: "json",
        }),
        post(session.endpoint, "/api/control-plane/photon/commercial-status", session.bearer, {
          request_id: `desktop-commercial-${randomUUID()}`,
        }),
      ]);
      const snapshot = verifySnapshot(snapshotEnvelope, {
        publicKey: session.publicKey,
        tenantId: tenant,
        nowMs: issuedAt.getTime(),
        minimumSequence: minimumSequences.get(tenant) || 0,
      });
      if (!billingEnvelope || billingEnvelope.customer_content_included !== false
          || !Array.isArray(billingEnvelope.items)) {
        throw new PhotonBillingBrokerError("photon_billing_response_boundary_invalid");
      }
      const billingRecords = billingEnvelope.items.map(verifyBillingRecord);
      if (!commercialEnvelope || commercialEnvelope.tenant_id !== tenant
          || commercialEnvelope.customer_content_included !== false
          || typeof commercialEnvelope.commercial_hold !== "boolean"
          || !Number.isSafeInteger(commercialEnvelope.unresolved_dispute_count)
          || commercialEnvelope.unresolved_dispute_count < 0
          || !Number.isSafeInteger(commercialEnvelope.disputed_minor)
          || commercialEnvelope.disputed_minor < 0
          || !Number.isSafeInteger(commercialEnvelope.photons_pending_reversal)
          || commercialEnvelope.photons_pending_reversal < 0) {
        throw new PhotonBillingBrokerError("photon_commercial_status_boundary_invalid");
      }
      minimumSequences.set(tenant, snapshot.sequence);
      return {
        connected: true,
        tenant_id: tenant,
        wallet: {
          available_photons: snapshot.available_photons,
          reserved_photons: snapshot.reserved_photons,
          lifetime_consumed_photons: snapshot.lifetime_consumed_photons,
          ledger_transaction_count: snapshot.ledger_transaction_count,
          sequence: snapshot.sequence,
          valid_until: snapshot.valid_until,
        },
        billing_records: billingRecords,
        commercial_status: {
          commercial_hold: commercialEnvelope.commercial_hold,
          unresolved_dispute_count: commercialEnvelope.unresolved_dispute_count,
          disputed_minor: commercialEnvelope.disputed_minor,
          photons_pending_reversal: commercialEnvelope.photons_pending_reversal,
        },
        customer_content_included: false,
        local_model_tokens_billed: false,
      };
    },
  };
}

module.exports = {
  PhotonBillingBrokerError,
  canonicalBytes,
  canonicalHash,
  createPhotonBillingBroker,
};
