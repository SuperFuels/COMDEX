// src/routes/ChatThread.tsx (FIRST HALF — UPDATED)
import { useEffect, useMemo, useRef, useState } from "react";
import useGlyphnet from "@/hooks/useGlyphnet";
import { getRecent, rememberTopic, resolveHumanAddress, getContacts } from "@/lib/addressBook";
import type { RecentItem } from "@/lib/addressBook";

type GraphKey = "personal" | "work";

const CLIENT_ID = (() => {
  const k = "gnet:clientId";
  let v = sessionStorage.getItem(k);
  if (!v) {
    v = "chat-thread#" + Math.random().toString(36).slice(2, 8);
    try { sessionStorage.setItem(k, v); } catch {}
  }
  return v;
})();

// ──────────────────────────────────────────────────────────────
// Utils
// ──────────────────────────────────────────────────────────────
function resolveApiBase(): string {
  const host = location.host;
  const isCodespaces = host.endsWith(".app.github.dev");
  if (isCodespaces) return `https://${host.replace("-5173", "-8080")}`;
  if (host === "localhost:5173" || host === "127.0.0.1:5173") return "http://localhost:8080";
  const envHost = (import.meta as any)?.env?.VITE_API_HOST as string | undefined;
  if (envHost) {
    const scheme = location.protocol === "https:" ? "https" : "http";
    return `${scheme}://${envHost}`;
  }
  const m = host.match(/^(.*):5173$/);
  if (m) return `${location.protocol}//${m[1]}:8080`;
  return `${location.protocol}//${host}`;
}

function abToB64(buf: ArrayBuffer) {
  let bin = "";
  const bytes = new Uint8Array(buf);
  const CH = 0x8000;
  for (let i = 0; i < bytes.length; i += CH) {
    bin += String.fromCharCode(...bytes.subarray(i, i + CH));
  }
  return btoa(bin);
}

function b64ToBlob(b64: string, mime: string) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

type NormalizedMsg =
  | { id: string; ts: number; kind: "text"; from?: string; to?: string; text: string }
  | { id: string; ts: number; kind: "voice"; from?: string; to?: string; mime: string; data_b64: string; durMs?: number };

// Normalize an incoming event from the WS hook into our UI shape.
function normalizeIncoming(ev: any): NormalizedMsg | undefined {
  const ts = Math.round(((ev?.ts as number) ?? Date.now()));
  const from = ev?.from;
  const to = ev?.to;

  // Voice (capsule.voice_frame or voice_frame)
  const vf = ev?.capsule?.voice_frame ?? ev?.voice_frame;
  if (vf && (vf.data_b64 || vf.bytes_b64 || vf.b64)) {
    const id = `vf:${vf.channel ?? "ch"}:${vf.seq ?? 0}:${vf.ts ?? ts}`;
    const mime = vf.mime || vf.codec || "audio/webm";
    const data_b64 = vf.data_b64 || vf.bytes_b64 || vf.b64 || "";
    return { id, ts: (vf.ts ? Math.round(vf.ts) : ts), kind: "voice", from, to, mime, data_b64 };
  }

  // Text (capsule.glyphs / glyph_stream / text)
  const txt =
    (Array.isArray(ev?.capsule?.glyphs) ? ev.capsule.glyphs.join("") : undefined) ??
    (Array.isArray(ev?.capsule?.glyph_stream) ? ev.capsule.glyph_stream.join("") : undefined) ??
    ev?.text ??
    ev?.payload?.text;

  if (typeof txt === "string" && txt.length) {
    const id = `txt:${ev?.id ?? ts}:${txt.slice(0, 16)}`;
    return { id, ts, kind: "text", from, to, text: txt };
  }

  return undefined;
}

