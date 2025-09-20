// File: frontend/components/GlyphNetDebugger.tsx

import React, { useEffect, useState, useCallback, useRef } from "react";
import axios from "axios";

interface PacketLog {
  node: string;
  glyph: string;
  timestamp: string;
  status?: "ok" | "error" | "info";
  message?: string;
}

export default function GlyphNetDebugger() {
  const [logs, setLogs] = useState<PacketLog[]>([]);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get("/api/glyphnet/logs");
      setLogs(res.data.logs || []);
    } catch (err) {
      console.error("Failed to fetch GlyphNet logs:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs(); // initial load

    // Open WS connection
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
        // Assume backend sends { type: "glyph_packet", log: {...} }
        if (data.type === "glyph_packet" && data.log) {
          setLogs((prev) => [...prev.slice(-199), data.log]); // keep max 200
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

  return (
    <div className="bg-black text-white p-4 rounded-md border border-cyan-500 shadow-lg">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-bold text-cyan-400 flex items-center">
          🛰️ GlyphNet Debugger
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