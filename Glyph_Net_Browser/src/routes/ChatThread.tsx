// src/routes/ChatThread.tsx (FIRST HALF — UPDATED)
import useGlyphnet from "@/hooks/useGlyphnet";
import { getRecent, rememberTopic, resolveHumanAddress, getContacts } from "@/lib/addressBook";
import type { RecentItem } from "@/lib/addressBook";
import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { canonKG, resolveLabelToWA } from '../utils/nameService';
import type { GraphKey } from '../utils/nameService';
import { makePeer, DEFAULT_ICE } from "../utils/webrtc";
import type { SignalCapsule, VoiceOffer, VoiceAnswer, IceCapsule } from "@/utils/callTypes";

  // ICE servers state (inside component)
const [iceServers, setIceServers] = useState<RTCIceServer[]>(DEFAULT_ICE);

const CLIENT_ID = (() => {
  const k = "gnet:clientId";
  let v = sessionStorage.getItem(k);
  if (!v) {
    v = "chat-thread#" + Math.random().toString(36).slice(2, 8);
    try { sessionStorage.setItem(k, v); } catch {}
  }
  return v;
})();

function hash8(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}
type IceCfg = RTCIceServer[];

function saveIceServers(next: IceCfg) {
  setIceServers(next);
  try { localStorage.setItem("gnet:iceServers", JSON.stringify(next)); } catch {}
}

// Quick helper to append a TURN server
function addTurnServer(uri: string, username?: string, credential?: string) {
  const next = iceServers.slice();
  next.push({ urls: [uri], username, credential });
  saveIceServers(next);
}

