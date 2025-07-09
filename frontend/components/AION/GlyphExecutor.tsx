import React, { useEffect, useState } from 'react';
import axios from 'axios';

// ✅ Define the intent type
type TessarisIntent = {
  type: string;
  name: string;
  status: string;
  source: string;
  preview?: string;
};

export default function GlyphExecutor() {
  const [intents, setIntents] = useState<TessarisIntent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIntents();
  }, []);

  const fetchIntents = async () => {
    try {
      const res = await axios.get<TessarisIntent[]>('/api/aion/tessaris-intents');
      setIntents(res.data);
    } catch (err) {
      console.error('Failed to fetch Tessaris intents:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-6 border border-gray-200 rounded p-4 bg-white shadow">
      <h3 className="text-lg font-semibold mb-2">🧠 Tessaris Glyph Executor</h3>
      {loading ? (
        <p className="text-sm text-gray-500">Loading intents...</p>
      ) : intents.length === 0 ? (
        <p className="text-sm text-gray-500">No pending glyph intents.</p>
      ) : (
        <ul className="space-y-2">
          {intents.map((intent, idx) => (
            <li key={idx} className="border rounded p-2">
              <div className="text-sm text-gray-700">
                <strong>{intent.type}</strong> → {intent.name}
              </div>
              <div className="text-xs text-gray-500">
                Status: {intent.status} | Source: {intent.source}
              </div>
              {intent.preview && (
                <div className="text-xs mt-1 bg-gray-50 p-1 rounded">
                  {intent.preview}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}