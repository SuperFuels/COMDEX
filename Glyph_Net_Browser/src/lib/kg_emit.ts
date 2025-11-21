// src/lib/kg_emit.ts
// TS wrapper around the UMD global loaded from /public/js/kg_emit.js

type KgEmit = {
  emitTextToKG: (args: any) => Promise<any>;
  emitTranscriptPosted?: (args: any) => Promise<any>;
  emitVoiceToKG: (args: any) => Promise<any>;
  emitPttSession: (args: any) => Promise<any>;
  emitFloorLock?: (args: any) => Promise<any>;
  emitCallState?: (args: any) => Promise<any>;
  emitFileEvent?: (args: any) => Promise<any>;
};

// Options for the transcript emitter (typed)
export type TranscriptPostedOpts = {
  apiBase?: string;                 // optional; will fall back to window.KG_API_BASE
  kg: "personal" | "work";
  ownerWa: string;
  topicWa: string;
  text: string;
  transcript_of?: string | null;
  engine?: string;
  ts: number;                       // epoch ms
  agentId: string;
};

// Soft getter (does NOT throw) so we can fall back to direct fetch
function maybeGetAPI(): KgEmit | null {
  const g = typeof window !== "undefined" ? (window as any).KGEmit : null;
  return (g || null) as KgEmit | null;
}

// Hard getter (throws) used by the other wrappers that require UMD to be present
function getAPI(): KgEmit {
  const g = typeof window !== "undefined" ? (window as any).KGEmit : null;
  if (!g) {
    throw new Error(
      'KGEmit UMD script not loaded. Ensure <script src="/js/kg_emit.js"></script> is in index.html.'
    );
  }
  return g as KgEmit;
}

export function emitTextToKG(args: any) {
  return getAPI().emitTextToKG(args);
}

/**
 * Emitter: Transcript posted → Message(kind=text, transcript_of=msg_id)
 * Uses UMD KGEmit.emitTranscriptPosted if available; otherwise falls back to POST /api/kg/events.
 */
export async function emitTranscriptPosted(opts: TranscriptPostedOpts) {
  const api = maybeGetAPI();
  if (api?.emitTranscriptPosted) {
    // Prefer UMD if provided by the page
    return api.emitTranscriptPosted(opts);
  }

  // Fallback: direct HTTP to KG writer
  const apiBase =
    opts.apiBase ??
    (typeof window !== "undefined" ? (window as any).KG_API_BASE : "") ??
    "";

  const body = {
    kg: opts.kg,
    events: [
      {
        entity: "Message",
        kind: "text",
        text: opts.text,
        transcript_of: opts.transcript_of ?? null,
        engine: opts.engine || undefined,
        ts: opts.ts,
        topic_wa: opts.topicWa,
        agent_id: opts.agentId,
      },
    ],
  };

  const res = await fetch(`${apiBase}/api/kg/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`emitTranscriptPosted failed: HTTP ${res.status} ${msg}`);
  }

  // return whatever the KG writer returned (or empty object)
  try {
    return await res.json();
  } catch {
    return {};
  }
}

export function emitVoiceToKG(args: any) {
  return getAPI().emitVoiceToKG(args);
}

export function emitPttSession(args: any) {
  return getAPI().emitPttSession(args);
}

export function emitFloorLock(args: any) {
  const api = getAPI();
  if (!api.emitFloorLock) {
    return Promise.reject(new Error("emitFloorLock not available in KGEmit"));
  }
  return api.emitFloorLock(args);
}

export function emitCallState(args: any) {
  const api = getAPI();
  if (!api.emitCallState) {
    return Promise.reject(new Error("emitCallState not available in KGEmit"));
  }
  return api.emitCallState(args);
}

export function emitFileEvent(args: any) {
  const api = getAPI();
  if (!api.emitFileEvent) {
    return Promise.reject(new Error("emitFileEvent not available in KGEmit"));
  }
  return api.emitFileEvent(args);
}