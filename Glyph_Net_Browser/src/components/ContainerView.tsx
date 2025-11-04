// src/components/ContainerView.tsx
import { useEffect, useMemo, useState, useCallback } from "react";
import useWebSocket from "@/hooks/useWebSocket";
import type { ResolveReply } from "@/lib/api/wormholes";
import type { DcContainer } from "@/lib/types/dc";
import DimensionRenderer from "@/components/DimensionRenderer";
import PromptBar from "@/components/PromptBar";
import TimeControls from "@/components/TimeControls";

type TimeStatus = {
  tick?: number;
  playing?: boolean;
  ratio?: number;
  loop_enabled?: boolean;
  loop_range?: [number, number];
  decay_enabled?: boolean;
};

export default function ContainerView() {
  const [res, setRes] = useState<ResolveReply | null>(null);
  const [timeStatus, setTimeStatus] = useState<Partial<TimeStatus> | null>(null);

  // track URL hash so we react to #/container/<id> changes
  const [hash, setHash] = useState<string>(location.hash || "");
  useEffect(() => {
    const onHash = () => setHash(location.hash || "");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Listen for wormhole resolution events
  useEffect(() => {
    const onResolved = (e: any) => setRes(e.detail as ResolveReply);
    window.addEventListener("wormhole:resolved", onResolved as any);
    return () => window.removeEventListener("wormhole:resolved", onResolved as any);
  }, []);

  // containerId: reply.to → reply.name(.tp stripped) → deep-link /#/container/<id>
  const containerId = useMemo(() => {
    if (res?.to) return res.to;
    if (res?.name) return res.name.replace(/\.tp$/i, "");
    const [, second, third] = (hash || "").split("/");
    return second === "container" && third ? decodeURIComponent(third) : "";
  }, [res, hash]);

  // GHX socket for this container
  const wsPath = containerId ? `/ws/ghx/${encodeURIComponent(containerId)}` : "";
  const { connected, lastJsonMessage } = useWebSocket(wsPath);

  // Feed time updates from GHX into local status (for TimeControls)
  useEffect(() => {
    const msg: any = lastJsonMessage;
    if (!msg || msg.container_id !== containerId) return;
    if (msg.type === "time_update") {
      setTimeStatus({
        tick: msg.tick,
        playing: msg.status?.playing,
        ratio: msg.status?.ratio,
        loop_enabled: msg.status?.loop_enabled,
        loop_range: msg.status?.loop_range,
        decay_enabled: msg.status?.decay_enabled,
      });
    }
  }, [lastJsonMessage, containerId]);

  // Fetch the .dc when we know the id
  const [dc, setDc] = useState<DcContainer | null>(null);
  const [dcErr, setDcErr] = useState<string | null>(null);
  const [dcLoading, setDcLoading] = useState(false);

  const loadDc = useCallback((id: string) => {
    setDcLoading(true);
    setDcErr(null);
    fetch(`/api/aion/container/${encodeURIComponent(id)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json();
      })
      .then((json) => setDc(json as DcContainer))
      .catch((e) => setDcErr(String(e)))
      .finally(() => setDcLoading(false));
  }, []);

  useEffect(() => {
    if (!containerId) return;
    loadDc(containerId);
  }, [containerId, loadDc]);

  // Reflect GHX projection events into dc.meta (so DimensionRenderer can show them)
  useEffect(() => {
    if (!lastJsonMessage || !containerId) return;
    const evt: any = lastJsonMessage;
    if (evt.event === "ghx_projection" && evt.container_id === containerId) {
      setDc((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          meta: {
            ...(prev.meta ?? {}),
            last_projection: evt.payload,
          },
        };
      });
    }
  }, [lastJsonMessage, containerId]);

  // On glyphs_updated, refetch the container to get the new glyphs
  useEffect(() => {
    const msg: any = lastJsonMessage;
    if (!msg || msg.container_id !== containerId) return;
    if (msg.type === "glyphs_updated") {
      loadDc(containerId);
    }
  }, [lastJsonMessage, containerId, loadDc]);

  // ➕ Inject two sample glyphs (optimistic UI)
  const [injecting, setInjecting] = useState(false);
  const injectSample = useCallback(async () => {
    if (!containerId || injecting) return;

    const sample = [
      { id: `g-${Date.now()}`,     symbol: "⊕", text: "hello" },
      { id: `g-${Date.now() + 1}`, symbol: "↔", text: "link"  },
    ];

    // Optimistic add
    setDc((prev) =>
      prev ? { ...prev, glyphs: [ ...(prev.glyphs ?? []), ...sample ] } : prev
    );

    setInjecting(true);
    try {
      const r = await fetch(`/api/aion/container/inject-glyphs/${encodeURIComponent(containerId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ glyphs: sample }),
      });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      // Bus will refresh; safety reload if needed:
      // loadDc(containerId);
    } catch (e) {
      console.warn("Inject sample glyphs failed:", e);
      loadDc(containerId); // rollback to server truth
    } finally {
      setInjecting(false);
    }
  }, [containerId, injecting, loadDc]);

  // ⨯ Clear all glyphs (uses /container/save to write an empty glyph array)
  const clearGlyphs = useCallback(async () => {
    if (!containerId) return;
    try {
      const payload: DcContainer = {
        ...(dc ?? { id: containerId, type: "container", meta: {} }),
        glyphs: [],
      };
      const r = await fetch(`/api/aion/container/save/${encodeURIComponent(containerId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      // ensure immediate UI update (even if GHX push lags)
      loadDc(containerId);
    } catch (e) {
      console.warn("Clear glyphs failed:", e);
    }
  }, [containerId, dc, loadDc]);

  // Empty / loading state before we have an id
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
        <div style={{ marginBottom: 8, color: "#0f172a", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontWeight: 700 }}>{containerId}</span>
          <span style={{ marginLeft: 8, fontSize: 12, color: "#475569" }}>
            WS: {connected ? "🟢 connected" : "🔴 disconnected"}
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
            onAfterAction={() => loadDc(containerId)} // force-refresh after /inject or /clear
          />
        </div>

        {/* Time controls */}
        <div style={{ marginBottom: 8 }}>
          <TimeControls containerId={containerId} status={timeStatus} />
        </div>

        {dcLoading && (
          <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
            Loading container…
          </div>
        )}

        {dcErr && (
          <div style={{ padding: 12, border: "1px solid #fecaca", borderRadius: 8, background: "#fff0f0", color: "#991b1b" }}>
            Container not found or error: {dcErr}
          </div>
        )}

        {dc && <DimensionRenderer dc={dc} />}

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
        <div style={{ padding: 12, border: "1px solid #e5e7eb", borderRadius: 8, background: "#fff" }}>
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
            <div style={{ marginTop: 8, fontSize: 12, color: "#64748b" }}>
              Waiting for events…
            </div>
          )}
        </div>
      </div>
    </div>
  );
}