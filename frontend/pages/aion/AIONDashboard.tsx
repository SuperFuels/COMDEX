// pages/aion/AIONDashboard.tsx

import React, { useState } from "react";

export default function AIONDashboard() {
  const [leftLog, setLeftLog] = useState<string[]>([]);
  const [rightLog, setRightLog] = useState<string[]>([]);
  const [askInput, setAskInput] = useState("");

  const handleLeftAction = async (endpoint: string) => {
    try {
      const res = await fetch(`/api/aion/${endpoint}`);
      const data = await res.json();
      const result = typeof data === "object" ? JSON.stringify(data, null, 2) : data;
      setLeftLog((prev) => [...prev, `[${endpoint}]:\n${result}`]);
    } catch (err: any) {
      setLeftLog((prev) => [...prev, `❌ Error calling ${endpoint}: ${err.message}`]);
    }
  };

  const handleAsk = async () => {
    if (!askInput.trim()) return;
    try {
      const res = await fetch("/api/aion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: askInput }),
      });
      const data = await res.json();
      setRightLog((prev) => [...prev, `🧠 AION: ${data.result || "No response"}`]);
      setAskInput("");
    } catch (err: any) {
      setRightLog((prev) => [...prev, `❌ Error: ${err.message}`]);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* LEFT SIDE */}
      <div className="w-1/2 flex flex-col border-r border-gray-300 bg-white">
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          <div className="border rounded p-3 bg-gray-50">
            <h3 className="font-semibold mb-2">🌌 Dream Visualizer</h3>
            <div className="h-64 bg-gray-100 text-gray-600 text-sm p-2 rounded overflow-auto">
              Coming soon: Visualized dreams & memory maps
            </div>
          </div>

          <div className="border rounded p-3 bg-black text-green-400 text-sm h-64 overflow-auto">
            {leftLog.map((line, idx) => (
              <pre key={idx} className="whitespace-pre-wrap mb-2">{line}</pre>
            ))}
          </div>
        </div>

        {/* LEFT FOOTER */}
        <div className="sticky bottom-0 z-10 bg-white border-t border-gray-300 flex justify-between items-center p-3 space-x-2">
          <button onClick={() => handleLeftAction("boot-skill")} className="bg-purple-600 text-white px-3 py-2 rounded w-full">🔄 Boot Skill</button>
          <button onClick={() => handleLeftAction("skill-reflect")} className="bg-yellow-500 text-white px-3 py-2 rounded w-full">💠 Reflect</button>
          <button onClick={() => handleLeftAction("run-dream")} className="bg-green-600 text-white px-3 py-2 rounded w-full">🌙 Run Dream</button>
          <button onClick={() => handleLeftAction("game-dream")} className="bg-indigo-600 text-white px-3 py-2 rounded w-full">🎮 Game Dream</button>
        </div>
      </div>

      {/* RIGHT SIDE */}
      <div className="w-1/2 flex flex-col bg-gray-50">
        <div className="flex-1 overflow-y-auto p-4 bg-gray-100">
          <div className="border rounded p-3 bg-black text-green-400 text-sm h-full overflow-auto">
            {rightLog.map((line, idx) => (
              <pre key={idx} className="whitespace-pre-wrap mb-2">{line}</pre>
            ))}
          </div>
        </div>

        {/* RIGHT FOOTER */}
        <div className="sticky bottom-0 z-10 bg-white border-t border-gray-300 flex items-center space-x-2 p-3">
          <input
            type="text"
            value={askInput}
            onChange={(e) => setAskInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            placeholder="Ask AION something..."
            className="flex-1 border rounded px-3 py-2"
          />
          <button onClick={handleAsk} className="bg-blue-600 text-white px-4 py-2 rounded">
            Ask
          </button>
        </div>
      </div>
    </div>
  );
}