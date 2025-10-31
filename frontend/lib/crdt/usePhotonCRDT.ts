import * as Y from "yjs"
import { WebsocketProvider } from "y-websocket"
import { useEffect, useRef, useState } from "react"
import { bootstrapReplay } from "@/lib/replay/bootstrapReplay"

export function usePhotonCRDT(docId: string = "photon_doc") {
  const ydocRef = useRef<Y.Doc>()
  const ytextRef = useRef<Y.Text>()
  const [content, setContent] = useState("")

  // Init once
  if (!ydocRef.current) {
    ydocRef.current = new Y.Doc()
    ytextRef.current = ydocRef.current.getText("photon")
  }

  useEffect(() => {
    const ydoc = ydocRef.current!
    const ytext = ytextRef.current!

    // Connect to CRDT websocket daemon
    const provider = new WebsocketProvider(
      "ws://localhost:8765",
      docId,
      ydoc
    )

    // Rehydrate document from replay log on load
    bootstrapReplay(docId, ytext)

    // Watch CRDT → React state
    const observer = () => setContent(ytext.toString())
    ytext.observe(observer)

    provider.on("status", (e: any) => {
      console.log("CRDT status:", e.status)
    })

    return () => {
      ytext.unobserve(observer)
      provider.destroy()
    }
  }, [docId])

  // Local editor → CRDT apply
  const updateContent = (v: string) => {
    const ytext = ytextRef.current!
    ytext.delete(0, ytext.length)
    ytext.insert(0, v)
  }

  return {
    content,
    updateContent,
    ydoc: ydocRef.current,
    ytext: ytextRef.current
  }
}