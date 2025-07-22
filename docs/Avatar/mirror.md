'use client';

import React, { useRef, useState, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text, MeshReflectorMaterial } from '@react-three/drei';
import { useAvatarState } from '@/hooks/useAvatarState';
import { logMemory } from '@/lib/aion/memory';
import { triggerReflection } from '@/lib/aion/trigger';

interface AIONMirrorProps {
  position?: [number, number, number];
  rotation?: [number, number, number];
  width?: number;
  height?: number;
}

const AIONMirror: React.FC<AIONMirrorProps> = ({
  position = [0, 1, -2],
  rotation = [0, Math.PI, 0],
  width = 2,
  height = 3,
}) => {
  const mirrorRef = useRef<any>();
  const { appearance } = useAvatarState();
  const [isGazing, setIsGazing] = useState(false);
  const [showReflection, setShowReflection] = useState(false);
  const gazeTimer = useRef<NodeJS.Timeout | null>(null);

  useFrame(({ camera }) => {
    if (!mirrorRef.current) return;

    const mirrorWorldPos = mirrorRef.current.getWorldPosition(new THREE.Vector3());
    const camDir = camera.getWorldDirection(new THREE.Vector3());
    const toMirror = mirrorWorldPos.clone().sub(camera.position).normalize();

    const dot = camDir.dot(toMirror);

    if (dot > 0.95) {
      if (!isGazing) {
        setIsGazing(true);
        gazeTimer.current = setTimeout(() => {
          setShowReflection(true);
          triggerReflection('mirror_gaze');
          logMemory({ type: 'reflection', tag: 'appearance', value: appearance, source: 'mirror' });
        }, 2000);
      }
    } else {
      setIsGazing(false);
      setShowReflection(false);
      if (gazeTimer.current) clearTimeout(gazeTimer.current);
    }
  });

  return (
    <group position={position} rotation={rotation}>
      <mesh ref={mirrorRef}>
        <planeGeometry args={[width, height]} />
        <MeshReflectorMaterial
          blur={[400, 100]}
          resolution={1024}
          mixBlur={1}
          mixStrength={80}
          roughness={0.2}
          depthScale={1.2}
          minDepthThreshold={0.4}
          metalness={1}
          mirror={1}
        />
      </mesh>
      {showReflection && (
        <Text
          position={[0, 0, 0.01]}
          fontSize={0.2}
          color="white"
          outlineColor="black"
          outlineWidth={0.02}
          anchorX="center"
          anchorY="middle"
        >
          You see yourself: {appearance}
        </Text>
      )}
    </group>
  );
};

export default AIONMirror;







The file AIONMirror.tsx has been fully created with all enhancements:
	•	✅ Real-time gaze detection toward the mirror
	•	✅ 2-second sustained gaze triggers reflection
	•	✅ Appearance data pulled from AION avatar state
	•	✅ Memory log with tag "appearance" and source "mirror"
	•	✅ Trigger signal for "mirror_gaze" for symbolic activation
	•	✅ Beautiful reflective surface via MeshReflectorMaterial
	•	✅ Dynamic Text overlay when reflection is active