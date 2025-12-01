// Glyph_Net_Browser/src/components/DevFieldCanvas.tsx
// Minimal Quantum Field / GHX viewer for Dev Tools.
//
// Sources of GHX:
//  - WebSocket:   /ws/ghx   (same backend as main field canvas)
//  - Frontend:    window.dispatchEvent("devtools.ghx", { detail: { ghx, ... } })
//
// Draws a simple 2D "quantum field" with a holographic floor and
// a framed hologram container, pinned to a logical grid row.

import { useEffect, useRef, useState } from "react";

type GhxNode = { id: string; data: any };
type GhxEdge = { id: string; source: string; target: string; kind?: string };

type GhxPacket = {
  ghx_version: string;
  origin: string;
  container_id: string;
  nodes: GhxNode[];
  edges: GhxEdge[];
  metadata?: Record<string, any>;
};

export default function DevFieldCanvas() {
  const [status, setStatus] = useState<string>("Disconnected");
  const [lastPacket, setLastPacket] = useState<GhxPacket | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // cleanup on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  // 🔌 Connect to /ws/ghx
  function connectWs() {
    if (typeof window === "undefined") return;

    // avoid reconnect spam
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/ghx`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    setStatus("Connecting to /ws/ghx…");

    ws.onopen = () => {
      setStatus("Connected to /ws/ghx");
    };

    ws.onclose = () => {
      setStatus("Disconnected");
    };

    ws.onerror = () => {
      setStatus("Error on /ws/ghx");
    };

    ws.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);

        // Support either bare GHX packet or { ghx: {...} }
        const packet: GhxPacket = raw.ghx ?? raw;

        if (!packet || !Array.isArray(packet.nodes) || !Array.isArray(packet.edges)) {
          return;
        }

        setLastPacket(packet);
        drawPacket(packet);
      } catch (e) {
        console.error("DevFieldCanvas: bad GHX message", e);
      }
    };
  }

  function drawPacket(packet: GhxPacket) {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width, height } = canvas;

    // reset + dark space background
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#020617"; // slate-950
    ctx.fillRect(0, 0, width, height);

    // subtle vignette
    const vignette = ctx.createRadialGradient(
      width / 2,
      height * 0.45,
      0,
      width / 2,
      height * 0.45,
      Math.max(width, height) * 0.8
    );
    vignette.addColorStop(0, "rgba(15,23,42,0)");
    vignette.addColorStop(1, "rgba(0,0,0,0.75)");
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, width, height);

    // holographic floor / stage (bottom 60%)
    const horizonY = height * 0.35;
    const gridBottom = height;
    const spacing = 40;

    ctx.save();
    ctx.beginPath();
    ctx.rect(0, horizonY, width, gridBottom - horizonY);
    ctx.clip();

    // floor gradient
    const floorGrad = ctx.createLinearGradient(0, horizonY, 0, gridBottom);
    floorGrad.addColorStop(0, "rgba(15,23,42,0.4)");
    floorGrad.addColorStop(1, "rgba(15,23,42,1)");
    ctx.fillStyle = floorGrad;
    ctx.fillRect(0, horizonY, width, gridBottom - horizonY);

    // grid lines (fake perspective)
    ctx.strokeStyle = "rgba(30,64,175,0.35)";
    ctx.lineWidth = 0.5;

    // vertical-ish lines converging to center
    for (let x = -width; x <= width * 2; x += spacing) {
      ctx.beginPath();
      ctx.moveTo(width / 2 + (x - width / 2) * 0.25, horizonY);
      ctx.lineTo(x, gridBottom);
      ctx.stroke();
    }

    // horizontal lines
    // keep track of y positions so we can "pin" to one row
    const horizontalYs: number[] = [];
    for (let y = horizonY + spacing; y < gridBottom; y += spacing) {
      const t = (y - horizonY) / (gridBottom - horizonY);
      const halfWidth = width * (0.2 + 0.8 * t);
      ctx.beginPath();
      ctx.moveTo(width / 2 - halfWidth, y);
      ctx.lineTo(width / 2 + halfWidth, y);
      ctx.stroke();
      horizontalYs.push(y);
    }

    ctx.restore();

    const n = packet.nodes.length;
    if (n === 0) return;

    // === Framed hologram pinned to a logical grid cell ===

    // Frame size: smaller, card-like
    const frameW = width * 0.42;
    const frameH = height * 0.26;

    // treat the floor as a set of rows; pick one row as the "tile" we stand on
    // e.g. rowIndex = 1 → second horizontal grid line from the horizon
    const rowIndex = Math.min(1, Math.max(0, horizontalYs.length - 1));
    const baseY = horizontalYs[rowIndex] ?? (horizonY + spacing * 2); // fallback

    // centre column for now (later: offset this for multiple frames)
    const centerX = width / 2;

    // bottom edge of frame sits exactly on baseY
    const centerY = baseY - frameH / 2;

    // layout radius for nodes inside the frame
    const radius = Math.min(frameW, frameH) * 0.35;

    const positions: Record<string, { x: number; y: number }> = {};

    // layout nodes on a circle / ring INSIDE the frame
    packet.nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, n);
      const r = n === 1 ? 0 : radius;
      const x = centerX + r * Math.cos(angle);
      const y = centerY + r * Math.sin(angle);
      positions[node.id] = { x, y };
    });

    // central hologram FRAME (container window)
    ctx.save();
    ctx.translate(centerX, centerY);

    // glowing inner panel
    const panelGrad = ctx.createLinearGradient(0, -frameH / 2, 0, frameH / 2);
    panelGrad.addColorStop(0, "rgba(15,23,42,0.3)");
    panelGrad.addColorStop(0.5, "rgba(56,189,248,0.16)");
    panelGrad.addColorStop(1, "rgba(15,23,42,0.7)");
    ctx.fillStyle = panelGrad;
    ctx.fillRect(-frameW / 2, -frameH / 2, frameW, frameH);

    // border glow
    ctx.shadowBlur = 24;
    ctx.shadowColor = "rgba(59,130,246,0.9)";
    ctx.strokeStyle = "rgba(191,219,254,0.95)";
    ctx.lineWidth = 2;
    ctx.strokeRect(-frameW / 2, -frameH / 2, frameW, frameH);

    // subtle inner grid in frame
    ctx.shadowBlur = 0;
    ctx.strokeStyle = "rgba(148,163,184,0.25)";
    ctx.lineWidth = 0.5;
    const innerCols = 6;
    const innerRows = 4;
    for (let i = 1; i < innerCols; i++) {
      const x = -frameW / 2 + (frameW * i) / innerCols;
      ctx.beginPath();
      ctx.moveTo(x, -frameH / 2);
      ctx.lineTo(x, frameH / 2);
      ctx.stroke();
    }
    for (let j = 1; j < innerRows; j++) {
      const y = -frameH / 2 + (frameH * j) / innerRows;
      ctx.beginPath();
      ctx.moveTo(-frameW / 2, y);
      ctx.lineTo(frameW / 2, y);
      ctx.stroke();
    }

    ctx.restore();

    // edges
    ctx.save();
    ctx.lineWidth = 1.3;
    ctx.globalAlpha = 0.9;
    packet.edges.forEach((edge) => {
      const s = positions[edge.source];
      const t = positions[edge.target];
      if (!s || !t) return;

      const kind = edge.kind ?? "";
      if (kind === "entangled") ctx.strokeStyle = "rgba(56,189,248,0.85)";
      else if (kind === "teleport") ctx.strokeStyle = "rgba(129,140,248,0.9)";
      else if (kind === "logic") ctx.strokeStyle = "rgba(251,191,36,0.95)";
      else ctx.strokeStyle = "rgba(148,163,184,0.7)";

      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    });
    ctx.restore();

    // nodes (glowing points; root treated as brighter "container core")
    packet.nodes.forEach((node, idx) => {
      const pos = positions[node.id];
      if (!pos) return;

      const symbol = node.data?.symbol ?? node.data?.type ?? "•";

      let base = "#38bdf8"; // cyan
      if (symbol === "unknown") base = "#f97316"; // orange
      else if (typeof symbol === "string" && symbol.match(/[A-Z]/)) base = "#a855f7"; // violet

      const isRoot = idx === 0;

      ctx.save();
      ctx.translate(pos.x, pos.y);

      // glow halo
      const glowRadius = isRoot ? 20 : 12;
      ctx.shadowBlur = isRoot ? 26 : 16;
      ctx.shadowColor = base;
      const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, glowRadius);
      grad.addColorStop(0, base);
      grad.addColorStop(1, "rgba(15,23,42,0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(0, 0, glowRadius, 0, Math.PI * 2);
      ctx.fill();

      // inner core
      ctx.shadowBlur = 0;
      ctx.fillStyle = isRoot ? "#fefce8" : "#f9fafb";
      ctx.beginPath();
      ctx.arc(0, 0, isRoot ? 5.5 : 4, 0, Math.PI * 2);
      ctx.fill();

      // small local frame marker around root, hinting it's the active container
      if (isRoot) {
        ctx.strokeStyle = "rgba(248,250,252,0.9)";
        ctx.lineWidth = 1;
        const size = 18;
        ctx.beginPath();
        ctx.rect(-size, -size * 0.6, size * 2, size * 1.2);
        ctx.stroke();
      }

      // 🔤 label: only show root label (avoid Value / Name spam)
      if (isRoot) {
        const label = String(node.data?.label ?? symbol ?? node.id);
        ctx.font = "11px system-ui, -apple-system, sans-serif";
        ctx.fillStyle = "#e5e7eb";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(label, 0, -22);
      }

      ctx.restore();
    });
  }

  // 🎧 Auto-connect + seed from last hologram + listen for devtools events
  useEffect(() => {
    // 1) auto-connect WS when Field tab mounts
    connectWs();

    // 2) seed from last hologram if PhotonEditor already built one
    if (typeof window !== "undefined") {
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
        drawPacket(seeded);
      }
    }

    // 3) listen for future holograms from PhotonEditor
    function handleDevGhx(ev: Event) {
      const detail = (ev as CustomEvent).detail;
      if (!detail) return;

      const packet: GhxPacket = detail.ghx ?? detail;
      if (!packet || !Array.isArray(packet.nodes) || !Array.isArray(packet.edges)) {
        return;
      }

      if (typeof window !== "undefined") {
        (window as any).__DEVTOOLS_LAST_GHX = packet;
      }

      setLastPacket(packet);
      drawPacket(packet);
    }

    window.addEventListener("devtools.ghx", handleDevGhx as any);
    return () => window.removeEventListener("devtools.ghx", handleDevGhx as any);
  }, []);

  // redraw if lastPacket changes
  useEffect(() => {
    if (lastPacket) {
      drawPacket(lastPacket);
    }
  }, [lastPacket]);

  return (
    <div style={{ display: "flex", height: "100%", gap: 12 }}>
      {/* Left: canvas */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          minWidth: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            fontSize: 12,
          }}
        >
          <div>
            <div style={{ fontWeight: 600 }}>Dev Field Canvas</div>
            <div style={{ color: "#6b7280" }}>{status}</div>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
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
            >
              Connect / Reconnect
            </button>
          </div>
        </div>

        <div
          style={{
            flex: 1,
            borderRadius: 12,
            border: "1px solid #020617",
            background: "#020617",
            padding: 8,
            minHeight: 0,
          }}
        >
          <canvas
            ref={canvasRef}
            width={800}
            height={480}
            style={{
              width: "100%",
              height: "100%",
              display: "block",
              background: "transparent",
            }}
          />
        </div>
      </div>

      {/* Right: packet inspector */}
      <div
        style={{
          width: 320,
          maxWidth: 320,
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 8,
          fontSize: 11,
          display: "flex",
          flexDirection: "column",
          gap: 6,
          minWidth: 0,
        }}
      >
        <div style={{ fontWeight: 600 }}>Last GHX packet</div>

        {lastPacket ? (
          <>
            <div style={{ color: "#6b7280" }}>
              origin: <code>{lastPacket.origin}</code>
            </div>
            <div style={{ color: "#6b7280" }}>
              nodes: {lastPacket.nodes.length} · edges: {lastPacket.edges.length}
            </div>
            <pre
              style={{
                marginTop: 4,
                maxHeight: 260,
                overflow: "auto",
                background: "#ffffff",
                borderRadius: 6,
                padding: 6,
              }}
            >
              {JSON.stringify(lastPacket, null, 2)}
            </pre>
          </>
        ) : (
          <div style={{ color: "#6b7280" }}>
            No GHX packets yet. Trigger <b>AST → Hologram</b> or send GHX via{" "}
            <code>/ws/ghx</code>.
          </div>
        )}
      </div>
    </div>
  );
}