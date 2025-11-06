import { useEffect, useMemo, useRef, useState } from "react";
import { getRecent } from "@/lib/addressBook";

type InboxItem = {
  id?: string;
  ts?: number;
  glyphs: string[];
  stream: string[];
  to: string;
  voice?: { channel: string; seq: number; mime: string; size: number };
};

// SSR-safe location access
function getLoc() {
  if (typeof window === "undefined") {
    return { host: "", hostname: "", protocol: "http:", origin: "" } as Location;
  }
  return window.location;
}

// Resolve a correct WS URL for Codespaces/local/other hosts
function resolveWsURL(pathAndQuery: string) {
  const { host, hostname, protocol } = getLoc();

  if (!host) return pathAndQuery; // SSR safeguard

  // Codespaces: use the 8080 sibling app with WSS
  if (host.endsWith(".app.github.dev")) {
    return `wss://${host.replace("-5173", "-8080")}${pathAndQuery}`;
  }

  // Any Vite dev host on port 5173
  if (host.endsWith(":5173")) {
    const scheme = protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${hostname}:8080${pathAndQuery}`;
  }

  // Default: same host, protocol-matching WS scheme
  const scheme = protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${host}${pathAndQuery}`;
}

// base64 -> Uint8Array
function b64ToBytes(b64: string) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

type VoiceQueue = { audio: HTMLAudioElement; q: Blob[]; playing: boolean };

export default function WaveInbox({ defaultTopic }: { defaultTopic?: string }) {
  const loc = getLoc();
  const [topic, setTopic] = useState(defaultTopic || "ucs://local/ucs_hub");
  const [wsUp, setWsUp] = useState(false);
  const [items, setItems] = useState<InboxItem[]>([]);
  const [audioEnabled, setAudioEnabled] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const voiceMap = useRef<Map<string, VoiceQueue>>(new Map());

  const recent = getRecent(8);

  // Optional: hydrate from #/inbox?topic=... deep link
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

  // 🔗 Copy Invite deep-link (#/inbox?topic=...)
  const copyInvite = async () => {
    const url = `${loc.origin}/#/inbox?topic=${encodeURIComponent(topic)}`;
    try {
      await navigator.clipboard.writeText(url);
      alert("Invite link copied:\n" + url);
    } catch {
      // Fallback if clipboard blocked
      // eslint-disable-next-line no-alert
      prompt("Copy this link:", url);
    }
  };

  // Build WS URL once per topic change
  const wsURL = useMemo(() => {
    const q = new URLSearchParams({
      token: "dev-token",
      topic, // server accepts raw ucs://… directly
    }).toString();
    return resolveWsURL(`/ws/glyphnet?${q}`);
  }, [topic]);

  useEffect(() => {
    if (!topic) return;

    const ws = new WebSocket(wsURL);
    socketRef.current = ws;

    ws.onopen = () => setWsUp(true);
    ws.onclose = () => setWsUp(false);
    ws.onerror = () => setWsUp(false);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        const env = msg?.envelope ?? msg?.env;
        if (!env) return;

        const cap = env.capsule ?? {};
        const toStrArray = (x: any) => (Array.isArray(x) ? x.map(String) : []);

        const baseNext: InboxItem = {
          id: env.id,
          ts: env.ts ?? Date.now(),
          glyphs: toStrArray(cap.glyphs),
          stream: toStrArray(cap.glyph_stream),
          // prefer server-reported recipient/topic if present
          to: env.recipient || env.topic || topic,
        };

        // Voice frame handling
        const vf = cap.voice_frame;
        if (vf?.data_b64) {
          const bytes = b64ToBytes(vf.data_b64);
          const blob = new Blob([bytes], { type: vf.mime || "audio/webm" });
          enqueueVoice(vf.channel, blob);

          setItems((prev) => [
            {
              ...baseNext,
              voice: {
                channel: vf.channel,
                seq: vf.seq ?? 0,
                mime: vf.mime || "audio/webm",
                size: blob.size,
              },
            },
            ...prev,
          ].slice(0, 200)); // bound growth for voice frames too
        } else {
          // Textual capsule
          setItems((prev) => [baseNext, ...prev].slice(0, 200));
        }

        // Broadcast a lightweight event
        window.dispatchEvent(
          new CustomEvent("glyphnet:wave", {
            detail: { topic: baseNext.to, id: baseNext.id },
          })
        );
      } catch (err) {
        console.warn("WaveInbox parse error:", err);
      }
    };

    return () => {
      try {
        ws.close();
      } catch {}
    };
  }, [wsURL, topic]);

  function ensureQueue(chan: string): VoiceQueue {
    let vq = voiceMap.current.get(chan);
    if (!vq) {
      const audio = new Audio();
      audio.preload = "auto";
      vq = { audio, q: [], playing: false };
      voiceMap.current.set(chan, vq);
    }
    return vq;
  }

  function playNext(chan: string) {
    const vq = voiceMap.current.get(chan);
    if (!vq || vq.playing) return;
    const next = vq.q.shift();
    if (!next) return;

    vq.playing = true;
    const url = URL.createObjectURL(next);
    vq.audio.src = url;

    // Autoplay can be blocked until user toggles audio on
    if (!audioEnabled) {
      vq.playing = false;
      URL.revokeObjectURL(url);
      return;
    }

    vq.audio.onended = () => {
      URL.revokeObjectURL(url);
      vq.playing = false;
      setTimeout(() => playNext(chan), 10);
    };
    vq.audio.onerror = () => {
      URL.revokeObjectURL(url);
      vq.playing = false;
      setTimeout(() => playNext(chan), 10);
    };
    vq.audio
      .play()
      .catch(() => {
        vq.playing = false;
        URL.revokeObjectURL(url);
      });
  }

  function enqueueVoice(chan: string, blob: Blob) {
    const vq = ensureQueue(chan);
    vq.q.push(blob);
    if (!vq.playing) playNext(chan);
  }

  return (
    <div>
      <h3 style={{ margin: "10px 0" }}>
        Wave Inbox{" "}
        <span
          style={{
            fontSize: 12,
            marginLeft: 6,
            color: wsUp ? "#16a34a" : "#b91c1c",
          }}
        >
          ws: {wsUp ? "● connected" : "● disconnected"}
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
      </h3>

      <input
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        style={{ width: "100%", marginBottom: 6, padding: 8 }}
        placeholder="ucs://realm/container"
      />

      {recent.length > 0 && (
        <div style={{ marginBottom: 8, fontSize: 12, color: "#475569" }}>
          Recent:{" "}
          {recent.map((a) => (
            <button
              key={a.topic}
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

      <div style={{ fontSize: 12, marginBottom: 6, color: "#475569" }}>
        Topic: {topic}
      </div>

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
    </div>
  );
}
