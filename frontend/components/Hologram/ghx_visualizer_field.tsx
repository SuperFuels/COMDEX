// File: frontend/components/Hologram/ghx_visualizer_field.tsx

import React, { useEffect, useRef, useState } from "react"
import useWebSocket from "../../hooks/useWebSocket"
import {
  renderGHXBeam,
  renderGlyphCollapse,
  renderPatternOverlay,
} from "./ghxFieldRenderers"
import CodexHUD from "@/components/AION/CodexHUD";

interface GHXVisualizerProps {
  containerId: string
  width?: number
  height?: number
}

export const GHXVisualizerField: React.FC<GHXVisualizerProps> = ({
  containerId,
  width = 1200,
  height = 800,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [ctx, setCtx] = useState<CanvasRenderingContext2D | null>(null)

  // WebSocket hook
  const handleWebSocketMessage = (data: any) => {
    const type = data.type || data.event

    if (!type || !ctx) return

    switch (type) {
      case "ghx_beam":
        renderGHXBeam(ctx, data.payload)
        break

      case "ghx_collapse":
        renderGlyphCollapse(ctx, data.payload)
        break

      case "ghx_pattern":
        renderPatternOverlay(ctx, data.payload)
        break

      case "container_loaded":
        if (data.container_id === containerId) {
          ctx.clearRect(0, 0, width, height)
        }
        break

      default:
        break
    }
  }

  const { connected, emit } = useWebSocket("/ws/ghx", handleWebSocketMessage, [
    "ghx_beam",
    "ghx_collapse",
    "ghx_pattern",
    "container_loaded",
  ])

  // Set canvas context on mount
  useEffect(() => {
    if (canvasRef.current) {
      setCtx(canvasRef.current.getContext("2d"))
    }
  }, [])

  return (
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="rounded-2xl shadow-xl border border-gray-800 bg-black"
      />
      <CodexHUD containerId={containerId} />
    </div>
  )
}