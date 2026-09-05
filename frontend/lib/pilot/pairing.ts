export type MotherDescriptor = {
  schema_version: "pilot.mother-descriptor.v1";
  mother_id: string;
  mother_public_key: string;
  mother_fingerprint: string;
  endpoint: string;
  ca_sha256: string;
  issued_at: string;
  expires_at: string;
  mother_signature: string;
};

type StoredDeviceKey = {
  id: "pilot-device-key-v1";
  privateKey: CryptoKey;
  publicKey: string;
  createdAt: string;
};

type StoredInboxCursor = {
  id: string;
  motherId: string;
  deviceId: string;
  revision: number;
  updatedAt: string;
};

export type PhonePairingChallenge = {
  schema_version: "pilot.phone-pairing-challenge.v1";
  challenge_id: string;
  mother_id: string;
  mother_fingerprint: string;
  mother_descriptor_hash: string;
  persona_id: string;
  device_id: string;
  device_label: string;
  phone_public_key: string;
  requested_scopes: string[];
  nonce: string;
  issued_at: string;
  expires_at: string;
  mother_descriptor: MotherDescriptor;
  mother_signature: string;
};

export type PilotMobileConnection = {
  id: "pilot-mobile-connection-v1";
  endpoint: string;
  liveInboxUrl?: string;
  motherDescriptor?: MotherDescriptor;
  directRemoteRoute?: Record<string, unknown>;
  opaqueRelayRoute?: Record<string, unknown>;
  trustWords: string[];
  certificate: Record<string, unknown>;
  lease: Record<string, unknown>;
  connectedAt: string;
};

type StoredRecord = StoredDeviceKey | PilotMobileConnection | StoredInboxCursor;

const DATABASE = "pilot-private-device";
const STORE = "keys";

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((value) => { binary += String.fromCharCode(value); });
  return btoa(binary);
}

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function arrayBuffer(bytes: Uint8Array): ArrayBuffer {
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).sort(([left], [right]) => left.localeCompare(right));
    return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`).join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error("Pilot could not open protected phone storage"));
  });
}

async function readStoredKey(): Promise<StoredDeviceKey | undefined> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const request = database.transaction(STORE, "readonly").objectStore(STORE).get("pilot-device-key-v1");
    request.onsuccess = () => { resolve(request.result as StoredDeviceKey | undefined); database.close(); };
    request.onerror = () => reject(new Error("Pilot could not read this phone key"));
  });
}

async function writeStoredKey(record: StoredDeviceKey): Promise<void> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE, "readwrite");
    transaction.objectStore(STORE).put(record);
    transaction.oncomplete = () => { database.close(); resolve(); };
    transaction.onerror = () => reject(new Error("Pilot could not protect this phone key"));
  });
}

async function readRecord<T extends StoredRecord>(id: string): Promise<T | undefined> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const request = database.transaction(STORE, "readonly").objectStore(STORE).get(id);
    request.onsuccess = () => { resolve(request.result as T | undefined); database.close(); };
    request.onerror = () => reject(new Error("Pilot could not read this protected connection"));
  });
}

async function writeRecord(record: StoredRecord): Promise<void> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE, "readwrite");
    transaction.objectStore(STORE).put(record);
    transaction.oncomplete = () => { database.close(); resolve(); };
    transaction.onerror = () => reject(new Error("Pilot could not protect this connection"));
  });
}

export async function ensurePilotDeviceKey(): Promise<{ publicKey: string; created: boolean }> {
  if (!window.isSecureContext || !window.crypto?.subtle || !window.indexedDB) {
    throw new Error("Open Pilot through its trusted secure address to connect this phone");
  }
  const existing = await readStoredKey();
  if (existing?.privateKey && existing.publicKey) return { publicKey: existing.publicKey, created: false };

  const generated = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]) as CryptoKeyPair;
  const rawPublic = new Uint8Array(await crypto.subtle.exportKey("raw", generated.publicKey));
  const exportedPrivate = new Uint8Array(await crypto.subtle.exportKey("pkcs8", generated.privateKey));
  const protectedPrivate = await crypto.subtle.importKey("pkcs8", exportedPrivate, { name: "Ed25519" }, false, ["sign"]);
  exportedPrivate.fill(0);
  const record: StoredDeviceKey = {
    id: "pilot-device-key-v1",
    privateKey: protectedPrivate,
    publicKey: bytesToBase64(rawPublic),
    createdAt: new Date().toISOString(),
  };
  await writeStoredKey(record);
  return { publicKey: record.publicKey, created: true };
}

export async function signPilotPayload(payload: Record<string, unknown>): Promise<string> {
  const stored = await readStoredKey();
  if (!stored?.privateKey) throw new Error("Connect this phone to Pilot first");
  const signature = await crypto.subtle.sign("Ed25519", stored.privateKey, new TextEncoder().encode(canonical(payload)));
  return bytesToBase64(new Uint8Array(signature));
}

export async function verifyMotherDescriptor(descriptor: MotherDescriptor, expectedFingerprint?: string): Promise<boolean> {
  try {
    if (descriptor.schema_version !== "pilot.mother-descriptor.v1" || new Date(descriptor.expires_at).getTime() <= Date.now()) return false;
    const endpoint = new URL(descriptor.endpoint);
    if (endpoint.protocol !== "https:" || endpoint.username || endpoint.password || endpoint.pathname !== "/") return false;
    const publicBytes = base64ToBytes(descriptor.mother_public_key);
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", arrayBuffer(publicBytes)));
    const fingerprint = Array.from(digest.slice(0, 16)).map((value) => value.toString(16).padStart(2, "0")).join("");
    if (fingerprint !== descriptor.mother_fingerprint || (expectedFingerprint && fingerprint !== expectedFingerprint)) return false;
    const { mother_signature, ...payload } = descriptor;
    const publicKey = await crypto.subtle.importKey("raw", arrayBuffer(publicBytes), { name: "Ed25519" }, false, ["verify"]);
    return crypto.subtle.verify(
      "Ed25519",
      publicKey,
      arrayBuffer(base64ToBytes(mother_signature)),
      new TextEncoder().encode(canonical(payload)),
    );
  } catch {
    return false;
  }
}

function normalizedEndpoint(value: string): string {
  const parsed = new URL(value.trim());
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || (parsed.pathname !== "/" && parsed.pathname !== "")) {
    throw new Error("Use the trusted HTTPS address shown by your Pilot");
  }
  parsed.pathname = "";
  parsed.search = "";
  parsed.hash = "";
  return parsed.toString().replace(/\/$/, "");
}

async function postJson(endpoint: string, path: string, body: Record<string, unknown>, signal?: AbortSignal): Promise<Record<string, unknown>> {
  const response = await fetch(`${endpoint}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });
  const result = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok) throw new Error(String(result.error || "Pilot could not complete that secure request"));
  return result;
}

async function verifiedDirectRemoteEndpoints(connection: PilotMobileConnection): Promise<string[]> {
  const route = connection.directRemoteRoute;
  const mother = connection.motherDescriptor;
  if (!route || !mother || route.schema_version !== "pilot.direct-remote-route.v1") return [];
  if (new Date(String(route.expires_at || "")).getTime() <= Date.now()) return [];
  if (route.mother_id !== connection.certificate.mother_id || route.mother_fingerprint !== connection.certificate.mother_fingerprint) return [];
  if (route.relay_used !== false || route.contains_mother_secret !== false) return [];
  if (!await verifyMotherRecord(route, mother)) return [];
  const candidates = Array.isArray(route.endpoints) ? route.endpoints.map(String) : [];
  if (candidates.length > 4 || new Set(candidates).size !== candidates.length) return [];
  return candidates.map(normalizedEndpoint);
}

