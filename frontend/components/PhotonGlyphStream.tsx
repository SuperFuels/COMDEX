import { useEffect, useState } from "react"

export function PhotonGlyphStream() {
  const [glyphs, setGlyphs] = useState<any[]>([])

  useEffect(() => {
    const sse = new EventSource("/api/sci/stream")
    sse.onmessage = (msg) => {
      const evt = JSON.parse(msg.data)
      if (evt.type === "glyph_stream") setGlyphs(evt.data.glyphs)
    }
    return () => sse.close()
  }, [])

  return (
    <div className="bg-black text-cyan-300 p-2 text-xs font-mono h-32 overflow-auto border">
      {glyphs.map((g, i) => (
        <span key={i} className="mr-1">{g.text}</span>
      ))}
    </div>
  )
}