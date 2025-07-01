import React, { useEffect, useState } from "react";

interface Dream {
  label: string;
  content: string;
  timestamp: string;
  milestone_tags: string[];
}

export default function DreamReflections() {
  const [dreams, setDreams] = useState<Dream[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/aion/dreams")
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch dreams");
        return res.json();
      })
      .then(data => {
        setDreams(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading dreams...</p>;
  if (error) return <p>Error loading dreams: {error}</p>;

  return (
    <div className="dream-list">
      <h2>AION Dream Reflections</h2>
      {dreams.length === 0 && <p>No dreams found yet.</p>}
      {dreams.map(dream => (
        <div key={dream.label} className="dream-entry border p-4 mb-4 rounded shadow">
          <div className="flex justify-between items-center mb-2">
            <strong>{dream.label}</strong>
            <time dateTime={dream.timestamp}>
              {new Date(dream.timestamp).toLocaleString()}
            </time>
          </div>
          <p className="mb-2 whitespace-pre-wrap">{dream.content}</p>
          <div className="tags flex gap-2">
            {dream.milestone_tags.map(tag => (
              <span key={tag} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-semibold">
                {tag}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
