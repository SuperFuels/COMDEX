// --- 🌊 PhotonLens Lifecycle Overlay ---
import { useEffect } from "react"
import { listenSCI } from "@/lib/sci"
import { usePhotonHUD } from "./usePhotonHUD"
import { mapPatternToHue } from "@/utils/patternHue"

interface MutationState {
  id: string
  hue: number
  intensity: number
  decay: number
}

export function usePhotonLensOverlay() {
  const { addGlowPulse, syncWavefield } = usePhotonHUD()
  const mutationMap = new Map<string, MutationState>()

  useEffect(() => {
    // --- 🔁 MUTATION (dynamic evolution bloom) ---
    const stopMutation = listenSCI("pattern_mutation", (evt: any) => {
      const { pattern_id, name, origin_sqi, new_sqi } = evt
      const delta = Math.abs(new_sqi - origin_sqi)
      if (delta < 0.005) return

      const hue = mapPatternToHue(pattern_id)
      const intensity = Math.min(delta * 4.5, 1.0)
      const decay = 0.92

      mutationMap.set(pattern_id, { id: pattern_id, hue, intensity, decay })

      addGlowPulse({
        hue,
        intensity,
        duration: 600,
        label: name,
        source: "pattern_mutation"
      })

      syncWavefield(intensity)
    })

    // --- 🌱 BIRTH (blue expansion) ---
    const stopBirth = listenSCI("pattern_birth", (evt: any) => {
      const { name, sqi } = evt
      const hue = 210
      const intensity = 0.25 + (sqi ?? 0.3) * 0.4

      addGlowPulse({
        hue,
        intensity,
        duration: 900,
        label: `${name} birth`,
        source: "pattern_birth"
      })

      syncWavefield(intensity * 0.6)
    })

    // --- ⚰️ COLLAPSE (red implosion) ---
    const stopCollapse = listenSCI("pattern_collapse", (evt: any) => {
      const { name, sqi } = evt
      const hue = 0
      const intensity = 0.2 + (1 - (sqi ?? 0.1)) * 0.6

      addGlowPulse({
        hue,
        intensity,
        duration: 800,
        label: `${name} collapse`,
        source: "pattern_collapse"
      })

      syncWavefield(-intensity * 0.5)
    })

    return () => {
      stopMutation()
      stopBirth()
      stopCollapse()
    }
  }, [])
}