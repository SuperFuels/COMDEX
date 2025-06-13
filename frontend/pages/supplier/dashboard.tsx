// File: frontend/pages/supplier/dashboard.tsx
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

const TABS = ['Sales','Marketing','Operations','Shipments','Financials','Clients']

export default function SupplierDashboard() {
  useAuthRedirect('supplier')

  // ── Metrics fetch ─────────────────────────────────────────────
  const [metrics, setMetrics] = useState<SupplierMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // ── Terminal state ────────────────────────────────────────────
  const [queryText, setQueryText]   = useState('')
  const [analysisText, setAnalysis] = useState('')
  const [chartData, setChartData]   = useState<ChartPoint[] | null>(null)
  const [searchResults, setResults] = useState<any[] | null>(null)
  const [isWorking, setWorking]     = useState(false)

  // ── Split‐pane ref & state ────────────────────────────────────
  const containerRef = useRef<HTMLDivElement>(null)
  const [dividerX, setDividerX] = useState(0)
  const dragging = useRef(false)

  // on mount, set initial divider to container midpoint
  useEffect(() => {
    const w = containerRef.current?.clientWidth
    if (w) setDividerX(w / 2)
  }, [])

  // handle document‐level mouse events
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return
      const { left, width } = containerRef.current.getBoundingClientRect()
      let x = e.clientX - left
      // enforce min 120px per pane
      x = Math.max(120, Math.min(width - 120, x))
      setDividerX(x)
    }
    const onMouseUp = () => { dragging.current = false }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  const onDividerMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
  }

  // ── Fetch supplier metrics ─────────────────────────────────────
  useEffect(() => {
    let active = true
    api.get<SupplierMetrics>('/supplier/dashboard')
      .then(r => active && setMetrics(r.data))
      .catch(e => active && setError(e.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  // ── Terminal query ────────────────────────────────────────────
  const handleSend = async () => {
    if (!queryText.trim()) return
    setWorking(true)
    setAnalysis('')
    setResults(null)
    setChartData(null)
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: { 'Content-Type':'application/json' },
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
      setAnalysis('❌ Something went wrong.')
    } finally {
      setWorking(false)
    }
  }
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); handleSend() }
  }
  const handleTab = (tab: string) => {
    setQueryText(tab)
    setTimeout(handleSend, 50)
  }

  // ── Loading / error UI ───────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }
  if (error || !metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  // build fallback spark-chart
  const m = metrics
  const SUMMARY = [
    { label: 'Sales Today',    value: m.totalSalesToday,  color: 'text-blue-600' },
    { label: 'Active Listings', value: m.activeListings, color: 'text-green-600' },
    { label: 'Open Orders',     value: m.openOrders,      color: 'text-green-600' },
    { label: '30d Proceeds',    value: `£${m.proceeds30d}`, color: 'text-blue-600' },
    { label: 'Feedback',        value: m.feedbackRating,  color: 'text-purple-600' },
  ]
  const fallback: ChartPoint[] = SUMMARY.map((_, i) => ({
    time:  Math.floor(Date.now()/1000) - (SUMMARY.length - i) * 3600,
    value: typeof SUMMARY[i].value === 'number'
      ? (SUMMARY[i].value as number)
      : 0
  }))

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-4">
        <div ref={containerRef} className="relative flex h-[calc(100vh-4rem-4rem)]">
          {/* Left Pane */}
          <div
            className="overflow-auto pr-2 font-mono text-gray-800 text-sm"
            style={{ width: dividerX }}
          >
            <p className="mb-2">Hello, Supplier — welcome to Central Command.</p>
            {SUMMARY.map(it => (
              <p key={it.label} className="mb-1">
                <span>“{it.label}”: </span>
                <span className={it.color}>{it.value}</span>
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
            onMouseDown={onDividerMouseDown}
            className="bg-gray-300 hover:bg-blue-500"
            style={{
              cursor: 'col-resize',
              width: 6,
              marginLeft: -3,
              zIndex: 10
            }}
          />

          {/* Right Pane */}
          <div className="overflow-auto pl-2 flex-1">
            {searchResults ? (
              <div className="space-y-4">
                {searchResults.map((item,i)=>
                  <pre key={i} className="bg-white p-3 rounded shadow text-xs">
                    {JSON.stringify(item,null,2)}
                  </pre>
                )}
              </div>
            ) : (chartData||fallback).length > 0 ? (
              <Chart
                data={chartData||fallback}
                height={window.innerHeight - (4*16) - 64}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Select a tab or ask a question…</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer Terminal */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-4 flex">
          <div className="w-[calc(50%-20px)] flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={e=>setQueryText(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 border rounded py-2 px-4 text-sm"
            />
            <button
              onClick={handleSend}
              disabled={isWorking}
              className="bg-black text-white border rounded py-2 px-4 hover:bg-gray-900 disabled:opacity-50"
            >
              {isWorking ? 'Working…' : 'Send'}
            </button>
          </div>
          <div className="w-[50%] flex space-x-2 pl-4">
            {TABS.map(tab=>(
              <button
                key={tab}
                onClick={()=>handleTab(tab)}
                className="border rounded px-3 py-1 text-sm hover:bg-gray-100"
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