// ──────────────────────────────────────────────────────────────
export default function ChatThread({
  defaultTopic,
  defaultGraph,
}: {
  defaultTopic?: string;
  defaultGraph?: GraphKey;
}) {
  // Per-tab agent id (used in lock ownership + sent as X-Agent-Id on /tx)
  const AGENT_ID = useMemo(() => {
    let id = sessionStorage.getItem("gnet:agentId");
    if (!id) {
      id = "chat-thread:" + Math.random().toString(36).slice(2, 10);
      sessionStorage.setItem("gnet:agentId", id);
    }
    return id;
  }, []);

  // Topic: prefer #/chat?topic=, else prop, else local default
  const [topic, setTopic] = useState<string>(() => {
    const h = window.location.hash || "";
    const qs = h.includes("?") ? h.slice(h.indexOf("?") + 1) : "";
    const sp = new URLSearchParams(qs);
    return sp.get("topic") || defaultTopic || "ucs://local/ucs_hub";
  });

  // Address input is derived from topic and stays in sync
  const [addrInput, setAddrInput] = useState<string>(topic || "");
  useEffect(() => setAddrInput(topic || ""), [topic]);

  // Graph: prefer #/chat?kg=, else prop, else "personal"
  const [graph, setGraph] = useState<GraphKey>(() => {
    const h = window.location.hash || "";
    const qs = h.includes("?") ? h.slice(h.indexOf("?") + 1) : "";
    const sp = new URLSearchParams(qs);
    const kg = (sp.get("kg") || defaultGraph || "personal").toLowerCase() as GraphKey;
    return kg === "work" ? "work" : "personal";
  });

  useEffect(() => {
    if (defaultTopic) setTopic((t) => t || defaultTopic);
  }, [defaultTopic]);

  // React to hash changes
  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash || "";
      const qs = h.includes("?") ? h.slice(h.indexOf("?") + 1) : "";
      const sp = new URLSearchParams(qs);
      const t = sp.get("topic");
      if (t) setTopic(t);
      const kg = sp.get("kg") as GraphKey | null;
      if (kg) setGraph(kg === "work" ? "work" : "personal");
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const { connected, messages } = useGlyphnet(topic);

  // ─── Floor control (walkie-talkie) state ─────────────────────
  const [floorOwned, setFloorOwned] = useState(false);
  const [floorBusyBy, setFloorBusyBy] = useState<string | null>(null);
  const lockResourceRef = useRef<string | null>(null);
  const keepaliveRef = useRef<number | null>(null);

  // 🔒 Handle lock events (entanglement_lock) for this topic
  // NOTE: messages are newest-first in useGlyphnet, so scanning by index would miss events.
  // We dedupe by a synthetic key instead.
  const processedLocksRef = useRef<Set<string>>(new Set());
  const pttDownRef = useRef(false); // declared here so lock effect can read it

  useEffect(() => {
    const resource = `voice:${topic}`;
    const makeKey = (ev: any) =>
      `${ev?.resource}|${ev?.state}|${ev?.owner}|${ev?.until ?? ""}|${ev?.granted ?? ""}|${ev?.ts ?? ""}`;

    for (const raw of messages) {
      const ev = (raw as any)?.entanglement_lock || (raw as any);
      if (ev?.type !== "entanglement_lock") continue;

      // accept either "resource" or helper "resourceTopic"
      const evResource = ev?.resource || (ev?.resourceTopic ? `voice:${ev.resourceTopic}` : undefined);
      if (evResource !== resource) continue;

      const k = makeKey(ev);
      if (processedLocksRef.current.has(k)) continue;
      processedLocksRef.current.add(k);

      if (ev.state === "held") {
        if (ev.owner && ev.owner !== AGENT_ID) {
          setFloorBusyBy(ev.owner);
          if (floorOwned) stopPTT(); // defined later in file
          setFloorOwned(false);
        } else if (ev.owner === AGENT_ID) {
          setFloorBusyBy(null);
          setFloorOwned(true);
        }
      } else if (ev.state === "free") {
        // Ignore our own denied acquire echo (race)
        if (ev.owner === AGENT_ID && ev.granted === false) {
          setFloorOwned(false);
          setFloorBusyBy((prev) => prev || "busy");
        } else {
          setFloorBusyBy(null);
          if (!pttDownRef.current) setFloorOwned(false);
        }
      }
    }
  }, [messages, topic, AGENT_ID, floorOwned]);


  const recent = useMemo(() => getRecent(8), []);

  // audio prefs
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [audioVol, setAudioVol] = useState(0.9);

  // mic picker …
  const [mics, setMics] = useState<MediaDeviceInfo[]>([]);
  const [selectedMicId, setSelectedMicId] = useState<string>(() => localStorage.getItem("gnet:micDeviceId") || "");

  async function refreshMics() {
    try {
      const list = await navigator.mediaDevices.enumerateDevices();
      const onlyMics = list.filter((d) => d.kind === "audioinput");
      setMics(onlyMics);
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

  function chooseMic(id: string) {
    setSelectedMicId(id);
    try {
      localStorage.setItem("gnet:micDeviceId", id);
    } catch {}
  }

  // Invite link carries graph
  async function copyInvite() {
    const url = `${location.origin}/#/chat?topic=${encodeURIComponent(topic)}&kg=${graph}`;
    try {
      await navigator.clipboard.writeText(url);
      alert("Invite link copied:\n" + url);
    } catch {
      prompt("Copy this link:", url);
    }
  }

  // Thread state is namespaced by graph + topic
  const storageKey = useMemo(() => `gnet:thread:${graph}:${topic}`, [graph, topic]);
  const [thread, setThread] = useState<NormalizedMsg[]>([]);
  const seenRef = useRef<Set<string>>(new Set());

  // reset view when switching conversation (topic/graph)
  useEffect(() => {
    setThread([]);
    seenRef.current = new Set();
  }, [storageKey]);

  // Load per-thread history from sessionStorage whenever the storageKey changes
  useEffect(() => {
    let parsed: NormalizedMsg[] = [];
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (raw) parsed = JSON.parse(raw);
    } catch {}
    setThread(parsed);
    seenRef.current = new Set(parsed.map((m) => m.id));
  }, [storageKey]);

  // Merge incoming WS messages into this thread (de-duped by id), then persist
  useEffect(() => {
    if (!messages || !messages.length) return;

    setThread((prev) => {
      let next = prev.slice();
      let changed = false;

      for (const ev of messages) {
        const nm = normalizeIncoming(ev);
        if (!nm) continue;
        if (seenRef.current.has(nm.id)) continue;
        seenRef.current.add(nm.id);
        next.push(nm);
        changed = true;
      }

      if (changed) {
        next.sort((a, b) => a.ts - b.ts);
        try {
          sessionStorage.setItem(storageKey, JSON.stringify(next));
        } catch {}
        return next;
      }
      return prev;
    });
  }, [messages, storageKey]);

  // ──────────────────────────────────────────────────────────────
  // Composer + PTT state …
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [pttDown, setPttDown] = useState(false);
  const mrRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  // pttDownRef is declared above so the lock-effect can read it
  const cancelOnStartRef = useRef(false); // future: prevents early release race if needed
  const [micReady, setMicReady] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const meterRAF = useRef<number | null>(null);
  const urlsRef = useRef<string[]>([]);
  useEffect(
    () => () => {
      urlsRef.current.forEach((u) => URL.revokeObjectURL(u));
      urlsRef.current = [];
    },
    []
  );
  const scrollRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [thread.length]);

  // Initial server history load per topic/graph
  const apiBase = useMemo(() => resolveApiBase(), []);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(
          `${apiBase}/api/glyphnet/thread?topic=${encodeURIComponent(topic)}&kg=${graph}&limit=200`
        );
        if (!r.ok) throw new Error(`thread fetch ${r.status}`);
        const j = await r.json();
        const evs: any[] = j.events || [];
        const norm: NormalizedMsg[] = evs
          .map((e) => normalizeIncoming(e))
          .filter(Boolean) as NormalizedMsg[];

        if (cancelled) return;
        const merged = norm.sort((a, b) => a.ts - b.ts);
        setThread(merged);
        seenRef.current = new Set(merged.map((m) => m.id));
        try {
          sessionStorage.setItem(storageKey, JSON.stringify(merged));
        } catch {}
      } catch {
        // swallow fetch/CORS errors; UI will still show local/WS data
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase, topic, graph, storageKey]);
  // Send text (adds graph in meta)
  async function sendText() {
    const msg = text.trim();
    if (!msg) return;

    setBusy(true);

    const tempId = `local:${Date.now()}:${Math.random().toString(36).slice(2, 6)}`;
    const optim: NormalizedMsg = { id: tempId, ts: Date.now(), kind: "text", text: msg };

    setThread((prev) => {
      const next = [...prev, { ...optim, from: AGENT_ID }];
      try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
      return next;
    });

    try {
      const res = await fetch(`${apiBase}/api/glyphnet/tx`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Agent-Token": "dev-token",
          "X-Agent-Id": AGENT_ID, // unify id everywhere
        },
        body: JSON.stringify({
          recipient: topic,
          capsule: { glyphs: [msg], glyph_stream: [msg] },
          meta: { trace_id: AGENT_ID, graph },
        }),
      });

      let payload: any = null;
      try { payload = await res.json(); } catch {}
      if (!res.ok || (payload && payload.status && payload.status !== "ok")) {
        console.warn("[sendText] tx not ok", { status: res.status, payload });
        // keep optimistic bubble; don't touch recents/input
        return;
      }

      // ✅ persist this conversation in recents for the current graph
      rememberTopic(topic, addrInput || topic, graph);
      setText("");
    } catch (err) {
      console.warn("[sendText] network/error", err);
    } finally {
      setBusy(false);
    }
  }

  function pickMime(): string {
    const candidates = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"];
    for (const m of candidates) {
      if ((window as any).MediaRecorder?.isTypeSupported?.(m)) return m;
    }
    return "audio/webm";
  }

  async function ensureMicPTT(): Promise<{ stream: MediaStream; mime: string }> {
    // reuse the stream if it’s still active
    if (streamRef.current && streamRef.current.active) {
      return { stream: streamRef.current, mime: pickMime() };
    }
    const audio: MediaTrackConstraints = {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    };
    if (selectedMicId) audio.deviceId = { exact: selectedMicId };

    const stream = await navigator.mediaDevices.getUserMedia({ audio });
    streamRef.current = stream;
    setMicReady(true);
    startMeter(stream);
    // after permission is granted device labels become available
    try { await navigator.mediaDevices.enumerateDevices(); refreshMics(); } catch {}
    return { stream, mime: pickMime() };
  }

  function startMeter(stream: MediaStream) {
    stopMeter();
    const Ctx = (window as any).AudioContext || (window as any).webkitAudioContext;
    const ctx: AudioContext = new Ctx();
    audioCtxRef.current = ctx;

    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    src.connect(analyser);

    const data = new Uint8Array(analyser.fftSize);
    const tick = () => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      setMicLevel(Math.sqrt(sum / data.length));
      meterRAF.current = requestAnimationFrame(tick);
    };
    tick();
  }

  function stopMeter() {
    if (meterRAF.current != null) cancelAnimationFrame(meterRAF.current);
    meterRAF.current = null;
    try { audioCtxRef.current?.close(); } catch {}
    audioCtxRef.current = null;
  }

  // Send a lock capsule via GlyphNet
  async function sendLock(op: "acquire" | "refresh" | "release", resource: string, ttl_ms = 3500) {
    const owner = AGENT_ID; // unify on AGENT_ID
    await fetch(`${apiBase}/api/glyphnet/tx`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Agent-Token": "dev-token",
        "X-Agent-Id": owner,
      },
      body: JSON.stringify({
        recipient: topic,
        capsule: { entanglement_lock: { op, resource, owner, ttl_ms, ts: Date.now() } },
        meta: { trace_id: owner, graph },
      }),
    });
  }

  // Wait briefly for a grant/deny event for this resource (scan newest-first safely)
  function waitForLock(resource: string, timeoutMs = 1200): Promise<"granted" | "denied" | "timeout"> {
    const started = Date.now();
    const seen = new Set<string>();
    const key = (ev: any) => `${ev?.resource || ev?.resourceTopic}|${ev?.state}|${ev?.owner}|${ev?.granted ?? ""}|${ev?.ts ?? ""}`;

    return new Promise((resolve) => {
      const deadline = setTimeout(() => resolve("timeout"), timeoutMs);

      const tick = () => {
        for (const m of messages) {
          const ev = (m as any)?.entanglement_lock || (m as any);
          if (ev?.type !== "entanglement_lock") continue;

          const evResource = ev?.resource || (ev?.resourceTopic ? `voice:${ev.resourceTopic}` : undefined);
          if (evResource !== resource) continue;

          const k = key(ev);
          if (seen.has(k)) continue;
          seen.add(k);

          // ignore our own denied echo race
          if (ev.state === "free" && ev.owner === AGENT_ID && ev.granted === false) continue;

          if (ev.granted === true)  { clearTimeout(deadline); return resolve("granted"); }
          if (ev.granted === false) { clearTimeout(deadline); return resolve("denied");  }
        }
        if (Date.now() - started >= timeoutMs) return; // deadline handler will resolve
        requestAnimationFrame(tick);
      };

      requestAnimationFrame(tick);
    });
  }

  // Visual state: show immediate "pressed" + (optional) spinner while waiting for lock
  const [awaitingLock, setAwaitingLock] = useState(false);

  async function startPTT() {
    if (pttDownRef.current) return;
    pttDownRef.current = true;

    // immediate feedback like the old Outbox
    setPttDown(true);
    setAwaitingLock(true);
    console.debug("[PTT] down", { topic, AGENT_ID });

    // Acquire the floor
    const resource = `voice:${topic}`;
    lockResourceRef.current = resource;
    await sendLock("acquire", resource, 3500);
    const res = await waitForLock(resource, 1500);

    if (res !== "granted") {
      setAwaitingLock(false);
      setFloorOwned(false);
      pttDownRef.current = false;
      setPttDown(false);
      // No lock was granted; clear our local reference
      lockResourceRef.current = null;
      return;
    }

    setAwaitingLock(false);
    setFloorOwned(true);
    setFloorBusyBy(null);

    // Keep the lock alive while held
    keepaliveRef.current = window.setInterval(() => {
      if (lockResourceRef.current) sendLock("refresh", lockResourceRef.current, 3500).catch(() => {});
    }, 2000);

    // Start mic
    let stream: MediaStream, mime: string;
    try {
      ({ stream, mime } = await ensureMicPTT());
      // ensure meter is running in case we reused an existing stream
      if (!audioCtxRef.current) startMeter(stream);
    } catch {
      alert("Microphone permission is required for PTT.");
      pttDownRef.current = false;
      setPttDown(false);
      // release the lock we just got
      if (keepaliveRef.current != null) { clearInterval(keepaliveRef.current); keepaliveRef.current = null; }
      const r0 = lockResourceRef.current; lockResourceRef.current = null;
      if (r0) sendLock("release", r0).catch(() => {});
      setFloorOwned(false);
      return;
    }

    const rec = new MediaRecorder(stream, { mimeType: mime });
    mrRef.current = rec;

    const chunks: Blob[] = [];
    rec.ondataavailable = (ev: BlobEvent) => {
      if (ev.data && ev.data.size) {
        chunks.push(ev.data);
        // console.debug("[PTT] chunk bytes=", ev.data.size);
      }
    };

    rec.onstop = async () => {
      try {
        const totalBytes = chunks.reduce((n, b) => n + b.size, 0);
        if (!totalBytes) {
          console.debug("[PTT] empty recording (no bytes)");
          return;
        }

        const full = new Blob(chunks, { type: mime });
        const ab   = await full.arrayBuffer();
        const b64  = abToB64(ab);

        // optimistic bubble (voice note)
        const localId = `local-voice:${Date.now()}:${Math.random().toString(36).slice(2, 6)}`;
        const optimistic: NormalizedMsg = { id: localId, ts: Date.now(), kind: "voice", mime, data_b64: b64 };
        setThread((prev) => {
          const next = [...prev, optimistic];
          try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
          return next;
        });

        const channel = `voice:${topic}#${Math.random().toString(36).slice(2, 10)}`;
        await fetch(`${apiBase}/api/glyphnet/tx`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Agent-Id": AGENT_ID,
            "X-Agent-Token": "dev-token",
          },
          body: JSON.stringify({
            recipient: topic,
            capsule: { voice_frame: { channel, seq: 0, ts: Date.now(), mime, data_b64: b64 } },
            meta: { trace_id: AGENT_ID + "-ptt", graph },
          }),
        });

        rememberTopic(topic, addrInput || topic, graph);
      } finally {
        mrRef.current = null;
        pttDownRef.current = false;
        setPttDown(false);
        // Release the floor
        if (keepaliveRef.current != null) { clearInterval(keepaliveRef.current); keepaliveRef.current = null; }
        const r1 = lockResourceRef.current; lockResourceRef.current = null;
        if (r1) sendLock("release", r1).catch(() => {});
        setFloorOwned(false);
      }
    };

    // IMPORTANT: start with NO timeslice so we get a single proper file (fixes 0:00)
    rec.start();
  }

  function stopPTT() {
    console.debug("[PTT] up");
    setAwaitingLock(false);
    setPttDown(false);
    try {
      // Do NOT call requestData(); on quick taps this can yield an empty blob.
      mrRef.current?.stop();
    } catch {}
    if (keepaliveRef.current != null) { clearInterval(keepaliveRef.current); keepaliveRef.current = null; }
    const r = lockResourceRef.current; lockResourceRef.current = null;
    if (r) sendLock("release", r).catch(() => {});
    setFloorOwned(false);
  }

  // ── keep going into the UI half…
  // Small helper to render an initial/avatar for recents
  function initials(s: string) {
    const parts = s.trim().split(/\s+/);
    const a = (parts[0] || "").charAt(0).toUpperCase();
    const b = (parts[1] || "").charAt(0).toUpperCase();
    return (a + b) || a || "👤";
  }

  // Contacts + Recents for the left rail
  const contacts = useMemo(() => getContacts(), []);
  const recents = useMemo(() => getRecent(20), []);

  // (UI / second half continues below…)

  function playUrlForVoice(m: Extract<NormalizedMsg, { kind: "voice" }>) {
    const url = URL.createObjectURL(b64ToBlob(m.data_b64, m.mime));
    urlsRef.current.push(url);
    return url;
  }

  // keep a local edit buffer for the topic input (already syncs from topic)
  // setAddrInput is defined above; we also allow changing the address here.
  function applyTopicChange(next: string) {
    const v = (next || "").trim();
    if (!v) return;

    // Always resolve to the canonical topic + graph
    const resolved = resolveHumanAddress(v, graph);
    setGraph(resolved.graph);
    setTopic(resolved.topic);

    // Build a clean URL. If the user typed a human handle (contains "@"),
    // keep that in the hash; otherwise use the canonical URI.
    try {
      const sp = new URLSearchParams();
      sp.set("topic", v.includes("@") ? v : resolved.topic);
      sp.set("kg", resolved.graph);
      location.hash = "#/chat?" + sp.toString();
    } catch {}

    try {
      // Store a single recent per (topic, graph) with a nice label
      rememberTopic(resolved.topic, resolved.label || v, resolved.graph);
    } catch {}
  }

  const [showSettings, setShowSettings] = useState(false);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", height: "100%", gap: 12 }}>
      {/* Left rail: Recents / Contacts and graph toggle */}
      <aside
        data-contacts-count={contacts.length}
        style={{
          border: "1px solid #e5e7eb",
          background: "#fff",
          borderRadius: 8,
          padding: 10,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          minHeight: 0,
        }}
      >
        {/* Graph toggle */}
        <div style={{ display: "inline-flex", border: "1px solid #e5e7eb", borderRadius: 8, overflow: "hidden" }}>
          {(["personal", "work"] as GraphKey[]).map((k) => (
            <button
              key={k}
              onClick={() => {
                setGraph(k);
                const sp = new URLSearchParams();
                sp.set("topic", topic);
                sp.set("kg", k);
                location.hash = "#/chat?" + sp.toString();
              }}
              style={{
                padding: "4px 8px",
                background: graph === k ? "#eef2ff" : "#fff",
                border: "none",
                cursor: "pointer",
                fontSize: 12,
              }}
              title={k === "personal" ? "Personal graph" : "Work graph"}
            >
              {k === "personal" ? "Personal" : "Work"}
            </button>
          ))}
        </div>

        {/* Address bar that accepts "kevin@work" */}
        <input
          aria-label="Address or topic"
          value={addrInput}
          onChange={(e) => setAddrInput(e.target.value)}
          onBlur={() => applyTopicChange(addrInput)}
          onKeyDown={(e) => {
            if (e.key === "Enter") applyTopicChange(addrInput);
          }}
          placeholder="kevin@work  •  ucs://realm/contact_or_hub"
          style={{
            width: "100%",
            padding: "6px 8px",
            borderRadius: 8,
            border: "1px solid #e5e7eb",
            background: "#f8fafc",
            fontSize: 13,
          }}
        />

        {/* Inbox / Recent chats */}
        <div style={{ fontWeight: 600, fontSize: 13, color: "#334155" }}>Recent</div>
        <div style={{ overflow: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
          {recents.map((r) => (
            <button
              key={r.topic + (r.label || "")}
              onClick={() => applyTopicChange(r.label ? `${r.label}@${r.graph}` : r.topic)}
              style={{
                display: "grid",
                gridTemplateColumns: "28px 1fr",
                gap: 8,
                alignItems: "center",
                padding: "6px 8px",
                borderRadius: 8,
                border: "1px solid #e5e7eb",
                background: topic === r.topic ? "#eff6ff" : "#fff",
                cursor: "pointer",
                textAlign: "left",
              }}
              title={r.topic}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  border: "1px solid #e5e7eb",
                  display: "grid",
                  placeItems: "center",
                  fontSize: 12,
                  background: "#fafafa",
                }}
              >
                {initials(r.label || r.topic.replace(/^ucs:\/\//, ""))}
              </div>
              <div style={{ overflow: "hidden" }}>
                <div style={{ fontSize: 13, whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden" }}>
                  {r.label || r.topic}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8" }}>{r.graph}</div>
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Right: Chat pane */}
      <div style={{ display: "flex", flexDirection: "column", height: "100%", minWidth: 0 }}>
        {/* Header */}
        <div
          style={{
            position: "relative",
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "10px 12px",
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            background: "#fff",
          }}
        >
          <button
            onClick={() => (location.hash = "#/inbox?topic=" + encodeURIComponent(topic))}
            style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer" }}
          >
            ← Back
          </button>

          <div style={{ fontWeight: 600 }}>Chat</div>
          <div style={{ fontSize: 12, color: connected ? "#16a34a" : "#b91c1c" }}>
            {connected ? "● online" : "● offline"}
          </div>

          {/* Floor status */}
          {!!floorBusyBy && !floorOwned && (
            <div style={{ fontSize: 12, color: "#b45309", marginLeft: 8 }} title="Another user is holding the floor">
              channel busy: <code>{floorBusyBy}</code>
            </div>
          )}

          {/* Simplified KG indicator */}
          <div style={{ marginLeft: "auto", fontSize: 12, color: "#475569" }}>
            Identity:&nbsp;<code>{(addrInput.split("@")[0] || "user")}.tp</code>
          </div>

          {/* Copy invite */}
          <button
            onClick={copyInvite}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer" }}
            title="Copy invite link to clipboard"
          >
            Copy Invite
          </button>

          {/* Settings (gear) consolidates audio + mic controls */}
          <div style={{ position: "relative" }}>
            <button
              onClick={() => setShowSettings((v) => !v)}
              title="Audio & mic settings"
              style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer" }}
            >
              ⚙️
            </button>
            {showSettings && (
              <div
                style={{
                  position: "absolute",
                  right: 0,
                  top: "calc(100% + 6px)",
                  width: 260,
                  border: "1px solid #e5e7eb",
                  borderRadius: 8,
                  background: "#fff",
                  boxShadow: "0 10px 30px rgba(0,0,0,.12)",
                  padding: 10,
                  zIndex: 10,
                }}
              >
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                  <input type="checkbox" checked={audioEnabled} onChange={(e) => setAudioEnabled(e.target.checked)} />
                  Enable audio playback
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8 }}>
                  <span style={{ fontSize: 12, color: "#475569" }}>Volume</span>
                  <input
                    aria-label="Playback volume"
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={audioVol}
                    onChange={(e) => setAudioVol(parseFloat(e.target.value))}
                    style={{ width: 140 }}
                    title="Playback volume"
                  />
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8 }}>
                  <span style={{ fontSize: 12, color: "#475569" }}>Mic</span>
                  <select
                    aria-label="Microphone device"
                    value={selectedMicId}
                    onChange={(e) => chooseMic(e.target.value)}
                    style={{ flex: 1, padding: "4px 6px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff" }}
                    title="Select input device"
                  >
                    <option value="">System default</option>
                    {mics.map((d) => (
                      <option key={d.deviceId} value={d.deviceId}>
                        {d.label || d.deviceId}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={refreshMics}
                    style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer" }}
                    title="Refresh input devices"
                  >
                    ↺
                  </button>
                  {!micReady && (
                    <button
                      onClick={() => ensureMicPTT().catch(() => alert("Microphone permission is required for PTT."))}
                      style={{ padding: "4px 8px", borderRadius: 6, border: "1px dashed #94a3b8", background: "#fff", fontSize: 12 }}
                      title="Request mic access"
                    >
                      Enable mic
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflow: "auto",
            padding: 12,
            background: "#f8fafc",
            display: "flex",
            flexDirection: "column",
            gap: 8,
            marginTop: 8,
            border: "1px solid #e5e7eb",
            borderRadius: 8,
          }}
        >
          {thread.map((m) => {
            const mine =
              (m as any).from === AGENT_ID ||
              (!("from" in (m as any)) && (m.id.startsWith("local:") || m.id.startsWith("local-voice:")));
            const base = {
              alignSelf: mine ? "flex-end" : "flex-start",
              background: mine ? "#dbeafe" : "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              padding: "8px 10px",
              maxWidth: "80%",
              boxShadow: "0 1px 1px rgba(0,0,0,0.04)",
            } as const;
            return (
              <div key={m.id} style={base}>
                {m.kind === "text" ? (
                  <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <audio
                      src={playUrlForVoice(m)}
                      controls
                      preload="metadata"
                      muted={!audioEnabled}
                      onLoadedMetadata={(e) => {
                        try { e.currentTarget.volume = audioVol; } catch {}
                      }}
                      style={{ width: 240 }}
                    />
                    <span style={{ fontSize: 12, color: "#64748b" }}>{m.mime.replace("audio/", "")}</span>
                  </div>
                )}
                <div style={{ fontSize: 10, color: "#94a3b8", marginTop: 4 }}>
                  {new Date(m.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Composer (sticky in pane) */}
        <div
          style={{
            position: "sticky",
            bottom: 0,
            borderTop: "1px solid #e5e7eb",
            background: "#fff",
            padding: 8,
            display: "grid",
            gridTemplateColumns: "1fr auto",
            gap: 8,
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            marginTop: 8,
          }}
        >
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={2}
            placeholder="Type a message"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendText();
              }
            }}
            style={{
              width: "100%",
              padding: 8,
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              resize: "none",
              fontSize: 14,
              background: "#f8fafc",
            }}
          />
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            {/* phone icon (placeholder for calls) */}
            <button
              onClick={() => alert("Calls coming soon")}
              title="Call"
              style={{
                width: 36,
                height: 36,
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                background: "#fff",
                cursor: "pointer",
              }}
            >
              📞
            </button>

            {/* mic icon (PTT) */}
            <button
              disabled={!!floorBusyBy && !floorOwned}
              onPointerDown={startPTT}
              onPointerUp={stopPTT}
              onPointerCancel={stopPTT}
              onPointerLeave={stopPTT}
              title={
                !!floorBusyBy && !floorOwned
                  ? `Channel busy (${floorBusyBy})`
                  : (floorOwned || pttDown ? "Recording… release to send" : (micReady ? "Press and hold to talk" : "Press and hold (will ask for mic)"))
              }
              aria-pressed={pttDown || floorOwned}
              style={{
                width: 36,
                height: 36,
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                background: (pttDown || floorOwned)
                  ? "#dbeafe"                               // blue-ish when active/recording
                  : ((awaitingLock) ? "#e0e7ff"            // light indigo while acquiring the lock
                    : ((!!floorBusyBy && !floorOwned) ? "#fde68a" : "#fff")),
                boxShadow: (pttDown || floorOwned)
                  ? "0 0 0 2px #93c5fd inset, 0 0 12px rgba(59,130,246,.55)"
                  : (awaitingLock ? "0 0 0 2px #a5b4fc inset" : "none"),
                transition: "box-shadow 120ms ease, background 120ms ease",
                cursor: (!!floorBusyBy && !floorOwned) ? "not-allowed" : "pointer",
              }}
            >
              {awaitingLock ? "⏳" : "🎙"}
            </button>

            {(awaitingLock || pttDown || floorOwned) && (
              <span style={{ fontSize: 11, color: awaitingLock ? "#4338ca" : "#1d4ed8", alignSelf: "center" }}>
                {awaitingLock ? "acquiring…" : "listening…"}
              </span>
            )}

            {/* send icon */}
            <button
              onClick={sendText}
              disabled={busy || !text.trim()}
              title="Send"
              style={{
                width: 36,
                height: 36,
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                background: busy || !text.trim() ? "#e2e8f0" : "#fff",
                cursor: busy || !text.trim() ? "not-allowed" : "pointer",
              }}
            >
              ➤
            </button>

            {/* tiny input meter */}
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: 8 }}>
              <div title="Input level" style={{ width: 120, height: 6, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.min(100, Math.round(micLevel * 200))}%`,
                    height: "100%",
                    background: floorOwned ? "#60a5fa" : "#22c55e", // blue when recording, green idle
                    transition: "width 60ms linear, background 120ms ease",
                  }}
                />
              </div>
              {micReady && micLevel < 0.02 && (
                <span style={{ fontSize: 11, color: "#b45309" }}>no input?</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}