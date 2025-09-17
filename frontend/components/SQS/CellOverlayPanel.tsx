// File: frontend/components/SQS/CellOverlayPanel.tsx

import React from "react";

interface CellOverlayPanelProps {
  id?: string;
  position?: number[];
  sqi?: number;
  entropy?: number;
  mutated?: boolean;
  mutationNotes?: string[];
  emotion?: string;
  visible: boolean;
}

export const CellOverlayPanel: React.FC<CellOverlayPanelProps> = ({
  id,
  position,
  sqi,
  entropy,
  mutated,
  mutationNotes = [],
  emotion,
  visible,
}) => {
  if (!visible) return null;

  return (
    <div className="absolute right-4 top-4 bg-white shadow-xl rounded-2xl border border-gray-300 p-4 max-w-md text-sm z-50">
      <div className="font-semibold text-gray-700 mb-2">🧠 Cell Insight</div>

      {id && (
        <div>
          <span className="font-medium text-gray-600">ID:</span> {id}
        </div>
      )}

      {position && (
        <div>
          <span className="font-medium text-gray-600">Position:</span> [{position.join(", ")}]
        </div>
      )}

      {typeof sqi === "number" && (
        <div>
          <span className="font-medium text-gray-600">SQI:</span> {sqi.toFixed(4)}
        </div>
      )}

      {typeof entropy === "number" && (
        <div>
          <span className="font-medium text-gray-600">Entropy:</span> {entropy.toFixed(4)}
        </div>
      )}

      {emotion && (
        <div>
          <span className="font-medium text-gray-600">Emotion:</span> {emotion}
        </div>
      )}

      {mutated && (
        <div className="mt-2">
          <span className="font-medium text-gray-600">Mutations:</span>
          <ul className="list-disc list-inside text-gray-700">
            {mutationNotes.length > 0 ? (
              mutationNotes.map((note, i) => <li key={i}>{note}</li>)
            ) : (
              <li>Mutation detected</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};