// frontend/components/Hologram/HolographicViewer.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import { forwardRef } from "react";              // <-- fixes 'forwardRef' not found
import { Canvas, useFrame, useThree } from "@react-three/fiber"; // <-- ensures types are present

// ✅ hooks (default / named as you actually export them)
import useWebSocket from "@/hooks/useWebSocket";
import { useAvatarGlyphs } from "@/hooks/useAvatarGlyphs";
import { useCodexCoreProjection } from "@/hooks/useCodexCoreProjection";

import HologramHUD from "./HologramHUD";
import GHXReplaySlider from "./GHXReplaySlider";
import AvatarThoughtProjection from "@/components/Hologram/AvatarThoughtProjection";
import MemoryHaloRing from "@/components/Hologram/MemoryHaloRing";
import MemoryBridgeBeams from "@/components/Hologram/MemoryBridgeBeams";
import SoulLawHUD from "@/components/Soul/SoulLawHUD";
import { useCanvasRecorder } from "@/hooks/useCanvasRecorder";

/* ------------------------------------------------------------------ */
/* Shims for missing utilities/components so this file compiles safely */
/* ------------------------------------------------------------------ */

// very small JSON exporter
function exportGHXLocal(data: unknown, name = "projection") {
  try {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    /* no-op */
  }
}

// text-to-speech (best-effort; safe no-ops SSR)
function preloadVoices() {
  /* optional warmup */
}
function playGlyphNarration(text: string, opts?: { voice?: string; language?: string }) {
  if (typeof window === "undefined") return;
  try {
    const msg = new SpeechSynthesisUtterance(text);
    if (opts?.language) msg.lang = opts.language;
    window.speechSynthesis?.speak(msg);
  } catch {
    /* no-op */
  }
}

// simple rotating layered sphere used when layoutMode === "symbolic"
function LayeredContainerSphere({
  glyphs,
  radius = 2.2,
  rotationSpeed = 0.003,
}: {
  glyphs: { symbol: string; layer: number }[];
  radius?: number;
  rotationSpeed?: number;
}) {
  // loosen type to dodge three/@types-three mismatch
  const groupRef = useRef<any>(null);

  // lightweight manual RAF so we don't pull in useFrame here
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      if (groupRef.current) {
        groupRef.current.rotation.y += rotationSpeed;
      }
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [rotationSpeed]);

  return (
    <group ref={groupRef as any}>
      {glyphs.map((g, i) => {
        const layer = Math.max(0, g.layer ?? 0);
        const r = radius + layer * 0.35;
        const angle = (i / Math.max(1, glyphs.length)) * Math.PI * 2;
        const pos: [number, number, number] = [
          r * Math.cos(angle),
          (layer - 1) * 0.25,
          r * Math.sin(angle),
        ];
        return (
          <mesh key={`layer-glyph-${i}`} position={pos}>
            <sphereGeometry args={[0.06, 12, 12]} />
            <meshStandardMaterial
              color="#00ffff"
              emissive="#00ffff"
              emissiveIntensity={0.8}
            />
            <Html distanceFactor={12}>
              <div className="text-xs text-cyan-300">{g.symbol}</div>
            </Html>
          </mesh>
        );
      })}
    </group>
  );
}

// minimal line helper (avoids drei <Line> typings)
// ⚠️ R3F v8+ expects BufferAttribute via `args: [array, itemSize]`
function SimpleLine({
  from,
  to,
  color = "#aa00ff",
  opacity = 0.7,
  linewidth = 1,
}: {
  from: [number, number, number];
  to: [number, number, number];
  color?: string;
  opacity?: number;
  linewidth?: number;
}) {
  const positions = new Float32Array([...from, ...to]);
  return (
    <line>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial color={color} transparent opacity={opacity} linewidth={linewidth} />
    </line>
  );
}

/* ----------------------------- Types ---------------------------------- */

type GlyphPoint = {
  glyph_id: string;
  symbol: string;
  position: { x: number; y: number; z: number; t: string };
  light_intensity: number;
  trigger_state: string;
  narration?: { text_to_speak: string; voice?: string; language?: string };
  agent_id?: string;
};

