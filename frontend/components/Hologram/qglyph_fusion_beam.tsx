import React, { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { animated, useSpring } from "@react-spring/three";
import { Html } from "@react-three/drei";

type BeamProps = {
  source: THREE.Vector3;
  target: THREE.Vector3;
  logicType?: "collapse" | "mutate" | "push" | "replay";
  entropy?: number;
  cost?: number;
  pulseSpeed?: number;
  showLabel?: boolean;
  onClick?: () => void;
};

const logicColors: Record<string, string> = {
  collapse: "#ff0055",
  mutate: "#00ddff",
  push: "#ffaa00",
  replay: "#cc00ff",
};

function computeGradientColor(entropy?: number, cost?: number, type?: string): string {
  if (type && logicColors[type]) return logicColors[type];
  const hue = (entropy || 0.5) * 240 - (cost || 0) * 40;
  return `hsl(${Math.max(0, Math.min(300, hue))}, 100%, 55%)`;
}

export const QGlyphFusionBeam: React.FC<BeamProps> = ({
  source,
  target,
  logicType,
  entropy,
  cost,
  pulseSpeed = 1,
  showLabel = true,
  onClick,
}) => {
  const beamRef = useRef<THREE.Mesh>(null!);
  const materialRef = useRef<THREE.MeshBasicMaterial>(null!);

  const color = useMemo(() => computeGradientColor(entropy, cost, logicType), [
    entropy,
    cost,
    logicType,
  ]);

  const direction = useMemo(() => {
    const dir = new THREE.Vector3().subVectors(target, source);
    return {
      length: dir.length(),
      rotation: new THREE.Euler().setFromQuaternion(
        new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          dir.clone().normalize()
        )
      ),
    };
  }, [source, target]);

  const animatedProps = useSpring({
    scale: pulseSpeed
      ? {
          to: async (next) => {
            while (true) {
              await next({ scale: [1.25, 1, 1.25] });
              await next({ scale: [1, 1, 1] });
            }
          },
        }
      : { scale: [1, 1, 1] },
    config: { duration: 1500 / pulseSpeed },
  });

  useFrame(() => {
    if (materialRef.current) {
      materialRef.current.color.set(color);
      materialRef.current.opacity = 0.5 + 0.4 * Math.sin(Date.now() * 0.005 * pulseSpeed);
    }
  });

  return (
    <>
      <animated.mesh
        ref={beamRef}
        position={source.clone().add(target).multiplyScalar(0.5)}
        rotation={direction.rotation}
        scale={animatedProps.scale}
        onClick={onClick}
      >
        <cylinderGeometry args={[0.03, 0.03, direction.length, 8]} />
        <meshBasicMaterial
          ref={materialRef}
          transparent
          opacity={0.8}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </animated.mesh>

      {showLabel && (
        <Html position={source.clone().add(target).multiplyScalar(0.5)} center distanceFactor={10}>
          <div
            style={{
              background: "rgba(0,0,0,0.6)",
              color: "#fff",
              padding: "4px 8px",
              fontSize: "0.75rem",
              borderRadius: "4px",
              pointerEvents: "none",
              whiteSpace: "nowrap",
            }}
          >
            {logicType || "beam"}
          </div>
        </Html>
      )}
    </>
  );
};