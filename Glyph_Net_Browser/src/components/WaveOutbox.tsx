// src/components/WaveOutbox.tsx
import { useMemo, useRef, useState } from "react";
import { getRecent, rememberTopic } from "@/lib/addressBook";

// Resolve API base for Codespaces, local dev, or custom host
function resolveApiBase(): string {
  const host = location.host;
  const isCodespaces = host.endsWith(".app.github.dev");

  // Codespaces: Vite on -5173, backend on -8080 (HTTPS)
  if (isCodespaces) return `https://${host.replace("-5173", "-8080")}`;

  // Local Vite dev
  if (host === "localhost:5173" || host === "127.0.0.1:5173") return "http://localhost:8080";

  // Optional override via env (e.g. VITE_API_HOST="api.myhost:8080")
  const envHost = (import.meta as any)?.env?.VITE_API_HOST as string | undefined;
  if (envHost) {
    const scheme = location.protocol === "https:" ? "https" : "http";
    return `${scheme}://${envHost}`;
  }

  // If we're on somehost:5173, try same host :8080
  const m = host.match(/^(.*):5173$/);
  if (m) return `${location.protocol}//${m[1]}:8080`;

  // Fallback: same origin (co-hosted backend/proxy)
  return `${location.protocol}//${host}`;
}

// util: ArrayBuffer -> base64 (large-safe)
function abToB64(buf: ArrayBuffer) {
  let bin = "";
  const bytes = new Uint8Array(buf);
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(bin);
}

