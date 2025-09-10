import React from "react";

interface EmotionOverlayProps {
  nodes: any[]; // Replace with proper type
}

const EmotionOverlay: React.FC<EmotionOverlayProps> = ({ nodes }) => {
  return (
    <>
      {nodes.map((node) => {
        if (!node.emotion) return null;
        return (
          <mesh key={`emotion-${node.id}`} position={node.position}>
            <sphereGeometry args={[0.6, 32, 32]} />
            <meshStandardMaterial
              color={node.emotion === "curiosity" ? "#00ffcc" :
                     node.emotion === "frustration" ? "#ff5555" :
                     "#ccccff"}
              transparent
              opacity={0.3}
              emissive="#ffffff"
              emissiveIntensity={0.8}
            />
          </mesh>
        );
      })}
    </>
  );
};

export default EmotionOverlay;