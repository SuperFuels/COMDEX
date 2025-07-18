// File: frontend/components/AION/TessarisTracePanel.tsx

import React, { useEffect, useState } from "react";

interface TraceEntry {
  timestamp: string;
  intent_type: string;
  payload: any;
  glyph?: string;
  source?: string;
  metadata?: Record<string, any>;
}

const TessarisTracePanel: React.FC = () => {
  const [traces, setTraces] = useState<TraceEntry[]>([]);

  useEffect(() => {
    const ws = new WebSocket("wss://comdex-api-kappa.vercel.app/ws/updates");

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "intent_trace") {
          setTraces((prev) => [data.data, ...prev.slice(0, 99)]);
        }
      } catch (err) {
        console.error("Trace parse error:", err);
      }
    };

    ws.onerror = (e) => console.warn("TessarisTrace WS error:", e);
    ws.onclose = () => console.log("TessarisTrace WS closed");

    return () => ws.close();
  }, []);

  if (traces.length === 0) {
    return (
      <div className="text-sm text-gray-500 px-4 py-2 bg-white border rounded shadow">
        No intent traces yet.
      </div>
    );
  }

  return (
    <div className="p-4 rounded-md bg-white shadow border text-sm space-y-3 overflow-y-auto max-h-[450px]">
      <h3 className="font-semibold text-lg mb-3">🧠 Tessaris Intent Trace</h3>
      {traces.map((trace, index) => (
        <div key={index} className="border-b pb-2 mb-2">
          <div className="text-xs text-gray-500">
            {new Date(trace.timestamp).toLocaleString()}
          </div>
          <div className="text-sm">
            🔖 <strong>{trace.intent_type}</strong>
          </div>
          {trace.glyph && (
            <div className="text-sm">🔣 Glyph: <span className="font-mono">{trace.glyph}</span></div>
          )}
          {trace.source && (
            <div className="text-sm">
              📁 Source: <span className="text-xs text-gray-700">{trace.source}</span>
            </div>
          )}
          <pre className="bg-gray-50 text-xs p-2 rounded overflow-x-auto mt-2">
            {JSON.stringify(trace.payload, null, 2)}
          </pre>
          {trace.metadata && (
            <div className="text-xs text-gray-600 mt-1">
              🧾 Metadata: {JSON.stringify(trace.metadata)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default TessarisTracePanel;