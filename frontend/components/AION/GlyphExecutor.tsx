import React, { useEffect, useState } from 'react';
import axios from 'axios';

type TessarisIntent = {
  type: string;
  name: string;
  status: string;
  source: string;
  reason?: string;
  preview?: string;
};

export default function GlyphExecutor() {
  const [intents, setIntents] = useState<TessarisIntent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchIntents();
  }, []);

  const fetchIntents = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await axios.get<TessarisIntent[]>('/api/aion/tessaris-intents');
      setIntents(res.data);
    } catch (err) {
      console.error('Failed to fetch Tessaris intents:', err);
      setError("Could not fetch glyph intents.");
    } finally {
      setLoading(false);
    }
  };

  const renderStatusBadge = (status: string) => {
    const color =
      status === "pending"
        ? "bg-yellow-200 text-yellow-800"
        : status === "executed"
        ? "bg-green-200 text-green-800"
        : "bg-gray-200 text-gray-700";
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full font-mono ${color}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="mt-6 border border-gray-200 rounded p-4 bg-white shadow-sm">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-semibold">🧠 Tessaris Glyph Executor</h3>
        <button
          onClick={fetchIntents}
          className="text-sm px-3 py-1 bg-blue-100 hover:bg-blue-200 text-blue-800 rounded"
        >
          🔄 Refresh
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading intents...</p>
      ) : error ? (
        <p className="text-sm text-red-500">{error}</p>
      ) : intents.length === 0 ? (
        <p className="text-sm text-gray-500">No pending glyph intents.</p>
      ) : (
        <ul className="space-y-3">
          {intents.map((intent, idx) => (
            <li
              key={idx}
              className="border rounded p-3 bg-gray-50 hover:bg-white transition shadow-sm"
            >
              <div className="flex justify-between items-center">
                <div className="text-sm text-gray-800">
                  <span className="font-bold">{intent.type}</span>
                  <span className="mx-1 text-blue-600 font-mono">→</span>
                  <span className="font-medium">{intent.name}</span>
                </div>
                {renderStatusBadge(intent.status)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Source: {intent.source}
              </div>
              {intent.reason && (
                <div className="text-xs mt-1 text-indigo-600 italic">
                  🧠 Trigger Reason: {intent.reason}
                </div>
              )}
              {intent.preview && (
                <pre className="text-xs mt-2 bg-white border rounded p-2 overflow-x-auto text-gray-700 whitespace-pre-wrap">
                  {intent.preview}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}