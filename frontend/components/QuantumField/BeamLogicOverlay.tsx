// 📁 components/QuantumField/BeamLogicOverlay.tsx
import React from "react";
import { Html as DreiHtml } from "@react-three/drei";

interface BeamLogicPacket {
  trace_direction?: string;
  infer_depth?: number;
  cause?: string;
  intent?: string;
  prediction?: string;
}

interface BeamLogicOverlayProps {
  position: [number, number, number];
  packet: BeamLogicPacket;
  visible: boolean;
}

const BeamLogicOverlay: React.FC<BeamLogicOverlayProps> = ({ position, packet, visible }) => {
  if (!visible || !packet) return null;

  return (
    <DreiHtml
      position={[position[0], position[1] + 1.2, position[2]]}
      center
      distanceFactor={8}
    >
      <div className="bg-black/80 text-white text-xs px-3 py-2 rounded shadow max-w-sm animate-fade-in">
        <div className="font-bold mb-1 text-indigo-300">Logic Packet</div>

        {packet.trace_direction && (
          <div>
            <strong className="text-sky-400">Direction:</strong> {packet.trace_direction}
          </div>
        )}

        {typeof packet.infer_depth === "number" && (
          <div>
            <strong className="text-purple-400">Depth:</strong> {packet.infer_depth}
          </div>
        )}

        {packet.cause && (
          <div>
            <strong className="text-pink-400">Cause:</strong> {packet.cause}
          </div>
        )}

        {packet.intent && (
          <div>
            <strong className="text-emerald-400">Intent:</strong> {packet.intent}
          </div>
        )}

        {packet.prediction && (
          <div>
            <strong className="text-yellow-300">Prediction:</strong> {packet.prediction}
          </div>
        )}
      </div>
    </DreiHtml>
  );
};

export default BeamLogicOverlay;