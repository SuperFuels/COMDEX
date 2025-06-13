"use client"

import { useEffect, useState, useRef } from "react"
import Draggable from "react-draggable"
import useAuthRedirect from "@/hooks/useAuthRedirect"
import api from "@/lib/api"
import Chart, { ChartPoint } from "@/components/Chart"

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
  useAuthRedirect("supplier")

  const [metrics, setMetrics]       = useState<SupplierMetrics | null>(null)
  const [loadingMetrics, setLoading] = useState(true)
  const [error, setError]           = useState<string | null>(null)

  const [queryText, setQueryText]   = useState("")
  const [analysisText, setAnalysis] = useState("")
  const [chartData, setChartData]   = useState<ChartPoint[] | null>(null)
  const [searchResults, setResults] = useState<any[] | null>(null)
  const [isWorking, setWorking]     = useState(false)

  const TABS = ["Sales","Marketing","Operations","Shipments","Financials","Clients"]

  // ─── Divider state ─────────────────────────────────────────
  const initialX = typeof window !== "undefined" ? window.innerWidth * 0.5 : 300
  const [dividerX, setDividerX] = useState(initialX)
  const dragRef = useRef<HTMLDivElement>(null!)

  // ─── Fetch metrics ─────────────────────────────────────────
  useEffect(() => {
    let active = true
    api.get<SupplierMetrics>("/supplier/dashboard")
      .then(r => active && setMetrics(r.data))
      .catch(e => active && setError(e.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  // ─── Send terminal query ───────────────────────────────────
  const handleSend = async () => {
    if (!queryText.trim()) return
    setWorking(true)
    setAnalysis("")
    setResults(null)
    setChartData(null)

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: "POST",
          headers: { "Content-Type":"application/json" },
          body: JSON.stringify({ prompt: queryText.trim() }),
        }
      )
      const json = (await res.json()) as TerminalPayload
      setAnalysis(json.analysisText || "")
      if (Array.isArray(json.visualPayload.products)) {
        setResults(json.visualPayload.products)
      } else if (Array.isArray(json.visualPayload.chartData)) {
        setChartData(json.visualPayload.chartData!)
      }
    } catch {
      setAnalysis("❌ Something went wrong. Please try again.")
    } finally {
      setWorking(false)
    }
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleSend()
    }
  }

  if (loadingMetrics) {
    return <div className="min-h-screen flex items-center justify-center bg-bg-page"><p className="text-text-secondary">Loading…</p></div>
  }
  if (error || !metrics) {
    return <div className="min-h-screen flex items-center justify-center bg-bg-page"><p className="text-red-600">{error}</p></div>
  }

  const m = metrics
  const METRICS = [
    { label: "Sales Today",    value: m.totalSalesToday,   color: "text-blue-600" },
    { label: "Active Listings", value: m.activeListings,   color: "text-green-600" },
    { label: "Open Orders",     value: m.openOrders,        color: "text-green-600" },
    { label: "30d Proceeds",    value: `£${m.proceeds30d}`, color: "text-blue-600" },
    { label: "Feedback",        value: m.feedbackRating,    color: "text-purple-600" },
  ]
  const fallbackChart: ChartPoint[] = METRICS.map((_, i) => ({
    time:  Math.floor(Date.now()/1000) - (METRICS.length - i) * 3600,
    value: typeof METRICS[i].value === "number" ? METRICS[i].value as number : 0
  }))

  return (
    <div className="bg-bg-page min-h-screen flex flex-col">
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="relative h-[calc(100vh-4rem-4rem)]">

          <Draggable
            axis="x"
            bounds="parent"
            nodeRef={dragRef}
            position={{ x: dividerX, y: 0 }}
            onDrag={(_, d) => setDividerX(d.x)}
          >
            <div
              ref={dragRef}
              style={{
                position: "absolute", top: 0, bottom: 0, left: dividerX,
                width: "6px", cursor: "col-resize",
                background: "#3B82F6", zIndex: 10,
              }}
            />
          </Draggable>

          <div className="flex h-full">
            {/* Left */}
            <div style={{ width: dividerX, overflow: "auto" }} className="pr-2 font-mono text-text dark:text-text-secondary text-sm">
              <p className="mb-2">Hello, Supplier — welcome to Central Command.</p>
              {METRICS.map(mt => (
                <p key={mt.label} className="mb-1">
                  <span>“{mt.label}”: </span><span className={mt.color}>{mt.value}</span>
                </p>
              ))}
              {analysisText && (
                <div className="mt-4 space-y-1">
                  {analysisText.split("\n").map((l,i)=><p key={i} className="mb-1">{l}</p>)}
                </div>
              )}
            </div>

            {/* Right */}
            <div style={{ flex: 1, overflow: "auto" }} className="pl-2">
              {searchResults ? (
                <div className="space-y-4">
                  {searchResults.map((item,i)=>(
                    <pre key={i} className="bg-white dark:bg-gray-800 p-3 rounded shadow text-xs">
                      {JSON.stringify(item,null,2)}
                    </pre>
                  ))}
                </div>
              ) : (chartData||fallbackChart).length>0 ? (
                <Chart data={chartData||fallbackChart}
                       height={Math.floor(window.innerHeight - 4*16 - 64)} />
              ) : (
                <div className="h-full flex items-center justify-center text-text-secondary">
                  <p>Select a tab or ask a question to see visual output here.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <footer className="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 border-t border-border-light dark:border-gray-700 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2 flex">
          <div className="w-[calc(50%-20px)] flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={e=>setQueryText(e.target.value)}
              onKeyDown={onKey}
              className="flex-1 py-2 px-4 border rounded bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button onClick={handleSend} disabled={isWorking}
              className="py-2 px-4 bg-black text-white border rounded hover:bg-gray-900 disabled:opacity-50">
              {isWorking?"Working…":"Send"}
            </button>
          </div>
          <div className="w-[50%] flex space-x-2 pl-4">
            {TABS.map(tab=>(
              <button key={tab}
                onClick={()=>{ setQueryText(tab.toLowerCase()); setTimeout(handleSend,50) }}
                className="py-2 px-4 text-sm font-medium border rounded bg-white dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-700"
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