// SymbolicTeleportPath.tsx
export function SymbolicTeleportPath({ path }: { path: [number, number, number][] }) {
  return (
    <group>
      {path.map((pos, idx) => (
        <mesh key={idx} position={pos}>
          <sphereGeometry args={[0.03, 12, 12]} />
          <meshStandardMaterial color="#66ffcc" emissive="#229988" emissiveIntensity={1} />
        </mesh>
      ))}
    </group>
  );
}