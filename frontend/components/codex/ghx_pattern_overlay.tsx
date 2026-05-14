// File: frontend/components/codex/ghx_pattern_overlay.tsx

import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";

interface PatternStep {
  timestamp?: string;
  glyphs?: string[];
  context?: string;
  prediction?: string[];
  sqi_score?: number;
  event_type?: string;
  emotion?: string;
  intensity?: number;
}

interface PatternReplayData {
  pattern_id: string;
  steps: PatternStep[];
  summary: string;
  glyphs: string[];
  avg_sqi?: number;
}

interface Props {
  replay: PatternReplayData;
  highlight?: boolean;
  autoPlay?: boolean;
}

const tagColors: Record<string, string> = {
  activation: "bg-green-700",
  collapse: "bg-red-700",
  evolution: "bg-blue-700",
  mutation: "bg-yellow-700 text-black",
  emotion_tag: "bg-pink-700",
};

const GHXPatternOverlay: React.FC<Props> = ({
  replay,
  highlight = true,
  autoPlay = true,
}) => {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (!autoPlay) return;
    const interval = setInterval(() => {
      setStepIndex((prev) => (prev + 1) % replay.steps.length);
    }, 1500);
    return () => clearInterval(interval);
  }, [replay.steps.length, autoPlay]);

  const current = replay.steps[stepIndex];

  return (
    <Card className="w-full max-w-xl mx-auto my-4 p-4 bg-black text-white border border-purple-500 shadow-xl">
      <CardContent>
        <h2 className="text-lg font-bold text-purple-300">
          Pattern Replay: {replay.pattern_id}
        </h2>
        <p className="text-sm text-gray-400 mb-2">{replay.summary}</p>

        <motion.div
          className="grid grid-cols-5 gap-2 text-center my-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
        >
          {current?.glyphs?.map((glyph, idx) => (
            <span
              key={idx}
              className={`text-xl px-2 py-1 rounded-md border transition-all ${
                highlight ? "bg-purple-800 border-purple-400" : "bg-gray-800 border-gray-700"
              }`}
            >
              {glyph}
            </span>
          ))}
        </motion.div>

        <div className="text-xs text-gray-400 space-y-1">
          <div>⏱️ {current?.timestamp || "Unknown time"}</div>
          <div>🎯 Context: {current?.context || "None"}</div>
          <div>🔮 Prediction: {current?.prediction?.join(", ") || "N/A"}</div>
          <div>🧠 SQI Score: {current?.sqi_score?.toFixed(4) ?? "N/A"}</div>

          {current?.event_type && (
            <div className={`inline-block px-2 py-1 rounded-md text-xs font-semibold mt-1 ${
              tagColors[current.event_type] || "bg-gray-700"
            }`}>
              🔁 Event: {current.event_type}
            </div>
          )}

          {current?.emotion && (
            <div className="text-pink-400">
              💓 Emotion: {current.emotion} ({(current.intensity ?? 0).toFixed(2)})
            </div>
          )}
        </div>

        {/* Optional controls (future): 
        <div className="flex mt-2 space-x-2 justify-end">
          <button onClick={() => setStepIndex(Math.max(0, stepIndex - 1))}>◀️</button>
          <button onClick={() => setStepIndex((stepIndex + 1) % replay.steps.length)}>▶️</button>
        </div>
        */}
      </CardContent>
    </Card>
  );
};

export default GHXPatternOverlay;