function IceSettings() {
  const [open, setOpen] = useState(false);
  const [uri, setUri] = useState("");
  const [username, setUsername] = useState("");
  const [credential, setCredential] = useState("");

  function addTurnLocal() {
    if (!uri.trim() || !username.trim() || !credential.trim()) return;
    const next = [...iceServers, {
      urls: [uri.trim()],
      username: username.trim(),
      credential: credential.trim(),
    }];
    setIceServers(next);
    try { localStorage.setItem("gnet:iceServers", JSON.stringify(next)); } catch {}
    setUri(""); setUsername(""); setCredential("");
  }

  function clearLocalOverride() {
    setIceServers(DEFAULT_ICE);
    try { localStorage.removeItem("gnet:iceServers"); } catch {}
  }

  return (
    <div style={{ marginLeft: 8, display: "inline-flex", alignItems: "center", position: "relative" }}>
      <button
        onClick={() => setOpen(v => !v)}
        title="Call settings (ICE)"
        style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}
      >
        ⚙️ Call Settings
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 6px)",
            padding: 10,
            width: 300,
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            boxShadow: "0 6px 20px rgba(0,0,0,0.08)",
            zIndex: 20,
          }}
        >
          <div style={{ fontSize: 12, marginBottom: 6, fontWeight: 600 }}>ICE servers in use</div>
          <ul style={{ margin: 0, padding: 0, listStyle: "none", maxHeight: 140, overflow: "auto" }}>
            {iceServers.map((s, i) => (
              <li key={i} style={{ fontSize: 12, padding: "2px 0" }}>
                {Array.isArray(s.urls) ? s.urls.join(", ") : s.urls}
                {s.username ? ` — ${s.username}` : ""}
              </li>
            ))}
          </ul>

          <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
            (If backend provides TURN via /api/rtc/ice, it will auto-apply.)
          </div>

          <hr style={{ margin: "8px 0", borderColor: "#eee" }} />

          <div style={{ display: "grid", gap: 6 }}>
            <input
              placeholder="turns:host:5349?transport=tcp"
              value={uri}
              onChange={(e) => setUri(e.target.value)}
              style={{ fontSize: 12, padding: 6, border: "1px solid #e5e7eb", borderRadius: 6 }}
            />
            <input
              placeholder="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={{ fontSize: 12, padding: 6, border: "1px solid #e5e7eb", borderRadius: 6 }}
            />
            <input
              placeholder="credential (password/secret)"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              style={{ fontSize: 12, padding: 6, border: "1px solid #e5e7eb", borderRadius: 6 }}
            />
            <div style={{ display: "flex", gap: 6 }}>
              <button
                onClick={addTurnLocal}
                style={{ fontSize: 12, padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb" }}
              >
                + Add TURN (local override)
              </button>
              <button
                onClick={clearLocalOverride}
                style={{ fontSize: 12, padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb" }}
              >
                Reset to defaults
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

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

// --- de-dupe helpers ---
function hashStr(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) { h = ((h<<5) - h) + s.charCodeAt(i); h |= 0; }
  return h.toString(36);
}

// Robust, cheap fingerprint for base64 payloads
function fpB64(b64: string) {
  const s = b64 || "";
  const len = s.length;
  const head = s.slice(0, 12);
  const tail = s.slice(Math.max(0, len - 12));
  return `${len}:${head}:${tail}`;
}

type NormalizedMsg =
  | { id: string; ts: number; kind: "text"; from?: string; to?: string; text: string }
  | { id: string; ts: number; kind: "voice"; from?: string; to?: string; mime: string; data_b64: string; durMs?: number };

// Normalize an incoming event from the WS hook into our UI shape.
// Normalize an incoming event (works with raw + WS "glyphnet_capsule" wrapper)
function normalizeIncoming(ev: any): NormalizedMsg | undefined {
  // support both raw envelopes and WS wrapper: { type:"glyphnet_capsule", envelope:{...} }
  const envelope = ev?.envelope ?? ev ?? {};
  const cap = ev?.capsule ?? envelope?.capsule ?? {};

  // timestamps + ids
  const ts = Math.round((envelope?.ts as number) ?? (ev?.ts as number) ?? Date.now());
  const evId =
    ev?.id || ev?.msg_id || envelope?.id || envelope?.msg_id;

  // metadata
  const from =
    ev?.from ??
    ev?.meta?.from ??
    envelope?.meta?.from ??
    envelope?.meta?.trace_id;

  const to =
    ev?.to ??
    ev?.meta?.to ??
    envelope?.meta?.to;

  // ── Voice frame …
  const vf = cap?.voice_frame ?? ev?.voice_frame;
  if (vf && (vf.data_b64 || vf.bytes_b64 || vf.b64)) {
    const idBase =
      evId ||
      `${vf.channel ?? "ch"}:${vf.seq ?? 0}:${vf.ts ?? ts}`;
    const id = `vf:${idBase}`;
    const mime = vf.mime || vf.codec || "audio/webm";
    const data_b64 = vf.data_b64 || vf.bytes_b64 || vf.b64 || "";
    return {
      id,
      ts: (vf.ts ? Math.round(vf.ts) : ts),
      kind: "voice",
      from,
      to,
      mime,
      data_b64,
    };
  }

  // ── Voice note …
  const vn = cap?.voice_note ?? ev?.voice_note;
  if (vn && (vn.data_b64 || vn.bytes_b64 || vn.b64)) {
    const idBase = evId || `${vn.ts ?? ts}:${vn.mime ?? "audio/webm"}`;
    const id = `vn:${idBase}`;
    const mime = vn.mime || vn.codec || "audio/webm";
    const data_b64 = vn.data_b64 || vn.bytes_b64 || vn.b64 || "";
    return {
      id,
      ts: (vn.ts ? Math.round(vn.ts) : ts),
      kind: "voice",
      from,
      to,
      mime,
      data_b64,
    };
  }

  // ── Text …
  const glyphs = Array.isArray(cap?.glyphs) ? cap.glyphs : undefined;
  const glyphStream = Array.isArray(cap?.glyph_stream) ? cap.glyph_stream : undefined;

  const txt =
    (glyphs ? glyphs.join("") : undefined) ??
    (typeof ev?.text === "string" ? ev.text : undefined) ??
    (glyphStream ? glyphStream.join("") : undefined);

  if (typeof txt === "string" && txt.length) {
    const id = evId ? `txt:${evId}` : `txt:${ts}:${hash8(txt)}`;
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

  const base = useMemo(() => resolveApiBase(), []);

  // Topic: prefer #/chat?topic=, else prop, else local default
  const [topic, setTopic] = useState<string>(() => {
    const h = window.location.hash || "";
    const qs = h.includes("?") ? h.slice(h.indexOf("?") + 1) : "";
    const sp = new URLSearchParams(qs);
    return sp.get("topic") || defaultTopic || "ucs://local/ucs_hub";
  });

  // Graph: prefer #/chat?kg=, else prop, else "personal"
  const [graph, setGraph] = useState<GraphKey>(() => {
    const h = window.location.hash || "";
    const qs = h.includes("?") ? h.slice(h.indexOf("?") + 1) : "";
    const sp = new URLSearchParams(qs);
    const kg = (sp.get("kg") || defaultGraph || "personal").toLowerCase() as GraphKey;
    return kg === "work" ? "work" : "personal";
  });

  // ✅ Now call the hook (AFTER topic & graph exist)
  const { connected, messages, reconnecting } = useGlyphnet(topic, graph);

  // Address input is derived from topic and stays in sync
  const [addrInput, setAddrInput] = useState<string>(topic || "");
  useEffect(() => setAddrInput(topic || ""), [topic]);

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

  // Load ICE from backend once (and when base changes)
  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const r = await fetch(`${base}/api/rtc/ice`);
        const j = await r.json().catch(() => ({}));
        const list = Array.isArray(j?.iceServers) ? j.iceServers : DEFAULT_ICE;
        if (!cancel) setIceServers(list.length ? list : DEFAULT_ICE);
      } catch {
        if (!cancel) setIceServers(DEFAULT_ICE);
      }
    })();
    return () => { cancel = true; };
  }, [base]);

  // ─── Floor control (walkie-talkie) state ─────────────────────
  const lockResourceRef = useRef<string | null>(null);
  const keepaliveRef = useRef<number | null>(null);

  // PTT + meter state
  const [pttDown, setPttDown] = useState(false);
  const pttDownRef = useRef(false);
  useEffect(() => { pttDownRef.current = pttDown; }, [pttDown]);
  const [floorOwned, setFloorOwned] = useState(false);        // already declared in Part 1
  const [floorBusyBy, setFloorBusyBy] = useState<string | null>(null); // declared in Part 1
  const lastGrantedRef = useRef<boolean>(false);
  const lastAcquireMsRef = useRef<number>(0);
  
  // ⬇️ ADD THIS HERE
  const metricsRef = useRef<{
    sessions: number;
    grants: number;
    denies: number;
    talkMs: number;
    lastStart: number;
    lastAcquireMs: number;
  }>({
    sessions: 0,
    grants: 0,
    denies: 0,
    talkMs: 0,
    lastStart: 0,
    lastAcquireMs: 0,
  });
  // ⬆️

  const [micLevel, setMicLevel] = useState(0);

  // 🔒 Handle lock events (entanglement_lock) for this topic
  const processedLocksRef = useRef<Set<string>>(new Set());

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

  // 🎛️ Mic level loop (start/stop only during PTT)
  const rafRef = useRef<number | null>(null);
  function stopLevelLoop() {
    if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    setMicLevel(0);
  }
  function startLevelLoop() {
    if (rafRef.current != null) return; // already running
    const tick = () => {
      // TODO: read analyser node here and call setMicLevel(level)
      if (pttDown || floorOwned) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        stopLevelLoop();
      }
    };
    rafRef.current = requestAnimationFrame(tick);
  }
  useEffect(() => () => stopLevelLoop(), []);

  // Signaling capsule shapes
  type VoiceOffer  = { voice_offer:  { sdp: string; call_id: string } };
  type VoiceAnswer = { voice_answer: { sdp: string; call_id: string } };
  type VoiceIce    = { ice: { candidate: RTCIceCandidateInit; call_id: string } };

  const recent = useMemo(() => getRecent(8), []);

  // audio prefs
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [audioVol, setAudioVol] = useState(0.9);

    // --- WebRTC signaling scaffolding ---
  type VoiceCaps = {
    voice_offer?: { sdp: string; call_id: string };
    voice_answer?: { sdp: string; call_id: string };
    ice?: { candidate: RTCIceCandidateInit; call_id: string };
  };
  
  const pendingOfferRef = React.useRef<VoiceCaps['voice_offer'] | null>(null);

  const lossRef = useRef<{ recv: number; lost: number; lastSeq: Map<string, number> }>({
    recv: 0,
    lost: 0,
    lastSeq: new Map(),
  });

  // WebRTC: call state + refs (canonical)
  type CallState = "idle" | "ringing" | "offering" | "connecting" | "connected" | "ended";
  const [callState, setCallState] = React.useState<CallState>("idle");

  const pcRef = React.useRef<RTCPeerConnection | null>(null);
  const callIdRef = React.useRef<string | null>(null);

  const localStreamRef = React.useRef<MediaStream | null>(null);
  const remoteStreamRef = React.useRef<MediaStream | null>(null);
  const remoteAudioRef = React.useRef<HTMLAudioElement | null>(null);

  // Mute / Hold state + original mic track
  const [muted, setMuted] = useState(false);
  const [onHold, setOnHold] = useState(false);
  const origTrackRef = useRef<MediaStreamTrack | null>(null);

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

  function clearThreadCache() {
    try { sessionStorage.removeItem(storageKey); } catch {}
    // also wipe in-memory state so the UI reflects the clear immediately
    setThread([]);
    seenRef.current = new Set();
    seenSigRef.current = new Set();
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
  const seenSigRef = useRef<Set<string>>(new Set());
  
  // RTT stash
  const lastRttRef = useRef<number>(0);

  // Sent-cache (ACKed ids) to avoid replays on reconnect
  const sentKey = useMemo(() => `gnet:sent:${graph}:${topic}`, [graph, topic]);
  const sentRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(sentKey);
      sentRef.current = new Set<string>(raw ? JSON.parse(raw) : []);
    } catch {
      sentRef.current = new Set();
    }
  }, [sentKey]);
  function rememberSent(id: string) {
    if (!id) return;
    sentRef.current.add(id);
    if (sentRef.current.size > 500) {
      const trimmed = Array.from(sentRef.current).slice(-500);
      sentRef.current = new Set(trimmed);
    }
    try { sessionStorage.setItem(sentKey, JSON.stringify(Array.from(sentRef.current))); } catch {}
  }

  // reset view when switching conversation (topic/graph)
  useEffect(() => {
    setThread([]);
    seenRef.current = new Set();
    seenSigRef.current = new Set();
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
    // also seed signature de-dupe for already-present items
    for (const m of parsed) {
      const sig = m.kind === "text"
        ? `txt|${(m as any).text}|${Math.round((m.ts || 0) / 5000)}`
        : `vf|${m.mime}|${fpB64(m.data_b64)}|${Math.round((m.ts || 0) / 5000)}`;
      seenSigRef.current.add(sig);
    }
  }, [storageKey]);

  // Merge incoming WS messages into this thread (de-duped), then persist
  useEffect(() => {
    if (!messages?.length) return;

    setThread((prev) => {
      const next = prev.slice();
      let changed = false;

      for (const ev of messages) {
        // ── RTT from server echo
        if ((ev as any)?.meta?.t0) {
          const rtt = Date.now() - ((ev as any).meta.t0 as number);
          lastRttRef.current = rtt;
        }

        // ── Chunk loss (PTT voice_frame only)
        const vf = (ev as any)?.capsule?.voice_frame
          ?? (ev as any)?.envelope?.capsule?.voice_frame;
        if (vf && typeof vf.seq === "number" && typeof vf.channel === "string") {
          const key = `${topic}|${vf.channel}`; // per-topic, per-channel
          const prevSeq = lossRef.current.lastSeq.get(key);
          if (typeof prevSeq === "number") {
            if (vf.seq > prevSeq + 1) lossRef.current.lost += (vf.seq - prevSeq - 1); // gap
            if (vf.seq > prevSeq) {
              lossRef.current.recv += 1;
              lossRef.current.lastSeq.set(key, vf.seq);
            }
            // else duplicate/out-of-order → ignore for recv/lost
          } else {
            // first packet on this channel
            lossRef.current.lastSeq.set(key, vf.seq);
            lossRef.current.recv += 1;
          }
        }

        // ── WebRTC signaling intercept (do not render into thread)
        {
          const cap =
            ((ev as any)?.envelope?.capsule ??
            (ev as any)?.capsule ??
            {}) as any;

          if (cap.voice_offer || cap.voice_answer || cap.ice) {
            const myCall = callIdRef.current;
            const traceId =
              (ev as any)?.envelope?.meta?.trace_id ??
              (ev as any)?.meta?.trace_id;

            if (cap.voice_offer) {
              // Ignore our own offer echoes
              if (traceId !== AGENT_ID) {
                setCallState("ringing");
                // store latest offer so Accept can consume it
                pendingOfferRef.current = cap.voice_offer as { sdp: string; call_id: string };
              }
            } else if (cap.voice_answer && myCall && pcRef.current) {
              if ((cap.voice_answer as any).call_id === myCall) {
                pcRef.current
                  .setRemoteDescription(JSON.parse((cap.voice_answer as any).sdp))
                  .catch(() => {});
                setCallState("connected");
              }
            } else if (cap.ice && myCall && pcRef.current) {
              if ((cap.ice as any).call_id === myCall) {
                pcRef.current
                  .addIceCandidate((cap.ice as any).candidate)
                  .catch(() => {});
              }
            }
            continue; // skip thread rendering for signaling frames
          }
        }

        const nm = normalizeIncoming(ev);
        if (!nm) continue;

        // 1) content-level de-dup (server may replay recent items)
        const sig =
          nm.kind === "text"
            ? `txt|${(nm as any).text}|${Math.round((nm.ts || 0) / 5000)}`
            : `vf|${nm.mime}|${fpB64((nm as any).data_b64)}|${Math.round((nm.ts || 0) / 5000)}`;
        if (seenSigRef.current.has(sig)) {
          seenRef.current.add(nm.id);
          continue;
        }

        // 2) id-level de-dup
        if (seenRef.current.has(nm.id)) continue;

        // 3) server echo of a voice note → replace optimistic local-voice (preserve from)
        if (nm.kind === "voice") {
          const kNow = `${nm.mime}|${fpB64((nm as any).data_b64)}`;
          const i = next.findIndex(
            (m) =>
              m.kind === "voice" &&
              String(m.id).startsWith("local-voice:") &&
              `${m.mime}|${fpB64((m as any).data_b64)}` === kNow
          );
          if (i !== -1) {
            next[i] = { ...nm, from: (next[i] as any).from || (nm as any).from };
            seenRef.current.add(nm.id);
            seenSigRef.current.add(sig);
            if ((ev as any)?.id) rememberSent((ev as any).id);
            changed = true;
            continue;
          }
        }

        // 4) server echo of a text we just sent → replace optimistic local text
        if (nm.kind === "text") {
          // Prefer author match (trace_id/AGENT_ID) when possible
          if ((nm as any).from === AGENT_ID) {
            const j = [...next].reverse().findIndex(
              (m) => m.kind === "text" && String(m.id).startsWith("local:")
            );
            if (j !== -1) {
              const i = next.length - 1 - j;
              next[i] = { ...nm, from: (next[i] as any).from || (nm as any).from };
              seenRef.current.add(nm.id);
              seenSigRef.current.add(sig);
              if ((ev as any)?.id) rememberSent((ev as any).id);
              changed = true;
              continue;
            }
          }

          // Fallback: text + time-window match
          const i = next.findIndex(
            (m) =>
              m.kind === "text" &&
              String(m.id).startsWith("local:") &&
              (m as any).text === (nm as any).text &&
              Math.abs((nm.ts || 0) - (m.ts || 0)) <= 2500
          );
          if (i !== -1) {
            next[i] = { ...nm, from: (next[i] as any).from || (nm as any).from };
            seenRef.current.add(nm.id);
            seenSigRef.current.add(sig);
            if ((ev as any)?.id) rememberSent((ev as any).id);
            changed = true;
            continue;
          }
        }

        // 5) brand-new message → append
        next.push(nm);
        seenRef.current.add(nm.id);
        seenSigRef.current.add(sig);
        if ((ev as any)?.id) rememberSent((ev as any).id);
        changed = true;
      }

      if (!changed) return prev;

      next.sort((a, b) => a.ts - b.ts);
      try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
      return next;
    });
  }, [messages, storageKey, topic, graph, AGENT_ID]);

  // ──────────────────────────────────────────────────────────────
  // Composer + PTT state …
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const iceServers = DEFAULT_ICE;
  const mrRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const audioCtxRef = useRef<AudioContext | null>(null);
  const meterRAF = useRef<number | null>(null);

  const urlsRef = useRef<string[]>([]);
  useEffect(() => {
    return () => {
      urlsRef.current.forEach((u) => URL.revokeObjectURL(u));
      urlsRef.current = [];
    };
  }, []);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [thread.length]);

  // Initial server history load per topic/graph (id+sig de-dupe will avoid duplicates)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(
          `${base}/api/glyphnet/thread?topic=${encodeURIComponent(topic)}&kg=${graph}&limit=200`
        );
        if (!r.ok) throw new Error(`thread fetch ${r.status}`);
        const j = await r.json();
        const evs: any[] = j.events || [];

        // Seed loss metrics from the fetched history
        (function seedLossFromServer() {
          const L = lossRef.current;
          L.recv = 0; L.lost = 0; L.lastSeq = new Map();
          for (const ev of evs) {
            const vf = ev?.capsule?.voice_frame;
            if (!vf || typeof vf.seq !== "number" || typeof vf.channel !== "string") continue;
            const key = `${topic}|${vf.channel}`;
            const prev = L.lastSeq.get(key);
            if (typeof prev === "number") {
              if (vf.seq > prev + 1) L.lost += (vf.seq - prev - 1);
              if (vf.seq > prev) { L.recv += 1; L.lastSeq.set(key, vf.seq); }
            } else {
              L.lastSeq.set(key, vf.seq);
              L.recv += 1;
            }
          }
        })();

        const norm: NormalizedMsg[] = evs
          .map((e) => normalizeIncoming(e))
          .filter(Boolean) as NormalizedMsg[];

        if (cancelled) return;
        const merged = norm.sort((a, b) => a.ts - b.ts);

        // Merge into state + hydrate dedupe sets
        setThread(merged);
        seenRef.current = new Set(merged.map((m) => m.id));
        seenSigRef.current = new Set(
          merged.map((m) =>
            m.kind === "text"
              ? `txt|${(m as any).text}|${Math.round((m.ts || 0) / 5000)}`
              : `vf|${m.mime}|${fpB64(m.data_b64)}|${Math.round((m.ts || 0) / 5000)}`
          )
        );
        try { sessionStorage.setItem(storageKey, JSON.stringify(merged)); } catch {}
      } catch {
        // swallow fetch/CORS errors; UI will still show local/WS data
      }
    })();
    return () => { cancelled = true; };
  }, [base, topic, graph, storageKey]);

  useEffect(() => {
    lossRef.current = { recv: 0, lost: 0, lastSeq: new Map() };
  }, [topic, graph]);



  // ──────────────────────────────────────────────────────────────
  // Send text (adds graph in meta) + optimistic bubble + sent-cache
  async function sendText() {
    const msg = text.trim();
    if (!msg) return;

    setBusy(true);

    const tempId = `local:${Date.now()}:${Math.random().toString(36).slice(2, 6)}`;
    const optim: NormalizedMsg = { id: tempId, ts: Date.now(), kind: "text", text: msg, from: AGENT_ID };

    setThread((prev) => {
      const next = [...prev, optim];
      try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
      return next;
    });

    try {
      const res = await fetch(`${base}/api/glyphnet/tx`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Agent-Token": "dev-token",
          "X-Agent-Id": AGENT_ID,
        },
        body: JSON.stringify({
          recipient: topic,
          capsule: { glyphs: [msg] },
          meta: { trace_id: AGENT_ID, graph, t0: Date.now() }, // ← added here
        }),
      });

      let payload: any = null;
      try { payload = await res.json(); } catch {}
      if (payload?.msg_id) rememberSent(payload.msg_id);

      rememberTopic(topic, addrInput || topic, graph);
      setText("");
    } catch (err) {
      console.warn("[sendText] network/error", err);
    } finally {
      setBusy(false);
    }
  }

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function mimeFromName(name: string): string {
    const ext = (name.split(".").pop() || "").toLowerCase();
    return (
      {
        webm: "audio/webm",
        ogg:  "audio/ogg",
        mp3:  "audio/mpeg",
        m4a:  "audio/mp4",
        wav:  "audio/wav",
        aac:  "audio/aac",
        flac: "audio/flac",
      } as Record<string, string>
    )[ext] || "audio/webm";
  }

  async function sendVoiceNoteFile(f: File) {
    try {
      const mime = f.type || mimeFromName(f.name);
      const arr = await f.arrayBuffer();
      const data_b64 = abToB64(arr);

      // optimistic bubble (re-uses voice echo replacement via mime+fpB64)
      const localId = `local-voice:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
      const optimistic: NormalizedMsg = {
        id: localId, kind: "voice", ts: Date.now(), from: AGENT_ID, mime, data_b64,
      };
      setThread((t) => {
        const next = [...t, optimistic];
        try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
        return next;
      });

      // POST voice_note capsule
      const r = await fetch(`${base}/api/glyphnet/tx`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Agent-Token": "dev-token",
          "X-Agent-Id": AGENT_ID,
        },
        body: JSON.stringify({
          recipient: topic,
          graph,
          capsule: { voice_note: { ts: Date.now(), mime, data_b64 } },
          meta: { trace_id: AGENT_ID, graph, t0: Date.now() },
        }),
      });

      const j = await r.json().catch(() => ({} as any));
      if (j?.msg_id) rememberSent(j.msg_id);

      // ⬇️ Optional transcription → send glyphs:[text]
      if (transcribeOnAttach) {
        setTranscribing(true);
        const t = await transcribeAudio(mime, data_b64); // expects { text, engine }
        setTranscribing(false);
        if (t?.text) {
          await fetch(`${base}/api/glyphnet/tx`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Agent-Token": "dev-token",
              "X-Agent-Id": AGENT_ID,
            },
            body: JSON.stringify({
              recipient: topic,
              graph,
              capsule: { glyphs: [t.text] },
              meta: {
                trace_id: AGENT_ID,
                graph,
                t0: Date.now(),
                transcript_of: j?.msg_id || null,
                engine: t.engine || undefined,
              },
            }),
          }).catch(() => {});
        }
      }

      // persist recents
      rememberTopic(topic, addrInput || topic, graph);
    } catch (e) {
      console.warn("[sendVoiceNoteFile] failed", e);
    }
  }

  // ——— Signaling: POST a signaling capsule over the existing /tx path ———
  async function txSig(capsule: object) {
    await fetch(`${base}/api/glyphnet/tx`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Agent-Token": "dev-token",
        "X-Agent-Id": AGENT_ID,
      },
      body: JSON.stringify({
        recipient: topic,
        graph,
        capsule,
        meta: { trace_id: AGENT_ID, graph, t0: Date.now() },
      }),
    }).catch(() => {});
  }

  async function sendOffer(sdp: string, callId: string) {
    return txSig({ voice_offer: { sdp, call_id: callId } } satisfies VoiceOffer);
  }
  async function sendAnswer(sdp: string, callId: string) {
    return txSig({ voice_answer: { sdp, call_id: callId } } satisfies VoiceAnswer);
  }
  async function sendIce(candidate: RTCIceCandidateInit, callId: string) {
    return txSig({ ice: { candidate, call_id: callId } } satisfies VoiceIce);
  }

  function rememberLocalMicTrack(stream: MediaStream) {
    const t = stream.getAudioTracks?.()[0];
    if (t && !origTrackRef.current) origTrackRef.current = t;
  }

  function toggleMute() {
    setMuted(prev => {
      const next = !prev;
      try {
        const track = origTrackRef.current;
        if (track) track.enabled = !next; // mute = disable local mic track
      } catch {}
      return next;
    });
  }

  async function toggleHold() {
    const pc = pcRef.current;
    const track = origTrackRef.current;
    if (!pc) return;

    const next = !onHold;
    try {
      const sender = pc.getSenders().find(s => s.track && s.track.kind === "audio");
      if (sender) {
        if (next) {
          await sender.replaceTrack(null);          // pause sending
        } else {
          await sender.replaceTrack(track || null); // resume
        }
      }
    } catch {}
    setOnHold(next);
  }

  // ——— Outbound: start a call ———
  async function startCall() {
    if (callState !== "idle") return;

    const callId =
      crypto?.randomUUID?.() || `call-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    callIdRef.current = callId;
    setCallState("offering");

    // reuse mic helper (AEC/AGC/NS already configured there)
    const { stream } = await ensureMicPTT();

    const pc = await makePeer(
      "caller",
      {
        onLocalDescription: (sdp) => sendOffer(JSON.stringify(sdp), callId),
        onLocalIce: (cand) => sendIce(cand, callId),
        onRemoteTrack: (ms) => {
          if (remoteAudioRef.current) remoteAudioRef.current.srcObject = ms;
        },
      },
      { iceServers }
    );

    pc.onconnectionstatechange = () => {
      const s = pc.connectionState;
      if (s === "connected") setCallState("connected");
      if (s === "failed" || s === "closed" || s === "disconnected") setCallState("ended");
    };

    // attach local mic tracks
    stream.getTracks().forEach((t) => pc.addTrack(t, stream));
    rememberLocalMicTrack(stream);   // ⬅️ capture original mic track for mute/hold
    pcRef.current = pc;

    // create + send SDP offer via helper
    await (pc as any)._emitLocalDescription("offer");
  }

  // ——— Inbound: accept a ringing call ———
  async function acceptCall() {
    const offer = (window as any).__pendingOffer as { sdp: string; call_id: string } | undefined;
    if (!offer) return;

    callIdRef.current = offer.call_id;
    setCallState("connecting");

    const { stream } = await ensureMicPTT();

    const pc = await makePeer(
      "callee",
      {
        onLocalDescription: (sdp) => sendAnswer(JSON.stringify(sdp), offer.call_id),
        onLocalIce: (cand) => sendIce(cand, offer.call_id),
        onRemoteTrack: (ms) => {
          if (remoteAudioRef.current) remoteAudioRef.current.srcObject = ms;
        },
      },
      { iceServers }
    );

    pc.onconnectionstatechange = () => {
      const s = pc.connectionState;
      if (s === "connected") setCallState("connected");
      if (s === "failed" || s === "closed" || s === "disconnected") setCallState("ended");
    };

    // attach local mic tracks
    stream.getTracks().forEach((t) => pc.addTrack(t, stream));
    rememberLocalMicTrack(stream);   // ⬅️ capture original mic track for mute/hold
    pcRef.current = pc;

    // apply remote offer, create + send answer
    await pc.setRemoteDescription(JSON.parse(offer.sdp));
    await (pc as any)._emitLocalDescription("answer");

    // clear pending offer
    (window as any).__pendingOffer = null;
  }

  // ——— Decline / Hangup ———
  function declineCall() {
    (window as any).__pendingOffer = null;
    setCallState("idle");
  }

  function hangupCall() {
    try { pcRef.current?.getSenders().forEach((s) => s.track?.stop()); } catch {}
    try { pcRef.current?.close(); } catch {}
    pcRef.current = null;
    callIdRef.current = null;

    // ⬇️ reset mute/hold + original track
    origTrackRef.current = null;
    setMuted(false);
    setOnHold(false);

    setCallState("ended");
  }
  
  // ──────────────────────────────────────────────────────────────
  // Mic / PTT helpers
  const [transcribing, setTranscribing] = React.useState(false);
  const rec2sAndSend = React.useCallback(async () => {
    let stream: MediaStream | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      alert("Mic permission is required");
      return;
    }

    const mr = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    mr.ondataavailable = (e) => e.data && chunks.push(e.data);

    mr.start();
    await new Promise((r) => setTimeout(r, 2000));
    mr.stop();
    await new Promise((r) => (mr.onstop = r as any));

    const blob = new Blob(chunks, { type: mr.mimeType || "audio/webm" });
    const b64 = abToB64(await blob.arrayBuffer());

    try {
      const res = await fetch(`${base}/api/media/transcribe`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Agent-Token": "dev-token",
          "X-Agent-Id": AGENT_ID || "console",
        },
        body: JSON.stringify({ mime: blob.type || "audio/webm", data_b64: b64 }),
      });
      const j = await res.json().catch(() => ({}));
      console.log("[transcribe test]", j);
      alert(j.text ? `Transcript: ${j.text}` : `No text (engine: ${j.engine})`);
    } catch (e) {
      console.warn("[transcribe test] failed", e);
      alert("Transcribe request failed (see console).");
    } finally {
      if (stream) stream.getTracks().forEach((t) => t.stop());
    }
  }, [base]);

  async function transcribeAudio(mime: string, b64: string): Promise<{ text: string; engine?: string } | null> {
    try {
      const r = await fetch(`${base}/api/media/transcribe`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Agent-Token": "dev-token",
          "X-Agent-Id": AGENT_ID,
        },
        body: JSON.stringify({ mime, data_b64: b64 }),
      });
      const j = await r.json().catch(() => ({} as any));
      if (typeof j?.text === "string") return { text: j.text, engine: j.engine };
    } catch (e) {
      console.warn("[transcribeAudio] failed", e);
    }
    return null;
  }

  type PttEntry = {
    at: number;           // session start ms
    dur: number;          // duration ms
    acquireMs?: number;   // time-to-grant ms for that session
    granted: boolean;     // whether floor was acquired for this session
  };

  function pttKey(g: GraphKey, t: string) {
    return `gnet:ptt:log:${g}:${t}`;
  }

  function loadPttLog(g: GraphKey, t: string): PttEntry[] {
    try { return JSON.parse(localStorage.getItem(pttKey(g, t)) || "[]"); } catch { return []; }
  }

  function savePttLog(g: GraphKey, t: string, arr: PttEntry[]) {
    try { localStorage.setItem(pttKey(g, t), JSON.stringify(arr.slice(-10))); } catch {}
  }

  function pickMime(): string {
    const candidates = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"];
    for (const m of candidates) {
      if ((window as any).MediaRecorder?.isTypeSupported?.(m)) return m;
    }
    return "audio/webm";
  }

  async function sendSignal(capsule: SignalCapsule) {
    await fetch(`${base}/api/glyphnet/tx`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Agent-Token": "dev-token",
        "X-Agent-Id": AGENT_ID,
      },
      body: JSON.stringify({
        recipient: topic,
        graph,
        capsule,
        meta: { trace_id: AGENT_ID, graph, t0: Date.now() },
      }),
    });
  }

  const [micReady, setMicReady] = useState(false);
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

    const stream = await navigator.mediaDevices.getUserMedia({ audio });
    streamRef.current = stream;
    setMicReady(true);
    // after permission is granted device labels become available
    try { await navigator.mediaDevices.enumerateDevices(); refreshMics(); } catch {}
    return { stream, mime: pickMime() };
  }

  function stopMeter() {
    if (meterRAF.current != null) cancelAnimationFrame(meterRAF.current);
    meterRAF.current = null;
    try { audioCtxRef.current?.close(); } catch {}
    audioCtxRef.current = null;
    setMicLevel(0);
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
    meterRAF.current = requestAnimationFrame(tick);
  }

  const voiceUrlMapRef = useRef<Map<string, string>>(new Map());
  useEffect(() => {
    return () => {
      for (const u of voiceUrlMapRef.current.values()) {
        try { URL.revokeObjectURL(u); } catch {}
      }
      voiceUrlMapRef.current.clear();
    };
  }, []);

  function playUrlForVoice(m: Extract<NormalizedMsg, { kind: "voice" }>) {
    const key = `${m.id}|${m.mime}`;
    const map = voiceUrlMapRef.current;
    let url = map.get(key);
    if (!url) {
      url = URL.createObjectURL(b64ToBlob(m.data_b64, m.mime));
      map.set(key, url);
    }
    return url;
  }

  // ──────────────────────────────────────────────────────────────
  // Floor control (lock ops) + waiter
  async function sendLock(
    op: "acquire" | "refresh" | "release",
    resource: string,
    ttl_ms = 3500
  ) {
    const owner = AGENT_ID;
    await fetch(`${base}/api/glyphnet/tx`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Agent-Token": "dev-token",
        "X-Agent-Id": owner,
      },
      body: JSON.stringify({
        recipient: topic,
        capsule: { entanglement_lock: { op, resource, owner, ttl_ms, ts: Date.now() } },
        meta: { trace_id: owner, graph, t0: Date.now() }, // ← added t0
      }),
    });
  }

  function waitForLock(resource: string, timeoutMs = 1200): Promise<"granted" | "denied" | "timeout"> {
    const started = Date.now();
    const seen = new Set<string>();
    const key = (ev: any) =>
      `${ev?.resource || ev?.resourceTopic}|${ev?.state}|${ev?.owner}|${ev?.granted ?? ""}|${ev?.ts ?? ""}`;

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

          // ignore our own denied race echo
          if (ev.state === "free" && ev.owner === AGENT_ID && ev.granted === false) continue;

          if (ev.granted === true)  { clearTimeout(deadline); return resolve("granted"); }
          if (ev.granted === false) { clearTimeout(deadline); return resolve("denied");  }
        }
        if (Date.now() - started >= timeoutMs) return; // timeout handler will resolve
        requestAnimationFrame(tick);
      };

      requestAnimationFrame(tick);
    });
  }

  // ──────────────────────────────────────────────────────────────
  // PTT: press/hold to record; on release send single voice note blob
  const [awaitingLock, setAwaitingLock] = useState(false);
  // ^ kept here as reference; real state is defined earlier in Part 1

  const pttChannelRef = useRef<string>("");
  const seqRef = useRef<number>(0);
  useEffect(() => {
    // re-derive channel when topic changes so sessions don't collide
    pttChannelRef.current = `ch-${hash8(topic)}-${hash8(AGENT_ID)}`;
    seqRef.current = 0;
  }, [topic, AGENT_ID]);

  async function startPTT() {
    if (pttDownRef.current) return;
    pttDownRef.current = true;
    setAwaitingLock(true);
    setPttDown(true);

    // ── metrics: mark attempt start
    metricsRef.current.lastStart = Date.now();

    // Acquire the floor
    const resource = `voice:${topic}`;
    lockResourceRef.current = resource;
    await sendLock("acquire", resource, 3500);
    const res = await waitForLock(resource, 1500);

    if (res !== "granted") {
      // ── metrics: denied
      metricsRef.current.denies++;
      lastGrantedRef.current = false;

      setAwaitingLock(false);
      setFloorOwned(false);
      pttDownRef.current = false;
      setPttDown(false);
      lockResourceRef.current = null;
      return;
    } else {
      // ── metrics: granted + time-to-grant
      metricsRef.current.grants++;
      const t = Date.now() - metricsRef.current.lastStart;
      metricsRef.current.lastAcquireMs = t;
      lastAcquireMsRef.current = t;
      lastGrantedRef.current = true;
    }

    setAwaitingLock(false);
    setFloorOwned(true);
    setFloorBusyBy(null);

    // Keep the lock alive while held
    keepaliveRef.current = window.setInterval(() => {
      if (lockResourceRef.current) {
        sendLock("refresh", lockResourceRef.current, 3500).catch(() => {});
      }
    }, 2000);

    // Start mic
    let stream: MediaStream, mime: string;
    try {
      ({ stream, mime } = await ensureMicPTT());
      startMeter(stream); // Meter ONLY during PTT
    } catch {
      alert("Microphone permission is required for PTT.");
      pttDownRef.current = false;
      setPttDown(false);
      if (keepaliveRef.current != null) {
        clearInterval(keepaliveRef.current);
        keepaliveRef.current = null;
      }
      const r0 = lockResourceRef.current; lockResourceRef.current = null;
      if (r0) sendLock("release", r0).catch(() => {});
      setFloorOwned(false);
      return;
    }

    // Start MediaRecorder and buffer chunks; we will send ONE voice note on release
    chunksRef.current = [];
    try {
      const rec = new MediaRecorder(stream, { mimeType: mime });
      mrRef.current = rec;
      rec.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data);
      };
      rec.start(200); // collect every 200ms; we will stitch later
    } catch (e) {
      console.warn("MediaRecorder start failed:", e);
    }
  }

  async function stopPTT() {
    if (!pttDownRef.current) return;
    pttDownRef.current = false;
    setPttDown(false);

    // ── metrics: accumulate talk time + session count + persist per-topic
    if (metricsRef.current.lastStart) {
      const startAt = metricsRef.current.lastStart;
      const dur = Date.now() - startAt;
      metricsRef.current.sessions++;
      metricsRef.current.talkMs += dur;
      metricsRef.current.lastStart = 0;

      // persist per-topic entry (last 10)
      const log = loadPttLog(graph, topic);
      log.push({
        at: startAt,
        dur,
        acquireMs: lastAcquireMsRef.current || undefined,
        granted: !!lastGrantedRef.current,
      });
      savePttLog(graph, topic, log);
    }

    stopMeter(); // stop the visual meter immediately

    // Stop recorder and build a single blob
    const rec = mrRef.current;
    if (rec && rec.state !== "inactive") {
      const done = new Promise<void>((resolve) => {
        rec.onstop = () => resolve();
      });
      try { rec.stop(); } catch {}
      await done;
    }
    mrRef.current = null;

    // Combine chunks into one voice note and send
    try {
      if (chunksRef.current.length) {
        const mime = pickMime();
        const blob = new Blob(chunksRef.current, { type: mime });
        chunksRef.current = [];

        const arr = await blob.arrayBuffer();
        const data_b64 = abToB64(arr);

        const vfCapsule = {
          voice_frame: {
            channel: pttChannelRef.current,
            seq: (seqRef.current++) | 0, // single note; seq still useful
            ts: Date.now(),
            mime,
            data_b64,
          },
        };

        // Optimistic local bubble + POST /tx
        await sendVoiceFrame(vfCapsule);
      }
    } catch (e) {
      console.warn("send voice note failed:", e);
    }

    // Release the floor
    if (keepaliveRef.current != null) {
      clearInterval(keepaliveRef.current);
      keepaliveRef.current = null;
    }
    const res = lockResourceRef.current;
    lockResourceRef.current = null;
    if (res) {
      try { await sendLock("release", res); } catch {}
    }
    setFloorOwned(false);
  }

  async function sendVoiceFrame(vfCapsule: any) {
    const localId = `local-voice:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
    const optimistic: NormalizedMsg = {
      id: localId,
      kind: "voice",
      ts: Date.now(),
      from: AGENT_ID,
      mime: vfCapsule.voice_frame?.mime,
      data_b64: vfCapsule.voice_frame?.data_b64,
    };

    setThread((t) => {
      const next = [...t, optimistic];
      try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
      return next;
    });

    try {
      const r = await fetch(`${base}/api/glyphnet/tx`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Agent-Token": "dev-token",
          "X-Agent-Id": AGENT_ID,
        },
        body: JSON.stringify({
          recipient: topic,
          graph,
          capsule: vfCapsule,
          meta: { trace_id: AGENT_ID, graph, t0: Date.now() }, // ← added t0 here
        }),
      });

      const j = await r.json().catch(() => ({} as any));
      if (j?.msg_id) rememberSent(j.msg_id);
    } catch (e) {
      console.warn("[sendVoiceFrame] network/error", e);
    }
  } // ← end sendVoiceFrame

  // ——— Voice Note (file attach) ———
  const attachInputRef = useRef<HTMLInputElement | null>(null);

  const [transcribeOnAttach, setTranscribeOnAttach] = useState<boolean>(() => {
    try { return localStorage.getItem("gnet:transcribeOnAttach") === "1"; } catch { return false; }
  });

  function attachVoiceFile() {
    attachInputRef.current?.click();
  }

  async function onPickVoiceFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    // allow re-pick of same file next time
    e.target.value = "";
    if (!f) return;

    const mime = f.type || mimeFromName(f.name); // fallback by extension
    const ab = await f.arrayBuffer();
    const b64 = abToB64(ab);

    // optimistic bubble (re-uses same local-voice pattern as PTT)
    const localId = `local-voice:${Date.now()}:${Math.random().toString(36).slice(2, 6)}`;
    const optimistic: NormalizedMsg = {
      id: localId,
      ts: Date.now(),
      kind: "voice",
      from: AGENT_ID,
      mime,
      data_b64: b64,
    };
    setThread((prev) => {
      const next = [...prev, optimistic];
      try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
      return next;
    });

    // send as voice_note capsule (with t0 for RTT)
    try {
      const r = await fetch(`${base}/api/glyphnet/tx`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Agent-Token": "dev-token",
          "X-Agent-Id": AGENT_ID,
        },
        body: JSON.stringify({
          recipient: topic,
          graph,
          capsule: { voice_note: { ts: Date.now(), mime, data_b64: b64 } },
          meta: { trace_id: AGENT_ID, graph, t0: Date.now() },
        }),
      });

      const j = await r.json().catch(() => ({} as any));
      if (j?.msg_id) rememberSent(j.msg_id);

      // ⬇️ Optional transcription → send as text capsule
      if (transcribeOnAttach) {
        setTranscribing(true);
        const t = await transcribeAudio(mime, b64); // expects { text, engine }
        setTranscribing(false);
        if (t?.text) {
          await fetch(`${base}/api/glyphnet/tx`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Agent-Token": "dev-token",
              "X-Agent-Id": AGENT_ID,
            },
            body: JSON.stringify({
              recipient: topic,
              graph,
              capsule: { glyphs: [t.text] },
              meta: {
                trace_id: AGENT_ID,
                graph,
                t0: Date.now(),
                transcript_of: j?.msg_id || null,
                engine: t.engine || undefined,
              },
            }),
          }).catch(() => {});
        }
      }

      // persist recents
      rememberTopic(topic, addrInput || topic, graph);
    } catch (err) {
      console.warn("[voice_note] send failed", err);
    }
  }

  // Small helper to render an initial/avatar for recents
  function initials(s: string) {
    const parts = s.trim().split(/\s+/);
    const a = (parts[0] || "").charAt(0).toUpperCase();
    const b = (parts[1] || "").charAt(0).toUpperCase();
    return (a + b) || a || "👤";
  }

  // Contacts + Recents for the left rail
  const contacts = useMemo(() => getContacts(), []);
  const recents = useMemo(() => {
    const seen = new Set<string>();
    const out: RecentItem[] = [];
    for (const r of getRecent(20)) {
      const k = `${r.topic}|${r.graph}`;
      if (seen.has(k)) continue;
      seen.add(k);
      out.push(r);
    }
    return out;
  }, []);

  // keep a local edit buffer for the topic input (already syncs from topic)
  async function applyTopicChange(next: string) {
    const raw = (next || '').trim();
    if (!raw) return;

    const kgOut = (raw.includes('@') ? raw.split('@').pop()! : graph) as string;
    const kgCanon: GraphKey = canonKG(kgOut);

    const { wa, label } = await resolveLabelToWA(base, kgCanon, raw);

    setGraph(kgCanon);           // no cast needed now
    setTopic(wa);
    setAddrInput(`${label}@${kgCanon}`);

    try {
      const sp = new URLSearchParams();
      sp.set('topic', wa);
      sp.set('kg', kgCanon);
      location.hash = '#/chat?' + sp.toString();
    } catch {}

    try {
      rememberTopic(wa, label || raw, kgCanon); // no cast needed
    } catch {}
  }

  const [showSettings, setShowSettings] = useState(false);

  // …after toggleHold / hangupCall, before `return (`
  function IceSettings() {
    const [open, setOpen] = useState(false);
    const [uri, setUri] = useState("");
    const [username, setUsername] = useState("");
    const [credential, setCredential] = useState("");

    function addTurnLocal() {
      if (!uri.trim() || !username.trim() || !credential.trim()) return;
      const next = [
        ...iceServers,
        { urls: [uri.trim()], username: username.trim(), credential: credential.trim() },
      ];
      setIceServers(next);
      try { localStorage.setItem("gnet:iceServers", JSON.stringify(next)); } catch {}
      setUri(""); setUsername(""); setCredential("");
    }

    function clearLocalOverride() {
      setIceServers(DEFAULT_ICE);
      try { localStorage.removeItem("gnet:iceServers"); } catch {}
    }

    return (
      <div style={{ marginLeft: 8, display: "inline-flex", alignItems: "center", position: "relative" }}>
        <button
          onClick={() => setOpen(v => !v)}
          title="Call settings (ICE)"
          style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}
        >
          ⚙️ Call Settings
        </button>

        {open && (
          <div
            style={{
              position: "absolute",
              right: 0,
              top: "calc(100% + 6px)",
              padding: 10,
              width: 300,
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              boxShadow: "0 6px 20px rgba(0,0,0,0.08)",
              zIndex: 20,
            }}
          >
            <div style={{ fontSize: 12, marginBottom: 6, fontWeight: 600 }}>ICE servers in use</div>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", maxHeight: 140, overflow: "auto" }}>
              {iceServers.map((s, i) => (
                <li key={i} style={{ fontSize: 12, padding: "2px 0" }}>
                  {Array.isArray(s.urls) ? s.urls.join(", ") : s.urls}
                  {s.username ? ` — ${s.username}` : ""}
                </li>
              ))}
            </ul>

            <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
              (If backend provides TURN via /api/rtc/ice, it will auto-apply.)
            </div>

            <hr style={{ margin: "8px 0", borderColor: "#eee" }} />

            <div style={{ display: "grid", gap: 6 }}>
              <input
                placeholder="turns:host:5349?transport=tcp"
                value={uri}
                onChange={(e) => setUri(e.target.value)}
                style={{ fontSize: 12, padding: 6, border: "1px solid #e5e7eb", borderRadius: 6 }}
              />
              <input
                placeholder="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{ fontSize: 12, padding: 6, border: "1px solid #e5e7eb", borderRadius: 6 }}
              />
              <input
                placeholder="credential (password/secret)"
                value={credential}
                onChange={(e) => setCredential(e.target.value)}
                style={{ fontSize: 12, padding: 6, border: "1px solid #e5e7eb", borderRadius: 6 }}
              />
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  onClick={addTurnLocal}
                  style={{ fontSize: 12, padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb" }}
                >
                  + Add TURN (local override)
                </button>
                <button
                  onClick={clearLocalOverride}
                  style={{ fontSize: 12, padding: "4px 8px", borderRadius: 6, border: "1px solid #e5e7eb" }}
                >
                  Reset to defaults
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ---- Mic button computed props (keeps JSX simple) ----
  const micDisabled = !!floorBusyBy && !floorOwned;

  const micTitle = micDisabled
    ? `Channel busy (${floorBusyBy})`
    : (floorOwned || pttDown)
      ? "Recording… release to send"
      : (micReady ? "Press and hold to talk" : "Press and hold (will ask for mic)");

  const micBg =
    (pttDown || floorOwned) ? "#dbeafe"
    : awaitingLock           ? "#e0e7ff"
    : micDisabled            ? "#fde68a"
    : "#fff";

  const micShadow =
    (pttDown || floorOwned)
      ? "0 0 0 2px #93c5fd inset, 0 0 12px rgba(59,130,246,.55)"
      : (awaitingLock ? "0 0 0 2px #a5b4fc inset" : "none");

  const micCursor = micDisabled ? "not-allowed" : "pointer";

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
              key={`${r.topic}|${r.graph}`}
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

        {/* WS reconnecting toast */}
        {reconnecting && (
          <div
            style={{
              position: "fixed",
              top: 10,
              right: 10,
              background: "#111827",
              color: "#fff",
              padding: "6px 10px",
              borderRadius: 8,
              boxShadow: "0 8px 30px rgba(0,0,0,.2)",
              fontSize: 12,
              zIndex: 50,
              opacity: 0.9,
            }}
          >
            reconnecting…
          </div>
        )}

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
          <button /* ← Back */>…</button>

          <div style={{ fontWeight: 600 }}>Chat</div>
          <div style={{ fontSize: 12, color: connected ? "#16a34a" : "#b91c1c" }}>
            {connected ? "● online" : "● offline"}
          </div>

          {/* WebRTC remote audio sink (hidden) */}
          <audio ref={remoteAudioRef} autoPlay playsInline style={{ display: "none" }} />

          {/* Call strip */}
          {callState === "ringing" && (
            <div style={{ marginLeft: 8, display: "inline-flex", gap: 6 }}>
              <span style={{ fontSize: 12 }}>📳 Incoming call…</span>
              <button onClick={acceptCall} style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}>
                Accept
              </button>
              <button onClick={declineCall} style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}>
                Decline
              </button>
            </div>
          )}

          {(callState === "connected" || callState === "connecting" || callState === "offering") && (
            <div style={{ marginLeft: 8, display: "inline-flex", gap: 6 }}>
              <span style={{ fontSize: 12 }}>
                {callState === "connected" ? "🔊 In call" : callState === "offering" ? "…calling" : "…connecting"}
              </span>
              <button onClick={toggleMute} style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}>
                {muted ? "Unmute" : "Mute"}
              </button>
              <button onClick={toggleHold} style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}>
                {onHold ? "Resume" : "Hold"}
              </button>
              <button onClick={hangupCall} style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}>
                Hang up
              </button>
            </div>
          )}

          {/* ICE settings button */}
          <IceSettings />

          {/* Floor status (keep it once, inside header) */}
          {!!floorBusyBy && !floorOwned && (
            <div
              style={{ fontSize: 12, color: "#b45309", marginLeft: 8 }}
              title="Another user is holding the floor"
            >
              channel busy: <code>{floorBusyBy}</code>
            </div>
          )}

          {/* Right side of header */}
          <div style={{ marginLeft: "auto", fontSize: 12, color: "#475569" }}>
            Identity:&nbsp;<code>{(addrInput.split("@")[0] || "user")}.tp</code>
          </div>
          <button onClick={copyInvite}>Copy Invite</button>
          <button onClick={clearThreadCache}>Reset</button>

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
                  <input
                    type="checkbox"
                    checked={audioEnabled}
                    onChange={(e) => setAudioEnabled(e.target.checked)}
                  />
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

                {/* Transcribe toggle */}
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, marginTop: 8 }}>
                  <input
                    type="checkbox"
                    checked={transcribeOnAttach}
                    onChange={(e) => {
                      const v = e.target.checked;
                      setTranscribeOnAttach(v);
                      try { localStorage.setItem("gnet:transcribeOnAttach", v ? "1" : "0"); } catch {}
                    }}
                  />
                  Transcribe on attach (send text)
                </label>

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
                  <button
                    onClick={rec2sAndSend}
                    style={{ marginTop: 8, padding: "6px 8px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer", width: "100%" }}
                    title="Record 2s and hit /api/media/transcribe"
                  >
                    🎙️ Test Transcribe (2s)
                  </button>
                </div>
              </div>
            )}
          </div>
        </div> {/* CLOSE HEADER */}

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
                  <div style={{ whiteSpace: "pre-wrap" }}>{(m as any).text}</div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <audio
                      src={playUrlForVoice(m as any)}
                      controls
                      preload="metadata"
                      muted={!audioEnabled}
                      onPlay={(e) => {
                        try { e.currentTarget.volume = audioVol; } catch {}
                      }}
                      style={{ width: 240 }}
                    />
                    <span style={{ fontSize: 12, color: "#64748b" }}>{(m as any).mime?.replace?.("audio/", "") || "audio"}</span>
                  </div>
                )}
                <div style={{ fontSize: 10, color: "#94a3b8", marginTop: 4 }}>
                  {new Date(m.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            );
          })}
        </div>

        {/* 🔊 Mic meter bar — ABOVE composer */}
        <div
          style={{
            position: "sticky",
            bottom: 64,
            zIndex: 3,
            pointerEvents: "none",
            display: "flex",
            justifyContent: "flex-end",
            paddingRight: 8,
            marginTop: 8,
          }}
        >
          <div style={{ width: 220, display: "flex", alignItems: "center", gap: 8 }}>
            <div
              title="Input level"
              style={{
                flex: "0 0 160px",
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
                  background: floorOwned ? "#60a5fa" : "#22c55e",
                  transition: "width 60ms linear, background 120ms ease",
                }}
              />
            </div>
            <span
              style={{
                minWidth: 60,
                textAlign: "right",
                fontSize: 11,
                color: micReady && micLevel < 0.02 ? "#b45309" : "transparent",
              }}
            >
              no input?
            </span>
          </div>
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
            gridTemplateColumns: "1fr 128px",
            alignItems: "end",
            gap: 8,
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            marginTop: 8,
          }}
        >
          {/* Wrap to prevent grid column collapse */}
          <div style={{ minWidth: 0 }}>
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
          </div>

          {/* Icon lane */}
          <div
            style={{
              minWidth: 128,
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "flex-end",
              gap: 8,
            }}
          >
            {/* 🎵 quick-pick voice note */}
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,.webm,.ogg,.mp3,.m4a,.wav,.aac,.flac"
              style={{ display: "none" }}
              onChange={(e) => {
                const f = e.currentTarget.files?.[0];
                if (f) sendVoiceNoteFile(f);
                e.currentTarget.value = ""; // allow re-pick of same file
              }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              title="Attach voice note"
              style={{
                width: 36, height: 36, borderRadius: 999,
                border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer",
              }}
            >
              🎵
            </button>
            {/* 📞 call (start outbound) */}
            <button
              onClick={startCall}
              title="Start call"
              style={{
                width: 36, height: 36, borderRadius: 999,
                border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer",
              }}
            >
              📞
            </button>
            {/* 📎 audio attach (separate ref) */}
            <button
              onClick={attachVoiceFile}
              title="Attach audio file"
              style={{
                width: 36,
                height: 36,
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                background: "#fff",
                cursor: "pointer",
              }}
            >
              📎
            </button>
            <input
              ref={attachInputRef}
              type="file"
              accept="audio/*,.webm,.ogg,.mp3,.m4a,.wav,.aac,.flac"
              onChange={onPickVoiceFile}
              style={{ display: "none" }}
            />

            {/* 🎙 PTT */}
            <button
              disabled={micDisabled}
              onPointerDown={startPTT}
              onPointerUp={stopPTT}
              onPointerCancel={stopPTT}
              onPointerLeave={stopPTT}
              title={micTitle}
              aria-pressed={pttDown || floorOwned}
              style={{
                width: 36,
                height: 36,
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                background: micBg,
                boxShadow: micShadow,
                transition: "box-shadow 120ms ease, background 120ms ease",
                cursor: micCursor,
              }}
            >
              {awaitingLock ? "⏳" : "🎙"}
            </button>

            {/* ➤ send */}
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
          </div>
        </div>

        <div style={{ marginTop: 6, alignSelf: "flex-end", fontSize: 11, color: "#94a3b8" }}>
          {(() => {
            const s = metricsRef.current;
            const recv = lossRef.current.recv || 0;
            const lost = lossRef.current.lost || 0;
            const total = recv + lost;
            const lossPct = total ? Math.round((lost / total) * 100) : 0;
            const rtt = lastRttRef.current || 0;
            return `${s.sessions} PTT • talk ${Math.round(s.talkMs/1000)}s • last lock ${s.lastAcquireMs}ms • loss ${lossPct}% (${lost}/${total}) • rtt ${rtt}ms`;
          })()}
        </div>

        {/* ── PTT summary panel (last 10) ───────────────────────────── */}
        {(() => {
          const log = loadPttLog(graph, topic);
          if (!log?.length) return null;

          const totalTalkMs = log.reduce((acc, s) => acc + (s.dur || 0), 0);
          const acqVals = log.map(s => s.acquireMs).filter((v): v is number => typeof v === "number");
          const avgAcquire = acqVals.length ? Math.round(acqVals.reduce((a, b) => a + b, 0) / acqVals.length) : 0;
          const grants = log.filter(s => s.granted).length;
          const denies = log.length - grants;

          return (
            <div
              style={{
                marginTop: 8,
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                background: "#fff",
                padding: 8,
                fontSize: 11,
                color: "#475569",
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 6 }}>
                PTT sessions (last {log.length})
              </div>

              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 6 }}>
                <span>Total talk: <strong>{Math.round(totalTalkMs / 1000)}s</strong></span>
                <span>Avg acquire: <strong>{avgAcquire}ms</strong></span>
                <span>Grants/Denies: <strong>{grants}</strong>/<strong>{denies}</strong></span>
              </div>

              <div style={{ maxHeight: 140, overflow: "auto", borderTop: "1px dashed #e5e7eb", paddingTop: 6 }}>
                {log.slice().reverse().map((s, i) => (
                  <div key={s.at + ":" + i} style={{ display: "grid", gridTemplateColumns: "1fr auto auto auto", gap: 8, alignItems: "baseline", padding: "2px 0" }}>
                    <div style={{ color: "#64748b" }}>
                      {new Date(s.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </div>
                    <div title="duration">⏱ {Math.round((s.dur || 0) / 1000)}s</div>
                    <div title="time to grant">{typeof s.acquireMs === "number" ? `⚡ ${s.acquireMs}ms` : "⚡ —"}</div>
                    <div title="granted?">{s.granted ? "✅ granted" : "❌ denied"}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })()}
      </div>
    </div>  
  );
};