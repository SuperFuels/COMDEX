// File: frontend/components/Hologram/qfcHelpers.ts
import * as THREE from "three";
import * as TWEENNS from "@tweenjs/tween.js";
import React from "react";

/** Local shim to mirror backend "broadcast_qfc_update" semantics. */
export function broadcast_qfc_update(payload: any) {
  try {
    window.dispatchEvent(new CustomEvent("qfc_update", { detail: payload }));
  } catch {
    /* no-op in SSR */
  }
}

/** 🎨 Get link color by type */
export function getLinkColor(type?: string): string {
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
}

/** Move camera/controls to a node (by id). Tween when possible; snap otherwise. */
export function setOrbitTargetToGlyphFactory(opts: {
  nodes: Array<{ id: string | number; position: [number, number, number] }>;
  cameraRef: React.RefObject<THREE.PerspectiveCamera>;
  controlsRef: React.RefObject<any>; // OrbitControls
}) {
  const { nodes, cameraRef, controlsRef } = opts;

  return (glyphId: string | number) => {
    const n = nodes.find((x: any) => String(x?.id) === String(glyphId));
    if (!n || !controlsRef.current) return;

    const target = new THREE.Vector3(n.position[0], n.position[1], n.position[2]);

    // Prefer the imported tween namespace; fall back to global if present.
    const T = (TWEENNS as any)?.Tween ? (TWEENNS as any) : (globalThis as any).TWEEN;

    if (T && cameraRef.current) {
      new T.Tween(controlsRef.current.target)
        .to({ x: target.x, y: target.y, z: target.z }, 900)
        .easing(T.Easing.Quadratic.Out)
        .onUpdate(() => controlsRef.current.update?.())
        .start();

      const camPos = cameraRef.current.position.clone();
      new T.Tween(camPos)
        .to({ x: target.x + 5, y: target.y + 5, z: target.z + 5 }, 900)
        .easing(T.Easing.Quadratic.Out)
        .onUpdate(() => {
          if (!cameraRef.current) return;
          cameraRef.current.position.set(camPos.x, camPos.y, camPos.z);
          controlsRef.current.update?.();
        })
        .start();
    } else {
      try {
        controlsRef.current.target.copy(target);
        controlsRef.current.update?.();
      } catch {
        /* no-op */
      }
    }
  };
}

/** Center by glyph id/label using merged nodes (de-duped & safe) */
export function centerToGlyphFactory(opts: {
  mergedNodes: Array<{
    id?: string | number;
    glyph?: string | number;
    position: [number, number, number];
  }>;
  setObserverPosition: React.Dispatch<
    React.SetStateAction<[number, number, number]>
  >;
  setOrbitTargetToGlyph: (glyphId: string | number) => void;
}) {
  const { mergedNodes, setObserverPosition, setOrbitTargetToGlyph } = opts;

  return (glyphOrId: string | number) => {
    const key = String(glyphOrId);
    const node = mergedNodes.find(
      (n: any) => String(n?.id ?? "") === key || String(n?.glyph ?? "") === key
    );
    if (!node) {
      console.warn("❌ Glyph not found in nodes:", glyphOrId);
      return;
    }

    setObserverPosition(node.position as [number, number, number]);
    setOrbitTargetToGlyph((node as any).id ?? glyphOrId);
  };
}