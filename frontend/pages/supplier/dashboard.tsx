'use client'

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

  // Metrics
  const [metrics, setMetrics] = useState<SupplierMetrics|null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string|null>(null)

  // Terminal
  const [queryText, setQueryText]   = useState('')
  const [analysisText, setAnalysis] = useState('')
  const [chartData, setChartData]   = useState<ChartPoint[]|null>(null)
  const [searchResults, setResults] = useState<any[]|null>(null)
  const [working, setWorking]       = useState(false)

  // Split-pane
  const containerRef = useRef<HTMLDivElement>(null)
  const [dividerX, setDividerX] = useState(0)
  const dragging = useRef(false)

  // center on mount
  useEffect(() => {
    const w = containerRef.current?.clientWidth||0
    setDividerX(w/2)
  }, [])

  // drag handlers
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current||!containerRef.current) return
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

  // fetch metrics
  useEffect(() => {
    api.get<SupplierMetrics>('/supplier/dashboard')
      .then(r=>setMetrics(r.data))
      .catch(e=>setError(e.message))
      .finally(()=>setLoading(false))
  }, [])

  // query terminal
  const sendQuery = async () => {
    if (!queryText.trim()) return
    setWorking(true)
    setAnalysis(''); setResults(null); setChartData(null)
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: queryText.trim() })
        }
      )
      const j = await res.json() as TerminalPayload
      setAnalysis(j.analysisText||'')
      if (Array.isArray(j.visualPayload.products)) setResults(j.visualPayload.products)
      else if (Array.isArray(j.visualPayload.chartData)) setChartData(j.visualPayload.chartData)
    } catch {
      setAnalysis('❌ Something went wrong.')
    } finally {
      setWorking(false)
    }
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key==='Enter') { e.preventDefault(); sendQuery() }
  }

  const onTabClick = (lbl: string) => {
    setQueryText(lbl)
    setTimeout(sendQuery, 50)
  }

  if (loading) return <div className="h-screen flex items-center justify-center">Loading…</div>
  if (error||!metrics) return <div className="h-screen flex items-center justify-center text-red-500">{error||'Error'}</div>

  return (
    <div className="relative flex flex-col h-screen bg-gray-50">
      {/* Panes container */}
      <div ref={containerRef} className="relative flex-1 flex overflow-hidden">
        {/* Left Pane */}
        <div
          className="bg-white p-6 overflow-auto"
          style={{ flexBasis: dividerX, flexShrink: 0 }}
        >
          <h2 className="text-xl font-semibold mb-4">Hello, Supplier — welcome.</h2>
          <p>Sales Today: <span className="text-blue-600">{metrics.totalSalesToday}</span></p>
          <p>Active Listings: <span className="text-green-600">{metrics.activeListings}</span></p>
          <p>Open Orders: <span className="text-green-600">{metrics.openOrders}</span></p>
          <p>30d Proceeds: <span className="text-blue-600">£{metrics.proceeds30d}</span></p>
          <p>Feedback: <span className="text-purple-600">{metrics.feedbackRating}</span></p>
          {analysisText && (
            <div className="mt-6 space-y-1">
              {analysisText.split('\n').map((l,i)=><p key={i}>{l}</p>)}
            </div>
          )}
        </div>

        {/* Draggable Divider */}
        <div
          onMouseDown={onDividerDown}
          className="absolute top-0 h-full bg-gray-200 cursor-col-resize"
          style={{ left: dividerX-3, width: 6, zIndex: 20 }}
        />

        {/* Right Pane */}
        <div
          className="bg-white p-6 overflow-auto flex-1"
          style={{ marginLeft: dividerX }}
        >
          {searchResults ? (
            searchResults.map((item,i)=>(
              <div key={i} className="bg-white border border-gray-200 rounded p-4 mb-4 shadow-sm">
                <pre className="text-xs">{JSON.stringify(item,null,2)}</pre>
              </div>
            ))
          ) : chartData?.length ? (
            <Chart
              data={chartData}
              height={(containerRef.current?.clientHeight||0)-64}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              <p>Select a tab or ask a question to see visual output here.</p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Footer */}
      <footer className="absolute bottom-0 left-0 w-full bg-white border-t border-gray-200 px-6 py-3 flex items-center space-x-3">
        <input
          type="text"
          className="flex-1 border border-gray-300 rounded px-4 py-2"
          placeholder="Type a question…"
          value={queryText}
          onChange={e=>setQueryText(e.target.value)}
          onKeyDown={onKey}
        />
        <button
          onClick={sendQuery}
          disabled={working}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {working ? 'Working…' : 'Send'}
        </button>
        <div className="flex space-x-2">
          {COMMAND_TABS.map(label=>(
            <button
              key={label}
              onClick={()=>onTabClick(label)}
              className="px-3 py-1 border rounded text-sm"
            >
              {label}
            </button>
          ))}
        </div>
      </footer>
    </div>
  )
}