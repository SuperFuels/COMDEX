// frontend/components/AION/GlyphInspector.tsx
import React, { useState } from "react";
import { mutateGlyph, scoreMutation } from "@/lib/api";
import useWebSocket from "../../hooks/useWebSocket";

interface GlyphInspectorProps {
  coord: string;
  data: any;
  onClose: () => void;
  history?: any[];
}

const GlyphInspector: React.FC<GlyphInspectorProps> = ({ coord, data, onClose, history = [] }) => {
  const [editedGlyph, setEditedGlyph] = useState(data);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localScore, setLocalScore] = useState<number | null>(data?.score ?? null);
  const [scoreBreakdown, setScoreBreakdown] = useState<Record<string, number> | null>(
    data?.score_breakdown ?? null
  );

  const { emit } = useWebSocket("ws://localhost:8000/ws", () => {}, ["glyph_update"]);

  const handleChange = (field: string, value: string) => {
    setEditedGlyph({ ...editedGlyph, [field]: value });
  };

  const validate = () => {
    const required = ["type", "tag", "value", "action"];
    return required.every((f) => editedGlyph[f] && editedGlyph[f].trim() !== "");
  };

  const handleSubmit = async () => {
    if (!validate()) {
      alert("Please fill out all fields (type, tag, value, action)");
      return;
    }

    setIsSubmitting(true);
    try {
      await mutateGlyph(editedGlyph);

      const scored = await scoreMutation(editedGlyph);
      if (scored && typeof scored.total === "number") {
        setLocalScore(scored.total);
        setScoreBreakdown(scored.breakdown);
      }

      emit("glyph_updated", { coord, glyph: editedGlyph }); // ✅ Correct emit
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      alert("Failed to mutate glyph: " + message);
    }
    setIsSubmitting(false);
  };

  const previewLogic = () => {
    const { type, tag, value, action } = editedGlyph || {};
    if (!type && !tag && !value && !action) return null;
    const symbol = `⟦ ${type || "?"} | ${tag || "?"} : ${value || "?"} → ${action || "?"} ⟧`;
    return (
      <div className="bg-gray-100 p-3 mt-3 rounded text-sm font-mono text-gray-800 border">
        <div className="text-xs text-gray-500 mb-1">Symbolic Logic:</div>
        {symbol}
      </div>
    );
  };

  const renderHistory = () => {
    if (!Array.isArray(history) || history.length === 0) return null;
    return (
      <div className="mt-4 text-sm">
        <div className="text-xs text-gray-400 mb-1">History:</div>
        <ul className="max-h-32 overflow-y-auto border p-2 rounded bg-gray-50 text-xs">
          {history.map((h, idx) => (
            <li key={idx}>
              ⟦ {h.type || "?"} | {h.tag || "?"} : {h.value || "?"} → {h.action || "?"} ⟧
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="p-4 border rounded bg-white shadow-md w-full max-w-lg relative">
      {isSubmitting && (
        <div className="absolute inset-0 bg-white bg-opacity-60 flex items-center justify-center z-10">
          <div className="text-blue-600 animate-spin text-xl">⏳</div>
        </div>
      )}

      <h2 className="text-lg font-bold mb-3">Edit Glyph: {coord}</h2>

      <label className="block mb-2">
        Type:
        <input
          className="w-full border px-2 py-1"
          value={editedGlyph.type}
          onChange={(e) => handleChange("type", e.target.value)}
        />
      </label>

      <label className="block mb-2">
        Tag:
        <input
          className="w-full border px-2 py-1"
          value={editedGlyph.tag}
          onChange={(e) => handleChange("tag", e.target.value)}
        />
      </label>

      <label className="block mb-2">
        Value:
        <input
          className="w-full border px-2 py-1"
          value={editedGlyph.value}
          onChange={(e) => handleChange("value", e.target.value)}
        />
      </label>

      <label className="block mb-2">
        Action:
        <input
          className="w-full border px-2 py-1"
          value={editedGlyph.action}
          onChange={(e) => handleChange("action", e.target.value)}
        />
      </label>

      {typeof localScore === "number" && (
        <div className="mt-4">
          <div className="text-sm font-semibold mb-1">🧠 Mutation Score:</div>
          <div className="bg-gray-800 text-white rounded px-3 py-2 text-sm w-fit">
            Total Score: <span className="font-bold">{localScore}</span>
          </div>
          {scoreBreakdown && (
            <ul className="text-xs text-gray-400 mt-2 list-disc list-inside">
              {Object.entries(scoreBreakdown).map(([key, val]) => (
                <li key={key}>
                  {key}: <span className="text-white">{val}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {previewLogic()}
      {renderHistory()}

      <div className="flex justify-between mt-4">
        <button
          className="bg-gray-300 px-4 py-2 rounded"
          onClick={onClose}
          disabled={isSubmitting}
        >
          Cancel
        </button>
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded"
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