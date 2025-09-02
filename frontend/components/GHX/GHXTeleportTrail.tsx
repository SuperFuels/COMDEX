// GHXTeleportTrail.tsx
export function GHXTeleportTrail({ trail = [] }: { trail: [number, number, number][] }) {
  if (trail.length < 2) return null;
  const points = trail.flat();

  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={trail.length}
          array={new Float32Array(points)}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial color="#00ffff" linewidth={2} />
    </line>
  );
}