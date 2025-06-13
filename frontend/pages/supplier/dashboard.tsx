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

  // metrics + terminal
  const [metrics, setMetrics]       = useState<SupplierMetrics | null>(null)
  const [loadingMetrics, setLoading] = useState(true)
  const [error, setError]           = useState<string | null>(null)
  const [queryText, setQueryText]   = useState('')
  const [analysisText, setAnalysis] = useState('')
  const [chartData, setChartData]   = useState<ChartPoint[] | null>(null)
  const [searchResults, setResults] = useState<any[] | null>(null)
  const [isWorking, setWorking]     = useState(false)

  // split pane
  const containerRef = useRef<HTMLDivElement>(null)
  const [dividerX, setDividerX] = useState(0)
  const dragging = useRef(false)

  useEffect(() => {
    if (containerRef.current) {
      setDividerX(containerRef.current.clientWidth / 2)
    }
  }, [containerRef.current])

  const onMouseMove = (e: MouseEvent) => {
    if (!dragging.current || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    let x = e.clientX - rect.left
    x = Math.max(50, Math.min(rect.width - 50, x))
    setDividerX(x)
  }
  const onMouseUp = () => { dragging.current = false }
  const onMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    dragging.current = true
  }
  useEffect(() => {
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  // fetch metrics
  useEffect(() => {
    let active = true
    api.get<SupplierMetrics>('/supplier/dashboard')
      .then(r => active && setMetrics(r.data))
      .catch(e => active && setError(e.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  // terminal query
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
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ prompt: queryText.trim() }),
        }
      )
      const json = await res.json() as TerminalPayload
      setAnalysis(json.analysisText || '')
      if (Array.isArray(json.visualPayload.products)) setResults(json.visualPayload.products)
      else if (Array.isArray(json.visualPayload.chartData)) setChartData(json.visualPayload.chartData)
    } catch {
      setAnalysis('❌ Something went wrong.')
    } finally {
      setWorking(false)
    }
  }
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); handleSend() }
  }
  const handleTab = (tab: string) => {
    setQueryText(tab)
    setTimeout(handleSend, 50)
  }

  if (loadingMetrics) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50"><p>Loading…</p></div>
  }
  if (error || !metrics) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50"><p className="text-red-600">{error}</p></div>
  }

  const m = metrics
  const METRICS = [
    { label:'Sales Today',    value:m.totalSalesToday, color:'text-blue-600' },
    { label:'Active Listings',value:m.activeListings, color:'text-green-600' },
    { label:'Open Orders',    value:m.openOrders,      color:'text-green-600' },
    { label:'30d Proceeds',   value:`£${m.proceeds30d}`, color:'text-blue-600' },
    { label:'Feedback',       value:m.feedbackRating,  color:'text-purple-600' },
  ]
  const fallbackChart: ChartPoint[] = METRICS.map((_,i)=>({
    time: Math.floor(Date.now()/1000) - (METRICS.length - i)*3600,
    value: typeof METRICS[i].value === 'number' ? METRICS[i].value as number : 0,
  }))

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-4">
        <div ref={containerRef} className="relative h-[calc(100vh-4rem-4rem)]">
          <div className="absolute inset-0 flex">
            {/* Left Pane */}
            <div
              className="overflow-auto pr-2 font-mono text-gray-800 text-sm"
              style={{ width: dividerX }}
            >
              <p className="mb-2">Hello, Supplier — welcome to Central Command.</p>
              {METRICS.map(mt=>(
                <p key={mt.label} className="mb-1">
                  <span>“{mt.label}”: </span><span className={mt.color}>{mt.value}</span>
                </p>
              ))}
              {analysisText && (
                <div className="mt-4 space-y-1">
                  {analysisText.split('\n').map((l,i)=><p key={i}>{l}</p>)}
                </div>
              )}
            </div>
            {/* Divider */}
            <div
              onMouseDown={onMouseDown}
              style={{
                position:'absolute', left:dividerX-3, top:0, bottom:0,
                width:6, cursor:'col-resize', background:'#BBB', zIndex:20
              }}
            />
            {/* Right Pane */}
            <div
              className="overflow-auto pl-2"
              style={{ flex:1, marginLeft:dividerX+3 }}
            >
              {searchResults ? (
                <div className="space-y-4">
                  {searchResults.map((it,i)=>(
                    <pre key={i} className="bg-white p-3 rounded shadow text-xs">
                      {JSON.stringify(it,null,2)}
                    </pre>
                  ))}
                </div>
              ) : (chartData || fallbackChart).length>0 ? (
                <Chart data={chartData||fallbackChart} height={window.innerHeight-4*16-64} />
              ) : (
                <div className="h-full flex items-center justify-center">
                  <p>Select a tab or ask a question…</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* footer */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-4 flex">
          <div className="w-[calc(50%-20px)] flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={e=>setQueryText(e.target.value)}
              onKeyDown={onKeyDown}
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