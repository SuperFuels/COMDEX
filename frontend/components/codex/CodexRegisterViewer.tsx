// 📁 frontend/components/Codex/CodexRegisterViewer.tsx

import React from "react";

interface Props {
  registers: Record<string, any>;
}

export default function CodexRegisterViewer({ registers }: Props) {
  return (
    <div className="bg-gray-900 p-4 rounded-xl shadow-xl text-sm">
      <h2 className="text-lg font-semibold mb-2 text-cyan-300">🔧 Virtual Registers</h2>
      {Object.keys(registers).length === 0 ? (
        <p className="text-gray-400 italic">No registers yet.</p>
      ) : (
        <ul className="space-y-1">
          {Object.entries(registers).map(([key, value]) => (
            <li key={key} className="text-white">
              <span className="font-bold text-cyan-400">{key}</span>:{" "}
              <span className="text-green-300">
                {typeof value === "object" ? JSON.stringify(value) : String(value)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}