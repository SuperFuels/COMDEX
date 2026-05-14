// frontend/components/Codex/CodexRegisterDebugTrace.tsx

import React from "react";

interface DebugTraceProps {
  trace: any[];
}

export default function CodexRegisterDebugTrace({ trace }: DebugTraceProps) {
  if (!trace || trace.length === 0) return null;

  return (
    <div className="bg-gray-900 p-4 rounded-lg text-white mt-4">
      <h3 className="text-cyan-400 font-bold mb-2">📊 Register Debug Trace</h3>
      <div className="space-y-2 max-h-96 overflow-y-scroll text-sm">
        {trace.map((step, index) => (
          <div key={index} className="border border-cyan-800 p-2 rounded-md">
            <div className="text-cyan-300 mb-1">🔹 Step {index + 1}</div>
            <pre className="whitespace-pre-wrap">{JSON.stringify(step, null, 2)}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}