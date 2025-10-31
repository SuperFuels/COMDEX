import * as Y from "yjs"
import { WebsocketProvider } from "y-websocket"

export function initPhotonCRDT(docId = "photon-room-1") {
  const ydoc = new Y.Doc()

  const provider = new WebsocketProvider(
    "ws://localhost:8765",
    docId,
    ydoc,
  )

  const ytext = ydoc.getText("photon")

  return { ydoc, provider, ytext }
}