async function verifyRemoteMother(endpoint: string, connection: PilotMobileConnection, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`${endpoint}/.well-known/pilot-mother`, { cache: "no-store", signal });
  const result = await response.json().catch(() => ({})) as Record<string, unknown>;
  const descriptor = result.descriptor as MotherDescriptor;
  if (!response.ok || !descriptor || !await verifyMotherDescriptor(descriptor, String(connection.certificate.mother_fingerprint || ""))) {
    throw new Error("A remote endpoint could not prove it is your Pilot");
  }
  if (descriptor.mother_id !== connection.certificate.mother_id) {
    throw new Error("A remote endpoint presented a different Pilot identity");
  }
}

async function verifiedOpaqueRelayRoute(connection: PilotMobileConnection): Promise<Record<string, unknown> | undefined> {
  const route = connection.opaqueRelayRoute;
  const mother = connection.motherDescriptor;
  if (!route || !mother || route.schema_version !== "pilot.opaque-relay-route.v1") return undefined;
  if (new Date(String(route.expires_at || "")).getTime() <= Date.now()) return undefined;
  if (route.mother_id !== connection.certificate.mother_id || route.mother_fingerprint !== connection.certificate.mother_fingerprint) return undefined;
  if (route.operator_can_read_content !== false || route.contains_mother_secret !== false) return undefined;
  if (route.content_encryption !== "x25519_hkdf_sha256_aes_256_gcm") return undefined;
  if (!await verifyMotherRecord(route, mother)) return undefined;
  normalizedEndpoint(String(route.relay_endpoint || ""));
  if (!/^relay_[0-9a-f]{32}$/.test(String(route.opaque_route_id || ""))) return undefined;
  if (base64ToBytes(String(route.mother_transport_public_key || "")).byteLength !== 32) return undefined;
  if (String(route.submission_token || "").length < 32) return undefined;
  return route;
}

async function relayKey(shared: ArrayBuffer, requestId: string, direction: "request" | "response"): Promise<CryptoKey> {
  const material = await crypto.subtle.importKey("raw", shared, "HKDF", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    {
      name: "HKDF",
      hash: "SHA-256",
      salt: new Uint8Array(),
      info: new TextEncoder().encode(canonical({ protocol: "pilot-opaque-relay-v1", request_id: requestId, direction })),
    },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    [direction === "request" ? "encrypt" : "decrypt"],
  );
}

