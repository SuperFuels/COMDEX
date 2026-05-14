import React from "react";

export const getHeatColor = (heatLevel: number = 0) => {
  if (heatLevel > 0.8) return "#ff0000";     // 🔥 hot
  if (heatLevel > 0.5) return "#ffaa00";     // 🟧 warm
  if (heatLevel > 0.2) return "#00ccff";     // 🟦 cool
  return "#888888";                          // neutral
};

export default function HeatMapOverlay({ glyphs }: { glyphs: any[] }) {
  return (
    <>
      {glyphs.map((g) =>
        g.position && g.heatLevel > 0 ? (
          <mesh key={`heatmap-${g.id}`} position={g.position}>
            <sphereGeometry args={[0.3 + g.heatLevel * 0.4, 16, 16]} />
            <meshBasicMaterial
              color={getHeatColor(g.heatLevel)}
              transparent
              opacity={0.2 + g.heatLevel * 0.6}
            />
          </mesh>
        ) : null
      )}
    </>
  );
}