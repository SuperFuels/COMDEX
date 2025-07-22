import React, { useEffect, useState } from "react";
import axios from "axios";

interface PacketLog {
  node: string;
  glyph: string;
  timestamp: string;
}

export default function GlyphNetDebugger() {
  const [logs, setLogs] = useState<PacketLog[]>([]);

  const fetchLogs = async () => {
    try {
      const res = await axios.get("/api/glyphnet/logs");
      setLogs(res.data.logs || []);
    } catch (err) {
      console.error("Failed to fetch GlyphNet logs:", err);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000); // Refresh every 3s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-black text-white p-4 rounded-md border border-cyan-500">
      <h2 className="text-lg font-bold mb-3 text-cyan-400">🛰️ GlyphNet Debugger</h2>
      <div className="max-h-96 overflow-y-auto space-y-2">
        {logs.map((log, idx) => (
          <div
            key={idx}
            className="bg-gray-800 p-2 rounded flex justify-between items-center"
          >
            <div>
              <strong className="text-yellow-400">{log.glyph}</strong>
              <span className="ml-2 text-sm text-gray-400">
                @ {log.node}
              </span>
            </div>
            <div className="text-sm text-gray-500">{log.timestamp}</div>
          </div>
        ))}
        {logs.length === 0 && (
          <div className="text-gray-500">No packets yet.</div>
        )}
      </div>
    </div>
  );
}