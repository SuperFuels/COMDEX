// ──────────────────────────────────────────────────────────────
// src/routes/ChatThread.tsx — TOP SECTION (replace through normalizeIncoming)
// ─────────────────────────────────────────────────────────────-

import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import useGlyphnet from "@/hooks/useGlyphnet";
import {
  getRecent,
  rememberTopic,
  rememberLabel,
  resolveHumanAddress,
  getContacts,
} from "@/lib/addressBook";
import type { RecentItem } from "@/lib/addressBook";
import { canonKG, resolveLabelToWA } from "@/utils/nameService";
import type { GraphKey } from "@/utils/nameService";
import { makePeer, DEFAULT_ICE } from "@/utils/webrtc";
import { Telemetry } from "@/utils/telemetry";
import { resolveApiBase } from "@/utils/base";
import { importAesKey, attachSenderE2EE, attachReceiverE2EE } from "@/utils/webrtc_e2ee";
import TransportPicker from "@/components/TransportPicker";
import { KG_API_BASE } from "@/utils/kgApiBase";
// ⚠️ If WS_ID is unused in this file, remove the next line to avoid noUnusedLocals errors.

import {
  emitTextToKG,
  emitVoiceToKG,
  emitPttSession,
  emitFloorLock,
  emitCallState,
  emitTranscriptPosted,
} from "@/lib/kg_emit";

import type {
  SignalCapsule,
  VoiceOffer,
  VoiceAnswer,
  IceCapsule as VoiceIce,
  VoiceCancel,
  VoiceReject,
  VoiceEnd,
  VoiceCaps,
} from "@/utils/callTypes";
import {
  postTx,
  transportBase,
  onRadioHealth,
  getTransportMode,
  setTransportMode,
} from "@/utils/transport";
import type { TransportMode } from "@/utils/transport";

// ──────────────────────────────────────────────────────────────
// Owner / environment
// ──────────────────────────────────────────────────────────────

function getOwnerWa(): string {
  try {
    const u = (window as any).__currentUser;
    if (u?.wa) return u.wa;
  } catch {}
  const fromLS = localStorage.getItem("gnet:ownerWa");
  return fromLS || "dev@local";
}

const IP_BASE_DEFAULT = resolveApiBase();
const OWNER_WA = getOwnerWa();


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

// ──────────────────────────────────────────────────────────────
// Packed-signaling helpers (import only; NO re-exports)
// Keeping these as locals avoids Vite Fast-Refresh export churn.
// ─────────────────────────────────────────────────────────────-
import {
  SIG_TAG,
  packSig as _packSig,
  unpackSig as _unpackSig,
} from "@/utils/sigpack";

// Local aliases used in this module
const packSig = _packSig;
const unpackSig = (glyph: string): Partial<VoiceCaps> | null => {
  const v: any = _unpackSig(glyph);
  if (!v) return null;
  const { voice_offer, voice_answer, ice, voice_cancel, voice_reject, voice_end } = v;
  if (voice_offer || voice_answer || ice || voice_cancel || voice_reject || voice_end) {
    return { voice_offer, voice_answer, ice, voice_cancel, voice_reject, voice_end };
  }
  return null;
};

// DevTools helpers
;(window as any).__packSig = packSig;
;(window as any).__unpackSig = unpackSig;

// ──────────────────────────────────────────────────────────────
// Utils
// ─────────────────────────────────────────────────────────────-

