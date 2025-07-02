import { useState, useEffect } from "react";

export default function AIONTerminal() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [milestone, setMilestone] = useState<any>(null);
  const [dreams, setDreams] = useState<string[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [currentGoal, setCurrentGoal] = useState<string>(""); // <-- NEW state added here
  const [energy, setEnergy] = useState<any>(null);
  const [tokens, setTokens] = useState<any>(null);
  const [gridProgress, setGridProgress] = useState<any>(null);

  // New state for funding survival
  const [fundAmount, setFundAmount] = useState<number>(0);
  const [fundingLoading, setFundingLoading] = useState(false);
  const [fundingMessage, setFundingMessage] = useState("");

  const fetchData = () => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/status`)
      .then((res) => res.json())
      .then((data) => setMilestone(data))
      .catch(() => setMilestone(null));

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/dreams`)
      .then((res) => res.json())
      .then((data) => setDreams(data.dreams || []));

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/strategy-plan`)
      .then((res) => res.json())
      .then((data) => setStrategies(data.strategy || []));

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/current-goal`)
      .then((res) => res.json())
      .then((data) => setCurrentGoal(data.current_goal || ""))
      .catch(() => setCurrentGoal(""));

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/energy`)
      .then((res) => res.json())
      .then((data) => setEnergy(data));

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/tokens`)
      .then((res) => res.json())
      .then((data) => setTokens(data));

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/grid-progress`)
      .then((res) => res.json())
      .then((data) => setGridProgress(data));
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResponse("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/prompt`, {
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

  const handleGameDreamTrigger = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/test-game-dream`, {
        method: "POST",
      });
      const data = await res.json();
      alert(`🧠 Game Dream Result:\n${data.dream}`);
    } catch (err) {
      alert("❌ Error triggering game dream.");
    }
  };

  // New handler to fund survival energy with $STK
  const handleFundSurvival = async () => {
    if (fundAmount <= 0) {
      setFundingMessage("❌ Enter a positive amount to fund.");
      return;
    }
    if (!tokens || tokens.stk < fundAmount) {
      setFundingMessage("❌ Insufficient $STK balance.");
      return;
    }

    setFundingLoading(true);
    setFundingMessage("");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/fund-survival`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: fundAmount }),
      });
      const data = await res.json();

      if (!res.ok) {
        setFundingMessage(`❌ Funding failed: ${data.detail || "Unknown error"}`);
      } else {
        setFundingMessage(`✅ Successfully funded ${fundAmount} $STK to recharge energy.`);
        setFundAmount(0);
        fetchData(); // refresh energy and tokens display
      }
    } catch (error) {
      setFundingMessage("❌ Backend unreachable.");
    } finally {
      setFundingLoading(false);
    }
  };

  // Helper to show if energy is critical or shutdown
  const isEnergyCritical = () => {
    if (!energy) return false;
    return energy.power_level < 30 && energy.alive;
  };

  const isEnergyShutdown = () => {
    if (!energy) return false;
    return !energy.alive;
  };

  return (
    <div className="p-4 max-w-4xl mx-auto bg-gray-900 text-white rounded-xl shadow-xl">
      <h2 className="text-2xl font-bold mb-4">🧠 AION Terminal</h2>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="text"
          className="p-3 rounded bg-gray-800 text-white focus:outline-none"
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
        <div className="mt-6 p-4 bg-gray-800 rounded-lg">
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

      {gridProgress && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">🌐 Grid World Progress</h3>
          <p>🟩 Explored Tiles: {gridProgress.explored} / 100</p>
          <p>🎯 Current Goal: {gridProgress.goal || "None"}</p>
          <p>✅ Completed: {gridProgress.complete ? "Yes" : "No"}</p>
        </div>
      )}

      {dreams.length > 0 && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">💭 Recent Dreams</h3>
          <ul className="list-disc list-inside ml-4 text-sm">
            {dreams.slice(0, 5).map((dream, i) => (
              <li key={i}>{dream}</li>
            ))}
          </ul>
        </div>
      )}

      {currentGoal && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">🎯 Current Top Priority Goal</h3>
          <p>{currentGoal}</p>
        </div>
      )}

      {strategies.length > 0 && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">📌 Strategy Plan</h3>
          {strategies.slice(0, 3).map((s, i) => (
            <div key={i} className="mb-2">
              <p>🎯 <strong>{s.goal}</strong></p>
              <p className="text-sm">🛠 {s.action}</p>
              <p className="text-xs text-gray-400">📅 {s.timestamp}</p>
            </div>
          ))}
        </div>
      )}

      {energy && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">🔋 Energy & Compute Status</h3>
          <p>⚡️ Compute Budget: {energy.compute}</p>
          <p>🧠 Memory Used: {energy.memory}</p>
          <p>📊 Load Level: {energy.load}</p>
          <p>🔌 Power Level: {energy.power_level?.toFixed(2)}</p>

          {(isEnergyCritical() || isEnergyShutdown()) && (
            <div className="mt-2 p-2 bg-red-700 rounded text-sm font-semibold">
              {isEnergyShutdown()
                ? "🚨 AION is powered down! Please fund survival to reboot."
                : "⚠️ Energy level critical! Please fund survival to recharge energy."}
            </div>
          )}

          <div className="mt-4 flex items-center gap-2">
            <input
              type="number"
              min={0}
              step={1}
              className="p-2 rounded bg-gray-700 text-white w-24"
              value={fundAmount}
              onChange={(e) => setFundAmount(Number(e.target.value))}
              disabled={fundingLoading || isEnergyShutdown()}
              placeholder="$STK to spend"
            />
            <button
              onClick={handleFundSurvival}
              disabled={fundingLoading || isEnergyShutdown()}
              className="bg-yellow-500 hover:bg-yellow-600 text-black py-2 px-4 rounded font-semibold"
            >
              {fundingLoading ? "Funding..." : "Fund Survival"}
            </button>
          </div>
          {fundingMessage && (
            <p className="mt-2 text-sm">{fundingMessage}</p>
          )}
        </div>
      )}

      {tokens && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">💰 AION Wallet</h3>
          <p>🪙 $STK: {tokens.stk}</p>
          <p>💵 $GLU: {tokens.glu}</p>
          <p>🏦 $GTC: {tokens.gtc}</p>
        </div>
      )}

      <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-2">🎮 Game ↔ Dream ↔ VisionCore</h3>
        <button
          onClick={handleGameDreamTrigger}
          className="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded"
        >
          Trigger Game-Dream Loop
        </button>
      </div>
    </div>
  );
}