// File: frontend/pages/supplier/dashboard.tsx
"use client"

import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import Chart, { ChartPoint } from '@/components/Chart'
import api from '@/lib/api'

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

export default function SupplierDashboard() {
  // block non-suppliers
  useAuthRedirect('supplier')

  // 1) supplier metrics state
  const [metrics, setMetrics]       = useState<SupplierMetrics | null>(null)
  const [loadingMetrics, setLoading] = useState(true)
  const [error, setError]           = useState<string | null>(null)

  // 2) terminal state
  const [queryText, setQueryText]   = useState('')
  const [analysisText, setAnalysis] = useState('')
  const [chartData, setChartData]   = useState<ChartPoint[] | null>(null)
  const [searchResults, setResults] = useState<any[] | null>(null)
  const [isWorking, setWorking]     = useState(false)

  const TABS = ['Sales','Marketing','Operations','Shipments','Financials','Clients']

  // ── Fetch supplier metrics
  useEffect(() => {
    let m = true
    api.get<SupplierMetrics>('/supplier/dashboard')
      .then(r => m && setMetrics(r.data))
      .catch(e=> m && setError(e.message))
      .finally(()=> m && setLoading(false))
    return ()=>{ m = false }
  }, [])

  // ── Send terminal query
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
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ prompt: queryText.trim() })
        }
      )
      const json = (await res.json()) as TerminalPayload

      setAnalysis(json.analysisText || '')
      const vp = json.visualPayload
      if (Array.isArray(vp.products))  setResults(vp.products)
      else if (Array.isArray(vp.chartData)) setChartData(vp.chartData!)
    } catch {
      setAnalysis('❌ Something went wrong. Please try again.')
    } finally {
      setWorking(false)
    }
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  // ── Loading / error
  if (loadingMetrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-text-secondary">Loading…</p>
      </div>
    )
  }
  if (error || !metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  // ── Render
  const m = metrics
  const METRICS = [
    { label: 'Sales Today',   value: m.totalSalesToday, color: 'text-blue-600' },
    { label: 'Active Listings', value: m.activeListings, color: 'text-green-600' },
    { label: 'Open Orders',    value: m.openOrders,    color: 'text-green-600' },
    { label: '30d Proceeds',   value: `£${m.proceeds30d}`, color: 'text-blue-600' },
    { label: 'Feedback',       value: m.feedbackRating, color: 'text-purple-600' },
  ]

  // sample fallback chart if needed
  const fallbackChart: ChartPoint[] = METRICS.map((_, i)=>({
    time: Math.floor(Date.now()/1000) - (METRICS.length - i) * 3600,
    value: typeof METRICS[i].value === 'number' ? METRICS[i].value as number : 0
  }))

  return (
    <div className="bg-bg-page min-h-screen flex flex-col">
      {/* Navbar spacer */}
      <div className="h-16" />

      {/* Main */}
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* Left Pane */}
          <div className="flex-1 overflow-auto pr-2 font-mono text-text dark:text-text-secondary text-sm">
            <p className="mb-2">Hello, Supplier — welcome to Central Command.</p>
            {METRICS.map((mt)=>(
              <p key={mt.label} className="mb-1">
                <span>{`“${mt.label}”: `}</span>
                <span className={mt.color}>{mt.value}</span>
              </p>
            ))}

            {/** AI analysis text */}
            {analysisText && (
              <div className="mt-4 space-y-1">
                {analysisText.split('\n').map((l,i)=>(
                  <p key={i} className="mb-1">{l}</p>
                ))}
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="w-px bg-border-light dark:bg-gray-700" />

          {/* Right Pane */}
          <div className="flex-1 overflow-auto pl-2">
            {searchResults ? (
              <div className="space-y-4">
                {searchResults.map((item,i)=>(
                  <pre key={i} className="bg-white dark:bg-gray-800 p-3 rounded shadow text-xs">
                    {JSON.stringify(item, null, 2)}
                  </pre>
                ))}
              </div>
            ) : (chartData || fallbackChart).length > 0 ? (
              <Chart
                data={chartData || fallbackChart}
                height={Math.floor(window.innerHeight - 4*16 - 64)}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-text-secondary">
                <p>Select a tab or ask a question to see visual output here.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer (terminal input + tabs) */}
      <footer className="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 border-t border-border-light dark:border-gray-700 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2 flex">
          {/* Input + Send */}
          <div className="w-[calc(50%-20px)] flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question (e.g. “Build my report”)"
              value={queryText}
              onChange={e=>setQueryText(e.target.value)}
              onKeyDown={onKey}
              className="flex-1 py-2 px-4 border border-black rounded bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleSend}
              disabled={isWorking}
              className="py-2 px-4 bg-black text-white border border-black rounded hover:bg-gray-900 disabled:opacity-50"
            >
              {isWorking ? 'Working…' : 'Send'}
            </button>
          </div>

          {/* Tabs */}
          <div className="w-[50%] flex space-x-2 pl-4">
            {TABS.map(tab=>(
              <button
                key={tab}
                onClick={()=>{
                  setQueryText(tab.toLowerCase())
                  setTimeout(handleSend, 50)
                }}
                className="py-2 px-4 text-sm font-medium border border-black rounded bg-white dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-700"
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