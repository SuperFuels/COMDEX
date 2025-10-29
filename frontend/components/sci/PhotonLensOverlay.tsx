// =====================================================
//  🌌 PhotonLens Overlay — Live Resonant Visualization
// =====================================================
"use client";

import React, { useEffect, useRef, useState } from "react";

export default function PhotonLensOverlay({
  wsUrl = process.env.NEXT_PUBLIC_QFC_WS || "ws://localhost:8003/ws/qfc",
  containerId = "sci:editor:init",
}: {
  wsUrl?: string;
  containerId?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [status, setStatus] = useState("🔭 Initializing PhotonLens…");
  const [connected, setConnected] = useState(false);
  const [frames, setFrames] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // connect to QFC websocket for live frame updates
  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setStatus("🟢 Connected to QFC Field Stream");
      ws.send(JSON.stringify({ type: "subscribe", container_id: containerId }));
    };

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "qfc.frame") {
        setFrames((f) => [...f.slice(-100), msg.frame]); // keep recent 100 frames
        drawFrame(msg.frame);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setStatus("🔴 Disconnected — retrying…");
      setTimeout(() => window.location.reload(), 2500);
    };

    return () => ws.close();
  }, [wsUrl, containerId]);

  // 🌀 Simple wave rendering demo (expandable to D3/WebGL)
  function drawFrame(frame: any) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (!frame?.waves) return;

    frame.waves.forEach((w: any, i: number) => {
      const x = (i * 50 + Date.now() / 20) % canvas.width;
      const amplitude = (Math.sin(Date.now() / 500 + i) + 1) * 30;
      ctx.beginPath();
      ctx.strokeStyle = "rgba(80,200,255,0.7)";
      ctx.moveTo(x, canvas.height / 2 - amplitude);
      ctx.lineTo(x, canvas.height / 2 + amplitude);
      ctx.stroke();
    });
  }

  // 🔗 Commit last frame to Knowledge Graph or Lean state
  async function commitFrameToKnowledge() {
    const frame = frames.at(-1);
    if (!frame) return alert("No frame to commit.");
    await fetch("/api/sci/commit_atom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        container_id: containerId,
        label: "PhotonLens Snapshot",
        frame,
      }),
    });
    setStatus("🧠 Frame committed to Knowledge Graph.");
  }

  return (
    <div className="flex flex-col bg-neutral-950 border-l border-neutral-800 w-[38%]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-800 bg-neutral-900 text-xs">
        <span>{status}</span>
        <button
          onClick={commitFrameToKnowledge}
          disabled={!connected}
          className="px-2 py-1 bg-blue-700 hover:bg-blue-600 rounded border border-blue-500"
        >
          ⟲ Commit Frame
        </button>
      </div>
      <canvas ref={canvasRef} className="flex-1 w-full h-full" />
    </div>
  );
}