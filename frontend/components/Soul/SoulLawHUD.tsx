import { useEffect, useState } from 'react'
import useWebSocket from '@/hooks/useWebSocket'

type SoulLawEvent = {
  coord?: string
  glyph: string
  verdict: string
  tick: number
  timestamp: number
  container_id?: string
}

type AwarenessEvent = {
  type: 'uncertain_glyph' | 'blindspot_detected'
  glyph: string
  tick: number
  coord?: string
  container_id?: string
  context?: string
  confidence_score?: number
  timestamp: number
}

export default function SoulLawHUD() {
  const [events, setEvents] = useState<SoulLawEvent[]>([])
  const [awareness, setAwareness] = useState<AwarenessEvent[]>([])

  // Listen to GlyphNet awareness + SoulLaw
  useWebSocket(
    '/ws/glyphnet',
    (msg) => {
      if (msg?.type === 'soul_law_event' && msg.data) {
        setEvents((prev) => [msg.data, ...prev.slice(0, 49)])
      }
      if (
        (msg?.type === 'uncertain_glyph' || msg?.type === 'blindspot_detected') &&
        msg.data
      ) {
        setAwareness((prev) => [msg.data, ...prev.slice(0, 19)])
      }
    },
    ['soul_law_event', 'uncertain_glyph', 'blindspot_detected']
  )

  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-[85vh] overflow-y-auto p-3 bg-black bg-opacity-70 rounded-2xl shadow-2xl border border-purple-500 text-white text-sm z-50 space-y-6">
      
      {/* 🧠 SoulLaw Verdicts */}
      <div>
        <div className="font-bold text-purple-300 mb-2">🧠 SoulLaw Verdicts</div>
        {events.length === 0 && (
          <div className="text-gray-400 italic">No verdicts yet</div>
        )}
        {events.map((e, idx) => (
          <div
            key={`verdict-${e.timestamp}-${idx}`}
            className={`mb-2 p-2 rounded-lg ${
              e.verdict === 'violation'
                ? 'bg-red-800 border border-red-400'
                : 'bg-green-800 border border-green-400'
            }`}
          >
            <div className="flex justify-between">
              <span className="font-mono">{e.glyph}</span>
              <span className="text-xs text-gray-300">tick {e.tick}</span>
            </div>
            <div className="text-xs mt-1 space-y-1">
              <div><strong>Verdict:</strong> {e.verdict}</div>
              {e.coord && <div><strong>Coord:</strong> {e.coord}</div>}
              {e.container_id && <div><strong>Container:</strong> {e.container_id}</div>}
            </div>
          </div>
        ))}
      </div>

      {/* 👁️ Awareness Events */}
      <div>
        <div className="font-bold text-yellow-300 mb-2">👁️ Awareness Events</div>
        {awareness.length === 0 && (
          <div className="text-gray-400 italic">No blindspots or uncertainty</div>
        )}
        {awareness.map((a, idx) => (
          <div
            key={`awareness-${a.timestamp}-${idx}`}
            className={`mb-2 p-2 rounded-lg ${
              a.type === 'blindspot_detected'
                ? 'bg-yellow-900 border border-yellow-400'
                : 'bg-blue-900 border border-blue-400'
            }`}
          >
            <div className="flex justify-between">
              <span className="font-mono">{a.glyph}</span>
              <span className="text-xs text-gray-300">tick {a.tick}</span>
            </div>
            <div className="text-xs mt-1 space-y-1">
              <div>
                <strong>Type:</strong>{' '}
                {a.type === 'blindspot_detected' ? '⚠️ Blindspot' : '🌀 Low Confidence'}
              </div>
              {a.context && <div><strong>Context:</strong> {a.context}</div>}
              {a.coord && <div><strong>Coord:</strong> {a.coord}</div>}
              {a.container_id && <div><strong>Container:</strong> {a.container_id}</div>}
              {a.confidence_score !== undefined && (
                <div>
                  <strong>Confidence:</strong>{' '}
                  <span className={a.confidence_score < 0.5 ? 'text-red-300' : 'text-green-300'}>
                    {(a.confidence_score * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}