async function postViaOpaqueRelay(
  connection: PilotMobileConnection,
  path: string,
  body: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  const route = await verifiedOpaqueRelayRoute(connection);
  if (!route) throw new TypeError("No verified private relay route is available");
  const relayEndpoint = normalizedEndpoint(String(route.relay_endpoint));
  const routeId = String(route.opaque_route_id);
  const requestId = `relay_request_${crypto.randomUUID().replaceAll("-", "")}`;
  const generated = await crypto.subtle.generateKey("X25519", true, ["deriveBits"]) as CryptoKeyPair;
  const motherKey = await crypto.subtle.importKey(
    "raw", arrayBuffer(base64ToBytes(String(route.mother_transport_public_key))), "X25519", false, [],
  );
  const shared = await crypto.subtle.deriveBits({ name: "X25519", public: motherKey }, generated.privateKey, 256);
  const key = await relayKey(shared, requestId, "request");
  const now = new Date();
  const lifetime = Math.min(120, Math.max(5, Number(route.request_lifetime_seconds || 120)));
  const metadata = {
    schema_version: "pilot.opaque-relay-request.v1",
    opaque_route_id: routeId,
    request_id: requestId,
    created_at: now.toISOString(),
    expires_at: new Date(now.getTime() + lifetime * 1000).toISOString(),
    ephemeral_public_key: bytesToBase64(new Uint8Array(await crypto.subtle.exportKey("raw", generated.publicKey))),
  };
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce, additionalData: new TextEncoder().encode(canonical(metadata)), tagLength: 128 },
    key,
    new TextEncoder().encode(canonical({ path, body })),
  );
  const envelope = {
    ...metadata,
    nonce: bytesToBase64(nonce),
    ciphertext: bytesToBase64(new Uint8Array(ciphertext)),
  };
  if (JSON.stringify(envelope).length > Number(route.max_envelope_bytes || 0)) {
    throw new Error("That private request is too large for the relay route");
  }
  const submissionToken = String(route.submission_token);
  const submitted = await fetch(`${relayEndpoint}/v1/relay/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ envelope, submission_token: submissionToken }),
    cache: "no-store",
    signal,
  });
  if (!submitted.ok) throw new TypeError("The private relay could not accept this request");

  const deadline = Date.now() + lifetime * 1000;
  while (Date.now() < deadline) {
    if (signal?.aborted) throw new DOMException("Relay request cancelled", "AbortError");
    const response = await fetch(`${relayEndpoint}/v1/relay/responses`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ opaque_route_id: routeId, request_id: requestId, submission_token: submissionToken }),
      cache: "no-store",
      signal,
    });
    if (response.status === 204) {
      await new Promise((resolve) => window.setTimeout(resolve, 650));
      continue;
    }
    if (!response.ok) throw new TypeError("The private relay response was unavailable");
    const relayResponse = await response.json() as Record<string, unknown>;
    const responseEnvelope = (relayResponse.envelope || relayResponse) as Record<string, unknown>;
    const responseMetadata = {
      schema_version: responseEnvelope.schema_version,
      opaque_route_id: responseEnvelope.opaque_route_id,
      request_id: responseEnvelope.request_id,
      created_at: responseEnvelope.created_at,
      expires_at: responseEnvelope.expires_at,
    };
    if (
      responseMetadata.schema_version !== "pilot.opaque-relay-response.v1"
      || responseMetadata.opaque_route_id !== routeId
      || responseMetadata.request_id !== requestId
      || new Date(String(responseMetadata.expires_at || "")).getTime() <= Date.now()
    ) throw new Error("Pilot rejected an invalid private relay response");
    const responseKey = await relayKey(shared, requestId, "response");
    const plaintext = await crypto.subtle.decrypt(
      {
        name: "AES-GCM",
        iv: arrayBuffer(base64ToBytes(String(responseEnvelope.nonce || ""))),
        additionalData: new TextEncoder().encode(canonical(responseMetadata)),
        tagLength: 128,
      },
      responseKey,
      arrayBuffer(base64ToBytes(String(responseEnvelope.ciphertext || ""))),
    );
    const decoded = JSON.parse(new TextDecoder().decode(plaintext)) as { status: number; body: Record<string, unknown> };
    if (!Number.isInteger(decoded.status) || !decoded.body || typeof decoded.body !== "object") {
      throw new Error("Pilot could not verify the private relay response");
    }
    if (decoded.status < 200 || decoded.status >= 300) {
      throw new Error(String(decoded.body.error || "Pilot could not complete that secure request"));
    }
    return decoded.body;
  }
  throw new TypeError("Pilot is still unreachable through the private relay");
}

async function postConnectedJson(
  connection: PilotMobileConnection,
  path: string,
  body: Record<string, unknown>,
  onRoute?: (route: "lan" | "direct" | "relay") => void,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  try {
    const result = await postJson(connection.endpoint, path, body, signal);
    onRoute?.("lan");
    return result;
  } catch (localError) {
    if (!(localError instanceof TypeError)) throw localError;
    const candidates = await verifiedDirectRemoteEndpoints(connection);
    for (const endpoint of candidates) {
      try {
        await verifyRemoteMother(endpoint, connection, signal);
        const result = await postJson(endpoint, path, body, signal);
        onRoute?.("direct");
        return result;
      } catch (remoteError) {
        if (!(remoteError instanceof TypeError)) throw remoteError;
      }
    }
    try {
      const result = await postViaOpaqueRelay(connection, path, body, signal);
      onRoute?.("relay");
      return result;
    } catch (relayError) {
      if (!(relayError instanceof TypeError)) throw relayError;
    }
    throw localError;
  }
}

async function verifyMotherRecord(record: Record<string, unknown>, descriptor: MotherDescriptor): Promise<boolean> {
  try {
    const signature = String(record.mother_signature || "");
    const payload = { ...record };
    delete payload.mother_signature;
    const publicKey = await crypto.subtle.importKey(
      "raw",
      arrayBuffer(base64ToBytes(descriptor.mother_public_key)),
      { name: "Ed25519" },
      false,
      ["verify"],
    );
    return crypto.subtle.verify(
      "Ed25519",
      publicKey,
      arrayBuffer(base64ToBytes(signature)),
      new TextEncoder().encode(canonical(payload)),
    );
  } catch {
    return false;
  }
}

export async function discoverPilot(value: string): Promise<{ endpoint: string; descriptor: MotherDescriptor; trustWords: string[]; liveInboxUrl?: string }> {
  const endpoint = normalizedEndpoint(value);
  const response = await fetch(`${endpoint}/.well-known/pilot-mother`, { cache: "no-store" });
  const result = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok) throw new Error(String(result.error || "Pilot was not found at that address"));
  const descriptor = result.descriptor as MotherDescriptor;
  if (!await verifyMotherDescriptor(descriptor) || normalizedEndpoint(descriptor.endpoint) !== endpoint) {
    throw new Error("This Pilot could not prove its identity");
  }
  let liveInboxUrl: string | undefined;
  if (result.inbox_websocket_url) {
    const candidate = new URL(String(result.inbox_websocket_url));
    if (candidate.protocol !== "wss:" || candidate.hostname !== new URL(endpoint).hostname || candidate.pathname !== "/v1/inbox/live") {
      throw new Error("Pilot advertised an invalid private Inbox address");
    }
    liveInboxUrl = candidate.toString();
  }
  return { endpoint, descriptor, trustWords: Array.isArray(result.trust_words) ? result.trust_words.map(String) : [], liveInboxUrl };
}

export async function beginPilotPairing(args: {
  endpoint: string;
  personaId?: string;
  deviceLabel: string;
}): Promise<{ challenge: PhonePairingChallenge; trustWords: string[]; liveInboxUrl?: string }> {
  const discovered = await discoverPilot(args.endpoint);
  const phone = await ensurePilotDeviceKey();
  const result = await postJson(discovered.endpoint, "/v1/pairing/challenges", {
    persona_id: args.personaId || "",
    device_label: args.deviceLabel,
    phone_public_key: phone.publicKey,
    requested_scopes: [
      "inbox.read", "message.send", "task.create", "task.respond", "tv.control",
      "calendar.read", "calendar.propose", "calendar.approve", "calendar.execute",
      "contacts.read", "contacts.write", "contacts.resolve",
      "communication.read", "communication.draft", "communication.approve",
      "communication.execute", "communication.convert", "communication.followup", "communication.call",
      "communication.invite", "communication.invite.claim", "communication.protect",
      "services.read", "services.propose", "services.approve", "services.execute",
      "library.read", "library.write", "library.continue",
      "devices.read", "devices.discover", "devices.control", "tv.observe",
      "experiences.read", "experiences.control",
      "memory.read", "memory.write", "memory.export",
      "guardian.read", "guardian.configure", "guardian.alert",
      "intelligence.read", "intelligence.use", "intelligence.configure",
      "workspace.invitations.read", "workspace.invitations.respond",
      "workspace.read",
      "workspace.conversation",
      "workspace.cards.read", "workspace.cards.act", "workspace.approve",
      "workspace.signoff.prepare", "workspace.signoff.read", "workspace.signoff",
      "workspace.files.reference",
      "workspace.desktop.handoff",
      "workspace.commercial.read", "workspace.commercial.control",
    ],
  }) as unknown as PhonePairingChallenge;
  if (result.mother_fingerprint !== discovered.descriptor.mother_fingerprint || !await verifyMotherDescriptor(result.mother_descriptor, discovered.descriptor.mother_fingerprint)) {
    throw new Error("The Pilot identity changed during connection");
  }
  const signed = { ...result } as Record<string, unknown>;
  delete signed.mother_descriptor;
  delete signed.mother_signature;
  if (!await verifyMotherRecord({ ...signed, mother_signature: result.mother_signature }, discovered.descriptor)) {
    throw new Error("Pilot returned an unverified connection challenge");
  }
  return { challenge: result, trustWords: discovered.trustWords, liveInboxUrl: discovered.liveInboxUrl };
}

export async function completePilotPairing(args: {
  endpoint: string;
  challenge: PhonePairingChallenge;
  confirmationCode: string;
  trustWords: string[];
  liveInboxUrl?: string;
}): Promise<PilotMobileConnection> {
  const { mother_descriptor: descriptor, mother_signature: _signature, ...signedChallenge } = args.challenge;
  const phoneSignature = await signPilotPayload(signedChallenge);
  const result = await postJson(normalizedEndpoint(args.endpoint), "/v1/pairing/complete", {
    challenge_id: args.challenge.challenge_id,
    confirmation_code: args.confirmationCode,
    phone_signature: phoneSignature,
  });
  const certificate = result.certificate as Record<string, unknown>;
  const lease = result.lease as Record<string, unknown>;
  if (!await verifyMotherRecord(certificate, descriptor) || !await verifyMotherRecord(lease, descriptor)) {
    throw new Error("Pilot returned an unverified phone connection");
  }
  const connection: PilotMobileConnection = {
    id: "pilot-mobile-connection-v1",
    endpoint: normalizedEndpoint(args.endpoint),
    liveInboxUrl: args.liveInboxUrl,
    motherDescriptor: descriptor,
    directRemoteRoute: result.direct_remote_route && await verifyMotherRecord(result.direct_remote_route as Record<string, unknown>, descriptor)
      ? result.direct_remote_route as Record<string, unknown>
      : undefined,
    opaqueRelayRoute: result.opaque_relay_route && await verifyMotherRecord(result.opaque_relay_route as Record<string, unknown>, descriptor)
      ? result.opaque_relay_route as Record<string, unknown>
      : undefined,
    trustWords: args.trustWords,
    certificate,
    lease,
    connectedAt: new Date().toISOString(),
  };
  await writeRecord(connection);
  return connection;
}

export async function getPilotConnection(): Promise<PilotMobileConnection | undefined> {
  return readRecord<PilotMobileConnection>("pilot-mobile-connection-v1");
}

export async function readPilotInbox(
  connection: PilotMobileConnection,
  onRoute?: (route: "lan" | "direct" | "relay") => void,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  return postConnectedJson(connection, "/v1/inbox/stream", {
    persona_id: String(connection.certificate.persona_id || ""),
    certificate: connection.certificate,
    lease: connection.lease,
  }, onRoute, signal);
}

export async function readTrustedPilotHandoffs(
  connection: PilotMobileConnection,
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    purpose: "read_trusted_handoffs",
  };
  return postConnectedJson(connection, "/v1/network/handoffs/snapshot", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function sendTrustedPilotHandoff(
  connection: PilotMobileConnection,
  args: {
    handoffType: "message" | "task" | "reminder" | "file" | "moment";
    relationshipId: string;
    recipientPersonaId: string;
    recipientMotherId: string;
    title?: string;
    body?: string;
    detail?: string;
    dueAt?: string;
    file?: File;
    momentId?: string;
    contextHash?: string;
    providerUrl?: string;
  },
): Promise<Record<string, unknown>> {
  const request: Record<string, unknown> = {
    persona_id: String(connection.certificate.persona_id || ""),
    recipient_persona_id: args.recipientPersonaId,
    recipient_mother_id: args.recipientMotherId,
    relationship_id: args.relationshipId,
    handoff_type: args.handoffType,
    idempotency_key: `trusted_handoff_${crypto.randomUUID()}`,
  };
  if (args.handoffType === "message") request.body = args.body || "";
  if (args.handoffType === "task") request.title = args.title || "";
  if (args.handoffType === "reminder") {
    request.card_type = "reminder";
    request.title = args.title || "";
    request.detail = args.detail || "";
    request.due_at = args.dueAt || "";
  }
  if (args.handoffType === "file") {
    if (!args.file || args.file.size > 1_000_000) throw new Error("Choose a supported file smaller than 1 MB");
    const bytes = new Uint8Array(await args.file.arrayBuffer());
    request.filename = args.file.name;
    request.media_type = args.file.type || "application/octet-stream";
    request.content_base64 = bytesToBase64(bytes);
    bytes.fill(0);
  }
  if (args.handoffType === "moment") {
    request.card_type = "moment";
    request.title = args.title || "Pilot Moment";
    request.detail = args.detail || "Rights-safe shared context";
    request.moment_id = args.momentId || "";
    request.context_hash = args.contextHash || "";
    request.share_mode = "context_card";
    request.provider_url = args.providerUrl || "";
    request.rights = { protected_audio_copied: false, protected_video_copied: false };
  }
  return postConnectedJson(connection, "/v1/network/handoffs/send", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function approveTrustedPilotTask(
  connection: PilotMobileConnection,
  args: { relationshipId: string; recipientPersonaId: string; actionId: string; scopeHash: string },
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    recipient_persona_id: args.recipientPersonaId,
    relationship_id: args.relationshipId,
    action_id: args.actionId,
    scope_hash: args.scopeHash,
    decision: "approved",
    idempotency_key: `trusted_task_approval_${crypto.randomUUID()}`,
  };
  return postConnectedJson(connection, "/v1/network/handoffs/tasks/approve", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function actOnPilotTask(
  connection: PilotMobileConnection,
  actionId: string,
  event: "accepted" | "declined" | "read" | "corrected" | "cancelled" | "snoozed" | "completed",
  details: { title?: string; until?: string } = {},
): Promise<Record<string, unknown>> {
  const request: Record<string, unknown> = {
    persona_id: String(connection.certificate.persona_id || ""),
    action_id: actionId,
    idempotency_key: `phone_${crypto.randomUUID()}`,
  };
  let path = "/v1/inbox/tasks/transition";
  if (event === "accepted" || event === "declined") {
    request.decision = event;
    path = "/v1/inbox/tasks/respond";
  } else {
    request.event = event;
    if (details.title) request.title = details.title;
    if (details.until) request.until = details.until;
  }
  return postConnectedJson(connection, path, {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function searchPilotInbox(
  connection: PilotMobileConnection,
  query: string,
  kind: "all" | "messages" | "tasks" | "files" = "all",
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    query: query.trim(),
    kind,
    idempotency_key: `search_${crypto.randomUUID()}`,
  };
  return postConnectedJson(connection, "/v1/inbox/search", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function downloadPilotAttachment(
  connection: PilotMobileConnection,
  attachmentId: string,
): Promise<{ filename: string; mediaType: string; bytes: Uint8Array }> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    attachment_id: attachmentId,
    idempotency_key: `attachment_read_${crypto.randomUUID()}`,
  };
  const result = await postConnectedJson(connection, "/v1/inbox/attachments/read", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
  return {
    filename: String(result.filename || "Pilot attachment"),
    mediaType: String(result.media_type || "application/octet-stream"),
    bytes: base64ToBytes(String(result.content_base64 || "")),
  };
}

export async function sendPilotAttachment(
  connection: PilotMobileConnection,
  args: { recipientPersonaId: string; recipientMotherId: string; file: File },
): Promise<Record<string, unknown>> {
  if (args.file.size > 1_000_000) throw new Error("Choose a file smaller than 1 MB");
  const bytes = new Uint8Array(await args.file.arrayBuffer());
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    recipient_persona_id: args.recipientPersonaId,
    recipient_mother_id: args.recipientMotherId,
    filename: args.file.name,
    media_type: args.file.type || "application/octet-stream",
    content_base64: bytesToBase64(bytes),
    idempotency_key: `attachment_send_${crypto.randomUUID()}`,
  };
  bytes.fill(0);
  return postConnectedJson(connection, "/v1/inbox/attachments/send", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function controlPilotPttFloor(
  connection: PilotMobileConnection,
  args: {
    operation: "acquire" | "renew" | "release";
    recipientPersonaId?: string;
    recipientMotherId?: string;
    floorId?: string;
  },
): Promise<Record<string, unknown>> {
  const request: Record<string, unknown> = {
    persona_id: String(connection.certificate.persona_id || ""),
    operation: args.operation,
    idempotency_key: `ptt_${args.operation}_${crypto.randomUUID()}`,
  };
  if (args.recipientPersonaId) request.recipient_persona_id = args.recipientPersonaId;
  if (args.recipientMotherId) request.recipient_mother_id = args.recipientMotherId;
  if (args.floorId) request.floor_id = args.floorId;
  return postConnectedJson(connection, "/v1/inbox/ptt/floor", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function sendPilotVoiceNote(
  connection: PilotMobileConnection,
  args: {
    recipientPersonaId: string;
    recipientMotherId: string;
    floorId: string;
    blob: Blob;
    durationMs: number;
    retentionSeconds?: number;
  },
): Promise<Record<string, unknown>> {
  if (args.blob.size > 1_500_000) throw new Error("Keep voice notes below 1.5 MB");
  const bytes = new Uint8Array(await args.blob.arrayBuffer());
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    recipient_persona_id: args.recipientPersonaId,
    recipient_mother_id: args.recipientMotherId,
    media_type: args.blob.type.split(";", 1)[0] || "audio/webm",
    content_base64: bytesToBase64(bytes),
    duration_ms: Math.max(100, Math.min(120_000, Math.round(args.durationMs))),
    retention_seconds: args.retentionSeconds || 86_400,
    ptt_floor_id: args.floorId,
    idempotency_key: `voice_note_${crypto.randomUUID()}`,
  };
  bytes.fill(0);
  return postConnectedJson(connection, "/v1/inbox/voice-notes/send", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function sendPilotStructuredCard(
  connection: PilotMobileConnection,
  args: {
    recipientPersonaId: string;
    recipientMotherId: string;
    cardType: "reminder" | "follow_up" | "calendar" | "document_review";
    title: string;
    detail?: string;
    dueAt?: string;
    startsAt?: string;
    endsAt?: string;
  },
): Promise<Record<string, unknown>> {
  const request: Record<string, unknown> = {
    persona_id: String(connection.certificate.persona_id || ""),
    recipient_persona_id: args.recipientPersonaId,
    recipient_mother_id: args.recipientMotherId,
    card_type: args.cardType,
    title: args.title,
    detail: args.detail || "",
    idempotency_key: `card_${crypto.randomUUID()}`,
  };
  if (args.dueAt) request.due_at = args.dueAt;
  if (args.startsAt) request.starts_at = args.startsAt;
  if (args.endsAt) request.ends_at = args.endsAt;
  return postConnectedJson(connection, "/v1/inbox/cards/send", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function readPersonalPilot(
  connection: PilotMobileConnection,
): Promise<Record<string, unknown>> {
  const request = {
    purpose: "read_personal_pilot",
    persona_id: String(connection.certificate.persona_id || ""),
  };
  return postConnectedJson(connection, "/v1/personal/snapshot", {
    request,
    certificate: connection.certificate,
    lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function createPersonalReminder(
  connection: PilotMobileConnection,
  args: {
    taskId: string;
    trigger: "time" | "arrival" | "departure" | "journey" | "closing_time";
    at?: string;
    locationLabel?: string;
    repetition?: string;
    locationPermissionId?: string;
  },
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    task_id: args.taskId,
    trigger: args.trigger,
    at: args.at || "",
    location_label: args.locationLabel || "",
    repetition: args.repetition || "none",
    location_permission_id: args.locationPermissionId || "",
    idempotency_key: `reminder_create_${crypto.randomUUID()}`,
  };
  return postConnectedJson(connection, "/v1/personal/reminders/create", {
    request, certificate: connection.certificate, lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function updatePersonalReminder(
  connection: PilotMobileConnection,
  reminderId: string,
  operation: "snooze" | "complete" | "cancel",
  until?: string,
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    reminder_id: reminderId,
    operation,
    until: until || "",
    idempotency_key: `reminder_${operation}_${crypto.randomUUID()}`,
  };
  return postConnectedJson(connection, "/v1/personal/reminders/transition", {
    request, certificate: connection.certificate, lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

async function postSignedPersonal(
  connection: PilotMobileConnection,
  path: string,
  request: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return postConnectedJson(connection, path, {
    request, certificate: connection.certificate, lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function readPersonalCalendar(connection: PilotMobileConnection): Promise<Record<string, unknown>> {
  const request = {
    purpose: "read_private_calendar",
    persona_id: String(connection.certificate.persona_id || ""),
  };
  return postSignedPersonal(connection, "/v1/personal/calendar/snapshot", request);
}

export async function readPersonalAvailability(
  connection: PilotMobileConnection,
  args: { start: string; end: string; slotMinutes: number },
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    start: args.start,
    end: args.end,
    slot_minutes: args.slotMinutes,
    idempotency_key: `calendar_availability_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/calendar/availability", request);
}

