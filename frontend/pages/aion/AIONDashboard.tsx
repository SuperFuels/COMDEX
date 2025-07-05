// pages/aion/AIONDashboard.tsx

import React from "react";
import dynamic from "next/dynamic";
const AIONTerminal = dynamic(() => import("@/components/AIONTerminal"), { ssr: false });

export default function AIONDashboard() {
  const handleAction = async (endpoint: string) => {
    try {
      const res = await fetch(`/api/aion/${endpoint}`);
      const data = await res.json();
      console.log(`[${endpoint}]`, data);
    } catch (err) {
      console.error(`Error calling ${endpoint}:`, err);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* LEFT PANEL */}
      <div className="w-1/4 bg-white p-4 border-r border-gray-200 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-2">🧠 AION Dashboard</h2>
        <p className="text-sm text-gray-500 mb-4">Control buttons populate below.</p>

        <div className="space-y-3">
          <button onClick={() => handleAction("boot-skill")} className="w-full py-2 bg-purple-600 text-white rounded shadow">
            🔄 Boot Skill
          </button>
          <button onClick={() => handleAction("skill-reflect")} className="w-full py-2 bg-yellow-500 text-white rounded shadow">
            💠 Reflect
          </button>
          <button onClick={() => handleAction("run-dream")} className="w-full py-2 bg-green-600 text-white rounded shadow">
            🌙 Run Dream
          </button>
          <button onClick={() => handleAction("game-dream")} className="w-full py-2 bg-indigo-600 text-white rounded shadow">
            🎮 Game Dream
          </button>
        </div>

        <div className="mt-6">
          <h3 className="font-semibold mb-2">🌌 Dream Visualizer</h3>
          <div className="h-64 bg-gray-100 border rounded p-2 text-xs text-gray-600">
            Coming soon: Visualized dreams & memory maps
          </div>
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div className="flex-1 bg-gray-50 overflow-y-auto p-4">
        <AIONTerminal />
      </div>
    </div>
  );
}