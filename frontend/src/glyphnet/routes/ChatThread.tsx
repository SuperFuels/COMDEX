// ──────────────────────────────────────────────────────────────
// src/routes/ChatThread.tsx — TOP SECTION (replace through normalizeIncoming)
// ─────────────────────────────────────────────────────────────-

import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import useGlyphnet from "@glyphnet/hooks/useGlyphnet";
import {
  getRecent,
  rememberTopic,
  rememberLabel,
  resolveHumanAddress,
  getContacts,
} from "@glyphnet/lib/addressBook";
import type { RecentItem } from "@glyphnet/lib/addressBook";
import { canonKG, resolveLabelToWA } from "@glyphnet/utils/nameService";
import type { GraphKey } from "@glyphnet/utils/nameService";
import { makePeer, DEFAULT_ICE } from "@glyphnet/utils/webrtc";
import { Telemetry } from "@glyphnet/utils/telemetry";
import { resolveApiBase } from "@glyphnet/utils/base";
import {
  importAesKey,
  attachSenderE2EE,
  attachReceiverE2EE,
} from "@glyphnet/utils/webrtc_e2ee";
import TransportPicker from "@glyphnet/components/TransportPicker";
import { KG_API_BASE } from "@glyphnet/utils/kgApiBase";
import VisitHistoryPanel from "@glyphnet/components/VisitHistoryPanel";
import { getIdentity, type AgentIdentity } from "@glyphnet/utils/identity";
import KGSearchPanel from "@glyphnet/components/KGSearchPanel";

import {
  emitTextToKG,
  emitVoiceToKG,
  emitPttSession,
  emitFloorLock,
  emitCallState,
  emitTranscriptPosted,
} from "@glyphnet/lib/kg_emit";

import type {
  SignalCapsule,
  VoiceOffer,
  VoiceAnswer,
  IceCapsule as VoiceIce,
  VoiceCancel,
  VoiceReject,
  VoiceEnd,
  VoiceCaps,
} from "@glyphnet/utils/callTypes";
import {
  postTx,
  transportBase,
  onRadioHealth,
  getTransportMode,
  setTransportMode,
} from "@glyphnet/utils/transport";
import type { TransportMode } from "@glyphnet/utils/transport";

import {
  SIG_TAG,
  packSig as _packSig,
  unpackSig as _unpackSig,
} from "@glyphnet/utils/sigpack";

// ──────────────────────────────────────────────────────────────
// Owner / environment
// ─────────────────────────────────────────────────────────────-

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
    try {
      sessionStorage.setItem(k, v);
    } catch {}
  }
  return v;
})();

