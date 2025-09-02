// GHXAnchorMemory.tsx
export function GHXAnchorMemory({ anchors }: { anchors: any[] }) {
  return (
    <group>
      {anchors.map((a, i) => (
        <mesh key={i} position={a.position}>
          <boxGeometry args={[0.1, 0.1, 0.1]} />
          <meshStandardMaterial color="#ffcc00" transparent opacity={0.5} />
        </mesh>
      ))}
    </group>
  );
}