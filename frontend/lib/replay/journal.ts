// frontend/lib/replay/journal.ts

/**
 * Journal a replay event.
 * v1 = in-browser only, backend picks up via CRDT/WS
 */
export function journalEvent(evt: any) {
  if (!evt) return
  
  // Debug visibility during dev
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("photon-replay-event", { detail: evt })
    )
  }
}