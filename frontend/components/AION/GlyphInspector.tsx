import React, { useState } from "react";
import { Glyph } from "@/types";
import { mutateGlyph } from "@/lib/api"

interface GlyphInspectorProps {
  coord: string;
  data: any;
  onClose: () => void;
}

const GlyphInspector: React.FC<GlyphInspectorProps> = ({ coord, data, onClose }) => {
  const [editedGlyph, setEditedGlyph] = useState(data);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (field: string, value: string) => {
    setEditedGlyph({ ...editedGlyph, [field]: value });
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      // Assuming mutateGlyph is imported and expects the glyph data
      await mutateGlyph(editedGlyph);
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