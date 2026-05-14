// frontend/hooks/useHUDPulse.ts
import { useEffect, useState } from "react"

export function useHUDPulse(key: string) {
  const [pulse, setPulse] = useState(0)

  useEffect(() => {
    const handler = () => {
      setPulse(Date.now()) // bump to trigger pulse UI
      setTimeout(() => setPulse(0), 300) // decay pulse
    }

    window.addEventListener("photon-wavefield-pulse", handler)
    return () => window.removeEventListener("photon-wavefield-pulse", handler)
  }, [key])

  return pulse
}