// Base64 helper (used for voice notes)
function abToB64(buf: ArrayBuffer) {
  let bin = "";
  const bytes = new Uint8Array(buf);
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

function b64ToBlob(b64: string, mime: string) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

// De-dupe helpers
function hashStr(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) { h = ((h << 5) - h) + s.charCodeAt(i); h |= 0; }
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
  | { id: string; ts: number; kind: "text";  from?: string; to?: string; text: string }
  | { id: string; ts: number; kind: "voice"; from?: string; to?: string; mime: string; data_b64: string; durMs?: number };

// ──────────────────────────────────────────────────────────────
// Normalize an incoming event (raw OR WS { type:'glyphnet_capsule', envelope })
// ─────────────────────────────────────────────────────────────-
// Normalize an incoming event (handles raw + WS "glyphnet_capsule" wrapper)
function normalizeIncoming(ev: any): NormalizedMsg | null {
  // unwrap WS wrapper like: { type:"glyphnet_capsule", envelope:{...} }
  let evt = ev;
  if (evt?.type === "glyphnet_capsule" && evt?.envelope) evt = evt.envelope;

  // Prefer an outer "envelope" if present, then the capsule, then the raw evt
  const envelope: any = evt?.envelope ?? evt ?? {};
  const cap: any = evt?.capsule ?? envelope?.capsule ?? evt ?? {};
  
  // Timestamp / ids
  const ts = Math.round(
    Number(
      (envelope?.ts as number) ??
      (cap?.ts as number) ??
      (evt?.ts as number) ??
      Date.now()
    )
  );

  const evId =
    evt?.id ??
    evt?.msg_id ??
    envelope?.id ??
    envelope?.msg_id ??
    cap?.id ??
    null;

  // Meta
  const from =
    evt?.from ??
    evt?.meta?.from ??
    envelope?.meta?.from ??
    envelope?.meta?.trace_id ??
    cap?.meta?.from ??
    undefined;

  const to =
    evt?.to ??
    evt?.meta?.to ??
    envelope?.meta?.to ??
    cap?.meta?.to ??
    undefined;

  // ── WS fanout: chat_message (instant path)
  {
    const cm =
      cap?.chat_message ??
      envelope?.capsule?.chat_message ??
      evt?.chat_message;

    if (cm && typeof cm.text === "string" && cm.text.trim()) {
      const at = Math.round(Number(cm.at ?? ts));
      const salt =
        typeof (window as any)?.hash8 === "function"
          ? (window as any).hash8(cm.text)
          : Math.random().toString(36).slice(2, 8);
      const id = evId
        ? `txt:${evId}`
        : `chat:${cm.from || from || "peer"}:${at}:${salt}`;
      return {
        id,
        ts: at,
        kind: "text",
        text: cm.text,
        from: cm.from ?? from,
        to,
      };
    }
  }

  // ── Voice frame (PTT single-blob variant)
  {
    const vf = cap?.voice_frame ?? envelope?.capsule?.voice_frame ?? ev?.voice_frame;
    if (vf && (vf.data_b64 || vf.bytes_b64 || vf.b64)) {
      const idBase = evId || `${vf.channel ?? "ch"}:${vf.seq ?? 0}:${vf.ts ?? ts}`;
      const id = `vf:${idBase}`;
      const mime = vf.mime || vf.codec || "audio/webm";
      const data_b64 = vf.data_b64 || vf.bytes_b64 || vf.b64 || "";
      return {
        id,
        ts: vf.ts ? Math.round(vf.ts) : ts,
        kind: "voice",
        from,
        to,
        mime,
        data_b64,
      };
    }
  }

  // ── Voice note (file-attach path)
  {
    const vn = cap?.voice_note ?? envelope?.capsule?.voice_note ?? ev?.voice_note;
    if (vn && (vn.data_b64 || vn.bytes_b64 || vn.b64)) {
      const idBase = evId || `${vn.ts ?? ts}:${vn.mime ?? "audio/webm"}`;
      const id = `vn:${idBase}`;
      const mime = vn.mime || vn.codec || "audio/webm";
      const data_b64 = vn.data_b64 || vn.bytes_b64 || vn.b64 || "";
      return {
        id,
        ts: vn.ts ? Math.round(vn.ts) : ts,
        kind: "voice",
        from,
        to,
        mime,
        data_b64,
      };
    }
  }

  // ── Text (glyphs / glyph_stream) with packed signaling guard
  const glyphs: string[] | undefined =
    Array.isArray(cap?.glyphs)
      ? cap.glyphs
      : Array.isArray(envelope?.capsule?.glyphs)
      ? envelope.capsule.glyphs
      : undefined;

  const glyphStream: string[] | undefined =
    Array.isArray(cap?.glyph_stream)
      ? cap.glyph_stream
      : Array.isArray(envelope?.capsule?.glyph_stream)
      ? envelope.capsule.glyph_stream
      : undefined;

  // detect packed signaling embedded as a glyph
  const maybePacked =
    (glyphs && glyphs.find((g: any) => typeof g === "string" && g.includes(SIG_TAG))) ??
    (glyphStream && glyphStream.find((g: any) => typeof g === "string" && g.includes(SIG_TAG)));

  if (maybePacked) {
    const sig = unpackSig(maybePacked);
    if (
      sig &&
      (sig.voice_offer || sig.voice_answer || sig.ice || sig.voice_cancel || sig.voice_reject || sig.voice_end)
    ) {
      return null; // drop signaling disguised as glyph
    }
  }

  // flatten to a single text string if present
  const txt =
    (glyphs ? glyphs.join("") : undefined) ??
    (glyphStream ? glyphStream.join("") : undefined) ??
    (typeof envelope?.text === "string" ? envelope.text : undefined) ??
    (typeof ev?.text === "string" ? ev.text : undefined) ??
    (typeof cap?.text === "string" ? cap.text : undefined);

  // guard against packed signaling in plain text too
  if (typeof txt === "string" && txt.includes(SIG_TAG)) {
    const sig = unpackSig(txt);
    if (
      sig &&
      (sig.voice_offer || sig.voice_answer || sig.ice || sig.voice_cancel || sig.voice_reject || sig.voice_end)
    ) {
      return null;
    }
  }

  if (typeof txt === "string" && txt.trim().length) {
    const salt =
      typeof (window as any)?.hash8 === "function"
        ? (window as any).hash8(txt)
        : Math.random().toString(36).slice(2, 8);
    const id = evId ? `txt:${evId}` : `txt:${ts}:${salt}`;
    return { id, ts, kind: "text", from, to, text: txt };
  }

  return null;
}

// ──────────────────────────────────────────────────────────────
export default function ChatThread({
  defaultTopic,
  defaultGraph,
}: {
  defaultTopic?: string;
  defaultGraph?: GraphKey;
}) {
  // ICE servers state (inside component)
  const [iceServers, setIceServers] = useState<RTCIceServer[]>(() => {
    try {
      const raw = localStorage.getItem("gnet:iceServers");
      const parsed = raw ? (JSON.parse(raw) as RTCIceServer[]) : null;
      return Array.isArray(parsed) && parsed.length ? parsed : DEFAULT_ICE;
    } catch {
      return DEFAULT_ICE;
    }
  });

  // Per-tab agent id (used in lock ownership + X-Agent-Id)
  const AGENT_ID = useMemo(() => {
    let id = sessionStorage.getItem("gnet:agentId");
    if (!id) {
      id = "chat-thread:" + Math.random().toString(36).slice(2, 10);
      try { sessionStorage.setItem("gnet:agentId", id); } catch {}
    }
    return id;
  }, []);

  // Dev-only: tolerate builds without the old WS_ID export.
  // This is ONLY for logging and has no effect on routing/locks.
  const WS_ID = useMemo<string>(() => {
    try {
      return (
        (window as any).__gnet_conn_id ??
        (window as any).__gnet_ws_id ??
        sessionStorage.getItem("gnet:lastConnId") ??
        "n/a"
      );
    } catch {
      return "n/a";
    }
  }, []);

  // Topic: prefer #/chat?topic=, else prop, else default
  const [topic, setTopic] = useState<string>(() => {
    const h = window.location.hash || "";
    const qs = h.includes("?") ? h.slice(h.indexOf("?") + 1) : "";
    const sp = new URLSearchParams(qs);
    return sp.get("topic") || defaultTopic || "ucs://local/ucs_hub";
  });

  // Canonicalize topic to a stable WA (same string in every tab)
  const topicWa = useMemo(() => {
    try {
      const r = resolveHumanAddress(topic);
      return (typeof r === "string" && r) ? r : (topic || "");
    } catch {
      return topic || "";
    }
  }, [topic]);

  // Reflect canonical back into state only if user typed a WA-like string
  useEffect(() => {
    if (!topicWa || topicWa === topic) return;
    if (/^ucs:\/\//i.test(topic)) setTopic(topicWa);
  }, [topicWa]);

  // ──────────────────────────────────────────────────────────────
  // Graph / transport / sockets / PTT scaffolding
  // ──────────────────────────────────────────────────────────────

  const [graph, setGraph] = useState<GraphKey>(() => {
    const h = window.location.hash || "";
    const qs = h.includes("?") ? h.slice(h.indexOf("?") + 1) : "";
    const sp = new URLSearchParams(qs);
    const kg = (sp.get("kg") || defaultGraph || "personal").toString().toLowerCase();
    return kg === "work" ? "work" : "personal";
  });

  // Temporary seeded contacts (replace with real data later)
  const contacts = [
    { name: "Dave Ross",    wa: "ucs://wave.tp/dave@personal",  kg: "personal", initials: "DR" },
    { name: "Alice Nguyen", wa: "ucs://wave.tp/alice@work",     kg: "work",     initials: "AN" },
    { name: "Nia Patel",    wa: "ucs://wave.tp/nia@personal",   kg: "personal", initials: "NP" },
  ];

  // Use canonical topic for comparisons so both tabs match exactly
  const isActive = (wa: string) => (topicWa || "").toLowerCase() === wa.toLowerCase();

  // ── Telemetry (RF/IP send success/error counters) ─────────────
  const [tele, setTele] = useState(Telemetry.snap());
  useEffect(() => {
    const id = window.setInterval(() => setTele(Telemetry.snap()), 1500);
    return () => clearInterval(id);
  }, []);

  const resetTelemetry = useCallback(() => {
    try { Telemetry.reset(); } catch {}
    setTele(Telemetry.snap()); // refresh UI immediately
  }, []);

  // Radio-node health → drives base selection
  const [radioOk, setRadioOk] = useState(false);
  const [lastHealthAt, setLastHealthAt] = useState<number>(Date.now());

  useEffect(() => {
    // onRadioHealth returns an unsubscribe in our impl
    return onRadioHealth(ok => {
      setRadioOk(ok);
      setLastHealthAt(Date.now());
    });
  }, []);

  // Policy-aware base (auto-chooses radio-node vs cloud)
  // NOTE: we pass radioOk to recompute when status flips.
  const base = useMemo(() => transportBase(IP_BASE_DEFAULT), [radioOk]);

  // Pure cloud base (only use if you must force cloud)
  const ipBase = IP_BASE_DEFAULT;

  // ✅ Now call the hook (AFTER topic & graph exist)
  // IMPORTANT: use canonical topicWa so both tabs subscribe to the same exact string.
  const { connected, messages, reconnecting } = useGlyphnet(topicWa, graph);

    // Thread state is namespaced by graph + canonical topic
  const storageKey = useMemo(() => `gnet:thread:${graph}:${topicWa}`, [graph, topicWa]);
  const [thread, setThread] = useState<NormalizedMsg[]>([]);
  const seenRef = useRef<Set<string>>(new Set());
  const seenSigRef = useRef<Set<string>>(new Set());
  const processedCapsRef = useRef<Set<string>>(new Set());
  
  // TEMP: direct WS subscriber for immediate fanout (ephemeral id so echo collapses it)
  useEffect(() => {
    if (!topicWa) return;

    const wsUrl =
      `${location.origin.replace(/^http/, "ws")}` +
      `/ws/glyphnet?topic=${encodeURIComponent(topicWa)}&kg=${graph}&token=dev-token`;

    const ws = new WebSocket(wsUrl);

    const onMessage = (e: MessageEvent) => {
      let frame: any = e.data;
      try { frame = JSON.parse(frame); } catch {}

      const env: any = frame?.envelope ?? frame ?? {};
      const cap: any = env?.capsule ?? frame?.capsule ?? {};

      // Fanout chat → ephemeral local:* id
      const cm = cap?.chat_message ?? env?.capsule?.chat_message ?? frame?.chat_message;
      if (cm && typeof cm.text === "string" && cm.text.trim()) {
        const at = Math.round(Number(cm.at ?? Date.now()));
        const text = cm.text.trim();
        const salt = (window as any)?.hash8 ? (window as any).hash8(text) : Math.random().toString(36).slice(2, 6);
        const localId = `local:fanout:${at}:${salt}`;

        setThread(prev => {
          // if we already have a canonical near this time/text, skip
          const hasCanonical = prev.some(m =>
            m?.kind === "text" &&
            !String(m.id).startsWith("local:") &&
            (m as any).text === text &&
            Math.abs((m.ts || 0) - at) <= 10000
          );
          if (hasCanonical) return prev;

          // avoid duplicate ephemerals
          const hasEphemeral = prev.some(m =>
            m?.kind === "text" &&
            String(m.id).startsWith("local:") &&
            (m as any).text === text &&
            Math.abs((m.ts || 0) - at) <= 2000
          );
          if (hasEphemeral) return prev;

          const next = [...prev, { id: localId, ts: at, kind: "text", from: cm.from, text } as NormalizedMsg]
            .sort((a, b) => (a.ts || 0) - (b.ts || 0));
          try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
          // do NOT add to seenSigRef — let the persisted echo replace it
          return next;
        });
        return;
      }

      // Non-chat frames (e.g., glyph echo / voice) → normal path
      const nm = normalizeIncoming(frame);
      if (!nm) return;

      const sigKey =
        nm.kind === "text"
          ? `txt|${(nm as any).text}|${Math.floor((nm.ts || 0) / 3000)}`
          : `vf|${(nm as any).mime}|${fpB64((nm as any).data_b64)}|${Math.floor((nm.ts || 0) / 3000)}`;

      setThread(prev => {
        let next = [...prev];

        // if this is the canonical echo for an earlier ephemeral, upgrade it
        if (nm.kind === "text") {
          const i = next.findIndex(m =>
            m?.kind === "text" &&
            String(m.id).startsWith("local:") &&
            (m as any).text === (nm as any).text &&
            Math.abs((m.ts || 0) - (nm.ts || 0)) <= 10000
          );
          if (i !== -1) {
            next[i] = nm;
            const dupIdx = next.findIndex((m, idx) => idx !== i && m.id === nm.id);
            if (dupIdx !== -1) next.splice(dupIdx, 1);
            next.sort((a, b) => (a.ts || 0) - (b.ts || 0));
            try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
            seenRef.current.add(nm.id);
            seenSigRef.current.add(sigKey);
            return next;
          }
        }

        if (next.some(p => p.id === nm.id)) return prev;
        if (seenSigRef.current.has(sigKey)) return prev;

        next = [...next, nm].sort((a, b) => (a.ts || 0) - (b.ts || 0));
        try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
        seenRef.current.add(nm.id);
        seenSigRef.current.add(sigKey);
        return next;
      });
    };

    ws.addEventListener("message", onMessage);
    ws.addEventListener("error", () => {});
    ws.addEventListener("close", () => {});
    return () => { try { ws.removeEventListener("message", onMessage); ws.close(); } catch {} };
  }, [topicWa, graph, storageKey]);

  // Address input mirrors topic and stays in sync
  const [addrInput, setAddrInput] = useState<string>(topic || "");
  useEffect(() => setAddrInput(topic || ""), [topic]);

  // If a defaultTopic prop comes later, only adopt it if we currently have none
  useEffect(() => {
    if (defaultTopic) setTopic(t => t || defaultTopic);
  }, [defaultTopic]);

  // React to hash changes (keep local state in sync with URL)
  // We do not force canonicalization here; the topicWa memo + effect handles that.
  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash || "";
      const qs = h.includes("?") ? h.slice(h.indexOf("?") + 1) : "";
      const sp = new URLSearchParams(qs);
      const t = sp.get("topic");
      if (t) setTopic(t);
      const kg = (sp.get("kg") || "").toString().toLowerCase();
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

  const offerTimeoutRef = useRef<number | null>(null);

  // WebRTC: call state + refs (canonical)
  type CallState = "idle" | "ringing" | "offering" | "connecting" | "connected" | "ended";
  const [callState, setCallState] = useState<CallState>("idle");

  useEffect(() => {
    if (callState === "offering" || callState === "connecting") {
      // auto-cancel after 30s if not answered
      offerTimeoutRef.current = window.setTimeout(() => {
        cancelOutbound(); // defined later
      }, 30_000);
    }
    return () => {
      if (offerTimeoutRef.current != null) {
        clearTimeout(offerTimeoutRef.current);
        offerTimeoutRef.current = null;
      }
    };
  }, [callState]);

  // ─── Floor control (walkie-talkie) state ─────────────────────
  const lockResourceRef = useRef<string | null>(null);
  const keepaliveRef = useRef<number | null>(null);

  // PTT + meter state
  const [pttDown, setPttDown] = useState(false);
  const pttDownRef = useRef(false);
  useEffect(() => { pttDownRef.current = pttDown; }, [pttDown]);

  const [floorOwned, setFloorOwned] = useState(false);
  const [floorBusyBy, setFloorBusyBy] = useState<string | null>(null);
  const lastGrantedRef = useRef<boolean>(false);
  const lastAcquireMsRef = useRef<number>(0);

  // ⬇️ metricsRef for PTT sessions
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

  // 🔒 Handle lock events (entanglement_lock) for this topic
  useEffect(() => {
    const resource = `voice:${topicWa}`;

    // stronger de-dupe key but still uses ev (resource already normalized above)
    const makeKey = (ev: any) => {
      const idish =
        ev?.id || ev?.event_id || ev?.nonce ||
        `${ev?.resource}|${ev?.state}|${ev?.owner}|${ev?.granted ?? ""}|${Math.floor((ev?.ts ?? 0)/100)}`; // 100ms bucket
      return idish;
    };

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
          // ✅ only stop if we're actually in a PTT/recording state
          if (pttDownRef.current || (mrRef.current && mrRef.current.state !== "inactive")) {
            stopPTT();
          }
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
  }, [messages, topicWa, AGENT_ID, floorOwned]);

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

  const recent = useMemo(() => getRecent(8), []);

  // audio prefs
  const [audioVol, setAudioVol] = useState(0.9);
  const [audioEnabled, setAudioEnabled] = useState(true);
  useEffect(() => {
    if (remoteAudioRef.current) {
      remoteAudioRef.current.muted = !audioEnabled;
      try { remoteAudioRef.current.volume = audioVol; } catch {}
    }
  }, [audioEnabled, audioVol]);

  useEffect(() => {
    return () => {
      try { pcRef.current?.getSenders().forEach(s => s.track?.stop()); } catch {}
      try { pcRef.current?.close(); } catch {}
      pcRef.current = null;
      callIdRef.current = null;
    };
  }, []);

  // --- WebRTC refs (types imported at top; do NOT redeclare) ---
  const pendingOfferRef = useRef<VoiceOffer["voice_offer"] | null>(null);

  const lossRef = useRef<{ recv: number; lost: number; lastSeq: Map<string, number> }>({
    recv: 0,
    lost: 0,
    lastSeq: new Map(),
  });

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const callIdRef = useRef<string | null>(null);

  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);

  // Mute / Hold state + original mic track
  const [muted, setMuted] = useState(false);
  const [onHold, setOnHold] = useState(false);
  const origTrackRef = useRef<MediaStreamTrack | null>(null);

  // mic picker …
  const [mics, setMics] = useState<MediaDeviceInfo[]>([]);
  const [selectedMicId, setSelectedMicId] = useState<string>(() => localStorage.getItem("gnet:micDeviceId") || "");

  // Ringtones
  // Ringtones
  const ringAudio = useRef<HTMLAudioElement | null>(null);
  useEffect(() => {
    // lazily create once
    if (!ringAudio.current) {
      const el = new Audio("/ring.mp3"); // small asset in /public
      el.loop = true;
      el.preload = "auto";
      // iOS/Safari kindness
      (el as any).playsInline = true;
      try { el.setAttribute("playsinline", ""); } catch {}
      ringAudio.current = el;
    }

    const el = ringAudio.current;
    if (!el) return;

    if (callState === "ringing") {
      el.muted = false;
      try { el.currentTime = 0; } catch {}
      el.play().catch(() => {}); // autoplay may need a gesture; swallow errors
    } else {
      try { el.pause(); el.currentTime = 0; } catch {}
    }
  }, [callState]);

  const micDisabled = (!!floorBusyBy && !floorOwned) || callState !== "idle";

  // Call duration timer
  const [callSecs, setCallSecs] = useState(0);
  const callTimerRef = useRef<number | null>(null);
  const callStartedAtRef = useRef<number | null>(null);
  const callSecsRef = useRef(0);

  useEffect(() => {
    if (callState === "connected") {
      callStartedAtRef.current = Date.now();
      callSecsRef.current = 0;
      setCallSecs(0);
      callTimerRef.current = window.setInterval(() => {
        setCallSecs((s) => {
          const next = s + 1;
          callSecsRef.current = next;
          return next;
        });
      }, 1000);
    } else if (callTimerRef.current != null) {
      clearInterval(callTimerRef.current);
      callTimerRef.current = null;
    }
    return () => {
      if (callTimerRef.current != null) {
        clearInterval(callTimerRef.current);
        callTimerRef.current = null;
      }
    };
  }, [callState]);

  const [lastCandType, setLastCandType] = useState<string>("");
  // Attach onicecandidate when a pc exists; this effect runs whenever callState flips,
  // which correlates with (re)creating the RTCPeerConnection in our flow.
  useEffect(() => {
    const pc = pcRef.current;
    if (!pc) return;
    pc.onicecandidate = (e) => {
      if (e.candidate) {
        const t = /candidate:.* typ (\w+)/.exec(e.candidate.candidate)?.[1] || "";
        if (t) setLastCandType(t); // "host" | "srflx" | "relay"
        if (callIdRef.current) {
          try { sendIce(e.candidate.toJSON(), callIdRef.current).catch(() => {}); } catch {}
        }
      }
    };
  }, [callState]);

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
      // ignore (no permission or unsupported)
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
    try { localStorage.setItem("gnet:micDeviceId", id); } catch {}
  }

  function clearThreadCache() {
    try { sessionStorage.removeItem(storageKey); } catch {}
    // also wipe in-memory state so the UI reflects the clear immediately
    setThread([]);
    seenRef.current = new Set();
    seenSigRef.current = new Set();
  }

  // Invite link (use canonical topic so the other tab gets the SAME thread)
  async function copyInvite() {
    const url = `${location.origin}/#/chat?topic=${encodeURIComponent(topicWa)}&kg=${graph}`;
    try {
      await navigator.clipboard.writeText(url);
      alert("Invite link copied:\n" + url);
    } catch {
      prompt("Copy this link:", url);
    }
  }
    
  // RTT stash
  const lastRttRef = useRef<number>(0);

  // Sent-cache (ACKed ids) to avoid replays on reconnect — also by canonical topic
  const sentKey = useMemo(() => `gnet:sent:${graph}:${topicWa}`, [graph, topicWa]);
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
      const sig =
        m.kind === "text"
          ? `txt|${(m as any).text}|${Math.round((m.ts || 0) / 5000)}`
          : `vf|${m.mime}|${fpB64((m as any).data_b64)}|${Math.round((m.ts || 0) / 5000)}`;
      seenSigRef.current.add(sig);
    }
  }, [storageKey]);

