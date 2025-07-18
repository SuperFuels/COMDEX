// ✅ Compress to Glyphs button added to avatar-runtime.tsx
// ✅ Calls /api/aion/synthesize_glyphs with GPT-like input
// ✅ Shows compressed glyph result + optional grid placement

import React, { useState } from "react";

export default function GlyphCompressorPanel() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  const handleCompress = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/aion/synthesize_glyphs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input }),
      });
      const data = await res.json();
      if (data?.glyphs) {
        setResult(data.glyphs.join(" "));
      } else {
        setResult("No glyphs returned");
      }
    } catch (err) {
      console.error("Compression failed", err);
      setResult("Error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-4 p-4 border rounded bg-gray-50">
      <h3 className="text-lg font-semibold mb-2">🧬 Compress to Glyphs</h3>
      <textarea
        rows={4}
        className="w-full p-2 border rounded mb-2 text-sm"
        placeholder="Enter GPT-style text, reflections, or thoughts..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <button
        onClick={handleCompress}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        {loading ? "Compressing..." : "🔗 Compress"}
      </button>
      {result && (
        <div className="mt-3 p-2 bg-white border rounded text-sm whitespace-pre-wrap">
          <strong>🧠 Compressed Glyphs:</strong>
          <div className="mt-1">{result}</div>
        </div>
      )}
    </div>
  );
}