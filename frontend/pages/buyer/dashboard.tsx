// File: frontend/pages/buyer/dashboard.tsx
"use client"

import { useEffect, useState, useRef } from "react"
import Draggable, { DraggableData, DraggableEvent } from "react-draggable"
import useAuthRedirect from "@/hooks/useAuthRedirect"
import api from "@/lib/api"
import Chart, { ChartPoint } from "@/components/Chart"

interface BuyerMetrics {
  totalSalesToday: number
  openOrders: number
  pendingEscrow: number
  availableProducts: number
  activeDeals: number
}

const METRICS = [
  { key: "totalSalesToday",   label: "Sales Today",        color: "text-blue-600" },
  { key: "openOrders",        label: "Open Orders",        color: "text-green-600" },
  { key: "pendingEscrow",     label: "Pending Escrow",     color: "text-purple-600" },
  { key: "availableProducts", label: "Available Products", color: "text-green-600" },
  { key: "activeDeals",       label: "Active Deals",       color: "text-blue-600" },
]

const COMMAND_TABS = [
  "Deal Flow","Shipments","Messages","Escrow",
  "Contracts","Suppliers","Products",
]

export default function BuyerDashboard() {
  useAuthRedirect("buyer")

  const containerRef = useRef<HTMLDivElement>(null)
  const [minX, setMinX]         = useState(0)
  const [maxX, setMaxX]         = useState(0)
  const [dividerX, setDividerX] = useState(0)

  const [metrics, setMetrics]               = useState<BuyerMetrics | null>(null)
  const [loadingMetrics, setLoadingMetrics] = useState(true)
  const [errorMetrics, setErrorMetrics]     = useState<string | null>(null)

  const [queryText, setQueryText]       = useState("")
  const [analysisText, setAnalysisText] = useState("")
  const [chartData, setChartData]       = useState<ChartPoint[] | null>(null)
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [nextPage, setNextPage]         = useState<number | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

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

  // fetch metrics
  useEffect(() => {
    let mounted = true
    api.get<BuyerMetrics>("/buyer/dashboard")
      .then(r => mounted && setMetrics(r.data))
      .catch(() => {
        if (mounted) {
          console.warn("Failed to fetch buyer metrics; using zeros.")
          setMetrics({
            totalSalesToday:   0,
            openOrders:        0,
            pendingEscrow:     0,
            availableProducts: 0,
            activeDeals:       0,
          })
        }
      })
      .finally(() => mounted && setLoadingMetrics(false))
    return () => { mounted = false }
  }, [])

  const handleSend = async () => {
    if (!queryText.trim()) return
    setIsProcessing(true)
    setAnalysisText("")
    setChartData(null)
    setSearchResults(null)
    setNextPage(null)

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/terminal/query`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: queryText.trim() }),
        }
      )
      const json = await res.json()
      setAnalysisText(json.analysisText || "")
      if (Array.isArray(json.visualPayload.products)) {
        setSearchResults(json.visualPayload.products)
        setNextPage((json.visualPayload as any).nextPage || null)
      } else if (Array.isArray(json.visualPayload.chartData)) {
        setChartData(json.visualPayload.chartData!)
      }
    } catch {
      setAnalysisText("❌ Something went wrong. Please try again.")
    } finally {
      setIsProcessing(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleSend()
    }
  }
  const handleTab = (label: string) => {
    setQueryText(label)
    setTimeout(handleSend, 50)
  }

  if (loadingMetrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }
  if (errorMetrics || !metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-500">{errorMetrics || "Error loading metrics"}</p>
      </div>
    )
  }

  const m = metrics
  const fallbackChart: ChartPoint[] = METRICS.map(({ key }) => ({
    time:  Math.floor(Date.now() / 1000),
    value: (m as any)[key] as number,
  }))

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <main ref={containerRef} className="flex-1 max-w-[calc(100%-40px)] mx-auto px-4">
        <div className="relative h-full">
          <Draggable
            axis="x"
            bounds={{ left: minX, right: maxX }}
            position={{ x: dividerX, y: 0 }}
            onDrag={(_, d: DraggableData) => {
              const x = Math.min(maxX, Math.max(minX, d.x))
              setDividerX(x)
            }}
          >
            <div
              className="absolute top-0 bottom-0 z-10 w-[6px] bg-gray-300 hover:bg-blue-500 cursor-col-resize transition-colors"
              style={{ left: dividerX }}
            />
          </Draggable>

          <div className="flex h-full">
            <div
              className="pr-4 font-mono text-gray-800 text-sm overflow-auto"
              style={{ width: dividerX }}
            >
              <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>
              {METRICS.map(({ key, label, color }) => {
                const val = (m as any)[key] || 0
                return (
                  <p key={key} className="mb-1">
                    <span>“{label}”: </span>
                    <span className={color}>{val}</span>
                  </p>
                )
              })}
              {analysisText && (
                <div className="mt-4 space-y-1">
                  {analysisText.split("\n").map((line, i) => (
                    <p key={i} className="mb-1">{line}</p>
                  ))}
                </div>
              )}
            </div>
            <div className="flex-1 pl-4 overflow-auto">
              {searchResults ? (
                <div className="space-y-4">
                  {searchResults.map((item, i) => (
                    <pre key={i} className="bg-white p-3 rounded shadow text-xs">
                      {JSON.stringify(item, null, 2)}
                    </pre>
                  ))}
                </div>
              ) : (chartData || fallbackChart).length > 0 ? (
                <Chart
                  data={chartData || fallbackChart}
                  height={Math.max(200, (containerRef.current?.clientHeight || 400) - 32)}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500">
                  <p>Select a button or ask a question to see visual output here.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <footer className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-300 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-4 flex">
          <div className="w-[calc(50%-20px)] flex items-center space-x-2">
            <input
              type="text"
              placeholder="Type a question…"
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 py-2 px-4 border rounded bg-white text-sm"
            />
            <button
              onClick={handleSend}
              disabled={isProcessing}
              className="py-2 px-4 bg-black text-white border rounded hover:bg-gray-900 disabled:opacity-50"
            >
              {isProcessing ? "Working…" : "Send"}
            </button>
          </div>
          <div className="w-[50%] flex flex-wrap items-center space-x-2 pl-8">
            {COMMAND_TABS.map(label => (
              <button
                key={label}
                onClick={() => handleTab(label)}
                className="px-3 py-1 border rounded-md text-sm hover:bg-gray-100"
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}