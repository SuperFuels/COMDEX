import { useEffect, useState } from "react"
import { initPhotonCRDT } from "@/lib/crdt/photonCRDT"

export function usePhotonCRDT() {
  const [{ ytext }, set] = useState<any>({})

  useEffect(() => {
    const { ytext } = initPhotonCRDT()
    set({ ytext })
  }, [])

  return ytext
}