// DreamGhostEntry.tsx
import { Html } from '@react-three/drei';

export function DreamGhostEntry({ position, label }: { position: [number, number, number]; label?: string }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.1, 16, 16]} />
      <meshStandardMaterial color="#8844ff" transparent opacity={0.3} />
      {label && (
        <Html center>
          <div style={{ fontSize: "0.6em", color: "#8844ff", opacity: 0.8 }}>{label}</div>
        </Html>
      )}
    </mesh>
  );
}