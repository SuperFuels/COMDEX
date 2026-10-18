export type AgentIdentity = {
  agentId: string;  // short fingerprint
  wa: string;       // e.g. ucs://self/<fp>
  pubkey_b64: string;
};

let processIdentity: AgentIdentity | null = null;
let processPrivateKey: CryptoKey | null = null;

export async function getIdentity(): Promise<AgentIdentity> {
  if (processIdentity) return processIdentity;

  const kp = await window.crypto.subtle.generateKey(
    { name: "Ed25519", namedCurve: "Ed25519" } as any,
    true,
    ["sign", "verify"]
  );
  const pub = new Uint8Array(await crypto.subtle.exportKey("raw", kp.publicKey));
  const priv = new Uint8Array(await crypto.subtle.exportKey("pkcs8", kp.privateKey));
  processPrivateKey = await crypto.subtle.importKey(
    "pkcs8",
    priv,
    { name: "Ed25519" },
    false,
    ["sign"],
  );
  priv.fill(0);

  const fpBuf = await crypto.subtle.digest("SHA-256", pub);
  const fp = Array.from(new Uint8Array(fpBuf))
    .slice(0, 16)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  const wa = `ucs://self/${fp}`;

  const id: AgentIdentity = {
    agentId: fp,
    wa,
    pubkey_b64: btoa(String.fromCharCode(...pub)),
  };

  processIdentity = id;
  return id;
}

export async function signIdentityPayload(payload: string | Uint8Array): Promise<string> {
  await getIdentity();
  if (!processPrivateKey) throw new Error("Identity key is unavailable");
  const bytes = typeof payload === "string" ? new TextEncoder().encode(payload) : payload;
  const data = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer;
  const signature = new Uint8Array(
    await crypto.subtle.sign("Ed25519", processPrivateKey, data),
  );
  return btoa(String.fromCharCode(...signature));
}
