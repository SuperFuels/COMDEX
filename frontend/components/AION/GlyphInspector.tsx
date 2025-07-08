import React, { useState } from 'react';

interface GlyphInspectorProps {
  coord: string;
  data: any;
  onClose: () => void;
}

const GLYPH_TYPES = ["", "⚙", "🧠", "🔒", "🌐"];

export default function GlyphInspector({ coord, data, onClose }: GlyphInspectorProps) {
  const [glyph, setGlyph] = useState(data.glyph || "");

  const handleApplyMutation = async () => {
    try {
      const res = await fetch("/api/aion/mutate-glyph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coord, glyph }),
      });
      if (!res.ok) throw new Error("Mutation failed");
      onClose(); // close on success
    } catch (err) {
      alert("Failed to mutate glyph: " + err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white p-6 rounded shadow-md max-w-sm w-full">
        <h2 className="text-lg font-semibold mb-2">🔍 Glyph Inspector</h2>
        <p><strong>Coord:</strong> {coord}</p>
        <div className="mb-2">
          <label className="block text-sm font-medium mb-1">Glyph Type:</label>
          <select
            className="border p-1 rounded w-full text-sm"
            value={glyph}
            onChange={(e) => setGlyph(e.target.value)}
          >
            {GLYPH_TYPES.map((g) => (
              <option key={g} value={g}>{g || "[empty]"}</option>
            ))}
          </select>
        </div>
        <pre className="text-xs mt-2 bg-gray-100 p-2 rounded max-h-32 overflow-auto">{JSON.stringify(data, null, 2)}</pre>
        <div className="flex justify-between items-center mt-4">
          <button onClick={onClose} className="px-3 py-1 bg-gray-300 text-sm rounded">Cancel</button>
          <button onClick={handleApplyMutation} className="px-3 py-1 bg-blue-500 text-white text-sm rounded">Apply Mutation</button>
        </div>
      </div>
    </div>
  );
}