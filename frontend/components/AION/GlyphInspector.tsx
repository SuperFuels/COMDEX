import React, { useState } from "react";
import { mutateGlyph, scoreMutation } from "@/lib/api";

interface GlyphInspectorProps {
  coord: string;
  data: any;
  onClose: () => void;
}

const GlyphInspector: React.FC<GlyphInspectorProps> = ({ coord, data, onClose }) => {
  const [editedGlyph, setEditedGlyph] = useState(data);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localScore, setLocalScore] = useState<number | null>(data?.score ?? null);
  const [scoreBreakdown, setScoreBreakdown] = useState<Record<string, number> | null>(
    data?.score_breakdown ?? null
  );

  const handleChange = (field: string, value: string) => {
    setEditedGlyph({ ...editedGlyph, [field]: value });
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await mutateGlyph(editedGlyph);

      // ⏱️ Optionally auto-score after mutation
      const scored = await scoreMutation(editedGlyph);
      if (scored && typeof scored.total === "number") {
        setLocalScore(scored.total);
        setScoreBreakdown(scored.breakdown);
      }

      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      alert("Failed to mutate glyph: " + message);
    }
    setIsSubmitting(false);
  };

  return (
    <div className="p-4 border rounded bg-white shadow-md w-full max-w-lg">
      <h2 className="text-lg font-bold mb-2">Edit Glyph: {coord}</h2>

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

      {/* 🧠 Mutation Score */}
      {typeof localScore === "number" && (
        <div className="mt-4">
          <div className="text-sm font-semibold mb-1">🧠 Mutation Score:</div>
          <div className="bg-gray-800 text-white rounded px-3 py-2 text-sm w-fit">
            Total Score: <span className="font-bold">{localScore}</span>
          </div>
          {scoreBreakdown && typeof scoreBreakdown === "object" && (
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