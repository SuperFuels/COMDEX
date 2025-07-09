import React, { useState, useEffect } from "react";

interface GlyphMutatorProps {
  containerId: string;
  coord: string;
  glyphData: any;
  onMutationComplete: () => void;
  onClose?: () => void;
}

export default function GlyphMutator({
  containerId,
  coord,
  glyphData,
  onMutationComplete,
  onClose,
}: GlyphMutatorProps) {
  const [originalGlyph, setOriginalGlyph] = useState(glyphData);
  const [editedGlyph, setEditedGlyph] = useState(glyphData);
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [diff, setDiff] = useState<string | null>(null);

  useEffect(() => {
    setOriginalGlyph(glyphData);
    setEditedGlyph(glyphData);
  }, [glyphData]);

  const handleSubmit = async () => {
    setStatus("submitting");
    setError(null);

    try {
      const res = await fetch("/api/aion/submit-mutation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_container: containerId,
          coord: coord,
          logic_before: originalGlyph,
          logic_after: editedGlyph,
        }),
      });

      const result = await res.json();
      if (!res.ok) {
        setStatus("error");
        setError(result.detail || "Unknown error");
      } else {
        setStatus("success");
        onMutationComplete(); // signal update
      }
    } catch (err: any) {
      setStatus("error");
      setError(err.message || "Unexpected error");
    }

    setTimeout(() => setStatus("idle"), 3000);
  };

  const generateDiff = () => {
    const linesBefore = originalGlyph.split("\n");
    const linesAfter = editedGlyph.split("\n");
    const result: string[] = [];

    for (let i = 0; i < Math.max(linesBefore.length, linesAfter.length); i++) {
      const before = linesBefore[i] || "";
      const after = linesAfter[i] || "";
      if (before !== after) {
        result.push(`- ${before}`);
        result.push(`+ ${after}`);
      } else {
        result.push(`  ${before}`);
      }
    }

    setDiff(result.join("\n"));
  };

  return (
    <div className="p-4 border rounded bg-white shadow-md max-w-xl w-full">
      <h2 className="text-lg font-bold mb-2">🧬 Glyph Mutator</h2>
      <p className="text-sm mb-2 text-gray-600">
        Container: <strong>{containerId}</strong> | Coord: <strong>{coord}</strong>
      </p>

      <textarea
        className="w-full h-40 p-2 border rounded text-sm font-mono"
        value={editedGlyph}
        onChange={(e) => setEditedGlyph(e.target.value)}
      />

      <div className="flex justify-between mt-3">
        <button
          onClick={handleSubmit}
          disabled={status === "submitting"}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
        >
          {status === "submitting" ? "Submitting..." : "Submit Mutation"}
        </button>

        <button
          onClick={generateDiff}
          className="px-3 py-2 text-sm bg-gray-100 rounded hover:bg-gray-200"
        >
          Show Diff
        </button>

        {onClose && (
          <button
            onClick={onClose}
            className="text-sm text-red-500 hover:underline"
          >
            Close
          </button>
        )}
      </div>

      {status === "success" && (
        <p className="text-green-600 mt-2 text-sm">✅ Mutation submitted!</p>
      )}
      {status === "error" && (
        <p className="text-red-600 mt-2 text-sm">❌ {error}</p>
      )}

      {diff && (
        <pre className="mt-3 p-3 bg-gray-100 border rounded text-xs overflow-auto max-h-40">
          {diff}
        </pre>
      )}
    </div>
  );
}