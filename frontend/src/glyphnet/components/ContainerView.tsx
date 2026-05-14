// src/components/ContainerView.tsx
import { useEffect, useMemo, useState, useCallback, useRef } from "react";

import useWebSocket from "@glyphnet/hooks/useWebSocket";
import type { ResolveReply } from "@glyphnet/lib/api/wormholes";
import type { DcContainer } from "@glyphnet/lib/types/dc";
import DimensionRenderer from "@glyphnet/components/DimensionRenderer";
import PromptBar from "@glyphnet/components/PromptBar";
import TimeControls from "@glyphnet/components/TimeControls";
import KGDock from "@glyphnet/components/KGDock";

import { fetchEntanglements, type EntanglementView } from "@glyphnet/lib/kg";

type TimeStatus = {
  tick?: number;
  playing?: boolean;
  ratio?: number;
  loop_enabled?: boolean;
  loop_range?: [number, number];
  decay_enabled?: boolean;
};

function staticPathsFor(id: string): string[] {
  const paths = [
    `/containers/${encodeURIComponent(id)}.json`,
    `/containers/${encodeURIComponent(id)}/manifest.json`,
  ];
  if (id.includes("__")) {
    const [user, name] = id.split("__", 2);
    const u = encodeURIComponent(user);
    const n = encodeURIComponent(name);
    paths.push(
      `/containers/${u}/${n}.json`,
      `/containers/${u}/${n}/manifest.json`
    );
  }
  // NEW: shared containers live under /containers/shared/
  paths.push(
    `/containers/shared/${encodeURIComponent(id)}.json`,
    `/containers/shared/${encodeURIComponent(id)}/manifest.json`
  );
  return paths;
}

// ---------- helpers: robust JSON fetch + URL candidates ----------
async function fetchJSONStrict(url: string, signal?: AbortSignal) {
  const r = await fetch(url, { cache: "no-store", signal });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`HTTP ${r.status} at ${url}; body: ${txt.slice(0, 120)}`);
  }
  const ct = (r.headers.get("content-type") || "").toLowerCase();
  // Be strict about JSON; many dev servers will return index.html here
  const body = await r.text();
  if (!ct.includes("application/json")) {
    const head = body.slice(0, 120).trim();
    if (head.startsWith("<!doctype") || head.startsWith("<html")) {
      throw new Error(`Expected JSON from ${url} but received HTML (likely your SPA index.html). Put a manifest at /containers/<id>.json or fix the proxy route.`);
    }
    // try JSON anyway if content-type is missing but looks like JSON
    try { return JSON.parse(body); } catch {
      throw new Error(`Non-JSON response from ${url}: ${head}`);
    }
  }
  try { return JSON.parse(body); } catch (e: any) {
    throw new Error(`Invalid JSON from ${url}: ${e?.message || e}`);
  }
}

function candidateContainerUrls(id: string) {
  const base = "/";
  return [
    // API (backend) first, if present
    `/api/aion/container/${encodeURIComponent(id)}`,
    // Static fallbacks (put files under public/containers/)
    `${base}containers/${encodeURIComponent(id)}.json`,
    `${base}containers/${encodeURIComponent(id)}/manifest.json`,
  ];
}

type EntanglementPillProps = {
  kg: "personal" | "work";
  containerId: string;
};

function EntanglementPill(props: {
  kg: "personal" | "work";
  containerId: string;
}) {
  const { kg, containerId } = props;
  const [data, setData] = useState<EntanglementView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetchEntanglements(kg, containerId);
        if (!cancelled) {
          setData(res);
          setError(null);
        }
      } catch (e: any) {
        if (!cancelled) {
          setData(null);
          setError(e?.message || "error");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [kg, containerId]);

  if (error || !data || !data.ok) return null;
  if (!data.entangled_with || data.entangled_with.length === 0) return null;

  const label =
    data.entangled_with.length === 1
      ? data.entangled_with[0]
      : `${data.entangled_with[0]} +${data.entangled_with.length - 1}`;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 11,
        border: "1px solid rgba(148,163,184,0.6)",
        background: "rgba(15,23,42,0.04)",
        whiteSpace: "nowrap",
      }}
      title={data.entangled_with.join(", ")}
    >
      <span style={{ fontSize: 13 }}>↔</span>
      <span>Entangled with&nbsp;{label}</span>
    </span>
  );
}

