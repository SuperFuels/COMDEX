// frontend/components/PhotonLensCanvas.tsx
import { useEffect, useRef } from "react"
import { initPhotonWavefield } from "@/lib/render/photonWavefield"

export default function PhotonLensCanvas() {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (ref.current) initPhotonWavefield(ref.current)
  }, [])

  return <canvas ref={ref} className="absolute inset-0 z-0" />
}