function hash8(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

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

// --- DEV ONLY: wire up logs + expose window.peek/window.__pc ---
// --- DEV ONLY: wire up logs + expose window.peek/window.__pc ---
function wireRtcDebug(
  pc: RTCPeerConnection,
  role: "caller" | "callee",
  callId?: string
) {
  // prevent double-wiring the same PC
  if ((pc as any).__gnetWired) return pc;
  (pc as any).__gnetWired = true;

  // if RTC_DEBUG is explicitly set to false, suppress console noise,
  // but still wire peek/stats helpers
  const rtcDebugFlag = (window as any).RTC_DEBUG;
  const loggingEnabled = rtcDebugFlag === undefined ? true : !!rtcDebugFlag;

  const tag = `[RTC:${role}]`;
  const log = (...a: any[]) => {
    if (!loggingEnabled) return;
    console.log(tag, ...a);
  };

  const expose = () => {
    (window as any).__pc = pc;
    if (callId) (window as any).__callId = callId;
    (window as any).__role = role;
    (window as any).peek = () => ({
      callId: (window as any).__callId ?? null,
      role: (window as any).__role ?? null,
      signaling: pc.signalingState,
      ice: pc.iceConnectionState,
      conn: pc.connectionState,
      local: pc.localDescription?.type,
      remote: pc.remoteDescription?.type,
      cand: (window as any).__candType ?? null,
      senders: pc
        .getSenders()
        .map((s) => s.track?.kind)
        .filter(Boolean),
      receivers: pc
        .getReceivers()
        .map((r) => r.track?.kind)
        .filter(Boolean),
    });
  };

  // initial exposure
  expose();

  // Core state-change logging
  pc.addEventListener("negotiationneeded", () => log("negotiationneeded"));
  pc.addEventListener("signalingstatechange", () => {
    expose();
    log("signaling:", pc.signalingState);
  });
  pc.addEventListener("icegatheringstatechange", () =>
    log("icegathering:", pc.iceGatheringState)
  );
  pc.addEventListener("iceconnectionstatechange", () =>
    log("iceconnection:", pc.iceConnectionState)
  );
  pc.addEventListener("connectionstatechange", () =>
    log("connection:", pc.connectionState)
  );

  pc.addEventListener("track", (ev: RTCTrackEvent) => {
    const t = ev.track;
    log(
      "track:",
      t?.kind,
      t?.id,
      "enabled:",
      t?.enabled,
      "muted:",
      (t as any)?.muted ?? false
    );
  });

  pc.addEventListener("icecandidate", (ev) => {
    const cand = ev.candidate?.candidate || "";
    const typ = / typ (\w+)/.exec(cand)?.[1];
    if (typ) (window as any).__candType = typ;
    log("icecandidate:", typ || "none");
  });

  (pc as any).onicecandidateerror = (e: any) =>
    log("icecandidateerror", e?.errorCode, e?.errorText || e);

  // quick stats sampler (call pc.__startStats() in dev tools to start)
  let statsTimer: any = null;
  (pc as any).__startStats = (interval = 1500) => {
    if (statsTimer) return;
    statsTimer = setInterval(async () => {
      try {
        const rpt = await pc.getStats();
        let inbound: any, outbound: any, rtt: any;
        rpt.forEach((s: any) => {
          if (s.type === "remote-inbound-rtp" && s.kind === "audio")
            rtt = s.roundTripTime;
          if (s.type === "inbound-rtp" && s.kind === "audio") inbound = s;
          if (s.type === "outbound-rtp" && s.kind === "audio") outbound = s;
        });
        log("stats:", {
          inBytes: inbound?.bytesReceived,
          outBytes: outbound?.bytesSent,
          rtt,
        });
      } catch {
        // ignore stats errors in dev
      }
    }, interval);
  };

  (pc as any).__stopStats = () => {
    if (statsTimer) clearInterval(statsTimer);
    statsTimer = null;
  };

  return pc;
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
  | {
      id: string;
      ts: number;
      kind: "text";
      from?: string;
      to?: string;
      text: string;
    }
  | {
      id: string;
      ts: number;
      kind: "voice";
      from?: string;
      to?: string;
      mime: string;
      data_b64: string;
      durMs?: number;
      name?: string;
      size?: number;
    };

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
  // ── Voice note (file-attach path)
  {
    const vn =
      cap?.voice_note ??
      envelope?.capsule?.voice_note ??
      ev?.voice_note;

    if (vn && (vn.data_b64 || vn.bytes_b64 || vn.b64)) {
      const idBase = evId || `${vn.ts ?? ts}:${vn.mime ?? "audio/webm"}`;
      const id = `vn:${idBase}`;
      const mime = vn.mime || vn.codec || "audio/webm";
      const data_b64 = vn.data_b64 || vn.bytes_b64 || vn.b64 || "";

      const name: string | undefined =
        typeof vn.name === "string" && vn.name.trim()
          ? vn.name
          : undefined;

      const size: number | undefined =
        typeof vn.size === "number"
          ? vn.size
          : undefined;

      return {
        id,
        ts: vn.ts ? Math.round(vn.ts) : ts,
        kind: "voice",
        from,
        to,
        mime,
        data_b64,
        ...(name ? { name } : {}),
        ...(size !== undefined ? { size } : {}),
      } as NormalizedMsg;
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

  const [showText, setShowText] = useState(true);
  const [showVoice, setShowVoice] = useState(true);
  const [showCall, setShowCall] = useState(true);
  const [showSystem, setShowSystem] = useState(true);

  // Per-tab agent id (used in lock ownership + X-Agent-Id)
  const AGENT_ID = useMemo(() => {
    let id = sessionStorage.getItem("gnet:agentId");
    if (!id) {
      id = "chat-thread:" + Math.random().toString(36).slice(2, 10);
      try { sessionStorage.setItem("gnet:agentId", id); } catch {}
    }
    return id;
  }, []);

  const [identity, setIdentity] = useState<AgentIdentity | null>(null);

  useEffect(() => {
    let cancelled = false;

    getIdentity()
      .then((id) => {
        if (!cancelled) setIdentity(id);
      })
      .catch((err) => {
        console.warn("[identity] failed to init", err);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // 👇 RIGHT HERE: derive fallback + active IDs
  const FALLBACK_AGENT_ID = AGENT_ID;   // old per-tab id
  const FALLBACK_OWNER_WA = OWNER_WA;   // from getOwnerWa()

  const ACTIVE_AGENT_ID = identity?.agentId || FALLBACK_AGENT_ID;
  const ACTIVE_OWNER_WA = identity?.wa || FALLBACK_OWNER_WA;

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

  const [showVisits, setShowVisits] = useState(false);

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
  // Keep a per-session de-dupe set for WS-delivered message IDs
  const seenRxIdsRef = useRef<Set<string>>(new Set());

  // ──────────────────────────────────────────────────────────────
    // TEMP: direct WS subscriber (chat + voice_note + signaling with de-dupe)
  // ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!topicWa) return;

    const wsUrl =
      `${location.origin.replace(/^http/, "ws")}` +
      `/ws/glyphnet?topic=${encodeURIComponent(topicWa)}&kg=${graph}&token=dev-token`;

    const ws = new WebSocket(wsUrl);

    const norm = (s?: string) =>
      String(s || "").toLowerCase().replace(/^ucs:\/\//, "").replace(/\/+$/, "");

    const matchesTopic = (rec?: string) => {
      if (!rec) return true;
      const a = norm(rec), b = norm(topicWa);
      return a === b || a.endsWith("/" + b) || b.endsWith("/" + a);
    };

    const onMessage = (e: MessageEvent) => {
      let frame: any;
      try { frame = JSON.parse(e.data as any); } catch { return; }
      if (!frame) return;

      const env: any  = frame?.envelope ?? frame ?? {};
      const cap: any  = env?.capsule   ?? frame?.capsule ?? {};
      const meta: any = env?.meta      ?? frame?.meta    ?? {};
      const msgId: string | undefined = env?.msg_id || env?.id || frame?.msg_id;

      const sender = meta?.trace_id || env?.from || frame?.from || "";

      // ───────── SIGNALING over WS (offer/answer/ice/cancel/reject/end) ─────────
      {
        let sig: any = null;

        // native caps?
        if (
          cap?.voice_offer || cap?.voice_answer || cap?.ice ||
          cap?.voice_cancel || cap?.voice_reject || cap?.voice_end
        ) {
          sig = cap;
        } else {
          // packed in glyph string?
          const gs: string[] | undefined =
            (Array.isArray(cap?.glyphs) ? cap.glyphs : undefined) ??
            (Array.isArray(cap?.glyph_stream) ? cap.glyph_stream : undefined);
          if (gs) {
            for (const g of gs) {
              const m = typeof unpackSig === "function" ? unpackSig(g) : null;
              if (
                m && (m.voice_offer || m.voice_answer || m.ice ||
                      m.voice_cancel || m.voice_reject || m.voice_end)
              ) { sig = m; break; }
            }
          }
        }

        if (sig) {
          // ignore self-echo
          if (String(sender) === String(AGENT_ID)) return;

          // topic / kg filter
          const rec = env?.recipient || env?.to || meta?.topicWa || "";
          if (!matchesTopic(rec)) return;
          const gRx = env?.graph || meta?.graph;
          if (gRx && gRx !== graph) return;

          // de-dupe
          const key = typeof sigKey === "function" ? sigKey(sig) : JSON.stringify(sig).slice(0, 512);
          if (sigSeenInRef.current.has(key)) return;
          sigSeenInRef.current.add(key);

          handleInboundSig(sig, meta);
          return; // handled
        }
      }

      // ───────── VOICE NOTE (live fanout) ─────────
      if (cap?.voice_note) {
        const v = cap.voice_note;
        const rec = env?.recipient || env?.to || meta?.topicWa || "";
        if (!matchesTopic(rec)) return;
        const gRx = env?.graph || meta?.graph;
        if (gRx && gRx !== graph) return;

        // ignore 100% identical payloads
        const sig = `vf|${String(v.mime || "")}|${String(v.data_b64 || v.bytes_b64 || v.b64 || "").slice(0, 16)}|${Math.floor((Number(v.ts) || 0) / 3000)}`;
        if (seenSigRef.current.has(sig)) return;
        seenSigRef.current.add(sig);
        if (msgId) seenRef.current.add(msgId);

        setThread((prev) => {
          const id =
            msgId ||
            `rx-voice:${v.ts || Date.now()}:${Math.random().toString(36).slice(2, 6)}`;
          if (prev.some((m) => m.id === id)) return prev;

          const next = [
            ...prev,
            {
              id,
              kind: "voice",
              ts: Number(v.ts) || Date.now(),
              from: sender || "remote",
              mime: String(v.mime || "audio/webm"),
              data_b64: String(v.data_b64 || v.bytes_b64 || v.b64 || ""),
              ...(typeof v.name === "string" && v.name.trim()
                ? { name: v.name }
                : {}),
              ...(typeof v.size === "number" ? { size: v.size } : {}),
            } as NormalizedMsg,
          ].sort((a, b) => (a.ts || 0) - (b.ts || 0));

          try {
            sessionStorage.setItem(storageKey, JSON.stringify(next));
          } catch {}
          return next;
        });
        return;
      }

      // ───────────── CHAT fanout (ephemeral for OTHER tabs only) ─────────────
      const cm = cap?.chat_message ?? env?.capsule?.chat_message ?? frame?.chat_message;
      if (cm && typeof cm.text === "string" && cm.text.trim()) {
        const at   = Math.round(Number(cm.at ?? Date.now()));
        const text = cm.text.trim();

        // 👇 NEW: ignore our own fanout (sender already shows optimistic bubble)
        const from   = cm.from ?? meta?.trace_id ?? env?.from ?? "";
        const rxConn = meta?.conn_id ?? env?.meta?.conn_id ?? null; // requires withConnMeta on send
        const isSelf = String(from) === String(AGENT_ID) || (!!WS_ID && rxConn === WS_ID);
        if (isSelf) return;

        // If canonical exists already, skip
        const hasCanonical = thread.some(m =>
          m?.kind === "text" &&
          !String(m.id).startsWith("local:") &&
          (m as any).text === text &&
          Math.abs((m.ts || 0) - at) <= 15000
        );
        if (hasCanonical) return;

        // Avoid duplicate ephemerals using a coarse signature
        const sig = `txt|${text}|${Math.floor(at / 5000)}`;
        const priorLocalId = ephTextMapRef.current.get(sig);
        if (priorLocalId && thread.some(m => m.id === priorLocalId)) return;

        const localId = `local:fanout:${at}:${Math.random().toString(36).slice(2, 6)}`;
        ephTextMapRef.current.set(sig, localId);

        setThread(prev => {
          const next = [
            ...prev,
            { id: localId, ts: at, kind: "text", from: cm.from, text } as NormalizedMsg,
          ].sort((a, b) => (a.ts || 0) - (b.ts || 0));
          try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
          return next;
        });
        return;
      }

      // ───────── Persisted/canonical path (leave your existing normalizeIncoming flow) ─────────
      const nm = normalizeIncoming(frame);
      if (!nm) return;

      const sigKey2 =
        nm.kind === "text"
          ? `txt|${(nm as any).text}|${Math.floor((nm.ts || 0) / 3000)}`
          : `vf|${(nm as any).mime}|${(nm as any).data_b64?.slice?.(0, 16)}|${Math.floor((nm.ts || 0) / 3000)}`;

      setThread((prev) => {
        if (prev.some((p) => p.id === nm.id)) return prev;
        if (seenSigRef.current.has(sigKey2)) return prev;
        const next = [...prev, nm].sort((a, b) => (a.ts || 0) - (b.ts || 0));
        try { sessionStorage.setItem(storageKey, JSON.stringify(next)); } catch {}
        seenRef.current.add(nm.id);
        seenSigRef.current.add(sigKey2);
        return next;
      });
    };

    ws.addEventListener("message", onMessage);
    ws.addEventListener("error", (e) => console.log("[WS] error", e));
    ws.addEventListener("open", () => console.log("[WS] open", wsUrl));
    return () => { try { ws.removeEventListener("message", onMessage); ws.close(); } catch {} };
  }, [topicWa, graph, storageKey, thread.length]);
  // ───────────────────────────────────────────────────────────────────────────────

  // Address input mirrors topic and stays in sync
  const [addrInput, setAddrInput] = useState<string>(topic || "");
  useEffect(() => setAddrInput(topic || ""), [topic]);

  const [floorOwned, setFloorOwned] = useState(false);
  // Safety net: if the tab loses focus or becomes hidden, make sure we stop
  useEffect(() => {
    const onBlur = () => { if (pttDownRef.current || floorOwned) stopPTT(); };
    const onVis = () => { if (document.hidden && (pttDownRef.current || floorOwned)) stopPTT(); };
    window.addEventListener("blur", onBlur);
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [floorOwned]); // stopPTT is a function declaration, safe to reference

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

  // PTT pointer management
  const micRef = useRef<HTMLButtonElement | null>(null);
  const activePointerIdRef = useRef<number | null>(null);

  const handlePointerDownPTT = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (micDisabled) return;
    e.preventDefault();
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch {}
    activePointerIdRef.current = e.pointerId;
    startPTT(); // sets pttDownRef.current = true internally
  };

  const handlePointerUpPTT = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (activePointerIdRef.current !== null && e.pointerId === activePointerIdRef.current) {
      e.preventDefault();
      activePointerIdRef.current = null;
      stopPTT();
    }
  };

  const handlePointerCancelPTT = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (activePointerIdRef.current !== null && e.pointerId === activePointerIdRef.current) {
      activePointerIdRef.current = null;
      stopPTT();
    }
  };

  const handleKeyDownPTT = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.code === "Space" && !micDisabled && !pttDownRef.current) {
      e.preventDefault();
      startPTT();
    }
  };

  const handleKeyUpPTT = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.code === "Space") {
      e.preventDefault();
      stopPTT();
    }
  };

  // —— signaling de-dupe + tiny queues ——
  const appliedOffersRef  = useRef<Set<string>>(new Set());
  const appliedAnswersRef = useRef<Set<string>>(new Set());
  const addedIceRef       = useRef<Set<string>>(new Set()); // key `${callId}|${candidate}`

  // queues keyed by call_id
  const queuedIceRef      = useRef<Map<string, RTCIceCandidateInit[]>>(new Map());
  const pendingAnswerRef  = useRef<Map<string, RTCSessionDescriptionInit>>(new Map());

  // add (or queue) ICE until remoteDescription exists
  function maybeAddIce(pc: RTCPeerConnection, cand: RTCIceCandidateInit, callId: string) {
    const key = `${callId}|${cand.candidate}`;
    if (addedIceRef.current.has(key)) return;

    if (!pc.remoteDescription) {
      const list = queuedIceRef.current.get(callId) || [];
      list.push(cand);
      queuedIceRef.current.set(callId, list);
      return;
    }

    pc.addIceCandidate(cand).catch((e) => console.warn("[RTC] addIceCandidate", e));
    addedIceRef.current.add(key);
  }

  // flush queued ICE once remoteDescription is set
  function flushQueuedIce(pc: RTCPeerConnection, callId: string) {
    const list = queuedIceRef.current.get(callId);
    if (!list?.length) return;

    for (const c of list) {
      const key = `${callId}|${c.candidate}`;
      if (!addedIceRef.current.has(key)) {
        pc.addIceCandidate(c).catch((e) => console.warn("[RTC] addIceCandidate/flush", e));
        addedIceRef.current.add(key);
      }
    }
    queuedIceRef.current.delete(callId);
  }

  function takeQueuedAnswer(callId: string): RTCSessionDescriptionInit | undefined {
    const d = pendingAnswerRef.current.get(callId);
    if (d) pendingAnswerRef.current.delete(callId);
    return d;
  }

  // one-shot cleanup between calls
  function cleanupCallSets() {
    appliedOffersRef.current.clear();
    appliedAnswersRef.current.clear();
    addedIceRef.current.clear();
    queuedIceRef.current.clear();
    pendingAnswerRef.current.clear();
  }

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
  const ephTextMapRef = useRef<Map<string, string>>(new Map());
  const sigSeenInRef = useRef<Set<string>>(new Set());

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

  const inCall =
  callState === "offering" || callState === "connecting" || callState === "connected";

  const micDisabled = (!!floorBusyBy && !floorOwned) || inCall;

  // Call duration timer
  const [callSecs, setCallSecs] = useState(0);
  const callTimerRef = useRef<number | null>(null);
  const callStartedAtRef = useRef<number | null>(null);

  function callSecsNow(): number {
    return callStartedAtRef.current ? Math.max(0, Math.round((Date.now() - callStartedAtRef.current) / 1000)) : 0;
  }
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
      if (!e.candidate) return;
      const t = /candidate:.* typ (\w+)/.exec(e.candidate.candidate)?.[1] || "";
      if (t) setLastCandType(t);
      if (callIdRef.current) {
        try { sendIce(e.candidate.toJSON(), callIdRef.current).catch(() => {}); } catch {}
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
          handleSig(sig);           // ← actually process signaling
          continue;                 // do not render signaling
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

// Call UI state
const [incoming, setIncoming] = useState<boolean>(false);

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
      ownerWa: ACTIVE_OWNER_WA,    // <- identity.wa or fallback OWNER_WA
      topicWa: topicWa,
      text: msg,
      ts: now,
      agentId: ACTIVE_AGENT_ID,    // <- identity.agentId or fallback AGENT_ID
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
      ownerWa: ACTIVE_OWNER_WA,   // <- from identity.ts (wa) or fallback
      topicWa,                    // topicWa: topicWa is redundant, shorthand is fine
      mime,
      data_b64,
      durMs: undefined,
      ts: Date.now(),
      agentId: ACTIVE_AGENT_ID,   // <- from identity.agentId or fallback
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
      try {
        setTranscribing(true);
        // IMPORTANT: in this function the variables are `mime` and `data_b64`
        const t = await transcribeAudio(mime, data_b64); // expects { text, engine }
        setTranscribing(false);

        if (t?.text) {
          const txMeta = withConnMeta({
            trace_id: AGENT_ID,
            graph,
            t0: Date.now(),
            transcript_of: j?.msg_id || null,
            engine: t.engine || undefined,
          });

          // send the text bubble into the thread
          await postTx(
            base,
            { recipient: topicWa, graph, capsule: { glyphs: [t.text] }, meta: txMeta },
            headers
          ).catch(() => {});

          // journal transcript to the KG
          emitTranscriptPosted({
            apiBase: KG_API_BASE,
            kg: graph,
            ownerWa: ACTIVE_OWNER_WA,          // ✅ identity-based owner
            topicWa,
            text: t.text,
            transcript_of: j?.msg_id || null,
            engine: t.engine,
            ts: Date.now(),
            agentId: ACTIVE_AGENT_ID,          // ✅ identity-based agent
          }).catch(() => {});
        }
      } catch {
        setTranscribing(false);
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
  // ───────────────── RTC debug helpers ─────────────────


  function exposePeerDebug(pc: RTCPeerConnection | null, role: "caller" | "callee") {
    (window as any).__pc = pc || null;
    (window as any).__role = role;
    (window as any).__callId = callIdRef.current || null;
    (window as any).peek = () => {
      const p = pcRef.current;
      return p ? {
        callId: callIdRef.current,
        role,
        signaling: p.signalingState,
        ice: p.iceConnectionState,
        conn: p.connectionState,
        local: p.localDescription?.type,
        remote: p.remoteDescription?.type,
      } : null;
    };
  }

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

  // helper (place once near your other refs/helpers)
  const queueAnswer = (callId: string, desc: RTCSessionDescriptionInit) => {
    pendingAnswerRef.current.set(callId, desc);
  };

  // Legacy wrapper — route everything to the single signaling handler to avoid races.
  async function handleInboundSig(sig: any, _meta: any = {}) {
    return handleSig(sig); // all OFFER/ANSWER/ICE/CANCEL handled inside handleSig
  }

  // ——— Call functions ———
  async function sendOffer(sdp: string, callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,      // ✅ identity WA
        topicWa,
        call_id: callId,
        kind: "offer",
        ice_type: undefined,
        secs: 0,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,      // ✅ identity agentId
      }).catch(() => {});
    } catch {}
    return txSig({ voice_offer: { sdp, call_id: callId } } satisfies VoiceOffer);
  }

  async function sendAnswer(sdp: string, callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,      // ✅
        topicWa,
        call_id: callId,
        kind: "answer",
        ice_type: undefined,
        secs: 0,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,      // ✅
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
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,     // ✅ use identity WA
        topicWa,
        call_id: callId,
        kind: "cancel",
        ice_type: undefined,
        secs: 0,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,     // ✅ use identity agentId
      }).catch(() => {});
    } catch {}
    return txSig({ voice_cancel: { call_id: callId } } as VoiceCancel);
  }

  async function sendReject(callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,     // ✅
        topicWa,
        call_id: callId,
        kind: "reject",
        ice_type: undefined,
        secs: 0,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,     // ✅
      }).catch(() => {});
    } catch {}
    return txSig({ voice_reject: { call_id: callId } } as VoiceReject);
  }

  async function sendEnd(callId: string) {
    try {
      emitCallState({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,     // ✅
        topicWa,
        call_id: callId,
        kind: "end",
        ice_type: lastCandType || undefined,
        secs: callSecsRef.current || 0,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,     // ✅
      }).catch(() => {});
    } catch {}
    return txSig({ voice_end: { call_id: callId } } as VoiceEnd);
  }

  // ───────────────── startCall — with RTC debug wiring ─────────────────

  // Helper: prefer OPUS and disable DTX on the sender (safe if unsupported)
  async function configureAudioSender(pc: RTCPeerConnection) {
    try {
      const tx = pc.getTransceivers?.().find(tr => tr.sender?.track?.kind === "audio");
      const caps = RTCRtpReceiver.getCapabilities?.("audio");
      if (tx?.setCodecPreferences && caps?.codecs?.length) {
        const opus = caps.codecs.filter(c => /opus/i.test(c.mimeType));
        const rest = caps.codecs.filter(c => !/opus/i.test(c.mimeType));
        tx.setCodecPreferences([...opus, ...rest]);
      }

      const snd = pc.getSenders?.().find(s => s.track?.kind === "audio");
      if (snd?.getParameters) {
        const p = snd.getParameters();
        p.encodings = p.encodings || [{}];
        (p.encodings[0] as any).dtx = false; // keep frames flowing while speaking
        await snd.setParameters(p).catch(() => {});
      }
    } catch {}
  }

  async function handleSig(sig: any) {
    const pc = pcRef.current;

    // -------- OFFER (callee path) --------
    if (sig?.voice_offer) {
      const { sdp, call_id } = sig.voice_offer;
      if (appliedOffersRef.current.has(call_id)) return;

      // queue it for UI "Accept"
      pendingOfferRef.current = { sdp, call_id };
      try { ringAudio.current?.play?.().catch(()=>{}); } catch {}
      setCallState(s => (s === "idle" ? "ringing" : s));
      return;
    }

    // -------- ANSWER (caller only) --------
    if (sig?.voice_answer) {
      const incomingId = sig.voice_answer.call_id || "";
      const currentId  = callIdRef.current || "";
      const pc         = pcRef.current;

      // Always parse once
      const desc: RTCSessionDescriptionInit =
        typeof sig.voice_answer.sdp === "string"
          ? JSON.parse(sig.voice_answer.sdp)
          : sig.voice_answer.sdp;

      // Debug breadcrumb (safe to keep)
      console.debug("[ANSWER] recv", {
        incomingId,
        currentId,
        callState,
        pcState: pc?.signalingState,
        applied: appliedAnswersRef.current.has(incomingId),
      });

      // Hard guards — ignore strays/late echoes
      if (!pc)                           return;                     // no peer
      if (!incomingId || incomingId !== currentId) return;           // not our call
      if (appliedAnswersRef.current.has(incomingId)) return;         // already applied
      if (callState !== "offering")          return;                 // caller only
      if (pc.signalingState !== "have-local-offer") return;          // only valid window

      try {
        await pc.setRemoteDescription(desc);
        appliedAnswersRef.current.add(incomingId);
        flushQueuedIce(pc, incomingId);                               // no await
      } catch (e) {
        console.warn("[RTC] setRemoteDescription(answer) failed", e);
      }
      return;
    }

    // -------- ICE (both paths) --------
    if (sig?.ice?.candidate) {
      const callId = sig.ice.call_id || callIdRef.current || "";
      const cand: RTCIceCandidateInit = sig.ice.candidate;
      const key = `${callId}|${cand.candidate}`;
      if (addedIceRef.current.has(key)) return;

      if (pc && pc.remoteDescription) {
        try { await pc.addIceCandidate(cand); addedIceRef.current.add(key); }
        catch (e) { console.warn("[RTC] addIceCandidate failed", e); }
      } else {
        const arr = queuedIceRef.current.get(callId) || [];
        arr.push(cand);
        queuedIceRef.current.set(callId, arr);
      }
      return;
    }

    // -------- CANCEL / REJECT / END --------
    if (sig.voice_cancel || sig.voice_reject || sig.voice_end) {
      // derive call id + kind
      const cid =
        sig.voice_cancel?.call_id ||
        sig.voice_reject?.call_id ||
        sig.voice_end?.call_id ||
        callIdRef.current ||
        pendingOfferRef.current?.call_id ||
        (window as any).__callId ||
        "n/a";

      const kind: "cancel" | "reject" | "end" =
        sig.voice_cancel ? "cancel" : (sig.voice_reject ? "reject" : "end");

      // duration (fallback if callSecsNow() isn't defined)
      const secsNow =
        typeof (callSecsNow as any) === "function"
          ? (callSecsNow as any)()
          : (callStartedAtRef?.current
              ? Math.max(0, Math.round((Date.now() - callStartedAtRef.current) / 1000))
              : 0);

      // journal to KG (use live identity)
      try {
        emitCallState({
          apiBase: KG_API_BASE,
          kg: graph,
          ownerWa: ACTIVE_OWNER_WA,   // ✅ identity.wa
          topicWa,
          call_id: cid,
          kind,
          secs: secsNow,
          ts: Date.now(),
          agentId: ACTIVE_AGENT_ID,   // ✅ identity.agentId
        }).catch(() => {});
      } catch {}

      // return UI to idle (your reset handles timers/pc/refs)
      resetCallLocalState("idle");
      return;
    }
  }

  async function startCall() {
    if (callState !== "idle") return;

    // clean slate for this call
    cleanupCallSets();

    const callId =
      crypto?.randomUUID?.() || `call-${Date.now()}-${Math.random().toString(36).slice(2,6)}`;
    callIdRef.current = callId;
    setCallState("offering");

    // KG: record outbound offer (use live identity)
    emitCallState({
      apiBase: KG_API_BASE,
      kg: graph,
      ownerWa: ACTIVE_OWNER_WA,        // ✅ identity.wa
      topicWa,
      call_id: callId,                 // use the local var; equals callIdRef.current
      kind: "offer",
      ts: Date.now(),
      agentId: ACTIVE_AGENT_ID,        // ✅ identity.agentId
    }).catch(() => {});

    const { stream } = await ensureMicPTT({ force: false });

    const pc = await makePeer(
      "caller",
      {
        onLocalDescription: (sdp) => sendOffer(JSON.stringify(sdp), callId),
        onLocalIce: (cand) => sendIce(cand, callId),
        onRemoteTrack: (ms) => {
          const el = remoteAudioRef.current;
          if (!el) return;
          try {
            el.srcObject = ms;
            el.autoplay = true;
            el.muted = false;
            el.volume = 1;
            el.play?.().catch(() => {});
          } catch {}
        },
      },
      { iceServers }
    );

    // 🔎 debug taps (caller)
    wireRtcDebug(pc, "caller");
    exposePeerDebug(pc, "caller");   // if you kept this helper
    (window as any).__callId = callId;

    pc.onicecandidateerror = (e: any) => console.warn("[RTC:caller] icecandidateerror", e?.errorCode, e?.errorText || e);

    pc.onsignalingstatechange = async () => {
      // If an answer arrived early, apply it once we have-local-offer
      if (pc.signalingState === "have-local-offer") {
        const queued = pendingAnswerRef.current.get(callId);
        if (queued && !appliedAnswersRef.current.has(callId)) {
          try {
            await pc.setRemoteDescription(queued);
            appliedAnswersRef.current.add(callId);
            pendingAnswerRef.current.delete(callId);

            // remote desc is set → flush any queued ICE from caller
            flushQueuedIce(pc, callId);
          } catch (e) {
            console.warn("[RTC] apply queued answer failed", e);
          }
        }
      }
    };

    pc.onconnectionstatechange = () => {
      const s = pc.connectionState;

      if (s === "connected") {
        setCallState("connected");
        // mark start time for duration calc
        if (callStartedAtRef?.current == null) {
          callStartedAtRef.current = Date.now();
        }
        if (callIdRef.current) {
          emitCallState({
            apiBase: KG_API_BASE,
            kg: graph,
            ownerWa: ACTIVE_OWNER_WA,                // ✅ identity.wa
            topicWa,
            call_id: callIdRef.current!,
            kind: "connected",
            ice_type: lastCandType || undefined,
            secs: 0,
            ts: Date.now(),
            agentId: ACTIVE_AGENT_ID,                // ✅ identity.agentId
          }).catch(() => {});
        }
        return;
      }

      if (s === "failed" || s === "closed" || s === "disconnected") {
        // compute duration if we have a start time
        const started = callStartedAtRef?.current || null;
        const secs =
          started ? Math.max(0, Math.round((Date.now() - started) / 1000)) : 0;

        if (callIdRef.current) {
          emitCallState({
            apiBase: KG_API_BASE,
            kg: graph,
            ownerWa: ACTIVE_OWNER_WA,                 // ✅ identity.wa
            topicWa,
            call_id: callIdRef.current!,
            kind: "end",
            ice_type: lastCandType || undefined,
            secs,
            ts: Date.now(),
            agentId: ACTIVE_AGENT_ID,                 // ✅ identity.agentId
          }).catch(() => {});
        }

        setCallState("ended");
        return;
      }
    };

    // ensure local track is hot
    const a = stream.getAudioTracks?.()[0];
    if (a) {
      a.enabled = true;
      try {
        await a.applyConstraints({ echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } as any);
      } catch {}
    }

    try { stream.getTracks().forEach(t => pc.addTrack(t, stream)); } catch {}
    rememberLocalMicTrack(stream);
    await configureAudioSender(pc).catch(()=>{});
    pcRef.current = pc;

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

    // clean slate for this call
    cleanupCallSets();
    appliedOffersRef.current.add(offer.call_id);

    callIdRef.current = offer.call_id;
    setCallState("connecting");

    const { stream } = await ensureMicPTT({ force: false });

    const pc = await makePeer(
      "callee",
      {
        onLocalDescription: (sdp) => sendAnswer(JSON.stringify(sdp), offer.call_id),
        onLocalIce: (cand) => sendIce(cand, offer.call_id),
        onRemoteTrack: (ms) => {
          const el = remoteAudioRef.current;
          if (!el) return;
          try {
            el.srcObject = ms;
            el.autoplay = true;
            el.muted = false;
            el.volume = 1;
            el.play?.().catch(() => {});
          } catch {}
        },
      },
      { iceServers }
    );

    // 🔎 debug taps (callee)
    wireRtcDebug(pc, "callee");
    exposePeerDebug(pc, "callee");
    (window as any).__callId = offer.call_id;

    pc.onicecandidateerror = (e: any) => console.warn("[RTC:callee] icecandidateerror", e?.errorCode, e?.errorText || e);

    pc.onconnectionstatechange = () => {
      const s = pc.connectionState;
      if (s === "connected") {
        setCallState("connected");
        if (callIdRef.current) {
          emitCallState({
            apiBase: KG_API_BASE,
            kg: graph,
            ownerWa: ACTIVE_OWNER_WA,                // ✅ use live identity WA
            topicWa,
            call_id: callIdRef.current,
            kind: "connected",
            ice_type: lastCandType || undefined,
            secs: 0,
            ts: Date.now(),
            agentId: ACTIVE_AGENT_ID,                // ✅ use live identity agentId
          }).catch(() => {});
        }
      }
      if (s === "failed" || s === "closed" || s === "disconnected") {
        setCallState("ended");
      }
    };

    // hot local track
    const a = stream.getAudioTracks?.()[0];
    if (a) {
      a.enabled = true;
      try {
        await a.applyConstraints({ echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } as any);
      } catch {}
    }

    try { stream.getTracks().forEach(t => pc.addTrack(t, stream)); } catch {}
    rememberLocalMicTrack(stream);
    await configureAudioSender(pc).catch(()=>{});
    pcRef.current = pc;

    try {
      const desc =
        typeof offer.sdp === "string" ? JSON.parse(offer.sdp) : offer.sdp;

      await pc.setRemoteDescription(desc);
      appliedOffersRef.current.add(offer.call_id);

      // create + send the local ANSWER via makePeer's onLocalDescription
      await (pc as any)._emitLocalDescription("answer");

      // KG: record that we answered
      emitCallState({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,          // ✅ identity WA
        topicWa,
        call_id: callIdRef.current!,
        kind: "answer",
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,          // ✅ identity agentId
      }).catch(() => {});

      // remote desc is set → flush any queued ICE from caller
      flushQueuedIce(pc, offer.call_id);
    } catch (e) {
      console.error("Failed to accept call:", e);
      setCallState("ended");
      return;
    }

    // stop ringing + clear
    try {
      const el = ringAudio.current;
      if (el) { el.pause(); try { el.currentTime = 0; } catch {} }
    } catch {}
    pendingOfferRef.current = null;
  }

  // End the call (local end signal + full teardown)
  async function endCall() {
    const id = callIdRef.current;

    // Stop media & close PC first
    try { pcRef.current?.getSenders?.().forEach(s => s.track?.stop?.()); } catch {}
    try { pcRef.current?.close?.(); } catch {}

    // ⬇️ teardown snapshot (before nulling refs)
    try { (window as any).__lastPeer = (window as any).peek?.(); } catch {}
    (window as any).__pc = null;
    (window as any).__callId = null;

    // Clear refs
    pcRef.current = null;
    callIdRef.current = null;

    // Signal end to peer (ok after closing local PC)
    try { if (id) await sendEnd(id); } catch {}

    // Optional: summary + cleanup
    try { logCallSummary?.("local"); } catch {}
    try { cleanupCallSets?.(); } catch {}

    // Return UI to ready state (phone icon)
    try { resetCallLocalState?.("idle"); } catch { setCallState("idle"); }
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

  function resetCallLocalState(next: CallState = "idle") {
    // stop call timer
    try { if (callTimerRef.current != null) { clearInterval(callTimerRef.current); callTimerRef.current = null; } } catch {}

    // stop tracks + close pc
    try { pcRef.current?.getSenders?.().forEach(s => s.track?.stop?.()); } catch {}
    try { pcRef.current?.close?.(); } catch {}
    pcRef.current = null;

    // clear call ids
    callIdRef.current = null;

    // stop any ringing
    try { const el = ringAudio.current; if (el) { el.pause(); try { el.currentTime = 0; } catch {} } } catch {}

    // clear remote audio sink
    try { if (remoteAudioRef.current) (remoteAudioRef.current as any).srcObject = null; } catch {}

    // reset flags
    origTrackRef.current = null;
    setMuted(false);
    setOnHold(false);
    setCallSecs(0);
    try { setLastCandType(""); } catch {}

    // wipe per-call de-dupe/queues
    cleanupCallSets(); // you already have this

    // final UI state
    setCallState(next);
  }

  // Hang up the call
  function hangupCall() {
    const cid = callIdRef.current || (window as any).__callId || null;
    const endKind =
      (callState === "offering" || callState === "connecting") ? "cancel" : "end";

    if (cid) {
      console.log("[hangupCall]", cid);
      if (callState === "offering" || callState === "connecting") {
        // cancel before remote answer
        sendCancel(cid).catch(err => console.error("[hangupCall] cancel failed:", err));
      } else if (callState === "connected") {
        // normal end after connect
        sendEnd(cid).catch(err => console.error("[hangupCall] end failed:", err));
      }
    }

    // --- emit call state to KG (end/cancel) ---
    try {
      const secsNow =
        typeof (callSecsNow as any) === "function"
          ? (callSecsNow as any)()
          : (callStartedAtRef?.current
              ? Math.max(0, Math.round((Date.now() - callStartedAtRef.current) / 1000))
              : 0);

      emitCallState({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,          // ✅ identity-based owner
        topicWa,
        call_id: cid || "n/a",
        kind: endKind,
        secs: secsNow,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,          // ✅ identity-based agentId
      }).catch(() => {});
    } catch {}

    // stop call timer if any
    try {
      if (callTimerRef.current != null) {
        clearInterval(callTimerRef.current);
        callTimerRef.current = null;
      }
    } catch {}

    // stop any ringing just in case
    try {
      const el = ringAudio.current;
      if (el) { el.pause(); try { el.currentTime = 0; } catch {} }
    } catch {}

    // local summary bubble
    logCallSummary("local");

    // --- teardown PC BEFORE nulling refs ---
    try { pcRef.current?.getSenders().forEach(s => s.track?.stop()); } catch {}
    try { pcRef.current?.close?.(); } catch {}

    // snapshot last peer (optional debug)
    try { (window as any).__lastPeer = (window as any).peek?.(); } catch {}
    (window as any).__pc = null;
    (window as any).__callId = null;

    // clear refs
    pcRef.current = null;
    callIdRef.current = null;

    // reset local mic/hold state
    origTrackRef.current = null;
    setMuted(false);
    setOnHold(false);

    // optional: clear any signaling queues
    try { cleanupCallSets?.(); } catch {}

    // back to idle so UI returns to phone icon
    resetCallLocalState("idle");
  }


  // Cancel the outbound call
  function cancelOutbound() {
    const cid = callIdRef.current || (window as any).__callId || null;

    if (cid) {
      console.log("[cancelOutbound] Cancelling outbound", cid);
      sendCancel(cid).catch(err => console.error("[cancelOutbound] cancel failed:", err));
    }

    // --- emit call state to KG (always "cancel" here) ---
    try {
      const secsNow =
        typeof (callSecsNow as any) === "function"
          ? (callSecsNow as any)()
          : (callStartedAtRef?.current
              ? Math.max(0, Math.round((Date.now() - callStartedAtRef.current) / 1000))
              : 0);

      emitCallState({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,      // ✅ identity-based owner
        topicWa,
        call_id: cid || "n/a",
        kind: "cancel",
        secs: secsNow,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,      // ✅ identity-based agent
      }).catch(() => {});
    } catch {}

    // stop call timer if any
    try {
      if (callTimerRef.current != null) {
        clearInterval(callTimerRef.current);
        callTimerRef.current = null;
      }
    } catch {}

    // stop any ringing just in case
    try {
      const el = ringAudio.current;
      if (el) { el.pause(); try { el.currentTime = 0; } catch {} }
    } catch {}

    // local summary bubble
    logCallSummary("local");

    // --- teardown PC BEFORE nulling refs ---
    try { pcRef.current?.getSenders().forEach(s => s.track?.stop()); } catch {}
    try { pcRef.current?.close?.(); } catch {}

    // snapshot last peer (optional debug)
    try { (window as any).__lastPeer = (window as any).peek?.(); } catch {}
    (window as any).__pc = null;
    (window as any).__callId = null;

    // clear refs
    pcRef.current = null;
    callIdRef.current = null;

    // reset local mic/hold state
    origTrackRef.current = null;
    setMuted(false);
    setOnHold(false);

    // optional: clear any signaling queues
    try { cleanupCallSets?.(); } catch {}

    // return to idle (not "ended") so user can place another call
    resetCallLocalState("idle");
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

  // ───────────────── Mic setup for PTT ─────────────────
  const [micReady, setMicReady] = useState(false);

  // Prefer WebM/Opus when supported; fall back to MP4/AAC on Safari/iOS.
  const MIME_PREFS = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4;codecs=mp4a.40.2",
  ];

  function pickMime(): string {
    const ok = (m: string) =>
      typeof MediaRecorder !== "undefined" &&
      typeof MediaRecorder.isTypeSupported === "function" &&
      MediaRecorder.isTypeSupported(m);
    for (const m of MIME_PREFS) if (ok(m)) return m;
    return "audio/webm";
  }

  /**
   * Ensure a hot microphone stream for PTT/calls.
   * Reuses the current stream when possible; pass {force:true} to recreate.
   */
  async function ensureMicPTT(
    opts: { force?: boolean } = {}
  ): Promise<{ stream: MediaStream; mime: string }> {
    // Reuse existing, keep track enabled
    if (streamRef.current && streamRef.current.active && !opts.force) {
      const t = streamRef.current.getAudioTracks?.()[0];
      if (t) t.enabled = true; // 🔊 ensure hot mic
      setMicReady(true);
      return { stream: streamRef.current, mime: pickMime() };
    }

    // Build constraints (respect selectedMicId if present)
    const constraints: MediaStreamConstraints = {
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
        ...(selectedMicId ? { deviceId: { exact: selectedMicId } } : {}),
      } as MediaTrackConstraints,
      video: false,
    };

    // Acquire a fresh stream
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    const t = stream.getAudioTracks?.()[0];

    if (t) {
      // Keep it live + apply helpful processing; ignore failures silently
      t.enabled = true; // 🔊
      t.applyConstraints?.({
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      } as MediaTrackConstraints).catch(() => {});
    }

    streamRef.current = stream;
    setMicReady(true);

    // After permission, device labels are available — refresh device list if you have the helper
    try {
      await navigator.mediaDevices.enumerateDevices();
      // @ts-ignore optional helper provided elsewhere
      refreshMics?.();
    } catch {}

    // Choose a working recorder mime for this UA
    const mime = pickMime();
    return { stream, mime };
  }

  function stopMeter() {
    if (meterRAF.current != null) cancelAnimationFrame(meterRAF.current);
    meterRAF.current = null;
    try {
      audioCtxRef.current?.close();
    } catch (e) {
      console.error("AudioContext close failed:", e);
    }
    audioCtxRef.current = null;
    setMicLevel(0);
  }

  function startMeter(stream: MediaStream) {
    stopMeter(); // stop previous meter before starting a new one
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

  const pttChannelRef = useRef<string>("");
  const seqRef = useRef<number>(0);
  useEffect(() => {
    // re-derive channel when topic changes so sessions don't collide
    pttChannelRef.current = `ch-${hash8(topicWa)}-${hash8(AGENT_ID)}`;
    seqRef.current = 0;
  }, [topicWa, AGENT_ID]);

  // ───────────────── startPTT (timeslice + requestData pulses) ─────────────────
  async function startPTT() {
    if (pttDownRef.current) return;

    pttDownRef.current = true;
    setAwaitingLock(true);
    setPttDown(true);

    // ── metrics: mark attempt start
    metricsRef.current.lastStart = Date.now();

    const resource = `voice:${topicWa}`;
    lockResourceRef.current = resource;

    // begin recording immediately so we don't lose audio while waiting on lock
    let stream: MediaStream | null = null;
    let mime: string = "audio/webm";
    chunksRef.current = [];

    try {
      const mic = await ensureMicPTT(); // { stream, mime }
      stream = mic.stream;
      mime   = mic.mime;
      try { startMeter(stream); } catch {}
    } catch {
      alert("Microphone permission is required for PTT.");
      pttDownRef.current = false;
      setPttDown(false);
      setAwaitingLock(false);
      metricsRef.current.lastStart = 0;
      return;
    }

    // ───────────────── MediaRecorder: start WITH timeslice + pulses ─────────────────
    try {
      let rec: MediaRecorder;
      try {
        rec = new MediaRecorder(stream!, { mimeType: mime || pickMime() });
      } catch {
        rec = new MediaRecorder(stream!); // fallback if UA rejects options
      }
      mrRef.current = rec;

      rec.onstart = () => console.log("[startPTT] recorder start", rec.mimeType);
      rec.onerror = (ev) => console.warn("[startPTT] recorder error", (ev as any)?.error || ev);
      rec.ondataavailable = (ev: BlobEvent) => {
        const ok = !!(ev?.data && ev.data.size > 0);
        if (ok) chunksRef.current.push(ev.data);
        console.log("[startPTT] dataavailable", ev?.data?.type, ev?.data?.size, ok ? "" : "— dropped");
      };

      // ✅ Timeslice makes Safari/iPhone actually flush audio
      rec.start(250);

      // Extra coax pulses (Safari sometimes ignores timeslice)
      const pulse = () => { try { rec.requestData(); } catch {} };
      const pulseId = window.setInterval(pulse, 500);
      rec.addEventListener("stop", () => { try { clearInterval(pulseId); } catch {} }, { once: true });
      (rec as any).__poke = pulse;
    } catch (e) {
      console.warn("[startPTT] MediaRecorder start failed:", e);
      pttDownRef.current = false;
      setPttDown(false);
      setAwaitingLock(false);
      return;
    }

    // try to acquire the floor in parallel
    let lockOutcome: "granted" | "denied" | "timeout" = "timeout";
    try { await sendLock("acquire", resource, 3500); } catch {}
    try { lockOutcome = await waitForLock(resource, 1500); } catch {}

    if (lockOutcome === "granted") {
      metricsRef.current.grants++;
      const tGrant = Date.now() - (metricsRef.current.lastStart || Date.now());
      metricsRef.current.lastAcquireMs = tGrant;
      lastAcquireMsRef.current = tGrant;
      lastGrantedRef.current = true;

      emitFloorLock({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,   // ✅ identity WA (fallbacks if not ready)
        topicWa,
        state: "held",
        acquire_ms: tGrant,
        granted: true,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,   // ✅ identity agentId (fallbacks if not ready)
      }).catch(() => {});

      setAwaitingLock(false);
      setFloorOwned(true);
      setFloorBusyBy(null);

      keepaliveRef.current = window.setInterval(() => {
        if (lockResourceRef.current) {
          sendLock("refresh", lockResourceRef.current, 3500).catch(() => {});
        }
      }, 2000);

    } else if (lockOutcome === "denied") {
      console.warn("[startPTT] lock denied — cancel PTT");
      metricsRef.current.denies++;
      lastGrantedRef.current = false;

      try { mrRef.current?.requestData?.(); } catch {}
      try { mrRef.current?.stop?.(); } catch {}
      mrRef.current = null;
      chunksRef.current = [];

      setAwaitingLock(false);
      setFloorOwned(false);
      pttDownRef.current = false;
      setPttDown(false);
      lockResourceRef.current = null;

      emitPttSession({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,                 // ✅ use active WA
        topicWa,
        talkMs: 0,
        grants: metricsRef.current.grants,
        denies: metricsRef.current.denies,
        lastAcquireMs: metricsRef.current.lastAcquireMs,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,                 // ✅ use active agentId
      }).catch(() => {});

      emitFloorLock({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,                 // ✅ use active WA
        topicWa,
        state: "denied",
        acquire_ms: 0,
        granted: false,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,                 // ✅ use active agentId
      }).catch(() => {});

      stopMeter();
      return;

    } else {
      // Timeout: proceed in soft-lock so dev flow keeps working
      console.warn("[startPTT] lock timeout — proceeding (soft-lock)");
      setAwaitingLock(false);
      setFloorOwned(true);
      lastGrantedRef.current = true;

      keepaliveRef.current = window.setInterval(() => {
        if (lockResourceRef.current) sendLock("refresh", lockResourceRef.current, 3500).catch(() => {});
      }, 2000);
    }

    // stop gracefully if input track ends mid-PTT
    const t = stream!.getAudioTracks?.()[0];
    if (t) t.onended = () => { console.warn("[startPTT] input track ended"); try { stopPTT(); } catch {} };
  }
  // ───────────────── stopPTT ─────────────────
  async function stopPTT() {
    console.log("[stopPTT] Stopping PTT...");

    // Don't bail early — still release lock / flush recorder if a stray pointerup fires.
    const wasDown =
      pttDownRef.current || pttDown || floorOwned ||
      !!(mrRef.current && mrRef.current.state !== "inactive");

    // mark up-front to suppress duplicate stop storms
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
      console.log(
        `[stopPTT] Talk time accumulated: ${lastDur}ms. Total talk time: ${metricsRef.current.talkMs}ms.`
      );

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

      // Journal this PTT session (fire-and-forget)
      emitPttSession({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,                 // ← device WA or fallback
        topicWa,
        talkMs: lastDur,
        grants: metricsRef.current.grants,
        denies: metricsRef.current.denies,
        lastAcquireMs: metricsRef.current.lastAcquireMs,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,                 // ← device agentId or fallback
      }).catch(() => {});
    }

    stopMeter(); // stop the visual meter immediately
    console.log("[stopPTT] Visual meter stopped.");

    // Stop recorder and collect final chunk
    const rec = mrRef.current; // keep reference (mrRef may be nulled later)
    try {
      if (rec && rec.state !== "inactive") {
        // Nudge a final chunk (Safari/WebKit often needs this)
        try { (rec as any).__poke?.(); } catch {}
        try { typeof rec.requestData === "function" && rec.requestData(); } catch {}

        // Wait for 'stop' and drain trailing dataavailable events
        const onStopped = new Promise<void>((resolve) =>
          rec.addEventListener("stop", () => resolve(), { once: true })
        );

        const drainData = new Promise<void>((resolve) => {
          // Resolve shortly after the last dataavailable; allows multiple small packets
          let drainTimer: number | undefined;
          const handler = (e: BlobEvent) => {
            if (e?.data && e.data.size > 0) chunksRef.current.push(e.data);
            if (drainTimer) clearTimeout(drainTimer);
            drainTimer = window.setTimeout(() => {
              rec.removeEventListener("dataavailable", handler as any);
              resolve();
            }, 50);
          };
          rec.addEventListener("dataavailable", handler as any);
        });

        try { rec.stop(); } catch (e) { console.error("[stopPTT] Error stopping recorder:", e); }

        await Promise.allSettled([onStopped, drainData]);

        // If still no chunks, give UA one last tick and poke
        if (!chunksRef.current.length) {
          await new Promise((r) => setTimeout(r, 80));
          try { (rec as any).__poke?.(); } catch {}
        }
      }
    } catch (e) {
      console.warn("[stopPTT] recorder stop error", e);
    } finally {
      // ensure we clear ref now that we've tried to drain
      mrRef.current = null;
    }

    // Combine chunks into one voice note and send (persisted voice_note → shows up on other window)
    try {
      if (chunksRef.current.length) {
        // Prefer the first chunk's type; fall back to recorder mime (if any) then pickMime()
        const firstType = (chunksRef.current[0] as any)?.type || (rec?.mimeType || "");
        const blob = new Blob(chunksRef.current, { type: firstType || pickMime() });
        chunksRef.current = [];

        const chosenMime = blob.type || firstType || pickMime();
        console.log("[stopPTT] Combined voice chunks into blob.", { chosenMime, bytes: blob.size });

        const arr = await blob.arrayBuffer();
        const data_b64 = abToB64(arr);

        // Non-blocking KG journal
        emitVoiceToKG({
          apiBase: KG_API_BASE,
          kg: graph,
          ownerWa: ACTIVE_OWNER_WA,        // ← identity.wa or fallback OWNER_WA
          topicWa,                         // shorthand is fine
          mime: chosenMime,
          data_b64,
          durMs: lastDur || undefined,
          ts: Date.now(),
          agentId: ACTIVE_AGENT_ID,        // ← identity.agentId or fallback AGENT_ID
        }).catch(() => {});

        await sendVoiceNoteCapsule(chosenMime, data_b64);
        console.log("[stopPTT] voice_note sent.");
      } else if (wasDown) {
        console.log("[stopPTT] No chunks recorded — skipping send.");
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
        sendLock("release", r0).catch(() => {});
        console.log("[stopPTT] Lock released.");
      }
      setFloorOwned(false);

      // Journal that the floor is now free
      emitFloorLock({
        apiBase: KG_API_BASE,
        kg: graph,
        ownerWa: ACTIVE_OWNER_WA,  // ✅ device WA (identity) not fallback
        topicWa,
        state: "free",
        acquire_ms: lastAcquireMsRef.current || metricsRef.current.lastAcquireMs || 0,
        granted: true,
        ts: Date.now(),
        agentId: ACTIVE_AGENT_ID,  // ✅ device agentId (identity) not legacy
      }).catch(() => {});
      console.log("[stopPTT] Floor state updated to free.");

    }
  }

  // ───────────────── sendVoiceNoteCapsule (persisted; replaces frame send) ─────────────────
  async function sendVoiceNoteCapsule(mimeType: string, b64: string) {
    if (!b64) {
      console.warn("[sendVoiceNoteCapsule] empty data_b64");
      return;
    }

    // Optimistic bubble so the sender sees it immediately
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

    const headers = withConnHeaders({
      "Content-Type": "application/json",
      "X-Agent-Token": "dev-token",
      "X-Agent-Id": AGENT_ID,
    });
    const meta = withConnMeta({ trace_id: AGENT_ID, graph, t0: Date.now() });

    try {
      const body = {
        recipient: topicWa, // canonical recipient
        graph,
        capsule: { voice_note: { ts: Date.now(), mime: mimeType, data_b64: b64 } },
        meta,
      };

      console.log("[sendVoiceNoteCapsule] POST → /api/glyphnet/tx", { mimeType });
      const res = await postTx(base, body, headers);

      // RF profile guardrail
      if (res.status === 413) {
        const j = await res.json().catch(() => ({} as any));
        console.warn("[sendVoiceNoteCapsule] 413 payload too large", j);
        alert(
          j?.error === "too large"
            ? `Voice clip too large for RF path (${j.size} > ${j.max} bytes). Try a shorter clip or switch to IP-only.`
            : "Voice clip rejected: too large for current profile."
        );
        return;
      }

      const ct = res.headers.get("content-type") || "";
      const payload = ct.includes("application/json")
        ? await res.json().catch(() => ({} as any))
        : await res.text();

      if (!res.ok) {
        console.warn("[sendVoiceNoteCapsule] HTTP", res.status, payload);
        return;
      }

      const msgId = (payload as any)?.msg_id;
      if (msgId) {
        rememberSent(msgId);
        // Swap optimistic id with server id so downstream acks correlate
        setThread((prev) => prev.map((m) => (m.id === localId ? { ...m, id: msgId } : m)));
        console.log("[sendVoiceNoteCapsule] delivered ✓", { msg_id: msgId });
      } else {
        console.log("[sendVoiceNoteCapsule] OK (no msg_id)", payload);
      }
    } catch (e) {
      console.warn("[sendVoiceNoteCapsule] network/error", e);
    }
  }
  // Transcription toggle — single source of truth (persists in localStorage)
  // ⚠️ Move this ABOVE its first usage if referenced earlier in the component.
  const [transcribeOnAttach, setTranscribeOnAttach] = useState<boolean>(() => {
    try { return localStorage.getItem("gnet:transcribeOnAttach") === "1"; }
    catch { return false; }
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
    // allow re-pick of same file
    e.target.value = "";
    if (!f) return;

    const name = f.name;
    const mimeType = f.type || mimeFromName(name);
    const size = f.size ?? 0;

    console.log("[attachFile] picked file →", { name, mimeType, size });

    // Read & encode
    let b64 = "";
    try {
      const ab = await f.arrayBuffer();
      b64 = abToB64(ab);
    } catch (err) {
      console.warn("[attachFile] failed to read file", err);
      return;
    }

    // Rough base64 → bytes estimate (sanity vs f.size)
    const approxBytes =
      Math.max(
        0,
        Math.floor(b64.length * 0.75) -
          (b64.endsWith("==") ? 2 : b64.endsWith("=") ? 1 : 0)
      );
    console.log("[attachFile] sizes →", {
      fileBytes: size,
      approxBytesFromB64: approxBytes,
    });

    // 🔹 Journal the voice/file note to the KG (non-blocking)
    emitVoiceToKG({
      apiBase: KG_API_BASE,
      kg: graph,
      ownerWa: ACTIVE_OWNER_WA, // <- identity.wa or fallback OWNER_WA
      topicWa,
      mime: mimeType,
      data_b64: b64,
      durMs: undefined, // fill with real duration if/when you have it
      ts: Date.now(),
      agentId: ACTIVE_AGENT_ID, // <- identity.agentId or fallback AGENT_ID
      name,
      size,
    }).catch(() => {});

    // Optimistic bubble so sender sees it instantly
    const localId = `local-voice:${Date.now()}:${Math.random()
      .toString(36)
      .slice(2, 6)}`;
    const optimistic: NormalizedMsg = {
      id: localId,
      ts: Date.now(),
      kind: "voice",
      from: AGENT_ID,
      mime: mimeType,
      data_b64: b64,
      name,
      size,
    } as any;

    setThread((prev) => {
      const next = [...prev, optimistic];
      try {
        sessionStorage.setItem(storageKey, JSON.stringify(next));
      } catch {}
      return next;
    });

    // Build headers/meta with per-tab conn id (safe fallbacks)
    const headers =
      typeof withConnHeaders === "function"
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

    const meta =
      typeof withConnMeta === "function"
        ? withConnMeta({ trace_id: AGENT_ID, graph, t0: Date.now() })
        : { trace_id: AGENT_ID, graph, t0: Date.now() };

    try {
      const body = {
        recipient: topicWa, // canonical
        graph,
        capsule: {
          voice_note: {
            ts: Date.now(),
            mime: mimeType,
            data_b64: b64,
            name,
            size,
          },
        },
        meta,
      };

      console.log("[attachFile] POST → /api/glyphnet/tx", {
        mimeType,
        approxBytes,
      });
      const res = await postTx(base, body, headers);

      if (res.status === 413) {
        const j = await res.json().catch(() => ({} as any));
        console.warn("[attachFile] 413 too large", j);
        alert(
          j?.error === "too large"
            ? `Attachment too large for RF path (${j.size} > ${j.max} bytes). Try a smaller file or switch to IP-only.`
            : "Attachment rejected: too large for current RF profile."
        );
        return;
      }

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        console.warn("[attachFile] HTTP error", res.status, txt);
        return;
      }

      const j = await res.json().catch(() => ({} as any));
      if (j?.msg_id) {
        rememberSent(j.msg_id);
        // Swap optimistic id for server id so downstream acks correlate
        setThread((prev) =>
          prev.map((m) => (m.id === localId ? { ...m, id: j.msg_id } : m))
        );
        console.log("[attachFile] delivered ✓", {
          msg_id: j.msg_id,
          bytes: approxBytes,
        });
      } else {
        console.log("[attachFile] OK (no msg_id)", j);
      }

      // ⬇️ Optional transcription → send glyphs:[text] and journal to KG
      if (transcribeOnAttach) {
        setTranscribing(true);
        const t = await transcribeAudio(mimeType, b64); // expects { text, engine }
        setTranscribing(false);

        if (t?.text) {
          const txMeta =
            typeof withConnMeta === "function"
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

          // send the transcript as a text bubble
          await postTx(
            base,
            { recipient: topicWa, graph, capsule: { glyphs: [t.text] }, meta: txMeta },
            headers
          ).catch(() => {});

          // 🧾 Journal transcript into KG
          emitTranscriptPosted({
            apiBase: KG_API_BASE,
            kg: graph,
            ownerWa: ACTIVE_OWNER_WA, // ✅ identity-based owner
            topicWa,
            text: t.text,
            transcript_of: j?.msg_id || null,
            engine: t.engine,
            ts: Date.now(),
            agentId: ACTIVE_AGENT_ID, // ✅ identity-based agent
          }).catch(() => {});
        }
      }

      rememberTopic(topicWa || topic, addrInput || topicWa || topic, graph);
    } catch (err) {
      console.warn("[attachFile] send failed", err);
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

  // --- Allow AI memory of habits (per graph) ---
  const [allowHabits, setAllowHabits] = useState<boolean>(() => {
    try { return localStorage.getItem(`gnet:allowHabits:${graph}`) === "1"; }
    catch { return false; }
  });
  useEffect(() => {
    try { localStorage.setItem(`gnet:allowHabits:${graph}`, allowHabits ? "1" : "0"); } catch {}
  }, [graph, allowHabits]);

  const habitsAllowed = () => allowHabits === true;

  function shouldShow(item: any) {
    if (item?.__type === "call-rollup") return showCall; // rollup row
    const k = (item?.kind || "").toLowerCase();
    if (k === "text")  return showText;
    if (k === "voice") return showVoice;
    if (k === "call")  return showCall;   // if you ever render call items directly
    return showSystem;                    // everything else = system/other
  }

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

  // place once near other refs:
  ;(window as any).gnetDebug = () => ({
    pttDownRef: pttDownRef.current,
    mrState: mrRef.current?.state,
    mrType: mrRef.current?.mimeType,
    chunks: chunksRef.current?.length,
    lastStart: metricsRef.current?.lastStart,
  });

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
          {/* Thread context pill + filters */}
          <div style={{ marginLeft: 8, display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span
              style={{
                fontSize: 12, padding: "2px 8px", border: "1px solid #e5e7eb",
                borderRadius: 999, background: "#fff"
              }}
              title={`${topicWa} @ ${graph}`}
            >
              {topicWa} @ {graph}
            </span>
            <div style={{ display: "inline-flex", gap: 6, fontSize: 12 }}>
              <label><input type="checkbox" checked={showText} onChange={e=>setShowText(e.target.checked)} /> text</label>
              <label><input type="checkbox" checked={showVoice} onChange={e=>setShowVoice(e.target.checked)} /> voice</label>
              <label><input type="checkbox" checked={showCall} onChange={e=>setShowCall(e.target.checked)} /> calls</label>
              <label><input type="checkbox" checked={showSystem} onChange={e=>setShowSystem(e.target.checked)} /> system</label>
            </div>
          </div>
          {/* Always-visible hang-up while not idle (both caller & callee) */}
          {callState !== "idle" && (
            <button
              onClick={endCall}            // or hangupCall if that's what you named it
              title="Hang up"
              style={{
                marginLeft: 8,
                padding: "6px 10px",
                borderRadius: 999,
                border: "1px solid #ef4444",
                background: "#ef4444",
                color: "#fff",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              📞 End
            </button>
          )}

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

                {/* Allow habits toggle */}
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, marginTop: 8 }}>
                  <input
                    type="checkbox"
                    checked={allowHabits}
                    onChange={(e) => setAllowHabits(e.target.checked)}
                  />
                  Allow AI memory of habits (per graph)
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
                    <hr style={{ margin: "10px 0", borderColor: "#eee" }} />
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={() => setShowVisits(true)}
                    style={{ fontSize: 12, padding: "6px 8px", borderRadius: 6, border: "1px solid #e5e7eb", background: "#fff", cursor: "pointer" }}
                    title="View visit history for this thread"
                  >
                    🗂 View Visit History
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
          {renderList.filter(shouldShow).map((item: any) => {
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
            // filter
            if (m.kind === "text" && !showText) return null;
            if (m.kind === "voice" && !showVoice) return null;
            if (isCallSummaryMsg(m as any) && !showCall) return null;
            if ((m as any)?.kind === "system" && !showSystem) return null;

            const idStr = String(m?.id ?? "");
            const mine =
              (m as any)?.from === AGENT_ID ||
              (!("from" in (m as any)) &&
                (idStr.startsWith("local:") || idStr.startsWith("local-voice:")));

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
                    {(() => {
                      const mime = (m as any).mime || "";
                      const url = playUrlForVoice(m as any);

                      const isAudio = mime.startsWith("audio/");
                      const isImage = mime.startsWith("image/");

                      // Friendly name if we have one
                      const name =
                        (m as any).name ||
                        (mime && mime.includes("/")
                          ? mime.split("/")[1]
                          : "file");

                      if (isAudio) {
                        // 🎙 real voice note
                        return (
                          <>
                            <audio
                              src={url}
                              controls
                              preload="metadata"
                              muted={!audioEnabled}
                              onPlay={(e) => {
                                try {
                                  e.currentTarget.volume = audioVol;
                                } catch {}
                              }}
                              style={{ width: 240 }}
                            />
                            <span style={{ fontSize: 12, color: "#64748b" }}>
                              {String(mime.replace("audio/", "")) || "audio"}
                            </span>
                          </>
                        );
                      }

                      if (isImage) {
                        // 🖼 image attachment
                        return (
                          <img
                            src={url}
                            alt={name}
                            style={{
                              maxWidth: 240,
                              maxHeight: 240,
                              borderRadius: 12,
                              display: "block",
                            }}
                          />
                        );
                      }

                      // 📄 generic file (pdf, doc, etc.)
                      return (
                        <a
                          href={url}
                          download={name}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            fontSize: 13,
                            textDecoration: "none",
                          }}
                        >
                          📎 {name} ({mime || "file"})
                        </a>
                      );
                    })()}
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
            {callState === "idle" ? (
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
            ) : (
              <button
                onClick={endCall}    // or hangupCall
                title="Hang up"
                style={{
                  width: 36, height: 36, borderRadius: 999,
                  border: "1px solid #ef4444", background: "#ef4444",
                  color: "#fff", cursor: "pointer",
                }}
              >
                📴
              </button>
            )}
            {/* 📎 file / audio attach (separate ref) */}
            <button
              onClick={attachVoiceFile}
              title="Attach file"
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
              // allow audio, images, and PDFs (you can add more mime types later)
              accept="audio/*,image/*,application/pdf"
              onChange={onPickVoiceFile}
              style={{ display: "none" }}
            />

            {/* 🎙 PTT */}
            <button
              ref={micRef}
              disabled={micDisabled}
              onPointerDown={handlePointerDownPTT}
              onPointerUp={handlePointerUpPTT}
              onPointerCancel={handlePointerCancelPTT}
              onKeyDown={handleKeyDownPTT}
              onKeyUp={handleKeyUpPTT}
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
                touchAction: "none",    // important for mobile pointer capture
                userSelect: "none",
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
          // NOTE: log is keyed by (graph, topicWa) in stopPTT → use topicWa here too
          const log = loadPttLog(graph, topicWa);
          if (!log || log.length === 0) return null;

          const totalTalkMs = log.reduce((acc, s) => acc + (s.dur || 0), 0);
          const acqVals = log
            .map((s) => s.acquireMs)
            .filter((v): v is number => typeof v === "number");
          const avgAcquire = acqVals.length
            ? Math.round(acqVals.reduce((a, b) => a + b, 0) / acqVals.length)
            : 0;
          const grants = log.filter((s) => s.granted).length;
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
                <span style={{ fontSize: 12, opacity: 0.6, marginLeft: 8 }}>
                  RF ok/err: {tele.rf_ok}/{tele.rf_err} · IP ok/err: {tele.ip_ok}/{tele.ip_err} {rfPill}
                </span>
                <button
                  onClick={resetTelemetry}
                  style={{
                    fontSize: 11,
                    padding: "2px 6px",
                    borderRadius: 6,
                    border: "1px solid #e5e7eb",
                    background: "#fff",
                  }}
                  title="Zero RF/IP counters"
                >
                  ↺ counters
                </button>
              </div>
            </div>
          );
        })()}
        {/* 👉 Always-visible KG search panel for this graph/topic */}
        <div style={{ marginTop: 12 }}>
          <KGSearchPanel kg={graph} topicWa={topicWa} />
        </div>
        {/* ───── Visit History modal ───── */}
        {showVisits && (
          <div
            role="dialog"
            aria-modal="true"
            onClick={() => setShowVisits(false)}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.35)",
              display: "grid",
              placeItems: "center",
              zIndex: 1000,
              padding: 12,
            }}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                width: "min(920px, 96vw)",
                maxHeight: "86vh",
                overflow: "auto",
                background: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: 12,
                boxShadow: "0 20px 50px rgba(0,0,0,.25)",
                padding: 12,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <strong style={{ fontSize: 14 }}>Visit History</strong>
                <span style={{ fontSize: 12, color: "#64748b" }}>
                  {addrInput || topicWa}
                </span>
                <button
                  onClick={() => setShowVisits(false)}
                  style={{
                    marginLeft: "auto",
                    fontSize: 12,
                    padding: "4px 8px",
                    borderRadius: 6,
                    border: "1px solid #e5e7eb",
                    background: "#fff",
                    cursor: "pointer",
                  }}
                  aria-label="Close"
                  title="Close"
                >
                  ✕
                </button>
              </div>

              <VisitHistoryPanel kg={graph as "personal" | "work"} topicWa={topicWa} />
            </div>
          </div>
        )}
      </div>
    </div>  
  );
};
