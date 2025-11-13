// frontend/src/lib/net.ts
import { protectCapsule } from "./qkd_wrap";

/**
 * Resolve the backend host for different environments:
 * - GitHub Codespaces:  ...-5173.app.github.dev  ->  ...-8080.app.github.dev
 * - Local Vite dev:     localhost:5173           ->  localhost:8080
 *                       127.0.0.1:5173           ->  127.0.0.1:8080
 * - Prod/other:         keep host as-is
 */
function resolveBackendHost(): string {
  const { host, hostname } = window.location;

  // Codespaces pattern: "-5173.app.github.dev" → "-8080.app.github.dev"
  if (host.endsWith(".app.github.dev")) {
    return host.replace("-5173", "-8080");
  }

  // Local vite dev ports → backend on 8080
  if (host.endsWith(":5173")) {
    return `${hostname}:8080`;
  }

  // Default: same host
  return host;
}

export function backendBase(): string {
  const proto = window.location.protocol; // "http:" | "https:"
  return `${proto}//${resolveBackendHost()}`;
}

export function glyphnetWsUrl(recipient: string, token = "dev-token"): string {
  const isHttps = window.location.protocol === "https:";
  const scheme = isHttps ? "wss" : "ws";
  const host = resolveBackendHost();

  const qs = new URLSearchParams({
    token,
    topic: recipient, // raw ucs://... value; URLSearchParams will encode
  });

  return `${scheme}://${host}/ws/glyphnet?${qs.toString()}`;
}

/**
 * Send a GlyphNet capsule to the backend. If VITE_QKD_E2EE=1, the capsule will be
 * encrypted via the QKD wrapper before POSTing.
 */
export async function sendGlyphnetTx(opts: {
  recipient: string;           // ucs://... address
  graph?: string;              // e.g., "personal"
  capsule: any;                // capsule object
  meta?: Record<string, any>;  // extra metadata (optional)
}): Promise<Response> {
  const { recipient, capsule, meta = {}, graph = "personal" } = opts;

  let capsuleToSend = capsule;
  let metaToSend: Record<string, any> = { ...meta };

  // Feature flag from Vite env
  const E2EE_ENABLED = (import.meta as any)?.env?.VITE_QKD_E2EE === "1";

  if (E2EE_ENABLED) {
    // Replace localWA with your actual identity if you have it in state
    const localWA = meta?.localWA || "ucs://local/self";
    const remoteWA = recipient; // if recipient is ucs://..., this is fine

    const { capsule: protectedCapsule } = await protectCapsule({
      capsule,
      localWA,
      remoteWA,
      kg: graph || "personal",
    });

    capsuleToSend = protectedCapsule;
    metaToSend.qkd_required = true; // mark for routing/telemetry
  }

  return fetch(`${backendBase()}/api/glyphnet/tx`, {
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