export default function WaveOutbox() {
  const [to, setTo] = useState("ucs://local/ucs_hub");
  const [label, setLabel] = useState("");
  const [text, setText] = useState("");
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  // PTT state
  const [micReady, setMicReady] = useState(false);
  const [pttDown, setPttDown] = useState(false);
  const mrRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const seqRef = useRef<number>(0);
  const channelRef = useRef<string>("");

  const recent = getRecent(8);
  const apiBase = useMemo(() => resolveApiBase(), []);

  async function send() {
    const msg = text.trim();
    if (!msg) return;

    setBusy(true);
    setResult(null);

    try {
      const r = await fetch(`${apiBase}/api/glyphnet/tx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipient: to,
          capsule: { glyphs: [msg], glyph_stream: [msg] }, // keep both for compatibility
          meta: { trace_id: "browser-outbox" },
        }),
      });

      const json = await r.json().catch(() => ({}));
      if (!r.ok) {
        setResult({ status: r.status, statusText: r.statusText, body: json });
      } else {
        setResult(json);
        if (json?.status === "ok") {
          rememberTopic(to, label || undefined);
          setText("");
          // Open the thread
          location.hash = `#/inbox?topic=${encodeURIComponent(to)}`;
        }
      }
    } catch (e: any) {
      setResult({ error: String(e) });
    } finally {
      setBusy(false);
    }
  }

  // --- PTT (Push-To-Talk) ---
  async function ensureMic() {
    if (streamRef.current) return;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    streamRef.current = stream;
    setMicReady(true);
  }

  function pickMime(): string {
    const candid = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
    ];
    for (const c of candid) {
      if (MediaRecorder.isTypeSupported(c)) return c;
    }
    return ""; // let browser pick
  }

  async function startPTT() {
    try {
      await ensureMic();
    } catch (e) {
      alert("Microphone permission is required for PTT.");
      return;
    }

    // New logical channel per hold; receiver stitches via (channel, seq)
    channelRef.current = `voice:${to}#${Date.now().toString(36)}`;
    seqRef.current = 0;

    const mime = pickMime();
    const mr = new MediaRecorder(streamRef.current!, mime ? { mimeType: mime } : undefined);

    mr.ondataavailable = async (ev) => {
      if (!ev.data || ev.data.size === 0) return;
      try {
        const buf = await ev.data.arrayBuffer();
        const b64 = abToB64(buf);
        const payload = {
          recipient: to,
          capsule: {
            voice_frame: {
              channel: channelRef.current,
              seq: seqRef.current++,
              ts: Date.now(),
              mime: mr.mimeType || mime || "audio/webm",
              data_b64: b64,
            },
          },
          meta: { trace_id: "ptt-frame" },
        };
        // fire-and-forget; errors are non-fatal per-frame
        fetch(`${apiBase}/api/glyphnet/tx`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }).catch(() => {});
      } catch {}
    };

    mr.start(250); // ~200–300ms frames
    mrRef.current = mr;
    setPttDown(true);
  }

  function stopPTT() {
    const mr = mrRef.current;
    if (mr && mr.state !== "inactive") {
      mr.stop();
    }
    mrRef.current = null;
    setPttDown(false);
    // keep microphone stream alive for snappier next press (stop if you prefer)
    // streamRef.current?.getTracks().forEach(t => t.stop()); streamRef.current = null;
  }

  return (
    <div>
      <h3 style={{ margin: "10px 0" }}>Wave Outbox</h3>

      {/* To: (datalist + quick chips) */}
      <input
        list="gnet-topics"
        value={to}
        onChange={(e) => setTo(e.target.value)}
        style={{ width: "100%", padding: 8, marginBottom: 6 }}
        placeholder="ucs://realm/container"
      />
      <datalist id="gnet-topics">
        {recent.map((a) => (
          <option key={a.topic} value={a.topic}>
            {a.label || a.topic}
          </option>
        ))}
      </datalist>

      {/* Optional label for Address Book */}
      <input
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Add a label (e.g., Kevin • wave.tp)"
        style={{ width: "100%", padding: 8, marginBottom: 6 }}
      />

      {recent.length > 0 && (
        <div style={{ marginBottom: 6, fontSize: 12, color: "#475569" }}>
          Recent:{" "}
          {recent.map((a) => (
            <button
              key={a.topic}
              onClick={() => setTo(a.topic)}
              style={{
                marginRight: 6,
                border: "1px solid #e5e7eb",
                borderRadius: 12,
                padding: "2px 8px",
                background: "#fff",
              }}
              title={`used ${a.uses}×`}
            >
              {a.label || a.topic}
            </button>
          ))}
        </div>
      )}

      {/* Body (text) */}
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        style={{ width: "100%", padding: 8, marginTop: 4 }}
        placeholder="type a wave…"
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
        }}
      />

      <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
        <button
          onClick={send}
          disabled={busy}
          style={{
            padding: "6px 10px",
            borderRadius: 6,
            border: "1px solid #e5e7eb",
            background: busy ? "#e2e8f0" : "#f8fafc",
            cursor: busy ? "not-allowed" : "pointer",
            fontSize: 13,
          }}
        >
          {busy ? "Sending…" : "Send Wave"}
        </button>

        {/* Hold-to-talk */}
        <button
          onMouseDown={startPTT}
          onMouseUp={stopPTT}
          onMouseLeave={() => pttDown && stopPTT()}
          onTouchStart={startPTT}
          onTouchEnd={stopPTT}
          style={{
            padding: "8px 12px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: pttDown ? "#fee2e2" : "#fff",
            fontSize: 13,
          }}
          title={micReady ? "Hold to talk" : "Hold to talk (will ask for mic)"}
        >
          {pttDown ? "● Talking…" : "🎙 Hold to talk"}
        </button>
        {!micReady && (
          <button
            onClick={ensureMic}
            style={{ fontSize: 12, border: "1px dashed #94a3b8", borderRadius: 6, padding: "4px 8px", background: "#fff" }}
            title="Prepare microphone access (optional)"
          >
            Enable mic
          </button>
        )}
      </div>

      {result && (
        <pre
          style={{
            marginTop: 10,
            background: "#f8fafc",
            padding: 8,
            borderRadius: 6,
            overflow: "auto",
          }}
        >
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}