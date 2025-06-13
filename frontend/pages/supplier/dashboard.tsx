"use client"

import { useEffect, useRef, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'

type SupplierMetrics = {
  totalSalesToday: number
  activeListings: number
  openOrders: number
  proceeds30d: number
  feedbackRating: number
}

type TerminalPayload = {
  analysisText: string
  visualPayload: {
    products?: any[]
    chartData?: ChartPoint[]
  }
}

const COMMAND_TABS = [
  'Sales','Marketing','Operations','Shipments','Financials','Clients'
]

export default function SupplierDashboard() {
  useAuthRedirect('supplier')

  // — Metrics —
  const [metrics, setMetrics] = useState<SupplierMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // — Terminal —
  const [queryText, setQueryText]   = useState('')
  const [analysisText, setAnalysis] = useState('')
  const [chartData, setChartData]   = useState<ChartPoint[] | null>(null)
  const [searchResults, setResults] = useState<any[] | null>(null)
  const [isWorking, setWorking]     = useState(false)

  // — Split-pane refs & state —
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging     = useRef(false)
  const [dividerX, setDividerX] = useState(0)

  // On mount measure and center divider
  useEffect(() => {
    const w = containerRef.current?.clientWidth
    if (w) setDividerX(w / 2)
  }, [])

  // Track global mouse move/up for dragging
  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!dragging.current || !containerRef.current) return
      const { left, width } = containerRef.current.getBoundingClientRect()
      let x = e.clientX - left
      // clamp: min 25%, max 75%
      const min = width * 0.25
      const max = width * 0.75
      x = Math.max(min, Math.min(max, x))
      setDividerX(x)
    }
    function onUp() { dragging.current = false }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  function onDividerDown(e: React.MouseEvent) {
    e.preventDefault()
    dragging.current = true
  }

  // Fetch supplier metrics
  useEffect(() => {
    let active = true
    api.get<SupplierMetrics>('/supplier/dashboard')
      .then(r => active && setMetrics(r.data))
      .catch(e => active && setError(e.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  // Send AI terminal query
  async function sendQuery() {
    if (!queryText.trim()) return
    setWorking(true)
    setAnalysis('')
    setResults(null)
    setChartData(null)
    try {
      const res  = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: queryText.trim() }),
        }
      )
      const json = (await res.json()) as TerminalPayload
      setAnalysis(json.analysisText || '')
      if (Array.isArray(json.visualPayload.products)) {
        setResults(json.visualPayload.products)
      } else if (Array.isArray(json.visualPayload.chartData)) {
        setChartData(json.visualPayload.chartData!)
      }
    } catch {
      setAnalysis('❌ Something went wrong. Please try again.')
    } finally {
      setWorking(false)
    }
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); sendQuery() }
  }

  function onTabClick(label: string) {
    setQueryText(label)
    setTimeout(sendQuery, 50)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p>Loading…</p>
      </div>
    )
  }
  if (error || !metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  const m = metrics
  const METRICS = [
    { label: 'Sales Today',    value: m.totalSalesToday,   color: 'text-blue-600' },
    { label: 'Active Listings', value: m.activeListings,   color: 'text-green-600' },
    { label: 'Open Orders',     value: m.openOrders,        color: 'text-green-600' },
    { label: '30d Proceeds',    value: `£${m.proceeds30d}`, color: 'text-blue-600'  },
    { label: 'Feedback',        value: m.feedbackRating,    color: 'text-purple-600' },
  ]

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div
          ref={containerRef}
          className="relative flex h-[calc(100vh-4rem-4rem)]"
        >
          {/* Left Pane */}
          <div
            className="overflow-auto pr-2 font-mono text-gray-800 text-sm"
            style={{ width: dividerX }}
          >
            <p className="mb-2">Hello, Supplier — welcome to Central Command.</p>
            {METRICS.map(mt => (
              <p key={mt.label} className="mb-1">
                <span>“{mt.label}”: </span>
                <span className={mt.color}>{mt.value}</span>
              </p>
            ))}
            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((l,i)=>
                  <p key={i} className="mb-1">{l}</p>
                )}
              </div>
            )}
          </div>

          {/* Divider */}
          <div
            onMouseDown={onDividerDown}
            className="cursor-col-resize bg-gray-300 hover:bg-blue-500"
            style={{ width: 6, marginLeft: -3, zIndex: 10 }}
          />

          {/* Right Pane */}
          <div className="flex-1 overflow-auto pl-2">
            {searchResults ? (
              <div className="space-y-4">
                {searchResults.map((item,i) => (
                  <pre
                    key={i}
                    className="bg-white p-3 rounded shadow text-xs"
                  >
                    {JSON.stringify(item, null, 2)}
                  </pre>
                ))}
              </div>
            ) : (chartData || []).length > 0 ? (
              <Chart
                data={chartData!}
                height={containerRef.current!.clientHeight - 64}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Select a tab or ask a question to see visual output here.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2 flex items-center justify-between">
          {/* Input + Send */}
          <div className="flex-1 flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              onKeyDown={onKey}
              className="flex-1 py-2 px-4 border rounded text-sm"
            />
            <button
              onClick={sendQuery}
              disabled={isWorking}
              className="py-2 px-4 bg-black text-white rounded disabled:opacity-50"
            >
              {isWorking ? 'Working…' : 'Send'}
            </button>
          </div>

          {/* Tabs */}
          <div className="flex space-x-2 ml-4">
            {COMMAND_TABS.map(tab => (
              <button
                key={tab}
                onClick={() => onTabClick(tab)}
                className="px-3 py-1 border rounded text-sm"
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}