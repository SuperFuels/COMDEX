// lib/resolve.ts
export type ResolveOut = {
  did: string;
  inbox_topic: string;  // e.g. ucs://aion.tp/nova/inbox
  wa?: string;          // handle@realm
  wn?: string;          // wn:8R2J-7QF4-...
  pubkeys: { signing: string; prekey?: string };
  meta?: Record<string, any>;
};

export async function resolveAddress(addr: string): Promise<ResolveOut> {
  // 1) raw UCS topic passthrough
  if (addr.startsWith("ucs://")) {
    return { did: "did:gnet:volatile", inbox_topic: addr, pubkeys: { signing: "" } };
  }
  // 2) WA: handle@realm
  const m = addr.match(/^([^@]+)@([a-z0-9.-]+)$/i);
  if (m) {
    const [, handle, realm] = m;
    // Try DNS-backed first: https://<realm>/.well-known/gnet.json
    // Fallback to your backend registry:
    const r = await fetch(`/api/registry/resolve?addr=${encodeURIComponent(addr)}`);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return await r.json();
  }
  // 3) Wave Number / DID (backend knows how to resolve)
  if (addr.startsWith("wn:") || addr.startsWith("did:gnet:")) {
    const r = await fetch(`/api/registry/resolve?addr=${encodeURIComponent(addr)}`);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return await r.json();
  }
  throw new Error("Unsupported address format");
}