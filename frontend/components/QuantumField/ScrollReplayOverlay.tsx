import React from "react";

interface ScrollReplayOverlayProps {
  trail?: any[];
}

const ScrollReplayOverlay: React.FC<ScrollReplayOverlayProps> = ({ trail = [] }) => {
  return (
    <>
      {trail.map((item, i) => (
        <mesh key={`scroll-replay-${i}`} position={item.position}>
          <sphereGeometry args={[0.3, 24, 24]} />
          <meshStandardMaterial color="#ff00ff" transparent opacity={0.2} />
        </mesh>
      ))}
    </>
  );
};

export default ScrollReplayOverlay;