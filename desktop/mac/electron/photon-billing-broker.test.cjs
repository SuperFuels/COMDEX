"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  canonicalBytes,
  canonicalHash,
  createPhotonBillingBroker,
} = require("./photon-billing-broker");

function fixture({ tamperRecord = false, tamperCommercial = false } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-photon-broker-"));
  const sessionPath = path.join(root, "session.json");
  const authorityPublicKeyPath = path.join(root, "wallet-authority.pem");
  const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
  fs.writeFileSync(authorityPublicKeyPath, publicKey.export({ type: "spki", format: "pem" }), { mode: 0o600 });
  const accessToken = {
    payload: {
      schema_version: "tessaris.photon-control-plane-token.v1",
      token_id: "token-1",
      subject_id: "desktop-node-1",
      tenant_id: "home-fixed",
      scopes: ["billing.read", "wallet.read"],
      audience: "tessaris-photon-control-plane",
      issued_at: "2026-10-17T09:59:00.000Z",
      expires_at: "2026-10-17T10:30:00.000Z",
      customer_content_included: false,
    },
    signature: "server-verifies-this-token",
  };
  fs.writeFileSync(sessionPath, JSON.stringify({
    schema_version: "tessaris.photon-desktop-session.v1",
    endpoint: "https://billing.tessaris.example",
    tenant_id: "home-fixed",
    access_token: accessToken,
  }), { mode: 0o600 });
  const walletPayload = {
    schema_version: "tessaris.photon-wallet-snapshot.v1",
    tenant_id: "home-fixed",
    sequence: 7,
    available_photons: 12000,
    reserved_photons: 250,
    lifetime_consumed_photons: 750,
    ledger_transaction_count: 4,
    ledger_anchor: "a".repeat(64),
    issued_at: "2026-10-17T10:00:00.000Z",
    valid_until: "2026-10-17T10:05:00.000Z",
    customer_content_included: false,
    local_model_tokens_billed: false,
  };
  const wallet = {
    payload: walletPayload,
    signature: crypto.sign(null, canonicalBytes(walletPayload), privateKey).toString("base64url"),
  };
  const recordPayload = {
    schema_version: "tessaris.photon-billing-record.v1",
    document_kind: "photon_bundle_payment_receipt",
    tax_invoice: false,
    receipt_id: "revolut:order-1",
    order_id: "order-1",
    external_reference: "photon-order-1",
    product_id: "photon-10000",
    amount_minor: 1000,
    refunded_minor: 0,
    disputed_minor: 0,
    currency: "EUR",
    photons_granted: 10000,
    photons_reversed: 0,
    photons_dispute_reversed: 0,
    commercial_hold: false,
    price_book_version: "price-v1",
    provider: "revolut",
    provider_state: "completed",
    paid_at: "2026-10-17T09:00:00.000Z",
    ledger_transaction_id: "revolut-grant:order-1",
    ledger_transaction_hash: "b".repeat(64),
    customer_content_included: false,
    local_model_tokens_billed: false,
  };
  const record = { ...recordPayload, record_hash: canonicalHash(recordPayload) };
  if (tamperRecord) record.amount_minor += 1;
  const authorization = [];
  const fetchImpl = async (url, options) => {
    authorization.push(options.headers.Authorization);
    return {
      ok: true,
      async json() {
        if (url.endsWith("wallet-snapshot")) return wallet;
        if (url.endsWith("commercial-status")) return {
          tenant_id: tamperCommercial ? "another-business" : "home-fixed",
          commercial_hold: false,
          unresolved_dispute_count: 0,
          disputed_minor: 0,
          photons_pending_reversal: 0,
          customer_content_included: false,
        };
        return { items: [record], customer_content_included: false };
      },
    };
  };
  return {
    root, sessionPath, authorityPublicKeyPath, authorization,
    broker: createPhotonBillingBroker({
      sessionPath,
      authorityPublicKeyPath,
      fetchImpl,
      now: () => new Date("2026-10-17T10:00:30.000Z"),
      randomUUID: () => "00000000-0000-4000-8000-000000000001",
    }),
  };
}

test("returns only verified tenant-bound display data and keeps bearer in main process", async (t) => {
  const value = fixture();
  t.after(() => fs.rmSync(value.root, { recursive: true, force: true }));
  const view = await value.broker.getView("home-fixed");
  assert.equal(view.connected, true);
  assert.equal(view.wallet.available_photons, 12000);
  assert.equal(view.billing_records[0].amount_minor, 1000);
  assert.equal(view.commercial_status.commercial_hold, false);
  assert.equal(view.customer_content_included, false);
  assert.equal(view.local_model_tokens_billed, false);
  assert.equal(JSON.stringify(view).includes("access_token"), false);
  assert.equal(JSON.stringify(view).includes("Authorization"), false);
  assert.equal(value.authorization.length, 3);
  assert.ok(value.authorization.every((header) => header.startsWith("Bearer ")));
});

test("fails closed for tenant mismatch and tampered billing evidence", async (t) => {
  const value = fixture({ tamperRecord: true });
  t.after(() => fs.rmSync(value.root, { recursive: true, force: true }));
  await assert.rejects(() => value.broker.getView("another-business"), /photon_requested_tenant_mismatch/);
  await assert.rejects(() => value.broker.getView("home-fixed"), /photon_billing_record_hash_invalid/);
});

test("rejects a session file readable by other local users", async (t) => {
  const value = fixture();
  t.after(() => fs.rmSync(value.root, { recursive: true, force: true }));
  if (process.platform === "win32") return;
  fs.chmodSync(value.sessionPath, 0o644);
  await assert.rejects(() => value.broker.getView("home-fixed"), /photon_session_permissions_too_open/);
});

test("rejects commercial hold state that is not tenant-bound", async (t) => {
  const value = fixture({ tamperCommercial: true });
  t.after(() => fs.rmSync(value.root, { recursive: true, force: true }));
  await assert.rejects(
    () => value.broker.getView("home-fixed"),
    /photon_commercial_status_boundary_invalid/,
  );
});
