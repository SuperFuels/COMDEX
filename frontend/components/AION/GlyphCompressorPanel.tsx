import React, { useState } from "react";

export default function GlyphCompressorPanel() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCompress = async () => {
    if (!input.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch("/api/aion/synthesize_glyphs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input }),
      });
      const data = await res.json();

      if (res.ok && Array.isArray(data?.glyphs)) {
        setResult(data.glyphs);
      } else {
        setError(data?.error || "No glyphs returned.");
      }
    } catch (err) {
      console.error("Compression failed", err);
      setError("Server error.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      handleCompress();
    }
  };

  return (
    <div className="mt-4 p-4 border rounded bg-gray-50 shadow-sm">
      <h3 className="text-lg font-semibold mb-2">🧬 Compress to Glyphs</h3>
      <textarea
        rows={4}
        className="w-full p-2 border rounded mb-2 text-sm focus:outline-none focus:ring focus:border-blue-300"
        placeholder="Enter GPT-style thoughts, reflections, or logic..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <div className="flex items-center justify-between">
        <button
          onClick={handleCompress}
          disabled={loading}
          className={`px-4 py-2 text-white rounded ${
            loading ? "bg-blue-400 cursor-wait" : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {loading ? "Compressing..." : "🔗 Compress"}
        </button>
        <span className="text-xs text-gray-400 ml-2">(⌘+Enter or Ctrl+Enter)</span>
      </div>

      {error && (
        <div className="mt-3 p-2 bg-red-50 border border-red-400 text-red-700 text-sm rounded">
          ⚠️ {error}
        </div>
      )}

      {result && (
        <div className="mt-3 p-2 bg-white border rounded text-sm whitespace-pre-wrap">
          <strong>🧠 Compressed Glyphs:</strong>
          <div className="mt-1 text-xl break-words">
            {result.join(" ")}
          </div>
        </div>
      )}
    </div>
  );
}