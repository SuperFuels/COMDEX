import { applyReplay } from "@/lib/api"

// Apply replay frames to CRDT document
export async function bootstrapReplay(docId: string, ytext: any) {
  try {
    const res = await fetch(`/api/replay/log?docId=${docId}`)
    const data = await res.json()
    const frames = data?.frames || []
    if (!frames.length) return

    const text = await applyReplay(frames)
    if (text?.content) {
      ytext.delete(0, ytext.length)
      ytext.insert(0, text.content)
      console.log("🔁 CRDT rehydrated from replay:", docId)
    }
  } catch (err) {
    console.warn("⚠️ Replay bootstrap failed:", err)
  }
}