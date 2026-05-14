import React from "react";

export interface QWaveMetadata {
  emotion?: string;
  memory_weight?: number;
  logic_packet?: {
    trace_direction?: string;
    infer_depth?: number;
  };
}

export interface QWavePreviewPanelProps {
  selectedBeamId?: string;
  beamMetadata?: QWaveMetadata;
}

export const QWavePreviewPanel: React.FC<QWavePreviewPanelProps> = ({
  selectedBeamId,
  beamMetadata,
}) => {
  if (!selectedBeamId || !beamMetadata) return null;

  const {
    emotion = "neutral",
    memory_weight = 0,
    logic_packet = {},
  } = beamMetadata;

  const emotionLabel = {
    curiosity: "🧠 Curious Beam",
    urgency: "⚡ Urgent Beam",
    wonder: "✨ Wonder Beam",
    neutral: "🔸 Neutral Beam",
  }[emotion] || "🔸 Unknown Beam";

  const trace = logic_packet.trace_direction || "unknown";
  const depth = logic_packet.infer_depth ?? "N/A";

  return (
    <div className="absolute bottom-4 left-4 bg-white/90 text-black rounded-xl p-4 shadow-lg max-w-sm z-50">
      <div className="text-xl font-bold mb-2">{emotionLabel}</div>
      <div className="text-sm">
        <div><strong>Beam ID:</strong> {selectedBeamId}</div>
        <div><strong>Emotion:</strong> {emotion}</div>
        <div><strong>Memory Weight:</strong> {memory_weight.toFixed(2)}</div>
        <div><strong>Logic Inference:</strong></div>
        <ul className="ml-4 list-disc">
          <li><strong>Direction:</strong> {trace}</li>
          <li><strong>Depth:</strong> {depth}</li>
        </ul>
      </div>
    </div>
  );
};