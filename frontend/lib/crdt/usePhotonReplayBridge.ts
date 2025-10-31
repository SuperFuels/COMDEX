// frontend/lib/crdt/usePhotonReplayBridge.ts
import { useEffect } from "react"
import { journalEvent } from "@/lib/replay/journal"
import { usePhotonCRDT } from "./usePhotonCRDT"

// HUD pulse for remote replay events
function pulse() {
  window.dispatchEvent(new CustomEvent("photon-replay-pulse"))
}

export function usePhotonReplayBridge(docId = "default") {
  const { ytext } = usePhotonCRDT(docId)

  //
  // ✅ 1) SEND local CRDT edits → replay log
  //
  useEffect(() => {
    if (!ytext) return

    const handler = () => {
      journalEvent({
        type: "photon_edit",
        doc: docId,
        content: ytext.toString(),
        ts: Date.now()
      })
    }

    ytext.observe(handler)
    return () => ytext.unobserve(handler)
  }, [ytext, docId])

  //
  // ✅ 2) LISTEN for remote replay events → HUD pulse
  //
  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/replay`)

    ws.onmessage = () => pulse()

    return () => ws.close()
  }, [])
}