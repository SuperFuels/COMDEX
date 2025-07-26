// frontend/components/Hologram/HolographicViewer.tsx
"use client";

import { useEffect, useRef, useState, forwardRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAvatarGlyphs } from "@/hooks/useAvatarGlyphs";
import { useCodexCoreProjection } from "@/hooks/useCodexCoreProjection";
import HologramHUD from "./HologramHUD";
import { exportGHX } from "@/utils/ghx_exporter";
import { playGlyphNarration, preloadVoices } from "@/utils/hologram_audio";
import GHXReplaySlider from "./GHXReplaySlider";
import LayeredContainerSphere from "./LayeredContainerSphere";
import AvatarThoughtProjection from "@/components/Hologram/AvatarThoughtProjection";
import MemoryHaloRing from "@/components/Hologram/MemoryHaloRing";
import MemoryBridgeBeams from "@/components/Hologram/MemoryBridgeBeams";

type GlyphPoint = {
  glyph_id: string;
  symbol: string;
  position: { x: number; y: number; z: number; t: string };
  light_intensity: number;
  trigger_state: string;
  narration?: {
    text_to_speak: string;
    voice?: string;
    language?: string;
  };
};

type GHXPacket = {
  light_field: GlyphPoint[];
  rendered_at: string;
  projection_id: string;
};

export default function HolographicViewer({ containerId }: { containerId: string }) {
  const [projection, setProjection] = useState<GHXPacket | null>(null);
  const [replayMode, setReplayMode] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [layoutMode, setLayoutMode] = useState<"symbolic" | "raw">("symbolic");
  const [trailHistory, setTrailHistory] = useState<GlyphPoint[]>([]);
  const [focusedGlyph, setFocusedGlyph] = useState<GlyphPoint | null>(null);
  const [showCodexCore, setShowCodexCore] = useState(false);

  const glyphRefs = useRef<{ [id: string]: THREE.Mesh }>({});
  const avatarRef = useRef<THREE.Object3D>(null);
  const wsUrl = `/ws/ghx/${containerId}`;
  const { sendJsonMessage, lastJsonMessage } = useWebSocket(wsUrl);

  const activeGlyphs = useAvatarGlyphs(containerId);
  const coreProjection = useCodexCoreProjection(containerId);
  const combinedProjection = showCodexCore ? coreProjection : projection;

  useEffect(() => {
    preloadVoices();
  }, []);

  useEffect(() => {
    if (lastJsonMessage?.event === "ghx_projection") {
      setProjection(lastJsonMessage.payload);
      setTrailHistory([]);
    }
    if (lastJsonMessage?.event === "glyph_triggered") {
      const updated = lastJsonMessage.activation;
      const mesh = glyphRefs.current[updated.glyph_id];
      if (mesh) mesh.material.color.set("#ff00ff");
    }
  }, [lastJsonMessage]);

  useEffect(() => {
    if (focusedGlyph) {
      const n = focusedGlyph.narration;
      if (n) {
        playGlyphNarration(n.text_to_speak, {
          voice: n.voice,
          language: n.language
        });
      } else {
        playGlyphNarration(focusedGlyph.symbol);
      }
    }
  }, [focusedGlyph]);

  const handleGlyphClick = (glyphId: string, symbol: string) => {
    sendJsonMessage({ event: "trigger_glyph", glyph_id: glyphId });
    const glyph = combinedProjection?.light_field.find((g) => g.glyph_id === glyphId);
    if (glyph?.narration) {
      playGlyphNarration(glyph.narration.text_to_speak, {
        voice: glyph.narration.voice,
        language: glyph.narration.language
      });
    } else {
      playGlyphNarration(`Symbol ${symbol}`);
    }
    if (glyph) setFocusedGlyph(glyph);
  };

  const handleExport = () => {
    if (combinedProjection) exportGHX(combinedProjection);
  };

  const handleFrameSelect = (i: number) => {
    if (combinedProjection) {
      const g = combinedProjection.light_field[i];
      if (g?.narration) {
        playGlyphNarration(g.narration.text_to_speak, {
          voice: g.narration.voice,
          language: g.narration.language
        });
      } else {
        playGlyphNarration(g.symbol);
      }
      setTrailHistory((prev) => [...prev, g]);
      setFocusedGlyph(g);
    }
  };

  const layeredGlyphs =
    combinedProjection?.light_field.map((g, idx) => ({
      symbol: g.symbol,
      layer: idx % 3,
    })) || [];

  const glyphPositionMap: { [symbol: string]: THREE.Vector3 } = {};
  combinedProjection?.light_field.forEach((g) => {
    glyphPositionMap[g.symbol] = new THREE.Vector3(g.position.x, g.position.y, g.position.z);
  });

  return (
    <div className="relative w-full h-[80vh] flex flex-col gap-2">
      <Canvas camera={{ position: [0, 0, 3.5], fov: 45 }}>
        <ambientLight intensity={0.7} />
        <pointLight position={[5, 5, 5]} />
        <OrbitControls />

        {layoutMode === "symbolic" && combinedProjection ? (
          <LayeredContainerSphere
            glyphs={layeredGlyphs}
            radius={2.2}
            rotationSpeed={0.003}
          />
        ) : (
          <>
            {trailHistory.map((glyph, idx) => (
              <mesh
                key={`${glyph.glyph_id}-trail-${idx}`}
                position={[glyph.position.x, glyph.position.y, glyph.position.z]}
              >
                <sphereGeometry args={[0.4, 16, 16]} />
                <meshStandardMaterial color="#ffffff" transparent opacity={0.1} />
              </mesh>
            ))}
            {combinedProjection?.light_field.map((glyph) => (
              <AnimatedGlyphNode
                key={glyph.glyph_id}
                glyph={glyph}
                layoutMode={layoutMode}
                onClick={handleGlyphClick}
                onHover={() => playGlyphNarration(glyph.symbol)}
                ref={(ref) => {
                  if (ref) glyphRefs.current[glyph.glyph_id] = ref;
                }}
              />
            ))}
          </>
        )}

        <AvatarThoughtProjection
          thoughts={activeGlyphs}
          orbitRadius={2.8}
          avatarPosition={[0, 0, 0]}
          avatarRef={avatarRef}
        />

        <MemoryHaloRing
          glyphs={[
            { symbol: "🧠", weight: 1.0 },
            { symbol: "↔", weight: 0.7 },
            { symbol: "⬁", weight: 1.2 },
          ]}
          avatarRef={avatarRef}
        />

        <MemoryBridgeBeams glyphPositions={glyphPositionMap} />
      </Canvas>

      <HologramHUD
        projectionId={combinedProjection?.projection_id}
        renderedAt={combinedProjection?.rendered_at}
        totalGlyphs={combinedProjection?.light_field.length || 0}
        triggeredGlyphs={
          combinedProjection?.light_field.filter((g) => g.trigger_state !== "idle").length || 0
        }
        onReplayToggle={(v) => setReplayMode(v)}
        onTraceOverlayToggle={(v) => setShowTrace(v)}
        onExport={handleExport}
        onLayoutToggle={() =>
          setLayoutMode(layoutMode === "symbolic" ? "raw" : "symbolic")
        }
        onCodexCoreToggle={(v) => setShowCodexCore(v)}
        renderedGlyphs={combinedProjection?.light_field || []}
        setCurrentGlyph={setFocusedGlyph}
      />

      <GHXReplaySlider
        projection={combinedProjection}
        onFrameSelect={handleFrameSelect}
        onPlayToggle={(v) => setReplayMode(v)}
      />
    </div>
  );
}