export async function preparePersonalCalendarChange(
  connection: PilotMobileConnection,
  args: {
    action: "create" | "reschedule" | "cancel";
    title: string;
    start?: string;
    end?: string;
    providerEventId?: string;
    location?: string;
    travelMinutes?: number;
    reminderMinutes?: number;
    calendarId?: string;
    timeZone?: string;
    attendees?: string[];
    description?: string;
    notifyAttendees?: boolean;
  },
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    action: args.action,
    title: args.title,
    start: args.start || "",
    end: args.end || "",
    provider_event_id: args.providerEventId || "",
    location: args.location || "",
    travel_minutes: args.travelMinutes || 0,
    reminder_minutes: args.reminderMinutes || 0,
    calendar_id: args.calendarId || "primary",
    time_zone: args.timeZone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    attendees: args.attendees || [],
    description: args.description || "",
    notify_attendees: Boolean(args.notifyAttendees),
    idempotency_key: `calendar_prepare_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/calendar/prepare", request);
}

export async function decidePersonalCalendarChange(
  connection: PilotMobileConnection,
  proposalId: string,
  scopeHash: string,
  approved: boolean,
  acceptConflicts = false,
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    proposal_id: proposalId,
    scope_hash: scopeHash,
    approved,
    accept_conflicts: acceptConflicts,
    idempotency_key: `calendar_decide_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/calendar/decide", request);
}

