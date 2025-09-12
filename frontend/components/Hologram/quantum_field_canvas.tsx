// File: frontend/components/Hologram/quantum_field_canvas.tsx

import React, { useRef, useEffect, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { QWaveBeam, BeamProps } from "@/components/QuantumField/beam_renderer";
import TraceCollapseRenderer from "@/components/QuantumField/Replay/trace_collapse_renderer";
import { snapToEntangledMemoryLayout } from "@/lib/layout";
import { useQfcSocket } from "@/hooks/useQfcSocket";
import HoverAgentLogicView from "@/components/QuantumField/Memory/hover_agent_logic_view";
import { QWavePreviewPanel } from "@/components/QuantumField/QWavePreviewPanel";
import { EntropyNode } from "@/components/QuantumField/styling/EntropyNode";
import HighlightedOperator from "@/components/QuantumField/highlighted_symbolic_operators";
import PredictedLayerRenderer from "@/components/QuantumField/PredictedLayerRenderer";
import ClusterZoomRenderer from "@/components/QuantumField/cluster_zoom_renderer";
import EmotionOverlay from "@/components/QuantumField/EmotionOverlay";
import ScrollReplayOverlay from "@/components/QuantumField/ScrollReplayOverlay";
import StrategyOverlay from "@/components/QuantumField/StrategyOverlay";
import ObserverViewport from "@/components/QuantumField/ObserverViewport";
import MemoryScroller from "@/components/QuantumField/MemoryScroller";
import HoverMutationTrace from "@/components/QuantumField/HoverMutationTrace";
import MultiNodeCollapseTrail from "@/components/QuantumField/MultiNodeCollapseTrail";
import BreakthroughDeadendTrail from "@/components/QuantumField/BreakthroughDeadendTrail";
import BeamLogicOverlay from "@/components/QuantumField/BeamLogicOverlay";
import { rerouteBeam } from "./beam_rerouter";
import { useQFCFocus } from "@/hooks/useQFCFocus";
import { GlyphNode } from "@/types/qfc";
import {
  HtmlEmotionPulse,
  MeshEmotionPulse,
} from "@/components/QuantumField/EmotionPulseOverlay";
import HolographicCausalityTrails, {
  CausalityTrailSegment,
} from "@/components/QuantumField/Replay/holographic_causality_trails";
import HoverMemorySummary from "components/Hologram/HoverMemorySummary";

// ------------------ Types ------------------

interface Link {
  source: string;
  target: string;
  type?: "entangled" | "teleport" | "logic";
  tick?: number;
}

interface QuantumFieldCanvasProps {
  nodes: GlyphNode[];
  links: Link[];
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (targetContainerId: string) => void;
}

// ------------------ Main Component ------------------

// Optional — only if you're rendering collapse trail overlays:

interface QuantumFieldCanvasProps {
  nodes: GlyphNode[];
  links: Link[];
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (targetContainerId: string) => void;

  predictedMode?: boolean;
  predictedOverlay?: {
    nodes: GlyphNode[];
    links: Link[];
  };
} => {
  const [showPredictedLayer, setShowPredictedLayer] = useState(false);
  const [predictedMode, setPredictedMode] = useState(false);
  const [predictedOverlay, setPredictedOverlay] = useState(false);
  const [splitScreen, setSplitScreen] = useState(false);
  const [beamData, setBeamData] = useState<any | null>(null);
  const [selectedBeam, setSelectedBeam] = useState<any | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<any>(null); // OrbitControls
  const [selectedBranch, setSelectedBranch] = useState("trail-1");
  const availableBranches = ["trail-1", "trail-2", "trail-3"];
  const [observerPosition, setObserverPosition] = useState<[number, number, number]>([0, 0, 0]);
  const observerDirection: [number, number, number] = [0, 0, -1]; // forward facing direction
  const collapseTrails = [ ... ];
  const breakthroughTrails = [ ... ];
  const deadendTrails = [ ... ];
  const [replayFrames, setReplayFrames] = useState<any[]>([]);
  const [isReplaying, setIsReplaying] = useState(false);
  const [playbackIndex, setPlaybackIndex] = useState(0);


  useEffect(() => {
    fetch("/api/test-mixed-beams")
      .then((res) => res.json())
      .then(setBeamData)
      .catch(console.error);
  }, []);
  // 🎬 Replay playback loop
  useEffect(() => {
    if (!isReplaying) return;

  const interval = setInterval(() => {
    setPlaybackIndex((prev) => {
      if (prev >= replayFrames.length - 1) {
        clearInterval(interval);
        setIsReplaying(false);
        return prev;
      }
      return prev + 1;
    });
  }, 100); // ⏱️ 100ms per frame

    return () => clearInterval(interval);
  }, [isReplaying, replayFrames]);

  const handleRetryFromBranch = async () => {
    const res = await fetch("/api/mutate_from_branch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trailId: selectedBranch }),
    });

    const result = await res.json();
    broadcast_qfc_update(result); // 🔁 Push new glyphs/beams into QFC live
  };
  const specialOps = new Set(["⧖", "↔", "⬁", "🧬", "🪞"]);
  const [focusedNode, setFocusedNode] = useState<string | null>(null);
  const handleDroppedScroll = async (glyph: string, scroll: string) => {
    console.log("📥 Dropped Scroll:", glyph, scroll);

    try {
      const response = await fetch("/api/inject_scroll", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ glyph, scroll }),
      });

      const result = await response.json();

      // ⬆️ Inject response into QFC field live
      if (result && result.glyphs) {
        broadcast_qfc_update(result); // 🚀 Inject into QFC
        setOrbitTargetToGlyph(glyph); // 🎯 Optional: center to glyph

        // 🎥 Capture current frame after successful scroll injection
        const frame = {
          timestamp: Date.now(),
          glyphs: props.nodes,
          links: props.links,
          observer: observerPosition,
          branch: selectedBranch,
          scrolls: [{ glyph, scroll }],
        };
        setReplayFrames((prev) => [...prev, frame]);
      } else {
        console.warn("⚠️ No glyphs returned from scroll injection");
      }
    } catch (err) {
      console.error("❌ Scroll injection failed:", err);
    }
  };

  return (
    <div
        className="relative w-full h-full"
        onDrop={(e) => {
          e.preventDefault();
          const data = e.dataTransfer.getData("application/glyph-scroll");
          if (data) {
            const { glyph, scroll } = JSON.parse(data);
            handleDroppedScroll(glyph, scroll);
          }
        }}
        onDragOver={(e) => e.preventDefault()}
      >
      {/* 🎛️ Controls Panel */}
      <div className="absolute top-4 left-4 z-50 space-y-2">
        <Button
          className="text-xs px-3 py-1 h-8 bg-blue-900 hover:bg-blue-800"
          onClick={() => setShowPredictedLayer(!showPredictedLayer)}
        >
          🔮 {showPredictedLayer ? "Hide" : "Show"} Predicted Layer
        </Button>
        <Button
          className="text-xs px-3 py-1 h-8 bg-purple-700 hover:bg-purple-600"
          onClick={() => setSplitScreen(!splitScreen)}
        >
          🧠 {splitScreen ? "Unsplit View" : "Split Reality / Dream"}
        </Button>
        <Button
          className="text-xs px-3 py-1 h-8 bg-slate-700 hover:bg-slate-600"
          onClick={() => setPredictedMode(!predictedMode)}
        >
          🌓 {predictedMode ? "Normal" : "Fade Real Nodes"}
        </Button>
        <Button
          className="text-xs px-3 py-1 h-8 bg-sky-900 hover:bg-sky-800"
          onClick={() => setPredictedOverlay(!predictedOverlay)}
        >
          🌐 {predictedOverlay ? "Hide Overlay" : "Show Overlay"}
        </Button>
      </div>

      {/* Canvas and core rendering logic goes here */}
      {/* ... you can continue refactoring the rest of the canvas, node rendering, beams, overlays, etc. */}
    </div>
  );
};

