// =====================================================
//  ⚛️ Live SQI Energy Meter — Resonance Dashboard
// =====================================================
"use client";

import React, { useEffect, useState } from "react";

export default function SQIEnergyMeter({
  wsUrl = process.env.NEXT_PUBLIC_QFC_WS || "ws://localhost:8003/ws/qfc",
  containerId = "sci:editor:init",
}: {
  wsUrl?: string;
  containerId?: string;
}) {
  const [sqi, setSQI] = useState<number>(0.5);
  const [energy, setEnergy] = useState<number>(1.0);
  const [status, setStatus] = useState<string>("listening…");

  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        setStatus("🟢 Connected");
        ws.send(JSON.stringify({ type: "subscribe", container_id: containerId }));
      };
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.type === "sqi_state") {
          setSQI(msg.data.sqi_score ?? 0);
          setEnergy(msg.data.qqc_energy ?? 0);
        }
      };
      ws.onclose = () => setStatus("🔴 Disconnected");
    } catch (e) {
      setStatus("⚠️ Connection error");
    }
    return () => ws?.close();
  }, [wsUrl, containerId]);

  const sqiPercent = Math.round(sqi * 100);
  const energyPercent = Math.round(energy * 100);

  return (
    <div className="flex flex-col bg-neutral-950 border-t border-neutral-800 text-xs px-3 py-2">
      <div className="flex justify-between items-center mb-1">
        <span className="text-zinc-400">SQI Coherence</span>
        <span className="text-zinc-300 font-mono">{sqiPercent}%</span>
      </div>
      <div className="w-full h-2 bg-neutral-800 rounded">
        <div
          className="h-2 rounded bg-gradient-to-r from-cyan-400 to-blue-500 transition-all"
          style={{ width: `${sqiPercent}%` }}
        />
      </div>

      <div className="flex justify-between items-center mt-2 mb-1">
        <span className="text-zinc-400">Resonant Energy</span>
        <span className="text-zinc-300 font-mono">{energyPercent}%</span>
      </div>
      <div className="w-full h-2 bg-neutral-800 rounded">
        <div
          className="h-2 rounded bg-gradient-to-r from-amber-400 to-red-500 transition-all"
          style={{ width: `${energyPercent}%` }}
        />
      </div>

      <div className="mt-2 text-[10px] text-zinc-500 text-right italic">
        {status}
      </div>
    </div>
  );
}