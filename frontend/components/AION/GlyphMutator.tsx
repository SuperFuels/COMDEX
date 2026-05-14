// frontend/components/AION/AIONGlyphMutator.tsx
'use client';

import React, { useState, useEffect } from "react";

interface GlyphLogic {
  type: string;
  tag: string;
  value: string;
  action: string;
  [key: string]: any;
}

interface GlyphMutatorProps {
  containerId: string;
  coord: string;
  glyphData: GlyphLogic;
  onMutationComplete: () => void;
  onClose?: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') || '';

export default function AIONGlyphMutator({
  containerId,
  coord,
  glyphData,
  onMutationComplete,
  onClose,
}: GlyphMutatorProps) {
  const [originalGlyph, setOriginalGlyph] = useState<GlyphLogic>(glyphData);
  const [editedGlyph, setEditedGlyph] = useState<GlyphLogic>(glyphData);
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [diff, setDiff] = useState<string | null>(null);

  useEffect(() => {
    setOriginalGlyph(glyphData);
    setEditedGlyph(glyphData);
    setDiff(null);
  }, [glyphData]);

  const handleSubmit = async () => {
    setStatus("submitting");
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/aion/submit-mutation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_container: containerId,
          coord,
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
        onMutationComplete();
      }
    } catch (err: any) {
      setStatus("error");
      setError(err.message || "Unexpected error");
    }

    setTimeout(() => setStatus("idle"), 3000);
  };

  const handleFieldChange = (field: keyof GlyphLogic, value: string) => {
    setEditedGlyph((prev) => ({ ...prev, [field]: value }));
  };

  const generateDiff = () => {
    const keys = new Set([...Object.keys(originalGlyph), ...Object.keys(editedGlyph)]);
    const lines: string[] = [];

    keys.forEach((key) => {
      const before = originalGlyph[key] || "";
      const after = editedGlyph[key] || "";
      if (before !== after) {
        lines.push(`- ${key}: ${before}`);
        lines.push(`+ ${key}: ${after}`);
      } else {
        lines.push(`  ${key}: ${before}`);
      }
    });

    setDiff(lines.join("\n"));
  };

  const renderField = (label: keyof GlyphLogic) => (
    <label key={label} className="block mb-2">
      {(label as string).charAt(0).toUpperCase() + (label as string).slice(1)}:
      <input
        className="w-full border px-2 py-1 text-sm rounded"
        value={editedGlyph[label] || ""}
        onChange={(e) => handleFieldChange(label, e.target.value)}
      />
    </label>
  );

  const renderSymbolicPreview = () => {
    const { type, tag, value, action } = editedGlyph;
    return `⟦ ${type || "?"} | ${tag || "?"} : ${value || "?"} → ${action || "?"} ⟧`;
  };

  return (
    <div className="p-4 border rounded bg-white shadow-md max-w-xl w-full">
      <h2 className="text-lg font-bold mb-2">🧬 Glyph Mutator</h2>
      <p className="text-sm mb-3 text-gray-600">
        Container: <strong>{containerId}</strong> | Coord: <strong>{coord}</strong>
      </p>

      <div className="space-y-2">
        {["type", "tag", "value", "action"].map((field) => renderField(field as keyof GlyphLogic))}
      </div>

      <div className="mt-3">
        <div className="text-xs text-gray-500 mb-1">Symbolic Preview:</div>
        <div className="bg-gray-100 p-2 font-mono text-sm rounded">{renderSymbolicPreview()}</div>
      </div>

      <div className="flex justify-between mt-4 items-center gap-2">
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
            className="text-sm text-red-500 hover:underline ml-auto"
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
        <pre className="mt-3 p-3 bg-gray-100 border rounded text-xs overflow-auto max-h-40 whitespace-pre-wrap">
          {diff}
        </pre>
      )}
    </div>
  );
}