export async function executePersonalCalendarChange(
  connection: PilotMobileConnection,
  proposalId: string,
  scopeHash: string,
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    proposal_id: proposalId,
    scope_hash: scopeHash,
    idempotency_key: `calendar_execute_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/calendar/execute", request);
}

export async function readPersonalContacts(
  connection: PilotMobileConnection,
  query = "",
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    query: query.trim(),
    idempotency_key: `contacts_read_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/contacts/snapshot", request);
}

export async function savePersonalContact(
  connection: PilotMobileConnection,
  args: {
    contactId?: string;
    displayName: string;
    email?: string;
    whatsapp?: string;
    pilotPersonaId?: string;
    pilotMotherId?: string;
    preferredRoute?: "pilot" | "whatsapp" | "email" | "";
  },
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    contact_id: args.contactId || "",
    display_name: args.displayName.trim(),
    email: args.email?.trim() || "",
    whatsapp: args.whatsapp?.trim() || "",
    pilot_persona_id: args.pilotPersonaId?.trim() || "",
    pilot_mother_id: args.pilotMotherId?.trim() || "",
    preferred_route: args.preferredRoute || "",
    idempotency_key: `contact_save_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/contacts/save", request);
}

export async function removePersonalContact(
  connection: PilotMobileConnection,
  contactId: string,
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    contact_id: contactId,
    idempotency_key: `contact_remove_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/contacts/remove", request);
}

export async function resolvePersonalContact(
  connection: PilotMobileConnection,
  displayName: string,
  requestedRoute = "",
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    display_name: displayName.trim(),
    requested_route: requestedRoute,
    idempotency_key: `contact_resolve_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/contacts/resolve", request);
}

export async function readPersonalCommunication(
  connection: PilotMobileConnection,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/communication/snapshot", {
    purpose: "read_private_communication",
    persona_id: String(connection.certificate.persona_id || ""),
    idempotency_key: `communication_read_${crypto.randomUUID()}`,
  });
}

export async function preparePersonalCommunication(
  connection: PilotMobileConnection,
  args: { contactId: string; channel: "email" | "whatsapp" | "pilot"; subject?: string; body: string; replyToMessageId?: string },
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/communication/prepare", {
    persona_id: String(connection.certificate.persona_id || ""),
    contact_id: args.contactId,
    channel: args.channel,
    subject: args.subject?.trim() || "",
    body: args.body.trim(),
    reply_to_message_id: args.replyToMessageId || "",
    idempotency_key: `communication_prepare_${crypto.randomUUID()}`,
  });
}

export async function decidePersonalCommunication(
  connection: PilotMobileConnection, draftId: string, contentHash: string, approved: boolean,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/communication/decide", {
    persona_id: String(connection.certificate.persona_id || ""),
    draft_id: draftId, content_hash: contentHash, approved,
    idempotency_key: `communication_decide_${crypto.randomUUID()}`,
  });
}

export async function executePersonalCommunication(
  connection: PilotMobileConnection, draftId: string, contentHash: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/communication/execute", {
    persona_id: String(connection.certificate.persona_id || ""),
    draft_id: draftId, content_hash: contentHash,
    idempotency_key: `communication_execute_${crypto.randomUUID()}`,
  });
}

export async function convertReceivedCommunication(
  connection: PilotMobileConnection, messageId: string, target: "task" | "reminder" | "calendar",
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/communication/convert", {
    persona_id: String(connection.certificate.persona_id || ""),
    message_id: messageId, target,
    idempotency_key: `communication_convert_${crypto.randomUUID()}`,
  });
}

export async function scheduleCommunicationFollowUp(
  connection: PilotMobileConnection, draftId: string, dueAt: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/communication/follow-up", {
    persona_id: String(connection.certificate.persona_id || ""),
    draft_id: draftId, due_at: dueAt,
    idempotency_key: `communication_followup_${crypto.randomUUID()}`,
  });
}

export async function prepareCommunicationCall(
  connection: PilotMobileConnection, contactId: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/communication/call", {
    persona_id: String(connection.certificate.persona_id || ""),
    contact_id: contactId,
    idempotency_key: `communication_call_${crypto.randomUUID()}`,
  });
}

export async function createCommunicationInvitation(
  connection: PilotMobileConnection,
  draftId: string,
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    draft_id: draftId,
    public_base_url: connection.endpoint,
    idempotency_key: `communication_invite_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/communication/invite", request);
}

