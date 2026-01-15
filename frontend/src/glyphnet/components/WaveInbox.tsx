import { useEffect, useMemo, useRef, useState } from "react";
import useGlyphnet from "@glyphnet/hooks/useGlyphnet";
import { VoiceJitterBuffer } from "@glyphnet/lib/audio/jitter";
import { getRecent } from "@glyphnet/lib/addressBook";

type InboxItem = {
  id?: string;
  ts?: number;
  glyphs: string[];
  stream: string[];
  to: string;
  voice?: { channel: string; seq: number; mime: string; size: number; data_b64?: string };
};

type JitterEntry = { buf: VoiceJitterBuffer };

type VoiceChunk = { seq: number; mime: string; bytes: Uint8Array };
type VoiceTrack = { channel: string; mime: string; chunks: VoiceChunk[]; updated: number };

const MAX_ITEMS = 200;
const STORAGE_PREFIX = "gnet:inbox:";

// SSR-safe location (for invite URL + hash deep-link)
function getLoc() {
  if (typeof window === "undefined") {
    return { host: "", hostname: "", protocol: "http:", origin: "", hash: "" } as unknown as Location;
  }
  return window.location;
}

// Base64 (including URL-safe) → bytes with padding fix
function b64ToBytesSafe(b64: string): Uint8Array {
  if (!b64) return new Uint8Array(0);
  b64 = b64.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4;
  if (pad) b64 += "===".slice(pad);
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export default function WaveInbox({ defaultTopic }: { defaultTopic?: string }) {
  const loc = getLoc();

  // topic state + deep-link hydration
  const [topic, setTopic] = useState(defaultTopic || "ucs://local/ucs_hub");
  useEffect(() => {
    if (defaultTopic) return;
    const hash = loc.hash || "";
    const qs = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
    if (qs) {
      const sp = new URLSearchParams(qs);
      const t = sp.get("topic");
      if (t) setTopic(t);
    }
  }, [defaultTopic]);
  useEffect(() => {
    if (defaultTopic) setTopic(defaultTopic);
  }, [defaultTopic]);

  // Wire up to GlyphNet
  const { connected, messages } = useGlyphnet(topic);

  // Items feed (+ restore from storage on topic change)
  const [items, setItems] = useState<InboxItem[]>([]);
  const storageKey = useMemo(() => `${STORAGE_PREFIX}${topic}`, [topic]);

  // Audio controls
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [volume, setVolume] = useState(0.9);

  // Per-channel jitter buffers + dedupe + manual tracks
  const buffersRef = useRef<Map<string, JitterEntry>>(new Map());
  const seenRef = useRef<Set<string>>(new Set());
  const tracksRef = useRef<Map<string, VoiceTrack>>(new Map());
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Recent topics
  const recent = useMemo(() => getRecent(8), []);

  // Invite link
  const copyInvite = async () => {
    const url = `${loc.origin}/#/inbox?topic=${encodeURIComponent(topic)}`;
    try {
      await navigator.clipboard.writeText(url);
      alert("Invite link copied:\n" + url);
    } catch {
      // eslint-disable-next-line no-alert
      prompt("Copy this link:", url);
    }
  };

  // Restore cache on topic change
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (raw) {
        const cached: InboxItem[] = JSON.parse(raw);
        setItems(cached);
        // hydrate dedupe
        seenRef.current.clear();
        for (const it of cached) {
          if (it.id) seenRef.current.add(it.id);
          if (it.voice) seenRef.current.add(`${it.voice.channel}:${it.voice.seq}`);
        }
      } else {
        setItems([]);
        seenRef.current.clear();
      }
    } catch {
      setItems([]);
      seenRef.current.clear();
    }
    // reset buffers/tracks when switching topics
    buffersRef.current.clear();
    tracksRef.current.clear();
  }, [storageKey]);

  // Feed transformer: WS messages → items[] + jitter playback + track assembly
  useEffect(() => {
    if (!messages.length) return;

    const nextItems: InboxItem[] = [];

    for (const m of messages) {
      // accept both shapes: { type, envelope } and { envelope } or { id, capsule, ... }
      const env: any = (m as any)?.envelope ?? m;
      if (!env) continue;

      const cap = env.capsule ?? {};
      const vf = cap.voice_frame as
        | { channel: string; seq: number; ts?: number; mime?: string; data_b64?: string }
        | undefined;

      // de-dupe
      const key = env?.id || (vf ? `${vf.channel}:${vf.seq}` : "");
      if (key && seenRef.current.has(key)) continue;
      if (key) seenRef.current.add(key);

      // build base row
      const toStrArray = (x: any) => (Array.isArray(x) ? x.map(String) : []);
      const baseItem: InboxItem = {
        id: env.id,
        ts: env.ts ?? Date.now(),
        glyphs: toStrArray(cap.glyphs),
        stream: toStrArray(cap.glyph_stream),
        to: env.recipient || env.topic || topic,
      };

      if (vf?.data_b64) {
        const bytes = b64ToBytesSafe(vf.data_b64);
        const mime = vf.mime || "audio/webm;codecs=opus";

        nextItems.push({
          ...baseItem,
          voice: { channel: vf.channel, seq: vf.seq ?? 0, mime, size: bytes.length, data_b64: vf.data_b64 },
        });

        // Assemble manual track per channel for Play/Download
        let track = tracksRef.current.get(vf.channel);
        if (!track) {
          track = { channel: vf.channel, mime, chunks: [], updated: Date.now() };
          tracksRef.current.set(vf.channel, track);
        }
        track.mime = mime; // last wins
        track.chunks.push({ seq: vf.seq ?? 0, mime, bytes });
        // keep ordered (guard out-of-order delivery)
        track.chunks.sort((a, b) => a.seq - b.seq);
        track.updated = Date.now();

        // Optional streaming path (jitter buffer)
        if (audioEnabled) {
          let entry = buffersRef.current.get(vf.channel);
          if (!entry) {
            entry = { buf: new VoiceJitterBuffer() };
            buffersRef.current.set(vf.channel, entry);
          }
          try {
            entry.buf.setVolume?.(volume);
            entry.buf.push(vf.seq, mime, vf.data_b64); // sequence-aware push
          } catch {
            // swallow transient decode errors
          }
        }
      } else {
        // textual capsule (avoid spamming empty rows)
        if ((baseItem.glyphs && baseItem.glyphs.length) || (baseItem.stream && baseItem.stream.length)) {
          nextItems.push(baseItem);
        }
      }

      // lightweight badge/event
      if (baseItem.id) {
        window.dispatchEvent(
          new CustomEvent("glyphnet:wave", {
            detail: { topic: baseItem.to, id: baseItem.id },
          })
        );
      }
    }

    if (nextItems.length) {
      setItems((prev) => {
        const merged = [...nextItems, ...prev].slice(0, MAX_ITEMS);
        try {
          sessionStorage.setItem(storageKey, JSON.stringify(merged));
        } catch {}
        return merged;
      });
    }
  }, [messages, audioEnabled, volume, topic, storageKey]);

  // Nudge buffers when audio enabled / volume changes
  useEffect(() => {
    if (!audioEnabled) return;
    for (const [, entry] of buffersRef.current) {
      entry.buf.setVolume?.(volume);
    }
  }, [audioEnabled, volume]);

  function toArrayBuffer(view: Uint8Array): ArrayBuffer {
    const { buffer, byteOffset, byteLength } = view;

    if (buffer instanceof ArrayBuffer) {
      return buffer.slice(byteOffset, byteOffset + byteLength);
    }
    // SharedArrayBuffer path: copy into a fresh ArrayBuffer
    const out = new ArrayBuffer(byteLength);
    new Uint8Array(out).set(new Uint8Array(buffer as SharedArrayBuffer, byteOffset, byteLength));
    return out;
  }

  function buildBlob(track: VoiceTrack): Blob | null {
    if (!track.chunks.length) return null;
    const useful = track.chunks.filter(c => c.bytes && c.bytes.length > 200);
    const chosen = useful.length ? useful : track.chunks;
    const total = chosen.reduce((n, c) => n + c.bytes.length, 0);
    if (total < 200) return null;

    const parts: BlobPart[] = chosen.map(c => toArrayBuffer(c.bytes));
    return new Blob(parts, { type: track.mime || "audio/webm;codecs=opus" });
  }

  // Play a channel (assembled)
  async function playChannel(channel: string) {
    const track = tracksRef.current.get(channel);
    if (!track) return;
    const blob = buildBlob(track);
    if (!blob) {
      alert("Nothing playable yet for this channel (only header-sized chunks). Try recording longer or releasing-to-send.");
      return;
    }
    // Can the browser play this MIME?
    const mime = track.mime || "audio/webm;codecs=opus";
    const test = document.createElement("audio");
    const support = test.canPlayType(mime);
    if (!support) {
      alert(`Failed to play audio. Unsupported format: ${mime}`);
      return;
    }

    const url = URL.createObjectURL(blob);
    if (!audioRef.current) audioRef.current = new Audio();
    const el = audioRef.current;
    el.volume = Math.max(0, Math.min(1, volume));
    el.src = url;
    try {
      await el.play();
    } catch (err) {
      console.error(err);
      alert(`Audio play failed: ${String((err as any)?.message || err)}`);
    } finally {
      // clean up after it ends
      el.onended = () => URL.revokeObjectURL(url);
    }
  }

  // Download a channel (assembled)
  function downloadChannel(channel: string) {
    const track = tracksRef.current.get(channel);
    if (!track) return;
    const blob = buildBlob(track);
    if (!blob) {
      alert("No audio to download yet for this channel.");
      return;
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const ext = (track.mime || "").includes("ogg") ? "ogg" : "webm";
    a.href = url;
    a.download = `voice_${channel.replace(/[:/#]/g, "_")}.${ext}`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      a.remove();
    }, 0);
  }

  // Render recent voice channels (most recent first)
  const voiceRows = useMemo(() => {
    const arr = Array.from(tracksRef.current.values());
    arr.sort((a, b) => b.updated - a.updated);
    return arr.slice(0, 16);
  }, [items.length]); // re-evaluate as feed grows

  return (
    <div>
      <h3 style={{ margin: "10px 0" }}>
        Wave Inbox{" "}
        <span
          style={{
            fontSize: 12,
            marginLeft: 6,
            color: connected ? "#16a34a" : "#b91c1c",
          }}
        >
          ws: {connected ? "● connected" : "● disconnected"}
        </span>
        <button
          onClick={copyInvite}
          style={{
            marginLeft: 8,
            fontSize: 12,
            border: "1px solid #e5e7eb",
            borderRadius: 6,
            padding: "2px 6px",
            background: "#fff",
            cursor: "pointer",
          }}
          title="Copy a link that opens Inbox on this topic"
        >
          Copy Invite
        </button>
        <label style={{ marginLeft: 8, fontSize: 12, color: "#475569", userSelect: "none" }}>
          <input
            type="checkbox"
            checked={audioEnabled}
            onChange={(e) => setAudioEnabled(e.target.checked)}
            style={{ marginRight: 6 }}
          />
          Enable audio
        </label>
        <span style={{ marginLeft: 10, fontSize: 12, color: "#475569" }}>vol</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={volume}
          onChange={(e) => setVolume(parseFloat(e.target.value))}
          style={{ verticalAlign: "middle" }}
          aria-label="Volume"
        />
      </h3>

      <input
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        style={{ width: "100%", marginBottom: 6, padding: 8 }}
        placeholder="ucs://realm/container"
      />

      {getRecent(8).length > 0 && (
        <div style={{ marginBottom: 8, fontSize: 12, color: "#475569" }}>
          Recent:{" "}
          {getRecent(8).map((a) => (
            <button
              key={`recent:${a.topic}`}
              onClick={() => setTopic(a.topic)}
              style={{
                marginRight: 6,
                border: "1px solid #e5e7eb",
                borderRadius: 12,
                padding: "2px 8px",
                background: "#fff",
              }}
              title={a.label || a.topic}
            >
              {a.label || a.topic}
            </button>
          ))}
        </div>
      )}

      <div style={{ fontSize: 12, marginBottom: 6, color: "#475569" }}>Topic: {topic}</div>

      <pre
        style={{
          padding: 8,
          border: "1px solid #e5e7eb",
          borderRadius: 6,
          background: "#fff",
          maxHeight: 420,
          overflow: "auto",
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
          fontSize: 12,
        }}
      >
        {items.length
          ? items
              .map((m) => {
                const head = `+ id=${(m.id || "").slice(0, 8)}.. ts=${m.ts}`;
                const g = `  glyphs: ${JSON.stringify(m.glyphs)}`;
                const s = `  stream: ${JSON.stringify(m.stream)}`;
                const t = `  to: ${m.to}`;
                const v = m.voice
                  ? `  voice: { channel: ${m.voice.channel}, seq: ${m.voice.seq}, mime: ${m.voice.mime}, size: ${m.voice.size} }`
                  : "";
                return [head, g, s, t, v].filter(Boolean).join("\n");
              })
              .join("\n\n")
          : "Waiting for waves on " + topic + "…"}
      </pre>

      {/* Voice channels (assembled) */}
      {voiceRows.length > 0 && (
        <div
          style={{
            marginTop: 8,
            padding: 8,
            border: "1px solid #e5e7eb",
            borderRadius: 6,
            background: "#fff",
          }}
        >
          {voiceRows.map((tr) => {
            const usefulCount = tr.chunks.filter(c => c.bytes.length > 200).length;
            const totalBytes = tr.chunks.reduce((n, c) => n + c.bytes.length, 0);
            return (
              <div key={tr.channel} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <code style={{ flex: 1 }}>
                  {tr.channel} • {usefulCount || tr.chunks.length} {usefulCount ? "chunks" : "chunks (mostly headers)"} • {tr.mime} • size: {totalBytes}
                </code>
                <button onClick={() => playChannel(tr.channel)} style={{ padding: "2px 8px", border: "1px solid #e5e7eb", borderRadius: 6 }}>
                  ▶ Play
                </button>
                <button onClick={() => downloadChannel(tr.channel)} style={{ padding: "2px 8px", border: "1px solid #e5e7eb", borderRadius: 6 }}>
                  ⬇ Download
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Debug live voice feed */}
      <div
        style={{
          marginTop: 8,
          padding: 8,
          border: "1px solid #e5e7eb",
          borderRadius: 6,
          background: "#fff",
          maxHeight: 220,
          overflow: "auto",
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
          fontSize: 12,
        }}
      >
        {messages
          .map((m) => (m as any)?.envelope ?? m)
          .filter((env) => env?.capsule?.voice_frame)
          .slice(0, 60)
          .map((env: any) => {
            const vf = env.capsule.voice_frame;
            const k = env.id || `${vf.channel}:${vf.seq}`;
            return (
              <div key={`vf:${k}`} style={{ padding: "2px 0" }}>
                <code>voice</code> • <strong>{vf.channel}</strong> • seq {vf.seq} • {vf.mime}
              </div>
            );
          })}
      </div>
    </div>
  );
}