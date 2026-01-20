// GHXReplaySelector.tsx
import { Html as DreiHtml } from '@react-three/drei';

export function GHXReplaySelector({ trace = [], onSelect }: { trace: any[]; onSelect: (idx: number) => void }) {
  return (
    <group>
      {trace.map((item, idx) => (
        <mesh
          key={item.id}
          position={item.position}
          onClick={(e) => {
            e.stopPropagation();
            onSelect(idx);
          }}
        >
          <sphereGeometry args={[0.05, 16, 16]} />
          <meshStandardMaterial emissive="#ffaa00" emissiveIntensity={1.5} />
          <DreiHtml center>
            <div style={{ fontSize: "0.7em", color: "#ffaa00" }}>⧖ {idx}</div>
          </DreiHtml>
        </mesh>
      ))}
    </group>
  );
}