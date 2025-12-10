// File: frontend/components/GlyphNetDebugger.tsx

import React, { useEffect, useState, useCallback, useRef } from "react";
import axios from "axios";

interface PacketLog {
  node: string;
  glyph: string;
  timestamp: string;
  status?: "ok" | "error" | "info";
  message?: string;
  transport?: string;      // "tcp" | "gwave" | "ble" | "radio" | ...
  direction?: "in" | "out";
}

export default function GlyphNetDebugger() {
  const [logs, setLogs] = useState<PacketLog[]>([]);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get("/api/glyphnet/logs");
      // Backend can return logs already shaped as PacketLog[]
      setLogs(res.data.logs || []);
    } catch (err) {
      console.error("Failed to fetch GlyphNet logs:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs(); // initial load

    const wsUrl =
      process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/glyphnet";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[GlyphNetDebugger] ✅ Connected to WS");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Expected shape (best case):
        // { type: "glyph_packet", log: { ...PacketLog } }
        // But we’re defensive and can derive from other shapes too.
        if (data.type === "glyph_packet") {
          const baseLog = (data.log || {}) as Partial<PacketLog> & {
            [k: string]: any;
          };

          const derived: PacketLog = {
            node:
              baseLog.node ||
              data.node ||
              baseLog.source ||
              "unknown-node",
            glyph:
              baseLog.glyph ||
              baseLog.glyph_id ||
              data.glyph ||
              data.event ||
              "glyph",
            timestamp:
              baseLog.timestamp ||
              data.timestamp ||
              new Date().toISOString(),
            status: baseLog.status || data.status || "info",
            message:
              baseLog.message ||
              baseLog.detail ||
              data.message ||
              undefined,
            transport:
              baseLog.transport ||
              data.transport ||
              data.channel ||
              undefined,
            direction:
              baseLog.direction ||
              data.direction ||
              (data.subtype === "recv" ? "in" : "out"),
          };

          setLogs((prev) => [...prev.slice(-199), derived]); // keep max 200
        }
      } catch (err) {
        console.error("[GlyphNetDebugger] Failed to parse WS message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("[GlyphNetDebugger] WS error:", err);
    };

    ws.onclose = () => {
      console.warn("[GlyphNetDebugger] ❌ WS connection closed");
    };

    return () => {
      ws.close();
    };
  }, [fetchLogs]);

  const timeAgo = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    if (diff < 1000) return "just now";
    if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
    return new Date(ts).toLocaleTimeString();
  };

  const statusColor = (status?: string) => {
    switch (status) {
      case "ok":
        return "bg-green-500";
      case "error":
        return "bg-red-500";
      case "info":
        return "bg-blue-500";
      default:
        return "bg-gray-500";
    }
  };

  const transportLabel = (transport?: string) => {
    if (!transport) return "n/a";
    return transport.toUpperCase();
  };

  const transportColor = (transport?: string) => {
    const t = (transport || "").toLowerCase();
    if (t === "ble") return "bg-purple-600 text-white";
    if (t === "gwave") return "bg-cyan-600 text-white";
    if (t === "tcp") return "bg-emerald-600 text-white";
    if (t === "radio") return "bg-orange-600 text-white";
    if (t === "light") return "bg-yellow-500 text-black";
    return "bg-gray-700 text-gray-100";
  };

  const directionArrow = (dir?: "in" | "out") => {
    if (dir === "in") return "⬇︎";
    if (dir === "out") return "⬆︎";
    return "";
  };

  return (
    <div className="bg-black text-white p-4 rounded-md border border-cyan-500 shadow-lg">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-bold text-cyan-400 flex items-center gap-2">
          🛰️ GlyphNet Debugger
          <span className="text-xs text-gray-400">
            (shows TCP / GWave / BLE / Radio)
          </span>
        </h2>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="px-3 py-1 text-sm rounded bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 transition"
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="max-h-96 overflow-y-auto space-y-2">
        {logs.map((log, idx) => (
          <div
            key={idx}
            className="bg-gray-800 p-2 rounded flex justify-between items-center hover:bg-gray-700 transition"
          >
            <div>
              <div className="flex items-center space-x-2">
                <span
                  className={`inline-block w-2 h-2 rounded-full ${statusColor(
                    log.status
                  )}`}
                ></span>
                <strong className="text-yellow-400">{log.glyph}</strong>
                <span className="ml-2 text-sm text-gray-400">@ {log.node}</span>

                {/* Transport pill */}
                <span
                  className={`ml-2 px-2 py-0.5 text-xs rounded-full font-mono ${transportColor(
                    log.transport
                  )}`}
                >
                  {directionArrow(log.direction)} {transportLabel(log.transport)}
                </span>
              </div>
              {log.message && (
                <div className="text-xs text-gray-500 mt-1">{log.message}</div>
              )}
            </div>
            <div className="text-sm text-gray-500">{timeAgo(log.timestamp)}</div>
          </div>
        ))}
        {logs.length === 0 && (
          <div className="text-gray-500 italic">No packets yet.</div>
        )}
      </div>
    </div>
  );
}