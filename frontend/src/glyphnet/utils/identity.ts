export type AgentIdentity = {
  agentId: string;  // short fingerprint
  wa: string;       // e.g. ucs://self/<fp>
  pubkey_b64: string;
  privkey_b64: string; // for now; later move from localStorage
};

const KEY_DB = "gnet:identity:v1";

export async function getIdentity(): Promise<AgentIdentity> {
  const cached = localStorage.getItem(KEY_DB);
  if (cached) return JSON.parse(cached);

  const kp = await window.crypto.subtle.generateKey(
    { name: "Ed25519", namedCurve: "Ed25519" } as any,
    true,
    ["sign", "verify"]
  );
  const pub = new Uint8Array(await crypto.subtle.exportKey("raw", kp.publicKey));
  const priv = new Uint8Array(await crypto.subtle.exportKey("pkcs8", kp.privateKey));

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
    privkey_b64: btoa(String.fromCharCode(...priv)),
  };

  localStorage.setItem(KEY_DB, JSON.stringify(id));
  return id;
}