export async function protectCommunicationContact(
  connection: PilotMobileConnection,
  contactId: string,
  operation: "block" | "report",
  category = "spam",
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    contact_id: contactId,
    operation,
    category,
    idempotency_key: `communication_${operation}_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/communication/protect", request);
}

export async function readPersonalServices(connection: PilotMobileConnection): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/services/snapshot", {
    purpose: "read_private_service_actions",
    persona_id: String(connection.certificate.persona_id || ""),
    idempotency_key: `services_read_${crypto.randomUUID()}`,
  });
}

export async function preparePersonalServiceAction(
  connection: PilotMobileConnection,
  service: "shopping" | "booking" | "maps" | "music",
  action: string,
  parameters: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/services/prepare", {
    persona_id: String(connection.certificate.persona_id || ""), service, action, parameters,
    idempotency_key: `services_prepare_${crypto.randomUUID()}`,
  });
}

export async function updatePersonalServiceDetails(
  connection: PilotMobileConnection, proposalId: string, details: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/services/update", {
    persona_id: String(connection.certificate.persona_id || ""), proposal_id: proposalId, details,
    idempotency_key: `services_update_${crypto.randomUUID()}`,
  });
}

export async function decidePersonalServiceAction(
  connection: PilotMobileConnection, proposalId: string, parametersHash: string, approved: boolean,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/services/decide", {
    persona_id: String(connection.certificate.persona_id || ""), proposal_id: proposalId,
    parameters_hash: parametersHash, approved,
    idempotency_key: `services_decide_${crypto.randomUUID()}`,
  });
}

export async function executePersonalServiceAction(
  connection: PilotMobileConnection, proposalId: string, parametersHash: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/services/execute", {
    persona_id: String(connection.certificate.persona_id || ""), proposal_id: proposalId,
    parameters_hash: parametersHash,
    idempotency_key: `services_execute_${crypto.randomUUID()}`,
  });
}

export async function readPersonalLibrary(connection: PilotMobileConnection): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/library/snapshot", {
    purpose: "read_private_library",
    persona_id: String(connection.certificate.persona_id || ""),
    idempotency_key: `library_read_${crypto.randomUUID()}`,
  });
}

export async function claimPersonalLibraryItem(
  connection: PilotMobileConnection, saveId: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/library/claim", {
    persona_id: String(connection.certificate.persona_id || ""), save_id: saveId,
    idempotency_key: `library_claim_${crypto.randomUUID()}`,
  });
}

export async function deletePersonalLibraryItem(
  connection: PilotMobileConnection, saveId: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/library/delete", {
    persona_id: String(connection.certificate.persona_id || ""), save_id: saveId,
    idempotency_key: `library_delete_${crypto.randomUUID()}`,
  });
}

export async function continuePersonalLibraryItem(
  connection: PilotMobileConnection, saveId: string,
  action: "research" | "shortlist" | "task" | "shopping" | "trip" | "playlist" | "learning",
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/library/continue", {
    persona_id: String(connection.certificate.persona_id || ""), save_id: saveId, action,
    idempotency_key: `library_continue_${crypto.randomUUID()}`,
  });
}

export async function readPersonalDeviceMesh(connection: PilotMobileConnection): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/devices/snapshot", {
    purpose: "read_private_device_mesh",
    persona_id: String(connection.certificate.persona_id || ""),
    idempotency_key: `devices_read_${crypto.randomUUID()}`,
  });
}

export async function discoverPersonalDevices(connection: PilotMobileConnection): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/devices/discover", {
    purpose: "scan_local_device_advertisements",
    persona_id: String(connection.certificate.persona_id || ""),
    idempotency_key: `devices_discover_${crypto.randomUUID()}`,
  });
}

export async function controlPersonalTV(
  connection: PilotMobileConnection, command: string, args: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/tv/control", {
    persona_id: String(connection.certificate.persona_id || ""), command, arguments: args,
    idempotency_key: `tv_control_${crypto.randomUUID()}`,
  });
}

export async function changePersonalTVSession(
  connection: PilotMobileConnection, operation: "acquire" | "release",
): Promise<Record<string, unknown>> {
  const personaId = String(connection.certificate.persona_id || "");
  const deviceId = String(connection.certificate.device_id || "");
  const possessionNonce = crypto.randomUUID();
  const possessionPayload = {
    purpose: operation === "acquire" ? "activate_shared_screen" : "release_shared_screen",
    persona_id: personaId, device_id: deviceId, nonce: possessionNonce,
  };
  return postSignedPersonal(connection, "/v1/personal/tv/session", {
    persona_id: personaId, operation, possession_nonce: possessionNonce,
    possession_signature: await signPilotPayload(possessionPayload),
    idempotency_key: `tv_session_${crypto.randomUUID()}`,
  });
}

export async function confirmPersonalTVPresence(
  connection: PilotMobileConnection,
): Promise<Record<string, unknown>> {
  const request = {
    purpose: "confirm_local_phone_presence",
    persona_id: String(connection.certificate.persona_id || ""),
    idempotency_key: `tv_presence_${crypto.randomUUID()}`,
  };
  // Presence deliberately uses only the mother's paired LAN endpoint. A relay or
  // public route can carry commands, but it cannot prove that the phone is home.
  return postJson(connection.endpoint, "/v1/personal/tv/presence", {
    request, certificate: connection.certificate, lease: connection.lease,
    phone_signature: await signPilotPayload(request),
  });
}

export async function controlPersonalTVPresentation(
  connection: PilotMobileConnection,
  args: {
    operation: "present" | "dismiss";
    contentKind?: "document" | "dashboard" | "briefing";
    contentId?: string;
    title?: string;
    authorityDomain?: "personal" | "workspace" | "boardroom";
    membershipId?: string;
  },
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/tv/presentation", {
    persona_id: String(connection.certificate.persona_id || ""),
    operation: args.operation,
    content_kind: args.contentKind || "",
    content_id: args.contentId || "",
    title: args.title || "",
    authority_domain: args.authorityDomain || "personal",
    membership_id: args.membershipId || "",
    idempotency_key: `tv_presentation_${crypto.randomUUID()}`,
  });
}

export async function controlPersonalIotPreset(
  connection: PilotMobileConnection, preset: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/devices/iot-control", {
    persona_id: String(connection.certificate.persona_id || ""), command: "ir_send", preset,
    idempotency_key: `iot_control_${crypto.randomUUID()}`,
  });
}

export async function readPersonalExperiences(
  connection: PilotMobileConnection,
): Promise<Record<string, unknown>> {
  const request = {
    purpose: "read_private_learning_games_entertainment",
    persona_id: String(connection.certificate.persona_id || ""),
    idempotency_key: `experiences_read_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/experiences/snapshot", request);
}

export async function controlPersonalExperience(
  connection: PilotMobileConnection,
  operation:
    | "learning_start" | "learning_answer" | "learning_next" | "learning_repeat"
    | "games_open" | "games_continue"
    | "entertainment_continue_prepare" | "entertainment_continue_confirm" | "entertainment_continue_execute"
    | "entertainment_remember" | "entertainment_watchlist_add",
  args: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  const request = {
    persona_id: String(connection.certificate.persona_id || ""),
    operation,
    arguments: args,
    idempotency_key: `experience_${operation}_${crypto.randomUUID()}`,
  };
  return postSignedPersonal(connection, "/v1/personal/experiences/control", request);
}

export async function readPersonalMemory(
  connection: PilotMobileConnection, targetPersonaId?: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/memory/snapshot", {
    purpose: "inspect_private_memory",
    persona_id: String(connection.certificate.persona_id || ""),
    target_persona_id: targetPersonaId || String(connection.certificate.persona_id || ""),
    idempotency_key: `memory_read_${crypto.randomUUID()}`,
  });
}

export async function createPersonalMemory(
  connection: PilotMobileConnection,
  args: { targetPersonaId?: string; kind: string; summary: string; scope: "private" | "household_shared" },
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/memory/create", {
    persona_id: String(connection.certificate.persona_id || ""),
    target_persona_id: args.targetPersonaId || String(connection.certificate.persona_id || ""),
    kind: args.kind, summary: args.summary, scope: args.scope,
    idempotency_key: `memory_create_${crypto.randomUUID()}`,
  });
}

export async function updatePersonalMemory(
  connection: PilotMobileConnection,
  args: { targetPersonaId?: string; memoryId: string; summary: string; scope: "private" | "household_shared" },
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/memory/update", {
    persona_id: String(connection.certificate.persona_id || ""),
    target_persona_id: args.targetPersonaId || String(connection.certificate.persona_id || ""),
    memory_id: args.memoryId, summary: args.summary, scope: args.scope,
    idempotency_key: `memory_update_${crypto.randomUUID()}`,
  });
}

