import React, { useEffect, useState } from "react";
import { CheckCircle, XCircle, PlayCircle, RefreshCw } from "lucide-react";

type Intent = {
  type: string;
  data: any;
  approved?: boolean;
  status?: "pending" | "executed" | "denied";
};

const TessarisIntentVisualizer: React.FC = () => {
  const [intents, setIntents] = useState<Intent[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [executing, setExecuting] = useState(false);

  const fetchIntents = async () => {
    const res = await fetch("/api/aion/tessaris-intents");
    const json = await res.json();
    setIntents(json || []);
  };

  const triggerExecution = async () => {
    setExecuting(true);
    await fetch("/api/aion/execute-intents", { method: "POST" });
    await fetchIntents();
    setExecuting(false);
  };

  const approveIntent = (index: number) => {
    const updated = [...intents];
    updated[index].approved = true;
    setIntents(updated);
  };

  const denyIntent = (index: number) => {
    const updated = [...intents];
    updated[index].approved = false;
    updated[index].status = "denied";
    setIntents(updated);
  };

  useEffect(() => {
    fetchIntents();
  }, []);

  const filtered = intents.filter((i) => {
    if (filter === "all") return true;
    return i.type === filter;
  });

  return (
    <div className="p-3 border rounded shadow bg-white max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-lg font-semibold">🧠 Tessaris Intents</h2>
        <div className="flex space-x-2 items-center">
          <select
            className="border p-1 text-sm rounded"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="goal">Goal</option>
            <option value="plan">Plan</option>
            <option value="avatar_action">Avatar Action</option>
          </select>
          <button
            onClick={fetchIntents}
            className="px-2 py-1 border rounded text-sm hover:bg-gray-100"
          >
            <RefreshCw className="inline-block w-4 h-4 mr-1" />
            Refresh
          </button>
          <button
            onClick={triggerExecution}
            className={`px-2 py-1 text-sm rounded text-white ${
              executing ? "bg-gray-400" : "bg-green-600 hover:bg-green-700"
            }`}
            disabled={executing}
          >
            <PlayCircle className="inline-block w-4 h-4 mr-1" />
            Execute Intents
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map((intent, i) => (
          <div
            key={i}
            className={`border p-2 rounded text-sm ${
              intent.status === "denied" ? "bg-red-100" : "bg-gray-50"
            }`}
          >
            <div className="flex justify-between items-center">
              <div>
                <span className="font-mono text-xs text-gray-500">#{i + 1}</span>{" "}
                <strong className="uppercase">{intent.type}</strong>
              </div>
              <div className="flex space-x-2">
                {intent.approved === true ? (
                  <CheckCircle className="text-green-500 w-4 h-4" />
                ) : intent.approved === false ? (
                  <XCircle className="text-red-500 w-4 h-4" />
                ) : (
                  <>
                    <button
                      onClick={() => approveIntent(i)}
                      className="text-green-600 text-xs hover:underline"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => denyIntent(i)}
                      className="text-red-600 text-xs hover:underline"
                    >
                      Deny
                    </button>
                  </>
                )}
              </div>
            </div>
            <pre className="mt-1 text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(intent.data, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TessarisIntentVisualizer;