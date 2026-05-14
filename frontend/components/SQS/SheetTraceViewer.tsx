import React from "react";

export function SheetTraceViewer({ trace }: { trace: any[] }) {
  if (!trace || trace.length === 0) return null;

  return (
    <div className="bg-gray-900 p-4 rounded shadow text-sm text-white">
      <h3 className="text-lg font-bold mb-2 text-cyan-300">🔭 LightCone Trace</h3>
      <ul className="space-y-2 max-h-64 overflow-y-auto">
        {trace.map((entry, i) => (
          <li key={i} className="bg-white/5 p-3 rounded">
            <div><strong>🧬 Cell ID:</strong> {entry.cell_id}</div>
            <div><strong>🧠 Result:</strong> {entry.result?.result || "—"}</div>
            <div><strong>✅ Status:</strong> {entry.result?.status || "—"}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}