export async function deletePersonalMemory(
  connection: PilotMobileConnection, args: { targetPersonaId?: string; memoryId: string },
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/memory/delete", {
    persona_id: String(connection.certificate.persona_id || ""),
    target_persona_id: args.targetPersonaId || String(connection.certificate.persona_id || ""),
    memory_id: args.memoryId, confirm_irrecoverable: true,
    idempotency_key: `memory_delete_${crypto.randomUUID()}`,
  });
}

export async function exportPersonalMemory(
  connection: PilotMobileConnection, targetPersonaId?: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/memory/export", {
    persona_id: String(connection.certificate.persona_id || ""),
    target_persona_id: targetPersonaId || String(connection.certificate.persona_id || ""),
    idempotency_key: `memory_export_${crypto.randomUUID()}`,
  });
}

export async function readPersonalGuardian(
  connection: PilotMobileConnection, targetPersonaId?: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/guardian/snapshot", {
    purpose: "read_private_guardian",
    persona_id: String(connection.certificate.persona_id || ""),
    target_persona_id: targetPersonaId || String(connection.certificate.persona_id || ""),
    idempotency_key: `guardian_read_${crypto.randomUUID()}`,
  });
}

export async function configurePersonalGuardian(
  connection: PilotMobileConnection,
  args: { targetPersonaId?: string; contactId: string; channel: string; shareLocation: boolean; locationPermissionReceipt?: string },
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/guardian/configure", {
    persona_id: String(connection.certificate.persona_id || ""),
    target_persona_id: args.targetPersonaId || String(connection.certificate.persona_id || ""),
    contact_id: args.contactId, channel: args.channel, share_location: args.shareLocation,
    location_permission_receipt: args.locationPermissionReceipt || "", allow_interruption: true,
    idempotency_key: `guardian_configure_${crypto.randomUUID()}`,
  });
}

export async function controlPersonalGuardian(
  connection: PilotMobileConnection,
  args: { targetPersonaId?: string; operation: "request" | "confirm" | "cancel"; incidentId?: string; trigger?: string; location?: Record<string, unknown> },
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/guardian/action", {
    persona_id: String(connection.certificate.persona_id || ""),
    target_persona_id: args.targetPersonaId || String(connection.certificate.persona_id || ""),
    operation: args.operation, incident_id: args.incidentId || "", trigger: args.trigger || "",
    location: args.location || {}, idempotency_key: `guardian_${args.operation}_${crypto.randomUUID()}`,
  });
}

export async function readPersonalIntelligence(connection: PilotMobileConnection): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/intelligence/snapshot", {
    purpose: "read_private_intelligence_route",
    persona_id: String(connection.certificate.persona_id || ""),
    idempotency_key: `intelligence_read_${crypto.randomUUID()}`,
  });
}

export async function askPersonalIntelligence(
  connection: PilotMobileConnection, query: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/intelligence/ask", {
    persona_id: String(connection.certificate.persona_id || ""), query,
    idempotency_key: `intelligence_ask_${crypto.randomUUID()}`,
  });
}

export async function configurePersonalIntelligence(
  connection: PilotMobileConnection, mode: "native" | "gemini" | "boost", geminiGroundingEnabled = false,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/personal/intelligence/configure", {
    persona_id: String(connection.certificate.persona_id || ""), mode,
    gemini_grounding_enabled: geminiGroundingEnabled,
    idempotency_key: `intelligence_configure_${crypto.randomUUID()}`,
  });
}

export async function readWorkspaceInvitations(connection: PilotMobileConnection): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/invitations/snapshot", {
    persona_id: String(connection.certificate.persona_id || ""),
    purpose: "review_workspace_invitations",
    idempotency_key: `workspace_invitation_read_${crypto.randomUUID()}`,
  });
}

export async function respondWorkspaceInvitation(
  connection: PilotMobileConnection, invitationId: string, decision: "accepted" | "declined",
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/invitations/respond", {
    persona_id: String(connection.certificate.persona_id || ""), invitation_id: invitationId,
    decision, idempotency_key: `workspace_invitation_${decision}_${crypto.randomUUID()}`,
  });
}

export async function readWorkspaceSurface(
  connection: PilotMobileConnection, membershipId: string,
  surface: "overview" | "briefings" | "departments" | "dashboards" | "files",
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/surfaces/read", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    surface, idempotency_key: `workspace_${surface}_${crypto.randomUUID()}`,
  });
}

export async function createWorkspaceFileReference(
  connection: PilotMobileConnection, sourceMembershipId: string, targetMembershipId: string, fileId: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/files/reference", {
    persona_id: String(connection.certificate.persona_id || ""), source_membership_id: sourceMembershipId,
    target_membership_id: targetMembershipId, file_id: fileId,
    idempotency_key: `workspace_file_reference_${crypto.randomUUID()}`,
  });
}

export async function readWorkspaceFileReferences(
  connection: PilotMobileConnection, membershipId: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/files/references", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    idempotency_key: `workspace_file_references_${crypto.randomUUID()}`,
  });
}

export async function prepareWorkspaceDesktopHandoff(
  connection: PilotMobileConnection, membershipId: string, purpose: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/handoffs/desktop", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId, purpose,
    idempotency_key: `workspace_desktop_handoff_${crypto.randomUUID()}`,
  });
}

export async function readWorkspaceCommercialDashboard(
  connection: PilotMobileConnection, membershipId: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/commercial/snapshot", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    purpose: "read_content_free_commercial_dashboard",
    idempotency_key: `workspace_commercial_read_${crypto.randomUUID()}`,
  });
}

export async function controlWorkspaceCommercialService(
  connection: PilotMobileConnection, membershipId: string,
  action: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/commercial/action", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    ...action, idempotency_key: `workspace_commercial_action_${crypto.randomUUID()}`,
  });
}

export async function sendWorkspaceConversationTurn(
  connection: PilotMobileConnection, membershipId: string, departmentId: string, userText: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/conversations/turn", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    department_id: departmentId, user_text: userText,
    idempotency_key: `workspace_conversation_${crypto.randomUUID()}`,
  });
}

export async function readWorkspaceReviewCards(
  connection: PilotMobileConnection, membershipId: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/cards/snapshot", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    idempotency_key: `workspace_cards_${crypto.randomUUID()}`,
  });
}

export async function actOnWorkspaceReviewCard(
  connection: PilotMobileConnection, membershipId: string, cardId: string,
  operation: "review" | "correct" | "delegate" | "approve", expectedScopeHash: string,
  details: { correction?: string; recipient_ref?: string } = {},
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/cards/action", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    card_id: cardId, operation, expected_scope_hash: expectedScopeHash, ...details,
    idempotency_key: `workspace_card_${operation}_${crypto.randomUUID()}`,
  });
}

export async function prepareWorkspaceSignoff(
  connection: PilotMobileConnection, membershipId: string, cardId: string, expectedScopeHash: string,
  signatoryRole: "accountant" | "auditor" | "adviser" | "director", statement: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/signoffs/prepare", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    card_id: cardId, expected_scope_hash: expectedScopeHash, signatory_role: signatoryRole, statement,
    idempotency_key: `workspace_signoff_prepare_${crypto.randomUUID()}`,
  });
}

export async function readWorkspaceSignoffs(connection: PilotMobileConnection, membershipId: string): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/signoffs/snapshot", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    idempotency_key: `workspace_signoff_read_${crypto.randomUUID()}`,
  });
}

export async function decideWorkspaceSignoff(
  connection: PilotMobileConnection, membershipId: string, packageId: string, expectedPackageHash: string,
  decision: "signed" | "rejected", professionalReference: string,
): Promise<Record<string, unknown>> {
  return postSignedPersonal(connection, "/v1/workspaces/signoffs/decide", {
    persona_id: String(connection.certificate.persona_id || ""), membership_id: membershipId,
    package_id: packageId, expected_package_hash: expectedPackageHash, decision,
    professional_reference: professionalReference,
    idempotency_key: `workspace_signoff_${decision}_${crypto.randomUUID()}`,
  });
}

