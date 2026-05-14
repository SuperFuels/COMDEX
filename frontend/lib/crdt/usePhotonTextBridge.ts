import { useEffect } from "react"
import { usePhotonCRDT } from "./usePhotonCRDT"
import { journalEvent } from "@/lib/replay/journal"

// HUD event pulse
function pulseWave(intensity: number) {
  window.dispatchEvent(
    new CustomEvent("photon-wavefield-pulse", { detail: { v: intensity } })
  )
}

async function sendToSCI(text: string) {
  try {
    await fetch("/api/photon/ingest_text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
  } catch {}
}

function textToGlyphPulse(text: string): number {
  if (!text) return 0
  const last = text.at(-1)
  if ("⊕⟲⟧⟦μπ".includes(last ?? "")) return 0.7
  if ("+-*/".includes(last ?? "")) return 0.4
  return 0.2
}

export function usePhotonTextBridge(docId: string = "default") {
  const { content, ytext } = usePhotonCRDT(docId)

  // CRDT → Replay journal
  useEffect(() => {
    if (!ytext) return

    const handler = () => {
      journalEvent({
        type: "glyph_edit",
        doc: docId,
        content: ytext.toString()
      })
    }

    ytext.observe(handler)
    return () => ytext.unobserve(handler)
  }, [ytext, docId])

  // HUD + SCI pulse stream
  useEffect(() => {
    if (!content) return
    const strength = textToGlyphPulse(content)
    pulseWave(strength)
    sendToSCI(content)
  }, [content])
}