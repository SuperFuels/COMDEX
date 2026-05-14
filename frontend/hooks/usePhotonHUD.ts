import { useState } from "react";

interface GlowPulseArgs {
  hue: number
  intensity: number
  duration: number
  label?: string
  source?: string
}

export function usePhotonHUD() {
  const [glowPulses, setGlowPulses] = useState<GlowPulseArgs[]>([])

  function addGlowPulse({ hue, intensity, duration, label, source }: GlowPulseArgs) {
    const pulse = {
      hue,
      intensity,
      duration,
      label,
      source,
      ts: performance.now()
    }

    setGlowPulses(p => [...p, pulse])
    setTimeout(() => setGlowPulses(p => p.filter(x => x !== pulse)), duration)
  }

  function syncWavefield(v: number) {
    // positive = outward pulse, negative = inward contraction
    window.dispatchEvent(
      new CustomEvent("photon-wavefield-pulse", { detail: { v } })
    )
  }

  return { addGlowPulse, syncWavefield, glowPulses }
}