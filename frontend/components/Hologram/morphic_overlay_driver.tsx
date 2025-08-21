// File: frontend/components/hologram/morphic_overlay_driver.tsx

import React, { useEffect, useMemo } from "react";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import { QGlyphFusionBeam } from "./qglyph_fusion_beam";

type GlyphNode = {
  id: string;
  position: [number, number, number];
  entropy?: number;
  cost?: number;
  type?: "collapse" | "mutate" | "push" | "replay";
  goalScore?: number;
  linkedTo?: string[]; // entangled nodes
  replayedFrom?: string;
};

type MorphicOverlayProps = {
  glyphs: GlyphNode[];
  links?: { source: string; target: string; type?: GlyphNode["type"] }[];
  activeGoal?: string;
  showTraces?: boolean;
  onBeamClick?: (sourceId: string, targetId: string, logicType: string) => void;
};

export const MorphicOverlayDriver: React.FC<MorphicOverlayProps> = ({
  glyphs,
  links = [],
  activeGoal,
  showTraces = true,
  onBeamClick,
}) => {
  const glyphMap = useMemo(() => {
    const map = new Map<string, GlyphNode>();
    glyphs.forEach((g) => map.set(g.id, g));
    return map;
  }, [glyphs]);

  const resolvePosition = (id: string): THREE.Vector3 | null => {
    const node = glyphMap.get(id);
    return node ? new THREE.Vector3(...node.position) : null;
  };

  // ⏯ Replay beams
  const replayBeams = useMemo(() => {
    if (!showTraces) return null;
    return glyphs.map((glyph) => {
      if (!glyph.replayedFrom) return null;
      const source = resolvePosition(glyph.replayedFrom);
      const target = resolvePosition(glyph.id);
      if (!source || !target) return null;

      return (
        <QGlyphFusionBeam
          key={`${glyph.replayedFrom}⧖${glyph.id}`}
          source={source}
          target={target}
          logicType="replay"
          entropy={glyph.entropy}
          cost={glyph.cost}
          pulseSpeed={1.5}
          showLabel={false}
          onClick={() =>
            onBeamClick?.(glyph.replayedFrom!, glyph.id, "replay")
          }
        />
      );
    }).filter(Boolean);
  }, [glyphs, showTraces, onBeamClick]);

  // ↔ Entangled beams
  const entangledBeams = useMemo(() => {
    return glyphs.flatMap((glyph) => {
      if (!glyph.linkedTo) return [];
      return glyph.linkedTo.map((targetId) => {
        const source = resolvePosition(glyph.id);
        const target = resolvePosition(targetId);
        if (!source || !target) return null;

        return (
          <QGlyphFusionBeam
            key={`${glyph.id}↔${targetId}`}
            source={source}
            target={target}
            logicType="mutate"
            entropy={glyph.entropy}
            cost={glyph.cost}
            pulseSpeed={2}
            showLabel={false}
            onClick={() => onBeamClick?.(glyph.id, targetId, "mutate")}
          />
        );
      });
    }).filter(Boolean);
  }, [glyphs, onBeamClick]);

  // ➕ General link beams (e.g., collapse, push)
  const logicBeams = useMemo(() => {
    return links.map(({ source, target, type = "collapse" }) => {
      const sourcePos = resolvePosition(source);
      const targetPos = resolvePosition(target);
      const sourceGlyph = glyphMap.get(source);
      if (!sourcePos || !targetPos || !sourceGlyph) return null;

      return (
        <QGlyphFusionBeam
          key={`${source}→${target}`}
          source={sourcePos}
          target={targetPos}
          logicType={type}
          entropy={sourceGlyph.entropy}
          cost={sourceGlyph.cost}
          pulseSpeed={1.2}
          showLabel={false}
          onClick={() => onBeamClick?.(source, target, type)}
        />
      );
    }).filter(Boolean);
  }, [links, glyphMap, onBeamClick]);

  // 🎯 Goal overlays
  const goalOverlays = useMemo(() => {
    return glyphs.map((glyph) => {
      if (!glyph.goalScore || glyph.goalScore < 0.5) return null;
      return (
        <Html
          key={`goal-${glyph.id}`}
          position={new THREE.Vector3(...glyph.position)}
          distanceFactor={10}
          style={{
            background: "rgba(0, 255, 0, 0.3)",
            color: "#fff",
            padding: "4px 6px",
            borderRadius: "4px",
            fontSize: "0.75rem",
            pointerEvents: "none",
          }}
        >
          🎯 Goal {Math.round(glyph.goalScore * 100)}%
        </Html>
      );
    }).filter(Boolean);
  }, [glyphs]);

  // 🌐 Future symbolic broadcast (stub)
  useEffect(() => {
    // TODO: Hook into GlyphNet WebSocket broadcast
    // broadcastSymbolicOverlayUpdate(glyphs, links);
  }, [glyphs, links]);

  return (
    <>
      {entangledBeams}
      {replayBeams}
      {logicBeams}
      {goalOverlays}
    </>
  );
};