export default function ContainerView() {
  const [res, setRes] = useState<ResolveReply | null>(null);
  const [timeStatus, setTimeStatus] = useState<Partial<TimeStatus> | null>(null);

  // SSR-safe hash
  const initialHash = typeof window !== "undefined" ? window.location.hash : "";
  const [hash, setHash] = useState<string>(initialHash);

  useEffect(() => {
    const onHash = () => setHash(window.location.hash || "");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Listen for wormhole resolution events
  useEffect(() => {
    const onResolved = (e: Event) => {
      const detail = (e as CustomEvent).detail as ResolveReply;
      setRes(detail);
    };
    window.addEventListener("wormhole:resolved", onResolved as any);
    return () => window.removeEventListener("wormhole:resolved", onResolved as any);
  }, []);

  // containerId from (priority) res.to → res.name (.tp stripped) → #/container/<id>
  const containerId = useMemo(() => {
    if (res?.to) return res.to;
    if (res?.name) return res.name.replace(/\.tp$/i, "");
    const parts = (hash || "").replace(/^#\/?/, "").split("/");
    if (parts[0] === "container" && parts[1]) return decodeURIComponent(parts[1]);
    return "";
  }, [res, hash]);

  // GHX socket path
  const wsPath = useMemo(
    () => (containerId ? `/ws/ghx?id=${encodeURIComponent(containerId)}` : ""),
    [containerId]
  );
  const { connected, lastJsonMessage } = useWebSocket(wsPath);

  // Normalize GHX message helpers
  const msgFor = (m: any) => (m && typeof m === "object" ? m : null);
  const msgType = (m: any) => m?.type ?? m?.event ?? m?.kind;

  // Feed time updates from GHX into local status (for TimeControls)
  useEffect(() => {
    const msg = msgFor(lastJsonMessage);
    if (!msg || msg.container_id !== containerId) return;
    if (msgType(msg) === "time_update") {
      const s = msg.status ?? {};
      setTimeStatus({
        tick: msg.tick,
        playing: s.playing,
        ratio: s.ratio,
        loop_enabled: s.loop_enabled,
        loop_range: s.loop_range,
        decay_enabled: s.decay_enabled,
      });
    }
  }, [lastJsonMessage, containerId]);

  // Fetch the container (robust: try multiple URLs, detect HTML)
  const [dc, setDc] = useState<DcContainer | null>(null);
  const [dcErr, setDcErr] = useState<string | null>(null);
  const [dcLoading, setDcLoading] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  // Abort any in-flight container fetch on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const loadDc = useCallback((id: string) => {
    // cancel previous fetch if any
    abortRef.current?.abort();

    const ac = new AbortController();
    abortRef.current = ac;

    setDcLoading(true);
    setDcErr(null);

    (async () => {
      let lastErr: any;
      for (const url of candidateContainerUrls(id)) {
        try {
          const json = await fetchJSONStrict(url, ac.signal);
          setDc(json as DcContainer);
          setDcErr(null);
          return;
        } catch (e) {
          lastErr = e;
        }
      }
      throw lastErr || new Error(`No manifest found for ${id}`);
    })()
      .catch((e) => {
        if (ac.signal.aborted) return;
        setDc(null);
        setDcErr(String(e?.message || e));
      })
      .finally(() => {
        if (!ac.signal.aborted) {
          setDcLoading(false);
        }
      });
  }, []);

  // Derive graph + title from the container meta
  const kg: "personal" | "work" =
    (dc?.meta as any)?.graph === "work" ? "work" : "personal";

  const containerTitle =
    (dc?.meta as any)?.title || containerId || "(unnamed container)";

  // Fetch container whenever containerId changes
  useEffect(() => {
    if (!containerId) return;
    loadDc(containerId);
  }, [containerId, loadDc]);

  // Reflect GHX projection events into dc.meta (for DimensionRenderer)
  useEffect(() => {
    const msg = msgFor(lastJsonMessage);
    if (!msg || msg.container_id !== containerId) return;

    if (msgType(msg) === "ghx_projection") {
      setDc((prev) =>
        prev
          ? {
              ...prev,
              meta: {
                ...(prev.meta ?? {}),
                last_projection: msg.payload,
              },
            }
          : prev
      );
    }
  }, [lastJsonMessage, containerId]);

  // On glyphs_updated, refetch the container to get the new glyphs
  useEffect(() => {
    const msg = msgFor(lastJsonMessage);
    if (!msg || msg.container_id !== containerId) return;
    if (msgType(msg) === "glyphs_updated") {
      loadDc(containerId);
    }
  }, [lastJsonMessage, containerId, loadDc]);

  // ➕ Inject two sample glyphs (optimistic UI)
  const [injecting, setInjecting] = useState(false);
  const injectSample = useCallback(async () => {
    if (!containerId || injecting) return;

    const now = Date.now();
    const sample = [
      { id: `g-${now}`, symbol: "⊕", text: "hello" },
      { id: `g-${now + 1}`, symbol: "↔", text: "link" },
    ];

    // Optimistic add
    setDc((prev) => (prev ? { ...prev, glyphs: [...(prev.glyphs ?? []), ...sample] } : prev));

    setInjecting(true);
    try {
      const r = await fetch(
        `/api/aion/container/inject-glyphs/${encodeURIComponent(containerId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ glyphs: sample }),
        }
      );
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      // Bus should refresh; still ensure UI is in sync:
      loadDc(containerId);
    } catch (e) {
      console.warn("Inject sample glyphs failed:", e);
      // Roll back to server truth
      loadDc(containerId);
    } finally {
      setInjecting(false);
    }
  }, [containerId, injecting, loadDc]);

  // ⨯ Clear all glyphs via save
  const clearGlyphs = useCallback(async () => {
    if (!containerId) return;
    try {
      const payload: DcContainer = {
        ...(dc ?? { id: containerId, type: "container", meta: {} }),
        glyphs: [],
      };
      const r = await fetch(
        `/api/aion/container/save/${encodeURIComponent(containerId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      loadDc(containerId);
    } catch (e) {
      console.warn("Clear glyphs failed:", e);
    }
  }, [containerId, dc, loadDc]);

  if (!containerId) {
    return (
      <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
        <strong>Container:</strong> (enter a wormhole name) <br />
        <span>Awaiting resolver…</span>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      {/* Left: container render */}
      <div>
        <div
          style={{
            marginBottom: 8,
            color: "#0f172a",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{ fontWeight: 700 }}>{containerId}</span>

          <span
            style={{
              marginLeft: 8,
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "2px 8px",
              borderRadius: 999,
              fontSize: 11,
              border: connected
                ? "1px solid rgba(34,197,94,0.5)"    // light green border
                : "1px solid rgba(248,113,113,0.5)", // light red border
              background: connected
                ? "rgba(22,163,74,0.06)"
                : "rgba(220,38,38,0.06)",
              color: connected ? "#047857" : "#b91c1c",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "999px",
                background: connected ? "#22c55e" : "#f97373",
                boxShadow: connected
                  ? "0 0 4px rgba(34,197,94,0.7)"
                  : "none",
              }}
            />
            <span>{connected ? "Live" : "Offline"}</span>
          </span>
        </div>

        {/* Quick test buttons */}
        <div style={{ marginBottom: 8, display: "flex", alignItems: "center" }}>
          <button
            onClick={injectSample}
            disabled={injecting}
            style={{
              padding: "6px 10px",
              borderRadius: 6,
              border: "1px solid #e5e7eb",
              background: injecting ? "#e2e8f0" : "#f8fafc",
              cursor: injecting ? "not-allowed" : "pointer",
              fontSize: 13,
            }}
          >
            {injecting ? "Injecting…" : "+ Inject sample glyphs"}
          </button>

          <button
            onClick={clearGlyphs}
            style={{
              marginLeft: 8,
              padding: "6px 10px",
              borderRadius: 6,
              border: "1px solid #e5e7eb",
              background: "#fff7f7",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            ⨯ Clear glyphs
          </button>
        </div>

        {/* Prompt input */}
        <div style={{ marginBottom: 8 }}>
          <PromptBar
            containerId={containerId}
            onAfterAction={() => loadDc(containerId)}
          />
        </div>

        {/* Time controls */}
        <div style={{ marginBottom: 8 }}>
          <TimeControls containerId={containerId} status={timeStatus} />
        </div>

        {dcLoading && (
          <div
            style={{
              padding: 12,
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              background: "#fff",
            }}
          >
            Loading container…
          </div>
        )}

        {dcErr && (
          <div
            style={{
              padding: 12,
              border: "1px solid #fecaca",
              borderRadius: 8,
              background: "#fff0f0",
              color: "#991b1b",
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 4 }}>
              Container not found or error
            </div>
            <div
              style={{
                whiteSpace: "pre-wrap",
                fontFamily: "monospace",
                fontSize: 12,
              }}
            >
              {dcErr}
            </div>
            <div
              style={{ marginTop: 8, fontSize: 12, color: "#334155" }}
            >
              Tip: if you’re developing without a backend route, add a static
              manifest at
              <code> public/containers/{containerId}.json</code> or
              <code> public/containers/{containerId}/manifest.json</code>.
            </div>
          </div>
        )}

        {/* Main container render */}
        {dc && <DimensionRenderer dc={dc} />}

        /* KG Dock: only show on our three KG topology containers */
        {dc && (
          <div style={{ marginTop: 12 }}>
            <KGDock kg={kg} containerId={containerId} />
          </div>
        )}

        {res?.container?.meta && (
          <pre
            style={{
              marginTop: 10,
              background: "#f8fafc",
              padding: 8,
              borderRadius: 6,
              overflow: "auto",
            }}
          >
            {JSON.stringify(res.container.meta, null, 2)}
          </pre>
        )}
      </div>

      {/* Right: GHX event feed */}
      <div>
        <div
          style={{
            padding: 12,
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            background: "#fff",
          }}
        >
          <strong>GHX feed</strong>
          {lastJsonMessage ? (
            <pre
              style={{
                marginTop: 8,
                background: "#f8fafc",
                padding: 8,
                borderRadius: 6,
                maxHeight: 360,
                overflow: "auto",
              }}
            >
              {JSON.stringify(lastJsonMessage, null, 2)}
            </pre>
          ) : (
            <div
              style={{
                marginTop: 8,
                fontSize: 12,
                color: "#64748b",
              }}
            >
              Waiting for events…
            </div>
          )}
        </div>
      </div>
    </div>
  );
}