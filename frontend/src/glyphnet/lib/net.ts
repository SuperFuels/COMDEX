// frontend/src/lib/net.ts
import { protectCapsule } from "./qkd_wrap";

/** Normalise a path to start with a single leading slash. */
function normPath(p: string) {
  return p.startsWith("/") ? p : `/${p}`;
}

/**
 * Central base for the radio runtime.
 * - If VITE_RADIO_BASE is set → use it (absolute).
 * - If unset → return "" so callers produce *relative* URLs (Vite proxy).
 */
export function getRadioBase(): string {
  const raw = (import.meta as any)?.env?.VITE_RADIO_BASE ?? "";
  const trimmed = String(raw).trim();
  if (!trimmed) return ""; // proxy/relative mode
  return trimmed.replace(/\/+$/, "");
}

/** Build an HTTP URL targeting the radio runtime (absolute or relative). */
export function httpUrl(path: string) {
  const base = getRadioBase();
  return base ? `${base}${normPath(path)}` : normPath(path);
}

/** Resolve the correct WS base (absolute when VITE_RADIO_BASE, otherwise current origin). */
function resolveWsBase(): string {
  const base = getRadioBase();
  if (base) {
    return base.startsWith("https")
      ? base.replace(/^https/i, "wss")
      : base.replace(/^http/i, "ws");
  }
  // Derive from the current page origin for proxy/relative mode
  const origin = window.location.origin;
  return origin.startsWith("https")
    ? origin.replace(/^https/i, "wss")
    : origin.replace(/^http/i, "ws");
}

/** Build a WS/WSS URL targeting the radio runtime (absolute in Option B; absolute-from-origin in Option A). */
export function wsUrl(path: string) {
  const wsBase = resolveWsBase();
  return `${wsBase}${normPath(path)}`;
}

/** Back-compat helper used by chat/transport layers. */
export function glyphnetWsUrl(recipient: string, token = "dev-token"): string {
  const qs = new URLSearchParams({
    token,
    topic: recipient, // ucs://...; URLSearchParams will encode
  });
  return wsUrl(`/ws/glyphnet?${qs.toString()}`);
}

/**
 * Send a GlyphNet capsule via the radio runtime.
 * If VITE_QKD_E2EE === "1", the capsule is wrapped using the QKD layer.
 */
export async function sendGlyphnetTx(opts: {
  recipient: string;           // ucs://... address
  graph?: string;              // e.g. "personal"
  capsule: any;                // capsule object
  meta?: Record<string, any>;  // extra metadata (optional)
}): Promise<Response> {
  const { recipient, capsule, meta = {}, graph = "personal" } = opts;

  let capsuleToSend = capsule;
  const metaToSend: Record<string, any> = { ...meta };

  const E2EE_ENABLED = (import.meta as any)?.env?.VITE_QKD_E2EE === "1";

  if (E2EE_ENABLED) {
    const localWA = meta?.localWA || "ucs://local/self";
    const remoteWA = recipient;

    const { capsule: protectedCapsule } = await protectCapsule({
      capsule,
      localWA,
      remoteWA,
      kg: graph || "personal",
    });

    capsuleToSend = protectedCapsule;
    metaToSend.qkd_required = true;
  }

  return fetch(httpUrl("/api/glyphnet/tx"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      recipient,
      graph,
      capsule: capsuleToSend,
      meta: metaToSend,
    }),
  });
}