export default QuantumFieldCanvas;

// 🎨 Get link color by type
const getLinkColor = (type?: string): string => {
  switch (type) {
    case "entangled":
      return "#ff66ff";
    case "teleport":
      return "#00ffff";
    case "logic":
      return "#66ff66";
    default:
      return "#8888ff";
  }
};

// 🌐 Glyph Node Component
const Node = ({
  node,
  onTeleport,
}: {
  node: GlyphNode;
  onTeleport?: (id: string) => void;
}) => {
  const ref = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const pulseRef = useRef(0);

  useFrame(() => {
    if (ref.current) {
      if (node.predicted) {
        pulseRef.current += 0.05;
        const scale = 1 + 0.1 * Math.sin(pulseRef.current);
        ref.current.scale.set(scale, scale, scale);
      }
      if (hovered) {
        ref.current.rotation.y += 0.01;
      }
    }
  });

  return (
    <mesh
      ref={ref}
      position={node.position}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
      onClick={() => node.containerId && onTeleport?.(node.containerId)}
    >
      <sphereGeometry args={[0.3, 32, 32]} />
      <meshStandardMaterial
        color={
          node.locked
            ? "#ff3333"
            : node.color || (node.predicted ? "#00ffff" : "#ffffff")
        }
        emissive={
          node.locked
            ? "#ff3333"
            : node.predicted
            ? "#00ffff"
            : "#000000"
        }
        emissiveIntensity={node.locked ? 2.0 : node.predicted ? 1.5 : 0}
      />

      {/* 🟢 Emotion Pulse Overlay */}
      {node.emotion && (
        <>
          <MeshEmotionPulse node={node} />
          <HtmlEmotionPulse node={node} />
        </>
      )}

      {/* 🏷️ Label UI */}
      <Html>
        <Card className="p-2 rounded-xl shadow-lg text-xs text-center bg-white/80 backdrop-blur">
          ...
        </Card>
      </Html>

      {/* 🔒 Floating lock */}
      {node.locked && (
        <Html
          position={[
            node.position[0],
            node.position[1] + 1.5,
            node.position[2],
          ]}
        >
          <div className="text-2xl text-red-500 font-bold drop-shadow">🔒</div>
        </Html>
      )}
    </mesh>
  );
};

