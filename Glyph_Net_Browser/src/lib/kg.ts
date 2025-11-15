// src/lib/kg.ts
export async function emitKG(base: string, args: {
  kg: "personal"|"work",
  owner: string,         // owner WA
  events: Array<{
    id?: string;
    thread_id?: string;
    topic_wa?: string;
    type: string;        // "message"|"visit"|"file"|"call"|"ptt_session"|"floor_lock"
    kind?: string;       // e.g. "text"|"voice"|"offer"|"answer"...
    ts?: number;
    size?: number;
    sha256?: string|null;
    payload?: any;
  }>;
}) {
  const r = await fetch(`${base}/api/kg/events`, {
    method: "POST",
    headers: { "Content-Type":"application/json" },
    body: JSON.stringify(args),
  });
  if (!r.ok) throw new Error(`emitKG ${r.status}`);
  return r.json();
}