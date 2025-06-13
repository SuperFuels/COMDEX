// File: frontend/pages/supplier/dashboard.tsx
"use client"

import { useEffect, useState, useRef } from "react"
import Draggable, { DraggableData, DraggableEvent } from "react-draggable"
import useAuthRedirect from "@/hooks/useAuthRedirect"
import Chart, { ChartPoint } from "@/components/Chart"
import api from "@/lib/api"

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
  useAuthRedirect("supplier")

  const containerRef = useRef<HTMLDivElement>(null)
  const [minX, setMinX]       = useState(0)
  const [maxX, setMaxX]       = useState(0)
  const [dividerX, setDividerX] = useState(0)

  const [metrics, setMetrics]       = useState<SupplierMetrics|null>(null)
  const [loadingMetrics, setLoading] = useState(true)
  const [error, setError]           = useState<string|null>(null)

  const [queryText, setQueryText]   = useState("")
  const [analysisText, setAnalysis] = useState("")
  const [chartData, setChartData]   = useState<ChartPoint[]|null>(null)
  const [searchResults, setResults] = useState<any[]|null>(null)
  const [isWorking, setWorking]     = useState(false)

  // measure & init
  useEffect(() => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    const W = rect.width
    const quarter = W * 0.25
    setMinX(quarter)
    setMaxX(W - quarter)
    setDividerX(W / 2)
  }, [])

  // load metrics
  useEffect(() => {
    let a = true
    api.get<SupplierMetrics>("/supplier/dashboard")
      .then(r=>a&&setMetrics(r.data))
      .catch(e=>a&&setError(e.message))
      .finally(()=>a&&setLoading(false))
    return()=>{ a=false }
  }, [])

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
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ prompt: queryText.trim() }),
        }
      )
      const json = await res.json() as TerminalPayload
      setAnalysis(json.analysisText||"")
      if (Array.isArray(json.visualPayload.products)) {
        setResults(json.visualPayload.products)
      } else if (Array.isArray(json.visualPayload.chartData)) {
        setChartData(json.visualPayload.chartData!)
      }
    } catch {
      setAnalysis("❌ Something went wrong.")
    } finally {
      setWorking(false)
    }
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key==="Enter") {
      e.preventDefault()
      handleSend()
    }
  }

  if (loadingMetrics) {
    return <div className="min-h-screen flex items-center justify-center bg-bg-page">
      <p className="text-text-secondary">Loading…</p>
    </div>
  }
  if (error||!metrics) {
    return <div className="min-h-screen flex items-center justify-center bg-bg-page">
      <p className="text-red-600">{error}</p>
    </div>
  }

  const m = metrics!
  const METRICS = [
    { label:"Sales Today",    value:m.totalSalesToday,   color:"text-blue-600" },
    { label:"Active Listings", value:m.activeListings,   color:"text-green-600" },
    { label:"Open Orders",     value:m.openOrders,        color:"text-green-600" },
    { label:"30d Proceeds",    value:`£${m.proceeds30d}`, color:"text-blue-600" },
    { label:"Feedback",        value:m.feedbackRating,    color:"text-purple-600" },
  ]
  const fallbackChart:ChartPoint[] = METRICS.map((_,i)=>({
    time: Math.floor(Date.now()/1000)-(METRICS.length-i)*3600,
    value: typeof METRICS[i].value==="number"?METRICS[i].value as number:0,
  }))

  return (
    <div className="bg-bg-page min-h-screen flex flex-col">
      <main ref={containerRef} className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="relative h-[calc(100vh-4rem-4rem)]">
          {/* draggable */}
          <Draggable
            axis="x"
            bounds={{ left:minX, right:maxX }}
            position={{ x:dividerX,y:0 }}
            onDrag={(_:DraggableEvent,d:DraggableData)=>{
              const x=Math.min(maxX,Math.max(minX,d.x))
              setDividerX(x)
            }}
          >
            <div
              className="absolute top-0 bottom-0 z-10 w-[6px] bg-border-light hover:bg-blue-500 cursor-col-resize transition-colors"
              style={{ left:dividerX }}
            />
          </Draggable>

          <div className="flex h-full">
            <div className="pr-2 font-mono text-text dark:text-text-secondary text-sm overflow-auto" style={{ width:dividerX }}>
              <p className="mb-2">Hello, Supplier — welcome.</p>
              {METRICS.map(mt=>(
                <p key={mt.label} className="mb-1">
                  <span>“{mt.label}”: </span>
                  <span className={mt.color}>{mt.value}</span>
                </p>
              ))}
              {analysisText&&(
                <div className="mt-4 space-y-1">
                  {analysisText.split("\n").map((l,i)=>(
                    <p key={i} className="mb-1">{l}</p>
                  ))}
                </div>
              )}
            </div>

            <div className="flex-1 pl-2 overflow-auto">
              {searchResults?(
                <div className="space-y-4">
                  {searchResults.map((it,i)=>(
                    <pre key={i} className="bg-white dark:bg-gray-800 p-3 rounded shadow text-xs">
                      {JSON.stringify(it,null,2)}
                    </pre>
                  ))}
                </div>
              ):(chartData||fallbackChart).length>0?(
                <Chart
                  data={chartData||fallbackChart}
                  height={Math.max(200,(containerRef.current?.clientHeight||400)-32)}
                />
              ):(
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
            <button
              onClick={handleSend}
              disabled={isWorking}
              className="py-2 px-4 bg-black text-white border rounded hover:bg-gray-900 disabled:opacity-50"
            >
              {isWorking?"Working…":"Send"}
            </button>
          </div>
          <div className="w-[50%] flex space-x-2 pl-4">
            {TABS.map(tab=>(
              <button
                key={tab}
                onClick={()=>{ setQueryText(tab.toLowerCase()); setTimeout(handleSend,50)}}
                className="py-2 px-4 text-sm font-medium border rounded bg-white dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-700"
              >{tab}</button>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}