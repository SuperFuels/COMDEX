"use client";

import { useState, useEffect } from "react";

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
  const [tileMap, setTileMap] = useState<string | null>(null);
  const [goal, setGoal] = useState<string>("Loading...");
  const [recentEvents, setRecentEvents] = useState<any[]>([]);
  const [eventCount, setEventCount] = useState<number>(0);
  const [gameDreamLoading, setGameDreamLoading] = useState(false);
  const [gameDreamResult, setGameDreamResult] = useState("");
  const [gameDreams, setGameDreams] = useState<string[]>([]);
  const [bootSkills, setBootSkills] = useState<any[]>([]);
  const [bootLoading, setBootLoading] = useState(false);
  const [reflecting, setReflecting] = useState(false);
  const [identityDesc, setIdentityDesc] = useState<string>("");
  const [traits, setTraits] = useState<TraitMap>({});
  const [awareness, setAwareness] = useState<Awareness | null>(null);

  useEffect(() => {
    fetchStatus();
    fetchTileMap();
    fetchGoal();
    fetchRecentEvents();
    fetchBootSkills();
    fetchIdentity();
    fetchAwareness();
    const interval = setInterval(fetchRecentEvents, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/status`);
      const data = await res.json();
      setStatus(data);
    } catch {
      setStatus(null);
    }
  };

  const fetchTileMap = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/grid/map`);
      const data = await res.json();
      setTileMap(data.image_base64);
    } catch {
      setTileMap(null);
    }
  };

  const fetchGoal = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/goal`);
      const data = await res.json();
      setGoal(data.goal || "No goal available");
    } catch {
      setGoal("Error fetching goal");
    }
  };

  const fetchRecentEvents = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/game-event/recent`);
      const data = await res.json();
      setRecentEvents(data.events || []);
      setEventCount(data.total || 0);
    } catch {
      setRecentEvents([]);
      setEventCount(0);
    }
  };

  const fetchAwareness = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/situation`);
      const data = await res.json();
      setAwareness(data.awareness || null);
    } catch {
      setAwareness(null);
    }
  };

  const fetchBootSkills = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/boot-skills`);
      const data = await res.json();
      setBootSkills(data.skills || []);
    } catch {
      setBootSkills([]);
    }
  };

  const fetchIdentity = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/identity`);
      const data = await res.json();
      setIdentityDesc(data.description || "No identity data.");
      setTraits(data.personality_traits || {});
    } catch {
      setIdentityDesc("❌ Failed to fetch identity.");
      setTraits({});
    }
  };

  const handleBootSkill = async () => {
    setBootLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/boot-skill`, { method: "POST" });
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
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/skill-reflect`, { method: "POST" });
      const data = await res.json();
      setResponse(`🧠 Reflection: ${data.message || data.result || "No reflection result."}`);
    } catch {
      setResponse("❌ Reflection failed.");
    } finally {
      setReflecting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setResponse("");
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion`, {
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

  const handleDreamTrigger = async () => {
    setResponse("🌙 Triggering dream cycle...");
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/run-dream`, {
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
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/test-game-dream`, {
        method: "POST",
      });
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
    <div className="p-4 max-w-3xl mx-auto bg-gray-900 text-white rounded-xl shadow-xl">
      <h2 className="text-xl font-bold mb-4">🧠 AION Terminal</h2>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="text"
          className="p-2 rounded bg-gray-800 text-white focus:outline-none"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask AION anything..."
        />
        <button
          type="submit"
          className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded"
          disabled={loading}
        >
          {loading ? "Thinking..." : "Ask AION"}
        </button>
      </form>

      {response && (
        <div className="mt-4 p-3 bg-gray-800 rounded">
          <strong>💬 AION:</strong>
          <p className="mt-2 whitespace-pre-line">{response}</p>
        </div>
      )}

      <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-2">🪪 Identity & Traits</h3>
        <pre className="text-sm whitespace-pre-wrap text-gray-300 mb-3">{identityDesc}</pre>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(traits).map(([trait, value]) => (
            <div key={trait} className="text-sm">
              <strong>{trait}</strong>: {value.toFixed(2)}
              <div className="w-full h-2 bg-gray-700 rounded">
                <div
                  className="h-2 bg-green-400 rounded"
                  style={{ width: `${value * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {awareness && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">🧭 Situational Awareness</h3>
          <p className="text-sm">Risk: <strong className="text-red-400">{awareness.current_risk}</strong></p>
          <div className="text-sm mt-2 space-y-1">
            <p>✅ Positive: {awareness.recent_summary.positive}</p>
            <p>🟨 Neutral: {awareness.recent_summary.neutral}</p>
            <p>❌ Negative: {awareness.recent_summary.negative}</p>
          </div>
        </div>
      )}

      <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-2">📌 Milestone-Linked Goals</h3>
        <GoalsList />
      </div>
    </div>
  );
}

function GoalsList() {
  const [goals, setGoals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGoals = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/goals`);
        const data = await res.json();
        setGoals(data.goals || []);
      } catch {
        setGoals([]);
      } finally {
        setLoading(false);
      }
    };
    fetchGoals();
  }, []);

  if (loading) return <p>Loading goals...</p>;
  if (goals.length === 0) return <p>No milestone-linked goals found.</p>;

  return (
    <ul className="list-disc list-inside text-sm ml-4 space-y-1 max-h-40 overflow-y-auto">
      {goals.map((goal, idx) => (
        <li key={idx}>
          <strong>{goal.name}</strong> — <span className="text-green-400">{goal.status}</span>
          <br />
          <span className="text-xs text-gray-400">
            {new Date(goal.created_at).toLocaleString()}
          </span>
        </li>
      ))}
    </ul>
  );
}