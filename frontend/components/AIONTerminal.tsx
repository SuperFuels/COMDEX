import React, { useEffect, useState, FormEvent } from "react";

type Props = {
  side: "left" | "right";
};

export default function AIONTerminal({ side }: Props) {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [bootLoading, setBootLoading] = useState(false);
  const [reflecting, setReflecting] = useState(false);
  const [gameDreamLoading, setGameDreamLoading] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  const fetchAndSet = async (
    path: string,
    label: string,
    extract: (data: any) => string
  ) => {
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
    <div className="w-full h-full flex flex-col gap-2">
      <div className="text-xs text-gray-500 italic">
        Terminal Side: <b>{side}</b>
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          className="flex-1 p-2 border border-gray-300 rounded"
          placeholder="Ask AION anything..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          {loading ? "Thinking..." : "Ask"}
        </button>
      </form>

      <div className="bg-gray-100 p-3 rounded shadow-inner whitespace-pre-wrap text-sm overflow-auto h-[250px]">
        <strong>💬 AION:</strong>
        <br />
        {response || "No reply."}
      </div>
    </div>
  );
}