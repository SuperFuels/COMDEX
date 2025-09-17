// frontend/hooks/useCodexCoreProjection.ts
import { useState } from "react";
import useWebSocket from "./useWebSocket";

type GHXProjectionPayload = {
  light_field?: any[];
  rendered_at?: string;
  projection_id?: string;
  // …allow anything else from backend without being strict
  [k: string]: any;
};

type Incoming =
  | { event?: string; type?: string; payload?: any; data?: any }
  | string
  | null
  | undefined;

function parseIncoming(raw: Incoming) {
  if (raw == null) return null;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw);
    } catch {
      // non-JSON text — wrap so we don't crash
      return { payload: raw };
    }
  }
  return raw;
}

/**
 * Subscribe to the Codex Core GHX stream for a container and keep the latest
 * projection in state.
 */
export function useCodexCoreProjection(containerId: string) {
  const [projection, setProjection] = useState<GHXProjectionPayload | null>(null);

  // Your useWebSocket expects at least (url, onMessage)
  useWebSocket(`/ws/ghx_core/${containerId}`, (message: Incoming) => {
    const msg = parseIncoming(message);
    const isProjection =
      msg?.event === "ghx_projection" || msg?.type === "ghx_projection";

    if (isProjection) {
      // prefer "payload", fall back to "data"
      const next = (msg as any).payload ?? (msg as any).data ?? null;
      setProjection(next);
    }
  });

  return projection;
}