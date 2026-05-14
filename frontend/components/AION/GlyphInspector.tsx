// File: frontend/components/AION/GlyphInspector.tsx
'use client';

import React, { useState, useMemo } from "react";
import { mutateGlyph, scoreMutation } from "@/lib/api";
import useWebSocket from "../../hooks/useWebSocket";

interface GlyphData {
  type?: string;
  tag?: string;
  value?: string;
  action?: string;
  score?: number;
  score_breakdown?: Record<string, number>;
  denied?: boolean;
  denial_reason?: string;
  [key: string]: any;
}

interface GlyphInspectorProps {
  coord: string;
  data: GlyphData;
  onClose: () => void;
  history?: GlyphData[];
}

const GlyphInspector: React.FC<GlyphInspectorProps> = ({ coord, data, onClose, history = [] }) => {
  const [editedGlyph, setEditedGlyph] = useState<GlyphData>({ ...data });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localScore, setLocalScore] = useState<number | null>(data?.score ?? null);
  const [scoreBreakdown, setScoreBreakdown] = useState<Record<string, number> | null>(
    data?.score_breakdown ?? null
  );

  const { emit } = useWebSocket("/ws", () => {}, ["glyph_updated"]);

  const handleChange = (field: string, value: string) => {
    setEditedGlyph((prev: GlyphData) => ({ ...prev, [field]: value }));
  };

  const validate = () => {
    const required = ["type", "tag", "value", "action"];
    return required.every((f) => (editedGlyph[f] ?? "").trim() !== "");
  };

  const handleSubmit = async () => {
    if (!validate()) {
      alert("Please fill out all fields (type, tag, value, action)");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        coord,
        type: editedGlyph.type || "",
        tag: editedGlyph.tag || "",
        value: editedGlyph.value || "",
        action: editedGlyph.action || "",
      };

      await mutateGlyph(payload);
      const scored = await scoreMutation(payload);

      if (scored?.total !== undefined) {
        setLocalScore(scored.total);
        setScoreBreakdown(scored.breakdown);
      }

      emit("glyph_updated", { coord, glyph: editedGlyph });
      onClose();
    } catch (err) {
      alert("Failed to mutate glyph: " + (err instanceof Error ? err.message : String(err)));
    }
    setIsSubmitting(false);
  };

  const symbolicPreview = useMemo(() => {
    const { type, tag, value, action } = editedGlyph;
    return `⟦ ${type || "?"} | ${tag || "?"} : ${value || "?"} → ${action || "?"} ⟧`;
  }, [editedGlyph]);

  const renderHistory = () =>
    Array.isArray(history) && history.length > 0 ? (
      <div className="mt-4 text-sm">
        <div className="text-xs text-gray-400 mb-1">History:</div>
        <ul className="max-h-32 overflow-y-auto border p-2 rounded bg-gray-50 text-xs font-mono">
          {history.map((h, idx) => (
            <li key={idx}>
              ⟦ {h.type || "?"} | {h.tag || "?"} : {h.value || "?"} → {h.action || "?"} ⟧
            </li>
          ))}
        </ul>
      </div>
    ) : null;

  return (
    <div className="p-4 border rounded bg-white shadow-md w-full max-w-lg relative">
      {isSubmitting && (
        <div className="absolute inset-0 bg-white bg-opacity-60 flex items-center justify-center z-10">
          <div className="text-blue-600 animate-spin text-xl">⏳</div>
        </div>
      )}

      <h2 className="text-lg font-bold mb-4">✏️ Edit Glyph at {coord}</h2>

      {["type", "tag", "value", "action"].map((field) => (
        <label key={field} className="block mb-2">
          {field.charAt(0).toUpperCase() + field.slice(1)}:
          <input
            className="w-full border px-2 py-1 text-sm"
            value={String(editedGlyph[field] ?? "")}
            onChange={(e) => handleChange(field, e.target.value)}
          />
        </label>
      ))}

      {data?.denied && data?.denial_reason && (
        <div className="bg-red-100 text-red-700 text-xs p-2 mt-2 rounded border border-red-300">
          ❌ Denial Reason: {data.denial_reason}
        </div>
      )}

      <div className="mt-3 text-sm">
        <div className="text-xs text-gray-500 mb-1">Symbolic Logic Preview:</div>
        <div className="bg-gray-100 px-3 py-2 rounded font-mono">{symbolicPreview}</div>
      </div>

      {typeof localScore === "number" && (
        <div className="mt-4 text-sm">
          <div className="font-semibold mb-1">🧠 Mutation Score</div>
          <div className="bg-gray-800 text-white px-3 py-2 rounded w-fit">
            Total Score: <span className="font-bold">{localScore}</span>
          </div>
          {scoreBreakdown && (
            <ul className="text-xs text-gray-500 mt-2 list-disc list-inside">
              {Object.entries(scoreBreakdown)
                .filter(([, val]) => val !== 0)
                .map(([key, val]) => (
                  <li key={key}>
                    {key}: <span className="text-gray-800 font-bold">{val}</span>
                  </li>
                ))}
            </ul>
          )}
        </div>
      )}

      {renderHistory()}

      <div className="flex justify-between mt-5">
        <button
          className="bg-gray-300 px-4 py-2 rounded text-sm"
          onClick={onClose}
          disabled={isSubmitting}
        >
          Cancel
        </button>
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm"
          onClick={handleSubmit}
          disabled={isSubmitting}
        >
          {isSubmitting ? "Submitting..." : "Submit Mutation"}
        </button>
      </div>
    </div>
  );
};

export default GlyphInspector;