export function watchPilotInbox(
  connection: PilotMobileConnection,
  callbacks: {
    onStream: (stream: Record<string, unknown>) => void;
    onState: (state: "connecting" | "live" | "reconnecting" | "offline" | "closed") => void;
    onRoute?: (route: "lan" | "direct" | "relay") => void;
    initialRevision?: number;
  },
): () => void {
  let stopped = false;
  let socket: WebSocket | null = null;
  let socketRetry = 750;
  let pollRetry = 1_000;
  let afterRevision = Math.max(0, Number(callbacks.initialRevision || 0));
  let socketTimer: number | undefined;
  let pollTimer: number | undefined;
  let heartbeatTimer: number | undefined;
  let pollInFlight = false;
  let activePoll: AbortController | undefined;
  let socketGeneration = 0;
  let streamDelivered = callbacks.initialRevision !== undefined;
  const cursorId = `pilot-inbox-cursor:${String(connection.certificate.mother_id || "")}:${String(connection.certificate.device_id || "")}`;

  const persistCursor = async () => {
    await writeRecord({
      id: cursorId,
      motherId: String(connection.certificate.mother_id || ""),
      deviceId: String(connection.certificate.device_id || ""),
      revision: afterRevision,
      updatedAt: new Date().toISOString(),
    });
  };

  const acceptStream = (stream: Record<string, unknown>) => {
    const revision = Math.max(0, Number(stream.revision || 0));
    if (revision < afterRevision || (revision === afterRevision && streamDelivered)) return;
    afterRevision = revision;
    streamDelivered = true;
    callbacks.onStream(stream);
    void persistCursor();
  };

  const jitter = (milliseconds: number) => Math.round(milliseconds * (0.85 + Math.random() * 0.3));

  const scheduleSocket = (delay: number) => {
    if (stopped || !connection.liveInboxUrl || !navigator.onLine || socketTimer) return;
    socketTimer = window.setTimeout(() => {
      socketTimer = undefined;
      void connectSocket();
    }, jitter(delay));
  };

  const schedulePoll = (delay: number) => {
    if (stopped || !navigator.onLine || pollTimer || pollInFlight) return;
    pollTimer = window.setTimeout(() => {
      pollTimer = undefined;
      void pollOnce();
    }, jitter(delay));
  };

  const pollOnce = async () => {
    if (stopped || pollInFlight) return;
    if (!navigator.onLine) {
      callbacks.onState("offline");
      return;
    }
    pollInFlight = true;
    const controller = new AbortController();
    activePoll = controller;
    let nextPoll = pollRetry;
    let reschedule = true;
    callbacks.onState("reconnecting");
    try {
      const stream = await readPilotInbox(connection, callbacks.onRoute, controller.signal);
      acceptStream(stream);
      callbacks.onState("live");
      pollRetry = 1_000;
      nextPoll = 2_500;
    } catch {
      if (controller.signal.aborted) {
        reschedule = false;
        return;
      }
      callbacks.onState("reconnecting");
      pollRetry = Math.min(pollRetry * 2, 30_000);
      nextPoll = pollRetry;
    } finally {
      if (activePoll === controller) activePoll = undefined;
      pollInFlight = false;
    }
    if (reschedule) schedulePoll(nextPoll);
  };

  const connectSocket = async () => {
    if (stopped || !connection.liveInboxUrl || socket || !navigator.onLine) return;
    callbacks.onState(socketRetry === 750 ? "connecting" : "reconnecting");
    const generation = ++socketGeneration;
    socket = new WebSocket(connection.liveInboxUrl);
    const openDeadline = window.setTimeout(() => {
      if (generation === socketGeneration && socket?.readyState !== WebSocket.OPEN) socket?.close();
    }, 8_000);
    socket.onopen = async () => {
      clearTimeout(openDeadline);
      if (generation !== socketGeneration || stopped) return socket?.close();
      try {
        const request = {
          purpose: "open_inbox_stream",
          persona_id: String(connection.certificate.persona_id || ""),
          device_id: String(connection.certificate.device_id || ""),
          lease_id: String(connection.lease.lease_id || ""),
          nonce: crypto.randomUUID(),
          after_revision: afterRevision,
        };
        socket?.send(JSON.stringify({
          request,
          certificate: connection.certificate,
          lease: connection.lease,
          phone_signature: await signPilotPayload(request),
        }));
      } catch {
        socket?.close();
      }
    };
    socket.onmessage = (event) => {
      if (generation !== socketGeneration || stopped) return;
      try {
        const payload = JSON.parse(String(event.data)) as Record<string, unknown>;
        if (payload.type === "inbox.ready") {
          callbacks.onState("live");
          callbacks.onRoute?.("lan");
          if (pollTimer) clearTimeout(pollTimer);
          pollTimer = undefined;
          activePoll?.abort();
        }
        if (payload.type === "inbox.snapshot" && payload.stream && typeof payload.stream === "object") {
          const stream = payload.stream as Record<string, unknown>;
          acceptStream(stream);
          callbacks.onState("live");
          callbacks.onRoute?.("lan");
          socketRetry = 750;
          pollRetry = 1_000;
          if (pollTimer) clearTimeout(pollTimer);
          pollTimer = undefined;
        }
      } catch {
        // A malformed live frame is ignored; the signed polling boundary remains available.
      }
    };
    socket.onclose = () => {
      clearTimeout(openDeadline);
      if (generation !== socketGeneration) return;
      socket = null;
      if (stopped) return callbacks.onState("closed");
      if (!navigator.onLine) return callbacks.onState("offline");
      callbacks.onState("reconnecting");
      schedulePoll(0);
      scheduleSocket(socketRetry);
      socketRetry = Math.min(socketRetry * 2, 30_000);
    };
  };

  const networkChanged = () => {
    if (stopped) return;
    socketGeneration += 1;
    if (socketTimer) clearTimeout(socketTimer);
    if (pollTimer) clearTimeout(pollTimer);
    socketTimer = undefined;
    pollTimer = undefined;
    activePoll?.abort();
    activePoll = undefined;
    socket?.close();
    socket = null;
    if (!navigator.onLine) {
      callbacks.onState("offline");
      return;
    }
    socketRetry = 750;
    pollRetry = 1_000;
    callbacks.onState("reconnecting");
    schedulePoll(0);
    scheduleSocket(150);
  };

  const becameVisible = () => {
    if (document.visibilityState === "visible") networkChanged();
  };

  window.addEventListener("online", networkChanged);
  window.addEventListener("offline", networkChanged);
  document.addEventListener("visibilitychange", becameVisible);
  heartbeatTimer = window.setInterval(() => {
    if (socket?.readyState === WebSocket.OPEN) socket.send("ping");
  }, 15_000);

  void readRecord<StoredInboxCursor>(cursorId).then((saved) => {
    if (saved && saved.motherId === connection.certificate.mother_id && saved.deviceId === connection.certificate.device_id) {
      afterRevision = Math.max(afterRevision, Number(saved.revision || 0));
    }
    if (!navigator.onLine) return callbacks.onState("offline");
    if (connection.liveInboxUrl) void connectSocket();
    else void pollOnce();
  });
  return () => {
    stopped = true;
    socketGeneration += 1;
    if (socketTimer) clearTimeout(socketTimer);
    if (pollTimer) clearTimeout(pollTimer);
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    activePoll?.abort();
    window.removeEventListener("online", networkChanged);
    window.removeEventListener("offline", networkChanged);
    document.removeEventListener("visibilitychange", becameVisible);
    socket?.close();
    callbacks.onState("closed");
  };
}