// Merge incoming WS messages into this thread (de-duped), then persist
// Merge incoming WS messages into this thread (de-duped), then persist
useEffect(() => {
  if (!messages?.length) return;

  const uniqById = (arr: any[]) => {
    const keep = new Map<string, any>();
    for (const m of arr) {
      const k = String(m?.id ?? "");
      if (!k) continue;
      const prev = keep.get(k);
      if (!prev || (m.ts ?? 0) >= (prev.ts ?? 0)) keep.set(k, m);
    }
    return [...keep.values()];
  };

  const batchSeen = new Set<string>();

  setThread((prev) => {
    let next = uniqById(prev as any[]);
    let changed = next.length !== (prev as any[]).length;

    for (const evRaw of messages as any[]) {
      const ev: any  = evRaw ?? {};
      const env: any = ev?.envelope ?? ev ?? {};
      const cap: any = env?.capsule  ?? ev?.capsule ?? {};

      // 0) Drop frames we've already consumed by envelope/msg id (cross-batch)
      const frameId: string | null =
        ev?.id ?? ev?.msg_id ?? env?.id ?? env?.msg_id ?? cap?.id ?? null;
      if (frameId) {
        try {
          if (processedCapsRef.current.has(frameId)) continue;
          processedCapsRef.current.add(frameId);
        } catch {
          /* if ref not present, skip this guard */
        }
      }

      // 1) Topic guard (accept if absent; otherwise must match our canonical topic)
      try {
        const eventTopic =
          env?.topic ??
          env?.recipient ??
          cap?.resourceTopic ??
          env?.meta?.topic ??
          env?.meta?.to ??
          env?.meta?.recipient;

        if (
          eventTopic &&
          String(eventTopic).toLowerCase() !== (topicWa || "").toLowerCase()
        ) {
          continue;
        }
      } catch {}

      // 2) Ignore WS fanout chat frames; rely on persisted glyph echo
      const cm = cap?.chat_message ?? env?.capsule?.chat_message;
      if (cm && typeof cm?.text === "string") continue;

      // 3) Batch de-dupe to avoid double-processing identical shapes in one tick
      {
        const eid =
          env?.id ?? env?.msg_id ?? ev?.id ?? ev?.msg_id ??
          `${env?.ts ?? ""}|${env?.meta?.trace_id ?? ""}|${
            (Array.isArray(cap?.glyphs) && cap.glyphs.join("")) ||
            (Array.isArray(cap?.glyph_stream) && cap.glyph_stream.join("")) ||
            cap?.voice_note?.ts ||
            cap?.voice_frame?.seq ||
            ""
          }`;
        const k = String(eid || "");
        if (k && batchSeen.has(k)) continue;
        if (k) batchSeen.add(k);
      }

      // 4) RTT + PTT accounting (unchanged)
      if (typeof env?.meta?.t0 === "number") {
        lastRttRef.current = Date.now() - Number(env.meta.t0);
      }
      {
        const vf = cap?.voice_frame;
        if (vf && typeof vf.seq === "number" && typeof vf.channel === "string") {
          const key = `${topicWa}|${vf.channel}`;
          const prevSeq = lossRef.current.lastSeq.get(key);
          if (typeof prevSeq === "number") {
            if (vf.seq > prevSeq + 1) lossRef.current.lost += (vf.seq - prevSeq - 1);
            if (vf.seq > prevSeq) {
              lossRef.current.recv += 1;
              lossRef.current.lastSeq.set(key, vf.seq);
            }
          } else {
            lossRef.current.lastSeq.set(key, vf.seq);
            lossRef.current.recv += 1;
          }
        }
      }

      // 5) Intercept signaling (never render)
      {
        let sig: any = cap;

        const hasNative =
          !!sig?.voice_offer || !!sig?.voice_answer || !!sig?.ice ||
          !!sig?.voice_cancel || !!sig?.voice_reject || !!sig?.voice_end;

        if (!hasNative) {
          const gs: string[] | undefined =
            (Array.isArray(cap?.glyphs) ? cap.glyphs : undefined) ??
            (Array.isArray(cap?.glyph_stream) ? cap.glyph_stream : undefined) ??
            (Array.isArray(ev?.glyphs) ? ev.glyphs : undefined) ??
            (Array.isArray(ev?.glyph_stream) ? ev.glyph_stream : undefined) ??
            (Array.isArray(env?.capsule?.glyphs) ? env.capsule.glyphs : undefined) ??
            (Array.isArray(env?.capsule?.glyph_stream) ? env.capsule.glyph_stream : undefined);

          if (gs && gs.length) {
            for (const g of gs) {
              const m = unpackSig(g);
              if (
                m &&
                (m.voice_offer || m.voice_answer || m.ice ||
                 m.voice_cancel || m.voice_reject || m.voice_end)
              ) { sig = m; break; }
            }
          }
        }

        if (
          sig?.voice_offer || sig?.voice_answer || sig?.ice ||
          sig?.voice_cancel || sig?.voice_reject || sig?.voice_end
        ) {
          // … existing signaling handling lives elsewhere …
          continue; // do not render signaling
        }
      }

      // 6) Normalize content we actually render
      const nm = normalizeIncoming(ev);
      if (!nm) continue;

      // 7) Collapse optimistic by meta.local_id first (authoritative)
      //    This MUST happen before any id/signature de-dupe so the optimistic bubble
      //    is reliably replaced by the server echo even if another path already inserted it.
      {
        const localId: string | undefined =
          env?.meta?.local_id ?? ev?.meta?.local_id ?? cap?.local_id ?? undefined;

        if (localId && nm.kind === "text") {
          const i = next.findIndex((m: any) => String(m.id) === String(localId));
          if (i !== -1) {
            const canonicalId = frameId ? `txt:${frameId}` : nm.id;
            next[i] = {
              ...nm,
              id: canonicalId,
              from: (next[i] as any).from || (nm as any).from || AGENT_ID,
            };

            // If a separate entry with the same canonical id already exists (e.g. from a temp WS insert),
            // drop it now to avoid a visible double.
            const dupIdx = next.findIndex((m: any, idx: number) => idx !== i && m.id === canonicalId);
            if (dupIdx !== -1) next.splice(dupIdx, 1);

            seenRef.current.add(canonicalId);
            changed = true;
            // we intentionally DO NOT add sigKey yet (we haven't computed it); uniqById will protect us later.
            continue;
          }
        }
      }

      // 8) Fallback collapse by text/time proximity (10s window) for optimistic local:* ids
      if (nm.kind === "text") {
        let i = -1;
        for (let k = next.length - 1; k >= 0; k--) {
          const m = next[k];
          if (m?.kind !== "text" || !String(m.id).startsWith("local:")) continue;
          const sameText = (m as any).text === (nm as any).text;
          const nearTime  = Math.abs((nm.ts || 0) - (m.ts || 0)) <= 10000;
          if (sameText || nearTime) { i = k; break; }
        }
        if (i !== -1) {
          const canonicalId = frameId ? `txt:${frameId}` : nm.id;
          next[i] = { ...nm, id: canonicalId, from: (next[i] as any).from || (nm as any).from || AGENT_ID };

          // Remove any other duplicate with the same canonical id
          const dupIdx = next.findIndex((m: any, idx: number) => idx !== i && m.id === canonicalId);
          if (dupIdx !== -1) next.splice(dupIdx, 1);

          seenRef.current.add(canonicalId);
          changed = true;
          continue;
        }
      }

      // 9) Server echo of a voice note → replace optimistic local-voice
      if (nm.kind === "voice") {
        const kNow = `${(nm as any).mime}|${fpB64((nm as any).data_b64)}`;
        const i = next.findIndex(
          (m: any) =>
            m.kind === "voice" &&
            String(m.id).startsWith("local-voice:") &&
            `${(m as any).mime}|${fpB64((m as any).data_b64)}` === kNow
        );
        if (i !== -1) {
          next[i] = { ...nm, from: (next[i] as any).from || (nm as any).from };
          seenRef.current.add(nm.id);
          changed = true;
          continue;
        }
      }

      // 10) Strong id de-dupe (replace if newer ts)
      //     (Placed AFTER collapses so it doesn't short-circuit them.)
      {
        const idx = next.findIndex((m: any) => m.id === nm.id);
        if (idx !== -1) {
          if ((nm.ts ?? 0) >= (next[idx].ts ?? 0)) next[idx] = nm;
          changed = true;
          continue;
        }
      }

      // 11) Soft signature de-dupe (guards slight id/ts differences)
      const sigKey =
        nm.kind === "text"
          ? `txt|${(nm as any).text}|${Math.floor((nm.ts || 0) / 3000)}`
          : `vf|${(nm as any).mime}|${fpB64((nm as any).data_b64)}|${Math.floor((nm.ts || 0) / 3000)}`;
      if (seenSigRef.current.has(sigKey)) { 
        seenRef.current.add(nm.id); 
        continue; 
      }

      // 12) Brand-new message
      next.push(nm);

      // mark ids we might see under alternate forms
      const idGuess = nm.id || (frameId ? `txt:${frameId}` : "");
      if (idGuess) seenRef.current.add(idGuess);
      if (frameId) seenRef.current.add(`txt:${frameId}`);
      seenSigRef.current.add(sigKey);
      changed = true;
    } // ← END for (const evRaw of messages)

    if (!changed) return prev;

    next = uniqById(next).sort((a: any, b: any) => (a.ts || 0) - (b.ts || 0));
    try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
    return next as any;
  }); // ← END setThread
}, [messages, storageKey, topicWa, graph, AGENT_ID, callState, lastCandType]); // ← END useEffect

// ──────────────────────────────────────────────────────────────
// Composer + PTT state …
const [text, setText] = useState("");
const [busy, setBusy] = useState(false);
const mrRef = useRef<MediaRecorder | null>(null);
const chunksRef = useRef<BlobPart[]>([]);
const streamRef = useRef<MediaStream | null>(null);

// If you don't have a UI toggle yet, keep transcription off by default.
// (Prevents ReferenceErrors when sending voice notes.)

