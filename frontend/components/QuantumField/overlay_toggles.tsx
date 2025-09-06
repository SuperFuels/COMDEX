// frontend/components/QuantumField/overlay_toggles.tsx

import React from "react";

export interface OverlayToggleState {
  showPredicted: boolean;
  showCollapsed: boolean;
  showSQIScore: boolean;
  onTogglePredicted: () => void;
  onToggleCollapsed: () => void;
  onToggleSQIScore: () => void;
}

const OverlayToggles: React.FC<OverlayToggleState> = ({
  showPredicted,
  showCollapsed,
  showSQIScore,
  onTogglePredicted,
  onToggleCollapsed,
  onToggleSQIScore,
}) => {
  return (
    <div className="flex flex-col space-y-2 p-2 text-xs text-white">
      <label className="inline-flex items-center space-x-2">
        <input
          type="checkbox"
          checked={showPredicted}
          onChange={onTogglePredicted}
          className="form-checkbox text-cyan-400"
        />
        <span>🔮 Show Predicted</span>
      </label>
      <label className="inline-flex items-center space-x-2">
        <input
          type="checkbox"
          checked={showCollapsed}
          onChange={onToggleCollapsed}
          className="form-checkbox text-pink-400"
        />
        <span>💥 Show Collapsed</span>
      </label>
      <label className="inline-flex items-center space-x-2">
        <input
          type="checkbox"
          checked={showSQIScore}
          onChange={onToggleSQIScore}
          className="form-checkbox text-green-400"
        />
        <span>📊 Show SQI Score</span>
      </label>
    </div>
  );
};

export default OverlayToggles;