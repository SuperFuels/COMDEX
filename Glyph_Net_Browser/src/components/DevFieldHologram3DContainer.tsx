// Glyph_Net_Browser/src/components/DevFieldHologram3DContainer.tsx
"use client";

import React, { useEffect, useRef, useState } from "react";
import { DevFieldHologram3DScene, GhxPacket } from "./DevFieldHologram3D";
import { GHXVisualizerField } from "./GHXVisualizerField";
import type { HoloIR } from "../lib/types/holo";

export interface DevFieldHologram3DContainerProps {
  // Optional .holo snapshot from DevTools
  holo?: HoloIR | null;
}

export default function DevFieldHologram3DContainer(
  { holo }: DevFieldHologram3DContainerProps,
) {
  const [status, setStatus] = useState<string>("Disconnected");
  const [lastPacket, setLastPacket] = useState<GhxPacket | null>(null);
  const [focusMode, setFocusMode] = useState<"world" | "focus">("world");
  const socketRef = useRef<WebSocket | null>(null);

  const toggleFocus = () =>
    setFocusMode((m) => (m === "world" ? "focus" : "world"));

  // --- WebSocket cleanup on unmount ----------------------------------------
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  function connectWs() {
    // If we already have a Holo snapshot, we don't need live GHX
    if (holo) return;
    if (typeof window === "undefined") return;

    if (
      socketRef.current &&
      socketRef.current.readyState === WebSocket.OPEN
    ) {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/ghx`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    setStatus("Connecting to /ws/ghx…");

    ws.onopen = () => setStatus("Connected to /ws/ghx");
    ws.onclose = () => setStatus("Disconnected");
    ws.onerror = () => setStatus("Error on /ws/ghx");

    ws.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        const packet: GhxPacket = (raw.ghx ?? raw) as GhxPacket;

        if (
          !packet ||
          !Array.isArray(packet.nodes) ||
          !Array.isArray(packet.edges)
        ) {
          return;
        }

        if (typeof window !== "undefined") {
          (window as any).__DEVTOOLS_LAST_GHX = packet;
        }

        setLastPacket(packet);
      } catch (e) {
        console.error("DevFieldHologram3DContainer: bad GHX message", e);
      }
    };
  }

  // --- auto-connect, seed from last GHX, listen to devtools events ----------
  useEffect(() => {
    // only auto-connect WS if we *don't* already have a holo snapshot
    if (!holo) {
      connectWs();
    } else {
      // if we switch to a holo snapshot, close any old socket
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      setStatus("Holo snapshot loaded");
    }

    if (typeof window !== "undefined" && !holo) {
      const g = (window as any).__DEVTOOLS_LAST_GHX;
      if (g && Array.isArray(g.nodes) && Array.isArray(g.edges)) {
        const seeded: GhxPacket = {
          ghx_version: g.ghx_version ?? "1.0",
          origin: g.origin ?? "devtools.ast_hologram",
          container_id: g.container_id ?? "devtools",
          nodes: g.nodes,
          edges: g.edges,
          metadata: g.metadata ?? {},
        };
        setLastPacket(seeded);
      }
    }

    function handleDevGhx(ev: Event) {
      if (holo) return; // if we’re viewing a holo snapshot, ignore live GHX events

      const detail = (ev as CustomEvent).detail;
      if (!detail) return;

      const packet: GhxPacket = (detail.ghx ?? detail) as GhxPacket;
      if (
        !packet ||
        !Array.isArray(packet.nodes) ||
        !Array.isArray(packet.edges)
      ) {
        return;
      }

      if (typeof window !== "undefined") {
        (window as any).__DEVTOOLS_LAST_GHX = packet;
      }

      setLastPacket(packet);
    }

    window.addEventListener("devtools.ghx", handleDevGhx as any);
    return () =>
      window.removeEventListener("devtools.ghx", handleDevGhx as any);
  }, [holo]);

  // --- Build a GhxPacket from the Holo snapshot (if present) ---------------
  const holoPacket: GhxPacket | null = holo
    ? ({
        ghx_version: "1.0",
        origin: `holo:${holo.holo_id}`,
        container_id: holo.container_id,

        // Map Holo nodes → GhxNode (add required `data`)
        nodes: (holo.ghx?.nodes ?? []).map((n) => ({
          id: n.id,
          label: n.label,
          type: n.type ?? "holo_node",
          tags: n.tags ?? [],
          pos: n.pos,
          icon: n.icon,
          meta: n.meta ?? {},
          data: {
            ...(n.meta ?? {}),
            from: "holo",
          },
        })),

        // Map Holo edges → GhxEdge (add required `data`, source/target)
        edges: (holo.ghx?.edges ?? []).map((e, idx) => ({
          id: e.id ?? `holo-edge-${idx}`,
          src: e.src,
          dst: e.dst,
          source: e.src,
          target: e.dst,
          relation: e.relation,
          weight: e.weight,
          tags: e.tags ?? [],
          meta: e.meta ?? {},
          data: {
            relation: e.relation,
            ...(e.meta ?? {}),
            from: "holo",
          },
        })),

        metadata: {
          holo_id: holo.holo_id,
          kind: holo.kind,
          timefold: holo.timefold,
          indexing: holo.indexing,
        },
      } as GhxPacket)
    : null;

  const packetForScene: GhxPacket | null = holoPacket ?? lastPacket;

  const nodeCount = packetForScene?.nodes?.length ?? 0;
  const edgeCount = packetForScene?.edges?.length ?? 0;
  const origin = packetForScene?.origin ?? (holo ? "holo_export" : "—");

  const statusText = holo
    ? `Holo snapshot: ${holo.holo_id}`
    : status;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        height: "100%",
      }}
    >
      {/* header row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          fontSize: 12,
        }}
      >
        <div>
          <div style={{ fontWeight: 600 }}>Dev Field Canvas (3D)</div>
          <div style={{ color: "#6b7280" }}>{statusText}</div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            onClick={toggleFocus}
            style={{
              fontSize: 12,
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: focusMode === "focus" ? "#0ea5e9" : "#0f172a",
              color: "#e5e7eb",
              cursor: "pointer",
            }}
          >
            {focusMode === "focus" ? "↩︎ Back to Field" : "🔍 Focus Card"}
          </button>

          <button
            type="button"
            onClick={connectWs}
            style={{
              fontSize: 12,
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#0f172a",
              color: "#e5e7eb",
              cursor: "pointer",
            }}
            disabled={!!holo} // when viewing a holo snapshot, WS connect is not needed
          >
            Connect / Reconnect
          </button>
        </div>
      </div>

      {/* main split: field (left) + inspector (right) */}
      <div
        style={{
          flex: 1,
          display: "flex",
          gap: 12,
          minHeight: 0,
        }}
      >
        {/* 3D field card */}
        <div
          style={{
            flex: 1,
            borderRadius: 12,
            border: "1px solid #020617",
            background: "#020617",
            overflow: "hidden",
            minHeight: 0,
          }}
        >
          <DevFieldHologram3DScene
            packet={packetForScene}
            focusMode={focusMode}
            onToggleFocus={toggleFocus}
          />
        </div>

        {/* right-hand inspector */}
        <div
          style={{
            width: 320,
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
            padding: 12,
            display: "flex",
            flexDirection: "column",
            fontSize: 12,
            minHeight: 0,
          }}
        >
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontWeight: 600, marginBottom: 2 }}>
              {holo ? "Holo GHX view" : "Last GHX packet"}
            </div>
            {packetForScene ? (
              <div style={{ color: "#6b7280" }}>
                origin:{" "}
                <span style={{ fontFamily: "monospace" }}>{origin}</span>
                <br />
                nodes: {nodeCount} • edges: {edgeCount}
              </div>
            ) : (
              <div style={{ color: "#6b7280" }}>
                No GHX packets yet. Trigger <b>AST → Hologram</b>, export a
                <b> .holo</b>, or send GHX via <code>/ws/ghx</code>.
              </div>
            )}
          </div>

          {/* tiny 2D GHX sketch */}
          <div style={{ marginBottom: 8 }}>
            <GHXVisualizerField packet={packetForScene} />
          </div>

          <div
            style={{
              flex: 1,
              borderRadius: 8,
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              padding: 8,
              overflow: "auto",
              fontFamily:
                'SFMono-Regular, ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
              fontSize: 11,
              lineHeight: 1.4,
              whiteSpace: "pre",
            }}
          >
            {packetForScene
              ? JSON.stringify(packetForScene, null, 2)
              : "// waiting for first GHX packet…"}
          </div>
        </div>
      </div>
    </div>
  );
}