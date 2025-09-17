// File: frontend/components/EmotionSQIPanel.tsx

import React from "react";

export type EmotionSQIPanelProps = {
  emotion?: string;
  sqi?: number;
};

export const EmotionSQIPanel: React.FC<EmotionSQIPanelProps> = ({ emotion, sqi }) => {
  const emotionEmoji = {
    inspired: "💡",
    curious: "🤔",
    neutral: "😐",
    frustrated: "😣",
    excited: "🎉",
    anxious: "😰",
  }[emotion || "neutral"];

  const getSQITier = (score: number | undefined) => {
    if (score === undefined) return { label: "n/a", color: "gray" };
    if (score > 0.9) return { label: "Ultra", color: "purple" };
    if (score > 0.75) return { label: "High", color: "blue" };
    if (score > 0.5) return { label: "Medium", color: "green" };
    if (score > 0.25) return { label: "Low", color: "yellow" };
    return { label: "Weak", color: "red" };
  };

  const tier = getSQITier(sqi);

  return (
    <div className="text-xs p-2 rounded-md border border-gray-200 bg-white shadow-sm w-fit space-y-1">
      <div className="flex items-center gap-1">
        <span className="text-sm">Emotion:</span>
        <span title={emotion} className="font-semibold">
          {emotionEmoji} {emotion || "neutral"}
        </span>
      </div>

      <div className="flex items-center gap-1">
        <span className="text-sm">SQI:</span>
        <span
          className={`text-${tier.color}-600 font-semibold px-2 py-0.5 rounded bg-${tier.color}-100`}
          title={`Tier: ${tier.label}`}
        >
          {sqi !== undefined ? sqi.toFixed(2) : "n/a"} ({tier.label})
        </span>
      </div>
    </div>
  );
};

export default EmotionSQIPanel;