"use client";

import { useState, useEffect, FormEvent } from "react";

type TraitMap = Record<string, number>;
type ImpactSummary = {
  positive: number;
  neutral: number;
  negative: number;
};
type Awareness = {
  recent_summary: ImpactSummary;
  current_risk: string;
};

export default function AIONTerminal() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<any>(null);
  const [goal, setGoal] = useState<string>("Loading...");
  const [bootSkills, setBootSkills] = useState<any[]>([]);
  const [reflecting, setReflecting] = useState(false);
  const [bootLoading, setBootLoading] = useState(false);
  const [identityDesc, setIdentityDesc] = useState<string>("");
  const [traits, setTraits] = useState<TraitMap>({});
  const [awareness, setAwareness] = useState<Awareness | null>(null);
  const [gameDreamResult, setGameDreamResult] = useState("");
  const [gameDreams, setGameDreams] = useState<string[]>([]);
  const [gameDreamLoading, setGameDreamLoading] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  useEffect(() => {
    fetchStatus();
    fetchGoal();
    fetchBootSkills();
    fetchIdentity();
    fetchAwareness();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/aion/status`);
      const data = await res.json();
      setStatus(data);
    } catch {
      setStatus(null);
    }
  };

  const fetchGoal = async () => {
    try {
      const res = await fetch(`${API_BASE}/aion/goal`);
      const data = await res.json();
      setGoal(data.goal || "No goal available");
    } catch {
      setGoal("Error fetching goal");
    }
  };

  const fetchBootSkills = async () => {
    try {
      const res = await fetch(`${API_BASE}/aion/boot-skills`);
      const data = await res.json();
      setBootSkills(data.skills || []);
    } catch {
      setBootSkills([]);
    }
  };

  const fetchIdentity = async () => {
    try {
      const res = await fetch(`${API_BASE}/aion/identity`);
      const data = await res.json();
      setIdentityDesc(data.description || "No identity data.");
      setTraits(data.personality_traits || {});
    } catch {
      setIdentityDesc("❌ Failed to fetch identity.");
      setTraits({});
    }
  };

  const fetchAwareness = async () => {
    try {
      const res = await fetch(`${API_BASE}/aion/situation`);
      const data = await res.json();
      setAwareness(data.awareness || null);
    } catch {
      setAwareness(null);
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
      setResponse(data.reply || "No reply.");
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
      fetchBootSkills();
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
      setResponse(`🧠 Reflection: ${data.message || data.result || "No reflection result."}`);
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
    setGameDreamResult("");
    try {
      const res = await fetch(`${API_BASE}/aion/test-game-dream`, { method: "POST" });
      const data = await res.json();
      if (data?.dream) {
        setGameDreamResult(data.dream);
        setGameDreams((prev) => [data.dream, ...prev]);
      } else {
        setGameDreamResult("❌ No dream returned.");
      }
    } catch {
      setGameDreamResult("❌ Error triggering game dream.");
    } finally {
      setGameDreamLoading(false);
    }
  };

  return (
    <div className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-300 shadow-inner z-50">
      <div className="p-4 max-h-[60vh] overflow-y-auto text-sm font-mono text-gray-800">
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

        {response && (
          <div className="bg-gray-100 p-3 rounded mb-4 whitespace-pre-wrap">
            <strong>💬 AION:</strong>
            <div>{response}</div>
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-2">
          <button
            onClick={handleBootSkill}
            disabled={bootLoading}
            className="bg-purple-600 text-white px-3 py-1 rounded hover:bg-purple-700"
          >
            {bootLoading ? "Loading..." : "🔁 Boot Skill"}
          </button>
          <button
            onClick={handleSkillReflect}
            disabled={reflecting}
            className="bg-yellow-500 text-white px-3 py-1 rounded hover:bg-yellow-600"
          >
            {reflecting ? "Reflecting..." : "🪞 Reflect"}
          </button>
          <button
            onClick={handleDreamTrigger}
            className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
          >
            🌙 Run Dream
          </button>
          <button
            onClick={handleGameDreamTrigger}
            disabled={gameDreamLoading}
            className="bg-indigo-600 text-white px-3 py-1 rounded hover:bg-indigo-700"
          >
            {gameDreamLoading ? "Dreaming..." : "🎮 Game Dream"}
          </button>
        </div>

        {gameDreamResult && (
          <div className="bg-gray-100 p-2 rounded mt-2 whitespace-pre-wrap">
            <strong>🎮 Game Dream Result:</strong>
            <p>{gameDreamResult}</p>
          </div>
        )}
      </div>
    </div>
  );
}