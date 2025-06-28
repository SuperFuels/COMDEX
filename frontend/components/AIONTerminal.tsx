import { useState, useEffect } from "react";

export default function AIONTerminal() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [milestone, setMilestone] = useState<any>(null);

  useEffect(() => {
    const fetchMilestone = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/status`);
        const data = await res.json();
        setMilestone(data);
      } catch {
        setMilestone(null);
      }
    };
    fetchMilestone();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResponse("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ trigger: "manual" }),
      });
      const data = await res.json();
      setResponse(`✅ Dream Result:\n\n${data.result || data.message || "Dream complete."}`);
    } catch (err) {
      setResponse("❌ Dream scheduler error: Could not reach backend.");
    }
  };

  return (
    <div className="p-4 max-w-xl mx-auto bg-gray-900 text-white rounded-xl shadow-xl">
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

      {milestone && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">📊 AION Milestone Summary</h3>
          <p>🧬 Phase: <strong>{milestone.phase}</strong></p>
          <p>✅ Unlocked Modules: {milestone.unlocked.join(", ")}</p>
          <p>🔒 Locked Modules: {milestone.locked.join(", ")}</p>
          <p>📈 Milestones Reached:</p>
          <ul className="list-disc list-inside ml-4 text-sm">
            {milestone.milestones.map((m: string, i: number) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
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
    </div>
  );
}