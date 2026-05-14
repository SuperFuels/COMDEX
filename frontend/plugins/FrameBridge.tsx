// frontend/plugins/FrameBridge.ts
import React from "react";
import { useThree, useFrame } from "@react-three/fiber";
import { pluginManager } from "./plugin_manager";

export type FrameBridgeProps = {
  /** Optional provider for live graph data */
  getGraph?: () => { nodes?: any[]; links?: any[] } | undefined;
  /** Optional tick source you maintain elsewhere (otherwise Date.now() is used) */
  tickRef?: React.MutableRefObject<number | undefined>;
};

/**
 * Place inside a <Canvas>. On every frame, calls plugins with:
 * { scene, camera, gl, nodes, links, tick }
 */
export default function FrameBridge({ getGraph, tickRef }: FrameBridgeProps) {
  const { scene, camera, gl } = useThree();

  useFrame(() => {
    const g = getGraph?.();
    const nodes = g?.nodes ?? [];
    const links = g?.links ?? [];
    const ctx: any = {
      scene,
      camera,
      gl,
      nodes,
      links,
      tick: tickRef?.current ?? Date.now(),
    };

    try {
      pluginManager.notifyRenderFrame(ctx);
    } catch (err) {
      if (process.env.NODE_ENV !== "production") {
        console.warn("[FrameBridge] notifyRenderFrame error:", err);
      }
    }
  });

  return null;
}