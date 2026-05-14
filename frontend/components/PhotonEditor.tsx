// frontend/components/photon/PhotonEditor.tsx
import { useState } from "react"
import { usePhotonCRDT } from "@/lib/crdt/usePhotonCRDT"
import { usePhotonTextBridge } from "@/lib/crdt/usePhotonTextBridge"
import { usePhotonReplayBridge } from "@/lib/crdt/usePhotonReplayBridge"
import { saveAtom } from "@/lib/atoms/useAtomSave"

export default function PhotonEditor({ docId = "default" }) {
  // CRDT state
  const { content, updateContent } = usePhotonCRDT(docId)

  // Sync live CRDT → glyph stream + HUD
  usePhotonTextBridge(docId)

  // ✅ NEW: connect replay reducer → CRDT doc
  usePhotonReplayBridge(docId)

  // Local UI preview values
  const [currentName, setCurrentName] = useState("Untitled")
  const [currentSQI, setCurrentSQI] = useState(0)
  const [currentGlyphStream, setCurrentGlyphStream] = useState<any[]>([])
  const [recentPatternIds, setRecentPatternIds] = useState<string[]>([])

  return (
    <div className="w-full flex flex-col gap-2">

      {/* document name */}
      <input
        className="bg-zinc-900 text-zinc-200 px-2 py-1 text-xs rounded"
        value={currentName}
        onChange={(e) => setCurrentName(e.target.value)}
        placeholder="Atom name"
      />

      {/* photon editor */}
      <textarea
        value={content}
        onChange={(e) => updateContent(e.target.value)}
        className="w-full h-[300px] bg-black text-green-300 p-2 font-mono text-sm rounded"
        placeholder="Photon CRDT editor — synced across Codex workspace"
      />

      {/* save button */}
      <button
        className="px-3 py-1 text-xs bg-purple-600 rounded hover:bg-purple-500 transition"
        onClick={async () => {
          await saveAtom({
            name: currentName,
            glyphs: currentGlyphStream,
            sqi: currentSQI,
            patterns: recentPatternIds
          })
        }}
      >
        ✦ Save to Atom Vault
      </button>
    </div>
  )
}