type GHXPacket = {
  light_field: GlyphPoint[];
  rendered_at: string;
  projection_id: string;
};

type EntangledLink = {
  source: GlyphPoint;
  target: GlyphPoint;
  confidence?: number; // used for ghost links
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
  const { isRecording, startRecording, stopRecording, downloadRecording, downloadUrl } =
    useCanvasRecorder();
  const [predictionForks, setPredictionForks] = useState<any[]>([]);

  // ✅ NEW: entanglement links and captions
  const [entangledLinks, setEntangledLinks] = useState<EntangledLink[]>([]);
  const [currentCaption, setCurrentCaption] = useState<string>("");

  const glyphRefs = useRef<{ [id: string]: THREE.Mesh }>({});
  const wsUrl = `/ws/ghx/${containerId}`;
  const socket = useWebSocket(wsUrl) as any; // be permissive about hook shape
  const sendJsonMessage: ((data: any) => void) | undefined = socket?.sendJsonMessage;
  const lastJsonMessage: any = socket?.lastJsonMessage;

  const activeGlyphs = useAvatarGlyphs(containerId);
  const coreProjection = useCodexCoreProjection(containerId);
  const combinedProjection = showCodexCore ? coreProjection : projection;

  // ✅ Safely coerce light_field into an array for HUD / slider
  const lightField: GlyphPoint[] = Array.isArray(
    (combinedProjection as any)?.light_field
  )
    ? ((combinedProjection as any).light_field as GlyphPoint[])
    : [];

  // ✅ Normalized projection object for GHXReplaySlider
  const ghxProjection: GHXProjection | null = combinedProjection
    ? {
        projection_id: (combinedProjection as any).projection_id,
        rendered_at: (combinedProjection as any).rendered_at,
        light_field: lightField,
      }
    : null;

  useEffect(() => {
    preloadVoices();
  }, []);

  /** ------------------------------------------------------------------
   *  Socket event handling (single effect – no nesting)
   *  ------------------------------------------------------------------ */
  useEffect(() => {
    if (!lastJsonMessage) return;

    const evt = (lastJsonMessage as any).event || (lastJsonMessage as any).type;

    // GHX projection pushed
    if (evt === "ghx_projection") {
      setProjection((lastJsonMessage as any).payload as GHXPacket);
      setTrailHistory([]);
      setEntangledLinks([]);
      setCurrentCaption("");
      return;
    }

    // node triggered → momentary highlight
    if (evt === "glyph_triggered") {
      const updated = (lastJsonMessage as any).activation as { glyph_id: string };
      const mesh = glyphRefs.current[updated.glyph_id];
      if (mesh) {
        const mat = mesh.material as THREE.MeshStandardMaterial;
        if (mat?.color) mat.color.set("#ff00ff");
      }
      return;
    }

    // replay frames include glyph list, entangled links, and an optional caption
    if (evt === "glyph_replay_frame") {
      type GlyphBrief = { symbol?: string; glyph?: string };
      type LinkBrief  = { source: string; target: string };
      type ReplayFrame = {
        glyphs?: GlyphBrief[];
        entangled_links?: LinkBrief[];
        caption?: string;
      };

      const { glyphs = [], entangled_links = [], caption = "" }: ReplayFrame =
        (lastJsonMessage as ReplayFrame);

      // map entangled links to points in current projection
      if ((entangled_links?.length ?? 0) > 0 && combinedProjection?.light_field) {
        const mapped: EntangledLink[] = entangled_links
          .map((link: LinkBrief) => {
            const source = combinedProjection.light_field!.find(
              (g: GlyphPoint) => g.glyph_id === link.source
            );
            const target = combinedProjection.light_field!.find(
              (g: GlyphPoint) => g.glyph_id === link.target
            );
            return source && target ? ({ source, target } as EntangledLink) : null;
          })
          .filter((v: EntangledLink | null): v is EntangledLink => !!v);
        setEntangledLinks(mapped);
      } else {
        setEntangledLinks([]);
      }

      // caption fallbacks
      if (caption) {
        setCurrentCaption(caption);
      } else if (glyphs.length > 0) {
        const symbols = glyphs
          .map((g: GlyphBrief) => g.symbol ?? g.glyph ?? "?")
          .join(", ");
        setCurrentCaption(`Glyphs: ${symbols}`);
      } else {
        setCurrentCaption("");
      }
      return;
    }

    // predictive forks → show dashed ghost links + caption
    if (evt === "predictive_forks_response") {
      type PredictionFork = {
        id: string;
        input_glyph: string;
        predicted_glyph: string;
        confidence: number;
        agent_id?: string;
      };

      const forks: PredictionFork[] = ((lastJsonMessage as any).predictions || []) as PredictionFork[];

      if (combinedProjection?.light_field) {
        const ghostLinks: EntangledLink[] = forks
          .map((p: PredictionFork): EntangledLink | null => {
            const source = combinedProjection.light_field!.find(
              (g: GlyphPoint) => g.symbol === p.input_glyph
            );
            if (!source) return null;

            const ghost: GlyphPoint = {
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
              agent_id: p.agent_id || "remote",
            };
            return { source, target: ghost, confidence: p.confidence };
          })
          .filter((v: EntangledLink | null): v is EntangledLink => !!v);

        setEntangledLinks((prev) => [...prev, ...ghostLinks]);
      }

      setCurrentCaption(
        `🔮 Predicted forks: ${forks
          .map((f) => `${f.predicted_glyph} (${(f.confidence * 100).toFixed(0)}%)`)
          .join(", ")}`
      );
      setPredictionForks(forks);
    }
  }, [lastJsonMessage, combinedProjection]);

  /* ------------------------------------------------------------------ */

  useEffect(() => {
    if (!focusedGlyph) return;
    const n = focusedGlyph.narration;
    if (n?.text_to_speak) {
      playGlyphNarration(n.text_to_speak, { voice: n.voice, language: n.language });
    } else {
      playGlyphNarration(focusedGlyph.symbol);
    }
  }, [focusedGlyph]);

  const handleGlyphClick = (glyphId: string, symbol: string) => {
    sendJsonMessage?.({ event: "trigger_glyph", glyph_id: glyphId });

    const g = combinedProjection?.light_field?.find(
      (gp: GlyphPoint) => gp.glyph_id === glyphId
    );
    if (g?.narration?.text_to_speak) {
      playGlyphNarration(g.narration.text_to_speak, {
        voice: g.narration.voice,
        language: g.narration.language,
      });
    } else {
      playGlyphNarration(`Symbol ${symbol}`);
    }
    if (g) setFocusedGlyph(g);
  };

  const handleExport = () => {
    if (combinedProjection)
      exportGHXLocal(combinedProjection, `projection-${combinedProjection.projection_id}`);
  };

  const handleFrameSelect = (i: number) => {
    const g = combinedProjection?.light_field?.[i] as GlyphPoint | undefined;
    if (!g) return;

    if (g.narration?.text_to_speak) {
      playGlyphNarration(g.narration.text_to_speak, {
        voice: g.narration.voice,
        language: g.narration.language,
      });
    } else {
      playGlyphNarration(g.symbol);
    }
    setTrailHistory((prev) => [...prev, g]);
    setFocusedGlyph(g);

    const entLinks = entangledLinks.filter(
      (link) => link.source.glyph_id === g.glyph_id || link.target.glyph_id === g.glyph_id
    );
    setCurrentCaption(
      entLinks.length
        ? `↔ Entangled: ${entLinks.map((l) => `${l.source.symbol} ↔ ${l.target.symbol}`).join(", ")}`
        : `Glyph: ${g.symbol}`
    );
  };

  const layeredGlyphs =
    (combinedProjection?.light_field ?? []).map((g: GlyphPoint, idx: number) => ({
      symbol: g.symbol,
      layer: idx % 3,
    }));

  const glyphPositionMap: { [symbol: string]: THREE.Vector3 } = {};
  (combinedProjection?.light_field ?? []).forEach((g: GlyphPoint) => {
    glyphPositionMap[g.symbol] = new THREE.Vector3(g.position.x, g.position.y, g.position.z);
  });

  // AvatarThoughtProjection expects ThoughtGlyph[] with an `id` field; adapt quickly.
  const thoughtGlyphs = (activeGlyphs ?? []).map((g: any) => ({
    id: g.id ?? g.glyph_id ?? g.symbol ?? String(Math.random()),
    symbol: g.symbol ?? g.glyph ?? "?",
  }));

  // If you still want a local avatarRef for other effects
  const avatarRef = useRef<THREE.Object3D | null>(null);

  return (
    <div className="relative w-full h-[80vh] flex flex-col gap-2">
      <Canvas ref={canvasRef} camera={{ position: [0, 0, 3.5], fov: 45 }}>
        <ambientLight intensity={0.7} />
        <pointLight position={[5, 5, 5]} />
        <OrbitControls />

        {layoutMode === "symbolic" && combinedProjection ? (
          <LayeredContainerSphere glyphs={layeredGlyphs} radius={2.2} rotationSpeed={0.003} />
        ) : (
          <>
            {trailHistory.map((glyph: GlyphPoint, idx: number) => (
              <mesh
                key={`${glyph.glyph_id}-trail-${idx}`}
                position={[glyph.position.x, glyph.position.y, glyph.position.z]}
              >
                <sphereGeometry args={[0.4, 16, 16]} />
                <meshStandardMaterial color="#ffffff" transparent opacity={0.1} />
              </mesh>
            ))}

            {(combinedProjection?.light_field ?? []).map((glyph: GlyphPoint) => (
              <AnimatedGlyphNode
                key={glyph.glyph_id}
                glyph={glyph}
                layoutMode={layoutMode}
                onClick={handleGlyphClick}
                onHover={() => playGlyphNarration(glyph.symbol)}
                ref={(ref: THREE.Mesh | null) => {
                  if (ref) glyphRefs.current[glyph.glyph_id] = ref;
                }}
              />
            ))}

            {/* entangled glyph paths */}
            {entangledLinks.map((link: EntangledLink, idx: number) => (
              <SimpleLine
                key={`ent-link-${idx}`}
                from={[link.source.position.x, link.source.position.y, link.source.position.z]}
                to={[link.target.position.x, link.target.position.y, link.target.position.z]}
                color="#aa00ff"
                linewidth={2}
                opacity={0.7}
              />
            ))}
          </>
        )}

      {/* Avatar + memory overlays (both can use avatarRef; cast if component types are stricter) */}
      {(AvatarThoughtProjection as any)({
        thoughts: thoughtGlyphs,
        orbitRadius: 2.8,
        avatarPosition: [0, 0, 0],
        avatarRef: avatarRef,
      })}

      <MemoryHaloRing
        glyphs={[
          { symbol: "🧠", weight: 1.0 },
          { symbol: "↔", weight: 0.7 },
          { symbol: "⬁", weight: 1.2 },
        ]}
        avatarRef={avatarRef}
      />

      <MemoryBridgeBeams glyphPositions={glyphPositionMap} containerId={containerId} />
    </Canvas>

    {/* HUD + overlays live in the same root container */}
    <HologramHUD
      projectionId={combinedProjection?.projection_id}
      renderedAt={combinedProjection?.rendered_at}
      totalGlyphs={lightField.length}
      triggeredGlyphs={
        lightField.filter((g: GlyphPoint) => g.trigger_state !== "idle").length
      }
      onReplayToggle={(v) => setReplayMode(v)}
      onTraceOverlayToggle={(v) => setShowTrace(v)}
      onExport={handleExport}
      onLayoutToggle={() =>
        setLayoutMode((m) => (m === "symbolic" ? "raw" : "symbolic"))
      }
      renderedGlyphs={lightField}
      setCurrentGlyph={setFocusedGlyph}
      currentCaption={currentCaption}
    />

    {/* 🎥 Recording Controls */}
    <div className="absolute top-4 left-4 flex gap-2 z-50">
      <button
        onClick={() =>
          isRecording
            ? stopRecording()
            : canvasRef.current && startRecording(canvasRef.current)
        }
        className={`px-3 py-1 text-xs rounded shadow ${
          isRecording ? "bg-red-500 hover:bg-red-600" : "bg-green-500 hover:bg-green-600"
        }`}
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
      <div className="absolute bottom-36 left-1/2 -translate-x-1/2 flex gap-4 bg-black/70 px-4 py-2 rounded-lg shadow-lg z-50">
        <button
          onClick={() => {
            predictionForks.forEach((f: { id: string }) =>
              sendJsonMessage?.({ event: "prediction_accept", glyph_id: f.id })
            );
            setPredictionForks([]);
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

    {/* Caption bubble */}
    {currentCaption && (
      <div className="absolute bottom-24 left-1/2 -translate-x-1/2 bg-black/70 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
        {currentCaption}
      </div>
    )}

    {/* Replay slider */}
    <GHXReplaySlider
      projection={ghxProjection}
      onFrameSelect={handleFrameSelect}
      onPlayToggle={(v) => setReplayMode(v)}
    />

    <SoulLawHUD />
  </div>
);
}
/* ------------------------------------------------------------------ */
/* AnimatedGlyphNode                                                   */
/* ------------------------------------------------------------------ */

type AnimatedGlyphNodeProps = {
  glyph: GlyphPoint;
  layoutMode: "symbolic" | "raw";
  onClick: (glyphId: string, symbol: string) => void;
  onHover?: () => void;
};


type GHXProjection = {
  projection_id?: string;
  rendered_at?: string | number;
  light_field: GlyphPoint[];
};

const AnimatedGlyphNode = forwardRef<any, AnimatedGlyphNodeProps>((props, fwdRef) => {
  const { glyph, layoutMode, onClick, onHover } = props;
  const meshRef = useRef<any>(null);
  const { camera } = useThree();
  const baseColor = getSymbolColor(glyph.symbol);
  const frequency = getPulseFrequency(glyph.symbol);
  const mutated = isMutatedGlyph(glyph.symbol);

  const getLayoutPosition = (): [number, number, number] => {
    if (layoutMode === "symbolic") {
      return [glyph.position.x, glyph.position.y, glyph.position.z];
    }
    // simple deterministic scatter for "raw"
    const base = glyph.symbol.codePointAt(0) ?? 0;
    return [
      (base % 10) * 4 - 20,
      (Math.floor(base / 10) % 10) * 3 - 10,
      (Math.floor(base / 100) % 10) * 3 - 5,
    ];
  };

  // bridge local ref -> forwarded ref, all as `any` to dodge @types/three mismatch
  const assignRef = (node: any) => {
    meshRef.current = node;
    if (typeof fwdRef === "function") {
      fwdRef(node);
    } else if (fwdRef && typeof fwdRef === "object") {
      (fwdRef as React.MutableRefObject<any>).current = node;
    }
  };

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const pulse = 0.5 + 0.5 * Math.sin(clock.elapsedTime * frequency);

    const dirToGlyph = new THREE.Vector3()
      .subVectors(meshRef.current.position, camera.position)
      .normalize();
    const gazeBoost = dirToGlyph.dot(camera.getWorldDirection(new THREE.Vector3()));
    const focusFactor = Math.max(0, gazeBoost);

    const mat = meshRef.current.material as any;
    const intensity = glyph.light_intensity * (1 + pulse + 0.8 * focusFactor);
    mat.emissiveIntensity = mutated ? intensity * 2.2 : intensity;
  });

  return (
    <mesh
      position={getLayoutPosition()}
      ref={assignRef as any}
      onClick={() => onClick(glyph.glyph_id, glyph.symbol)}
      onPointerOver={() => onHover?.()}
    >
      <sphereGeometry args={[0.7, 32, 32]} />
      <meshStandardMaterial
        color={mutated ? "#ff4444" : baseColor}
        emissive={mutated ? "#ff4444" : baseColor}
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
/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */

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
  const base = symbol.codePointAt(0) ?? 42;
  return 0.5 + (base % 5) * 0.2;
}