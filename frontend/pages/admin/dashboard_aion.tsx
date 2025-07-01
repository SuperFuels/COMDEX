'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import Chart from '@/components/Chart'

type AionMetrics = {
  maturityLevel: number
  memoryEntries: number
  currentEmotion: string
  lastInput: string
  lastAction: string
}

export default function AionDashboard() {
  useAuthRedirect('admin')

  const [metrics, setMetrics] = useState<AionMetrics | null>(null)
  const [queryText, setQueryText] = useState('')
  const [responseText, setResponseText] = useState('')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)
  const [dividerX, setDividerX] = useState(0)
  const dragging = useRef(false)

  useLayoutEffect(() => {
    const w = containerRef.current?.clientWidth ?? 0
    setDividerX(w / 2)
  }, [])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const { left, width } = containerRef.current.getBoundingClientRect()
      let x = e.clientX - left
      const min = width * 0.2, max = width * 0.8
      x = Math.max(min, Math.min(max, x))
      setDividerX(x)
    }
    const onUp = () => { dragging.current = false }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  const onDividerDown = (e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
  }

  useEffect(() => {
    let active = true
    fetch('/api/aion/metrics')
      .then(r => r.json())
      .then(data => active && setMetrics(data))
      .catch(err => active && setError(err.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  const sendQuery = async () => {
    if (!queryText.trim()) return
    setWorking(true)
    setResponseText('')
    try {
      const res = await fetch('/api/aion/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: queryText.trim() })
      })
      const json = await res.json()
      setResponseText(json.response || 'No response.')
    } catch {
      setResponseText('❌ Error talking to AION.')
    } finally {
      setWorking(false)
    }
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      sendQuery()
    }
  }

  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-gray-50">
      <p>Loading AION data…</p>
    </div>
  )
  if (error || !metrics) return (
    <div className="h-screen flex items-center justify-center bg-gray-50">
      <p className="text-red-500">{error || 'Error loading AION'}</p>
    </div>
  )

  const totalW = containerRef.current?.clientWidth ?? 0
  const rightWidth = Math.max(0, totalW - dividerX)

  return (
    <div className="relative flex flex-col h-screen bg-gray-50">
      <div ref={containerRef} className="relative flex-1 flex overflow-hidden min-h-0">
        <div
          className="bg-white p-6 overflow-auto min-w-0"
          style={{ flexBasis: dividerX, flexShrink: 0 }}
        >
          <h2 className="text-xl font-semibold mb-4">AION Core Status</h2>
          <p>Maturity Level: <span className="text-blue-600">{metrics.maturityLevel}</span></p>
          <p>Memory Entries: <span className="text-green-600">{metrics.memoryEntries}</span></p>
          <p>Current Emotion: <span className="text-purple-600">{metrics.currentEmotion}</span></p>
          <p className="mt-4 text-sm text-gray-500">Last Input:</p>
          <p className="italic text-gray-700">{metrics.lastInput}</p>
          <p className="mt-2 text-sm text-gray-500">Last Action:</p>
          <p className="italic text-gray-700">{metrics.lastAction}</p>
          {responseText && (
            <div className="mt-6 bg-gray-100 border border-gray-200 p-4 rounded">
              <p className="text-sm text-gray-700 whitespace-pre-line">{responseText}</p>
            </div>
          )}
        </div>

        <div
          onMouseDown={onDividerDown}
          className="absolute top-0 h-full w-1 bg-gray-300 cursor-col-resize z-20"
          style={{ left: dividerX - 0.5 }}
        />

        <div
          className="bg-white p-6 overflow-auto min-w-0"
          style={{ flexBasis: rightWidth, flexShrink: 0 }}
        >
          <textarea
            rows={6}
            placeholder="Speak to AION here..."
            className="w-full border border-gray-300 rounded p-3 mb-4"
            value={queryText}
            onChange={e => setQueryText(e.target.value)}
            onKeyDown={onKey}
          />
          <button
            onClick={sendQuery}
            disabled={working}
            className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            {working ? 'Thinking…' : 'Send to AION'}
          </button>
        </div>
      </div>
    </div>
  )
}
