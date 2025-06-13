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

const COMMAND_TABS = ['Sales','Marketing','Operations','Shipments','Financials','Clients']

export default function SupplierDashboard() {
  useAuthRedirect('supplier')

  // ── Metrics ────────────────────────────────────────────────────
  const [metrics, setMetrics]       = useState<SupplierMetrics | null>(null)
  const [loadingMetrics, setLoading] = useState(true)
  const [error, setError]           = useState<string | null>(null)

  // ── Terminal ───────────────────────────────────────────────────
  const [queryText, setQueryText]   = useState('')
  const [analysisText, setAnalysis] = useState('')
  const [chartData, setChartData]   = useState<ChartPoint[] | null>(null)
  const [searchResults, setResults] = useState<any[] | null>(null)
  const [isWorking, setWorking]     = useState(false)

  // ── Split-pane refs & state ───────────────────────────────────
  const containerRef = useRef<HTMLDivElement>(null)
  const [dividerX, setDividerX] = useState(0)
  const dragging = useRef(false)

  // center divider on mount
  useEffect(() => {
    const w = containerRef.current?.clientWidth
    if (w) setDividerX(w / 2)
  }, [])

  // global mouse handlers for drag
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const { left, width } = containerRef.current.getBoundingClientRect()
      let x = e.clientX - left
      // enforce 25%–75% bounds
      x = Math.max(width * 0.25, Math.min(width * 0.75, x))
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

  // ── Fetch metrics ──────────────────────────────────────────────
  useEffect(() => {
    let active = true
    api.get<SupplierMetrics>('/supplier/dashboard')
      .then(r => active && setMetrics(r.data))
      .catch(e => active && setError(e.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  // ── Terminal send ─────────────────────────────────────────────
  const sendQuery = async () => {
    if (!queryText.trim()) return
    setWorking(true)
    setAnalysis('')
    setResults(null)
    setChartData(null)

    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: queryText.trim() }),
        }
      )
      const json = (await resp.json()) as TerminalPayload
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
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      sendQuery()
    }
  }
  const onTabClick = (label: string) => {
    setQueryText(label)
    setTimeout(sendQuery, 50)
  }

  // ── Render ─────────────────────────────────────────────────────
  if (loadingMetrics) {
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

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <main className="flex-1 mx-auto px-2 max-w-[calc(100%-40px)]">
        <div
          ref={containerRef}
          className="relative flex h-[calc(100vh-4rem-4rem)]"
        >
          {/* Left Pane */}
          <div
            className="overflow-auto pr-2 font-mono text-gray-800 text-sm"
            style={{ width: dividerX }}
          >
            <p className="mb-2">Hello, Supplier — welcome.</p>
            <p>“Sales Today”: <span className="text-blue-600">{m.totalSalesToday}</span></p>
            <p>“Active Listings”: <span className="text-green-600">{m.activeListings}</span></p>
            <p>“Open Orders”: <span className="text-green-600">{m.openOrders}</span></p>
            <p>“30d Proceeds”: <span className="text-blue-600">£{m.proceeds30d}</span></p>
            <p>“Feedback”: <span className="text-purple-600">{m.feedbackRating}</span></p>
            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((l,i)=><p key={i}>{l}</p>)}
              </div>
            )}
          </div>

          {/* Divider */}
          <div
            onMouseDown={onDividerDown}
            className="bg-gray-300 hover:bg-blue-500"
            style={{ cursor:'col-resize', width:6, marginLeft:-3, zIndex:10 }}
          />

          {/* Right Pane */}
          <div className="flex-1 overflow-auto pl-2">
            {searchResults ? (
              searchResults.map((item,i)=>(
                <pre
                  key={i}
                  className="bg-white p-3 rounded shadow mb-2 text-xs"
                >{JSON.stringify(item, null, 2)}</pre>
              ))
            ) : chartData && chartData.length > 0 ? (
              <Chart
                data={chartData}
                height={(containerRef.current?.clientHeight ?? 400) - 32}
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
        <div className="max-w-[calc(100%-40px)] mx-auto px-2 flex">
          <div className="w-[calc(50%-20px)] flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={e=>setQueryText(e.target.value)}
              onKeyDown={onKey}
              className="flex-1 py-2 px-4 border rounded text-sm"
            />
            <button
              onClick={sendQuery}
              disabled={isWorking}
              className="py-2 px-4 bg-black text-white rounded text-sm"
            >
              {isWorking ? 'Working…' : 'Send'}
            </button>
          </div>
          <div className="flex-1 flex justify-end space-x-2 pl-4">
            {COMMAND_TABS.map(tab=>(
              <button
                key={tab}
                onClick={()=>onTabClick(tab)}
                className="px-3 py-1 border rounded text-sm"
              >{tab}</button>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}