import { useEffect, useState } from "react";

type Status = {
  phase: string;
  unlocked: string[];
  locked: string[];
  milestones: {
    name: string;
    timestamp: string;
    source?: string;
  }[];
};

export default function AIONStatus() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/aion/status")
      .then((res) => res.json())
      .then((data) => setStatus(data))
      .catch(() => setError("❌ Failed to load AION status."));
  }, []);

  if (error) return <div className="text-red-500">{error}</div>;

  if (!status) return <div className="text-white">Loading AION status...</div>;

  return (
    <div className="mt-6 p-4 bg-gray-900 text-white rounded-xl shadow">
      <h2 className="text-lg font-bold mb-2">🧬 AION Growth Status</h2>
      <p className="mb-2">🧠 Current Phase: <strong>{status.phase}</strong></p>

      <div className="mb-2">
        <p>✅ Unlocked Modules:</p>
        <ul className="list-disc ml-5">
          {status.unlocked.map((mod) => (
            <li key={mod}>{mod}</li>
          ))}
        </ul>
      </div>

      <div className="mb-2">
        <p>🔒 Locked Modules:</p>
        <ul className="list-disc ml-5 text-gray-400">
          {status.locked.map((mod) => (
            <li key={mod}>{mod}</li>
          ))}
        </ul>
      </div>

      <div>
        <p>🪪 Milestones:</p>
        <ul className="list-decimal ml-5">
          {status.milestones.map((m, i) => (
            <li key={i}>
              {m.name} <span className="text-gray-400">({m.timestamp.split("T")[0]})</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
