// public/js/kg_emit.js
// UMD: <script src="/js/kg_emit.js"></script> → window.KGEmit.*

(function (root, factory) {
  if (typeof module === "object" && typeof module.exports === "object") {
    module.exports = factory();
  } else if (typeof define === "function" && define.amd) {
    define([], factory);
  } else {
    const api = factory();
    try { root.KGEmit = api; } catch {}
  }
})(typeof window !== "undefined" ? window : globalThis, function () {
  /** @typedef {"personal"|"work"} KG */

  // ───────── helpers ─────────
  function normalizeKg(kg) {
    kg = String(kg || "personal").toLowerCase();
    return kg === "work" ? "work" : "personal";
  }
  function fpB64(b64) {
    const len = b64?.length ?? 0;
    const head = b64?.slice(0, 12) ?? "";
    const tail = len > 12 ? b64.slice(-12) : "";
    return `${len}:${head}..${tail}`;
  }
  function sigText(text, ts) {
    const bucket = Math.round((ts || Date.now()) / 5000);
    return `txt|${text}|${bucket}`;
  }
  function sigVoice(mime, b64, ts) {
    const bucket = Math.round((ts || Date.now()) / 5000);
    return `vf|${mime}|${fpB64(b64)}|${bucket}`;
  }
  function makeThreadId(kg, topicWa) {
    return `kg:${normalizeKg(kg)}:${topicWa}`;
  }
  function withBase(apiBase, path) {
    const base = apiBase || "";
    return base.endsWith("/") ? `${base.slice(0, -1)}${path}` : `${base}${path}`;
  }
  function nowId(prefix) { return `${prefix}${Date.now()}`; }

  // ───────── transport (auto-discover path + shape) ─────────
  async function postDiscovered(apiBase, kg, ownerWa, topicWa, items, opts = {}) {
    const KEY_PATH  = "kgEmit:path";
    const KEY_SHAPE = "kgEmit:shape"; // "items" | "events"

    const cachedPath  = localStorage.getItem(KEY_PATH);
    const cachedShape = localStorage.getItem(KEY_SHAPE);

    const CANDIDATES = (cachedPath && cachedShape)
      ? [{ path: cachedPath, shape: cachedShape }]
      : [
          { path: "/api/kg/append", shape: "items" },
          { path: "/api/kg/events", shape: "events" },
          { path: "/api/kg/event",  shape: "items" },
          { path: "/api/kg/put",    shape: "items" },
        ];

    const tryOnce = async ({ path, shape }) => {
      const url = withBase(apiBase, path);
      const headers = { "Content-Type": "application/json" };
      if (opts.agentId) headers["X-Agent-Id"] = String(opts.agentId);
      if (opts.agentToken) headers["X-Agent-Token"] = String(opts.agentToken);

      const body_items = {
        kg: normalizeKg(kg),
        ownerWa,
        owner_wa: ownerWa,
        topicWa,
        topic_wa: topicWa,
        items,
        agentId: opts.agentId || undefined,
        agent_id: opts.agentId || undefined,
      };
      const body_events = {
        kg: normalizeKg(kg),
        owner: ownerWa,
        events: items,
      };
      const body = shape === "events" ? body_events : body_items;

      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        keepalive: true,
      });

      if (res.ok) {
        if (path !== cachedPath || shape !== cachedShape) {
          try { localStorage.setItem(KEY_PATH, path); } catch {}
          try { localStorage.setItem(KEY_SHAPE, shape); } catch {}
        }
        return res.json().catch(() => ({}));
      }

      if (res.status === 404) throw Object.assign(new Error("404"), { retryNext: true });

      if (res.status === 400 || res.status === 415 || res.status === 422) {
        if (shape === "events") {
          const alt = await fetch(url, {
            method: "POST",
            headers,
            body: JSON.stringify(body_items),
            keepalive: true,
          });
          if (alt.ok) {
            try { localStorage.setItem(KEY_PATH, path); } catch {}
            try { localStorage.setItem(KEY_SHAPE, "items"); } catch {}
            return alt.json().catch(() => ({}));
          }
        } else {
          const alt = await fetch(url, {
            method: "POST",
            headers,
            body: JSON.stringify(body_events),
            keepalive: true,
          });
          if (alt.ok) {
            try { localStorage.setItem(KEY_PATH, path); } catch {}
            try { localStorage.setItem(KEY_SHAPE, "events"); } catch {}
            return alt.json().catch(() => ({}));
          }
        }
      }

      const text = await res.text().catch(() => "");
      const err = new Error(`${res.status}: ${text || res.statusText}`);
      err.status = res.status;
      throw err;
    };

    let lastErr;
    for (const c of CANDIDATES) {
      try { return await tryOnce(c); }
      catch (e) {
        lastErr = e;
        if (!e || !e.retryNext) {
          if (c.path === cachedPath && c.shape === cachedShape) {
            try { localStorage.removeItem(KEY_PATH); } catch {}
            try { localStorage.removeItem(KEY_SHAPE); } catch {}
            continue;
          }
        }
      }
    }
    throw new Error("KG emit failed (no working endpoint). " + (lastErr?.message || lastErr));
  }

  // ───────── emitters (build one “items” record; transport maps as needed) ─────────
  async function emitTextToKG({
    apiBase = "",
    kg,
    ownerWa,
    topicWa,
    text,
    ts = Date.now(),
    glyphId,
    agentId,
    agentToken,
  }) {
    topicWa = (topicWa || "ucs://local/ucs_hub").trim();
    const item = {
      id: glyphId || undefined,
      thread_id: makeThreadId(kg, topicWa),
      topic_wa: topicWa,
      type: "message",
      kind: "text",
      ts,
      size: (text || "").length,
      payload: { text, signature: sigText(text, ts) },
    };
    return postDiscovered(apiBase, kg, ownerWa, topicWa, [item], { agentId, agentToken });
  }

  async function emitTranscriptPosted({
    apiBase = "",
    kg,
    ownerWa,
    topicWa,
    text,
    transcript_of,
    engine,
    ts = Date.now(),
    glyphId,
    agentId,
    agentToken,
  }) {
    topicWa = (topicWa || "ucs://local/ucs_hub").trim();
    const item = {
      id: glyphId || undefined,
      thread_id: makeThreadId(kg, topicWa),
      topic_wa: topicWa,
      type: "message",
      kind: "text",
      ts,
      size: (text || "").length,
      payload: { text, transcript_of: transcript_of || null, engine: engine || null },
    };
    return postDiscovered(apiBase, kg, ownerWa, topicWa, [item], { agentId, agentToken });
  }

  async function emitVoiceToKG({
    apiBase = "",
    kg,
    ownerWa,
    topicWa,
    mime,
    data_b64,
    durMs,
    ts = Date.now(),
    sha256,
    glyphId,
    agentId,
    agentToken,
  }) {
    topicWa = (topicWa || "ucs://local/ucs_hub").trim();
    const item = {
      id: glyphId || undefined,
      thread_id: makeThreadId(kg, topicWa),
      topic_wa: topicWa,
      type: "message",
      kind: "voice",
      ts,
      size: (data_b64 || "").length,
      sha256: sha256 || null,
      payload: {
        mime, durMs,
        data_fp: fpB64(data_b64),
        signature: sigVoice(mime, data_b64, ts),
      },
    };
    return postDiscovered(apiBase, kg, ownerWa, topicWa, [item], { agentId, agentToken });
  }

  async function emitPttSession({
    apiBase = "",
    kg,
    ownerWa,
    topicWa,
    talkMs,
    grants,
    denies,
    lastAcquireMs,
    ts = Date.now(),
    agentId,
    agentToken,
  }) {
    topicWa = (topicWa || "ucs://local/ucs_hub").trim();
    const item = {
      type: "ptt_session",
      kind: "voice",
      ts,
      thread_id: makeThreadId(kg, topicWa),
      topic_wa: topicWa,
      payload: { talkMs, grants, denies, lastAcquireMs },
    };
    return postDiscovered(apiBase, kg, ownerWa, topicWa, [item], { agentId, agentToken });
  }

  async function emitFloorLock({
    apiBase = "",
    kg,
    ownerWa,
    topicWa,
    state,        // 'held'|'free'|'denied'
    acquire_ms,
    granted,
    ts = Date.now(),
    agentId,
    agentToken,
  }) {
    topicWa = (topicWa || "ucs://local/ucs_hub").trim();
    const item = {
      type: "floor_lock",
      kind: state,
      ts,
      thread_id: makeThreadId(kg, topicWa),
      topic_wa: topicWa,
      payload: { owner: ownerWa, acquire_ms, granted },
    };
    return postDiscovered(apiBase, kg, ownerWa, topicWa, [item], { agentId, agentToken });
  }

  async function emitCallState({
    apiBase = "",
    kg,
    ownerWa,
    topicWa,
    call_id,
    kind,     // 'offer'|'answer'|'connected'|'end'|'reject'|'cancel'
    ice_type,
    secs,
    ts = Date.now(),
    agentId,
    agentToken,
  }) {
    topicWa = (topicWa || "ucs://local/ucs_hub").trim();
    const item = {
      type: "call",
      kind,
      ts,
      thread_id: makeThreadId(kg, topicWa),
      topic_wa: topicWa,
      payload: { call_id, ice_type, secs },
    };
    return postDiscovered(apiBase, kg, ownerWa, topicWa, [item], { agentId, agentToken });
  }

  async function emitFileEvent({
    apiBase = "",
    kg,
    ownerWa,
    topicWa,
    kind, file_id, name, mime, size, sha256,
    ts = Date.now(),
    agentId, agentToken,
  }) {
    topicWa = (topicWa || "ucs://local/ucs_hub").trim();
    const item = {
      type: "file",
      kind,
      ts,
      thread_id: makeThreadId(kg, topicWa),
      topic_wa: topicWa,
      size: size ?? null,
      sha256: sha256 ?? null,
      payload: { file_id, name, mime, size, sha256 },
    };
    return postDiscovered(apiBase, kg, ownerWa, topicWa, [item], { agentId, agentToken });
  }

  // ---- Visits/Dwell emitter ----------------------------------------------------
  function initVisitEmitters(opts = {}) {
    const {
      apiBase = "",
      ownerWa,
      // legacy names (optional)
      kg,
      topicWa,
      getUri,
      getTitle,
      // new live readers (preferred)
      getGraph,
      getTopic,
      getPath,
      debug = false,
      agentId,
      agentToken,
    } = opts;

    const g = () => (typeof getGraph === "function" ? getGraph() : normalizeKg(kg));
    const t = () => {
      const v = typeof getTopic === "function" ? getTopic() : (topicWa || "ucs://local/ucs_hub");
      return (v || "ucs://local/ucs_hub").trim();
    };
    const pathNow  = () =>
      (typeof getPath === "function"
        ? getPath()
        : (typeof location !== "undefined" ? (location.hash || location.pathname || "/") : "/"));
    const uriNow   = () =>
      (typeof getUri === "function"
        ? getUri()
        : (typeof location !== "undefined" ? location.href : "about:blank"));
    const titleNow = () =>
      (typeof getTitle === "function"
        ? getTitle()
        : (typeof document !== "undefined" ? document.title : ""));

    let startedAt = 0;
    let lastPath = "";
    let visitId = null;

    const log = (...a) => { if (debug || (typeof window !== "undefined" && window.KG_DEBUG)) console.log("[KG visits]", ...a); };

    const emitPage = async () => {
      const ts = Date.now();
      const host = (typeof location !== "undefined" ? location.host : "");
      const referrer = (typeof document !== "undefined" ? document.referrer || "" : "");
      const item = {
        id: `local:visit:${ts}:${Math.random().toString(36).slice(2,7)}`,
        type: "visit",
        kind: "page",
        ts,
        thread_id: makeThreadId(g(), t()),
        topic_wa: t(),
        payload: {
          uri: pathNow(),
          title: titleNow(),
          href: uriNow(),
          host,
          referrer,
        },
      };
      startedAt = ts;
      lastPath = item.payload.uri;
      visitId = item.id;
      log("page", item.payload);
      try {
        await postDiscovered(apiBase, g(), ownerWa, t(), [item], { agentId, agentToken });
      } catch (e) {
        log("post page failed:", e);
      }
    };

    const emitDwell = async () => {
      if (!startedAt || !visitId) return;
      const ts = Date.now();
      const durS = Math.max(0, Math.round((ts - startedAt) / 1000));
      const item = {
        id: `${visitId}:dwell`,
        type: "visit",
        kind: "dwell",
        ts,
        thread_id: makeThreadId(g(), t()),
        topic_wa: t(),
        payload: { uri: lastPath, duration_s: durS, origin_id: visitId },
      };
      log("dwell", item.payload);
      startedAt = 0;
      visitId = null;
      try {
        await postDiscovered(apiBase, g(), ownerWa, t(), [item], { agentId, agentToken });
      } catch (e) {
        log("post dwell failed:", e);
      }
    };

    // listeners
    const onHash = () => { emitDwell(); emitPage(); };
    const onHide = () => { emitDwell(); };

    if (typeof window !== "undefined") {
      window.addEventListener("hashchange", onHash);
      window.addEventListener("visibilitychange", () => { if (document.hidden) onHide(); });
      window.addEventListener("pagehide", onHide);
      window.addEventListener("beforeunload", onHide);
    }

    // initial pageview
    emitPage();

    // return stop() to detach listeners
    return function stop() {
      if (typeof window !== "undefined") {
        window.removeEventListener("hashchange", onHash);
        window.removeEventListener("visibilitychange", onHide);
        window.removeEventListener("pagehide", onHide);
        window.removeEventListener("beforeunload", onHide);
      }
      emitDwell();
    };
  }

  return {
  // utils
  normalizeKg, makeThreadId, sigText, sigVoice,
  // emitters
  emitTextToKG, emitTranscriptPosted, emitVoiceToKG,
  emitPttSession, emitFloorLock, emitCallState, emitFileEvent,
  // NEW
  initVisitEmitters,
};

});