// 🔗 Visual Link Line Component
const LinkLine: React.FC<{
  source: GlyphNode;
  target: GlyphNode;
  type?: string;
  isDream?: boolean;
}> = ({ source, target, type, isDream = false }) => {
  const points = [
    new THREE.Vector3(...source.position),
    new THREE.Vector3(...target.position),
  ];
  const geometry = new THREE.BufferGeometry().setFromPoints(points);

  return (
    <line>
      <primitive object={geometry} attach="geometry" />
      <lineBasicMaterial
        attach="material"
        color={isDream ? "#d946ef" : "#888"}
        linewidth={1}
        transparent
        opacity={isDream ? 0.4 : 1}
      />
    </line>
  );
};

  // 💠 ReplayPulse Overlay for Entangled Nodes
  const ReplayPulse: React.FC<{ position: [number, number, number] }> = ({ position }) => {
    const pulseRef = useRef<THREE.Mesh>(null);

    useFrame(({ clock }) => {
      const scale = 1 + Math.sin(clock.getElapsedTime() * 4) * 0.2;
      if (pulseRef.current) {
        pulseRef.current.scale.set(scale, scale, scale);
      }
    });

    return (
      <mesh position={position} ref={pulseRef}>
        <ringGeometry args={[0.5, 0.6, 32]} />
        <meshBasicMaterial color="#00ffcc" transparent opacity={0.6} />
      </mesh>
    );
  };
  const getNodeById = (id: string) => nodes.find((n) => n.id === id);

  const setOrbitTargetToGlyph = (glyphId: string) => {
    const node = nodes.find((n) => n.id === glyphId);
    if (!node || !cameraRef.current || !controlsRef.current) return;

    const target = new THREE.Vector3(...node.position);

    // Smooth camera animation
    new TWEEN.Tween(controlsRef.current.target)
      .to(target, 1000)
      .easing(TWEEN.Easing.Quadratic.Out)
      .onUpdate(() => {
        controlsRef.current.update();
      })
      .start();

    // Optionally move the camera itself
    new TWEEN.Tween(cameraRef.current.position)
      .to(
        {
          x: target.x + 5,
          y: target.y + 5,
          z: target.z + 5,
        },
        1000
      )
      .easing(TWEEN.Easing.Quadratic.Out)
      .start();
  };

  // 🔁 Load QWave Beams
  useEffect(() => {
    fetch("/api/test-mixed-beams")
      .then((res) => res.json())
      .then(setBeamData)
      .catch(console.error);
  }, []);

  // 🧪 Static Test Collapse Trails
  const collapseTrails = [
    {
      id: "trail-1",
      path: [
        [0, 0, 0],
        [1, 2, 0],
        [2, 4, 0],
      ],
      color: "#ffaa00",
    },
  ];

  const breakthroughTrails = [
    {
      points: [
        [0, 0, 0],
        [1.5, 0.5, 0],
        [2.2, 1.2, 0],
      ],
      type: "breakthrough",
    },
  ];

  const deadendTrails = [
    {
      points: [
        [1, -1, 0],
        [1.5, -1.5, 0],
        [2.0, -2.0, 0],
      ],
      type: "deadend",
    },
  ];

  // 🌌 Q11c: Merge Predicted (Dream) Nodes + Links into Main Canvas
  const predictedNodes: GlyphNode[] = []; // hook up to qfcData?.predictedNodes
  const predictedLinks: any[] = [];

  const mergedNodes = [
    ...nodes.filter((node) => {
      const matchTick = tickFilter === undefined || node.tick === tickFilter;
      const matchCollapse =
        showCollapsed || node.collapse_state !== "collapsed";
      return matchTick && matchCollapse;
    }),
    ...predictedNodes
      .filter((pn) => !nodes.some((n) => n.id === pn.id))
      .map((pn) => ({
        ...pn,
        isDream: true,
      })),
  ];

  const mergedLinks = [
    ...links.filter((link) => {
      const matchTick = tickFilter === undefined || link.tick === tickFilter;
      return matchTick;
    }),
    ...predictedLinks
      .filter(
        (pl) =>
          !links.some(
            (l) => l.source === pl.source && l.target === pl.target
          )
      )
      .map((pl) => ({
        ...pl,
        isDream: true,
      })),
  ];

  // ✅ QWave Beam Rendering with Logic Overlays
  const qwaveBeams = (beamData || [])
    .filter((beam) => beam.source && beam.target)
    .map(
      ({
        source,
        target,
        qwave,
        id,
        predicted,
        collapse_state,
        sqiScore,
      }: BeamProps) => {
        const hasLogicPacket = qwave?.logic_packet;
        const midPosition: [number, number, number] = [
          (source[0] + target[0]) / 2,
          (source[1] + target[1]) / 2,
          (source[2] + target[2]) / 2,
        ];

        return (
          <React.Fragment key={`beam-${id}`}>
            <group
              onClick={() =>
                setSelectedBeam({
                  source,
                  target,
                  qwave,
                  id,
                  predicted,
                  collapse_state,
                  sqiScore,
                })
              }
            >
              <QWaveBeam
                source={source}
                target={target}
                prediction={predicted}
                collapseState={collapse_state}
                sqiScore={sqiScore || 0}
                show={true}
              />
            </group>

            {hasLogicPacket && (
              <BeamLogicOverlay
                position={midPosition}
                packet={qwave.logic_packet}
                visible={true}
              />
            )}
          </React.Fragment>
        );
      }
  );
  const setOrbitTargetToGlyph = (glyph: string) => {
    const node = mergedNodes.find((n) => n.glyph === glyph);
    if (node) {
      console.log("🎯 Centering to glyph node:", glyph, node.position);
      setObserverPosition(node.position);
    } else {
      console.warn("❌ Glyph not found in nodes:", glyph);
    }
  };
  const renderReplayFrame = (frame: any) => {
    return (
      <>
        {frame.glyphs.map((node: any, idx: number) => (
          <Node
            key={idx}
            node={node}
            onTeleport={onTeleport}
            highlight={true}
            className="ring-2 ring-yellow-400 scale-105"
          />
        ))}
        {frame.links.map((link: any, idx: number) => (
          <LinkComponent key={idx} link={link} />
        ))}
      </>
    );
  };
  return (
    <>
      {/* 🧠 Render QWave Beams */}
      {qwaveBeams}
      {/* 🌀 Replay Beam Trails */}
      {isReplaying &&
        replayFrames[playbackIndex]?.links?.map((link: any, idx: number) => {
          if (!link.trail) return null;
          return (
            <ReplayBeamTrail
              key={`replay-trail-${idx}`}
              trail={link.trail}
              type={link.collapseState || "collapsed"}
              tick={link.tick}
            />
          );
        })}

      {/* 🔘 HUD Controls */}
      <div className="absolute top-4 left-4 z-50 space-y-2">
        <Button
          className="text-xs px-3 py-1 h-8 bg-blue-900 hover:bg-blue-800"
          onClick={() => setShowPredictedLayer(!showPredictedLayer)}
        >
          🔮 {showPredictedLayer ? "Hide" : "Show"} Predicted Layer
        </Button>
        <Button
          className="text-xs px-3 py-1 h-8 bg-purple-700 hover:bg-purple-600"
          onClick={() => setSplitScreen(!splitScreen)}
        >
          🧠 {splitScreen ? "Unsplit View" : "Split Reality / Dream"}
        </Button>
        <Button
          className="text-xs px-3 py-1 h-8 bg-green-900 hover:bg-green-800"
          onClick={() => setIsReplaying(!isReplaying)}
        >
          {isReplaying ? "⏸ Pause Replay" : "▶️ Start Replay"}
        </Button>
        <Button
          className="text-xs px-3 py-1 h-8 bg-slate-700 hover:bg-slate-600"
          onClick={() => setPredictedMode(!predictedMode)}
        >
          🌓 {predictedMode ? "Normal" : "Fade Real Nodes"}
        </Button>
        <Button
          className="text-xs px-3 py-1 h-8 bg-sky-900 hover:bg-sky-800"
          onClick={() => setPredictedOverlay(!predictedOverlay)}
        >
          🌐 {predictedOverlay ? "Hide Overlay" : "Show Overlay"}
        </Button>
      </div>
      {isReplaying && replayFrames[playbackIndex] && (
        <div className="absolute top-4 right-4 text-xs bg-black/70 text-white p-2 rounded z-50">
          ⏪ Replaying Frame #{playbackIndex}
        </div>
      )}
      {/* 🔁 Branch Selection + Retry */}
      <div className="absolute top-4 right-4 z-50 w-64">
        <ReplayBranchSelector
          availableBranches={availableBranches}
          selectedBranch={selectedBranch}
          onSelect={setSelectedBranch}
          onRetry={handleRetryFromBranch}
        />
      </div>
      {/* 🧠 Canvas Views */}
      <div className="h-full w-full relative flex">
        {splitScreen ? (
          // 🟢 Split View: Real vs Dream
          <div className="w-1/2 h-full border-r border-slate-700">
            <Canvas
              camera={{ position: [0, 0, 10], fov: 50 }}
              onCreated={({ camera }) => {
                cameraRef.current = camera;
              }}
            >
              <ambientLight intensity={0.7} />
              <pointLight position={[10, 10, 10]} />
              <OrbitControls
                ref={controlsRef}
                enableZoom
                enablePan
                enableRotate
                target={new THREE.Vector3(...observerPosition)}
              />

              {/* 🌐 Symbolic QWave Beams */}
              {beamData.map((beam, idx) => (
                <group key={idx} onClick={() => setSelectedBeam(beam)}>
                  <QWaveBeam {...beam} />
                </group>
              ))}

              {/* 🌈 Nodes (Real + Dream) */}
              {isReplaying && replayFrames[playbackIndex] && (
                <>
                  {renderReplayFrame(replayFrames[playbackIndex])}
                </>
              )}
              {mergedNodes.map((node) => {
                const inView = isInObserverView(node.position, observerPosition, observerDirection);

                return (
                  <React.Fragment key={node.id}>
                    {(node.source === "dream" || node.isDream) && (
                      <mesh position={node.position}>
                        <ringGeometry args={[0.6, 0.75, 32]} />
                        <meshBasicMaterial
                          color="#d946ef"
                          transparent
                          opacity={0.75}
                        />
                      </mesh>
                    )}

                    <Node
                      node={node}
                      onTeleport={onTeleport}
                      highlight={inView}
                      className={node.glyph === focusedNode ? "ring-2 ring-green-400 scale-110" : ""}
                    />

                  {/* ✨ Entropy Overlay */}
                  {typeof node.entropy === "number" && (
                    <EntropyNode
                      position={node.position}
                      entropy={node.entropy}
                      nodeId={node.id}
                    />
                  )}
                  {/* 🧠 Hover Memory Summary */}
                  {node.memoryTrace && (
                    <HoverMemorySummary
                      position={[
                        node.position[0],
                        node.position[1] + 1.5,
                        node.position[2],
                      ]}
                      summary={node.memoryTrace.summary}
                      containerId={node.memoryTrace.containerId}
                      agentId={node.memoryTrace.agentId}
                    />
                  )}
                </React.Fragment>
              ))}

              {/* 🔗 Merged Links (Real + Dream) */}
              {mergedLinks.map((link, i) => {
                const source = getNodeById(link.source);
                const target = getNodeById(link.target);
                if (!source || !target) return null;
                return (
                  <LinkLine
                    key={`link-${i}`}
                    source={source}
                    target={target}
                    type={link.type}
                  />
                );
              })}

              {/* 🔮 Predicted Layer Overlay */}
              {showPredictedLayer && (
                <PredictedLayerRenderer
                  nodes={qfcData?.predictedNodes || []}
                  links={qfcData?.predictedLinks || []}
                />
              )}

              {/* 💫 Optional HUD Layers */}
              <EmotionOverlay visible={emotionOverlayEnabled} />
              <ScrollReplayOverlay visible={scrollReplayActive} />
              <StrategyOverlay visible={strategyOverlayEnabled} />
              <ObserverViewport enabled={observerMode} />
              <MemoryScroller active={memoryScrollerActive} />
            </Canvas>
          </div>
        ) : (
          // 🔁 Default Unified View
          <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
            <ambientLight intensity={0.7} />
            <pointLight position={[10, 10, 10]} />
            <OrbitControls
              enableZoom
              enablePan
              enableRotate
              target={new THREE.Vector3(...observerPosition)}
            />

            {/* 🔮 Predicted Overlay */}
            {showPredictedLayer && (
              <PredictedLayerRenderer
                nodes={qfcData?.predictedNodes || []}
                links={qfcData?.predictedLinks || []}
                visible={true}
              />
            )}

            {/* 🔗 Links */}
            {mergedLinks.map((link, i) => {
              const source = getNodeById(link.source);
              const target = getNodeById(link.target);
              if (!source || !target) return null;
              return (
                <LinkLine
                  key={`link-${i}`}
                  source={source}
                  target={target}
                  type={link.type}
                />
              );
            })}
          </Canvas>
          </div> {/* end of split-screen real view left half */}

          {/* 💫 Render QWaveBeams between nodes (mergedLinks) */}
          {mergedLinks.map((link, i) => {
            const source = getNodeById(link.source);
            const target = getNodeById(link.target);
            if (!source || !target) return null;

            return (
              <group key={`beam-${i}`} onClick={() => setSelectedBeam(link)}>
                <QWaveBeam
                  source={source.position}
                  target={target.position}
                  prediction={source.predicted || target.predicted}
                  collapseState={source.collapse_state || target.collapse_state}
                  sqiScore={
                    source.goalMatchScore ??
                    source.rewriteSuccessProb ??
                    target.goalMatchScore ??
                    target.rewriteSuccessProb ??
                    0
                  }
                  show={true}
                />
              </group>
            );
          })}

          {/* 🌈 Glyph Nodes from beamData */}
          {beamData?.glyphs?.map((glyph: any) => (
            <React.Fragment key={`beam-glyph-${glyph.id}`}>
              <Node node={glyph} onTeleport={onTeleport} />
              {specialOps.has(glyph.value) && glyph.type === "operator" && (
                <HighlightedOperator value={glyph.value} position={glyph.position} />
              )}
            </React.Fragment>
          ))}

          {/* 🚀 Mixed Beams with rerouted paths */}
          {beamData?.beams?.map((beam: any) => {
            const { id, source, target, predicted, collapse_state, sqiScore } = beam;
            const reroutedPath = rerouteBeam(source, target, focusPoint);

            return (
              <QWaveBeam
                key={`mixed-beam-${id}`}
                path={reroutedPath}
                prediction={predicted}
                collapseState={collapse_state}
                sqiScore={sqiScore || 0}
                show={true}
              />
            );
          })}

          {/* ⚛ Filtered Node Rendering */}
          {filteredNodes.map((node) => (
            <React.Fragment key={node.id}>
              {/* 🧠 Node */}
              <Node node={node} onTeleport={onTeleport} />

              {/* 🔒 SoulLaw Lock */}
              {node.locked && (
                <Html
                  position={[
                    node.position[0],
                    node.position[1] + 1.5,
                    node.position[2],
                  ]}
                >
                  <div className="text-2xl text-red-500 font-bold drop-shadow">
                    🔒
                  </div>
                </Html>
              )}

              {/* 🎨 Entropy Overlay */}
              {typeof node.entropy === "number" && (
                <EntropyNode
                  position={node.position}
                  entropy={node.entropy}
                  nodeId={node.id}
                />
              )}

              {/* 🧠 Memory Trace Hover */}
              {node.memoryTrace && (
                <HoverAgentLogicView
                  position={[
                    node.position[0],
                    node.position[1] + 1.2,
                    node.position[2],
                  ]}
                  logicSummary={node.memoryTrace.summary}
                  containerId={node.memoryTrace.containerId}
                  agentId={node.memoryTrace.agentId}
                />
              )}

              {/* ➕ Spawn Container Button */}
              <Html
                position={[
                  node.position[0] + 0.8,
                  node.position[1] + 1.2,
                  node.position[2],
                ]}
              >
                <button
                  className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded shadow"
                  onClick={async () => {
                    try {
                      const res = await fetch("/api/spawn_container_from_node", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ nodeId: node.id }),
                      });
                      const data = await res.json();
                      if (data.success && data.newContainerId) {
                        alert(`✅ Container spawned: ${data.newContainerId}`);
                      } else {
                        alert("⚠️ Failed to spawn container.");
                      }
                    } catch (err) {
                      alert("🚨 Spawn failed: " + err);
                    }
                  }}
                >
                  ➕ Spawn
                </button>
              </Html>
            </React.Fragment>
          ))}

          {/* 🔍 Zoom Highlights */}
          <ClusterZoomRenderer
            nodes={filteredNodes}
            radius={2.5}
            onZoomed={(ids) => console.log("🔍 Zoomed cluster:", ids)}
          />

          {/* 🧠 Collapse + Causality Trails */}
          <TraceCollapseRenderer trails={collapseTrails} color="#ffaa00" />
          <HoverMutationTrace
            trails={hoverMutationTrails}
            hoveredNodeId={hoveredNode?.id}
          />
          <HolographicCausalityTrails trails={causalitySegments} />
          <BreakthroughDeadendTrail
            segments={[...(breakthroughTrails || []), ...(deadendTrails || [])]}
            visible={true}
          />
          <MultiNodeCollapseTrail segments={multiCollapseTrails} visible={true} />

          {/* 🔬 QWave Preview Panel */}
          {selectedBeam?.id && (
            <QWavePreviewPanel
              selectedBeamId={selectedBeam.id}
              beamMetadata={selectedBeam.qwave}
            />
          )}

  {/* 🌐 Predicted Overlay (Real View) */}
  {predictedOverlay && (
    <PredictedLayerRenderer
      nodes={qfcData?.predictedNodes || []}
      links={qfcData?.predictedLinks || []}
      visible={true}
    />
  )}

  {/* 🔮 Dream QFC Canvas (Right side) */}
  <div className="w-1/2 h-full">
    <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[5, 5, 5]} />
      <OrbitControls
        enableZoom
        enablePan
        enableRotate
        target={new THREE.Vector3(...observerPosition)}
      />

      {/* 🔮 Predicted Layer */}
      <PredictedLayerRenderer
        nodes={qfcData?.predictedNodes || []}
        links={qfcData?.predictedLinks || []}
        visible={true}
      />

      {/* 💫 Dream Visual Layers */}
      <EmotionOverlay visible={emotionOverlayEnabled} />
      <ScrollReplayOverlay visible={scrollReplayActive} />
      <StrategyOverlay visible={strategyOverlayEnabled} />
      <ObserverViewport enabled={observerMode} />
      <MemoryScroller active={memoryScrollerActive} />
    </Canvas>
  </div> {/* End of right-side canvas */}


  {/* 📤 Collapse Timeline Export + Tick Info Panel */}
  <div className="absolute top-4 right-4 text-xs text-white bg-black/70 rounded-md p-2 z-50 space-y-2">
    <div>
      🕓 Tick Filter: <strong>{tickFilter ?? "—"}</strong>
    </div>
    <div>
      📉 Collapsed Nodes:{" "}
      <strong>{nodes.filter((n: any) => n.collapse_state === "collapsed").length}</strong>
    </div>
    <button
      className="w-full mt-1 px-3 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-white"
      onClick={() => {
        const exportData = nodes
          .filter((n: any) => showCollapsed || n.collapse_state !== "collapsed")
          .map((n: any) => ({
            id: n.id,
            label: n.label,
            tick: n.tick,
            state: n.collapse_state,
            entropy: n.entropy,
            goalMatchScore: n.goalMatchScore,
            rewriteSuccessProb: n.rewriteSuccessProb,
          }));

        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `collapse_timeline_tick${tickFilter ?? "all"}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }}
    >
      ⬇️ Export Collapse Timeline
    </button>
  </div> {/* End of right-side export panel */}
      </div> {/* End of right-side export panel */}
    </div> {/* End of full canvas wrapper */}
          </div> // 🧠 End of full layout wrapper
        );
    }; // ✅ Correctly close the QuantumFieldCanvas component

export const QuantumFieldCanvasLoader: React.FC<{
  containerId: string;
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (id: string) => void;
}> = ({ containerId, tickFilter, showCollapsed, onTeleport }) => {
  const [data, setData] = useState<{ nodes: any[]; links: any[] }>({
    nodes: [],
    links: [],
  });

// ✅ Inject scrolls into active field via backend + auto-focus on glyph
  useEffect(() => {
    const handleScrollInjection = async (event: any) => {
      const { glyphId, scrollContent } = event.detail || {};
      console.log("📥 Scroll Inject Event:", glyphId, scrollContent);

      try {
        const response = await fetch("/api/inject_scroll", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ glyph: glyphId, scroll: scrollContent }),
        });

        const result = await response.json();

        if (result && result.glyphs) {
          // 🚀 Inject returned glyph nodes into QFC
          setData((prev) => {
            const updatedNodes = [...prev.nodes, ...result.glyphs];
            // 💡 Animate camera to focus on injected glyph after render
            setTimeout(() => {
              setOrbitTargetToGlyph(glyphId);
            }, 100);
            return {
              ...prev,
              nodes: updatedNodes,
            };
          });

          console.log("✅ Scroll injected and rendered:", result.glyphs);
        } else {
          console.warn("⚠️ No glyphs returned from scroll injection");
        }
      } catch (err) {
        console.error("❌ Scroll injection failed:", err);
      }
    };

    window.addEventListener("scroll_injected", handleScrollInjection);
    return () => {
      window.removeEventListener("scroll_injected", handleScrollInjection);
    };
  }, []);

    window.addEventListener("scroll_injected", handleScrollInjection);
    return () => {
      window.removeEventListener("scroll_injected", handleScrollInjection);
    };
  }, []);

  // 📡 Load initial QFC data
  useEffect(() => {
    fetch(`/api/qfc_view/${containerId}`)
      .then((res) => res.json())
      .then((json) => {
        const rawNodes = json.nodes || [];
        const links = json.links || [];

        const centerId = rawNodes[0]?.id;
        const snappedNodes = snapToEntangledMemoryLayout(rawNodes, containerId);

        const annotatedNodes = snappedNodes.map((node: any) => {
          const glyphTrace = node.glyphTrace ?? node.memory ?? null;

          let goalType: "goal" | "strategy" | "milestone" | null = null;
          const label = node.label?.toLowerCase() ?? "";
          if (label.includes("goal")) goalType = "goal";
          else if (label.includes("strategy")) goalType = "strategy";
          else if (label.includes("milestone")) goalType = "milestone";

          let memoryTrace = null;
          if (Array.isArray(glyphTrace) && glyphTrace.length > 0) {
            const last = glyphTrace[glyphTrace.length - 1];
            memoryTrace = {
              summary: last.summary || last.intent || "Observed symbolic memory",
              containerId: node.containerId || containerId,
              agentId: node.agentId || "aion-agent",
            };
          }

          return {
            ...node,
            goalType,
            memoryTrace,
            containerId: node.containerId || containerId || "kevin_1244.dc.json",
          };
        });

        setData({ nodes: annotatedNodes, links });
      });
  }, [containerId]);

  // 🔄 Live updates from socket
  useQfcSocket(containerId, (payload) => {
    setData((prev) => ({
      nodes: [...prev.nodes, ...(payload.nodes || [])],
      links: [...prev.links, ...(payload.links || [])],
    }));
  });

  return (
    <QuantumFieldCanvas
      {...data}
      tickFilter={tickFilter}
      showCollapsed={showCollapsed}
      onTeleport={(id) => {
        const node = data.nodes.find((n) => n.id === id);
        const targetContainer = node?.containerId;
        if (targetContainer) {
          window.location.href = `/dimension/${targetContainer.replace(".dc.json", "")}`;
        } else {
          alert("⚠️ No container ID found for node: " + id);
        }
      }}
    />
  );
};

// 🔍 Utility to check if a node is within observer's field of view
function isInObserverView(
  nodePosition: [number, number, number],
  observerPosition: [number, number, number],
  direction: [number, number, number],
  fovAngle: number = Math.PI / 3 // 60° default
) {
  const vecToNode = new THREE.Vector3(
    nodePosition[0] - observerPosition[0],
    nodePosition[1] - observerPosition[1],
    nodePosition[2] - observerPosition[2]
  ).normalize();

  const observerDir = new THREE.Vector3(...direction).normalize();
  const angle = observerDir.angleTo(vecToNode);
  return angle <= fovAngle / 2;
}