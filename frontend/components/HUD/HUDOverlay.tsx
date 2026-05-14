// frontend/components/HUD/HUDOverlay.tsx
import { useHUDPulse } from "@/hooks/useHUDPulse"

export default function HUDOverlay() {
  const pulseKey = useHUDPulse("global-hud")

  return (
    <>
      {/* ✅ global pulse indicator */}
      {pulseKey > 0 && (
        <div className="hud-pulse bg-green-400/70 fixed top-2 right-2 rounded-full w-4 h-4 animate-ping" />
      )}

      {/* ✅ hook point for future SQI glow */}
      <div id="sqi-halo-overlay" className="pointer-events-none"></div>

      {/* ✅ optional waveform debug portal */}
      <div id="photon-wave-portal" className="pointer-events-none"></div>
    </>
  )
}