import React from "react";

interface StrategyOverlayProps {
  strategies: any[];
}

const StrategyOverlay: React.FC<StrategyOverlayProps> = ({ strategies }) => {
  return (
    <>
      {strategies.map((s, i) => (
        <mesh key={`strategy-${i}`} position={s.position}>
          <boxGeometry args={[0.4, 0.4, 0.4]} />
          <meshStandardMaterial color="#00f" transparent opacity={0.4} />
        </mesh>
      ))}
    </>
  );
};

export default StrategyOverlay;