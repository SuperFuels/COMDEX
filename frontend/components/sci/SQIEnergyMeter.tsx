// =====================================================
//  ⚛️ Live SQI Energy Meter — Resonance Dashboard
// =====================================================
"use client";

import React, { useEffect, useRef, useState } from "react";

// ─────────────────────────────────────────────
// 🔌 WS URL helpers (same-origin by default; no hardcoded localhost ports)
// ─────────────────────────────────────────────
function wsOrigin(): string {
  if (typeof window === "undefined") return "ws://localhost";
  return window.location.origin.replace(/^http/i, "ws");
}

function resolveWsUrl(input?: string): string {
  // Priority:
  // 1) explicit prop wsUrl
  // 2) NEXT_PUBLIC_QFC_WS
  // 3) same-origin "/ws/qfc"
  const raw = input || process.env.NEXT_PUBLIC_QFC_WS || `${wsOrigin()}/ws/qfc`;

  if (/^wss?:\/\//i.test(raw)) return raw;
  if (/^https?:\/\//i.test(raw)) return raw.replace(/^http/i, "ws");

  const base = wsOrigin();
  const path = raw.startsWith("/") ? raw : `/${raw}`;
  return `${base}${path}`;
}

function clamp01(n: number): number {
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

export default function SQIEnergyMeter({
  wsUrl,
  containerId = "sci:editor:init",
}: {
  wsUrl?: string;
  containerId?: string;
}) {
  const [sqi, setSQI] = useState<number>(0.5);
  const [energy, setEnergy] = useState<number>(1.0);
  const [status, setStatus] = useState<string>("listening…");

  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    const url = resolveWsUrl(wsUrl);

    const cleanup = () => {
      if (retryRef.current) {
        window.clearTimeout(retryRef.current);
        retryRef.current = null;
      }
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;
    };

    const connect = () => {
      if (!alive) return;
      cleanup();

      setStatus("🔭 Connecting…");
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!alive) return;
        setStatus("🟢 Connected");
        try {
          ws.send(JSON.stringify({ type: "subscribe", container_id: containerId }));
        } catch {}
      };

      ws.onmessage = (ev) => {
        if (!alive) return;
        try {
          const msg = JSON.parse(ev.data);

          // Accept either "sqi_state" (your current schema) or any future variant
          if (msg?.type === "sqi_state" && msg?.data) {
            setSQI(clamp01(msg.data.sqi_score ?? 0));
            setEnergy(clamp01(msg.data.qqc_energy ?? 0));
          }
        } catch {
          // ignore bad frames
        }
      };

      ws.onclose = () => {
        if (!alive) return;
        setStatus("🔴 Disconnected — retrying…");
        retryRef.current = window.setTimeout(connect, 1200);
      };

      ws.onerror = () => {
        // let onclose handle retry
      };
    };

    connect();

    return () => {
      alive = false;
      cleanup();
    };
  }, [wsUrl, containerId]);

  const sqiPercent = Math.round(clamp01(sqi) * 100);
  const energyPercent = Math.round(clamp01(energy) * 100);

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

      <div className="mt-2 text-[10px] text-zinc-500 text-right italic">{status}</div>
    </div>
  );
}