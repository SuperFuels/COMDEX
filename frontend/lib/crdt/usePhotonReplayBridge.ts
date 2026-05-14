// frontend/lib/crdt/usePhotonReplayBridge.ts
import { useEffect } from "react"
import { journalEvent } from "@/lib/replay/journal"
import { usePhotonCRDT } from "./usePhotonCRDT"

// HUD pulse for remote replay events
function pulse() {
  if (typeof window === "undefined") return
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
  //     (HTTPS-safe: ws → wss when needed)
  //
  useEffect(() => {
    if (typeof window === "undefined") return

    const scheme = window.location.protocol === "https:" ? "wss" : "ws"
    const url = `${scheme}://${window.location.host}/ws/replay`

    let ws: WebSocket | null = null

    try {
      ws = new WebSocket(url)
    } catch (err) {
      console.warn("PhotonReplayBridge: failed to construct WebSocket", err)
      return
    }

    ws.onmessage = () => {
      try {
        pulse()
      } catch (err) {
        console.warn("PhotonReplayBridge: pulse handler failed", err)
      }
    }

    ws.onerror = (err) => {
      console.warn("PhotonReplayBridge: WebSocket error", err)
    }

    return () => {
      try {
        ws?.close()
      } catch {
        /* no-op */
      }
    }
  }, [])
}