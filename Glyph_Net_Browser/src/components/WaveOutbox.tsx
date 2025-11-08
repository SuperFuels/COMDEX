import { useEffect, useMemo, useRef, useState } from "react";
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

  // Mic devices + selection (persisted)
  const [mics, setMics] = useState<MediaDeviceInfo[]>([]);
  const [selectedMicId, setSelectedMicId] = useState<string>(() => localStorage.getItem("gnet:micDeviceId") || "");

  // PTT state
  const [micReady, setMicReady] = useState(false);
  const [pttDown, setPttDown] = useState(false);
  const mrRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const seqRef = useRef<number>(0);
  const channelRef = useRef<string>("");
  const chunksRef = useRef<Blob[]>([]); // (unused for full-note flow; safe to keep)
  const micLevelRef = useRef(0);
  const [micLevel, setMicLevel] = useState(0);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const meterRAF = useRef<number | undefined>();

  // also track down state in a ref for handler lifetimes
  const pttDownRef = useRef(false);

  // per-frame ACKS from /api/glyphnet/tx
  const [acks, setAcks] = useState<{ seq: number; status: string; reason?: string }[]>([]);

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
        headers: {
          "Content-Type": "application/json",
          "X-Agent-Token": "dev-token",
          "X-Agent-Id": "browser-outbox",
        },
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
          location.hash = `#/inbox?topic=${encodeURIComponent(to)}`;
        }
      }
    } catch (e: any) {
      setResult({ error: String(e) });
    } finally {
      setBusy(false);
    }
  }

  // MIME selection for Opus
  function pickMime(): string {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/ogg;codecs=opus",
      "audio/webm",
    ];
    for (const m of candidates) {
      if ((window as any).MediaRecorder?.isTypeSupported?.(m)) return m;
    }
    return "audio/webm";
  }

  // Mic helper for PTT (honors selected deviceId)
  async function ensureMicPTT(): Promise<{ stream: MediaStream; mime: string }> {
    if (streamRef.current && streamRef.current.active) {
      return { stream: streamRef.current, mime: pickMime() };
    }

    const audio: MediaTrackConstraints = {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    };
    if (selectedMicId) audio.deviceId = { exact: selectedMicId };

    // Prompt for permission with the chosen (or default) device
    const stream = await navigator.mediaDevices.getUserMedia({ audio });
    streamRef.current = stream;
    setMicReady(true);

    // Start the live meter & refresh device labels (labels require permission)
    startMeter(stream);
    refreshMics();

    return { stream, mime: pickMime() };
  }

  // Device list management
  async function refreshMics() {
    try {
      const list = await navigator.mediaDevices.enumerateDevices();
      const onlyMics = list.filter((d) => d.kind === "audioinput");
      setMics(onlyMics);

      // If a stored device no longer exists, clear it
      if (selectedMicId && !onlyMics.some((d) => d.deviceId === selectedMicId)) {
        setSelectedMicId("");
        localStorage.removeItem("gnet:micDeviceId");
      }
    } catch {
      // ignore
    }
  }
  useEffect(() => {
    refreshMics();
    const onChange = () => refreshMics();
    navigator.mediaDevices?.addEventListener?.("devicechange", onChange);
    return () => navigator.mediaDevices?.removeEventListener?.("devicechange", onChange);
  }, []);

  function handleSelectMic(id: string) {
    setSelectedMicId(id);
    if (id) localStorage.setItem("gnet:micDeviceId", id);
    else localStorage.removeItem("gnet:micDeviceId");

    // If a stream is already open, close it so next press uses the new device
    try { streamRef.current?.getTracks().forEach((t) => t.stop()); } catch {}
    streamRef.current = null;
  }

  async function startPTT() {
    if (pttDownRef.current) return;
    pttDownRef.current = true;

    let stream: MediaStream, mime: string;
    try {
      ({ stream, mime } = await ensureMicPTT());
      // Safety: if ensureMicPTT returned an existing stream and meter isn't running, kick it.
      if (!audioCtxRef.current) startMeter(stream);
    } catch {
      alert("Microphone permission is required for PTT.");
      pttDownRef.current = false;
      return;
    }

    // fresh logical channel per press (kept)
    channelRef.current = `voice:${to}#${Math.random().toString(36).slice(2, 10)}`;

    const rec = new MediaRecorder(stream, { mimeType: mime });
    mrRef.current = rec;

    // collect ALL chunks, including the final 'flush' chunk fired after stop()
    const chunks: Blob[] = [];
    rec.ondataavailable = (ev: BlobEvent) => {
      if (ev.data && ev.data.size) chunks.push(ev.data);
    };

    rec.onstop = async () => {
      try {
        if (!chunks.length) return;

        // assemble the full recording
        const full = new Blob(chunks, { type: mime });
        const ab = await full.arrayBuffer();

        // base64 encode
        let bin = "";
        const bytes = new Uint8Array(ab);
        const CH = 0x8000;
        for (let i = 0; i < bytes.length; i += CH) {
          bin += String.fromCharCode(...bytes.subarray(i, i + CH));
        }
        const b64 = btoa(bin);

        const vf = {
          channel: channelRef.current!, // stitched by (channel, seq)
          seq: 0,                       // single payload per press
          ts: Date.now(),
          mime,
          data_b64: b64,
        };

        // send once
        const r = await fetch(`${apiBase}/api/glyphnet/tx`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Agent-Id": "browser-outbox",
            "X-Agent-Token": "dev-token",
          },
          body: JSON.stringify({
            recipient: to,
            capsule: { voice_frame: vf },
            meta: { trace_id: "ptt-full" },
          }),
        });

        const j = await r.json().catch(() => ({}));
        const status = j?.status || (r.ok ? "ok" : "err");
        setAcks((prev) => [{ seq: 0, status, reason: j?.reason }, ...prev].slice(0, 200));
      } finally {
        // cleanup for next press
        mrRef.current = null;
        pttDownRef.current = false;
        setPttDown(false);
        // (UI cleanup, meter stop, etc. handled in the second half)
      }
    };

    // IMPORTANT: no timeslice — let the browser write one good file
    rec.start();
    setPttDown(true);
  }

  // ---- Meter helpers (used by ensureMicPTT / cleanup in second half) ----
  function stopMeter() {
    if (meterRAF.current !== undefined) cancelAnimationFrame(meterRAF.current);
    meterRAF.current = undefined;
    try { audioCtxRef.current?.close(); } catch {}
    audioCtxRef.current = null;
  }

  function startMeter(stream: MediaStream) {
    stopMeter();
    const Ctor: any = (window as any).AudioContext || (window as any).webkitAudioContext;
    const ctx = new Ctor();
    audioCtxRef.current = ctx;
    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    src.connect(analyser);

    const data = new Uint8Array(analyser.fftSize);
    const tick = () => {
      analyser.getByteTimeDomainData(data);
      // RMS of centered waveform
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / data.length); // ~0..1
      micLevelRef.current = rms;
      setMicLevel(rms);
      meterRAF.current = requestAnimationFrame(tick);
    };
    tick();
  }
  // (UI + cleanup continues in the second half…)

  function stopPTT() {
    // do NOT gate the final data with pttDownRef here — onstop will send
    try { mrRef.current?.stop(); } catch {}
    // pttDownRef/current flags are cleared in onstop (first half)
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      try { mrRef.current?.stop(); } catch {}
      mrRef.current = null;

      // stop the live input meter first (closes AudioContext)
      try { stopMeter(); } catch {}

      // then stop the mic tracks
      try { streamRef.current?.getTracks().forEach((t) => t.stop()); } catch {}
      streamRef.current = null;

      pttDownRef.current = false;
    };
  }, []);

  const prepareMic = async () => {
    try {
      // ensureMicPTT already starts the input meter
      await ensureMicPTT();
    } catch {
      alert("Microphone permission is required for PTT.");
    }
  };

  // JSX to render
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
          <option key={`${a.topic}::${a.label || ""}`} value={a.topic}>
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
              key={`chip:${a.topic}`}
              onClick={() => setTo(a.topic)}
              style={{
                marginRight: 6,
                border: "1px solid #e5e7eb",
                borderRadius: 12,
                padding: "2px 8px",
                background: "#fff",
                cursor: "pointer",
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

      {/* Mic device picker + controls */}
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          marginTop: 8,
          flexWrap: "wrap",
        }}
      >
        {/* Mic picker */}
        <label style={{ fontSize: 12, color: "#334155" }}>
          Mic:&nbsp;
          <select
            value={selectedMicId}
            onChange={(e) => handleSelectMic(e.target.value)}
            style={{
              fontSize: 12,
              padding: "4px 6px",
              border: "1px solid #e5e7eb",
              borderRadius: 6,
              background: "#fff",
              minWidth: 220,
            }}
            title={
              mics.length
                ? "Choose your microphone device"
                : "Grant microphone permission to see device names"
            }
          >
            <option value="">System default</option>
            {mics.map((d, i) => (
              <option key={d.deviceId || `mic-${i}`} value={d.deviceId}>
                {d.label || `Microphone ${i + 1}`}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={refreshMics}
          style={{
            fontSize: 12,
            border: "1px solid #e5e7eb",
            borderRadius: 6,
            padding: "4px 8px",
            background: "#fff",
            cursor: "pointer",
          }}
          title="Refresh device list"
        >
          ↻ Refresh
        </button>

        {/* (Optional) hint when names are blank */}
        {!micReady && mics.length > 0 && !mics.some(m => m.label) && (
          <span style={{ fontSize: 12, color: "#6b7280" }}>
            Device names hidden — click “Enable mic” to grant permission.
          </span>
        )}
      </div>

      {/* Action row: send + PTT + meter + enable mic */}
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          marginTop: 8,
          flexWrap: "wrap",
        }}
      >
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

        {/* Hold-to-talk (pointer events cover mouse + touch) */}
        <button
          onPointerDown={startPTT}
          onPointerUp={stopPTT}
          onPointerCancel={stopPTT}
          onPointerLeave={stopPTT}
          style={{
            padding: "8px 12px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: pttDown ? "#fee2e2" : "#fff",
            fontSize: 13,
            cursor: "pointer",
          }}
          title={micReady ? "Hold to talk" : "Hold to talk (will ask for mic)"}
          aria-pressed={pttDown}
        >
          {pttDown ? "🔴 Talking…" : "🎙 Hold to talk"}
        </button>

        {/* Mic input level meter */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            title="Input level"
            style={{
              width: 100,
              height: 6,
              background: "#e5e7eb",
              borderRadius: 4,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${Math.min(100, Math.round(micLevel * 200))}%`,
                height: "100%",
                background: "#22c55e",
                transition: "width 60ms linear",
              }}
            />
          </div>
          {micReady && micLevel < 0.02 && (
            <span style={{ fontSize: 12, color: "#b45309" }}>no input?</span>
          )}
        </div>

        {!micReady && (
          <button
            onClick={prepareMic}
            style={{
              fontSize: 12,
              border: "1px dashed #94a3b8",
              borderRadius: 6,
              padding: "4px 8px",
              background: "#fff",
              cursor: "pointer",
            }}
            title="Prepare microphone access (optional)"
          >
            Enable mic
          </button>
        )}
      </div>

      {/* 🔁 Per-frame ACK table */}
      {acks.length > 0 && (
        <div
          style={{
            marginTop: 8,
            maxHeight: 160,
            overflow: "auto",
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 6,
          }}
        >
          <table style={{ width: "100%", fontSize: 12 }}>
            <thead>
              <tr>
                <th align="left">seq</th>
                <th align="left">status</th>
                <th align="left">note</th>
              </tr>
            </thead>
            <tbody>
              {acks.map((a) => (
                <tr key={`ack:${a.seq}`}>
                  <td>{a.seq}</td>
                  <td>{a.status}</td>
                  <td>{a.reason || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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