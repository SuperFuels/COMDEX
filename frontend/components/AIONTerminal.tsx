import { useState, useEffect } from "react";

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

  useEffect(() => {
    fetchStatus();
    fetchTileMap();
    fetchGoal();
    fetchRecentEvents();
    const interval = setInterval(() => {
      fetchRecentEvents();
    }, 3000);
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

      if (!res.ok) {
        setResponse(`❌ AION error: ${data.detail || "Unknown error"}`);
      } else {
        setResponse(data.reply);
      }
    } catch (err) {
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
    } catch (err) {
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
    } catch (err) {
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

      {status && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow space-y-4">
          <h3 className="text-lg font-semibold">📊 AION Progress Summary</h3>
          <p>🧬 <strong>Phase:</strong> {status.phase}</p>
          <p>📈 <strong>Strategy Count:</strong> {status.strategy_count}</p>
          <p>🔓 <strong>Unlocked:</strong> {status.unlocked.join(", ") || "None"}</p>
          <p>🔒 <strong>Locked:</strong> {status.locked.join(", ") || "None"}</p>

          <div>
            <h4 className="font-semibold">🏁 Grid World</h4>
            <p>Progress: {status.grid_progress.percent_explored}%</p>
            <p>Zones Learned: {status.grid_progress.learned_zones.join(", ") || "None"}</p>
          </div>

          <div>
            <h4 className="font-semibold">🏆 Milestones</h4>
            <ul className="list-disc list-inside text-sm ml-4">
              {status.milestones.map((m: string, i: number) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {tileMap && (
        <div className="mt-6 bg-gray-800 rounded-lg p-4 text-center">
          <h3 className="text-lg font-semibold mb-2">🗺️ Grid World Tile Map</h3>
          <img
            src={`data:image/png;base64,${tileMap}`}
            alt="Grid World Map"
            className="rounded border border-gray-700 shadow-md mx-auto"
          />
          <button
            onClick={fetchTileMap}
            className="mt-4 bg-gray-600 hover:bg-gray-700 text-white py-1 px-4 rounded text-sm"
          >
            🔁 Refresh Tile Map
          </button>
        </div>
      )}

      <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-2">🌙 Dream Scheduler</h3>
        <p className="mb-2 text-sm">
          Trigger a manual dream cycle to reflect on memory and plan new goals.
        </p>
        <button
          onClick={handleDreamTrigger}
          className="bg-purple-600 hover:bg-purple-700 text-white py-2 px-4 rounded"
        >
          🌙 Run Dream Now
        </button>
      </div>

      <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow space-y-2">
        <h3 className="text-lg font-semibold mb-2">🎮 Game Learning Panel</h3>
        <p>🎯 <strong>Current Goal:</strong> {goal}</p>
        <p>📈 <strong>Total Events:</strong> {eventCount}</p>
        <h4 className="font-semibold mt-2">📜 Recent Events</h4>
        <ul className="list-disc list-inside text-sm ml-4 max-h-40 overflow-y-auto">
          {recentEvents.map((evt, idx) => (
            <li key={idx}>{evt.timestamp} – {evt.event} {evt.metadata?.direction ? `(→ ${evt.metadata.direction})` : ""}</li>
          ))}
        </ul>
      </div>

      <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-2">🎮 Game ↔ Dream ↔ VisionCore</h3>
        <button
          onClick={handleGameDreamTrigger}
          disabled={gameDreamLoading}
          className="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded"
        >
          {gameDreamLoading ? "Dreaming..." : "Trigger Game-Dream Loop"}
        </button>

        {gameDreamResult && (
          <div className="mt-4 p-3 bg-gray-700 rounded">
            <strong>🧠 Game Dream:</strong>
            <p className="mt-2 whitespace-pre-line text-sm">{gameDreamResult}</p>
          </div>
        )}

        {gameDreams.length > 1 && (
          <div className="mt-4">
            <h4 className="font-semibold mb-1 text-sm">📚 Past Game Dreams</h4>
            <ul className="list-disc list-inside text-xs text-gray-300">
              {gameDreams.slice(1, 5).map((dream, i) => (
                <li key={i} className="mt-1">{dream}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}