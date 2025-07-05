import React, { useEffect, useState, FormEvent } from "react";
import { TraitMap, Awareness } from "../../types";

export default function AIONTerminal() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [bootLoading, setBootLoading] = useState(false);
  const [reflecting, setReflecting] = useState(false);
  const [gameDreamLoading, setGameDreamLoading] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  const fetchAndSet = async (path: string, label: string, extract: (data: any) => string) => {
    setResponse(`⏳ Fetching ${label}...`);
    try {
      const res = await fetch(`${API_BASE}${path}`);
      const data = await res.json();
      setResponse(`✅ ${label}:\n\n${extract(data)}`);
    } catch {
      setResponse(`❌ Failed to fetch ${label}`);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setResponse("");
    try {
      const res = await fetch(`${API_BASE}/aion`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      setResponse(`💬 AION:\n\n${data.reply || "No reply."}`);
    } catch {
      setResponse("❌ AION error: Backend unreachable.");
    } finally {
      setLoading(false);
    }
  };

  const handleBootSkill = async () => {
    setBootLoading(true);
    try {
      const res = await fetch(`${API_BASE}/aion/boot-skill`, { method: "POST" });
      const data = await res.json();
      setResponse(`📦 Boot Skill: ${data.message || data.title || "No skill loaded."}`);
    } catch {
      setResponse("❌ Error loading skill.");
    } finally {
      setBootLoading(false);
    }
  };

  const handleSkillReflect = async () => {
    setReflecting(true);
    try {
      const res = await fetch(`${API_BASE}/aion/skill-reflect`, { method: "POST" });
      const data = await res.json();
      setResponse(`🪞 Reflection: ${data.message || data.result || "No reflection result."}`);
    } catch {
      setResponse("❌ Reflection failed.");
    } finally {
      setReflecting(false);
    }
  };

  const handleDreamTrigger = async () => {
    setResponse("🌙 Triggering dream cycle...");
    try {
      const res = await fetch(`${API_BASE}/run-dream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trigger: "manual" }),
      });
      const data = await res.json();
      setResponse(`✅ Dream Result:\n\n${data.result || data.message || "Dream complete."}`);
    } catch {
      setResponse("❌ Dream scheduler error: Could not reach backend.");
    }
  };

  const handleGameDreamTrigger = async () => {
    setGameDreamLoading(true);
    try {
      const res = await fetch(`${API_BASE}/aion/test-game-dream`, { method: "POST" });
      const data = await res.json();
      setResponse(`🎮 Game Dream:\n\n${data.dream || "No dream returned."}`);
    } catch {
      setResponse("❌ Error triggering game dream.");
    } finally {
      setGameDreamLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 grid grid-cols-2 gap-2 p-4">
        {/* LEFT: Terminal Output */}
        <div className="border rounded p-4 bg-white whitespace-pre-wrap text-sm font-mono overflow-y-auto">
          {response || "Awaiting command..."}
        </div>

        {/* RIGHT: Prompt Input */}
        <div className="flex flex-col">
          <form onSubmit={handleSubmit} className="flex gap-2 mb-3">
            <input
              type="text"
              className="flex-1 p-2 border border-gray-300 rounded focus:outline-none"
              placeholder="Ask AION anything..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              {loading ? "Thinking..." : "Ask"}
            </button>
          </form>

          <div className="flex flex-wrap gap-2 mb-2">
            <button onClick={() => fetchAndSet("/aion/status", "Status", d => `Unlocked: ${d.unlocked?.join(", ") || "-"}\nLocked: ${d.locked?.join(", ") || "-"}`)} className="bg-blue-500 text-white px-3 py-1 rounded">Status</button>
            <button onClick={() => fetchAndSet("/aion/goal", "Goal", d => d.goal || "No goal")} className="bg-blue-500 text-white px-3 py-1 rounded">Goal</button>
            <button onClick={() => fetchAndSet("/aion/identity", "Identity", d => `${d.description}\nTraits: ${JSON.stringify(d.personality_traits, null, 2)}`)} className="bg-blue-500 text-white px-3 py-1 rounded">Identity</button>
            <button onClick={() => fetchAndSet("/aion/situation", "Situation", d => JSON.stringify(d.awareness, null, 2))} className="bg-blue-500 text-white px-3 py-1 rounded">Situation</button>
          </div>

          <div className="flex flex-wrap gap-2 mb-2">
            <button onClick={handleBootSkill} disabled={bootLoading} className="bg-purple-600 text-white px-3 py-1 rounded">{bootLoading ? "Loading..." : "🔁 Boot Skill"}</button>
            <button onClick={handleSkillReflect} disabled={reflecting} className="bg-yellow-500 text-white px-3 py-1 rounded">{reflecting ? "Reflecting..." : "🪞 Reflect"}</button>
            <button onClick={handleDreamTrigger} className="bg-green-600 text-white px-3 py-1 rounded">🌙 Run Dream</button>
            <button onClick={handleGameDreamTrigger} disabled={gameDreamLoading} className="bg-indigo-600 text-white px-3 py-1 rounded">{gameDreamLoading ? "Dreaming..." : "🎮 Game Dream"}</button>
            <button className="bg-gray-200 px-3 py-1 rounded">Dream Visualizer</button>
          </div>
        </div>
      </div>
    </div>
  );
}