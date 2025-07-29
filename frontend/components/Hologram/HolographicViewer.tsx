// frontend/components/Hologram/HolographicViewer.tsx
"use client";

import { useEffect, useRef, useState, forwardRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html, Line } from "@react-three/drei"; // ✅ Added Line for entanglement paths
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
import SoulLawHUD from '@/components/Soul/SoulLawHUD'
import { useCanvasRecorder } from "@/hooks/useCanvasRecorder";

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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { isRecording, startRecording, stopRecording, downloadRecording, downloadUrl } = useCanvasRecorder();
  const [predictionForks, setPredictionForks] = useState<any[]>([]);

  // ✅ NEW: entanglement links and captions
  const [entangledLinks, setEntangledLinks] = useState<{ source: GlyphPoint; target: GlyphPoint }[]>([]);
  const [currentCaption, setCurrentCaption] = useState<string>("");

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
      setEntangledLinks([]);
      setCurrentCaption("");
    }
    if (lastJsonMessage?.event === "glyph_triggered") {
      const updated = lastJsonMessage.activation;
      const mesh = glyphRefs.current[updated.glyph_id];
      if (mesh) mesh.material.color.set("#ff00ff");
    }
    // ✅ NEW: listen for entangled replay frames
    if (lastJsonMessage?.type === "glyph_replay_frame") {
      const { glyphs = [], entangled_links = [], caption = "" } = lastJsonMessage;

    // 🔮 NEW: Listen for predictive forks (A7b/A7c + A8c agent colors)
    if (lastJsonMessage?.type === "predictive_forks_response") {
      const forks = lastJsonMessage.predictions || [];

      const ghostLinks = forks
        .map((p: any) => ({
          id: p.id,
          source: combinedProjection?.light_field.find((g) => g.symbol === p.input_glyph),
          target: {
            glyph_id: `ghost-${p.id}`,
            symbol: p.predicted_glyph,
            position: {
              x: Math.random() * 4 - 2,
              y: Math.random() * 4 - 2,
              z: Math.random() * 2 - 1,
              t: "future",
            },
            light_intensity: 0.3,
            trigger_state: "ghost",
            agent_id: p.agent_id || "remote", // ✅ Ghost fork agent identity
          },
          confidence: p.confidence,
        }))
        .filter((link: { source: GlyphPoint }) => link.source); // ✅ Typed filter

      // Merge ghost dashed links into entangled links
      setEntangledLinks((prev) => [...prev, ...ghostLinks]);

      // Caption with predicted forks + confidence
      setCurrentCaption(
        `🔮 Predicted forks: ${forks
          .map((f: any) => `${f.predicted_glyph} (${(f.confidence * 100).toFixed(0)}%)`)
          .join(", ")}`
      );

      // ✅ Store forks for Accept/Reject buttons
      setPredictionForks(forks);
    }

    // 🔗 Entangled link mapping (↔ live links)
    if (entangled_links.length > 0 && combinedProjection) {
      const mappedLinks = entangled_links
        .map((link: any) => {
          const source = combinedProjection.light_field.find((g) => g.glyph_id === link.source);
          const target = combinedProjection.light_field.find((g) => g.glyph_id === link.target);
          return source && target ? { source, target } : null;
        })
        .filter((l): l is { source: GlyphPoint; target: GlyphPoint } => !!l);

      setEntangledLinks(mappedLinks);
    } else {
      setEntangledLinks([]); // clear links if none present
    }

    // 🏷️ Caption fallback: if no predictive forks or caption, list glyph symbols
    if (caption) {
      setCurrentCaption(caption);
    } else if (glyphs.length > 0) {
      const symbols = glyphs.map((g: any) => g.symbol || g.glyph || "?").join(", ");
      setCurrentCaption(`Glyphs: ${symbols}`);
    } else {
      setCurrentCaption("");
    }
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

      // ✅ Update caption + entangled links for this frame (slider-driven)
      const entLinks = entangledLinks.filter(
        (link) => link.source.glyph_id === g.glyph_id || link.target.glyph_id === g.glyph_id
      );
      if (entLinks.length > 0) {
        setCurrentCaption(`↔ Entangled: ${entLinks.map(l => `${l.source.symbol} ↔ ${l.target.symbol}`).join(", ")}`);
      } else {
        setCurrentCaption(`Glyph: ${g.symbol}`);
      }
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
      <Canvas ref={canvasRef} camera={{ position: [0, 0, 3.5], fov: 45 }}>
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

            {/* ✅ Render entangled glyph paths (↔ lines) */}
            {entangledLinks.map((link, idx) => (
              <Line
                key={`ent-link-${idx}`}
                points={[
                  [link.source.position.x, link.source.position.y, link.source.position.z],
                  [link.target.position.x, link.target.position.y, link.target.position.z]
                ]}
                color="#aa00ff"
                lineWidth={2}
                transparent
                opacity={0.7}
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
        currentCaption={currentCaption} // ✅ Added caption prop
      />

      {/* 🎥 Recording Controls */}
      <div className="absolute top-4 left-4 flex gap-2 z-50">
        <button
          onClick={() => isRecording ? stopRecording() : startRecording(canvasRef.current!)}
          className={`px-3 py-1 text-xs rounded shadow ${isRecording ? "bg-red-500 hover:bg-red-600" : "bg-green-500 hover:bg-green-600"}`}
        >
          {isRecording ? "⏹ Stop Recording" : "🎥 Start Recording"}
        </button>
        {downloadUrl && (
          <button
            onClick={() => downloadRecording()}
            className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 rounded shadow"
          >
            💾 Save Video
          </button>
        )}
      </div>
      
      {/* 🔮 Prediction Fork Controls */}
      {predictionForks.length > 0 && (
        <div className="absolute bottom-36 left-1/2 transform -translate-x-1/2 flex gap-4 bg-black/70 px-4 py-2 rounded-lg shadow-lg z-50">
          <button
            onClick={() => {
              predictionForks.forEach((f) =>
                sendJsonMessage({ event: "prediction_accept", glyph_id: f.id })
              );
              setPredictionForks([]); // clear after accept
            }}
            className="px-3 py-1 bg-green-600 hover:bg-green-700 rounded text-white text-sm shadow"
          >
            ✅ Accept Forks
          </button>
          <button
            onClick={() => setPredictionForks([])}
            className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-white text-sm shadow"
          >
            ❌ Reject Forks
          </button>
        </div>
      )}

      {/* ✅ Pass caption to HUD */}
      {currentCaption && (
        <div className="absolute bottom-24 left-1/2 transform -translate-x-1/2 bg-black/70 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          {currentCaption}
        </div>
      )}

      {/* 🔮 Accept/Reject Predicted Forks (A7c) */}
      {predictionForks?.length > 0 && (
        <div className="absolute bottom-40 left-1/2 transform -translate-x-1/2 flex gap-2">
          <button
            onClick={() => {
              sendJsonMessage({ event: "accept_prediction_forks", forks: predictionForks });
              setPredictionForks([]);
            }}
            className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded shadow"
          >
            ✅ Accept Forks
          </button>
          <button
            onClick={() => setPredictionForks([])}
            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded shadow"
          >
            ❌ Reject
          </button>
        </div>
      )}

      <GHXReplaySlider
        projection={combinedProjection}
        onFrameSelect={handleFrameSelect}
        onPlayToggle={(v) => setReplayMode(v)}
      />

      <SoulLawHUD />
    </div>
  );
}

// Existing AnimatedGlyphNode remains unchanged
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