useEffect(() => { callSecsRef.current = callSecs; }, [callSecs]);

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
  // scroll after React paints the new bubble
  requestAnimationFrame(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  });
}, [thread.length]);

// Initial server history load per topic/graph (use CANONICAL topicWa)
useEffect(() => {
  let cancelled = false;
  if (!topicWa) return;

  (async () => {
    try {
      const r = await fetch(
        `${base}/api/glyphnet/thread?topic=${encodeURIComponent(topicWa)}&kg=${graph}&limit=200`
      );
      if (!r.ok) throw new Error(`thread fetch ${r.status}`);
      const j = await r.json();
      const evs: any[] = j.events || [];

      // Seed loss metrics from the fetched history (keyed by canonical topic)
      (function seedLossFromServer() {
        const L = lossRef.current;
        L.recv = 0; L.lost = 0; L.lastSeq = new Map();
        for (const ev of evs) {
          const vf = ev?.capsule?.voice_frame;
          if (!vf || typeof vf.seq !== "number" || typeof vf.channel !== "string") continue;
          const key = `${topicWa}|${vf.channel}`;
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
}, [base, topicWa, graph, storageKey]);

useEffect(() => {
  // reset loss stats when switching threads
  lossRef.current = { recv: 0, lost: 0, lastSeq: new Map() };
}, [topicWa, graph]);

// Send text (journals to KG, WS fanout, legacy glyphs) + optimistic bubble + sent-cache
// Send text (journal → KG, persistent glyphs echo only) + optimistic bubble + sent-cache
async function sendText() {
  const msg = text.trim();
  if (!msg || busy) return;

  setBusy(true);

  try {
    const now = Date.now();

    // deterministic optimistic id for this send
    const localId = `local:${AGENT_ID}:${now}:${Math.random().toString(36).slice(2,6)}`;

    // conn-aware headers + meta that the server will echo back (lets us collapse optimistic)
    const headers = withConnHeaders({
      "Content-Type": "application/json",
      "X-Agent-Token": "dev-token",
      "X-Agent-Id": AGENT_ID,
    });
    const meta = withConnMeta({ trace_id: AGENT_ID, graph, t0: now, local_id: localId });

    // 0) Optimistic append (sender sees one bubble immediately; guard double-clicks)
    setThread(prev => {
      if (prev.some(m => m.id === localId)) return prev;
      const next = [
        ...prev,
        { id: localId, ts: now, kind: "text", text: msg, from: AGENT_ID } as NormalizedMsg,
      ];
      try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
      return next;
    });

    // 1) Journal to KG (fire-and-forget) — canonical topic
    emitTextToKG({
      apiBase: KG_API_BASE,
      kg: graph,
      ownerWa: OWNER_WA,
      topicWa: topicWa,
      text: msg,
      ts: now,
      agentId: AGENT_ID,
    }).catch(() => {});

    // 2) 🔇 WS fanout is DISABLED to avoid duplicate inserts in UIs.
    //    If you ever want instant WS fanout again, flip FANOUT to true,
    //    and ensure your merge effect skips cap.chat_message frames.
    // 2) WS fanout so peers see it immediately (persisted echo will collapse it)
    const FANOUT = true;
    try {
      await postTx(
        base,
        { recipient: topicWa, graph, capsule: { chat_message: { text: msg, from: AGENT_ID, at: now } }, meta },
        headers
      );
    } catch {}

    // 3) Authoritative persistent path — send glyphs (server persists, echoes with msg_id)
    const res = await postTx(
      base,
      { recipient: topicWa, graph, capsule: { glyphs: [msg] }, meta },
      headers
    );

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      console.warn("[sendText] HTTP", res.status, body);
    } else {
      const payload = await res.json().catch(() => ({} as any));
      if (payload?.msg_id) rememberSent(payload.msg_id);
    }

    rememberTopic(topicWa, addrInput || topic, graph);
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

    // 🔹 Journal the voice note to the KG (non-blocking) — canonical topic
    emitVoiceToKG({
      apiBase: KG_API_BASE,
      kg: graph,
      ownerWa: OWNER_WA,
      topicWa: topicWa,
      mime,
      data_b64,
      durMs: undefined,
      ts: Date.now(),
      agentId: AGENT_ID,
    }).catch(() => {});

    // Optimistic bubble (server echo will replace via msg_id)
    const localId = `local-voice:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
    const optimistic: NormalizedMsg = {
      id: localId,
      kind: "voice",
      ts: Date.now(),
      from: AGENT_ID,
      mime,
      data_b64,
    };
    setThread((t) => {
      const next = [...t, optimistic];
      try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
      return next;
    });

    // Conn-aware headers + meta (adds X-Conn-Id + meta.conn_id)
    const headers = withConnHeaders({
      "Content-Type": "application/json",
      "X-Agent-Token": "dev-token",
      "X-Agent-Id": AGENT_ID,
    });
    const meta = withConnMeta({ trace_id: AGENT_ID, graph, t0: Date.now() });

    // POST voice_note (policy-aware: Auto / Radio-only / IP-only) — canonical recipient
    const r = await postTx(
      base,
      {
        recipient: topicWa,
        graph,
        capsule: { voice_note: { ts: Date.now(), mime, data_b64 } },
        meta,
      },
      headers
    );

    // RF profile guardrail
    if (r.status === 413) {
      const j = await r.json().catch(() => ({} as any));
      alert(
        j?.error === "too large"
          ? `Voice note too large for RF path (${j.size} > ${j.max} bytes). Try a shorter clip or switch to IP-only.`
          : "Voice note rejected: too large for current RF profile."
      );
      return;
    }

    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      console.warn("[sendVoiceNoteFile] HTTP", r.status, txt);
      return;
    }

    const j = await r.json().catch(() => ({} as any));
    if (j?.msg_id) {
      rememberSent(j.msg_id);
      // swap optimistic id so acks correlate
      setThread((prev) =>
        prev.map((m) => (m.id === localId ? { ...m, id: j.msg_id } : m))
      );
    }

    // ⬇️ Optional transcription → send glyphs:[text] and journal to KG
    if (transcribeOnAttach) {
      setTranscribing(true);
      const t = await transcribeAudio(mime, data_b64); // expects { text, engine }
      setTranscribing(false);

      if (t?.text) {
        try {
          await postTx(
            base,
            {
              recipient: topicWa,
              graph,
              capsule: { glyphs: [t.text] },
              meta: withConnMeta({
                trace_id: AGENT_ID,
                graph,
                t0: Date.now(),
                transcript_of: j?.msg_id || null,
                engine: t.engine || undefined,
              }),
            },
            headers
          );

          // Journal transcript itself into KG (fire-and-forget)
          emitTranscriptPosted({
            apiBase: KG_API_BASE,
            kg: graph,
            ownerWa: OWNER_WA,
            topicWa: topicWa,
            text: t.text,
            transcript_of: j?.msg_id || null,
            engine: t.engine,
            ts: Date.now(),
            agentId: AGENT_ID,
          }).catch(() => {});
        } catch {
          // swallow; UI already has the voice bubble
        }
      }
    }

    rememberTopic(topicWa, addrInput || topic, graph);
  } catch (e) {
    console.warn("[sendVoiceNoteFile] failed", e);
  }
}

  // Attach the per-tab connection id to signaling headers/meta (optional + safe)
  const withConnMeta = (meta: any = {}) => {
    const m = { ...meta };
    if (WS_ID && WS_ID !== "n/a") (m as any).conn_id = WS_ID;
    return m;
  };
  const withConnHeaders = (h: Record<string, string> = {}) => {
    const out = { ...h };
    if (WS_ID && WS_ID !== "n/a") out["X-Conn-Id"] = WS_ID;
    return out;
  };

  // ───────────── txSig helpers (keep near txSig) ─────────────
  const SIG_DEDUPE_MS = 800; // ignore identical capsule within this window
  const _sentSigCache = new Map<string, number>();

  function sigKey(capsule: any): string {
    const k = Object.keys(capsule || {})[0] || "unknown";
    const p = (capsule as any)[k] || {};

    // Compact, unique enough ICE key
    if (k === "ice" && p?.candidate?.candidate) {
      return `ice:${topicWa}:${p.call_id || ""}:${p.candidate.candidate}`;
    }

    const call = p?.call_id ? `:${p.call_id}` : "";
    const body = JSON.stringify(p).slice(0, 512); // avoid giant keys
    return `${k}:${topicWa}${call}:${body}`;
  }

  // — Signaling: POST a signaling capsule; fallback packs as glyph if needed —
  async function txSig(capsule: object) {
    // De-dupe identical capsules fired in quick succession
    const key = sigKey(capsule as any);
    const now = Date.now();
    const last = _sentSigCache.get(key) || 0;
    if (now - last < SIG_DEDUPE_MS) {
      console.debug("[txSig] deduped:", key, `(${now - last}ms)`);
      return;
    }
    _sentSigCache.set(key, now);

    const common = {
      recipient: topicWa, // canonical WA so both tabs match
      graph,
      meta: withConnMeta({ trace_id: AGENT_ID, graph, t0: Date.now() }),
    };
    const headers = withConnHeaders({
      "Content-Type": "application/json",
      "X-Agent-Token": "dev-token",
      "X-Agent-Id": AGENT_ID,
    });

    console.log("[txSig]", { wsId: WS_ID, capsule, topicWa });

    // Try primary first
    try {
      const r = await postTx(base, { ...common, capsule }, headers);
      if (!r.ok) {
        console.warn("[txSig] primary non-OK:", r.status, r.statusText);
        throw new Error(`primary ${r.status}`);
      }
      return;
    } catch (err) {
      console.warn("[txSig] primary failed → fallback as glyph", err);
    }

    // Fallback: packed signaling inside glyphs
    try {
      const packed = packSig(capsule);
      const r2 = await postTx(base, { ...common, capsule: { glyphs: [packed] } }, headers);
      if (!r2.ok) {
        console.warn("[txSig] fallback non-OK:", r2.status, r2.statusText);
      }
    } catch (err2) {
      console.warn("[txSig] fallback failed", err2);
    }
  }

  // ——— Call functions ———
  async function sendOffer(sdp: string, callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        call_id: callId, kind: "offer", ice_type: undefined, secs: 0,
        ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});
    } catch {}
    return txSig({ voice_offer: { sdp, call_id: callId } } satisfies VoiceOffer);
  }

  async function sendAnswer(sdp: string, callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        call_id: callId, kind: "answer", ice_type: undefined, secs: 0,
        ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});
    } catch {}
    return txSig({ voice_answer: { sdp, call_id: callId } } satisfies VoiceAnswer);
  }

  async function sendIce(candidate: RTCIceCandidateInit, callId: string) {
    return txSig({ ice: { candidate, call_id: callId } } satisfies VoiceIce);
  }

  async function sendCancel(callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        call_id: callId, kind: "cancel", ice_type: undefined, secs: 0,
        ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});
    } catch {}
    return txSig({ voice_cancel: { call_id: callId } } as VoiceCancel);
  }

  async function sendReject(callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        call_id: callId, kind: "reject", ice_type: undefined, secs: 0,
        ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});
    } catch {}
    return txSig({ voice_reject: { call_id: callId } } as VoiceReject);
  }

  async function sendEnd(callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        call_id: callId, kind: "end", ice_type: lastCandType || undefined,
        secs: callSecsRef.current || 0, ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});
    } catch {}
    return txSig({ voice_end: { call_id: callId } } as VoiceEnd);
  }

  async function startCall() {
    if (callState !== "idle") return;

    const callId =
      crypto?.randomUUID?.() || `call-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    callIdRef.current = callId;
    setCallState("offering");

    const { stream } = await ensureMicPTT();

    const pc = await makePeer(
      "caller",
      {
        onLocalDescription: (sdp) => sendOffer(JSON.stringify(sdp), callId),
        onLocalIce: (cand) => sendIce(cand, callId), // only place we send ICE for caller
        onRemoteTrack: (ms) => {
          if (remoteAudioRef.current) remoteAudioRef.current.srcObject = ms;
        },
      },
      { iceServers }
    );

    pc.onicecandidate = (e) => {
      if (e.candidate) {
        const t = /candidate:.* typ (\w+)/.exec(e.candidate.candidate)?.[1] || "";
        if (t) setLastCandType(t);
      }
    };

    pc.onconnectionstatechange = () => {
      const s = pc.connectionState;
      if (s === "connected") {
        setCallState("connected");
        if (callIdRef.current) {
          emitCallState({
            apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
            call_id: callIdRef.current, kind: "connected",
            ice_type: lastCandType || undefined, secs: 0, ts: Date.now(), agentId: AGENT_ID,
          }).catch(() => {});
        }
      }
      if (s === "failed" || s === "closed" || s === "disconnected") {
        setCallState("ended");
      }
    };

    // attach local mic tracks
    stream.getTracks().forEach((t) => pc.addTrack(t, stream));
    rememberLocalMicTrack(stream);
    pcRef.current = pc;

    // emit SDP offer via helper
    try {
      await (pc as any)._emitLocalDescription("offer");
    } catch (e) {
      console.error("Offer emit failed:", e);
      setCallState("ended");
    }
  }

  async function acceptCall() {
    const offer = pendingOfferRef.current as { sdp: string; call_id: string } | null;
    if (!offer) return;

    callIdRef.current = offer.call_id;
    setCallState("connecting");

    const { stream } = await ensureMicPTT();

    const pc = await makePeer(
      "callee",
      {
        onLocalDescription: (sdp) => sendAnswer(JSON.stringify(sdp), offer.call_id),
        onLocalIce: (cand) => sendIce(cand, offer.call_id), // only here for callee ICE
        onRemoteTrack: (ms) => {
          if (remoteAudioRef.current) remoteAudioRef.current.srcObject = ms;
        },
      },
      { iceServers }
    );

    pc.onicecandidate = (e) => {
      if (e.candidate) {
        const t = /candidate:.* typ (\w+)/.exec(e.candidate.candidate)?.[1] || "";
        if (t) setLastCandType(t);
      }
    };

    pc.onconnectionstatechange = () => {
      const s = pc.connectionState;
      if (s === "connected") {
        setCallState("connected");
        if (callIdRef.current) {
          emitCallState({
            apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
            call_id: callIdRef.current, kind: "connected",
            ice_type: lastCandType || undefined, secs: 0, ts: Date.now(), agentId: AGENT_ID,
          }).catch(() => {});
        }
      }
      if (s === "failed" || s === "closed" || s === "disconnected") {
        setCallState("ended");
      }
    };

    // attach local mic tracks
    stream.getTracks().forEach((t) => pc.addTrack(t, stream));
    rememberLocalMicTrack(stream);
    pcRef.current = pc;

    // apply remote offer, then emit our answer
    try {
      const desc = typeof offer.sdp === "string" ? JSON.parse(offer.sdp) : offer.sdp;
      await pc.setRemoteDescription(desc);
      await (pc as any)._emitLocalDescription("answer");
    } catch (e) {
      console.error("Failed to accept call:", e);
      setCallState("ended");
      return;
    }

    // stop ringing and clear pending offer
    try {
      const el = ringAudio.current;
      if (el) {
        el.pause();
        try { el.currentTime = 0; } catch {}
      }
    } catch {}
    pendingOfferRef.current = null;
  }

  // —— Additional Functions: rememberLocalMicTrack, declineCall, toggleMute, toggleHold ———

  function rememberLocalMicTrack(stream: MediaStream) {
    try {
      const t = stream.getAudioTracks?.()[0];
      if (t && !origTrackRef.current) origTrackRef.current = t;
    } catch {}
  }

  // ---- de-dupe: don't fire reject storms for the same call_id ----
  const REJECT_TTL_MS = 30_000; // how long a callId stays suppressed
  const rejectedCallIdsRef = React.useRef<Set<string>>(new Set());
  const inflightRejectsRef = React.useRef<Map<string, Promise<void>>>(new Map());

  async function sendRejectOnce(callId: string) {
    if (!callId) return;

    if (rejectedCallIdsRef.current.has(callId)) {
      console.debug("[reject] duplicate suppressed:", callId);
      return;
    }
    const inflight = inflightRejectsRef.current.get(callId);
    if (inflight) {
      console.debug("[reject] already inflight:", callId);
      await inflight.catch(() => {});
      return;
    }

    const task = (async () => {
      try {
        await sendReject(callId);
        console.log("[reject] sent for", callId);
        rejectedCallIdsRef.current.add(callId);
        window.setTimeout(() => {
          rejectedCallIdsRef.current.delete(callId);
        }, REJECT_TTL_MS);
      } catch (e) {
        console.warn("[reject] failed for", callId, e);
      } finally {
        inflightRejectsRef.current.delete(callId);
      }
    })();

    inflightRejectsRef.current.set(callId, task);
    await task;
  }

  function declineCall() {
    const pending = (pendingOfferRef.current as { sdp: string; call_id: string } | null);
    if (pending?.call_id) {
      console.log("[declineCall] rejecting", pending.call_id);
      sendRejectOnce(pending.call_id).catch(() => {});
    }

    pendingOfferRef.current = null;
    setCallState("idle");

    // stop any ringing
    try {
      const el = ringAudio.current;
      if (el) {
        el.pause();
        try { el.currentTime = 0; } catch {}
      }
    } catch {}
  }

  function toggleMute() {
    setMuted((prev) => {
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
      const sender = pc.getSenders().find((s) => s.track && s.track.kind === "audio");
      if (sender) {
        if (next) {
          await sender.replaceTrack(null);      // pause sending
        } else {
          await sender.replaceTrack(track || null); // resume
        }
      }
    } catch {}
    setOnHold(next);
  }

  // Format duration for logging (silent)
  function fmtDur(secs: number) {
    const s = Number.isFinite(secs) ? Math.max(0, Math.floor(secs)) : 0;
    if (!s) return "—";
    const m = Math.floor(s / 60);
    const r = s % 60;
    return m ? `${m}m ${r.toString().padStart(2, "0")}s` : `${r}s`;
  }

  // Avoid duplicate end bubbles when both sides trigger a summary
  const callSummarySentRef = useRef<Set<string>>(new Set());

  // Single, final version — paste in place
  function logCallSummary(source: "local" | "remote") {
    const callId = callIdRef.current || "n/a";
    if (callSummarySentRef.current.has(callId)) return; // already logged for this call
    callSummarySentRef.current.add(callId);

    const endedAt = Date.now();
    const secs = Math.max(0, Number(callSecsRef.current ?? 0));
    const when = new Date(endedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const msg = `📞 Call ended • ${secs ? fmtDur(secs) : "—"} • ${when}`;

    console.log("[logCallSummary]", { callId, secs, msg });

    const id = `call:${callId}:${endedAt}`;
    const bubble: NormalizedMsg = {
      id,
      ts: endedAt,
      kind: "text",
      text: msg,
      ...(source === "local" ? { from: AGENT_ID } : {}),
    };

    setThread((prev) => {
      const next = [...prev, bubble];
      try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch (e) {
        console.error("[logCallSummary] persist failed:", e);
      }
      return next;
    });
  }

  // Hang up the call
  function hangupCall() {
    const cid = callIdRef.current;
    if (cid) {
      console.log("[hangupCall]", cid);
      if (callState === "offering" || callState === "connecting") {
        // cancel before remote answer
        sendCancel(cid).catch((err) => console.error("[hangupCall] cancel failed:", err));
      } else if (callState === "connected") {
        // normal end after connect
        sendEnd(cid).catch((err) => console.error("[hangupCall] end failed:", err));
      }
    }

    // stop call timer if any
    try {
      if (callTimerRef.current != null) {
        clearInterval(callTimerRef.current);
        callTimerRef.current = null;
      }
    } catch {}

    logCallSummary("local");

    try { pcRef.current?.getSenders().forEach((s) => s.track?.stop()); } catch (err) {
      console.error("[hangupCall] stop senders failed:", err);
    }
    try { pcRef.current?.close(); } catch (err) {
      console.error("[hangupCall] pc close failed:", err);
    }
    pcRef.current = null;
    callIdRef.current = null;

    // stop any ringing just in case
    try {
      const el = ringAudio.current; if (el) { el.pause(); try { el.currentTime = 0; } catch {} }
    } catch {}

    origTrackRef.current = null;
    setMuted(false);
    setOnHold(false);

    setCallState("ended");
  }

  // Cancel the outbound call
  function cancelOutbound() {
    const cid = callIdRef.current;

    if (cid) {
      console.log("[cancelOutbound] Cancelling outbound", cid);
      sendCancel(cid).catch((err) => console.error("[cancelOutbound] cancel failed:", err));
    }

    // stop call timer if any
    try {
      if (callTimerRef.current != null) {
        clearInterval(callTimerRef.current);
        callTimerRef.current = null;
      }
    } catch {}

    // Clean up local peer/mic
    try { pcRef.current?.getSenders().forEach((s) => s.track?.stop()); } catch (err) {
      console.error("[cancelOutbound] stop senders failed:", err);
    }
    try { pcRef.current?.close(); } catch (err) {
      console.error("[cancelOutbound] pc close failed:", err);
    }
    pcRef.current = null;
    callIdRef.current = null;

    // reset mute/hold + original track
    origTrackRef.current = null;
    setMuted(false);
    setOnHold(false);

    // stop any ringing just in case
    try {
      const el = ringAudio.current; if (el) { el.pause(); try { el.currentTime = 0; } catch {} }
    } catch (err) {
      console.error("[cancelOutbound] ring stop failed:", err);
    }

    // end state (you can choose "idle" if you prefer)
    setCallState("ended");

    // optional: local summary bubble
    logCallSummary("local");
  }

  // Format duration for PTT / rollups (silent)
  function formatDur(sec: number) {
    return fmtDur(sec);
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

  // Capture PTT log details
  function pttKey(g: GraphKey, t: string) {
    return `gnet:ptt:log:${g}:${t}`;
  }

  type PttEntry = {
    at: number;           // session start ms
    dur: number;          // duration ms
    acquireMs?: number;   // time-to-grant ms for that session
    granted: boolean;     // whether floor was acquired for this session
  };

  // Load PTT logs from localStorage
  function loadPttLog(g: GraphKey, t: string): PttEntry[] {
    try {
      return JSON.parse(localStorage.getItem(pttKey(g, t)) || "[]");
    } catch {
      console.error("[loadPttLog] Error loading PTT logs.");
      return [];
    }
  }

  // Save PTT logs to localStorage
  function savePttLog(g: GraphKey, t: string, arr: PttEntry[]) {
    try {
      localStorage.setItem(pttKey(g, t), JSON.stringify(arr.slice(-10)));
    } catch {
      console.error("[savePttLog] Error saving PTT logs.");
    }
  }

  // Select mime type for PTT
  function pickMime(): string {
    const candidates = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"];
    for (const m of candidates) {
      if ((window as any).MediaRecorder?.isTypeSupported?.(m)) return m;
    }
    console.warn("[pickMime] No supported mime type found.");
    return "audio/webm";
  }

  // ─── Generic signal send (glyphs/text etc) ───
  async function sendSignal(capsule: SignalCapsule) {
    const headers = withConnHeaders({
      "Content-Type": "application/json",
      "X-Agent-Token": "dev-token",
      "X-Agent-Id": AGENT_ID,
    });
    await postTx(
      base,
      {
        recipient: topicWa, // use canonical
        graph,
        capsule,
        meta: withConnMeta({ trace_id: AGENT_ID, graph, t0: Date.now() }),
      },
      headers
    );
  }

  // Ensure microphone is ready for PTT
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
    try { audioCtxRef.current?.close(); } catch (e) { console.error("AudioContext close failed:", e); }
    audioCtxRef.current = null;
    setMicLevel(0);
  }

  function startMeter(stream: MediaStream) {
    stopMeter();  // stop previous meter before starting a new one
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
    // Safari can start suspended; try to resume once
    ctx.resume?.().catch(() => {});
    meterRAF.current = requestAnimationFrame(tick);
  }

  const voiceUrlMapRef = useRef<Map<string, string>>(new Map());
  useEffect(() => {
    return () => {
      for (const u of voiceUrlMapRef.current.values()) {
        try { URL.revokeObjectURL(u); } catch (e) { console.error("revokeObjectURL failed:", e); }
      }
      voiceUrlMapRef.current.clear();
    };
  }, []);

  function playUrlForVoice(m: Extract<NormalizedMsg, { kind: "voice" }>) {
    // Key includes a short hash of the payload to avoid stale-URL reuse if the same id is reused
    const sig = `${m.mime}|${(m.data_b64 || "").slice(0, 32)}`;
    const key = `${m.id}|${sig}`;
    const map = voiceUrlMapRef.current;

    let url = map.get(key);
    if (!url) {
      // Revoke any older URL for same id (e.g., mime changed)
      for (const [k, u] of map.entries()) {
        if (k.startsWith(`${m.id}|`) && k !== key) {
          try { URL.revokeObjectURL(u); } catch {}
          map.delete(k);
        }
      }
      url = URL.createObjectURL(b64ToBlob(m.data_b64, m.mime));
      map.set(key, url);
    }
    return url;
  }

  // ─── Floor lock ops ───
  async function sendLock(op: "acquire" | "refresh" | "release", resource: string, ttl_ms = 3500) {
    const owner = AGENT_ID;
    const headers = withConnHeaders({
      "Content-Type": "application/json",
      "X-Agent-Token": "dev-token",
      "X-Agent-Id": owner,
    });
    try {
      await postTx(
        base,
        {
          recipient: topicWa, // canonical
          graph,
          capsule: { entanglement_lock: { op, resource, owner, ttl_ms, ts: Date.now() } },
          meta: withConnMeta({ trace_id: owner, graph, t0: Date.now() }),
        },
        headers
      );
    } catch (e) {
      console.warn("[sendLock] post failed", e);
    }
  }

  function waitForLock(resource: string, timeoutMs = 1200): Promise<"granted" | "denied" | "timeout"> {
    const started = Date.now();
    const seen = new Set<string>();
    const key = (ev: any) =>
      `${ev?.resource || ev?.resourceTopic}|${ev?.state}|${ev?.owner}|${ev?.granted ?? ""}|${ev?.ts ?? ""}`;

    return new Promise((resolve) => {
      const deadline = setTimeout(() => resolve("timeout"), timeoutMs);

      const tick = () => {
        // use latest messages each frame (no stale closure)
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
    pttChannelRef.current = `ch-${hash8(topicWa)}-${hash8(AGENT_ID)}`;
    seqRef.current = 0;
  }, [topicWa, AGENT_ID]);

  // ───────────────── startPTT (with KG floor_lock emits) ─────────────────
  async function startPTT() {
    if (pttDownRef.current) return;

    pttDownRef.current = true;
    setAwaitingLock(true);
    setPttDown(true);

    // ── metrics: mark attempt start
    metricsRef.current.lastStart = Date.now();

    // Acquire the floor (canonical topic)
    const resource = `voice:${topicWa}`;
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

      // journal denied attempt (0ms talk)
      emitPttSession({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        talkMs: 0, grants: metricsRef.current.grants, denies: metricsRef.current.denies,
        lastAcquireMs: metricsRef.current.lastAcquireMs, ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});

      // floor_lock (denied)
      emitFloorLock({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        state: "denied", acquire_ms: 0, granted: false, ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});

      metricsRef.current.lastStart = 0;
      return;
    }

    // ── metrics: granted + time-to-grant
    metricsRef.current.grants++;
    const t = Date.now() - metricsRef.current.lastStart;
    metricsRef.current.lastAcquireMs = t;
    lastAcquireMsRef.current = t;
    lastGrantedRef.current = true;

    // journal floor_lock(held)
    emitFloorLock({
      apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
      state: "held", acquire_ms: t, granted: true, ts: Date.now(), agentId: AGENT_ID,
    }).catch(() => {});

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
      if (keepaliveRef.current != null) { clearInterval(keepaliveRef.current); keepaliveRef.current = null; }
      const r0 = lockResourceRef.current; lockResourceRef.current = null;
      if (r0) sendLock("release", r0).catch(() => {});
      setFloorOwned(false);

      // journal zero-length session + floor_lock(free)
      emitPttSession({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        talkMs: 0, grants: metricsRef.current.grants, denies: metricsRef.current.denies,
        lastAcquireMs: metricsRef.current.lastAcquireMs, ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});
      emitFloorLock({
        apiBase: KG_API_BASE, kg: graph, ownerWa: OWNER_WA, topicWa,
        state: "free", acquire_ms: lastAcquireMsRef.current || metricsRef.current.lastAcquireMs || 0,
        granted: true, ts: Date.now(), agentId: AGENT_ID,
      }).catch(() => {});
      metricsRef.current.lastStart = 0;
      return;
    }

    // Start MediaRecorder and buffer chunks; we will send ONE voice note on release
    chunksRef.current = [];
    try {
      // Use the mime we negotiated in ensureMicPTT(), but fall back if the browser rejects it
      const desiredMime = mime; // from ensureMicPTT()
      let rec: MediaRecorder;
      try {
        rec = new MediaRecorder(stream, { mimeType: desiredMime });
      } catch {
        rec = new MediaRecorder(stream);
      }
      mrRef.current = rec;

      rec.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data);
      };

      // Collect small chunks for responsive stop; we’ll stitch at stopPTT
      rec.start(200);
    } catch (e) {
      console.warn("[startPTT] MediaRecorder start failed:", e);
    }
    }

    // ───────────────── stopPTT ─────────────────
    async function stopPTT() {
      console.log("[stopPTT] Stopping PTT...");

      if (!pttDownRef.current) {
        console.log("[stopPTT] PTT is not currently down.");
        return;
      }

      pttDownRef.current = false;
      setPttDown(false);

      // ── metrics: accumulate talk time + session count + persist per-topic
      let lastDur = 0;
      if (metricsRef.current.lastStart) {
        const startAt = metricsRef.current.lastStart;
        lastDur = Date.now() - startAt;
        metricsRef.current.sessions++;
        metricsRef.current.talkMs += lastDur;
        metricsRef.current.lastStart = 0;
        console.log(`[stopPTT] Talk time accumulated: ${lastDur}ms. Total talk time: ${metricsRef.current.talkMs}ms.`);

        // Persist per-topic entry (last 10)
        const log = loadPttLog(graph, topicWa);
        log.push({
          at: startAt,
          dur: lastDur,
          acquireMs: lastAcquireMsRef.current || undefined,
          granted: !!lastGrantedRef.current,
        });
        savePttLog(graph, topicWa, log);
        console.log("[stopPTT] Updated PTT log.");

        // Journal this PTT session
        emitPttSession({
          apiBase: KG_API_BASE,
          kg: graph,
          ownerWa: OWNER_WA,
          topicWa: topicWa,
          talkMs: lastDur,
          grants: metricsRef.current.grants,
          denies: metricsRef.current.denies,
          lastAcquireMs: metricsRef.current.lastAcquireMs,
          ts: Date.now(),
          agentId: AGENT_ID,
        }).catch((err) => {
          console.error("[stopPTT] Error emitting PTT session:", err);
        });
      }

      stopMeter(); // stop the visual meter immediately
      console.log("[stopPTT] Visual meter stopped.");

      // Stop recorder and build a single blob
      const rec = mrRef.current;
      if (rec && rec.state !== "inactive") {
        const done = new Promise<void>((resolve) => {
          rec.onstop = () => resolve();
        });
        try {
          rec.stop();
          console.log("[stopPTT] Recorder stopped.");
        } catch (e) {
          console.error("[stopPTT] Error stopping recorder:", e);
        }
        await done;
      }
      mrRef.current = null;

      // Combine chunks into one voice note and send
      try {
        if (chunksRef.current.length) {
          const chosenMime = pickMime();
          const blob = new Blob(chunksRef.current, { type: chosenMime });
          chunksRef.current = [];
          console.log("[stopPTT] Combined voice chunks into blob.");

          const arr = await blob.arrayBuffer();
          const data_b64 = abToB64(arr);

          // Non-blocking KG journal of the voice clip
          emitVoiceToKG({
            apiBase: KG_API_BASE,
            kg: graph,
            ownerWa: OWNER_WA,
            topicWa: topicWa,
            mime: chosenMime,
            data_b64,
            durMs: lastDur || undefined,
            ts: Date.now(),
            agentId: AGENT_ID,
          }).catch((err) => {
            console.error("[stopPTT] Error emitting voice to KG:", err);
          });

          console.log("[stopPTT] Voice clip journaled to KG.");

          const vfCapsule = {
            voice_frame: {
              channel: pttChannelRef.current,
              seq: (seqRef.current++) | 0, // single note; seq still useful
              ts: Date.now(),
              mime: chosenMime,
              data_b64,
            },
          };

          await sendVoiceFrame(vfCapsule);
          console.log("[stopPTT] Voice frame sent.");
        }
      } catch (e) {
        console.warn("[stopPTT] failed to build/send voice note", e);
      } finally {
        // Release lock + cleanup keepalive every time
        if (keepaliveRef.current != null) {
          clearInterval(keepaliveRef.current);
          keepaliveRef.current = null;
          console.log("[stopPTT] Keepalive interval cleared.");
        }
        const r0 = lockResourceRef.current;
        lockResourceRef.current = null;
        if (r0) {
          sendLock("release", r0).catch((err) => {
            console.error("[stopPTT] Error releasing lock:", err);
          });
          console.log("[stopPTT] Lock released.");
        }
        setFloorOwned(false);

        // 🔹 Journal that the floor is now free
        emitFloorLock({
          apiBase: KG_API_BASE,
          kg: graph,
          ownerWa: OWNER_WA,
          topicWa: topicWa,
          state: "free",
          acquire_ms: lastAcquireMsRef.current || metricsRef.current.lastAcquireMs || 0,
          granted: true,
          ts: Date.now(),
          agentId: AGENT_ID,
        }).catch((err) => {
          console.error("[stopPTT] Error emitting floor free:", err);
        });
        console.log("[stopPTT] Floor state updated to free.");
      }
    }

    // ───────────────── sendVoiceFrame (now OUTSIDE stopPTT) ─────────────────
    async function sendVoiceFrame(vfCapsule: any) {
      const vf = vfCapsule?.voice_frame || {};
      const b64 = vf.data_b64 || "";
      const mimeType = vf.mime || "audio/webm";
      const channel = vf.channel;
      const seq = vf.seq;

      if (!b64) {
        console.warn("[sendVoiceFrame] no data_b64 in capsule");
        return;
      }

      // Rough base64 → bytes estimate
      const approxBytes =
        Math.max(0, Math.floor(b64.length * 0.75) - (b64.endsWith("==") ? 2 : b64.endsWith("=") ? 1 : 0));

      console.log("[sendVoiceFrame] prepare →", {
        channel,
        seq,
        mimeType,
        approxBytes,
        wsId: typeof WS_ID !== "undefined" ? WS_ID : "(n/a)",
      });

      const localId = `local-voice:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
      const optimistic: NormalizedMsg = {
        id: localId,
        kind: "voice",
        ts: Date.now(),
        from: AGENT_ID,
        mime: mimeType,
        data_b64: b64,
      };

      setThread((t) => {
        const next = [...t, optimistic];
        try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
        return next;
      });

      // Build headers/meta with per-tab conn id (helpers were added earlier)
      const headers = typeof withConnHeaders === "function"
        ? withConnHeaders({
            "Content-Type": "application/json",
            "X-Agent-Token": "dev-token",
            "X-Agent-Id": AGENT_ID,
          })
        : {
            "Content-Type": "application/json",
            "X-Agent-Token": "dev-token",
            "X-Agent-Id": AGENT_ID,
          };

      const meta = typeof withConnMeta === "function"
        ? withConnMeta({ trace_id: AGENT_ID, graph, t0: Date.now() })
        : { trace_id: AGENT_ID, graph, t0: Date.now() };

      try {
        const body = {
          recipient: topicWa, // canonical recipient
          graph,
          capsule: vfCapsule,
          meta,
        };

        console.log("[sendVoiceFrame] POST →", { url: base, channel, seq, size: approxBytes });

        const res = await postTx(base, body, headers);

        // RF profile guardrail
        if (res.status === 413) {
          const j = await res.json().catch(() => ({} as any));
          console.warn("[sendVoiceFrame] 413 payload too large", j);
          alert(
            j?.error === "too large"
              ? `Voice clip too large for RF path (${j.size} > ${j.max} bytes). Try a shorter clip or switch to IP-only.`
              : "Voice clip rejected: too large for current profile."
          );
          return;
        }

        if (!res.ok) {
          const txt = await res.text().catch(() => "");
          console.warn("[sendVoiceFrame] HTTP error", res.status, txt);
          return;
        }

        const j = await res.json().catch(() => ({} as any));
        if (j?.msg_id) {
          rememberSent(j.msg_id);

          // Swap optimistic id with server id so acks correlate
          setThread((prev) =>
            prev.map((m) => (m.id === localId ? { ...m, id: j.msg_id } : m))
          );

          console.log("[sendVoiceFrame] delivered ✓", {
            msg_id: j.msg_id,
            channel,
            seq,
            wsId: typeof WS_ID !== "undefined" ? WS_ID : "(n/a)",
          });
        } else {
          console.log("[sendVoiceFrame] OK but no msg_id in response", j);
        }
      } catch (e) {
        console.warn("[sendVoiceFrame] network/error", e);
      }
    } // ← end sendVoiceFrame

    // Transcription toggle — single source of truth (persists in localStorage)
    const [transcribeOnAttach, setTranscribeOnAttach] = useState<boolean>(() => {
      try {
        return localStorage.getItem("gnet:transcribeOnAttach") === "1";
      } catch {
        return false;
      }
    });
    useEffect(() => {
      try { localStorage.setItem("gnet:transcribeOnAttach", transcribeOnAttach ? "1" : "0"); } catch {}
    }, [transcribeOnAttach]);

    function attachVoiceFile() {
      attachInputRef.current?.click();
    }

    // Voice note picker → send as voice_note (policy-aware: Auto / Radio-only / IP-only)
    const attachInputRef = useRef<HTMLInputElement | null>(null);

    // ───────────────── onPickVoiceFile — with logging + per-tab conn id ─────────────────
    async function onPickVoiceFile(e: React.ChangeEvent<HTMLInputElement>) {
      const f = e.target.files?.[0];
      e.target.value = ""; // allow re-pick of same file
      if (!f) return;

      const name = f.name;
      const mimeType = f.type || mimeFromName(name);
      const size = f.size ?? 0;

      console.log("[attachVoice] picked file →", { name, mimeType, size });

      // Read & encode
      let b64 = "";
      try {
        const ab = await f.arrayBuffer();
        b64 = abToB64(ab);
      } catch (err) {
        console.warn("[attachVoice] failed to read file", err);
        return;
      }

      // Rough base64 → bytes estimate (sanity vs f.size)
      const approxBytes =
        Math.max(0, Math.floor(b64.length * 0.75) - (b64.endsWith("==") ? 2 : b64.endsWith("=") ? 1 : 0));
      console.log("[attachVoice] sizes →", { fileBytes: size, approxBytesFromB64: approxBytes });

      // 🔹 Journal the voice note to the KG (non-blocking)
      emitVoiceToKG({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: OWNER_WA,
        topicWa: topicWa,
        mime: mimeType,
        data_b64: b64,
        durMs: undefined, // or real duration if known
        ts: Date.now(),
        agentId: AGENT_ID,
      }).catch(() => {});

      // Optimistic bubble
      const localId = `local-voice:${Date.now()}:${Math.random().toString(36).slice(2, 6)}`;
      const optimistic: NormalizedMsg = {
        id: localId,
        ts: Date.now(),
        kind: "voice",
        from: AGENT_ID,
        mime: mimeType,
        data_b64: b64,
      };
      setThread((prev) => {
        const next = [...prev, optimistic];
        try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
        return next;
      });

      // Build headers/meta with conn_id if helpers exist
      const headers = typeof withConnHeaders === "function"
        ? withConnHeaders({
            "Content-Type": "application/json",
            "X-Agent-Token": "dev-token",
            "X-Agent-Id": AGENT_ID,
          })
        : {
            "Content-Type": "application/json",
            "X-Agent-Token": "dev-token",
            "X-Agent-Id": AGENT_ID,
          };

      const meta = typeof withConnMeta === "function"
        ? withConnMeta({ trace_id: AGENT_ID, graph, t0: Date.now() })
        : { trace_id: AGENT_ID, graph, t0: Date.now() };

      try {
        const body = {
          recipient: topicWa, // canonical
          graph,
          capsule: { voice_note: { ts: Date.now(), mime: mimeType, data_b64: b64 } },
          meta,
        };

        console.log("[attachVoice] POST →", { url: base, mimeType, approxBytes });

        const res = await postTx(base, body, headers);

        if (res.status === 413) {
          const j = await res.json().catch(() => ({} as any));
          console.warn("[attachVoice] 413 too large", j);
          alert(
            j?.error === "too large"
              ? `Voice note too large for RF path (${j.size} > ${j.max} bytes). Try a shorter clip or switch to IP-only.`
              : "Voice note rejected: too large for current RF profile."
          );
          return;
        }

        if (!res.ok) {
          const txt = await res.text().catch(() => "");
          console.warn("[attachVoice] HTTP error", res.status, txt);
          return;
        }

        const j = await res.json().catch(() => ({} as any));
        if (j?.msg_id) {
          rememberSent(j.msg_id);
          // Swap optimistic id for server id so downstream acks correlate
          setThread((prev) => prev.map((m) => (m.id === localId ? { ...m, id: j.msg_id } : m)));
          console.log("[attachVoice] delivered ✓", { msg_id: j.msg_id, bytes: approxBytes });
        } else {
          console.log("[attachVoice] OK (no msg_id)", j);
        }

        // ⬇️ Optional transcription → send glyphs:[text] and journal to KG
        if (transcribeOnAttach) {
          setTranscribing(true);
          const t = await transcribeAudio(mimeType, b64);
          setTranscribing(false);
          if (t?.text) {
            const txMeta = typeof withConnMeta === "function"
              ? withConnMeta({
                  trace_id: AGENT_ID,
                  graph,
                  t0: Date.now(),
                  transcript_of: j?.msg_id || null,
                  engine: t.engine || undefined,
                })
              : {
                  trace_id: AGENT_ID,
                  graph,
                  t0: Date.now(),
                  transcript_of: j?.msg_id || null,
                  engine: t.engine || undefined,
                };

            await postTx(
              base,
              {
                recipient: topicWa, // canonical
                graph,
                capsule: { glyphs: [t.text] },
                meta: txMeta,
              },
              headers
            ).catch(() => {});

            // 🧾 Journal transcript into KG
            emitTranscriptPosted({
              apiBase: KG_API_BASE,
              kg: graph,
              ownerWa: OWNER_WA,
              topicWa: topicWa,
              text: t.text,
              transcript_of: j?.msg_id || null,
              engine: t.engine,
              ts: Date.now(),
              agentId: AGENT_ID,
            }).catch(() => {});
          }
        }

        rememberTopic(topicWa || topic, addrInput || topicWa || topic, graph);
      } catch (err) {
        console.warn("[attachVoice] send failed", err);
      }
    }

  // Small helper to render an initial/avatar for recents
  function initials(s: string) {
    const parts = s.trim().split(/\s+/);
    const a = (parts[0] || "").charAt(0).toUpperCase();
    const b = (parts[1] || "").charAt(0).toUpperCase();
    return (a + b) || a || "👤";
  }

  // ── Call history rollup helpers ──────────────────────────────────────────────
  function isCallSummaryMsg(m: NormalizedMsg): boolean {
    return (
      m?.kind === "text" &&
      typeof (m as any).text === "string" &&
      (m as any).text.startsWith("📞 Call ended")
    );
  }

  // Parse "📞 Call ended • 2m 5s • 09:41" or "📞 Call ended • 15s • 09:41" or "• — •"
  function parseCallSecsFromText(txt: string): number {
    const m = /Call ended\s*•\s*([^•]+)\s*•/i.exec(txt);
    if (!m) return 0;
    const dur = m[1].trim();
    if (dur === "—") return 0;
    let secs = 0;
    const mm = /(\d+)\s*m/.exec(dur);
    const ss = /(\d+)\s*s/.exec(dur);
    if (mm) secs += parseInt(mm[1], 10) * 60;
    if (ss) secs += parseInt(ss[1], 10);
    return secs;
  }

  function dayKey(ts: number): string {
    const d = new Date(ts);
    const y = d.getFullYear();
    const m = `${d.getMonth() + 1}`.padStart(2, "0");
    const da = `${d.getDate()}`.padStart(2, "0");
    return `${y}-${m}-${da}`;
  }

  function dayLabel(ts: number): string {
    const d = new Date(ts);
    const today = new Date();
    const yday = new Date();
    yday.setDate(today.getDate() - 1);

    const same = (a: Date, b: Date) =>
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate();

    if (same(d, today)) return "Today";
    if (same(d, yday)) return "Yesterday";

    return d.toLocaleDateString([], {
      month: "short",
      day: "numeric",
      year: d.getFullYear() !== today.getFullYear() ? "numeric" : undefined,
    });
  }

  // Build a render list that replaces individual call-ended bubbles with a daily rollup line
  type CallRollupItem = {
    __type: "call-rollup";
    id: string;
    ts: number;
    label: string;
    count: number;
    totalSecs: number;
    day: string;
  };

  const renderList = useMemo<(NormalizedMsg | CallRollupItem)[]>(() => {
    if (!thread.length) return [];

    // Group by day; gather calls and non-call messages per day (preserving order for non-calls)
    const byDayCalls = new Map<string, { ts0: number; count: number; total: number }>();
    const byDayNonCalls = new Map<string, NormalizedMsg[]>();

    for (const m of thread) {
      const dk = dayKey(m.ts || Date.now());
      if (isCallSummaryMsg(m)) {
        const secs = parseCallSecsFromText((m as any).text || "");
        const g = byDayCalls.get(dk) || { ts0: m.ts, count: 0, total: 0 };
        g.ts0 = Math.min(g.ts0, m.ts);
        g.count += 1;
        g.total += secs;
        byDayCalls.set(dk, g);
      } else {
        const arr = byDayNonCalls.get(dk) || [];
        arr.push(m);
        byDayNonCalls.set(dk, arr);
      }
    }

    // Determine chronological day order based on earliest ts per day (from either calls or non-calls)
    const allDays = new Set<string>([...byDayCalls.keys(), ...byDayNonCalls.keys()]);
    const dayOrder = [...allDays].sort((a, b) => {
      const aTs = Math.min(
        byDayCalls.get(a)?.ts0 ?? Number.MAX_SAFE_INTEGER,
        byDayNonCalls.get(a)?.[0]?.ts ?? Number.MAX_SAFE_INTEGER
      );
      const bTs = Math.min(
        byDayCalls.get(b)?.ts0 ?? Number.MAX_SAFE_INTEGER,
        byDayNonCalls.get(b)?.[0]?.ts ?? Number.MAX_SAFE_INTEGER
      );
      return aTs - bTs;
    });

    const out: (NormalizedMsg | CallRollupItem)[] = [];
    for (const dk of dayOrder) {
      const cg = byDayCalls.get(dk);
      if (cg && cg.count > 0) {
        const lbl = `${dayLabel(cg.ts0)} • 📞 ${cg.count} call${cg.count === 1 ? "" : "s"} • ${formatDur(cg.total)}`;
        out.push({
          __type: "call-rollup",
          id: `call-rollup:${dk}:${cg.ts0}`,
          ts: cg.ts0,
          label: lbl,
          count: cg.count,
          totalSecs: cg.total,
          day: dk,
        });
      }
      const non = byDayNonCalls.get(dk);
      if (non && non.length) out.push(...non);
    }

    // Keep global chronological ordering (rollups use earliest ts of their day)
    out.sort((a, b) => (a as any).ts - (b as any).ts);
    return out;
  }, [thread]);

  // Contacts + Recents for the left rail
  //const contacts = useMemo(() => getContacts(), []);
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
    const kgIn = canonKG(graph);
    const { wa, label, kg } = resolveLabelToWA(base, kgIn, next);

    setGraph(kg);
    setTopic(wa);
    setAddrInput(`${label}@${kg}`);

    // persist in address book to reduce duplicates
    rememberLabel(kg, wa, label);
    rememberTopic(wa, label, kg);
  }

  const [showSettings, setShowSettings] = useState(false);

  // ───────────────── ICE/TURN quick settings popover ─────────────────
  const IceSettings: React.FC = () => {
    const [open, setOpen] = useState(false);
    const [uri, setUri] = useState("");
    const [username, setUsername] = useState("");
    const [credential, setCredential] = useState("");

    function addTurnLocal() {
      if (!uri.trim() || !username.trim() || !credential.trim()) return;
      const next: RTCIceServer[] = [
        ...iceServers,
        { urls: uri.trim(), username: username.trim(), credential: credential.trim() },
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
                <button onClick={copyInvite}>Copy Invite</button>
                <button onClick={clearThreadCache}>Reset</button>
                <button
                  onClick={resetTelemetry}
                  style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}
                  title="Reset RF/IP send counters"
                >
                  Reset Telemetry
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // simple pill text used elsewhere
  const rfPill = radioOk ? "📡 Radio healthy" : "☁️ IP fallback";

  const TransportSettings: React.FC<{ radioOk: boolean; lastHealthAt: number }> = ({
    radioOk,
    lastHealthAt,
  }) => {
    const [mode, setMode] = useState<TransportMode>(getTransportMode());

    // keep only this listener to reflect external mode changes
    useEffect(() => {
      const onExt = (e: any) => setMode(e.detail as TransportMode);
      window.addEventListener("gnet:transport-mode", onExt);
      return () => window.removeEventListener("gnet:transport-mode", onExt);
    }, []);

    return (
      <div style={{ marginLeft: 8, display: "inline-flex", alignItems: "center", gap: 6 }}>
        <TransportPicker />
        <span
          style={{ fontSize: 12, opacity: 0.75 }}
          title={`last health check: ${new Date(lastHealthAt).toLocaleTimeString()}`}
        >
          {mode === "ip-only"
            ? "☁️ IP-only"
            : mode === "radio-only"
            ? "📡 Radio-only"
            : radioOk
            ? "📡 Radio (healthy)"
            : "☁️ IP (fallback)"}
        </span>
      </div>
    );
  };

  // ---- Mic button computed props (keeps JSX simple) ---
  const micTitle =
    micDisabled
      ? `Channel busy (${floorBusyBy})`
      : floorOwned || pttDown
      ? "Recording… release to send"
      : micReady
      ? "Press and hold to talk"
      : "Press and hold (will ask for mic)";

  const micBg =
    pttDown || floorOwned
      ? "#dbeafe"
      : awaitingLock
      ? "#e0e7ff"
      : micDisabled
      ? "#fde68a"
      : "#fff";

  const micShadow =
    pttDown || floorOwned
      ? "0 0 0 2px #93c5fd inset, 0 0 12px rgba(59,130,246,.55)"
      : awaitingLock
      ? "0 0 0 2px #a5b4fc inset"
      : "none";

  const micCursor = micDisabled ? "not-allowed" : "pointer";

return (
  <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", height: "100%", gap: 12 }}>
    {/* Left rail: Recents / Contacts and graph toggle */}
    <aside
      data-contacts-count={String(contacts.length)}
      style={{
        border: "1px solid #e5e7eb",
        background: "#fff",        // was "#0fff" (cyan). Use "#f8fafc" to match <main> if preferred.
        borderRadius: 8,
        padding: 10,
        display: "flex",
        flexDirection: "column",
        gap: 10,
        minHeight: 0,
        minWidth: 0,
        overflow: "hidden",
      }}
    >
        {/* Graph toggle */}
        <div
          style={{
            display: "inline-flex",
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
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

        {/* Address bar that accepts "kevin@work" or a full ucs:// URL */}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <div style={{ position: "relative", flex: 1 }}>
            <input
              aria-label="Address or topic"
              value={addrInput}
              onChange={(e) => setAddrInput(e.target.value)}
              onBlur={() => addrInput.trim() && applyTopicChange(addrInput.trim())}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const v = addrInput.trim();
                  if (v) applyTopicChange(v);
                }
              }}
              placeholder="dave@personal  •  ucs://wave.tp/dave"
              list="addr-suggestions"
              style={{
                width: "100%",
                padding: "8px 34px 8px 10px", // room for the clear (×) button
                borderRadius: 8,
                border: "1px solid #e5e7eb",
                background: "#f8fafc",
                fontSize: 13,
              }}
            />

            {/* Clear (×) */}
            {addrInput ? (
              <button
                type="button"
                onClick={() => setAddrInput("")}
                title="Clear"
                aria-label="Clear"
                style={{
                  position: "absolute",
                  right: 6,
                  top: "50%",
                  transform: "translateY(-50%)",
                  width: 22,
                  height: 22,
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  background: "#fff",
                  fontSize: 12,
                  lineHeight: "20px",
                  cursor: "pointer",
                }}
              >
                ×
              </button>
            ) : null}
          </div>

          {/* Go */}
          <button
            type="button"
            onClick={() => addrInput.trim() && applyTopicChange(addrInput.trim())}
            style={{
              padding: "8px 10px",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              fontSize: 13,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
            title="Open conversation"
          >
            Go
          </button>

          {/* Type-ahead suggestions */}
          <datalist id="addr-suggestions">
            {contacts?.map((c) => (
              <option key={`c:${c.wa}`} value={`${c.name}@${c.kg}`}>
                {c.wa}
              </option>
            ))}
            {recents?.map((r) => {
              const label = r.label || r.topic;
              return (
                <option key={`r:${r.topic}|${r.graph}`} value={`${label}@${r.graph}`}>
                  {r.topic}
                </option>
              );
            })}
          </datalist>
        </div>

        {/* Contacts */}
        <div style={{ fontWeight: 700, fontSize: 13, color: "#334155" }}>Contacts</div>

        {/* (optional) small search field just to neaten the rail */}
        <div style={{ padding: "6px 0 8px" }}>
          <input
            placeholder="Search contacts…"
            spellCheck={false}
            style={{
              width: "100%",
              maxWidth: "100%",
              boxSizing: "border-box",
              padding: "8px 10px",
              borderRadius: 10,
              border: "1px solid #e5e7eb",
              outline: "none",
            }}
          />
        </div>

        <div style={{ overflow: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
          {contacts.map((c) => (
            <button
              key={c.wa}
              onClick={() => applyTopicChange(c.wa)}
              title={c.wa}
              style={{
                display: "grid",
                gridTemplateColumns: "36px minmax(0, 1fr)",
                gap: 10,
                alignItems: "center",
                padding: "10px 12px",
                borderRadius: 12,
                border: "1px solid #e5e7eb",
                background: isActive(c.wa) ? "#f1f5f9" : "#fff",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              {/* avatar */}
              <div
                aria-hidden
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  border: "1px solid #e5e7eb",
                  display: "grid",
                  placeItems: "center",
                  fontSize: 12,
                  fontWeight: 800,
                  background: "#f8fafc",
                  color: "#111827",
                }}
              >
                {c.initials || initials(c.name)}
              </div>

              {/* name + tag */}
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    whiteSpace: "nowrap",
                    textOverflow: "ellipsis",
                    overflow: "hidden",
                    fontSize: 14,
                    fontWeight: 700,
                    color: "#111827",
                  }}
                >
                  {c.name}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8" }}>
                  {String(c.kg).toLowerCase()}
                </div>
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

          {/* Call strip */}
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

              {callState === "connected" ? (
                <button onClick={hangupCall} style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}>
                  Hang up
                </button>
              ) : (
                <button onClick={cancelOutbound} style={{ fontSize: 12, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb" }}
                  title="Cancel outgoing call">
                  Cancel
                </button>
              )}
            </div>
          )}

          {/* ICE settings button */}
          <IceSettings />

          {/* Transport policy (Auto / Radio-only / IP-only) */}
          <TransportSettings radioOk={radioOk} lastHealthAt={lastHealthAt} />

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
          {renderList.map((item: any) => {
            // Rollup row
            if (item?.__type === "call-rollup") {
              return (
                <div
                  key={item.id}
                  style={{
                    alignSelf: "center",
                    background: "#f1f5f9",
                    border: "1px dashed #e5e7eb",
                    borderRadius: 999,
                    padding: "4px 10px",
                    fontSize: 12,
                    color: "#475569",
                  }}
                  title={`${item.count} call${item.count === 1 ? "" : "s"} • total ${formatDur(item.totalSecs)}`}
                >
                  {item.label}
                </div>
              );
            }

            // Normal message bubble
            const m = item as NormalizedMsg;
            const idStr = String(m?.id ?? "");
            const mine =
              (m as any)?.from === AGENT_ID ||
              (!("from" in (m as any)) && (idStr.startsWith("local:") || idStr.startsWith("local-voice:")));

            const base: React.CSSProperties = {
              alignSelf: mine ? "flex-end" : "flex-start",
              background: mine ? "#dbeafe" : "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              padding: "8px 10px",
              maxWidth: "80%",
              boxShadow: "0 1px 1px rgba(0,0,0,0.04)",
            };

            return (
              <div key={idStr} style={base}>
                {m.kind === "text" ? (
                  <div style={{ whiteSpace: "pre-wrap" }}>{(m as any).text || ""}</div>
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
                    <span style={{ fontSize: 12, color: "#64748b" }}>
                      {(String((m as any).mime || "").replace("audio/", "")) || "audio"}
                    </span>
                  </div>
                )}
                <div style={{ fontSize: 10, color: "#94a3b8", marginTop: 4 }}>
                  {new Date(Number((m as any).ts || Date.now())).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
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

        {/* ── compact metrics line ───────────────────────────────────────── */}
        <div style={{ marginTop: 6, alignSelf: "flex-end", fontSize: 11, color: "#94a3b8" }}>
          {(() => {
            const s = metricsRef.current;
            const recv = lossRef.current?.recv ?? 0;
            const lost = lossRef.current?.lost ?? 0;
            const total = recv + lost;
            const lossPct = total ? Math.round((lost / total) * 100) : 0;
            const rtt = lastRttRef.current ?? 0;
            return `${s.sessions} PTT • talk ${Math.round(s.talkMs / 1000)}s • last lock ${s.lastAcquireMs}ms • loss ${lossPct}% (${lost}/${total}) • rtt ${rtt}ms`;
          })()}
        </div>

        {/* ── PTT summary panel (last 10) ──────────────────────────────── */}
        {(() => {
          const log = loadPttLog(graph, topic);
          if (!log || log.length === 0) return null;

          const totalTalkMs = log.reduce((acc, s) => acc + (s.dur || 0), 0);
          const acqVals = log
            .map(s => s.acquireMs)
            .filter((v): v is number => typeof v === "number");
          const avgAcquire = acqVals.length
            ? Math.round(acqVals.reduce((a, b) => a + b, 0) / acqVals.length)
            : 0;
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
                <span>
                  Total talk: <strong>{Math.round(totalTalkMs / 1000)}s</strong>
                </span>
                <span>
                  Avg acquire: <strong>{avgAcquire}ms</strong>
                </span>
                <span>
                  Grants/Denies: <strong>{grants}</strong>/<strong>{denies}</strong>
                </span>
              </div>

              <div
                style={{
                  maxHeight: 140,
                  overflow: "auto",
                  borderTop: "1px dashed #e5e7eb",
                  paddingTop: 6,
                }}
              >
                {log
                  .slice()
                  .reverse()
                  .map((s, i) => (
                    <div
                      key={`${s.at}:${i}`}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr auto auto auto",
                        gap: 8,
                        alignItems: "baseline",
                        padding: "2px 0",
                      }}
                    >
                      <div style={{ color: "#64748b" }}>
                        {new Date(s.at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </div>
                      <div title="duration">⏱ {Math.round((s.dur || 0) / 1000)}s</div>
                      <div title="time to grant">
                        {typeof s.acquireMs === "number" ? `⚡ ${s.acquireMs}ms` : "⚡ —"}
                      </div>
                      <div title="granted?">{s.granted ? "✅ granted" : "❌ denied"}</div>
                    </div>
                  ))}
              </div>

              <div
                style={{
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  padding: "6px 8px",
                  opacity: 0.85,
                }}
              >
                {/* existing bits like RTT / loss / ICE type */}
                <span style={{ fontSize: 12 }}>RTT: {lastRttRef.current ?? 0} ms</span>
                <span style={{ fontSize: 12 }}>
                  Loss: {(() => {
                    const recv2 = lossRef.current?.recv ?? 0;
                    const lost2 = lossRef.current?.lost ?? 0;
                    const tot2 = recv2 + lost2;
                    return tot2 ? Math.round((lost2 / tot2) * 100) : 0;
                  })()}
                  %
                </span>
                <span style={{ fontSize: 12 }}>ICE: {lastCandType || "—"}</span>
                {/* telemetry (rf/ip ok/err) */}
                <span style={{ fontSize: 12, opacity: 0.6, marginLeft: 8 }}>
                  RF ok/err: {tele.rf_ok}/{tele.rf_err} · IP ok/err: {tele.ip_ok}/{tele.ip_err}
                  {" "}
                  {rfPill}
                </span>
                <button
                  onClick={resetTelemetry}
                  style={{ fontSize: 11, padding: "2px 6px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff" }}
                  title="Zero RF/IP counters"
                >
                  ↺ counters
                </button>
              </div>
            </div>
          );
        })()}
      </div>
    </div>  
  );
};