const AnimatedGlyphNode = forwardRef<THREE.Mesh, {
  glyph: GlyphPoint;
  layoutMode: "symbolic" | "raw";
  onClick: (glyphId: string, symbol: string) => void;
  onHover?: () => void;
}>(({ glyph, layoutMode, onClick, onHover }, ref) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const { camera } = useThree();
  const baseColor = getSymbolColor(glyph.symbol);
  const frequency = getPulseFrequency(glyph.symbol);
  const isMutated = isMutatedGlyph(glyph.symbol);

  const getLayoutPosition = () => {
    if (layoutMode === "symbolic") return [glyph.position.x, glyph.position.y, glyph.position.z];
    const base = glyph.symbol.codePointAt(0) || 0;
    return [
      (base % 10) * 4 - 20,
      Math.floor(base / 10) % 10 * 3 - 10,
      Math.floor(base / 100) % 10 * 3 - 5
    ];
  };

  useFrame(({ clock }) => {
    if (meshRef.current) {
      const pulse = 0.5 + 0.5 * Math.sin(clock.elapsedTime * frequency);
      const dist = meshRef.current.position.distanceTo(camera.position);
      const dirToGlyph = new THREE.Vector3().subVectors(meshRef.current.position, camera.position).normalize();
      const gazeBoost = dirToGlyph.dot(camera.getWorldDirection(new THREE.Vector3()));
      const focusFactor = Math.max(0, gazeBoost);
      const mat = meshRef.current.material as THREE.MeshStandardMaterial;
      const intensity = glyph.light_intensity * (1 + pulse + 0.8 * focusFactor);
      mat.emissiveIntensity = isMutated ? intensity * 2.2 : intensity;
    }
  });

  return (
    <mesh
      position={getLayoutPosition()}
      ref={(node) => {
        meshRef.current = node!;
        if (ref && typeof ref === "function") ref(node!);
        else if (ref && typeof ref === "object") (ref as any).current = node!;
      }}
      onClick={() => onClick(glyph.glyph_id, glyph.symbol)}
      onPointerOver={() => onHover?.()}
    >
      <sphereGeometry args={[0.7, 32, 32]} />
      <meshStandardMaterial
        color={isMutated ? "#ff4444" : baseColor}
        emissive={isMutated ? "#ff4444" : baseColor}
        emissiveIntensity={glyph.light_intensity}
      />
      <Html distanceFactor={8}>
        <div className="text-xs text-white bg-black/50 px-1 py-0.5 rounded">
          {glyph.symbol}
        </div>
      </Html>
    </mesh>
  );
});
AnimatedGlyphNode.displayName = "AnimatedGlyphNode";

function isMutatedGlyph(symbol: string) {
  return symbol === "⬁";
}

function getSymbolColor(symbol: string) {
  switch (symbol) {
    case "⊕": return "#ffcc00";
    case "↔": return "#aa00ff";
    case "⧖": return "#00ffff";
    case "🧠": return "#00ff66";
    case "⬁": return "#ff4444";
    case "→": return "#66ccff";
    default: return "#ffffff";
  }
}

function getPulseFrequency(symbol: string) {
  const base = symbol.codePointAt(0) || 42;
  return 0.5 + (base % 5) * 0.2;
}